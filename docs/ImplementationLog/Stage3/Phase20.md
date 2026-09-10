# Stage 3 - Phase 20

Status: Progress

Started: 2026-09-10

Completed:

Related Tasks: T122

Related ADRs: [ADR-0021](../../../ADR/0021-organization-tenant-boundary-enforcement.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md) (§6 Address finalization), [ADR-0036](../../../ADR/0036-fresh-installation-party-enablement-boundary.md) (Decision 4 = this task)

Git Commit: 5518e1e (branch `feature/t122-address-tenant-finalization-rls`)

Pull Request: https://github.com/Intelligentclown/Legal_DMS/pull/213 (base `main`; exact-head CI green)

Release:

---

## Objective

Finalize the Address tenant boundary: make `addresses.organization_id` NOT NULL
and enforce a default-deny, Organization-scoped Row Level Security backstop on
`addresses` through the non-owning `legal_dms_app` runtime role, per ADR-0021
(Organization is the tenant boundary) and ADR-0036 Decision 4 (address
finalization is the `organization_id`-NOT-NULL constraint boundary). Publish via
an implementation PR and stop for independent QA.

## Implemented Scope

- New reversible Alembic migration `9c4a7e2d1b5f` (parent `f3b7c9d1e2a4`):
  - `addresses.organization_id` `ALTER ... SET NOT NULL` — deliberately fail
    closed: any retained NULL-org Address makes the ALTER raise
    `... contains null values` and the whole migration aborts (no backfill,
    no reset, no deletion, and nothing else in the migration runs).
  - `ENABLE` + `FORCE ROW LEVEL SECURITY` on `addresses`.
  - Exactly four default-deny policies (`addresses_select` /
    `addresses_insert` / `addresses_update` / `addresses_delete`), each scoped
    by the T105 null-safe Organization GUC
    `organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid`
    (SELECT/UPDATE/DELETE by `USING`; INSERT/UPDATE by `WITH CHECK`), giving a
    default-deny backstop for the runtime role while the owning superuser and
    Alembic bypass RLS as before.
  - Downgrade fully reverses: drop the four policies, `NO FORCE`, `DISABLE`,
    restore `organization_id` nullable — i.e. exactly T120's contract — while
    preserving org-scoped rows and values.
- Updated the `Address` ORM contract: `organization_id` is now non-optional
  (`Mapped[UUID]`), keeping the Organization FK, the `(organization_id, id)`
  support key, and the same-Organization composite Address relationships
  (Client/Party/Property plus the T120 dependency chain) unchanged.
- Test support: parameterized
  `provision_disposable_database_with(prefix, upgrade_target=...)` in
  `tests/support/synthetic_migration.py` for era-split disposable databases.
