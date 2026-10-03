"""Authenticated T149 pre-acceptance Enquiry and Quotation routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import BaseModel, Field

from app.application.acceptance_service import AcceptanceService
from app.application.common.pagination import DEFAULT_PAGE_SIZE, PageRequest, PageResult
from app.application.enquiry_service import EnquiryService
from app.application.errors.exceptions import ForbiddenError
from app.application.interfaces.auth import CurrentUser
from app.application.matter_service import MatterService
from app.infrastructure.persistence.models.enquiry import Enquiry, Quotation, QuotationRevision
from app.infrastructure.persistence.models.matter import MatterStatus, MatterType
from app.infrastructure.persistence.sqlalchemy_enquiry_repository import SqlAlchemyEnquiryRepository
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.infrastructure.persistence.sqlalchemy_party_repository import SqlAlchemyPartyRepository
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.presentation.api.deps import CurrentUserDep, DBSessionDep, RequirePermission
from app.presentation.common.response import ApiResponse, paginated_response

router = APIRouter(prefix="/enquiries")


async def get_service(session: DBSessionDep) -> EnquiryService:
    return EnquiryService(SqlAlchemyEnquiryRepository(session), SqlAlchemyPartyRepository(session))


ServiceDep = Annotated[EnquiryService, Depends(get_service)]


async def get_acceptance_service(session: DBSessionDep) -> AcceptanceService:
    parties = SqlAlchemyPartyRepository(session)
    return AcceptanceService(
        SqlAlchemyEnquiryRepository(session),
        parties,
        MatterService(
            SqlAlchemyMatterRepository(session),
            parties,
            SqlAlchemyRepository(session, MatterType),
            SqlAlchemyRepository(session, MatterStatus),
        ),
    )


AcceptanceServiceDep = Annotated[AcceptanceService, Depends(get_acceptance_service)]


class EnquiryCreate(BaseModel):
    party_id: UUID | None = None
    prospect_display_name: str | None = Field(default=None, min_length=1, max_length=255)
    prospect_phone: str | None = Field(default=None, max_length=20)
    prospect_email: str | None = Field(default=None, max_length=255)
    prospect_description: str | None = Field(default=None, max_length=2000)
    prospect_source: str | None = Field(default=None, max_length=255)


class EnquiryUpdate(BaseModel):
    prospect_display_name: str | None = Field(default=None, min_length=1, max_length=255)
    prospect_phone: str | None = Field(default=None, max_length=20)
    prospect_email: str | None = Field(default=None, max_length=255)
    prospect_description: str | None = Field(default=None, max_length=2000)
    prospect_source: str | None = Field(default=None, max_length=255)


class PartyLink(BaseModel):
    party_id: UUID


class EnquiryRead(BaseModel):
    id: UUID
    party_id: UUID | None
    prospect_display_name: str | None
    prospect_phone: str | None
    prospect_email: str | None
    prospect_description: str | None
    prospect_source: str | None
    created_at: datetime | None
    updated_at: datetime | None


class QuotationRead(BaseModel):
    id: UUID
    enquiry_id: UUID
    created_at: datetime | None


class RevisionCreate(BaseModel):
    proposal_snapshot: dict[str, object] = Field(min_length=1)


class RevisionRead(BaseModel):
    id: UUID
    quotation_id: UUID
    ordinal: int
    proposal_snapshot: dict[str, object]
    issued_at: datetime | None
    issued_by: UUID | None
    created_at: datetime | None


class AcceptanceMatterCreate(BaseModel):
    matter_number: str = Field(min_length=1, max_length=50)
    matter_type_id: UUID
    matter_status_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    opened_at: datetime


class AcceptanceRead(BaseModel):
    id: UUID
    matter_id: UUID
    quotation_revision_id: UUID
    replayed: bool


def _organization(user: CurrentUser) -> UUID:
    if user.organization_id is None:
        raise ForbiddenError("No Organization context is resolved for this caller")
    return UUID(user.organization_id)


def _actor(user: CurrentUser) -> UUID:
    if user.id is None:
        raise ForbiddenError("Authenticated actor identity is required")
    return UUID(user.id)


def _enquiry(row: Enquiry) -> EnquiryRead:
    return EnquiryRead(
        id=row.id,
        party_id=row.party_id,
        prospect_display_name=row.prospect_display_name,
        prospect_phone=row.prospect_phone,
        prospect_email=row.prospect_email,
        prospect_description=row.prospect_description,
        prospect_source=row.prospect_source,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _quotation(row: Quotation) -> QuotationRead:
    return QuotationRead(id=row.id, enquiry_id=row.enquiry_id, created_at=row.created_at)


def _revision(row: QuotationRevision) -> RevisionRead:
    return RevisionRead(
        id=row.id,
        quotation_id=row.quotation_id,
        ordinal=row.ordinal,
        proposal_snapshot=row.proposal_snapshot,
        issued_at=row.issued_at,
        issued_by=row.issued_by,
        created_at=row.created_at,
    )


@router.get("", dependencies=[Depends(RequirePermission("enquiries:read"))])
async def list_enquiries(
    current_user: CurrentUserDep,
    service: ServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[EnquiryRead]]:
    request, organization_id = PageRequest(page=page, page_size=page_size), _organization(
        current_user
    )
    result = PageResult.create(
        [
            _enquiry(row)
            for row in await service.list(
                organization_id, limit=request.limit, offset=request.offset
            )
        ],
        await service.count(organization_id),
        request,
    )
    response = paginated_response(result)
    return ApiResponse(data=response.data, meta=response.meta)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("enquiries:write"))],
)
async def create_enquiry(
    payload: EnquiryCreate, current_user: CurrentUserDep, service: ServiceDep
) -> ApiResponse[EnquiryRead]:
    return ApiResponse(
        data=_enquiry(
            await service.create(
                _organization(current_user), payload.model_dump(), _actor(current_user)
            )
        )
    )


@router.get("/{enquiry_id}", dependencies=[Depends(RequirePermission("enquiries:read"))])
async def get_enquiry(
    enquiry_id: UUID, current_user: CurrentUserDep, service: ServiceDep
) -> ApiResponse[EnquiryRead]:
    return ApiResponse(data=_enquiry(await service.get(_organization(current_user), enquiry_id)))


@router.put("/{enquiry_id}", dependencies=[Depends(RequirePermission("enquiries:write"))])
async def update_enquiry(
    enquiry_id: UUID, payload: EnquiryUpdate, current_user: CurrentUserDep, service: ServiceDep
) -> ApiResponse[EnquiryRead]:
    fields = {name: getattr(payload, name) for name in payload.model_fields_set}
    return ApiResponse(
        data=_enquiry(
            await service.update(
                _organization(current_user), enquiry_id, fields, _actor(current_user)
            )
        )
    )


@router.put("/{enquiry_id}/party", dependencies=[Depends(RequirePermission("enquiries:write"))])
async def link_party(
    enquiry_id: UUID, payload: PartyLink, current_user: CurrentUserDep, service: ServiceDep
) -> ApiResponse[EnquiryRead]:
    return ApiResponse(
        data=_enquiry(
            await service.link_party(
                _organization(current_user), enquiry_id, payload.party_id, _actor(current_user)
            )
        )
    )


@router.get(
    "/{enquiry_id}/quotations", dependencies=[Depends(RequirePermission("quotations:read"))]
)
async def list_quotations(
    enquiry_id: UUID,
    current_user: CurrentUserDep,
    service: ServiceDep,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ApiResponse[list[QuotationRead]]:
    request, organization_id = PageRequest(page=page, page_size=page_size), _organization(
        current_user
    )
    result = PageResult.create(
        [
            _quotation(row)
            for row in await service.list_quotations(
                organization_id, enquiry_id, limit=request.limit, offset=request.offset
            )
        ],
        await service.count_quotations(organization_id, enquiry_id),
        request,
    )
    response = paginated_response(result)
    return ApiResponse(data=response.data, meta=response.meta)


@router.post(
    "/{enquiry_id}/quotations",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("quotations:write"))],
)
async def create_quotation(
    enquiry_id: UUID, current_user: CurrentUserDep, service: ServiceDep
) -> ApiResponse[QuotationRead]:
    return ApiResponse(
        data=_quotation(
            await service.create_quotation(
                _organization(current_user), enquiry_id, _actor(current_user)
            )
        )
    )


@router.get(
    "/{enquiry_id}/quotations/{quotation_id}",
    dependencies=[Depends(RequirePermission("quotations:read"))],
)
async def get_quotation(
    enquiry_id: UUID, quotation_id: UUID, current_user: CurrentUserDep, service: ServiceDep
) -> ApiResponse[QuotationRead]:
    return ApiResponse(
        data=_quotation(
            await service.quotation(_organization(current_user), enquiry_id, quotation_id)
        )
    )


@router.get(
    "/{enquiry_id}/quotations/{quotation_id}/revisions",
    dependencies=[Depends(RequirePermission("quotations:read"))],
)
async def list_revisions(
    enquiry_id: UUID, quotation_id: UUID, current_user: CurrentUserDep, service: ServiceDep
) -> ApiResponse[list[RevisionRead]]:
    return ApiResponse(
        data=[
            _revision(row)
            for row in await service.revisions(
                _organization(current_user), enquiry_id, quotation_id
            )
        ]
    )


@router.post(
    "/{enquiry_id}/quotations/{quotation_id}/revisions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequirePermission("quotations:write"))],
)
async def create_revision(
    enquiry_id: UUID,
    quotation_id: UUID,
    payload: RevisionCreate,
    current_user: CurrentUserDep,
    service: ServiceDep,
) -> ApiResponse[RevisionRead]:
    return ApiResponse(
        data=_revision(
            await service.create_revision(
                _organization(current_user),
                enquiry_id,
                quotation_id,
                payload.proposal_snapshot,
                _actor(current_user),
            )
        )
    )


@router.get(
    "/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}",
    dependencies=[Depends(RequirePermission("quotations:read"))],
)
async def get_revision(
    enquiry_id: UUID,
    quotation_id: UUID,
    revision_id: UUID,
    current_user: CurrentUserDep,
    service: ServiceDep,
) -> ApiResponse[RevisionRead]:
    return ApiResponse(
        data=_revision(
            await service.revision(
                _organization(current_user), enquiry_id, quotation_id, revision_id
            )
        )
    )


@router.post(
    "/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/issue",
    dependencies=[Depends(RequirePermission("quotations:write"))],
)
async def issue_revision(
    enquiry_id: UUID,
    quotation_id: UUID,
    revision_id: UUID,
    current_user: CurrentUserDep,
    service: ServiceDep,
) -> ApiResponse[RevisionRead]:
    return ApiResponse(
        data=_revision(
            await service.issue(
                _organization(current_user),
                enquiry_id,
                quotation_id,
                revision_id,
                _actor(current_user),
            )
        )
    )


@router.post(
    "/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/accept",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(RequirePermission("quotations:accept")),
        Depends(RequirePermission("matters:write")),
    ],
)
async def accept_revision(
    enquiry_id: UUID,
    quotation_id: UUID,
    revision_id: UUID,
    payload: AcceptanceMatterCreate,
    current_user: CurrentUserDep,
    service: AcceptanceServiceDep,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> ApiResponse[AcceptanceRead]:
    acceptance, matter, replayed = await service.accept(
        _organization(current_user),
        enquiry_id,
        quotation_id,
        revision_id,
        payload.model_dump(),
        idempotency_key,
        _actor(current_user),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
    return ApiResponse(
        data=AcceptanceRead(
            id=acceptance.id,
            matter_id=matter.id,
            quotation_revision_id=acceptance.quotation_revision_id,
            replayed=replayed,
        )
    )
