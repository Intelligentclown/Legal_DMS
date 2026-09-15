"""SQLAlchemy implementation of `PartyRepository` (T124) —
`SqlAlchemyRepository[Party]` plus the org-scoped lookups the port adds,
mirroring `SqlAlchemyUserRepository` (T50/T105).
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.party_repository import PartyRepository
from app.infrastructure.persistence.models.party import Party
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyPartyRepository(SqlAlchemyRepository[Party], PartyRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Party)

    async def get_by_id_in_organization(
        self, party_id: UUID, organization_id: UUID
    ) -> Party | None:
        stmt = select(Party).where(Party.id == party_id, Party.organization_id == organization_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Party]:
        stmt = (
            select(Party)
            .where(Party.organization_id == organization_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_in_organization(self, organization_id: UUID) -> int:
        stmt = (
            select(func.count()).select_from(Party).where(Party.organization_id == organization_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
