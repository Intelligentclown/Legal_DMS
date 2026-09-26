from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.infrastructure.persistence.models.document import (
    Document,
    DocumentVersion,
    DocumentVersionIdempotencyKey,
)
from app.infrastructure.persistence.models.storage import FileStorageRecord


class DocumentVersionRepository(ABC):
    @abstractmethod
    async def lock_document(self, document: Document) -> Document: ...

    @abstractmethod
    async def next_version_number(self, document_id: UUID) -> int: ...

    @abstractmethod
    async def list(self, organization_id: UUID, document_id: UUID) -> Sequence[DocumentVersion]: ...

    @abstractmethod
    async def get(
        self, organization_id: UUID, document_id: UUID, version_id: UUID
    ) -> DocumentVersion | None: ...

    @abstractmethod
    async def latest(self, organization_id: UUID, document_id: UUID) -> DocumentVersion | None: ...

    @abstractmethod
    async def idempotency(
        self, organization_id: UUID, document_id: UUID, key: str
    ) -> DocumentVersionIdempotencyKey | None: ...

    @abstractmethod
    async def storage(
        self, organization_id: UUID, storage_id: UUID
    ) -> FileStorageRecord | None: ...

    @abstractmethod
    async def add(
        self,
        storage: FileStorageRecord,
        version: DocumentVersion,
        key: DocumentVersionIdempotencyKey | None,
    ) -> None: ...
