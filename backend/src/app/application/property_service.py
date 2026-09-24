"""Property application service (T135): Organization-scoped, Party-canonical
Property writes and Party/Client-distinct ownership reads.

Every entry point here takes a resolved `organization_id` from the caller's
authenticated context — there is deliberately no path that accepts an
Organization chosen by the caller, so the service itself cannot be used to
smuggle a Property (or an owner) into (or out of) a tenant.

T135 is the bounded Property application surface over the T133 tenant-
finalized schema. Ownership operates on the existing model exactly as T133
authorized: new owners are Party-canonical (`PropertyOwner.party_id` set,
`client_id` kept NULL — no Client identity is ever manufactured), while
retained legacy Client-linked owners stay readable through the same
representation via `legacy_client_id`. There is no Client participation on
the write surface, no Party→Client dual-write, and no legacy conversion.

Validation (authorized scope: existing-model field/type and bounded
same-Organization reference validation):

- `survey_number` is required and can never be cleared (the model column is
  NOT NULL); a missing/`null` survey number on create or an explicit `null`
  on update is a clean `ValidationError` (422);
- an `address_id` must belong to the caller's Organization — a mismatched
  reference surfaces as a clean `ValidationError` (422) instead of the
  composite-FK's `IntegrityError` (500), mirroring `PartyService`;
- a `village_id` must resolve to an existing row in the reference table —
  a nonexistent reference is a clean `ValidationError` (422), not an FK 500,
  mirroring `AddressService` (Villages are reference data, not tenant rows);
- each supplied owner requires a `party_id` that exists in the caller's
  Organization (cross-Org owner references fail closed with 422 and nothing
  is persisted), a `from_date`, and bounded ownership metadata matching the
  model CHECK constraints (`ownership_share` within `(0, 100]`, `to_date`
  never before `from_date`); duplicate Party ownership of the same Property
  in one create is rejected;
- `property_type` is bounded by the pydantic `Literal` at the presentation
  layer, matching the model's CHECK constraint — the service keeps the model
  default for an omitted type.

Ownership is a canonical-creation concern only: update is bounded to the
ordinary scalar Property fields and never mutates owner rows (documented in
the T135 implementation log). Reads are ungated (permission surface +
Organization scoping + T133 forced RLS already protect them), and there is
no installation-state write gate here: T135 explicitly does not copy or
generalize `PartyWriteGate`, mirroring T130's AddressService reasoning.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.application.errors.exceptions import NotFoundError, ValidationError
from app.application.interfaces.address_repository import AddressRepository
from app.application.interfaces.party_repository import PartyRepository
from app.application.interfaces.property_repository import PropertyRepository
from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.persistence.models.geography import Village
from app.infrastructure.persistence.models.property import Property, PropertyOwner

_WRITABLE_FIELDS = frozenset(
    {
        "property_type",
        "survey_number",
        "sub_division_number",
        "area_value",
        "area_unit",
        "address_id",
        "village_id",
        "registration_number",
    }
)

# PropertyOwner columns the write surface may carry. `client_id` is
# deliberately absent: T135 never writes legacy Client ownership.
_OWNER_FIELDS = frozenset(
    {
        "party_id",
        "ownership_share",
        "ownership_type",
        "from_date",
        "to_date",
    }
)

# NOT NULL columns that cannot be cleared via an explicit `null` on update
# (the schema already rejects an omitted/missing value on create).
_NOT_NULLABLE_FIELDS = frozenset({"survey_number", "property_type"})


class PropertyService:
    """Orchestrates Owner/Address/Village validation + Property persistence."""

    def __init__(
        self,
        repository: PropertyRepository,
        party_repository: PartyRepository,
        address_repository: AddressRepository,
        village_repository: AbstractRepository[Village],
    ) -> None:
        self._repository = repository
        self._party_repository = party_repository
        self._address_repository = address_repository
        self._village_repository = village_repository
        self._logger = get_logger("service.property")

    async def get_in_organization(self, property_id: UUID, organization_id: UUID) -> Property:
        property_ = await self._repository.get_by_id_in_organization(property_id, organization_id)
        if property_ is None:
            raise NotFoundError(f"Property with id {property_id} was not found")
        return property_

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Property]:
        return await self._repository.list_in_organization(
            organization_id, limit=limit, offset=offset
        )

    async def count_in_organization(self, organization_id: UUID) -> int:
        return await self._repository.count_in_organization(organization_id)

    async def owners(self, property_: Property) -> Sequence[PropertyOwner]:
        return await self._repository.list_owners(property_.id, property_.organization_id)

    async def create_in_organization(
        self,
        organization_id: UUID,
        fields: Mapping[str, Any],
        owner_specs: Sequence[Mapping[str, Any]],
    ) -> Property:
        writable = {key: value for key, value in fields.items() if key in _WRITABLE_FIELDS}
        for field in _NOT_NULLABLE_FIELDS:
            if not writable.get(field):
                raise ValidationError(f"{field} is required")
        await self._validate_references(writable, organization_id)
        if writable.get("area_value") is not None and writable["area_value"] <= 0:
            raise ValidationError("area_value must be greater than 0")
        property_ = Property(id=uuid4(), organization_id=organization_id, **writable)
        owners = await self._build_owner_rows(owner_specs, organization_id, property_.id)
        return await self._repository.add_with_owners(property_, owners)

    async def update_in_organization(
        self, property_id: UUID, organization_id: UUID, fields: Mapping[str, Any]
    ) -> Property:
        property_ = await self.get_in_organization(property_id, organization_id)
        writable = {key: value for key, value in fields.items() if key in _WRITABLE_FIELDS}
        for field in _NOT_NULLABLE_FIELDS:
            if field in fields and not writable.get(field):
                raise ValidationError(f"{field} is required and cannot be cleared")
        await self._validate_references(writable, organization_id)
        area_value = writable.get("area_value")
        if area_value is not None and area_value <= 0:
            raise ValidationError("area_value must be greater than 0")
        for key, value in writable.items():
            setattr(property_, key, value)
        return await self._repository.update(property_)

    async def _build_owner_rows(
        self,
        owner_specs: Sequence[Mapping[str, Any]],
        organization_id: UUID,
        property_id: UUID,
    ) -> list[PropertyOwner]:
        seen: set[UUID] = set()
        rows: list[PropertyOwner] = []
        for spec in owner_specs:
            writable = {key: value for key, value in spec.items() if key in _OWNER_FIELDS}
            party_id = writable.get("party_id")
            if party_id is None:
                raise ValidationError("party_id is required for ownership")
            if party_id in seen:
                raise ValidationError("duplicate PropertyOwner participation")
            seen.add(party_id)
            if (
                await self._party_repository.get_by_id_in_organization(party_id, organization_id)
                is None
            ):
                raise ValidationError(
                    f"Party with id {party_id} does not exist in this Organization"
                )
            if not writable.get("from_date"):
                raise ValidationError("from_date is required for ownership")
            share = writable.get("ownership_share")
            if share is not None and not (Decimal(0) < share <= Decimal(100)):
                raise ValidationError("ownership_share must be greater than 0 and at most 100")
            to_date = writable.get("to_date")
            if to_date is not None and to_date < writable["from_date"]:
                raise ValidationError("to_date must not precede from_date")
            rows.append(
                PropertyOwner(
                    organization_id=organization_id,
                    property_id=property_id,
                    client_id=None,
                    **writable,
                )
            )
        return rows

    async def _validate_references(
        self, writable: Mapping[str, Any], organization_id: UUID
    ) -> None:
        address_id = writable.get("address_id")
        if address_id is not None and (
            await self._address_repository.get_by_id_in_organization(address_id, organization_id)
            is None
        ):
            raise ValidationError(
                f"Address with id {address_id} does not exist in this Organization"
            )
        village_id = writable.get("village_id")
        if village_id is not None and await self._village_repository.get_by_id(village_id) is None:
            raise ValidationError(f"village_id with id {village_id} does not exist")
