"""Event bus port: publish/subscribe for domain events. Concrete
implementations live in `infrastructure/events/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.domain.events.domain_event import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(ABC):
    @abstractmethod
    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None: ...

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...

    async def publish_all(self, events: list[DomainEvent]) -> None:
        """Convenience for `bus.publish_all(aggregate.pull_events())`."""
        for event in events:
            await self.publish(event)
