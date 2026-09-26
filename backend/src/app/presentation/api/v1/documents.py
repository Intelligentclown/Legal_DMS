"""File-canonical Document metadata routes (T139)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.document_service import DocumentService
from app.application.document_version_service import DocumentVersionService
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.application.interfaces.file_storage import FileStorage
from app.infrastructure.di.container import container
from app.infrastructure.persistence.models.document import Document, DocumentType
from app.infrastructure.persistence.sqlalchemy_document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy_document_version_repository import (
    SqlAlchemyDocumentVersionRepository,
)
from app.infrastructure.persistence.sqlalchemy_file_repository import SqlAlchemyFileRepository
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import (
    CurrentUserDep,
    DBSessionDep,
    RequirePermission,
    TransactionOutcomeContextDep,
)
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/matters/{matter_id}/files/{file_id}/documents")


async def get_document_service(session: DBSessionDep) -> DocumentService:
    return DocumentService(
        SqlAlchemyDocumentRepository(session),
        SqlAlchemyFileRepository(session),
        SqlAlchemyMatterRepository(session),
        SqlAlchemyRepository(session, DocumentType),
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


async def get_document_version_service(
    session: DBSessionDep, outcome: TransactionOutcomeContextDep
) -> DocumentVersionService:
    return DocumentVersionService(
        SqlAlchemyDocumentVersionRepository(session), container.resolve(FileStorage), outcome
    )


DocumentVersionServiceDep = Annotated[DocumentVersionService, Depends(get_document_version_service)]


class DocumentCreate(BaseModel):
    document_type_id: UUID
    title: str = Field(min_length=1, max_length=255)
    status: str = Field(default="draft", min_length=1, max_length=50)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=50)
    document_type_id: UUID | None = None
    version: int | None = Field(default=None, ge=1)


class DocumentRead(BaseModel):
    id: UUID
    document_type_id: UUID
    title: str
    status: str
    version: int


class DocumentVersionRead(BaseModel):
    id: UUID
    version_number: int
    change_summary: str | None
    created_at: object | None


def _organization(user: CurrentUser) -> UUID:
    if user.organization_id is None:
        raise ForbiddenError("No Organization context is resolved for this caller")
    return UUID(user.organization_id)


def _read(document: Document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        document_type_id=document.document_type_id,
        title=document.title,
        status=document.status,
        version=document.version,
    )


def _version_read(version) -> DocumentVersionRead:
    return DocumentVersionRead(
        id=version.id,
        version_number=version.version_number,
        change_summary=version.change_summary,
        created_at=version.created_at,
    )


@router.get("", dependencies=[Depends(RequirePermission("documents:read"))])
async def list_documents(
    matter_id: UUID,
    file_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[DocumentRead]]:
    request = PageRequest(page=page, page_size=page_size)
    organization_id = _organization(current_user)
    documents = await service.list_in_file(
        organization_id, matter_id, file_id, limit=request.limit, offset=request.offset
    )
    result = PageResult.create(
        [_read(document) for document in documents],
        total=await service.count_in_file(organization_id, matter_id, file_id),
        request=request,
    )
    response = paginated_response(result)
    return ApiResponse(data=response.data, meta=response.meta)


@router.get("/{document_id}", dependencies=[Depends(RequirePermission("documents:read"))])
async def get_document(
    matter_id: UUID,
    file_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> ApiResponse[DocumentRead]:
    return ApiResponse(
        data=_read(
            await service.get_in_file(document_id, _organization(current_user), matter_id, file_id)
        )
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("documents:write"))],
)
async def create_document(
    matter_id: UUID,
    file_id: UUID,
    payload: DocumentCreate,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> ApiResponse[DocumentRead]:
    actor_id = UUID(current_user.id) if current_user.id is not None else None
    return ApiResponse(
        data=_read(
            await service.create_in_file(
                _organization(current_user),
                matter_id,
                file_id,
                payload.model_dump(),
                actor_id=actor_id,
            )
        )
    )


@router.put("/{document_id}", dependencies=[Depends(RequirePermission("documents:write"))])
async def update_document(
    matter_id: UUID,
    file_id: UUID,
    document_id: UUID,
    payload: DocumentUpdate,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> ApiResponse[DocumentRead]:
    actor_id = UUID(current_user.id) if current_user.id is not None else None
    fields = {field: getattr(payload, field) for field in payload.model_fields_set}
    return ApiResponse(
        data=_read(
            await service.update_in_file(
                document_id,
                _organization(current_user),
                matter_id,
                file_id,
                fields,
                actor_id=actor_id,
            )
        )
    )


@router.get("/{document_id}/versions", dependencies=[Depends(RequirePermission("documents:read"))])
async def list_document_versions(
    matter_id: UUID,
    file_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    versions: DocumentVersionServiceDep,
) -> ApiResponse[list[DocumentVersionRead]]:
    document = await documents.get_in_file(
        document_id, _organization(current_user), matter_id, file_id
    )
    return ApiResponse(
        data=[
            _version_read(version)
            for version in await versions.list(_organization(current_user), document)
        ]
    )


@router.get(
    "/{document_id}/versions/latest", dependencies=[Depends(RequirePermission("documents:read"))]
)
async def latest_document_version(
    matter_id: UUID,
    file_id: UUID,
    document_id: UUID,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    versions: DocumentVersionServiceDep,
) -> ApiResponse[DocumentVersionRead]:
    organization_id = _organization(current_user)
    document = await documents.get_in_file(document_id, organization_id, matter_id, file_id)
    return ApiResponse(data=_version_read(await versions.latest(organization_id, document)))


@router.get(
    "/{document_id}/versions/{version_id}",
    dependencies=[Depends(RequirePermission("documents:read"))],
)
async def get_document_version(
    matter_id: UUID,
    file_id: UUID,
    document_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    versions: DocumentVersionServiceDep,
) -> ApiResponse[DocumentVersionRead]:
    organization_id = _organization(current_user)
    document = await documents.get_in_file(document_id, organization_id, matter_id, file_id)
    return ApiResponse(
        data=_version_read(await versions.get(organization_id, document, version_id))
    )


@router.post(
    "/{document_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("documents:write"))],
)
async def create_document_version(
    matter_id: UUID,
    file_id: UUID,
    document_id: UUID,
    content: Annotated[bytes, Body()],
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    versions: DocumentVersionServiceDep,
    filename: Annotated[str, Header(alias="X-Filename")],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    mime_type: Annotated[str | None, Header(alias="Content-Type")] = None,
    change_summary: str | None = None,
) -> ApiResponse[DocumentVersionRead]:
    organization_id = _organization(current_user)
    document = await documents.get_in_file(document_id, organization_id, matter_id, file_id)
    version = await versions.create(
        organization_id,
        document,
        content,
        filename,
        mime_type,
        idempotency_key,
        UUID(current_user.id) if current_user.id else None,
        change_summary,
    )
    return ApiResponse(data=_version_read(version))


@router.get(
    "/{document_id}/versions/{version_id}/content",
    dependencies=[Depends(RequirePermission("documents:read"))],
)
async def download_document_version(
    matter_id: UUID,
    file_id: UUID,
    document_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    documents: DocumentServiceDep,
    versions: DocumentVersionServiceDep,
) -> Response:
    organization_id = _organization(current_user)
    document = await documents.get_in_file(document_id, organization_id, matter_id, file_id)
    _version, record, content = await versions.download(organization_id, document, version_id)
    return Response(
        content=content,
        media_type=record.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{record.original_filename}"'},
    )
