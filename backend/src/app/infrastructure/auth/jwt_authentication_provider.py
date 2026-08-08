"""Real `AuthenticationProvider` (T52/D7/ADR-0019): decodes a bearer token
via `T47`'s JWT utility, then re-derives the caller's identity and roles
live from the database via `T50`'s `UserRepository` -- never trusts a
token's own claims as the source of truth for anything beyond "which user,"
matching the defense-in-depth pattern `AuthService.refresh()` already
established (a revoked/deactivated user or a role change takes effect
immediately, not only after the token's own `exp`).

`token=None`, a malformed/expired/tampered token, an unknown/malformed
`sub`, or an inactive user all resolve to the same anonymous default --
never raises. Whether an anonymous result is acceptable for a given route
is `AuthorizationService`'s decision (`T53`), not this class's.
"""

from __future__ import annotations

from uuid import UUID

from app.application.interfaces.auth import AuthenticationProvider, CurrentUser
from app.application.interfaces.user_repository import UserRepository
from app.infrastructure.config.settings import Settings
from app.infrastructure.security.jwt_service import decode_token


class JwtAuthenticationProvider(AuthenticationProvider):
    def __init__(self, user_repository: UserRepository, settings: Settings) -> None:
        self._user_repository = user_repository
        self._settings = settings

    async def get_current_user(self, token: str | None) -> CurrentUser:
        if token is None:
            return CurrentUser()

        claims = decode_token(token, self._settings)
        if claims is None:
            return CurrentUser()

        try:
            user_id = UUID(claims["sub"])
        except (KeyError, ValueError, TypeError):
            return CurrentUser()

        user = await self._user_repository.get_by_id(user_id)
        if user is None or not user.is_active:
            return CurrentUser()

        roles = await self._user_repository.get_role_names(user.id)
        return CurrentUser(
            id=str(user.id),
            display_name=user.full_name,
            roles=roles,
            is_authenticated=True,
        )
