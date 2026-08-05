"""Geography schema: a Country -> State -> District -> Taluka -> Village
administrative hierarchy, matching the Indian (Gujarat-specific) land-record
structure implied by the survey-number/village-search indexing requirements
and the Gujarat-districts seed data.

No `AuditMixin` — these are reference/lookup data, not audited business
records (same treatment as `matter_types`, `document_types`, etc.
elsewhere in this schema).
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    iso_code: Mapped[str] = mapped_column(String(3), unique=True)


class State(Base):
    __tablename__ = "states"
    __table_args__ = (UniqueConstraint("country_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(10))


class District(Base):
    __tablename__ = "districts"
    __table_args__ = (UniqueConstraint("state_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    state_id: Mapped[UUID] = mapped_column(ForeignKey("states.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))


class Taluka(Base):
    __tablename__ = "talukas"
    __table_args__ = (UniqueConstraint("district_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("districts.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))


class Village(Base):
    __tablename__ = "villages"
    __table_args__ = (UniqueConstraint("taluka_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    taluka_id: Mapped[UUID] = mapped_column(ForeignKey("talukas.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
