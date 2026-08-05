"""Workflow schema: the persisted counterpart to Stage 1's in-memory
`WorkflowEngine`/`WorkflowDefinition`/`Transition`
(`backend/src/app/application/workflow/engine.py`).

`WorkflowHistory.entity_id` is a polymorphic reference (`entity_type` +
`entity_id`, no FK constraint) so any entity — not just Matters — can have
a workflow tracked against it. Trade-off: no DB-level referential
integrity on `entity_id`; standard for this pattern, documented rather
than hidden (see docs/Database.md).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class WorkflowState(Base):
    __tablename__ = "workflow_states"
    __table_args__ = (UniqueConstraint("workflow_definition_id", "code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_definitions.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class WorkflowHistory(Base):
    __tablename__ = "workflow_history"
    __table_args__ = (
        Index("ix_workflow_history_entity_type_entity_id", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_definitions.id"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[UUID] = mapped_column()
    from_state_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflow_states.id"))
    to_state_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_states.id"))
    event: Mapped[str] = mapped_column(String(100))
    transitioned_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(String(1000))
