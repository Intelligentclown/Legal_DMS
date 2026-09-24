"""seed_file_permissions_and_role_grants

Revision ID: be439c0d6fdb
Revises: b8c4d2e1f7a9
Create Date: 2026-09-24 18:38:41.776418

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "be439c0d6fdb"
down_revision: str | Sequence[str] | None = "b8c4d2e1f7a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT_REVISION = "b8c4d2e1f7a9"
_FILE_PERMISSIONS = ("files:read", "files:write")
_MATRIX: dict[str, tuple[str, ...]] = {
    "Administrator": ("files:read", "files:write"),
    "Advocate": ("files:read", "files:write"),
    "Paralegal": ("files:read", "files:write"),
    "Clerk": ("files:read", "files:write"),
    "Accountant": ("files:read",),
    "Read Only": ("files:read",),
}
_PROVENANCE_FUNCTIONS = (
    "legal_dms_provenance.record_fresh_birth(uuid,uuid)",
    "legal_dms_provenance.enter_operational_fresh(uuid)",
)


def _advance_provenance_guard(from_revision: str, to_revision: str) -> None:
    connection = op.get_bind()
    for signature in _PROVENANCE_FUNCTIONS:
        definition = connection.execute(
            sa.text("SELECT pg_get_functiondef(CAST(:signature AS regprocedure))").bindparams(
                signature=signature
            )
        ).scalar_one()
        if from_revision not in definition:
            raise RuntimeError("unexpected operational-fresh provenance function contract")
        op.execute(sa.text(definition.replace(from_revision, to_revision)))


def upgrade() -> None:
    connection = op.get_bind()
    _advance_provenance_guard(_PARENT_REVISION, revision)
    roles_result = connection.execute(sa.text("SELECT id, name FROM roles")).mappings()
    roles = {row["name"]: row["id"] for row in roles_result}
    if missing_roles := set(_MATRIX) - set(roles):
        raise RuntimeError(f"roles missing for file permission grants: {sorted(missing_roles)}")
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("category", sa.String()),
    )
    permissions_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings()
    existing = {row["code"]: row["id"] for row in permissions_result}
    rows = [("files:read", "View files"), ("files:write", "Create and edit files")]
    op.bulk_insert(
        permissions,
        [
            {"id": uuid.uuid4(), "code": code, "description": desc, "category": "files"}
            for code, desc in rows
            if code not in existing
        ],
    )
    permissions_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings()
    existing = {row["code"]: row["id"] for row in permissions_result}
    role_permissions = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    grants = {
        (row["role_id"], row["permission_id"])
        for row in connection.execute(
            sa.text("SELECT role_id, permission_id FROM role_permissions")
        ).mappings()
    }
    rows = [
        {"id": uuid.uuid4(), "role_id": roles[role], "permission_id": existing[code]}
        for role, codes in _MATRIX.items()
        for code in codes
        if (roles[role], existing[code]) not in grants
    ]
    if rows:
        op.bulk_insert(role_permissions, rows)


def downgrade() -> None:
    connection = op.get_bind()
    roles_result = connection.execute(sa.text("SELECT id, name FROM roles")).mappings()
    role_map = {row["name"]: row["id"] for row in roles_result}
    permissions_result = connection.execute(sa.text("SELECT id, code FROM permissions")).mappings()
    permission_map = {row["code"]: row["id"] for row in permissions_result}
    for role, codes in _MATRIX.items():
        for code in codes:
            if role in role_map and code in permission_map:
                op.execute(
                    sa.text(
                        "DELETE FROM role_permissions WHERE role_id = :role_id "
                        "AND permission_id = :permission_id"
                    ).bindparams(role_id=role_map[role], permission_id=permission_map[code])
                )
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('files:read', 'files:write')"))
    _advance_provenance_guard(revision, _PARENT_REVISION)
