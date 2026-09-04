from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cli.client_migration_preflight import run_client_migration_preflight
from app.infrastructure.persistence.models.client import Address, Client, ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment, PaymentMethod
from app.infrastructure.persistence.models.geography import Country
from app.infrastructure.persistence.models.identity import User
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment


async def _make_country(session: AsyncSession) -> Country:
    existing_codes = set((await session.execute(select(Country.iso_code))).scalars())
    iso_code = f"{str(uuid4())[:2].upper()}"
    while iso_code in existing_codes:
        iso_code = f"{str(uuid4())[:2].upper()}"
    country = Country(name=f"Country-{uuid4()}", iso_code=iso_code)
    session.add(country)
    await session.flush()
    return country


async def _make_org_user(session: AsyncSession, organization: Organization) -> User:
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Resolver",
        organization_id=organization.id,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_reference_rows(
    session: AsyncSession,
) -> tuple[MatterType, MatterStatus, PaymentMethod]:
    matter_type = MatterType(code=f"MT-{uuid4()}", name="Civil")
    matter_status = MatterStatus(code=f"MS-{uuid4()}", name="Open")
    payment_method = PaymentMethod(code=f"PM-{uuid4()}", name="Cash")
    session.add_all([matter_type, matter_status, payment_method])
    await session.flush()
    return matter_type, matter_status, payment_method


async def _make_client_graph(
    session: AsyncSession,
    *,
    client_user: User | None,
    address_user: User | None = None,
    property_user: User | None = None,
    invoice_user: User | None = None,
    payment_user: User | None = None,
) -> Client:
    country = await _make_country(session)
    matter_type, matter_status, payment_method = await _make_reference_rows(session)
    address = Address(
        line1="123 Main",
        country_id=country.id,
        created_by=None if address_user is None else address_user.id,
        updated_by=None if address_user is None else address_user.id,
    )
    session.add(address)
    await session.flush()

    client = Client(
        full_name="Client",
        primary_phone="9876543210",
        address_id=address.id,
        created_by=None if client_user is None else client_user.id,
        updated_by=None if client_user is None else client_user.id,
    )
    session.add(client)
    await session.flush()

    contact = ClientContact(
        client_id=client.id,
        contact_name="Contact",
        relationship_type="assistant",
        created_by=None if client_user is None else client_user.id,
        updated_by=None if client_user is None else client_user.id,
    )
    property_row = Property(
        property_type="agricultural",
        survey_number=f"SN-{uuid4()}",
        address_id=address.id,
        created_by=None if property_user is None else property_user.id,
        updated_by=None if property_user is None else property_user.id,
    )
    session.add_all([contact, property_row])
    await session.flush()

    owner = PropertyOwner(
        property_id=property_row.id,
        client_id=client.id,
        ownership_share=Decimal("100.00"),
        from_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        created_by=None if property_user is None else property_user.id,
        updated_by=None if property_user is None else property_user.id,
    )
    matter = Matter(
        matter_number=f"M-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=matter_status.id,
        client_id=client.id,
        property_id=property_row.id,
        title="Matter",
        opened_at=datetime.now(UTC),
        created_by=None if client_user is None else client_user.id,
        updated_by=None if client_user is None else client_user.id,
    )
    appointment = Appointment(
        matter_id=matter.id,
        client_id=client.id,
        title="Meeting",
        starts_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
        ends_at=datetime(2026, 1, 2, 10, 0, tzinfo=UTC),
        created_by=None if client_user is None else client_user.id,
        updated_by=None if client_user is None else client_user.id,
    )
    session.add_all([owner, matter, appointment])
    await session.flush()

    invoice = Invoice(
        invoice_number=f"INV-{uuid4()}",
        matter_id=matter.id,
        client_id=client.id,
        amount=Decimal("100.00"),
        total_amount=Decimal("100.00"),
        issued_at=datetime.now(UTC),
        created_by=None if invoice_user is None else invoice_user.id,
        updated_by=None if invoice_user is None else invoice_user.id,
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
        created_by=None if payment_user is None else payment_user.id,
        updated_by=None if payment_user is None else payment_user.id,
    )
    session.add(payment)
    await session.flush()
    return client


def _client_result(report, client_id: str):
    return next(item for item in report.clients if item.node_id == client_id)


def _address_result(report, address_id: str):
    return next(item for item in report.addresses if item.node_id == address_id)


@pytest.mark.asyncio
class TestClientMigrationPreflight:
    async def test_deterministic_client_and_graph_from_allowed_evidence(
        self, db_session: AsyncSession
    ) -> None:
        organization = Organization(name=f"Org-{uuid4()}")
        db_session.add(organization)
        await db_session.flush()
        user = await _make_org_user(db_session, organization)
        client = await _make_client_graph(
            db_session,
            client_user=user,
            address_user=user,
            property_user=user,
            invoice_user=user,
            payment_user=user,
        )

        report = await run_client_migration_preflight(db_session)
        client_report = _client_result(report, str(client.id))

        assert client_report.classification == "deterministic"
        assert client_report.candidate_organization_ids == (str(organization.id),)
        assert report.classifications["deterministic"] >= 1

    async def test_zero_evidence_is_unmappable(self, db_session: AsyncSession) -> None:
        client = await _make_client_graph(
            db_session,
            client_user=None,
            address_user=None,
            property_user=None,
            invoice_user=None,
            payment_user=None,
        )

        report = await run_client_migration_preflight(db_session)
        client_report = _client_result(report, str(client.id))

        assert client_report.classification == "unmappable"
        assert client_report.candidate_organization_ids == ()

    async def test_conflicting_evidence_is_ambiguous(self, db_session: AsyncSession) -> None:
        org_a = Organization(name=f"OrgA-{uuid4()}")
        org_b = Organization(name=f"OrgB-{uuid4()}")
        db_session.add_all([org_a, org_b])
        await db_session.flush()
        user_a = await _make_org_user(db_session, org_a)
        user_b = await _make_org_user(db_session, org_b)
        client = await _make_client_graph(
            db_session,
            client_user=user_a,
            address_user=user_a,
            property_user=user_b,
            invoice_user=user_b,
            payment_user=user_b,
        )

        report = await run_client_migration_preflight(db_session)
        client_report = _client_result(report, str(client.id))

        assert client_report.classification == "ambiguous"
        assert set(client_report.candidate_organization_ids) == {str(org_a.id), str(org_b.id)}

    async def test_cross_tenant_address_is_ambiguous(self, db_session: AsyncSession) -> None:
        org_a = Organization(name=f"OrgA-{uuid4()}")
        org_b = Organization(name=f"OrgB-{uuid4()}")
        db_session.add_all([org_a, org_b])
        await db_session.flush()
        user_a = await _make_org_user(db_session, org_a)
        user_b = await _make_org_user(db_session, org_b)
        client_a = await _make_client_graph(
            db_session,
            client_user=user_a,
            address_user=None,
            property_user=user_a,
            invoice_user=user_a,
            payment_user=user_a,
        )
        client_b = await _make_client_graph(
            db_session,
            client_user=user_b,
            address_user=None,
            property_user=user_b,
            invoice_user=user_b,
            payment_user=user_b,
        )
        shared_address_id = client_a.address_id
        assert shared_address_id is not None
        client_b.address_id = shared_address_id
        await db_session.flush()

        report = await run_client_migration_preflight(db_session)
        address_report = _address_result(report, str(shared_address_id))

        assert address_report.classification == "ambiguous"
        assert set(address_report.candidate_organization_ids) == {str(org_a.id), str(org_b.id)}
