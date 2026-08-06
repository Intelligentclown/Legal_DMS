"""Tests for the in-memory cache."""

from __future__ import annotations

from app.application.interfaces.cache import Cache
from app.infrastructure.cache import in_memory_cache as in_memory_cache_module
from app.infrastructure.cache.in_memory_cache import InMemoryCache
from app.infrastructure.di.container import configure_container, container


class TestInMemoryCache:
    async def test_get_on_a_missing_key_returns_none(self) -> None:
        cache = InMemoryCache()

        assert await cache.get("missing") is None

    async def test_set_then_get_returns_the_value(self) -> None:
        cache = InMemoryCache()

        await cache.set("greeting", "hello")

        assert await cache.get("greeting") == "hello"

    async def test_set_overwrites_an_existing_value(self) -> None:
        cache = InMemoryCache()
        await cache.set("greeting", "hello")

        await cache.set("greeting", "goodbye")

        assert await cache.get("greeting") == "goodbye"

    async def test_delete_removes_the_value(self) -> None:
        cache = InMemoryCache()
        await cache.set("greeting", "hello")

        await cache.delete("greeting")

        assert await cache.get("greeting") is None

    async def test_delete_on_a_missing_key_does_not_raise(self) -> None:
        cache = InMemoryCache()

        await cache.delete("missing")

    async def test_clear_removes_every_entry(self) -> None:
        cache = InMemoryCache()
        await cache.set("a", 1)
        await cache.set("b", 2)

        await cache.clear()

        assert await cache.get("a") is None
        assert await cache.get("b") is None

    async def test_entry_without_ttl_does_not_expire(self, monkeypatch) -> None:
        clock = {"now": 0.0}
        monkeypatch.setattr(in_memory_cache_module.time, "monotonic", lambda: clock["now"])
        cache = InMemoryCache()
        await cache.set("greeting", "hello")

        clock["now"] = 1_000_000.0

        assert await cache.get("greeting") == "hello"

    async def test_entry_expires_after_its_ttl_elapses(self, monkeypatch) -> None:
        clock = {"now": 0.0}
        monkeypatch.setattr(in_memory_cache_module.time, "monotonic", lambda: clock["now"])
        cache = InMemoryCache()
        await cache.set("greeting", "hello", ttl_seconds=10)

        clock["now"] = 5.0
        assert await cache.get("greeting") == "hello"

        clock["now"] = 10.0
        assert await cache.get("greeting") is None


class TestConfigureContainer:
    def test_registers_cache_resolvable_as_in_memory_implementation(self) -> None:
        configure_container()

        resolved = container.resolve(Cache)

        assert isinstance(resolved, InMemoryCache)

    def test_cache_is_registered_singleton(self) -> None:
        configure_container()

        first = container.resolve(Cache)
        second = container.resolve(Cache)

        assert first is second
