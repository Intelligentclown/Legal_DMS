"""Enquiry, quotation, and acceptance tenant/integrity foundation (T148)."""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e148c0f5a8b2"
down_revision: str | Sequence[str] | None = "cdcfd7df5fde"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT = "cdcfd7df5fde"
_GUC = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
_PROVENANCE_FUNCTIONS = (
    "legal_dms_provenance.record_fresh_birth(uuid,uuid)",
    "legal_dms_provenance.enter_operational_fresh(uuid)",
)
_PERMISSIONS = (
    ("enquiries:read", "View enquiries", "enquiries"),
    ("enquiries:write", "Create and edit enquiries", "enquiries"),
    ("quotations:read", "View quotations", "quotations"),
    ("quotations:write", "Create and revise quotations", "quotations"),
    ("quotations:accept", "Accept quotations", "quotations"),
)
_GRANTS = {
    "Administrator": tuple(code for code, _description, _category in _PERMISSIONS),
    "Advocate": tuple(code for code, _description, _category in _PERMISSIONS),
    "Paralegal": ("enquiries:read", "enquiries:write", "quotations:read", "quotations:write"),
    "Clerk": ("enquiries:read", "enquiries:write", "quotations:read"),
    "Accountant": ("enquiries:read", "quotations:read"),
    "Read Only": ("enquiries:read", "quotations:read"),
}


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


def _advance_provenance(from_revision: str, to_revision: str) -> None:
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


def _seed_permissions() -> None:
    connection = op.get_bind()
    roles = {
        row["name"]: row["id"]
        for row in connection.execute(sa.text("SELECT id, name FROM roles")).mappings()
    }
    if missing := set(_GRANTS) - set(roles):
        raise RuntimeError(f"roles missing for T148 permission grants: {sorted(missing)}")
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("category", sa.String()),
    )
    known = {
        row["code"]: row["id"]
        for row in connection.execute(sa.text("SELECT id, code FROM permissions")).mappings()
    }
    new_rows = [
        {"id": uuid.uuid4(), "code": code, "description": description, "category": category}
        for code, description, category in _PERMISSIONS
        if code not in known
    ]
    if new_rows:
        op.bulk_insert(permissions, new_rows)
    known = {
        row["code"]: row["id"]
        for row in connection.execute(sa.text("SELECT id, code FROM permissions")).mappings()
    }
    existing_grants = {
        (row["role_id"], row["permission_id"])
        for row in connection.execute(
            sa.text("SELECT role_id, permission_id FROM role_permissions")
        ).mappings()
    }
    role_permissions = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    rows = [
        {"id": uuid.uuid4(), "role_id": roles[role], "permission_id": known[code]}
        for role, codes in _GRANTS.items()
        for code in codes
        if (roles[role], known[code]) not in existing_grants
    ]
    if rows:
        op.bulk_insert(role_permissions, rows)


