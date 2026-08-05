"""File storage port: business logic must never depend directly on
filesystem/cloud SDK APIs. Concrete implementations live in
`infrastructure/storage/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredFile:
    path: str
    size: int
    content_type: str | None = None


class FileStorage(ABC):
    @abstractmethod
    async def save(
        self, path: str, content: bytes, *, content_type: str | None = None
    ) -> StoredFile: ...

    @abstractmethod
    async def read(self, path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, path: str) -> None: ...

    @abstractmethod
    async def exists(self, path: str) -> bool: ...
