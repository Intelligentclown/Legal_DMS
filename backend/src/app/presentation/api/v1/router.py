"""Aggregates all v1 routers into one, mounted under `settings.api_v1_prefix`
in `main.py`. Future feature routers (matters, clients, documents, ...) get
included here as they're added, keeping `main.py` version-agnostic.
"""

from fastapi import APIRouter

from app.presentation.api.v1 import (
    addresses,
    auth,
    documents,
    files,
    health,
    lookups,
    matters,
    parties,
    properties,
    users,
    version,
)

router = APIRouter()
router.include_router(addresses.router, tags=["addresses"])
router.include_router(auth.router, tags=["auth"])
router.include_router(documents.router, tags=["documents"])
router.include_router(files.router, tags=["files"])
router.include_router(health.router, tags=["health"])
# T146: global reference-vocabulary discovery. Mounted before `matters` only
# for alphabetical consistency with the import/inclusion order above; these
# are distinct top-level paths with no interaction with `/matters/...`.
router.include_router(lookups.router, tags=["lookups"])
router.include_router(matters.router, tags=["matters"])
router.include_router(parties.router, tags=["parties"])
router.include_router(properties.router, tags=["properties"])
router.include_router(users.router, tags=["users"])
router.include_router(version.router, tags=["version"])
