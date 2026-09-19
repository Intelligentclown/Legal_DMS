"""T127 runtime classification and PartyWriteGate PostgreSQL integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.install_classifier import (
    InstallationClassificationError,
    InstallationState,
)
from app.application.party_write_gate import PartyWriteGate
from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
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
    provision_empty_disposable_database,
)

HEAD = "c4e7a9b2d6f1"
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def operational_database() -> Iterator[tuple[str, str]]:
    url, db_name = provision_empty_disposable_database("legal_dms_t127_operational")
    try:
        asyncio.run(establish_fresh_installation(url))
        asyncio.run(run_bootstrap(url))
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


@pytest.fixture(scope="session")
def upgraded_database() -> Iterator[tuple[str, str]]:
    url, db_name = provision_disposable_database_with("legal_dms_t127_upgrade")
    try:
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


@pytest.fixture
async def operational_engine(operational_database: tuple[str, str]) -> AsyncEngine:
    engine = create_async_engine(operational_database[0])
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def upgraded_engine(upgraded_database: tuple[str, str]) -> AsyncEngine:
    engine = create_async_engine(upgraded_database[0])
    try:
        yield engine
    finally:
        await engine.dispose()


async def _seed_org_country_address(session) -> tuple[Organization, Country, Address]:
    org = Organization(name=f"T127-Org-{uuid4()}")
    session.add(org)
    await session.flush()
    used_codes = set((await session.execute(select(Country.iso_code))).scalars())
    iso_code = f"{str(uuid4())[:2].upper()}"
    while iso_code in used_codes:
        iso_code = f"{str(uuid4())[:2].upper()}"
    country = Country(name=f"Country-{uuid4()}", iso_code=iso_code)
    session.add(country)
    await session.flush()
    address = Address(organization_id=org.id, line1="T127 Addr", country_id=country.id)
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
        full_name="T127 Client",
        primary_phone="9876543210",
        address_id=address.id,
    )
    session.add(client)
    await session.flush()
    return client


async def _seed_party_and_ledger(
    session, org: Organization, address: Address, client: Client
) -> None:
    session.add(
        Party(
            id=client.id,
            organization_id=org.id,
            party_type="individual",
            display_name="T127 Party",
            primary_phone="9876543210",
            address_id=address.id,
        )
    )
    await session.flush()
    session.add(
        ClientPartyMigrationLedger(
            legacy_client_id=client.id,
            party_id=client.id,
            organization_id=org.id,
            executor_version="t127.test.v1",
            reconciliation_set_id=f"set:{uuid4()}",
            source_report_sha256="0" * 64,
            resolution_mode="deterministic",
            source_client_version=1,
            source_client_updated_at=datetime.now(UTC),
            source_fingerprint=f"fp-{uuid4()}",
            execution_run_id=uuid4(),
        )
    )
    await session.flush()


async def test_operational_database_sits_at_repository_head(
    operational_database: tuple[str, str],
) -> None:
    assert alembic_current_branch(operational_database[0]) == HEAD


async def test_bootstrapped_installation_classifies_operational_fresh(
    operational_engine: AsyncEngine,
) -> None:
    async with async_sessionmaker(operational_engine)() as session:
        assert await SqlAlchemyInstallationClassifier(session).classify() == (
            InstallationState.OPERATIONAL_FRESH
        )
        await PartyWriteGate(SqlAlchemyInstallationClassifier(session)).ensure_writable()


async def test_classifier_holds_migration_evidence_locks_through_request_transaction(
    operational_engine: AsyncEngine,
) -> None:
    async with async_sessionmaker(operational_engine)() as session:
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.OPERATIONAL_FRESH
        pid = int((await session.execute(text("SELECT pg_backend_pid()"))).scalar_one())
        async with operational_engine.connect() as observer:
            result = await observer.execute(
                text(
                    "SELECT count(*) FROM pg_locks WHERE pid = :pid "
                    "AND locktype = 'relation' AND mode = 'ShareLock' "
                    "AND relation IN ('clients'::regclass, "
                    "'client_party_migration_ledger'::regclass)"
                ),
                {"pid": pid},
            )
            assert int(result.scalar_one()) == 2


async def test_party_and_address_growth_preserve_operational_fresh(
    operational_engine: AsyncEngine,
) -> None:
    async with async_sessionmaker(operational_engine, expire_on_commit=False)() as session:
        org, _country, address = await _seed_org_country_address(session)
        session.add(
            Party(
                organization_id=org.id,
                party_type="individual",
                display_name="T127 Operational Party",
                primary_phone="7000000001",
                address_id=address.id,
            )
        )
        await session.flush()
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.OPERATIONAL_FRESH
        await PartyWriteGate(classifier).ensure_writable()


async def test_empty_upgraded_database_is_unproven_and_denied(
    upgraded_engine: AsyncEngine,
) -> None:
    async with async_sessionmaker(upgraded_engine)() as session:
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.UNPROVEN
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_party_only_t124_database_is_legacy_and_denied(
    upgraded_engine: AsyncEngine,
) -> None:
    async with async_sessionmaker(upgraded_engine, expire_on_commit=False)() as session:
        org = Organization(name=f"T127 Party-only Org-{uuid4()}")
        session.add(org)
        await session.flush()
        session.add(
            Party(
                organization_id=org.id,
                party_type="individual",
                display_name="T124-era Party",
                primary_phone="7000000001",
            )
        )
        await session.flush()
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.LEGACY_WITH_BUSINESS_DATA
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_legacy_and_partial_migration_are_denied(upgraded_engine: AsyncEngine) -> None:
    async with async_sessionmaker(upgraded_engine, expire_on_commit=False)() as session:
        org, _country, address = await _seed_org_country_address(session)
        covered = await _seed_client(session, org, address, uuid4())
        await _seed_party_and_ledger(session, org, address, covered)
        await _seed_client(session, org, address, uuid4())
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.LEGACY_WITH_BUSINESS_DATA
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_complete_migration_is_migrated_and_ordinary_writes_remain_denied(
    upgraded_engine: AsyncEngine,
) -> None:
    async with async_sessionmaker(upgraded_engine, expire_on_commit=False)() as session:
        org, _country, address = await _seed_org_country_address(session)
        client = await _seed_client(session, org, address)
        await _seed_party_and_ledger(session, org, address, client)
        classifier = SqlAlchemyInstallationClassifier(session)
        assert await classifier.classify() == InstallationState.MIGRATED
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_operational_provenance_with_migration_evidence_fails_closed(
    operational_engine: AsyncEngine,
) -> None:
    async with async_sessionmaker(operational_engine, expire_on_commit=False)() as session:
        org, _country, address = await _seed_org_country_address(session)
        await _seed_client(session, org, address)
        classifier = SqlAlchemyInstallationClassifier(session)
        with pytest.raises(InstallationClassificationError):
            await classifier.classify()
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


@pytest.mark.parametrize(
    "view_sql",
    (
        "SELECT installation_id, event_kind, "
        "'unsupported.v1'::text AS provenance_contract_version, "
        "observed_schema_revision, occurred_at FROM legal_dms_provenance.installation_events "
        "WHERE event_kind = 'OPERATIONAL_FRESH_ENTERED'",
        "SELECT installation_id, event_kind, provenance_contract_version, 'bad-revision'::text "
        "AS observed_schema_revision, occurred_at FROM legal_dms_provenance.installation_events "
        "WHERE event_kind = 'OPERATIONAL_FRESH_ENTERED'",
    ),
)
async def test_unsupported_projection_evidence_fails_closed(
    operational_engine: AsyncEngine, view_sql: str
) -> None:
    async with async_sessionmaker(operational_engine, expire_on_commit=False)() as session:
        await session.execute(
            text("CREATE OR REPLACE VIEW legal_dms_provenance.runtime_state AS " f"{view_sql}")
        )
        classifier = SqlAlchemyInstallationClassifier(session)
        with pytest.raises(InstallationClassificationError):
            await classifier.classify()
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()


async def test_unreadable_projection_fails_closed(operational_engine: AsyncEngine) -> None:
    async with async_sessionmaker(operational_engine, expire_on_commit=False)() as session:
        await session.execute(text("DROP VIEW legal_dms_provenance.runtime_state"))
        classifier = SqlAlchemyInstallationClassifier(session)
        with pytest.raises(InstallationClassificationError):
            await classifier.classify()
        with pytest.raises(ForbiddenError):
            await PartyWriteGate(classifier).ensure_writable()
