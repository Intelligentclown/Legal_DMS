"""Base building blocks for the domain layer.

No framework imports belong here — domain code must stay usable regardless of
what web framework, ORM, or delivery mechanism the outer layers use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.domain.events.domain_event import DomainEvent


class Entity:
    """Base class for domain entities: identity-based equality via `id`."""

    id: UUID

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Base marker for immutable, value-based-equality domain objects."""


class AggregateRoot(Entity):
    """An Entity that is the root of a consistency boundary and collects the
    domain events raised by changes to it.

    After a repository persists a change, call `pull_events()` and hand the
    result to an `EventBus` (see `application/interfaces/event_bus.py`) to
    publish them. Events are cleared once pulled so they're never published
    twice.
    """

    def __init__(self) -> None:
        self._domain_events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
