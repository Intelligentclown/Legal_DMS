"""T123: Party Organization-scoped RLS backstop — PostgreSQL tests.

Everything here runs against a freshly provisioned, disposable PostgreSQL
database migrated to the repository head (never the shared development
database), per the T123 queue-row precondition: the forward migration and its
positive validation are only for genuinely empty/fresh targets.

Covered:

- fresh-upgrade evidence (the disposable database sits at the repository
  head);
- catalog/security-attribute assertions (via the owning admin superuser,
  which as the table owner bypasses RLS): `parties` has
  `relrowsecurity` + `relforcerowsecurity`; the RLS/policy surface covers
  the four tenant tables {parties, addresses, organizations, users};
  `parties` has exactly four default-deny policies whose quals/with-checks
  are all GUC-driven; `legal_dms_app` owns nothing relevant and is not
  SUPERUSER/BYPASSRLS; the Party schema contract T116 established
  (`organization_id` NOT NULL, support key, composite Address FK) is
  unchanged by T123;
- the owning/admin path the T118 executor uses is unaffected: a Party write
  straight through the owning superuser with no GUC succeeds and is visible
  to the owner while the runtime `legal_dms_app` role still sees it only
  through an org context — RLS is backstopped, not weakened;
- behavioral assertions through the real restricted role (`legal_dms_app`):
  no-context is default-deny for every command; org-scoped visibility;
  cross-org SELECT/INSERT/UPDATE/DELETE denied; same-org UPDATE succeeds with
  the org preserved; an org-reassignment UPDATE is rejected by the policy's
  WITH CHECK;
- GUC isolation for parties across commit and pooled-connection reuse;
- Party → Address integrity, both as the composite FK through the owning
  path (cross-org composite references rejected, same-org accepted) and
  layered with RLS (the app role's org-scoped party insert still cannot
  point at another Organization's Address);
- downgrade restoration: `alembic downgrade 9c4a7e2d1b5f` disables Party
  RLS, drops all four Party policies, preserves rows and org values, and
  restores the T122-era RLS surface.

The downgrade case is the last test in this module: it intentionally mutates
the disposable database back to the T122 head.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.config import get_settings
from app.infrastructure.persistence.models.client import Address
from app.infrastructure.persistence.models.geography import Country
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import Party
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

HEAD = "62cadaff2571"
PARENT_HEAD = "9c4a7e2d1b5f"

BACKEND_DIR = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Provisioning + engine fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    """One disposable PostgreSQL database migrated to the repository head
    (which is now the T123 head), created on first use and destroyed +
    disposal-confirmed in teardown."""
    url, db_name = provision_disposable_database_with("legal_dms_t123_rls")
    try:
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


def _disposable_app_url(disposable_url: str) -> str:
    """App-role URL for the disposable database: same host/db as the admin URL,
    credentials from `app_database_url` (the `legal_dms_app` runtime role)."""
    admin = make_url(disposable_url)
    app = make_url(get_settings().app_database_url)
    return admin.set(username=app.username, password=app.password).render_as_string(
        hide_password=False
    )


@pytest.fixture
async def admin_engine(disposable_db: tuple[str, str]) -> AsyncGenerator[AsyncEngine, None]:
    url, _db_name = disposable_db
    engine = create_async_engine(url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def app_engine(disposable_db: tuple[str, str]) -> AsyncGenerator[AsyncEngine, None]:
    url, _db_name = disposable_db
    engine = create_async_engine(_disposable_app_url(url))
    try:
        async with engine.connect():
            pass
    except Exception as exc:
        await engine.dispose()
        pytest.skip(
            f"legal_dms_app is not reachable on the disposable database ({exc}) — "
            "run `uv run provision-app-role` and re-run with APP_DATABASE_URL pointing "
            "at the same host as DATABASE_URL."
        )
        return
    yield engine
    await engine.dispose()


@pytest.fixture
async def seeded_context(admin_engine: AsyncEngine) -> SimpleNamespace:
    """Two committed Organizations, a country, org-scoped addresses, and two
    org-A Parties + one org-B Party, committed through the owning superuser
    (RLS-bypassing) so the app-role connection sees them."""
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org_a = Organization(name=f"T123-Org-A-{uuid4()}")
        org_b = Organization(name=f"T123-Org-B-{uuid4()}")
        session.add_all([org_a, org_b])
        await session.flush()

        used_codes = set((await session.execute(select(Country.iso_code))).scalars())
        iso_code = f"{str(uuid4())[:2].upper()}"
        while iso_code in used_codes:
            iso_code = f"{str(uuid4())[:2].upper()}"
        country = Country(name=f"Country-{uuid4()}", iso_code=iso_code)
        session.add(country)
        await session.flush()

        addr_a1 = Address(organization_id=org_a.id, line1="Addr A-1", country_id=country.id)
        addr_a3 = Address(organization_id=org_a.id, line1="Addr A-3", country_id=country.id)
        addr_b2 = Address(organization_id=org_b.id, line1="Addr B-2", country_id=country.id)
        session.add_all([addr_a1, addr_a3, addr_b2])
        await session.flush()

        party_a1 = Party(
            organization_id=org_a.id,
            party_type="individual",
            display_name="Party A-1",
            primary_phone="7000000001",
            address_id=addr_a1.id,
        )
        party_a2 = Party(
            organization_id=org_a.id,
            party_type="individual",
            display_name="Party A-2",
            primary_phone="7000000002",
            address_id=addr_a3.id,
        )
        party_b1 = Party(
            organization_id=org_b.id,
            party_type="organization",
            display_name="Party B-1",
            primary_phone="7000000003",
            address_id=addr_b2.id,
        )
        session.add_all([party_a1, party_a2, party_b1])
        await session.commit()

    return SimpleNamespace(
        org_a=org_a.id,
        org_b=org_b.id,
        country=country.id,
        addr_a1=addr_a1.id,
        addr_a3=addr_a3.id,
        addr_b2=addr_b2.id,
        party_a1=party_a1.id,
        party_a2=party_a2.id,
        party_b1=party_b1.id,
    )


async def _set_org_context(conn, organization_id: str | None) -> None:
    await conn.execute(
        text("SELECT set_config('app.current_organization_id', :val, true)").bindparams(
            val=organization_id
        )
    )


# ---------------------------------------------------------------------------
# Fresh-upgrade + catalog / security-attribute assertions
# ---------------------------------------------------------------------------


class TestFreshUpgradeAtHead:
    async def test_disposable_database_sits_at_the_repository_head(
        self, disposable_db: tuple[str, str]
    ) -> None:
        url, _db_name = disposable_db
        assert alembic_current_branch(url) == HEAD


class TestPartiesRowSecuritySurface:
    async def test_parties_has_row_security_and_force_enabled(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            row = await conn.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE oid = 'parties'::regclass"
                )
            )
            relrowsecurity, relforcerowsecurity = row.one()
        assert relrowsecurity is True
        assert relforcerowsecurity is True

    async def test_rls_surface_covers_exactly_the_four_tenant_tables(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT relname FROM pg_class WHERE relkind = 'r' AND relrowsecurity = true")
            )
            tables = set(result.scalars())
        assert tables == {"parties", "addresses", "organizations", "users"}

    async def test_pg_policies_cover_exactly_the_four_tenant_tables(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(text("SELECT DISTINCT tablename FROM pg_policies"))
            tables = set(result.scalars())
        assert tables == {"parties", "addresses", "organizations", "users"}

    async def test_parties_has_exactly_four_default_deny_guc_policies(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT policyname, cmd, qual, with_check FROM pg_policies "
                    "WHERE tablename = 'parties' ORDER BY cmd"
                )
            )
            policies = result.all()
        assert [policy.cmd for policy in policies] == ["DELETE", "INSERT", "SELECT", "UPDATE"]
        assert [policy.policyname for policy in policies] == [
            "parties_delete",
            "parties_insert",
            "parties_select",
            "parties_update",
        ]
        by_cmd = {policy.cmd: policy for policy in policies}
        # USING-based policies carry a `qual`; INSERT-only carries `with_check`;
        # UPDATE carries both -- and every side is driven by the org GUC.
        assert by_cmd["SELECT"].qual is not None
        assert by_cmd["DELETE"].qual is not None
        assert by_cmd["INSERT"].qual is None and by_cmd["INSERT"].with_check is not None
        assert by_cmd["UPDATE"].qual is not None and by_cmd["UPDATE"].with_check is not None
        for policy in policies:
            combined = f"{policy.qual or ''} {policy.with_check or ''}"
            assert "app.current_organization_id" in combined
            assert "current_user" not in combined

    async def test_legal_dms_app_does_not_own_parties(self, admin_engine: AsyncEngine) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tableowner FROM pg_tables WHERE tablename = 'parties'")
            )
            owner = result.scalar_one()
        assert owner != "legal_dms_app"

    async def test_legal_dms_app_is_not_superuser_and_does_not_bypass_rls(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'legal_dms_app'")
            )
            rolsuper, rolbypassrls = result.one()
        assert rolsuper is False
        assert rolbypassrls is False

    async def test_party_schema_contract_is_unchanged(self, admin_engine: AsyncEngine) -> None:
        async with admin_engine.connect() as conn:
            not_null = await conn.execute(
                text(
                    "SELECT NOT attnotnull FROM pg_attribute "
                    "WHERE attrelid = 'parties'::regclass AND attname = 'organization_id'"
                )
            )
            assert not_null.scalar_one() is False
            constraints = set(
                (
                    await conn.execute(
                        text(
                            "SELECT conname FROM pg_constraint "
                            "WHERE conrelid = 'parties'::regclass"
                        )
                    )
                ).scalars()
            )
        assert "uq_parties_organization_id_id" in constraints
        assert "fk_parties_organization_id_addresses" in constraints


# ---------------------------------------------------------------------------
# Owning/admin path (the T118 executor's path) stays working
# ---------------------------------------------------------------------------


class TestOwningExecutorPathUnaffected:
    """The T118 migration executor writes through `get_session_factory()` →
    `settings.database_url`, the owning/admin role, which bypasses RLS as
    table owner/superuser. A Party write straight through that path with no
    GUC must succeed and remain visible to the owner — proven here while the
    runtime `legal_dms_app` role still sees it only through an org context
    (RLS backstopped, not weakened)."""

    async def test_owning_path_party_write_with_no_guc_succeeds_and_app_stays_scoped(
        self, admin_engine: AsyncEngine, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        new_id = uuid4()
        async with admin_engine.connect() as conn, conn.begin():
            await conn.execute(
                text(
                    "INSERT INTO parties (id, organization_id, party_type, display_name, "
                    "primary_phone, address_id) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                    "'individual', 'Owner Path Party', '7000000999', CAST(:addr AS uuid))"
                ).bindparams(
                    id=str(new_id),
                    org=str(seeded_context.org_a),
                    addr=str(seeded_context.addr_a1),
                )
            )
            visible_to_owner = (
                await conn.execute(
                    text("SELECT count(*) FROM parties WHERE id = CAST(:id AS uuid)").bindparams(
                        id=str(new_id)
                    )
                )
            ).scalar_one()

        # Same row is invisible to the runtime role without context, and visible
        # only through the org context -- proof RLS still backstops the owner's
        # writes even though FORCE RLS does not block the owning role's own path.
        async with app_engine.connect() as conn:
            no_context_count = (
                await conn.execute(
                    text("SELECT count(*) FROM parties WHERE id = CAST(:id AS uuid)").bindparams(
                        id=str(new_id)
                    )
                )
            ).scalar_one()
        assert no_context_count == 0
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            scoped_count = (
                await conn.execute(
                    text("SELECT count(*) FROM parties WHERE id = CAST(:id AS uuid)").bindparams(
                        id=str(new_id)
                    )
                )
            ).scalar_one()
        assert scoped_count == 1
        assert visible_to_owner == 1

        # Cleanup through the owning path leaves the DB pristine.
        async with admin_engine.connect() as conn, conn.begin():
            await conn.execute(
                text("DELETE FROM parties WHERE id = CAST(:id AS uuid)").bindparams(id=str(new_id))
            )


# ---------------------------------------------------------------------------
# Behavioral assertions through the real restricted role
# ---------------------------------------------------------------------------


class TestDefaultDenyWithoutContext:
    async def test_select_returns_no_rows_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        _ = seeded_context
        async with app_engine.connect() as conn:
            result = await conn.execute(text("SELECT count(*) FROM parties"))
            assert result.scalar_one() == 0

    async def test_insert_is_rejected_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            with pytest.raises(Exception, match=r"row-level security"):
                await conn.execute(
                    text(
                        "INSERT INTO parties (id, organization_id, party_type, display_name, "
                        "primary_phone) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'individual', 'No Context Insert', '7000000004')"
                    ).bindparams(id=str(uuid4()), org=str(seeded_context.org_a))
                )

    async def test_update_is_a_no_op_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            result = await conn.execute(
                text(
                    "UPDATE parties SET display_name = 'No Context Update' "
                    "WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.party_a1))
            )
            assert result.rowcount == 0

    async def test_delete_is_a_no_op_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            result = await conn.execute(
                text("DELETE FROM parties WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.party_a1)
                )
            )
            assert result.rowcount == 0


class TestOrganizationScopedVisibility:
    async def test_org_a_caller_sees_only_its_own_parties(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            rows = (await conn.execute(text("SELECT id FROM parties"))).scalars()
        assert set(rows) == {seeded_context.party_a1, seeded_context.party_a2}

    async def test_org_b_caller_sees_only_its_own_party(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_b))
            rows = (await conn.execute(text("SELECT id FROM parties"))).scalars()
        assert set(rows) == {seeded_context.party_b1}

    async def test_cross_organization_select_returns_empty(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            result = await conn.execute(
                text("SELECT id FROM parties WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.party_b1)
                )
            )
            assert result.scalars().all() == []

    async def test_cross_organization_insert_is_rejected(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            with pytest.raises(Exception, match=r"row-level security"):
                await conn.execute(
                    text(
                        "INSERT INTO parties (id, organization_id, party_type, display_name, "
                        "primary_phone) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'individual', 'Cross Org Insert', '7000000005')"
                    ).bindparams(id=str(uuid4()), org=str(seeded_context.org_b))
                )

    async def test_cross_organization_update_is_a_no_op(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            result = await conn.execute(
                text(
                    "UPDATE parties SET display_name = 'Hijacked' WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.party_b1))
            )
            assert result.rowcount == 0

    async def test_cross_organization_delete_is_a_no_op(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            result = await conn.execute(
                text("DELETE FROM parties WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.party_b1)
                )
            )
            assert result.rowcount == 0

    async def test_update_of_own_row_preserving_organization_succeeds(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            await _set_org_context(conn, str(seeded_context.org_a))
            result = await conn.execute(
                text(
                    "UPDATE parties SET display_name = 'Own Row Update' "
                    "WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.party_a1))
            )
            assert result.rowcount == 1
            seen = (
                await conn.execute(
                    text(
                        "SELECT display_name FROM parties WHERE id = CAST(:id AS uuid)"
                    ).bindparams(id=str(seeded_context.party_a1))
                )
            ).scalar_one()
            assert seen == "Own Row Update"
            await trans.rollback()  # keep the seeded value pristine for later tests

    async def test_own_row_insert_succeeds(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            await _set_org_context(conn, str(seeded_context.org_a))
            await conn.execute(
                text(
                    "INSERT INTO parties (id, organization_id, party_type, display_name, "
                    "primary_phone, address_id) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                    "'individual', 'Own Row Insert', '7000000006', CAST(:addr AS uuid))"
                ).bindparams(
                    id=str(uuid4()),
                    org=str(seeded_context.org_a),
                    addr=str(seeded_context.addr_a1),
                )
            )
            await trans.rollback()

    async def test_organization_reassignment_update_is_rejected_by_with_check(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            with pytest.raises(Exception, match=r"row-level security"):
                await conn.execute(
                    text(
                        "UPDATE parties SET organization_id = CAST(:org AS uuid) "
                        "WHERE id = CAST(:id AS uuid)"
                    ).bindparams(id=str(seeded_context.party_a1), org=str(seeded_context.org_b))
                )


class TestTenantGucIsolationForParties:
    async def test_local_guc_does_not_leak_across_commit_or_pooled_reuse(
        self, disposable_db: tuple[str, str], seeded_context: SimpleNamespace
    ) -> None:
        url, _db_name = disposable_db
        engine = create_async_engine(_disposable_app_url(url), pool_size=1, max_overflow=0)
        try:
            async with engine.connect() as conn:
                # tx1: local-scoped GUC permits an org-A insert, then commits.
                tx = await conn.begin()
                await _set_org_context(conn, str(seeded_context.org_a))
                await conn.execute(
                    text(
                        "INSERT INTO parties (id, organization_id, party_type, display_name, "
                        "primary_phone) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'individual', 'Leaked GUC Party', '7000000007')"
                    ).bindparams(id=str(uuid4()), org=str(seeded_context.org_a))
                )
                await tx.commit()

                # tx2: same pooled connection, no GUC set -- default deny.
                tx = await conn.begin()
                result = await conn.execute(text("SELECT count(*) FROM parties"))
                assert result.scalar_one() == 0
                with pytest.raises(Exception, match=r"row-level security"):
                    await conn.execute(
                        text(
                            "INSERT INTO parties (id, organization_id, party_type, display_name, "
                            "primary_phone) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                            "'individual', 'Leaked GUC Again', '7000000008')"
                        ).bindparams(id=str(uuid4()), org=str(seeded_context.org_a))
                    )
                await tx.rollback()
        finally:
            await engine.dispose()


# ---------------------------------------------------------------------------
# Party → Address integrity (composite FK + its layering with RLS)
# ---------------------------------------------------------------------------


class TestPartyAddressIntegrity:
    """The existing (organization_id, address_id) -> (organization_id, id)
    composite FK on parties must keep working under the new RLS: same-Org
    references are accepted, cross-Org references are rejected, and the app
    role's org-scoped insert still cannot smuggle a cross-Org address into
    a party (the policy's WITH CHECK passes for an org-A party; the composite
    FK then rejects the org-B address)."""

    @staticmethod
    async def _assert_owning_path_composite_guard(
        admin_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        # Same-org reference: accepted.
        same_id = uuid4()
        async with admin_engine.connect() as conn, conn.begin():
            await conn.execute(
                text(
                    "INSERT INTO parties (id, organization_id, party_type, display_name, "
                    "primary_phone, address_id) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                    "'individual', 'FK Party', '7000000009', CAST(:addr AS uuid))"
                ).bindparams(
                    id=str(same_id),
                    org=str(seeded_context.org_a),
                    addr=str(seeded_context.addr_a1),
                )
            )
        # Cross-org reference: rejected by the composite FK.
        async with admin_engine.connect() as conn, conn.begin():
            with pytest.raises(
                IntegrityError,
                match=r'foreign key constraint "fk_parties_organization_id_addresses"',
            ):
                await conn.execute(
                    text(
                        "INSERT INTO parties (id, organization_id, party_type, display_name, "
                        "primary_phone, address_id) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'individual', 'FK Cross Party', '7000000010', CAST(:addr AS uuid))"
                    ).bindparams(
                        id=str(uuid4()),
                        org=str(seeded_context.org_a),
                        addr=str(seeded_context.addr_b2),
                    )
                )
        # Clean up the accepted same-org row.
        async with admin_engine.connect() as conn:
            await conn.execute(
                text("DELETE FROM parties WHERE id = CAST(:id AS uuid)").bindparams(id=str(same_id))
            )
            await conn.commit()

    async def test_owning_path_composite_fk_still_protects_party_address_reference(
        self, admin_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        await self._assert_owning_path_composite_guard(admin_engine, seeded_context)

    async def test_app_role_org_scoped_insert_cannot_point_at_cross_org_address(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            with pytest.raises(
                IntegrityError,
                match=r'foreign key constraint "fk_parties_organization_id_addresses"',
            ):
                await conn.execute(
                    text(
                        "INSERT INTO parties (id, organization_id, party_type, display_name, "
                        "primary_phone, address_id) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'individual', 'RLS FK Layer', '7000000011', CAST(:addr AS uuid))"
                    ).bindparams(
                        id=str(uuid4()),
                        org=str(seeded_context.org_a),
                        addr=str(seeded_context.addr_b2),
                    )
                )


# ---------------------------------------------------------------------------
# Downgrade restoration (must stay the last test in this module)
# ---------------------------------------------------------------------------


def test_downgrade_restores_t122_contract_and_preserves_data(
    disposable_db: tuple[str, str],
) -> None:
    url, _db_name = disposable_db
    party_rows_before = asyncio.run(_party_org_rows(url))

    _run_alembic_child(url, "downgrade", PARENT_HEAD)

    assert alembic_current_branch(url) == PARENT_HEAD
    assert asyncio.run(_parties_rls_force_flags(url)) == (False, False)
    assert asyncio.run(_parties_policy_names(url)) == []
    # Rows and their org values survive the downgrade untouched.
    assert asyncio.run(_party_org_rows(url)) == party_rows_before
    # T122-era RLS surface is restored exactly.
    assert asyncio.run(_rls_surface_tables(url)) == {"addresses", "organizations", "users"}
    # The T116 Party schema (org NOT NULL, support key) is retained.
    assert asyncio.run(_party_organization_id_not_null(url)) is True
    assert asyncio.run(_party_support_key_exists(url)) is True


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _run_alembic_child(disposable_url: str, *args: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = disposable_url
    env["PYTHONPATH"] = str(BACKEND_DIR / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} failed for {disposable_url}:\n{proc.stdout}\n{proc.stderr}"
        )


async def _party_org_rows(url: str) -> list[tuple[str, str]]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT CAST(id AS text), CAST(organization_id AS text) "
                    "FROM parties ORDER BY id"
                )
            )
            return [(str(row[0]), str(row[1])) for row in result.all()]
    finally:
        await engine.dispose()


async def _parties_rls_force_flags(url: str) -> tuple[bool, bool]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE oid = 'parties'::regclass"
                )
            )
            rls, force = result.one()
            return bool(rls), bool(force)
    finally:
        await engine.dispose()


async def _parties_policy_names(url: str) -> list[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT policyname FROM pg_policies WHERE tablename = 'parties'")
            )
            return sorted(result.scalars())
    finally:
        await engine.dispose()


async def _rls_surface_tables(url: str) -> set[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT relname FROM pg_class WHERE relkind = 'r' AND relrowsecurity = true")
            )
            return set(result.scalars())
    finally:
        await engine.dispose()


async def _party_organization_id_not_null(url: str) -> bool:
    """True when `parties.organization_id` is NOT NULL in the catalog."""
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT NOT attnotnull FROM pg_attribute "
                    "WHERE attrelid = 'parties'::regclass AND attname = 'organization_id'"
                )
            )
            return not bool(result.scalar_one())
    finally:
        await engine.dispose()


async def _party_support_key_exists(url: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT count(*) FROM pg_constraint "
                    "WHERE conrelid = 'parties'::regclass "
                    "AND conname = 'uq_parties_organization_id_id'"
                )
            )
            return int(result.scalar_one()) == 1
    finally:
        await engine.dispose()
