from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.errors.exceptions import ValidationError
from app.application.matter_service import MatterService
from app.infrastructure.persistence.models.matter import MatterStatus, MatterType
from app.infrastructure.persistence.models.party import Party


class _MatterRepository:
    def __init__(self) -> None:
        self.created = []
        self.participants = []

    async def add_with_participants(self, matter, participants):
        self.created.append(matter)
        self.participants.extend(participants)
        return matter


class _PartyRepository:
    def __init__(self, party: Party | None) -> None:
        self.party = party

    async def get_by_id_in_organization(self, party_id, organization_id):
        if (
            self.party
            and self.party.id == party_id
            and self.party.organization_id == organization_id
        ):
            return self.party
        return None


class _LookupRepository:
    def __init__(self, item) -> None:
        self.item = item

    async def get_by_id(self, item_id):
        return self.item if self.item.id == item_id else None


def _service(party: Party | None):
    matters = _MatterRepository()
    matter_type = MatterType(id=uuid4(), code="civil", name="Civil")
    matter_status = MatterStatus(id=uuid4(), code="open", name="Open")
    return (
        MatterService(
            matters,
            _PartyRepository(party),
            _LookupRepository(matter_type),
            _LookupRepository(matter_status),
        ),
        matters,
        matter_type,
        matter_status,
    )


@pytest.mark.asyncio
async def test_canonical_create_keeps_client_shadow_null() -> None:
    organization_id = uuid4()
    party = Party(
        id=uuid4(),
        organization_id=organization_id,
        party_type="individual",
        display_name="Client",
        primary_phone="9876543210",
    )
    service, repository, matter_type, matter_status = _service(party)

    matter = await service.create_in_organization(
        organization_id,
        {
            "matter_number": "MAT-1",
            "matter_type_id": matter_type.id,
            "matter_status_id": matter_status.id,
            "title": "Canonical matter",
            "opened_at": datetime.now(UTC),
        },
        party.id,
        [],
    )

    assert matter.client_id is None
    assert len(repository.created) == 1
    assert [(row.party_id, row.role) for row in repository.participants] == [(party.id, "client")]


@pytest.mark.asyncio
async def test_invalid_participant_does_not_create_partial_matter() -> None:
    organization_id = uuid4()
    party = Party(
        id=uuid4(),
        organization_id=organization_id,
        party_type="individual",
        display_name="Client",
        primary_phone="9876543210",
    )
    service, repository, matter_type, matter_status = _service(party)

    with pytest.raises(ValidationError):
        await service.create_in_organization(
            organization_id,
            {
                "matter_number": "MAT-2",
                "matter_type_id": matter_type.id,
                "matter_status_id": matter_status.id,
                "title": "Rejected matter",
                "opened_at": datetime.now(UTC),
            },
            party.id,
            [(uuid4(), "advocate")],
        )

    assert repository.created == []
    assert repository.participants == []
