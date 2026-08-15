"""Integration tests for T61's `GET /api/v1/auth/me`, against the real
mounted FastAPI app and real Postgres.

Reuses T58/T59/T60's `test_auth_login.py` pattern verbatim: `httpx.AsyncClient`
against an `ASGITransport` wrapping the real `app`, with `get_db` overridden
(test-infrastructure only) to yield this test's own `db_session` -- needed
because `fastapi.testclient.TestClient` runs the app on a separate
event-loop thread, which breaks a `db_session`-backed override.

`/me` is the first route to go through `CurrentUserDep` (T52-T57) rather
than `AuthServiceDep` -- these tests are the first real-HTTP-request proof
that a missing, malformed, expired, or inactive-user token all resolve to
the same 401 via that dependency chain, not just `RequirePermission`'s
unit-level coverage.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import get_db
from app.infrastructure.persistence.models.identity import Role, User, UserRole
from app.infrastructure.security.jwt_service import create_access_token
from app.infrastructure.security.password_hasher import hash_password
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
    return response.json()["access_token"]


async def _assign_role(db_session: AsyncSession, user: User, role_name: str) -> None:
    role = Role(name=role_name)
    db_session.add(role)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()


class TestMe:
    async def test_valid_token_returns_profile_and_roles(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, full_name="Ada Advocate")
        role_name = f"Role-{uuid4()}"
        await _assign_role(db_session, user, role_name)
        access_token = await _login(client, user)

        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(user.id)
        assert data["display_name"] == "Ada Advocate"
        assert data["roles"] == [role_name]

    async def test_missing_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_malformed_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
        )

        assert response.status_code == 401

    async def test_expired_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        settings = get_settings()
        user = await _make_user(db_session)
        expired_settings = settings.model_copy(update={"access_token_ttl_minutes": -1})
        token = create_access_token(str(user.id), [], expired_settings)

        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401

    async def test_inactive_user_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        access_token = await _login(client, user)
        user.is_active = False
        await db_session.flush()

        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 401

    async def test_unknown_user_token_returns_401(self, client: AsyncClient) -> None:
        settings = get_settings()
        token = create_access_token(str(uuid4()), [], settings)

        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401

    async def test_multiple_roles_all_returned(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        first_role = f"Alpha-{uuid4()}"
        second_role = f"Beta-{uuid4()}"
        await _assign_role(db_session, user, first_role)
        await _assign_role(db_session, user, second_role)
        access_token = await _login(client, user)

        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        assert response.json()["data"]["roles"] == [first_role, second_role]
