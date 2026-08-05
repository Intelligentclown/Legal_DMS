"""Activity, audit, and notification schema.

`activity_logs` and `audit_logs` both use the polymorphic `entity_type` +
`entity_id` / `resource_type` + `resource_id` pattern (no FK constraint) —
same trade-off as `workflow_history`, documented in docs/Database.md.

`audit_logs` mirrors Stage 1's `AuditLogger.record()` signature
(`backend/src/app/application/interfaces/audit.py`) exactly, so a future
`SqlAlchemyAuditLogger` implementation can read/write this table without
the port itself changing. This table directly reverses ADR-0007 (which
deferred a DB-backed audit table) — see ADR-0009 for why that reversal is
correct now.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_logs_entity_type_entity_id", "entity_type", "entity_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[UUID] = mapped_column()
    action: Mapped[str] = mapped_column(String(100))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    details: Mapped[dict | None] = mapped_column(JSONB)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_resource_type_resource_id", "resource_type", "resource_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    # Python attribute name avoids shadowing SQLAlchemy's own `Base.metadata`
    # class attribute; the actual DB column is still named "metadata" to
    # match AuditLogger.record()'s `metadata` parameter exactly.
    audit_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_recipient_id_is_read", "recipient_id", "is_read"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(String(2000))
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    is_read: Mapped[bool] = mapped_column(default=False, server_default="false")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
