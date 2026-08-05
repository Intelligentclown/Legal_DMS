"""Notification port: sends a notification to a recipient over some channel
(email, SMS, in-app, ...). Concrete implementations live in
`infrastructure/notifications/`.

Distinct from the frontend's toast UI (`NotificationProvider` in the React
app) — this is server-side, for things that need to reach a user outside
the currently-open app window (e.g. "your document is ready").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"


@dataclass(frozen=True, slots=True)
class Notification:
    recipient: str
    title: str
    body: str
    channel: NotificationChannel = NotificationChannel.IN_APP


class Notifier(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> None: ...
