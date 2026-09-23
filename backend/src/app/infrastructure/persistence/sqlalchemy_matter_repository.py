"""SQLAlchemy Matter repository for the bounded T134 application surface."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.matter_repository import MatterRepository
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.party import MatterParty
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class SqlAlchemyMatterRepository(SqlAlchemyRepository[Matter], MatterRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Matter)

    async def get_by_id_in_organization(
        self, matter_id: UUID, organization_id: UUID
    ) -> Matter | None:
        result = await self._session.execute(
            select(Matter).where(Matter.id == matter_id, Matter.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Matter]:
        result = await self._session.execute(
            select(Matter)
            .where(Matter.organization_id == organization_id)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_in_organization(self, organization_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Matter)
            .where(Matter.organization_id == organization_id)
        )
        return result.scalar_one()

    async def list_participants(
        self, matter_id: UUID, organization_id: UUID
    ) -> Sequence[MatterParty]:
        result = await self._session.execute(
            select(MatterParty).where(
                MatterParty.matter_id == matter_id,
                MatterParty.organization_id == organization_id,
            )
        )
        return result.scalars().all()

    async def add_with_participants(
        self, matter: Matter, participants: Sequence[MatterParty]
    ) -> Matter:
        # A savepoint makes the aggregate atomic even when the caller catches
        # a database validation failure before the request transaction exits.
        async with self._session.begin_nested():
            self._session.add(matter)
            await self._session.flush()
            self._session.add_all(participants)
            await self._session.flush()
        return matter
