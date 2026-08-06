"""Command bus port: dispatches a command to the single handler registered
for its type, returning that handler's `Result`. Concrete implementations
live in `infrastructure/commands/`.

Distinct from `EventBus`: an event may have zero-to-many subscribed handlers
reacting to something that already happened (fire-and-forget); a command has
exactly one handler that performs the requested action and reports
success/failure via `Result[R, AppError]` — dispatch is how a caller (a
route, a job, another use case) invokes a use case without importing its
concrete handler directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from app.application.errors.exceptions import AppError
from app.domain.common.result import Result


class Command:
    """Marker base class for commands dispatched through a `CommandBus`.

    Subclass and add command-specific fields (typically a frozen dataclass,
    mirroring `DomainEvent`). Not an `ABC` — a command has no behavior of its
    own to declare abstract, only data.
    """


CommandHandler = Callable[[Any], Awaitable[Result[Any, AppError]]]


class CommandBusError(Exception):
    """Raised on command-bus misuse: registering a second handler for a
    command type that already has one, or dispatching a command type with no
    registered handler. Both are programming errors, not runtime business
    failures — those are reported via the handler's `Result`, not this
    exception.
    """


class CommandBus(ABC):
    @abstractmethod
    def register(self, command_type: type[Command], handler: CommandHandler) -> None:
        """Register `handler` as *the* handler for `command_type`.

        A command bus dispatches to exactly one handler per command type
        (unlike `EventBus.subscribe`, which allows many). Implementations
        must raise `CommandBusError` if `command_type` already has a
        registered handler, rather than silently overwriting it.
        """
        ...

    @abstractmethod
    async def dispatch[R](self, command: Command) -> Result[R, AppError]:
        """Dispatch `command` to its registered handler and return the
        handler's `Result`.

        Implementations must raise `CommandBusError` if no handler is
        registered for `type(command)`.
        """
        ...
