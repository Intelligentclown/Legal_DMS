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

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    func,
)
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
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_documents_organization_id_id"),
        ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_documents_organization_id_matters",
        ),
        ForeignKeyConstraint(
            ["organization_id", "matter_id", "file_id"],
            ["files.organization_id", "files.matter_id", "files.id"],
            name="fk_documents_organization_id_matter_id_files",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    matter_id: Mapped[UUID] = mapped_column(ForeignKey("matters.id"), index=True)
    file_id: Mapped[UUID | None] = mapped_column(index=True)
    document_type_id: Mapped[UUID] = mapped_column(ForeignKey("document_types.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="draft")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number"),
        UniqueConstraint("organization_id", "id", name="uq_document_versions_organization_id_id"),
        UniqueConstraint(
            "organization_id",
            "file_storage_record_id",
            name="uq_document_versions_organization_id_file_storage_record_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "document_id"],
            ["documents.organization_id", "documents.id"],
            name="fk_document_versions_organization_id_documents",
        ),
        ForeignKeyConstraint(
            ["organization_id", "file_storage_record_id"],
            ["file_storage_records.organization_id", "file_storage_records.id"],
            name="fk_document_versions_organization_id_file_storage_records",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    file_storage_record_id: Mapped[UUID] = mapped_column(ForeignKey("file_storage_records.id"))
    change_summary: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class DocumentVersionIdempotencyKey(Base):
    """Persisted retry evidence for the later version-create transaction."""

    __tablename__ = "document_version_idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "document_id",
            "idempotency_key",
            name="uq_document_version_idempotency_keys_scope_key",
        ),
        ForeignKeyConstraint(
            ["organization_id", "document_id"],
            ["documents.organization_id", "documents.id"],
            name="fk_dv_idempotency_org_documents",
        ),
        ForeignKeyConstraint(
            ["organization_id", "document_version_id"],
            ["document_versions.organization_id", "document_versions.id"],
            name="fk_dv_idempotency_org_document_versions",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    document_id: Mapped[UUID] = mapped_column(index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    payload_fingerprint: Mapped[str] = mapped_column(String(64))
    document_version_id: Mapped[UUID] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
