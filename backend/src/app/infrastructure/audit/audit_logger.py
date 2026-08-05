"""Logs audit entries as structured JSON to a dedicated `app.audit` logger
channel. No database table yet — a queryable audit table would edge toward
"business entity" territory Stage 1's charter excludes; revisit once a real
audit-query need exists (see ADR/0007).
"""

from __future__ import annotations

from typing import Any

from app.application.interfaces.audit import AuditLogger
from app.application.interfaces.auth import CurrentUser
from app.infrastructure.logging.logger import get_logger

logger = get_logger("audit")


class LoggingAuditLogger(AuditLogger):
    async def record(
        self,
        actor: CurrentUser,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        logger.info(
            "Audit event",
            extra={
                "actor_id": actor.id,
                "actor_display_name": actor.display_name,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "metadata": metadata or {},
            },
        )
