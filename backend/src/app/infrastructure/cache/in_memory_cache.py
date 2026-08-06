"""In-process cache: a dict-backed store with optional per-entry TTL,
expired lazily on read (no background sweep). A real distributed
implementation (e.g. Redis) can satisfy the same `Cache` port later without
touching any caller.

Uses `time.monotonic()` rather than wall-clock time for expiry so a system
clock change (NTP sync, manual adjustment, DST) can't make entries expire
early or late.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.application.interfaces.cache import Cache


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float | None


class InMemoryCache(Cache):
    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at <= time.monotonic():
            del self._entries[key]
            return None
        return entry.value

    async def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds is not None else None
        self._entries[key] = _Entry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> None:
        self._entries.pop(key, None)

    async def clear(self) -> None:
        self._entries.clear()
