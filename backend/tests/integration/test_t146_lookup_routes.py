"""T146 API evidence: authenticated read-only discovery of the existing
Matter Type, Matter Status and Document Type vocabularies.

Follows `test_matter_routes.py`/`test_property_routes.py`'s established
pattern exactly: a session-scoped disposable PostgreSQL database built by
the real provenance + bootstrap path, a per-test `get_db`/`get_admin_db`
override, and a real login through `/api/v1/auth/login` to obtain the bearer
token under test.

Covers the six things T146's authorization requires be proven:

- unauthenticated callers cannot use any of the three collections;
- `matters:read` is what Matter Type and Matter Status require, and
  `documents:read` is what Document Type requires -- allowed *and* denied,
  in both directions (neither permission substitutes for the other);
- each response exposes exactly its intended existing selector fields and
  nothing invented (notably no `is_active` on Matter Status);
- results are deterministically ordered by the existing ordering columns;
- `is_active` filtering happens for Matter Type/Document Type and does not
  happen for Matter Status, which has no such column;
- the collections are read-only -- no write verb is mounted for any of them.
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
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)

_PASSWORD = "correct horse battery staple"
_MATTER_TYPES_PATH = "/api/v1/matter-types"
_MATTER_STATUSES_PATH = "/api/v1/matter-statuses"
_DOCUMENT_TYPES_PATH = "/api/v1/document-types"


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t146_lookups")
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


async def _headers(http: AsyncClient, session: AsyncSession, *codes: str) -> dict[str, str]:
    organization = Organization(id=uuid4(), name=f"Org-{uuid4()}")
    user = User(
        email=f"{uuid4()}@example.com",
        full_name="Lookup user",
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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [_MATTER_TYPES_PATH, _MATTER_STATUSES_PATH, _DOCUMENT_TYPES_PATH])
async def test_unauthenticated_callers_cannot_use_the_lookup_collections(
    client: AsyncClient, path: str
) -> None:
    response = await client.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_existing_permissions_are_required_and_never_substituted(
    client: AsyncClient, session: AsyncSession
) -> None:
    """`matters:read` gates the two Matter-owned vocabularies;
    `documents:read` gates Document Type. Neither permission opens the
    other's collection, and no third permission is involved."""
    matter_reader = await _headers(client, session, "matters:read")
    document_reader = await _headers(client, session, "documents:read")
    both = await _headers(client, session, "matters:read", "documents:read")

    assert (await client.get(_MATTER_TYPES_PATH, headers=matter_reader)).status_code == 200
    assert (await client.get(_MATTER_STATUSES_PATH, headers=matter_reader)).status_code == 200
    assert (await client.get(_MATTER_TYPES_PATH, headers=document_reader)).status_code == 403
    assert (await client.get(_MATTER_STATUSES_PATH, headers=document_reader)).status_code == 403

    assert (await client.get(_DOCUMENT_TYPES_PATH, headers=document_reader)).status_code == 200
    assert (await client.get(_DOCUMENT_TYPES_PATH, headers=matter_reader)).status_code == 403

    assert (await client.get(_MATTER_TYPES_PATH, headers=both)).status_code == 200
    assert (await client.get(_DOCUMENT_TYPES_PATH, headers=both)).status_code == 200

    no_permissions = await _headers(client, session)
    assert (await client.get(_MATTER_TYPES_PATH, headers=no_permissions)).status_code == 403
    assert (await client.get(_DOCUMENT_TYPES_PATH, headers=no_permissions)).status_code == 403


