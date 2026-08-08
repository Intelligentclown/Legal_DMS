"""User repository port (T50/ADR-0018): `AbstractRepository[User]` plus the
two lookups `AuthService` needs that the generic port can't express —
"find by email" (login) and "this user's role names" (JWT `roles` claim).
Narrow and concrete, not a general-purpose query interface: each method
exists because `AuthService` has a real, immediate caller for it, not
speculatively.

References `infrastructure.persistence.models.identity.User` directly —
per ADR-0008, this project's persistence models *are* the entities (no
separate domain-model layer exists to reference instead). `AuthService`
is the first application-layer code to depend on a concrete infrastructure
model type; earlier ports (`AbstractRepository[T]`, `BaseService[T]`)
stayed generic because nothing had a concrete entity to plug in yet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.identity import User


class UserRepository(AbstractRepository[User], ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_role_names(self, user_id: UUID) -> frozenset[str]:
        """The names (`Role.name`, e.g. `"Administrator"`) of every role
        assigned to `user_id` via `user_roles` — the exact set `AuthService`
        puts in a JWT access token's `roles` claim."""
        ...
