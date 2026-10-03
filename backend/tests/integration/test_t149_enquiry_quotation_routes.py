"""T149/T152 route, tenant, issuance and PostgreSQL conversion evidence."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.database import session as session_module
from app.infrastructure.persistence.models.client import Client
from app.infrastructure.persistence.models.enquiry import Acceptance
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
from app.infrastructure.persistence.models.party import MatterParty, Party
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)


@pytest.fixture(scope="session")
def t149_database() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t149")
    try:
        asyncio.run(establish_fresh_installation(url))
        asyncio.run(run_bootstrap(url))
        yield url, name
    finally:
        drop_disposable_database(name)


@pytest.fixture
async def t149_client(
    t149_database: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[tuple[AsyncClient, async_sessionmaker[AsyncSession]], None]:
    engine = create_async_engine(t149_database[0])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(session_module, "get_app_session_factory", lambda: factory)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, factory
    finally:
        await engine.dispose()


async def _credentials(
    factory: async_sessionmaker[AsyncSession], *permissions: str
) -> tuple[dict[str, str], UUID, UUID]:
    async with factory() as db:
        org = Organization(id=uuid4(), name=f"T149-{uuid4()}")
        user = User(
            email=f"{uuid4()}@example.test",
            full_name="T149 User",
            password_hash=hash_password("correct horse battery staple"),
            organization_id=org.id,
            is_active=True,
        )
        db.add(org)
        await db.flush()
        party = Party(
            organization_id=org.id,
            party_type="individual",
            display_name="Existing Party",
            primary_phone="5551234567",
        )
        db.add_all([user, party])
        await db.flush()
        role = Role(name=f"T149-{uuid4()}")
        db.add(role)
        await db.flush()
        for code in permissions:
            permission = (
                await db.execute(select(Permission).where(Permission.code == code))
            ).scalar_one()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()
        return {"email": user.email, "password": "correct horse battery staple"}, org.id, party.id


async def _token(client: AsyncClient, credentials: dict[str, str]) -> str:
    response = await client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_t149_routes_tenant_boundary_pagination_and_issuance(
    t149_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, factory = t149_client
    credentials, _organization, party_id = await _credentials(
        factory, "enquiries:read", "enquiries:write", "quotations:read", "quotations:write"
    )
    token = await _token(client, credentials)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/enquiries", headers=headers, json={"prospect_display_name": "Prospect"}
    )
    assert created.status_code == 201
    enquiry_id = created.json()["data"]["id"]
    assert (
        await client.put(
            f"/api/v1/enquiries/{enquiry_id}/party",
            headers=headers,
            json={"party_id": str(party_id)},
        )
    ).status_code == 200
    listing = await client.get("/api/v1/enquiries?page_size=1", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["pagination"]["total"] == 1
    quotation = await client.post(f"/api/v1/enquiries/{enquiry_id}/quotations", headers=headers)
    assert quotation.status_code == 201
    quotation_id = quotation.json()["data"]["id"]

    async def revision(scope: str):
        return await client.post(
            f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions",
            headers=headers,
            json={"proposal_snapshot": {"scope": scope}},
        )

    left, right = await asyncio.gather(revision("left"), revision("right"))
    assert {left.status_code, right.status_code} == {201}
    assert sorted([left.json()["data"]["ordinal"], right.json()["data"]["ordinal"]]) == [1, 2]
    revision_id = left.json()["data"]["id"]
    issued = await client.post(
        f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/issue",
        headers=headers,
    )
    assert issued.status_code == 200
    assert issued.json()["data"]["issued_by"] is not None
    assert (
        await client.post(
            f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/issue",
            headers=headers,
        )
    ).status_code == 409

    other_credentials, _other_org, _ = await _credentials(
        factory, "enquiries:read", "quotations:read"
    )
    other_headers = {"Authorization": f"Bearer {await _token(client, other_credentials)}"}
    assert (
        await client.get(f"/api/v1/enquiries/{enquiry_id}", headers=other_headers)
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}", headers=other_headers
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_t149_permissions_are_narrow_and_do_not_consume_accept(
    t149_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, factory = t149_client
    credentials, _organization, _party = await _credentials(factory, "quotations:accept")
    headers = {"Authorization": f"Bearer {await _token(client, credentials)}"}
    assert (await client.get("/api/v1/enquiries", headers=headers)).status_code == 403
    assert (
        await client.post("/api/v1/enquiries", headers=headers, json={"prospect_display_name": "P"})
    ).status_code == 403


async def _t152_setup(
    client: AsyncClient,
    factory: async_sessionmaker[AsyncSession],
    permissions: tuple[str, ...],
    *,
    party_linked: bool = True,
) -> tuple[dict[str, str], UUID, UUID, UUID, UUID, dict[str, object]]:
    credentials, organization_id, party_id = await _credentials(factory, *permissions)
    headers = {"Authorization": f"Bearer {await _token(client, credentials)}"}
    enquiry_payload = (
        {"party_id": str(party_id)} if party_linked else {"prospect_display_name": "P"}
    )
    enquiry = await client.post("/api/v1/enquiries", headers=headers, json=enquiry_payload)
    assert enquiry.status_code == 201
    enquiry_id = UUID(enquiry.json()["data"]["id"])
    quotation = await client.post(f"/api/v1/enquiries/{enquiry_id}/quotations", headers=headers)
    assert quotation.status_code == 201
    quotation_id = UUID(quotation.json()["data"]["id"])
    revision = await client.post(
        f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions",
        headers=headers,
        json={"proposal_snapshot": {"scope": "exact evidence"}},
    )
    assert revision.status_code == 201
    revision_id = UUID(revision.json()["data"]["id"])
    issued = await client.post(
        f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/issue",
        headers=headers,
    )
    assert issued.status_code == 200
    async with factory() as db:
        matter_type_id = (await db.execute(select(MatterType.id).limit(1))).scalar_one()
        matter_status_id = (await db.execute(select(MatterStatus.id).limit(1))).scalar_one()
    matter = {
        "matter_number": f"T152-{uuid4()}",
        "matter_type_id": str(matter_type_id),
        "matter_status_id": str(matter_status_id),
        "title": "Converted matter",
        "opened_at": datetime.now(UTC).isoformat(),
    }
    return (
        headers,
        organization_id,
        party_id,
        enquiry_id,
        quotation_id,
        {
            "revision_id": revision_id,
            "matter": matter,
        },
    )


def _accept_path(enquiry_id: UUID, quotation_id: UUID, revision_id: UUID) -> str:
    return (
        f"/api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions/"
        f"{revision_id}/accept"
    )


@pytest.mark.asyncio
async def test_t152_accepts_exact_issued_revision_creates_party_canonical_matter_and_replays(
    t149_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, factory = t149_client
    headers, organization_id, party_id, enquiry_id, quotation_id, values = await _t152_setup(
        client,
        factory,
        ("enquiries:write", "quotations:write", "quotations:accept", "matters:write"),
    )
    revision_id, matter = values["revision_id"], values["matter"]
    path = _accept_path(enquiry_id, quotation_id, revision_id)
    accepted = await client.post(path, headers={**headers, "Idempotency-Key": "same"}, json=matter)
    assert accepted.status_code == 201
    data = accepted.json()["data"]
    assert data["replayed"] is False
    replay = await client.post(path, headers={**headers, "Idempotency-Key": "same"}, json=matter)
    assert replay.status_code == 200
    assert replay.json()["data"] == {**data, "replayed": True}
    changed = {**matter, "title": "changed"}
    assert (
        await client.post(path, headers={**headers, "Idempotency-Key": "same"}, json=changed)
    ).status_code == 409
    assert (
        await client.post(path, headers={**headers, "Idempotency-Key": "different"}, json=matter)
    ).status_code == 409

    other_credentials, _other_org, _other_party = await _credentials(
        factory, "quotations:accept", "matters:write"
    )
    other_headers = {"Authorization": f"Bearer {await _token(client, other_credentials)}"}
    assert (
        await client.post(
            path, headers={**other_headers, "Idempotency-Key": "foreign"}, json=matter
        )
    ).status_code == 404

    async with factory() as db:
        acceptance = (
            await db.execute(select(Acceptance).where(Acceptance.enquiry_id == enquiry_id))
        ).scalar_one()
        assert acceptance.quotation_revision_id == revision_id
        assert acceptance.quotation_id == quotation_id
        converted = await db.get(Matter, acceptance.matter_id)
        assert converted is not None and converted.client_id is None
        participants = (
            (await db.execute(select(MatterParty).where(MatterParty.matter_id == converted.id)))
            .scalars()
            .all()
        )
        assert [(row.party_id, row.role) for row in participants] == [(party_id, "client")]
        assert (
            await db.execute(
                select(func.count())
                .select_from(Client)
                .where(Client.organization_id == organization_id)
            )
        ).scalar_one() == 0
        assert (
            await db.execute(
                select(func.count())
                .select_from(File)
                .where(File.organization_id == organization_id)
            )
        ).scalar_one() == 0


@pytest.mark.asyncio
async def test_t152_requires_party_and_both_authorities_and_serializes_concurrent_conversion(
    t149_client: tuple[AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, factory = t149_client
    # A prospect-only enquiry is intentionally not silently turned into a Party.
    headers, _org, _party, enquiry_id, quotation_id, values = await _t152_setup(
        client,
        factory,
        ("enquiries:write", "quotations:write", "quotations:accept", "matters:write"),
        party_linked=False,
    )
    path = _accept_path(enquiry_id, quotation_id, values["revision_id"])
    assert (
        await client.post(
            path, headers={**headers, "Idempotency-Key": "no-party"}, json=values["matter"]
        )
    ).status_code == 422

    # Acceptance alone cannot create a Matter.
    limited, _org, _party, enquiry_id, quotation_id, values = await _t152_setup(
        client, factory, ("enquiries:write", "quotations:write", "quotations:accept")
    )
    path = _accept_path(enquiry_id, quotation_id, values["revision_id"])
    assert (
        await client.post(
            path, headers={**limited, "Idempotency-Key": "missing-matter"}, json=values["matter"]
        )
    ).status_code == 403

    headers, _org, _party, enquiry_id, quotation_id, values = await _t152_setup(
        client,
        factory,
        ("enquiries:write", "quotations:write", "quotations:accept", "matters:write"),
    )
    path = _accept_path(enquiry_id, quotation_id, values["revision_id"])

    async def convert(key: str):
        return await client.post(
            path, headers={**headers, "Idempotency-Key": key}, json=values["matter"]
        )

    left, right = await asyncio.gather(convert("left"), convert("right"))
    assert sorted([left.status_code, right.status_code]) == [201, 409]
    async with factory() as db:
        assert (
            await db.execute(
                select(func.count())
                .select_from(Acceptance)
                .where(Acceptance.enquiry_id == enquiry_id)
            )
        ).scalar_one() == 1
        assert (
            await db.execute(
                select(func.count()).select_from(Matter).where(Matter.organization_id == _org)
            )
        ).scalar_one() == 1
