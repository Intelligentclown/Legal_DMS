"""SQLAlchemy implementation of `RolePermissionRepository` (T53): one query
joining `roles` -> `role_permissions` -> `permissions`, grouped into a
role-name -> permission-codes mapping.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.role_permission_repository import RolePermissionRepository
from app.infrastructure.persistence.models.identity import Permission, Role, RolePermission


class SqlAlchemyRolePermissionRepository(RolePermissionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_permission_codes_by_role_name(self) -> Mapping[str, frozenset[str]]:
        stmt = (
            select(Role.name, Permission.code)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
        )
        result = await self._session.execute(stmt)

        codes_by_role: dict[str, set[str]] = {}
        for role_name, permission_code in result.all():
            codes_by_role.setdefault(role_name, set()).add(permission_code)

        return {role_name: frozenset(codes) for role_name, codes in codes_by_role.items()}
