"""Tests for the performance metrics framework."""

from __future__ import annotations

import logging

import pytest

from app.application.interfaces.metrics import MetricsService
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.metrics.logging_metrics_service import LoggingMetricsService


class TestLoggingMetricsServiceIncrement:
    def test_increment_logs_a_structured_entry(self, caplog: pytest.LogCaptureFixture) -> None:
        metrics = LoggingMetricsService()

        with caplog.at_level(logging.INFO, logger="app.metrics"):
            metrics.increment("matters.created")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.metric_type == "counter"
        assert record.metric_name == "matters.created"
        assert record.value == 1
        assert record.tags == {}

    def test_increment_accepts_an_explicit_value_and_tags(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        metrics = LoggingMetricsService()

        with caplog.at_level(logging.INFO, logger="app.metrics"):
            metrics.increment("matters.created", value=5, tags={"region": "gj"})

        assert caplog.records[0].value == 5
        assert caplog.records[0].tags == {"region": "gj"}


class TestLoggingMetricsServiceGauge:
    def test_gauge_logs_a_structured_entry(self, caplog: pytest.LogCaptureFixture) -> None:
        metrics = LoggingMetricsService()

        with caplog.at_level(logging.INFO, logger="app.metrics"):
            metrics.gauge("queue.depth", 42.0)

        record = caplog.records[0]
        assert record.metric_type == "gauge"
        assert record.metric_name == "queue.depth"
        assert record.value == 42.0
        assert record.tags == {}


class TestLoggingMetricsServiceRecordDuration:
    def test_record_duration_logs_a_structured_entry(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        metrics = LoggingMetricsService()

        with caplog.at_level(logging.INFO, logger="app.metrics"):
            metrics.record_duration("request.latency", 0.125, tags={"route": "/health"})

        record = caplog.records[0]
        assert record.metric_type == "duration"
        assert record.metric_name == "request.latency"
        assert record.value == 0.125
        assert record.tags == {"route": "/health"}


class TestMetricsServiceTimer:
    def test_timer_records_a_duration_on_normal_exit(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        metrics = LoggingMetricsService()

        with caplog.at_level(logging.INFO, logger="app.metrics"), metrics.timer("block.duration"):
            pass

        record = caplog.records[0]
        assert record.metric_type == "duration"
        assert record.metric_name == "block.duration"
        assert record.value >= 0

    def test_timer_records_a_duration_and_reraises_on_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        metrics = LoggingMetricsService()

        with (
            caplog.at_level(logging.INFO, logger="app.metrics"),
            pytest.raises(RuntimeError, match="boom"),
            metrics.timer("block.duration"),
        ):
            raise RuntimeError("boom")

        assert len(caplog.records) == 1
        assert caplog.records[0].metric_name == "block.duration"


class TestConfigureContainer:
    def test_registers_metrics_service_as_logging_implementation(self) -> None:
        configure_container()

        assert isinstance(container.resolve(MetricsService), LoggingMetricsService)

    def test_metrics_service_is_registered_singleton(self) -> None:
        configure_container()

        first = container.resolve(MetricsService)
        second = container.resolve(MetricsService)

        assert first is second
