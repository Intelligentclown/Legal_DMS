"""SQLAlchemy declarative base.

All future ORM models (in `infrastructure/persistence/`) inherit from this.
Kept separate from `session.py` so Alembic can import just the metadata
without pulling in engine/session construction.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
