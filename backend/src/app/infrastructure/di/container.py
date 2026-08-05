"""A minimal, hand-rolled dependency injection container.

Not a framework — a small registry mapping a type to a factory callable that
produces it, with optional singleton caching. It exists so services can
declare what they depend on without manually instantiating concrete
implementations inside business code, and so any registered implementation
can be swapped for another (e.g. a fake in tests) without touching callers.

FastAPI's own `Depends()` remains how HTTP routes receive most dependencies
day to day — `presentation/api/deps.py` is built on top of this container for
things with simple (singleton) lifecycles, like `Settings`. Request-scoped
resources with teardown (the DB session) stay on FastAPI's native generator
`Depends()` pattern directly — the container isn't meant to replace that,
it complements it for everything else (services, ports/implementations used
outside a request too, e.g. background jobs or event handlers).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.interfaces.event_bus import EventBus
from app.application.interfaces.job_queue import JobQueue
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.events.in_memory_event_bus import InMemoryEventBus
from app.infrastructure.jobs.in_memory_job_queue import InMemoryJobQueue


class ContainerError(Exception):
    """Raised when resolving a type that was never registered."""


class Container:
    def __init__(self) -> None:
        self._factories: dict[type, Callable[[], Any]] = {}
        self._singletons: dict[type, bool] = {}
        self._instances: dict[type, Any] = {}

    def register[T](
        self, interface: type[T], factory: Callable[[], T], *, singleton: bool = True
    ) -> None:
        self._factories[interface] = factory
        self._singletons[interface] = singleton
        self._instances.pop(interface, None)

    def resolve[T](self, interface: type[T]) -> T:
        if interface not in self._factories:
            raise ContainerError(f"No registration found for {interface!r}")

        if self._singletons[interface]:
            if interface not in self._instances:
                self._instances[interface] = self._factories[interface]()
            return self._instances[interface]

        return self._factories[interface]()

    def is_registered(self, interface: type) -> bool:
        return interface in self._factories

    def override[T](self, interface: type[T], instance: T) -> None:
        """Force-set a resolved instance directly. For tests swapping in fakes."""
        self._factories[interface] = lambda: instance
        self._singletons[interface] = True
        self._instances[interface] = instance

    def reset(self) -> None:
        """Clear all registrations. For test isolation."""
        self._factories.clear()
        self._singletons.clear()
        self._instances.clear()


container = Container()


def configure_container() -> None:
    """Register the app's core services. Called once at startup — see `main.py`."""
    from app.workers.registry import registry as job_registry

    container.register(Settings, get_settings)
    container.register(EventBus, InMemoryEventBus)
    container.register(JobQueue, lambda: InMemoryJobQueue(job_registry.jobs))
