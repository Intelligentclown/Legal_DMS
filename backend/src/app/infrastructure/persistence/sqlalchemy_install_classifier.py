"""SQLAlchemy implementation of the ADR-0036 fresh-install classifier (T124).

`classify()` reads a live row-presence snapshot of the eleven governed
legacy-object tables (see the port docstring for the exact exclusion of
`parties` and the scaffolding tables) and maps it deterministically onto
`InstallationState`:

    FRESH
        every governed legacy-object table row count is zero.
    MIGRATED
        NOT fresh, AND the migration ledger is non-empty AND every
        `clients` row is covered by a ledger entry.
    LEGACY_WITH_BUSINESS_DATA
        everything else with at least one governed row (the cutover is in
        progress, or ledger coverage is incomplete/fragmented).

The ledger-coverage check counts distinct `legacy_client_id` values in
`client_party_migration_ledger` and compares against the total `clients`
row count — no join or partial-ledger heuristics are needed because the
ledger is append-only and keyed exactly one-per-legacy-client by design
(T118/A DR-0034).

Counts are evaluated per table within a single snapshot to stay
deterministic; an inability to read any governed table (e.g. the role is
denied) surfaces as an exception, which the caller treats as fail-closed.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.install_classifier import (
    InstallationClassifier,
    InstallationState,
)

# The twelve governed legacy-object tables: ADR-0036 requires the *fresh
# definition* to be the full zero-row set, but the per-write predicate the
# classifier evaluates excludes `parties` (the slice's own product surface) —
# see the port docstring. `parties` is therefore not consulted by classify().
_GOVERNED_TABLES: tuple[str, ...] = (
    "clients",
    "client_contacts",
    "addresses",
    "properties",
    "property_owners",
    "matters",
    "appointments",
    "invoices",
    "payments",
    "matter_parties",
    "client_party_migration_ledger",
)
_LEDGER_TABLE = "client_party_migration_ledger"
_CLIENTS_TABLE = "clients"

_logger = logging.getLogger(__name__)


class SqlAlchemyInstallationClassifier(InstallationClassifier):
    """Row-presence classifier backed by one SQLAlchemy `AsyncSession`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _count_rows(self, table_name: str) -> int:
        """Row count for a literal, validator-whitelisted table name.

        The table names come from this class's own frozen tuple — they are
        bound as table identifiers, never interpolated from caller input —
        so there is no SQL-injection surface here.
        """
        stmt = text(f"SELECT count(*) FROM {table_name}")
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def classify(self) -> InstallationState:
        counts = {table: await self._count_rows(table) for table in _GOVERNED_TABLES}
        _logger.debug("install classification row-presence snapshot: %s", counts)

        if all(count == 0 for count in counts.values()):
            return InstallationState.FRESH

        ledger_rows = counts[_LEDGER_TABLE]
        clients_total = counts[_CLIENTS_TABLE]
        ledger_covered = await self._ledger_covered_clients_count()
        if ledger_rows > 0 and ledger_covered == clients_total:
            return InstallationState.MIGRATED

        return InstallationState.LEGACY_WITH_BUSINESS_DATA

    async def _ledger_covered_clients_count(self) -> int:
        stmt = select(func.count(func.distinct(text("legacy_client_id")))).select_from(
            text(_LEDGER_TABLE)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
