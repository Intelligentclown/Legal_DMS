"""Transaction pipeline behavior: wraps a `CommandBus` so each dispatched
command runs inside its own unit-of-work transaction boundary -- begun
before the inner bus dispatches to the handler, committed if the handler's
`Result` is a success, rolled back if it's a failure. A handler exception --
including `asyncio.CancelledError` (e.g. a client disconnect, a request
timeout, a server shutdown grace period) -- also rolls back before
propagating, same as `InMemoryCommandBus`'s own propagation behavior for
regular exceptions.

A decorator over `CommandBus`, not a new `CommandBus` implementation of its
own -- construct it with an inner bus and a `UnitOfWork` factory (a fresh
instance per dispatch, since a unit of work isn't shared across concurrent
transactions), then register/resolve the decorated instance wherever the
plain inner bus would otherwise go. `Command`/`CommandHandler`/`CommandBus`
are untouched by this -- a handler that needs the transaction resolves the
`UnitOfWork` from wherever it's wired, not from a parameter on `dispatch()`.
See ADR-0012.
"""

from __future__ import annotations

from collections.abc import Callable

from app.application.errors.exceptions import AppError
from app.application.interfaces.command_bus import Command, CommandBus, CommandHandler
from app.application.interfaces.unit_of_work import UnitOfWork
from app.domain.common.result import Result
from app.infrastructure.logging.logger import get_logger

logger = get_logger("commands")


class TransactionPipelineBehavior(CommandBus):
    def __init__(self, inner: CommandBus, unit_of_work_factory: Callable[[], UnitOfWork]) -> None:
        self._inner = inner
        self._unit_of_work_factory = unit_of_work_factory

    def register(self, command_type: type[Command], handler: CommandHandler) -> None:
        self._inner.register(command_type, handler)

    async def dispatch[R](self, command: Command) -> Result[R, AppError]:
        unit_of_work = self._unit_of_work_factory()
        await unit_of_work.begin()

        try:
            result = await self._inner.dispatch(command)
        except BaseException:
            # BaseException, not Exception: asyncio.CancelledError inherits
            # from BaseException (since Python 3.8), not Exception. A plain
            # `except Exception` here would let a cancelled dispatch skip
            # rollback and leave the unit of work `_active=True`.
            await unit_of_work.rollback()
            raise

        if result.is_success:
            await unit_of_work.commit()
        else:
            await unit_of_work.rollback()

        logger.info(
            "Transaction pipeline dispatched command",
            extra={
                "command_type": type(command).__name__,
                "committed": result.is_success,
            },
        )
        return result
