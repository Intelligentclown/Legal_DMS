"""Liveness check — proves the API process is up and reachable. Deliberately
has no database dependency so it stays fast and meaningful even if the
database is temporarily unavailable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from app.presentation.api.deps import SettingsDep

router = APIRouter()


@router.get("/health", summary="Liveness check")
async def health_check(settings: SettingsDep) -> dict[str, Any]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }
