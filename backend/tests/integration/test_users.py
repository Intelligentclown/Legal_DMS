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
from sqlalchemy import func, select
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


async def _grant_permissions(db_session: AsyncSession, user: User, *permission_codes: str) -> None:
    """T63's own, more general sibling of `_grant_users_manage()` above --
    attaches one uniquely-named `Role` carrying every given (already-seeded)
    permission code to `user`. Left standalone rather than rewriting
    `_grant_users_manage()` to delegate to this, so T62's existing tests
    stay untouched."""
    role = Role(name=f"Role-{uuid4()}")
    db_session.add(role)
    await db_session.flush()
    for code in permission_codes:
        result = await db_session.execute(select(Permission).where(Permission.code == code))
        permission = result.scalar_one()
        db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()


async def _headers_with_permissions(
    client: AsyncClient, db_session: AsyncSession, *permission_codes: str
) -> dict[str, str]:
    caller = await _make_user(db_session)
    await _grant_permissions(db_session, caller, *permission_codes)
    access_token = await _login(client, caller)
    return {"Authorization": f"Bearer {access_token}"}


async def _make_role(db_session: AsyncSession, **overrides: object) -> Role:
    defaults: dict[str, object] = {"name": f"Role-{uuid4()}"}
    role = Role(**{**defaults, **overrides})
    db_session.add(role)
    await db_session.flush()
    return role


class TestAuthorization:
    async def test_list_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_list_invalid_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/users", headers={"Authorization": "Bearer not-a-real-token"}
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_list_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _unauthorized_headers(client, db_session)

        response = await client.get("/api/v1/users", headers=headers)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_get_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.get(f"/api/v1/users/{user.id}")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_get_invalid_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.get(
            f"/api/v1/users/{user.id}", headers={"Authorization": "Bearer not-a-real-token"}
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_get_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        headers = await _unauthorized_headers(client, db_session)

        response = await client.get(f"/api/v1/users/{user.id}", headers=headers)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_create_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users",
            json={"email": f"{uuid4()}@example.com", "full_name": "Nobody", "password": "x"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_create_invalid_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/users",
            json={"email": f"{uuid4()}@example.com", "full_name": "Nobody", "password": "x"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

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
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_update_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": user.email, "full_name": user.full_name, "phone": None},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_update_invalid_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.put(
            f"/api/v1/users/{user.id}",
            json={"email": user.email, "full_name": user.full_name, "phone": None},
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

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
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_deactivate_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.post(f"/api/v1/users/{user.id}/deactivate")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_deactivate_invalid_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/deactivate",
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_deactivate_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        headers = await _unauthorized_headers(client, db_session)

        response = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)


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
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)


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
        assert response.json()["error"]["code"] == "conflict"
        assert isinstance(response.json()["error"]["message"], str)


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
        assert response.json()["error"]["code"] == "validation_error"
        assert isinstance(response.json()["error"]["message"], str)

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
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

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
        assert response.json()["error"]["code"] == "conflict"
        assert isinstance(response.json()["error"]["message"], str)


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
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)


