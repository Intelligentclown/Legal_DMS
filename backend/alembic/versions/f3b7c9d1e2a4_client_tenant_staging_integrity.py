"""Legacy Client tenant staging and same-Organization integrity foundation

Revision ID: f3b7c9d1e2a4
Revises: b7e8a4f2c6d0
Create Date: 2026-09-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3b7c9d1e2a4"
down_revision: str | Sequence[str] | None = "b7e8a4f2c6d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CLIENT_REFERENCES = (
    "property_owners",
    "matters",
    "appointments",
    "invoices",
    "payments",
    "client_contacts",
)

_DEPENDENCY_REFERENCES = (
    ("properties", "address_id", "addresses"),
    ("property_owners", "property_id", "properties"),
    ("matters", "property_id", "properties"),
    ("appointments", "matter_id", "matters"),
    ("invoices", "matter_id", "matters"),
    ("payments", "invoice_id", "invoices"),
    ("payments", "matter_id", "matters"),
)


def _add_tenant_fk(table_name: str, column_name: str, target_table: str) -> None:
    """Keep the legacy FK and add a nullable same-Organization guard."""
    op.create_foreign_key(
        op.f(f"fk_{table_name}_organization_id_{target_table}"),
        table_name,
        target_table,
        ["organization_id", column_name],
        ["organization_id", "id"],
    )


def _drop_tenant_fk(table_name: str, target_table: str) -> None:
    op.drop_constraint(
        op.f(f"fk_{table_name}_organization_id_{target_table}"), table_name, type_="foreignkey"
    )


def upgrade() -> None:
    """Add nullable Client tenant staging without mutating legacy rows."""
    op.add_column("clients", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_clients_organization_id_organizations"),
        "clients",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_clients_organization_id"), "clients", ["organization_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_clients_organization_id_id", "clients", ["organization_id", "id"]
    )

    _add_tenant_fk("clients", "address_id", "addresses")
    for table_name in _CLIENT_REFERENCES:
        _add_tenant_fk(table_name, "client_id", "clients")
    for table_name, column_name, target_table in _DEPENDENCY_REFERENCES:
        _add_tenant_fk(table_name, column_name, target_table)


def downgrade() -> None:
    """Restore the pre-T120 independent legacy foreign keys."""
    for table_name, _column_name, target_table in reversed(_DEPENDENCY_REFERENCES):
        _drop_tenant_fk(table_name, target_table)
    for table_name in reversed(_CLIENT_REFERENCES):
        _drop_tenant_fk(table_name, "clients")
    _drop_tenant_fk("clients", "addresses")

    op.drop_constraint("uq_clients_organization_id_id", "clients", type_="unique")
    op.drop_index(op.f("ix_clients_organization_id"), table_name="clients")
    op.drop_constraint(
        op.f("fk_clients_organization_id_organizations"), "clients", type_="foreignkey"
    )
    op.drop_column("clients", "organization_id")
