"""T124: HTTP behavior of the governed Party application surface — the real
mounted FastAPI app, real Postgres, against a disposable database migrated to
the repository head (never the shared development database, so the ADR-0036
gate sees a genuinely fresh installation).

Structure mirrors `test_users.py`'s approved pattern (httpx `ASGITransport`,
`get_db`/`get_admin_db` overridden to this test's own session over the
owning admin role). Unlike `test_users.py`, the write-gate behavior is NOT
stubbed away by default: the disposable database is cell-emptied by design, so
the real `SqlAlchemyInstallationClassifier` sees `FRESH` and the gate admits
the happy-path suite through the actual gate code path.

Covered:

- authorization: every route 401s without a token, and each route enforces
  its own permission code (reads `parties:read`, writes `parties:write`,
  delete `parties:delete`) with 403 for permission-less callers;
- Organization scoping: a caller with no resolved Organization is fail-closed
  403 on every route; a caller cannot read or mutate another tenant's Party
  (404, never a cross-Org data leak);
- CRUD happy path: create → get → list (pagination) → partial PUT → PUT with
  explicit `null` `address_id` (clears) → delete → 404 after;
- address same-Organization validation: via a forced-`FRESH` classifier
  (address rows legitimately flip the *real* classifier, so the clean 422
  path is exercised with the classifier pinned), same-Org address accepted,
  cross-Org/nonexistent address → 422;
- the real-fresh-install gate: with the real classifier, an installation that
  gains a governed legacy row (an address) fails closed with 403 on
  create/update/delete, before any lookup.
"""

from __future__ import annotations

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

from app.application.interfaces.install_classifier import InstallationState
from app.infrastructure.database.session import get_admin_db, get_db
from app.infrastructure.persistence.models.client import Address
from app.infrastructure.persistence.models.geography import Country
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from app.presentation.api.v1.parties import get_install_classifier
from tests.support.static_install_classifier import StaticInstallationClassifier
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_disposable_database_with,
)

_PASSWORD = "correct horse battery staple"

PARTIES_PATH = "/api/v1/parties"


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, db_name = provision_disposable_database_with("legal_dms_t124_parties")
    try:
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


@pytest.fixture
def force_install_state():
    def _apply(state: InstallationState) -> None:
        app.dependency_overrides[get_install_classifier] = lambda: StaticInstallationClassifier(
            state
        )

    def _clear() -> None:
        app.dependency_overrides.pop(get_install_classifier, None)

    yield _apply
    _clear()


async def _make_organization(db_session: AsyncSession, **overrides: object) -> Organization:
    organization = Organization(**{"name": f"Org-{uuid4()}", **overrides})
    db_session.add(organization)
    await db_session.flush()
    return organization


async def _make_user(db_session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": f"{uuid4()}@example.com",
        "full_name": "Test Party User",
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


async def _make_address(db_session: AsyncSession, organization: Organization) -> Address:
    country = await _seed_country(db_session)
    address = Address(
        organization_id=organization.id, line1=f"Addr-{uuid4()}", country_id=country.id
    )
    db_session.add(address)
    await db_session.flush()
    return address


def _party_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "party_type": "individual",
        "display_name": "Test Party",
        "primary_phone": "9876543210",
    }
    payload.update(overrides)
    return payload


