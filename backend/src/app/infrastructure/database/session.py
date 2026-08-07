"""Async SQLAlchemy engine/session management.

The engine is created lazily and cached so it's built once from validated
settings rather than at import time with whatever module-load-order happens
to be in effect. `get_db` is the FastAPI dependency every route/repository
uses to obtain a request-scoped `AsyncSession`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url, echo=settings.is_development, pool_pre_ping=True
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Commits on a clean exit (the request handler returned normally), rolls
    back on any exception, before the session closes. See ADR-0020 -- this is
    a deliberate policy, not incidental: repositories only `flush()` within
    the transaction; this dependency is what actually persists it.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
