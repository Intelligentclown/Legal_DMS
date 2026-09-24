"""Property repository port (T135): `AbstractRepository[Property]` plus the
org-scoped and owner-graph operations the `properties.py` presentation layer
and `PropertyService` need.

Same reasoning and pattern as `PartyRepository` (T124) and
`MatterRepository` (T134): narrow and concrete — one method per immediate
caller need — not a general query interface. The persistence model is
referenced directly, per ADR-0008. Properties are already tenant-finalized
and RLS-protected (T133); every lookup below is scoped to the caller's
resolved Organization so cross-tenant IDs stay non-enumerable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.property import Property, PropertyOwner


class PropertyRepository(AbstractRepository[Property], ABC):
    @abstractmethod
    async def get_by_id_in_organization(
        self, property_id: UUID, organization_id: UUID
    ) -> Property | None:
        """T135: the target Property, only if it belongs to `organization_id` —
        cross-Org lookups return the same 404 as a nonexistent id."""
        ...

    @abstractmethod
    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Property]:
        """T135: every Property in `organization_id`, paginated."""
        ...

    @abstractmethod
    async def count_in_organization(self, organization_id: UUID) -> int:
        """T135: total Property count in `organization_id`, for pagination."""
        ...

    @abstractmethod
    async def list_owners(
        self, property_id: UUID, organization_id: UUID
    ) -> Sequence[PropertyOwner]:
        """T135: every PropertyOwner row of `property_id`, scoped to
        `organization_id` (the owner rows carry the same tenant as the
        Property they belong to)."""
        ...

    @abstractmethod
    async def add_with_owners(
        self, property_: Property, owners: Sequence[PropertyOwner]
    ) -> Property:
        """T135: persist a Property and its PropertyOwner aggregate
        atomically — a failure anywhere leaves neither row behind."""
        ...
