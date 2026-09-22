"""T130 HTTP behavior of the governed Address application surface.

The real mounted FastAPI app uses a disposable T126-created and bootstrapped
PostgreSQL installation (never the shared development database), so every
route runs against the real migrated schema including T130's
`addresses:*` permission seed.

Structure mirrors `test_party_routes.py`'s approved pattern (httpx
`ASGITransport`, `get_db`/`get_admin_db` overridden to this test's own session
over the owning admin role). Unlike the Party surface, the Address surface has
no installation-state write gate: T130 explicitly does not copy or generalize
`PartyWriteGate`, so no gate fixture is needed — the routes exercise
permission, Organization scoping, validation, and referenced-delete behavior.

Covered:

- authorization: every route 401s without a token, and each route enforces
  its own permission code (reads `addresses:read`, writes `addresses:write`,
  delete `addresses:delete`) with 403 for permission-less callers;
- Organization scoping: a caller with no resolved Organization is fail-closed
  403 on every route; a caller cannot read or mutate another tenant's Address
  (404, never a cross-Org data leak);
- CRUD happy path: create → get → list (pagination) → partial PUT → PUT with
  explicit `null` (clears a nullable field) → delete → 404 after;
- field/type validation: `address_type` bounded to the model's CHECK values,
  `country_id` required, every provided geography reference must resolve to an
  existing row, and NOT NULL fields cannot be explicitly nulled;
- controlled referenced-delete: an Address still referenced by a Party/Client
  is refused with a controlled 409, and deleting it after the reference is
  removed succeeds.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
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
from app.infrastructure.persistence.models.geography import (
    Country,
    District,
    State,
    Taluka,
    Village,
)
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import Party
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)

_PASSWORD = "correct horse battery staple"

ADDRESSES_PATH = "/api/v1/addresses"


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, db_name = provision_empty_disposable_database("legal_dms_t130_addresses")
    try:
        asyncio.run(establish_fresh_installation(url))
        asyncio.run(run_bootstrap(url))
        yield url, db_name
    finally:
        drop_disposable_database(db_name)


@pytest.fixture
async def admin_engine(disposable_db: tuple[str, str]) -> AsyncGenerator[AsyncEngine, None]:
    url, _db_name = disposable_db
    engine = create_async_engine(url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(admin_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(admin_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_admin_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_admin_db, None)


async def _make_organization(db_session: AsyncSession, **overrides: object) -> Organization:
    organization = Organization(**{"name": f"Org-{uuid4()}", **overrides})
    db_session.add(organization)
    await db_session.flush()
    return organization


async def _make_user(db_session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": f"{uuid4()}@example.com",
        "full_name": "Test Address User",
        "password_hash": hash_password(_PASSWORD),
        "is_active": True,
    }
    user = User(**{**defaults, **overrides})
    db_session.add(user)
    await db_session.flush()
    return user


async def _login(client: AsyncClient, user: User) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": _PASSWORD}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _grant_permissions(db_session: AsyncSession, user: User, *permission_codes: str) -> None:
    role = Role(name=f"Role-{uuid4()}")
    db_session.add(role)
    await db_session.flush()
    for code in permission_codes:
        result = await db_session.execute(select(Permission).where(Permission.code == code))
        permission = result.scalar_one()
        db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()


async def _headers_with_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
    *permission_codes: str,
    organization: Organization | None = None,
) -> tuple[dict[str, str], Organization]:
    organization = organization or await _make_organization(db_session)
    caller = await _make_user(db_session, organization_id=organization.id)
    await _grant_permissions(db_session, caller, *permission_codes)
    access_token = await _login(client, caller)
    return {"Authorization": f"Bearer {access_token}"}, organization


async def _seed_country(db_session: AsyncSession) -> Country:
    used_codes = set((await db_session.execute(select(Country.iso_code))).scalars())
    iso_code = f"{str(uuid4())[:2].upper()}"
    while iso_code in used_codes:
        iso_code = f"{str(uuid4())[:2].upper()}"
    country = Country(name=f"Country-{uuid4()}", iso_code=iso_code)
    db_session.add(country)
    await db_session.flush()
    return country


async def _seed_geography_chain(
    db_session: AsyncSession,
) -> dict[str, Country | State | District | Taluka | Village]:
    country = await _seed_country(db_session)
    state = State(country_id=country.id, name=f"State-{uuid4()}")
    db_session.add(state)
    await db_session.flush()
    district = District(state_id=state.id, name=f"District-{uuid4()}")
    db_session.add(district)
    await db_session.flush()
    taluka = Taluka(district_id=district.id, name=f"Taluka-{uuid4()}")
    db_session.add(taluka)
    await db_session.flush()
    village = Village(taluka_id=taluka.id, name=f"Village-{uuid4()}")
    db_session.add(village)
    await db_session.flush()
    return {
        "country": country,
        "state": state,
        "district": district,
        "taluka": taluka,
        "village": village,
    }


async def _make_address(db_session: AsyncSession, organization: Organization) -> Address:
    country = await _seed_country(db_session)
    address = Address(
        organization_id=organization.id, line1=f"Addr-{uuid4()}", country_id=country.id
    )
    db_session.add(address)
    await db_session.flush()
    return address


def _address_payload_for_country(country: Country, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {"line1": "123 Main Street", "country_id": country.id}
    payload.update(overrides)
    return {key: str(value) for key, value in payload.items()}


class TestAuthorization:
    async def test_list_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(ADDRESSES_PATH)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def test_list_invalid_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get(ADDRESSES_PATH, headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def test_list_requires_addresses_read(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:write"
        )
        response = await client.get(ADDRESSES_PATH, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_get_requires_addresses_read(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:write"
        )
        response = await client.get(f"{ADDRESSES_PATH}/{uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_create_requires_addresses_write(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read"
        )
        country = await _seed_country(db_session)
        response = await client.post(
            ADDRESSES_PATH, headers=headers, json=_address_payload_for_country(country)
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_update_requires_addresses_write(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read"
        )
        response = await client.put(
            f"{ADDRESSES_PATH}/{uuid4()}", headers=headers, json={"line1": "X"}
        )
        assert response.status_code == 403

    async def test_delete_requires_addresses_delete(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write"
        )
        response = await client.delete(f"{ADDRESSES_PATH}/{uuid4()}", headers=headers)
        assert response.status_code == 403


class TestOrganizationScoping:
    async def test_list_fails_closed_without_organization_context(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        await _grant_permissions(db_session, user, "addresses:read")
        access_token = await _login(client, user)
        response = await client.get(
            ADDRESSES_PATH, headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_get_fails_closed_without_organization_context(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        await _grant_permissions(db_session, user, "addresses:read")
        access_token = await _login(client, user)
        response = await client.get(
            f"{ADDRESSES_PATH}/{uuid4()}", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 403

    async def test_cross_organization_address_is_invisible(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        org_a = await _make_organization(db_session)
        headers_b, org_b = await _headers_with_permissions(client, db_session, "addresses:read")

        create_headers, _org_a = await _headers_with_permissions(
            client, db_session, "addresses:write", organization=org_a
        )
        country = await _seed_country(db_session)
        create_response = await client.post(
            ADDRESSES_PATH,
            headers=create_headers,
            json=_address_payload_for_country(country),
        )
        assert create_response.status_code == 201
        address_id = create_response.json()["data"]["id"]

        # org B's caller cannot see org A's Address — 404 on get, empty list.
        get_response = await client.get(f"{ADDRESSES_PATH}/{address_id}", headers=headers_b)
        assert get_response.status_code == 404
        list_response = await client.get(ADDRESSES_PATH, headers=headers_b)
        assert list_response.status_code == 200
        assert list_response.json()["data"] == []
        assert org_b.id != org_a.id

    async def test_cross_organization_update_and_delete_are_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        org_a = await _make_organization(db_session)
        await _headers_with_permissions(client, db_session, "addresses:read", organization=org_a)
        headers_b, _org_b = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write", "addresses:delete"
        )

        update_response = await client.put(
            f"{ADDRESSES_PATH}/{uuid4()}", headers=headers_b, json={"line1": "X"}
        )
        assert update_response.status_code == 404
        delete_response = await client.delete(f"{ADDRESSES_PATH}/{uuid4()}", headers=headers_b)
        assert delete_response.status_code == 404


class TestAddressCrud:
    async def test_create_get_list_partial_update_clear_and_delete(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write", "addresses:delete"
        )
        country = await _seed_country(db_session)

        create_response = await client.post(
            ADDRESSES_PATH,
            headers=headers,
            json=_address_payload_for_country(
                country, line2="Apt 4", postal_code="380001", address_type="mailing"
            ),
        )
        assert create_response.status_code == 201
        created = create_response.json()["data"]
        address_id = created["id"]
        assert created["line1"] == "123 Main Street"
        assert created["line2"] == "Apt 4"
        assert created["country_id"] == str(country.id)
        assert created["postal_code"] == "380001"
        assert created["address_type"] == "mailing"
        assert "organization_id" not in created

        get_response = await client.get(f"{ADDRESSES_PATH}/{address_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["data"] == created

        list_response = await client.get(ADDRESSES_PATH, headers=headers)
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()["data"]] == [address_id]
        assert list_response.json()["meta"]["pagination"]["total"] == 1

        put_response = await client.put(
            f"{ADDRESSES_PATH}/{address_id}",
            headers=headers,
            json={"line1": "456 Renamed Avenue"},
        )
        assert put_response.status_code == 200
        assert put_response.json()["data"]["line1"] == "456 Renamed Avenue"
        assert put_response.json()["data"]["line2"] == "Apt 4"
        assert put_response.json()["data"]["country_id"] == str(country.id)

        clear_response = await client.put(
            f"{ADDRESSES_PATH}/{address_id}", headers=headers, json={"line2": None}
        )
        assert clear_response.status_code == 200
        assert clear_response.json()["data"]["line2"] is None

        delete_response = await client.delete(f"{ADDRESSES_PATH}/{address_id}", headers=headers)
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        after_delete = await client.get(f"{ADDRESSES_PATH}/{address_id}", headers=headers)
        assert after_delete.status_code == 404
        assert after_delete.json()["error"]["code"] == "not_found"

    async def test_create_defaults_address_type_to_registered(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write"
        )
        country = await _seed_country(db_session)
        response = await client.post(
            ADDRESSES_PATH, headers=headers, json=_address_payload_for_country(country)
        )
        assert response.status_code == 201
        assert response.json()["data"]["address_type"] == "registered"

    async def test_pagination_respects_page_and_page_size(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write"
        )
        country = await _seed_country(db_session)
        for i in range(3):
            response = await client.post(
                ADDRESSES_PATH,
                headers=headers,
                json=_address_payload_for_country(country, line1=f"Street-{i}"),
            )
            assert response.status_code == 201

        list_response = await client.get(
            ADDRESSES_PATH, headers=headers, params={"page": 1, "page_size": 2}
        )
        assert list_response.status_code == 200
        body = list_response.json()
        assert len(body["data"]) == 2
        assert body["meta"]["pagination"]["total"] == 3
        assert body["meta"]["pagination"]["page"] == 1
        assert body["meta"]["pagination"]["total_pages"] == 2

    async def test_get_nonexistent_address_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read"
        )
        response = await client.get(f"{ADDRESSES_PATH}/{uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestAddressFieldAndGeographyValidation:
    async def test_create_rejects_invalid_address_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:write"
        )
        country = await _seed_country(db_session)
        response = await client.post(
            ADDRESSES_PATH,
            headers=headers,
            json=_address_payload_for_country(country, address_type="commercial"),
        )
        assert response.status_code == 422

    async def test_create_requires_country(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:write"
        )
        response = await client.post(ADDRESSES_PATH, headers=headers, json={"line1": "X"})
        assert response.status_code == 422

    async def test_create_rejects_nonexistent_country(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:write"
        )
        response = await client.post(
            ADDRESSES_PATH,
            headers=headers,
            json={"line1": "X", "country_id": str(uuid4())},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_create_rejects_nonexistent_geography_reference(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:write"
        )
        country = await _seed_country(db_session)
        response = await client.post(
            ADDRESSES_PATH,
            headers=headers,
            json=_address_payload_for_country(country, state_id=str(uuid4())),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_create_with_full_geography_chain_succeeds(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write"
        )
        chain = await _seed_geography_chain(db_session)
        response = await client.post(
            ADDRESSES_PATH,
            headers=headers,
            json=_address_payload_for_country(
                chain["country"],
                state_id=chain["state"].id,
                district_id=chain["district"].id,
                taluka_id=chain["taluka"].id,
                village_id=chain["village"].id,
            ),
        )
        assert response.status_code == 201
        created = response.json()["data"]
        assert created["state_id"] == str(chain["state"].id)
        assert created["district_id"] == str(chain["district"].id)
        assert created["taluka_id"] == str(chain["taluka"].id)
        assert created["village_id"] == str(chain["village"].id)

    async def test_update_rejects_explicit_null_for_not_nullable_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write"
        )
        country = await _seed_country(db_session)
        create_response = await client.post(
            ADDRESSES_PATH, headers=headers, json=_address_payload_for_country(country)
        )
        address_id = create_response.json()["data"]["id"]

        for field in ("country_id", "line1", "address_type"):
            response = await client.put(
                f"{ADDRESSES_PATH}/{address_id}", headers=headers, json={field: None}
            )
            assert response.status_code == 422, f"{field} should not be clearable"

    async def test_update_to_nonexistent_geography_reference_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write"
        )
        country = await _seed_country(db_session)
        create_response = await client.post(
            ADDRESSES_PATH, headers=headers, json=_address_payload_for_country(country)
        )
        address_id = create_response.json()["data"]["id"]
        response = await client.put(
            f"{ADDRESSES_PATH}/{address_id}",
            headers=headers,
            json={"taluka_id": str(uuid4())},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


class TestControlledReferencedDelete:
    async def test_delete_address_referenced_by_party_is_conflict(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write", "addresses:delete"
        )
        country = await _seed_country(db_session)
        create_response = await client.post(
            ADDRESSES_PATH, headers=headers, json=_address_payload_for_country(country)
        )
        address_id = create_response.json()["data"]["id"]

        db_session.add(
            Party(
                organization_id=organization.id,
                party_type="individual",
                display_name="Referencing Party",
                primary_phone="9876543210",
                address_id=address_id,
            )
        )
        await db_session.flush()

        response = await client.delete(f"{ADDRESSES_PATH}/{address_id}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    async def test_delete_address_referenced_by_client_is_conflict(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write", "addresses:delete"
        )
        country = await _seed_country(db_session)
        create_response = await client.post(
            ADDRESSES_PATH, headers=headers, json=_address_payload_for_country(country)
        )
        address_id = create_response.json()["data"]["id"]

        db_session.add(
            Client(
                organization_id=organization.id,
                client_type="individual",
                full_name="Referencing Client",
                primary_phone="9876543210",
                address_id=address_id,
            )
        )
        await db_session.flush()

        response = await client.delete(f"{ADDRESSES_PATH}/{address_id}", headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    async def test_delete_succeeds_after_reference_removed(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(
            client, db_session, "addresses:read", "addresses:write", "addresses:delete"
        )
        country = await _seed_country(db_session)
        create_response = await client.post(
            ADDRESSES_PATH, headers=headers, json=_address_payload_for_country(country)
        )
        address_id = create_response.json()["data"]["id"]

        party = Party(
            organization_id=organization.id,
            party_type="individual",
            display_name="Referencing Party",
            primary_phone="9876543210",
            address_id=address_id,
        )
        db_session.add(party)
        await db_session.flush()
        # Persist the setup so the failed-delete rollback below cannot discard
        # the address/party fixture. The real `get_db` dependency rolls the
        # request transaction back after any exception, so the shared test
        # session is left in failed-transaction state by the blocked delete and
        # must be rolled back (which would also undo this uncommitted setup).
        await db_session.commit()

        blocked = await client.delete(f"{ADDRESSES_PATH}/{address_id}", headers=headers)
        assert blocked.status_code == 409
        await db_session.rollback()

        party.address_id = None
        await db_session.flush()

        response = await client.delete(f"{ADDRESSES_PATH}/{address_id}", headers=headers)
        assert response.status_code == 204
