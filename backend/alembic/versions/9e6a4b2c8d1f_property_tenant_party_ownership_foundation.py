"""T133 Property tenant and Party-canonical ownership foundation.

Property ownership is derived only from already-governed, directly related
Organization evidence.  A missing or conflicting candidate aborts before any
write.  Client remains an optional compatibility/evidence shadow; this
migration never creates Client or Party identity.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# SQL migration predicates are retained verbatim for auditability; this is the
# same approved migration-file E501 convention used by the T132 predecessor.
# ruff: noqa: E501

revision: str = "9e6a4b2c8d1f"
down_revision: str | Sequence[str] | None = "7f1b9c3d4a2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT_REVISION = "7f1b9c3d4a2e"
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


def _fail_closed_property_evidence() -> None:
    # Candidates are only direct governed relationships: retained Property
    # ownership, finalized Address, finalized Matter, and owner Client/Party.
    # A singleton candidate is authoritative; zero or multiple candidates are
    # deliberately not guessed.
    op.execute(sa.text("""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM properties p
            CROSS JOIN LATERAL (
              SELECT count(DISTINCT candidate) AS candidates
              FROM (
                SELECT p.organization_id AS candidate
                UNION ALL SELECT a.organization_id FROM addresses a WHERE a.id = p.address_id
                UNION ALL SELECT m.organization_id FROM matters m WHERE m.property_id = p.id
                UNION ALL SELECT po.organization_id FROM property_owners po WHERE po.property_id = p.id
                UNION ALL SELECT c.organization_id FROM property_owners po JOIN clients c ON c.id = po.client_id WHERE po.property_id = p.id
                UNION ALL SELECT pa.organization_id FROM property_owners po JOIN parties pa ON pa.id = po.party_id WHERE po.property_id = p.id
              ) evidence WHERE candidate IS NOT NULL
            ) e
            WHERE e.candidates <> 1
          ) THEN
            RAISE EXCEPTION 'cannot finalize Property organization: ownership evidence is missing or contradictory';
          END IF;
          IF EXISTS (
            SELECT 1 FROM property_owners po
            LEFT JOIN properties p ON p.id = po.property_id
            LEFT JOIN clients c ON c.id = po.client_id
            LEFT JOIN parties pa ON pa.id = po.party_id
            WHERE p.id IS NULL
              OR (po.client_id IS NOT NULL AND (c.id IS NULL OR c.organization_id IS NULL))
              OR (po.party_id IS NOT NULL AND (pa.id IS NULL OR pa.organization_id IS NULL))
              OR (p.organization_id IS NOT NULL AND po.organization_id IS NOT NULL AND po.organization_id IS DISTINCT FROM p.organization_id)
              OR (p.organization_id IS NOT NULL AND po.client_id IS NOT NULL AND c.organization_id IS DISTINCT FROM p.organization_id)
              OR (p.organization_id IS NOT NULL AND po.party_id IS NOT NULL AND pa.organization_id IS DISTINCT FROM p.organization_id)
          ) THEN
            RAISE EXCEPTION 'cannot finalize PropertyOwner organization: reference organizations conflict or lack evidence';
          END IF;
        END $$;
    """))


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


def upgrade() -> None:
    _fail_closed_property_evidence()
    op.execute(sa.text("""
        WITH evidence AS (
          SELECT p.id, min(candidate::text)::uuid AS organization_id
          FROM properties p
          CROSS JOIN LATERAL (
            SELECT p.organization_id AS candidate
            UNION ALL SELECT a.organization_id FROM addresses a WHERE a.id = p.address_id
            UNION ALL SELECT m.organization_id FROM matters m WHERE m.property_id = p.id
            UNION ALL SELECT po.organization_id FROM property_owners po WHERE po.property_id = p.id
            UNION ALL SELECT c.organization_id FROM property_owners po JOIN clients c ON c.id = po.client_id WHERE po.property_id = p.id
            UNION ALL SELECT pa.organization_id FROM property_owners po JOIN parties pa ON pa.id = po.party_id WHERE po.property_id = p.id
          ) candidates
          WHERE candidate IS NOT NULL
          GROUP BY p.id
        )
        UPDATE properties p SET organization_id = evidence.organization_id
        FROM evidence WHERE p.id = evidence.id AND p.organization_id IS NULL
    """))
    op.execute(
        "UPDATE property_owners po SET organization_id = p.organization_id FROM properties p WHERE p.id = po.property_id AND po.organization_id IS NULL"
    )
    op.alter_column("properties", "organization_id", nullable=False, existing_nullable=True)
    op.alter_column("property_owners", "organization_id", nullable=False, existing_nullable=True)
    op.alter_column("property_owners", "client_id", nullable=True, existing_nullable=False)
    _install_rls("properties")
    _install_rls("property_owners")
    _advance_provenance_guard(_PARENT_REVISION, revision)


def downgrade() -> None:
    # Party-only ownership cannot be represented before T133.  Refuse rather
    # than fabricate Client evidence.
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM property_owners WHERE party_id IS NOT NULL AND client_id IS NULL)"
        )
    ).scalar_one():
        raise RuntimeError("cannot downgrade T133 while Party-only PropertyOwner rows exist")
    op.alter_column("property_owners", "client_id", nullable=False, existing_nullable=True)
    for table in ("property_owners", "properties"):
        for action in ("delete", "update", "insert", "select"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.alter_column("property_owners", "organization_id", nullable=True, existing_nullable=False)
    op.alter_column("properties", "organization_id", nullable=True, existing_nullable=False)
    _advance_provenance_guard(revision, _PARENT_REVISION)
