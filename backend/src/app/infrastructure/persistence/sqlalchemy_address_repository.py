"""SQLAlchemy implementation of `AddressRepository` (T130) —
`SqlAlchemyRepository[Address]` plus the org-scoped lookups the port adds,
mirroring `SqlAlchemyPartyRepository` (T124).
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.address_repository import AddressRepository
from app.infrastructure.persistence.models.client import Address
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyAddressRepository(SqlAlchemyRepository[Address], AddressRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Address)

    async def get_by_id_in_organization(
        self, address_id: UUID, organization_id: UUID
    ) -> Address | None:
        stmt = select(Address).where(
            Address.id == address_id, Address.organization_id == organization_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Address]:
        stmt = (
            select(Address)
            .where(Address.organization_id == organization_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_in_organization(self, organization_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Address)
            .where(Address.organization_id == organization_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
