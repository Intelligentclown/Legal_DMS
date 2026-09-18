"""Operational-fresh provenance persistence and privilege foundation (T126).

The upgrade creates schema and security primitives only. It deliberately
creates no birth or operational evidence for an upgraded database.

Revision ID: c4e7a9b2d6f1
Revises: 1b8f4a9c2e6d
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e7a9b2d6f1"
down_revision: str | Sequence[str] | None = "1b8f4a9c2e6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "legal_dms_provenance"
_APP_ROLE = "legal_dms_app"
_BOOTSTRAP_ROLE = "legal_dms_bootstrap"
_CONTRACT_VERSION = "adr-0037.v1"
_PREDICATE_VERSION = "adr-0036-full-bootstrap.v1"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA {_SCHEMA}")
    op.execute(f"REVOKE ALL ON SCHEMA {_SCHEMA} FROM PUBLIC")
    op.execute(f"""
        CREATE TABLE {_SCHEMA}.installation_events (
            id uuid PRIMARY KEY,
            installation_id uuid NOT NULL,
            event_sequence integer NOT NULL,
            event_kind text NOT NULL,
            provenance_contract_version text NOT NULL,
            observed_schema_revision text NOT NULL,
            bootstrap_predicate_version text,
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_installation_events_kind CHECK (
                event_kind IN ('FRESH_BIRTH', 'OPERATIONAL_FRESH_ENTERED')
            ),
            CONSTRAINT ck_installation_events_sequence CHECK (event_sequence IN (1, 2)),
            CONSTRAINT ck_installation_events_predicate CHECK (
                (event_kind = 'FRESH_BIRTH' AND bootstrap_predicate_version IS NULL)
                OR
                (event_kind = 'OPERATIONAL_FRESH_ENTERED' AND
                 bootstrap_predicate_version = '{_PREDICATE_VERSION}')
            ),
            CONSTRAINT uq_installation_events_sequence UNIQUE (installation_id, event_sequence),
            CONSTRAINT uq_installation_events_kind UNIQUE (installation_id, event_kind)
        )
        """)
    op.execute(
        f"CREATE UNIQUE INDEX uq_installation_events_single_birth ON {_SCHEMA}.installation_events "
        "(event_kind) WHERE event_kind = 'FRESH_BIRTH'"
    )
    op.execute(
        f"CREATE UNIQUE INDEX uq_installation_events_single_operational ON "
        f"{_SCHEMA}.installation_events "
        "(event_kind) WHERE event_kind = 'OPERATIONAL_FRESH_ENTERED'"
    )
    op.execute(f"""
        CREATE FUNCTION {_SCHEMA}.reject_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'installation provenance is append-only';
        END;
        $$
        """)
    op.execute(f"""
        CREATE FUNCTION {_SCHEMA}.validate_event_insert() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.event_kind = 'FRESH_BIRTH' AND NEW.event_sequence <> 1 THEN
                RAISE EXCEPTION 'fresh birth must be sequence 1';
            END IF;
            IF NEW.event_kind = 'OPERATIONAL_FRESH_ENTERED' AND NEW.event_sequence <> 2 THEN
                RAISE EXCEPTION 'operational transition must be sequence 2';
            END IF;
            RETURN NEW;
        END;
        $$
        """)
    op.execute(
        f"CREATE TRIGGER installation_events_validate BEFORE INSERT ON "
        f"{_SCHEMA}.installation_events "
        f"FOR EACH ROW EXECUTE FUNCTION {_SCHEMA}.validate_event_insert()"
    )
    op.execute(
        f"CREATE TRIGGER installation_events_immutable BEFORE UPDATE OR DELETE "
        f"ON {_SCHEMA}.installation_events FOR EACH ROW "
        f"EXECUTE FUNCTION {_SCHEMA}.reject_event_mutation()"
    )
    op.execute(f"""
        CREATE FUNCTION {_SCHEMA}.record_fresh_birth(p_event_id uuid, p_installation_id uuid)
        RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public, {_SCHEMA}
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
            IF EXISTS (SELECT 1 FROM {_SCHEMA}.installation_events) THEN
                RAISE EXCEPTION 'installation provenance already exists';
            END IF;
            IF (SELECT version_num FROM alembic_version) <> '{revision}' THEN
                RAISE EXCEPTION 'fresh birth requires supported schema revision {revision}';
            END IF;
            INSERT INTO {_SCHEMA}.installation_events (
                id, installation_id, event_sequence, event_kind, provenance_contract_version,
                observed_schema_revision, bootstrap_predicate_version
            ) VALUES (
                p_event_id, p_installation_id, 1, 'FRESH_BIRTH', '{_CONTRACT_VERSION}',
                '{revision}', NULL
            );
            RETURN p_installation_id;
        END;
        $$
        """)
    op.execute(f"""
        CREATE FUNCTION {_SCHEMA}.enter_operational_fresh(p_event_id uuid)
        RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public, {_SCHEMA}
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
            SELECT installation_id INTO birth_id FROM {_SCHEMA}.installation_events
             WHERE event_kind = 'FRESH_BIRTH'
               AND provenance_contract_version = '{_CONTRACT_VERSION}';
            IF birth_id IS NULL OR (SELECT count(*) FROM {_SCHEMA}.installation_events
                WHERE event_kind = 'FRESH_BIRTH') <> 1 THEN
                RAISE EXCEPTION 'valid singleton fresh birth is required';
            END IF;
            SELECT id INTO existing_id FROM {_SCHEMA}.installation_events
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
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_APP_ROLE}'
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
            INSERT INTO {_SCHEMA}.installation_events (
                id, installation_id, event_sequence, event_kind, provenance_contract_version,
                observed_schema_revision, bootstrap_predicate_version
            ) VALUES (
                p_event_id, birth_id, 2, 'OPERATIONAL_FRESH_ENTERED', '{_CONTRACT_VERSION}',
                '{revision}', '{_PREDICATE_VERSION}'
            );
            RETURN p_event_id;
        END;
        $$
        """)
    op.execute(f"""
        CREATE VIEW {_SCHEMA}.runtime_state AS
        SELECT installation_id, event_kind, provenance_contract_version, observed_schema_revision,
               occurred_at
        FROM {_SCHEMA}.installation_events
        WHERE event_kind = 'OPERATIONAL_FRESH_ENTERED'
        """)
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {_SCHEMA} FROM PUBLIC")
    op.execute(f"REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {_SCHEMA} FROM PUBLIC")
    op.execute(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO {_APP_ROLE}")
    op.execute(f"GRANT SELECT ON {_SCHEMA}.runtime_state TO {_APP_ROLE}")
    op.execute(f"""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_BOOTSTRAP_ROLE}') THEN
                GRANT USAGE ON SCHEMA {_SCHEMA} TO {_BOOTSTRAP_ROLE};
                GRANT EXECUTE ON FUNCTION {_SCHEMA}.enter_operational_fresh(uuid)
                    TO {_BOOTSTRAP_ROLE};
            END IF;
        END $$
        """)


def downgrade() -> None:
    op.execute(f"DROP SCHEMA {_SCHEMA} CASCADE")
