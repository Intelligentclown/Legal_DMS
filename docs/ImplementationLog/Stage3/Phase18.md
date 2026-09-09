# Stage 3 - Phase 18

Status: Done (QA Approved; ready for PM pre-merge gate)

Started: 2026-09-09

Completed: 2026-09-09

Related Tasks: T119

Related ADRs: [ADR-0034](../../../ADR/0034-party-client-migration-persistence-and-execution-ledger.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md)

Git Commit: implementation `9cf8e3d`; implementation-log head reviewed by QA `5f31b1f9fbf17dee7d6e9543039e31385ddbf2c3`; corrected QA approval evidence `7728b56973ef58e328d2c30ee9a509d808ca0f89` (baseline `03b4529`; authorized by `6db7c7d`)

Pull Request: #207 (open; QA Approved; ready for PM pre-merge gate)

Release:

---

## Objective

Build a development/testing-only rehearsal harness that proves the governed
T108 → T109 → T110 → T111 → T118 migration path against synthetic data in a
**disposable** PostgreSQL database, and extract the T118 integration-test
helpers into a shared support module that both the T118 regression suite and
the new T119 rehearsal suite consume. The harness is rehearsal-only: it must
never run a committed rehearsal against the shared dev database, and it must
behave identically to a controlled rollback rehearsal facing a resilient
failure mid-transaction.

## Scope (rehearsal-only)

- Extract the T118 integration-test seed/apply/freeze/cleanup helpers into a
  shared test-support module and refactor `test_client_migration_executor.py`
  to import them (behavior unchanged; 27 T118 tests still pass).
- Add a reusable disposable-DB provision/migrate/drop facility plus a
  controlled, test-only unit-fault injector.
- Add a T119 rehearsal suite exercising the complete and aborted governed
  paths on a disposable DB at the Alembic head.
- **Not** in scope (unchanged exclusions): Party CRUD/API/services, app
  cutover, RLS expansion/tenant finalization, `organization_id` hardening,
  `matters.client_id` removal, Client retirement, Representative
  normalization, MatterParty vocabulary, business services, production/staging
  infrastructure, ADR #20, ADR status changes, T120+.

## Tasks Implemented

- **Shared support module** (`backend/tests/support/synthetic_migration.py`):
  extracted and renamed the T118 test helpers (`seed_country`, `seed_lookups`,
  `make_org`, `make_user`, `seed_client_graph`, `make_entry`, `make_artifact`,
  `apply_anchor_against`, `freeze_basis`, `seed_ids`, `cleanup_committed`,
  `make_isolated_session`, constants `SCHEMA_VERSION`/`REPORT_TYPE`/
  `EXECUTOR_VERSION`, `EMPTY_SHA`, `SYNTHETIC_PAN`, `SYNTHETIC_AADHAAR`). The
  seed graph keeps `full_name="Test Client"` so the existing T118 assertions
  remain valid. Synthetic identity values are fixed, explicit test stand-ins —
  no realistic PAN/Aadhaar or sensitive identifiers.
- **Disposable-DB facility** (same module): `provision_disposable_database()`
  creates a fresh database on the same PostgreSQL server (as a child
  `alembic upgrade head` subprocess with a `DATABASE_URL` override), and
  `drop_disposable_database()` destroys it with `DROP ... WITH (FORCE)`.
  `alembic_current_branch()` asserts the disposable DB is at the migration
  head. Rehearsal data **never** touches the shared dev DB.
- **Test-only fault injection** (same module): `InjectedUnitFault` plus
  class-based async CM `inject_unit_fault_on_ledger_flush(session)` which
  registers a SQLAlchemy `before_flush` listener on `session.sync_session` that
  raises when a `ClientPartyMigrationLedger` appears in `session.new`. This
  fires exactly at the executor's final flush (after the Party is already
  flushed inside the open transaction), forcing `run_migration_executor` to
  catch, `session.rollback()`, and `break` — proving a complete unit rollback.
  It is purely additive test code and does not weaken the executor's
  transaction boundaries.
- **T119 rehearsal suite** (`backend/tests/integration/test_synthetic_migration_rehearsal.py`):
  session-scoped disposable-DB fixture plus 7 tests (see Tests Added).

## Files Modified

- `backend/tests/support/synthetic_migration.py` (new) — shared test support
  module (seed graph, freeze/apply helpers, disposable-DB provision/drop,
  unit-fault injector).
