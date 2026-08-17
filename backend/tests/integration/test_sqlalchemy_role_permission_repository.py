"""Integration tests for T53's `SqlAlchemyRolePermissionRepository`, against
the real migrated schema -- proves the `roles` -> `role_permissions` ->
`permissions` join actually produces the right role-name -> permission-codes
mapping, not just that the query parses.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.identity import Permission, Role, RolePermission
from app.infrastructure.persistence.sqlalchemy_role_permission_repository import (
    SqlAlchemyRolePermissionRepository,
)


def _unique_code(prefix: str) -> str:
    # permissions.code is unique, and Stage 2's seed migration already populated real
    # codes like "matters:read" -- tests must not collide with already-committed seed data.
    return f"{prefix}:{uuid4()}"


async def _grant(session: AsyncSession, role_name: str, permission_code: str) -> None:
    role = Role(name=role_name)
    permission = Permission(code=permission_code, category="test")
    session.add_all([role, permission])
    await session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await session.flush()


class TestSqlAlchemyRolePermissionRepository:
    async def test_no_role_permissions_rows_yields_empty_mapping(
        self, db_session: AsyncSession
    ) -> None:
        # T66 seeds the matrix, so we must clear it first to test the empty case.
        from sqlalchemy import text
        await db_session.execute(text("DELETE FROM role_permissions"))
        repository = SqlAlchemyRolePermissionRepository(db_session)

        mapping = await repository.get_permission_codes_by_role_name()

        assert mapping == {}

    async def test_single_grant_is_reflected(self, db_session: AsyncSession) -> None:
        role_name = f"Role-{uuid4()}"
        code = _unique_code("matters")
        await _grant(db_session, role_name, code)
        repository = SqlAlchemyRolePermissionRepository(db_session)

        mapping = await repository.get_permission_codes_by_role_name()

        assert mapping[role_name] == frozenset({code})

    async def test_role_with_multiple_granted_permissions(self, db_session: AsyncSession) -> None:
        role = Role(name=f"Role-{uuid4()}")
        read_code, write_code = _unique_code("matters"), _unique_code("matters")
        read_permission = Permission(code=read_code, category="test")
        write_permission = Permission(code=write_code, category="test")
        db_session.add_all([role, read_permission, write_permission])
        await db_session.flush()
        db_session.add_all(
            [
                RolePermission(role_id=role.id, permission_id=read_permission.id),
                RolePermission(role_id=role.id, permission_id=write_permission.id),
            ]
        )
        await db_session.flush()
        repository = SqlAlchemyRolePermissionRepository(db_session)

        mapping = await repository.get_permission_codes_by_role_name()

        assert mapping[role.name] == frozenset({read_code, write_code})

    async def test_role_with_no_grants_is_absent_from_the_mapping(
        self, db_session: AsyncSession
    ) -> None:
        ungranted_role = Role(name=f"Role-{uuid4()}")
        db_session.add(ungranted_role)
        await db_session.flush()
        repository = SqlAlchemyRolePermissionRepository(db_session)

        mapping = await repository.get_permission_codes_by_role_name()

        assert ungranted_role.name not in mapping

    async def test_two_roles_sharing_a_permission_each_get_their_own_entry(
        self, db_session: AsyncSession
    ) -> None:
        code = _unique_code("matters")
        permission = Permission(code=code, category="test")
        role_a = Role(name=f"Role-A-{uuid4()}")
        role_b = Role(name=f"Role-B-{uuid4()}")
        db_session.add_all([permission, role_a, role_b])
        await db_session.flush()
        db_session.add_all(
            [
                RolePermission(role_id=role_a.id, permission_id=permission.id),
                RolePermission(role_id=role_b.id, permission_id=permission.id),
            ]
        )
        await db_session.flush()
        repository = SqlAlchemyRolePermissionRepository(db_session)

        mapping = await repository.get_permission_codes_by_role_name()

        assert mapping[role_a.name] == frozenset({code})
        assert mapping[role_b.name] == frozenset({code})
