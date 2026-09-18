"""Provision the narrowly privileged ADR-0037 bootstrap database role."""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import text

from app.infrastructure.cli.provision_app_role import ProvisioningError, run_provision
from app.infrastructure.database.session import get_session_factory

ROLE_NAME = "legal_dms_bootstrap"


async def _grant_bootstrap_access(session) -> None:
    """Grant only routine execution after the provenance migration exists."""
    exists = await session.execute(
        text("SELECT to_regnamespace('legal_dms_provenance') IS NOT NULL")
    )
    if bool(exists.scalar_one()):
        await session.execute(
            text("GRANT USAGE ON SCHEMA legal_dms_provenance TO legal_dms_bootstrap")
        )
        await session.execute(
            text(
                "GRANT EXECUTE ON FUNCTION legal_dms_provenance.enter_operational_fresh(uuid) "
                "TO legal_dms_bootstrap"
            )
        )


async def _async_main() -> None:
    password = os.environ.get("POSTGRES_BOOTSTRAP_PASSWORD")
    if not password:
        print("provision-bootstrap-role failed: POSTGRES_BOOTSTRAP_PASSWORD is required")
        raise SystemExit(1)
    async with get_session_factory()() as session:
        try:
            result = await run_provision(session, role_name=ROLE_NAME, password=password)
            if result.attribute_problems:
                raise ProvisioningError("existing bootstrap role has unexpected attributes")
            await _grant_bootstrap_access(session)
            await session.commit()
        except ProvisioningError as exc:
            await session.rollback()
            print(f"provision-bootstrap-role failed: {exc}")
            raise SystemExit(1) from None
    print(f"Bootstrap role {ROLE_NAME!r} is provisioned with routine-only access.")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
