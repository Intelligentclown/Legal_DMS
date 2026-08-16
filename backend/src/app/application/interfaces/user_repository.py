"""User repository port (T50/ADR-0018): `AbstractRepository[User]` plus the
lookups/mutations `AuthService` (T50) and the `users.py` routes (T62/T63)
need that the generic port can't express — "find by email" (login), "this
user's role names" (JWT `roles` claim), and "assign/remove a role"
(`user_roles`). Narrow and concrete, not a general-purpose query interface:
each method exists because a real, immediate caller needs it, not
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
from app.infrastructure.persistence.models.identity import User, UserRole


class UserRepository(AbstractRepository[User], ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_role_names(self, user_id: UUID) -> frozenset[str]:
        """The names (`Role.name`, e.g. `"Administrator"`) of every role
        assigned to `user_id` via `user_roles` — the exact set `AuthService`
        puts in a JWT access token's `roles` claim."""
        ...

    @abstractmethod
    async def assign_role(self, user_id: UUID, role_id: UUID, assigned_by: UUID) -> UserRole | None:
        """Create the `user_roles` row for `(user_id, role_id)`, attributing
        it to `assigned_by`. Returns `None` (no row created) if the exact
        assignment already exists — the same "narrow lookup, caller decides
        the HTTP status" shape `get_by_email()` already established; the
        caller (T63's `assign_role()` route) is what turns a `None` into a
        `409 ConflictError`, not this method."""
        ...

    @abstractmethod
    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Delete the `user_roles` row for `(user_id, role_id)` if it
        exists. Returns whether a row was actually deleted — the caller
        (T63's `remove_role()` route) is what turns `False` into a `404
        NotFoundError`, not this method."""
        ...