class TestRoleAssignmentAuthorization:
    """T63: both role-assignment routes share T62's router-level dependency,
    now `RequirePermission("users:manage", "roles:manage")` -- allowed on
    *either* permission alone, not just `users:manage`."""

    async def test_assign_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_assign_invalid_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles",
            json={"role_id": str(role.id)},
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_remove_requires_authentication(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_remove_invalid_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)

        response = await client.delete(
            f"/api/v1/users/{user.id}/roles/{role.id}",
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_assign_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        headers = await _unauthorized_headers(client, db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_remove_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        headers = await _unauthorized_headers(client, db_session)

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_users_manage_alone_allows_assign(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        headers = await _headers_with_permissions(client, db_session, "users:manage")

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 201

    async def test_roles_manage_alone_allows_assign(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        headers = await _headers_with_permissions(client, db_session, "roles:manage")

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 201

    async def test_users_manage_alone_allows_remove(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()
        headers = await _headers_with_permissions(client, db_session, "users:manage")

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204

    async def test_roles_manage_alone_allows_remove(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()
        headers = await _headers_with_permissions(client, db_session, "roles:manage")

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204

    async def test_both_permissions_together_still_allowed(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        headers = await _headers_with_permissions(
            client, db_session, "users:manage", "roles:manage"
        )

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 201

    async def test_existing_single_permission_behavior_is_unchanged(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Regression (also covers items 10/31): T62's own `list_users`
        route -- still gated by the same router-level dependency, now
        carrying two permission codes instead of one -- continues denying
        an unpermitted caller and allowing a `users:manage` one exactly as
        before T63."""
        headers = await _authorized_headers(client, db_session)
        denied_headers = await _unauthorized_headers(client, db_session)

        allowed = await client.get("/api/v1/users", headers=headers)
        denied = await client.get("/api/v1/users", headers=denied_headers)

        assert allowed.status_code == 200
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "forbidden"
        assert isinstance(denied.json()["error"]["message"], str)


class TestAssignRole:
    async def test_valid_assignment_returns_201_with_correct_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        caller = await _make_user(db_session)
        await _grant_permissions(db_session, caller, "users:manage")
        access_token = await _login(client, caller)
        headers = {"Authorization": f"Bearer {access_token}"}
        target = await _make_user(db_session)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{target.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["user_id"] == str(target.id)
        assert data["role_id"] == str(role.id)
        assert data["assigned_at"] is not None
        assert data["assigned_by"] == str(caller.id)

    async def test_unknown_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{uuid4()}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_unknown_role_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(uuid4())}, headers=headers
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_duplicate_assignment_returns_409_and_creates_no_second_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)
        role = await _make_role(db_session)

        first = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )
        second = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert first.status_code == 201
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "conflict"
        assert isinstance(second.json()["error"]["message"], str)
        result = await db_session.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
        assert len(result.scalars().all()) == 1

    async def test_assignment_creates_no_role_or_role_permission_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        roles_before = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()
        role_permissions_before = (
            await db_session.execute(select(func.count()).select_from(RolePermission))
        ).scalar_one()

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 201
        roles_after = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()
        role_permissions_after = (
            await db_session.execute(select(func.count()).select_from(RolePermission))
        ).scalar_one()
        assert roles_after == roles_before
        assert role_permissions_after == role_permissions_before


class TestRemoveRole:
    async def test_existing_assignment_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204
        assert response.content == b""

    async def test_user_role_and_other_assignments_remain(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)
        role_to_remove = await _make_role(db_session)
        other_role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role_to_remove.id))
        db_session.add(UserRole(user_id=user.id, role_id=other_role.id))
        await db_session.flush()

        response = await client.delete(
            f"/api/v1/users/{user.id}/roles/{role_to_remove.id}", headers=headers
        )

        assert response.status_code == 204
        assert await db_session.get(User, user.id) is not None
        assert await db_session.get(Role, role_to_remove.id) is not None
        remaining = await db_session.execute(select(UserRole).where(UserRole.user_id == user.id))
        remaining_role_ids = {row.role_id for row in remaining.scalars().all()}
        assert remaining_role_ids == {other_role.id}

    async def test_missing_assignment_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)
        role = await _make_role(db_session)  # never assigned to `user`

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_unknown_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        role = await _make_role(db_session)

        response = await client.delete(f"/api/v1/users/{uuid4()}/roles/{role.id}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_unknown_role_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{uuid4()}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_removal_creates_no_role_or_role_permission_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers = await _authorized_headers(client, db_session)
        user = await _make_user(db_session)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()
        roles_before = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()
        role_permissions_before = (
            await db_session.execute(select(func.count()).select_from(RolePermission))
        ).scalar_one()

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204
        roles_after = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()
        role_permissions_after = (
            await db_session.execute(select(func.count()).select_from(RolePermission))
        ).scalar_one()
        assert roles_after == roles_before
        assert role_permissions_after == role_permissions_before
