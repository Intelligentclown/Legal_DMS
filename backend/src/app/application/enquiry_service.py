"""T149 Organization-scoped Enquiry, Quotation and revision orchestration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from app.application.errors.exceptions import ConflictError, NotFoundError, ValidationError
from app.application.interfaces.enquiry_repository import EnquiryRepository
from app.application.interfaces.party_repository import PartyRepository
from app.infrastructure.persistence.models.enquiry import Enquiry, Quotation, QuotationRevision

_ENQUIRY_FIELDS = frozenset(
    {
        "prospect_display_name",
        "prospect_phone",
        "prospect_email",
        "prospect_description",
        "prospect_source",
    }
)


class EnquiryService:
    def __init__(self, repository: EnquiryRepository, parties: PartyRepository) -> None:
        self._repository, self._parties = repository, parties

    async def get(self, organization_id: UUID, enquiry_id: UUID) -> Enquiry:
        enquiry = await self._repository.get(organization_id, enquiry_id)
        if enquiry is None:
            raise NotFoundError("Enquiry was not found")
        return enquiry

    async def list(self, organization_id: UUID, *, limit: int, offset: int) -> Sequence[Enquiry]:
        return await self._repository.list(organization_id, limit=limit, offset=offset)

    async def count(self, organization_id: UUID) -> int:
        return await self._repository.count(organization_id)

    async def create(
        self, organization_id: UUID, fields: Mapping[str, Any], actor_id: UUID | None
    ) -> Enquiry:
        values = {key: value for key, value in fields.items() if key in _ENQUIRY_FIELDS}
        party_id = fields.get("party_id")
        if party_id is not None:
            await self._party(organization_id, party_id)
        if party_id is None and not values.get("prospect_display_name"):
            raise ValidationError("prospect_display_name is required when party_id is absent")
        return await self._repository.add(
            Enquiry(
                organization_id=organization_id,
                party_id=party_id,
                created_by=actor_id,
                updated_by=actor_id,
                **values,
            )
        )

    async def update(
        self,
        organization_id: UUID,
        enquiry_id: UUID,
        fields: Mapping[str, Any],
        actor_id: UUID | None,
    ) -> Enquiry:
        enquiry = await self.get(organization_id, enquiry_id)
        for key, value in fields.items():
            if key in _ENQUIRY_FIELDS:
                setattr(enquiry, key, value)
        if enquiry.party_id is None and not enquiry.prospect_display_name:
            raise ValidationError("prospect_display_name is required until a Party is linked")
        enquiry.updated_by = actor_id
        return await self._repository.update(enquiry)

    async def link_party(
        self, organization_id: UUID, enquiry_id: UUID, party_id: UUID, actor_id: UUID | None
    ) -> Enquiry:
        enquiry = await self.get(organization_id, enquiry_id)
        await self._party(organization_id, party_id)
        enquiry.party_id, enquiry.updated_by = party_id, actor_id
        return await self._repository.update(enquiry)

    async def quotation(
        self, organization_id: UUID, enquiry_id: UUID, quotation_id: UUID
    ) -> Quotation:
        await self.get(organization_id, enquiry_id)
        quotation = await self._repository.get_quotation(organization_id, enquiry_id, quotation_id)
        if quotation is None:
            raise NotFoundError("Quotation was not found")
        return quotation

    async def list_quotations(
        self, organization_id: UUID, enquiry_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Quotation]:
        await self.get(organization_id, enquiry_id)
        return await self._repository.list_quotations(
            organization_id, enquiry_id, limit=limit, offset=offset
        )

    async def count_quotations(self, organization_id: UUID, enquiry_id: UUID) -> int:
        await self.get(organization_id, enquiry_id)
        return await self._repository.count_quotations(organization_id, enquiry_id)

    async def create_quotation(
        self, organization_id: UUID, enquiry_id: UUID, actor_id: UUID | None
    ) -> Quotation:
        await self.get(organization_id, enquiry_id)
        return await self._repository.add_quotation(
            Quotation(organization_id=organization_id, enquiry_id=enquiry_id, created_by=actor_id)
        )

    async def create_revision(
        self,
        organization_id: UUID,
        enquiry_id: UUID,
        quotation_id: UUID,
        snapshot: dict[str, object],
        actor_id: UUID | None,
    ) -> QuotationRevision:
        if not snapshot:
            raise ValidationError("proposal_snapshot must not be empty")
        # Lock the parent aggregate before MAX+1. PostgreSQL row locks serialize all
        # allocations for this Quotation; the unique constraint remains the backstop.
        quotation = await self._repository.lock_quotation(organization_id, enquiry_id, quotation_id)
        if quotation is None:
            raise NotFoundError("Quotation was not found")
        ordinal = await self._repository.next_revision_ordinal(quotation.id)
        return await self._repository.add_revision(
            QuotationRevision(
                id=uuid4(),
                organization_id=organization_id,
                quotation_id=quotation.id,
                ordinal=ordinal,
                proposal_snapshot=snapshot,
                created_by=actor_id,
            )
        )

    async def revisions(
        self, organization_id: UUID, enquiry_id: UUID, quotation_id: UUID
    ) -> Sequence[QuotationRevision]:
        await self.quotation(organization_id, enquiry_id, quotation_id)
        return await self._repository.list_revisions(organization_id, quotation_id)

    async def revision(
        self, organization_id: UUID, enquiry_id: UUID, quotation_id: UUID, revision_id: UUID
    ) -> QuotationRevision:
        await self.quotation(organization_id, enquiry_id, quotation_id)
        revision = await self._repository.get_revision(organization_id, quotation_id, revision_id)
        if revision is None:
            raise NotFoundError("Quotation revision was not found")
        return revision

    async def issue(
        self,
        organization_id: UUID,
        enquiry_id: UUID,
        quotation_id: UUID,
        revision_id: UUID,
        actor_id: UUID,
    ) -> QuotationRevision:
        revision = await self.revision(organization_id, enquiry_id, quotation_id, revision_id)
        if revision.issued_at is not None or revision.issued_by is not None:
            raise ConflictError("Quotation revision has already been issued")
        from datetime import UTC, datetime

        revision.issued_at, revision.issued_by = datetime.now(UTC), actor_id
        return await self._repository.update_revision(revision)

    async def _party(self, organization_id: UUID, party_id: UUID) -> None:
        if await self._parties.get_by_id_in_organization(party_id, organization_id) is None:
            raise ValidationError("Party does not exist in this Organization")
