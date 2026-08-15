"""Integration tests for T59's `POST /api/v1/auth/refresh`, against the real
mounted FastAPI app and real Postgres.

Reuses T58's `test_auth_login.py` pattern verbatim: `httpx.AsyncClient`
against an `ASGITransport` wrapping the real `app`, with `get_db` overridden
(test-infrastructure only) to yield this test's own `db_session` -- needed
because `fastapi.testclient.TestClient` runs the app on a separate
event-loop thread, which breaks a `db_session`-backed override.

`AuthService.refresh()` (T50/T51) already proves the underlying logic
correct at the unit level (`tests/unit/test_auth_service.py`'s `TestRefresh`)
-- these tests prove the same scenarios are reachable and correctly
translated through the real HTTP route: a real login, rotation, and each of
`refresh()`'s four identical-message failure branches (invalid, expired,
revoked, unknown), built the same way that unit suite does but against a
real `RefreshToken` row via `db_session` instead of an in-memory fake.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import get_db
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

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


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


class TestRefresh:
    async def test_valid_refresh_token_returns_a_new_token_pair(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        refresh_token = await _login(client, user)

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["refresh_token"] != refresh_token
        assert body["token_type"] == "bearer"

    async def test_rotated_token_cannot_be_reused(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        refresh_token = await _login(client, user)

        first_use = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        second_use = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )

        assert first_use.status_code == 200
        assert second_use.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
        )

        assert response.status_code == 401

    async def test_expired_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Defense in depth: a syntactically valid, correctly-signed token
        whose *stored row* has already expired, independent of its own JWT
        `exp` claim -- mirrors `test_auth_service.py`'s
        `test_jwt_valid_but_db_row_expired_fails`."""
        settings = get_settings()
        user = await _make_user(db_session)
        token = create_refresh_token(str(user.id), settings)
        db_session.add(
            RefreshToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=hash_token(token),
                issued_at=datetime.now(UTC) - timedelta(days=30),
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await db_session.flush()

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})

        assert response.status_code == 401

    async def test_revoked_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        refresh_token = await _login(client, user)

        await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 401

    async def test_unknown_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """A syntactically valid, correctly-signed refresh token that was
        never actually issued (no matching stored row)."""
        settings = get_settings()
        never_issued = create_refresh_token(str(uuid4()), settings)

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": never_issued})

        assert response.status_code == 401

    async def test_malformed_request_body_returns_422(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 422
