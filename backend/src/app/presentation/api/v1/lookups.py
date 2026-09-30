"""T146: authenticated read-only discovery of the existing Matter Type,
Matter Status and Document Type reference vocabularies.

Three bounded, deliberately identical-in-shape collection endpoints, so an
authenticated Organization user can populate the selector fields the
existing create flows already require (`matter_type_id`,
`matter_status_id`, `document_type_id`) without out-of-band knowledge of the
seeded reference rows.

These three paths cannot live in the existing `matters.py`/`documents.py`
modules: those routers are mounted under the `/matters` and
`/matters/{matter_id}/files/{file_id}/documents` prefixes respectively, so
the top-level reference collections get their own small module instead of
distorting either prefix. Everything else follows those modules' own
conventions -- a hand-written router (never the CRUD factory), a
request-scoped service dependency, `ApiResponse`, and per-route
`RequirePermission`.

Deliberate boundaries, each of which T146's authorization draws explicitly:

- **Read-only.** No create/update/delete route exists for any of the three
  vocabularies, here or anywhere else in the repository. A
  `MatterType`/`MatterStatus`/`DocumentType` row is still created exactly the
  way it always was -- by the existing seed revision.
- **Projection is existing persisted state only.** `MatterTypeRead`,
  `MatterStatusRead` and `DocumentTypeRead` populate exactly the fields the
  models already have and a selector needs: `id`, `code`, `name`, plus the
  one state flag each model genuinely carries (`is_active` on
  `MatterType`/`DocumentType`, `is_terminal` on `MatterStatus`). Nothing is
  derived, computed or invented -- in particular `MatterStatus` has no
  `is_active` column and none is exposed here.
- **Existing ordering fields only.** `MatterType`/`MatterStatus` are ordered
  by their persisted `sort_order`, then `code` as the existing unique
  tie-break. `DocumentType` has no ordering column, so it is ordered by
  `code`.
- **Existing active-state semantics only.** `MatterType`/`DocumentType` have
  a persisted `is_active` column, so both collections are filtered to active
  rows -- a selector must not offer a deactivated value. `MatterStatus` has
  no such column and is therefore returned unfiltered; `is_terminal` is a
  genuine persisted column and is projected as-is, not used as a filter.
- **Existing permissions only.** `matters:read` for the two Matter-owned
  vocabularies and `documents:read` for Document Type, through the existing
  `RequirePermission` factory. No new permission family, no anonymous
  variant, no weakening of authentication or RBAC.
- **Reference data stays reference data.** All three tables are global: no
  `organization_id` column, no RLS policy, seeded once by the existing
  revision. These routes therefore impose no Organization scoping the tables
  do not already have and manufacture no tenant ownership.

No vocabulary administration, configurability, tenant/Organization-specific
vocabulary, Work Type/Classification equivalence, workflow/Government Status
architecture, or new persistence is established here.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.application.document_service import DocumentService
from app.application.matter_service import MatterService
from app.infrastructure.persistence.models.document import DocumentType
from app.infrastructure.persistence.models.matter import MatterStatus, MatterType
from app.infrastructure.persistence.sqlalchemy_document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy_file_repository import SqlAlchemyFileRepository
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.infrastructure.persistence.sqlalchemy_party_repository import SqlAlchemyPartyRepository
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse

router = APIRouter()


async def get_matter_lookup_service(session: DBSessionDep) -> MatterService:
    """Built exactly as `matters.py` builds its own. The two lookup
    repositories here are the same ones `MatterService` already validates
    `matter_type_id`/`matter_status_id` against, so this adds no new
    persistence wiring and no new service -- only a new read."""
    return MatterService(
        SqlAlchemyMatterRepository(session),
        SqlAlchemyPartyRepository(session),
        SqlAlchemyRepository(session, MatterType),
        SqlAlchemyRepository(session, MatterStatus),
    )


async def get_document_lookup_service(session: DBSessionDep) -> DocumentService:
    """Mirrors `documents.py`'s own construction, reusing the
    `document_type_repository` that service already validates
    `document_type_id` against."""
    return DocumentService(
        SqlAlchemyDocumentRepository(session),
        SqlAlchemyFileRepository(session),
        SqlAlchemyMatterRepository(session),
        SqlAlchemyRepository(session, DocumentType),
    )


MatterLookupServiceDep = Annotated[MatterService, Depends(get_matter_lookup_service)]
DocumentLookupServiceDep = Annotated[DocumentService, Depends(get_document_lookup_service)]


class MatterTypeRead(BaseModel):
    id: UUID
    code: str
    name: str
    is_active: bool


class MatterStatusRead(BaseModel):
    id: UUID
    code: str
    name: str
    is_terminal: bool


class DocumentTypeRead(BaseModel):
    id: UUID
    code: str
    name: str
    is_active: bool


def _matter_type_read(matter_type: MatterType) -> MatterTypeRead:
    return MatterTypeRead(
        id=matter_type.id,
        code=matter_type.code,
        name=matter_type.name,
        is_active=matter_type.is_active,
    )


def _matter_status_read(matter_status: MatterStatus) -> MatterStatusRead:
    return MatterStatusRead(
        id=matter_status.id,
        code=matter_status.code,
        name=matter_status.name,
        is_terminal=matter_status.is_terminal,
    )


def _document_type_read(document_type: DocumentType) -> DocumentTypeRead:
    return DocumentTypeRead(
        id=document_type.id,
        code=document_type.code,
        name=document_type.name,
        is_active=document_type.is_active,
    )


@router.get("/matter-types", dependencies=[Depends(RequirePermission("matters:read"))])
async def list_matter_types(
    service: MatterLookupServiceDep,
) -> ApiResponse[list[MatterTypeRead]]:
    return ApiResponse(data=[_matter_type_read(row) for row in await service.list_matter_types()])


@router.get("/matter-statuses", dependencies=[Depends(RequirePermission("matters:read"))])
async def list_matter_statuses(
    service: MatterLookupServiceDep,
) -> ApiResponse[list[MatterStatusRead]]:
    return ApiResponse(
        data=[_matter_status_read(row) for row in await service.list_matter_statuses()]
    )


@router.get("/document-types", dependencies=[Depends(RequirePermission("documents:read"))])
async def list_document_types(
    service: DocumentLookupServiceDep,
) -> ApiResponse[list[DocumentTypeRead]]:
    return ApiResponse(
        data=[_document_type_read(row) for row in await service.list_document_types()]
    )
