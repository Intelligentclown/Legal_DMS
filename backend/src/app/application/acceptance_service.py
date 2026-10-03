"""T152 acceptance-to-Matter conversion inside the existing request transaction."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from app.application.enquiry_service import EnquiryService
from app.application.errors.exceptions import ConflictError, NotFoundError, ValidationError
from app.application.interfaces.enquiry_repository import EnquiryRepository
from app.application.interfaces.party_repository import PartyRepository
from app.application.matter_service import MatterService
from app.infrastructure.persistence.models.enquiry import Acceptance
from app.infrastructure.persistence.models.matter import Matter

_MATTER_FIELDS = frozenset(
    {"matter_number", "matter_type_id", "matter_status_id", "title", "description", "opened_at"}
)


class AcceptanceService:
    """Bounded conversion orchestration; repositories/services only flush, never commit."""

    def __init__(
        self,
        enquiries: EnquiryRepository,
        parties: PartyRepository,
        matter_service: MatterService,
    ) -> None:
        self._enquiries = enquiries
        self._matter_service = matter_service
        # Reuse the established hierarchy and exact-revision reads rather than
        # introducing a second persistence traversal.
        self._hierarchy = EnquiryService(enquiries, parties)

    async def accept(
        self,
        organization_id: UUID,
        enquiry_id: UUID,
        quotation_id: UUID,
        revision_id: UUID,
        matter_fields: Mapping[str, Any],
        idempotency_key: str,
        actor_id: UUID,
    ) -> tuple[Acceptance, Matter, bool]:
        fields = {key: value for key, value in matter_fields.items() if key in _MATTER_FIELDS}
        fingerprint = self._fingerprint(enquiry_id, quotation_id, revision_id, fields)

        # PostgreSQL's row lock is the authoritative competing-conversion
        # serialization point.  A missing/cross-tenant row stays non-enumerating.
        enquiry = await self._enquiries.lock_enquiry(organization_id, enquiry_id)
        if enquiry is None:
            raise NotFoundError("Enquiry was not found")

        existing = await self._enquiries.acceptance_for_enquiry(organization_id, enquiry_id)
        if existing is not None:
            if existing.idempotency_key == idempotency_key:
                if existing.request_fingerprint != fingerprint:
                    raise ConflictError("Idempotency-Key was reused with a different request")
                matter = await self._matter_service.get_in_organization(
                    existing.matter_id, organization_id
                )
                return existing, matter, True
            raise ConflictError("Enquiry has already been converted")

        if enquiry.party_id is None:
            raise ValidationError("Acceptance requires an Enquiry linked to a canonical Party")
        quotation = await self._hierarchy.quotation(organization_id, enquiry_id, quotation_id)
        revision = await self._hierarchy.revision(
            organization_id, enquiry_id, quotation.id, revision_id
        )
        # T150's persisted paired issuance facts are the only eligibility
        # predicate: no status/vocabulary architecture is inferred here.
        if revision.issued_at is None or revision.issued_by is None:
            raise ValidationError("Quotation revision is not eligible for acceptance")

        matter = await self._matter_service.create_in_organization(
            organization_id, fields, enquiry.party_id, []
        )
        acceptance = await self._enquiries.add_acceptance(
            Acceptance(
                id=uuid4(),
                organization_id=organization_id,
                enquiry_id=enquiry.id,
                quotation_id=quotation.id,
                quotation_revision_id=revision.id,
                matter_id=matter.id,
                accepted_by=actor_id,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
            )
        )
        return acceptance, matter, False

    @staticmethod
    def _fingerprint(
        enquiry_id: UUID, quotation_id: UUID, revision_id: UUID, matter_fields: Mapping[str, Any]
    ) -> str:
        """Stable, explicit fingerprint over every material conversion input."""
        payload = {
            "enquiry_id": str(enquiry_id),
            "quotation_id": str(quotation_id),
            "quotation_revision_id": str(revision_id),
            "matter": {
                key: str(value) if isinstance(value, UUID) else value
                for key, value in matter_fields.items()
            },
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(encoded).hexdigest()
