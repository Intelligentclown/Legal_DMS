"""T182 real-filesystem evidence for DocumentVersion operations."""

from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import subprocess
import sys
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient, HTTPError
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.interfaces.file_storage import FileStorage
from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from app.infrastructure.cli.operational_fresh_bootstrap import run_bootstrap
from app.infrastructure.database import session as session_module
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.persistence.models.document import (
    DocumentVersion,
    DocumentVersionIdempotencyKey,
)
from app.infrastructure.persistence.models.storage import FileStorageRecord
from app.infrastructure.persistence.sqlalchemy_document_version_repository import (
    SqlAlchemyDocumentVersionRepository,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage
from app.main import app
from tests.integration.test_t142_document_version_routes import _seed_authorized_document
from tests.support.synthetic_migration import (
    drop_disposable_database,
    provision_empty_disposable_database,
)


@pytest.fixture(scope="session")
def t182_database() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t182_physical")
    try:
        asyncio.run(establish_fresh_installation(url))
        asyncio.run(run_bootstrap(url))
        yield url, name
    finally:
        drop_disposable_database(name)


@pytest.fixture
async def physical_client(
    t182_database: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[
    tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path], None
]:
    engine = create_async_engine(t182_database[0])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    root = tmp_path / "physical-storage"
    storage = LocalFileStorage(root)
    monkeypatch.setattr(session_module, "get_app_session_factory", lambda: factory)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)
    container.override(FileStorage, storage)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield client, factory, storage, root
    finally:
        configure_container()
        await engine.dispose()


async def _login_and_path(client: AsyncClient, factory: async_sessionmaker[AsyncSession]):
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    login = await client.post("/api/v1/auth/login", json=credentials)
    assert login.status_code == 200
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, path


def _available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


async def _wait_for_service(url: str, process: subprocess.Popen[object]) -> None:
    async with AsyncClient(base_url=url) as client:
        for _ in range(50):
            if process.poll() is not None:
                raise RuntimeError("T182 restart-test service stopped during startup")
            try:
                if (await client.get("/api/v1/health")).status_code == 200:
                    return
            except HTTPError:
                pass
            await asyncio.sleep(0.1)
    raise RuntimeError("T182 restart-test service did not become ready")


@pytest.mark.asyncio
async def test_t182_physical_upload_integrity_and_idempotency_conflict(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
) -> None:
    client, factory, _storage, root = physical_client
    headers, path = await _login_and_path(client, factory)
    payload = b"T182 physical bytes\x00\xff"
    upload_headers = {
        **headers,
        "X-Filename": "evidence.bin",
        "Content-Type": "application/octet-stream",
        "Idempotency-Key": "t182-physical",
    }
    created = await client.post(path, headers=upload_headers, content=payload)
    assert created.status_code == 201
    version_id = UUID(created.json()["data"]["id"])
    async with factory() as db:
        record = (
            await db.execute(
                select(FileStorageRecord)
                .join(
                    DocumentVersion,
                    FileStorageRecord.id == DocumentVersion.file_storage_record_id,
                )
                .where(DocumentVersion.id == version_id)
            )
        ).scalar_one()
        assert record.size_bytes == len(payload)
        assert record.checksum_sha256 == hashlib.sha256(payload).hexdigest()
        assert record.mime_type == "application/octet-stream"
        assert record.original_filename == "evidence.bin"
        assert (root / record.file_path).read_bytes() == payload
    replay = await client.post(path, headers=upload_headers, content=payload)
    assert replay.status_code == 201 and replay.json()["data"]["id"] == str(version_id)
    physical_before_conflict = {
        item.relative_to(root): item.read_bytes() for item in root.rglob("content")
    }
    assert len(physical_before_conflict) == 1
    async with factory() as db:
        counts_before_conflict = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )
    conflict = await client.post(path, headers=upload_headers, content=b"different payload")
    assert conflict.status_code == 409
    assert {
        item.relative_to(root): item.read_bytes() for item in root.rglob("content")
    } == physical_before_conflict
    download = await client.get(f"{path}/{version_id}/content", headers=headers)
    assert download.status_code == 200 and download.content == payload
    assert download.headers["content-type"].startswith("application/octet-stream")
    assert 'filename="evidence.bin"' in download.headers["content-disposition"]
    async with factory() as db:
        counts_after_conflict = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )
    assert counts_after_conflict == counts_before_conflict


