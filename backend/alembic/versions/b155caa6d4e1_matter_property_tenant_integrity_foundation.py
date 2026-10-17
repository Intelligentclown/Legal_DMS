"""MatterProperty tenant and integrity schema foundation (T155)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b155caa6d4e1"
down_revision: str | Sequence[str] | None = "8d77007b9d7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT = "8d77007b9d7f"
_GUC = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
_PROVENANCE_FUNCTIONS = (
    "legal_dms_provenance.record_fresh_birth(uuid,uuid)",
    "legal_dms_provenance.enter_operational_fresh(uuid)",
)


def _advance_provenance(from_revision: str, to_revision: str) -> None:
    """Preserve operational-fresh guards while advancing their sole head."""
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


def _rls(*, remove: bool = False) -> None:
    table = "matter_properties"
    if remove:
        for action in ("delete", "update", "insert", "select"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        return
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (organization_id = {_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK (organization_id = {_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_update ON {table} FOR UPDATE "
        f"USING (organization_id = {_GUC}) WITH CHECK (organization_id = {_GUC})"
    )
    op.execute(
        f"CREATE POLICY {table}_delete ON {table} FOR DELETE USING (organization_id = {_GUC})"
    )


def upgrade() -> None:
    op.create_table(
        "matter_properties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("matter_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
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
            name="fk_matter_properties_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_matter_properties_organization_id_matters",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["properties.organization_id", "properties.id"],
            name="fk_matter_properties_organization_id_properties",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_matter_properties_created_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name="fk_matter_properties_updated_by_users"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_matter_properties_organization_id_id"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "matter_id",
            "property_id",
            name="uq_matter_properties_organization_id_matter_id_property_id",
        ),
    )
    for columns in (
        ("organization_id",),
        ("matter_id",),
        ("property_id",),
        ("organization_id", "matter_id"),
        ("organization_id", "property_id"),
    ):
        op.create_index(
            "ix_matter_properties_" + "_".join(columns), "matter_properties", list(columns)
        )
    _rls()
    _advance_provenance(_PARENT, revision)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT EXISTS (SELECT 1 FROM matter_properties)")).scalar_one():
        raise RuntimeError("cannot downgrade T155 while canonical MatterProperty rows exist")
    _rls(remove=True)
    for columns in (
        ("organization_id", "property_id"),
        ("organization_id", "matter_id"),
        ("property_id",),
        ("matter_id",),
        ("organization_id",),
    ):
        op.drop_index("ix_matter_properties_" + "_".join(columns), table_name="matter_properties")
    op.drop_table("matter_properties")
    _advance_provenance(revision, _PARENT)
