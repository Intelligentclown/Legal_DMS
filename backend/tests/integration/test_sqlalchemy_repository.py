"""Integration tests for the generic SqlAlchemyRepository, run against a
real Postgres instance (`docker compose up -d` — see DevelopmentGuide.md).
Skipped automatically if Postgres isn't reachable, so `pytest` still runs
cleanly without Docker.

Uses its own isolated declarative base (not the app's `Base`) so this
test-only table never touches the real schema or shows up in Alembic
autogenerate diffs.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.config import get_settings
from app.infrastructure.persistence.sqlalchemy_repository import SqlAlchemyRepository


class _TestBase(DeclarativeBase):
    pass


class _TestItem(_TestBase):
    __tablename__ = "_test_repository_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str]


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # A fresh engine per test, not the app's cached get_engine() singleton —
    # pytest-asyncio gives each test function its own event loop, and an
    # asyncpg connection pool can't outlive the loop it was created on.
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_TestBase.metadata.create_all)
    except OperationalError:
        await engine.dispose()
        pytest.skip("Postgres is not reachable — start it with `docker compose up -d`.")
        return

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(_TestBase.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def repository(db_session: AsyncSession) -> SqlAlchemyRepository[_TestItem]:
    return SqlAlchemyRepository(db_session, _TestItem)


class TestSqlAlchemyRepository:
    async def test_add_then_get_by_id_round_trips(
        self, repository: SqlAlchemyRepository[_TestItem], db_session: AsyncSession
    ) -> None:
        item = _TestItem(id=uuid4(), name="widget")

        await repository.add(item)
        await db_session.commit()

        found = await repository.get_by_id(item.id)

        assert found is not None
        assert found.name == "widget"

    async def test_get_by_id_returns_none_when_missing(
        self, repository: SqlAlchemyRepository[_TestItem]
    ) -> None:
        assert await repository.get_by_id(uuid4()) is None

    async def test_count_reflects_rows_added(
        self, repository: SqlAlchemyRepository[_TestItem], db_session: AsyncSession
    ) -> None:
        assert await repository.count() == 0

        for i in range(4):
            await repository.add(_TestItem(id=uuid4(), name=f"item-{i}"))
        await db_session.commit()

        assert await repository.count() == 4

    async def test_list_respects_limit(
        self, repository: SqlAlchemyRepository[_TestItem], db_session: AsyncSession
    ) -> None:
        for i in range(3):
            await repository.add(_TestItem(id=uuid4(), name=f"item-{i}"))
        await db_session.commit()

        results = await repository.list(limit=2)

        assert len(results) == 2

    async def test_update_persists_changes(
        self, repository: SqlAlchemyRepository[_TestItem], db_session: AsyncSession
    ) -> None:
        item = _TestItem(id=uuid4(), name="original")
        await repository.add(item)
        await db_session.commit()

        item.name = "renamed"
        await repository.update(item)
        await db_session.commit()

        found = await repository.get_by_id(item.id)
        assert found is not None
        assert found.name == "renamed"

    async def test_delete_removes_the_row(
        self, repository: SqlAlchemyRepository[_TestItem], db_session: AsyncSession
    ) -> None:
        item = _TestItem(id=uuid4(), name="to-delete")
        await repository.add(item)
        await db_session.commit()

        await repository.delete(item.id)
        await db_session.commit()

        assert await repository.get_by_id(item.id) is None
