"""File and Document tenant/compatibility schema foundation (T137)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# ruff: noqa: E501

revision: str = "b8c4d2e1f7a9"
down_revision: str | Sequence[str] | None = "9e6a4b2c8d1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT_REVISION = "9e6a4b2c8d1f"
_ORG_GUC = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
_PROVENANCE_FUNCTIONS = (
    "legal_dms_provenance.record_fresh_birth(uuid,uuid)",
    "legal_dms_provenance.enter_operational_fresh(uuid)",
)


def _advance_provenance_guard(from_revision: str, to_revision: str) -> None:
    connection = op.get_bind()
    for signature in _PROVENANCE_FUNCTIONS:
        definition = connection.execute(
            sa.text("SELECT pg_get_functiondef(CAST(:signature AS regprocedure))").bindparams(
                signature=signature
            )
        ).scalar_one()
        if from_revision not in definition:
            raise RuntimeError("unexpected operational-fresh provenance function contract")
        op.execute(sa.text(definition.replace(from_revision, to_revision)))


def _install_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (organization_id = {_ORG_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK (organization_id = {_ORG_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_update ON {table} FOR UPDATE USING (organization_id = {_ORG_GUC}) WITH CHECK (organization_id = {_ORG_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_delete ON {table} FOR DELETE USING (organization_id = {_ORG_GUC})"
    )


def _remove_rls(table: str) -> None:
    for action in ("delete", "update", "insert", "select"):
        op.execute(f"DROP POLICY IF EXISTS {table}_{action} ON {table}")
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def _assert_document_organization_evidence() -> None:
    op.execute(sa.text("""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM documents d
            LEFT JOIN matters m ON m.id = d.matter_id
            LEFT JOIN organizations o ON o.id = m.organization_id
            WHERE m.id IS NULL OR m.organization_id IS NULL OR o.id IS NULL
          ) THEN
            RAISE EXCEPTION 'cannot backfill Document organization: Matter ownership evidence is missing or contradictory';
          END IF;
        END $$;
    """))


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("matter_id", sa.Uuid(), nullable=False),
        sa.Column("file_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
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
            ["created_by"], ["users.id"], name=op.f("fk_files_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_files_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_files_organization_id_matters",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_files_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_files")),
        sa.UniqueConstraint("organization_id", "id", name="uq_files_organization_id_id"),
        sa.UniqueConstraint(
            "organization_id", "matter_id", "id", name="uq_files_organization_id_matter_id_id"
        ),
        sa.UniqueConstraint("matter_id", "file_number", name="uq_files_matter_id_file_number"),
    )
    op.create_index(op.f("ix_files_organization_id"), "files", ["organization_id"], unique=False)
    op.create_index(op.f("ix_files_matter_id"), "files", ["matter_id"], unique=False)
    op.create_table(
        "file_number_sequences",
        sa.Column("matter_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "next_number > 0", name=op.f("ck_file_number_sequences_next_number_positive")
        ),
        sa.ForeignKeyConstraint(
            ["matter_id"], ["matters.id"], name=op.f("fk_file_number_sequences_matter_id_matters")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_file_number_sequences_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_file_number_sequences_organization_id_matters",
        ),
        sa.PrimaryKeyConstraint("matter_id", name=op.f("pk_file_number_sequences")),
        sa.UniqueConstraint(
            "organization_id",
            "matter_id",
            name="uq_file_number_sequences_organization_id_matter_id",
        ),
    )
    op.create_index(
        op.f("ix_file_number_sequences_organization_id"),
        "file_number_sequences",
        ["organization_id"],
        unique=False,
    )

    op.add_column("documents", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.add_column("documents", sa.Column("file_id", sa.Uuid(), nullable=True))
    _assert_document_organization_evidence()
    op.execute(
        "UPDATE documents d SET organization_id = m.organization_id FROM matters m WHERE m.id = d.matter_id"
    )
    if (
        op.get_bind()
        .execute(sa.text("SELECT EXISTS (SELECT 1 FROM documents WHERE organization_id IS NULL)"))
        .scalar_one()
    ):
        raise RuntimeError("cannot finalize Document organization backfill")
    op.alter_column("documents", "organization_id", nullable=False, existing_nullable=True)
    op.create_index(
        op.f("ix_documents_organization_id"), "documents", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_documents_file_id"), "documents", ["file_id"], unique=False)
    op.create_unique_constraint(
        "uq_documents_organization_id_id", "documents", ["organization_id", "id"]
    )
    op.create_foreign_key(
        op.f("fk_documents_organization_id_organizations"),
        "documents",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_documents_organization_id_matters",
        "documents",
        "matters",
        ["organization_id", "matter_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_documents_organization_id_matter_id_files",
        "documents",
        "files",
        ["organization_id", "matter_id", "file_id"],
        ["organization_id", "matter_id", "id"],
    )

    for table in ("files", "file_number_sequences", "documents"):
        _install_rls(table)
    _advance_provenance_guard(_PARENT_REVISION, revision)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM files) OR EXISTS (SELECT 1 FROM file_number_sequences) OR EXISTS (SELECT 1 FROM documents WHERE file_id IS NOT NULL) "
        )
    ).scalar_one():
        raise RuntimeError(
            "cannot downgrade T137 while File identity, number history, or Document File assignments exist"
        )
    for table in ("documents", "file_number_sequences", "files"):
        _remove_rls(table)
    op.drop_constraint(
        "fk_documents_organization_id_matter_id_files", "documents", type_="foreignkey"
    )
    op.drop_constraint("fk_documents_organization_id_matters", "documents", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_documents_organization_id_organizations"), "documents", type_="foreignkey"
    )
    op.drop_constraint("uq_documents_organization_id_id", "documents", type_="unique")
    op.drop_index(op.f("ix_documents_file_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_organization_id"), table_name="documents")
    op.drop_column("documents", "file_id")
    op.drop_column("documents", "organization_id")
    op.drop_index(
        op.f("ix_file_number_sequences_organization_id"), table_name="file_number_sequences"
    )
    op.drop_table("file_number_sequences")
    op.drop_index(op.f("ix_files_matter_id"), table_name="files")
    op.drop_index(op.f("ix_files_organization_id"), table_name="files")
    op.drop_table("files")
    _advance_provenance_guard(revision, _PARENT_REVISION)