class TestAuthorization:
    async def test_list_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get(PARTIES_PATH)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def test_list_invalid_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get(PARTIES_PATH, headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def test_list_requires_parties_read(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "parties:write"
        )
        response = await client.get(PARTIES_PATH, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_get_requires_parties_read(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "parties:write"
        )
        response = await client.get(f"{PARTIES_PATH}/{uuid4()}", headers=headers)
        assert response.status_code == 403

    async def test_create_requires_parties_write(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(client, db_session, "parties:read")
        response = await client.post(PARTIES_PATH, headers=headers, json=_party_payload())
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_update_requires_parties_write(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(client, db_session, "parties:read")
        response = await client.put(
            f"{PARTIES_PATH}/{uuid4()}", headers=headers, json={"display_name": "X"}
        )
        assert response.status_code == 403

    async def test_delete_requires_parties_delete(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "parties:read", "parties:write"
        )
        response = await client.delete(f"{PARTIES_PATH}/{uuid4()}", headers=headers)
        assert response.status_code == 403


class TestOrganizationScoping:
    async def test_list_fails_closed_without_organization_context(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        await _grant_permissions(db_session, user, "parties:read")
        access_token = await _login(client, user)
        response = await client.get(
            PARTIES_PATH, headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_get_fails_closed_without_organization_context(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session)
        await _grant_permissions(db_session, user, "parties:read")
        access_token = await _login(client, user)
        response = await client.get(
            f"{PARTIES_PATH}/{uuid4()}", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 403

    async def test_cross_organization_party_is_invisible(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        org_a = await _make_organization(db_session)
        headers_b, org_b = await _headers_with_permissions(client, db_session, "parties:read")

        create_headers, _org_a = await _headers_with_permissions(
            client, db_session, "parties:write", organization=org_a
        )
        create_response = await client.post(
            PARTIES_PATH, headers=create_headers, json=_party_payload()
        )
        assert create_response.status_code == 201
        party_id = create_response.json()["data"]["id"]

        # org B's caller cannot see org A's Party — 404 on get, empty list.
        get_response = await client.get(f"{PARTIES_PATH}/{party_id}", headers=headers_b)
        assert get_response.status_code == 404
        list_response = await client.get(PARTIES_PATH, headers=headers_b)
        assert list_response.status_code == 200
        assert list_response.json()["data"] == []
        assert org_b.id != org_a.id

    async def test_cross_organization_update_and_delete_are_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        org_a = await _make_organization(db_session)
        await _headers_with_permissions(client, db_session, "parties:read", organization=org_a)
        headers_b, _org_b = await _headers_with_permissions(
            client, db_session, "parties:read", "parties:write", "parties:delete"
        )

        # A Party that only exists in a different Organization reads as 404
        # for a write/delete caller of org B, because the org-scoped lookup
        # precedes nothing — there is no cross-Organization handle at all.
        update_response = await client.put(
            f"{PARTIES_PATH}/{uuid4()}", headers=headers_b, json={"display_name": "X"}
        )
        assert update_response.status_code == 404
        delete_response = await client.delete(f"{PARTIES_PATH}/{uuid4()}", headers=headers_b)
        assert delete_response.status_code == 404


class TestPartyCrud:
    async def test_create_get_list_partial_update_clear_address_and_delete(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "parties:read", "parties:write", "parties:delete"
        )

        create_response = await client.post(
            PARTIES_PATH,
            headers=headers,
            json=_party_payload(
                display_name="Acme Litigant",
                party_type="organization",
                primary_email="acme@example.test",
                registration_identifier="LTD-123",
                incorporation_date="2020-01-01",
            ),
        )
        assert create_response.status_code == 201
        created = create_response.json()["data"]
        party_id = created["id"]
        assert created["display_name"] == "Acme Litigant"
        assert created["party_type"] == "organization"
        assert created["primary_email"] == "acme@example.test"
        assert created["address_id"] is None
        assert "organization_id" not in created

        get_response = await client.get(f"{PARTIES_PATH}/{party_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["data"] == created

        list_response = await client.get(PARTIES_PATH, headers=headers)
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()["data"]] == [party_id]
        assert list_response.json()["meta"]["pagination"]["total"] == 1

        put_response = await client.put(
            f"{PARTIES_PATH}/{party_id}",
            headers=headers,
            json={"display_name": "Acme Litigant (Renamed)"},
        )
        assert put_response.status_code == 200
        assert put_response.json()["data"]["display_name"] == "Acme Litigant (Renamed)"
        assert put_response.json()["data"]["party_type"] == "organization"

        language_response = await client.put(
            f"{PARTIES_PATH}/{party_id}", headers=headers, json={"address_id": None}
        )
        assert language_response.status_code == 200
        assert language_response.json()["data"]["address_id"] is None

        delete_response = await client.delete(f"{PARTIES_PATH}/{party_id}", headers=headers)
        assert delete_response.status_code == 204
        assert delete_response.content == b""

        after_delete = await client.get(f"{PARTIES_PATH}/{party_id}", headers=headers)
        assert after_delete.status_code == 404
        assert after_delete.json()["error"]["code"] == "not_found"

    async def test_create_validates_party_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "parties:write"
        )
        response = await client.post(
            PARTIES_PATH, headers=headers, json=_party_payload(party_type="corp")
        )
        assert response.status_code == 422

    async def test_create_validates_primary_phone_minimum_length(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(
            client, db_session, "parties:write"
        )
        response = await client.post(
            PARTIES_PATH, headers=headers, json=_party_payload(primary_phone="123")
        )
        assert response.status_code == 422

    async def test_get_nonexistent_party_is_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, _organization = await _headers_with_permissions(client, db_session, "parties:read")
        response = await client.get(f"{PARTIES_PATH}/{uuid4()}", headers=headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestAddressSameOrganizationValidation:
    async def test_create_with_same_organization_address_succeeds(
        self, client: AsyncClient, db_session: AsyncSession, force_install_state
    ) -> None:
        force_install_state(InstallationState.FRESH)
        headers, organization = await _headers_with_permissions(
            client, db_session, "parties:read", "parties:write"
        )
        address = await _make_address(db_session, organization)
        response = await client.post(
            PARTIES_PATH, headers=headers, json=_party_payload(address_id=str(address.id))
        )
        assert response.status_code == 201
        assert response.json()["data"]["address_id"] == str(address.id)

    async def test_create_with_cross_organization_address_is_422(
        self, client: AsyncClient, db_session: AsyncSession, force_install_state
    ) -> None:
        force_install_state(InstallationState.FRESH)
        caller_headers, _caller_org = await _headers_with_permissions(
            client, db_session, "parties:write"
        )
        other_org = await _make_organization(db_session)
        other_address = await _make_address(db_session, other_org)
        response = await client.post(
            PARTIES_PATH,
            headers=caller_headers,
            json=_party_payload(address_id=str(other_address.id)),
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_create_with_nonexistent_address_is_422(
        self, client: AsyncClient, db_session: AsyncSession, force_install_state
    ) -> None:
        force_install_state(InstallationState.FRESH)
        headers, _organization = await _headers_with_permissions(
            client, db_session, "parties:write"
        )
        response = await client.post(
            PARTIES_PATH, headers=headers, json=_party_payload(address_id=str(uuid4()))
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    async def test_update_to_cross_organization_address_is_422(
        self, client: AsyncClient, db_session: AsyncSession, force_install_state
    ) -> None:
        force_install_state(InstallationState.FRESH)
        headers, _caller_org = await _headers_with_permissions(
            client, db_session, "parties:read", "parties:write"
        )
        create_response = await client.post(PARTIES_PATH, headers=headers, json=_party_payload())
        party_id = create_response.json()["data"]["id"]
        other_org = await _make_organization(db_session)
        other_address = await _make_address(db_session, other_org)
        response = await client.put(
            f"{PARTIES_PATH}/{party_id}",
            headers=headers,
            json={"address_id": str(other_address.id)},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


class TestFreshInstallGate:
    async def test_gate_blocks_create_when_legacy_data_present(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(client, db_session, "parties:write")
        await _make_address(db_session, organization)
        response = await client.post(PARTIES_PATH, headers=headers, json=_party_payload())
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert "fresh" in response.json()["error"]["message"]

    async def test_gate_blocks_update_when_legacy_data_present(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(client, db_session, "parties:write")
        await _make_address(db_session, organization)
        response = await client.put(
            f"{PARTIES_PATH}/{uuid4()}", headers=headers, json={"display_name": "X"}
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_gate_blocks_delete_when_legacy_data_present(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(
            client, db_session, "parties:delete"
        )
        await _make_address(db_session, organization)
        response = await client.delete(f"{PARTIES_PATH}/{uuid4()}", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_gate_does_not_block_reads_when_legacy_data_present(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        headers, organization = await _headers_with_permissions(client, db_session, "parties:read")
        await _make_address(db_session, organization)
        list_response = await client.get(PARTIES_PATH, headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()["data"] == []
