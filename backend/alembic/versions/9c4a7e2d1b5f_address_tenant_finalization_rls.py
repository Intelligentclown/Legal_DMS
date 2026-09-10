"""Address tenant finalization + Organization-scoped RLS backstop (T122)

Finalizes the tenant boundary for `addresses` per ADR-0021 (Organization is
the tenant boundary) and ADR-0036 (Decision 4: address finalization is the
`organization_id`-NOT-NULL constraint boundary), with a default-deny, GUC-
driven Row Level Security backstop enforced through the non-owning,
non-bypass application role.

Two operations:

1. **Finalization** — `addresses.organization_id` becomes `NOT NULL`. This is
   deliberately a fail-closed constraint: if any legacy `addresses` row still
   has a NULL `organization_id`, the `ALTER COLUMN ... SET NOT NULL` raises
   `contains null values` and the whole migration aborts (nothing is
   backfilled or deleted, and nothing else in this migration runs). Positive
   validation therefore runs only against a genuinely fresh, disposable
   database (T122's queue row's precondition), never the shared development
   database and never production data.

2. **RLS backstop** — `addresses` gains `ENABLE` + `FORCE ROW LEVEL SECURITY`
   plus exactly four default-deny policies (`addresses_select` /
   `addresses_insert` / `addresses_update` / `addresses_delete`), each scoped
   by the Organization GUC that T105 introduced:

       organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid

   With no GUC set the `NULLIF` guards make the expression evaluate to "no
   match", so every command is denied by default (SELECT/UPDATE/DELETE use
   `USING`; INSERT/UPDATE use `WITH CHECK`). With a GUC set, only rows of the
   caller's own Organization are selectable/updatable/deletable and only same-
   Organization inserts are permitted. `FORCE` makes the policies a genuine
   backstop for the non-owning `legal_dms_app` runtime role (which is neither
   `SUPERUSER` nor `BYPASSRLS`). The owning/admin role and Alembic are
   Postgres superusers in the standard deployment and bypass RLS entirely, so
   migration history administration is unaffected. The existing same-Org
   `(organization_id, id)` support key and all composite Address relationships
   (`fk_clients_organization_id_addresses`,
   `fk_parties_organization_id_addresses`,
   `fk_properties_organization_id_addresses`, plus the T120 dependency chain)
   are preserved unchanged.

Revision ID: 9c4a7e2d1b5f
Revises: f3b7c9d1e2a4
Create Date: 2026-09-10

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4a7e2d1b5f"
down_revision: str | Sequence[str] | None = "f3b7c9d1e2a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same null-safe GUC pattern T105's organizations/users policies use: a custom
# GUC that has already been `set_config()`-ed (even with NULL) reads back as an
# empty string, not SQL NULL, so `NULLIF(..., '')` is required before the cast
# to keep the "no context => default deny" property under connection pooling.
_ORG_GUC = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"


def upgrade() -> None:
    """Finalize `addresses.organization_id` and enforce its RLS backstop."""
    # Fail closed on any legacy NULL-org Address (postgres raises "contains
    # null values" here first; nothing else in this migration has run yet).
    op.alter_column(
        "addresses",
        "organization_id",
        nullable=False,
        existing_nullable=True,
    )

    op.execute("ALTER TABLE addresses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE addresses FORCE ROW LEVEL SECURITY")

    op.execute(
        "CREATE POLICY addresses_select ON addresses "
        f"FOR SELECT USING (organization_id = {_ORG_GUC})"
    )
    # INSERT/UPDATE with CHECK so a caller can never write a row into another
    # Organization (or an Organization they do not currently hold context for).
    op.execute(
        "CREATE POLICY addresses_insert ON addresses "
        f"FOR INSERT WITH CHECK (organization_id = {_ORG_GUC})"
    )
    op.execute(
        "CREATE POLICY addresses_update ON addresses "
        f"FOR UPDATE USING (organization_id = {_ORG_GUC}) "
        f"WITH CHECK (organization_id = {_ORG_GUC})"
    )
    op.execute(
        "CREATE POLICY addresses_delete ON addresses "
        f"FOR DELETE USING (organization_id = {_ORG_GUC})"
    )


def downgrade() -> None:
    """Restore T120's contract: nullable `organization_id`, no Address RLS."""
    op.execute("DROP POLICY IF EXISTS addresses_delete ON addresses")
    op.execute("DROP POLICY IF EXISTS addresses_update ON addresses")
    op.execute("DROP POLICY IF EXISTS addresses_insert ON addresses")
    op.execute("DROP POLICY IF EXISTS addresses_select ON addresses")
    op.execute("ALTER TABLE addresses NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE addresses DISABLE ROW LEVEL SECURITY")

    op.alter_column(
        "addresses",
        "organization_id",
        nullable=True,
        existing_nullable=False,
    )
