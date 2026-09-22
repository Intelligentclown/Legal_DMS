"""T132 Matter tenant finalization and Party-canonical foundation.

The only authorized legacy ownership derivation is ``Matter.client_id`` to
``Client.organization_id``.  MatterParty, Party, and Property are validation
evidence only: none can supply an Organization for a NULL-org Matter.
"""

# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7f1b9c3d4a2e"
down_revision: str | Sequence[str] | None = "5d8a3f2e9c6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT_REVISION = "5d8a3f2e9c6b"
_ORG_GUC = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
_PROVENANCE_FUNCTIONS = (
    "legal_dms_provenance.record_fresh_birth(uuid,uuid)",
    "legal_dms_provenance.enter_operational_fresh(uuid)",
)


def _advance_provenance_guard(from_revision: str, to_revision: str) -> None:
    """Preserve T126/T130's functions verbatim except for their head guard."""
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


def _fail_closed_legacy_evidence() -> None:
    """Reject ambiguity/conflict before changing the Matter tenant boundary."""
    op.execute(sa.text("""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM matters m
                LEFT JOIN clients c ON c.id = m.client_id
                WHERE m.organization_id IS NULL
                  AND (m.client_id IS NULL OR c.id IS NULL OR c.organization_id IS NULL)
              ) THEN
                RAISE EXCEPTION 'cannot finalize Matter organization: NULL ownership lacks Client-derived organization evidence';
              END IF;
              IF EXISTS (
                SELECT 1 FROM matters m JOIN clients c ON c.id = m.client_id
                WHERE m.organization_id IS NOT NULL AND m.client_id IS NOT NULL
                  AND m.organization_id IS DISTINCT FROM c.organization_id
              ) THEN
                RAISE EXCEPTION 'cannot finalize Matter organization: Matter and Client organizations conflict';
              END IF;
              IF EXISTS (
                SELECT 1 FROM matter_parties mp JOIN matters m ON m.id = mp.matter_id
                WHERE mp.organization_id IS DISTINCT FROM m.organization_id
              ) THEN
                RAISE EXCEPTION 'cannot finalize Matter organization: MatterParty organization conflicts with Matter';
              END IF;
              IF EXISTS (
                SELECT 1 FROM matter_parties mp JOIN parties p ON p.id = mp.party_id
                WHERE mp.organization_id IS DISTINCT FROM p.organization_id
              ) THEN
                RAISE EXCEPTION 'cannot finalize Matter organization: MatterParty organization conflicts with Party';
              END IF;
              IF EXISTS (
                SELECT 1 FROM matters m JOIN properties p ON p.id = m.property_id
                WHERE m.organization_id IS NOT NULL AND p.organization_id IS NOT NULL
                  AND m.organization_id IS DISTINCT FROM p.organization_id
              ) THEN
                RAISE EXCEPTION 'cannot finalize Matter organization: Property organization conflicts with Matter';
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
    _fail_closed_legacy_evidence()
    # This update is deliberately the sole ownership derivation in this migration.
    op.execute(
        "UPDATE matters AS m SET organization_id = c.organization_id "
        "FROM clients AS c WHERE m.organization_id IS NULL AND m.client_id = c.id"
    )
    op.alter_column("matters", "organization_id", nullable=False, existing_nullable=True)
    op.alter_column("matters", "client_id", nullable=True, existing_nullable=False)
    _install_rls("matters")
    _install_rls("matter_parties")
    _advance_provenance_guard(_PARENT_REVISION, revision)


def downgrade() -> None:
    # No Client identity is invented.  A Party-canonical Matter without the
    # compatibility shadow correctly prevents downgrade rather than corrupting evidence.
    op.alter_column("matters", "client_id", nullable=False, existing_nullable=True)
    for table in ("matter_parties", "matters"):
        for action in ("delete", "update", "insert", "select"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.alter_column("matters", "organization_id", nullable=True, existing_nullable=False)
    _advance_provenance_guard(revision, _PARENT_REVISION)
