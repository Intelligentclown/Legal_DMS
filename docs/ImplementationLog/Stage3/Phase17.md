-----------------------------------------------

# Stage 3 - Phase 17

Status: Done (QA Approved; ready for PM pre-merge gate)

Started: 2026-09-08

Completed: 2026-09-08 (remediation: 2026-09-08)

Related Tasks: T118

Related ADRs: [ADR-0034](../../../ADR/0034-party-client-migration-persistence-and-execution-ledger.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md)

Git Commit: implementation `cf9726e4fdecfcbd0fd3fabab803b6add6cb2e85`; QA decision (Rework required) `b65f5b96439572079203b134c2b89a6decdd90f0`; remediation `93c2f51e3d8df2d80dced1cb15e7c312e2e1d3b2d`; QA re-review target `090c0d26c1dbc83e63de673751c4002efa8e1a03`; QA approval evidence `7b3db8ee0f813058726a2bcbab47db339959754e`

Pull Request: #205 (open; QA Approved; ready for PM pre-merge gate)

Release:

-----------------------------------------------

## Objective

Implement the write-capable governed migration executor per ADR-0034 step 5 / ADR-0035: load a
validated client-reconciliation artifact, plan an anchored Party/Client write-set, apply it in a
single committed transaction per anchor in write mode, emit a per-anchor audit ledger row that the
reconciliation/identity layer can replay idempotently, and gate the entire run on non-executable
decisions, stale artifacts, or dependency churn — without any schema change.

## Tasks Implemented

- Added `client_migration_executor.py` (CLI entry `client-migration-executor`) implementing the
  load–compare–plan–apply pipeline for the governed executor role defined in the ADR-0034 execution
  ledger contract.
- Anchors: each report anchor (party/client decision row) with `decision="mapped"` and a resolved
  client object; planning computes an append/backfill write-set (Party business row plus optional
  bridge backfill of `property_owners`, `appointments`, `invoices`, `payments`, `client_contacts`,
  and `matter_parties`) without mutating the legacy client row.
- Write mode commits per anchor within a single transaction; persisted `ClientPartyMigrationLedger`
  rows carry the canonical `source_fingerprint` (SHA-256 of the canonical JSON report snapshot) plus
  `source_client_version`, `source_client_updated_at`, and `source_report_sha256` provenance.
- Run-level gating: the run is `gated=True` (zero anchors, no writes) when the artifact is stale,
  invalid, errored, or any decision is non-executable (`unmappable`/`ambiguous`), per ADR-0035 §13;
  the per-anchor `non_executable_decision` branch is retained defensively.
- Idempotence/replay: an already-committed basis for the same client anchors the current run against
  it (verified unchanged via fingerprint + version/updated_at); any drift rejects the run on basis
  collision, keeping the ledger append-only.
- No schema or ADR change: `source_fingerprint` uses the existing `VARCHAR(255)` column
  (`models/party.py`), and the executor relies solely on T116/T117 bridges.

## Files Modified

- `backend/src/app/infrastructure/cli/client_migration_executor.py` (new)
- `backend/tests/integration/test_client_migration_executor.py` (new)
- `backend/pyproject.toml` (add `client-migration-executor` console script)

## Tests Added

- `test_client_migration_executor.py` (27 integration tests) covers: dry-run plans the write-set and
  rolls everything back; write mode commits one anchor and leaves the legacy graph untouched;
  re-running after a commit is an append-only noop; non-executable decisions gate the whole run;
  stale/errored artifacts gate with no writes; unmappable decisions fail closed with rolled-back
  writes; changed live anchor state rejects as basis collision; missing-organization decision
  gates all writes; conflicting Matter-Party closes fails closed; the ledger is append-only with no
  duplicate basis; anchor additions during the run are rejected as dependency churn.
- QA-rework additions (2026-09-08): `test_live_client_mutation_after_commit_fails_closed`
  (write-mode commit followed by a live legacy-Client mutation must never replay as
  `already_completed` — it gates on the staleness preflight or fails as `basis_collision`, keeps
  exactly one ledger row, and leaves the Party and legacy Client unchanged);
  `test_changed_live_anchor_state_rejects_as_basis_collision` (apply_anchor's own identical-completion
  check rejects a mutated live anchor even without a gating preflight);
  `test_committed_ledger_source_fingerprint_matches_live_anchor` (the committed `source_fingerprint`,
  `source_client_version`, `source_client_updated_at` equal the live-computed fingerprint and anchor
  state); `test_two_live_client_versions_produce_different_fingerprints`;
  `test_client_source_fingerprint_timestamp_canonicalization_is_timezone_safe`.
