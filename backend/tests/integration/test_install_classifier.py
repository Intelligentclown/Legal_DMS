"""T124: ADR-0036 fresh-install classification + the fail-closed Party write
gate — PostgreSQL tests against a disposable database migrated to the
repository head.

Every scenario builds its governed rows inside the same (uncommitted)
transaction the classifier reads from, then rolls back, so the shared
disposable database stays pristine regardless of test order:

- `FRESH`: an empty installation (only tenant/auth scaffolding present)
  classifies fresh, and the gate admits a Party write;
- `parties` rows alone never flip the classification (the slice's own
  product surface is excluded from the per-write predicate);
- a single governed legacy object (address, client, ...) classifies
  `LEGACY_WITH_BUSINESS_DATA` and the gate blocks with `ForbiddenError`;
- a fully ledger-covered client set plus ledger rows classifies `MIGRATED`
  and the gate still blocks (ordinary writes stay gated post-cutover);
- a ledger that does not yet cover every `clients` row — even one with
  ledger entries present — classifies `LEGACY_WITH_BUSINESS_DATA`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.install_classifier import InstallationState
from app.application.party_write_gate import PartyWriteGate
from app.infrastructure.persistence.models.client import Address, Client
from app.infrastructure.persistence.models.geography import Country
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import ClientPartyMigrationLedger, Party
from app.infrastructure.persistence.sqlalchemy_install_classifier import (
    SqlAlchemyInstallationClassifier,
)
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_disposable_database_with,
)

HEAD = "c4e7a9b2d6f1"

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, db_name = provision_disposable_database_with("legal_dms_t124_classifier")
    try:
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


@pytest.fixture
async def admin_engine(disposable_db: tuple[str, str]) -> AsyncEngine:
    url, _db_name = disposable_db
    engine = create_async_engine(url)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _seed_org_country_address(session) -> tuple[Organization, Country, Address]:
    org = Organization(name=f"T124-Org-{uuid4()}")
    session.add(org)
    await session.flush()

    used_codes = set((await session.execute(select(Country.iso_code))).scalars())
    iso_code = f"{str(uuid4())[:2].upper()}"
    while iso_code in used_codes:
        iso_code = f"{str(uuid4())[:2].upper()}"
    country = Country(name=f"Country-{uuid4()}", iso_code=iso_code)
    session.add(country)
    await session.flush()

    address = Address(organization_id=org.id, line1="T124 Addr", country_id=country.id)
    session.add(address)
    await session.flush()
    return org, country, address


async def _seed_client(
    session, org: Organization, address: Address, client_id: UUID | None = None
) -> Client:
    client = Client(
        id=client_id,
        organization_id=org.id,
        client_type="individual",
        full_name="T124 Client",
        primary_phone="9876543210",
        address_id=address.id,
    )
    session.add(client)
    await session.flush()
    return client


async def _seed_party_and_ledger(
    session, org: Organization, address: Address, client: Client
) -> None:
    party = Party(
        id=client.id,
        organization_id=org.id,
        party_type="individual",
        display_name="T124 Party",
        primary_phone="9876543210",
        address_id=address.id,
    )
    session.add(party)
    await session.flush()

    ledger = ClientPartyMigrationLedger(
        legacy_client_id=client.id,
        party_id=client.id,
        organization_id=org.id,
        executor_version="t124.test.v1",
        reconciliation_set_id=f"set:{uuid4()}",
        source_report_sha256="0" * 64,
        resolution_mode="deterministic",
        source_client_version=1,
        source_client_updated_at=datetime.now(UTC),
        source_fingerprint=f"fp-{uuid4()}",
        execution_run_id=uuid4(),
    )
    session.add(ledger)
    await session.flush()


async def test_disposable_database_sits_at_the_repository_head(
    disposable_db: tuple[str, str],
) -> None:
    url, _db_name = disposable_db
    assert alembic_current_branch(url) == HEAD


async def test_empty_installation_classifies_fresh(admin_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.FRESH


async def test_fresh_state_admits_party_write(admin_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        gate = PartyWriteGate(SqlAlchemyInstallationClassifier(session))
        await gate.ensure_writable()


async def test_parties_rows_alone_never_flip_the_classification(
    admin_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org = Organization(name=f"T124-Org-{uuid4()}")
        session.add(org)
        await session.flush()
        session.add(
            Party(
                organization_id=org.id,
                party_type="individual",
                display_name="T124 Solo Party",
                primary_phone="7000000001",
            )
        )
        await session.flush()

        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.FRESH
        gate = PartyWriteGate(classifier)
        await gate.ensure_writable()


async def test_address_row_classifies_legacy_and_gate_blocks(
    admin_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        await _seed_org_country_address(session)
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.LEGACY_WITH_BUSINESS_DATA
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_client_without_ledger_classifies_legacy_and_gate_blocks(
    admin_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org, _country, address = await _seed_org_country_address(session)
        await _seed_client(session, org, address)
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.LEGACY_WITH_BUSINESS_DATA
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_full_ledger_coverage_classifies_migrated_and_gate_blocks(
    admin_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org, _country, address = await _seed_org_country_address(session)
        client = await _seed_client(session, org, address)
        await _seed_party_and_ledger(session, org, address, client)
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.MIGRATED
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_ledger_with_uncovered_clients_classifies_legacy(
    admin_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        org, _country, address = await _seed_org_country_address(session)
        covered = await _seed_client(session, org, address, client_id=uuid4())
        await _seed_party_and_ledger(session, org, address, covered)
        await _seed_client(session, org, address, client_id=uuid4())

        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.LEGACY_WITH_BUSINESS_DATA
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()
