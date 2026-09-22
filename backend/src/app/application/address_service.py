"""Address application service (T130): Organization-mandatory CRUD for
Addresses, with country-required and bounded geographic-reference validation,
and controlled referenced-delete behavior.

Every entry point here takes a resolved `organization_id` from the caller's
authenticated context — there is deliberately no path that accepts an
Organization chosen by the caller, so the service itself cannot be used to
smuggle an Address into (or out of) a tenant.

Validation (authorized scope: existing-model field/type and bounded
geographic-reference validation):

- `country_id` is required and can never be cleared (the model column is
  NOT NULL); a missing/`null` country on create or an explicit `null` on
  update is a clean `ValidationError` (422);
- every provided geography reference (`state_id`, `district_id`, `taluka_id`,
  `village_id`) must resolve to an existing row in its own reference table —
  a nonexistent reference is a clean `ValidationError` (422), not an FK 500.
  Hierarchy-consistency traversal (village -> taluka -> ... -> country) is
  deliberately out of scope: the existing reference model has no dedicated
  repository/consistency contract beyond these FK existences, and inventing
  one would be new architecture (T130 excludes new hierarchy work);
- `address_type` is bounded by the pydantic `Literal` at the presentation
  layer, matching the model's CHECK constraint — the service keeps the model
  default for an omitted type.

Referenced delete: deleting an Address still referenced by a Client, Party,
or other dependent row would violate the composite/plain FKs the schema
already enforces (T122 preserved them deliberately). No cascade or
reassignment is authorized, so the service translates the resulting
`IntegrityError` into a controlled `ConflictError` (409) instead of leaking
a 500 — the schema-level relationship is preserved unchanged.

Consistent with `PartyService`, reads are ungated (permission surface +
Organization scoping + T122 forced RLS already protect them), and there is
no installation-state write gate here: T130 explicitly does not copy or
generalize `PartyWriteGate`, and creating a new Address installation-state
policy would require STOP/escalation beyond this authorization.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.application.errors.exceptions import (
    ConflictError,
    NotFoundError,
    UnexpectedError,
    ValidationError,
)
from app.application.interfaces.address_repository import AddressRepository
from app.application.interfaces.repository import AbstractRepository, SupportsId
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.persistence.models.client import Address

_WRITABLE_FIELDS = frozenset(
    {
        "line1",
        "line2",
        "village_id",
        "taluka_id",
        "district_id",
        "state_id",
        "country_id",
        "postal_code",
        "address_type",
    }
)

# Geography reference keys -> the model attribute on Address. Bounded to the
# schema's existing reference columns (country is required; the rest optional).
_REFERENCE_FIELDS = (
    "country_id",
    "state_id",
    "district_id",
    "taluka_id",
    "village_id",
)

# NOT NULL columns that cannot be cleared via an explicit `null` on update
# (the schema already rejects an omitted/missing value on create).
_NOT_NULLABLE_FIELDS = frozenset({"country_id", "line1", "address_type"})


class AddressService:
    """Orchestrates Geography reference validation + Address persistence."""

    def __init__(
        self,
        repository: AddressRepository,
        reference_repositories: Mapping[str, AbstractRepository[SupportsId]],
    ) -> None:
        self._repository = repository
        self._reference_repositories = reference_repositories
        self._logger = get_logger("service.address")

    async def get_in_organization(self, address_id: UUID, organization_id: UUID) -> Address:
        address = await self._repository.get_by_id_in_organization(address_id, organization_id)
        if address is None:
            raise NotFoundError(f"Address with id {address_id} was not found")
        return address

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Address]:
        return await self._repository.list_in_organization(
            organization_id, limit=limit, offset=offset
        )

    async def count_in_organization(self, organization_id: UUID) -> int:
        return await self._repository.count_in_organization(organization_id)

    async def create_in_organization(
        self, organization_id: UUID, fields: Mapping[str, Any]
    ) -> Address:
        writable = {key: value for key, value in fields.items() if key in _WRITABLE_FIELDS}
        if writable.get("country_id") is None:
            raise ValidationError("country_id is required")
        await self._validate_geography_references(writable)
        address = Address(organization_id=organization_id, **writable)
        return await self._repository.add(address)

    async def update_in_organization(
        self, address_id: UUID, organization_id: UUID, fields: Mapping[str, Any]
    ) -> Address:
        address = await self.get_in_organization(address_id, organization_id)
        writable = {key: value for key, value in fields.items() if key in _WRITABLE_FIELDS}
        if "country_id" in fields and writable.get("country_id") is None:
            raise ValidationError("country_id is required and cannot be cleared")
        for field in _NOT_NULLABLE_FIELDS - {"country_id"}:
            if field in writable and writable.get(field) is None:
                raise ValidationError(f"{field} is required and cannot be cleared")
        await self._validate_geography_references(writable)
        for key, value in writable.items():
            setattr(address, key, value)
        return await self._repository.update(address)

    async def delete_in_organization(self, address_id: UUID, organization_id: UUID) -> None:
        address = await self.get_in_organization(address_id, organization_id)
        try:
            await self._repository.delete(address.id)
        except IntegrityError:
            self._logger.warning(
                "Referenced-delete blocked for address %s in organization %s",
                address_id,
                organization_id,
            )
            raise ConflictError(
                f"Address with id {address_id} is referenced by other records and cannot be deleted"
            ) from None

    async def _validate_geography_references(self, fields: Mapping[str, Any]) -> None:
        for key in _REFERENCE_FIELDS:
            ref_id = fields.get(key)
            if ref_id is None:
                continue
            repository = self._reference_repositories.get(key.removesuffix("_id"))
            if repository is None:
                raise UnexpectedError(f"Internal geography repository for {key} is not configured")
            reference = await repository.get_by_id(ref_id)
            if reference is None:
                raise ValidationError(f"{key} with id {ref_id} does not exist")
