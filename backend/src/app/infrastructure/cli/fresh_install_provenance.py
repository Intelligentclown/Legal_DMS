"""Guarded initial-install path for ADR-0037 birth evidence.

This command is intentionally distinct from an ordinary Alembic upgrade. It
only accepts a database with no user tables, takes a transaction-scoped lock,
and runs the complete migration chain plus birth insertion on one serializable
connection. Existing databases therefore receive schema support only.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.infrastructure.database.session import get_engine

REVISION = "9e6a4b2c8d1f"
_LOCK_KEY = "legal_dms.initial-install.v1"


class FreshInstallError(Exception):
    """Raised when the target cannot prove it is a new installation."""


async def _assert_blank_target(connection: AsyncConnection) -> None:
    result = await connection.execute(
        text(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm')"
        )
    )
    existing = sorted(str(name) for name in result.scalars())
    if existing:
        raise FreshInstallError(
            "fresh-install birth requires a database with no pre-existing public objects"
        )


def _upgrade_on_connection(connection: Connection) -> None:
    config = Config(str(Path(__file__).parents[4] / "alembic.ini"))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def establish_fresh_installation(database_url: str | None = None) -> str:
    """Install the schema and immutable birth in one serializable transaction."""
    engine: AsyncEngine | None = create_async_engine(database_url) if database_url else None
    connectable = engine or get_engine()
    try:
        async with connectable.connect() as raw_connection:
            connection = await raw_connection.execution_options(isolation_level="SERIALIZABLE")
            async with connection.begin():
                await connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": _LOCK_KEY}
                )
                await _assert_blank_target(connection)
                await connection.execute(
                    text(
                        "CREATE TEMP TABLE legal_dms_fresh_install_guard "
                        "(valid boolean NOT NULL) ON COMMIT DROP"
                    )
                )
                await connection.execute(
                    text("INSERT INTO legal_dms_fresh_install_guard VALUES (true)")
                )
                await connection.run_sync(_upgrade_on_connection)
                installation_id = uuid4()
                await connection.execute(
                    text(
                        "SELECT legal_dms_provenance.record_fresh_birth("
                        ":event_id, :installation_id)"
                    ),
                    {"event_id": uuid4(), "installation_id": installation_id},
                )
        return str(installation_id)
    finally:
        if engine is not None:
            await engine.dispose()


async def _async_main() -> None:
    try:
        installation_id = await establish_fresh_installation()
    except FreshInstallError as exc:
        print(f"fresh-install-provenance failed: {exc}")
        raise SystemExit(1) from None
    print(f"Established fresh installation birth {installation_id} at schema revision {REVISION}.")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
