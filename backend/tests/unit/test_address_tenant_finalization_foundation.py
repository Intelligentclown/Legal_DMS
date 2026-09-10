"""T122 unit tests: Address tenant finalization model contract + migration intent.

Static, CI-runnable tests (no database required). The real runtime behavior of
the migration (NOT NULL enforcement, RLS ENABLE/FORCE/policies, default-deny
behavior, downgrade restoration, GUC isolation) is exercised against a
disposable PostgreSQL database in
`tests/integration/test_address_tenant_finalization_and_rls.py`, and the
fail-closed null-legacy upgrade in
`tests/integration/test_address_null_legacy_upgrade_fails_closed.py`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa

from app.infrastructure.persistence.models.client import Address

MIGRATION_REVISION = "9c4a7e2d1b5f"
PARENT_REVISION = "f3b7c9d1e2a4"


class RecordingOperations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def f(self, name: str) -> str:
        return name

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        def operation(*args: object, **kwargs: object) -> None:
            self.calls.append((name, args, kwargs))

        return operation


def _migration_module() -> ModuleType:
    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / f"{MIGRATION_REVISION}_address_tenant_finalization_rls.py"
    )
    spec = importlib.util.spec_from_file_location("t122_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAddressModelContract:
    def test_organization_id_is_non_optional_and_keeps_the_organization_fk(self) -> None:
        column = Address.__table__.c.organization_id
        assert column.nullable is False
        assert column.index is True
        assert any(
            foreign_key.target_fullname == "organizations.id" for foreign_key in column.foreign_keys
        )

    def test_addresses_keep_the_same_organization_support_key(self) -> None:
        assert any(
            isinstance(constraint, sa.UniqueConstraint)
            and tuple(constraint.columns.keys()) == ("organization_id", "id")
            for constraint in Address.__table__.constraints
        )


class TestMigrationWiring:
    def test_revision_extends_the_t120_head(self) -> None:
        module = _migration_module()
        assert module.revision == MIGRATION_REVISION
        assert module.down_revision == PARENT_REVISION
        assert module.branch_labels is None
        assert module.depends_on is None


class TestMigrationIntent:
    def test_upgrade_finalizes_not_null_then_enables_and_forces_rls(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.upgrade()

        assert [call[0] for call in operations.calls] == [
            "alter_column",
            "execute",
            "execute",
            "execute",
            "execute",
            "execute",
            "execute",
        ]
        alter = operations.calls[0]
        assert alter[1] == ("addresses", "organization_id")
        assert alter[2] == {"nullable": False, "existing_nullable": True}
        sql_statements = [call[1][0] for call in operations.calls if call[0] == "execute"]
        assert sql_statements[0] == "ALTER TABLE addresses ENABLE ROW LEVEL SECURITY"
        assert sql_statements[1] == "ALTER TABLE addresses FORCE ROW LEVEL SECURITY"
        assert [stmt.partition(" ")[0] for stmt in sql_statements[2:]] == [
            "CREATE",
            "CREATE",
            "CREATE",
            "CREATE",
        ]
        assert (
            sql_statements[2] == "CREATE POLICY addresses_select ON addresses "
            "FOR SELECT USING (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
        assert (
            sql_statements[3] == "CREATE POLICY addresses_insert ON addresses "
            "FOR INSERT WITH CHECK (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
        assert (
            sql_statements[4] == "CREATE POLICY addresses_update ON addresses "
            "FOR UPDATE USING (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid) "
            "WITH CHECK (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
        assert (
            sql_statements[5] == "CREATE POLICY addresses_delete ON addresses "
            "FOR DELETE USING (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )

    def test_downgrade_reverses_rls_then_restores_nullable(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.downgrade()

        assert [call[0] for call in operations.calls] == [
            "execute",
            "execute",
            "execute",
            "execute",
            "execute",
            "execute",
            "alter_column",
        ]
        sql_statements = [call[1][0] for call in operations.calls if call[0] == "execute"]
        assert sql_statements == [
            "DROP POLICY IF EXISTS addresses_delete ON addresses",
            "DROP POLICY IF EXISTS addresses_update ON addresses",
            "DROP POLICY IF EXISTS addresses_insert ON addresses",
            "DROP POLICY IF EXISTS addresses_select ON addresses",
            "ALTER TABLE addresses NO FORCE ROW LEVEL SECURITY",
            "ALTER TABLE addresses DISABLE ROW LEVEL SECURITY",
        ]
        alter = operations.calls[-1]
        assert alter[1] == ("addresses", "organization_id")
        assert alter[2] == {"nullable": True, "existing_nullable": False}
