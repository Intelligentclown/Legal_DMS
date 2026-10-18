"""SQLAlchemy persistence for Matter-owned canonical Property participation."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.matter_property_repository import MatterPropertyRepository
from app.infrastructure.persistence.models.matter_property import MatterProperty
from app.infrastructure.persistence.models.property import Property


class SqlAlchemyMatterPropertyRepository(MatterPropertyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_properties(self, matter_id: UUID, organization_id: UUID) -> Sequence[Property]:
        result = await self._session.execute(
            select(Property)
            .join(MatterProperty, MatterProperty.property_id == Property.id)
            .where(
                MatterProperty.matter_id == matter_id,
                MatterProperty.organization_id == organization_id,
                Property.organization_id == organization_id,
            )
            .order_by(Property.id)
        )
        return result.scalars().all()

    async def add_if_absent(self, association: MatterProperty) -> bool:
        # The savepoint preserves the outer request transaction after a
        # concurrent unique-pair collision.  This method never commits.
        try:
            async with self._session.begin_nested():
                self._session.add(association)
                await self._session.flush()
        except IntegrityError as exc:
            # Only the pair uniqueness collision is idempotent.  A different
            # integrity defect must keep its normal failure semantics rather
            # than being misreported as a successful duplicate request.
            if getattr(exc.orig, "sqlstate", None) == "23505":
                return False
            raise
        return True

    async def remove_if_present(
        self, matter_id: UUID, property_id: UUID, organization_id: UUID
    ) -> bool:
        result = await self._session.execute(
            delete(MatterProperty).where(
                MatterProperty.matter_id == matter_id,
                MatterProperty.property_id == property_id,
                MatterProperty.organization_id == organization_id,
            )
        )
        await self._session.flush()
        return result.rowcount == 1
