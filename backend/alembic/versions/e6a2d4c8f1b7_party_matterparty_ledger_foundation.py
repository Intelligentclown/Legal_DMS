"""Party, bounded MatterParty, and migration execution-ledger schema foundation

Revision ID: e6a2d4c8f1b7
Revises: d8f4a6c9b3e1
Create Date: 2026-09-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6a2d4c8f1b7"
down_revision: str | Sequence[str] | None = "d8f4a6c9b3e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ADR-0035 step-2 schema without writing legacy data."""
    op.create_table(
        "parties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("party_type", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("primary_phone", sa.String(length=20), nullable=False),
        sa.Column("primary_email", sa.String(length=255), nullable=True),
        sa.Column("address_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("pan_number", sa.String(length=10), nullable=True),
        sa.Column("aadhaar_number", sa.String(length=12), nullable=True),
        sa.Column("gstin", sa.String(length=15), nullable=True),
        sa.Column("registration_identifier", sa.String(length=50), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("occupation", sa.String(length=255), nullable=True),
        sa.Column("incorporation_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "party_type IN ('individual', 'organization')", name=op.f("ck_parties_party_type")
        ),
        sa.CheckConstraint(
            "length(primary_phone) >= 7", name=op.f("ck_parties_primary_phone_length")
        ),
        sa.CheckConstraint(
            "pan_number IS NULL OR pan_number ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'",
            name=op.f("ck_parties_pan_number_format"),
        ),
        sa.CheckConstraint(
            "aadhaar_number IS NULL OR aadhaar_number ~ '^[0-9]{12}$'",
            name=op.f("ck_parties_aadhaar_number_format"),
        ),
        sa.CheckConstraint(
            "gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'",
            name=op.f("ck_parties_gstin_format"),
        ),
        sa.CheckConstraint(
            "registration_identifier IS NULL OR length(registration_identifier) > 0",
            name=op.f("ck_parties_registration_identifier_non_empty"),
        ),
        sa.CheckConstraint(
            "party_type = 'individual' OR "
            "(aadhaar_number IS NULL AND date_of_birth IS NULL "
            "AND gender IS NULL AND occupation IS NULL)",
            name=op.f("ck_parties_individual_fields_only"),
        ),
        sa.CheckConstraint(
            "party_type = 'organization' OR "
            "(registration_identifier IS NULL AND incorporation_date IS NULL)",
            name=op.f("ck_parties_organization_fields_only"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_parties_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "address_id"],
            ["addresses.organization_id", "addresses.id"],
            name="fk_parties_organization_id_addresses",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_parties_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_parties_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parties")),
        sa.UniqueConstraint("organization_id", "id", name="uq_parties_organization_id_id"),
    )
    op.create_index(
        op.f("ix_parties_organization_id"), "parties", ["organization_id"], unique=False
    )
    op.create_index(
        "ix_parties_organization_id_party_type",
        "parties",
        ["organization_id", "party_type"],
        unique=False,
    )
    op.create_index(
        "ix_parties_organization_id_display_name",
        "parties",
        ["organization_id", "display_name"],
        unique=False,
    )
    op.create_index(
        "ix_parties_organization_id_primary_phone",
        "parties",
        ["organization_id", "primary_phone"],
        unique=False,
    )
    op.create_index(
        "ix_parties_organization_id_primary_email",
        "parties",
        ["organization_id", "primary_email"],
        unique=False,
        postgresql_where=sa.text("primary_email IS NOT NULL"),
    )
    op.create_index(
        "ix_parties_organization_id_pan_number",
        "parties",
        ["organization_id", "pan_number"],
        unique=False,
        postgresql_where=sa.text("pan_number IS NOT NULL"),
    )
    op.create_index(
        "ix_parties_organization_id_aadhaar_number",
        "parties",
        ["organization_id", "aadhaar_number"],
        unique=False,
        postgresql_where=sa.text("aadhaar_number IS NOT NULL"),
    )
    op.create_index(
        "ix_parties_organization_id_gstin",
        "parties",
        ["organization_id", "gstin"],
        unique=False,
        postgresql_where=sa.text("gstin IS NOT NULL"),
    )
    op.create_index(
        "ix_parties_organization_id_registration_identifier",
        "parties",
        ["organization_id", "registration_identifier"],
        unique=False,
        postgresql_where=sa.text("registration_identifier IS NOT NULL"),
    )

    op.create_table(
        "matter_parties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("matter_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_matter_parties_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_matter_parties_organization_id_matters",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "party_id"],
            ["parties.organization_id", "parties.id"],
            name="fk_matter_parties_organization_id_parties",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_matter_parties_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_matter_parties_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matter_parties")),
        sa.UniqueConstraint(
            "matter_id", "party_id", "role", name="uq_matter_parties_matter_id_party_id_role"
        ),
    )
    op.create_index(
        op.f("ix_matter_parties_organization_id"),
        "matter_parties",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_matter_parties_matter_id"), "matter_parties", ["matter_id"], unique=False
    )
    op.create_index(
        op.f("ix_matter_parties_party_id"), "matter_parties", ["party_id"], unique=False
    )

    op.create_table(
        "client_party_migration_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("legacy_client_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("executor_version", sa.String(length=100), nullable=False),
        sa.Column("reconciliation_set_id", sa.String(length=255), nullable=False),
        sa.Column("source_report_sha256", sa.String(length=64), nullable=False),
        sa.Column("resolution_mode", sa.String(length=32), nullable=False),
        sa.Column("source_client_version", sa.Integer(), nullable=False),
        sa.Column("source_client_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=255), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("artifact_actor_type", sa.String(length=32), nullable=True),
        sa.Column("artifact_actor_id", sa.String(length=255), nullable=True),
        sa.Column("operator_note", sa.String(length=2000), nullable=True),
        sa.Column("execution_run_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "party_id = legacy_client_id",
            name=op.f("ck_client_party_migration_ledger_party_id_matches_legacy_client_id"),
        ),
        sa.CheckConstraint(
            "resolution_mode IN ('deterministic', 'operator_reconciled')",
            name=op.f("ck_client_party_migration_ledger_resolution_mode"),
        ),
        sa.ForeignKeyConstraint(
            ["legacy_client_id"],
            ["clients.id"],
            name=op.f("fk_client_party_migration_ledger_legacy_client_id_clients"),
        ),
        sa.ForeignKeyConstraint(
            ["party_id"],
            ["parties.id"],
            name=op.f("fk_client_party_migration_ledger_party_id_parties"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_client_party_migration_ledger_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_party_migration_ledger")),
        sa.UniqueConstraint(
            "legacy_client_id",
            "party_id",
            "organization_id",
            "executor_version",
            "reconciliation_set_id",
            "source_report_sha256",
            "source_fingerprint",
            name="uq_client_party_migration_ledger_identical_completion",
        ),
        sa.UniqueConstraint(
            "legacy_client_id",
            "executor_version",
            "reconciliation_set_id",
            "source_report_sha256",
            name="uq_client_party_migration_ledger_basis_collision",
        ),
    )
    op.create_index(
        "ix_client_party_migration_ledger_organization_id",
        "client_party_migration_ledger",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_client_party_migration_ledger_party_id",
        "client_party_migration_ledger",
        ["party_id"],
        unique=False,
    )
    op.create_index(
        "ix_client_party_migration_ledger_completed_at",
        "client_party_migration_ledger",
        ["completed_at"],
        unique=False,
    )
    op.create_index(
        "ix_client_party_migration_ledger_execution_run_id",
        "client_party_migration_ledger",
        ["execution_run_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop only the T116 schema foundation in dependency-safe order."""
    op.drop_index(
        "ix_client_party_migration_ledger_execution_run_id",
        table_name="client_party_migration_ledger",
    )
    op.drop_index(
        "ix_client_party_migration_ledger_completed_at", table_name="client_party_migration_ledger"
    )
    op.drop_index(
        "ix_client_party_migration_ledger_party_id", table_name="client_party_migration_ledger"
    )
    op.drop_index(
        "ix_client_party_migration_ledger_organization_id",
        table_name="client_party_migration_ledger",
    )
    op.drop_table("client_party_migration_ledger")
    op.drop_index(op.f("ix_matter_parties_party_id"), table_name="matter_parties")
    op.drop_index(op.f("ix_matter_parties_matter_id"), table_name="matter_parties")
    op.drop_index(op.f("ix_matter_parties_organization_id"), table_name="matter_parties")
    op.drop_table("matter_parties")
    op.drop_index("ix_parties_organization_id_registration_identifier", table_name="parties")
    op.drop_index("ix_parties_organization_id_gstin", table_name="parties")
    op.drop_index("ix_parties_organization_id_aadhaar_number", table_name="parties")
    op.drop_index("ix_parties_organization_id_pan_number", table_name="parties")
    op.drop_index("ix_parties_organization_id_primary_email", table_name="parties")
    op.drop_index("ix_parties_organization_id_primary_phone", table_name="parties")
    op.drop_index("ix_parties_organization_id_display_name", table_name="parties")
    op.drop_index("ix_parties_organization_id_party_type", table_name="parties")
    op.drop_index(op.f("ix_parties_organization_id"), table_name="parties")
    op.drop_table("parties")
