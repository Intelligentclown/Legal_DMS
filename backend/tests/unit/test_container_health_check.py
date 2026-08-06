"""Tests for the container health check."""

from __future__ import annotations

import pytest

from app.infrastructure.di.container import Container, configure_container, container
from app.infrastructure.di.health_check import (
    ContainerHealthCheckError,
    assert_container_healthy,
    check_container_health,
)


class _Widget:
    pass


class _BrokenWidget:
    def __init__(self) -> None:
        raise ValueError("boom")


class TestCheckContainerHealth:
    def test_a_healthy_container_reports_no_failures(self) -> None:
        c = Container()
        c.register(_Widget, _Widget)

        failures = check_container_health(c)

        assert failures == []

    def test_a_broken_factory_is_reported_not_raised(self) -> None:
        c = Container()
        c.register(_BrokenWidget, _BrokenWidget)

        failures = check_container_health(c)

        assert len(failures) == 1
        assert failures[0].interface is _BrokenWidget
        assert isinstance(failures[0].error, ValueError)

    def test_multiple_broken_factories_are_all_reported(self) -> None:
        c = Container()
        c.register(_Widget, _Widget)
        c.register(_BrokenWidget, _BrokenWidget)

        failures = check_container_health(c)

        assert {failure.interface for failure in failures} == {_BrokenWidget}

    def test_an_empty_container_reports_no_failures(self) -> None:
        c = Container()

        assert check_container_health(c) == []


class TestAssertContainerHealthy:
    def test_a_healthy_container_does_not_raise(self) -> None:
        c = Container()
        c.register(_Widget, _Widget)

        assert_container_healthy(c)

    def test_a_broken_factory_raises_with_the_failure_listed(self) -> None:
        c = Container()
        c.register(_BrokenWidget, _BrokenWidget)

        with pytest.raises(ContainerHealthCheckError) as exc_info:
            assert_container_healthy(c)

        assert exc_info.value.failures[0].interface is _BrokenWidget
        assert "boom" in str(exc_info.value)


class TestRealAppContainer:
    def test_the_real_configure_container_produces_a_healthy_container(self) -> None:
        configure_container()

        assert_container_healthy(container)
