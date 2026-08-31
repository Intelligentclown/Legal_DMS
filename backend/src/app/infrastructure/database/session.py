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
    """The admin/owning-role engine (`settings.database_url`) -- used by
    Alembic, `bootstrap.py`, and the new T105 CLIs (`provision_app_role.py`,
    `reconcile_organizations.py`). Not used by the live app's `get_db()`
    (see `get_app_engine()` below) -- see T105's plan for why these are
    deliberately two separate roles/engines, not one.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url, echo=settings.is_development, pool_pre_ping=True
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


@lru_cache
def get_app_engine() -> AsyncEngine:
    """T105/ADR-0021: the non-owning `legal_dms_app`-role engine
    (`settings.app_database_url`) -- used only by `get_db()`, the live app's
    request-serving dependency, so `FORCE`d RLS on `organizations`/`users`
    is a genuine backstop for real traffic, not a no-op for a table-owning
    connection. Cached the same way `get_engine()` is -- an async engine
    can't outlive the event loop it was created on, so tests that need a
    fresh one per event loop must clear this cache too (see
    `test_get_db_transaction_policy.py`).
    """
    settings = get_settings()
    return create_async_engine(
        settings.app_database_url, echo=settings.is_development, pool_pre_ping=True
    )


def get_app_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_app_engine(), expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Commits on a clean exit (the request handler returned normally), rolls
    back on any exception, before the session closes. See ADR-0020 -- this is
    a deliberate policy, not incidental: repositories only `flush()` within
    the transaction; this dependency is what actually persists it.

    T105: sourced from `get_app_session_factory()` (the restricted
    `legal_dms_app` role), not `get_session_factory()` -- every dependent
    that also asks for `DBSessionDep` within the same request (including
    `JwtAuthenticationProvider`, per `presentation/api/deps.py`) receives
    this exact session/transaction, which is what lets the tenant-context
    GUCs `JwtAuthenticationProvider` sets actually apply to this request's
    later queries (see ADR/0021's connection-pool/session-GUC obligation).
    """
    session_factory = get_app_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """Same commit/rollback policy as `get_db()`, but sourced from
    `get_session_factory()` (the admin/owning role, unaffected by RLS).

    T105 discovery, not anticipated by the original plan: `AuthService`
    (T50/T58 -- login/refresh/logout, unmodified by this task) looks up a
    `User` by email (login) or a stored `user_id` (refresh) *before* any
    tenant context can possibly exist -- there is no JWT yet, so
    `JwtAuthenticationProvider`'s self-row RLS carve-out cannot apply, and a
    plain org-scoped `users_select` policy would make every login/refresh
    attempt indistinguishable from "unknown user," breaking a shipped,
    out-of-scope feature. This is exactly the "administrative/system-level
    operation... explicit, separately-named system context" ADR/0021 itself
    already calls for -- authentication is necessarily pre-tenant-scope, the
    same category bootstrap-admin/reconcile-organizations already fall into.
    `presentation/api/deps.py`'s `get_auth_service()` uses this instead of
    `get_db()` for exactly this reason; nothing about `AuthService`'s own
    code changes.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
