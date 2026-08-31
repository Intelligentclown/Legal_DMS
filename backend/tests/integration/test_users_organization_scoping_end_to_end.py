"""T105: end-to-end proof of Decision 3 (authentication and every later
request-scoped query share one `AsyncSession`/transaction) -- through the
**real** request dependency path, not isolated `set_config`+`SELECT` calls
and not the usual `get_db`-override `client` fixture every other route test
in this suite uses (`test_users.py` included). This file deliberately does
**not** override `get_db`: it uses `conftest.py`'s plain `TestClient(app)`
fixture so `GET /users`/`GET /users/{id}` genuinely flow through
`app_database_url`/`legal_dms_app`/RLS, exactly as they would in production.

Skips gracefully (mirroring the existing `OperationalError` pattern used
throughout this suite) if `legal_dms_app`/RLS aren't provisioned yet.

Seeded rows are committed via a fresh admin-role engine (mirroring
`database_url`, not the cached `get_engine()` singleton -- see
`test_organizations_users_rls.py`'s identical per-test-event-loop
reasoning), then cleaned up after -- this test cannot use the usual
rollback-only `db_session` fixture for setup, since a different role/
connection (`legal_dms_app`, via the real app) must be able to see this
data at all.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import get_app_engine
from app.infrastructure.persistence.models.identity import (
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.security.password_hasher import hash_password
from app.main import app

_PASSWORD = "correct horse battery staple"


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """The plain, unmodified TestClient -- no `get_db` override. Deliberately
    different from every other route test file in this suite (see module
    docstring)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
async def _require_app_role_reachable() -> None:
    """Checks reachability via a throwaway engine, deliberately *not*
    `get_app_engine()` itself: this fixture runs on pytest-asyncio's own
    event loop, but `TestClient` drives the real app (and therefore the
    real `get_db()`/`get_app_engine()`) on a *different* thread/event loop
    of its own (the same reason `test_auth_me.py`'s docstring gives for why
    override-based tests use `httpx.AsyncClient` instead). If this fixture
    primed `get_app_engine()`'s cache on the wrong loop first, the actual
    request later would fail with "attached to a different loop" -- not a
    graceful skip. `get_app_engine.cache_clear()` before and after keeps
    this fixture's own check from leaving anything cached at all.
    """
    get_app_engine.cache_clear()
    settings = get_settings()
    probe_engine = create_async_engine(settings.app_database_url)
    try:
        async with probe_engine.connect():
            pass
    except Exception:
        pytest.skip(
            "legal_dms_app is not reachable/provisioned — run `uv run provision-app-role` "
            "then `uv run alembic upgrade head`."
        )
    finally:
        await probe_engine.dispose()
        get_app_engine.cache_clear()


async def _seed_organization_with_authorized_user() -> tuple[Organization, User, Role, str]:
    """Creates, via a fresh admin-role engine (not the cached `get_engine()`
    singleton -- see `test_organizations_users_rls.py`'s identical reasoning),
    one committed Organization + one User granted `users:manage` (via a new,
    uniquely-named Role) -- returns (organization, user, role,
    plaintext_password). The Role is returned (not just User/Organization)
    so `_cleanup()` can delete it too -- a real, committed Role/RolePermission
    row left behind would otherwise silently inflate `test_seed_data.py`'s/
    `test_t66_role_permissions.py`'s exact-count assertions for every other
    test in the suite that happens to run after this one."""
    engine = create_async_engine(get_settings().database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        organization = Organization(name=f"Org-{uuid4()}")
        session.add(organization)
        await session.flush()

        user = User(
            email=f"{uuid4()}@example.com",
            full_name="Scoped Admin",
            password_hash=hash_password(_PASSWORD),
            is_active=True,
            organization_id=organization.id,
        )
        session.add(user)
        await session.flush()

        stmt_result = await session.execute(
            sa.select(Permission).where(Permission.code == "users:manage")
        )
        permission = stmt_result.scalar_one()

        role = Role(name=f"Role-{uuid4()}")
        session.add(role)
        await session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()
    await engine.dispose()

    return organization, user, role, _PASSWORD


async def _cleanup(
    *, organization_ids: list[str], user_ids: list[str], role_ids: list[str]
) -> None:
    engine = create_async_engine(get_settings().database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(sa.delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids)))
        await session.execute(sa.delete(UserRole).where(UserRole.user_id.in_(user_ids)))
        await session.execute(sa.delete(RolePermission).where(RolePermission.role_id.in_(role_ids)))
        await session.execute(sa.delete(Role).where(Role.id.in_(role_ids)))
        await session.execute(sa.delete(User).where(User.id.in_(user_ids)))
        await session.execute(sa.delete(Organization).where(Organization.id.in_(organization_ids)))
        await session.commit()
    await engine.dispose()


class TestCrossOrganizationScopingThroughTheRealRequestPath:
    async def test_a_caller_only_ever_sees_their_own_organizations_users(
        self, client: TestClient
    ) -> None:
        org_a, user_a, role_a, password_a = await _seed_organization_with_authorized_user()
        org_b, user_b, role_b, _password_b = await _seed_organization_with_authorized_user()
        try:
            login_response = client.post(
                "/api/v1/auth/login", json={"email": user_a.email, "password": password_a}
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Same-Organization: the caller sees their own row.
            own_response = client.get(f"/api/v1/users/{user_a.id}", headers=headers)
            assert own_response.status_code == 200
            assert own_response.json()["data"]["id"] == str(user_a.id)

            # Cross-Organization: org A's caller cannot see org B's user --
            # this is only possible if the authentication lookup above and
            # this GET's own query actually share the same GUC-bearing
            # transaction (Decision 3) -- proven through the real path, not
            # a hand-assembled unit test.
            cross_response = client.get(f"/api/v1/users/{user_b.id}", headers=headers)
            assert cross_response.status_code == 404

            list_response = client.get("/api/v1/users", headers=headers)
            assert list_response.status_code == 200
            listed_ids = {item["id"] for item in list_response.json()["data"]}
            assert str(user_a.id) in listed_ids
            assert str(user_b.id) not in listed_ids
        finally:
            await _cleanup(
                organization_ids=[str(org_a.id), str(org_b.id)],
                user_ids=[str(user_a.id), str(user_b.id)],
                role_ids=[str(role_a.id), str(role_b.id)],
            )
