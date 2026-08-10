"""Shared FastAPI dependency declarations, reused across routers.

`SettingsDep` and `CurrentUserDep` resolve through the DI container (see
`infrastructure/di/container.py`) rather than calling the concrete
implementation directly, so they're swappable in tests via
`container.override(...)` without touching any caller. `DBSessionDep`
intentionally stays on FastAPI's native generator `Depends()` pattern — a
request-scoped resource with teardown is exactly what that's for, and the
container doesn't try to replace it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.auth import (
    AuthenticationProvider,
    AuthorizationService,
    CurrentUser,
)
from app.infrastructure.config import Settings
from app.infrastructure.database.session import get_db
from app.infrastructure.di.container import container


def get_settings_dependency() -> Settings:
    return container.resolve(Settings)


def get_authentication_provider() -> AuthenticationProvider:
    return container.resolve(AuthenticationProvider)


def get_authorization_service() -> AuthorizationService:
    return container.resolve(AuthorizationService)


async def get_current_user(
    auth_provider: Annotated[AuthenticationProvider, Depends(get_authentication_provider)],
) -> CurrentUser:
    # token=None is a Stage 3 Phase 0 placeholder: real bearer-token
    # extraction from the request (HTTPBearer/OAuth2PasswordBearer) is
    # T56 (Phase 2), not yet built. AnonymousAuthenticationProvider ignores
    # the value either way, so behavior is unchanged until T56 lands.
    return await auth_provider.get_current_user(token=None)


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def RequirePermission(permission: str) -> Callable[..., Awaitable[None]]:
    """Dependency factory (T54, closes Stage 2.5's F11): use as
    `Depends(RequirePermission("matters:read"))`, either as a route
    parameter or in a router's `dependencies=[...]` list. Raises
    `ForbiddenError` (via `AuthorizationService.require_permission()`) if
    the resolved `CurrentUser` may not perform `permission` — the existing
    error handler turns that into the standard 403 response shape, no
    route needs to catch it itself.
    """

    async def _require_permission(
        user: CurrentUserDep,
        authorization_service: Annotated[AuthorizationService, Depends(get_authorization_service)],
    ) -> None:
        authorization_service.require_permission(user, permission)

    return _require_permission
