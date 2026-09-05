"""Client schema: Addresses (shared by clients and, later, properties),
Clients, and ClientContacts.

`pan_number`/`aadhaar_number` are stored as plain columns with a format
CHECK constraint — encrypting/masking this PII at rest is an application-
layer concern for whichever future feature actually reads/writes client
records, not a schema-design decision; flagged here rather than silently
ignored.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.persistence.models.mixins import AuditMixin, OptimisticLockMixin


class Address(Base, AuditMixin):
    __tablename__ = "addresses"
    __table_args__ = (
        # CheckConstraint's `name=` is the *logical* name only — the
        # naming_convention (see infrastructure/database/base.py) combines
        # it with the table name into the final "ck_<table>_<name>", so
        # passing an already-prefixed name here would double it up.
        CheckConstraint(
            "address_type IN ('registered', 'mailing', 'property', 'other')",
            name="address_type",
        ),
        UniqueConstraint("organization_id", "id", name="uq_addresses_organization_id_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    line1: Mapped[str] = mapped_column(String(255))
    line2: Mapped[str | None] = mapped_column(String(255))
    # Partial granularity is intentional: not every address has village-level
    # detail (e.g. an out-of-state mailing address) -- only country is required.
    village_id: Mapped[UUID | None] = mapped_column(ForeignKey("villages.id"), index=True)
    taluka_id: Mapped[UUID | None] = mapped_column(ForeignKey("talukas.id"))
    district_id: Mapped[UUID | None] = mapped_column(ForeignKey("districts.id"))
    state_id: Mapped[UUID | None] = mapped_column(ForeignKey("states.id"))
    country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    address_type: Mapped[str] = mapped_column(String(20), default="registered")


class Client(Base, AuditMixin, OptimisticLockMixin):
    __tablename__ = "clients"
    __table_args__ = (
        CheckConstraint("client_type IN ('individual', 'organization')", name="client_type"),
        CheckConstraint("length(primary_phone) >= 7", name="primary_phone_length"),
        CheckConstraint(
            "pan_number IS NULL OR pan_number ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'",
            name="pan_number_format",
        ),
        CheckConstraint(
            "aadhaar_number IS NULL OR aadhaar_number ~ '^[0-9]{12}$'",
            name="aadhaar_number_format",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_type: Mapped[str] = mapped_column(String(20), default="individual")
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    primary_phone: Mapped[str] = mapped_column(String(20), index=True)
    primary_email: Mapped[str | None] = mapped_column(String(255), index=True)
    pan_number: Mapped[str | None] = mapped_column(String(10))
    aadhaar_number: Mapped[str | None] = mapped_column(String(12))
    address_id: Mapped[UUID | None] = mapped_column(ForeignKey("addresses.id"))
    notes: Mapped[str | None] = mapped_column(String(2000))


class ClientContact(Base, AuditMixin):
    __tablename__ = "client_contacts"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_client_contacts_organization_id_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    contact_name: Mapped[str] = mapped_column(String(255))
    relationship_type: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(default=False, server_default="false")
