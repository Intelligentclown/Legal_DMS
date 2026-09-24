"""Persistence-only business File and Matter-scoped number counter models.

This is deliberately a schema foundation.  It has no allocation operation,
repository, service, or API: ADR-0027's atomic allocation belongs to the
later File application slice.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin, OptimisticLockMixin


class File(Base, AuditMixin, OptimisticLockMixin):
    """A Matter-owned business work package, not physical file storage."""

    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_files_organization_id_id"),
        UniqueConstraint(
            "organization_id", "matter_id", "id", name="uq_files_organization_id_matter_id_id"
        ),
        UniqueConstraint("matter_id", "file_number", name="uq_files_matter_id_file_number"),
        ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_files_organization_id_matters",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    matter_id: Mapped[UUID] = mapped_column(index=True)
    file_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))


class FileNumberSequence(Base):
    """One transactionally allocated counter per Matter (ADR-0027)."""

    __tablename__ = "file_number_sequences"
    __table_args__ = (
        CheckConstraint("next_number > 0", name="next_number_positive"),
        UniqueConstraint(
            "organization_id",
            "matter_id",
            name="uq_file_number_sequences_organization_id_matter_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_file_number_sequences_organization_id_matters",
        ),
    )

    matter_id: Mapped[UUID] = mapped_column(ForeignKey("matters.id"), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    next_number: Mapped[int] = mapped_column(Integer)
