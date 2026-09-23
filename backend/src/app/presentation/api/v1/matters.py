"""Bounded T134 Organization-scoped Matter application endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.application.matter_service import MatterService
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.party import MatterParty
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.infrastructure.persistence.sqlalchemy_party_repository import SqlAlchemyPartyRepository
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/matters")


async def get_matter_service(session: DBSessionDep) -> MatterService:
    return MatterService(
        SqlAlchemyMatterRepository(session),
        SqlAlchemyPartyRepository(session),
        SqlAlchemyRepository(session, MatterType),
        SqlAlchemyRepository(session, MatterStatus),
    )


MatterServiceDep = Annotated[MatterService, Depends(get_matter_service)]


class MatterParticipantCreate(BaseModel):
    party_id: UUID
    role: str = Field(min_length=1, max_length=50)


class MatterParticipantRead(BaseModel):
    party_id: UUID
    role: str


class MatterCreate(BaseModel):
    matter_number: str = Field(min_length=1, max_length=50)
    matter_type_id: UUID
    matter_status_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    opened_at: datetime
    client_party_id: UUID
    participants: list[MatterParticipantCreate] = Field(default_factory=list)


class MatterUpdate(BaseModel):
    matter_type_id: UUID | None = None
    matter_status_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    opened_at: datetime | None = None
    closed_at: datetime | None = None


class MatterRead(BaseModel):
    id: UUID
    matter_number: str
    matter_type_id: UUID
    matter_status_id: UUID
    title: str
    description: str | None
    opened_at: datetime
    closed_at: datetime | None
    legacy_client_id: UUID | None
    participants: list[MatterParticipantRead]


def _require_organization(current_user: CurrentUser) -> UUID:
    if current_user.organization_id is None:
        raise ForbiddenError("No Organization context is resolved for this caller")
    return UUID(current_user.organization_id)


def _to_read(matter: Matter, participants: list[MatterParty]) -> MatterRead:
    return MatterRead(
        id=matter.id,
        matter_number=matter.matter_number,
        matter_type_id=matter.matter_type_id,
        matter_status_id=matter.matter_status_id,
        title=matter.title,
        description=matter.description,
        opened_at=matter.opened_at,
        closed_at=matter.closed_at,
        legacy_client_id=matter.client_id,
        participants=[
            MatterParticipantRead(party_id=row.party_id, role=row.role) for row in participants
        ],
    )


@router.get("", dependencies=[Depends(RequirePermission("matters:read"))])
async def list_matters(
    current_user: CurrentUserDep,
    service: MatterServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[MatterRead]]:
    organization_id = _require_organization(current_user)
    request = PageRequest(page=page, page_size=page_size)
    matters = await service.list_in_organization(
        organization_id, limit=request.limit, offset=request.offset
    )
    total = await service.count_in_organization(organization_id)
    reads = [_to_read(matter, list(await service.participants(matter))) for matter in matters]
    page_result = PageResult.create(reads, total=total, request=request)
    response = paginated_response(page_result)
    return ApiResponse(data=response.data, meta=response.meta)


@router.get("/{matter_id}", dependencies=[Depends(RequirePermission("matters:read"))])
async def get_matter(
    matter_id: UUID, current_user: CurrentUserDep, service: MatterServiceDep
) -> ApiResponse[MatterRead]:
    matter = await service.get_in_organization(matter_id, _require_organization(current_user))
    return ApiResponse(data=_to_read(matter, list(await service.participants(matter))))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("matters:write"))],
)
async def create_matter(
    payload: MatterCreate, current_user: CurrentUserDep, service: MatterServiceDep
) -> ApiResponse[MatterRead]:
    matter = await service.create_in_organization(
        _require_organization(current_user),
        payload.model_dump(exclude={"client_party_id", "participants"}),
        payload.client_party_id,
        [(row.party_id, row.role) for row in payload.participants],
    )
    return ApiResponse(data=_to_read(matter, list(await service.participants(matter))))


@router.put("/{matter_id}", dependencies=[Depends(RequirePermission("matters:write"))])
async def update_matter(
    matter_id: UUID, payload: MatterUpdate, current_user: CurrentUserDep, service: MatterServiceDep
) -> ApiResponse[MatterRead]:
    changes = {key: getattr(payload, key) for key in payload.model_fields_set}
    matter = await service.update_in_organization(
        matter_id, _require_organization(current_user), changes
    )
    return ApiResponse(data=_to_read(matter, list(await service.participants(matter))))
