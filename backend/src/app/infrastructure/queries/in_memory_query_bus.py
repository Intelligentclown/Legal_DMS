"""In-process query bus: dispatches to the single handler registered for
each query type within the current process/event loop. A real distributed
implementation (e.g. routing reads to a replica or a dedicated read model)
can satisfy the same `QueryBus` port later without touching any caller.

Handler exceptions are not swallowed — they propagate to the dispatcher, so
a broken handler fails loudly rather than silently reporting a generic
failure `Result`. Mirrors `InMemoryCommandBus`'s propagation behavior.
"""

from __future__ import annotations

from app.application.errors.exceptions import AppError
from app.application.interfaces.query_bus import Query, QueryBus, QueryBusError, QueryHandler
from app.domain.common.result import Result
from app.infrastructure.logging.logger import get_logger

logger = get_logger("queries")


class InMemoryQueryBus(QueryBus):
    def __init__(self) -> None:
        self._handlers: dict[type[Query], QueryHandler] = {}

    def register(self, query_type: type[Query], handler: QueryHandler) -> None:
        if query_type in self._handlers:
            raise QueryBusError(
                f"A handler is already registered for {query_type!r}; a query bus "
                "dispatches to exactly one handler per query type"
            )
        self._handlers[query_type] = handler

    async def dispatch[R](self, query: Query) -> Result[R, AppError]:
        handler = self._handlers.get(type(query))
        if handler is None:
            raise QueryBusError(f"No handler registered for {type(query)!r}")

        logger.info(
            "Dispatching query",
            extra={"query_type": type(query).__name__},
        )
        return await handler(query)
