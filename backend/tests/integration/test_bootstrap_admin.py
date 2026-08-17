"""Integration tests for T67's `run_bootstrap()` (`infrastructure/cli/bootstrap.py`),
against the real migrated Postgres schema via the shared `db_session` fixture
(`tests/conftest.py`) -- everything is rolled back in teardown.

Doesn't exercise `main()`/`_async_main()` directly (those own `input()`/
`getpass()`/session-factory/commit concerns that are process-level, not
business logic) -- `run_bootstrap()` is the testable core those wrap, and is
exactly what the approved T67 scope requires coverage for: "no existing
user -> admin created correctly with hashed password and Administrator
role" and "an existing user -> command exits cleanly without creating a
duplicate".
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cli.bootstrap import run_bootstrap
from app.infrastructure.persistence.models.identity import Role, User, UserRole
from app.infrastructure.security.password_hasher import verify_password


async def _make_user(db_session: AsyncSession, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": f"{uuid4()}@example.com",
        "full_name": "Existing User",
        "password_hash": "irrelevant-for-this-test",
        "is_active": True,
    }
    user = User(**{**defaults, **overrides})
    db_session.add(user)
    await db_session.flush()
    return user


class TestRunBootstrapNoExistingUser:
    async def test_creates_admin_with_hashed_password(self, db_session: AsyncSession) -> None:
        email = f"{uuid4()}@example.com"
        password = "correct horse battery staple"

        created = await run_bootstrap(db_session, email=email, password=password)

        assert created is not None
        assert created.email == email
        assert created.password_hash != password
        assert verify_password(password, created.password_hash or "") is True

    async def test_assigns_administrator_role(self, db_session: AsyncSession) -> None:
        created = await run_bootstrap(
            db_session, email=f"{uuid4()}@example.com", password="correct horse battery staple"
        )
        assert created is not None

        result = await db_session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == created.id)
        )
        assert list(result.scalars().all()) == ["Administrator"]

    async def test_creates_exactly_one_user(self, db_session: AsyncSession) -> None:
        await run_bootstrap(
            db_session, email=f"{uuid4()}@example.com", password="correct horse battery staple"
        )

        result = await db_session.execute(select(User))
        assert len(result.scalars().all()) == 1


class TestRunBootstrapExistingUser:
    async def test_returns_none_without_creating_duplicate(self, db_session: AsyncSession) -> None:
        await _make_user(db_session)

        result = await run_bootstrap(
            db_session, email=f"{uuid4()}@example.com", password="correct horse battery staple"
        )

        assert result is None
        remaining = await db_session.execute(select(User))
        assert len(remaining.scalars().all()) == 1

    async def test_does_not_touch_existing_user(self, db_session: AsyncSession) -> None:
        existing = await _make_user(db_session)

        await run_bootstrap(
            db_session, email=f"{uuid4()}@example.com", password="correct horse battery staple"
        )

        refreshed = await db_session.get(User, existing.id)
        assert refreshed is not None
        assert refreshed.email == existing.email
