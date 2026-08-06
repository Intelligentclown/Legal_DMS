"""In-process unit of work: tracks whether a transaction is active and how
many times this instance has committed/rolled back, without backing an
actual resource. Proves the `UnitOfWork` contract that
`TransactionPipelineBehavior` depends on; a real resource-backed
implementation (e.g. wrapping a SQLAlchemy `AsyncSession`) can satisfy the
same port later without touching any caller, once a feature actually needs
one.

Registered *non-singleton* in the DI container (`singleton=False`) --
unlike every other Stage 1 port, a unit of work must not be shared as a
single instance across concurrent operations, since each transaction needs
its own begin/commit/rollback state.
"""

from __future__ import annotations

from app.application.interfaces.unit_of_work import UnitOfWork, UnitOfWorkError


class InMemoryUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self._active = False
        self.committed_count = 0
        self.rolled_back_count = 0

    @property
    def is_active(self) -> bool:
        return self._active

    async def begin(self) -> None:
        if self._active:
            raise UnitOfWorkError("A transaction is already active on this unit of work")
        self._active = True

    async def commit(self) -> None:
        if not self._active:
            raise UnitOfWorkError("No active transaction to commit")
        self._active = False
        self.committed_count += 1

    async def rollback(self) -> None:
        if not self._active:
            raise UnitOfWorkError("No active transaction to roll back")
        self._active = False
        self.rolled_back_count += 1
