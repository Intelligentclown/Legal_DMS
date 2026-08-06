"""Unit of work port: demarcates a transaction boundary around an operation
-- begin it, then either commit or roll it back based on the outcome.
Concrete implementations live in `infrastructure/`.

Deliberately minimal and silent on *what* resource is being transacted (a DB
session, a distributed transaction, ...) and on how a handler gains access
to it -- those are decisions for whichever concrete implementation and
consuming feature need them. `TransactionPipelineBehavior` (see
`infrastructure/commands/transaction_pipeline_behavior.py`) is the one
caller of this port today.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class UnitOfWorkError(Exception):
    """Raised on unit-of-work misuse: beginning a transaction while one is
    already active, or committing/rolling back when none is active.
    """


class UnitOfWork(ABC):
    @abstractmethod
    async def begin(self) -> None:
        """Start a new transaction. Raises `UnitOfWorkError` if one is
        already active on this instance."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the active transaction. Raises `UnitOfWorkError` if none
        is active."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the active transaction. Raises `UnitOfWorkError` if
        none is active."""
        ...
