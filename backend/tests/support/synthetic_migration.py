"""Shared synthetic fixtures and disposable-database helper for the governed
Party/Client migration rehearsal (T119) and the executor suite (T118).

This module is *test support code only*. It composes the public T108 preflight
CLI/core and the T118 migration executor core against synthetic, disposable
data so the rehearsal never touches a shared development database.

Everything that seeds a legacy `clients` graph intentionally uses synthetic
(clearly non-real) identifiers and values: the full name is a fixed string,
PAN/Aadhaar numbers are supplied only for explicit fail-closed scenarios and
never represent a real individual, and all UUIDs are freshly generated.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.cli.client_migration_executor import apply_anchor
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

BACKEND_DIR = Path(__file__).resolve().parents[2]

SCHEMA_VERSION = "t109.party-client-reconciliation.v1"
REPORT_TYPE = "t108.client-migration-preflight.v1"
EXECUTOR_VERSION = "t118.test.v1"
EMPTY_SHA = "0" * 64
# Synthetic only. These are deliberate test stand-ins and are never a real
# person's identifiers.
SYNTHETIC_PAN = "ABCDE1234F"
SYNTHETIC_AADHAAR = "123456789012"


async def seed_country(session: AsyncSession) -> Country:
    existing_codes = set((await session.execute(select(Country.iso_code))).scalars())
    iso_code = f"{str(uuid4())[:2].upper()}"
    while iso_code in existing_codes:
        iso_code = f"{str(uuid4())[:2].upper()}"
    country = Country(name=f"Country-{uuid4()}", iso_code=iso_code)
    session.add(country)
    await session.flush()
    return country


async def seed_lookups(
    session: AsyncSession,
) -> tuple[MatterType, MatterStatus, PaymentMethod]:
    matter_type = MatterType(code=f"MT-{uuid4()}", name="Civil")
    matter_status = MatterStatus(code=f"MS-{uuid4()}", name="Open")
    payment_method = PaymentMethod(code=f"PM-{uuid4()}", name="Cash")
    session.add_all([matter_type, matter_status, payment_method])
    await session.flush()
    return matter_type, matter_status, payment_method


async def make_org(session: AsyncSession) -> Organization:
    organization = Organization(name=f"Org-{uuid4()}")
    session.add(organization)
    await session.flush()
    return organization


async def make_user(session: AsyncSession, organization: Organization) -> User:
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Resolver",
        organization_id=organization.id,
    )
    session.add(user)
    await session.flush()
    return user


async def seed_client_graph(
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
    country = await seed_country(session)
    matter_type, matter_status, payment_method = await seed_lookups(session)
    created_by = None if user is None else user.id

    address = Address(
        line1="123 Synthetic Way",
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
        primary_email="synthetic@example.test",
        pan_number=pan_number,
        aadhaar_number=aadhaar_number,
        address_id=address.id,
        notes="synthetic legacy client",
        created_by=created_by,
        updated_by=created_by,
    )
    session.add(client)
    await session.flush()

    contact = ClientContact(
        client_id=client.id,
        contact_name="Synthetic Contact",
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


def make_entry(
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
            "note": "synthetic snapshot",
        }
    decision: dict[str, object] = {
        "state": state,
        "resolution_basis": "ADR-0033 SS6.2 reconciled evidence",
        "operator_note": "t119 synthetic rehearsal",
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
            "entered_by": {"actor_type": "synthetic", "actor_id": "synthetic-operator"},
        },
    }


def make_artifact(entry: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task": "T109",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": {
            "actor_type": "synthetic-cli",
            "actor_id": "synthetic-operator",
            "display_name": "Synthetic Operator",
        },
        "source_report": {
            "report_type": REPORT_TYPE,
            "report_path": "frozen-t108.json",
            "report_sha256": EMPTY_SHA,
        },
        "entries": [entry],
    }


async def apply_anchor_against(
    session: AsyncSession,
    client: Client,
    organization: Organization | None,
    *,
    entry: dict[str, object] | None = None,
    source_report_sha256: str = EMPTY_SHA,
    executor_version: str = EXECUTOR_VERSION,
):
    if entry is None:
        entry = make_entry(client, organization)
    return await apply_anchor(
        session,
        anchor_id=str(client.id),
        artifact_payload=make_artifact(entry),
        entry=entry,
        executor_version=executor_version,
        run_id=uuid4(),
        source_report_sha256=source_report_sha256,
    )


async def freeze_basis(
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
                "operator_note": override.get("operator_note", "t119 synthetic rehearsal"),
                "selected_organization_id": str(selected),
            }
            if state == "operator_reconciled":
                decision["organization_source"] = override.get("organization_source", "existing")
        else:
            decision = {
                "state": state,
                "resolution_basis": "no executable decision",
                "operator_note": "t119 synthetic rehearsal",
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
                    "entered_by": {"actor_type": "synthetic", "actor_id": "synthetic-operator"},
                },
            }
        )
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "task": "T109",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": {
            "actor_type": "synthetic-cli",
            "actor_id": "synthetic-operator",
            "display_name": "Synthetic Operator",
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


def seed_ids(
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


async def cleanup_committed(session: AsyncSession, ids: dict[str, UUID]) -> None:
    """Deletes a committed migration write-set plus its seeds in FK-safe
    dependency order so a disposable database is left clean for the next run."""
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


async def make_isolated_session() -> tuple[AsyncEngine, AsyncSession]:
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


class InjectedUnitFault(Exception):
    """Controlled test-only fault raised at a precise point inside one
    anchor's transactional write unit."""


