------------------------------------------------

# Stage 3 – Phase 48

Status: Implementation candidate ready for Independent QA

Started: 2026-10-20

Completed: 2026-10-20

Related Tasks: T169; Issue #339; authorization PR #344

Related ADRs: ADR-0020; ADR-0021; ADR-0022

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Reproduce the backend full-suite failures recorded for T167, verify the current
production contracts behind each historical cluster, and make only the
test-infrastructure, fixture, expectation, and regression changes authorized
for T169.

## Tasks Implemented

- Verified protected `origin/main` at
  `284bccad1d3a6024b964c3f420fe7f3e53330c4e` before creating the dedicated
  implementation branch.
- Reproduced the complete backend suite against a disposable PostgreSQL 16
  environment, classified the historical T167 failures, and separately
  identified three runner-network timeouts as environmental.
- Reconciled fixtures and expectations with the current tenant-bound
  non-null/composite-foreign-key contracts, RLS policy catalog, seed data and
  static RBAC matrix.
- Preserved application logging during in-process Alembic execution and added
  a real migration/logging regression test.
- Reconciled the specifically authorized stale Current Context Manifest test:
  mechanically derived governance now reports T170 as the latest Done task.

## Files Modified

- `backend/alembic/env.py`
- `backend/tests/support/synthetic_migration.py`
- `backend/tests/integration/test_alembic_logging.py`
- `backend/tests/integration/test_client_migration_executor.py`
- `backend/tests/integration/test_client_migration_preflight.py`
- `backend/tests/integration/test_financial_models.py`
- `backend/tests/integration/test_matter_and_workflow_models.py`
- `backend/tests/integration/test_organizations_users_rls.py`
- `backend/tests/integration/test_property_models.py`
- `backend/tests/integration/test_scheduling_models.py`
- `backend/tests/integration/test_seed_data.py`
- `backend/tests/integration/test_t66_role_permissions.py`
- `scripts/tests/test_current_context_manifest.py`
- `docs/ImplementationLog/Stage3/Phase48.md`

## Tests Added

- `test_in_process_alembic_preserves_existing_audit_logger_and_cli_current` runs the
  fresh-install migration path and verifies an `app.audit` log event still
  reaches its handler.
- Modified client, financial, matter, property and scheduling tests now make
  their valid tenant relationship explicit; their existing invalid-path tests
  continue to require database rejection.
- The RLS catalog assertion is exact for the current 19 tenant-bound tables;
  it does not derive expectations from the implementation under test.
- The T66 role-permission assertion uses an explicit current 114-edge matrix.

## Test Results

- Baseline command: `uv run pytest tests -q`, using the initial protected-main
  source in the disposable `legal_dms_t169_baseline` PostgreSQL 16 database:
  **890 passed, 51 failed, 1 error, 87 warnings in 857.36s**. The 45 historical
  T167 failures reproduced across the documented six clusters; four audit
  logging failures reproduced separately. Two failures and one error were
  connection timeouts from the runner's host-network route and are classified
  as environmental, not product or test-contract defects.
- Migration verification for each candidate database: `uv run alembic upgrade
  head`, `uv run alembic heads`, and `uv run alembic current` reported the sole
  `b155caa6d4e1 (head)` revision.
- Execution environment: a disposable `postgres:16-alpine` container (PostgreSQL
  16.15) on a private Docker network; each database was created empty, had the
  `legal_dms_app` runtime role provisioned, then was migrated from scratch by
  the runner image (`python:3.12-slim`, Python 3.12 and the locked `uv`
  environment). The runner reached PostgreSQL by the private service name,
  not a shared host database.
- Focused candidate command over the changed integration modules:
  **80 passed, 1 warning in 14.55s**.
- Candidate full suite run 1 command: `uv run pytest tests -q`, on independently
  initialized `legal_dms_t169_post1` PostgreSQL 16: **942 passed, 87 warnings
  in 418.98s**.
- Candidate full suite run 2 command: `uv run pytest tests -q`, on independently
  initialized `legal_dms_t169_post2` PostgreSQL 16: **942 passed, 87 warnings
  in 519.02s**.
- Governance: `python scripts/governance_validate.py` — passed with 0 warnings
  and 0 errors. `python -m pytest scripts/tests -q` — **86 passed, 36 subtests
  passed in 1.00s** after reconciling the stale T168 expectation.
- Static checks: `uv run black --check src tests alembic` — **332 files would
  be left unchanged**; `uv run ruff check src tests alembic` — **All checks
  passed**.
- The full-suite warnings are pre-existing Starlette/httpx deprecations and
  short JWT-secret fixture warnings; no warning suppression was introduced.

## Design Decisions

- `fileConfig(..., disable_existing_loggers=False)` is limited to Alembic
  bootstrap/test infrastructure. It prevents configuration from disabling the
  existing application audit logger during a multi-file test process without
  altering audit behavior or production API contracts.
- Production contracts, not historic fixture assumptions, are authoritative:
  Matter, Property, PropertyOwner and Client graphs use one Organization where
  current non-null columns and composite foreign keys require it.
- RLS and seed/RBAC reconciliation keeps exact, static expected sets. No
  assertion was weakened or dynamically derived from the live implementation.

## Problems Encountered

- The existing development PostgreSQL service used a persisted credential that
  did not match its documented runtime default. It was not changed. All
  evidence therefore uses an isolated disposable PostgreSQL 16 container with
  explicitly provisioned test roles.
- The baseline runner's `host.docker.internal` route produced two test failures
  and one test error through `asyncpg.TimeoutError`. Candidate runs used a
  private Docker network and independently initialized databases, eliminating
  this environmental source of noise.
- The T168 manifest test expected an obsolete governance frontier. The current
  mechanically derived repository state is T170, so the test was corrected to
  the verified contract.

## Deferred Work

- Independent QA, protected merge, T169 completion state, and any project-wide
  status changes remain separate authorized roles. This implementation does
  not update them.
- The pre-existing deprecation and test-fixture JWT warnings require separately
  authorized dependency/fixture work; they are not suppressed here.

## Future Considerations

- Any future migration changing tenant-bound tables, seed permissions, or role
  edges must update the corresponding explicit regression contract and provide
  fresh PostgreSQL evidence.
- The development PostgreSQL credential drift should be addressed only through
  a separately authorized environment-maintenance task.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

Notes: no ADR, bootstrap or project-state change is required or authorized for
this bounded implementation. The implementation changes no production model,
route, migration, security policy, transaction architecture, or API contract.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
