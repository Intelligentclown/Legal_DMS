"""T177 end-to-end API evidence for the post-conversion office journey.

The test deliberately composes the already-governed APIs instead of bypassing
them with repository writes.  Only the pre-existing Property fixture is seeded
directly: AC-04 is about associating an existing tenant-visible Property.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.errors.exceptions import NotFoundError
from app.application.interfaces.file_storage import FileStorage, StoredFile
from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.database import session as session_module
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.persistence.models.document import DocumentType
from app.infrastructure.persistence.models.identity import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.infrastructure.persistence.models.matter import MatterStatus, MatterType
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.party import Party
from app.infrastructure.persistence.models.property import Property
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)

_PASSWORD = "correct horse battery staple"
_JOURNEY_PERMISSIONS = (
    "enquiries:write",
    "quotations:write",
    "quotations:accept",
    "matters:read",
    "matters:write",
    "properties:read",
    "files:read",
    "files:write",
    "documents:read",
    "documents:write",
)


class MemoryStorage(FileStorage):
    """External storage substitute; database/transaction path remains production code."""

    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    async def save(
        self, path: str, content: bytes, *, content_type: str | None = None
    ) -> StoredFile:
        self.items[path] = content
        return StoredFile(path, len(content), content_type)

    async def read(self, path: str) -> bytes:
        if path not in self.items:
            raise NotFoundError(f"File not found: {path}")
        return self.items[path]

    async def delete(self, path: str) -> None:
        self.items.pop(path, None)

    async def exists(self, path: str) -> bool:
        return path in self.items


@pytest.fixture(scope="session")
def t177_database() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t177_journey")
    try:
        asyncio.run(establish_fresh_installation(url))
        asyncio.run(run_bootstrap(url))
        yield url, name
    finally:
        drop_disposable_database(name)


@pytest.fixture
async def t177_client(
    t177_database: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage], None]:
    engine = create_async_engine(t177_database[0])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = MemoryStorage()
    monkeypatch.setattr(session_module, "get_app_session_factory", lambda: factory)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)
    container.override(FileStorage, storage)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, factory, storage
    finally:
        configure_container()
        await engine.dispose()


async def _credentials(
    factory: async_sessionmaker[AsyncSession], *permissions: str
) -> tuple[dict[str, str], UUID, UUID]:
    async with factory() as db:
        organization = Organization(id=uuid4(), name=f"T177-{uuid4()}")
        user = User(
            email=f"{uuid4()}@example.test",
            full_name="T177 Operator",
            password_hash=hash_password(_PASSWORD),
            organization_id=organization.id,
            is_active=True,
        )
        party = Party(
            organization_id=organization.id,
            party_type="individual",
            display_name="Canonical T177 Client",
            primary_phone="5551234567",
        )
        db.add(organization)
        await db.flush()
        db.add_all([user, party])
        await db.flush()
        role = Role(name=f"T177-{uuid4()}")
        db.add(role)
        await db.flush()
        for code in permissions:
            permission = (
                await db.execute(select(Permission).where(Permission.code == code))
            ).scalar_one()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()
        return {"email": user.email, "password": _PASSWORD}, organization.id, party.id


async def _headers(client: AsyncClient, credentials: dict[str, str]) -> dict[str, str]:
    login = await client.post("/api/v1/auth/login", json=credentials)
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_t177_operator_completes_post_conversion_office_journey(
    t177_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
) -> None:
    """Exercise AC-01..08 through the canonical conversion and office APIs."""
    client, factory, storage = t177_client
    credentials, organization_id, party_id = await _credentials(factory, *_JOURNEY_PERMISSIONS)
    headers = await _headers(client, credentials)

    enquiry = await client.post(
        "/api/v1/enquiries", headers=headers, json={"party_id": str(party_id)}
    )
    assert enquiry.status_code == 201
    enquiry_id = enquiry.json()["data"]["id"]
    quotation = await client.post(f"/api/v1/enquiries/{enquiry_id}/quotations", headers=headers)
    assert quotation.status_code == 201
    quotation_id = quotation.json()["data"]["id"]
    revision = await client.post(
        f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions",
        headers=headers,
        json={"proposal_snapshot": {"scope": "T177 journey"}},
    )
    assert revision.status_code == 201
    revision_id = revision.json()["data"]["id"]
    assert (
        await client.post(
            f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/issue",
            headers=headers,
        )
    ).status_code == 200

    async with factory() as db:
        matter_type_id = (await db.execute(select(MatterType.id).limit(1))).scalar_one()
        matter_status_id = (await db.execute(select(MatterStatus.id).limit(1))).scalar_one()
    matter_payload = {
        "matter_number": f"T177-{uuid4()}",
        "matter_type_id": str(matter_type_id),
        "matter_status_id": str(matter_status_id),
        "title": "T177 converted matter",
        "opened_at": datetime.now(UTC).isoformat(),
    }
    accept_path = (
        f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/accept"
    )
    accepted = await client.post(
        accept_path,
        headers={**headers, "Idempotency-Key": "t177-convert-once"},
        json=matter_payload,
    )
    assert accepted.status_code == 201
    accepted_data = accepted.json()["data"]
    matter_id = accepted_data["matter_id"]
    replay = await client.post(
        accept_path,
        headers={**headers, "Idempotency-Key": "t177-convert-once"},
        json=matter_payload,
    )
    assert replay.status_code == 200 and replay.json()["data"] == {
        **accepted_data,
        "replayed": True,
    }

    reopened_matter = await client.get(f"/api/v1/matters/{matter_id}", headers=headers)
    assert reopened_matter.status_code == 200
    assert reopened_matter.json()["data"]["participants"] == [
        {"party_id": str(party_id), "role": "client"}
    ]

    async with factory() as db:
        property_ = Property(
            id=uuid4(),
            organization_id=organization_id,
            property_type="residential",
            survey_number=f"T177-{uuid4()}",
        )
        document_type_id = (await db.execute(select(DocumentType.id).limit(1))).scalar_one()
        db.add(property_)
        await db.commit()
    property_path = f"/api/v1/matters/{matter_id}/properties"
    association = await client.post(
        property_path, headers=headers, json={"property_id": str(property_.id)}
    )
    assert association.status_code == 201 and association.json()["data"]["id"] == str(property_.id)
    duplicate = await client.post(
        property_path, headers=headers, json={"property_id": str(property_.id)}
    )
    assert duplicate.status_code == 200
    listed_properties = await client.get(property_path, headers=headers)
    assert [item["id"] for item in listed_properties.json()["data"]] == [str(property_.id)]

    files_path = f"/api/v1/matters/{matter_id}/files"
    created_file = await client.post(
        files_path, headers=headers, json={"title": "T177 operator file"}
    )
    assert created_file.status_code == 201
    file_id = created_file.json()["data"]["id"]
    reopened_file = await client.get(f"{files_path}/{file_id}", headers=headers)
    assert (
        reopened_file.status_code == 200 and reopened_file.json()["data"]["matter_id"] == matter_id
    )

    documents_path = f"{files_path}/{file_id}/documents"
    created_document = await client.post(
        documents_path,
        headers=headers,
        json={"document_type_id": str(document_type_id), "title": "T177 evidence document"},
    )
    assert created_document.status_code == 201
    document_id = created_document.json()["data"]["id"]
    assert (await client.get(f"{documents_path}/{document_id}", headers=headers)).status_code == 200

    version_path = f"{documents_path}/{document_id}/versions"
    content = b"T177 office journey evidence: immutable bytes\n"
    version = await client.post(
        version_path,
        headers={
            **headers,
            "X-Filename": "t177-evidence.txt",
            "Idempotency-Key": "t177-version-1",
            "Content-Type": "text/plain",
        },
        content=content,
    )
    assert version.status_code == 201
    version_id = version.json()["data"]["id"]
    downloaded = await client.get(f"{version_path}/{version_id}/content", headers=headers)
    assert downloaded.status_code == 200 and downloaded.content == content
    assert downloaded.headers["content-type"].startswith("text/plain")
    assert 'filename="t177-evidence.txt"' in downloaded.headers["content-disposition"]
    assert list(storage.items.values()) == [content]

    other_credentials, _other_organization_id, _other_party_id = await _credentials(
        factory, *_JOURNEY_PERMISSIONS
    )
    other_headers = await _headers(client, other_credentials)
    assert (
        await client.get(f"/api/v1/matters/{matter_id}", headers=other_headers)
    ).status_code == 404
    assert (
        await client.get(f"{version_path}/{version_id}/content", headers=other_headers)
    ).status_code == 404
    limited_credentials, _limited_organization_id, _limited_party_id = await _credentials(
        factory, "matters:read"
    )
    limited_headers = await _headers(client, limited_credentials)
    assert (await client.get(files_path, headers=limited_headers)).status_code == 403
