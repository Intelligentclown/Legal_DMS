"""Centralized logging configuration.

Provides one place that wires up console + rotating file handlers with a
structured (JSON) formatter, so every module gets consistent, leveled,
machine-parseable logs by calling `configure_logging()` once at startup and
`get_logger(__name__)` everywhere else.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.infrastructure.config import Settings

_LOGGER_NAMESPACE = "app"
_RESERVED_LOG_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)


class JsonFormatter(logging.Formatter):
    """Renders each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED_LOG_RECORD_ATTRS
        }
        if extras:
            payload["extra"] = extras

        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    """Configure the `app` logger tree. Safe to call multiple times."""
    logger = logging.getLogger(_LOGGER_NAMESPACE)
    logger.handlers.clear()
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger nested under the `app` namespace, e.g. `app.presentation.api.health`."""
    return logging.getLogger(f"{_LOGGER_NAMESPACE}.{name}")
