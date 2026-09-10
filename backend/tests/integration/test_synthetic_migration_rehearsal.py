"""T119: synthetic Party/Client migration rehearsal harness.

A development/testing-only rehearsal that proves the governed
T108 -> T109 -> T110 -> T111 -> T118 Party/Client migration path against one
complete deterministic legacy Client anchor, using purely synthetic data in a
disposable PostgreSQL database.

Hard guarantees exercised here:

- the committed rehearsal runs against a disposable database (provisioned,
  migrated to the repository's *pre-address-finalization* head
  ``f3b7c9d1e2a4``, then destroyed) -- never the shared development database.
  It deliberately does not run on the T122 head: the rehearsal simulates a
  legacy pre-migration database whose `addresses` rows carry no Organization,
  which T122's migration makes structurally impossible on a fresh database
  (fail-closed NOT NULL; see `tests/integration/
  test_address_null_legacy_upgrade_fails_closed.py`). ``f3b7c9d1e2a4`` is
  exactly the contract T122's downgrade restores, so running the legacy-path
  suites on a database pinned at that revision is equivalent to exercising the
  downgraded state;
- one complete deterministic legacy anchor proves every migration dimension:
  Client, Address, Property, PropertyOwner, Matter, client-linked Appointment,
  matter-linked Appointment, Invoice, Payment, ClientContact; UUID-preserving
  Client -> Party; MatterParty `role='client'`; the five direct `party_id`
  bridges; Organization staging backfills; legacy compatibility columns intact;
  and exactly one immutable ledger completion;
- required negative scenarios: ambiguous Organization evidence resolved only
  via a provenance-bearing `operator_reconciled` T109 selection; stale frozen
  evidence rejected before writes; a changed live Client version/timestamp or a
  changed governed basis rejected fail-closed; cross-Organization
  Address/dependent-row disagreement rejected with zero writes;
- controlled fault-injection during one anchor's transactional write unit
  proves a complete rollback (no Party/MatterParty/bridge/staging/ledger
  residue and a still-valid source graph), a clean retry succeeds producing
  exactly one complete migration unit plus one ledger completion, and an
  identical replay is a no-op.

All identifiers are synthetic; no real PAN/Aadhaar or realistic sensitive
values are emitted anywhere.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.cli.client_migration_executor import run_migration_executor
from app.infrastructure.cli.client_reconciliation_artifact_validator import (
    validate_client_reconciliation_artifact,
)
from app.infrastructure.cli.client_reconciliation_staleness_preflight import (
    run_live_reconciliation_staleness_preflight,
)
from app.infrastructure.persistence.models.client import Address, Client, ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.party import (
    ClientPartyMigrationLedger,
    MatterParty,
    Party,
)
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment
from tests.support.synthetic_migration import (
    EXECUTOR_VERSION,
    alembic_current_branch,
    apply_anchor_against,
    cleanup_committed,
    drop_disposable_database,
    freeze_basis,
    inject_unit_fault_on_ledger_flush,
    make_entry,
    make_org,
    make_user,
    provision_disposable_database_with,
    seed_client_graph,
    seed_ids,
    sha256_of,
)

# T120 head = the pre-T122 era (nullable `addresses.organization_id`, no
# Address RLS). This rehearsal simulates a legacy pre-finalization database, so
# it pins this revision rather than the T122 repository head -- see this file's
# module docstring for the reasoning.
ALEMBIC_HEAD = "f3b7c9d1e2a4"


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    """One disposable, migrated PostgreSQL database for the whole rehearsal
    session. Created + migrated to the pinned pre-T122 legacy head on first
    use, destroyed + disposal confirmed in teardown."""
    url, db_name = provision_disposable_database_with(
        "legal_dms_t119_legacy", upgrade_target=ALEMBIC_HEAD
    )
    try:
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


def _make_session(disposable_url: str) -> tuple[AsyncEngine, AsyncSession]:
    engine = create_async_engine(disposable_url)
    return engine, async_sessionmaker(engine, expire_on_commit=False)()


async def _freeze_and_validate(session: AsyncSession) -> tuple[bytes, bytes]:
    report_bytes, artifact_bytes = await freeze_basis(session)
    validated = await validate_client_reconciliation_artifact(
        session,
        source_report_bytes=report_bytes,
        artifact_bytes=artifact_bytes,
    )
    assert validated.valid is True
    assert validated.executable is True
    return report_bytes, artifact_bytes


async def _assert_no_partial_residue(
    session: AsyncSession,
    client_id,
    *,
    preserve_preexisting_address_tenant: bool = False,
) -> None:
    """Asserts that no Party/MatterParty/bridge/staging residue survived a
    rolled-back unit and that the source legacy graph is still valid."""
    party = await session.get(Party, client_id)
    assert party is None
    matter_parties = (
        (await session.execute(select(MatterParty).where(MatterParty.party_id == client_id)))
        .scalars()
        .all()
    )
    assert matter_parties == []
    ledgers = (
        (
            await session.execute(
                select(ClientPartyMigrationLedger).where(
                    ClientPartyMigrationLedger.legacy_client_id == client_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert ledgers == []
    bridged = (
        await session.execute(
            select(func.count()).select_from(Appointment).where(Appointment.party_id == client_id)
        )
    ).scalar_one()
    assert bridged == 0
    legacy = await session.get(Client, client_id)
    assert legacy is not None
    assert legacy.organization_id is None
    legacy_address = await session.get(Address, legacy.address_id)
    assert legacy_address is not None
    if preserve_preexisting_address_tenant:
        assert legacy_address.organization_id is not None
    else:
        assert legacy_address.organization_id is None
    related_matters = (
        (await session.execute(select(Matter).where(Matter.client_id == client_id))).scalars().all()
    )
    related_owners = (
        (await session.execute(select(PropertyOwner).where(PropertyOwner.client_id == client_id)))
        .scalars()
        .all()
    )
    related_appointments = (
        (await session.execute(select(Appointment).where(Appointment.client_id == client_id)))
        .scalars()
        .all()
    )
    related_invoices = (
        (await session.execute(select(Invoice).where(Invoice.client_id == client_id)))
        .scalars()
        .all()
    )
    related_payments = (
        (await session.execute(select(Payment).where(Payment.client_id == client_id)))
        .scalars()
        .all()
    )
    related_contacts = (
        (await session.execute(select(ClientContact).where(ClientContact.client_id == client_id)))
        .scalars()
        .all()
    )
    assert all(row.organization_id is None for row in related_matters + related_owners)
    assert all(row.organization_id is None for row in related_appointments + related_invoices)
    assert all(row.organization_id is None for row in related_payments + related_contacts)
    for owner in related_owners:
        property_row = await session.get(Property, owner.property_id)
        assert property_row is not None
        assert property_row.organization_id is None
        property_address = await session.get(Address, property_row.address_id)
        assert property_address is not None
        if preserve_preexisting_address_tenant:
            assert property_address.organization_id is not None
        else:
            assert property_address.organization_id is None


async def test_rehearsal_is_disposable_and_at_migration_head(disposable_db) -> None:
    url, db_name = disposable_db
    assert db_name.startswith("legal_dms_t119_")
    assert alembic_current_branch(url) == ALEMBIC_HEAD


async def test_end_to_end_rehearsal_complete_anchor_graph(disposable_db) -> None:
    """The full T108 -> T109 -> T110 -> T111 -> T118 rehearsal over one complete
    deterministic legacy anchor, committed to the disposable database only."""
    disposable_url, _db_name = disposable_db
    engine, session = _make_session(disposable_url)
    client = None
    try:
        organization = await make_org(session)
        user = await make_user(session, organization)
        client, rows = await seed_client_graph(session, organization=organization, user=user)
        ids = seed_ids(client, organization, rows)
        await session.commit()
        client_id = client.id

        report_bytes, artifact_bytes = await _freeze_and_validate(session)
        report_sha = sha256_of(report_bytes)
        artifact_sha = sha256_of(artifact_bytes)
        assert len(report_sha) == 64
        assert len(artifact_sha) == 64

        staleness = await run_live_reconciliation_staleness_preflight(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
        )
        assert staleness.valid is True
        assert staleness.stale is False
        assert staleness.executable is True

        dry = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=True,
        )
        assert dry.gated is False
        assert dry.summary["committed_or_planned"] == 1
        assert dry.anchors[0].status == "planned"
        await _assert_no_partial_residue(session, client_id)

        committed = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert committed.gated is False
        assert committed.anchors[0].status == "committed"
        assert committed.summary == {
            "total": 1,
            "committed_or_planned": 1,
            "already_completed": 0,
            "failed": 0,
            "gated": 0,
        }
        ledger_id = committed.anchors[0].contents["ledger_entry"]

        party = await session.get(Party, client_id)
        assert party is not None
        assert party.id == client_id
        assert party.display_name == "Test Client"
        assert party.organization_id == organization.id

        matter_party = (
            await session.execute(
                select(MatterParty).where(
                    MatterParty.matter_id == rows["matter"].id,
                    MatterParty.party_id == client_id,
                    MatterParty.role == "client",
                )
            )
        ).scalar_one()
        assert matter_party is not None

        for bridge_row in (
            await session.get(Appointment, rows["appointment"].id),
            await session.get(Invoice, rows["invoice"].id),
            await session.get(Payment, rows["payment"].id),
            await session.get(PropertyOwner, rows["owner"].id),
            await session.get(ClientContact, rows["contact"].id),
        ):
            assert bridge_row.party_id == client_id

        matter = await session.get(Matter, rows["matter"].id)
        assert matter.organization_id == organization.id
        matter_linked = await session.get(Appointment, rows["matter_linked"].id)
        assert matter_linked.party_id is None
        assert matter_linked.organization_id == organization.id

        legacy = await session.get(Client, client_id)
        assert legacy.full_name == "Test Client"
        assert legacy.address_id == ids["address"]
        assert legacy.version is not None
        assert legacy.organization_id == organization.id

        ledger = (
            await session.execute(
                select(ClientPartyMigrationLedger).where(
                    ClientPartyMigrationLedger.legacy_client_id == client_id
                )
            )
        ).scalar_one()
        assert str(ledger.id) == ledger_id
        assert ledger.party_id == client_id
        assert ledger.resolution_mode == "deterministic"
        assert ledger.organization_id == organization.id

        replay = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert replay.gated is False
        assert replay.anchors[0].status == "already_completed"
        assert replay.anchors[0].contents["ledger_entry"] == ledger_id
        assert replay.summary == {
            "total": 1,
            "committed_or_planned": 0,
            "already_completed": 1,
            "failed": 0,
            "gated": 0,
        }
        ledger_count = (
            await session.execute(
                select(func.count())
                .select_from(ClientPartyMigrationLedger)
                .where(ClientPartyMigrationLedger.legacy_client_id == client_id)
            )
        ).scalar_one()
        assert ledger_count == 1
    finally:
        if client is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_operator_reconciled_resolves_ambiguous_evidence(disposable_db) -> None:
    """An ambiguous Organization is resolved only through a provenance-bearing
    operator_reconciled T109 selection, which then migrates successfully."""
    disposable_url, _db_name = disposable_db
    engine, session = _make_session(disposable_url)
    client = None
    try:
        org_a = await make_org(session)
        org_b = await make_org(session)
        user_a = await make_user(session, org_a)
        user_b = await make_user(session, org_b)
        client, rows = await seed_client_graph(session, organization=None, user=None)
        client_id = client.id
        # Conflicting created_by/updated_by users make the Organization evidence
        # genuinely ambiguous (org_a vs org_b), which is what a
        # provenance-bearing operator_reconciled T109 decision must resolve.
        client.created_by = user_a.id
        client.updated_by = user_b.id
        client.notes = "ambiguous evidence"
        await session.commit()
        ids = seed_ids(client, org_a, rows)

        report_bytes, artifact_bytes = await freeze_basis(
            session,
            overrides={
                str(client_id): {
                    "state": "operator_reconciled",
                    "selected_organization_id": str(org_a.id),
                    "organization_source": "existing",
                    "operator_note": "resolved from synthetic matter ownership review",
                }
            },
        )
        validated = await validate_client_reconciliation_artifact(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
        )
        assert validated.valid is True
        assert validated.executable is True

        result = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert result.gated is False
        assert result.anchors[0].status == "committed"
        assert result.anchors[0].resolution_mode == "operator_reconciled"
        party = await session.get(Party, client_id)
        assert party is not None
        assert party.organization_id == org_a.id
    finally:
        if client is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_stale_frozen_evidence_rejected_before_writes(disposable_db) -> None:
    """Frozen evidence that is stale relative to the live graph gates the run
    before any write."""
    disposable_url, _db_name = disposable_db
    engine, session = _make_session(disposable_url)
    client = None
    extra_client = None
    try:
        organization = await make_org(session)
        user = await make_user(session, organization)
        client, rows = await seed_client_graph(session, organization=organization, user=user)
        ids = seed_ids(client, organization, rows)
        client_id = client.id
        report_bytes, artifact_bytes = await _freeze_and_validate(session)
        await session.commit()

        # A second, unrelated legacy anchor appears after the basis was frozen.
        # Its own org/user keeps the two cleanup graphs independent.
        extra_org = await make_org(session)
        extra_user = await make_user(session, extra_org)
        extra_client, _extra_rows = await seed_client_graph(
            session, organization=extra_org, user=extra_user
        )
        extra_ids = seed_ids(extra_client, extra_org, _extra_rows)
        await session.commit()

        staleness = await run_live_reconciliation_staleness_preflight(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
        )
        assert staleness.stale is True
        assert staleness.executable is False

        result = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert result.gated is True
        assert result.summary == {
            "total": 0,
            "committed_or_planned": 0,
            "already_completed": 0,
            "failed": 0,
            "gated": 0,
        }
        await _assert_no_partial_residue(session, client_id)
        await _assert_no_partial_residue(session, extra_client.id)
    finally:
        if extra_client is not None:
            await cleanup_committed(session, extra_ids)
            await session.commit()
        if client is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_changed_live_client_basis_rejected_fail_closed(disposable_db) -> None:
    """A committed completion whose live Client was mutated afterwards is never
    replayed as already_completed; it is rejected fail-closed with zero new
    writes and exactly one preserved ledger row."""
    disposable_url, _db_name = disposable_db
    engine, session = _make_session(disposable_url)
    client = None
    try:
        organization = await make_org(session)
        user = await make_user(session, organization)
        client, rows = await seed_client_graph(session, organization=organization, user=user)
        ids = seed_ids(client, organization, rows)
        client_id = client.id
        report_bytes, artifact_bytes = await _freeze_and_validate(session)

        first = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert first.anchors[0].status == "committed"
        ledger_id = first.anchors[0].contents["ledger_entry"]

        live = await session.get(Client, client_id)
        live.notes = "legacy client mutated after rehearsal commit"
        await session.commit()
        await session.refresh(live)

        second = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert second.summary["already_completed"] == 0
        if second.gated:
            assert second.summary["total"] == 0
        else:
            assert second.anchors[0].status == "failed"
            assert second.anchors[0].failure_code == "basis_collision"

        ledgers = (
            (
                await session.execute(
                    select(ClientPartyMigrationLedger).where(
                        ClientPartyMigrationLedger.legacy_client_id == client_id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(ledgers) == 1
        assert str(ledgers[0].id) == ledger_id
    finally:
        if client is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_cross_organization_disagreement_rejected_zero_writes(disposable_db) -> None:
    """A dependent row (the Address) belonging to another Organization than the
    selected decision rejects the unit with zero writes."""
    disposable_url, _db_name = disposable_db
    engine, session = _make_session(disposable_url)
    client = None
    try:
        org_a = await make_org(session)
        org_b = await make_org(session)
        user_a = await make_user(session, org_a)
        client, rows = await seed_client_graph(session, organization=org_a, user=user_a)
        client_id = client.id
        # The legacy Address already carries a resolved Organization that
        # disagrees with the selected decision's Organization -- this must fail
        # closed as tenant disagreement with zero writes.
        address = await session.get(Address, rows["address"].id)
        assert address is not None
        address.organization_id = org_b.id
        await session.commit()
        ids = seed_ids(client, org_a, rows)

        entry = make_entry(client, org_a, selected_organization_id=org_a.id)
        result = await apply_anchor_against(session, client, org_a, entry=entry)
        await session.rollback()
        assert result.status == "failed"
        assert result.failure_code == "tenant_disagreement"
        await _assert_no_partial_residue(
            session,
            client_id,
            preserve_preexisting_address_tenant=True,
        )
    finally:
        if client is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_fault_injection_rollback_retry_noop(disposable_db) -> None:
    """Controlled mid-unit fault injection during one anchor's transactional
    write unit proves a complete rollback (no residue, valid source graph);
    a clean retry succeeds with exactly one complete migration unit and one
    ledger completion; and an identical replay is a no-op."""
    disposable_url, _db_name = disposable_db
    engine, session = _make_session(disposable_url)
    client = None
    try:
        organization = await make_org(session)
        user = await make_user(session, organization)
        client, rows = await seed_client_graph(session, organization=organization, user=user)
        ids = seed_ids(client, organization, rows)
        client_id = client.id
        # Commit the source graph so the injected failure + rollback only ever
        # affects the migration unit (proving the source graph stays valid).
        await session.commit()
        report_bytes, artifact_bytes = await _freeze_and_validate(session)

        async with inject_unit_fault_on_ledger_flush(session):
            injected = await run_migration_executor(
                session,
                source_report_bytes=report_bytes,
                artifact_bytes=artifact_bytes,
                executor_version=EXECUTOR_VERSION,
                dry_run=False,
            )

        assert injected.gated is False
        assert injected.anchors[0].status == "failed"
        assert injected.anchors[0].failure_code == "execution_error"
        await _assert_no_partial_residue(session, client_id)

        retry = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert retry.gated is False
        assert retry.anchors[0].status == "committed"
        assert retry.summary == {
            "total": 1,
            "committed_or_planned": 1,
            "already_completed": 0,
            "failed": 0,
            "gated": 0,
        }
        ledger_count = (
            await session.execute(
                select(func.count())
                .select_from(ClientPartyMigrationLedger)
                .where(ClientPartyMigrationLedger.legacy_client_id == client_id)
            )
        ).scalar_one()
        assert ledger_count == 1

        replay = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert replay.anchors[0].status == "already_completed"
        assert replay.summary["committed_or_planned"] == 0
        final_ledger_count = (
            await session.execute(
                select(func.count())
                .select_from(ClientPartyMigrationLedger)
                .where(ClientPartyMigrationLedger.legacy_client_id == client_id)
            )
        ).scalar_one()
        assert final_ledger_count == 1
    finally:
        if client is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()
