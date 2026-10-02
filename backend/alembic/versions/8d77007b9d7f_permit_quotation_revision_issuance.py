"""Permit exactly one QuotationRevision issuance transition (T150)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8d77007b9d7f"
down_revision: str | Sequence[str] | None = "e148c0f5a8b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT = "e148c0f5a8b2"
_PROVENANCE_FUNCTIONS = (
    "legal_dms_provenance.record_fresh_birth(uuid,uuid)",
    "legal_dms_provenance.enter_operational_fresh(uuid)",
)


def _advance_provenance(from_revision: str, to_revision: str) -> None:
    """Preserve the existing provenance functions except for their head guard."""
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


def upgrade() -> None:
    op.execute("DROP TRIGGER quotation_revisions_immutable ON quotation_revisions")
    op.execute(
        "CREATE FUNCTION legal_dms_permit_t150_quotation_revision_issuance() "
        "RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN "
        "IF TG_OP = 'DELETE' THEN "
        "RAISE EXCEPTION 'QuotationRevision evidence is immutable'; "
        "END IF; "
        "IF OLD.issued_at IS NOT NULL OR OLD.issued_by IS NOT NULL THEN "
        "RAISE EXCEPTION 'QuotationRevision has already been issued and is immutable'; "
        "END IF; "
        "IF NEW.issued_at IS NULL OR NEW.issued_by IS NULL THEN "
        "RAISE EXCEPTION 'QuotationRevision issuance requires issued_at and issued_by together'; "
        "END IF; "
        "IF (to_jsonb(NEW) - ARRAY['issued_at', 'issued_by']) "
        "IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['issued_at', 'issued_by']) THEN "
        "RAISE EXCEPTION 'QuotationRevision issuance may not change evidence or identity fields'; "
        "END IF; "
        "RETURN NEW; "
        "END; $$"
    )
    op.execute(
        "CREATE TRIGGER quotation_revisions_immutable BEFORE UPDATE OR DELETE "
        "ON quotation_revisions FOR EACH ROW EXECUTE FUNCTION "
        "legal_dms_permit_t150_quotation_revision_issuance()"
    )
    _advance_provenance(_PARENT, revision)


def downgrade() -> None:
    op.execute("DROP TRIGGER quotation_revisions_immutable ON quotation_revisions")
    op.execute("DROP FUNCTION legal_dms_permit_t150_quotation_revision_issuance()")
    op.execute(
        "CREATE TRIGGER quotation_revisions_immutable BEFORE UPDATE OR DELETE "
        "ON quotation_revisions FOR EACH ROW EXECUTE FUNCTION "
        "legal_dms_prevent_t148_evidence_mutation()"
    )
    _advance_provenance(revision, _PARENT)
