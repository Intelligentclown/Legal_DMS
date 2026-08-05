"""Tests for LocalFileStorage, isolated to a pytest tmp_path so nothing
touches the real project directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.application.errors.exceptions import NotFoundError
from app.application.interfaces.file_storage import FileStorage
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.storage.local_file_storage import LocalFileStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(tmp_path / "storage-root")


class TestLocalFileStorage:
    async def test_save_then_read_round_trips(self, storage: LocalFileStorage) -> None:
        stored = await storage.save("docs/note.txt", b"hello world", content_type="text/plain")

        assert stored.path == "docs/note.txt"
        assert stored.size == 11
        assert stored.content_type == "text/plain"
        assert await storage.read("docs/note.txt") == b"hello world"

    async def test_save_creates_intermediate_directories(self, storage: LocalFileStorage) -> None:
        await storage.save("a/b/c/deep.txt", b"x")

        assert await storage.exists("a/b/c/deep.txt")

    async def test_read_missing_file_raises_not_found(self, storage: LocalFileStorage) -> None:
        with pytest.raises(NotFoundError):
            await storage.read("does/not/exist.txt")

    async def test_exists_reflects_presence(self, storage: LocalFileStorage) -> None:
        assert not await storage.exists("thing.txt")
        await storage.save("thing.txt", b"data")
        assert await storage.exists("thing.txt")

    async def test_delete_removes_the_file(self, storage: LocalFileStorage) -> None:
        await storage.save("temp.txt", b"data")

        await storage.delete("temp.txt")

        assert not await storage.exists("temp.txt")

    async def test_delete_missing_file_does_not_raise(self, storage: LocalFileStorage) -> None:
        await storage.delete("never-existed.txt")

    async def test_path_traversal_is_rejected(self, storage: LocalFileStorage) -> None:
        with pytest.raises(ValueError, match="escapes the storage root"):
            await storage.save("../../etc/passwd", b"malicious")


class TestConfigureContainer:
    def test_registers_file_storage_as_local_implementation(self) -> None:
        configure_container()

        resolved = container.resolve(FileStorage)

        assert isinstance(resolved, LocalFileStorage)