@pytest.mark.asyncio
async def test_t182_physical_document_survives_fresh_backend_process_restart(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
    t182_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    """A second OS process must retrieve the committed physical blob unchanged."""
    _client, factory, _storage, root = physical_client
    credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    payload = b"T182 survives a clean backend process restart\x00\xff"
    admin_url = make_url(t182_database[0])
    app_url = admin_url.set(username="legal_dms_app", password="legal_dms_app")
    service_env = os.environ.copy()
    service_env.update(
        {
            "DATABASE_URL": admin_url.render_as_string(hide_password=False),
            "APP_DATABASE_URL": app_url.render_as_string(hide_password=False),
            "STORAGE_ROOT": str(root),
            "JWT_SECRET_KEY": "t182-disposable-test-key-that-is-at-least-32-chars",
            "ENVIRONMENT": "testing",
        }
    )
    backend_root = Path(__file__).resolve().parents[2]
    processes: list[subprocess.Popen[object]] = []
    log_handles = []

    def start_service(label: str) -> tuple[subprocess.Popen[object], str]:
        port = _available_loopback_port()
        log_handle = (tmp_path / f"t182-{label}-service.log").open("w", encoding="utf-8")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=backend_root,
            env=service_env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append(process)
        log_handles.append(log_handle)
        return process, f"http://127.0.0.1:{port}"

    try:
        first_process, first_url = start_service("first")
        await _wait_for_service(first_url, first_process)
        async with AsyncClient(base_url=first_url) as client:
            login = await client.post("/api/v1/auth/login", json=credentials)
            assert login.status_code == 200
            headers = {
                "Authorization": f"Bearer {login.json()['access_token']}",
                "X-Filename": "restart-evidence.bin",
                "Idempotency-Key": "t182-process-restart",
                "Content-Type": "application/octet-stream",
            }
            created = await client.post(path, headers=headers, content=payload)
            assert created.status_code == 201
            version_id = UUID(created.json()["data"]["id"])

        async with factory() as db:
            record = (
                await db.execute(
                    select(FileStorageRecord)
                    .join(
                        DocumentVersion,
                        FileStorageRecord.id == DocumentVersion.file_storage_record_id,
                    )
                    .where(DocumentVersion.id == version_id)
                )
            ).scalar_one()
            physical_path = root / record.file_path
            expected_checksum = record.checksum_sha256
            expected_size = record.size_bytes
        assert physical_path.read_bytes() == payload
        assert expected_checksum == hashlib.sha256(payload).hexdigest()
        assert expected_size == len(payload)

        first_process.terminate()
        await asyncio.to_thread(first_process.wait, 10)
        assert first_process.returncode is not None

        second_process, second_url = start_service("second")
        assert second_process.pid != first_process.pid
        await _wait_for_service(second_url, second_process)
        async with AsyncClient(base_url=second_url) as client:
            login = await client.post("/api/v1/auth/login", json=credentials)
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            metadata = await client.get(f"{path}/{version_id}", headers=headers)
            assert metadata.status_code == 200
            assert metadata.json()["data"]["id"] == str(version_id)
            recovered = await client.get(f"{path}/{version_id}/content", headers=headers)
            assert recovered.status_code == 200
            assert recovered.content == payload
            assert recovered.headers["content-type"].startswith("application/octet-stream")
            assert 'filename="restart-evidence.bin"' in recovered.headers["content-disposition"]

        async with factory() as db:
            assert (
                await db.execute(
                    select(func.count(DocumentVersion.id)).where(
                        DocumentVersion.document_id == document_id
                    )
                )
            ).scalar_one() == 1
            assert (
                await db.execute(
                    select(func.count(FileStorageRecord.id))
                    .join(
                        DocumentVersion,
                        FileStorageRecord.id == DocumentVersion.file_storage_record_id,
                    )
                    .where(DocumentVersion.document_id == document_id)
                )
            ).scalar_one() == 1
        assert physical_path.read_bytes() == payload
        assert hashlib.sha256(physical_path.read_bytes()).hexdigest() == expected_checksum
        assert physical_path.stat().st_size == expected_size
        assert len(list(root.rglob("content"))) == 1
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, 10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    await asyncio.to_thread(process.wait, 10)
        for log_handle in log_handles:
            log_handle.close()


@pytest.mark.asyncio
async def test_t182_physical_corruption_fails_closed(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
) -> None:
    client, factory, _storage, root = physical_client
    headers, path = await _login_and_path(client, factory)
    created = await client.post(
        path,
        headers={**headers, "X-Filename": "x.txt", "Content-Type": "text/plain"},
        content=b"original",
    )
    assert created.status_code == 201
    version_id = created.json()["data"]["id"]
    async with factory() as db:
        record = (
            await db.execute(
                select(FileStorageRecord)
                .join(
                    DocumentVersion,
                    FileStorageRecord.id == DocumentVersion.file_storage_record_id,
                )
                .where(DocumentVersion.id == UUID(version_id))
            )
        ).scalar_one()
        (root / record.file_path).write_bytes(b"corrupt")
    response = await client.get(f"{path}/{version_id}/content", headers=headers)
    assert response.status_code == 500
    assert response.content != b"corrupt"


@pytest.mark.asyncio
async def test_t182_post_write_database_failure_compensates_physical_blob(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The repository fault is after real save and before request commit."""
    client, factory, _storage, root = physical_client
    headers, path = await _login_and_path(client, factory)
    async with factory() as db:
        versions_before = (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one()
        records_before = (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one()

    async def fail_after_write(self, storage, version, key) -> None:
        raise RuntimeError("t182 injected database failure after physical write")

    monkeypatch.setattr(SqlAlchemyDocumentVersionRepository, "add", fail_after_write)
    response = await client.post(
        path,
        headers={**headers, "X-Filename": "rollback.txt", "Idempotency-Key": "rollback"},
        content=b"must be removed",
    )
    assert response.status_code == 500
    assert not list(root.rglob("content"))
    async with factory() as db:
        version_count = (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one()
        record_count = (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one()
    assert version_count == versions_before
    assert record_count == records_before


@pytest.mark.asyncio
async def test_t182_physical_write_failure_has_no_api_or_database_residue(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, factory, _storage, root = physical_client
    headers, path = await _login_and_path(client, factory)
    async with factory() as db:
        before = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )

    def fail_fsync(_fd: int) -> None:
        raise OSError("t182 physical write failure")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    response = await client.post(
        path,
        headers={**headers, "X-Filename": "write-failure.txt", "Idempotency-Key": "write-failure"},
        content=b"must not persist",
    )
    assert response.status_code == 500
    assert "physical-storage" not in response.text
    assert not list(root.rglob("content"))
    assert not list(root.rglob("tmp*"))
    async with factory() as db:
        after = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )
    assert after == before


@pytest.mark.asyncio
async def test_t182_physical_storage_is_tenant_scoped_and_rbac_denies_access(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
) -> None:
    client, factory, _storage, root = physical_client
    owner_headers, path = await _login_and_path(client, factory)
    created = await client.post(
        path,
        headers={**owner_headers, "X-Filename": "tenant-a.txt", "Content-Type": "text/plain"},
        content=b"tenant-a-only",
    )
    assert created.status_code == 201
    version_id = created.json()["data"]["id"]
    physical_before = {item.relative_to(root): item.read_bytes() for item in root.rglob("content")}
    assert len(physical_before) == 1
    assert next(iter(physical_before)).parts[0] == "organizations"

    other_credentials, _matter, _file, _document = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    other_login = await client.post("/api/v1/auth/login", json=other_credentials)
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    assert (await client.get(f"{path}/{version_id}", headers=other_headers)).status_code == 404
    denied = await client.get(f"{path}/{version_id}/content", headers=other_headers)
    assert denied.status_code == 404 and denied.content != b"tenant-a-only"
    assert {
        item.relative_to(root): item.read_bytes() for item in root.rglob("content")
    } == physical_before


@pytest.mark.asyncio
async def test_t182_rbac_denials_do_not_mutate_physical_document_storage(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
) -> None:
    client, factory, _storage, root = physical_client

    read_credentials, read_matter, read_file, read_document = await _seed_authorized_document(
        factory, "documents:read"
    )
    read_login = await client.post("/api/v1/auth/login", json=read_credentials)
    assert read_login.status_code == 200
    read_headers = {"Authorization": f"Bearer {read_login.json()['access_token']}"}
    read_path = (
        f"/api/v1/matters/{read_matter}/files/{read_file}/documents/{read_document}/versions"
    )
    async with factory() as db:
        before_denied_upload = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )
    denied_upload = await client.post(
        read_path,
        headers={
            **read_headers,
            "X-Filename": "denied-upload.txt",
            "Idempotency-Key": "t182-rbac-denied-upload",
            "Content-Type": "text/plain",
        },
        content=b"must-not-reach-storage",
    )
    assert denied_upload.status_code == 403
    assert not list(root.rglob("content"))
    assert not list(root.rglob("tmp*"))
    async with factory() as db:
        after_denied_upload = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )
    assert after_denied_upload == before_denied_upload

    write_credentials, write_matter, write_file, write_document = await _seed_authorized_document(
        factory, "documents:write"
    )
    write_login = await client.post("/api/v1/auth/login", json=write_credentials)
    assert write_login.status_code == 200
    write_headers = {"Authorization": f"Bearer {write_login.json()['access_token']}"}
    write_path = (
        f"/api/v1/matters/{write_matter}/files/{write_file}/documents/{write_document}/versions"
    )
    created = await client.post(
        write_path,
        headers={
            **write_headers,
            "X-Filename": "read-denied.txt",
            "Content-Type": "text/plain",
        },
        content=b"existing-content-must-remain-private",
    )
    assert created.status_code == 201
    version_id = created.json()["data"]["id"]
    physical_before = {item.relative_to(root): item.read_bytes() for item in root.rglob("content")}
    denied_download = await client.get(f"{write_path}/{version_id}/content", headers=write_headers)
    assert denied_download.status_code == 403
    assert denied_download.content != b"existing-content-must-remain-private"
    assert {
        item.relative_to(root): item.read_bytes() for item in root.rglob("content")
    } == physical_before


@pytest.mark.asyncio
async def test_t182_missing_or_invalid_organization_context_fails_closed(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
) -> None:
    client, factory, _storage, root = physical_client
    _credentials, matter_id, file_id, document_id = await _seed_authorized_document(
        factory, "documents:read", "documents:write"
    )
    path = f"/api/v1/matters/{matter_id}/files/{file_id}/documents/{document_id}/versions"
    async with factory() as db:
        before = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )
    for headers in ({}, {"Authorization": "Bearer malformed-token"}):
        response = await client.post(
            path,
            headers={
                **headers,
                "X-Filename": "no-organization-context.txt",
                "Idempotency-Key": "t182-no-organization-context",
                "Content-Type": "text/plain",
            },
            content=b"must-not-persist",
        )
        assert response.status_code == 401
    assert not list(root.rglob("content"))
    assert not list(root.rglob("tmp*"))
    async with factory() as db:
        after = (
            (await db.execute(select(func.count(DocumentVersion.id)))).scalar_one(),
            (await db.execute(select(func.count(FileStorageRecord.id)))).scalar_one(),
            (await db.execute(select(func.count(DocumentVersionIdempotencyKey.id)))).scalar_one(),
        )
    assert after == before


@pytest.mark.asyncio
async def test_t182_physical_storage_rejects_traversal_before_filesystem_access(
    physical_client: tuple[AsyncClient, async_sessionmaker[AsyncSession], LocalFileStorage, Path],
    tmp_path: Path,
) -> None:
    _client, _factory, storage, root = physical_client
    sentinel = tmp_path / "outside-storage-sentinel.txt"
    sentinel.write_bytes(b"must-remain-untouched")

    for unsafe_path in (str(Path("..") / sentinel.name), str(sentinel.resolve())):
        with pytest.raises(ValueError, match="escapes the storage root"):
            await storage.save(unsafe_path, b"malicious")
        with pytest.raises(ValueError, match="escapes the storage root"):
            await storage.read(unsafe_path)
        with pytest.raises(ValueError, match="escapes the storage root"):
            await storage.delete(unsafe_path)
        with pytest.raises(ValueError, match="escapes the storage root"):
            await storage.exists(unsafe_path)

    assert sentinel.read_bytes() == b"must-remain-untouched"
    assert not list(root.rglob("content"))
    assert not list(root.rglob("tmp*"))