- Seed-data reference suite: 5 passed.

## Test Results

- Focused executor suite on live PostgreSQL (dockerized `postgres:16-alpine`, healthy on `:5433`),
  disposable data only: 27 passed. Seed-data reference suite re-run: 5 passed.
- T108/T109/T110/T111 preflight/gating/integrity and T115/T116/T117 schema/bridge regression suites
  re-run: 43 passed.
- Full backend suite from a pristine dev DB: 620 passed, 21 skipped.
- Governance validator: `governance_validate: OK (0 warning(s), 0 errors)`; governance test suite:
  51 passed, 6 subtests passed.
- Post-run DB hygiene verified: all business/test tables back at 0 rows and reference/seed data at
  expected counts (`matter_types` 8, `matter_statuses` 6, `payment_methods` 6, `document_types` 10,
  `workflow_definitions` 1, `workflow_states` 6) — no residue.
- Ruff and Black passed on both changed Python files (`2 files would be left unchanged`);
  `git diff --check` passed.

## QA Rework Record (2026-09-08)

- QA decision `b65f5b9` (docs(qa): record T118 QA decision, Rework required) on reviewed HEAD
  `5f85bf2` was not approved: the original `source_fingerprint` was derived only from the frozen
  T108/artifact snapshot, so a legacy `clients` row mutated *after* a committed migration could be
  replayed as `already_completed` instead of failing closed. The requirement: identical-completion
  must be proven against the **live execution-time anchor state** of the legacy Client.
- Remediated (commit `93c2f51`): `client_source_fingerprint()` now computes the canonical
  live-anchor fingerprint `Client:<id>:<version>:<canonical-UTC-updated_at>` from the freshly read
  `clients` row (same `<Model>:<id>:<version>:<updated_at>` shape as T108
  `_fingerprint_for_record`, literal string, no hashing). `apply_anchor` reads the live row before
  the ledger replay loop and declares `already_completed` only when the committed ledger proves
  every governed identity dimension still matches (`party_id`, `organization_id`, `resolution_mode`,
  `source_client_version`, canonical `source_client_updated_at`, `source_fingerprint`) — any drift
  returns `basis_collision` (fail-closed, zero writes, no overwrite, no replacement ledger row).
  The executor's replay is therefore independent of any upstream preflight gate. No schema, model,
  ADR, or `VARCHAR(255)` change was required (`source_client_version` /
  `source_client_updated_at` / `source_fingerprint` columns already exist per ADR-0035 §8).
- Reproduction evidence: the write-mode regression test commits a migration to live PostgreSQL,
  mutates the legacy Client row (bumps `version` via OptimisticLockMixin and `updated_at` via
  `onupdate=func.now()`), re-runs, and asserts `summary["already_completed"] == 0` with the stale-run
  gated or `basis_collision` — never `already_completed`; the single ledger row, the Party, and the
  legacy Client are asserted unchanged.
- Scope preserved: the remediation touched only `client_migration_executor.py`, its integration test
  suite, and this phase log; QA review evidence, schema, models, ADR files, and upstream gates were
  left untouched.

## Design Decisions

- `source_fingerprint` is the canonical **live-anchor fingerprint**
  `Client:<id>:<version>:<canonical-UTC-updated_at>` derived from the execution-time `clients` row,
  mirroring the T108 `<Model>:<id>:<version>:<updated_at>` shape (`_fingerprint_for_record` in
  `client_migration_preflight.py`). It fits the existing `VARCHAR(255)` with no schema change and
  proves the exact legacy anchor version observed at execution time (ADR-0034 §4); the
  `test_changed_live_anchor_state_rejects_as_basis_collision` suite pins that contract. *(Original
  approach was a SHA-256 of the frozen report snapshot; the b65f5b9 QA rework rejected it as
  insufficient against post-commit Client mutation and replaced it with the live-anchor form.)*
