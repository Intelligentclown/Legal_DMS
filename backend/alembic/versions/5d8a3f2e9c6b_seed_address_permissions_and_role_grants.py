"""seed_address_permissions_and_role_grants (T130)

Adds the three `addresses:*` permission codes and their role grants, opening
the governed Address application surface (T130: repository port, org-scoped
repository, service, schemas, router/v1 registration over the already
tenant-finalized/RLS-protected Address aggregate).

This migration is required by the established permission architecture, which
seeds the `permissions` and `role_permissions` tables exclusively through
Alembic migrations: T66's `224b650e5235` established the natural-keyed,
forward-declared permission-code plus role -> permission matrix convention,
and every later permission family (T124's `1b8f4a9c2e6d`, etc.) seeds its
codes the same way. Without `addresses:*` rows, `RequirePermission` could
never find these codes and every Address route would fail closed.

`addresses:read` / `addresses:write` / `addresses:delete` mirror
`parties:*` / `clients:*` exactly:

    Administrator  read + write + delete
    Advocate       read + write + delete
    Paralegal      read + write
    Clerk          read + write
    Accountant     read
    Read Only      read

This takes `role_permissions` from 71 associations to 83 and `permissions`
from 21 codes to 24.

Because this is the first migration past the T126 provenance frontier
(`c4e7a9b2d6f1`), it also extends the single supported runtime contract to
the new head by recreating the two `legal_dms_provenance` functions
(`record_fresh_birth` and `enter_operational_fresh`) with the new supported
schema revision baked into their `alembic_version` guards. T126's design
explicitly requires this: "a future revision must explicitly extend the
supported runtime contract" (see `sqlalchemy_install_classifier.py`), and the
T126 QA review documents that upgrading past the frontier without adjusting
the bootstrap logic trips the `alembic_version` mismatch trigger to fail
closed. Without this extension no fresh install at the new head could record
a birth, `OPERATIONAL_FRESH` could never be established, and every
`establish_fresh_installation`-based integration fixture would break. The
function bodies are byte-identical to T126's except for the supported
revision literal -- no provenance schema, contract, predicate, policy, or
grant surface changes; the downgrade restores the parent's bodies verbatim.

Revision ID: 5d8a3f2e9c6b
Revises: c4e7a9b2d6f1
Create Date: 2026-09-22 00:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d8a3f2e9c6b"
down_revision: str | Sequence[str] | None = "c4e7a9b2d6f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADDRESS_PERMISSIONS = ("addresses:read", "addresses:write", "addresses:delete")

_PROVENANCE_SCHEMA = "legal_dms_provenance"
_CONTRACT_VERSION = "adr-0037.v1"
_PREDICATE_VERSION = "adr-0036-full-bootstrap.v1"

_MATRIX: dict[str, tuple[str, ...]] = {
    "Administrator": ("addresses:read", "addresses:write", "addresses:delete"),
    "Advocate": ("addresses:read", "addresses:write", "addresses:delete"),
    "Paralegal": ("addresses:read", "addresses:write"),
    "Clerk": ("addresses:read", "addresses:write"),
    "Accountant": ("addresses:read",),
    "Read Only": ("addresses:read",),
}


def _record_fresh_birth_sql(revision: str) -> str:
    """T126's `record_fresh_birth` body with a new supported-revision guard."""
    schema = _PROVENANCE_SCHEMA
    return f"""
        CREATE OR REPLACE FUNCTION {schema}.record_fresh_birth(
            p_event_id uuid, p_installation_id uuid
        )
        RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public, {schema}
        AS $$
        DECLARE marker boolean;
        BEGIN
            IF current_setting('transaction_isolation') <> 'serializable' THEN
                RAISE EXCEPTION 'fresh birth requires a serializable installer transaction';
            END IF;
            BEGIN
                EXECUTE 'SELECT valid FROM pg_temp.legal_dms_fresh_install_guard' INTO marker;
            EXCEPTION WHEN undefined_table THEN
                RAISE EXCEPTION 'fresh birth requires the guarded initial-install path';
            END;
            IF marker IS DISTINCT FROM true THEN
                RAISE EXCEPTION 'fresh-install guard is invalid';
            END IF;
            IF EXISTS (SELECT 1 FROM {schema}.installation_events) THEN
                RAISE EXCEPTION 'installation provenance already exists';
            END IF;
            IF (SELECT version_num FROM alembic_version) <> '{revision}' THEN
                RAISE EXCEPTION 'fresh birth requires supported schema revision {revision}';
            END IF;
            INSERT INTO {schema}.installation_events (
                id, installation_id, event_sequence, event_kind, provenance_contract_version,
                observed_schema_revision, bootstrap_predicate_version
            ) VALUES (
                p_event_id, p_installation_id, 1, 'FRESH_BIRTH', '{_CONTRACT_VERSION}',
                '{revision}', NULL
            );
            RETURN p_installation_id;
        END;
        $$
        """


