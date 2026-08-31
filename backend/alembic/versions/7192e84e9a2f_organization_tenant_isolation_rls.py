"""organization/users tenant-isolation RLS + legal_dms_app grants (T105/ADR-0021)

Pure DDL/DCL -- references the `legal_dms_app` role **by name only**. No
`CREATE ROLE`, no password, anywhere in this file. That role must already
exist before this migration runs -- provisioned by the separate, idempotent
`uv run provision-app-role` command (infrastructure/cli/provision_app_role.py),
never by Alembic (mixing "repeatable schema history" with "one-time secret
provisioning" is exactly the anti-pattern this split avoids). If the role is
missing, this migration fails loudly with a clear message rather than a raw
grant-target-does-not-exist error.

Grants are deliberately asymmetric across tables (see the plan's SS D):
`organizations` gets SELECT only (no route ever writes to it through this
role -- bootstrap-admin/the reconciliation CLI both run via the admin/owning
`database_url` role, which is a Postgres superuser and bypasses RLS
entirely, per ADR/0021's "administrative/system-level operations... explicit
system context" carve-out). `users` gets SELECT/INSERT/UPDATE (no DELETE --
nothing deletes a User row; deactivation is an UPDATE of is_active). Every
other existing table keeps the broad DML grant `get_db()` already needs as
the app's shared, general-purpose dependency -- this grant is plain DML
access, carries no row-level filtering, and does NOT make those tables
tenant-isolated. RLS (ENABLE/FORCE/POLICY) in this migration touches
exactly two tables: `organizations` and `users`. No other table gains any
row-level restriction.

The `users_insert` policy is intentionally narrow: `WITH CHECK
(organization_id IS NULL)`. This is not "the shape create_user happens to
produce" as its justification -- the actual, structural invariant is that
this policy makes it *impossible* for the application-facing INSERT path to
assign a User to *any* Organization, including the caller's own otherwise-
legitimate-looking one. ADR/0031 SS6.4 already decided the nullable column
must be able to represent a "not yet onboarded" User; this policy is the
database-level guarantee of that already-decided state, not a new one. See
`presentation/api/v1/users.py`'s `create_user` docstring and
`ADR/0031`/T105's authorization row for the full disclosure that the
eventual Organization-assignment policy for POST /users remains unresolved
and is not decided here.

Every `current_setting('app.current_*_id', true)` read in these policies is
wrapped in `NULLIF(..., '')` before the `::uuid` cast. Verified directly
against Postgres (not assumed): for a custom/unregistered GUC that has
already been `set_config()`-ed at least once on a session/connection,
`set_config(name, NULL, true)` does NOT make a later `current_setting(name,
true)` read back as true SQL `NULL` -- it returns an empty string instead,
which would otherwise raise `invalid input syntax for type uuid: ""` under
connection-pool reuse (a request with no Organization landing on a
connection a previous, org-scoped request already used). `NULLIF` converts
that empty string to real `NULL` before the cast, so the comparison safely
evaluates to "no match" either way.

Revision ID: 7192e84e9a2f
Revises: 64c319444b4c
Create Date: 2026-09-01 00:00:01.000000

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "7192e84e9a2f"
down_revision: str | Sequence[str] | None = "64c319444b4c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APP_ROLE = "legal_dms_app"


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Postgres/asyncpg do not support bind parameters inside a DO $$ ... $$
    # block's body at all ("parameters are supported only in SELECT, INSERT,
    # UPDATE, DELETE, MERGE and VALUES statements") -- so the role-existence
    # check is done as a plain, parameterized SELECT in Python instead, with
    # a clear Python-raised error, never a raw grant-target-missing trace.
    role_exists = conn.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :role_name").bindparams(role_name=_APP_ROLE)
    ).scalar_one_or_none()
    if role_exists is None:
        raise RuntimeError(
            f"role {_APP_ROLE!r} does not exist -- run `uv run provision-app-role` before "
            "`alembic upgrade head` (see infrastructure/cli/provision_app_role.py)"
        )

    # GRANT CONNECT ON DATABASE needs the actual database identifier -- resolved
    # dynamically so this migration isn't hardcoded to one deployment's DB name.
    # _APP_ROLE is a fixed, hardcoded constant (never external input), so it's
    # safe to embed directly in the DO block's own format() call below --
    # the DO block itself can't accept it as a bind parameter (see above).
    conn.execute(text(f"""
            DO $$
            BEGIN
               EXECUTE format(
                   'GRANT CONNECT ON DATABASE %I TO {_APP_ROLE}', current_database()
               );
            END
            $$;
            """))

    conn.execute(text("GRANT USAGE ON SCHEMA public TO legal_dms_app"))
    conn.execute(
        text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO legal_dms_app")
    )
    conn.execute(text("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO legal_dms_app"))
    conn.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO legal_dms_app"
        )
    )

    # Narrow organizations/users to exactly what T105 authorizes -- see this
    # file's own module docstring.
    conn.execute(text("REVOKE INSERT, UPDATE, DELETE ON organizations FROM legal_dms_app"))
    conn.execute(text("REVOKE DELETE ON users FROM legal_dms_app"))

    conn.execute(text("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY"))
    conn.execute(text("ALTER TABLE organizations FORCE ROW LEVEL SECURITY"))
    conn.execute(
        text(
            "CREATE POLICY organizations_select ON organizations "
            "FOR SELECT "
            "USING (id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
    )

    conn.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
    conn.execute(text("ALTER TABLE users FORCE ROW LEVEL SECURITY"))
    conn.execute(
        text(
            "CREATE POLICY users_select ON users "
            "FOR SELECT "
            "USING ("
            "  id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
            "  OR organization_id ="
            "     NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
            ")"
        )
    )
    conn.execute(
        text(
            "CREATE POLICY users_insert ON users "
            "FOR INSERT "
            "WITH CHECK (organization_id IS NULL)"
        )
    )
    conn.execute(
        text(
            "CREATE POLICY users_update ON users "
            "FOR UPDATE "
            "USING (organization_id ="
            "       NULLIF(current_setting('app.current_organization_id', true), '')::uuid) "
            "WITH CHECK (organization_id ="
            "            NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    conn.execute(text("DROP POLICY IF EXISTS users_update ON users"))
    conn.execute(text("DROP POLICY IF EXISTS users_insert ON users"))
    conn.execute(text("DROP POLICY IF EXISTS users_select ON users"))
    conn.execute(text("ALTER TABLE users NO FORCE ROW LEVEL SECURITY"))
    conn.execute(text("ALTER TABLE users DISABLE ROW LEVEL SECURITY"))

    conn.execute(text("DROP POLICY IF EXISTS organizations_select ON organizations"))
    conn.execute(text("ALTER TABLE organizations NO FORCE ROW LEVEL SECURITY"))
    conn.execute(text("ALTER TABLE organizations DISABLE ROW LEVEL SECURITY"))

    conn.execute(text("GRANT DELETE ON users TO legal_dms_app"))
    conn.execute(text("GRANT INSERT, UPDATE, DELETE ON organizations TO legal_dms_app"))

    conn.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM legal_dms_app"
        )
    )
    conn.execute(text("REVOKE USAGE ON ALL SEQUENCES IN SCHEMA public FROM legal_dms_app"))
    conn.execute(
        text(
            "REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
            "FROM legal_dms_app"
        )
    )
    conn.execute(text("REVOKE USAGE ON SCHEMA public FROM legal_dms_app"))
    conn.execute(text("""
            DO $$
            BEGIN
               EXECUTE format(
                   'REVOKE CONNECT ON DATABASE %I FROM legal_dms_app', current_database()
               );
            END
            $$;
            """))
