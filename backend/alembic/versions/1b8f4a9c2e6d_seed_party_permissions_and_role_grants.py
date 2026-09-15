"""seed_party_permissions_and_role_grants (T124)

Adds the three `parties:*` permission codes and their role grants, opening
the governed Party application surface (ADR-0036 gate conditions 3 + 5: an
authorized permission surface for `parties` operations that were previously
unreachable through the application API).

Exactly the same shape T66's `224b650e5235` established for every other
resource: natural-keyed, forward-declared permission codes plus a
role -> permission matrix. `parties:read` / `parties:write` / `parties:delete`
mirror `clients:*` exactly:

    Administrator  read + write + delete
    Advocate       read + write + delete
    Paralegal      read + write
    Clerk          read + write
    Accountant     read
    Read Only      read

This takes `role_permissions` from 59 associations to 71 and `permissions`
from 18 codes to 21. Only the `permissions` and `role_permissions` tables are
touched -- no schema, RLS, or data migration here (that is T122/T123's
already-finalized work).

Revision ID: 1b8f4a9c2e6d
Revises: 62cadaff2571
Create Date: 2026-09-15 00:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b8f4a9c2e6d"
down_revision: str | Sequence[str] | None = "62cadaff2571"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARTY_PERMISSIONS = ("parties:read", "parties:write", "parties:delete")

_MATRIX: dict[str, tuple[str, ...]] = {
    "Administrator": ("parties:read", "parties:write", "parties:delete"),
    "Advocate": ("parties:read", "parties:write", "parties:delete"),
    "Paralegal": ("parties:read", "parties:write"),
    "Clerk": ("parties:read", "parties:write"),
    "Accountant": ("parties:read",),
    "Read Only": ("parties:read",),
}


def upgrade() -> None:
    connection = op.get_bind()

    roles_result = connection.execute(sa.text("SELECT id, name FROM roles")).mappings().all()
    role_map = {row["name"]: row["id"] for row in roles_result}

    perms_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    perm_map = {row["code"]: row["id"] for row in perms_result}

    missing_roles = set(_MATRIX) - set(role_map)
    if missing_roles:
        raise RuntimeError(f"roles missing for party permission grants: {sorted(missing_roles)}")

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("category", sa.String()),
    )
    party_permission_rows = [
        ("parties:read", "View parties", "parties"),
        ("parties:write", "Create and edit parties", "parties"),
        ("parties:delete", "Delete parties", "parties"),
    ]
    new_permissions = [
        {
            "id": uuid.uuid4(),
            "code": code,
            "description": description,
            "category": category,
        }
        for code, description, category in party_permission_rows
        if code not in perm_map
    ]
    if new_permissions:
        op.bulk_insert(permissions, new_permissions)
        perms_result = (
            connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
        )
        perm_map = {row["code"]: row["id"] for row in perms_result}

    role_permissions = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )

    rows = []
    for role_name, perm_codes in _MATRIX.items():
        role_id = role_map[role_name]
        for code in perm_codes:
            perm_id = perm_map[code]
            rows.append({"id": uuid.uuid4(), "role_id": role_id, "permission_id": perm_id})

    if rows:
        op.bulk_insert(role_permissions, rows)


def downgrade() -> None:
    connection = op.get_bind()

    roles_result = connection.execute(sa.text("SELECT id, name FROM roles")).mappings().all()
    role_map = {row["name"]: row["id"] for row in roles_result}

    perms_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings().all()
    perm_map = {row["code"]: row["id"] for row in perms_result}

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )

    for role_name, perm_codes in _MATRIX.items():
        role_id = role_map.get(role_name)
        if role_id is None:
            continue
        for code in perm_codes:
            perm_id = perm_map.get(code)
            if perm_id is None:
                continue
            op.execute(
                role_permissions.delete().where(
                    sa.and_(
                        role_permissions.c.role_id == role_id,
                        role_permissions.c.permission_id == perm_id,
                    )
                )
            )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    for code in _PARTY_PERMISSIONS:
        perm_id = perm_map.get(code)
        if perm_id is not None:
            op.execute(permissions.delete().where(permissions.c.id == perm_id))
