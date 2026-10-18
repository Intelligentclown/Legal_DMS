"""Bounded T134 Organization-scoped Matter application endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.application.matter_property_service import MatterPropertyService
from app.application.matter_service import MatterService
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.party import MatterParty
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.sqlalchemy_matter_property_repository import (
    SqlAlchemyMatterPropertyRepository,
)
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.infrastructure.persistence.sqlalchemy_party_repository import SqlAlchemyPartyRepository
from app.infrastructure.persistence.sqlalchemy_property_repository import (
    SqlAlchemyPropertyRepository,
)
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import (
    AuditLoggerDep,
    CurrentUserDep,
    DBSessionDep,
    RequirePermission,
)
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


async def get_matter_property_service(
    session: DBSessionDep, audit_logger: AuditLoggerDep
) -> MatterPropertyService:
    return MatterPropertyService(
        SqlAlchemyMatterRepository(session),
        SqlAlchemyPropertyRepository(session),
        SqlAlchemyMatterPropertyRepository(session),
        audit_logger,
    )


MatterPropertyServiceDep = Annotated[MatterPropertyService, Depends(get_matter_property_service)]


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


class MatterPropertyCreate(BaseModel):
    property_id: UUID


class AssociatedPropertyOwnerRead(BaseModel):
    party_id: UUID | None
    legacy_client_id: UUID | None
    ownership_share: Decimal | None
    ownership_type: str
    from_date: date
    to_date: date | None


class AssociatedPropertyRead(BaseModel):
    """Property response-compatible representation for Matter association APIs."""

    id: UUID
    property_type: str
    survey_number: str
    sub_division_number: str | None
    area_value: Decimal | None
    area_unit: str | None
    address_id: UUID | None
    village_id: UUID | None
    registration_number: str | None
    owners: list[AssociatedPropertyOwnerRead]


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


def _property_to_read(property_: Property, owners: list[PropertyOwner]) -> AssociatedPropertyRead:
    return AssociatedPropertyRead(
        id=property_.id,
        property_type=property_.property_type,
        survey_number=property_.survey_number,
        sub_division_number=property_.sub_division_number,
        area_value=property_.area_value,
        area_unit=property_.area_unit,
        address_id=property_.address_id,
        village_id=property_.village_id,
        registration_number=property_.registration_number,
        owners=[
            AssociatedPropertyOwnerRead(
                party_id=row.party_id,
                legacy_client_id=row.client_id,
                ownership_share=row.ownership_share,
                ownership_type=row.ownership_type,
                from_date=row.from_date,
                to_date=row.to_date,
            )
            for row in owners
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


@router.get(
    "/{matter_id}/properties",
    dependencies=[
        Depends(RequirePermission("matters:read")),
        Depends(RequirePermission("properties:read")),
    ],
)
async def list_matter_properties(
    matter_id: UUID,
    current_user: CurrentUserDep,
    service: MatterPropertyServiceDep,
) -> ApiResponse[list[AssociatedPropertyRead]]:
    """List only canonical MatterProperty-backed, tenant-visible Properties."""
    organization_id = _require_organization(current_user)
    properties = await service.list_properties(matter_id, organization_id)
    reads = [
        _property_to_read(property_, list(await service.owners(property_)))
        for property_ in properties
    ]
    return ApiResponse(data=reads)


@router.post(
    "/{matter_id}/properties",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(RequirePermission("matters:write")),
        Depends(RequirePermission("properties:read")),
    ],
)
async def associate_matter_property(
    matter_id: UUID,
    payload: MatterPropertyCreate,
    response: Response,
    current_user: CurrentUserDep,
    service: MatterPropertyServiceDep,
) -> ApiResponse[AssociatedPropertyRead]:
    organization_id = _require_organization(current_user)
    property_, created = await service.associate(
        matter_id, payload.property_id, organization_id, current_user
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return ApiResponse(data=_property_to_read(property_, list(await service.owners(property_))))


@router.delete(
    "/{matter_id}/properties/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(RequirePermission("matters:write")),
        Depends(RequirePermission("properties:read")),
    ],
)
async def unlink_matter_property(
    matter_id: UUID,
    property_id: UUID,
    current_user: CurrentUserDep,
    service: MatterPropertyServiceDep,
) -> None:
    await service.unlink(matter_id, property_id, _require_organization(current_user), current_user)


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
