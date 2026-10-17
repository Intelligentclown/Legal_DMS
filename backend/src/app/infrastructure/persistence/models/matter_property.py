"""Canonical tenant-scoped Matter-to-Property participation persistence."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin


class MatterProperty(Base, AuditMixin):
    """One canonical Property participation link for a Matter within an Organization.

    This is intentionally a persistence-only association.  It does not encode
    a relationship type, status, ownership, or application lifecycle.
    """

    __tablename__ = "matter_properties"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_matter_properties_organization_id_id"),
        UniqueConstraint(
            "organization_id",
            "matter_id",
            "property_id",
            name="uq_matter_properties_organization_id_matter_id_property_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "matter_id"],
            ["matters.organization_id", "matters.id"],
            name="fk_matter_properties_organization_id_matters",
        ),
        ForeignKeyConstraint(
            ["organization_id", "property_id"],
            ["properties.organization_id", "properties.id"],
            name="fk_matter_properties_organization_id_properties",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    matter_id: Mapped[UUID] = mapped_column(index=True)
    property_id: Mapped[UUID] = mapped_column(index=True)
