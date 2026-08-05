"""A generic in-memory fake satisfying AbstractRepository, for tests that
need repository behavior without a real database.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository, SupportsId


class InMemoryRepository[T: SupportsId](AbstractRepository[T]):
    def __init__(self) -> None:
        self._items: dict[UUID, T] = {}

    async def get_by_id(self, id_: UUID) -> T | None:
        return self._items.get(id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[T]:
        return list(self._items.values())[offset : offset + limit]

    async def count(self) -> int:
        return len(self._items)

    async def add(self, entity: T) -> T:
        self._items[entity.id] = entity
        return entity

    async def update(self, entity: T) -> T:
        self._items[entity.id] = entity
        return entity

    async def delete(self, id_: UUID) -> None:
        self._items.pop(id_, None)
