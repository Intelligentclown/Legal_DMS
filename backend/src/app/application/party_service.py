"""Party application service (T124): Organization-mandatory CRUD for Parties,
gated by `PartyWriteGate` (ADR-0036 enablement) with address same-Organization
validation.

Every entry point here takes a resolved `organization_id` from the caller's
authenticated context — there is deliberately no path that accepts an
Organization chosen by the caller, so the service itself cannot be used to
smuggle a Party into (or out of) a tenant. `address_id` is validated as
belonging to the same Organization before the write, so a mismatched reference
surfaces as a clean `ValidationError` (422) instead of the composite-FK's
`IntegrityError` (500).

Create/update/delete each consult the gate before any mutation; reads are
ungated (permission surface + Organization scoping + T123 Party RLS already
protect them). The T118 migration executor's owning-path writes are a governed
transfer path and are deliberately not routed through this service.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from app.application.errors.exceptions import NotFoundError, ValidationError
from app.application.interfaces.install_classifier import InstallationClassifier
from app.application.interfaces.party_repository import PartyRepository
from app.application.interfaces.repository import AbstractRepository
from app.application.party_write_gate import PartyWriteGate
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.persistence.models.client import Address
from app.infrastructure.persistence.models.party import Party

_WRITABLE_FIELDS = frozenset(
    {
        "party_type",
        "display_name",
        "primary_phone",
        "primary_email",
        "address_id",
        "notes",
        "pan_number",
        "aadhaar_number",
        "gstin",
        "registration_identifier",
        "date_of_birth",
        "gender",
        "occupation",
        "incorporation_date",
    }
)


class PartyService:
    """Orchestrates the gate + address validation + Party persistence."""

    def __init__(
        self,
        repository: PartyRepository,
        address_repository: AbstractRepository[Address],
        classifier: InstallationClassifier,
    ) -> None:
        self._repository = repository
        self._address_repository = address_repository
        self._gate = PartyWriteGate(classifier)
        self._logger = get_logger("service.party")

    async def get_in_organization(self, party_id: UUID, organization_id: UUID) -> Party:
        party = await self._repository.get_by_id_in_organization(party_id, organization_id)
        if party is None:
            raise NotFoundError(f"Party with id {party_id} was not found")
        return party

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Party]:
        return await self._repository.list_in_organization(
            organization_id, limit=limit, offset=offset
        )

    async def count_in_organization(self, organization_id: UUID) -> int:
        return await self._repository.count_in_organization(organization_id)

    async def create_in_organization(
        self, organization_id: UUID, fields: Mapping[str, Any]
    ) -> Party:
        await self._gate.ensure_writable()
        writable = {key: value for key, value in fields.items() if key in _WRITABLE_FIELDS}
        address_id = writable.get("address_id")
        if address_id is not None:
            await self._validate_address(address_id, organization_id)
        party = Party(organization_id=organization_id, **writable)
        return await self._repository.add(party)

    async def update_in_organization(
        self, party_id: UUID, organization_id: UUID, fields: Mapping[str, Any]
    ) -> Party:
        await self._gate.ensure_writable()
        party = await self.get_in_organization(party_id, organization_id)
        address_id = fields.get("address_id")
        if address_id is not None:
            await self._validate_address(address_id, organization_id)
        for key, value in fields.items():
            if key in _WRITABLE_FIELDS:
                setattr(party, key, value)
        return await self._repository.update(party)

    async def delete_in_organization(self, party_id: UUID, organization_id: UUID) -> None:
        await self._gate.ensure_writable()
        party = await self.get_in_organization(party_id, organization_id)
        await self._repository.delete(party.id)

    async def _validate_address(self, address_id: UUID, organization_id: UUID) -> None:
        address = await self._address_repository.get_by_id(address_id)
        if address is None or address.organization_id != organization_id:
            raise ValidationError(
                f"Address with id {address_id} does not exist in this Organization"
            )
