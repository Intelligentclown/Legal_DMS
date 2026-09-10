"""Party Organization-scoped RLS backstop (T123)

Adds the default-deny, GUC-driven Row Level Security backstop for `parties`,
closing the last hold-out tenant table per ADR-0021 (Organization is the
tenant boundary), ADR-0035 (Decision 5: Party must have forced default-deny
RLS before it becomes a normal application-visible table), and ADR-0036.

`parties.organization_id` is already `NOT NULL` since T116, so this migration
needs no column change: it only installs the RLS backstop itself.

Scope is exactly the four Party commands — the same `parties_select` /
`parties_insert` / `parties_update` / `parties_delete` default-deny policy
surface T105/T122 already established for `organizations`/`users`/`addresses`:

    ENABLE + FORCE ROW LEVEL SECURITY
    exactly four policies:
        parties_select  FOR SELECT USING (organization_id = _ORG_GUC)
        parties_insert  FOR INSERT WITH CHECK (organization_id = _ORG_GUC)
        parties_update  FOR UPDATE USING + WITH CHECK (organization_id = _ORG_GUC)
        parties_delete  FOR DELETE USING (organization_id = _ORG_GUC)

With no GUC set the `NULLIF` guard makes the expression evaluate to "no
match", so every command is denied by default. With a GUC set, only rows of
the caller's own Organization are visible/updatable/deletable and only same-
Organization inserts are permitted. `FORCE` makes the policies a genuine
backstop for the non-owning `legal_dms_app` runtime role (neither `SUPERUSER`
nor `BYPASSRLS`). The owning/admin role and Alembic are Postgres superusers in
the standard deployment and bypass RLS entirely, so the T118 migration
executor's owning-path writes are unaffected.

`matter_parties`, `client_party_migration_ledger`, `clients`, `properties`,
`addresses`, `organizations`, and `users` are intentionally untouched.

Revision ID: 62cadaff2571
Revises: 9c4a7e2d1b5f
Create Date: 2026-09-10 14:08:44.046348

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "62cadaff2571"
down_revision: str | Sequence[str] | None = "9c4a7e2d1b5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same null-safe GUC pattern T105's organizations/users policies and T122's
# addresses policies use: a custom GUC that has already been `set_config()`-ed
# (even with NULL) reads back as an empty string, not SQL NULL, so
# `NULLIF(..., '')` is required before the cast to keep the "no context =>
# default deny" property under connection pooling.
_ORG_GUC = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"


def upgrade() -> None:
    """Enforce Party's Organization-scoped RLS backstop."""
    op.execute("ALTER TABLE parties ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE parties FORCE ROW LEVEL SECURITY")

    op.execute(
        "CREATE POLICY parties_select ON parties "
        f"FOR SELECT USING (organization_id = {_ORG_GUC})"
    )
    # INSERT/UPDATE with CHECK so a caller can never write a row into another
    # Organization (or an Organization they do not currently hold context for).
    op.execute(
        "CREATE POLICY parties_insert ON parties "
        f"FOR INSERT WITH CHECK (organization_id = {_ORG_GUC})"
    )
    op.execute(
        "CREATE POLICY parties_update ON parties "
        f"FOR UPDATE USING (organization_id = {_ORG_GUC}) "
        f"WITH CHECK (organization_id = {_ORG_GUC})"
    )
    op.execute(
        "CREATE POLICY parties_delete ON parties "
        f"FOR DELETE USING (organization_id = {_ORG_GUC})"
    )


def downgrade() -> None:
    """Restore T116's contract: no Party RLS. All rows are preserved."""
    op.execute("DROP POLICY IF EXISTS parties_delete ON parties")
    op.execute("DROP POLICY IF EXISTS parties_update ON parties")
    op.execute("DROP POLICY IF EXISTS parties_insert ON parties")
    op.execute("DROP POLICY IF EXISTS parties_select ON parties")
    op.execute("ALTER TABLE parties NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE parties DISABLE ROW LEVEL SECURITY")
