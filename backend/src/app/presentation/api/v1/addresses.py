"""`GET /addresses`, `GET /addresses/{id}`, `POST /addresses`,
`PUT /addresses/{id}`, and `DELETE /addresses/{id}` (T130): the governed
Address application surface over the tenant-finalized aggregate (T122).

Follows the `parties.py` (T124) conventions exactly:

- hand-written router (the `crud_router_factory.py` is deliberately unused,
  per T62's own precedence), mirroring the same
  `ApiResponse`/pagination/`_to_read` shape;
- per-route `RequirePermission` for the three Address permission codes
  seeded by T130's migration: `addresses:read` on list/get,
  `addresses:write` on create/update, `addresses:delete` on delete;
- Organization is derived only from the authenticated context
  (`_require_organization()`, mirroring `parties.py`'s fail-closed helper) and
  `AddressService`/`AddressRepository` are org-scoped, so a caller can never
  operate on another tenant's Address — cross-Org access reads as 404 and is
  gated identically to a nonexistent id;
- validation: `country_id` is required (and cannot be cleared), `address_type`
  is bounded by a `Literal` matching the model's CHECK constraint, and every
  provided geography reference (`state_id`/`district_id`/`taluka_id`/
  `village_id`) must resolve to an existing row (422, not an FK 500);
- a delete that an existing Client/Party/other dependent would violate is
  translated into a controlled 409 by the service — no cascade or
  reassignment (T130 preserves the schema's FK integrity unchanged).

`AddressRead` deliberately omits `organization_id` and the audit columns
(mirrors `PartyRead`/`UserRead` omitting sensitive/internal fields) —
`_to_read()` only ever populates the fields the read model declares. `PUT`
treats omitted fields as "leave unchanged" (partial update) while an
explicitly-`null` nullable field (`line2`, `postal_code`, ...) clears it; an
explicit `null` for a NOT NULL field (`line1`, `country_id`, `address_type`)
is rejected at the service boundary.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.application.address_service import AddressService
from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.persistence.models.client import Address
from app.infrastructure.persistence.models.geography import (
    Country,
    District,
    State,
    Taluka,
    Village,
)
from app.infrastructure.persistence.sqlalchemy_address_repository import (
    SqlAlchemyAddressRepository,
)
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/addresses")


async def get_address_repository(session: DBSessionDep) -> SqlAlchemyAddressRepository:
    """Built fresh per request — needs *this* request's session (mirrors
    `parties.py`'s `get_party_repository()` reasoning)."""
    return SqlAlchemyAddressRepository(session)


AddressRepositoryDep = Annotated[SqlAlchemyAddressRepository, Depends(get_address_repository)]


async def get_address_service(
    session: DBSessionDep, repository: AddressRepositoryDep
) -> AddressService:
    return AddressService(
        repository,
        {
            "country": SqlAlchemyRepository(session, Country),
            "state": SqlAlchemyRepository(session, State),
            "district": SqlAlchemyRepository(session, District),
            "taluka": SqlAlchemyRepository(session, Taluka),
            "village": SqlAlchemyRepository(session, Village),
        },
    )


AddressServiceDep = Annotated[AddressService, Depends(get_address_service)]


class AddressRead(BaseModel):
    id: UUID
    line1: str
    line2: str | None
    village_id: UUID | None
    taluka_id: UUID | None
    district_id: UUID | None
    state_id: UUID | None
    country_id: UUID
    postal_code: str | None
    address_type: str


class AddressCreate(BaseModel):
    line1: str = Field(min_length=1, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    village_id: UUID | None = None
    taluka_id: UUID | None = None
    district_id: UUID | None = None
    state_id: UUID | None = None
    country_id: UUID
    postal_code: str | None = Field(default=None, max_length=20)
    address_type: Literal["registered", "mailing", "property", "other"] = "registered"


class AddressUpdate(BaseModel):
    line1: str | None = Field(default=None, min_length=1, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    village_id: UUID | None = None
    taluka_id: UUID | None = None
    district_id: UUID | None = None
    state_id: UUID | None = None
    country_id: UUID | None = None
    postal_code: str | None = Field(default=None, max_length=20)
    address_type: Literal["registered", "mailing", "property", "other"] | None = None


def _to_read(address: Address) -> AddressRead:
    return AddressRead.model_validate(address, from_attributes=True)


def _require_organization(current_user: CurrentUser) -> UUID:
    """T105/ADR-0021: fail-closed if the caller has no resolved Organization —
    an authenticated, permission-holding caller with no Organization still
    cannot operate on any Address. Never proceeds unscoped."""
    if current_user.organization_id is None:
        raise ForbiddenError("No Organization context is resolved for this caller")
    return UUID(current_user.organization_id)


@router.get(
    "",
    summary="List addresses",
    dependencies=[Depends(RequirePermission("addresses:read"))],
)
async def list_addresses(
    current_user: CurrentUserDep,
    service: AddressServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[AddressRead]]:
    organization_id = _require_organization(current_user)
    request = PageRequest(page=page, page_size=page_size)
    items = await service.list_in_organization(
        organization_id, limit=request.limit, offset=request.offset
    )
    total = await service.count_in_organization(organization_id)
    page_result = PageResult.create(list(items), total=total, request=request)
    entity_response = paginated_response(page_result)
    return ApiResponse(
        data=[_to_read(address) for address in entity_response.data],
        meta=entity_response.meta,
    )


@router.get(
    "/{address_id}",
    summary="Get an address by id",
    dependencies=[Depends(RequirePermission("addresses:read"))],
)
async def get_address(
    address_id: UUID, current_user: CurrentUserDep, service: AddressServiceDep
) -> ApiResponse[AddressRead]:
    organization_id = _require_organization(current_user)
    address = await service.get_in_organization(address_id, organization_id)
    return ApiResponse(data=_to_read(address))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create an address",
    dependencies=[Depends(RequirePermission("addresses:write"))],
)
async def create_address(
    payload: AddressCreate, current_user: CurrentUserDep, service: AddressServiceDep
) -> ApiResponse[AddressRead]:
    organization_id = _require_organization(current_user)
    address = await service.create_in_organization(organization_id, payload.model_dump())
    return ApiResponse(data=_to_read(address))


@router.put(
    "/{address_id}",
    summary="Update an address",
    dependencies=[Depends(RequirePermission("addresses:write"))],
)
async def update_address(
    address_id: UUID,
    payload: AddressUpdate,
    current_user: CurrentUserDep,
    service: AddressServiceDep,
) -> ApiResponse[AddressRead]:
    organization_id = _require_organization(current_user)
    changes = {key: getattr(payload, key) for key in payload.model_fields_set}
    address = await service.update_in_organization(address_id, organization_id, changes)
    return ApiResponse(data=_to_read(address))


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an address",
    dependencies=[Depends(RequirePermission("addresses:delete"))],
)
async def delete_address(
    address_id: UUID, current_user: CurrentUserDep, service: AddressServiceDep
) -> None:
    organization_id = _require_organization(current_user)
    await service.delete_in_organization(address_id, organization_id)
