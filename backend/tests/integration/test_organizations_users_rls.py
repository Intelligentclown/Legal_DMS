"""T105/ADR-0021: RLS security tests for `organizations`/`users`.

Two categories, deliberately not conflated:

- **Catalog/security-attribute assertions** (via `db_session`, the admin/
  owning role -- reading `pg_roles`/`pg_class`/`pg_tables`/`pg_policies` is
  a superuser-visible operation regardless of RLS): `legal_dms_app` is not
  the table owner, is not `SUPERUSER`, does not have `BYPASSRLS`; both
  tables have `relrowsecurity`/`relforcerowsecurity` set; policies exist
  for exactly these two tables and no other. The point (per this task's own
  review) is that "a policy exists" alone is not the security property --
  someone changing role ownership later could leave a structural "policy
  exists" test passing while the actual backstop is neutralized. These
  assertions catch exactly that.
- **Behavioral tests through the real restricted role**
  (`app_database_url`/`legal_dms_app`, GUCs set via `set_config`, mirroring
  `SqlAlchemyUserRepository`'s own calls): cross-Organization `SELECT`
  returns empty; the self-row carve-out works; the `users_insert` policy
  permits exactly `organization_id IS NULL` and rejects every other value,
  including the caller's own otherwise-legitimate Organization.

Seeded rows must be genuinely **committed** (not just `flush()`ed) for a
*different* connection (the `legal_dms_app` one) to see them at all -- this
file cannot reuse the usual rollback-safety `db_session` fixture for
seeding; see `_seed()`/teardown below, mirroring `test_bootstrap_admin.py`'s
own "real commit, own cleanup" pattern.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import get_app_engine
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.organization import Organization

# ---------------------------------------------------------------------------
# Catalog / security-attribute assertions
# ---------------------------------------------------------------------------


class TestRoleIsNotTheTableOwner:
    async def test_legal_dms_app_does_not_own_organizations_or_users(
        self, db_session: AsyncSession
    ) -> None:
        result = await db_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE tablename IN ('organizations', 'users') AND tableowner = 'legal_dms_app'"
            )
        )
        assert result.scalars().all() == []


class TestRoleHasNoRlsBypassAttributes:
    async def test_legal_dms_app_is_not_superuser_and_does_not_bypass_rls(
        self, db_session: AsyncSession
    ) -> None:
        result = await db_session.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'legal_dms_app'")
        )
        rolsuper, rolbypassrls = result.one()
        assert rolsuper is False
        assert rolbypassrls is False


class TestForceRlsIsEnabledOnExactlyTheseTwoTables:
    async def test_organizations_and_users_have_row_security_and_force_enabled(
        self, db_session: AsyncSession
    ) -> None:
        result = await db_session.execute(
            text(
                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relname IN ('organizations', 'users') AND relkind = 'r'"
            )
        )
        rows = {row.relname: row for row in result.all()}
        assert set(rows) == {"organizations", "users"}
        for row in rows.values():
            assert row.relrowsecurity is True
            assert row.relforcerowsecurity is True

    async def test_no_other_table_has_row_security_enabled(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text(
                "SELECT relname FROM pg_class "
                "WHERE relkind = 'r' AND relrowsecurity = true "
                "AND relname NOT IN ('organizations', 'users')"
            )
        )
        assert result.scalars().all() == []


class TestPoliciesExistForExactlyOrganizationsAndUsers:
    async def test_pg_policies_covers_exactly_two_tables(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(text("SELECT DISTINCT tablename FROM pg_policies"))
        assert set(result.scalars().all()) == {"organizations", "users"}

    async def test_users_has_select_insert_and_update_policies(
        self, db_session: AsyncSession
    ) -> None:
        result = await db_session.execute(
            text("SELECT policyname, cmd FROM pg_policies WHERE tablename = 'users'")
        )
        commands = {row.cmd for row in result.all()}
        assert commands == {"SELECT", "INSERT", "UPDATE"}


# ---------------------------------------------------------------------------
# Behavioral tests through the real restricted role
# ---------------------------------------------------------------------------


@pytest.fixture
async def app_engine() -> AsyncGenerator[AsyncEngine, None]:
    get_app_engine.cache_clear()
    engine = get_app_engine()
    try:
        async with engine.connect():
            pass
    except Exception:
        await engine.dispose()
        get_app_engine.cache_clear()
        pytest.skip(
            "legal_dms_app is not reachable/provisioned — run `uv run provision-app-role` "
            "then `uv run alembic upgrade head`."
        )
        return
    yield engine
    await engine.dispose()
    get_app_engine.cache_clear()


@pytest.fixture
async def two_organizations_with_users() -> (
    AsyncGenerator[tuple[Organization, User, Organization, User], None]
):
    """Two committed Organizations, one User each -- via a fresh admin-role
    engine (not the cached `get_engine()` singleton, which can't outlive the
    event loop it was created on -- pytest-asyncio gives each test its own
    loop, same reasoning as `conftest.py`'s own `db_session` fixture), since
    a *different* connection (the app-role one) must be able to see this
    data at all, which an uncommitted `db_session` write can't provide.
    Cleaned up afterward regardless of test outcome.
    """
    admin_engine = create_async_engine(get_settings().database_url)
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org_a = Organization(name=f"Org-A-{uuid4()}")
        org_b = Organization(name=f"Org-B-{uuid4()}")
        session.add_all([org_a, org_b])
        await session.flush()

        user_a = User(
            email=f"{uuid4()}@example.com",
            full_name="User A",
            password_hash="irrelevant",
            organization_id=org_a.id,
        )
        user_b = User(
            email=f"{uuid4()}@example.com",
            full_name="User B",
            password_hash="irrelevant",
            organization_id=org_b.id,
        )
        session.add_all([user_a, user_b])
        await session.commit()

    try:
        yield org_a, user_a, org_b, user_b
    finally:
        async with factory() as session:
            await session.execute(
                text(
                    "DELETE FROM users WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid))"
                ).bindparams(a=str(user_a.id), b=str(user_b.id))
            )
            await session.execute(
                text(
                    "DELETE FROM organizations WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid))"
                ).bindparams(a=str(org_a.id), b=str(org_b.id))
            )
            await session.commit()
        await admin_engine.dispose()


async def _set_context(conn, *, user_id: str | None, organization_id: str | None) -> None:
    await conn.execute(
        text("SELECT set_config('app.current_user_id', :val, true)").bindparams(val=user_id)
    )
    await conn.execute(
        text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
            val=organization_id
        )
    )


class TestCrossOrganizationSelectReturnsEmpty:
    async def test_org_a_caller_cannot_see_org_b_users(
        self,
        app_engine: AsyncEngine,
        two_organizations_with_users: tuple[Organization, User, Organization, User],
    ) -> None:
        org_a, user_a, _org_b, user_b = two_organizations_with_users
        async with app_engine.connect() as conn, conn.begin():
            await _set_context(conn, user_id=str(user_a.id), organization_id=str(org_a.id))
            result = await conn.execute(
                text("SELECT id FROM users WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(user_b.id)
                )
            )
            assert result.scalars().all() == []

    async def test_org_a_caller_cannot_see_org_b_organization_row(
        self,
        app_engine: AsyncEngine,
        two_organizations_with_users: tuple[Organization, User, Organization, User],
    ) -> None:
        org_a, user_a, org_b, _user_b = two_organizations_with_users
        async with app_engine.connect() as conn, conn.begin():
            await _set_context(conn, user_id=str(user_a.id), organization_id=str(org_a.id))
            result = await conn.execute(
                text("SELECT id FROM organizations WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(org_b.id)
                )
            )
            assert result.scalars().all() == []


class TestSelfRowCarveOut:
    async def test_own_row_visible_with_no_organization_guc_set(
        self,
        app_engine: AsyncEngine,
        two_organizations_with_users: tuple[Organization, User, Organization, User],
    ) -> None:
        _org_a, user_a, _org_b, _user_b = two_organizations_with_users
        async with app_engine.connect() as conn, conn.begin():
            await _set_context(conn, user_id=str(user_a.id), organization_id=None)
            result = await conn.execute(
                text("SELECT id FROM users WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(user_a.id)
                )
            )
            assert result.scalar_one() == user_a.id


class TestUsersInsertPolicy:
    async def test_null_organization_id_insert_succeeds(self, app_engine: AsyncEngine) -> None:
        new_id = str(uuid4())
        email = f"{uuid4()}@example.com"
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(
                    text(
                        "INSERT INTO users (id, email, full_name, is_active, organization_id) "
                        "VALUES (CAST(:id AS uuid), :email, 'NULL Org User', true, NULL)"
                    ).bindparams(id=new_id, email=email)
                )
            finally:
                await trans.rollback()  # never actually persisted -- policy-only proof

    async def test_non_null_organization_id_insert_is_rejected_even_for_the_callers_own_org(
        self,
        app_engine: AsyncEngine,
        two_organizations_with_users: tuple[Organization, User, Organization, User],
    ) -> None:
        """The structural invariant: the application-facing INSERT path
        (this exact policy) cannot be used to assign *any* Organization --
        not an arbitrary other one, and not even the caller's own,
        otherwise-legitimate-looking Organization. Only NULL is ever
        permitted."""
        org_a, user_a, _org_b, _user_b = two_organizations_with_users
        new_id = str(uuid4())
        email = f"{uuid4()}@example.com"
        async with app_engine.connect() as conn, conn.begin():
            await _set_context(conn, user_id=str(user_a.id), organization_id=str(org_a.id))
            with pytest.raises(Exception, match=r"row-level security|new row violates"):
                await conn.execute(
                    text(
                        "INSERT INTO users (id, email, full_name, is_active, organization_id) "
                        "VALUES (CAST(:id AS uuid), :email, 'Should Be Rejected', true, "
                        "CAST(:org_id AS uuid))"
                    ).bindparams(id=new_id, email=email, org_id=str(org_a.id))
                )

    async def test_arbitrary_other_organization_id_insert_is_also_rejected(
        self,
        app_engine: AsyncEngine,
        two_organizations_with_users: tuple[Organization, User, Organization, User],
    ) -> None:
        org_a, user_a, org_b, _user_b = two_organizations_with_users
        new_id = str(uuid4())
        email = f"{uuid4()}@example.com"
        async with app_engine.connect() as conn, conn.begin():
            await _set_context(conn, user_id=str(user_a.id), organization_id=str(org_a.id))
            with pytest.raises(Exception, match=r"row-level security|new row violates"):
                await conn.execute(
                    text(
                        "INSERT INTO users (id, email, full_name, is_active, organization_id) "
                        "VALUES (CAST(:id AS uuid), :email, 'Cross-org insert attempt', true, "
                        "CAST(:org_id AS uuid))"
                    ).bindparams(id=new_id, email=email, org_id=str(org_b.id))
                )


class TestUsersUpdatePolicy:
    async def test_cannot_update_a_row_outside_the_callers_organization(
        self,
        app_engine: AsyncEngine,
        two_organizations_with_users: tuple[Organization, User, Organization, User],
    ) -> None:
        org_a, user_a, _org_b, user_b = two_organizations_with_users
        async with app_engine.connect() as conn, conn.begin():
            await _set_context(conn, user_id=str(user_a.id), organization_id=str(org_a.id))
            result = await conn.execute(
                text(
                    "UPDATE users SET full_name = 'Hijacked' WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(user_b.id))
            )
            assert result.rowcount == 0


class TestOrganizationsWritePrivilege:
    async def test_legal_dms_app_cannot_insert_into_organizations_at_all(
        self, app_engine: AsyncEngine
    ) -> None:
        """No route/authorized code path writes to `organizations` through
        this role (bootstrap-admin/reconcile-organizations both use the
        admin role) -- the privilege itself is withheld, denied before RLS
        is even consulted."""
        async with app_engine.connect() as conn, conn.begin():
            with pytest.raises(Exception, match="permission denied"):
                await conn.execute(
                    text(
                        "INSERT INTO organizations (id, name) VALUES (CAST(:id AS uuid), 'Nope')"
                    ).bindparams(id=str(uuid4()))
                )
