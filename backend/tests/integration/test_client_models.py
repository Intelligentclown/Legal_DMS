"""Schema-level tests for the client models: check constraints, required
FKs, and (for `Client`, which opts into `OptimisticLockMixin`) that
concurrent updates are actually detected.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm.exc import StaleDataError

from app.infrastructure.config import get_settings
from app.infrastructure.persistence.models.client import Address, Client, ClientContact
from app.infrastructure.persistence.models.geography import Country


async def _make_country(session: AsyncSession) -> Country:
    country = Country(name=f"Country-{uuid4()}", iso_code="XX")
    session.add(country)
    await session.flush()
    return country


def _client(**overrides: object) -> Client:
    defaults = {"full_name": "Jane Doe", "primary_phone": "9876543210"}
    return Client(**{**defaults, **overrides})


class TestAddress:
    async def test_requires_a_country(self, db_session: AsyncSession) -> None:
        db_session.add(Address(line1="123 Main St", country_id=uuid4()))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_address_type_must_be_a_known_value(self, db_session: AsyncSession) -> None:
        country = await _make_country(db_session)
        db_session.add(
            Address(line1="123 Main St", country_id=country.id, address_type="not-a-real-type")
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_partial_granularity_is_allowed(self, db_session: AsyncSession) -> None:
        country = await _make_country(db_session)
        address = Address(line1="PO Box 1", country_id=country.id, address_type="mailing")
        db_session.add(address)

        await db_session.flush()  # no village/taluka/district/state -- should be fine

        assert address.id is not None


class TestClient:
    async def test_valid_client_succeeds(self, db_session: AsyncSession) -> None:
        db_session.add(_client())
        await db_session.flush()

    async def test_client_type_must_be_a_known_value(self, db_session: AsyncSession) -> None:
        db_session.add(_client(client_type="not-a-real-type"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_primary_phone_too_short_is_rejected(self, db_session: AsyncSession) -> None:
        db_session.add(_client(primary_phone="123"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.parametrize("pan", ["ABCDE1234F", "abcde1234f", "12345", "ABCDE12345"])
    async def test_pan_number_format(self, db_session: AsyncSession, pan: str) -> None:
        db_session.add(_client(pan_number=pan))

        if pan == "ABCDE1234F":
            await db_session.flush()  # valid format, should not raise
        else:
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_aadhaar_number_must_be_12_digits(self, db_session: AsyncSession) -> None:
        db_session.add(_client(aadhaar_number="12345"))

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestClientContact:
    async def test_requires_an_existing_client(self, db_session: AsyncSession) -> None:
        db_session.add(
            ClientContact(client_id=uuid4(), contact_name="Rep", relationship_type="self")
        )

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestClientOptimisticLocking:
    async def test_concurrent_update_raises_stale_data_error(self) -> None:
        engine = create_async_engine(get_settings().database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        try:
            async with session_factory() as setup_session:
                client = _client(full_name="Version Test")
                setup_session.add(client)
                await setup_session.commit()
                client_id = client.id

            async with session_factory() as session_a, session_factory() as session_b:
                client_a = await session_a.get(Client, client_id)
                client_b = await session_b.get(Client, client_id)
                assert client_a is not None
                assert client_b is not None

                client_a.full_name = "Updated by A"
                await session_a.commit()

                client_b.full_name = "Updated by B"
                with pytest.raises(StaleDataError):
                    await session_b.commit()
        finally:
            async with session_factory() as cleanup_session:
                stale = await cleanup_session.get(Client, client_id)
                if stale is not None:
                    await cleanup_session.delete(stale)
                    await cleanup_session.commit()
            await engine.dispose()
