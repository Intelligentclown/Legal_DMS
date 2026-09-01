"""Integration tests for T60's `POST /api/v1/auth/logout`, against the real
mounted FastAPI app and real Postgres.

Reuses T58/T59's `test_auth_login.py`/`test_auth_refresh.py` pattern
verbatim: `httpx.AsyncClient` against an `ASGITransport` wrapping the real
`app`, with `get_db` overridden (test-infrastructure only) to yield this
test's own `db_session` -- needed because `fastapi.testclient.TestClient`
runs the app on a separate event-loop thread, which breaks a
`db_session`-backed override.

`AuthService.revoke()` (T50/T51) never raises and never returns a
`Result` -- an unknown or already-revoked token is a silent no-op, not a
failure. These tests prove that idempotent shape holds through the real
HTTP route: all three cases (valid, already-revoked, unknown token) return
`204`; only the valid-token case actually flips `revoked_at` in the
database, verified directly via a real `RefreshToken` row.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import get_admin_db, get_db
from app.infrastructure.persistence.models.identity import RefreshToken, User
from app.infrastructure.security.jwt_service import create_refresh_token
from app.infrastructure.security.password_hasher import hash_password
from app.infrastructure.security.token_hasher import hash_token
from app.main import app

_PASSWORD = "correct horse battery staple"


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # T105: AuthService (login/refresh/logout) now uses get_admin_db(), not
    # get_db() -- override both to the same db_session, or a row created
    # here via db_session (uncommitted) would be invisible to get_admin_db()'s
    # own, independent real connection.
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_admin_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_admin_db, None)


async def _make_user(db_session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": f"{uuid4()}@example.com",
        "full_name": "Test Advocate",
        "password_hash": hash_password(_PASSWORD),
        "is_active": True,
    }
    user = User(**{**defaults, **overrides})
    db_session.add(user)
    await db_session.flush()
    return user


async def _login(client: AsyncClient, user: User) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
    )
    assert response.status_code == 200
    return response.json()["refresh_token"]


async def _get_stored_token(db_session: AsyncSession, refresh_token: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


class TestLogout:
    async def test_valid_refresh_token_is_revoked(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        refresh_token = await _login(client, user)

        response = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})

        assert response.status_code == 204
        assert response.content == b""
        stored = await _get_stored_token(db_session, refresh_token)
        assert stored is not None
        assert stored.revoked_at is not None

    async def test_already_revoked_token_succeeds(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        refresh_token = await _login(client, user)
        first = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert first.status_code == 204

        second = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})

        assert second.status_code == 204

    async def test_unknown_token_succeeds(self, client: AsyncClient) -> None:
        settings = get_settings()
        never_issued = create_refresh_token(str(uuid4()), settings)

        response = await client.post("/api/v1/auth/logout", json={"refresh_token": never_issued})

        assert response.status_code == 204

    async def test_malformed_token_string_succeeds(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": "not-a-real-token"}
        )

        assert response.status_code == 204

    async def test_malformed_request_body_returns_422(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/auth/logout", json={})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert isinstance(response.json()["error"]["message"], str)
