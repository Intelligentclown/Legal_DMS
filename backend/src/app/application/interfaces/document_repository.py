"""Organization, Matter and File-scoped Document persistence port (T139)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.document import Document


class DocumentRepository(AbstractRepository[Document], ABC):
    @abstractmethod
    async def get_in_file(
        self, document_id: UUID, organization_id: UUID, matter_id: UUID, file_id: UUID
    ) -> Document | None: ...

    @abstractmethod
    async def list_in_file(
        self, organization_id: UUID, matter_id: UUID, file_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Document]: ...

    @abstractmethod
    async def count_in_file(self, organization_id: UUID, matter_id: UUID, file_id: UUID) -> int: ...
