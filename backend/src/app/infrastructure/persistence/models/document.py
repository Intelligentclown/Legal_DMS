"""Document schema: DocumentTypes (lookup), DocumentTemplates +
DocumentVariables (template-driven document generation, framework only —
no generation logic exists), Documents, and DocumentVersions.

`documents` deliberately has no `current_version_id` pointer back to
`document_versions` — that would create a circular FK between the two
tables (each referencing the other) for a denormalization with no proven
query need yet (no repository/service exists to benefit from it). "Latest
version" is derived by querying
`document_versions WHERE document_id = ? ORDER BY version_number DESC
LIMIT 1` — add the denormalized pointer later if a real feature's query
patterns actually need it.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin, OptimisticLockMixin


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class DocumentTemplate(Base, AuditMixin):
    __tablename__ = "document_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_type_id: Mapped[UUID] = mapped_column(ForeignKey("document_types.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000))
    file_storage_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("file_storage_records.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class DocumentVariable(Base):
    __tablename__ = "document_variables"
    __table_args__ = (UniqueConstraint("document_template_id", "variable_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_templates.id"), index=True
    )
    variable_name: Mapped[str] = mapped_column(String(100))
    variable_label: Mapped[str] = mapped_column(String(255))
    data_type: Mapped[str] = mapped_column(String(20), default="text")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    default_value: Mapped[str | None] = mapped_column(String(500))


class Document(Base, AuditMixin, OptimisticLockMixin):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    matter_id: Mapped[UUID] = mapped_column(ForeignKey("matters.id"), index=True)
    document_type_id: Mapped[UUID] = mapped_column(ForeignKey("document_types.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="draft")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    file_storage_record_id: Mapped[UUID] = mapped_column(ForeignKey("file_storage_records.id"))
    change_summary: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
