"""T135 unit evidence for the Property service contract."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.application.errors.exceptions import ValidationError
from app.application.property_service import PropertyService
from app.infrastructure.persistence.models.client import Address
from app.infrastructure.persistence.models.geography import Village
from app.infrastructure.persistence.models.party import Party
from app.infrastructure.persistence.models.property import Property


class _PropertyRepository:
    def __init__(self) -> None:
        self.created: list[Property] = []
        self.owners_by_property: dict[UUID, list[object]] = {}

    async def add_with_owners(self, property_, owners):
        self.created.append(property_)
        self.owners_by_property[property_.id] = list(owners)
        return property_

    async def get_by_id_in_organization(self, property_id, organization_id):
        for candidate in self.created:
            if candidate.id == property_id and candidate.organization_id == organization_id:
                return candidate
        return None

    async def list_owners(self, property_id, organization_id):
        return self.owners_by_property.get(property_id, [])

    async def update(self, entity):
        return entity


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


class _AddressRepository:
    def __init__(self, address: Address | None) -> None:
        self.address = address

    async def get_by_id_in_organization(self, address_id, organization_id):
        if (
            self.address
            and self.address.id == address_id
            and self.address.organization_id == organization_id
        ):
            return self.address
        return None


class _VillageRepository:
    def __init__(self, village: Village | None) -> None:
        self.village = village

    async def get_by_id(self, village_id):
        return self.village if self.village is not None and self.village.id == village_id else None


def _party(organization_id):
    return Party(
        id=uuid4(),
        organization_id=organization_id,
        party_type="individual",
        display_name="Owner",
        primary_phone="9876543210",
    )


def _address(organization_id):
    return Address(id=uuid4(), organization_id=organization_id, line1="Street", country_id=uuid4())


def _village() -> Village:
    return Village(id=uuid4(), taluka_id=uuid4(), name="Village")


def _service(
    *,
    party: Party | None = None,
    address: Address | None = None,
    village: Village | None = None,
) -> tuple[PropertyService, _PropertyRepository]:
    repository = _PropertyRepository()
    return (
        PropertyService(
            repository,
            _PartyRepository(party),
            _AddressRepository(address),
            _VillageRepository(village),
        ),
        repository,
    )


def _payload(property_type: str = "agricultural") -> dict[str, object]:
    return {
        "property_type": property_type,
        "survey_number": "SN-001",
        "sub_division_number": None,
        "area_value": Decimal("2.50"),
        "area_unit": "acre",
        "address_id": None,
        "village_id": None,
        "registration_number": None,
    }


def _owner(party: Party) -> dict[str, object]:
    return {
        "party_id": party.id,
        "ownership_share": Decimal("100"),
        "ownership_type": "owner",
        "from_date": date(2026, 1, 1),
        "to_date": None,
    }


@pytest.mark.asyncio
async def test_canonical_create_builds_party_only_owners() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    service, repository = _service(party=party)

    property_ = await service.create_in_organization(organization_id, _payload(), [_owner(party)])

    assert len(repository.created) == 1
    assert property_.organization_id == organization_id
    assert property_.survey_number == "SN-001"
    owners = repository.owners_by_property[property_.id]
    assert len(owners) == 1
    row = owners[0]
    assert row.party_id == party.id
    assert row.client_id is None
    assert row.ownership_share == Decimal("100")
    assert row.from_date == date(2026, 1, 1)


@pytest.mark.asyncio
async def test_invalid_party_does_not_create_partial_property() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    service, repository = _service(party=party)

    with pytest.raises(ValidationError):
        await service.create_in_organization(
            organization_id, _payload(), [_owner(party), _owner(_party(uuid4()))]
        )

    assert repository.created == []
    assert repository.owners_by_property == {}


@pytest.mark.asyncio
async def test_duplicate_party_ownership_is_rejected() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    service, repository = _service(party=party)

    with pytest.raises(ValidationError):
        await service.create_in_organization(
            organization_id, _payload(), [_owner(party), _owner(party)]
        )

    assert repository.created == []


@pytest.mark.asyncio
async def test_cross_organization_address_is_rejected() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    foreign_address = _address(uuid4())
    service, repository = _service(party=party, address=foreign_address)
    payload = {**_payload(), "address_id": foreign_address.id}

    with pytest.raises(ValidationError):
        await service.create_in_organization(organization_id, payload, [_owner(party)])

    assert repository.created == []
    assert repository.owners_by_property == {}


@pytest.mark.asyncio
async def test_unknown_village_reference_is_rejected() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    service, repository = _service(party=party, village=None)
    payload = {**_payload(), "village_id": uuid4()}

    with pytest.raises(ValidationError):
        await service.create_in_organization(organization_id, payload, [_owner(party)])

    assert repository.created == []


@pytest.mark.asyncio
async def test_survey_number_is_required() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    service, repository = _service(party=party)

    with pytest.raises(ValidationError):
        await service.create_in_organization(
            organization_id, {**_payload(), "survey_number": None}, [_owner(party)]
        )

    assert repository.created == []


@pytest.mark.asyncio
async def test_update_is_bounded_and_preserves_owners() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    service, _repository = _service(party=party)
    created = await service.create_in_organization(organization_id, _payload(), [_owner(party)])

    await service.update_in_organization(created.id, organization_id, {"area_unit": "hectare"})

    assert created.area_unit == "hectare"
    owners = await service.owners(created)
    assert len(owners) == 1
    assert owners[0].party_id == party.id
    assert owners[0].client_id is None


@pytest.mark.asyncio
async def test_survey_number_cannot_be_cleared() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    service, _repository = _service(party=party)
    created = await service.create_in_organization(organization_id, _payload(), [_owner(party)])

    with pytest.raises(ValidationError):
        await service.update_in_organization(created.id, organization_id, {"survey_number": None})

    assert created.survey_number == "SN-001"


@pytest.mark.asyncio
async def test_village_validation_accepts_existing_reference() -> None:
    organization_id = uuid4()
    party = _party(organization_id)
    village = _village()
    service, repository = _service(party=party, village=village)
    payload = {**_payload(), "village_id": village.id}

    property_ = await service.create_in_organization(organization_id, payload, [_owner(party)])

    assert property_.village_id == village.id
    assert len(repository.created) == 1
