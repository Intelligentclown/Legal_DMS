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

        # T105/ADR-0021: set app.current_user_id *before* the self-lookup below --
        # this is the RLS self-row carve-out that lets a caller read its own
        # `users` row before any Organization context is known (chicken-and-egg
        # a plain org-scoped policy alone can't solve). Runs on this provider's
        # own repository's session, the same DBSessionDep-yielded session every
        # other dependent of this request also receives (see get_db()/deps.py) --
        # so this GUC is visible to every later query in the same request.
        await self._user_repository.set_current_user_context(user_id)

        user = await self._user_repository.get_by_id(user_id)
        if user is None or not user.is_active:
            return CurrentUser()

        roles = await self._user_repository.get_role_names(user.id)

        # T105/ADR-0031 SS6.5: live, per-request rederivation from the database,
        # mirroring the roles lookup above exactly -- never a JWT claim. Fail-
        # closed either way (never a cast error): the RLS policies themselves
        # NULLIF() every current_setting() read before casting to ::uuid, since
        # a bound None here doesn't reliably read back as true SQL NULL once
        # this GUC has ever been set on the underlying pooled connection (see
        # SqlAlchemyUserRepository.set_current_organization_context()).
        await self._user_repository.set_current_organization_context(user.organization_id)

        return CurrentUser(
            id=str(user.id),
            display_name=user.full_name,
            roles=roles,
            is_authenticated=True,
            organization_id=str(user.organization_id) if user.organization_id else None,
        )
