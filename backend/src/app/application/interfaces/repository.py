"""Repository port: what application services depend on for persistence,
without knowing anything about SQLAlchemy or any other storage technology.
Concrete implementations live in `infrastructure/persistence/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID


class SupportsId(Protocol):
    """Structural type for anything with a UUID `id` — domain entities and
    SQLAlchemy models alike satisfy this without any inheritance relationship.
    """

    id: UUID


class AbstractRepository[T: SupportsId](ABC):
    """Generic repository port over a type `T` that has a UUID `id`."""

    @abstractmethod
    async def get_by_id(self, id_: UUID) -> T | None: ...

    @abstractmethod
    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[T]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def add(self, entity: T) -> T: ...

    @abstractmethod
    async def update(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, id_: UUID) -> None: ...
