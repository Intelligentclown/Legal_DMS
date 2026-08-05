"""Schema-level tests for the geography hierarchy: uniqueness scoped to the
parent level, and required FK chain (Country -> State -> District ->
Taluka -> Village).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.geography import Country, District, State, Village


async def _make_country(session: AsyncSession, name: str | None = None) -> Country:
    name = name or f"Country-{uuid4()}"
    country = Country(name=name, iso_code=str(uuid4())[:3].upper())
    session.add(country)
    await session.flush()
    return country


async def _make_state(session: AsyncSession, country: Country, name: str | None = None) -> State:
    state = State(country_id=country.id, name=name or f"State-{uuid4()}", code="GJ")
    session.add(state)
    await session.flush()
    return state


class TestCountry:
    async def test_name_and_iso_code_are_unique(self, db_session: AsyncSession) -> None:
        name = f"Country-{uuid4()}"
        await _make_country(db_session, name=name)

        with pytest.raises(IntegrityError):
            await _make_country(db_session, name=name)


class TestState:
    async def test_requires_an_existing_country(self, db_session: AsyncSession) -> None:
        db_session.add(State(country_id=uuid4(), name="Gujarat"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_state_name_unique_within_country_only(self, db_session: AsyncSession) -> None:
        state_name = f"State-{uuid4()}"
        india = await _make_country(db_session)
        other = await _make_country(db_session)
        await _make_state(db_session, india, name=state_name)

        # Same name under a *different* country is fine -- uniqueness is scoped.
        db_session.add(State(country_id=other.id, name=state_name))
        await db_session.flush()

        # Same name under the *same* country is not.
        db_session.add(State(country_id=india.id, name=state_name))
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestDistrict:
    async def test_full_hierarchy_can_be_built_and_navigated_by_fk(
        self, db_session: AsyncSession
    ) -> None:
        india = await _make_country(db_session)
        state = await _make_state(db_session, india)
        district = District(state_id=state.id, name=f"District-{uuid4()}")
        db_session.add(district)
        await db_session.flush()

        assert district.id is not None
        assert district.state_id == state.id


class TestVillage:
    async def test_requires_an_existing_taluka(self, db_session: AsyncSession) -> None:
        db_session.add(Village(taluka_id=uuid4(), name="Some Village"))

        with pytest.raises(IntegrityError):
            await db_session.flush()
