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
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
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
