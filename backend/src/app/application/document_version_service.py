"""Canonical immutable DocumentVersion orchestration (T142)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from uuid import UUID, uuid4

from app.application.errors.exceptions import ConflictError, NotFoundError, UnexpectedError
from app.application.interfaces.document_version_repository import DocumentVersionRepository
from app.application.interfaces.file_storage import FileStorage
from app.infrastructure.database.transaction_outcome import TransactionOutcomeContext
from app.infrastructure.persistence.models.document import (
    Document,
    DocumentVersion,
    DocumentVersionIdempotencyKey,
)
from app.infrastructure.persistence.models.storage import FileStorageRecord


class DocumentVersionService:
    def __init__(
        self,
        repository: DocumentVersionRepository,
        storage: FileStorage,
        outcome: TransactionOutcomeContext,
    ) -> None:
        self._repository, self._storage, self._outcome = repository, storage, outcome

    @staticmethod
    def storage_key(organization_id: UUID, version_id: UUID) -> str:
        return f"organizations/{organization_id}/document-versions/{version_id}/content"

    async def list(self, organization_id: UUID, document: Document) -> Sequence[DocumentVersion]:
        return await self._repository.list(organization_id, document.id)

    async def get(
        self, organization_id: UUID, document: Document, version_id: UUID
    ) -> DocumentVersion:
        version = await self._repository.get(organization_id, document.id, version_id)
        if version is None:
            raise NotFoundError("Document version was not found")
        return version

    async def latest(self, organization_id: UUID, document: Document) -> DocumentVersion:
        version = await self._repository.latest(organization_id, document.id)
        if version is None:
            raise NotFoundError("Document version was not found")
        return version

    async def create(
        self,
        organization_id: UUID,
        document: Document,
        content: bytes,
        filename: str,
        mime_type: str | None,
        idempotency_key: str | None,
        actor_id: UUID | None,
        change_summary: str | None,
    ) -> DocumentVersion:
        fingerprint = hashlib.sha256(content).hexdigest()
        if idempotency_key is not None:
            existing = await self._repository.idempotency(
                organization_id, document.id, idempotency_key
            )
            if existing is not None:
                if existing.payload_fingerprint != fingerprint:
                    raise ConflictError("Idempotency key was reused with different content")
                return await self.get(organization_id, document, existing.document_version_id)
        version_id, storage_id = uuid4(), uuid4()
        key = self.storage_key(organization_id, version_id)
        stored = await self._storage.save(key, content, content_type=mime_type)
        if stored.size != len(content):
            await self._storage.delete(key)
            raise UnexpectedError("Storage provider reported an unexpected byte size")
        await self._repository.lock_document(document)
        # A second lookup is required after the Document-local allocation lock.
        # Two retries can both miss the optimistic lookup above while one is
        # writing its blob; the lock serializes their durable idempotency
        # evidence without holding it during external storage I/O.
        if idempotency_key is not None:
            existing = await self._repository.idempotency(
                organization_id, document.id, idempotency_key
            )
            if existing is not None:
                await self._storage.delete(key)
                if existing.payload_fingerprint != fingerprint:
                    raise ConflictError("Idempotency key was reused with different content")
                return await self.get(organization_id, document, existing.document_version_id)
        self._outcome.register(lambda: self._storage.delete(key))
        number = await self._repository.next_version_number(document.id)
        record = FileStorageRecord(
            id=storage_id,
            organization_id=organization_id,
            storage_provider="local",
            file_path=key,
            original_filename=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            checksum_sha256=fingerprint,
            uploaded_by=actor_id,
        )
        version = DocumentVersion(
            id=version_id,
            organization_id=organization_id,
            document_id=document.id,
            version_number=number,
            file_storage_record_id=storage_id,
            change_summary=change_summary,
            created_by=actor_id,
        )
        evidence = (
            DocumentVersionIdempotencyKey(
                id=uuid4(),
                organization_id=organization_id,
                document_id=document.id,
                idempotency_key=idempotency_key,
                payload_fingerprint=fingerprint,
                document_version_id=version_id,
            )
            if idempotency_key is not None
            else None
        )
        await self._repository.add(record, version, evidence)
        return version

    async def download(
        self, organization_id: UUID, document: Document, version_id: UUID
    ) -> tuple[DocumentVersion, FileStorageRecord, bytes]:
        version = await self.get(organization_id, document, version_id)
        record = await self._repository.storage(organization_id, version.file_storage_record_id)
        if record is None:
            raise UnexpectedError("Document version storage ownership is invalid")
        content = await self._storage.read(record.file_path)
        if (
            len(content) != record.size_bytes
            or hashlib.sha256(content).hexdigest() != record.checksum_sha256
        ):
            raise UnexpectedError("Stored document content failed integrity verification")
        return version, record, content
