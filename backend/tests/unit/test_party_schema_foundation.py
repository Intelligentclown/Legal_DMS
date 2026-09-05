"""T116 tests for the governed Party, MatterParty, and ledger schema foundation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa

from app.infrastructure.persistence.models.party import (
    ClientPartyMigrationLedger,
    MatterParty,
    Party,
)


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
        / "e6a2d4c8f1b7_party_matterparty_ledger_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("t116_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _constraint_sql(table: sa.Table) -> set[str]:
    return {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, sa.CheckConstraint)
    }


class TestPartySchema:
    def test_party_uses_the_governed_columns_and_tenant_safe_address_fk(self) -> None:
        table = Party.__table__
        assert table.c.organization_id.nullable is False
        assert table.c.address_id.nullable is True
        assert Party.__mapper__.version_id_col is table.c.version
        assert set(table.c.keys()) >= {
            "id",
            "organization_id",
            "party_type",
            "display_name",
            "primary_phone",
            "primary_email",
            "address_id",
            "notes",
            "pan_number",
            "aadhaar_number",
            "gstin",
            "registration_identifier",
            "date_of_birth",
            "gender",
            "occupation",
            "incorporation_date",
        }
        assert any(
            foreign_key.column.table.name == "addresses"
            and tuple(element.parent.name for element in foreign_key.constraint.elements)
            == ("organization_id", "address_id")
            for foreign_key in table.foreign_keys
        )

    def test_party_constraints_and_indexes_match_adr_0035(self) -> None:
        table = Party.__table__
        constraints = _constraint_sql(table)
        assert "party_type IN ('individual', 'organization')" in constraints
        assert "length(primary_phone) >= 7" in constraints
        assert any("aadhaar_number IS NULL" in constraint for constraint in constraints)
        assert any("gstin IS NULL" in constraint for constraint in constraints)
        assert any("individual' OR" in constraint for constraint in constraints)
        assert any("organization' OR" in constraint for constraint in constraints)
        assert any(
            isinstance(constraint, sa.UniqueConstraint)
            and tuple(constraint.columns.keys()) == ("organization_id", "id")
            for constraint in table.constraints
        )
        assert {
            "ix_parties_organization_id_party_type",
            "ix_parties_organization_id_display_name",
            "ix_parties_organization_id_primary_phone",
            "ix_parties_organization_id_primary_email",
            "ix_parties_organization_id_pan_number",
            "ix_parties_organization_id_aadhaar_number",
            "ix_parties_organization_id_gstin",
            "ix_parties_organization_id_registration_identifier",
        } <= {index.name for index in table.indexes}


class TestMatterPartySchema:
    def test_matter_party_is_only_the_bounded_audited_join_contract(self) -> None:
        table = MatterParty.__table__
        assert set(table.c.keys()) >= {
            "id",
            "organization_id",
            "matter_id",
            "party_id",
            "role",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "version",
            "deleted_at",
        }
        assert not _constraint_sql(table)
        composite_targets = {
            tuple(element.target_fullname for element in foreign_key.constraint.elements)
            for foreign_key in table.foreign_keys
            if len(foreign_key.constraint.elements) == 2
        }
        assert ("matters.organization_id", "matters.id") in composite_targets
        assert ("parties.organization_id", "parties.id") in composite_targets
        assert any(
            isinstance(constraint, sa.UniqueConstraint)
            and tuple(constraint.columns.keys()) == ("matter_id", "party_id", "role")
            for constraint in table.constraints
        )


class TestLedgerSchema:
    def test_ledger_is_immutable_and_has_the_governed_identity_keys(self) -> None:
        table = ClientPartyMigrationLedger.__table__
        assert set(table.c.keys()) >= {
            "id",
            "legacy_client_id",
            "party_id",
            "organization_id",
            "executor_version",
            "reconciliation_set_id",
            "source_report_sha256",
            "resolution_mode",
            "source_client_version",
            "source_client_updated_at",
            "source_fingerprint",
            "completed_at",
            "artifact_actor_type",
            "artifact_actor_id",
            "operator_note",
            "execution_run_id",
        }
        assert not {"updated_at", "deleted_at", "version", "created_by", "updated_by"} & set(
            table.c.keys()
        )
        constraints = _constraint_sql(table)
        assert "party_id = legacy_client_id" in constraints
        assert "resolution_mode IN ('deterministic', 'operator_reconciled')" in constraints
        unique_columns = {
            tuple(constraint.columns.keys())
            for constraint in table.constraints
            if isinstance(constraint, sa.UniqueConstraint)
        }
        assert (
            "legacy_client_id",
            "party_id",
            "organization_id",
            "executor_version",
            "reconciliation_set_id",
            "source_report_sha256",
            "source_fingerprint",
        ) in unique_columns
        assert (
            "legacy_client_id",
            "executor_version",
            "reconciliation_set_id",
            "source_report_sha256",
        ) in unique_columns


class TestPartySchemaMigration:
    def test_upgrade_creates_only_the_three_governed_tables_and_indexes(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.upgrade()

        assert [call[1][0] for call in operations.calls if call[0] == "create_table"] == [
            "parties",
            "matter_parties",
            "client_party_migration_ledger",
        ]
        assert not {"execute", "bulk_insert", "add_column"} & {call[0] for call in operations.calls}

    def test_downgrade_drops_dependents_before_parties(self) -> None:
        module = _migration_module()
        operations = RecordingOperations()
        module.op = operations

        module.downgrade()

        dropped_tables = [call[1][0] for call in operations.calls if call[0] == "drop_table"]
        assert dropped_tables == ["client_party_migration_ledger", "matter_parties", "parties"]
