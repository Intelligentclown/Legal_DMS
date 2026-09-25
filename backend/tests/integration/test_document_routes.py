"""T139 File-canonical Document API, RBAC, and legacy-preservation evidence."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

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
from app.infrastructure.persistence.models.document import Document, DocumentType
from app.infrastructure.persistence.models.file import File
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.matter import Matter, MatterStatus, MatterType
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)

_PASSWORD = "correct horse battery staple"


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t139_documents")
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
        full_name="Document user",
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


async def _file(
    session: AsyncSession, organization: Organization
) -> tuple[Matter, File, DocumentType]:
    matter_type = (await session.execute(select(MatterType).limit(1))).scalar_one()
    matter_status = (await session.execute(select(MatterStatus).limit(1))).scalar_one()
    document_type = (await session.execute(select(DocumentType).limit(1))).scalar_one()
    matter = Matter(
        id=uuid4(),
        organization_id=organization.id,
        matter_number=f"MAT-{uuid4()}",
        matter_type_id=matter_type.id,
        matter_status_id=matter_status.id,
        title="Matter",
        opened_at=datetime.now(UTC),
    )
    session.add(matter)
    await session.flush()
    file = File(
        id=uuid4(),
        organization_id=organization.id,
        matter_id=matter.id,
        file_number=1,
        title="File",
    )
    session.add(file)
    await session.flush()
    return matter, file, document_type


@pytest.mark.asyncio
async def test_document_routes_are_file_canonical_and_do_not_surface_legacy_unfiled(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, organization = await _headers(client, session, "documents:read", "documents:write")
    matter, file, document_type = await _file(session, organization)
    legacy = Document(
        id=uuid4(),
        organization_id=organization.id,
        matter_id=matter.id,
        file_id=None,
        document_type_id=document_type.id,
        title="Legacy",
    )
    session.add(legacy)
    await session.flush()
    path = f"/api/v1/matters/{matter.id}/files/{file.id}/documents"
    create = await client.post(
        path, headers=headers, json={"title": "Filed", "document_type_id": str(document_type.id)}
    )
    assert create.status_code == 201
    created = create.json()["data"]
    document = await session.get(Document, UUID(created["id"]))
    assert document is not None
    assert (document.organization_id, document.matter_id, document.file_id) == (
        organization.id,
        matter.id,
        file.id,
    )
    listed = await client.get(path, headers=headers)
    assert [item["id"] for item in listed.json()["data"]] == [created["id"]]
    assert legacy.file_id is None
    update = await client.put(
        f"{path}/{document.id}",
        headers=headers,
        json={"title": "Renamed", "version": created["version"]},
    )
    assert update.status_code == 200 and update.json()["data"]["title"] == "Renamed"
    assert (await client.get(f"{path}/{legacy.id}", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_document_permissions_are_not_substituted_by_file_or_matter_permissions(
    client: AsyncClient, session: AsyncSession
) -> None:
    document_headers, organization = await _headers(
        client, session, "documents:read", "documents:write"
    )
    matter, file, document_type = await _file(session, organization)
    path = f"/api/v1/matters/{matter.id}/files/{file.id}/documents"
    other_headers, _ = await _headers(
        client, session, "files:read", "files:write", "matters:read", "matters:write"
    )
    assert (await client.get(path, headers=other_headers)).status_code == 403
    assert (
        await client.post(
            path,
            headers=other_headers,
            json={"title": "Denied", "document_type_id": str(document_type.id)},
        )
    ).status_code == 403
    assert (
        await client.post(
            path,
            headers=document_headers,
            json={"title": "Allowed", "document_type_id": str(document_type.id)},
        )
    ).status_code == 201