def upgrade() -> None:
    op.create_table(
        "enquiries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid()),
        sa.Column("prospect_display_name", sa.String(255)),
        sa.Column("prospect_phone", sa.String(20)),
        sa.Column("prospect_email", sa.String(255)),
        sa.Column("prospect_description", sa.String(2000)),
        sa.Column("prospect_source", sa.String(255)),
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
        sa.Column("created_by", sa.Uuid()),
        sa.Column("updated_by", sa.Uuid()),
        sa.CheckConstraint(
            "party_id IS NOT NULL OR prospect_display_name IS NOT NULL",
            name="ck_enquiries_party_or_prospect_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_enquiries_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "party_id"],
            ["parties.organization_id", "parties.id"],
            name="fk_enquiries_organization_id_parties",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_enquiries_created_by_users"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_enquiries_updated_by_users"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_enquiries_organization_id_id"),
    )
    op.create_index("ix_enquiries_organization_id", "enquiries", ["organization_id"])
    op.create_index("ix_enquiries_party_id", "enquiries", ["party_id"])
    op.create_index(
        "ix_enquiries_organization_id_party_id", "enquiries", ["organization_id", "party_id"]
    )
    op.create_table(
        "quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("enquiry_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid()),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_quotations_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "enquiry_id"],
            ["enquiries.organization_id", "enquiries.id"],
            name="fk_quotations_organization_id_enquiries",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_quotations_created_by_users"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_quotations_organization_id_id"),
        sa.UniqueConstraint(
            "organization_id",
            "enquiry_id",
            "id",
            name="uq_quotations_organization_id_enquiry_id_id",
        ),
    )
    op.create_index("ix_quotations_organization_id", "quotations", ["organization_id"])
    op.create_index("ix_quotations_enquiry_id", "quotations", ["enquiry_id"])
    op.create_index(
        "ix_quotations_organization_id_enquiry_id", "quotations", ["organization_id", "enquiry_id"]
    )
    op.create_table(
        "quotation_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("proposal_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("issued_by", sa.Uuid()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid()),
        sa.CheckConstraint("ordinal > 0", name="ck_quotation_revisions_ordinal_positive"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_quotation_revisions_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_quotation_revisions_organization_id_quotations",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"], ["users.id"], name="fk_quotation_revisions_issued_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_quotation_revisions_created_by_users"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_quotation_revisions_organization_id_id"
        ),
        sa.UniqueConstraint(
            "quotation_id", "ordinal", name="uq_quotation_revisions_quotation_id_ordinal"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "quotation_id",
            "id",
            name="uq_quotation_revisions_organization_id_quotation_id_id",
        ),
    )
    op.create_index(
        "ix_quotation_revisions_organization_id", "quotation_revisions", ["organization_id"]
    )
    op.create_index("ix_quotation_revisions_quotation_id", "quotation_revisions", ["quotation_id"])
    op.create_index(
        "ix_quotation_revisions_organization_id_quotation_id",
        "quotation_revisions",
        ["organization_id", "quotation_id"],
    )
    op.create_table(
        "acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("enquiry_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_revision_id", sa.Uuid(), nullable=False),
        sa.Column("matter_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_by", sa.Uuid(), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_acceptances_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "enquiry_id"],
            ["enquiries.organization_id", "enquiries.id"],
            name="fk_acceptances_organization_id_enquiries",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "enquiry_id", "quotation_id"],
            ["quotations.organization_id", "quotations.enquiry_id", "quotations.id"],
            name="fk_acceptances_organization_id_enquiry_id_quotations",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "quotation_id", "quotation_revision_id"],
            [
                "quotation_revisions.organization_id",
                "quotation_revisions.quotation_id",
                "quotation_revisions.id",
            ],
            name="fk_acceptances_organization_id_quotation_id_revisions",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_acceptances_organization_id_matters",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by"], ["users.id"], name="fk_acceptances_accepted_by_users"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_acceptances_organization_id_id"),
        sa.UniqueConstraint(
            "organization_id", "enquiry_id", name="uq_acceptances_organization_id_enquiry_id"
        ),
        sa.UniqueConstraint(
            "organization_id", "matter_id", name="uq_acceptances_organization_id_matter_id"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "quotation_revision_id",
            name="uq_acceptances_organization_id_quotation_revision_id",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "enquiry_id",
            "idempotency_key",
            name="uq_acceptances_organization_id_enquiry_id_idempotency_key",
        ),
    )
    for table, columns in (
        ("acceptances", ("organization_id",)),
        ("acceptances", ("enquiry_id",)),
        ("acceptances", ("quotation_id",)),
        ("acceptances", ("quotation_revision_id",)),
        ("acceptances", ("matter_id",)),
        ("acceptances", ("organization_id", "matter_id")),
    ):
        op.create_index("ix_" + table + "_" + "_".join(columns), table, list(columns))
    op.execute(
        "CREATE FUNCTION legal_dms_prevent_t148_evidence_mutation() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION "
        "'T148 quotation/acceptance evidence is immutable'; END; $$"
    )
    op.execute(
        "CREATE FUNCTION legal_dms_require_t148_acceptance_party() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN IF NOT EXISTS (SELECT 1 FROM enquiries "
        "WHERE id = NEW.enquiry_id AND organization_id = NEW.organization_id "
        "AND party_id IS NOT NULL) THEN RAISE EXCEPTION "
        "'T148 acceptance requires a canonical enquiry Party'; END IF; "
        "RETURN NEW; END; $$"
    )
    for table in ("quotation_revisions", "acceptances"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION legal_dms_prevent_t148_evidence_mutation()"
        )
    op.execute(
        "CREATE TRIGGER acceptances_require_party BEFORE INSERT ON acceptances "
        "FOR EACH ROW EXECUTE FUNCTION legal_dms_require_t148_acceptance_party()"
    )
    for table in ("enquiries", "quotations", "quotation_revisions", "acceptances"):
        _rls(table)
    _seed_permissions()
    _advance_provenance(_PARENT, revision)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM enquiries) "
            "OR EXISTS (SELECT 1 FROM quotations) "
            "OR EXISTS (SELECT 1 FROM quotation_revisions) "
            "OR EXISTS (SELECT 1 FROM acceptances)"
        )
    ).scalar_one():
        raise RuntimeError(
            "cannot downgrade T148 while pre-engagement or acceptance evidence exists"
        )
    permission_codes = tuple(code for code, _description, _category in _PERMISSIONS)
    connection.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN :codes)"
        ).bindparams(sa.bindparam("codes", expanding=True, value=permission_codes))
    )
    connection.execute(
        sa.text("DELETE FROM permissions WHERE code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True, value=permission_codes)
        )
    )
    for table in ("acceptances", "quotation_revisions", "quotations", "enquiries"):
        _rls(table, remove=True)
    op.drop_table("acceptances")
    op.drop_table("quotation_revisions")
    op.drop_table("quotations")
    op.drop_table("enquiries")
    op.execute("DROP FUNCTION legal_dms_prevent_t148_evidence_mutation()")
    op.execute("DROP FUNCTION legal_dms_require_t148_acceptance_party()")
    _advance_provenance(revision, _PARENT)
