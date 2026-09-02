"""T108/ADR-0033: read-only preflight inventory for legacy Client -> Party
migration.

This command never writes to the database. It inspects every legacy Client
anchor plus the authorized dependent graph and classifies Organization
evidence using only ADR-0033 SS6.2's allowed sources:

- reconciled `created_by` / `updated_by` users,
- explicit previously recorded ledger evidence supplied to the command,
- explicit FK-linked records whose Organization was already resolved by the
  same algorithm.

The output is an auditable JSON report for operator review, not a mutation
step. Unmappable or conflicting evidence remains unresolved by design.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session_factory
from app.infrastructure.persistence.models.client import Address, Client, ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment


@dataclass(frozen=True, slots=True)
class LedgerEvidence:
    organization_id: UUID
    fingerprint: str
    migration_version: str


@dataclass(frozen=True, slots=True)
class EvidencePath:
    source_type: str
    source_id: str
    path: str
    organization_id: str


@dataclass(frozen=True, slots=True)
class NodeReport:
    node_type: str
    node_id: str
    classification: str
    candidate_organization_ids: tuple[str, ...]
    evidence: tuple[EvidencePath, ...]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ClientPreflightReport:
    generated_for_client_ids: tuple[str, ...]
    classifications: dict[str, int]
    clients: tuple[NodeReport, ...]
    addresses: tuple[NodeReport, ...]
    properties: tuple[NodeReport, ...]
    property_owners: tuple[NodeReport, ...]
    matters: tuple[NodeReport, ...]
    appointments: tuple[NodeReport, ...]
    invoices: tuple[NodeReport, ...]
    payments: tuple[NodeReport, ...]
    client_contacts: tuple[NodeReport, ...]


def _fingerprint_for_record(record: object) -> str:
    version = getattr(record, "version", None)
    updated_at = getattr(record, "updated_at", None)
    return f"{type(record).__name__}:{record.id}:{version}:{updated_at}"


def _load_ledger(path: Path | None) -> dict[tuple[str, str], LedgerEvidence]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    ledger: dict[tuple[str, str], LedgerEvidence] = {}
    for record in records:
        ledger[(record["node_type"], record["node_id"])] = LedgerEvidence(
            organization_id=UUID(record["organization_id"]),
            fingerprint=record["fingerprint"],
            migration_version=record["migration_version"],
        )
    return ledger


@dataclass(slots=True)
class _ResolvedNode:
    classification: str
    candidates: set[UUID] = field(default_factory=set)
    evidence: list[EvidencePath] = field(default_factory=list)
    note: str | None = None


class _PreflightContext:
    def __init__(self, ledger: dict[tuple[str, str], LedgerEvidence]) -> None:
        self.ledger = ledger
        self.users: dict[UUID, User] = {}
        self.clients: dict[UUID, Client] = {}
        self.addresses: dict[UUID, Address] = {}
        self.properties: dict[UUID, Property] = {}
        self.property_owners: dict[UUID, PropertyOwner] = {}
        self.matters: dict[UUID, Matter] = {}
        self.appointments: dict[UUID, Appointment] = {}
        self.invoices: dict[UUID, Invoice] = {}
        self.payments: dict[UUID, Payment] = {}
        self.client_contacts: dict[UUID, ClientContact] = {}
        self.client_to_contacts: dict[UUID, list[ClientContact]] = {}
        self.client_to_matters: dict[UUID, list[Matter]] = {}
        self.client_to_property_owners: dict[UUID, list[PropertyOwner]] = {}
        self.client_to_appointments: dict[UUID, list[Appointment]] = {}
        self.client_to_invoices: dict[UUID, list[Invoice]] = {}
        self.client_to_payments: dict[UUID, list[Payment]] = {}
        self.client_to_addresses: dict[UUID, list[Address]] = {}
        self.property_to_owners: dict[UUID, list[PropertyOwner]] = {}
        self.property_to_address: dict[UUID, Address] = {}
        self.address_to_properties: dict[UUID, list[Property]] = {}
        self.address_to_clients: dict[UUID, list[Client]] = {}
        self.resolved: dict[tuple[str, UUID], _ResolvedNode] = {}

    async def load(self, session: AsyncSession) -> None:
        self.users = await self._by_id(session, select(User))
        self.clients = await self._by_id(session, select(Client))
        self.addresses = await self._by_id(session, select(Address))
        self.properties = await self._by_id(session, select(Property))
        self.property_owners = await self._by_id(session, select(PropertyOwner))
        self.matters = await self._by_id(session, select(Matter))
        self.appointments = await self._by_id(session, select(Appointment))
        self.invoices = await self._by_id(session, select(Invoice))
        self.payments = await self._by_id(session, select(Payment))
        self.client_contacts = await self._by_id(session, select(ClientContact))

        for contact in self.client_contacts.values():
            self.client_to_contacts.setdefault(contact.client_id, []).append(contact)
        for matter in self.matters.values():
            self.client_to_matters.setdefault(matter.client_id, []).append(matter)
        for owner in self.property_owners.values():
            self.client_to_property_owners.setdefault(owner.client_id, []).append(owner)
            self.property_to_owners.setdefault(owner.property_id, []).append(owner)
        for appointment in self.appointments.values():
            if appointment.client_id is not None:
                self.client_to_appointments.setdefault(appointment.client_id, []).append(
                    appointment
                )
        for invoice in self.invoices.values():
            self.client_to_invoices.setdefault(invoice.client_id, []).append(invoice)
        for payment in self.payments.values():
            self.client_to_payments.setdefault(payment.client_id, []).append(payment)
        for client in self.clients.values():
            if client.address_id is not None and client.address_id in self.addresses:
                address = self.addresses[client.address_id]
                self.client_to_addresses.setdefault(client.id, []).append(address)
                self.address_to_clients.setdefault(address.id, []).append(client)
        for property_row in self.properties.values():
            if property_row.address_id is not None and property_row.address_id in self.addresses:
                address = self.addresses[property_row.address_id]
                self.property_to_address[property_row.id] = address
                self.address_to_properties.setdefault(address.id, []).append(property_row)

    async def _by_id(self, session: AsyncSession, stmt: Select) -> dict[UUID, object]:
        result = await session.execute(stmt)
        return {row.id: row for row in result.scalars().all()}

    def classify_all(self) -> None:
        progress = True
        while progress:
            progress = False
            for node_type, records in (
                ("client", self.clients),
                ("address", self.addresses),
                ("property", self.properties),
                ("property_owner", self.property_owners),
                ("matter", self.matters),
                ("appointment", self.appointments),
                ("invoice", self.invoices),
                ("payment", self.payments),
                ("client_contact", self.client_contacts),
            ):
                for node_id, record in records.items():
                    resolved = self._classify_node(node_type, record)
                    key = (node_type, node_id)
                    if self.resolved.get(key) != resolved:
                        self.resolved[key] = resolved
                        progress = True

    def _classify_node(self, node_type: str, record: object) -> _ResolvedNode:
        evidence = self._evidence_for(node_type, record)
        candidates = {UUID(item.organization_id) for item in evidence}
        note: str | None = None
        if len(candidates) == 1:
            classification = "deterministic"
        elif len(candidates) == 0:
            classification = "unmappable"
            note = "No authoritative ADR-0033 evidence found."
        else:
            classification = "ambiguous"
            note = "Conflicting authoritative evidence found."
        return _ResolvedNode(
            classification=classification, candidates=candidates, evidence=evidence, note=note
        )

    def _evidence_for(self, node_type: str, record: object) -> list[EvidencePath]:
        evidence: list[EvidencePath] = []
        evidence.extend(self._user_evidence(record))
        evidence.extend(self._ledger_evidence(node_type, record))

        if node_type == "client":
            client = record
            for address in self.client_to_addresses.get(client.id, []):
                evidence.extend(
                    self._resolved_node_evidence(
                        "address", address.id, "clients.address_id -> addresses.id"
                    )
                )
            for contact in self.client_to_contacts.get(client.id, []):
                evidence.extend(
                    self._resolved_node_evidence(
                        "client_contact", contact.id, "client_contacts.client_id"
                    )
                )
            for matter in self.client_to_matters.get(client.id, []):
                evidence.extend(
                    self._resolved_node_evidence("matter", matter.id, "matters.client_id")
                )
            for owner in self.client_to_property_owners.get(client.id, []):
                evidence.extend(
                    self._resolved_node_evidence(
                        "property_owner", owner.id, "property_owners.client_id"
                    )
                )
                evidence.extend(
                    self._resolved_node_evidence(
                        "property",
                        owner.property_id,
                        "property_owners.property_id -> properties.id",
                    )
                )
            for appointment in self.client_to_appointments.get(client.id, []):
                evidence.extend(
                    self._resolved_node_evidence(
                        "appointment", appointment.id, "appointments.client_id"
                    )
                )
            for invoice in self.client_to_invoices.get(client.id, []):
                evidence.extend(
                    self._resolved_node_evidence("invoice", invoice.id, "invoices.client_id")
                )
            for payment in self.client_to_payments.get(client.id, []):
                evidence.extend(
                    self._resolved_node_evidence("payment", payment.id, "payments.client_id")
                )

        if node_type == "address":
            address = record
            for client in self.address_to_clients.get(address.id, []):
                evidence.extend(
                    self._resolved_node_evidence(
                        "client", client.id, "clients.address_id -> addresses.id"
                    )
                )
            for property_row in self.address_to_properties.get(address.id, []):
                evidence.extend(
                    self._resolved_node_evidence(
                        "property", property_row.id, "properties.address_id -> addresses.id"
                    )
                )

        if node_type == "property":
            property_row = record
            if property_row.id in self.property_to_address:
                evidence.extend(
                    self._resolved_node_evidence(
                        "address",
                        self.property_to_address[property_row.id].id,
                        "properties.address_id",
                    )
                )
            for owner in self.property_to_owners.get(property_row.id, []):
                evidence.extend(
                    self._resolved_node_evidence(
                        "property_owner", owner.id, "property_owners.property_id"
                    )
                )

        if node_type == "property_owner":
            owner = record
            evidence.extend(
                self._resolved_node_evidence("client", owner.client_id, "property_owners.client_id")
            )
            evidence.extend(
                self._resolved_node_evidence(
                    "property", owner.property_id, "property_owners.property_id"
                )
            )

        if node_type == "matter":
            matter = record
            evidence.extend(
                self._resolved_node_evidence("client", matter.client_id, "matters.client_id")
            )
            if matter.property_id is not None:
                evidence.extend(
                    self._resolved_node_evidence(
                        "property", matter.property_id, "matters.property_id"
                    )
                )

        if node_type == "appointment":
            appointment = record
            if appointment.client_id is not None:
                evidence.extend(
                    self._resolved_node_evidence(
                        "client", appointment.client_id, "appointments.client_id"
                    )
                )
            if appointment.matter_id is not None:
                evidence.extend(
                    self._resolved_node_evidence(
                        "matter", appointment.matter_id, "appointments.matter_id"
                    )
                )

        if node_type == "invoice":
            invoice = record
            evidence.extend(
                self._resolved_node_evidence("client", invoice.client_id, "invoices.client_id")
            )
            evidence.extend(
                self._resolved_node_evidence("matter", invoice.matter_id, "invoices.matter_id")
            )

        if node_type == "payment":
            payment = record
            evidence.extend(
                self._resolved_node_evidence("client", payment.client_id, "payments.client_id")
            )
            evidence.extend(
                self._resolved_node_evidence("matter", payment.matter_id, "payments.matter_id")
            )
            if payment.invoice_id is not None:
                evidence.extend(
                    self._resolved_node_evidence(
                        "invoice", payment.invoice_id, "payments.invoice_id"
                    )
                )

        if node_type == "client_contact":
            contact = record
            evidence.extend(
                self._resolved_node_evidence(
                    "client", contact.client_id, "client_contacts.client_id"
                )
            )

        return evidence

    def _user_evidence(self, record: object) -> list[EvidencePath]:
        evidence: list[EvidencePath] = []
        for field_name in ("created_by", "updated_by"):
            user_id = getattr(record, field_name, None)
            if user_id is None:
                continue
            user = self.users.get(user_id)
            if user is None or user.organization_id is None:
                continue
            evidence.append(
                EvidencePath(
                    source_type="user",
                    source_id=str(user.id),
                    path=f"{type(record).__name__}.{field_name} -> users.organization_id",
                    organization_id=str(user.organization_id),
                )
            )
        return evidence

    def _ledger_evidence(self, node_type: str, record: object) -> list[EvidencePath]:
        ledger = self.ledger.get((node_type, str(record.id)))
        if ledger is None or ledger.fingerprint != _fingerprint_for_record(record):
            return []
        return [
            EvidencePath(
                source_type="ledger",
                source_id=str(record.id),
                path=f"ledger:{ledger.migration_version}",
                organization_id=str(ledger.organization_id),
            )
        ]

    def _resolved_node_evidence(
        self, node_type: str, node_id: UUID, path: str
    ) -> list[EvidencePath]:
        resolved = self.resolved.get((node_type, node_id))
        if resolved is None or resolved.classification != "deterministic":
            return []
        assert len(resolved.candidates) == 1
        return [
            EvidencePath(
                source_type=node_type,
                source_id=str(node_id),
                path=path,
                organization_id=str(next(iter(resolved.candidates))),
            )
        ]

    def build_report(self) -> ClientPreflightReport:
        clients = [self._report_node("client", item) for item in self.clients.values()]
        addresses = [self._report_node("address", item) for item in self.addresses.values()]
        properties = [self._report_node("property", item) for item in self.properties.values()]
        property_owners = [
            self._report_node("property_owner", item) for item in self.property_owners.values()
        ]
        matters = [self._report_node("matter", item) for item in self.matters.values()]
        appointments = [
            self._report_node("appointment", item) for item in self.appointments.values()
        ]
        invoices = [self._report_node("invoice", item) for item in self.invoices.values()]
        payments = [self._report_node("payment", item) for item in self.payments.values()]
        contacts = [
            self._report_node("client_contact", item) for item in self.client_contacts.values()
        ]
        counts = {"deterministic": 0, "ambiguous": 0, "unmappable": 0}
        for report in clients:
            counts[report.classification] += 1
        return ClientPreflightReport(
            generated_for_client_ids=tuple(sorted(report.node_id for report in clients)),
            classifications=counts,
            clients=tuple(clients),
            addresses=tuple(addresses),
            properties=tuple(properties),
            property_owners=tuple(property_owners),
            matters=tuple(matters),
            appointments=tuple(appointments),
            invoices=tuple(invoices),
            payments=tuple(payments),
            client_contacts=tuple(contacts),
        )

    def _report_node(self, node_type: str, record: object) -> NodeReport:
        resolved = self.resolved[(node_type, record.id)]
        return NodeReport(
            node_type=node_type,
            node_id=str(record.id),
            classification=resolved.classification,
            candidate_organization_ids=tuple(sorted(str(item) for item in resolved.candidates)),
            evidence=tuple(resolved.evidence),
            note=resolved.note,
        )


async def run_client_migration_preflight(
    session: AsyncSession, *, ledger_path: Path | None = None
) -> ClientPreflightReport:
    ledger = _load_ledger(ledger_path)
    context = _PreflightContext(ledger)
    await context.load(session)
    context.classify_all()
    return context.build_report()


async def _async_main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        report = await run_client_migration_preflight(session)
        print(json.dumps(asdict(report), indent=2))


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
