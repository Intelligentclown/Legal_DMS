"""Tests for the in-memory query bus."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.application.errors.exceptions import AppError, NotFoundError
from app.application.interfaces.query_bus import Query, QueryBus, QueryBusError
from app.domain.common.result import Result
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.queries.in_memory_query_bus import InMemoryQueryBus


@dataclass(frozen=True, kw_only=True)
class _GetWidget(Query):
    widget_id: str


@dataclass(frozen=True, kw_only=True)
class _ListWidgets(Query):
    pass


_WIDGETS = {"1": "gizmo"}


async def _get_widget_handler(query: _GetWidget) -> Result[str, AppError]:
    widget = _WIDGETS.get(query.widget_id)
    if widget is None:
        return Result.fail(NotFoundError(f"widget {query.widget_id} not found"))
    return Result.ok(widget)


class TestInMemoryQueryBus:
    async def test_dispatch_invokes_the_registered_handler(self) -> None:
        bus = InMemoryQueryBus()
        bus.register(_GetWidget, _get_widget_handler)

        result = await bus.dispatch(_GetWidget(widget_id="1"))

        assert result.is_success
        assert result.value == "gizmo"

    async def test_dispatch_returns_the_handlers_failure_result(self) -> None:
        bus = InMemoryQueryBus()
        bus.register(_GetWidget, _get_widget_handler)

        result = await bus.dispatch(_GetWidget(widget_id="missing"))

        assert result.is_failure
        assert isinstance(result.error, NotFoundError)

    async def test_dispatch_routes_to_the_handler_matching_the_query_type(self) -> None:
        bus = InMemoryQueryBus()
        calls: list[str] = []

        async def list_handler(query: _ListWidgets) -> Result[list[str], AppError]:
            calls.append("list")
            return Result.ok(list(_WIDGETS.values()))

        bus.register(_GetWidget, _get_widget_handler)
        bus.register(_ListWidgets, list_handler)

        result = await bus.dispatch(_ListWidgets())

        assert result.value == ["gizmo"]
        assert calls == ["list"]

    async def test_dispatching_an_unregistered_query_type_raises(self) -> None:
        bus = InMemoryQueryBus()

        with pytest.raises(QueryBusError, match="No handler registered"):
            await bus.dispatch(_GetWidget(widget_id="1"))

    async def test_registering_a_second_handler_for_the_same_query_type_raises(self) -> None:
        bus = InMemoryQueryBus()
        bus.register(_GetWidget, _get_widget_handler)

        async def other_handler(query: _GetWidget) -> Result[str, AppError]:
            return Result.ok("other")

        with pytest.raises(QueryBusError, match="already registered"):
            bus.register(_GetWidget, other_handler)

    async def test_handler_exception_propagates(self) -> None:
        bus = InMemoryQueryBus()

        async def failing_handler(query: _GetWidget) -> Result[str, AppError]:
            raise RuntimeError("boom")

        bus.register(_GetWidget, failing_handler)

        with pytest.raises(RuntimeError, match="boom"):
            await bus.dispatch(_GetWidget(widget_id="1"))


class TestConfigureContainer:
    def test_registers_query_bus_resolvable_as_in_memory_implementation(self) -> None:
        configure_container()

        resolved = container.resolve(QueryBus)

        assert isinstance(resolved, InMemoryQueryBus)
