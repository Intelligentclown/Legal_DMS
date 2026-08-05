"""Local filesystem implementation of the `FileStorage` port. Future
providers (network storage, cloud storage, OneDrive, Google Drive) satisfy
the same port without touching any caller.

Uses plain synchronous file I/O inside `async def` methods — for local disk
this is fast enough that adding a dependency like `aiofiles` isn't
justified. A network/cloud-backed implementation would use its SDK's real
async client instead.
"""

from __future__ import annotations

from pathlib import Path

from app.application.errors.exceptions import NotFoundError
from app.application.interfaces.file_storage import FileStorage, StoredFile


class LocalFileStorage(FileStorage):
    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        """Resolve `path` under the storage root, rejecting anything that
        would escape it (e.g. via `../`) — a caller-supplied path should
        never be able to read/write outside the configured storage directory.
        """
        candidate = (self._root / path).resolve()
        root_resolved = self._root.resolve()
        if candidate != root_resolved and root_resolved not in candidate.parents:
            raise ValueError(f"Path {path!r} escapes the storage root")
        return candidate

    async def save(
        self, path: str, content: bytes, *, content_type: str | None = None
    ) -> StoredFile:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredFile(path=path, size=len(content), content_type=content_type)

    async def read(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.exists():
            raise NotFoundError(f"File not found: {path}")
        return target.read_bytes()

    async def delete(self, path: str) -> None:
        self._resolve(path).unlink(missing_ok=True)

    async def exists(self, path: str) -> bool:
        return self._resolve(path).exists()
