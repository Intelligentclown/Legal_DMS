"""Matter schema: MatterTypes/MatterStatuses (lookup tables) and Matters
itself — the central record tying together a client, optionally a
property, and everything else in the schema (documents, financials,
tasks, appointments) references a matter.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin, OptimisticLockMixin


class MatterType(Base):
    __tablename__ = "matter_types"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class MatterStatus(Base):
    __tablename__ = "matter_statuses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class Matter(Base, AuditMixin, OptimisticLockMixin):
    __tablename__ = "matters"
    __table_args__ = (
        CheckConstraint(
            "closed_at IS NULL OR closed_at >= opened_at", name="closed_at_after_opened_at"
        ),
        UniqueConstraint("organization_id", "id", name="uq_matters_organization_id_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    matter_number: Mapped[str] = mapped_column(String(50), unique=True)
    matter_type_id: Mapped[UUID] = mapped_column(ForeignKey("matter_types.id"), index=True)
    matter_status_id: Mapped[UUID] = mapped_column(ForeignKey("matter_statuses.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    property_id: Mapped[UUID | None] = mapped_column(ForeignKey("properties.id"), index=True)
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(2000))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
