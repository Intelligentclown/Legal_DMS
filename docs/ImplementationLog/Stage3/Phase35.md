------------------------------------------------

# Stage 3 – Phase 35

Status: Implementation / pre-QA verification in progress — not QA-ready

Started: 2026-09-26

Completed:

Related Tasks: T142

Related ADRs: ADR-0020, ADR-0021, ADR-0022, ADR-0041, ADR-0042

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement T142's canonical DocumentVersion application surface and ADR-0042 request outcome infrastructure.

## Tasks Implemented

Implemented ADR-0042/T144 request-local transaction outcome handling and the canonical nested immutable DocumentVersion surface.

## Files Modified

Backend transaction/session dependencies, DocumentVersion repository/service/router,
focused outcome tests, PostgreSQL production-path API evidence, and this log.

## Tests Added

`tests/unit/test_transaction_outcome.py` covers LIFO compensation ordering,
continue-after-cleanup-failure behavior, confirmed/uncertain suppression, and actual
function-scoped FastAPI yield-dependency finalization behavior.

`tests/unit/test_document_version_service.py` covers durable idempotency
reconciliation after the Document allocation lock and definitive-noncommit cleanup.

`tests/integration/test_t142_document_version_routes.py` exercises the production
route graph and `get_db` dependency against disposable PostgreSQL, including
same-Document idempotency races, different-Document independence, real RLS,
single-session transaction-local Organization GUC proof through commit, response
ordering, definitive and uncertain commit paths, durable retry reconciliation,
RBAC/hierarchy/legacy-fileless rejection, integrity failures, cancellation, and
storage-compensation failure behavior.

## Test Results

- Focused T142 unit and PostgreSQL production-path suites: `20 passed` (6 unit,
  14 integration), using disposable databases provisioned through the repository
  helpers and shell-only local Compose URLs on port `5433`.
- `ruff check src tests alembic`, `black --check src tests alembic`, `alembic heads`,
  `alembic current`, `scripts/governance_validate.py --report`, and `git diff --check`
  completed cleanly. Alembic head/current is `cdcfd7df5fde`.
- The identical complete backend command was also run in a detached clean worktree at
  exact `origin/main` `6b8923c6abda09fcab5e480bb545390e130d202b`, with the same
  shell-only local PostgreSQL configuration. Baseline: `775 passed, 66 failed`;
  candidate: `796 passed, 65 failed`. The candidate introduces 20 focused T142 tests,
  all passing. Of the inherited corpus, it introduces **zero** new failed nodes; the
  sole baseline-only failure is
  `tests/integration/test_t138_file_migration_and_allocator.py::test_same_matter_concurrent_allocation_is_unique_and_rollback_reuses_number`,
  which passes on the candidate.
- To compare cause rather than only totals, each side's failed-node cache was rerun
  with a JUnit report. The reruns retained 62 baseline and 61 candidate failures;
  all 61 common node IDs had identical normalized exception/assertion signatures
  (exception type plus first meaningful failure message). There were zero
  candidate-only failures and no signature mismatch. The difference is inherited
  test-state sensitivity, not a T142 regression.
- The inherited failures remain outside the T142 diff (audit logging, legacy
  client-migration, organization-required fixtures, operational-fresh/provenance,
  and other existing areas). Untouched `origin/main` still contains a manifest test
  expecting `T128` even though its project state records T144. This baseline debt is
  recorded but not repaired under T142.

## Design Decisions

ADR-0042's session-local request outcome context is being applied without changing ADR-0020 transaction ownership.

## Problems Encountered

The existing backend dependency set does not include `python-multipart`; the upload endpoint uses exact raw bytes and server-visible headers rather than introducing a dependency.

Earlier T142 stops are retained: ADR-0020's pre-T143 commit-outcome gap; FastAPI default request-scoped yield teardown ordering before T144; and an environmental PostgreSQL port/credential mismatch. T143/T144 supplied the first two architecture decisions; the final test run used the existing Compose service at port 5433 without reading or copying a private `.env`.

## Deferred Work

Independent QA, governance synchronization, and merge remain outside the Developer role and are not started.

## Future Considerations

Independent QA and governance synchronization remain outside the Developer role and
do not begin until Control Tower independently verifies the resulting exact PR head.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass — focused evidence is green; full-suite failures are
baseline-identical with zero T142-introduced regressions.
☑ Documentation updated
□ ADR updated (if required) — no new decision.
□ AI_BOOTSTRAP updated (if required) — not applicable.
□ PROJECT_STATE updated (if required) — Documentation Manager ownership after QA.
☑ No unrelated refactoring
☑ No scope creep
□ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
