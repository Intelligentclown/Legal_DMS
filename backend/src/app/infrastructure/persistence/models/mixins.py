"""Reusable mixins for persistence models.

`AuditMixin` provides the standard audit trail every "important entity"
needs per the Stage 2 charter: created/updated timestamps, soft delete
(`deleted_at`), who created/updated the row, and a `version` counter for
optimistic locking. Every audited table gets the `version` column, but only
some opt into SQLAlchemy actually *enforcing* it via
`__mapper_args__ = {"version_id_col": version}` — turned on per-model where
concurrent edits are realistic (documented per model).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    version: Mapped[int] = mapped_column(default=1, server_default="1")

    @declared_attr
    def created_by(cls) -> Mapped[UUID | None]:
        return mapped_column(ForeignKey("users.id"), default=None)

    @declared_attr
    def updated_by(cls) -> Mapped[UUID | None]:
        return mapped_column(ForeignKey("users.id"), default=None)
