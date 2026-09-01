"""Organization: the tenant/security boundary (ADR/0021 S4 rule 43), per
ADR/0031 SS6.1-SS6.4 and T105's authorized scope.

Fields are deliberately minimal -- name and legal_name only, per ADR/0031
SS24.1 ("DERIVED -- name/legal-name near-certainly required", nothing else
specified). No lifecycle/status field, no uniqueness constraint on `name`
(neither is decided by any accepted ADR) -- inventing either would exceed
T105's authorized scope.

This table itself is the tenant root and is not scoped to another
Organization (ADR/0031 SS15). `users.organization_id` (see identity.py) is
the only other T105-authorized tenant-scoped column; RLS enforcement for
both tables is added by a dedicated migration, not expressed here.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin


class Organization(Base, AuditMixin):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    legal_name: Mapped[str | None] = mapped_column(String(255))
