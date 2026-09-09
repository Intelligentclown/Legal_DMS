"""T120 structural coverage for Client tenant staging and composite FKs."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa

from app.infrastructure.persistence.models.client import Client, ClientContact
from app.infrastructure.persistence.models.financial import Invoice, Payment
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.models.scheduling import Appointment


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
    path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "f3b7c9d1e2a4_client_tenant_staging_integrity.py"
    )
    spec = importlib.util.spec_from_file_location("t120_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _has_tenant_fk(table: sa.Table, target: tuple[str, str]) -> bool:
    return any(
        isinstance(constraint, sa.ForeignKeyConstraint)
        and tuple(constraint.columns.keys()) == ("organization_id", target[0])
        and tuple(element.target_fullname for element in constraint.elements)
        == (f"{target[1]}.organization_id", f"{target[1]}.id")
        for constraint in table.constraints
    )


def test_client_tenant_staging_metadata_is_nullable_and_composite_safe() -> None:
    table = Client.__table__
    assert table.c.organization_id.nullable is True
    assert table.c.organization_id.index is True
    assert _has_tenant_fk(table, ("address_id", "addresses"))
    assert any(
        isinstance(constraint, sa.UniqueConstraint)
        and tuple(constraint.columns.keys()) == ("organization_id", "id")
        for constraint in table.constraints
    )


def test_all_authorized_legacy_graph_edges_use_same_organization_foreign_keys() -> None:
    expected = (
        (ClientContact.__table__, "client_id", "clients"),
        (Property.__table__, "address_id", "addresses"),
        (PropertyOwner.__table__, "property_id", "properties"),
        (PropertyOwner.__table__, "client_id", "clients"),
        (Matter.__table__, "property_id", "properties"),
        (Matter.__table__, "client_id", "clients"),
        (Appointment.__table__, "matter_id", "matters"),
        (Appointment.__table__, "client_id", "clients"),
        (Invoice.__table__, "matter_id", "matters"),
        (Invoice.__table__, "client_id", "clients"),
        (Payment.__table__, "invoice_id", "invoices"),
        (Payment.__table__, "matter_id", "matters"),
        (Payment.__table__, "client_id", "clients"),
    )
    for table, column_name, target_table in expected:
        assert _has_tenant_fk(table, (column_name, target_table))


def test_migration_replaces_only_authorized_foreign_keys_and_is_reversible() -> None:
    module = _migration_module()
    operations = RecordingOperations()
    module.op = operations

    module.upgrade()

    assert ("add_column", ("clients",), {}) in [
        (name, arguments[:1], keywords) for name, arguments, keywords in operations.calls
    ]
    created = [call for call in operations.calls if call[0] == "create_foreign_key"]
    composite_targets = {
        (tuple(call[1][3]), tuple(call[1][4]))
        for call in created
        if len(call[1]) >= 5 and len(call[1][3]) == 2
    }
    assert ("organization_id", "client_id") in {columns for columns, _targets in composite_targets}
    assert ("organization_id", "address_id") in {columns for columns, _targets in composite_targets}

    operations.calls.clear()
    module.downgrade()
    assert [call[0] for call in operations.calls].count("drop_column") == 1
    assert operations.calls[-1][0] == "drop_column"
