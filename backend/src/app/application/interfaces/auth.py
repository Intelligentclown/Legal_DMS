"""Authentication + authorization ports. No login mechanism exists yet —
Stage 1 ships only the "nobody is logged in" default
(`AnonymousAuthenticationProvider` in `infrastructure/auth/`) and a
permissive `AuthorizationService` default. A real mechanism (session, JWT,
...) and real permission rules arrive with a future auth stage, satisfying
these same ports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Shape of "who is acting" — not a User domain entity (none exists
    yet). The default (`CurrentUser()`) represents an anonymous caller.
    """

    id: str | None = None
    display_name: str = "Anonymous"
    roles: frozenset[str] = field(default_factory=frozenset)
    is_authenticated: bool = False


class AuthenticationProvider(ABC):
    @abstractmethod
    async def get_current_user(self) -> CurrentUser: ...


class AuthorizationService(ABC):
    @abstractmethod
    def require_permission(self, user: CurrentUser, permission: str) -> None:
        """Raise ForbiddenError if `user` may not perform `permission`."""
        ...
