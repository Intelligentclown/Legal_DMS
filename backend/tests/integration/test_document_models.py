"""Schema-level tests for the document and file storage models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.document import (
    Document,
    DocumentTemplate,
    DocumentType,
    DocumentVariable,
    DocumentVersion,
)
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.storage import FileStorageRecord


async def _make_document_type(session: AsyncSession) -> DocumentType:
    doc_type = DocumentType(code=f"DT-{uuid4()}", name="Sale Deed")
    session.add(doc_type)
    await session.flush()
    return doc_type


async def _make_file_record(session: AsyncSession) -> FileStorageRecord:
    record = FileStorageRecord(
        file_path=f"/storage/{uuid4()}.pdf",
        original_filename="deed.pdf",
        size_bytes=1024,
        checksum_sha256="a" * 64,
    )
    session.add(record)
    await session.flush()
    return record


async def _make_matter(session: AsyncSession) -> Matter:
    matter_type = MatterType(code=f"TYPE-{uuid4()}", name="Sale")
    status = MatterStatus(code=f"STATUS-{uuid4()}", name="Open")
    client = Client(full_name="Client", primary_phone="9876543210")
    session.add_all([matter_type, status, client])
    await session.flush()

    matter = Matter(
        matter_number=f"M-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=status.id,
        client_id=client.id,
        title="Test",
        opened_at=datetime.now(UTC),
    )
    session.add(matter)
    await session.flush()
    return matter


class TestFileStorageRecord:
    async def test_valid_record_succeeds(self, db_session: AsyncSession) -> None:
        record = await _make_file_record(db_session)

        assert record.id is not None
        assert record.storage_provider == "local"
        assert record.version == 1


class TestDocumentTemplate:
    async def test_requires_a_valid_document_type(self, db_session: AsyncSession) -> None:
        db_session.add(DocumentTemplate(document_type_id=uuid4(), name="Template"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_can_reference_a_file_storage_record(self, db_session: AsyncSession) -> None:
        doc_type = await _make_document_type(db_session)
        file_record = await _make_file_record(db_session)

        template = DocumentTemplate(
            document_type_id=doc_type.id, name="Template", file_storage_record_id=file_record.id
        )
        db_session.add(template)

        await db_session.flush()

        assert template.id is not None


class TestDocumentVariable:
    async def test_variable_name_unique_within_template(self, db_session: AsyncSession) -> None:
        doc_type = await _make_document_type(db_session)
        template = DocumentTemplate(document_type_id=doc_type.id, name="Template")
        db_session.add(template)
        await db_session.flush()

        db_session.add(
            DocumentVariable(
                document_template_id=template.id,
                variable_name="buyer_name",
                variable_label="Buyer Name",
            )
        )
        await db_session.flush()

        db_session.add(
            DocumentVariable(
                document_template_id=template.id,
                variable_name="buyer_name",
                variable_label="Duplicate",
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestDocumentAndVersions:
    async def test_document_requires_a_valid_matter(self, db_session: AsyncSession) -> None:
        doc_type = await _make_document_type(db_session)
        db_session.add(Document(matter_id=uuid4(), document_type_id=doc_type.id, title="x"))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_version_number_unique_within_document(self, db_session: AsyncSession) -> None:
        matter = await _make_matter(db_session)
        doc_type = await _make_document_type(db_session)
        document = Document(matter_id=matter.id, document_type_id=doc_type.id, title="Deed")
        db_session.add(document)
        await db_session.flush()

        file_record_1 = await _make_file_record(db_session)
        file_record_2 = await _make_file_record(db_session)

        db_session.add(
            DocumentVersion(
                document_id=document.id, version_number=1, file_storage_record_id=file_record_1.id
            )
        )
        await db_session.flush()

        db_session.add(
            DocumentVersion(
                document_id=document.id, version_number=1, file_storage_record_id=file_record_2.id
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_latest_version_is_derived_by_query_not_a_stored_pointer(
        self, db_session: AsyncSession
    ) -> None:
        matter = await _make_matter(db_session)
        doc_type = await _make_document_type(db_session)
        document = Document(matter_id=matter.id, document_type_id=doc_type.id, title="Deed")
        db_session.add(document)
        await db_session.flush()

        for version_number in (1, 2, 3):
            file_record = await _make_file_record(db_session)
            db_session.add(
                DocumentVersion(
                    document_id=document.id,
                    version_number=version_number,
                    file_storage_record_id=file_record.id,
                )
            )
        await db_session.flush()

        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        result = await db_session.execute(stmt)
        latest = result.scalar_one()

        assert latest.version_number == 3
