"""`GET /properties`, `GET /properties/{id}`, `POST /properties`, and
`PUT /properties/{id}` (T135): the governed Property application surface
over the tenant-finalized aggregate (T133), with Party-canonical ownership.

Follows the `matters.py` (T134) and `addresses.py` (T130) conventions exactly:

- hand-written router (the `crud_router_factory.py` is deliberately unused,
  per T62's own precedence), mirroring the same
  `ApiResponse`/pagination/`_to_read` shape;
- per-route `RequirePermission` for the two already-seeded Property
  permission codes: `properties:read` on list/get and `properties:write` on
  create/update (DELETE is deliberately omitted — the T134/T133 boundary
  keeps no governed Property lifecycle/deletion contract);
- Organization is derived only from the authenticated context
  (`_require_organization()`, mirroring `parties.py`'s fail-closed helper) and
  `PropertyService`/`PropertyRepository` are org-scoped, so a caller can never
  operate on another tenant's Property — cross-Org access reads as 404 and is
  gated identically to a nonexistent id;
- create accepts an optional `owners` list; every owner is Party-canonical
  (`party_id` belonging to the caller's Organization, `client_id` never
  written). Legacy Client-linked owners are read-only compatibility:
  `PropertyRead.owners[].party_id` is the canonical identity and
  `legacy_client_id` exposes retained Client links without collapsing the two
  identities into one field (T135, following T134's `legacy_client_id`
  precedent);
- validation: `property_type` is bounded by a `Literal` matching the model's
  CHECK constraint, `survey_number` is required and cannot be cleared, every
  provided `address_id` must belong to the caller's Organization (422, not a
  composite-FK 500), and a provided `village_id` must resolve to an existing
  reference row (422, not an FK 500);
- update is bounded to the ordinary scalar Property fields and never touches
  owner rows; extraneous request fields (including `client_id`) are ignored.

`PropertyRead` deliberately omits `organization_id` and the audit columns
(mirrors `PartyRead`/`AddressRead` omitting sensitive/internal fields) —
`_to_read()` only ever populates the fields the read model declares. `PUT`
treats omitted fields as "leave unchanged" (partial update) while an
explicitly-`null` nullable field (`sub_division_number`, `area_value`,
`address_id`, `village_id`, `registration_number`, ...) clears it; an
explicit `null` for a NOT NULL field (`survey_number`, `property_type`)
is rejected at the service boundary.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.application.property_service import PropertyService
from app.infrastructure.persistence.models.geography import Village
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.sqlalchemy_address_repository import (
    SqlAlchemyAddressRepository,
)
from app.infrastructure.persistence.sqlalchemy_party_repository import SqlAlchemyPartyRepository
from app.infrastructure.persistence.sqlalchemy_property_repository import (
    SqlAlchemyPropertyRepository,
)
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/properties")

_PROPERTY_TYPES = Literal["agricultural", "residential", "commercial", "industrial", "other"]


async def get_property_service(session: DBSessionDep) -> PropertyService:
    return PropertyService(
        SqlAlchemyPropertyRepository(session),
        SqlAlchemyPartyRepository(session),
        SqlAlchemyAddressRepository(session),
        SqlAlchemyRepository(session, Village),
    )


PropertyServiceDep = Annotated[PropertyService, Depends(get_property_service)]


class PropertyOwnerCreate(BaseModel):
    party_id: UUID
    ownership_share: Decimal | None = None
    ownership_type: str = Field(default="owner", min_length=1, max_length=50)
    from_date: date
    to_date: date | None = None


class PropertyOwnerRead(BaseModel):
    party_id: UUID | None
    legacy_client_id: UUID | None
    ownership_share: Decimal | None
    ownership_type: str
    from_date: date
    to_date: date | None


class PropertyCreate(BaseModel):
    property_type: _PROPERTY_TYPES = "agricultural"
    survey_number: str = Field(min_length=1, max_length=50)
    sub_division_number: str | None = Field(default=None, max_length=50)
    area_value: Decimal | None = None
    area_unit: str | None = Field(default=None, max_length=20)
    address_id: UUID | None = None
    village_id: UUID | None = None
    registration_number: str | None = Field(default=None, max_length=50)
    owners: list[PropertyOwnerCreate] = Field(default_factory=list)


class PropertyUpdate(BaseModel):
    property_type: _PROPERTY_TYPES | None = None
    survey_number: str | None = Field(default=None, min_length=1, max_length=50)
    sub_division_number: str | None = Field(default=None, max_length=50)
    area_value: Decimal | None = None
    area_unit: str | None = Field(default=None, max_length=20)
    address_id: UUID | None = None
    village_id: UUID | None = None
    registration_number: str | None = Field(default=None, max_length=50)


class PropertyRead(BaseModel):
    id: UUID
    property_type: str
    survey_number: str
    sub_division_number: str | None
    area_value: Decimal | None
    area_unit: str | None
    address_id: UUID | None
    village_id: UUID | None
    registration_number: str | None
    owners: list[PropertyOwnerRead]


def _require_organization(current_user: CurrentUser) -> UUID:
    if current_user.organization_id is None:
        raise ForbiddenError("No Organization context is resolved for this caller")
    return UUID(current_user.organization_id)


def _to_read(property_: Property, owners: Sequence[PropertyOwner]) -> PropertyRead:
    return PropertyRead(
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
            PropertyOwnerRead(
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


@router.get("", dependencies=[Depends(RequirePermission("properties:read"))])
async def list_properties(
    current_user: CurrentUserDep,
    service: PropertyServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[PropertyRead]]:
    organization_id = _require_organization(current_user)
    request = PageRequest(page=page, page_size=page_size)
    properties = await service.list_in_organization(
        organization_id, limit=request.limit, offset=request.offset
    )
    total = await service.count_in_organization(organization_id)
    reads = [_to_read(property_, list(await service.owners(property_))) for property_ in properties]
    page_result = PageResult.create(reads, total=total, request=request)
    response = paginated_response(page_result)
    return ApiResponse(data=response.data, meta=response.meta)


@router.get("/{property_id}", dependencies=[Depends(RequirePermission("properties:read"))])
async def get_property(
    property_id: UUID, current_user: CurrentUserDep, service: PropertyServiceDep
) -> ApiResponse[PropertyRead]:
    property_ = await service.get_in_organization(property_id, _require_organization(current_user))
    return ApiResponse(data=_to_read(property_, list(await service.owners(property_))))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("properties:write"))],
)
async def create_property(
    payload: PropertyCreate, current_user: CurrentUserDep, service: PropertyServiceDep
) -> ApiResponse[PropertyRead]:
    property_ = await service.create_in_organization(
        _require_organization(current_user),
        payload.model_dump(exclude={"owners"}),
        [owner.model_dump() for owner in payload.owners],
    )
    return ApiResponse(data=_to_read(property_, list(await service.owners(property_))))


@router.put("/{property_id}", dependencies=[Depends(RequirePermission("properties:write"))])
async def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    current_user: CurrentUserDep,
    service: PropertyServiceDep,
) -> ApiResponse[PropertyRead]:
    changes = {key: getattr(payload, key) for key in payload.model_fields_set}
    property_ = await service.update_in_organization(
        property_id, _require_organization(current_user), changes
    )
    return ApiResponse(data=_to_read(property_, list(await service.owners(property_))))
