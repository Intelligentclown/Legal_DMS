"""Audit logging port: records who did what, to what, for later review.
Concrete implementations live in `infrastructure/audit/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.application.interfaces.auth import CurrentUser


class AuditLogger(ABC):
    @abstractmethod
    async def record(
        self,
        actor: CurrentUser,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...
