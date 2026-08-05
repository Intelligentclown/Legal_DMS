"""SQLAlchemy declarative base.

All future ORM models (in `infrastructure/persistence/`) inherit from this.
Kept separate from `session.py` so Alembic can import just the metadata
without pulling in engine/session construction.

`naming_convention` is set once here so every constraint/index Alembic
autogenerates from any model gets a consistent, predictable name
(`ix_<table>_<column>`, `uq_<table>_<column>`, `fk_<table>_<column>_<ref>`,
`ck_<table>_<name>`, `pk_<table>`) instead of SQLAlchemy's default
auto-generated names, which vary and are awkward to reference in later
migrations (e.g. to drop a constraint by name).
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