@pytest.mark.asyncio
async def test_projections_expose_only_existing_selector_fields(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await _headers(client, session, "matters:read", "documents:read")

    matter_types = (await client.get(_MATTER_TYPES_PATH, headers=headers)).json()["data"]
    matter_statuses = (await client.get(_MATTER_STATUSES_PATH, headers=headers)).json()["data"]
    document_types = (await client.get(_DOCUMENT_TYPES_PATH, headers=headers)).json()["data"]

    assert matter_types and all(
        set(row) == {"id", "code", "name", "is_active"} for row in matter_types
    )
    # Matter Status has no `is_active` column; `is_terminal` is the only state
    # flag it genuinely carries, and nothing else is invented for it.
    assert matter_statuses
    assert all(set(row) == {"id", "code", "name", "is_terminal"} for row in matter_statuses)
    assert document_types
    assert all(set(row) == {"id", "code", "name", "is_active"} for row in document_types)

    seeded_types = (await session.execute(select(MatterType))).scalars().all()
    assert {row["id"] for row in matter_types} == {str(row.id) for row in seeded_types}
    seeded_statuses = (await session.execute(select(MatterStatus))).scalars().all()
    assert {row["id"] for row in matter_statuses} == {str(row.id) for row in seeded_statuses}
    seeded_document_types = (await session.execute(select(DocumentType))).scalars().all()
    assert {row["id"] for row in document_types} == {str(row.id) for row in seeded_document_types}


@pytest.mark.asyncio
async def test_ordering_is_deterministic_on_existing_columns(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers = await _headers(client, session, "matters:read", "documents:read")

    matter_types = (await client.get(_MATTER_TYPES_PATH, headers=headers)).json()["data"]
    matter_statuses = (await client.get(_MATTER_STATUSES_PATH, headers=headers)).json()["data"]
    document_types = (await client.get(_DOCUMENT_TYPES_PATH, headers=headers)).json()["data"]

    assert [row["code"] for row in matter_types] == [
        row.code
        for row in sorted(
            (await session.execute(select(MatterType))).scalars().all(),
            key=lambda row: (row.sort_order, row.code),
        )
    ]
    assert [row["code"] for row in matter_statuses] == [
        row.code
        for row in sorted(
            (await session.execute(select(MatterStatus))).scalars().all(),
            key=lambda row: (row.sort_order, row.code),
        )
    ]
    # `document_types` has no ordering column, so `code` alone orders it.
    assert [row["code"] for row in document_types] == sorted(row["code"] for row in document_types)

    repeat = (await client.get(_MATTER_TYPES_PATH, headers=headers)).json()["data"]
    assert repeat == matter_types


@pytest.mark.asyncio
async def test_active_filtering_applies_only_where_the_column_exists(
    client: AsyncClient, session: AsyncSession
) -> None:
    """`MatterType`/`DocumentType` have a persisted `is_active`, so a
    deactivated row must not be offered as a selectable value. `MatterStatus`
    has no such column, so nothing is filtered there -- the endpoint must
    not be silently hiding terminal statuses from a selector."""
    deactivated_type = MatterType(
        id=uuid4(), code=f"DEACT_{uuid4().hex[:8]}", name="Deactivated", is_active=False
    )
    deactivated_document_type = DocumentType(
        id=uuid4(), code=f"DEACT_{uuid4().hex[:8]}", name="Deactivated", is_active=False
    )
    session.add_all([deactivated_type, deactivated_document_type])
    await session.flush()

    headers = await _headers(client, session, "matters:read", "documents:read")

    matter_types = (await client.get(_MATTER_TYPES_PATH, headers=headers)).json()["data"]
    document_types = (await client.get(_DOCUMENT_TYPES_PATH, headers=headers)).json()["data"]
    matter_statuses = (await client.get(_MATTER_STATUSES_PATH, headers=headers)).json()["data"]

    assert str(deactivated_type.id) not in {row["id"] for row in matter_types}
    assert str(deactivated_document_type.id) not in {row["id"] for row in document_types}
    assert all(row["is_active"] is True for row in matter_types)
    assert all(row["is_active"] is True for row in document_types)

    terminal = next(row for row in matter_statuses if row["code"] == "CLOSED")
    assert terminal["is_terminal"] is True
    assert all({"id", "code", "name", "is_terminal"} == set(row) for row in matter_statuses)
    assert len(matter_statuses) == len(
        (await session.execute(select(MatterStatus))).scalars().all()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [_MATTER_TYPES_PATH, _MATTER_STATUSES_PATH, _DOCUMENT_TYPES_PATH])
@pytest.mark.parametrize("method", ["post", "put", "delete", "patch"])
async def test_lookup_collections_expose_no_write_verb(
    client: AsyncClient, session: AsyncSession, path: str, method: str
) -> None:
    headers = await _headers(client, session, "matters:read", "documents:read", "matters:write")

    if method == "delete":
        response = await client.delete(path, headers=headers)
    else:
        response = await getattr(client, method)(path, json={}, headers=headers)

    assert response.status_code == 405


@pytest.mark.asyncio
async def test_reference_data_is_global_and_tenant_independent(
    client: AsyncClient, session: AsyncSession
) -> None:
    """These are global reference tables -- no `organization_id`, no RLS.
    Two unrelated Organizations therefore see the same rows, and nothing
    here manufactures tenant ownership."""
    first = await _headers(client, session, "matters:read", "documents:read")
    second = await _headers(client, session, "matters:read", "documents:read")

    for path in (_MATTER_TYPES_PATH, _MATTER_STATUSES_PATH, _DOCUMENT_TYPES_PATH):
        assert (await client.get(path, headers=first)).json()["data"] == (
            await client.get(path, headers=second)
        ).json()["data"]
