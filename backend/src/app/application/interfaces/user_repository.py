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
from collections.abc import Sequence
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

    @abstractmethod
    async def set_current_user_context(self, user_id: UUID) -> None:
        """T105/ADR-0021: sets the `app.current_user_id` Postgres session GUC
        (transaction-local) on this repository's own session/connection —
        the self-row RLS carve-out `JwtAuthenticationProvider` needs *before*
        it can read its own `users` row to resolve an Organization (a
        chicken-and-egg the plain org-scoped policy alone can't solve). Not
        an ordinary data-access method — exists solely to propagate tenant
        context, per `ADR/0021`'s "set once per session, before any
        tenant-scoped query" requirement."""
        ...

    @abstractmethod
    async def set_current_organization_context(self, organization_id: UUID | None) -> None:
        """T105/ADR-0021: sets the `app.current_organization_id` Postgres
        session GUC (transaction-local) via a bound `NULL` for a caller with
        no resolved Organization yet. Fail-closed either way — the RLS
        policies themselves (not this call) are what guarantee no
        empty-string cast error, since Postgres does not reliably return
        true `NULL` from `current_setting()` for a custom GUC that was ever
        `set_config()`-ed to `NULL` on that connection (verified directly,
        not assumed — see `SqlAlchemyUserRepository`'s implementation)."""
        ...

    @abstractmethod
    async def get_by_id_in_organization(self, user_id: UUID, organization_id: UUID) -> User | None:
        """T105: the target user, only if it belongs to `organization_id` —
        used by `users.py`'s org-scoped routes so a cross-Organization
        request gets the same `404` as a nonexistent id, never a data leak."""
        ...

    @abstractmethod
    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[User]:
        """T105: every `User` in `organization_id`, paginated — the
        org-scoped equivalent of the generic `list()` `GET /users` used
        before this task."""
        ...

    @abstractmethod
    async def count_in_organization(self, organization_id: UUID) -> int:
        """T105: total `User` count in `organization_id` — the org-scoped
        equivalent of the generic `count()`, for pagination metadata."""
        ...
