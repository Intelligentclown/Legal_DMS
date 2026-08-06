"""Performance metrics port: records counters, gauges, and durations for
later observation. Concrete implementations live in `infrastructure/`.

Standalone port, not wired into any route, middleware, or bus dispatch yet
-- same category as `Cache`: a reusable capability proven with its own
default implementation, waiting for a future feature (or a future decision
to instrument `CommandBus`/`QueryBus` dispatch, HTTP middleware, etc.) to
actually call it.

`tags` values are not guaranteed to be redacted by any implementation (see
`LoggingMetricsService`) -- don't put sensitive data (emails, document IDs,
etc.) in a tag.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager


class MetricsService(ABC):
    @abstractmethod
    def increment(self, name: str, *, value: int = 1, tags: dict[str, str] | None = None) -> None:
        """Increase a counter metric by `value` (default 1)."""
        ...

    @abstractmethod
    def gauge(self, name: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        """Record a point-in-time value for `name`, replacing any previous
        reading."""
        ...

    @abstractmethod
    def record_duration(
        self, name: str, seconds: float, *, tags: dict[str, str] | None = None
    ) -> None:
        """Record how long an operation named `name` took, in seconds."""
        ...

    @contextmanager
    def timer(self, name: str, *, tags: dict[str, str] | None = None) -> Iterator[None]:
        """Measure the wrapped block's wall-clock duration and record it via
        `record_duration`, even if the block raises.

        Concrete convenience built on the abstract methods above -- same
        pattern as `EventBus.publish_all()` -- so implementations only need
        to provide the three primitives.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            self.record_duration(name, time.perf_counter() - start, tags=tags)
