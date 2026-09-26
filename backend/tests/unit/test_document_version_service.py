from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.document_version_service import DocumentVersionService
from app.application.errors.exceptions import ConflictError, UnexpectedError
from app.application.interfaces.file_storage import StoredFile
from app.infrastructure.database.transaction_outcome import (
    TransactionOutcome,
    TransactionOutcomeContext,
)
from app.infrastructure.persistence.models.document import (
    Document,
    DocumentVersion,
    DocumentVersionIdempotencyKey,
)


class Storage:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def save(self, path, content, *, content_type=None):
        self.items[path] = content
        return StoredFile(path, len(content), content_type)

    async def read(self, path):
        return self.items[path]

    async def delete(self, path):
        self.deleted.append(path)
        self.items.pop(path, None)


class Repository:
    def __init__(self) -> None:
        self.versions: list[DocumentVersion] = []
        self.keys: dict[str, DocumentVersionIdempotencyKey] = {}
        self.records = {}

    async def idempotency(self, _org, _document, key):
        return self.keys.get(key)

    async def lock_document(self, document):
        return document

    async def next_version_number(self, _document):
        return len(self.versions) + 1

    async def add(self, storage, version, key):
        self.records[storage.id] = storage
        self.versions.append(version)
        if key:
            self.keys[key.idempotency_key] = key

    async def list(self, _org, _document):
        return self.versions

    async def get(self, _org, _document, version_id):
        return next((v for v in self.versions if v.id == version_id), None)

    async def latest(self, _org, _document):
        return self.versions[-1] if self.versions else None

    async def storage(self, _org, storage_id):
        return self.records.get(storage_id)


def service():
    org, doc = uuid4(), Document(
        id=uuid4(),
        organization_id=uuid4(),
        matter_id=uuid4(),
        file_id=uuid4(),
        document_type_id=uuid4(),
        title="D",
    )
    doc.organization_id = org
    repo, storage, context = Repository(), Storage(), TransactionOutcomeContext()
    return DocumentVersionService(repo, storage, context), repo, storage, context, org, doc


@pytest.mark.asyncio
async def test_create_idempotency_download_and_definitive_compensation() -> None:
    app, _repo, storage, context, org, document = service()
    version = await app.create(org, document, b"exact", "a.txt", "text/plain", "key", None, None)
    assert version.version_number == 1
    assert DocumentVersionService.storage_key(org, version.id) in storage.items
    assert (
        await app.create(org, document, b"exact", "a.txt", "text/plain", "key", None, None)
        is version
    )
    with pytest.raises(ConflictError):
        await app.create(org, document, b"different", "a.txt", "text/plain", "key", None, None)
    _, _, content = await app.download(org, document, version.id)
    assert content == b"exact"
    await context.finalize(TransactionOutcome.DEFINITIVE_NON_COMMIT)
    assert storage.deleted


@pytest.mark.asyncio
async def test_download_rejects_checksum_corruption() -> None:
    app, _repo, storage, context, org, document = service()
    version = await app.create(org, document, b"exact", "a.txt", None, None, None, None)
    storage.items[DocumentVersionService.storage_key(org, version.id)] = b"corrupt"
    with pytest.raises(UnexpectedError):
        await app.download(org, document, version.id)
    await context.finalize(TransactionOutcome.CONFIRMED_COMMIT)


@pytest.mark.asyncio
async def test_create_rechecks_idempotency_after_document_lock() -> None:
    app, repo, storage, context, org, document = service()
    existing = await app.create(org, document, b"exact", "a.txt", None, "key", None, None)

    class RaceRepository(Repository):
        def __init__(self) -> None:
            super().__init__()
            self.locked = False

        async def idempotency(self, _org, _document, key):
            if not self.locked:
                return None
            return repo.keys.get(key)

        async def lock_document(self, current_document):
            self.locked = True
            return current_document

    race_repository = RaceRepository()
    race_app = DocumentVersionService(race_repository, storage, context)
    # Make the durable evidence become visible only after the allocation lock,
    # which is the interleaving concurrent retries must handle.
    race_repository.keys = repo.keys
    race_repository.versions = repo.versions
    race_repository.records = repo.records
    reconciled = await race_app.create(org, document, b"exact", "a.txt", None, "key", None, None)

    assert reconciled is existing
    assert len(storage.items) == 1
    await context.finalize(TransactionOutcome.CONFIRMED_COMMIT)