- `backend/tests/integration/test_synthetic_migration_rehearsal.py` (new) —
  T119 rehearsal harness.
- `backend/tests/integration/test_client_migration_executor.py` (refactor) —
  now imports its previously-private helpers from the shared support module;
  T118 coverage unchanged.

## Tests Added

- `test_rehearsal_is_disposable_and_at_migration_head` — proves the disposable
  DB is created, migrated to the Alembic head, exercised, and dropped with no
  residue.
- `test_end_to_end_rehearsal_complete_anchor_graph` — full deterministic
  anchor: T108/T109 freeze+validate, T110/T111 gates pass, dry-run plans the
  whole write-set and rolls back, write-mode commits exactly one anchor, replay
  is an append-only no-op, and all copy dimensions (`addresses_backfilled`,
  `matters_backfilled`, `matter_parties_created`, `property_owners_bridged`,
  `properties_backfilled`, `property_addresses_backfilled`,
  `appointments_bridged`, `matter_linked_appointments_staged`,
  `invoices_bridged`, `payments_bridged`, `client_contacts_bridged`) plus
  by-node hashes, provenance, and ledger counts are asserted.
- `test_operator_reconciled_resolves_ambiguous_evidence` — a deliberately
  ambiguous evidence set (`client.created_by` in org A, `client.updated_by` in
  org B) is resolved by `operator_reconciled` provenance and committed to the
  selected organization.
- `test_stale_frozen_evidence_rejected_before_writes` — an unrelated legacy
  anchor appears after the basis was frozen; the staleness preflight gates the
  run with zero writes and no partial residue.
- `test_changed_live_client_basis_rejected_fail_closed` — a committed
  completion whose live Client was mutated afterwards is never replayed as
  `already_completed`; it is rejected fail-closed with zero new writes and
  exactly one preserved ledger row.
- `test_cross_organization_disagreement_rejected_zero_writes` — a dependent
  row whose raw `organization_id` disagrees with the tenant under migration
  (here `address.organization_id`) fails closed via the executor's
  cross-tenant guard with zero writes.
- `test_fault_injection_rollback_retry_noop` (mandatory) — a controlled
  mid-unit fault proves a complete rollback: no Party, MatterParty, bridge,
  staging, or ledger residue and the committed source graph stays valid; a
  clean retry succeeds producing exactly one migration unit and one ledger
  completion; and an identical third run is a no-op (`already_completed`).

## Test Results

- T119 rehearsal suite on a disposable PostgreSQL DB: **7 passed**.
- Focused migration regression set (T108 preflight, T110 validator, T111
  staleness, T118 executor, T119 rehearsal): **59 passed**.
- Full backend suite from a pristine dev DB: **627 passed, 21 skipped**.
- Governance validator: `governance_validate: OK (0 warning(s), 0 errors)`;
  governance test suite: **51 passed**.
- Ruff and Black clean on all three changed Python files (3 files unchanged,
  `git diff --check` clean).
- Post-run DB hygiene verified: all business/test tables in the shared dev DB
  back at 0 rows — the rehearsal ran only against the dropped disposable DB.

## Rehearsal Evidence (disposable DB)

- Disposable DB: `legal_dms_t119_3ee94fff6883` — **created, migrated, run, and
  dropped** (`DISPOSAL_CONFIRMED_DROPPED`).
- Postgres: server `16.15` on `postgres:16-alpine`
  (`sha256:44c4ee9810eff91f7eab4d822642e01115b1a9eccce4bcbdde7604752d68eac6`),
  the same container image as the shared dev DB but a separate database.
- Alembic revision at head: `b7e8a4f2c6d0`.
- Executor version used by the rehearsal: `EXECUTOR_VERSION` (T118 test
  version constant in the shared support module).
- T108 report (frozen `client-migration-preflight.v1`) SHA-256:
  `49a3a47a21a46731f411b107da8d4693a6bea49f4a5ed75bde9af64c9d5c2283`.
- T109 artifact (`party-client-reconciliation.v1`) SHA-256:
  `76b0768bf02b9caa23af960d3aa5854283c7f590843bcaf5502babe1572a75bd`.
- T110 artifact validation: `valid=True`, `executable=True`.
- T111 staleness preflight: `valid=True`, `stale=False`, `executable=True`.
- T118 dry-run: `planned` — summary `{total:1, committed_or_planned:1,
  already_completed:0, failed:0, gated:0}` (rolled back).
- T118 write-mode commit: `committed` — full contents above (all bridge/backfill
  counts = 1, `ledger_entry` = one completion row).
