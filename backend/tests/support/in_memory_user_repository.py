"""In-memory fake satisfying `UserRepository` (T50; extended T63 for
`assign_role()`/`remove_role()`), for tests that need user lookup/role-name/
role-assignment behavior without a real database.
"""

from __future__ import annotations

from uuid import UUID

from app.application.interfaces.user_repository import UserRepository
from app.infrastructure.persistence.models.identity import User, UserRole
from tests.support.in_memory_repository import InMemoryRepository


class InMemoryUserRepository(InMemoryRepository[User], UserRepository):
    def __init__(self) -> None:
        super().__init__()
        self._role_names: dict[UUID, frozenset[str]] = {}
        self._user_roles: dict[tuple[UUID, UUID], UserRole] = {}

    def set_role_names(self, user_id: UUID, role_names: frozenset[str]) -> None:
        """Test setup helper -- not part of the `UserRepository` port."""
        self._role_names[user_id] = role_names

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._items.values() if user.email == email), None)

    async def get_role_names(self, user_id: UUID) -> frozenset[str]:
        return self._role_names.get(user_id, frozenset())

    async def assign_role(self, user_id: UUID, role_id: UUID, assigned_by: UUID) -> UserRole | None:
        key = (user_id, role_id)
        if key in self._user_roles:
            return None
        user_role = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        self._user_roles[key] = user_role
        return user_role

    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        return self._user_roles.pop((user_id, role_id), None) is not None