def _enter_operational_fresh_sql(revision: str) -> str:
    """T126's `enter_operational_fresh` body with a new supported-revision guard."""
    schema = _PROVENANCE_SCHEMA
    return f"""
        CREATE OR REPLACE FUNCTION {schema}.enter_operational_fresh(
            p_event_id uuid
        )
        RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public, {schema}
        AS $$
        DECLARE birth_id uuid; existing_id uuid; table_name text; row_count bigint;
        BEGIN
            IF current_setting('transaction_isolation') <> 'serializable' THEN
                RAISE EXCEPTION 'operational bootstrap requires serializable isolation';
            END IF;
            PERFORM pg_advisory_xact_lock(hashtext('legal_dms.operational-fresh-bootstrap.v1'));
            IF (SELECT version_num FROM alembic_version) <> '{revision}' THEN
                RAISE EXCEPTION 'unsupported schema revision for operational bootstrap';
            END IF;
            SELECT installation_id INTO birth_id FROM {schema}.installation_events
             WHERE event_kind = 'FRESH_BIRTH'
               AND provenance_contract_version = '{_CONTRACT_VERSION}';
            IF birth_id IS NULL OR (SELECT count(*) FROM {schema}.installation_events
                WHERE event_kind = 'FRESH_BIRTH') <> 1 THEN
                RAISE EXCEPTION 'valid singleton fresh birth is required';
            END IF;
            SELECT id INTO existing_id FROM {schema}.installation_events
             WHERE installation_id = birth_id AND event_kind = 'OPERATIONAL_FRESH_ENTERED';
            IF existing_id IS NOT NULL THEN
                RETURN existing_id;
            END IF;
            FOREACH table_name IN ARRAY ARRAY[
                'clients', 'client_contacts', 'addresses', 'properties', 'property_owners',
                'matters', 'appointments', 'invoices', 'payments', 'parties', 'matter_parties',
                'client_party_migration_ledger'
            ] LOOP
                EXECUTE format('SELECT count(*) FROM public.%I', table_name) INTO row_count;
                IF row_count <> 0 THEN
                    RAISE EXCEPTION 'bootstrap predicate failed: % contains business rows',
                        table_name;
                END IF;
            END LOOP;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'legal_dms_app'
                AND NOT rolsuper AND NOT rolbypassrls)
                OR NOT EXISTS (SELECT 1 FROM pg_class WHERE oid = 'parties'::regclass
                    AND relrowsecurity AND relforcerowsecurity)
                OR NOT EXISTS (SELECT 1 FROM pg_class WHERE oid = 'addresses'::regclass
                    AND relrowsecurity AND relforcerowsecurity)
                OR NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'addresses'::regclass
                    AND attname = 'organization_id' AND attnotnull)
                OR (SELECT count(*) FROM permissions WHERE code IN
                    ('parties:read', 'parties:write', 'parties:delete')) <> 3 THEN
                RAISE EXCEPTION 'required runtime security posture is not established';
            END IF;
            INSERT INTO {schema}.installation_events (
                id, installation_id, event_sequence, event_kind, provenance_contract_version,
                observed_schema_revision, bootstrap_predicate_version
            ) VALUES (
                p_event_id, birth_id, 2, 'OPERATIONAL_FRESH_ENTERED', '{_CONTRACT_VERSION}',
                '{revision}', '{_PREDICATE_VERSION}'
            );
            RETURN p_event_id;
        END;
        $$
        """


def upgrade() -> None:
    connection = op.get_bind()

    op.execute(_record_fresh_birth_sql(revision))
    op.execute(_enter_operational_fresh_sql(revision))

    roles_result = connection.execute(sa.text("SELECT id, name FROM roles")).mappings().all()
    role_map = {row["name"]: row["id"] for row in roles_result}

    perms_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    perm_map = {row["code"]: row["id"] for row in perms_result}

    missing_roles = set(_MATRIX) - set(role_map)
    if missing_roles:
        raise RuntimeError(f"roles missing for address permission grants: {sorted(missing_roles)}")

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("category", sa.String()),
    )
    address_permission_rows = [
        ("addresses:read", "View addresses", "addresses"),
        ("addresses:write", "Create and edit addresses", "addresses"),
        ("addresses:delete", "Delete addresses", "addresses"),
    ]
    new_permissions = [
        {
            "id": uuid.uuid4(),
            "code": code,
            "description": description,
            "category": category,
        }
        for code, description, category in address_permission_rows
        if code not in perm_map
    ]
    if new_permissions:
        op.bulk_insert(permissions, new_permissions)
        perms_result = (
            connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
        )
        perm_map = {row["code"]: row["id"] for row in perms_result}

    role_permissions = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )

    rows = []
    for role_name, perm_codes in _MATRIX.items():
        role_id = role_map[role_name]
        for code in perm_codes:
            perm_id = perm_map[code]
            rows.append({"id": uuid.uuid4(), "role_id": role_id, "permission_id": perm_id})

    if rows:
        op.bulk_insert(role_permissions, rows)


def downgrade() -> None:
    connection = op.get_bind()

    roles_result = connection.execute(sa.text("SELECT id, name FROM roles")).mappings().all()
    role_map = {row["name"]: row["id"] for row in roles_result}

    perms_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    perm_map = {row["code"]: row["id"] for row in perms_result}

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )

    for role_name, perm_codes in _MATRIX.items():
        role_id = role_map.get(role_name)
        if role_id is None:
            continue
        for code in perm_codes:
            perm_id = perm_map.get(code)
            if perm_id is None:
                continue
            op.execute(
                role_permissions.delete().where(
                    sa.and_(
                        role_permissions.c.role_id == role_id,
                        role_permissions.c.permission_id == perm_id,
                    )
                )
            )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    for code in _ADDRESS_PERMISSIONS:
        perm_id = perm_map.get(code)
        if perm_id is not None:
            op.execute(permissions.delete().where(permissions.c.id == perm_id))

    op.execute(_record_fresh_birth_sql(down_revision))
    op.execute(_enter_operational_fresh_sql(down_revision))
