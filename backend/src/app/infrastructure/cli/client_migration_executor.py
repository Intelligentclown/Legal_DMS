"""T118/ADR-0035 step 4: governed, write-capable Party/Client
reconciliation and migration executor.

The executor consumes the exact frozen T108 client-migration-preflight
report together with one T109-governed reconciliation artifact and the
current authoritative database state. It never writes anything unless every
gate passes:

- the T110 artifact validation is `valid` and `executable`;
- the T111 live reconciliation/staleness preflight is `valid`/`executable`
  (the frozen basis is still identical to the current legacy graph); and
- every Organization selected by an executable decision exists.

The default mode is a dry-run rehearsal: the full write set is applied and
flushed inside the transaction and then rolled back, so an operator can see
exactly what would be committed without persisting anything. Writes happen
only with an explicit `--write` flag, and one committed migration unit is
exactly one legacy `clients` anchor: the `parties` row, the ADR-0033
unambiguous `organization_id` staging backfills, the bounded
`matter_parties` rows (`role = 'client'`), the T117 direct `party_id`
bridge backfills, and one immutable `client_party_migration_ledger`
completion row -- all committed or all rolled back together (ADR-0020).

Idempotency and retry safety are ledger-driven: a retry that finds an
identical previously committed ledger entry (same basis, same Organization,
same source fingerprint) is a true no-op; any meaningful difference fails
closed without overwriting, heuristically repairing, or deleting anything.

`run_migration_executor()` is the testable core (per-anchor transactions;
the caller never commits -- it commits/rolls back each unit itself).
`apply_anchor()` applies one anchor's full write set and only flushes so a
unit can be inspected and rolled back as a single rehearsal or batch.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cli.client_reconciliation_artifact_validator import (
    ValidationIssue,
    canonical_json,
)
from app.infrastructure.cli.client_reconciliation_staleness_preflight import (
    run_live_reconciliation_staleness_preflight,
)
from app.infrastructure.database.session import get_session_factory
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

EXECUTOR_SCHEMA_VERSION = "t118.client-migration-executor.v1"
TASK = "T118"
EXECUTABLE_STATES = {"deterministic", "operator_reconciled"}


@dataclass(frozen=True, slots=True)
class AnchorExecutionResult:
    anchor_id: str
    set_id: str
    resolution_mode: str
    status: str
    failure_code: str | None = None
    failure_message: str | None = None
    contents: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class MigrationExecutionResult:
    schema_version: str
    task: str
    run_id: str
    executor_version: str
    dry_run: bool
    source_report_sha256: str
    gated: bool
    gating_issues: tuple[ValidationIssue, ...] = ()
    anchors: tuple[AnchorExecutionResult, ...] = ()
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task": self.task,
            "run_id": self.run_id,
            "executor_version": self.executor_version,
            "dry_run": self.dry_run,
            "source_report_sha256": self.source_report_sha256,
            "gated": self.gated,
            "gating_issues": [asdict(issue) for issue in self.gating_issues],
            "anchors": [asdict(anchor) for anchor in self.anchors],
            "summary": dict(self.summary),
        }


def _failed(
    anchor_id: str, set_id: str, mode: str, code: str, message: str
) -> AnchorExecutionResult:
    return AnchorExecutionResult(
        anchor_id=anchor_id,
        set_id=set_id,
        resolution_mode=mode,
        status="failed",
        failure_code=code,
        failure_message=message,
    )


def _read_frozen_documents(
    source_report_bytes: bytes, artifact_bytes: bytes
) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(source_report_bytes.decode("utf-8")),
        json.loads(artifact_bytes.decode("utf-8")),
    )


async def _collect_anchor_related(
    session: AsyncSession, client_uuid: UUID
) -> dict[str, list[object]]:
    """Returns the anchor's governed dependent rows, ordered and filtered
    exactly as the T108 preflight inventories them."""
    matters = list(
        (await session.execute(select(Matter).where(Matter.client_id == client_uuid))).scalars()
    )
    owners = list(
        (
            await session.execute(
                select(PropertyOwner).where(PropertyOwner.client_id == client_uuid)
            )
        ).scalars()
    )
    appointments = list(
        (
            await session.execute(
                select(Appointment).where(
                    and_(
                        Appointment.client_id.is_not(None),
                        Appointment.client_id == client_uuid,
                    )
                )
            )
        ).scalars()
    )
    invoices = list(
        (await session.execute(select(Invoice).where(Invoice.client_id == client_uuid))).scalars()
    )
    payments = list(
        (await session.execute(select(Payment).where(Payment.client_id == client_uuid))).scalars()
    )
    contacts = list(
        (
            await session.execute(
                select(ClientContact).where(ClientContact.client_id == client_uuid)
            )
        ).scalars()
    )
    matter_ids = [matter.id for matter in matters]
    matter_linked_appointments: list[Appointment] = []
    if matter_ids:
        matter_linked_appointments = list(
            (
                await session.execute(
                    select(Appointment).where(
                        and_(
                            Appointment.client_id.is_(None),
                            Appointment.matter_id.in_(matter_ids),
                        )
                    )
                )
            ).scalars()
        )
    return {
        "matters": matters,
        "owners": owners,
        "appointments": appointments,
        "matter_linked_appointments": matter_linked_appointments,
        "invoices": invoices,
        "payments": payments,
        "contacts": contacts,
    }


async def _load_property_chain(
    session: AsyncSession,
    owners: list[PropertyOwner],
    *,
    organization_id: UUID,
    tenant_violation: list[str],
) -> tuple[dict[UUID, Property], list[Address]]:
    """Loads each owner's Property and reaches its Address, applying the
    fail-closed tenant checks before anything is written."""
    properties: dict[UUID, Property] = {}
    addresses: list[Address] = []
    seen_addresses: set[UUID] = set()
    for owner in owners:
        property_row = await session.get(Property, owner.property_id)
        if property_row is None:
            continue
        properties[property_row.id] = property_row
        if (
            property_row.organization_id is not None
            and property_row.organization_id != organization_id
        ):
            tenant_violation.append(f"property {property_row.id} belongs to another Organization")
        if property_row.address_id is None or property_row.address_id in seen_addresses:
            continue
        seen_addresses.add(property_row.address_id)
        address = await session.get(Address, property_row.address_id)
        if address is None:
            continue
        addresses.append(address)
        if address.organization_id is not None and address.organization_id != organization_id:
            tenant_violation.append(
                f"property address {address.id} belongs to another Organization"
            )
    return properties, addresses


async def apply_anchor(
    session: AsyncSession,
    *,
    anchor_id: str,
    artifact_payload: dict[str, Any],
    entry: dict[str, Any],
    executor_version: str,
    run_id: UUID,
    source_report_sha256: str,
) -> AnchorExecutionResult:
    """Applies one legacy Client anchor's complete migration unit and
    flushes it, so the caller can inspect, commit, or roll it back as one
    atom. All fail-closed checks run before anything is added.

    Never updates or deletes `clients`, any `client_id` column, or any
    pre-existing migration row; never overwrites a resolved conflicting
    Organization; never infers Organization from names, geography, dates, or
    a single-Organization assumption; and never emits legacy PII values.
    """
    client_uuid = UUID(anchor_id)
    set_id = entry["set_id"]
    decision = entry["decision"]
    state = decision["state"]
    snapshot = entry["t108_snapshot"]
    fingerprint = hashlib.sha256(canonical_json(snapshot).encode("utf-8")).hexdigest()
    organization_id = UUID(decision["selected_organization_id"])
    operator_note = decision.get("operator_note") or None

    client = await session.get(Client, client_uuid)
    if client is None:
        return _failed(anchor_id, set_id, state, "missing_anchor", "legacy Client no longer exists")
    if await session.get(Organization, organization_id) is None:
        return _failed(
            anchor_id,
            set_id,
            state,
            "organization_not_found",
            "selected Organization does not exist",
        )

    stored = list(
        (
            await session.execute(
                select(ClientPartyMigrationLedger).where(
                    ClientPartyMigrationLedger.legacy_client_id == client_uuid
                )
            )
        ).scalars()
    )
    for ledger in stored:
        same_basis = (
            ledger.executor_version == executor_version
            and ledger.reconciliation_set_id == set_id
            and ledger.source_report_sha256 == source_report_sha256
        )
        if not same_basis:
            continue
        if ledger.organization_id == organization_id and ledger.source_fingerprint == fingerprint:
            return AnchorExecutionResult(
                anchor_id=anchor_id,
                set_id=set_id,
                resolution_mode=state,
                status="already_completed",
                contents={
                    "party_id": str(ledger.party_id),
                    "organization_id": str(ledger.organization_id),
                    "ledger_entry": str(ledger.id),
                },
            )
        return _failed(
            anchor_id,
            set_id,
            state,
            "basis_collision",
            "same reconciliation basis is already completed with a different "
            f"Organization or source fingerprint (ledger {ledger.id})",
        )
    if stored:
        return _failed(
            anchor_id,
            set_id,
            state,
            "already_migrated_different_basis",
            f"anchor already has a migration-ledger completion under a "
            f"different basis (ledger {stored[0].id})",
        )

    if await session.get(Party, client_uuid) is not None:
        existing_party = await session.get(Party, client_uuid)
        assert existing_party is not None
        if existing_party.organization_id != organization_id:
            return _failed(
                anchor_id,
                set_id,
                state,
                "party_organization_conflict",
                "a Party row already exists for this legacy Client in another Organization",
            )
        return _failed(
            anchor_id,
            set_id,
            state,
            "party_exists_without_ledger",
            "a Party row already exists for this legacy Client with no matching ledger completion",
        )

    related = await _collect_anchor_related(session, client_uuid)
    violations: list[str] = []

    client_address: Address | None = None
    if client.address_id is not None:
        client_address = await session.get(Address, client.address_id)
        if (
            client_address is not None
            and client_address.organization_id is not None
            and client_address.organization_id != organization_id
        ):
            violations.append(f"client address {client_address.id} belongs to another Organization")

    for label, rows in (
        ("matter", related["matters"]),
        ("property_owner", related["owners"]),
        ("appointment", related["appointments"] + related["matter_linked_appointments"]),
        ("invoice", related["invoices"]),
        ("payment", related["payments"]),
        ("client_contact", related["contacts"]),
    ):
        for row in rows:
            if row.organization_id is not None and row.organization_id != organization_id:
                violations.append(f"{label} {row.id} belongs to another Organization")

    for label, rows in (
        ("property_owner", related["owners"]),
        ("appointment", related["appointments"]),
        ("invoice", related["invoices"]),
        ("payment", related["payments"]),
        ("client_contact", related["contacts"]),
    ):
        for row in rows:
            if row.party_id is not None:
                violations.append(
                    f"{label} {row.id} already carries a party_id without a ledger completion"
                )

    for matter in related["matters"]:
        matter_parties = list(
            (
                await session.execute(
                    select(MatterParty).where(
                        and_(
                            MatterParty.matter_id == matter.id,
                            MatterParty.role == "client",
                        )
                    )
                )
            ).scalars()
        )
        for matter_party in matter_parties:
            if matter_party.party_id == client_uuid:
                violations.append(
                    f"matter {matter.id} already has a client MatterParty "
                    "without a ledger completion"
                )
            else:
                violations.append(f"matter {matter.id} already has a different party as its client")

    properties: dict[UUID, Property] = {}
    property_addresses: list[Address] = []
    if related["owners"]:
        properties, property_addresses = await _load_property_chain(
            session,
            related["owners"],
            organization_id=organization_id,
            tenant_violation=violations,
        )

    if violations:
        return _failed(
            anchor_id,
            set_id,
            state,
            (
                "unproven_partial_state"
                if any("party_id" in v for v in violations)
                else (
                    "tenant_disagreement"
                    if any("another Organization" in v for v in violations)
                    else "matter_party_conflict"
                )
            ),
            "; ".join(sorted(set(violations))),
        )

    if client.client_type == "organization" and client.aadhaar_number is not None:
        return _failed(
            anchor_id,
            set_id,
            state,
            "incompatible_party_fields",
            "an organization-typed Client carrying an Aadhaar cannot be represented "
            "by the Party schema",
        )

    party = Party(
        id=client_uuid,
        organization_id=organization_id,
        party_type=client.client_type,
        display_name=client.full_name,
        primary_phone=client.primary_phone,
        primary_email=client.primary_email,
        notes=client.notes,
        pan_number=client.pan_number,
        aadhaar_number=client.aadhaar_number,
    )
    session.add(party)
    await session.flush()

    def backfill_organization(row: object) -> None:
        if row.organization_id is None:
            row.organization_id = organization_id

    def bridge(row: object) -> None:
        backfill_organization(row)
        row.party_id = client_uuid

    if client_address is not None:
        backfill_organization(client_address)
    for matter in related["matters"]:
        backfill_organization(matter)
        session.add(
            MatterParty(
                organization_id=organization_id,
                matter_id=matter.id,
                party_id=client_uuid,
                role="client",
            )
        )
    for owner in related["owners"]:
        bridge(owner)
    for property_row in properties.values():
        backfill_organization(property_row)
    for address in property_addresses:
        backfill_organization(address)
    for appointment in related["appointments"]:
        bridge(appointment)
    for appointment in related["matter_linked_appointments"]:
        backfill_organization(appointment)
    for invoice in related["invoices"]:
        bridge(invoice)
    for payment in related["payments"]:
        bridge(payment)
    for contact in related["contacts"]:
        bridge(contact)

    ledger = ClientPartyMigrationLedger(
        legacy_client_id=client_uuid,
        party_id=client_uuid,
        organization_id=organization_id,
        executor_version=executor_version,
        reconciliation_set_id=set_id,
        source_report_sha256=source_report_sha256,
        resolution_mode=state,
        source_client_version=client.version,
        source_client_updated_at=client.updated_at,
        source_fingerprint=fingerprint,
        artifact_actor_type=artifact_payload["generated_by"].get("actor_type"),
        artifact_actor_id=artifact_payload["generated_by"].get("actor_id"),
        operator_note=operator_note,
        execution_run_id=run_id,
    )
    session.add(ledger)
    await session.flush()

    addresses_backfilled = [client_address] if client_address is not None else []
    addresses_backfilled.extend(property_addresses)
    return AnchorExecutionResult(
        anchor_id=anchor_id,
        set_id=set_id,
        resolution_mode=state,
        status="applied",
        contents={
            "party_id": str(client_uuid),
            "organization_id": str(organization_id),
            "addresses_backfilled": len({a.id for a in addresses_backfilled if a is not None}),
            "matters_backfilled": len(related["matters"]),
            "matter_parties_created": len(related["matters"]),
            "property_owners_bridged": len(related["owners"]),
            "properties_backfilled": len(properties),
            "property_addresses_backfilled": len({a.id for a in property_addresses}),
            "appointments_bridged": len(related["appointments"]),
            "matter_linked_appointments_staged": len(related["matter_linked_appointments"]),
            "invoices_bridged": len(related["invoices"]),
            "payments_bridged": len(related["payments"]),
            "client_contacts_bridged": len(related["contacts"]),
            "ledger_entry": str(ledger.id),
        },
    )


async def run_migration_executor(
    session: AsyncSession,
    *,
    source_report_bytes: bytes,
    artifact_bytes: bytes,
    executor_version: str,
    dry_run: bool = True,
) -> MigrationExecutionResult:
    """Gates T110/T111 plus Organization existence, then executes each
    executable anchor as its own committed unit (or as a rolled-back
    rehearsal in dry-run mode)."""
    source_report_sha256 = hashlib.sha256(source_report_bytes).hexdigest()
    run_id = uuid4()

    staleness = await run_live_reconciliation_staleness_preflight(
        session,
        source_report_bytes=source_report_bytes,
        artifact_bytes=artifact_bytes,
    )
    if not (staleness.valid and staleness.executable):
        gating_issues = list(staleness.issues)
        for anchor in staleness.anchors:
            gating_issues.extend(anchor.issues)
        summary = {
            "total": 0,
            "committed_or_planned": 0,
            "already_completed": 0,
            "failed": 0,
            "gated": 0,
        }
        return MigrationExecutionResult(
            schema_version=EXECUTOR_SCHEMA_VERSION,
            task=TASK,
            run_id=str(run_id),
            executor_version=executor_version,
            dry_run=dry_run,
            source_report_sha256=source_report_sha256,
            gated=True,
            gating_issues=tuple(gating_issues),
            summary=summary,
        )

    report_payload, artifact_payload = _read_frozen_documents(source_report_bytes, artifact_bytes)
    del report_payload
    entries = sorted(artifact_payload["entries"], key=lambda item: item["anchor"]["node_id"])

    anchors: list[AnchorExecutionResult] = []
    for entry in entries:
        anchor_id = entry["anchor"]["node_id"]
        set_id = entry["set_id"]
        state = entry["decision"]["state"]
        if state not in EXECUTABLE_STATES:
            anchors.append(
                AnchorExecutionResult(
                    anchor_id=anchor_id,
                    set_id=set_id,
                    resolution_mode=state,
                    status="gated",
                    failure_code="non_executable_decision",
                    failure_message="artifact decision is not executable",
                )
            )
            continue
        try:
            applied = await apply_anchor(
                session,
                anchor_id=anchor_id,
                artifact_payload=artifact_payload,
                entry=entry,
                executor_version=executor_version,
                run_id=run_id,
                source_report_sha256=source_report_sha256,
            )
        except Exception as error:  # pragma: no cover - defensive
            applied = _failed(
                anchor_id,
                set_id,
                state,
                "execution_error",
                f"{type(error).__name__}: {error}",
            )
        if applied.status == "failed":
            await session.rollback()
            anchors.append(applied)
            break
        if applied.status == "already_completed":
            anchors.append(applied)
            continue
        applied_status = "planned" if dry_run else "committed"
        anchors.append(
            AnchorExecutionResult(
                anchor_id=anchor_id,
                set_id=set_id,
                resolution_mode=state,
                status=applied_status,
                contents=applied.contents,
            )
        )
        if not dry_run:
            await session.commit()

    if dry_run:
        await session.rollback()

    summary = {
        "total": len(anchors),
        "committed_or_planned": sum(
            1 for anchor in anchors if anchor.status in ("committed", "planned")
        ),
        "already_completed": sum(1 for anchor in anchors if anchor.status == "already_completed"),
        "failed": sum(1 for anchor in anchors if anchor.status == "failed"),
        "gated": sum(1 for anchor in anchors if anchor.status == "gated"),
    }
    return MigrationExecutionResult(
        schema_version=EXECUTOR_SCHEMA_VERSION,
        task=TASK,
        run_id=str(run_id),
        executor_version=executor_version,
        dry_run=dry_run,
        source_report_sha256=source_report_sha256,
        gated=False,
        anchors=tuple(anchors),
        summary=summary,
    )


async def _async_main(
    source_report: Path, artifact: Path, executor_version: str, write: bool
) -> int:
    async with get_session_factory()() as session:
        result = await run_migration_executor(
            session,
            source_report_bytes=source_report.read_bytes(),
            artifact_bytes=artifact.read_bytes(),
            executor_version=executor_version,
            dry_run=not write,
        )
    print(json.dumps(result.to_dict(), indent=2))
    if result.gated:
        return 1
    if any(anchor.status == "failed" for anchor in result.anchors):
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="T118: governed Party/Client reconciliation & backfill executor"
    )
    parser.add_argument(
        "source_report", type=Path, help="frozen T108 client-migration-preflight JSON"
    )
    parser.add_argument("artifact", type=Path, help="T109-governed reconciliation artifact JSON")
    parser.add_argument(
        "--executor-version", required=True, help="explicit executor version recorded in the ledger"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="commit migration units (default is a dry-run rehearsal that writes nothing)",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            _async_main(args.source_report, args.artifact, args.executor_version, args.write)
        )
    )


if __name__ == "__main__":
    main()
