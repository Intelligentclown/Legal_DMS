"""Logs each metric event as structured JSON to a dedicated `app.metrics`
logger channel. No real metrics backend (StatsD, Prometheus, CloudWatch)
wired yet -- same "log it structurally for now" posture as
`LoggingNotifier`/`LoggingAuditLogger`.

`tags` values are logged verbatim below -- no redaction -- so callers must
not put sensitive data in a tag.
"""

from __future__ import annotations

from app.application.interfaces.metrics import MetricsService
from app.infrastructure.logging.logger import get_logger

logger = get_logger("metrics")


class LoggingMetricsService(MetricsService):
    def increment(self, name: str, *, value: int = 1, tags: dict[str, str] | None = None) -> None:
        logger.info(
            "Metric recorded",
            extra={
                "metric_type": "counter",
                "metric_name": name,
                "value": value,
                "tags": tags or {},
            },
        )

    def gauge(self, name: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        logger.info(
            "Metric recorded",
            extra={
                "metric_type": "gauge",
                "metric_name": name,
                "value": value,
                "tags": tags or {},
            },
        )

    def record_duration(
        self, name: str, seconds: float, *, tags: dict[str, str] | None = None
    ) -> None:
        logger.info(
            "Metric recorded",
            extra={
                "metric_type": "duration",
                "metric_name": name,
                "value": seconds,
                "tags": tags or {},
            },
        )
