"""tenant-supporting Address and downstream Organization schema foundation

Revision ID: d8f4a6c9b3e1
Revises: 7192e84e9a2f
Create Date: 2026-09-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8f4a6c9b3e1"
down_revision: str | Sequence[str] | None = "7192e84e9a2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "addresses",
    "properties",
    "matters",
    "property_owners",
    "appointments",
    "invoices",
    "payments",
    "client_contacts",
)


def upgrade() -> None:
    """Add nullable tenant ownership staging columns without backfilling legacy data."""
    for table_name in _TABLES:
        op.add_column(table_name, sa.Column("organization_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_{table_name}_organization_id_organizations"),
            table_name,
            "organizations",
            ["organization_id"],
            ["id"],
        )
        op.create_index(
            op.f(f"ix_{table_name}_organization_id"), table_name, ["organization_id"], unique=False
        )
        op.create_unique_constraint(
            f"uq_{table_name}_organization_id_id", table_name, ["organization_id", "id"]
        )


def downgrade() -> None:
    """Remove only the additive tenant-supporting schema foundation."""
    for table_name in reversed(_TABLES):
        op.drop_constraint(f"uq_{table_name}_organization_id_id", table_name, type_="unique")
        op.drop_index(op.f(f"ix_{table_name}_organization_id"), table_name=table_name)
        op.drop_constraint(
            op.f(f"fk_{table_name}_organization_id_organizations"), table_name, type_="foreignkey"
        )
        op.drop_column(table_name, "organization_id")
