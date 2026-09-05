"""Governed Party, bounded MatterParty, and immutable migration-ledger schema."""

from __future__ import annotations

from datetime import date, datetime
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin, OptimisticLockMixin


class Party(Base, AuditMixin, OptimisticLockMixin):
    __tablename__ = "parties"
    __table_args__ = (
        CheckConstraint("party_type IN ('individual', 'organization')", name="party_type"),
        CheckConstraint("length(primary_phone) >= 7", name="primary_phone_length"),
        CheckConstraint(
            "pan_number IS NULL OR pan_number ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'",
            name="pan_number_format",
        ),
        CheckConstraint(
            "aadhaar_number IS NULL OR aadhaar_number ~ '^[0-9]{12}$'",
            name="aadhaar_number_format",
        ),
        CheckConstraint(
            "gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'",
            name="gstin_format",
        ),
        CheckConstraint(
            "registration_identifier IS NULL OR length(registration_identifier) > 0",
            name="registration_identifier_non_empty",
        ),
        CheckConstraint(
            "party_type = 'individual' OR "
            "(aadhaar_number IS NULL AND date_of_birth IS NULL "
            "AND gender IS NULL AND occupation IS NULL)",
            name="individual_fields_only",
        ),
        CheckConstraint(
            "party_type = 'organization' OR "
            "(registration_identifier IS NULL AND incorporation_date IS NULL)",
            name="organization_fields_only",
        ),
        ForeignKeyConstraint(
            ["organization_id", "address_id"],
            ["addresses.organization_id", "addresses.id"],
            name="fk_parties_organization_id_addresses",
        ),
        UniqueConstraint("organization_id", "id", name="uq_parties_organization_id_id"),
        Index("ix_parties_organization_id_party_type", "organization_id", "party_type"),
        Index("ix_parties_organization_id_display_name", "organization_id", "display_name"),
        Index("ix_parties_organization_id_primary_phone", "organization_id", "primary_phone"),
        Index(
            "ix_parties_organization_id_primary_email",
            "organization_id",
            "primary_email",
            postgresql_where=text("primary_email IS NOT NULL"),
        ),
        Index(
            "ix_parties_organization_id_pan_number",
            "organization_id",
            "pan_number",
            postgresql_where=text("pan_number IS NOT NULL"),
        ),
        Index(
            "ix_parties_organization_id_aadhaar_number",
            "organization_id",
            "aadhaar_number",
            postgresql_where=text("aadhaar_number IS NOT NULL"),
        ),
        Index(
            "ix_parties_organization_id_gstin",
            "organization_id",
            "gstin",
            postgresql_where=text("gstin IS NOT NULL"),
        ),
        Index(
            "ix_parties_organization_id_registration_identifier",
            "organization_id",
            "registration_identifier",
            postgresql_where=text("registration_identifier IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    party_type: Mapped[str] = mapped_column(String(20))
    display_name: Mapped[str] = mapped_column(String(255))
    primary_phone: Mapped[str] = mapped_column(String(20))
    primary_email: Mapped[str | None] = mapped_column(String(255))
    address_id: Mapped[UUID | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(String(2000))
    pan_number: Mapped[str | None] = mapped_column(String(10))
    aadhaar_number: Mapped[str | None] = mapped_column(String(12))
    gstin: Mapped[str | None] = mapped_column(String(15))
    registration_identifier: Mapped[str | None] = mapped_column(String(50))
    date_of_birth: Mapped[date | None] = mapped_column()
    gender: Mapped[str | None] = mapped_column(String(50))
    occupation: Mapped[str | None] = mapped_column(String(255))
    incorporation_date: Mapped[date | None] = mapped_column()


class MatterParty(Base, AuditMixin):
    __tablename__ = "matter_parties"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_matter_parties_organization_id_matters",
        ),
        ForeignKeyConstraint(
            ["organization_id", "party_id"],
            ["parties.organization_id", "parties.id"],
            name="fk_matter_parties_organization_id_parties",
        ),
        UniqueConstraint(
            "matter_id", "party_id", "role", name="uq_matter_parties_matter_id_party_id_role"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    matter_id: Mapped[UUID] = mapped_column(index=True)
    party_id: Mapped[UUID] = mapped_column(index=True)
    role: Mapped[str] = mapped_column(String(50))


class ClientPartyMigrationLedger(Base):
    __tablename__ = "client_party_migration_ledger"
    __table_args__ = (
        CheckConstraint("party_id = legacy_client_id", name="party_id_matches_legacy_client_id"),
        CheckConstraint(
            "resolution_mode IN ('deterministic', 'operator_reconciled')", name="resolution_mode"
        ),
        UniqueConstraint(
            "legacy_client_id",
            "party_id",
            "organization_id",
            "executor_version",
            "reconciliation_set_id",
            "source_report_sha256",
            "source_fingerprint",
            name="uq_client_party_migration_ledger_identical_completion",
        ),
        UniqueConstraint(
            "legacy_client_id",
            "executor_version",
            "reconciliation_set_id",
            "source_report_sha256",
            name="uq_client_party_migration_ledger_basis_collision",
        ),
        Index("ix_client_party_migration_ledger_organization_id", "organization_id"),
        Index("ix_client_party_migration_ledger_party_id", "party_id"),
        Index("ix_client_party_migration_ledger_completed_at", "completed_at"),
        Index("ix_client_party_migration_ledger_execution_run_id", "execution_run_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    legacy_client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"))
    party_id: Mapped[UUID] = mapped_column(ForeignKey("parties.id"))
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    executor_version: Mapped[str] = mapped_column(String(100))
    reconciliation_set_id: Mapped[str] = mapped_column(String(255))
    source_report_sha256: Mapped[str] = mapped_column(String(64))
    resolution_mode: Mapped[str] = mapped_column(String(32))
    source_client_version: Mapped[int] = mapped_column(Integer())
    source_client_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_fingerprint: Mapped[str] = mapped_column(String(255))
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    artifact_actor_type: Mapped[str | None] = mapped_column(String(32))
    artifact_actor_id: Mapped[str | None] = mapped_column(String(255))
    operator_note: Mapped[str | None] = mapped_column(String(2000))
    execution_run_id: Mapped[UUID] = mapped_column()
