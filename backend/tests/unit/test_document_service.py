from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.document_service import DocumentService
from app.application.errors.exceptions import ConflictError, NotFoundError, ValidationError
from app.infrastructure.persistence.models.document import Document, DocumentType
from app.infrastructure.persistence.models.file import File
from app.infrastructure.persistence.models.matter import Matter


class _Documents:
    def __init__(self) -> None:
        self.items: list[Document] = []

    async def add(self, document: Document) -> Document:
        document.version = 1
        self.items.append(document)
        return document

    async def update(self, document: Document) -> Document:
        document.version += 1
        return document

    async def get_in_file(self, document_id, organization_id, matter_id, file_id):
        return next(
            (
                item
                for item in self.items
                if item.id == document_id
                and item.organization_id == organization_id
                and item.matter_id == matter_id
                and item.file_id == file_id
            ),
            None,
        )

    async def list_in_file(self, organization_id, matter_id, file_id, *, limit, offset):
        return [
            item
            for item in self.items
            if item.organization_id == organization_id
            and item.matter_id == matter_id
            and item.file_id == file_id
        ][offset : offset + limit]

    async def count_in_file(self, organization_id, matter_id, file_id):
        return len(
            await self.list_in_file(organization_id, matter_id, file_id, limit=100, offset=0)
        )


class _Matters:
    def __init__(self, matter: Matter) -> None:
        self.matter = matter

    async def get_by_id_in_organization(self, matter_id, organization_id):
        if self.matter.id == matter_id and self.matter.organization_id == organization_id:
            return self.matter
        return None


class _Files:
    def __init__(self, file: File) -> None:
        self.file = file

    async def get_in_matter(self, file_id, organization_id, matter_id):
        if (
            self.file.id == file_id
            and self.file.organization_id == organization_id
            and self.file.matter_id == matter_id
        ):
            return self.file
        return None


class _Types:
    def __init__(self, document_type: DocumentType) -> None:
        self.document_type = document_type

    async def get_by_id(self, document_type_id):
        return self.document_type if self.document_type.id == document_type_id else None


def _service() -> tuple[DocumentService, _Documents, File, DocumentType, Matter]:
    organization_id = uuid4()
    matter = Matter(id=uuid4(), organization_id=organization_id)
    file = File(
        id=uuid4(), organization_id=organization_id, matter_id=matter.id, file_number=1, title="F"
    )
    document_type = DocumentType(id=uuid4(), code="type", name="Type")
    documents = _Documents()
    return (
        DocumentService(documents, _Files(file), _Matters(matter), _Types(document_type)),
        documents,
        file,
        document_type,
        matter,
    )


@pytest.mark.asyncio
async def test_create_derives_tenant_and_matter_from_nested_file_context() -> None:
    service, documents, file, document_type, matter = _service()
    document = await service.create_in_file(
        file.organization_id,
        matter.id,
        file.id,
        {"title": "Filed document", "document_type_id": document_type.id},
    )
    assert documents.items == [document]
    assert (document.organization_id, document.matter_id, document.file_id) == (
        file.organization_id,
        file.matter_id,
        file.id,
    )


@pytest.mark.asyncio
async def test_create_rejects_mismatched_file_or_missing_document_type() -> None:
    service, documents, file, document_type, matter = _service()
    with pytest.raises(NotFoundError):
        await service.create_in_file(
            file.organization_id,
            uuid4(),
            file.id,
            {"title": "No", "document_type_id": document_type.id},
        )
    with pytest.raises(ValidationError):
        await service.create_in_file(
            file.organization_id, matter.id, file.id, {"title": "No", "document_type_id": uuid4()}
        )
    assert documents.items == []


@pytest.mark.asyncio
async def test_legacy_unfiled_is_never_listed_or_mutated_by_file_operations() -> None:
    service, documents, file, document_type, matter = _service()
    legacy = Document(
        id=uuid4(),
        organization_id=file.organization_id,
        matter_id=matter.id,
        file_id=None,
        document_type_id=document_type.id,
        title="Legacy",
    )
    documents.items.append(legacy)
    assert (
        await service.list_in_file(file.organization_id, matter.id, file.id, limit=10, offset=0)
        == []
    )
    with pytest.raises(NotFoundError):
        await service.get_in_file(legacy.id, file.organization_id, matter.id, file.id)
    assert legacy.file_id is None


@pytest.mark.asyncio
async def test_update_only_changes_metadata_and_honors_expected_version() -> None:
    service, _documents, file, document_type, matter = _service()
    document = await service.create_in_file(
        file.organization_id,
        matter.id,
        file.id,
        {"title": "Original", "document_type_id": document_type.id},
    )
    updated = await service.update_in_file(
        document.id,
        file.organization_id,
        matter.id,
        file.id,
        {"title": "Updated", "status": "final", "version": document.version},
    )
    assert (
        updated.title,
        updated.status,
        updated.organization_id,
        updated.matter_id,
        updated.file_id,
    ) == ("Updated", "final", file.organization_id, matter.id, file.id)
    with pytest.raises(ConflictError):
        await service.update_in_file(
            document.id, file.organization_id, matter.id, file.id, {"version": 1}
        )
