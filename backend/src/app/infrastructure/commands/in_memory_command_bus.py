"""In-process command bus: dispatches to the single handler registered for
each command type within the current process/event loop. A real
message-broker-backed implementation (for cross-process dispatch) can
satisfy the same `CommandBus` port later without touching any caller.

Handler exceptions are not swallowed — they propagate to the dispatcher, so
a broken handler fails loudly rather than silently reporting a generic
failure `Result`. This mirrors `InMemoryEventBus`'s propagation behavior.
"""

from __future__ import annotations

from app.application.errors.exceptions import AppError
from app.application.interfaces.command_bus import (
    Command,
    CommandBus,
    CommandBusError,
    CommandHandler,
)
from app.domain.common.result import Result
from app.infrastructure.logging.logger import get_logger

logger = get_logger("commands")


class InMemoryCommandBus(CommandBus):
    def __init__(self) -> None:
        self._handlers: dict[type[Command], CommandHandler] = {}

    def register(self, command_type: type[Command], handler: CommandHandler) -> None:
        if command_type in self._handlers:
            raise CommandBusError(
                f"A handler is already registered for {command_type!r}; a command bus "
                "dispatches to exactly one handler per command type"
            )
        self._handlers[command_type] = handler

    async def dispatch[R](self, command: Command) -> Result[R, AppError]:
        handler = self._handlers.get(type(command))
        if handler is None:
            raise CommandBusError(f"No handler registered for {type(command)!r}")

        logger.info(
            "Dispatching command",
            extra={"command_type": type(command).__name__},
        )
        return await handler(command)
