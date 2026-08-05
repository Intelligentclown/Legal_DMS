"""Aggregates all v1 routers into one, mounted under `settings.api_v1_prefix`
in `main.py`. Future feature routers (matters, clients, documents, ...) get
included here as they're added, keeping `main.py` version-agnostic.
"""

from fastapi import APIRouter

from app.presentation.api.v1 import health, version

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(version.router, tags=["version"])
