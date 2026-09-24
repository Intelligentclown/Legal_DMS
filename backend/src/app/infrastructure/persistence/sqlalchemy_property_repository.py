"""SQLAlchemy Property repository for the bounded T135 application surface."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.property_repository import PropertyRepository
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyPropertyRepository(SqlAlchemyRepository[Property], PropertyRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Property)

    async def get_by_id_in_organization(
        self, property_id: UUID, organization_id: UUID
    ) -> Property | None:
        result = await self._session.execute(
            select(Property).where(
                Property.id == property_id, Property.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Property]:
        result = await self._session.execute(
            select(Property)
            .where(Property.organization_id == organization_id)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_in_organization(self, organization_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Property)
            .where(Property.organization_id == organization_id)
        )
        return result.scalar_one()

    async def list_owners(
        self, property_id: UUID, organization_id: UUID
    ) -> Sequence[PropertyOwner]:
        result = await self._session.execute(
            select(PropertyOwner).where(
                PropertyOwner.property_id == property_id,
                PropertyOwner.organization_id == organization_id,
            )
        )
        return result.scalars().all()

    async def add_with_owners(
        self, property_: Property, owners: Sequence[PropertyOwner]
    ) -> Property:
        # A savepoint makes the aggregate atomic even when the caller catches
        # a database validation failure before the request transaction exits.
        async with self._session.begin_nested():
            self._session.add(property_)
            await self._session.flush()
            self._session.add_all(owners)
            await self._session.flush()
        return property_
