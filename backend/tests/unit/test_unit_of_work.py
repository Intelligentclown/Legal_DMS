"""Tests for the in-memory unit of work."""

from __future__ import annotations

import pytest

from app.application.interfaces.unit_of_work import UnitOfWork, UnitOfWorkError
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.transactions.in_memory_unit_of_work import InMemoryUnitOfWork


class TestInMemoryUnitOfWork:
    async def test_begin_then_commit_tracks_the_outcome(self) -> None:
        uow = InMemoryUnitOfWork()

        await uow.begin()
        assert uow.is_active
        await uow.commit()

        assert not uow.is_active
        assert uow.committed_count == 1
        assert uow.rolled_back_count == 0

    async def test_begin_then_rollback_tracks_the_outcome(self) -> None:
        uow = InMemoryUnitOfWork()

        await uow.begin()
        await uow.rollback()

        assert not uow.is_active
        assert uow.committed_count == 0
        assert uow.rolled_back_count == 1

    async def test_begin_twice_without_ending_raises(self) -> None:
        uow = InMemoryUnitOfWork()
        await uow.begin()

        with pytest.raises(UnitOfWorkError, match="already active"):
            await uow.begin()

    async def test_commit_without_begin_raises(self) -> None:
        uow = InMemoryUnitOfWork()

        with pytest.raises(UnitOfWorkError, match="No active transaction"):
            await uow.commit()

    async def test_rollback_without_begin_raises(self) -> None:
        uow = InMemoryUnitOfWork()

        with pytest.raises(UnitOfWorkError, match="No active transaction"):
            await uow.rollback()

    async def test_a_new_transaction_can_begin_after_commit(self) -> None:
        uow = InMemoryUnitOfWork()
        await uow.begin()
        await uow.commit()

        await uow.begin()
        await uow.commit()

        assert uow.committed_count == 2


class TestConfigureContainer:
    def test_registers_unit_of_work_resolvable_as_in_memory_implementation(self) -> None:
        configure_container()

        resolved = container.resolve(UnitOfWork)

        assert isinstance(resolved, InMemoryUnitOfWork)

    def test_unit_of_work_is_registered_non_singleton(self) -> None:
        configure_container()

        first = container.resolve(UnitOfWork)
        second = container.resolve(UnitOfWork)

        assert first is not second
