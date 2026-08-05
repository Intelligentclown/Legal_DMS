"""Logs notifications instead of actually sending them — the Stage 1
default. A real channel (email/SMS/push provider) satisfies the same
`Notifier` port later without touching any caller.
"""

from __future__ import annotations

from app.application.interfaces.notifier import Notification, Notifier
from app.infrastructure.logging.logger import get_logger

logger = get_logger("notifications")


class LoggingNotifier(Notifier):
    async def send(self, notification: Notification) -> None:
        logger.info(
            "Notification sent",
            extra={
                "channel": notification.channel,
                "recipient": notification.recipient,
                "title": notification.title,
            },
        )
