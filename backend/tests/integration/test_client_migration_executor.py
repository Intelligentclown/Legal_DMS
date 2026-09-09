"""T118/ADR-0035 step 4: integration tests for the governed Party/Client
migration & backfill executor.

Coverage mirrors the T118 authorization contract:

- deterministic and operator_reconciled executions construct the complete
  write unit (parties row, ADR-0033 Organization staging backfills, bounded
  matter_parties `role = 'client'` rows, T117 `party_id` bridges, and one
  immutable migration-ledger completion row);
- retry/idempotency is ledger-driven: identical replay is a true no-op only
  when the committed ledger proves the live legacy-anchor identity still
  matches (id, version, canonical updated_at via the live-derived source
  fingerprint); a legacy Client mutated after a committed completion fails
  closed as a stale basis collision rather than being replayed as
  `already_completed`, and any change of Organization or basis also fails
  closed;
- fail-closed guards: missing anchor, missing Organization, pre-existing
  Party without a ledger, partial bridge state, conflicting MatterParty,
  cross-tenant Organization disagreement, and Organization-typed Clients
  carrying Aadhaar;
- the T110/T111 gates block every write when the artifact hash is wrong or
  the live graph drifted from the frozen reconciliation basis;
- dry-runs roll back everything; write-mode commits per anchor and leaves
  the legacy `clients` graph untouched; re-running after a commit is an
  append-only no-op; and no Party CRUD is exposed through the HTTP API.

Tests that commit use their own engine and delete their rows afterwards so
the shared dev database stays clean. Everything that does not commit uses
the rollback-only `db_session` fixture.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cli.client_migration_executor import (
    EXECUTOR_SCHEMA_VERSION,
    TASK,
    client_source_fingerprint,
    run_migration_executor,
)
from app.infrastructure.persistence.models.client import Address, Client, ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import (
    ClientPartyMigrationLedger,
    MatterParty,
    Party,
)
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment
from app.main import app as api_app
from tests.support.synthetic_migration import (
    EXECUTOR_VERSION,
    SYNTHETIC_AADHAAR,
    SYNTHETIC_PAN,
    apply_anchor_against,
    cleanup_committed,
    freeze_basis,
    make_entry,
    make_isolated_session,
    make_org,
    make_user,
    seed_client_graph,
    seed_ids,
)


async def test_deterministic_apply_writes_the_complete_unit(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, rows = await seed_client_graph(db_session, organization=organization, user=user)

    result = await apply_anchor_against(db_session, client, organization)

    assert result.status == "applied"
    assert result.resolution_mode == "deterministic"
    assert result.contents["party_id"] == str(client.id)
    assert result.contents["organization_id"] == str(organization.id)
    assert result.contents["matters_backfilled"] == 1
    assert result.contents["matter_parties_created"] == 1
    assert result.contents["property_owners_bridged"] == 1
    assert result.contents["appointments_bridged"] == 1
    assert result.contents["matter_linked_appointments_staged"] == 1
    assert result.contents["invoices_bridged"] == 1
    assert result.contents["payments_bridged"] == 1
    assert result.contents["client_contacts_bridged"] == 1

    party = await db_session.get(Party, client.id)
    assert party is not None
    assert party.organization_id == organization.id
    assert party.party_type == "individual"
    assert party.display_name == client.full_name
    assert party.primary_phone == client.primary_phone
    assert party.primary_email == client.primary_email
    assert party.notes == client.notes

    matter = await db_session.get(Matter, rows["matter"].id)
    assert matter.organization_id == organization.id
    matter_party = (
        await db_session.execute(
            select(MatterParty).where(
                MatterParty.matter_id == matter.id,
                MatterParty.party_id == client.id,
                MatterParty.role == "client",
            )
        )
    ).scalar_one()
    assert matter_party.organization_id == organization.id

    appointment = await db_session.get(Appointment, rows["appointment"].id)
    assert appointment.organization_id == organization.id
    assert appointment.party_id == client.id
    linked = await db_session.get(Appointment, rows["matter_linked"].id)
    assert linked.organization_id == organization.id
    assert linked.party_id is None
    invoice = await db_session.get(Invoice, rows["invoice"].id)
    assert invoice.organization_id == organization.id
    assert invoice.party_id == client.id
    payment = await db_session.get(Payment, rows["payment"].id)
    assert payment.organization_id == organization.id
    assert payment.party_id == client.id
    owner = await db_session.get(PropertyOwner, rows["owner"].id)
    assert owner.organization_id == organization.id
    assert owner.party_id == client.id
    contact = await db_session.get(ClientContact, rows["contact"].id)
    assert contact.organization_id == organization.id
    assert contact.party_id == client.id
    property_row = await db_session.get(Property, rows["property"].id)
    assert property_row.organization_id == organization.id
    address = await db_session.get(Address, rows["address"].id)
    assert address.organization_id == organization.id

    ledger = (
        await db_session.execute(
            select(ClientPartyMigrationLedger).where(
                ClientPartyMigrationLedger.legacy_client_id == client.id
            )
        )
    ).scalar_one()
    assert ledger.party_id == client.id
    assert ledger.organization_id == organization.id
    assert ledger.executor_version == EXECUTOR_VERSION
    assert ledger.resolution_mode == "deterministic"
    assert ledger.source_client_version == client.version
    assert ledger.source_fingerprint


async def test_operator_reconciled_apply_records_the_operator_mode(
    db_session: AsyncSession,
) -> None:
    organization = await make_org(db_session)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=None)

    entry = make_entry(client, organization, state="operator_reconciled")
    result = await apply_anchor_against(db_session, client, organization, entry=entry)

    assert result.status == "applied"
    ledger = (
        await db_session.execute(
            select(ClientPartyMigrationLedger).where(
                ClientPartyMigrationLedger.legacy_client_id == client.id
            )
        )
    ).scalar_one()
    assert ledger.resolution_mode == "operator_reconciled"
    assert ledger.organization_id == organization.id


async def test_identical_replay_is_a_noop(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)

    first = await apply_anchor_against(db_session, client, organization)
    second = await apply_anchor_against(db_session, client, organization)

    assert first.status == "applied"
    assert second.status == "already_completed"
    assert second.contents["party_id"] == str(client.id)
    assert second.contents["ledger_entry"] == first.contents["ledger_entry"]
    count = (
        await db_session.execute(
            select(ClientPartyMigrationLedger).where(
                ClientPartyMigrationLedger.legacy_client_id == client.id
            )
        )
    ).scalar_one()
    assert count is not None


async def test_changed_live_anchor_state_rejects_as_basis_collision(
    db_session: AsyncSession,
) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)

    first = await apply_anchor_against(db_session, client, organization)
    assert first.status == "applied"

    before_version = client.version
    before_updated_at = client.updated_at
    client.notes = "legacy client mutated after the first application"
    await db_session.flush()
    await db_session.refresh(client)
    assert (client.version, client.updated_at) != (before_version, before_updated_at)
    assert client.version > before_version

    second = await apply_anchor_against(db_session, client, organization)

    assert second.status == "failed"
    assert second.failure_code == "basis_collision"
    assert second.status != "already_completed"


async def test_changed_organization_rejects_as_basis_collision(db_session: AsyncSession) -> None:
    organization_a = await make_org(db_session)
    organization_b = await make_org(db_session)
    user = await make_user(db_session, organization_a)
    client, _rows = await seed_client_graph(db_session, organization=organization_a, user=user)

    first = await apply_anchor_against(db_session, client, organization_a)
    redirected = make_entry(client, organization_b, selected_organization_id=organization_b.id)
    second = await apply_anchor_against(db_session, client, organization_a, entry=redirected)

    assert first.status == "applied"
    assert second.status == "failed"
    assert second.failure_code == "basis_collision"


async def test_changed_reconciliation_basis_rejects(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)

    first = await apply_anchor_against(db_session, client, organization)
    second = await apply_anchor_against(
        db_session,
        client,
        organization,
        entry=make_entry(client, organization, set_id="client-set:other:xxxx"),
        source_report_sha256="1" * 64,
    )

    assert first.status == "applied"
    assert second.status == "failed"
    assert second.failure_code == "already_migrated_different_basis"


async def test_missing_anchor_fails_closed(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    result = await apply_anchor_against(db_session, Client(id=uuid4()), organization)

    assert result.status == "failed"
    assert result.failure_code == "missing_anchor"


async def test_missing_organization_fails_closed(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)

    bogus = make_entry(client, organization, selected_organization_id=uuid4())
    result = await apply_anchor_against(db_session, client, organization, entry=bogus)

    assert result.status == "failed"
    assert result.failure_code == "organization_not_found"


async def test_party_without_ledger_fails_closed(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)
    db_session.add(
        Party(
            id=client.id,
            organization_id=organization.id,
            party_type="individual",
            display_name="Pre Existing",
            primary_phone="1234567",
        )
    )
    await db_session.flush()

    result = await apply_anchor_against(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "party_exists_without_ledger"


async def test_party_in_other_organization_conflicts(db_session: AsyncSession) -> None:
    organization_a = await make_org(db_session)
    organization_b = await make_org(db_session)
    user = await make_user(db_session, organization_a)
    client, _rows = await seed_client_graph(db_session, organization=organization_a, user=user)
    db_session.add(
        Party(
            id=client.id,
            organization_id=organization_b.id,
            party_type="individual",
            display_name="Pre Existing",
            primary_phone="1234567",
        )
    )
    await db_session.flush()

    result = await apply_anchor_against(db_session, client, organization_a)

    assert result.status == "failed"
    assert result.failure_code == "party_organization_conflict"


async def test_partial_bridge_state_without_ledger_fails_closed(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, rows = await seed_client_graph(db_session, organization=organization, user=user)
    invoice = await db_session.get(Invoice, rows["invoice"].id)
    assert invoice is not None
    invoice.party_id = uuid4()
    await db_session.flush()

    result = await apply_anchor_against(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "unproven_partial_state"


async def test_conflicting_matter_party_fails_closed(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, rows = await seed_client_graph(db_session, organization=organization, user=user)
    matter = await db_session.get(Matter, rows["matter"].id)
    assert matter is not None
    matter.organization_id = organization.id
    await db_session.flush()
    other_party = Party(
        id=uuid4(),
        organization_id=organization.id,
        party_type="individual",
        display_name="Other Client",
        primary_phone="1234567",
    )
    db_session.add(other_party)
    await db_session.flush()
    db_session.add(
        MatterParty(
            organization_id=organization.id,
            matter_id=rows["matter"].id,
            party_id=other_party.id,
            role="client",
        )
    )
    await db_session.flush()

    result = await apply_anchor_against(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "matter_party_conflict"


async def test_cross_tenant_organization_disagreement_fails_closed(
    db_session: AsyncSession,
) -> None:
    organization_a = await make_org(db_session)
    organization_b = await make_org(db_session)
    user = await make_user(db_session, organization_a)
    client, rows = await seed_client_graph(db_session, organization=organization_a, user=user)
    appointment = await db_session.get(Appointment, rows["appointment"].id)
    assert appointment is not None
    appointment.organization_id = organization_b.id
    await db_session.flush()

    result = await apply_anchor_against(db_session, client, organization_a)

    assert result.status == "failed"
    assert result.failure_code == "tenant_disagreement"


async def test_client_address_cross_tenant_fails_closed(db_session: AsyncSession) -> None:
    organization_a = await make_org(db_session)
    organization_b = await make_org(db_session)
    user = await make_user(db_session, organization_a)
    client, rows = await seed_client_graph(db_session, organization=organization_a, user=user)
    address = await db_session.get(Address, rows["address"].id)
    assert address is not None
    address.organization_id = organization_b.id
    await db_session.flush()

    result = await apply_anchor_against(db_session, client, organization_a)

    assert result.status == "failed"
    assert result.failure_code == "tenant_disagreement"


async def test_organization_client_with_aadhaar_is_incompatible(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(
        db_session,
        organization=organization,
        user=user,
        client_type="organization",
        aadhaar_number=SYNTHETIC_AADHAAR,
    )

    result = await apply_anchor_against(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "incompatible_party_fields"


async def test_dry_run_plans_the_write_set_and_rolls_back_everything(
    db_session: AsyncSession,
) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)
    client_id = str(client.id)
    report_bytes, artifact_bytes = await freeze_basis(db_session)

    result = await run_migration_executor(
        db_session,
        source_report_bytes=report_bytes,
        artifact_bytes=artifact_bytes,
        executor_version=EXECUTOR_VERSION,
        dry_run=True,
    )

    assert result.gated is False
    assert result.dry_run is True
    assert result.task == TASK
    assert result.schema_version == EXECUTOR_SCHEMA_VERSION
    assert result.anchors[0].status == "planned"
    assert result.anchors[0].contents["party_id"] == client_id
    assert result.summary == {
        "total": 1,
        "committed_or_planned": 1,
        "already_completed": 0,
        "failed": 0,
        "gated": 0,
    }
    assert await db_session.get(Party, UUID(client_id)) is None
    assert (
        await db_session.execute(
            select(ClientPartyMigrationLedger).where(
                ClientPartyMigrationLedger.legacy_client_id == UUID(client_id)
            )
        )
    ).first() is None


async def test_non_executable_decision_is_gated(db_session: AsyncSession) -> None:
    _client, _rows = await seed_client_graph(db_session, organization=None, user=None)
    report_bytes, artifact_bytes = await freeze_basis(db_session)

    result = await run_migration_executor(
        db_session,
        source_report_bytes=report_bytes,
        artifact_bytes=artifact_bytes,
        executor_version=EXECUTOR_VERSION,
        dry_run=True,
    )

    assert result.gated is True
    assert result.anchors == ()
    assert result.summary["total"] == 0
    assert await db_session.get(Party, _client.id) is None


async def test_t110_artifact_hash_failure_blocks_every_write(db_session: AsyncSession) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)
    report_bytes, artifact_bytes = await freeze_basis(db_session)
    artifact = json.loads(artifact_bytes.decode("utf-8"))
    artifact["source_report"]["report_sha256"] = "f" * 64
    artifact_bytes = json.dumps(artifact).encode("utf-8")

    result = await run_migration_executor(
        db_session,
        source_report_bytes=report_bytes,
        artifact_bytes=artifact_bytes,
        executor_version=EXECUTOR_VERSION,
        dry_run=False,
    )

    assert result.gated is True
    assert "source_report_hash_mismatch" in [issue.code for issue in result.gating_issues]
    assert result.summary["total"] == 0
    assert await db_session.get(Party, client.id) is None


async def test_t111_stale_basis_blocks_every_write(db_session: AsyncSession) -> None:
    organization_a = await make_org(db_session)
    organization_b = await make_org(db_session)
    user_a = await make_user(db_session, organization_a)
    user_b = await make_user(db_session, organization_b)
    client, _rows = await seed_client_graph(db_session, organization=organization_a, user=user_a)
    report_bytes, artifact_bytes = await freeze_basis(db_session)

    client.updated_by = user_b.id
    await db_session.flush()

    result = await run_migration_executor(
        db_session,
        source_report_bytes=report_bytes,
        artifact_bytes=artifact_bytes,
        executor_version=EXECUTOR_VERSION,
        dry_run=False,
    )

    assert result.gated is True
    assert "stale_current_snapshot" in [issue.code for issue in result.gating_issues]
    assert result.summary["total"] == 0
    assert await db_session.get(Party, client.id) is None


async def test_missing_organization_decision_gates_all_writes(db_session: AsyncSession) -> None:
    client, _rows = await seed_client_graph(db_session, organization=None, user=None)
    report_bytes, artifact_bytes = await freeze_basis(
        db_session,
        overrides={
            str(client.id): {
                "state": "operator_reconciled",
                "selected_organization_id": uuid4(),
                "organization_source": "existing",
            }
        },
    )

    result = await run_migration_executor(
        db_session,
        source_report_bytes=report_bytes,
        artifact_bytes=artifact_bytes,
        executor_version=EXECUTOR_VERSION,
        dry_run=False,
    )

    assert result.gated is True
    assert "organization_not_found" in [issue.code for issue in result.gating_issues]
    assert result.summary["total"] == 0
    assert await db_session.get(Party, client.id) is None


async def test_write_mode_commits_and_leaves_legacy_graph_untouched() -> None:
    engine, session = await make_isolated_session()
    client: Client | None = None
    organization: Organization | None = None
    ids: dict[str, UUID] | None = None
    try:
        organization = await make_org(session)
        user = await make_user(session, organization)
        client, rows = await seed_client_graph(
            session,
            organization=organization,
            user=user,
            pan_number=SYNTHETIC_PAN,
            aadhaar_number=SYNTHETIC_AADHAAR,
        )
        ids = seed_ids(client, organization, rows)
        report_bytes, artifact_bytes = await freeze_basis(session)

        result = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )

        assert result.gated is False
        assert result.dry_run is False
        assert result.anchors[0].status == "committed"
        assert result.summary["committed_or_planned"] == 1

        client = await session.get(Client, client.id)
        assert client is not None

        payload = json.dumps(result.to_dict())
        assert payload.startswith('{"schema_version"')
        assert SYNTHETIC_AADHAAR not in payload
        assert SYNTHETIC_PAN not in payload

        party = await session.get(Party, client.id)
        assert party is not None
        assert party.organization_id == organization.id
        assert party.party_type == "individual"
        assert party.display_name == client.full_name
        assert "organization_id" in result.anchors[0].contents

        matter = await session.get(Matter, rows["matter"].id)
        assert matter.organization_id == organization.id
        linked = await session.get(Appointment, rows["matter_linked"].id)
        assert linked.organization_id == organization.id
        assert linked.party_id is None

        ledger = (
            await session.execute(
                select(ClientPartyMigrationLedger).where(
                    ClientPartyMigrationLedger.legacy_client_id == client.id
                )
            )
        ).scalar_one()
        assert ledger.party_id == client.id
        assert ledger.resolution_mode == "deterministic"

        legacy = await session.get(Client, client.id)
        assert legacy is not None
        assert legacy.full_name == "Test Client"
        assert legacy.address_id == rows["address"].id
        bridged = await session.get(Appointment, rows["appointment"].id)
        assert bridged.client_id == client.id
        invoice = await session.get(Invoice, rows["invoice"].id)
        assert invoice.client_id == client.id
    finally:
        if ids is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_rerun_after_commit_is_append_only_noop() -> None:
    engine, session = await make_isolated_session()
    client: Client | None = None
    organization: Organization | None = None
    ids: dict[str, UUID] | None = None
    try:
        organization = await make_org(session)
        user = await make_user(session, organization)
        client, rows = await seed_client_graph(session, organization=organization, user=user)
        ids = seed_ids(client, organization, rows)
        report_bytes, artifact_bytes = await freeze_basis(session)

        first = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert first.anchors[0].status == "committed"
        ledger_id = first.anchors[0].contents["ledger_entry"]

        second = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )

        assert second.gated is False
        assert second.anchors[0].status == "already_completed"
        assert second.anchors[0].contents["ledger_entry"] == ledger_id
        assert second.summary == {
            "total": 1,
            "committed_or_planned": 0,
            "already_completed": 1,
            "failed": 0,
            "gated": 0,
        }
        ledger_count = (
            await session.execute(
                select(ClientPartyMigrationLedger).where(
                    ClientPartyMigrationLedger.legacy_client_id == client.id
                )
            )
        ).scalar_one()
        assert ledger_count is not None
    finally:
        if ids is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_live_client_mutation_after_commit_fails_closed() -> None:
    engine, session = await make_isolated_session()
    client: Client | None = None
    organization: Organization | None = None
    ids: dict[str, UUID] | None = None
    try:
        organization = await make_org(session)
        user = await make_user(session, organization)
        client, rows = await seed_client_graph(
            session,
            organization=organization,
            user=user,
            pan_number=SYNTHETIC_PAN,
            aadhaar_number=SYNTHETIC_AADHAAR,
        )
        ids = seed_ids(client, organization, rows)
        client_uuid = ids["client"]
        report_bytes, artifact_bytes = await freeze_basis(session)

        first = await run_migration_executor(
            session,
            source_report_bytes=report_bytes,
            artifact_bytes=artifact_bytes,
            executor_version=EXECUTOR_VERSION,
            dry_run=False,
        )
        assert first.anchors[0].status == "committed"
        committed_ledger_id = first.anchors[0].contents["ledger_entry"]

        live_before = await session.get(Client, client.id)
        assert live_before is not None
        before_version = live_before.version
        before_updated_at = live_before.updated_at

        live_before.notes = "legacy client mutated a time after migration"
        await session.commit()
        await session.refresh(live_before)

        live_after = live_before
        assert (live_after.version, live_after.updated_at) != (before_version, before_updated_at)
        assert live_after.version > before_version

        party = await session.get(Party, client.id)
        assert party is not None
        party_display_before = party.display_name
        party_organization_before = party.organization_id

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

        ledger_rows = list(
            (
                await session.execute(
                    select(ClientPartyMigrationLedger).where(
                        ClientPartyMigrationLedger.legacy_client_id == client_uuid
                    )
                )
            ).scalars()
        )
        assert len(ledger_rows) == 1
        assert str(ledger_rows[0].id) == committed_ledger_id

        party_after = await session.get(Party, client_uuid)
        assert party_after is not None
        assert party_after.display_name == party_display_before
        assert party_after.organization_id == party_organization_before

        legacy = await session.get(Client, client_uuid)
        assert legacy is not None
        assert legacy.full_name == "Test Client"
        assert legacy.address_id == ids["address"]
    finally:
        if ids is not None:
            await cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_committed_ledger_source_fingerprint_matches_live_anchor(
    db_session: AsyncSession,
) -> None:
    organization = await make_org(db_session)
    user = await make_user(db_session, organization)
    client, _rows = await seed_client_graph(db_session, organization=organization, user=user)
    live = await db_session.get(Client, client.id)
    assert live is not None

    result = await apply_anchor_against(db_session, client, organization)
    assert result.status == "applied"

    ledger = (
        await db_session.execute(
            select(ClientPartyMigrationLedger).where(
                ClientPartyMigrationLedger.legacy_client_id == client.id
            )
        )
    ).scalar_one()
    expected = client_source_fingerprint(
        client_id=client.id,
        version=live.version,
        updated_at=live.updated_at,
    )
    assert ledger.source_fingerprint == expected
    assert ledger.source_client_version == live.version
    assert ledger.source_client_updated_at == live.updated_at


def test_two_live_client_versions_produce_different_fingerprints() -> None:
    client_id = uuid4()
    updated_at = datetime(2026, 9, 8, 10, 0, 0, 0, tzinfo=UTC)
    assert client_source_fingerprint(
        client_id=client_id, version=1, updated_at=updated_at
    ) != client_source_fingerprint(client_id=client_id, version=2, updated_at=updated_at)


def test_client_source_fingerprint_timestamp_canonicalization_is_timezone_safe() -> None:
    client_id = uuid4()
    utc_instant = datetime(2026, 9, 8, 10, 0, 0, 0, tzinfo=UTC)
    shifted_instant = datetime(
        2026, 9, 8, 15, 30, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))
    )
    assert utc_instant.timestamp() == shifted_instant.timestamp()
    first = client_source_fingerprint(client_id=client_id, version=1, updated_at=utc_instant)
    second = client_source_fingerprint(client_id=client_id, version=1, updated_at=shifted_instant)
    assert first == second
    assert first == client_source_fingerprint(
        client_id=client_id, version=1, updated_at=utc_instant
    )


async def test_no_party_crud_is_exposed_through_the_api() -> None:
    def route_paths(routes: list) -> list[str]:
        paths: list[str] = []
        for route in routes:
            path = getattr(route, "path", None)
            if isinstance(path, str):
                paths.append(path)
            nested = getattr(route, "routes", None)
            if nested is not None:
                paths.extend(route_paths(list(nested)))
        return paths

    assert not any("parties" in path for path in route_paths(list(api_app.routes)))
