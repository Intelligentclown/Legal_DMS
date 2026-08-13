"""Shared FastAPI dependency declarations, reused across routers.

`SettingsDep` resolves through the DI container (see
`infrastructure/di/container.py`) rather than calling the concrete
implementation directly, so it's swappable in tests via
`container.override(...)` without touching any caller. `DBSessionDep`
intentionally stays on FastAPI's native generator `Depends()` pattern — a
request-scoped resource with teardown is exactly what that's for, and the
container doesn't try to replace it.

`CurrentUserDep`'s two upstream services (`AuthenticationProvider`/
`AuthorizationService`) follow the *same* request-scoped pattern as
`DBSessionDep`, not the container (T55) — `JwtAuthenticationProvider`/
`RbacAuthorizationService` both need a session-backed repository, and the
container has no mechanism to hand a factory the current request's session
(`resolve()` is synchronous, takes no arguments, and is usable outside a
request at all, e.g. from background jobs — it was never meant to be
request-aware). `get_authentication_provider()`/`get_authorization_service()`
below construct their service fresh per request instead, directly from
`DBSessionDep`, mirroring `DBSessionDep`'s own reasoning rather than
resolving through the container. See `ADR-0006` and
`docs/ImplementationLog/Stage3/Phase2.md`'s `T55` batch for the full
reasoning.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.errors.exceptions import UnauthorizedError
from app.application.interfaces.auth import (
    AuthenticationProvider,
    AuthorizationService,
    CurrentUser,
)
from app.infrastructure.auth.jwt_authentication_provider import JwtAuthenticationProvider
from app.infrastructure.auth.rbac_authorization_service import RbacAuthorizationService
from app.infrastructure.config import Settings
from app.infrastructure.database.session import get_db
from app.infrastructure.di.container import container
from app.infrastructure.persistence.sqlalchemy_role_permission_repository import (
    SqlAlchemyRolePermissionRepository,
)
from app.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository


def get_settings_dependency() -> Settings:
    return container.resolve(Settings)


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_authentication_provider(
    session: DBSessionDep, settings: SettingsDep
) -> AuthenticationProvider:
    """Built fresh per request (T55) — `SqlAlchemyUserRepository` needs
    *this* request's session, not a cached/shared one."""
    return JwtAuthenticationProvider(SqlAlchemyUserRepository(session), settings)


async def get_authorization_service(session: DBSessionDep) -> AuthorizationService:
    """Built fresh per request (T55): loads the role -> granted-permissions
    mapping from the database on every call, deliberately uncached — no
    existing, already-approved caching/invalidation policy covers this data,
    and `role_permissions`'s low write volume doesn't justify inventing one
    now (see `docs/ImplementationLog/Stage3/Phase2.md`'s `T55` batch)."""
    role_permission_repository = SqlAlchemyRolePermissionRepository(session)
    permission_codes_by_role_name = (
        await role_permission_repository.get_permission_codes_by_role_name()
    )
    return RbacAuthorizationService(permission_codes_by_role_name)


_bearer_scheme = HTTPBearer(auto_error=False)


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> str | None:
    """`auto_error=False` so a missing/malformed `Authorization` header
    resolves to `None` instead of HTTPBearer raising 401 itself -- whether
    an anonymous caller is acceptable is `AuthorizationService`'s decision
    (T53/T54), not this dependency's."""
    return credentials.credentials if credentials is not None else None


async def get_current_user(
    auth_provider: Annotated[AuthenticationProvider, Depends(get_authentication_provider)],
    token: Annotated[str | None, Depends(get_bearer_token)],
) -> CurrentUser:
    return await auth_provider.get_current_user(token=token)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def RequirePermission(permission: str) -> Callable[..., Awaitable[None]]:
    """Dependency factory (T54, closes Stage 2.5's F11): use as
    `Depends(RequirePermission("matters:read"))`, either as a route
    parameter or in a router's `dependencies=[...]` list. Raises
    `UnauthorizedError` (401) if the resolved `CurrentUser` isn't
    authenticated at all (T57 -- closes the 401/403 gap: no token,
    expired/malformed/tampered token all resolve to the same
    `is_authenticated=False`, and previously fell through to
    `AuthorizationService`'s anonymous-caller branch, which raises
    `ForbiddenError`/403 indistinguishably from an authenticated-but-
    unpermitted caller). Otherwise delegates to
    `AuthorizationService.require_permission()` exactly as before, which
    still raises `ForbiddenError` (403) if `permission` isn't granted — the
    existing error handler turns either into the standard error response
    shape, no route needs to catch it itself.
    """

    async def _require_permission(
        user: CurrentUserDep,
        authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> None:
        if not user.is_authenticated:
            raise UnauthorizedError("Authentication is required")
        authorization_service.require_permission(user, permission)

    return _require_permission
