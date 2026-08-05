"""Tests for the Stage 1 domain foundation: AggregateRoot, DomainEvent, Result."""

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.domain.common.entity import AggregateRoot, Entity
from app.domain.common.result import Result
from app.domain.events.domain_event import DomainEvent


class TestEntity:
    def test_entities_are_equal_by_id(self) -> None:
        shared_id = uuid4()

        class Widget(Entity):
            def __init__(self, id_):
                self.id = id_

        assert Widget(shared_id) == Widget(shared_id)
        assert Widget(uuid4()) != Widget(uuid4())


@dataclass(frozen=True, kw_only=True)
class SomethingHappened(DomainEvent):
    payload: str


class TestAggregateRoot:
    def test_add_event_then_pull_returns_it_and_clears(self) -> None:
        class Widget(AggregateRoot):
            def __init__(self):
                super().__init__()
                self.id = uuid4()

        widget = Widget()
        widget.add_event(SomethingHappened(payload="hello"))

        events = widget.pull_events()

        assert len(events) == 1
        assert events[0].payload == "hello"
        assert widget.pull_events() == []

    def test_domain_event_type_reflects_subclass_name(self) -> None:
        event = SomethingHappened(payload="x")

        assert event.event_type == "SomethingHappened"


class TestResult:
    def test_ok_carries_value_and_is_success(self) -> None:
        result: Result[int, str] = Result.ok(42)

        assert result.is_success
        assert not result.is_failure
        assert result.value == 42

    def test_fail_carries_error_and_is_failure(self) -> None:
        result: Result[int, str] = Result.fail("bad input")

        assert result.is_failure
        assert not result.is_success
        assert result.error == "bad input"

    def test_accessing_value_on_failed_result_raises(self) -> None:
        result: Result[int, str] = Result.fail("bad input")

        with pytest.raises(ValueError, match="failed Result"):
            _ = result.value

    def test_accessing_error_on_successful_result_raises(self) -> None:
        result: Result[int, str] = Result.ok(1)

        with pytest.raises(ValueError, match="successful Result"):
            _ = result.error
