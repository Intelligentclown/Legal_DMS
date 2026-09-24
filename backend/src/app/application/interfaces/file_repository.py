"""Organization- and Matter-scoped File persistence port (T138)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.file import File


class FileRepository(AbstractRepository[File], ABC):
    @abstractmethod
    async def get_in_matter(
        self, file_id: UUID, organization_id: UUID, matter_id: UUID
    ) -> File | None: ...

    @abstractmethod
    async def list_in_matter(
        self, organization_id: UUID, matter_id: UUID, *, limit: int, offset: int
    ) -> Sequence[File]: ...

    @abstractmethod
    async def count_in_matter(self, organization_id: UUID, matter_id: UUID) -> int: ...

    @abstractmethod
    async def allocate_and_add(self, file: File) -> File:
        """Allocate and insert in the caller's transaction; never commits."""
        ...
