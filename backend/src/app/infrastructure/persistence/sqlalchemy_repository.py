"""Generic SQLAlchemy implementation of the repository port.

Works directly against a SQLAlchemy declarative model — for Stage 1's
purposes the model *is* the entity being persisted, since no business
feature exists yet to justify a separate domain-model/persistence-model
mapping layer. A future feature that needs that distinction can wrap this
in its own repository subclass with explicit mapping; nothing here forces
it where it isn't needed.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repository import AbstractRepository, SupportsId


class SqlAlchemyRepository[ModelT: SupportsId](AbstractRepository[ModelT]):
    """Generic CRUD repository for a single SQLAlchemy declarative model."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id_: UUID) -> ModelT | None:
        return await self._session.get(self._model, id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        await self._session.flush()
        return entity

    async def delete(self, id_: UUID) -> None:
        instance = await self.get_by_id(id_)
        if instance is not None:
            await self._session.delete(instance)
            await self._session.flush()
