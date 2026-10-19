"""T134 API evidence for Party-canonical, Organization-scoped Matter writes."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.application.errors.exceptions import ConflictError
from app.application.matter_service import MatterService
from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.database.session import get_admin_db, get_db
from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import MatterParty, Party
from app.infrastructure.persistence.sqlalchemy_matter_repository import SqlAlchemyMatterRepository
from app.infrastructure.persistence.sqlalchemy_party_repository import SqlAlchemyPartyRepository
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)

_PASSWORD = "correct horse battery staple"
_PATH = "/api/v1/matters"


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t134_matters")
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
        full_name="Matter user",
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


async def _lookups(session: AsyncSession) -> tuple[MatterType, MatterStatus]:
    return (
        (await session.execute(select(MatterType).limit(1))).scalar_one(),
        (await session.execute(select(MatterStatus).limit(1))).scalar_one(),
    )


def _payload(matter_type: MatterType, matter_status: MatterStatus, party: Party) -> dict[str, str]:
    return {
        "matter_number": f"MAT-{uuid4()}",
        "matter_type_id": str(matter_type.id),
        "matter_status_id": str(matter_status.id),
        "title": "Canonical Matter",
        "opened_at": datetime.now(UTC).isoformat(),
        "client_party_id": str(party.id),
    }


@pytest.mark.asyncio
async def test_canonical_create_has_no_client_and_is_scoped(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(client, session, "matters:read", "matters:write")
    party = await _party(session, organization)
    matter_type, matter_status = await _lookups(session)
    clients_before = (await session.execute(select(func.count()).select_from(Client))).scalar_one()

    response = await client.post(
        _PATH, json=_payload(matter_type, matter_status, party), headers=headers
    )
    assert response.status_code == 201
    created = response.json()["data"]
    matter_id = UUID(created["id"])
    assert created["legacy_client_id"] is None
    assert created["participants"] == [{"party_id": str(party.id), "role": "client"}]
    matter = await session.get(Matter, matter_id)
    assert (
        matter is not None
        and matter.client_id is None
        and matter.organization_id == organization.id
    )
    assert (
        await session.execute(select(MatterParty).where(MatterParty.matter_id == matter_id))
    ).scalar_one().party_id == party.id
    assert (
        await session.execute(select(func.count()).select_from(Client))
    ).scalar_one() == clients_before

    other_headers, _other_org = await _headers(client, session, "matters:read")
    assert (await client.get(f"{_PATH}/{matter_id}", headers=other_headers)).status_code == 404
    assert (await client.get(_PATH, headers=other_headers)).json()["data"] == []

    update = await client.put(
        f"{_PATH}/{matter_id}", json={"title": "Updated canonical matter"}, headers=headers
    )
    assert update.status_code == 200
    assert update.json()["data"]["title"] == "Updated canonical matter"
    assert update.json()["data"]["legacy_client_id"] is None
    assert update.json()["data"]["participants"] == [{"party_id": str(party.id), "role": "client"}]
    assert (
        await client.put(f"{_PATH}/{matter_id}", json={"client_id": str(uuid4())}, headers=headers)
    ).status_code == 200
    await session.refresh(matter)
    assert matter.client_id is None

    denied_headers, _ = await _headers(client, session, "matters:read")
    assert (
        await client.put(f"{_PATH}/{matter_id}", json={"title": "Denied"}, headers=denied_headers)
    ).status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_or_invalid_participant_does_not_persist(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(client, session, "matters:write")
    _same_party = await _party(session, organization)
    other_headers, other_org = await _headers(client, session, "matters:read")
    other_party = await _party(session, other_org)
    matter_type, matter_status = await _lookups(session)
    before = (await session.execute(select(func.count()).select_from(Matter))).scalar_one()
    response = await client.post(
        _PATH, json=_payload(matter_type, matter_status, other_party), headers=headers
    )
    assert response.status_code == 422
    assert (await session.execute(select(func.count()).select_from(Matter))).scalar_one() == before
    assert (await session.execute(select(func.count()).select_from(MatterParty))).scalar_one() == 0
    assert other_headers  # proves the foreign Party belongs to a separately authenticated tenant.


@pytest.mark.asyncio
async def test_duplicate_matter_number_is_a_scoped_conflict_and_request_recovers(
    client: AsyncClient, session: AsyncSession
) -> None:
    """The real PostgreSQL constraint is global, but its 409 discloses no tenant."""
    headers_a, organization_a = await _headers(client, session, "matters:read", "matters:write")
    party_a = await _party(session, organization_a)
    matter_type, matter_status = await _lookups(session)
    payload = _payload(matter_type, matter_status, party_a)
    payload["matter_number"] = f"MAT-CONFLICT-{uuid4()}"

    created = await client.post(_PATH, json=payload, headers=headers_a)
    assert created.status_code == 201
    created_id = UUID(created.json()["data"]["id"])

    headers_b, organization_b = await _headers(client, session, "matters:read", "matters:write")
    party_b = await _party(session, organization_b)
    duplicate = {**payload, "client_party_id": str(party_b.id)}
    rejected = await client.post(_PATH, json=duplicate, headers=headers_b)

    assert rejected.status_code == 409
    assert rejected.json() == {
        "error": {"code": "conflict", "message": "Matter number is already in use"}
    }
    assert str(organization_a.id) not in rejected.text
    assert str(organization_b.id) not in rejected.text
    assert (
        await session.execute(
            select(Matter).where(Matter.matter_number == payload["matter_number"])
        )
    ).scalars().all() == [await session.get(Matter, created_id)]
    assert (
        await session.execute(select(MatterParty).where(MatterParty.matter_id == created_id))
    ).scalars().all()[0].party_id == party_a.id

    # A post-savepoint request on the same session remains usable.
    recovered = await client.post(
        _PATH, json=_payload(matter_type, matter_status, party_b), headers=headers_b
    )
    assert recovered.status_code == 201

    # RBAC remains ahead of persistence: an unprivileged caller cannot use the
    # conflict response to probe globally unique Matter numbers.
    read_only_headers, _ = await _headers(client, session, "matters:read")
    denied = await client.post(_PATH, json=duplicate, headers=read_only_headers)
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_concurrent_duplicate_matter_number_keeps_global_integrity(
    disposable_db: tuple[str, str], session: AsyncSession
) -> None:
    organization_a, organization_b = Organization(name=f"Org-{uuid4()}"), Organization(
        name=f"Org-{uuid4()}"
    )
    session.add_all([organization_a, organization_b])
    await session.flush()
    party_a, party_b = await _party(session, organization_a), await _party(session, organization_b)
    matter_type, matter_status = await _lookups(session)
    await session.commit()

    number = f"MAT-C-{uuid4().hex[:12]}"
    engine = create_async_engine(disposable_db[0])
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create(organization: Organization, party: Party) -> str:
        async with factory() as db:
            service = MatterService(
                SqlAlchemyMatterRepository(db),
                SqlAlchemyPartyRepository(db),
                SqlAlchemyRepository(db, MatterType),
                SqlAlchemyRepository(db, MatterStatus),
            )
            try:
                await service.create_in_organization(
                    organization.id,
                    {
                        "matter_number": number,
                        "matter_type_id": matter_type.id,
                        "matter_status_id": matter_status.id,
                        "title": "Concurrent Matter",
                        "opened_at": datetime.now(UTC),
                    },
                    party.id,
                    [],
                )
                await db.commit()
                return "created"
            except ConflictError:
                await db.commit()
                return "conflict"

    try:
        outcomes = await asyncio.gather(
            create(organization_a, party_a), create(organization_b, party_b)
        )
        assert sorted(outcomes) == ["conflict", "created"]
        async with factory() as verification:
            matters = (
                (await verification.execute(select(Matter).where(Matter.matter_number == number)))
                .scalars()
                .all()
            )
            assert len(matters) == 1
            participants = (
                (
                    await verification.execute(
                        select(MatterParty).where(MatterParty.matter_id == matters[0].id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(participants) == 1
    finally:
        async with factory() as cleanup:
            matter_ids = select(Matter.id).where(Matter.matter_number == number)
            await cleanup.execute(delete(MatterParty).where(MatterParty.matter_id.in_(matter_ids)))
            await cleanup.execute(delete(Matter).where(Matter.matter_number == number))
            await cleanup.execute(delete(Party).where(Party.id.in_((party_a.id, party_b.id))))
            await cleanup.execute(
                delete(Organization).where(
                    Organization.id.in_((organization_a.id, organization_b.id))
                )
            )
            await cleanup.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_legacy_client_link_is_read_without_canonical_rewrite(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(client, session, "matters:read")
    matter_type, matter_status = await _lookups(session)
    legacy_client = Client(
        id=uuid4(),
        organization_id=organization.id,
        client_type="individual",
        full_name="Retained legacy client",
        primary_phone="9876543210",
    )
    legacy_matter = Matter(
        id=uuid4(),
        organization_id=organization.id,
        matter_number=f"LEG-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=matter_status.id,
        client_id=legacy_client.id,
        title="Retained legacy matter",
        opened_at=datetime.now(UTC),
    )
    session.add_all([legacy_client, legacy_matter])
    await session.flush()

    response = await client.get(f"{_PATH}/{legacy_matter.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["legacy_client_id"] == str(legacy_client.id)
    assert response.json()["data"]["participants"] == []
    await session.refresh(legacy_matter)
    assert legacy_matter.client_id == legacy_client.id
    assert await session.get(Client, legacy_client.id) is not None
    assert (await session.execute(select(func.count()).select_from(MatterParty))).scalar_one() == 0
