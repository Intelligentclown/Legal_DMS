import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

EXPECTED_MATRIX = {
    "Administrator": {
        "matters:read", "matters:write", "matters:delete",
        "clients:read", "clients:write", "clients:delete",
        "properties:read", "properties:write", "properties:delete",
        "documents:read", "documents:write", "documents:delete",
        "financial:read", "financial:write",
        "users:manage", "roles:manage", "settings:manage",
        "reports:read"
    },
    "Advocate": {
        "matters:read", "matters:write", "matters:delete",
        "clients:read", "clients:write", "clients:delete",
        "properties:read", "properties:write", "properties:delete",
        "documents:read", "documents:write", "documents:delete",
        "financial:read", "reports:read"
    },
    "Paralegal": {
        "matters:read", "matters:write",
        "clients:read", "clients:write",
        "properties:read", "properties:write",
        "documents:read", "documents:write",
        "financial:read", "reports:read"
    },
    "Clerk": {
        "matters:read", "matters:write",
        "clients:read", "clients:write",
        "documents:read", "documents:write"
    },
    "Accountant": {
        "financial:read", "financial:write",
        "matters:read", "clients:read", "reports:read"
    },
    "Read Only": {
        "matters:read", "clients:read", "properties:read",
        "documents:read", "financial:read", "reports:read"
    }
}

async def test_t66_role_permissions_matrix_exact_match(db_session):
    # Fetch roles
    roles_res = await db_session.execute(text("SELECT id, name FROM roles"))
    roles = {str(r.id): r.name for r in roles_res.fetchall()}

    # Fetch permissions
    perms_res = await db_session.execute(text("SELECT id, code FROM permissions"))
    perms = {str(r.id): r.code for r in perms_res.fetchall()}

    # Fetch all role_permissions
    rp_res = await db_session.execute(text("SELECT role_id, permission_id FROM role_permissions"))
    actual_associations = rp_res.fetchall()

    # 5. Exactly 59 T66 associations
    msg = f"Expected 59 associations, got {len(actual_associations)}"
    assert len(actual_associations) == 59, msg

    # 6. No duplicate associations
    assert len(set(actual_associations)) == 59, "Found duplicate associations"

    # 1. Every authorized role exists (must have at least one permission in our matrix)
    # 2. Every authorized permission exists (must be used in our matrix)

    # Build actual matrix
    actual_matrix = {name: set() for name in EXPECTED_MATRIX}

    for rp in actual_associations:
        role_id_str = str(rp.role_id)
        perm_id_str = str(rp.permission_id)

        assert role_id_str in roles, f"Unknown role_id {role_id_str} in role_permissions"
        assert perm_id_str in perms, f"Unknown permission_id {perm_id_str} in role_permissions"

        role_name = roles[role_id_str]
        perm_code = perms[perm_id_str]

        if role_name in actual_matrix:
            actual_matrix[role_name].add(perm_code)
        else:
            pytest.fail(f"Unauthorized role found with permissions: {role_name}")

    # Check 3. Every authorized association exists
    # Check 4. No unauthorized association exists
    # 7. Incorrect role assignment detected
    # 8. Missing permission detected
    # 9. Unexpected permission detected
    for role, expected_perms in EXPECTED_MATRIX.items():
        actual_perms = actual_matrix[role]

        missing = expected_perms - actual_perms
        unexpected = actual_perms - expected_perms

        assert not missing, f"Role '{role}' is missing expected permissions: {missing}"
        assert not unexpected, f"Role '{role}' has unexpected permissions: {unexpected}"

    assert actual_matrix == EXPECTED_MATRIX