class inject_unit_fault_on_ledger_flush:
    """Async context manager that raises :class:`InjectedUnitFault` at the exact
    point where a migration unit's ledger row is about to be flushed -- after
    the Party row has already been written into the open transaction but before
    the unit is committed.

    This is the fault-injection point that proves the executor rolls back the
    *entire* transactional unit (Party, MatterParty, bridges, staging backfills
    and ledger) rather than leaving partial residue. It is implemented with a
    SQLAlchemy session-level `before_flush` listener and is entirely contained
    in test support code; it never modifies the production executor, its
    transactions, or any production boundary, and it never weakens the
    executor's transaction semantics.
    """

    def __init__(self, session: AsyncSession) -> None:
        # SQLAlchemy's async Session drives the underlying sync_session for all
        # flushes/commits; sync event listeners must attach there, not on the
        # AsyncSession proxy.
        self._sync_session = session.sync_session
        self._triggered = False

    async def __aenter__(self) -> None:
        event.listen(self._sync_session, "before_flush", self._before_flush)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        event.remove(self._sync_session, "before_flush", self._before_flush)

    def _before_flush(self, _sess, _flush_ctx, _instances) -> None:
        if self._triggered:
            return
        for obj in _sess.new:
            if isinstance(obj, ClientPartyMigrationLedger):
                self._triggered = True
                raise InjectedUnitFault("injected mid-unit fault before ledger flush")


def _disposable_branch_url(base_url: str, db_name: str) -> str:
    prefix, _, host_part = base_url.partition("@")
    host, _, _name = host_part.rpartition("/")
    return f"{prefix}@{host}/{db_name}"


def _maintenance_url(base_url: str) -> str:
    # Connect to the always-present `postgres` maintenance database on the
    # same host, using the same credentials, to create/drop the disposable DB.
    prefix, _, host_part = base_url.partition("@")
    host, _, _name = host_part.rpartition("/")
    return f"{prefix}@{host}/postgres"


async def _admin_execute(sql: str) -> None:
    engine = create_async_engine(get_settings().database_url, isolation_level="AUTOCOMMIT")
    admin_url = _maintenance_url(get_settings().database_url)
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            await conn.execute(text(sql))
    finally:
        await engine.dispose()


def _run_alembic_upgrade(disposable_url: str, db_name: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = disposable_url
    env["PYTHONPATH"] = str(BACKEND_DIR / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head failed for disposable DB {db_name}:\n"
            f"{proc.stdout}\n{proc.stderr}"
        )


def provision_disposable_database() -> tuple[str, str]:
    """Creates and migrates a dedicated disposable PostgreSQL database,
    returning `(disposable_url, db_name)`. The caller is responsible for
    calling :func:`drop_disposable_database` when done.

    This is the T119 hard guarantee that the committed rehearsal writes to a
    disposable database -- never the shared development database. Migration is
    delegated to a child `alembic upgrade head` process pointed at the
    disposable URL by an environment override, so it cannot touch the shared DB
    regardless of the configured default. Deliberately synchronous so it can be
    driven by a plain pytest fixture without async loop-scope complications.
    """
    base_url = get_settings().database_url
    db_name = f"legal_dms_t119_{uuid4().hex[:12]}"
    disposable_url = _disposable_branch_url(base_url, db_name)

    asyncio.run(_admin_execute(f'CREATE DATABASE "{db_name}"'))
    try:
        _run_alembic_upgrade(disposable_url, db_name)
    except BaseException:
        asyncio.run(_admin_execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
        raise
    return disposable_url, db_name


def drop_disposable_database(db_name: str) -> None:
    """Destroys a disposable database (with `FORCE`, so it works even if a
    connection lingers) and records a confirmation. Safe to call when the
    database does not exist."""
    asyncio.run(_admin_execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))


def sha256_of(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def alembic_current_branch(disposable_url: str) -> str:
    """Returns the Alembic revision the disposable database is currently on
    (evidence that the rehearsal ran at the repository migration head)."""
    env = dict(os.environ)
    env["DATABASE_URL"] = disposable_url
    env["PYTHONPATH"] = str(BACKEND_DIR / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    head = None
    for line in (proc.stdout + proc.stderr).splitlines():
        line = line.strip()
        if line and not line.lower().startswith(("info", "context", "warn")):
            head = line.split()[0]
            break
    if head is None:
        raise RuntimeError(f"could not resolve alembic current for {disposable_url}: {proc.stdout}")
    return head
