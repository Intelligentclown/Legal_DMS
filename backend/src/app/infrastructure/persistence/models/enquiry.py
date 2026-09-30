"""T148 pre-engagement persistence models.

These are deliberately persistence-only models.  They expose no application
service, route, conversion operation, or inferred Party creation behaviour.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Enquiry(Base):
    __tablename__ = "enquiries"
    __table_args__ = (
        CheckConstraint(
            "party_id IS NOT NULL OR prospect_display_name IS NOT NULL",
            name="party_or_prospect_evidence",
        ),
        ForeignKeyConstraint(
            ["organization_id", "party_id"],
            ["parties.organization_id", "parties.id"],
            name="fk_enquiries_organization_id_parties",
        ),
        UniqueConstraint("organization_id", "id", name="uq_enquiries_organization_id_id"),
        Index("ix_enquiries_organization_id_party_id", "organization_id", "party_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    party_id: Mapped[UUID | None] = mapped_column(index=True)
    prospect_display_name: Mapped[str | None] = mapped_column(String(255))
    prospect_phone: Mapped[str | None] = mapped_column(String(20))
    prospect_email: Mapped[str | None] = mapped_column(String(255))
    prospect_description: Mapped[str | None] = mapped_column(String(2000))
    prospect_source: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "enquiry_id"],
            ["enquiries.organization_id", "enquiries.id"],
            name="fk_quotations_organization_id_enquiries",
        ),
        UniqueConstraint("organization_id", "id", name="uq_quotations_organization_id_id"),
        UniqueConstraint(
            "organization_id",
            "enquiry_id",
            "id",
            name="uq_quotations_organization_id_enquiry_id_id",
        ),
        Index("ix_quotations_organization_id_enquiry_id", "organization_id", "enquiry_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    enquiry_id: Mapped[UUID] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class QuotationRevision(Base):
    __tablename__ = "quotation_revisions"
    __table_args__ = (
        CheckConstraint("ordinal > 0", name="ordinal_positive"),
        ForeignKeyConstraint(
            ["organization_id", "quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_quotation_revisions_organization_id_quotations",
        ),
        UniqueConstraint("organization_id", "id", name="uq_quotation_revisions_organization_id_id"),
        UniqueConstraint(
            "quotation_id", "ordinal", name="uq_quotation_revisions_quotation_id_ordinal"
        ),
        UniqueConstraint(
            "organization_id",
            "quotation_id",
            "id",
            name="uq_quotation_revisions_organization_id_quotation_id_id",
        ),
        Index(
            "ix_quotation_revisions_organization_id_quotation_id", "organization_id", "quotation_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    quotation_id: Mapped[UUID] = mapped_column(index=True)
    ordinal: Mapped[int] = mapped_column(Integer())
    proposal_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB())
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class Acceptance(Base):
    __tablename__ = "acceptances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "enquiry_id"],
            ["enquiries.organization_id", "enquiries.id"],
            name="fk_acceptances_organization_id_enquiries",
        ),
        ForeignKeyConstraint(
            ["organization_id", "enquiry_id", "quotation_id"],
            ["quotations.organization_id", "quotations.enquiry_id", "quotations.id"],
            name="fk_acceptances_organization_id_enquiry_id_quotations",
        ),
        ForeignKeyConstraint(
            ["organization_id", "quotation_id", "quotation_revision_id"],
            [
                "quotation_revisions.organization_id",
                "quotation_revisions.quotation_id",
                "quotation_revisions.id",
            ],
            name="fk_acceptances_organization_id_quotation_id_revisions",
        ),
        ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_acceptances_organization_id_matters",
        ),
        UniqueConstraint("organization_id", "id", name="uq_acceptances_organization_id_id"),
        UniqueConstraint(
            "organization_id", "enquiry_id", name="uq_acceptances_organization_id_enquiry_id"
        ),
        UniqueConstraint(
            "organization_id", "matter_id", name="uq_acceptances_organization_id_matter_id"
        ),
        UniqueConstraint(
            "organization_id",
            "quotation_revision_id",
            name="uq_acceptances_organization_id_quotation_revision_id",
        ),
        UniqueConstraint(
            "organization_id",
            "enquiry_id",
            "idempotency_key",
            name="uq_acceptances_organization_id_enquiry_id_idempotency_key",
        ),
        Index("ix_acceptances_organization_id_matter_id", "organization_id", "matter_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    enquiry_id: Mapped[UUID] = mapped_column(index=True)
    quotation_id: Mapped[UUID] = mapped_column(index=True)
    quotation_revision_id: Mapped[UUID] = mapped_column(index=True)
    matter_id: Mapped[UUID] = mapped_column(index=True)
    accepted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    idempotency_key: Mapped[str] = mapped_column(String(255))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
