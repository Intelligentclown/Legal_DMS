"""`GET /parties`, `GET /parties/{id}`, `POST /parties`, `PUT /parties/{id}`,
and `DELETE /parties/{id}` (T124): the governed Party application surface.

Follows the `users.py` established conventions (T62/T63/T105) exactly:

- hand-written router (the `crud_router_factory.py` is deliberately unused,
  per T62's own precedence), mirroring the same
  `ApiResponse`/pagination/`_to_read` shape;
- per-route `RequirePermission` for the three Party permission codes
  (unlike `users.py`, reads and writes are *not* uniformly gated here):
  `parties:read` on list/get, `parties:write` on create/update,
  `parties:delete` on delete — each code was seeded for the six roles by
  T124's migration and audited by `test_t66` at 71 `role_permissions`;
- Organization is derived only from the authenticated context
  (`_require_organization()`, mirroring `users.py`'s fail-closed helper) and
  `PartyService`/`PartyRepository` are org-scoped, so a caller can never
  operate on another tenant's Party — cross-Org access reads as 404 and is
  gated identically to a nonexistent id;
- `PartyService` enforces the ADR-0036 fresh-install write gate on
  create/update/delete (fail-closed 403 in any non-FRESH installation) and
  validates that an `address_id` belongs to the caller's Organization (422
  instead of a composite-FK 500); reads are ungated by the gate because they
  are already protected by permission + Organization scoping + T123 RLS.

`PartyRead` deliberately omits `organization_id` (mirrors `UserRead` omitting
sensitive/internal fields) — `_to_read()` only ever populates the fields the
read model declares. `PUT` treats omitted fields as "leave unchanged"
(partial update) while an explicitly-`null` `address_id` clears the Party's
address.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.application.interfaces.install_classifier import InstallationClassifier
from app.application.party_service import PartyService
from app.infrastructure.persistence.models.client import Address
from app.infrastructure.persistence.models.party import Party
from app.infrastructure.persistence.sqlalchemy_install_classifier import (
    SqlAlchemyInstallationClassifier,
)
from app.infrastructure.persistence.sqlalchemy_party_repository import (
    SqlAlchemyPartyRepository,
)
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/parties")


async def get_party_repository(session: DBSessionDep) -> SqlAlchemyPartyRepository:
    """Built fresh per request — needs *this* request's session (mirrors
    `users.py`'s `get_user_repository()` reasoning)."""
    return SqlAlchemyPartyRepository(session)


PartyRepositoryDep = Annotated[SqlAlchemyPartyRepository, Depends(get_party_repository)]


async def get_install_classifier(session: DBSessionDep) -> InstallationClassifier:
    """Built fresh per request over *this* request's session — the ADR-0036
    classifier reads the live row-presence snapshot on the same connection
    the Party write would use. Exposed as a module-local dependency so the
    route tests can override it (with either a graded fake or a real
    classifier against a dedicated database), without touching the container
    or `deps.py`."""
    return SqlAlchemyInstallationClassifier(session)


InstallationClassifierDep = Annotated[InstallationClassifier, Depends(get_install_classifier)]


async def get_party_service(
    session: DBSessionDep,
    repository: PartyRepositoryDep,
    classifier: InstallationClassifierDep,
) -> PartyService:
    return PartyService(
        repository,
        SqlAlchemyRepository(session, Address),
        classifier,
    )


PartyServiceDep = Annotated[PartyService, Depends(get_party_service)]


class PartyRead(BaseModel):
    id: UUID
    party_type: str
    display_name: str
    primary_phone: str
    primary_email: str | None
    address_id: UUID | None
    notes: str | None
    pan_number: str | None
    aadhaar_number: str | None
    gstin: str | None
    registration_identifier: str | None
    date_of_birth: date | None
    gender: str | None
    occupation: str | None
    incorporation_date: date | None


class PartyCreate(BaseModel):
    party_type: Literal["individual", "organization"]
    display_name: str
    primary_phone: str = Field(min_length=7)
    primary_email: str | None = None
    address_id: UUID | None = None
    notes: str | None = None
    pan_number: str | None = None
    aadhaar_number: str | None = None
    gstin: str | None = None
    registration_identifier: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    occupation: str | None = None
    incorporation_date: date | None = None


class PartyUpdate(BaseModel):
    party_type: Literal["individual", "organization"] | None = None
    display_name: str | None = None
    primary_phone: str | None = Field(default=None, min_length=7)
    primary_email: str | None = None
    address_id: UUID | None = None
    notes: str | None = None
    pan_number: str | None = None
    aadhaar_number: str | None = None
    gstin: str | None = None
    registration_identifier: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    occupation: str | None = None
    incorporation_date: date | None = None


def _to_read(party: Party) -> PartyRead:
    return PartyRead.model_validate(party, from_attributes=True)


def _require_organization(current_user: CurrentUser) -> UUID:
    """T105/ADR-0021: fail-closed if the caller has no resolved Organization —
    an authenticated, permission-holding caller with no Organization still
    cannot operate on any Party. Never proceeds unscoped."""
    if current_user.organization_id is None:
        raise ForbiddenError("No Organization context is resolved for this caller")
    return UUID(current_user.organization_id)


@router.get("", summary="List parties", dependencies=[Depends(RequirePermission("parties:read"))])
async def list_parties(
    current_user: CurrentUserDep,
    service: PartyServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[PartyRead]]:
    organization_id = _require_organization(current_user)
    request = PageRequest(page=page, page_size=page_size)
    items = await service.list_in_organization(
        organization_id, limit=request.limit, offset=request.offset
    )
    total = await service.count_in_organization(organization_id)
    page_result = PageResult.create(list(items), total=total, request=request)
    entity_response = paginated_response(page_result)
    return ApiResponse(
        data=[_to_read(party) for party in entity_response.data], meta=entity_response.meta
    )


@router.get(
    "/{party_id}",
    summary="Get a party by id",
    dependencies=[Depends(RequirePermission("parties:read"))],
)
async def get_party(
    party_id: UUID, current_user: CurrentUserDep, service: PartyServiceDep
) -> ApiResponse[PartyRead]:
    organization_id = _require_organization(current_user)
    party = await service.get_in_organization(party_id, organization_id)
    return ApiResponse(data=_to_read(party))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a party",
    dependencies=[Depends(RequirePermission("parties:write"))],
)
async def create_party(
    payload: PartyCreate, current_user: CurrentUserDep, service: PartyServiceDep
) -> ApiResponse[PartyRead]:
    organization_id = _require_organization(current_user)
    party = await service.create_in_organization(organization_id, payload.model_dump())
    return ApiResponse(data=_to_read(party))


@router.put(
    "/{party_id}",
    summary="Update a party",
    dependencies=[Depends(RequirePermission("parties:write"))],
)
async def update_party(
    party_id: UUID,
    payload: PartyUpdate,
    current_user: CurrentUserDep,
    service: PartyServiceDep,
) -> ApiResponse[PartyRead]:
    organization_id = _require_organization(current_user)
    changes = {key: getattr(payload, key) for key in payload.model_fields_set}
    party = await service.update_in_organization(party_id, organization_id, changes)
    return ApiResponse(data=_to_read(party))


@router.delete(
    "/{party_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a party",
    dependencies=[Depends(RequirePermission("parties:delete"))],
)
async def delete_party(
    party_id: UUID, current_user: CurrentUserDep, service: PartyServiceDep
) -> None:
    organization_id = _require_organization(current_user)
    await service.delete_in_organization(party_id, organization_id)
