"""Direct Party compatibility bridge schema foundation

Revision ID: b7e8a4f2c6d0
Revises: e6a2d4c8f1b7
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e8a4f2c6d0"
down_revision: str | Sequence[str] | None = "e6a2d4c8f1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BRIDGE_TABLES = (
    "property_owners",
    "appointments",
    "invoices",
    "payments",
    "client_contacts",
)


def upgrade() -> None:
    """Add nullable same-Organization Party bridges without backfilling legacy data."""
    for table_name in _BRIDGE_TABLES:
        op.add_column(table_name, sa.Column("party_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_{table_name}_organization_id_parties"),
            table_name,
            "parties",
            ["organization_id", "party_id"],
            ["organization_id", "id"],
        )
        op.create_index(op.f(f"ix_{table_name}_party_id"), table_name, ["party_id"], unique=False)


def downgrade() -> None:
    """Remove only the additive Party compatibility bridge foundation."""
    for table_name in reversed(_BRIDGE_TABLES):
        op.drop_index(op.f(f"ix_{table_name}_party_id"), table_name=table_name)
        op.drop_constraint(
            op.f(f"fk_{table_name}_organization_id_parties"), table_name, type_="foreignkey"
        )
        op.drop_column(table_name, "party_id")
