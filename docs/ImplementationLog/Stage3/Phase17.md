-----------------------------------------------

# Stage 3 - Phase 17

Status: Done

Started: 2026-09-08

Completed: 2026-09-08

Related Tasks: T118

Related ADRs: [ADR-0034](../../../ADR/0034-party-client-and-representative-migration-architecture.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md)

Git Commit: implementation `cf9726e4fdecfcbd0fd3fabab803b6add6cb2e85`

Pull Request: #205 (open; QA/documentation gates pending)

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

- `test_client_migration_executor.py` (23 integration tests) covers: dry-run plans the write-set and
  rolls everything back; write mode commits one anchor and leaves the legacy graph untouched;
  re-running after a commit is an append-only noop; non-executable decisions gate the whole run;
  stale/errored artifacts gate with no writes; unmappable decisions fail closed with rolled-back
  writes; changed source fingerprint rejects as basis collision; missing-organization decision
  gates all writes; conflicting Matter-Party closes fails closed; the ledger is append-only with no
  duplicate basis; anchor additions during the run are rejected as dependency churn.

## Test Results

- Focused executor suite on live PostgreSQL (dockerized `postgres:16-alpine`, healthy on `:5433`),
  disposable data only: 23 passed. Seed-data reference suite re-run: 5 passed.
- Full backend suite from a pristine dev DB: 616 passed, 21 skipped.
- Post-run DB hygiene verified: all business/test tables back at 0 rows and reference/seed data at
  expected counts (`matter_types` 8, `matter_statuses` 6, `payment_methods` 6, `document_types` 10,
  `workflow_definitions` 1, `workflow_states` 6) — no residue.
- Ruff and Black passed on both changed Python files (`2 files would be left unchanged`);
  `git diff --check` passed.

## Design Decisions

- `source_fingerprint` is a canonical SHA-256 hex digest of the report snapshot
  (`hashlib.sha256(canonical_json(snapshot).encode("utf-8")).hexdigest()`, 64 chars, fits the
  existing `VARCHAR(255)`). No schema change is needed because ADR-0034 §4's "exact legacy anchor
  version" burden is already carried by the separate `source_client_version`,
  `source_client_updated_at`, and `source_report_sha256` columns; the fingerprint proves exact
  snapshot equality, and the test `test_changed_source_fingerprint_rejects_as_basis_collision`
  pins that contract.
- Executability is decided at the artifact level: the T118 validator sets `executable=False` for any
  non-executable decision state, and T111 (run gating) therefore produces `gated=True` with a single
  `P1002`-style failed gate and no per-anchor work. This matches ADR-0035 §13 ("proceed only when
  every anchor is executable").
- Legacy `clients` rows are never modified or deleted by the executor; backfills write only to
  governed bridge columns and Party-adjacent tables, so a failed/rolled-back run leaves the legacy
  graph byte-identical.
- Audit ledger rows are the single source of replay truth: `source_fingerprint`
  (`sha256(fingerprint(source_client_version, source_client_updated_at, source_report_sha256))` at
  the ledger row) is also checked via the replay-comparison codepath so a touched `clients` row or
  changed report bytes trip basis-collision rather than silent divergence.

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
- QA review of this batch and PM pre-merge gate placement for PR #205.

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
☑ Tests added - 23 integration tests exercises the full gate/plan/apply/replay matrix.
☑ Existing tests pass - 616 passed, 21 skipped on live PostgreSQL; DB left pristine.
☑ Documentation updated - this phase log.
□ ADR updated (if required) - no new architecture decision; ADR-0034/0035 step implemented as governed.
□ AI_BOOTSTRAP updated (if required) - no standing convention changed.
□ PROJECT_STATE updated (if required) - pending Documentation Manager synchronization at batch review.
☑ No unrelated refactoring
☑ No scope creep - only T118-scope executor, tests, and its console-script entry.
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required