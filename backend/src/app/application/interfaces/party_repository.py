"""Party repository port (T124): `AbstractRepository[Party]` plus the
org-scoped lookups the `parties.py` presentation layer and `PartyService`
need.

Same reasoning and pattern as `UserRepository` (T50): narrow and concrete —
one method per immediate caller need — not a general query interface. The
persistence model is referenced directly, per ADR-0008.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.party import Party


class PartyRepository(AbstractRepository[Party], ABC):
    @abstractmethod
    async def get_by_id_in_organization(
        self, party_id: UUID, organization_id: UUID
    ) -> Party | None:
        """T124: the target Party, only if it belongs to `organization_id` —
        cross-Org lookups return the same 404 as a nonexistent id."""
        ...

    @abstractmethod
    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Party]:
        """T124: every Party in `organization_id`, paginated."""
        ...

    @abstractmethod
    async def count_in_organization(self, organization_id: UUID) -> int:
        """T124: total Party count in `organization_id`, for pagination."""
        ...
