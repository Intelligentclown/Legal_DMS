from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.document_version_repository import DocumentVersionRepository
from app.infrastructure.persistence.models.document import (
    Document,
    DocumentVersion,
    DocumentVersionIdempotencyKey,
)
from app.infrastructure.persistence.models.storage import FileStorageRecord


class SqlAlchemyDocumentVersionRepository(DocumentVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_document(self, document: Document) -> Document:
        return (
            await self._session.execute(
                select(Document).where(Document.id == document.id).with_for_update()
            )
        ).scalar_one()

    async def next_version_number(self, document_id: UUID) -> int:
        value = (
            await self._session.execute(
                select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(
                    DocumentVersion.document_id == document_id
                )
            )
        ).scalar_one()
        return value + 1

    async def list(self, organization_id: UUID, document_id: UUID) -> Sequence[DocumentVersion]:
        return (
            (
                await self._session.execute(
                    select(DocumentVersion)
                    .where(
                        DocumentVersion.organization_id == organization_id,
                        DocumentVersion.document_id == document_id,
                    )
                    .order_by(DocumentVersion.version_number)
                )
            )
            .scalars()
            .all()
        )

    async def get(
        self, organization_id: UUID, document_id: UUID, version_id: UUID
    ) -> DocumentVersion | None:
        return (
            await self._session.execute(
                select(DocumentVersion).where(
                    DocumentVersion.id == version_id,
                    DocumentVersion.organization_id == organization_id,
                    DocumentVersion.document_id == document_id,
                )
            )
        ).scalar_one_or_none()

    async def latest(self, organization_id: UUID, document_id: UUID) -> DocumentVersion | None:
        return (
            await self._session.execute(
                select(DocumentVersion)
                .where(
                    DocumentVersion.organization_id == organization_id,
                    DocumentVersion.document_id == document_id,
                )
                .order_by(DocumentVersion.version_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def idempotency(
        self, organization_id: UUID, document_id: UUID, key: str
    ) -> DocumentVersionIdempotencyKey | None:
        return (
            await self._session.execute(
                select(DocumentVersionIdempotencyKey).where(
                    DocumentVersionIdempotencyKey.organization_id == organization_id,
                    DocumentVersionIdempotencyKey.document_id == document_id,
                    DocumentVersionIdempotencyKey.idempotency_key == key,
                )
            )
        ).scalar_one_or_none()

    async def storage(self, organization_id: UUID, storage_id: UUID) -> FileStorageRecord | None:
        return (
            await self._session.execute(
                select(FileStorageRecord).where(
                    FileStorageRecord.id == storage_id,
                    FileStorageRecord.organization_id == organization_id,
                )
            )
        ).scalar_one_or_none()

    async def add(
        self,
        storage: FileStorageRecord,
        version: DocumentVersion,
        key: DocumentVersionIdempotencyKey | None,
    ) -> None:
        self._session.add_all([storage, version] + ([key] if key is not None else []))
        await self._session.flush()
