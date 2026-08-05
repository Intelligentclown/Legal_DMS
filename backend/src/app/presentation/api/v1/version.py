"""Reports the running application version — lets clients (and support
tooling) confirm exactly what build they're talking to.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.presentation.api.deps import SettingsDep

router = APIRouter()


@router.get("/version", summary="Application version")
async def get_version(settings: SettingsDep) -> dict[str, Any]:
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "api_prefix": settings.api_v1_prefix,
    }
