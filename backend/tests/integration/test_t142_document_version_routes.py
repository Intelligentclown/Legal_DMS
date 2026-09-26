"""T142 API evidence using the production transaction dependency and PostgreSQL."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.errors.exceptions import NotFoundError
from app.application.interfaces.file_storage import FileStorage, StoredFile
from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.database import session as session_module
from app.infrastructure.database.transaction_outcome import TransactionOutcome
from app.infrastructure.di.container import configure_container, container
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
from app.infrastructure.persistence.sqlalchemy_document_version_repository import (
    SqlAlchemyDocumentVersionRepository,
)
from app.infrastructure.persistence.sqlalchemy_user_repository import SqlAlchemyUserRepository
from app.infrastructure.security.password_hasher import hash_password
from app.main import app
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)


class MemoryStorage(FileStorage):
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.fail_delete = False

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
        self.deleted.append(path)
        if self.fail_delete:
            raise RuntimeError("simulated storage delete failure")
        self.items.pop(path, None)

    async def exists(self, path: str) -> bool:
        return path in self.items


class RecordingAsgiApp:
    def __init__(self, wrapped, events: list[str]) -> None:
        self._wrapped, self._events = wrapped, events

    async def __call__(self, scope, receive, send) -> None:
        async def record(message) -> None:
            if message["type"] == "http.response.start":
                self._events.append("response_start")
            await send(message)

        await self._wrapped(scope, receive, record)


@pytest.fixture(scope="session")
def disposable_db() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t142")
    try:
        asyncio.run(establish_fresh_installation(url))
        asyncio.run(run_bootstrap(url))
        yield url, name
    finally:
        drop_disposable_database(name)


@pytest.fixture
async def production_client(
    disposable_db: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage], None]:
    """Use production ``get_db``; only its database factory and the external blob port vary."""
    database_url, _ = disposable_db
    engine = create_async_engine(database_url)
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


async def _seed_authorized_document(
    factory: async_sessionmaker[AsyncSession], *permissions: str
) -> tuple[dict[str, str], UUID, UUID, UUID]:
    async with factory() as db:
        organization = Organization(id=uuid4(), name=f"T142-{uuid4()}")
        user = User(
            email=f"{uuid4()}@example.test",
            full_name="T142 User",
            password_hash=hash_password("correct horse battery staple"),
            organization_id=organization.id,
            is_active=True,
        )
        db.add(organization)
        await db.flush()
        db.add(user)
        await db.flush()
        role = Role(name=f"T142-{uuid4()}")
        db.add(role)
        await db.flush()
        for code in permissions:
            permission = (
                await db.execute(select(Permission).where(Permission.code == code))
            ).scalar_one()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.add(UserRole(user_id=user.id, role_id=role.id))
        matter_type = (await db.execute(select(MatterType).limit(1))).scalar_one()
        matter_status = (await db.execute(select(MatterStatus).limit(1))).scalar_one()
        document_type = (await db.execute(select(DocumentType).limit(1))).scalar_one()
        matter = Matter(
            id=uuid4(),
            organization_id=organization.id,
            matter_number=f"M-{uuid4()}",
            matter_type_id=matter_type.id,
            matter_status_id=matter_status.id,
            title="Matter",
            opened_at=datetime.now(UTC),
        )
        file = File(
            id=uuid4(),
            organization_id=organization.id,
            matter_id=matter.id,
            file_number=1,
            title="File",
        )
        document = Document(
            id=uuid4(),
            organization_id=organization.id,
            matter_id=matter.id,
            file_id=file.id,
            document_type_id=document_type.id,
            title="Document",
        )
        db.add(matter)
        await db.flush()
        db.add(file)
        await db.flush()
        db.add(document)
        await db.commit()
        return (
            {"email": user.email, "password": "correct horse battery staple"},
            matter.id,
            file.id,
            document.id,
        )


@pytest.mark.asyncio
async def test_canonical_version_routes_use_production_get_db_and_commit_before_reads(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
) -> None:
    client, factory, storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    assert login.status_code == 200
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Filename": "evidence.txt",
        "Idempotency-Key": "t142-route-key",
        "Content-Type": "text/plain",
    }
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    created = await client.post(path, headers=headers, content=b"exact bytes")
    assert created.status_code == 201
    version_id = UUID(created.json()["data"]["id"])
    assert created.json()["data"]["version_number"] == 1
    assert len(storage.items) == 1

    replay = await client.post(path, headers=headers, content=b"exact bytes")
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == str(version_id)
    conflict = await client.post(path, headers=headers, content=b"different bytes")
    assert conflict.status_code == 409

    # A new, real application request sees the committed result through RLS.
    listed = await client.get(path, headers={"Authorization": headers["Authorization"]})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]] == [str(version_id)]
    latest = await client.get(f"{path}/latest", headers={"Authorization": headers["Authorization"]})
    assert latest.status_code == 200 and latest.json()["data"]["id"] == str(version_id)
    fetched = await client.get(
        f"{path}/{version_id}", headers={"Authorization": headers["Authorization"]}
    )
    assert fetched.status_code == 200 and fetched.json()["data"]["version_number"] == 1
    downloaded = await client.get(
        f"{path}/{version_id}/content", headers={"Authorization": headers["Authorization"]}
    )
    assert downloaded.status_code == 200 and downloaded.content == b"exact bytes"


@pytest.mark.asyncio
async def test_same_document_concurrency_serializes_ordinals_and_idempotency(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
) -> None:
    client, factory, _storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    token = login.json()["access_token"]
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"

    async def create(key: str, content: bytes):
        return await client.post(
            path,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Filename": f"{key}.txt",
                "Idempotency-Key": key,
                "Content-Type": "text/plain",
            },
            content=content,
        )

    first, second = await asyncio.gather(create("one", b"one"), create("two", b"two"))
    assert {first.status_code, second.status_code} == {201}
    assert sorted(
        (first.json()["data"]["version_number"], second.json()["data"]["version_number"])
    ) == [1, 2]

    left, right = await asyncio.gather(create("same", b"same"), create("same", b"same"))
    assert left.status_code == right.status_code == 201
    assert left.json()["data"]["id"] == right.json()["data"]["id"]
    assert left.json()["data"]["version_number"] == 3


@pytest.mark.asyncio
async def test_different_documents_allocate_independently(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
) -> None:
    client, factory, _storage = production_client
    first_credentials, first_matter, first_file, first_document = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    second_credentials, second_matter, second_file, second_document = (
        await _seed_authorized_document(factory, "documents:read", "documents:write")
    )

    async def upload(
        credentials: dict[str, str], matter_id: UUID, file_id: UUID, document_id: UUID
    ):
        login = await client.post("/api/v1/auth/login", json=credentials)
        return await client.post(
            f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions",
            headers={
                "Authorization": f"Bearer {login.json()['access_token']}",
                "X-Filename": "independent.txt",
                "Idempotency-Key": str(document_id),
                "Content-Type": "text/plain",
            },
            content=b"independent",
        )

    first, second = await asyncio.gather(
        upload(first_credentials, first_matter, first_file, first_document),
        upload(second_credentials, second_matter, second_file, second_document),
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["data"]["version_number"] == second.json()["data"]["version_number"] == 1


@pytest.mark.asyncio
async def test_cross_organization_document_versions_are_non_enumerating(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
) -> None:
    client, factory, _storage = production_client
    owner_credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    other_credentials, _other_matter, _other_file, _other_document = (
        await _seed_authorized_document(factory, "documents:read", "documents:write")
    )
    owner_login = await client.post("/api/v1/auth/login", json=owner_credentials)
    other_login = await client.post("/api/v1/auth/login", json=other_credentials)
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    owner_headers = {
        "Authorization": f"Bearer {owner_login.json()['access_token']}",
        "X-Filename": "private.txt",
        "Content-Type": "text/plain",
    }
    created = await client.post(path, headers=owner_headers, content=b"private")
    assert created.status_code == 201
    version_id = created.json()["data"]["id"]
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    assert (await client.get(path, headers=other_headers)).status_code == 404
    assert (await client.get(f"{path}/{version_id}", headers=other_headers)).status_code == 404
    assert (
        await client.get(f"{path}/{version_id}/content", headers=other_headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_confirmed_commit_finalizes_before_success_response_start(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory, _storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    events: list[str] = []
    original_finalize = session_module._finalize_outcome

    async def record_finalize(context, outcome) -> None:
        events.append(str(outcome))
        await original_finalize(context, outcome)

    monkeypatch.setattr(session_module, "_finalize_outcome", record_finalize)
    async with AsyncClient(
        transport=ASGITransport(app=RecordingAsgiApp(app, events)), base_url="http://test"
    ) as recorder:
        response = await recorder.post(
            f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions",
            headers={
                "Authorization": f"Bearer {login.json()['access_token']}",
                "X-Filename": "ordering.txt",
                "Content-Type": "text/plain",
            },
            content=b"ordering",
        )
    assert response.status_code == 201
    assert events.index(str(TransactionOutcome.CONFIRMED_COMMIT)) < events.index("response_start")


@pytest.mark.asyncio
async def test_uncertain_commit_suppresses_compensation_and_reconciles_retry(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory, storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    events: list[str] = []
    original_finalize = session_module._finalize_outcome

    class CommitThenDisconnectSession(AsyncSession):
        async def commit(self) -> None:
            await super().commit()
            raise ConnectionError("simulated lost commit acknowledgement")

    async def record_finalize(context, outcome) -> None:
        events.append(str(outcome))
        await original_finalize(context, outcome)

    monkeypatch.setattr(session_module, "_finalize_outcome", record_finalize)
    fault_factory = async_sessionmaker(
        factory.kw["bind"], class_=CommitThenDisconnectSession, expire_on_commit=False
    )
    monkeypatch.setattr(session_module, "get_app_session_factory", lambda: fault_factory)
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Filename": "uncertain.txt",
        "Idempotency-Key": "uncertain-key",
        "Content-Type": "text/plain",
    }
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    async with AsyncClient(
        transport=ASGITransport(app=RecordingAsgiApp(app, events), raise_app_exceptions=False),
        base_url="http://test",
    ) as recorder:
        uncertain = await recorder.post(path, headers=headers, content=b"uncertain")
    assert uncertain.status_code == 500
    assert events.index(str(TransactionOutcome.COMMIT_OUTCOME_UNCERTAIN)) < events.index(
        "response_start"
    )
    assert len(storage.items) == 1

    monkeypatch.setattr(session_module, "get_app_session_factory", lambda: factory)
    retry = await client.post(path, headers=headers, content=b"uncertain")
    assert retry.status_code == 201
    assert retry.json()["data"]["version_number"] == 1
    assert len(storage.items) == 1


@pytest.mark.asyncio
async def test_definitive_precommit_failure_compensates_before_response_start(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory, storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    events: list[str] = []
    original_finalize = session_module._finalize_outcome

    async def fail_add(self, storage_record, version, key) -> None:
        raise RuntimeError("simulated definitive persistence failure")

    async def record_finalize(context, outcome) -> None:
        events.append(str(outcome))
        await original_finalize(context, outcome)

    monkeypatch.setattr(SqlAlchemyDocumentVersionRepository, "add", fail_add)
    monkeypatch.setattr(session_module, "_finalize_outcome", record_finalize)
    async with AsyncClient(
        transport=ASGITransport(app=RecordingAsgiApp(app, events), raise_app_exceptions=False),
        base_url="http://test",
    ) as recorder:
        response = await recorder.post(
            f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions",
            headers={
                "Authorization": f"Bearer {login.json()['access_token']}",
                "X-Filename": "rollback.txt",
                "Content-Type": "text/plain",
            },
            content=b"rollback",
        )
    assert response.status_code == 500
    assert events.index(str(TransactionOutcome.DEFINITIVE_NON_COMMIT)) < events.index(
        "response_start"
    )
    assert storage.items == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("replacement", [None, b"short", b"tampered-length"])
async def test_download_fails_closed_for_missing_or_corrupt_blob(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
    replacement: bytes | None,
) -> None:
    client, factory, storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Filename": "integrity.txt",
        "Content-Type": "text/plain",
    }
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    created = await client.post(path, headers=headers, content=b"expected bytes")
    assert created.status_code == 201
    stored_path = next(iter(storage.items))
    if replacement is None:
        storage.items.pop(stored_path)
    else:
        storage.items[stored_path] = replacement
    failed = await client.get(f"{path}/{created.json()['data']['id']}/content", headers=headers)
    assert failed.status_code >= 400


@pytest.mark.asyncio
async def test_compensation_delete_failure_preserves_primary_failure(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory, storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)

    async def fail_add(self, storage_record, version, key) -> None:
        raise RuntimeError("primary persistence failure")

    storage.fail_delete = True
    monkeypatch.setattr(SqlAlchemyDocumentVersionRepository, "add", fail_add)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as error_client:
        response = await error_client.post(
            f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions",
            headers={
                "Authorization": f"Bearer {login.json()['access_token']}",
                "X-Filename": "cleanup.txt",
                "Content-Type": "text/plain",
            },
            content=b"cleanup",
        )
    assert response.status_code == 500
    assert storage.deleted
    assert len(storage.items) == 1


@pytest.mark.asyncio
async def test_t142_uses_one_application_session_with_tenant_guc_through_commit(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory, _storage = production_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    seen: dict[str, object] = {}
    original_set_org = SqlAlchemyUserRepository.set_current_organization_context
    original_add = SqlAlchemyDocumentVersionRepository.add

    class TrackingSession(AsyncSession):
        async def commit(self) -> None:
            seen["commit_session"] = id(self)
            await super().commit()

    async def record_set_org(self, organization_id) -> None:
        seen["auth_session"] = id(self._session)
        await original_set_org(self, organization_id)
        seen["auth_guc"] = (
            await self._session.execute(
                text("SELECT current_setting('app.current_organization_id', true)")
            )
        ).scalar_one()

    async def record_add(self, storage_record, version, key) -> None:
        seen["persistence_session"] = id(self._session)
        seen["persistence_guc"] = (
            await self._session.execute(
                text("SELECT current_setting('app.current_organization_id', true)")
            )
        ).scalar_one()
        await original_add(self, storage_record, version, key)

    tracking_factory = async_sessionmaker(
        factory.kw["bind"], class_=TrackingSession, expire_on_commit=False
    )
    monkeypatch.setattr(session_module, "get_app_session_factory", lambda: tracking_factory)
    monkeypatch.setattr(
        SqlAlchemyUserRepository, "set_current_organization_context", record_set_org
    )
    monkeypatch.setattr(SqlAlchemyDocumentVersionRepository, "add", record_add)
    response = await client.post(
        f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions",
        headers={
            "Authorization": f"Bearer {login.json()['access_token']}",
            "X-Filename": "tenant.txt",
            "Content-Type": "text/plain",
        },
        content=b"tenant",
    )
    assert response.status_code == 201
    assert seen["auth_session"] == seen["persistence_session"] == seen["commit_session"]
    assert seen["auth_guc"] == seen["persistence_guc"]
    async with factory() as db:
        document = await db.get(Document, document_id)
        assert document is not None
        assert seen["auth_guc"] == str(document.organization_id)


@pytest.mark.asyncio
async def test_rbac_hierarchy_and_legacy_fileless_document_rejections(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
) -> None:
    client, factory, _storage = production_client
    read_credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read"
    )
    write_credentials, _matter, _file, _document = await _seed_authorized_document(
        factory, "documents:write"
    )
    read_login = await client.post("/api/v1/auth/login", json=read_credentials)
    write_login = await client.post("/api/v1/auth/login", json=write_credentials)
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    read_headers = {
        "Authorization": f"Bearer {read_login.json()['access_token']}",
        "X-Filename": "denied.txt",
        "Content-Type": "text/plain",
    }
    write_headers = {"Authorization": f"Bearer {write_login.json()['access_token']}"}
    assert (await client.post(path, headers=read_headers, content=b"denied")).status_code == 403
    assert (await client.get(path, headers=write_headers)).status_code == 403
    assert (
        await client.get(path.replace(str(matter_id), str(uuid4())), headers=read_headers)
    ).status_code == 404
    assert (
        await client.get(path.replace(str(file_id), str(uuid4())), headers=read_headers)
    ).status_code == 404
    assert (
        await client.get(path.replace(str(document_id), str(uuid4())), headers=read_headers)
    ).status_code == 404

    async with factory() as db:
        document = await db.get(Document, document_id)
        assert document is not None
        legacy = Document(
            id=uuid4(),
            organization_id=document.organization_id,
            matter_id=document.matter_id,
            file_id=None,
            document_type_id=document.document_type_id,
            title="Legacy unfiled",
        )
        db.add(legacy)
        await db.commit()
    legacy_path = path.replace(str(document_id), str(legacy.id))
    assert (await client.get(legacy_path, headers=read_headers)).status_code == 404


@pytest.mark.asyncio
async def test_cancellation_during_commit_is_uncertain_and_never_compensates(
    production_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], MemoryStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, factory, _storage = production_client
    calls: list[str] = []

    class CommitThenCancelSession(AsyncSession):
        async def commit(self) -> None:
            await super().commit()
            raise asyncio.CancelledError()

    cancel_factory = async_sessionmaker(
        factory.kw["bind"], class_=CommitThenCancelSession, expire_on_commit=False
    )
    monkeypatch.setattr(session_module, "get_app_session_factory", lambda: cancel_factory)
    dependency = session_module.get_db()
    session = await anext(dependency)
    context = session.info[session_module._OUTCOME_CONTEXT_KEY]

    async def compensation() -> None:
        calls.append("delete")

    context.register(compensation)
    with pytest.raises(asyncio.CancelledError):
        await anext(dependency)
    assert context.outcome is TransactionOutcome.COMMIT_OUTCOME_UNCERTAIN
    assert calls == []
