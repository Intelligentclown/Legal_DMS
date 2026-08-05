"""Shared FastAPI dependency declarations, reused across routers.

`SettingsDep` resolves through the DI container (see
`infrastructure/di/container.py`) rather than calling `get_settings()`
directly, so it's swappable in tests via `container.override(Settings, ...)`
without touching any caller. `DBSessionDep` intentionally stays on FastAPI's
native generator `Depends()` pattern — a request-scoped resource with
teardown is exactly what that's for, and the container doesn't try to
replace it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config import Settings
from app.infrastructure.database.session import get_db
from app.infrastructure.di.container import container


def get_settings_dependency() -> Settings:
    return container.resolve(Settings)


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
