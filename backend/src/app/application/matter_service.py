"""T134 Matter application service: Party-canonical, Organization-scoped writes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from app.application.errors.exceptions import NotFoundError, ValidationError
from app.application.interfaces.matter_repository import MatterRepository
from app.application.interfaces.party_repository import PartyRepository
from app.application.interfaces.repository import AbstractRepository
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.party import MatterParty

_CREATE_FIELDS = frozenset(
    {"matter_number", "matter_type_id", "matter_status_id", "title", "description", "opened_at"}
)
_UPDATE_FIELDS = frozenset(
    {"matter_type_id", "matter_status_id", "title", "description", "opened_at", "closed_at"}
)


class MatterService:
    def __init__(
        self,
        repository: MatterRepository,
        party_repository: PartyRepository,
        matter_type_repository: AbstractRepository[MatterType],
        matter_status_repository: AbstractRepository[MatterStatus],
    ) -> None:
        self._repository = repository
        self._party_repository = party_repository
        self._matter_type_repository = matter_type_repository
        self._matter_status_repository = matter_status_repository

    async def get_in_organization(self, matter_id: UUID, organization_id: UUID) -> Matter:
        matter = await self._repository.get_by_id_in_organization(matter_id, organization_id)
        if matter is None:
            raise NotFoundError(f"Matter with id {matter_id} was not found")
        return matter

    async def list_in_organization(
        self, organization_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Matter]:
        return await self._repository.list_in_organization(
            organization_id, limit=limit, offset=offset
        )

    async def count_in_organization(self, organization_id: UUID) -> int:
        return await self._repository.count_in_organization(organization_id)

    async def participants(self, matter: Matter) -> Sequence[MatterParty]:
        return await self._repository.list_participants(matter.id, matter.organization_id)

    async def create_in_organization(
        self,
        organization_id: UUID,
        fields: Mapping[str, Any],
        client_party_id: UUID,
        participants: Sequence[tuple[UUID, str]],
    ) -> Matter:
        writable = {key: value for key, value in fields.items() if key in _CREATE_FIELDS}
        await self._validate_type_and_status(
            writable["matter_type_id"], writable["matter_status_id"]
        )
        participant_specs = [(client_party_id, "client"), *participants]
        await self._validate_parties(participant_specs, organization_id)
        matter = Matter(id=uuid4(), organization_id=organization_id, client_id=None, **writable)
        rows = [
            MatterParty(
                organization_id=organization_id, matter_id=matter.id, party_id=party_id, role=role
            )
            for party_id, role in participant_specs
        ]
        return await self._repository.add_with_participants(matter, rows)

    async def update_in_organization(
        self, matter_id: UUID, organization_id: UUID, fields: Mapping[str, Any]
    ) -> Matter:
        matter = await self.get_in_organization(matter_id, organization_id)
        writable = {key: value for key, value in fields.items() if key in _UPDATE_FIELDS}
        if (
            "matter_type_id" in writable
            and await self._matter_type_repository.get_by_id(writable["matter_type_id"]) is None
        ):
            raise ValidationError("matter_type_id does not exist")
        if (
            "matter_status_id" in writable
            and await self._matter_status_repository.get_by_id(writable["matter_status_id"]) is None
        ):
            raise ValidationError("matter_status_id does not exist")
        for key, value in writable.items():
            setattr(matter, key, value)
        return await self._repository.update(matter)

    async def _validate_type_and_status(self, matter_type_id: UUID, matter_status_id: UUID) -> None:
        if await self._matter_type_repository.get_by_id(matter_type_id) is None:
            raise ValidationError("matter_type_id does not exist")
        if await self._matter_status_repository.get_by_id(matter_status_id) is None:
            raise ValidationError("matter_status_id does not exist")

    async def _validate_parties(
        self, participants: Sequence[tuple[UUID, str]], organization_id: UUID
    ) -> None:
        seen: set[tuple[UUID, str]] = set()
        for party_id, role in participants:
            if not role:
                raise ValidationError("participant role is required")
            if (party_id, role) in seen:
                raise ValidationError("duplicate MatterParty participation")
            seen.add((party_id, role))
            if (
                await self._party_repository.get_by_id_in_organization(party_id, organization_id)
                is None
            ):
                raise ValidationError(
                    f"Party with id {party_id} does not exist in this Organization"
                )
