"""T118/ADR-0035 step 4: integration tests for the governed Party/Client
migration & backfill executor.

Coverage mirrors the T118 authorization contract:

- deterministic and operator_reconciled executions construct the complete
  write unit (parties row, ADR-0033 Organization staging backfills, bounded
  matter_parties `role = 'client'` rows, T117 `party_id` bridges, and one
  immutable migration-ledger completion row);
- retry/idempotency is ledger-driven (identical replay is a no-op; any
  change of fingerprint, Organization, or basis fails closed);
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

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.cli.client_migration_executor import (
    EXECUTOR_SCHEMA_VERSION,
    TASK,
    apply_anchor,
    run_migration_executor,
)
from app.infrastructure.cli.client_migration_preflight import run_client_migration_preflight
from app.infrastructure.config import get_settings
from app.infrastructure.persistence.models.client import Address, Client, ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment, PaymentMethod
from app.infrastructure.persistence.models.geography import Country
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import (
    ClientPartyMigrationLedger,
    MatterParty,
    Party,
)
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment
from app.main import app as api_app

SCHEMA_VERSION = "t109.party-client-reconciliation.v1"
REPORT_TYPE = "t108.client-migration-preflight.v1"
EXECUTOR_VERSION = "t118.test.v1"
_EMPTY_SHA = "0" * 64
_PAN = "ABCDE1234F"
_AADHAAR = "123456789012"


async def _seed_country(session: AsyncSession) -> Country:
    existing_codes = set((await session.execute(select(Country.iso_code))).scalars())
    iso_code = f"{str(uuid4())[:2].upper()}"
    while iso_code in existing_codes:
        iso_code = f"{str(uuid4())[:2].upper()}"
    country = Country(name=f"Country-{uuid4()}", iso_code=iso_code)
    session.add(country)
    await session.flush()
    return country


async def _seed_lookups(
    session: AsyncSession,
) -> tuple[MatterType, MatterStatus, PaymentMethod]:
    matter_type = MatterType(code=f"MT-{uuid4()}", name="Civil")
    matter_status = MatterStatus(code=f"MS-{uuid4()}", name="Open")
    payment_method = PaymentMethod(code=f"PM-{uuid4()}", name="Cash")
    session.add_all([matter_type, matter_status, payment_method])
    await session.flush()
    return matter_type, matter_status, payment_method


async def _make_org(session: AsyncSession) -> Organization:
    organization = Organization(name=f"Org-{uuid4()}")
    session.add(organization)
    await session.flush()
    return organization


async def _make_user(session: AsyncSession, organization: Organization) -> User:
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Resolver",
        organization_id=organization.id,
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_client_graph(
    session: AsyncSession,
    *,
    organization: Organization | None,
    user: User | None,
    client_type: str = "individual",
    pan_number: str | None = None,
    aadhaar_number: str | None = None,
) -> tuple[Client, dict[str, object]]:
    """Seeds one legacy Client with the full T108 governed dependent graph
    (address, contact, property + owner, matter, client-linked and
    matter-linked appointments, invoice, payment). No row carries an
    Organization or party_id, matching the pre-migration legacy state."""
    country = await _seed_country(session)
    matter_type, matter_status, payment_method = await _seed_lookups(session)
    created_by = None if user is None else user.id

    address = Address(
        line1="123 Main",
        country_id=country.id,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(address)
    await session.flush()

    client = Client(
        client_type=client_type,
        full_name="Test Client",
        primary_phone="9876543210",
        primary_email="client@example.com",
        pan_number=pan_number,
        aadhaar_number=aadhaar_number,
        address_id=address.id,
        notes="legacy client",
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(client)
    await session.flush()

    contact = ClientContact(
        client_id=client.id,
        contact_name="Contact",
        relationship_type="assistant",
        created_by=created_by,
        updated_by=created_by,
    )
    property_row = Property(
        property_type="agricultural",
        survey_number=f"SN-{uuid4()}",
        address_id=address.id,
        created_by=created_by,
        updated_by=created_by,
    )
    session.add_all([contact, property_row])
    await session.flush()

    owner = PropertyOwner(
        property_id=property_row.id,
        client_id=client.id,
        ownership_share=Decimal("100.00"),
        from_date=date(2026, 1, 1),
        created_by=created_by,
        updated_by=created_by,
    )
    matter = Matter(
        matter_number=f"M-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=matter_status.id,
        client_id=client.id,
        property_id=property_row.id,
        title="Matter",
        opened_at=datetime.now(UTC),
        created_by=created_by,
        updated_by=created_by,
    )
    session.add_all([owner, matter])
    await session.flush()

    appointment = Appointment(
        matter_id=matter.id,
        client_id=client.id,
        title="Meeting",
        starts_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
        ends_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        created_by=created_by,
        updated_by=created_by,
    )
    matter_linked = Appointment(
        matter_id=matter.id,
        client_id=None,
        title="Court",
        starts_at=datetime(2026, 1, 3, 9, 0, tzinfo=UTC),
        ends_at=datetime(2026, 1, 3, 10, 0, tzinfo=UTC),
        created_by=created_by,
        updated_by=created_by,
    )
    session.add_all([appointment, matter_linked])
    await session.flush()

    invoice = Invoice(
        invoice_number=f"INV-{uuid4()}",
        matter_id=matter.id,
        client_id=client.id,
        amount=Decimal("100.00"),
        total_amount=Decimal("100.00"),
        issued_at=datetime.now(UTC),
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(invoice)
    await session.flush()

    payment = Payment(
        invoice_id=invoice.id,
        matter_id=matter.id,
        client_id=client.id,
        payment_method_id=payment_method.id,
        amount=Decimal("100.00"),
        paid_at=datetime.now(UTC),
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(payment)
    await session.flush()

    rows = {
        "country": country,
        "matter_type": matter_type,
        "matter_status": matter_status,
        "payment_method": payment_method,
        "address": address,
        "contact": contact,
        "property": property_row,
        "owner": owner,
        "matter": matter,
        "appointment": appointment,
        "matter_linked": matter_linked,
        "invoice": invoice,
        "payment": payment,
    }
    return client, rows


def _make_entry(
    client: Client,
    organization: Organization | None,
    *,
    state: str = "deterministic",
    selected_organization_id: UUID | None = None,
    snapshot: dict[str, object] | None = None,
    set_id: str | None = None,
) -> dict[str, object]:
    if snapshot is None:
        snapshot = {
            "classification": "deterministic",
            "candidate_organization_ids": [str(organization.id)],
            "evidence": [],
            "note": "test snapshot",
        }
    decision: dict[str, object] = {
        "state": state,
        "resolution_basis": "ADR-0033 SS6.2 reconciled evidence",
        "operator_note": "t118 test",
    }
    if state in ("deterministic", "operator_reconciled"):
        decision["selected_organization_id"] = str(
            organization.id if selected_organization_id is None else selected_organization_id
        )
    if state == "operator_reconciled":
        decision["organization_source"] = "existing"
    return {
        "set_id": set_id or f"client-set:{client.id}:testdigest",
        "anchor": {"node_type": "client", "node_id": str(client.id)},
        "t108_snapshot": snapshot,
        "decision": decision,
        "provenance": {
            "entered_at": datetime.now(UTC).isoformat(),
            "entered_by": {"actor_type": "t118-test", "actor_id": "test-operator"},
        },
    }


def _make_artifact(entry: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task": "T109",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": {
            "actor_type": "t118-test-cli",
            "actor_id": "t118-test-operator",
            "display_name": "Test Operator",
        },
        "source_report": {
            "report_type": REPORT_TYPE,
            "report_path": "frozen-t108.json",
            "report_sha256": _EMPTY_SHA,
        },
        "entries": [entry],
    }


async def _apply(
    session: AsyncSession,
    client: Client,
    organization: Organization | None,
    *,
    entry: dict[str, object] | None = None,
    source_report_sha256: str = _EMPTY_SHA,
    executor_version: str = EXECUTOR_VERSION,
):
    if entry is None:
        entry = _make_entry(client, organization)
    return await apply_anchor(
        session,
        anchor_id=str(client.id),
        artifact_payload=_make_artifact(entry),
        entry=entry,
        executor_version=executor_version,
        run_id=uuid4(),
        source_report_sha256=source_report_sha256,
    )


async def _freeze_basis(
    session: AsyncSession, *, overrides: dict[str, dict[str, object]] | None = None
) -> tuple[bytes, bytes]:
    """Builds the frozen T108 report and a mechanically valid T109 artifact
    from the current live graph, so the T110/T111 gates pass by construction.
    `overrides` keyed by client node_id can force a different decision."""
    report = await run_client_migration_preflight(session)
    report_bytes = json.dumps(asdict(report), ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(report_bytes).hexdigest()
    overrides = overrides or {}
    entries: list[dict[str, object]] = []
    for node in report.clients:
        override = overrides.get(node.node_id, {})
        decision: dict[str, object]
        state = str(override.get("state", node.classification))
        if state == "deterministic" or state == "operator_reconciled":
            selected = override.get("selected_organization_id")
            if selected is None:
                selected = node.candidate_organization_ids[0]
            decision = {
                "state": state,
                "resolution_basis": "ADR-0033 SS6.2 reconciled evidence",
                "operator_note": override.get("operator_note", "t118 test"),
                "selected_organization_id": str(selected),
            }
            if state == "operator_reconciled":
                decision["organization_source"] = override.get("organization_source", "existing")
        else:
            decision = {
                "state": state,
                "resolution_basis": "no executable decision",
                "operator_note": "t118 test",
            }
        entries.append(
            {
                "set_id": f"client-set:{node.node_id}:{digest[:12]}",
                "anchor": {"node_type": "client", "node_id": node.node_id},
                "t108_snapshot": {
                    "classification": node.classification,
                    "candidate_organization_ids": list(node.candidate_organization_ids),
                    "evidence": [asdict(item) for item in node.evidence],
                    "note": node.note,
                },
                "decision": decision,
                "provenance": {
                    "entered_at": datetime.now(UTC).isoformat(),
                    "entered_by": {"actor_type": "t118-test", "actor_id": "test-operator"},
                },
            }
        )
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "task": "T109",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": {
            "actor_type": "t118-test-cli",
            "actor_id": "t118-test-operator",
            "display_name": "Test Operator",
        },
        "source_report": {
            "report_type": REPORT_TYPE,
            "report_path": "frozen-t108.json",
            "report_sha256": digest,
        },
        "entries": entries,
    }
    artifact_bytes = json.dumps(artifact, ensure_ascii=False).encode("utf-8")
    return report_bytes, artifact_bytes


def _seed_ids(
    client: Client, organization: Organization, rows: dict[str, object]
) -> dict[str, UUID]:
    return {
        "client": client.id,
        "organization": organization.id,
        "matter": rows["matter"].id,
        "appointment": rows["appointment"].id,
        "matter_linked": rows["matter_linked"].id,
        "property": rows["property"].id,
        "address": rows["address"].id,
        "country": rows["country"].id,
        "matter_type": rows["matter_type"].id,
        "matter_status": rows["matter_status"].id,
        "payment_method": rows["payment_method"].id,
    }


async def _cleanup_committed(session: AsyncSession, ids: dict[str, UUID]) -> None:
    """Deletes a committed migration write-set plus its seeds in FK-safe
    dependency order so the shared dev database stays clean."""
    client_id = ids["client"]
    matter_id = ids["matter"]
    appointment_ids = [ids["appointment"], ids["matter_linked"]]
    rows_to_clear = (
        delete(ClientPartyMigrationLedger).where(
            ClientPartyMigrationLedger.legacy_client_id == client_id
        ),
        delete(MatterParty).where(MatterParty.party_id == client_id),
        delete(Appointment).where(Appointment.client_id == client_id),
        delete(Appointment).where(Appointment.id.in_(appointment_ids)),
        delete(Payment).where(Payment.client_id == client_id),
        delete(Invoice).where(Invoice.client_id == client_id),
        delete(PropertyOwner).where(PropertyOwner.client_id == client_id),
        delete(ClientContact).where(ClientContact.client_id == client_id),
        delete(Matter).where(Matter.id == matter_id),
        delete(Property).where(Property.id == ids["property"]),
        delete(Party).where(Party.id == client_id),
        delete(Client).where(Client.id == client_id),
        delete(Address).where(Address.id == ids["address"]),
        delete(User).where(User.organization_id == ids["organization"]),
        delete(Organization).where(Organization.id == ids["organization"]),
        delete(Country).where(Country.id == ids["country"]),
        delete(MatterType).where(MatterType.id == ids["matter_type"]),
        delete(MatterStatus).where(MatterStatus.id == ids["matter_status"]),
        delete(PaymentMethod).where(PaymentMethod.id == ids["payment_method"]),
    )
    for statement in rows_to_clear:
        await session.execute(statement)


async def _make_isolated_session() -> tuple[AsyncEngine, AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect():
            pass
    except OperationalError:
        await engine.dispose()
        pytest.skip("Postgres is not reachable — start it with `docker compose up -d`.")
        raise
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory()


async def test_deterministic_apply_writes_the_complete_unit(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, rows = await _seed_client_graph(db_session, organization=organization, user=user)

    result = await _apply(db_session, client, organization)

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
    organization = await _make_org(db_session)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=None)

    entry = _make_entry(client, organization, state="operator_reconciled")
    result = await _apply(db_session, client, organization, entry=entry)

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
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=user)

    first = await _apply(db_session, client, organization)
    second = await _apply(db_session, client, organization)

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


async def test_changed_source_fingerprint_rejects_as_basis_collision(
    db_session: AsyncSession,
) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=user)

    first = await _apply(db_session, client, organization)
    altered = _make_entry(
        client,
        organization,
        snapshot={
            "classification": "deterministic",
            "candidate_organization_ids": [str(organization.id)],
            "evidence": [],
            "note": "different frozen note",
        },
    )
    second = await _apply(db_session, client, organization, entry=altered)

    assert first.status == "applied"
    assert second.status == "failed"
    assert second.failure_code == "basis_collision"


async def test_changed_organization_rejects_as_basis_collision(db_session: AsyncSession) -> None:
    organization_a = await _make_org(db_session)
    organization_b = await _make_org(db_session)
    user = await _make_user(db_session, organization_a)
    client, _rows = await _seed_client_graph(db_session, organization=organization_a, user=user)

    first = await _apply(db_session, client, organization_a)
    redirected = _make_entry(client, organization_b, selected_organization_id=organization_b.id)
    second = await _apply(db_session, client, organization_a, entry=redirected)

    assert first.status == "applied"
    assert second.status == "failed"
    assert second.failure_code == "basis_collision"


async def test_changed_reconciliation_basis_rejects(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=user)

    first = await _apply(db_session, client, organization)
    second = await _apply(
        db_session,
        client,
        organization,
        entry=_make_entry(client, organization, set_id="client-set:other:xxxx"),
        source_report_sha256="1" * 64,
    )

    assert first.status == "applied"
    assert second.status == "failed"
    assert second.failure_code == "already_migrated_different_basis"


async def test_missing_anchor_fails_closed(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    result = await _apply(db_session, Client(id=uuid4()), organization)

    assert result.status == "failed"
    assert result.failure_code == "missing_anchor"


async def test_missing_organization_fails_closed(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=user)

    bogus = _make_entry(client, organization, selected_organization_id=uuid4())
    result = await _apply(db_session, client, organization, entry=bogus)

    assert result.status == "failed"
    assert result.failure_code == "organization_not_found"


async def test_party_without_ledger_fails_closed(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=user)
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

    result = await _apply(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "party_exists_without_ledger"


async def test_party_in_other_organization_conflicts(db_session: AsyncSession) -> None:
    organization_a = await _make_org(db_session)
    organization_b = await _make_org(db_session)
    user = await _make_user(db_session, organization_a)
    client, _rows = await _seed_client_graph(db_session, organization=organization_a, user=user)
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

    result = await _apply(db_session, client, organization_a)

    assert result.status == "failed"
    assert result.failure_code == "party_organization_conflict"


async def test_partial_bridge_state_without_ledger_fails_closed(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, rows = await _seed_client_graph(db_session, organization=organization, user=user)
    invoice = await db_session.get(Invoice, rows["invoice"].id)
    assert invoice is not None
    invoice.party_id = uuid4()
    await db_session.flush()

    result = await _apply(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "unproven_partial_state"


async def test_conflicting_matter_party_fails_closed(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, rows = await _seed_client_graph(db_session, organization=organization, user=user)
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

    result = await _apply(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "matter_party_conflict"


async def test_cross_tenant_organization_disagreement_fails_closed(
    db_session: AsyncSession,
) -> None:
    organization_a = await _make_org(db_session)
    organization_b = await _make_org(db_session)
    user = await _make_user(db_session, organization_a)
    client, rows = await _seed_client_graph(db_session, organization=organization_a, user=user)
    appointment = await db_session.get(Appointment, rows["appointment"].id)
    assert appointment is not None
    appointment.organization_id = organization_b.id
    await db_session.flush()

    result = await _apply(db_session, client, organization_a)

    assert result.status == "failed"
    assert result.failure_code == "tenant_disagreement"


async def test_client_address_cross_tenant_fails_closed(db_session: AsyncSession) -> None:
    organization_a = await _make_org(db_session)
    organization_b = await _make_org(db_session)
    user = await _make_user(db_session, organization_a)
    client, rows = await _seed_client_graph(db_session, organization=organization_a, user=user)
    address = await db_session.get(Address, rows["address"].id)
    assert address is not None
    address.organization_id = organization_b.id
    await db_session.flush()

    result = await _apply(db_session, client, organization_a)

    assert result.status == "failed"
    assert result.failure_code == "tenant_disagreement"


async def test_organization_client_with_aadhaar_is_incompatible(db_session: AsyncSession) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(
        db_session,
        organization=organization,
        user=user,
        client_type="organization",
        aadhaar_number=_AADHAAR,
    )

    result = await _apply(db_session, client, organization)

    assert result.status == "failed"
    assert result.failure_code == "incompatible_party_fields"


async def test_dry_run_plans_the_write_set_and_rolls_back_everything(
    db_session: AsyncSession,
) -> None:
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=user)
    client_id = str(client.id)
    report_bytes, artifact_bytes = await _freeze_basis(db_session)

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
    _client, _rows = await _seed_client_graph(db_session, organization=None, user=None)
    report_bytes, artifact_bytes = await _freeze_basis(db_session)

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
    organization = await _make_org(db_session)
    user = await _make_user(db_session, organization)
    client, _rows = await _seed_client_graph(db_session, organization=organization, user=user)
    report_bytes, artifact_bytes = await _freeze_basis(db_session)
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
    organization_a = await _make_org(db_session)
    organization_b = await _make_org(db_session)
    user_a = await _make_user(db_session, organization_a)
    user_b = await _make_user(db_session, organization_b)
    client, _rows = await _seed_client_graph(db_session, organization=organization_a, user=user_a)
    report_bytes, artifact_bytes = await _freeze_basis(db_session)

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
    client, _rows = await _seed_client_graph(db_session, organization=None, user=None)
    report_bytes, artifact_bytes = await _freeze_basis(
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
    engine, session = await _make_isolated_session()
    client: Client | None = None
    organization: Organization | None = None
    ids: dict[str, UUID] | None = None
    try:
        organization = await _make_org(session)
        user = await _make_user(session, organization)
        client, rows = await _seed_client_graph(
            session,
            organization=organization,
            user=user,
            pan_number=_PAN,
            aadhaar_number=_AADHAAR,
        )
        ids = _seed_ids(client, organization, rows)
        report_bytes, artifact_bytes = await _freeze_basis(session)

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
        assert _AADHAAR not in payload
        assert _PAN not in payload

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
            await _cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


async def test_rerun_after_commit_is_append_only_noop() -> None:
    engine, session = await _make_isolated_session()
    client: Client | None = None
    organization: Organization | None = None
    ids: dict[str, UUID] | None = None
    try:
        organization = await _make_org(session)
        user = await _make_user(session, organization)
        client, rows = await _seed_client_graph(session, organization=organization, user=user)
        ids = _seed_ids(client, organization, rows)
        report_bytes, artifact_bytes = await _freeze_basis(session)

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
            await _cleanup_committed(session, ids)
            await session.commit()
        await session.close()
        await engine.dispose()


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
