"""Integration tests for T62/T63's user-management routes (`GET`/`POST
/api/v1/users`, `GET`/`PUT /api/v1/users/{id}`, `POST
/api/v1/users/{id}/deactivate`, `POST /api/v1/users/{id}/roles`, `DELETE
/api/v1/users/{id}/roles/{role_id}`), against the real mounted FastAPI app
and real Postgres -- extended by T105 for Organization scoping.

Reuses T58-T61's `client` fixture / `_make_user()` / `_login()` pattern
verbatim (`httpx.AsyncClient` + `ASGITransport`, `get_db` overridden to
yield this test's own `db_session` -- the admin/owning Postgres role, which
bypasses RLS entirely as a superuser). **This file therefore does not
exercise RLS enforcement itself** -- it exercises this task's
application-layer scoping (`_require_organization()`/
`get_by_id_in_organization()` in `users.py`), which is independent of RLS
and must hold regardless of which role is actually connected. RLS
enforcement is covered separately by `test_organizations_users_rls.py` and
`test_users_organization_scoping_end_to_end.py` (the latter deliberately
does *not* override `get_db`, so it runs through the real restricted role).

T105: `_authorized_headers()`/`_unauthorized_headers()`/
`_headers_with_permissions()` now each create (or reuse, if passed) an
Organization and attach the caller to it, returning `(headers,
organization)` -- every existing test that creates an additional target
user via `_make_user()` passes `organization_id=organization.id` so the
target lands in the *same* Organization as the caller, preserving each
test's original pass/fail expectation. New `organization=<other>` tests
below prove the opposite (cross-Organization) case.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_admin_db, get_db
from app.infrastructure.persistence.models.identity import (
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.security.password_hasher import hash_password, verify_password
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


async def _make_organization(db_session: AsyncSession, **overrides: object) -> Organization:
    defaults: dict[str, object] = {"name": f"Org-{uuid4()}"}
    organization = Organization(**{**defaults, **overrides})
    db_session.add(organization)
    await db_session.flush()
    return organization


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


async def _authorized_headers(
    client: AsyncClient, db_session: AsyncSession, *, organization: Organization | None = None
) -> tuple[dict[str, str], Organization]:
    organization = organization or await _make_organization(db_session)
    caller = await _make_user(db_session, organization_id=organization.id)
    await _grant_users_manage(db_session, caller)
    access_token = await _login(client, caller)
    return {"Authorization": f"Bearer {access_token}"}, organization


async def _unauthorized_headers(
    client: AsyncClient, db_session: AsyncSession, *, organization: Organization | None = None
) -> tuple[dict[str, str], Organization]:
    """A real, authenticated caller who was never granted `users:manage`."""
    organization = organization or await _make_organization(db_session)
    caller = await _make_user(db_session, organization_id=organization.id)
    access_token = await _login(client, caller)
    return {"Authorization": f"Bearer {access_token}"}, organization


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
    client: AsyncClient,
    db_session: AsyncSession,
    *permission_codes: str,
    organization: Organization | None = None,
) -> tuple[dict[str, str], Organization]:
    organization = organization or await _make_organization(db_session)
    caller = await _make_user(db_session, organization_id=organization.id)
    await _grant_permissions(db_session, caller, *permission_codes)
    access_token = await _login(client, caller)
    return {"Authorization": f"Bearer {access_token}"}, organization


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
        headers, _organization = await _unauthorized_headers(client, db_session)

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
        headers, organization = await _unauthorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

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
        headers, _organization = await _unauthorized_headers(client, db_session)

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
        headers, organization = await _unauthorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

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
        headers, organization = await _unauthorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

        response = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)


class TestNoOrganizationFailsClosed:
    """T105/ADR-0021: an authenticated, `users:manage`-holding caller with
    no resolved Organization (e.g. one created via `create_user`, which
    always produces `organization_id = NULL`) must still be rejected on
    every one of these six routes -- never proceeds "unscoped."."""

    async def test_list_returns_403_for_an_organization_less_caller(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        caller = await _make_user(db_session)
        await _grant_users_manage(db_session, caller)
        access_token = await _login(client, caller)

        response = await client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_get_returns_403_for_an_organization_less_caller(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        caller = await _make_user(db_session)
        await _grant_users_manage(db_session, caller)
        access_token = await _login(client, caller)
        target = await _make_user(db_session)

        response = await client.get(
            f"/api/v1/users/{target.id}", headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"


class TestListUsers:
    async def test_list_returns_paginated_users(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        known = [await _make_user(db_session, organization_id=organization.id) for _ in range(2)]

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
        headers, organization = await _authorized_headers(client, db_session)
        for _ in range(3):
            await _make_user(db_session, organization_id=organization.id)

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

    async def test_list_never_includes_a_different_organizations_users(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
        other_organization = await _make_organization(db_session)
        outsider = await _make_user(db_session, organization_id=other_organization.id)

        response = await client.get("/api/v1/users?page=1&page_size=100", headers=headers)

        assert response.status_code == 200
        emails = {item["email"] for item in response.json()["data"]}
        assert outsider.email not in emails


class TestGetUser:
    async def test_existing_user_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(
            db_session,
            full_name="Grace Advocate",
            phone="555-0100",
            organization_id=organization.id,
        )

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
        headers, _organization = await _authorized_headers(client, db_session)

        response = await client.get(f"/api/v1/users/{uuid4()}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)


class TestCrossOrganizationScoping:
    """T105/ADR-0021: a request targeting a User outside the caller's own
    Organization gets the same `404` as a genuinely nonexistent id -- never
    a distinguishable response that would leak the target's existence."""

    async def test_get_returns_404_for_a_different_organizations_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
        other_organization = await _make_organization(db_session)
        outsider = await _make_user(db_session, organization_id=other_organization.id)

        response = await client.get(f"/api/v1/users/{outsider.id}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    async def test_put_returns_404_for_a_different_organizations_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
        other_organization = await _make_organization(db_session)
        outsider = await _make_user(db_session, organization_id=other_organization.id)

        response = await client.put(
            f"/api/v1/users/{outsider.id}",
            json={"email": outsider.email, "full_name": "Hijacked", "phone": None},
            headers=headers,
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    async def test_deactivate_returns_404_for_a_different_organizations_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
        other_organization = await _make_organization(db_session)
        outsider = await _make_user(
            db_session, organization_id=other_organization.id, is_active=True
        )

        response = await client.post(f"/api/v1/users/{outsider.id}/deactivate", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    async def test_assign_role_returns_404_for_a_different_organizations_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
        other_organization = await _make_organization(db_session)
        outsider = await _make_user(db_session, organization_id=other_organization.id)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{outsider.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    async def test_remove_role_returns_404_for_a_different_organizations_user(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
        other_organization = await _make_organization(db_session)
        outsider = await _make_user(db_session, organization_id=other_organization.id)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=outsider.id, role_id=role.id))
        await db_session.flush()

        response = await client.delete(
            f"/api/v1/users/{outsider.id}/roles/{role.id}", headers=headers
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestSameOrganizationWrongPermissionAndWrongOrganizationCorrectPermission:
    """ADR/0022's own named regression test, run together: neither
    ADR/0021's tenant check nor ADR/0022's permission check alone is
    sufficient -- a same-Organization caller with no permission is denied
    (403), and a correctly-permissioned caller in the *wrong* Organization
    is denied too (404, not a leak)."""

    async def test_same_organization_wrong_permission_is_denied(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        organization = await _make_organization(db_session)
        headers, _organization = await _unauthorized_headers(
            client, db_session, organization=organization
        )
        target = await _make_user(db_session, organization_id=organization.id)

        response = await client.get(f"/api/v1/users/{target.id}", headers=headers)

        assert response.status_code == 403

    async def test_correct_permission_wrong_organization_is_denied(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _caller_organization = await _authorized_headers(client, db_session)
        other_organization = await _make_organization(db_session)
        target = await _make_user(db_session, organization_id=other_organization.id)

        response = await client.get(f"/api/v1/users/{target.id}", headers=headers)

        assert response.status_code == 404


class TestCreateUser:
    async def test_valid_create_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
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
        headers, _organization = await _authorized_headers(client, db_session)
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
        headers, organization = await _authorized_headers(client, db_session)
        existing = await _make_user(db_session, organization_id=organization.id)

        response = await client.post(
            "/api/v1/users",
            json={"email": existing.email, "full_name": "Someone Else", "password": "x"},
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"
        assert isinstance(response.json()["error"]["message"], str)


class TestCreateUserOrganizationContract:
    """T105/ADR-0031 SS6.4: deterministic contract tests for `create_user`'s
    deliberately-unchanged Organization behavior -- not a before/after diff
    (this repository has no golden/snapshot mechanism), but direct
    assertions on the actual observable contract."""

    async def test_user_create_schema_has_no_organization_id_field(self) -> None:
        from app.presentation.api.v1.users import UserCreate

        assert "organization_id" not in UserCreate.model_fields

    async def test_created_user_always_has_organization_id_null(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)

        response = await client.post(
            "/api/v1/users",
            json={
                "email": f"{uuid4()}@example.com",
                "full_name": "Org-less New User",
                "password": "x",
            },
            headers=headers,
        )

        assert response.status_code == 201
        stored = await db_session.get(User, response.json()["data"]["id"])
        assert stored is not None
        assert stored.organization_id is None

    async def test_a_client_supplied_organization_id_has_no_effect(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        email = f"{uuid4()}@example.com"

        response = await client.post(
            "/api/v1/users",
            json={
                "email": email,
                "full_name": "Smuggled Field Attempt",
                "password": "x",
                # Not a real field on UserCreate -- Pydantic silently ignores
                # unknown fields by default, and create_user() never reads
                # payload.organization_id (it doesn't exist). This must have
                # zero effect, including *not* assigning the caller's own
                # otherwise-legitimate-looking Organization.
                "organization_id": str(organization.id),
            },
            headers=headers,
        )

        assert response.status_code == 201
        stored = await db_session.get(User, response.json()["data"]["id"])
        assert stored is not None
        assert stored.organization_id is None


class TestUpdateUser:
    async def test_valid_full_put_updates_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(
            db_session, full_name="Old Name", phone="555-0000", organization_id=organization.id
        )
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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, is_active=True, organization_id=organization.id)

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
        headers, _organization = await _authorized_headers(client, db_session)

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
        headers, organization = await _authorized_headers(client, db_session)
        first = await _make_user(db_session, organization_id=organization.id)
        second = await _make_user(db_session, organization_id=organization.id)

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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, is_active=True, organization_id=organization.id)

        response = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    async def test_database_row_and_relationships_are_preserved(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

        first = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)
        second = await client.post(f"/api/v1/users/{user.id}/deactivate", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["data"]["is_active"] is False

    async def test_unknown_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)

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
        headers, organization = await _unauthorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_remove_requires_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _unauthorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_users_manage_alone_allows_assign(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(client, db_session, "users:manage")
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 201

    async def test_roles_manage_alone_allows_assign(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(client, db_session, "roles:manage")
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(role.id)}, headers=headers
        )

        assert response.status_code == 201

    async def test_users_manage_alone_allows_remove(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(client, db_session, "users:manage")
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204

    async def test_roles_manage_alone_allows_remove(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(client, db_session, "roles:manage")
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204

    async def test_both_permissions_together_still_allowed(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(
            client, db_session, "users:manage", "roles:manage"
        )
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)

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
        headers, _organization = await _authorized_headers(client, db_session)
        denied_headers, _other_organization = await _unauthorized_headers(client, db_session)

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
        organization = await _make_organization(db_session)
        caller = await _make_user(db_session, organization_id=organization.id)
        await _grant_permissions(db_session, caller, "users:manage")
        access_token = await _login(client, caller)
        headers = {"Authorization": f"Bearer {access_token}"}
        target = await _make_user(db_session, organization_id=organization.id)
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
        headers, _organization = await _authorized_headers(client, db_session)
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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

        response = await client.post(
            f"/api/v1/users/{user.id}/roles", json={"role_id": str(uuid4())}, headers=headers
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_duplicate_assignment_returns_409_and_creates_no_second_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204
        assert response.content == b""

    async def test_user_role_and_other_assignments_remain(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
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
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)  # never assigned to `user`

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_unknown_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)
        role = await _make_role(db_session)

        response = await client.delete(f"/api/v1/users/{uuid4()}/roles/{role.id}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_unknown_role_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{uuid4()}", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert isinstance(response.json()["error"]["message"], str)

    async def test_removal_creates_no_role_or_role_permission_row(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _authorized_headers(client, db_session)
        user = await _make_user(db_session, organization_id=organization.id)
        role = await _make_role(db_session)
        db_session.add(UserRole(user_id=user.id, role_id=role.id))
        await db_session.flush()
        roles_before_removal = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()
        role_permissions_before_removal = (
            await db_session.execute(select(func.count()).select_from(RolePermission))
        ).scalar_one()

        response = await client.delete(f"/api/v1/users/{user.id}/roles/{role.id}", headers=headers)

        assert response.status_code == 204
        roles_after_removal = (
            await db_session.execute(select(func.count()).select_from(Role))
        ).scalar_one()
        role_permissions_after_removal = (
            await db_session.execute(select(func.count()).select_from(RolePermission))
        ).scalar_one()
        assert roles_after_removal == roles_before_removal
        assert role_permissions_after_removal == role_permissions_before_removal


class TestPermissionDeniedAuditing:
    """T65: `RequirePermission` (`deps.py`) records exactly one
    `permission_denied` `AuditLogger` event when the *final* candidate
    permission is also denied -- captured the same way
    `test_auth_login.py::TestLoginAuditing` captures `AuthService`'s events:
    `caplog` attached directly to the `app.audit` logger (`app`'s own
    logger has `propagate=False`, so a root-level capture would miss these).
    `GET /api/v1/users` is used throughout as a representative `T62`/`T63`
    route -- the router-level dependency is shared by all seven, so this
    one route's behavior generalizes to the others without needing to
    repeat the same assertions per route.

    `caplog.clear()` immediately after entering the capture block discards
    the `login_success` event `_authorized_headers()`/`_headers_with_permissions()`/
    `_login()` themselves generate while setting up the caller's token --
    without it, that unrelated event would be counted alongside (or instead
    of) the one this test actually cares about.
    """

    async def test_denied_request_records_exactly_one_permission_denied_event(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        headers, _organization = await _unauthorized_headers(client, db_session)

        with caplog.at_level(logging.INFO, logger="app.audit"):
            caplog.clear()
            response = await client.get("/api/v1/users", headers=headers)

        assert response.status_code == 403
        audit_records = [record for record in caplog.records if record.name == "app.audit"]
        assert len(audit_records) == 1
        record = audit_records[0]
        assert record.action == "permission_denied"
        assert record.resource_type == "endpoint"
        assert record.metadata == {"required_permissions": ["users:manage", "roles:manage"]}

    async def test_denied_request_actor_is_the_authenticated_caller(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caller = await _make_user(db_session)
        access_token = await _login(client, caller)
        headers = {"Authorization": f"Bearer {access_token}"}

        with caplog.at_level(logging.INFO, logger="app.audit"):
            caplog.clear()
            response = await client.get("/api/v1/users", headers=headers)

        assert response.status_code == 403
        audit_records = [record for record in caplog.records if record.name == "app.audit"]
        assert len(audit_records) == 1
        assert audit_records[0].actor_id == str(caller.id)

    async def test_authorized_request_records_no_permission_denied_event(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        headers, _organization = await _authorized_headers(client, db_session)

        with caplog.at_level(logging.INFO, logger="app.audit"):
            caplog.clear()
            response = await client.get("/api/v1/users", headers=headers)

        assert response.status_code == 200
        assert [record for record in caplog.records if record.name == "app.audit"] == []

    async def test_either_permission_alone_records_no_permission_denied_event(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """T63's OR-permission semantics preserved: a caller holding only
        `roles:manage` (not `users:manage`) is still authorized on this
        route via the second candidate permission succeeding, so the denial
        on the first candidate must not itself generate an audit event."""
        headers, _organization = await _headers_with_permissions(client, db_session, "roles:manage")

        with caplog.at_level(logging.INFO, logger="app.audit"):
            caplog.clear()
            response = await client.get("/api/v1/users", headers=headers)

        assert response.status_code == 200
        assert [record for record in caplog.records if record.name == "app.audit"] == []

    async def test_unauthenticated_401_records_no_audit_event(
        self, client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """401 (no/invalid token) is explicitly excluded from T65's scope --
        `RequirePermission` raises before ever reaching the permission
        check, let alone the audit call inside its `except` branch."""
        with caplog.at_level(logging.INFO, logger="app.audit"):
            caplog.clear()
            response = await client.get("/api/v1/users")

        assert response.status_code == 401
        assert [record for record in caplog.records if record.name == "app.audit"] == []