- Invariant counts after commit: `party=1`, `matter_parties=1`, `ledger=1`;
  Party UUID preserved (`party_id == legacy client id`); Organization intact.
- Identical replay: `already_completed`, summary `{total:1, committed_or_planned:0,
  already_completed:1, failed:0, gated:0}` (no-op).
- Disposal: disposable database dropped after the run; nothing left behind.

## Design Decisions

- **Disposable-only rehearsal**: `provision_disposable_database()` targets a
  separate, freshly created database on the same server (per user decision),
  migrated to head via a child `alembic` subprocess that inherits the override
  `DATABASE_URL`. The shared dev DB (`.env` →
  `postgresql+asyncpg://legal_dms:legal_dms@localhost:5433/legal_dms_dev`) is
  never used as a rehearsal target.
- **Shared support module** (per user decision): T118's private helpers moved
  verbatim (renamed) to `tests/support/synthetic_migration.py` so T118 and T119
  share one source of truth; no production code was touched.
- **Fault injection is test-only and outside the executor**: the `before_flush`
  listener raises `InjectedUnitFault` on the final ledger flush inside the
  executor's own transaction, so the executor's existing catch/rollback/break
  path (unchanged) proves complete unit rollback. The source graph is committed
  before the injected run so the rollback affects only the migration unit.
- **Mandatory negative scenarios**: staleness, changed-live-basis, and
  cross-organization disagreement all assert zero writes and preserved ledger
  state, matching the fail-closed guarantees required by T119.

## Problems Encountered

- **Shared-user FK during cleanup**: the first stale-test draft seeded the
  "extra" legacy anchor under the *same* org/user as the primary client, so
  `cleanup_committed` (which deletes users by `organization_id`) hit
  `fk_addresses_created_by_users` while the other client's address still
  referenced the user. Resolved by giving the secondary anchor its own
  independent org/user (and its own cleanup graph).
- **Rollback pulled the uncommitted seed with it in the fault test**: the first
  fault-injection draft ran the executor without first committing the seed, so
  the injected unit rollback also rolled back the uncommitted source graph and
  the `Client` resolved to `None`. Resolved by committing the source graph
  before the injected run — which is precisely the invariant the test intends
  to prove (the source graph survives a mid-unit rollback).
- **Async listener registration**: `event.listen` on the `AsyncSession` wrapper
  is invalid; the injector listens on `session.sync_session`, which fires at the
  executor's final flush. No production change was required.

## Deferred Work

- Party business CRUD/API/RLS, Organization backfill, cutover, and T109
  execution remain deferred to separately authorized work per the T119
  authorization record and ADR-0035 sequencing.
- PM pre-merge gate placement for PR #207 remains pending; final independent QA is Approved.

## Future Considerations

- The reusable support module and disposable-DB facility are the natural base
  for any later rehearsal of T120+ sequencing and for CI smoke runs against a
  disposable schema.
- If a future task adds a batch executor mode, the fault-injection helper
  generalizes to per-anchor interruption without touching production code.

## Reviewer Checklist

☑ Architecture preserved - test-only harness; CLI consumer of existing validator/preflight/executor infrastructure.
☑ Existing design patterns followed - mirrors Phase12-17 test conventions; no schema, model, ADR, or production change.
☑ Tests added - 7 T119 rehearsal tests + shared support module; T118 refactor preserves its 27 tests.
☑ Existing tests pass - 627 passed, 21 skipped on live PostgreSQL; migration regressions 59 passed; governance green.
☑ Documentation updated - this phase log with full rehearsal evidence and disposal confirmation.
□ ADR updated (if required) - rehearsal-only; no architecture decision changed.
□ AI_BOOTSTRAP updated (if required) - no standing convention changed.
☑ PROJECT_STATE updated (if required) - synchronized after final independent QA approval.
☑ No unrelated refactoring - only T118-helper extraction (per user decision) and the T119 harness.
☑ No scope creep - only T119-scope rehearsal harness, shared support module, and T118 import refactor.
☑ Ready for QA - final independent QA Approved at `7728b569` after review of `5f31b1f`.

## QA Decision

☑ Approved (`7728b569`) — corrected T119 QA evidence, one commit after reviewed implementation head `5f31b1f`.
□ Approved with comments
□ Rework required
□ Pending - superseded by the final independent QA decision above. The previously reported SHA was a T118 commit and is not T119 QA evidence.
