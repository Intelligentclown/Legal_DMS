"""Authentication + authorization ports. No login mechanism exists yet —
Stage 1 shipped only the "nobody is logged in" default
(`AnonymousAuthenticationProvider` in `infrastructure/auth/`) and a
permissive `AuthorizationService` default. A real mechanism (JWT, per
Stage 3's approved D1/D3) and real permission rules arrive with Stage 3's
later phases, satisfying these same ports.

`AuthenticationProvider.get_current_user()` takes an explicit `token`
parameter as of Stage 3 Phase 0 (D7, `ADR-0019`) — a breaking change to the
Stage 1 signature, made deliberately and documented rather than silently.
See `ADR-0019` for why the caller must pass the token in rather than the
provider discovering it some other way.
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
    async def get_current_user(self, token: str | None) -> CurrentUser:
        """Resolve `token` to a `CurrentUser`. `token=None` (no credential
        presented) must resolve the same as an invalid/expired token would
        — the anonymous default — never raise. Whether an anonymous result
        is acceptable for a given caller is a decision for
        `AuthorizationService`/the route, not this method."""
        ...


class AuthorizationService(ABC):
    @abstractmethod
    def require_permission(self, user: CurrentUser, permission: str) -> None:
        """Raise ForbiddenError if `user` may not perform `permission`."""
        ...
