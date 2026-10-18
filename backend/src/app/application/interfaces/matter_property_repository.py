"""Narrow canonical MatterProperty persistence port for T157."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.infrastructure.persistence.models.matter_property import MatterProperty
from app.infrastructure.persistence.models.property import Property


class MatterPropertyRepository(ABC):
    """Matter-owned canonical association persistence operations only."""

    @abstractmethod
    async def list_properties(
        self, matter_id: UUID, organization_id: UUID
    ) -> Sequence[Property]: ...

    @abstractmethod
    async def add_if_absent(self, association: MatterProperty) -> bool:
        """Persist one association, returning whether this call created it."""
        ...

    @abstractmethod
    async def remove_if_present(
        self, matter_id: UUID, property_id: UUID, organization_id: UUID
    ) -> bool:
        """Remove exactly one canonical association, if present."""
        ...
