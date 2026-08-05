"""Shared pytest fixtures for the backend test suite."""

from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.config import get_settings
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """A session against the real migrated schema (not a throwaway table set
    like the Stage 1 repository tests use). Everything a test does is rolled
    back in teardown, so no test leaves data behind regardless of pass/fail.

    A fresh engine per test, not a cached singleton — pytest-asyncio gives
    each test function its own event loop, and an asyncpg connection pool
    can't outlive the loop it was created on (see
    tests/integration/test_sqlalchemy_repository.py for where this was
    first hit).

    Requires `docker compose up -d` + `alembic upgrade head`; skips
    gracefully if Postgres isn't reachable.
    """
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect():
            pass
    except OperationalError:
        await engine.dispose()
        pytest.skip("Postgres is not reachable — start it with `docker compose up -d`.")
        return

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()
