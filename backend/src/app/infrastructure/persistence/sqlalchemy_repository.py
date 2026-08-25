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
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.common.query import FilterOperator, FilterSpec, SearchQuery
from app.application.interfaces.repository import AbstractRepository, SupportsId


def _filter_predicate(column: Any, spec: FilterSpec) -> ColumnElement[bool]:
    match spec.operator:
        case FilterOperator.EQ:
            return column == spec.value
        case FilterOperator.NEQ:
            return column != spec.value
        case FilterOperator.GT:
            return column > spec.value
        case FilterOperator.GTE:
            return column >= spec.value
        case FilterOperator.LT:
            return column < spec.value
        case FilterOperator.LTE:
            return column <= spec.value
        case FilterOperator.CONTAINS:
            return column.contains(spec.value)
        case FilterOperator.IN:
            return column.in_(spec.value)


class SqlAlchemyRepository[ModelT: SupportsId](AbstractRepository[ModelT]):
    """Generic CRUD repository for a single SQLAlchemy declarative model."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id_: UUID) -> ModelT | None:
        return await self._session.get(self._model, id_)

    async def list(
        self, *, limit: int = 100, offset: int = 0, query: SearchQuery | None = None
    ) -> Sequence[ModelT]:
        stmt = select(self._model)
        if query is not None and query.filters:
            conditions = [
                _filter_predicate(getattr(self._model, spec.field), spec) for spec in query.filters
            ]
            stmt = stmt.where(*conditions)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

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
