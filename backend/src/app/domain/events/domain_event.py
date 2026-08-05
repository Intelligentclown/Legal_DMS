"""Base type for domain events: things that happened (past tense) which other
parts of the system — event handlers, audit logging, notifications — may want
to react to. No framework imports; publishing is the EventBus port's job, not
the event's.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for domain events. Subclass and add event-specific fields.

    `kw_only=True` so subclasses can add their own required fields without
    running into dataclass "non-default argument follows default" ordering
    errors against this base's defaulted fields.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return type(self).__name__
