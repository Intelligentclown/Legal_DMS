"""T130: Address forced-RLS / runtime-role posture preserved at the new head.

T130 adds only the Address application surface + the `addresses:*` permission
seed/grant migration — it must not disturb the T122 tenant/RLS contract. This
module re-proves the runtime posture at the *new* head (`5d8a3f2e9c6b`) against
a disposable PostgreSQL database and the real restricted `legal_dms_app` role:

- catalog/security attributes: `addresses` still has `relrowsecurity` +
  `relforcerowsecurity`; its policy surface is still exactly the four
  default-deny GUC-driven policies (`addresses_select`/`insert`/`update`/
  `delete`); `legal_dms_app` still owns nothing relevant and is not
  SUPERUSER/BYPASSRLS;
- behavioral default-deny through the restricted role without Organization
  context, org-scoped visibility via `app.current_organization_id`, cross-Org
  SELECT/INSERT/UPDATE/DELETE denial, and a same-Org UPDATE that preserves the
  Organization.

Mirrors the T122 module's assertion technique (era-split discipline from the
queue row: exhaustive era-correct catalog snapshots live in the T122 suite at
`9c4a7e2d1b5f`; this module is a focused preservation guard at the T130 head).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
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

NEW_HEAD = "5d8a3f2e9c6b"

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, db_name = provision_disposable_database_with("legal_dms_t130_rls", upgrade_target=NEW_HEAD)
    try:
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


def _disposable_app_url(disposable_url: str) -> str:
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
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org_a = Organization(name=f"T130-Org-A-{uuid4()}")
        org_b = Organization(name=f"T130-Org-B-{uuid4()}")
        session.add_all([org_a, org_b])
        await session.flush()

        session.add_all(
            [
                User(
                    email=f"{uuid4()}@example.com",
                    full_name="T130 User A",
                    organization_id=org_a.id,
                ),
                User(
                    email=f"{uuid4()}@example.com",
                    full_name="T130 User B",
                    organization_id=org_b.id,
                ),
            ]
        )

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


class TestFreshUpgradeAtT130Head:
    async def test_disposable_database_sits_at_the_t130_head(
        self, disposable_db: tuple[str, str]
    ) -> None:
        url, _db_name = disposable_db
        assert alembic_current_branch(url) == NEW_HEAD


class TestAddressesRowSecurityPreserved:
    async def test_addresses_still_forces_row_security(self, admin_engine: AsyncEngine) -> None:
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

    async def test_addresses_still_has_exactly_four_default_deny_guc_policies(
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
        names = {policy.policyname for policy in policies}
        assert names == {
            "addresses_delete",
            "addresses_insert",
            "addresses_select",
            "addresses_update",
        }
        by_cmd = {policy.cmd: policy for policy in policies}
        assert by_cmd["SELECT"].qual is not None
        assert by_cmd["DELETE"].qual is not None
        assert by_cmd["INSERT"].qual is None and by_cmd["INSERT"].with_check is not None
        assert by_cmd["UPDATE"].qual is not None and by_cmd["UPDATE"].with_check is not None
        for policy in policies:
            combined = f"{policy.qual or ''} {policy.with_check or ''}"
            assert "app.current_organization_id" in combined
            assert "current_user" not in combined

    async def test_legal_dms_app_runtime_role_posture_unchanged(
        self, admin_engine: AsyncEngine
    ) -> None:
        async with admin_engine.connect() as conn:
            owner = (
                await conn.execute(
                    text("SELECT tableowner FROM pg_tables WHERE tablename = 'addresses'")
                )
            ).scalar_one()
            rolsuper, rolbypassrls = (
                await conn.execute(
                    text(
                        "SELECT rolsuper, rolbypassrls FROM pg_roles "
                        "WHERE rolname = 'legal_dms_app'"
                    )
                )
            ).one()
        assert owner != "legal_dms_app"
        assert rolsuper is False
        assert rolbypassrls is False


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

    async def test_update_and_delete_are_no_ops_with_no_organization_guc(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            updated = await conn.execute(
                text(
                    "UPDATE addresses SET line1 = 'No Context Update' WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.addr_a1))
            )
            assert updated.rowcount == 0
            deleted = await conn.execute(
                text("DELETE FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.addr_a1)
                )
            )
            assert deleted.rowcount == 0


class TestOrganizationScopedVisibility:
    async def test_org_a_caller_sees_only_its_own_addresses(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            rows = (await conn.execute(text("SELECT id FROM addresses"))).scalars()
        assert set(rows) == {seeded_context.addr_a1, seeded_context.addr_a3}

    async def test_cross_organization_select_is_empty(
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

    async def test_cross_organization_update_and_delete_are_no_ops(
        self, app_engine: AsyncEngine, seeded_context: SimpleNamespace
    ) -> None:
        async with app_engine.connect() as conn, conn.begin():
            await _set_org_context(conn, str(seeded_context.org_a))
            updated = await conn.execute(
                text(
                    "UPDATE addresses SET line1 = 'Hijacked' WHERE id = CAST(:id AS uuid)"
                ).bindparams(id=str(seeded_context.addr_b2))
            )
            assert updated.rowcount == 0
            deleted = await conn.execute(
                text("DELETE FROM addresses WHERE id = CAST(:id AS uuid)").bindparams(
                    id=str(seeded_context.addr_b2)
                )
            )
            assert deleted.rowcount == 0

    async def test_same_org_update_preserves_organization(
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
            org = (
                await conn.execute(
                    text(
                        "SELECT organization_id FROM addresses WHERE id = CAST(:id AS uuid)"
                    ).bindparams(id=str(seeded_context.addr_a1))
                )
            ).scalar_one()
            assert org == seeded_context.org_a
            await trans.rollback()  # keep the seeded value pristine for later tests
