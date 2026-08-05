"""System, configuration, AI, and plugin schema — the last table group.

Several of these tables are persisted counterparts to Stage 1 in-memory
frameworks, matching their shapes so a future implementation can satisfy
the existing port without changing it (same pattern as `audit_logs`
mirroring `AuditLogger`, see ADR-0009):

- `feature_flags` mirrors `Settings.feature_flags` — a future
  `SqlAlchemyFeatureFlagProvider` would read this table instead of env vars.
- `background_jobs` mirrors `JobRecord`/`JobStatus`
  (`application/interfaces/job_queue.py`).
- `system_events` is an event log a future persisted `EventBus` could
  write to, for history/replay — not a functional change to the
  publish/subscribe mechanism itself.
- `plugin_registry` persists enable/disable + config state for modules
  already registered in code via Stage 1's `ModuleRegistry`
  (`infrastructure/modules/registry.py`) — the code registry stays the
  source of truth for *what modules exist*; this table is where a future
  admin feature could toggle *whether they're active*.

`ai_requests`/`ai_responses` are deliberately minimal/generic (JSONB-free,
just a prompt/response pair) — no AI feature exists yet to justify a
richer shape; kept incomplete rather than guessed wrong.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ApplicationSetting(Base):
    __tablename__ = "application_settings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(String(1000))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    description: Mapped[str | None] = mapped_column(String(1000))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class AiRequest(Base):
    __tablename__ = "ai_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[UUID | None] = mapped_column()
    request_type: Mapped[str] = mapped_column(String(100))
    prompt: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")


class AiResponse(Base):
    __tablename__ = "ai_responses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ai_request_id: Mapped[UUID] = mapped_column(ForeignKey("ai_requests.id"), index=True)
    response_text: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(100))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PluginRegistryEntry(Base):
    __tablename__ = "plugin_registry"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    version: Mapped[str] = mapped_column(String(50))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    config: Mapped[dict | None] = mapped_column(JSONB)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BackgroundJobRecord(Base):
    __tablename__ = "background_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    payload: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
