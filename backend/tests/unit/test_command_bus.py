"""Tests for the in-memory command bus."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.application.errors.exceptions import AppError, ValidationError
from app.application.interfaces.command_bus import Command, CommandBus, CommandBusError
from app.domain.common.result import Result
from app.infrastructure.commands.in_memory_command_bus import InMemoryCommandBus
from app.infrastructure.di.container import configure_container, container


@dataclass(frozen=True, kw_only=True)
class _CreateWidget(Command):
    name: str


@dataclass(frozen=True, kw_only=True)
class _RenameWidget(Command):
    widget_id: str
    new_name: str


async def _create_widget_handler(command: _CreateWidget) -> Result[str, AppError]:
    if not command.name:
        return Result.fail(ValidationError("name must not be empty"))
    return Result.ok(f"widget:{command.name}")


class TestInMemoryCommandBus:
    async def test_dispatch_invokes_the_registered_handler(self) -> None:
        bus = InMemoryCommandBus()
        bus.register(_CreateWidget, _create_widget_handler)

        result = await bus.dispatch(_CreateWidget(name="gizmo"))

        assert result.is_success
        assert result.value == "widget:gizmo"

    async def test_dispatch_returns_the_handlers_failure_result(self) -> None:
        bus = InMemoryCommandBus()
        bus.register(_CreateWidget, _create_widget_handler)

        result = await bus.dispatch(_CreateWidget(name=""))

        assert result.is_failure
        assert isinstance(result.error, ValidationError)

    async def test_dispatch_routes_to_the_handler_matching_the_command_type(self) -> None:
        bus = InMemoryCommandBus()
        calls: list[str] = []

        async def rename_handler(command: _RenameWidget) -> Result[str, AppError]:
            calls.append(command.widget_id)
            return Result.ok(command.new_name)

        bus.register(_CreateWidget, _create_widget_handler)
        bus.register(_RenameWidget, rename_handler)

        result = await bus.dispatch(_RenameWidget(widget_id="1", new_name="new"))

        assert result.value == "new"
        assert calls == ["1"]

    async def test_dispatching_an_unregistered_command_type_raises(self) -> None:
        bus = InMemoryCommandBus()

        with pytest.raises(CommandBusError, match="No handler registered"):
            await bus.dispatch(_CreateWidget(name="gizmo"))

    async def test_registering_a_second_handler_for_the_same_command_type_raises(self) -> None:
        bus = InMemoryCommandBus()
        bus.register(_CreateWidget, _create_widget_handler)

        async def other_handler(command: _CreateWidget) -> Result[str, AppError]:
            return Result.ok("other")

        with pytest.raises(CommandBusError, match="already registered"):
            bus.register(_CreateWidget, other_handler)

    async def test_handler_exception_propagates(self) -> None:
        bus = InMemoryCommandBus()

        async def failing_handler(command: _CreateWidget) -> Result[str, AppError]:
            raise RuntimeError("boom")

        bus.register(_CreateWidget, failing_handler)

        with pytest.raises(RuntimeError, match="boom"):
            await bus.dispatch(_CreateWidget(name="gizmo"))


class TestConfigureContainer:
    def test_registers_command_bus_resolvable_as_in_memory_implementation(self) -> None:
        configure_container()

        resolved = container.resolve(CommandBus)

        assert isinstance(resolved, InMemoryCommandBus)
