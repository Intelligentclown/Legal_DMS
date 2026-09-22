"""Address repository port (T130): `AbstractRepository[Address]` plus the
org-scoped lookups the `addresses.py` presentation layer and `AddressService`
need.

Same reasoning and pattern as `PartyRepository` (T124): narrow and concrete —
one method per immediate caller need — not a general query interface. The
persistence model is referenced directly, per ADR-0008. Addresses are already
tenant-finalized and RLS-protected (T122); every lookup below is scoped to the
caller's resolved Organization so cross-tenant IDs stay non-enumerable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.client import Address


class AddressRepository(AbstractRepository[Address], ABC):
    @abstractmethod
    async def get_by_id_in_organization(
        self, address_id: UUID, organization_id: UUID
    ) -> Address | None:
        """T130: the target Address, only if it belongs to `organization_id` —
        cross-Org lookups return the same 404 as a nonexistent id."""
        ...

    @abstractmethod
    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Address]:
        """T130: every Address in `organization_id`, paginated."""
        ...

    @abstractmethod
    async def count_in_organization(self, organization_id: UUID) -> int:
        """T130: total Address count in `organization_id`, for pagination."""
        ...
