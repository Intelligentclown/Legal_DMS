"""Tests for the audit logging framework."""

from __future__ import annotations

import logging

import pytest

from app.application.interfaces.audit import AuditLogger
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.audit.audit_logger import LoggingAuditLogger
from app.infrastructure.di.container import configure_container, container


class TestLoggingAuditLogger:
    async def test_record_does_not_raise(self) -> None:
        audit_logger = LoggingAuditLogger()

        await audit_logger.record(
            actor=CurrentUser(),
            action="matter.created",
            resource_type="Matter",
            resource_id="123",
        )

    async def test_record_logs_a_structured_entry(self, caplog: pytest.LogCaptureFixture) -> None:
        audit_logger = LoggingAuditLogger()
        actor = CurrentUser(id="u1", display_name="Jane", is_authenticated=True)

        with caplog.at_level(logging.INFO, logger="app.audit"):
            await audit_logger.record(
                actor=actor,
                action="matter.created",
                resource_type="Matter",
                resource_id="123",
                metadata={"title": "New matter"},
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.actor_id == "u1"
        assert record.action == "matter.created"
        assert record.resource_type == "Matter"
        assert record.resource_id == "123"
        assert record.metadata == {"title": "New matter"}

    async def test_record_defaults_metadata_to_empty_dict(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        audit_logger = LoggingAuditLogger()

        with caplog.at_level(logging.INFO, logger="app.audit"):
            await audit_logger.record(actor=CurrentUser(), action="x", resource_type="Y")

        assert caplog.records[0].metadata == {}


class TestConfigureContainer:
    def test_registers_audit_logger_as_logging_implementation(self) -> None:
        configure_container()

        assert isinstance(container.resolve(AuditLogger), LoggingAuditLogger)
