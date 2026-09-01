"""Regression tests for `get_db()`'s commit/rollback transaction policy
(T42/T43, Stage 3 Phase 0 — see ADR-0020).

Exercises the real `get_db()` async generator directly, driving it exactly
the way FastAPI drives a generator dependency: advance past `yield` to get
the session, then either advance again (normal return -> commit) or
`athrow()` an exception into it (handler raised -> rollback). A test-only
fixture that bypasses `get_db()` couldn't prove this -- this is specifically
testing `get_db()`'s own post-yield code, not just SQLAlchemy's commit
semantics in general.

Uses its own isolated declarative base (not the app's `Base`) so this
test-only table never touches the real schema, same convention as
`test_sqlalchemy_repository.py`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.config import get_settings
from app.infrastructure.database.session import get_app_engine, get_db, get_engine


class _Base(DeclarativeBase):
    pass


class _Widget(_Base):
    __tablename__ = "_test_get_db_widgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str]


@pytest.fixture
async def _schema() -> AsyncGenerator[None, None]:
    # get_db() uses the app's cached get_engine()/get_app_engine() singletons,
    # not per-test engines -- clear both lru_caches so fresh engines get built
    # bound to *this* test's event loop (see AI_HANDOVER.md's "patterns
    # worth knowing" #3: a cached engine can't outlive the event loop it
    # was created on, and pytest-asyncio gives each test its own loop).
    # T105: get_db() itself now runs through get_app_engine() (the restricted
    # legal_dms_app role) -- this fixture still creates the throwaway table
    # via the unchanged get_engine() (admin role); legal_dms_app sees it
    # automatically via the RLS migration's ALTER DEFAULT PRIVILEGES.
    get_engine.cache_clear()
    get_app_engine.cache_clear()
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)
    except OperationalError:
        await engine.dispose()
        get_engine.cache_clear()
        pytest.skip("Postgres is not reachable — start it with `docker compose up -d`.")
        return

    try:
        async with get_app_engine().connect():
            pass
    except Exception:
        async with engine.begin() as conn:
            await conn.run_sync(_Base.metadata.drop_all)
        await engine.dispose()
        await get_app_engine().dispose()
        get_engine.cache_clear()
        get_app_engine.cache_clear()
        pytest.skip(
            "legal_dms_app is not reachable/provisioned — run `uv run provision-app-role` "
            "then `uv run alembic upgrade head`."
        )
        return

    yield

    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.drop_all)
    await engine.dispose()
    await get_app_engine().dispose()
    get_engine.cache_clear()
    get_app_engine.cache_clear()


async def _read_independently(widget_id: UUID) -> _Widget | None:
    """Reads via a brand-new engine/session, sharing nothing with whatever
    get_db() used -- proves durability across independent connections, not
    just visibility within the same uncommitted transaction."""
    engine = create_async_engine(get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        found = await session.get(_Widget, widget_id)
    await engine.dispose()
    return found


class TestGetDbCommitsOnSuccess:
    async def test_a_write_is_durably_visible_from_a_second_independent_session(
        self, _schema: None
    ) -> None:
        widget_id = uuid4()

        gen = get_db()
        session = await anext(gen)
        session.add(_Widget(id=widget_id, name="gizmo"))
        await session.flush()
        # Drive the generator past its yield point with no exception --
        # exactly what FastAPI does when the request handler returns
        # normally. This runs get_db()'s own post-yield commit.
        with pytest.raises(StopAsyncIteration):
            await anext(gen)

        found = await _read_independently(widget_id)

        assert found is not None
        assert found.name == "gizmo"


class TestGetDbRollsBackOnException:
    async def test_a_write_does_not_persist_if_the_request_raises(self, _schema: None) -> None:
        widget_id = uuid4()

        gen = get_db()
        session = await anext(gen)
        session.add(_Widget(id=widget_id, name="gizmo"))
        await session.flush()

        class _SimulatedRequestFailure(Exception):
            pass

        # Throw into the generator at its yield point -- exactly what
        # FastAPI does when the request handler raises. get_db()'s
        # except-block should roll back before re-raising.
        with pytest.raises(_SimulatedRequestFailure):
            await gen.athrow(_SimulatedRequestFailure("simulated handler failure"))

        found = await _read_independently(widget_id)

        assert found is None

    async def test_the_session_is_still_usable_for_rollback_before_it_closes(
        self, _schema: None
    ) -> None:
        """A weaker but more direct check: the except-block's rollback()
        call itself must not raise, and the original exception must be
        the one that propagates (not something from a broken rollback)."""
        gen = get_db()
        await anext(gen)

        class _SimulatedRequestFailure(Exception):
            pass

        with pytest.raises(_SimulatedRequestFailure, match="simulated"):
            await gen.athrow(_SimulatedRequestFailure("simulated handler failure"))


class TestPreviousTransactionBehaviorUnchanged:
    async def test_a_flushed_write_is_still_visible_within_the_same_session_before_commit(
        self, _schema: None
    ) -> None:
        """The pre-fix behavior this project's repository code always
        relied on -- flush() makes a write visible to a read in the *same*
        session even before commit -- must still hold after T42's fix."""
        widget_id = uuid4()

        gen = get_db()
        session = await anext(gen)
        session.add(_Widget(id=widget_id, name="gizmo"))
        await session.flush()

        found_in_same_session = await session.get(_Widget, widget_id)

        assert found_in_same_session is not None
        assert found_in_same_session.name == "gizmo"

        with pytest.raises(StopAsyncIteration):
            await anext(gen)

    async def test_a_session_with_no_writes_still_completes_cleanly(self, _schema: None) -> None:
        """A read-only request (nothing added/flushed) must still commit
        cleanly on exit -- commit() on a session with no pending changes
        is a safe no-op, not an error."""
        gen = get_db()
        await anext(gen)

        with pytest.raises(StopAsyncIteration):
            await anext(gen)
