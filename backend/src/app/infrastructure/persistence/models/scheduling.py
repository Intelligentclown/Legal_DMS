"""Scheduling & tagging schema: Tasks, Appointments, Tags, MatterTags."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin


class Task(Base, AuditMixin):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    matter_id: Mapped[UUID | None] = mapped_column(ForeignKey("matters.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(2000))
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="open")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Appointment(Base, AuditMixin):
    __tablename__ = "appointments"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="ends_at_after_starts_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    matter_id: Mapped[UUID | None] = mapped_column(ForeignKey("matters.id"), index=True)
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="scheduled")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str | None] = mapped_column(String(20))


class MatterTag(Base):
    __tablename__ = "matter_tags"
    __table_args__ = (UniqueConstraint("matter_id", "tag_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    matter_id: Mapped[UUID] = mapped_column(ForeignKey("matters.id"), index=True)
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("tags.id"), index=True)
