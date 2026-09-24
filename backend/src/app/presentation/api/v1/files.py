"""T138 File routes; File numbers and tenant identity are server-owned."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.errors.exceptions import ForbiddenError
from app.application.file_service import FileService
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.persistence.models.file import File
from app.infrastructure.persistence.sqlalchemy_file_repository import SqlAlchemyFileRepository
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/matters/{matter_id}/files")


async def get_file_service(session: DBSessionDep) -> FileService:
    return FileService(SqlAlchemyFileRepository(session), SqlAlchemyMatterRepository(session))


FileServiceDep = Annotated[FileService, Depends(get_file_service)]


class FileCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class FileUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


class FileRead(BaseModel):
    id: UUID
    matter_id: UUID
    file_number: int
    title: str
    version: int


def _organization(user: CurrentUser) -> UUID:
    if user.organization_id is None:
        raise ForbiddenError("No Organization context is resolved for this caller")
    return UUID(user.organization_id)


def _read(file: File) -> FileRead:
    return FileRead(
        id=file.id,
        matter_id=file.matter_id,
        file_number=file.file_number,
        title=file.title,
        version=file.version,
    )


@router.get("", dependencies=[Depends(RequirePermission("files:read"))])
async def list_files(
    matter_id: UUID,
    current_user: CurrentUserDep,
    service: FileServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[FileRead]]:
    request = PageRequest(page=page, page_size=page_size)
    organization_id = _organization(current_user)
    files = await service.list_in_matter(
        organization_id, matter_id, limit=request.limit, offset=request.offset
    )
    result = PageResult.create(
        [_read(file) for file in files],
        total=await service.count_in_matter(organization_id, matter_id),
        request=request,
    )
    response = paginated_response(result)
    return ApiResponse(data=response.data, meta=response.meta)


@router.get("/{file_id}", dependencies=[Depends(RequirePermission("files:read"))])
async def get_file(
    matter_id: UUID, file_id: UUID, current_user: CurrentUserDep, service: FileServiceDep
) -> ApiResponse[FileRead]:
    return ApiResponse(
        data=_read(await service.get_in_matter(file_id, _organization(current_user), matter_id))
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("files:write"))],
)
async def create_file(
    matter_id: UUID, payload: FileCreate, current_user: CurrentUserDep, service: FileServiceDep
) -> ApiResponse[FileRead]:
    actor_id = UUID(current_user.id) if current_user.id is not None else None
    return ApiResponse(
        data=_read(
            await service.create_in_matter(
                _organization(current_user), matter_id, payload.title, actor_id=actor_id
            )
        )
    )


@router.put("/{file_id}", dependencies=[Depends(RequirePermission("files:write"))])
async def update_file(
    matter_id: UUID,
    file_id: UUID,
    payload: FileUpdate,
    current_user: CurrentUserDep,
    service: FileServiceDep,
) -> ApiResponse[FileRead]:
    fields = {field: getattr(payload, field) for field in payload.model_fields_set}
    actor_id = UUID(current_user.id) if current_user.id is not None else None
    return ApiResponse(
        data=_read(
            await service.update_title_in_matter(
                file_id, _organization(current_user), matter_id, fields, actor_id=actor_id
            )
        )
    )
