"""Query bus port: dispatches a query to the single handler registered for
its type, returning that handler's `Result`. Concrete implementations live
in `infrastructure/queries/`.

Sibling to `CommandBus`, not to `EventBus`: like a command, a query has
exactly one handler that performs the read and reports success/failure via
`Result[R, AppError]` — dispatch is how a caller (a route, a job, another use
case) requests data without importing the concrete handler that knows how to
fetch it. Unlike a command, a query must not mutate state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from app.application.errors.exceptions import AppError
from app.domain.common.result import Result


class Query:
    """Marker base class for queries dispatched through a `QueryBus`.

    Subclass and add query-specific fields (typically a frozen dataclass,
    mirroring `Command`/`DomainEvent`). Not an `ABC` — a query has no
    behavior of its own to declare abstract, only data.
    """


QueryHandler = Callable[[Any], Awaitable[Result[Any, AppError]]]


class QueryBusError(Exception):
    """Raised on query-bus misuse: registering a second handler for a query
    type that already has one, or dispatching a query type with no
    registered handler. Both are programming errors, not runtime business
    failures — those are reported via the handler's own `Result`, not this
    exception.
    """


class QueryBus(ABC):
    @abstractmethod
    def register(self, query_type: type[Query], handler: QueryHandler) -> None:
        """Register `handler` as *the* handler for `query_type`.

        A query bus dispatches to exactly one handler per query type (unlike
        `EventBus.subscribe`, which allows many) — same semantics as
        `CommandBus.register`. Implementations must raise `QueryBusError` if
        `query_type` already has a registered handler, rather than silently
        overwriting it.
        """
        ...

    @abstractmethod
    async def dispatch[R](self, query: Query) -> Result[R, AppError]:
        """Dispatch `query` to its registered handler and return the
        handler's `Result`.

        Implementations must raise `QueryBusError` if no handler is
        registered for `type(query)`.
        """
        ...
