"""Property schema: Properties (land/real-estate records) and
PropertyOwners (ownership history, supporting multiple/partial/historical
owners per property).

`village_id` is denormalized directly onto `properties` (in addition to
being reachable via `address_id` -> `addresses.village_id`) specifically
so village-based property search doesn't require a join — a deliberate
trade-off documented in docs/Database.md's Risks section, not undone here.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin, OptimisticLockMixin


class Property(Base, AuditMixin, OptimisticLockMixin):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint(
            "property_type IN ('agricultural', 'residential', 'commercial', 'industrial', 'other')",
            name="property_type",
        ),
        CheckConstraint("area_value IS NULL OR area_value > 0", name="area_value_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    property_type: Mapped[str] = mapped_column(String(20), default="agricultural")
    survey_number: Mapped[str] = mapped_column(String(50), index=True)
    sub_division_number: Mapped[str | None] = mapped_column(String(50))
    area_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    area_unit: Mapped[str | None] = mapped_column(String(20))
    address_id: Mapped[UUID | None] = mapped_column(ForeignKey("addresses.id"))
    village_id: Mapped[UUID | None] = mapped_column(ForeignKey("villages.id"), index=True)
    registration_number: Mapped[str | None] = mapped_column(String(50), index=True)


class PropertyOwner(Base, AuditMixin):
    __tablename__ = "property_owners"
    __table_args__ = (
        CheckConstraint(
            "ownership_share IS NULL OR (ownership_share > 0 AND ownership_share <= 100)",
            name="ownership_share_range",
        ),
        CheckConstraint("to_date IS NULL OR to_date >= from_date", name="to_date_after_from_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    property_id: Mapped[UUID] = mapped_column(ForeignKey("properties.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    ownership_share: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ownership_type: Mapped[str] = mapped_column(String(50), default="owner")
    from_date: Mapped[date] = mapped_column()
    to_date: Mapped[date | None] = mapped_column()
