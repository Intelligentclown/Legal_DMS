"""SQLAlchemy implementation of ADR-0037 runtime classification (T127).

T126 supplies the only normal-runtime operational-fresh proof through its
read-only ``legal_dms_provenance.runtime_state`` projection. Row presence is
still used for migration and legacy evidence, but never turns an empty upgrade
into an entitled fresh installation.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.install_classifier import (
    InstallationClassificationError,
    InstallationClassifier,
    InstallationState,
)

# T126 binds both values into immutable operational-transition evidence. A
# future revision must explicitly extend the supported runtime contract. T130
# extended the contract to `5d8a3f2e9c6b`; T132 advances the supported head
# while preserving the same immutable provenance contract.
# by recreating the provenance functions' `alembic_version` guards.
_PROVENANCE_CONTRACT_VERSION = "adr-0037.v1"
_SUPPORTED_SCHEMA_REVISION = "cdcfd7df5fde"
_OPERATIONAL_EVENT_KIND = "OPERATIONAL_FRESH_ENTERED"
_RUNTIME_STATE_VIEW = "legal_dms_provenance.runtime_state"

_BUSINESS_TABLES: tuple[str, ...] = (
    "clients",
    "client_contacts",
    "addresses",
    "properties",
    "property_owners",
    "matters",
    "appointments",
    "invoices",
    "payments",
    "parties",
    "matter_parties",
    "client_party_migration_ledger",
)
_LEDGER_TABLE = "client_party_migration_ledger"
_CLIENTS_TABLE = "clients"

_logger = logging.getLogger(__name__)


class SqlAlchemyInstallationClassifier(InstallationClassifier):
    """Provenance-aware classifier backed by one SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _count_rows(self, table_name: str) -> int:
        """Count a literal, classifier-owned table name."""
        result = await self._session.execute(text(f"SELECT count(*) FROM {table_name}"))
        return int(result.scalar_one())

    async def classify(self) -> InstallationState:
        try:
            await self._lock_migration_evidence()
            counts = {table: await self._count_rows(table) for table in _BUSINESS_TABLES}
            ledger_covered = await self._ledger_covered_clients_count()
            operational = await self._operational_transition()
        except InstallationClassificationError:
            raise
        except SQLAlchemyError as exc:
            _logger.warning("installation classification could not read database evidence")
            raise InstallationClassificationError(
                "installation evidence could not be read safely"
            ) from exc

        _logger.debug("installation classification evidence: %s", counts)
        ledger_rows = counts[_LEDGER_TABLE]
        clients_total = counts[_CLIENTS_TABLE]
        migration_complete = ledger_rows > 0 and ledger_covered == clients_total

        # A Client or governed migration ledger entry is legacy/migration
        # evidence, not legitimate post-bootstrap Party/Address growth.
        if operational is not None and (clients_total > 0 or ledger_rows > 0):
            raise InstallationClassificationError(
                "operational-fresh provenance contradicts migration evidence"
            )

        if migration_complete:
            return InstallationState.MIGRATED
        if operational is not None:
            return InstallationState.OPERATIONAL_FRESH
        if any(count > 0 for count in counts.values()):
            return InstallationState.LEGACY_WITH_BUSINESS_DATA
        return InstallationState.UNPROVEN

    async def _lock_migration_evidence(self) -> None:
        """Hold migration-evidence stability through the request transaction.

        The Party service uses this session for both gate evaluation and the
        ensuing write. These short PostgreSQL locks make a concurrent Client
        insert or T118 ledger append wait until that transaction commits or
        rolls back, closing the classification-to-write race without changing
        the separate migration executor's transaction contract.
        """
        await self._session.execute(
            text("LOCK TABLE clients, client_party_migration_ledger IN SHARE MODE")
        )

    async def _operational_transition(self) -> tuple[str, str] | None:
        result = await self._session.execute(
            text(
                "SELECT installation_id, event_kind, provenance_contract_version, "
                f"observed_schema_revision FROM {_RUNTIME_STATE_VIEW}"
            )
        )
        rows = result.mappings().all()
        if not rows:
            return None
        if len(rows) != 1:
            raise InstallationClassificationError("operational provenance is forked")

        row = rows[0]
        if (
            row["installation_id"] is None
            or row["event_kind"] != _OPERATIONAL_EVENT_KIND
            or row["provenance_contract_version"] != _PROVENANCE_CONTRACT_VERSION
            or row["observed_schema_revision"] != _SUPPORTED_SCHEMA_REVISION
        ):
            raise InstallationClassificationError("operational provenance is unsupported")
        return str(row["installation_id"]), str(row["observed_schema_revision"])

    async def _ledger_covered_clients_count(self) -> int:
        stmt = select(func.count(func.distinct(text("legacy_client_id")))).select_from(
            text(_LEDGER_TABLE)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
