"""In-process event bus: dispatches to handlers registered via `subscribe`
within the current process/event loop. A real message-broker-backed
implementation (for cross-process delivery) can satisfy the same `EventBus`
port later without touching any caller.

Handler exceptions are not swallowed — they propagate to the publisher, so a
broken handler fails loudly rather than silently dropping an event. If a
future need arises for isolated/best-effort handler dispatch, that's a
deliberate design change worth its own decision, not a silent default.
"""

from __future__ import annotations

from collections import defaultdict

from app.application.interfaces.event_bus import EventBus, EventHandler
from app.domain.events.domain_event import DomainEvent
from app.infrastructure.logging.logger import get_logger

logger = get_logger("events")


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        logger.info(
            "Publishing event",
            extra={
                "event_type": event.event_type,
                "event_id": str(event.event_id),
                "handler_count": len(handlers),
            },
        )
        for handler in handlers:
            await handler(event)
