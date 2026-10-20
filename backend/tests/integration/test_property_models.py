"""Schema-level tests for the property models: check constraints and
required FKs.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.property import Property, PropertyOwner


def _property(*, organization_id, **overrides: object) -> Property:
    defaults = {"organization_id": organization_id, "survey_number": "123/A"}
    return Property(**{**defaults, **overrides})


async def _make_property(session: AsyncSession) -> Property:
    organization = Organization(name=f"Org-{uuid4()}")
    session.add(organization)
    await session.flush()
    prop = _property(organization_id=organization.id)
    session.add(prop)
    await session.flush()
    return prop


async def _make_client(session: AsyncSession, organization_id) -> Client:
    client = Client(organization_id=organization_id, full_name="Owner", primary_phone="9876543210")
    session.add(client)
    await session.flush()
    return client


class TestProperty:
    async def test_valid_property_succeeds(self, db_session: AsyncSession) -> None:
        organization = Organization(name=f"Org-{uuid4()}")
        db_session.add(organization)
        await db_session.flush()
        db_session.add(_property(organization_id=organization.id))
        await db_session.flush()

    async def test_property_type_must_be_a_known_value(self, db_session: AsyncSession) -> None:
        db_session.add(_property(organization_id=uuid4(), property_type="not-a-real-type"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_area_value_must_be_positive_when_given(self, db_session: AsyncSession) -> None:
        db_session.add(_property(organization_id=uuid4(), area_value=-5))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_area_value_may_be_omitted(self, db_session: AsyncSession) -> None:
        organization = Organization(name=f"Org-{uuid4()}")
        db_session.add(organization)
        await db_session.flush()
        prop = _property(organization_id=organization.id, area_value=None)
        db_session.add(prop)

        await db_session.flush()

        assert prop.id is not None


class TestPropertyOwner:
    async def test_requires_existing_property_and_client(self, db_session: AsyncSession) -> None:
        db_session.add(
            PropertyOwner(
                property_id=uuid4(),
                client_id=uuid4(),
                ownership_type="owner",
                from_date=date.today(),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_ownership_share_must_be_within_0_to_100(self, db_session: AsyncSession) -> None:
        prop = await _make_property(db_session)
        client = await _make_client(db_session, prop.organization_id)

        db_session.add(
            PropertyOwner(
                organization_id=prop.organization_id,
                property_id=prop.id,
                client_id=client.id,
                ownership_share=150,
                ownership_type="owner",
                from_date=date.today(),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_to_date_cannot_precede_from_date(self, db_session: AsyncSession) -> None:
        prop = await _make_property(db_session)
        client = await _make_client(db_session, prop.organization_id)

        db_session.add(
            PropertyOwner(
                organization_id=prop.organization_id,
                property_id=prop.id,
                client_id=client.id,
                ownership_type="owner",
                from_date=date.today(),
                to_date=date.today() - timedelta(days=1),
            )
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_valid_ownership_record_succeeds(self, db_session: AsyncSession) -> None:
        prop = await _make_property(db_session)
        client = await _make_client(db_session, prop.organization_id)

        db_session.add(
            PropertyOwner(
                organization_id=prop.organization_id,
                property_id=prop.id,
                client_id=client.id,
                ownership_share=50,
                ownership_type="owner",
                from_date=date.today(),
            )
        )

        await db_session.flush()
