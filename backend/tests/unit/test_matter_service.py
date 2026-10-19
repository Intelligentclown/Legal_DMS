from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.errors.exceptions import ConflictError, ValidationError
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


class _IntegrityErrorMatterRepository(_MatterRepository):
    def __init__(self, error: IntegrityError) -> None:
        super().__init__()
        self.error = error

    async def add_with_participants(self, matter, participants):
        raise self.error


class _PostgresError(Exception):
    def __init__(self, sqlstate: str, constraint_name: str) -> None:
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


class _AsyncpgAdapterError(Exception):
    def __init__(self, cause: BaseException) -> None:
        self.__cause__ = cause


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


def _unique_error(constraint_name: str, *, sqlstate: str = "23505") -> IntegrityError:
    return IntegrityError("INSERT INTO matters ...", {}, _PostgresError(sqlstate, constraint_name))


def _wrapped_unique_error(constraint_name: str) -> IntegrityError:
    return IntegrityError(
        "INSERT INTO matters ...",
        {},
        _AsyncpgAdapterError(_PostgresError("23505", constraint_name)),
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


@pytest.mark.asyncio
async def test_verified_matter_number_unique_violation_becomes_conflict() -> None:
    organization_id = uuid4()
    party = Party(
        id=uuid4(),
        organization_id=organization_id,
        party_type="individual",
        display_name="Client",
        primary_phone="9876543210",
    )
    service, _repository, matter_type, matter_status = _service(party)
    service._repository = _IntegrityErrorMatterRepository(
        _wrapped_unique_error("uq_matters_matter_number")
    )

    with pytest.raises(ConflictError, match="Matter number is already in use"):
        await service.create_in_organization(
            organization_id,
            {
                "matter_number": "MAT-UNIQUE",
                "matter_type_id": matter_type.id,
                "matter_status_id": matter_status.id,
                "title": "Rejected matter",
                "opened_at": datetime.now(UTC),
            },
            party.id,
            [],
        )


@pytest.mark.asyncio
async def test_non_target_integrity_error_remains_untranslated() -> None:
    organization_id = uuid4()
    party = Party(
        id=uuid4(),
        organization_id=organization_id,
        party_type="individual",
        display_name="Client",
        primary_phone="9876543210",
    )
    service, _repository, matter_type, matter_status = _service(party)
    expected = _unique_error("uq_matters_organization_id_id")
    service._repository = _IntegrityErrorMatterRepository(expected)

    with pytest.raises(IntegrityError) as raised:
        await service.create_in_organization(
            organization_id,
            {
                "matter_number": "MAT-OTHER",
                "matter_type_id": matter_type.id,
                "matter_status_id": matter_status.id,
                "title": "Rejected matter",
                "opened_at": datetime.now(UTC),
            },
            party.id,
            [],
        )

    assert raised.value is expected
