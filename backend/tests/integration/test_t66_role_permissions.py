import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

EXPECTED_MATRIX = {
    "Administrator": {
        "addresses:delete",
        "addresses:read",
        "addresses:write",
        "clients:delete",
        "clients:read",
        "clients:write",
        "documents:delete",
        "documents:read",
        "documents:write",
        "enquiries:read",
        "enquiries:write",
        "files:read",
        "files:write",
        "financial:read",
        "financial:write",
        "matters:delete",
        "matters:read",
        "matters:write",
        "parties:delete",
        "parties:read",
        "parties:write",
        "properties:delete",
        "properties:read",
        "properties:write",
        "quotations:accept",
        "quotations:read",
        "quotations:write",
        "reports:read",
        "roles:manage",
        "settings:manage",
        "users:manage",
    },
    "Advocate": {
        "addresses:delete",
        "addresses:read",
        "addresses:write",
        "clients:delete",
        "clients:read",
        "clients:write",
        "documents:delete",
        "documents:read",
        "documents:write",
        "enquiries:read",
        "enquiries:write",
        "files:read",
        "files:write",
        "financial:read",
        "matters:delete",
        "matters:read",
        "matters:write",
        "parties:delete",
        "parties:read",
        "parties:write",
        "properties:delete",
        "properties:read",
        "properties:write",
        "quotations:accept",
        "quotations:read",
        "quotations:write",
        "reports:read",
    },
    "Paralegal": {
        "addresses:read",
        "addresses:write",
        "clients:read",
        "clients:write",
        "documents:read",
        "documents:write",
        "enquiries:read",
        "enquiries:write",
        "files:read",
        "files:write",
        "financial:read",
        "matters:read",
        "matters:write",
        "parties:read",
        "parties:write",
        "properties:read",
        "properties:write",
        "quotations:read",
        "quotations:write",
        "reports:read",
    },
    "Clerk": {
        "addresses:read",
        "addresses:write",
        "clients:read",
        "clients:write",
        "documents:read",
        "documents:write",
        "enquiries:read",
        "enquiries:write",
        "files:read",
        "files:write",
        "matters:read",
        "matters:write",
        "parties:read",
        "parties:write",
        "quotations:read",
    },
    "Accountant": {
        "addresses:read",
        "clients:read",
        "enquiries:read",
        "files:read",
        "financial:read",
        "financial:write",
        "matters:read",
        "parties:read",
        "quotations:read",
        "reports:read",
    },
    "Read Only": {
        "addresses:read",
        "clients:read",
        "documents:read",
        "enquiries:read",
        "files:read",
        "financial:read",
        "matters:read",
        "parties:read",
        "properties:read",
        "quotations:read",
        "reports:read",
    },
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

    # Current head adds file and enquiry/quotation permission families to the
    # original T66/T124/T130 matrix; retain an exact, non-permissive contract.
    expected_associations = sum(len(codes) for codes in EXPECTED_MATRIX.values())
    msg = f"Expected {expected_associations} associations, got {len(actual_associations)}"
    assert len(actual_associations) == expected_associations, msg

    # 6. No duplicate associations
    assert len(set(actual_associations)) == expected_associations, "Found duplicate associations"

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