- Executability is decided at the artifact level: the T118 validator sets `executable=False` for any
  non-executable decision state, and T111 (run gating) therefore produces `gated=True` with a single
  `P1002`-style failed gate and no per-anchor work. This matches ADR-0035 §13 ("proceed only when
  every anchor is executable").
- Legacy `clients` rows are never modified or deleted by the executor; backfills write only to
  governed bridge columns and Party-adjacent tables, so a failed/rolled-back run leaves the legacy
  graph byte-identical.
- Audit ledger rows are the single source of replay truth, and `apply_anchor` re-reads the live
  legacy Client and recomputes its fingerprint before each replay decision; identical completion is
  declared only when the committed ledger still matches the live anchor state (`party_id`,
  `organization_id`, `resolution_mode`, `source_client_version`, canonical
  `source_client_updated_at`, `source_fingerprint`) alongside the reconciliation basis. Any drift —
  a mutated `clients` row, changed report bytes, or different resolution settings — trips
  `basis_collision` rather than silent divergence, and the executor's check does not depend on any
  upstream preflight.

## Problems Encountered

- Original fingerprint plan (JSON-serialized hash tuple) collided with the `VARCHAR(255)` column
  width; resolved by the canonical SHA-256 digest above. No migration was re-run or edited.
- Test hygiene issues that surfaced only against a live database: (1) seeded-ORM expiry after
  `rollback()` in committed-test `finally` blocks raised `MissingGreenlet` during cleanup, leaking
  committed write-sets that then poisoned later runs via artifact-wide anchoring — resolved by
  capturing seed IDs eagerly (`_seed_ids`) and running `_cleanup_committed(session, ids)` off plain
  UUID values before any rollback; (2) a latent FK-ordering bug in the cleanup helper (legacy
  `clients.address_id` references its seeded Address) — resolved by deleting the client before its
  address; (3) orphaned test-created lookup rows (`MT-`/`MS-`/`PM-` UUID codes) accumulated in the
  dev DB from earlier unmerged-epoch runs and tripped exact-count reference-seed tests — removed
  from the dev DB only; reference codes were verified intact before deletion.
- No repository migration or model file was changed during this phase; the dev database
  `alembic check` drift on `client_party_migration_ledger` remains the pre-existing T116 stale-local
  artifact documented in Phase16 and is not introduced by this phase.

## Deferred Work

- Party business CRUD/API/RLS, final bridge `NOT NULL` enforcement, Organization backfill, cutover,
  and T109 execution remain deferred to separately authorized work per the T118 authorization
  record and ADR-0035 sequencing.
- PM pre-merge gate placement for PR #205 remains pending; the final QA re-review is Approved.

## Future Considerations

- The executor's write path is deliberately single-transaction-per-anchor; a future batch mode for
  thousands of anchors should reuse the same plan/apply decomposition with per-anchor commit and an
  explicit policy on ledger flush ordering.
- Artifact-level anchoring forces an entire run to gate when any anchor is non-executable; if a
  later task wants partial migration it must be separately scoped and ADR-amended, not implemented
  inside this executor.

## Reviewer Checklist

☑ Architecture preserved - Clean Architecture; CLI consumer of the existing validator/preflight infrastructure.
☑ Existing design patterns followed - mirrors Phase12-16 CLI/test conventions; no schema or model change.
☑ Tests added - 27 integration tests (incl. QA-rework live-mutation regressions) exercise the full gate/plan/apply/replay matrix.
☑ Existing tests pass - 620 passed, 21 skipped on live PostgreSQL; DB left pristine. Governance + regression suites green.
☑ Documentation updated - this phase log incl. the b65f5b9 QA rework record.
□ ADR updated (if required) - no new architecture decision; ADR-0034/0035 step implemented as governed.
□ AI_BOOTSTRAP updated (if required) - no standing convention changed.
☑ PROJECT_STATE updated (if required) - synchronized after final independent QA approval.
☑ No unrelated refactoring
☑ No scope creep - only T118-scope executor, tests, and its console-script entry.
☑ Ready for QA - final independent QA re-review Approved at 7b3db8e after b65f5b9 remediation.

## QA Decision

☑ Approved (`7b3db8e`) — final independent re-review of remediation target `090c0d2`.
□ Approved with comments
□ Rework required — historical initial decision at `b65f5b9` identified the live-anchor fingerprint defect; remediation `93c2f51` and final re-review are recorded above.
