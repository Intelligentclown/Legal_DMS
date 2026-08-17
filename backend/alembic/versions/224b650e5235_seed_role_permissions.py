"""seed_role_permissions

Revision ID: 224b650e5235
Revises: 453c6838ad6f
Create Date: 2026-08-17 16:01:27.866291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '224b650e5235'
down_revision: Union[str, Sequence[str], None] = '453c6838ad6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    connection = op.get_bind()

    # Fetch roles
    roles_result = connection.execute(sa.text("SELECT id, name FROM roles")).mappings().all()
    role_map = {row["name"]: row["id"] for row in roles_result}

    # Fetch permissions
    perms_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    perm_map = {row["code"]: row["id"] for row in perms_result}

    matrix = {
        "Administrator": [
            "matters:read", "matters:write", "matters:delete",
            "clients:read", "clients:write", "clients:delete",
            "properties:read", "properties:write", "properties:delete",
            "documents:read", "documents:write", "documents:delete",
            "financial:read", "financial:write",
            "users:manage", "roles:manage", "settings:manage",
            "reports:read"
        ],
        "Advocate": [
            "matters:read", "matters:write", "matters:delete",
            "clients:read", "clients:write", "clients:delete",
            "properties:read", "properties:write", "properties:delete",
            "documents:read", "documents:write", "documents:delete",
            "financial:read", "reports:read"
        ],
        "Paralegal": [
            "matters:read", "matters:write",
            "clients:read", "clients:write",
            "properties:read", "properties:write",
            "documents:read", "documents:write",
            "financial:read", "reports:read"
        ],
        "Clerk": [
            "matters:read", "matters:write",
            "clients:read", "clients:write",
            "documents:read", "documents:write"
        ],
        "Accountant": [
            "financial:read", "financial:write",
            "matters:read", "clients:read", "reports:read"
        ],
        "Read Only": [
            "matters:read", "clients:read", "properties:read",
            "documents:read", "financial:read", "reports:read"
        ]
    }

    import uuid
    role_permissions = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )

    rows = []
    for role_name, perm_codes in matrix.items():
        role_id = role_map[role_name]
        for code in perm_codes:
            perm_id = perm_map[code]
            rows.append({
                "id": uuid.uuid4(),
                "role_id": role_id,
                "permission_id": perm_id
            })

    if rows:
        op.bulk_insert(role_permissions, rows)



def downgrade() -> None:

    op.execute("DELETE FROM role_permissions")

