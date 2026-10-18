"""T157 canonical MatterProperty HTTP, authorization, audit, and race coverage."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.application.interfaces.audit import AuditLogger
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.database.session import get_admin_db, get_db
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.matter_property import MatterProperty
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import MatterParty, Party
from app.infrastructure.persistence.models.property import Property, PropertyOwner
from app.infrastructure.persistence.sqlalchemy_matter_property_repository import (
    SqlAlchemyMatterPropertyRepository,
)
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)

_PASSWORD = "correct horse battery staple"
_PATH = "/api/v1/matters"


class RecordingAuditLogger(AuditLogger):
    def __init__(self) -> None:
        self.calls: list[tuple[CurrentUser, str, str, str | None, dict[str, object] | None]] = []

    async def record(
        self,
        actor: CurrentUser,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.calls.append((actor, action, resource_type, resource_id, metadata))


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t157_matter_property")
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
        full_name="T157 user",
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


async def _headers_without_organization(
    http: AsyncClient, session: AsyncSession, *codes: str
) -> dict[str, str]:
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Unscoped T157 user",
        password_hash=hash_password(_PASSWORD),
        organization_id=None,
        is_active=True,
    )
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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _matter(session: AsyncSession, organization: Organization) -> Matter:
    matter_type = (await session.execute(select(MatterType).limit(1))).scalar_one()
    matter_status = (await session.execute(select(MatterStatus).limit(1))).scalar_one()
    matter = Matter(
        id=uuid4(),
        organization_id=organization.id,
        matter_number=f"MAT-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=matter_status.id,
        title="T157 Matter",
        opened_at=datetime.now(UTC),
    )
    session.add(matter)
    await session.flush()
    return matter


async def _property(session: AsyncSession, organization: Organization) -> Property:
    property_ = Property(
        id=uuid4(),
        organization_id=organization.id,
        property_type="agricultural",
        survey_number=f"SUR-{uuid4()}",
    )
    session.add(property_)
    await session.flush()
    return property_


@pytest.mark.asyncio
async def test_canonical_list_associate_and_unlink_are_idempotent_and_audited(
    client: AsyncClient, session: AsyncSession
) -> None:
    audit = RecordingAuditLogger()
    container.override(AuditLogger, audit)
    try:
        headers, organization = await _headers(
            client, session, "matters:read", "matters:write", "properties:read"
        )
        matter = await _matter(session, organization)
        property_one, property_two = await _property(session, organization), await _property(
            session, organization
        )
        second_matter = await _matter(session, organization)
        party = Party(
            organization_id=organization.id,
            party_type="individual",
            display_name="Owner",
            primary_phone="9876543210",
        )
        session.add(party)
        await session.flush()
        session.add(
            PropertyOwner(
                organization_id=organization.id,
                property_id=property_one.id,
                party_id=party.id,
                ownership_type="owner",
                from_date=datetime.now(UTC).date(),
            )
        )
        await session.flush()

        assert (await client.get(f"{_PATH}/{matter.id}/properties", headers=headers)).json()[
            "data"
        ] == []
        first = await client.post(
            f"{_PATH}/{matter.id}/properties",
            json={"property_id": str(property_one.id)},
            headers=headers,
        )
        assert first.status_code == 201
        assert first.json()["data"]["id"] == str(property_one.id)
        assert first.json()["data"]["owners"][0]["party_id"] == str(party.id)
        assert (
            await client.post(
                f"{_PATH}/{matter.id}/properties",
                json={"property_id": str(property_one.id)},
                headers=headers,
            )
        ).status_code == 200
        assert (
            await client.post(
                f"{_PATH}/{matter.id}/properties",
                json={"property_id": str(property_two.id)},
                headers=headers,
            )
        ).status_code == 201
        assert (
            await client.post(
                f"{_PATH}/{second_matter.id}/properties",
                json={"property_id": str(property_one.id)},
                headers=headers,
            )
        ).status_code == 201
        listed = await client.get(f"{_PATH}/{matter.id}/properties", headers=headers)
        assert listed.status_code == 200
        assert {row["id"] for row in listed.json()["data"]} == {
            str(property_one.id),
            str(property_two.id),
        }
        assert (
            await session.execute(select(func.count()).select_from(MatterProperty))
        ).scalar_one() == 3

        assert (
            await client.delete(
                f"{_PATH}/{matter.id}/properties/{property_one.id}", headers=headers
            )
        ).status_code == 204
        assert (
            await client.delete(
                f"{_PATH}/{matter.id}/properties/{property_one.id}", headers=headers
            )
        ).status_code == 204
        assert await session.get(Matter, matter.id) is not None
        assert (
            await session.execute(
                select(func.count())
                .select_from(MatterProperty)
                .where(MatterProperty.matter_id == second_matter.id)
            )
        ).scalar_one() == 1
        assert await session.get(Property, property_one.id) is not None
        assert (
            await session.execute(select(func.count()).select_from(PropertyOwner))
        ).scalar_one() == 1
        assert (
            await session.execute(select(func.count()).select_from(MatterParty))
        ).scalar_one() == 0
        assert [call[1] for call in audit.calls if call[1].startswith("matter_property_")] == [
            "matter_property_associated",
            "matter_property_associated",
            "matter_property_associated",
            "matter_property_unlinked",
        ]
    finally:
        configure_container()


@pytest.mark.asyncio
async def test_tenant_authorization_and_legacy_boundaries(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(
        client, session, "matters:read", "matters:write", "properties:read"
    )
    matter = await _matter(session, organization)
    property_ = await _property(session, organization)
    other_headers, other_org = await _headers(
        client, session, "matters:read", "matters:write", "properties:read"
    )
    other_matter, other_property = await _matter(session, other_org), await _property(
        session, other_org
    )
    matter.property_id = property_.id
    await session.flush()

    assert (await client.get(f"{_PATH}/{matter.id}/properties", headers=headers)).json()[
        "data"
    ] == []
    assert (
        await client.post(
            f"{_PATH}/{matter.id}/properties",
            json={"property_id": str(other_property.id)},
            headers=headers,
        )
    ).status_code == 404
    assert (
        await client.get(f"{_PATH}/{matter.id}/properties", headers=other_headers)
    ).status_code == 404
    assert (
        await client.post(
            f"{_PATH}/{other_matter.id}/properties",
            json={"property_id": str(property_.id)},
            headers=headers,
        )
    ).status_code == 404
    denied_headers, _ = await _headers(client, session, "matters:read", "properties:read")
    assert (
        await client.post(
            f"{_PATH}/{matter.id}/properties",
            json={"property_id": str(property_.id)},
            headers=denied_headers,
        )
    ).status_code == 403
    no_property_read, _ = await _headers(client, session, "matters:read", "matters:write")
    assert (
        await client.get(f"{_PATH}/{matter.id}/properties", headers=no_property_read)
    ).status_code == 403
    assert (
        await client.post(
            f"{_PATH}/{matter.id}/properties",
            json={"property_id": str(property_.id)},
            headers=no_property_read,
        )
    ).status_code == 403
    no_matter_read, _ = await _headers(client, session, "properties:read")
    assert (
        await client.get(f"{_PATH}/{matter.id}/properties", headers=no_matter_read)
    ).status_code == 403
    unscoped_headers = await _headers_without_organization(
        client, session, "matters:read", "matters:write", "properties:read"
    )
    assert (
        await client.get(f"{_PATH}/{matter.id}/properties", headers=unscoped_headers)
    ).status_code == 403
    assert (
        await client.post(
            f"{_PATH}/{matter.id}/properties",
            json={"property_id": str(property_.id)},
            headers=headers,
        )
    ).status_code == 201
    await session.refresh(matter)
    assert matter.property_id == property_.id


@pytest.mark.asyncio
async def test_concurrent_duplicate_repository_attempts_create_exactly_one_row(
    disposable_db: tuple[str, str],
) -> None:
    url, _ = disposable_db
    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as seed:
            organization = Organization(id=uuid4(), name=f"Race-{uuid4()}")
            seed.add(organization)
            await seed.flush()
            matter, property_ = await _matter(seed, organization), await _property(
                seed, organization
            )
            await seed.commit()

        async def attempt() -> bool:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                created = await SqlAlchemyMatterPropertyRepository(db).add_if_absent(
                    MatterProperty(
                        organization_id=organization.id,
                        matter_id=matter.id,
                        property_id=property_.id,
                    )
                )
                await db.commit()
                return created

        results = await asyncio.gather(attempt(), attempt())
        assert sorted(results) == [False, True]
        async with async_sessionmaker(engine)() as verify:
            assert (
                await verify.execute(
                    select(func.count())
                    .select_from(MatterProperty)
                    .where(MatterProperty.matter_id == matter.id)
                )
            ).scalar_one() == 1
    finally:
        await engine.dispose()
