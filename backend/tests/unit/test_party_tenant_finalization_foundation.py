"""T123 unit tests: Party RLS backstop migration wiring + intent.

Static, CI-runnable tests (no database required). The real runtime behavior
of the migration (RLS ENABLE/FORCE/policies, default-deny behavior, GUC
isolation, downgrade restoration) is exercised against a disposable
PostgreSQL database in
`tests/integration/test_party_tenant_finalization_and_rls.py`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa

from app.infrastructure.persistence.models.party import Party

MIGRATION_REVISION = "62cadaff2571"
PARENT_REVISION = "9c4a7e2d1b5f"


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
        / f"{MIGRATION_REVISION}_party_row_level_security_backstop.py"
    )
    spec = importlib.util.spec_from_file_location("t123_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPartySchemaContract:
    def test_organization_id_remains_non_optional_and_organization_fk_is_kept(self) -> None:
        column = Party.__table__.c.organization_id
        assert column.nullable is False
        assert column.index is True
        assert any(
            foreign_key.target_fullname == "organizations.id" for foreign_key in column.foreign_keys
        )

    def test_parties_keep_the_same_organization_support_key(self) -> None:
        assert any(
            isinstance(constraint, sa.UniqueConstraint)
            and tuple(constraint.columns.keys()) == ("organization_id", "id")
            for constraint in Party.__table__.constraints
        )

    def test_parties_keep_the_composite_address_reference(self) -> None:
        assert any(
            isinstance(constraint, sa.ForeignKeyConstraint)
            and constraint.name == "fk_parties_organization_id_addresses"
            and tuple(constraint.columns.keys()) == ("organization_id", "address_id")
            and tuple(constraint.elements[0].target_fullname.split("."))
            == (
                "addresses",
                "organization_id",
            )
            for constraint in Party.__table__.constraints
        )


class TestMigrationWiring:
    def test_revision_extends_the_t122_head(self) -> None:
        module = _migration_module()
        assert module.revision == MIGRATION_REVISION
        assert module.down_revision == PARENT_REVISION
        assert module.branch_labels is None
        assert module.depends_on is None


class TestMigrationIntent:
    def test_upgrade_enables_forces_rls_then_creates_exactly_four_default_deny_policies(
        self,
    ) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.upgrade()

        assert [call[0] for call in operations.calls] == [
            "execute",
            "execute",
            "execute",
            "execute",
            "execute",
            "execute",
        ]
        sql_statements = [call[1][0] for call in operations.calls]
        assert sql_statements[0] == "ALTER TABLE parties ENABLE ROW LEVEL SECURITY"
        assert sql_statements[1] == "ALTER TABLE parties FORCE ROW LEVEL SECURITY"
        assert [stmt.partition(" ")[0] for stmt in sql_statements[2:]] == [
            "CREATE",
            "CREATE",
            "CREATE",
            "CREATE",
        ]
        assert (
            sql_statements[2] == "CREATE POLICY parties_select ON parties "
            "FOR SELECT USING (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
        assert (
            sql_statements[3] == "CREATE POLICY parties_insert ON parties "
            "FOR INSERT WITH CHECK (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
        assert (
            sql_statements[4] == "CREATE POLICY parties_update ON parties "
            "FOR UPDATE USING (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid) "
            "WITH CHECK (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )
        assert (
            sql_statements[5] == "CREATE POLICY parties_delete ON parties "
            "FOR DELETE USING (organization_id = "
            "NULLIF(current_setting('app.current_organization_id', true), '')::uuid)"
        )

    def test_downgrade_reverses_rls_without_touching_party_schema(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.downgrade()

        sql_statements = [call[1][0] for call in operations.calls]
        assert sql_statements == [
            "DROP POLICY IF EXISTS parties_delete ON parties",
            "DROP POLICY IF EXISTS parties_update ON parties",
            "DROP POLICY IF EXISTS parties_insert ON parties",
            "DROP POLICY IF EXISTS parties_select ON parties",
            "ALTER TABLE parties NO FORCE ROW LEVEL SECURITY",
            "ALTER TABLE parties DISABLE ROW LEVEL SECURITY",
        ]
