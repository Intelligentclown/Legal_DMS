"""Cache port: a key-value store with optional per-entry time-to-live, for
memoizing the result of an expensive operation. Concrete implementations
live in `infrastructure/`.

Standalone port, not wired into anything yet -- same category as
`FileStorage`/`SearchIndex`: a reusable capability proven with its own
default implementation, waiting for a future feature to actually use it.
Not a `QueryBus` pipeline hook (see ADR-0011's "caching" mention in its
deferred trade-offs) -- that would be a distinct, separate decision layering
a caching behavior on top of this port, not this port itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Return the cached value for `key`, or `None` if absent or
        expired. `None` is indistinguishable from "not cached" -- don't
        cache a value where that ambiguity matters."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        """Store `value` under `key`, replacing any existing entry.
        `ttl_seconds=None` means no expiry."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove `key` if present. No-op if absent."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Remove every entry."""
        ...
