"""Document Version / Storage tenant and integrity foundation (T141)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cdcfd7df5fde"
down_revision: str | Sequence[str] | None = "be439c0d6fdb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT = "be439c0d6fdb"
_GUC = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"


def _provenance(old: str, new: str) -> None:
    signatures = (
        "legal_dms_provenance.record_fresh_birth(uuid,uuid)",
        "legal_dms_provenance.enter_operational_fresh(uuid)",
    )
    for signature in signatures:
        statement = sa.text("SELECT pg_get_functiondef(CAST(:s AS regprocedure))")
        definition = op.get_bind().execute(statement.bindparams(s=signature)).scalar_one()
        if old not in definition:
            raise RuntimeError("unexpected operational-fresh provenance function contract")
        op.execute(sa.text(definition.replace(old, new)))


def _rls(table: str, *, remove: bool = False) -> None:
    if remove:
        for action in ("delete", "update", "insert", "select"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        return
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_select ON {table} FOR SELECT " f"USING (organization_id = {_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_insert ON {table} FOR INSERT "
        f"WITH CHECK (organization_id = {_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_update ON {table} FOR UPDATE "
        f"USING (organization_id = {_GUC}) WITH CHECK (organization_id = {_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_delete ON {table} FOR DELETE " f"USING (organization_id = {_GUC})"
    )


def _assert_backfill_evidence() -> None:
    op.execute(sa.text("""\
            DO $$ BEGIN
              IF EXISTS (
                SELECT 1 FROM document_versions dv
                LEFT JOIN documents d ON d.id = dv.document_id
                WHERE d.organization_id IS NULL
              ) THEN
                RAISE EXCEPTION
                  'cannot backfill DocumentVersion organization: invalid ownership evidence';
              END IF;
              IF EXISTS (
                SELECT 1 FROM document_versions a JOIN document_versions b
                  ON a.file_storage_record_id = b.file_storage_record_id AND a.id <> b.id
              ) THEN
                RAISE EXCEPTION
                  'cannot establish exclusive DocumentVersion FileStorageRecord ownership';
              END IF;
              IF EXISTS (
                SELECT 1 FROM document_versions dv
                WHERE EXISTS (
                  SELECT 1 FROM document_templates t
                  WHERE t.file_storage_record_id = dv.file_storage_record_id
                ) OR EXISTS (
                  SELECT 1 FROM qr_code_records q
                  WHERE q.qr_image_file_storage_record_id = dv.file_storage_record_id
                ) OR EXISTS (
                  SELECT 1 FROM receipts r
                  WHERE r.file_storage_record_id = dv.file_storage_record_id
                )
              ) THEN
                RAISE EXCEPTION
                  'cannot backfill storage organization: storage has a non-version consumer';
              END IF;
            END $$;
            """))


def upgrade() -> None:
    op.add_column("file_storage_records", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.add_column("document_versions", sa.Column("organization_id", sa.Uuid(), nullable=True))
    _assert_backfill_evidence()
    op.execute(
        "UPDATE document_versions dv SET organization_id = d.organization_id "
        "FROM documents d WHERE d.id = dv.document_id"
    )
    op.execute(
        "UPDATE file_storage_records fsr SET organization_id = d.organization_id "
        "FROM document_versions dv JOIN documents d ON d.id = dv.document_id "
        "WHERE fsr.id = dv.file_storage_record_id"
    )
    op.alter_column("document_versions", "organization_id", nullable=False, existing_nullable=True)
    op.create_unique_constraint(
        "uq_file_storage_records_organization_id_id",
        "file_storage_records",
        ["organization_id", "id"],
    )
    op.create_index(
        "ix_file_storage_records_organization_id", "file_storage_records", ["organization_id"]
    )
    op.create_foreign_key(
        "fk_file_storage_records_organization_id_organizations",
        "file_storage_records",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_document_versions_organization_id_id", "document_versions", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_document_versions_organization_id_file_storage_record_id",
        "document_versions",
        ["organization_id", "file_storage_record_id"],
    )
    op.create_index(
        "ix_document_versions_organization_id", "document_versions", ["organization_id"]
    )
    op.create_foreign_key(
        "fk_document_versions_organization_id_organizations",
        "document_versions",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_document_versions_organization_id_documents",
        "document_versions",
        "documents",
        ["organization_id", "document_id"],
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_document_versions_organization_id_file_storage_records",
        "document_versions",
        "file_storage_records",
        ["organization_id", "file_storage_record_id"],
        ["organization_id", "id"],
    )
    op.create_table(
        "document_version_idempotency_keys",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("payload_fingerprint", sa.String(64), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_dv_idempotency_org_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "document_id"],
            ["documents.organization_id", "documents.id"],
            name="fk_dv_idempotency_org_documents",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "document_version_id"],
            ["document_versions.organization_id", "document_versions.id"],
            name="fk_dv_idempotency_org_document_versions",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "document_id",
            "idempotency_key",
            name="uq_document_version_idempotency_keys_scope_key",
        ),
    )
    op.create_index(
        "ix_document_version_idempotency_keys_organization_id",
        "document_version_idempotency_keys",
        ["organization_id"],
    )
    op.create_index(
        "ix_document_version_idempotency_keys_document_id",
        "document_version_idempotency_keys",
        ["document_id"],
    )
    op.create_index(
        "ix_document_version_idempotency_keys_document_version_id",
        "document_version_idempotency_keys",
        ["document_version_id"],
    )
    for table in ("file_storage_records", "document_versions", "document_version_idempotency_keys"):
        _rls(table)
    _provenance(_PARENT, revision)


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM document_versions) "
                "OR EXISTS (SELECT 1 FROM document_version_idempotency_keys) "
                "OR EXISTS (SELECT 1 FROM file_storage_records WHERE organization_id IS NOT NULL)"
            )
        )
        .scalar_one()
    ):
        raise RuntimeError(
            "cannot downgrade T141 while tenant-owned version, storage, "
            "or idempotency evidence exists"
        )
    for table in (
        "document_version_idempotency_keys",
        "document_versions",
        "file_storage_records",
    ):
        _rls(table, remove=True)
    op.drop_index(
        "ix_document_version_idempotency_keys_document_version_id",
        table_name="document_version_idempotency_keys",
    )
    op.drop_index(
        "ix_document_version_idempotency_keys_document_id",
        table_name="document_version_idempotency_keys",
    )
    op.drop_index(
        "ix_document_version_idempotency_keys_organization_id",
        table_name="document_version_idempotency_keys",
    )
    op.drop_table("document_version_idempotency_keys")
    op.drop_constraint(
        "fk_document_versions_organization_id_file_storage_records",
        "document_versions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_document_versions_organization_id_documents", "document_versions", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_document_versions_organization_id_organizations",
        "document_versions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_document_versions_organization_id_file_storage_record_id",
        "document_versions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_document_versions_organization_id_id", "document_versions", type_="unique"
    )
    op.drop_index("ix_document_versions_organization_id", table_name="document_versions")
    op.drop_column("document_versions", "organization_id")
    op.drop_constraint(
        "fk_file_storage_records_organization_id_organizations",
        "file_storage_records",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_file_storage_records_organization_id_id", "file_storage_records", type_="unique"
    )
    op.drop_index("ix_file_storage_records_organization_id", table_name="file_storage_records")
    op.drop_column("file_storage_records", "organization_id")
    _provenance(revision, _PARENT)
