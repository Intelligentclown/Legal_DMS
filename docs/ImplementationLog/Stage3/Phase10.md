------------------------------------------------

# Stage 3 – Phase 10

Status: Done

Started: 2026-09-02

Completed: 2026-09-02

Related Tasks: T108

Related ADRs: ADR-0033

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement T108's read-only Party/Client migration preflight so the legacy Client graph can be inventoried and classified for Organization evidence without mutating any database state.

## Tasks Implemented

- Added `client-migration-preflight`, a dedicated backend CLI with a testable read-only core that inventories every legacy Client anchor and the authorized dependent graph across `clients`, `addresses`, `client_contacts`, `matters`, `property_owners`/`properties`, `appointments`, `invoices`, and `payments`.
- Implemented ADR-0033 SS6.2 evidence classification using only reconciled `created_by`/`updated_by` users, optional prior ledger evidence, and already-resolved explicit FK-linked records from the same migration slice.
- Emitted a machine-readable JSON audit report that records per-node classification, candidate Organization ids, and evidence paths for operator review.
- Added focused integration tests covering deterministic evidence, zero evidence, conflicting evidence, and cross-tenant Address conflict scenarios.

## Files Modified

- `backend/src/app/infrastructure/cli/client_migration_preflight.py`
- `backend/tests/integration/test_client_migration_preflight.py`
- `backend/pyproject.toml`
- `docs/ImplementationLog/Stage3/Phase10.md`

## Tests Added

- `backend/tests/integration/test_client_migration_preflight.py`
  Proves deterministic classification, zero-evidence fail-closed behavior, conflicting-evidence ambiguity, and cross-tenant Address ambiguity for the T108 preflight logic.

## Test Results

- `cd backend && uv run ruff check src tests` -> passed.
- `cd backend && uv run black --check src tests` -> passed.
- `cd backend && uv run python -c "from app.infrastructure.cli.client_migration_preflight import run_client_migration_preflight; print('import-ok')"` -> passed.
- `python scripts/governance_validate.py` -> passed (`0` warnings, `0` errors).
- `git diff --check` -> clean.
- `cd backend && uv run pytest tests/integration/test_client_migration_preflight.py -q` -> could not complete in this environment because the configured Postgres test database was unavailable/refused connection.
- `cd backend && uv run pytest tests/unit -q` -> 254 tests passed, 10 unrelated pre-existing environment errors in `tmp_path`-using tests because pytest could not write to the host temp directory exposed to this session.

## Design Decisions

- Kept the implementation surface intentionally small by following the existing T105 CLI pattern: a thin CLI entrypoint over a testable async core rather than introducing routes, container wiring, or a new service layer abstraction that no current caller needs.
- Treated the report as the auditable operator-review artifact, with explicit evidence paths and per-node classifications, instead of introducing any write path or reconciliation persistence in T108 itself.
- Used a fixed-point resolution pass so only already-deterministic linked records can contribute evidence, matching ADR-0033's "already resolved by this same algorithm" rule.

## Problems Encountered

- The backend test environment in this session did not have a reachable Postgres instance for the configured integration database, so the new database-backed tests could be added but not executed to completion here.
- Some unrelated existing unit tests rely on pytest-managed temp paths under the host temp directory, which this session could not write to; that produced environment errors unrelated to T108's code.

## Deferred Work

- If a later task introduces a governed reconciliation ledger artifact format, the preflight's optional ledger-evidence input can be tightened to that exact durable schema instead of the intentionally minimal shape used here.

## Future Considerations

- Independent QA should run the new integration test file against the repository's normal Postgres-backed test environment to confirm the four T108 evidence cases on a live database.
- If operator workflows need smaller scoped runs later, a future authorized task could add report filtering or output-file flags without changing T108's classification rules.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
□ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

Notes:
- Existing tests pass: `□` because the new integration tests could not complete without a reachable Postgres test database, and 10 unrelated existing unit tests failed for host temp-directory permission reasons in this session.
- ADR updated (if required): `□` because T108 implements ADR-0033; it does not change the architecture.
- AI_BOOTSTRAP updated (if required): `□` because no bootstrap/process rule changed.
- PROJECT_STATE updated (if required): `□` because project-wide status synchronization belongs after QA/closeout, not this implementation task.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
