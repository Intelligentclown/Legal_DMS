"""ADR-0036 fresh-install classification port (T124).

`InstallationClassifier` is the mechanical, runtime decision service for
ADR-0036's enablement gate: it classifies a live database as one of three
states and the application's `PartyWriteGate` consults it before every normal
Party write. The classification is derived *only* from the live row-presence
of the governed tables — never from an environment name, a config flag, a test
marker, or the repository's own development/test history. T124's authorization
row binds that constraint explicitly: the repository's history does not itself
satisfy the mechanical fresh-install classification, and this project history
must never be hardcoded here as runtime truth.

Three states:

- `FRESH`: all governed legacy-object tables are empty. In ADR-0036 terms
  this is the only state in which ordinary application Party writes are
  permitted — the flyway-from-scratch path ("law-firm installs and adopts the
  governed product without any pre-existing system to reconcile").
- `LEGACY_WITH_BUSINESS_DATA`: the legacy-object tables carry rows, but the
   migration ledger does not yet cover every `clients` row - the
  T108-T118 reconciliation/cutover window is still in progress. Normal Party
  writes stay gated (fail-closed).
- `MIGRATED`: the migration ledger is non-empty and every `clients` row is
  accounted for by a ledger entry, so the legacy cutover is complete.

The *per-write predicate* deliberately excludes `parties` itself (ADR-0036
slice scope, per T124's authorization row): `parties` is this slice's own
product surface, so a Party write can never retroactively flip the
installation out of the state that permitted it. The tables consulted are the
eleven governed legacy-object tables — `clients`, `client_contacts`,
`addresses`, `properties`, `property_owners`, `matters`, `appointments`,
`invoices`, `payments`, `matter_parties`, and `client_party_migration_ledger`
(a `parties` row can only legally exist today via the T118 migration
executor, which writes its ledger row in the same unit, so `parties` carries
no independent classification signal). ADR-0036's fresh-state *definition* is
still the full zero-row state — an empty governed legacy-object set — of which
the per-write predicate is the mechanical, slicesafe test. `organizations`,
`users`, `roles`/`permissions`, and the purely supporting lookup tables are
deliberately not classification signals: they are the tenant and
authorization scaffolding a fresh install necessarily provisions *before*
any governed feature surface exists.

Any state more advanced than `FRESH` — and any ambiguous/unknown observation —
must fail closed; `PartyWriteGate` (application layer) raises `ForbiddenError`
for every non-`FRESH` state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum


class InstallationState(StrEnum):
    """The mechanical classification of a live installation (ADR-0036)."""

    FRESH = "fresh"
    LEGACY_WITH_BUSINESS_DATA = "legacy_with_business_data"
    MIGRATED = "migrated"


class InstallationClassifier(ABC):
    """Port for the mechanical fresh-install classifier (ADR-0036, T124)."""

    @abstractmethod
    async def classify(self) -> InstallationState:
        """Classify the live installation from row-presence alone.

        Implementations must be deterministic and must never accept any
        non-database signal (env name, config, flags, caller assertions).
        """
        ...
