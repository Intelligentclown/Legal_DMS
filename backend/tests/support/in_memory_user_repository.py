"""In-memory fake satisfying `UserRepository` (T50), for tests that need
user lookup/role-name behavior without a real database.
"""

from __future__ import annotations

from uuid import UUID

from app.application.interfaces.user_repository import UserRepository
from app.infrastructure.persistence.models.identity import User
from tests.support.in_memory_repository import InMemoryRepository


class InMemoryUserRepository(InMemoryRepository[User], UserRepository):
    def __init__(self) -> None:
        super().__init__()
        self._role_names: dict[UUID, frozenset[str]] = {}

    def set_role_names(self, user_id: UUID, role_names: frozenset[str]) -> None:
        """Test setup helper -- not part of the `UserRepository` port."""
        self._role_names[user_id] = role_names

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._items.values() if user.email == email), None)

    async def get_role_names(self, user_id: UUID) -> frozenset[str]:
        return self._role_names.get(user_id, frozenset())
