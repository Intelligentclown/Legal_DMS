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

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.auth import AuthenticationProvider, CurrentUser
from app.infrastructure.config import Settings
from app.infrastructure.database.session import get_db
from app.infrastructure.di.container import container


def get_settings_dependency() -> Settings:
    return container.resolve(Settings)


def get_authentication_provider() -> AuthenticationProvider:
    return container.resolve(AuthenticationProvider)


async def get_current_user(
    auth_provider: Annotated[AuthenticationProvider, Depends(get_authentication_provider)],
) -> CurrentUser:
    return await auth_provider.get_current_user()


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
