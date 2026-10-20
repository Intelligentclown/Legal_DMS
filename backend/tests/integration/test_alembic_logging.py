"""Regression coverage for in-process Alembic logging configuration."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from app.application.interfaces.auth import CurrentUser
from app.infrastructure.audit.audit_logger import LoggingAuditLogger
from app.infrastructure.cli.fresh_install_provenance import establish_fresh_installation
from tests.support.synthetic_migration import (
    alembic_current_branch,
    drop_disposable_database,
    provision_empty_disposable_database,
)

HEAD = "b155caa6d4e1"


class _AuditCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def blank_database() -> Iterator[tuple[str, str]]:
    url, name = provision_empty_disposable_database("legal_dms_t169_logging")
    try:
        yield url, name
    finally:
        drop_disposable_database(name)


@pytest.mark.asyncio
async def test_in_process_alembic_preserves_existing_audit_logger_and_cli_current(
    blank_database: tuple[str, str],
) -> None:
    """Alembic preserves app.audit while configuring its own loggers."""
    url, _name = blank_database
    logger = logging.getLogger("app.audit")
    capture = _AuditCapture()
    original_disabled = logger.disabled
    logger.disabled = False
    logger.addHandler(capture)
    try:
        installation_id = await establish_fresh_installation(url)

        assert installation_id
        assert logger.disabled is False

        await LoggingAuditLogger().record(
            CurrentUser(id="t169", display_name="T169", is_authenticated=True),
            action="t169_migration_logging_check",
            resource_type="test",
        )

        assert [record.name for record in capture.records] == ["app.audit"]
        assert alembic_current_branch(url) == HEAD
    finally:
        logger.removeHandler(capture)
        logger.disabled = original_disabled