- Tests:
  - `test_address_tenant_finalization_foundation.py` (unit, CI-runnable): model
    contract, migration upgrade/downgrade intent via a recording ops wrapper,
    revision wiring (extends `f3b7c9d1e2a4`).
  - `test_address_tenant_finalization_and_rls.py` (integration, disposable
    DB at head): fresh-upgrade evidence; catalog surface now {addresses,
    organizations, users}; addresses NOT NULL enforced; four GUC default-deny
    policies with the right qual/with-check split; role posture; no-context
    default denial of every command; org-scoped visibility; cross-org
    SELECT/INSERT/UPDATE/DELETE denied; same-org UPDATE preserves org; GUC
    isolation across commit and pooled-connection reuse; composite-FK
    protections for Client/Property/Party; downgrade restoration of the T120
    contract with data preserved.
  - `test_address_null_legacy_upgrade_fails_closed.py` (integration,
    disposable DB pinned at `f3b7c9d1e2a4`): a deliberately constructed NULL-org
    Address makes `alembic upgrade head` fail closed with no partial residue.
  - `test_synthetic_migration_rehearsal.py` (T119): the rehearsal now provisions
    its disposable database pinned at the pre-T122 legacy head
    `f3b7c9d1e2a4` (the exact contract T122's downgrade restores), because the
    rehearsal simulates a legacy pre-finalization database whose Address rows
    carry no Organization — structurally impossible on a fresh T122 head.
  - `test_tenant_schema_foundation.py` (T115): `addresses` removed from the
    still-nullable staged-tenant set (T122 finalizes it; its non-nullable model
    contract is asserted by the new unit test). The T115 migration-intent tests
    are unchanged and still cover all eight staged tables.

## Data-Safety Decisions

- The forward migration runs only against genuinely empty/fresh targets; the
  shared development database is never forward-migrated and stays at the T120
  head `f3b7c9d1e2a4`.
- No backfill, no synthesized ownership for retained NULL-org rows, no reset,
  no deletion of any data, anywhere — the migration is fail-closed by design.
- Positive validation uses newly created disposable PostgreSQL databases that
  are dropped in fixture teardown; the negative (fail-closed) scenario uses a
  deliberately constructed NULL-org Address on its own disposable database.
- The T118/T119 legacy-path suites continue to run against the pre-T122 schema
  era (shared dev DB at T120 head and/or disposable databases pinned at
  `f3b7c9d1e2a4`), which is exactly the contract the T122 downgrade restores.

## Files Modified

- `backend/alembic/versions/9c4a7e2d1b5f_address_tenant_finalization_rls.py`
  (new; parent `f3b7c9d1e2a4`)
- `backend/src/app/infrastructure/persistence/models/client.py`
- `backend/tests/support/synthetic_migration.py`
- `backend/tests/integration/test_synthetic_migration_rehearsal.py`
- `backend/tests/integration/test_address_tenant_finalization_and_rls.py` (new)
- `backend/tests/integration/test_address_null_legacy_upgrade_fails_closed.py` (new)
- `backend/tests/unit/test_address_tenant_finalization_foundation.py` (new)
- `backend/tests/unit/test_tenant_schema_foundation.py`

## Verification To Date

Implementation-phase validation (all run on 2026-09-10 with
`APP_DATABASE_URL=postgresql+asyncpg://legal_dms_app:legal_dms_app@localhost:5433/legal_dms_dev`;
QA is a separate independent step and none of this substitutes for it):

- Tooling: `uv run ruff check src tests alembic` clean; `uv run black --check
  src tests alembic` clean; `git diff --check` clean.
- Unit: full `tests/unit` suite passes (309 tests), including the new
  `test_address_tenant_finalization_foundation.py` and the updated T115
  `test_tenant_schema_foundation.py`.
- New integration: `test_address_tenant_finalization_and_rls.py` — 25 passed on
  a disposable DB migrated to head; `test_address_null_legacy_upgrade_fails_closed.py`
  — 1 passed (null-legacy `alembic upgrade head` fails closed with no residue).
- Regressions on the shared dev DB (still at T120 head): T105
  `test_organizations_users_rls.py`, `test_tenant_context_guc_scoping.py`,
  `test_users_organization_scoping_end_to_end.py`, `test_client_models.py`,
  T118 `test_client_migration_executor.py`, T108-pref-light
  `test_client_migration_preflight.py`, and T119
  `test_synthetic_migration_rehearsal.py` (now pinned at `f3b7c9d1e2a4`)
  — all green.
- Full backend suite: **682 passed**.
- Alembic offline SQL (`f3b7c9d1e2a4:9c4a7e2d1b5f --sql`) renders the exact
  upgrade (SET NOT NULL, ENABLE/FORCE RLS, four GUC policies) and the reverse
  range renders the exact downgrade (DROP policies, NO FORCE/DISABLE, DROP
  NOT NULL). Note: full-chain offline `--sql` renders of the *entire* history
  are blocked by a pre-existing limitation (JSONB literal rendering in the T116
  seed-data migration) and are unaffected by this change.
- Manual disposable cycle on a scratch database: `alembic upgrade head` →
  `current == 9c4a7e2d1b5f` → `alembic downgrade f3b7c9d1e2a4` (rc 0) →
  `alembic upgrade head` (rc 0); all disposable databases confirmed dropped
  afterward.
- Governance: `scripts/governance_validate.py` clean (0 warnings/errors);
  `scripts/tests/test_governance_validate.py` — 51 passed (6 subtests).

## Exclusions Preserved

No real-data execution or writes against the shared development database, no
backfill/reset/deletion of retained data, no Party/permission/API/frontend
changes, no `clients`/other-table NOT NULL finalization, no T118-semantics
changes, no future-task authorization use, Required ADR #20 resolution, T121+
work, or independent QA occurred in this implementation phase.

## Deferred Work

Independent QA review, QA-approved implementation/evidence commits, PM pre-merge
gate, and merge of the T122 PR remain pending.