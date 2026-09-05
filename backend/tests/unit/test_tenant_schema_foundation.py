"""T115 tests for staged tenant ownership and its reversible migration."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa

from app.infrastructure.persistence.models.client import Address, ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment

TENANT_TABLES = {
    "addresses": Address,
    "properties": Property,
    "matters": Matter,
    "property_owners": PropertyOwner,
    "appointments": Appointment,
    "invoices": Invoice,
    "payments": Payment,
    "client_contacts": ClientContact,
}


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
        / "d8f4a6c9b3e1_tenant_supporting_address_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("t115_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTenantSchemaFoundation:
    def test_orm_models_match_the_staged_tenant_schema_contract(self) -> None:
        for model in TENANT_TABLES.values():
            column = model.__table__.c.organization_id
            assert column.nullable is True
            assert column.index is True
            assert any(
                foreign_key.target_fullname == "organizations.id"
                for foreign_key in column.foreign_keys
            )
            assert any(
                isinstance(constraint, sa.UniqueConstraint)
                and tuple(constraint.columns.keys()) == ("organization_id", "id")
                for constraint in model.__table__.constraints
            )

    def test_upgrade_adds_only_nullable_tenant_supporting_schema(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.upgrade()

        assert [call[0] for call in operations.calls] == [
            operation
            for _ in TENANT_TABLES
            for operation in (
                "add_column",
                "create_foreign_key",
                "create_index",
                "create_unique_constraint",
            )
        ]
        added_columns = [call[1] for call in operations.calls if call[0] == "add_column"]
        assert [table_name for table_name, _ in added_columns] == list(TENANT_TABLES)
        assert all(column.name == "organization_id" for _, column in added_columns)
        assert all(column.nullable is True for _, column in added_columns)
        assert not any(call[0] == "execute" for call in operations.calls)

    def test_downgrade_reverses_each_additive_schema_operation(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.downgrade()

        assert [call[0] for call in operations.calls] == [
            operation
            for _ in TENANT_TABLES
            for operation in ("drop_constraint", "drop_index", "drop_constraint", "drop_column")
        ]
        dropped_columns = [call[1] for call in operations.calls if call[0] == "drop_column"]
        assert [table_name for table_name, _ in dropped_columns] == list(reversed(TENANT_TABLES))
        assert all(column_name == "organization_id" for _, column_name in dropped_columns)
