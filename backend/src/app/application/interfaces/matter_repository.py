"""Organization-scoped Matter persistence port for T134."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.matter import Matter
from app.infrastructure.persistence.models.party import MatterParty


class MatterRepository(AbstractRepository[Matter], ABC):
    @abstractmethod
    async def get_by_id_in_organization(
        self, matter_id: UUID, organization_id: UUID
    ) -> Matter | None: ...

    @abstractmethod
    async def list_in_organization(
        self, organization_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> Sequence[Matter]: ...

    @abstractmethod
    async def count_in_organization(self, organization_id: UUID) -> int: ...

    @abstractmethod
    async def list_participants(
        self, matter_id: UUID, organization_id: UUID
    ) -> Sequence[MatterParty]: ...

    @abstractmethod
    async def add_with_participants(
        self, matter: Matter, participants: Sequence[MatterParty]
    ) -> Matter: ...
