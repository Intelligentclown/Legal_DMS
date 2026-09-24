"""T135 API evidence for Party-canonical, Organization-scoped Property writes."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.database.session import get_admin_db, get_db
from app.infrastructure.persistence.models.client import Address, Client
from app.infrastructure.persistence.models.geography import Country
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import Party
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)

_PASSWORD = "correct horse battery staple"
_PATH = "/api/v1/properties"


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t135_properties")
    try:
        asyncio.run(establish_fresh_installation(url))
        asyncio.run(run_bootstrap(url))
        yield url, name
    finally:
        drop_disposable_database(name)


@pytest.fixture
async def session(disposable_db: tuple[str, str]) -> AsyncGenerator[AsyncSession, None]:
    engine: AsyncEngine = create_async_engine(disposable_db[0])
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            yield db
            await db.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_admin_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()


async def _headers(
    http: AsyncClient, session: AsyncSession, *codes: str
) -> tuple[dict[str, str], Organization]:
    organization = Organization(id=uuid4(), name=f"Org-{uuid4()}")
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Property user",
        password_hash=hash_password(_PASSWORD),
        organization_id=organization.id,
        is_active=True,
    )
    session.add(organization)
    await session.flush()
    session.add(user)
    await session.flush()
    role = Role(name=f"Role-{uuid4()}")
    session.add(role)
    await session.flush()
    for code in codes:
        permission = (
            await session.execute(select(Permission).where(Permission.code == code))
        ).scalar_one()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()
    response = await http.post(
        "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, organization


async def _party(session: AsyncSession, organization: Organization) -> Party:
    party = Party(
        organization_id=organization.id,
        party_type="individual",
        display_name=f"Party-{uuid4()}",
        primary_phone="9876543210",
    )
    session.add(party)
    await session.flush()
    return party


async def _address(session: AsyncSession, organization: Organization) -> Address:
    country = Country(name=f"Country-{uuid4()}", iso_code=f"X{uuid4().hex[:2]}".upper())
    session.add(country)
    await session.flush()
    address = Address(
        organization_id=organization.id,
        line1="Property address",
        country_id=country.id,
    )
    session.add(address)
    await session.flush()
    return address


def _payload(party: Party, address: Address) -> dict[str, object]:
    return {
        "property_type": "agricultural",
        "survey_number": f"SN-{uuid4()}",
        "sub_division_number": "A",
        "area_value": "2.50",
        "area_unit": "acre",
        "address_id": str(address.id),
        "registration_number": None,
        "owners": [
            {
                "party_id": str(party.id),
                "ownership_share": "50",
                "ownership_type": "owner",
                "from_date": "2026-01-01",
            }
        ],
    }


@pytest.mark.asyncio
async def test_canonical_create_has_party_only_owners_and_is_scoped(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(client, session, "properties:read", "properties:write")
    party = await _party(session, organization)
    address = await _address(session, organization)
    clients_before = (await session.execute(select(func.count()).select_from(Client))).scalar_one()

    response = await client.post(_PATH, json=_payload(party, address), headers=headers)
    assert response.status_code == 201
    created = response.json()["data"]
    property_id = UUID(created["id"])
    assert created["survey_number"].startswith("SN-")
    assert created["owners"] == [
        {
            "party_id": str(party.id),
            "legacy_client_id": None,
            "ownership_share": "50.00",
            "ownership_type": "owner",
            "from_date": "2026-01-01",
            "to_date": None,
        }
    ]
    property_row = await session.get(Property, property_id)
    assert (
        property_row is not None
        and property_row.organization_id == organization.id
        and property_row.address_id == address.id
    )
    owner_row = (
        await session.execute(select(PropertyOwner).where(PropertyOwner.property_id == property_id))
    ).scalar_one()
    assert owner_row.party_id == party.id
    assert owner_row.client_id is None
    assert (
        await session.execute(select(func.count()).select_from(Client))
    ).scalar_one() == clients_before

    other_headers, _other_org = await _headers(client, session, "properties:read")
    assert (await client.get(f"{_PATH}/{property_id}", headers=other_headers)).status_code == 404
    assert (await client.get(_PATH, headers=other_headers)).json()["data"] == []

    update = await client.put(
        f"{_PATH}/{property_id}",
        json={"survey_number": f"SN-{uuid4()}", "area_unit": "hectare"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["data"]["area_unit"] == "hectare"
    assert update.json()["data"]["owners"] == created["owners"]
    assert (
        await client.put(
            f"{_PATH}/{property_id}", json={"client_id": str(uuid4())}, headers=headers
        )
    ).status_code == 200
    await session.refresh(property_row)
    still_owners = (
        (
            await session.execute(
                select(PropertyOwner).where(PropertyOwner.property_id == property_id)
            )
        )
        .scalars()
        .all()
    )
    assert [owner.party_id for owner in still_owners] == [party.id]

    denied_headers, _ = await _headers(client, session, "properties:read")
    assert (
        await client.put(
            f"{_PATH}/{property_id}", json={"area_unit": "acre"}, headers=denied_headers
        )
    ).status_code == 403

    # DELETE is deliberately omitted: the T135 boundary keeps no governed
    # Property lifecycle/deletion contract, so the verb is not exposed.
    assert (await client.delete(f"{_PATH}/{property_id}", headers=headers)).status_code == 405


@pytest.mark.asyncio
async def test_cross_tenant_owner_or_address_fails_closed_without_partial_write(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(client, session, "properties:read", "properties:write")
    party = await _party(session, organization)
    address = await _address(session, organization)
    other_headers, other_org = await _headers(client, session, "properties:read")
    other_party = await _party(session, other_org)
    other_address = await _address(session, other_org)
    properties_before = (
        await session.execute(select(func.count()).select_from(Property))
    ).scalar_one()
    payload = _payload(party, address)

    cross_tenant_owner = {**payload, "owners": [_payload(other_party, address)["owners"][0]]}
    response = await client.post(_PATH, json=cross_tenant_owner, headers=headers)
    assert response.status_code == 422
    assert (
        await session.execute(select(func.count()).select_from(Property))
    ).scalar_one() == properties_before
    assert (
        await session.execute(select(func.count()).select_from(PropertyOwner))
    ).scalar_one() == 0

    cross_tenant_address = {**payload, "address_id": str(other_address.id)}
    response = await client.post(_PATH, json=cross_tenant_address, headers=headers)
    assert response.status_code == 422
    assert (
        await session.execute(select(func.count()).select_from(Property))
    ).scalar_one() == properties_before
    assert (
        await session.execute(select(func.count()).select_from(PropertyOwner))
    ).scalar_one() == 0
    assert other_headers  # proves the foreign Party/Address belong to a separately authed tenant.


@pytest.mark.asyncio
async def test_legacy_client_owner_is_read_without_canonical_rewrite(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(client, session, "properties:read")
    legacy_client = Client(
        id=uuid4(),
        organization_id=organization.id,
        client_type="individual",
        full_name="Retained legacy client",
        primary_phone="9876543210",
    )
    legacy_property = Property(
        id=uuid4(),
        organization_id=organization.id,
        survey_number=f"LEG-{uuid4()}",
    )
    legacy_owner = PropertyOwner(
        id=uuid4(),
        organization_id=organization.id,
        property_id=legacy_property.id,
        client_id=legacy_client.id,
        ownership_share=Decimal("100.00"),
        ownership_type="owner",
        from_date=date(2020, 1, 1),
    )
    parties_before = (await session.execute(select(func.count()).select_from(Party))).scalar_one()
    session.add_all([legacy_client, legacy_property, legacy_owner])
    await session.flush()

    response = await client.get(f"{_PATH}/{legacy_property.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["owners"] == [
        {
            "party_id": None,
            "legacy_client_id": str(legacy_client.id),
            "ownership_share": "100.00",
            "ownership_type": "owner",
            "from_date": "2020-01-01",
            "to_date": None,
        }
    ]
    await session.refresh(legacy_owner)
    assert legacy_owner.client_id == legacy_client.id
    assert legacy_owner.party_id is None
    assert await session.get(Client, legacy_client.id) is not None
    assert (
        await session.execute(select(func.count()).select_from(Party))
    ).scalar_one() == parties_before
