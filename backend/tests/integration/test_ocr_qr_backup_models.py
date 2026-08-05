"""Schema-level tests for OCR, QR, and backup models, including a live
check that the full-text search GIN index actually works against Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.document import Document, DocumentType, DocumentVersion
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.storage import (
    Backup,
    FileStorageRecord,
    OcrJob,
    OcrResult,
    QrCodeRecord,
)


async def _make_document_version(session: AsyncSession) -> DocumentVersion:
    matter_type = MatterType(code=f"TYPE-{uuid4()}", name="Sale")
    status = MatterStatus(code=f"STATUS-{uuid4()}", name="Open")
    client = Client(full_name="Client", primary_phone="9876543210")
    doc_type = DocumentType(code=f"DT-{uuid4()}", name="Deed")
    session.add_all([matter_type, status, client, doc_type])
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

    document = Document(matter_id=matter.id, document_type_id=doc_type.id, title="Deed")
    session.add(document)
    await session.flush()

    file_record = FileStorageRecord(
        file_path=f"/storage/{uuid4()}.pdf",
        original_filename="deed.pdf",
        size_bytes=1024,
        checksum_sha256="a" * 64,
    )
    session.add(file_record)
    await session.flush()

    version = DocumentVersion(
        document_id=document.id, version_number=1, file_storage_record_id=file_record.id
    )
    session.add(version)
    await session.flush()
    return version


class TestOcrJobAndResult:
    async def test_ocr_job_requires_a_valid_document_version(
        self, db_session: AsyncSession
    ) -> None:
        db_session.add(OcrJob(document_version_id=uuid4()))

        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_ocr_result_full_text_search_index_works(self, db_session: AsyncSession) -> None:
        version = await _make_document_version(db_session)
        job = OcrJob(document_version_id=version.id, status="completed")
        db_session.add(job)
        await db_session.flush()

        result = OcrResult(
            ocr_job_id=job.id,
            page_number=1,
            extracted_text="This deed transfers ownership of survey number 123 in Ahmedabad.",
        )
        db_session.add(result)
        await db_session.flush()

        stmt = (
            select(OcrResult)
            .where(
                text("to_tsvector('english', extracted_text) @@ plainto_tsquery('english', :query)")
            )
            .params(query="ownership Ahmedabad")
        )
        found = (await db_session.execute(stmt)).scalars().all()

        assert result.id in [r.id for r in found]


class TestQrCodeRecord:
    async def test_code_value_must_be_unique(self, db_session: AsyncSession) -> None:
        db_session.add(QrCodeRecord(entity_type="matter", entity_id=uuid4(), code_value="QR-1"))
        await db_session.flush()

        db_session.add(QrCodeRecord(entity_type="matter", entity_id=uuid4(), code_value="QR-1"))
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestBackup:
    async def test_valid_backup_succeeds(self, db_session: AsyncSession) -> None:
        backup = Backup(backup_type="full", file_path="/backups/2026-08-05.tar.gz")
        db_session.add(backup)

        await db_session.flush()

        assert backup.id is not None
        assert backup.status == "pending"
