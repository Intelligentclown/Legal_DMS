"""Integration tests for T62's user-management routes (`GET`/`POST
/api/v1/users`, `GET`/`PUT /api/v1/users/{id}`, `POST
/api/v1/users/{id}/deactivate`), against the real mounted FastAPI app and
real Postgres.

Reuses T58-T61's `client` fixture / `_make_user()` / `_login()` pattern
verbatim (`httpx.AsyncClient` + `ASGITransport`, `get_db` overridden to
yield this test's own `db_session`).

All five routes share one router-level `RequirePermission("users:manage")`
dependency (T62) -- `_grant_users_manage()` is this file's own addition: it
creates a uniquely-named `Role`, attaches it to the already-**seeded**
`Permission(code="users:manage")` row (the seed migration deliberately does
not seed `role_permissions` itself -- T66's exact matrix is still pending
sign-off), and assigns that role to a user via `UserRole`, mirroring
`test_auth_dependency_wiring.py`'s existing role/permission grant pattern
rather than inventing a new one.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.persistence.models.identity import (
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.security.password_hasher import hash_password, verify_password
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


async def _grant_users_manage(db_session: AsyncSession, user: User) -> None:
    stmt = select(Permission).where(Permission.code == "users:manage")
    result = await db_session.execute(stmt)
    permission = result.scalar_one()

    role = Role(name=f"Role-{uuid4()}")
    db_session.add(role)
    await db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()


async def _authorized_headers(client: AsyncClient, db_session: AsyncSession) -> dict[str, str]:
    caller = await _make_user(db_session)
    await _grant_users_manage(db_session, caller)
    access_token = await _login(client, caller)
    return {"Authorization": f"Bearer {access_token}"}


async def _unauthorized_headers(client: AsyncClient, db_session: AsyncSession) -> dict[str, str]:
    """A real, authenticated caller who was never granted `users:manage`."""
    caller = await _make_user(db_session)
    access_token = await _login(client, caller)
    return {"Authorization": f"Bearer {access_token}"}


def _assert_no_password_fields(payload: dict[str, object]) -> None:
    assert "password" not in payload
    assert "password_hash" not in payload


class TestAuthorization:
    async def test_list_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users")

        assert response.status_code == 401

    async def test_list_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _unauthorized_headers(client, db_session)

        response = await client.get("/api/v1/users", headers=headers)

        assert response.status_code == 403

    async def test_get_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.get(f"/api/v1/users/{user.id}")

        assert response.status_code == 401

    async def test_get_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        headers = await _unauthorized_headers(client, db_session)

        response = await client.get(f"/api/v1/users/{user.id}", headers=headers)

        assert response.status_code == 403

    async def test_create_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users",
            json={"email": f"{uuid4()}@example.com", "full_name": "Nobody", "password": "x"},
        )

        assert response.status_code == 401

    async def test_create_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _unauthorized_headers(client, db_session)

        response = await client.post(
            "/api/v1/users",
            json={"email": f"{uuid4()}@example.com", "full_name": "Nobody", "password": "x"},
            headers=headers,
        )

        assert response.status_code == 403

    async def test_update_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": user.email, "full_name": user.full_name, "phone": None},
        )

        assert response.status_code == 401

    async def test_update_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        headers = await _unauthorized_headers(client, db_session)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": user.email, "full_name": user.full_name, "phone": None},
            headers=headers,
        )

        assert response.status_code == 403

    async def test_deactivate_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.post(f"/api/v1/users/{user.id}/deactivate")

        assert response.status_code == 401

    async def test_deactivate_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        headers = await _unauthorized_headers(client, db_session)

        response = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 403


class TestListUsers:
    async def test_list_returns_paginated_users(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        known = [await _make_user(db_session) for _ in range(2)]

        response = await client.get("/api/v1/users?page=1&page_size=100", headers=headers)

        assert response.status_code == 200
        body = response.json()
        emails = {item["email"] for item in body["data"]}
        for user in known:
            assert user.email in emails
            _assert_no_password_fields(next(i for i in body["data"] if i["email"] == user.email))
        pagination = body["meta"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 100
        assert pagination["total"] >= len(known)

    async def test_pagination_limit_and_offset(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        for _ in range(3):
            await _make_user(db_session)

        first_page = await client.get("/api/v1/users?page=1&page_size=1", headers=headers)
        second_page = await client.get("/api/v1/users?page=2&page_size=1", headers=headers)

        assert first_page.status_code == 200
        assert second_page.status_code == 200
        first_body = first_page.json()
        second_body = second_page.json()
        assert len(first_body["data"]) == 1
        assert len(second_body["data"]) == 1
        assert first_body["data"][0]["id"] != second_body["data"][0]["id"]
        assert first_body["meta"]["pagination"]["total"] >= 4  # 3 made here + the caller itself


class TestGetUser:
    async def test_existing_user_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, full_name="Grace Advocate", phone="555-0100")

        response = await client.get(f"/api/v1/users/{user.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(user.id)
        assert data["email"] == user.email
        assert data["full_name"] == "Grace Advocate"
        assert data["phone"] == "555-0100"
        assert data["is_active"] is True
        assert data["last_login_at"] is None
        _assert_no_password_fields(data)

    async def test_unknown_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)

        response = await client.get(f"/api/v1/users/{uuid4()}", headers=headers)

        assert response.status_code == 404


class TestCreateUser:
    async def test_valid_create_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        email = f"{uuid4()}@example.com"

        response = await client.post(
            "/api/v1/users",
            json={
                "email": email,
                "full_name": "New Advocate",
                "phone": "555-0101",
                "password": "a-brand-new-password",
            },
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["email"] == email
        assert data["full_name"] == "New Advocate"
        assert data["phone"] == "555-0101"
        assert data["is_active"] is True
        assert data["last_login_at"] is None
        _assert_no_password_fields(data)
        assert "a-brand-new-password" not in response.text

    async def test_password_is_hashed_in_database(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        email = f"{uuid4()}@example.com"

        response = await client.post(
            "/api/v1/users",
            json={"email": email, "full_name": "New Advocate", "password": "a-plaintext-secret"},
            headers=headers,
        )
        user_id = response.json()["data"]["id"]

        stored = await db_session.get(User, user_id)
        assert stored is not None
        assert stored.password_hash != "a-plaintext-secret"
        assert verify_password("a-plaintext-secret", stored.password_hash) is True

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        existing = await _make_user(db_session)

        response = await client.post(
            "/api/v1/users",
            json={"email": existing.email, "full_name": "Someone Else", "password": "x"},
            headers=headers,
        )

        assert response.status_code == 409


class TestUpdateUser:
    async def test_valid_full_put_updates_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, full_name="Old Name", phone="555-0000")
        new_email = f"{uuid4()}@example.com"

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": new_email, "full_name": "New Name", "phone": "555-9999"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == new_email
        assert data["full_name"] == "New Name"
        assert data["phone"] == "555-9999"

    async def test_updating_to_its_own_unchanged_email_succeeds(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": user.email, "full_name": "Renamed", "phone": None},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["full_name"] == "Renamed"

    async def test_missing_required_field_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": user.email, "full_name": "New Name"},  # "phone" key omitted
            headers=headers,
        )

        assert response.status_code == 422

    async def test_password_cannot_be_updated_through_this_route(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={
                "email": user.email,
                "full_name": user.full_name,
                "phone": None,
                "password": "a-smuggled-password",
            },
            headers=headers,
        )

        assert response.status_code == 200
        stored = await db_session.get(User, user.id)
        assert stored is not None
        assert verify_password(_PASSWORD, stored.password_hash) is True

    async def test_is_active_cannot_be_changed_through_this_route(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, is_active=True)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={
                "email": user.email,
                "full_name": user.full_name,
                "phone": None,
                "is_active": False,
            },
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is True

    async def test_unknown_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)

        response = await client.put(
            f"/api/v1/users/{uuid4()}",
            json={"email": "nobody@example.com", "full_name": "Nobody", "phone": None},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        first = await _make_user(db_session)
        second = await _make_user(db_session)

        response = await client.put(
            f"/api/v1/users/{second.id}",
            json={"email": first.email, "full_name": second.full_name, "phone": None},
            headers=headers,
        )

        assert response.status_code == 409


class TestDeactivateUser:
    async def test_active_user_becomes_inactive(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, is_active=True)

        response = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    async def test_database_row_and_relationships_are_preserved(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)
        await _grant_users_manage(db_session, user)  # gives the user a UserRole row too
        await _login(client, user)  # gives the user a RefreshToken row

        response = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 200
        stored = await db_session.get(User, user.id)
        assert stored is not None
        assert stored.is_active is False
        role_count = await db_session.execute(select(UserRole).where(UserRole.user_id == user.id))
        assert role_count.scalars().first() is not None
        token_count = await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        assert token_count.scalars().first() is not None

    async def test_second_deactivate_remains_successful(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)

        first = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)
        second = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["data"]["is_active"] is False

    async def test_unknown_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)

        response = await client.post(f"/api/v1/users/{uuid4()}/deactivate", headers=headers)

        assert response.status_code == 404
