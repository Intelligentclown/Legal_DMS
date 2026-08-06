"""Tests for the transaction pipeline behavior wrapping a CommandBus."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app.application.errors.exceptions import AppError, ValidationError
from app.application.interfaces.command_bus import Command
from app.domain.common.result import Result
from app.infrastructure.commands.in_memory_command_bus import InMemoryCommandBus
from app.infrastructure.commands.transaction_pipeline_behavior import TransactionPipelineBehavior
from app.infrastructure.transactions.in_memory_unit_of_work import InMemoryUnitOfWork


@dataclass(frozen=True, kw_only=True)
class _CreateWidget(Command):
    name: str


async def _create_widget_handler(command: _CreateWidget) -> Result[str, AppError]:
    if not command.name:
        return Result.fail(ValidationError("name must not be empty"))
    return Result.ok(f"widget:{command.name}")


class TestTransactionPipelineBehavior:
    async def test_dispatch_commits_the_unit_of_work_on_a_successful_result(self) -> None:
        inner = InMemoryCommandBus()
        inner.register(_CreateWidget, _create_widget_handler)
        units_of_work: list[InMemoryUnitOfWork] = []

        def factory() -> InMemoryUnitOfWork:
            uow = InMemoryUnitOfWork()
            units_of_work.append(uow)
            return uow

        pipeline = TransactionPipelineBehavior(inner, factory)

        result = await pipeline.dispatch(_CreateWidget(name="gizmo"))

        assert result.is_success
        assert result.value == "widget:gizmo"
        assert len(units_of_work) == 1
        assert units_of_work[0].committed_count == 1
        assert units_of_work[0].rolled_back_count == 0

    async def test_dispatch_rolls_back_the_unit_of_work_on_a_failure_result(self) -> None:
        inner = InMemoryCommandBus()
        inner.register(_CreateWidget, _create_widget_handler)
        units_of_work: list[InMemoryUnitOfWork] = []

        def factory() -> InMemoryUnitOfWork:
            uow = InMemoryUnitOfWork()
            units_of_work.append(uow)
            return uow

        pipeline = TransactionPipelineBehavior(inner, factory)

        result = await pipeline.dispatch(_CreateWidget(name=""))

        assert result.is_failure
        assert isinstance(result.error, ValidationError)
        assert units_of_work[0].committed_count == 0
        assert units_of_work[0].rolled_back_count == 1

    async def test_dispatch_rolls_back_and_reraises_on_handler_exception(self) -> None:
        inner = InMemoryCommandBus()

        async def failing_handler(command: _CreateWidget) -> Result[str, AppError]:
            raise RuntimeError("boom")

        inner.register(_CreateWidget, failing_handler)
        units_of_work: list[InMemoryUnitOfWork] = []

        def factory() -> InMemoryUnitOfWork:
            uow = InMemoryUnitOfWork()
            units_of_work.append(uow)
            return uow

        pipeline = TransactionPipelineBehavior(inner, factory)

        with pytest.raises(RuntimeError, match="boom"):
            await pipeline.dispatch(_CreateWidget(name="gizmo"))

        assert units_of_work[0].committed_count == 0
        assert units_of_work[0].rolled_back_count == 1

    async def test_dispatch_rolls_back_and_reraises_on_cancellation(self) -> None:
        inner = InMemoryCommandBus()

        async def cancelled_handler(command: _CreateWidget) -> Result[str, AppError]:
            raise asyncio.CancelledError()

        inner.register(_CreateWidget, cancelled_handler)
        units_of_work: list[InMemoryUnitOfWork] = []

        def factory() -> InMemoryUnitOfWork:
            uow = InMemoryUnitOfWork()
            units_of_work.append(uow)
            return uow

        pipeline = TransactionPipelineBehavior(inner, factory)

        with pytest.raises(asyncio.CancelledError):
            await pipeline.dispatch(_CreateWidget(name="gizmo"))

        assert units_of_work[0].committed_count == 0
        assert units_of_work[0].rolled_back_count == 1

    async def test_dispatch_rolls_back_and_reraises_on_a_base_exception(self) -> None:
        class _NotAnException(BaseException):
            pass

        inner = InMemoryCommandBus()

        async def failing_handler(command: _CreateWidget) -> Result[str, AppError]:
            raise _NotAnException("not an Exception subclass")

        inner.register(_CreateWidget, failing_handler)
        units_of_work: list[InMemoryUnitOfWork] = []

        def factory() -> InMemoryUnitOfWork:
            uow = InMemoryUnitOfWork()
            units_of_work.append(uow)
            return uow

        pipeline = TransactionPipelineBehavior(inner, factory)

        with pytest.raises(_NotAnException):
            await pipeline.dispatch(_CreateWidget(name="gizmo"))

        assert units_of_work[0].committed_count == 0
        assert units_of_work[0].rolled_back_count == 1

    async def test_register_delegates_to_the_inner_bus(self) -> None:
        inner = InMemoryCommandBus()
        pipeline = TransactionPipelineBehavior(inner, InMemoryUnitOfWork)

        pipeline.register(_CreateWidget, _create_widget_handler)
        result = await inner.dispatch(_CreateWidget(name="gizmo"))

        assert result.value == "widget:gizmo"

    async def test_each_dispatch_uses_a_fresh_unit_of_work(self) -> None:
        inner = InMemoryCommandBus()
        inner.register(_CreateWidget, _create_widget_handler)
        units_of_work: list[InMemoryUnitOfWork] = []

        def factory() -> InMemoryUnitOfWork:
            uow = InMemoryUnitOfWork()
            units_of_work.append(uow)
            return uow

        pipeline = TransactionPipelineBehavior(inner, factory)

        await pipeline.dispatch(_CreateWidget(name="first"))
        await pipeline.dispatch(_CreateWidget(name="second"))

        assert len(units_of_work) == 2
        assert units_of_work[0] is not units_of_work[1]
        assert units_of_work[0].committed_count == 1
        assert units_of_work[1].committed_count == 1
