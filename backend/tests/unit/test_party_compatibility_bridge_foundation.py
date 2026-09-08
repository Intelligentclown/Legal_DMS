"""T117 tests for the governed same-Organization Party compatibility bridges."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.infrastructure.persistence.models.client import ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment
from app.infrastructure.persistence.models.property import PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment

BRIDGE_TABLES = {
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
        / "b7e8a4f2c6d0_party_compatibility_bridge_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("t117_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _party_foreign_key(model) -> sa.ForeignKeyConstraint:
    return next(
        constraint
        for constraint in model.__table__.constraints
        if isinstance(constraint, sa.ForeignKeyConstraint)
        and tuple(constraint.columns.keys()) == ("organization_id", "party_id")
    )


class TestBridgeSchemaFoundation:
    def test_orm_models_expose_nullable_party_id_with_same_organization_party_fk(self) -> None:
        for model in BRIDGE_TABLES.values():
            table = model.__table__
            column = table.c.party_id
            assert column.nullable is True
            assert any(
                isinstance(constraint, sa.ForeignKeyConstraint)
                and tuple(constraint.columns.keys()) == ("organization_id", "party_id")
                and tuple(element.target_fullname for element in constraint.elements)
                == ("parties.organization_id", "parties.id")
                for constraint in table.constraints
            )
            assert not any(
                isinstance(constraint, sa.ForeignKeyConstraint)
                and tuple(constraint.columns.keys()) == ("party_id",)
                and tuple(element.target_fullname for element in constraint.elements)
                == ("parties.id",)
                for constraint in table.constraints
            )
            assert f"ix_{table.name}_party_id" in {index.name for index in table.indexes}
            assert table.c.client_id is not None
            assert table.c.organization_id.nullable is True

    def test_upgrade_adds_only_nullable_bridge_schema(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.upgrade()

        assert [call[0] for call in operations.calls] == [
            operation
            for _ in BRIDGE_TABLES
            for operation in ("add_column", "create_foreign_key", "create_index")
        ]
        added_columns = [call[1] for call in operations.calls if call[0] == "add_column"]
        assert [table_name for table_name, _ in added_columns] == list(BRIDGE_TABLES)
        assert all(column.name == "party_id" for _, column in added_columns)
        assert all(column.nullable is True for _, column in added_columns)
        created_fks = [call for call in operations.calls if call[0] == "create_foreign_key"]
        assert all(
            call[1][2] == "parties"
            and call[1][3] == ["organization_id", "party_id"]
            and call[1][4] == ["organization_id", "id"]
            for call in created_fks
        )
        assert not any(call[0] == "execute" for call in operations.calls)

    def test_downgrade_reverses_each_additive_bridge_operation(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.downgrade()

        assert [call[0] for call in operations.calls] == [
            operation
            for _ in reversed(BRIDGE_TABLES)
            for operation in ("drop_index", "drop_constraint", "drop_column")
        ]
        dropped_columns = [call[1] for call in operations.calls if call[0] == "drop_column"]
        assert [table_name for table_name, _ in dropped_columns] == list(reversed(BRIDGE_TABLES))
        assert all(column_name == "party_id" for _, column_name in dropped_columns)

    def test_bridge_party_fk_rejects_cross_tenant_pairing_and_accepts_null_and_same_tenant(
        self,
    ) -> None:
        for model in BRIDGE_TABLES.values():
            party_foreign_key = _party_foreign_key(model)
            metadata = sa.MetaData()
            organizations = sa.Table(
                "organizations", metadata, sa.Column("id", sa.Uuid(), primary_key=True)
            )
            parties = sa.Table(
                "parties",
                metadata,
                sa.Column("organization_id", sa.Uuid(), nullable=False),
                sa.Column("id", sa.Uuid(), primary_key=True),
                sa.UniqueConstraint("organization_id", "id"),
            )
            bridge = sa.Table(
                f"{model.__tablename__}_bridge_check",
                metadata,
                sa.Column("organization_id", sa.Uuid(), nullable=True),
                sa.Column("party_id", sa.Uuid(), nullable=True),
                sa.ForeignKeyConstraint(
                    party_foreign_key.column_keys,
                    [element.target_fullname for element in party_foreign_key.elements],
                ),
            )
            engine = sa.create_engine("sqlite://")

            with engine.begin() as connection:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                metadata.create_all(connection)
                organization_a, organization_b, party_id = uuid4(), uuid4(), uuid4()
                connection.execute(
                    organizations.insert(), [{"id": organization_a}, {"id": organization_b}]
                )
                connection.execute(
                    parties.insert(), {"organization_id": organization_a, "id": party_id}
                )
                connection.execute(bridge.insert(), {"organization_id": None, "party_id": None})
                connection.execute(
                    bridge.insert(),
                    {"organization_id": organization_a, "party_id": party_id},
                )
                with pytest.raises(sa.exc.IntegrityError):
                    connection.execute(
                        bridge.insert(),
                        {"organization_id": organization_b, "party_id": party_id},
                    )
