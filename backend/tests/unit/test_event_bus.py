"""Tests for the in-memory event bus, including a round trip through
AggregateRoot.pull_events() — the intended real usage pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.application.interfaces.event_bus import EventBus
from app.domain.common.entity import AggregateRoot
from app.domain.events.domain_event import DomainEvent
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.events.in_memory_event_bus import InMemoryEventBus


@dataclass(frozen=True, kw_only=True)
class _ThingHappened(DomainEvent):
    payload: str


@dataclass(frozen=True, kw_only=True)
class _OtherThingHappened(DomainEvent):
    pass


class TestInMemoryEventBus:
    async def test_publish_invokes_subscribed_handler(self) -> None:
        bus = InMemoryEventBus()
        received: list[_ThingHappened] = []

        async def handler(event: _ThingHappened) -> None:
            received.append(event)

        bus.subscribe(_ThingHappened, handler)
        event = _ThingHappened(payload="hello")

        await bus.publish(event)

        assert received == [event]

    async def test_publish_invokes_all_subscribed_handlers(self) -> None:
        bus = InMemoryEventBus()
        calls: list[str] = []

        async def handler_a(event: _ThingHappened) -> None:
            calls.append("a")

        async def handler_b(event: _ThingHappened) -> None:
            calls.append("b")

        bus.subscribe(_ThingHappened, handler_a)
        bus.subscribe(_ThingHappened, handler_b)

        await bus.publish(_ThingHappened(payload="x"))

        assert sorted(calls) == ["a", "b"]

    async def test_publish_with_no_subscribers_does_not_raise(self) -> None:
        bus = InMemoryEventBus()

        await bus.publish(_ThingHappened(payload="nobody listening"))

    async def test_handlers_only_receive_their_own_event_type(self) -> None:
        bus = InMemoryEventBus()
        received: list[DomainEvent] = []

        async def handler(event: _ThingHappened) -> None:
            received.append(event)

        bus.subscribe(_ThingHappened, handler)

        await bus.publish(_OtherThingHappened())

        assert received == []

    async def test_publish_all_dispatches_every_event(self) -> None:
        bus = InMemoryEventBus()
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        bus.subscribe(_ThingHappened, handler)
        bus.subscribe(_OtherThingHappened, handler)

        await bus.publish_all([_ThingHappened(payload="1"), _OtherThingHappened()])

        assert len(received) == 2

    async def test_handler_exception_propagates(self) -> None:
        bus = InMemoryEventBus()

        async def failing_handler(event: _ThingHappened) -> None:
            raise RuntimeError("boom")

        bus.subscribe(_ThingHappened, failing_handler)

        with pytest.raises(RuntimeError, match="boom"):
            await bus.publish(_ThingHappened(payload="x"))


class TestAggregateRootToEventBusRoundTrip:
    async def test_aggregate_events_can_be_pulled_and_published(self) -> None:
        class Widget(AggregateRoot):
            def __init__(self) -> None:
                super().__init__()
                self.id = uuid4()

        widget = Widget()
        widget.add_event(_ThingHappened(payload="created"))

        bus = InMemoryEventBus()
        received: list[_ThingHappened] = []

        async def handler(event: _ThingHappened) -> None:
            received.append(event)

        bus.subscribe(_ThingHappened, handler)

        await bus.publish_all(widget.pull_events())

        assert [e.payload for e in received] == ["created"]
        assert widget.pull_events() == []


class TestConfigureContainer:
    def test_registers_event_bus_resolvable_as_in_memory_implementation(self) -> None:
        configure_container()

        resolved = container.resolve(EventBus)

        assert isinstance(resolved, InMemoryEventBus)
