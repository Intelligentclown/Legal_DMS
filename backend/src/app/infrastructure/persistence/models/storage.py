"""File storage metadata: the DB-metadata companion to Stage 1's
`FileStorage`/`StoredFile` port
(`backend/src/app/application/interfaces/file_storage.py`). The database
never stores document/file *content* — only metadata (path, hash,
checksum, size, provider), per the charter's File Storage Strategy.

Created here (Documents section) rather than in its originally-planned
OCR/QR/Storage/Backups section, because `document_templates` and
`document_versions` both need to reference it — a table dependency the
original section grouping didn't account for. OCR/QR/Backup tables land
in their own section later, in this same module.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class FileStorageRecord(Base):
    __tablename__ = "file_storage_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    storage_provider: Mapped[str] = mapped_column(String(50), default="local")
    file_path: Mapped[str] = mapped_column(String(1000))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    retention_policy: Mapped[str | None] = mapped_column(String(100))
    uploaded_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OcrJob(Base):
    __tablename__ = "ocr_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_versions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(String(2000))


class OcrResult(Base):
    __tablename__ = "ocr_results"
    __table_args__ = (
        # GIN expression index preparing for full-text search over OCR'd
        # content, per the charter's "full text search preparation" index
        # requirement -- no search query code exists yet to use it (Stage 1's
        # SearchIndex port has an in-memory default; a Postgres-backed
        # implementation would use exactly this index).
        Index(
            "ix_ocr_results_extracted_text_fts",
            text("to_tsvector('english', extracted_text)"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ocr_job_id: Mapped[UUID] = mapped_column(ForeignKey("ocr_jobs.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    extracted_text: Mapped[str] = mapped_column(String)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    language: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QrCodeRecord(Base):
    __tablename__ = "qr_code_records"
    __table_args__ = (
        Index("ix_qr_code_records_entity_type_entity_id", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[UUID] = mapped_column()
    code_value: Mapped[str] = mapped_column(String(255), unique=True)
    qr_image_file_storage_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("file_storage_records.id")
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    generated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    backup_type: Mapped[str] = mapped_column(String(20), default="full")
    file_path: Mapped[str] = mapped_column(String(1000))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
