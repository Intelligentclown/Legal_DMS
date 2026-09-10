"""T122: Address tenant finalization + Organization-scoped RLS — PostgreSQL tests.

Everything here runs against a freshly provisioned, disposable PostgreSQL
database migrated to the repository head (never the shared development
database), per the T122 queue-row precondition: the forward migration and its
positive validation are only for genuinely empty/fresh targets.

Covered:

- fresh-upgrade evidence (the disposable database sits at the repository head);
- catalog/security-attribute assertions (via the owning admin superuser, which
  as the table owner bypasses RLS): `addresses` has
  `relrowsecurity` + `relforcerowsecurity`; the RLS/policy surface covers
  exactly the three tenant tables {addresses, organizations, users}; addresses
  has exactly four default-deny policies whose quals/with-checks are all
  GUC-driven; `legal_dms_app` owns nothing relevant and is not
  SUPERUSER/BYPASSRLS;
- finalization: `organization_id` is NOT NULL in the catalog and at runtime
  (NULL-org insert rejected; valid org accepted);
- behavioral assertions through the real restricted role (`legal_dms_app`):
  no-context is default-deny for every command; org-scoped visibility;
  cross-org SELECT/INSERT/UPDATE/DELETE denied; same-org UPDATE succeeds with
  the org preserved;
- GUC isolation for addresses across commit and pooled-connection reuse;
- same-Organization composite Address FKs still protect Client/Property/Party
  (cross-org composite references rejected, same-org accepted);
- downgrade restoration: `alembic downgrade f3b7c9d1e2a4` restores T120's
  contract (nullable `organization_id`, RLS disabled, no Address policies)
  and preserves org-scoped rows and values unchanged.

The downgrade case is the last test in this module: it intentionally mutates
the disposable database back to the T120 legacy head.
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
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.organization import Organization
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

NEW_HEAD = "9c4a7e2d1b5f"
LEGACY_HEAD = "f3b7c9d1e2a4"

BACKEND_DIR = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Provisioning + engine fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    """One disposable PostgreSQL database migrated to the T122 head, created
    on first use and destroyed + disposal-confirmed in teardown.

    Pinned to the T122 migration (`NEW_HEAD`) rather than the moving
    repository `head`: T123 and later RLS eras add more tenant tables, and
    this module's catalog assertions ("exactly three tenant tables with
    RLS", "pg_policies covers exactly three tables") are era-correct only
    at this module's own migration head (same era-split discipline T122
    itself applied by pinning T119/T120-era suites to their legacy heads)."""
    url, db_name = provision_disposable_database_with("legal_dms_t122_rls", upgrade_target=NEW_HEAD)
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
    """Two committed Organizations with one User each, a country, and three
    addresses (two in org A, one in org B), committed through the owning
    superuser (RLS-bypassing) so the app-role connection sees them."""
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org_a = Organization(name=f"T122-Org-A-{uuid4()}")
        org_b = Organization(name=f"T122-Org-B-{uuid4()}")
        session.add_all([org_a, org_b])
        await session.flush()

        user_a = User(
            email=f"{uuid4()}@example.com",
            full_name="T122 User A",
            organization_id=org_a.id,
        )
        user_b = User(
            email=f"{uuid4()}@example.com",
            full_name="T122 User B",
            organization_id=org_b.id,
        )
        session.add_all([user_a, user_b])

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
        await session.commit()

    return SimpleNamespace(
        org_a=org_a.id,
        org_b=org_b.id,
        user_a=user_a.id,
        user_b=user_b.id,
        country=country.id,
        addr_a1=addr_a1.id,
        addr_a3=addr_a3.id,
        addr_b2=addr_b2.id,
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
        assert alembic_current_branch(url) == NEW_HEAD


class TestAddressesFinalizationIsNotNull:
    async def test_null_organization_id_insert_is_rejected(
        self, admin_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with admin_engine.connect() as conn, conn.begin():
            with pytest.raises(IntegrityError, match=r"not-null constraint|null value"):
                await conn.execute(
                    text(
                        "INSERT INTO addresses (id, organization_id, line1, country_id, "
                        "address_type) VALUES (CAST(:id AS uuid), NULL, 'Should Fail', "
                        "CAST(:country_id AS uuid), 'registered')"
                    ).bindparams(
                        id=str(uuid4()),
                        country_id=str(seeded_context.country),
                    )
                )

    async def test_valid_organization_id_insert_succeeds(
        self, admin_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        new_id = uuid4()
        async with admin_engine.connect() as conn:
            await conn.execute(
                text(
                    "INSERT INTO addresses (id, organization_id, line1, country_id, "
                    "address_type) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                    "'Valid Org Address', CAST(:country_id AS uuid), 'registered')"
                ).bindparams(
                    id=str(new_id),
                    org=str(seeded_context.org_a),
                    country_id=str(seeded_context.country),
                )
            )
            await conn.execute(
                text("DELETE FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(new_id)
                )
            )
            await conn.commit()


class TestAddressesRowSecuritySurface:
    async def test_addresses_has_row_security_and_force_enabled(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            row = await conn.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE oid = 'addresses'::regclass"
                )
            )
            relrowsecurity, relforcerowsecurity = row.one()
        assert relrowsecurity is True
        assert relforcerowsecurity is True

    async def test_rls_surface_covers_exactly_the_three_tenant_tables(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT relname FROM pg_class WHERE relkind = 'r' AND relrowsecurity = true")
            )
            tables = set(result.scalars())
        assert tables == {"addresses", "organizations", "users"}

    async def test_pg_policies_cover_exactly_the_three_tenant_tables(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(text("SELECT DISTINCT tablename FROM pg_policies"))
            tables = set(result.scalars())
        assert tables == {"addresses", "organizations", "users"}

    async def test_addresses_has_exactly_four_default_deny_guc_policies(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT policyname, cmd, qual, with_check FROM pg_policies "
                    "WHERE tablename = 'addresses' ORDER BY cmd"
                )
            )
            policies = result.all()
        assert [policy.cmd for policy in policies] == ["DELETE", "INSERT", "SELECT", "UPDATE"]
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

    async def test_legal_dms_app_does_not_own_addresses(self, admin_engine: AsyncEngine) -> None:
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tableowner FROM pg_tables WHERE tablename = 'addresses'")
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


# ---------------------------------------------------------------------------
# Behavioral assertions through the real restricted role
# ---------------------------------------------------------------------------


class TestDefaultDenyWithoutContext:
    async def test_select_returns_no_rows_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        _ = seeded_context
        async with app_engine.connect() as conn:
            result = await conn.execute(text("SELECT count(*) FROM addresses"))
            assert result.scalar_one() == 0

    async def test_insert_is_rejected_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            with pytest.raises(Exception, match=r"row-level security"):
                await conn.execute(
                    text(
                        "INSERT INTO addresses (id, organization_id, line1, country_id, "
                        "address_type) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'No Context Insert', CAST(:country_id AS uuid), 'registered')"
                    ).bindparams(
                        id=str(uuid4()),
                        org=str(seeded_context.org_a),
                        country_id=str(seeded_context.country),
                    )
                )

    async def test_update_is_a_no_op_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            result = await conn.execute(
                text(
                    "UPDATE addresses SET line1 = 'No Context Update' "
                    "WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.addr_a1))
            )
            assert result.rowcount == 0

    async def test_delete_is_a_no_op_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            result = await conn.execute(
                text("DELETE FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.addr_a1)
                )
            )
            assert result.rowcount == 0


class TestOrganizationScopedVisibility:
    async def test_org_a_caller_sees_only_its_own_addresses(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            rows = (await conn.execute(text("SELECT id FROM addresses"))).scalars()
        assert set(rows) == {seeded_context.addr_a1, seeded_context.addr_a3}

    async def test_org_b_caller_sees_only_its_own_address(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_b))
            rows = (await conn.execute(text("SELECT id FROM addresses"))).scalars()
        assert set(rows) == {seeded_context.addr_b2}

    async def test_cross_organization_select_returns_empty(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            result = await conn.execute(
                text("SELECT id FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.addr_b2)
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
                        "INSERT INTO addresses (id, organization_id, line1, country_id, "
                        "address_type) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'Cross Org Insert', CAST(:country_id AS uuid), 'registered')"
                    ).bindparams(
                        id=str(uuid4()),
                        org=str(seeded_context.org_b),
                        country_id=str(seeded_context.country),
                    )
                )

    async def test_cross_organization_update_is_a_no_op(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            result = await conn.execute(
                text(
                    "UPDATE addresses SET line1 = 'Hijacked' WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.addr_b2))
            )
            assert result.rowcount == 0

    async def test_cross_organization_delete_is_a_no_op(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            result = await conn.execute(
                text("DELETE FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.addr_b2)
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
                    "UPDATE addresses SET line1 = 'Own Row Update' WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.addr_a1))
            )
            assert result.rowcount == 1
            seen = (
                await conn.execute(
                    text("SELECT line1 FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                        id=str(seeded_context.addr_a1)
                    )
                )
            ).scalar_one()
            assert seen == "Own Row Update"
            await trans.rollback()  # keep the seeded value pristine for later tests


class TestTenantGucIsolationForAddresses:
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
                        "INSERT INTO addresses (id, organization_id, line1, country_id, "
                        "address_type) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                        "'GUC Isolation', CAST(:country_id AS uuid), 'registered')"
                    ).bindparams(
                        id=str(uuid4()),
                        org=str(seeded_context.org_a),
                        country_id=str(seeded_context.country),
                    )
                )
                await tx.commit()

                # tx2: same pooled connection, no GUC set -- default deny.
                tx = await conn.begin()
                result = await conn.execute(text("SELECT count(*) FROM addresses"))
                assert result.scalar_one() == 0
                with pytest.raises(Exception, match=r"row-level security"):
                    await conn.execute(
                        text(
                            "INSERT INTO addresses (id, organization_id, line1, country_id, "
                            "address_type) VALUES (CAST(:id AS uuid), CAST(:org AS uuid), "
                            "'Leaked GUC', CAST(:country_id AS uuid), 'registered')"
                        ).bindparams(
                            id=str(uuid4()),
                            org=str(seeded_context.org_a),
                            country_id=str(seeded_context.country),
                        )
                    )
                await tx.rollback()
        finally:
            await engine.dispose()


class TestSameOrganizationCompositeAddressProtections:
    """The existing (organization_id, address_id) -> (organization_id, id)
    composite FKs must keep working after finalization: same-Org references
    are accepted, cross-Org references are rejected. Driven through the owning
    superuser (RLS-bypassing) so these assertions isolate FK semantics."""

    @staticmethod
    async def _assert_composite_guard(
        admin_engine: AsyncEngine,
        seeded_context: SimpleNamespace,
        *,
        table: str,
        columns: tuple[str, ...],
        literal_values: tuple[str, ...],
        fk_name: str,
    ) -> None:
        columns_sql = ", ".join(("id", "organization_id", "address_id", *columns))
        placeholders_sql = ", ".join(
            ("CAST(:id AS uuid)", "CAST(:org AS uuid)", "CAST(:addr AS uuid)", *literal_values)
        )
        # Same-org reference: accepted.
        same_id = uuid4()
        async with admin_engine.connect() as conn, conn.begin():
            await conn.execute(
                text(f"INSERT INTO {table} ({columns_sql}) VALUES ({placeholders_sql})").bindparams(
                    id=str(same_id),
                    org=str(seeded_context.org_a),
                    addr=str(seeded_context.addr_a1),
                )
            )
        # Cross-org reference: rejected by the composite FK.
        async with admin_engine.connect() as conn, conn.begin():
            with pytest.raises(IntegrityError, match=rf'foreign key constraint "{fk_name}"'):
                await conn.execute(
                    text(
                        f"INSERT INTO {table} ({columns_sql}) VALUES ({placeholders_sql})"
                    ).bindparams(
                        id=str(uuid4()),
                        org=str(seeded_context.org_a),
                        addr=str(seeded_context.addr_b2),
                    )
                )
        # Clean up the accepted same-org row.
        async with admin_engine.connect() as conn:
            await conn.execute(
                text(f"DELETE FROM {table} WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(same_id)
                )
            )
            await conn.commit()

    async def test_client_address_reference_must_match_organization(
        self, admin_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        await self._assert_composite_guard(
            admin_engine,
            seeded_context,
            table="clients",
            columns=("client_type", "full_name", "primary_phone"),
            literal_values=("'individual'", "'FK Client'", "'9876543210'"),
            fk_name="fk_clients_organization_id_addresses",
        )

    async def test_property_address_reference_must_match_organization(
        self, admin_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        await self._assert_composite_guard(
            admin_engine,
            seeded_context,
            table="properties",
            columns=("property_type", "survey_number"),
            literal_values=("'agricultural'", "'SN-FK-1'"),
            fk_name="fk_properties_organization_id_addresses",
        )

    async def test_party_address_reference_must_match_organization(
        self, admin_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        await self._assert_composite_guard(
            admin_engine,
            seeded_context,
            table="parties",
            columns=("party_type", "display_name", "primary_phone"),
            literal_values=("'individual'", "'FK Party'", "'9876543210'"),
            fk_name="fk_parties_organization_id_addresses",
        )


# ---------------------------------------------------------------------------
# Downgrade restoration (must stay the last test in this module)
# ---------------------------------------------------------------------------


def test_downgrade_restores_t120_nullable_no_rls_contract_and_preserves_data(
    disposable_db: tuple[str, str],
) -> None:
    url, _db_name = disposable_db
    org_rows_before = asyncio.run(_address_org_rows(url))

    _run_alembic_child(url, "downgrade", LEGACY_HEAD)

    assert alembic_current_branch(url) == LEGACY_HEAD
    assert asyncio.run(_addresses_organization_id_nullable(url)) is True
    assert asyncio.run(_addresses_rls_force_flags(url)) == (False, False)
    assert asyncio.run(_addresses_policy_names(url)) == []
    # Org-scoped rows and their org values survive the downgrade untouched.
    assert asyncio.run(_address_org_rows(url)) == org_rows_before
    # T120 contract again: a NULL-org Address is accepted (raw admin insert).
    assert asyncio.run(_null_org_address_now_accepted(url)) is True


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


async def _address_org_rows(url: str) -> list[tuple[str, str]]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT CAST(id AS text), CAST(organization_id AS text) "
                    "FROM addresses ORDER BY id"
                )
            )
            return [(str(row[0]), str(row[1])) for row in result.all()]
    finally:
        await engine.dispose()


async def _addresses_organization_id_nullable(url: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT NOT attnotnull FROM pg_attribute "
                    "WHERE attrelid = 'addresses'::regclass AND attname = 'organization_id'"
                )
            )
            return bool(result.scalar_one())
    finally:
        await engine.dispose()


async def _addresses_rls_force_flags(url: str) -> tuple[bool, bool]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE oid = 'addresses'::regclass"
                )
            )
            rls, force = result.one()
            return bool(rls), bool(force)
    finally:
        await engine.dispose()


async def _addresses_policy_names(url: str) -> list[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT policyname FROM pg_policies WHERE tablename = 'addresses'")
            )
            return sorted(result.scalars())
    finally:
        await engine.dispose()


async def _null_org_address_now_accepted(url: str) -> bool:
    engine = create_async_engine(url)
    new_id = uuid4()
    try:
        async with engine.connect() as conn:
            country_result = await conn.execute(text("SELECT id FROM countries LIMIT 1"))
            country_id = str(country_result.scalar_one())
            try:
                await conn.execute(
                    text(
                        "INSERT INTO addresses (id, organization_id, line1, country_id, "
                        "address_type) VALUES (CAST(:id AS uuid), NULL, 'Null Restored', "
                        "CAST(:country_id AS uuid), 'registered')"
                    ).bindparams(id=str(new_id), country_id=country_id)
                )
            except Exception:
                return False
            await conn.execute(
                text("DELETE FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(new_id)
                )
            )
            await conn.commit()
            return True
    finally:
        await engine.dispose()
