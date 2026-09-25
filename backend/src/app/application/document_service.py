"""Bounded File-canonical Document metadata use cases (T139)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from app.application.errors.exceptions import ConflictError, NotFoundError, ValidationError
from app.application.interfaces.document_repository import DocumentRepository
from app.application.interfaces.file_repository import FileRepository
from app.application.interfaces.matter_repository import MatterRepository
from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.document import Document, DocumentType

_MUTABLE_FIELDS = frozenset({"title", "status", "document_type_id"})


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        file_repository: FileRepository,
        matter_repository: MatterRepository,
        document_type_repository: AbstractRepository[DocumentType],
    ) -> None:
        self._repository = repository
        self._file_repository = file_repository
        self._matter_repository = matter_repository
        self._document_type_repository = document_type_repository

    async def _file(self, organization_id: UUID, matter_id: UUID, file_id: UUID) -> None:
        matter = await self._matter_repository.get_by_id_in_organization(matter_id, organization_id)
        if matter is None:
            raise NotFoundError(f"Matter with id {matter_id} was not found")
        if await self._file_repository.get_in_matter(file_id, organization_id, matter_id) is None:
            raise NotFoundError(f"File with id {file_id} was not found")

    async def _document_type(self, document_type_id: UUID) -> None:
        if await self._document_type_repository.get_by_id(document_type_id) is None:
            raise ValidationError(f"document_type_id with id {document_type_id} does not exist")

    async def list_in_file(
        self, organization_id: UUID, matter_id: UUID, file_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Document]:
        await self._file(organization_id, matter_id, file_id)
        return await self._repository.list_in_file(
            organization_id, matter_id, file_id, limit=limit, offset=offset
        )

    async def count_in_file(self, organization_id: UUID, matter_id: UUID, file_id: UUID) -> int:
        await self._file(organization_id, matter_id, file_id)
        return await self._repository.count_in_file(organization_id, matter_id, file_id)

    async def get_in_file(
        self, document_id: UUID, organization_id: UUID, matter_id: UUID, file_id: UUID
    ) -> Document:
        await self._file(organization_id, matter_id, file_id)
        document = await self._repository.get_in_file(
            document_id, organization_id, matter_id, file_id
        )
        if document is None:
            raise NotFoundError(f"Document with id {document_id} was not found")
        return document

    async def create_in_file(
        self,
        organization_id: UUID,
        matter_id: UUID,
        file_id: UUID,
        fields: Mapping[str, Any],
        *,
        actor_id: UUID | None = None,
    ) -> Document:
        await self._file(organization_id, matter_id, file_id)
        title = fields.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("title is required")
        document_type_id = fields.get("document_type_id")
        if not isinstance(document_type_id, UUID):
            raise ValidationError("document_type_id is required")
        await self._document_type(document_type_id)
        return await self._repository.add(
            Document(
                id=uuid4(),
                organization_id=organization_id,
                matter_id=matter_id,
                file_id=file_id,
                document_type_id=document_type_id,
                title=title,
                status=fields.get("status", "draft"),
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

    async def update_in_file(
        self,
        document_id: UUID,
        organization_id: UUID,
        matter_id: UUID,
        file_id: UUID,
        fields: Mapping[str, Any],
        *,
        actor_id: UUID | None = None,
    ) -> Document:
        document = await self.get_in_file(document_id, organization_id, matter_id, file_id)
        expected_version = fields.get("version")
        if expected_version is not None and expected_version != document.version:
            raise ConflictError("Document has been modified by another request")
        writable = {key: value for key, value in fields.items() if key in _MUTABLE_FIELDS}
        if "title" in writable and (
            not isinstance(writable["title"], str) or not writable["title"].strip()
        ):
            raise ValidationError("title is required")
        if "status" in writable and (
            not isinstance(writable["status"], str) or not writable["status"]
        ):
            raise ValidationError("status is required")
        if "document_type_id" in writable:
            await self._document_type(writable["document_type_id"])
        for key, value in writable.items():
            setattr(document, key, value)
        if writable:
            document.updated_by = actor_id
        return await self._repository.update(document)
