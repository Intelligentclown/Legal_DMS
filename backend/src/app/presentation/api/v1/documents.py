"""File-canonical Document metadata routes (T139)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.document_service import DocumentService
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.persistence.models.document import Document, DocumentType
from app.infrastructure.persistence.sqlalchemy_document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy_file_repository import SqlAlchemyFileRepository
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
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
