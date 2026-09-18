"""Restricted-role operational-fresh bootstrap for ADR-0037."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine


class OperationalBootstrapError(Exception):
    """Raised when operational-fresh bootstrap fails closed."""


async def run_bootstrap(database_url: str) -> str:
    engine = create_async_engine(database_url)
    try:
        # A second serializable transaction can snapshot before waiting on the
        # advisory lock. Retry once on its expected serialization/uniqueness
        # conflict so it observes the committed transition as an idempotent run.
        for attempt in range(2):
            try:
                async with engine.connect() as raw_connection:
                    connection = await raw_connection.execution_options(
                        isolation_level="SERIALIZABLE"
                    )
                    async with connection.begin():
                        result = await connection.execute(
                            text("SELECT legal_dms_provenance.enter_operational_fresh(:event_id)"),
                            {"event_id": uuid4()},
                        )
                        return str(result.scalar_one())
            except DBAPIError as exc:
                if attempt == 0 and getattr(exc.orig, "sqlstate", None) in {"23505", "40001"}:
                    continue
                raise
        raise OperationalBootstrapError("bootstrap retry exhausted")
    finally:
        await engine.dispose()


async def _async_main() -> None:
    database_url = os.environ.get("BOOTSTRAP_DATABASE_URL")
    if not database_url:
        print("operational-fresh-bootstrap failed: BOOTSTRAP_DATABASE_URL is required")
        raise SystemExit(1)
    try:
        event_id = await run_bootstrap(database_url)
    except Exception as exc:
        print(f"operational-fresh-bootstrap failed: {type(exc).__name__}")
        raise SystemExit(1) from None
    print(f"Operational-fresh bootstrap is complete ({event_id}).")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
