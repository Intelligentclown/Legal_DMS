"""Tests for the notification framework: Notifier port + LoggingNotifier."""

from __future__ import annotations

import logging

import pytest

from app.application.interfaces.notifier import Notification, NotificationChannel, Notifier
from app.infrastructure.di.container import configure_container, container
from app.infrastructure.notifications.logging_notifier import LoggingNotifier


class TestLoggingNotifier:
    async def test_send_does_not_raise(self) -> None:
        notifier = LoggingNotifier()

        await notifier.send(
            Notification(recipient="user@example.com", title="Hi", body="Hello there")
        )

    async def test_send_logs_a_structured_entry(self, caplog: pytest.LogCaptureFixture) -> None:
        notifier = LoggingNotifier()

        with caplog.at_level(logging.INFO, logger="app.notifications"):
            await notifier.send(
                Notification(
                    recipient="user@example.com",
                    title="Document ready",
                    body="Your document is ready to download.",
                    channel=NotificationChannel.EMAIL,
                )
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.recipient == "user@example.com"
        assert record.title == "Document ready"
        assert record.channel == NotificationChannel.EMAIL


class TestConfigureContainer:
    def test_registers_notifier_as_logging_implementation(self) -> None:
        configure_container()

        resolved = container.resolve(Notifier)

        assert isinstance(resolved, LoggingNotifier)
