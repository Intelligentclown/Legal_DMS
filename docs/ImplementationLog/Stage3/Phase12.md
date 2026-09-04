------------------------------------------------

# Stage 3 - Phase 12

Status: Done

Started: 2026-09-04

Completed: 2026-09-04

Related Tasks: T111

Related ADRs: ADR-0033

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement T111's read-only live reconciliation/staleness preflight, proving that current T108 Client evidence remains equivalent to the frozen T108/T109 reconciliation basis before any separately authorized write-capable work.

## Tasks Implemented

- Added `client-reconciliation-staleness-preflight`, a CLI wrapper over a testable async core.
- Reused T110 validation before recomputing T108 through its existing read-only core.
- Canonically compared each current Client snapshot and the complete Client-anchor set against the validated frozen reconciliation basis.
- Returned machine-readable per-anchor and overall stale/executable results, including fail-closed handling for malformed governed input, current snapshot drift, anchor-set drift, duplicate current anchors, and missing selected Organizations.

## Files Modified

- `backend/src/app/infrastructure/cli/client_reconciliation_artifact_validator.py`
- `backend/src/app/infrastructure/cli/client_reconciliation_staleness_preflight.py`
- `backend/tests/integration/test_client_migration_preflight.py`
- `backend/tests/unit/test_client_reconciliation_staleness_preflight.py`
- `backend/pyproject.toml`
- `docs/ImplementationLog/Stage3/Phase12.md`

## Tests Added

- `backend/tests/unit/test_client_reconciliation_staleness_preflight.py`
  Covers unchanged live evidence, classification/candidate/evidence/note drift, missing and extra anchors, duplicate current anchors, malformed artifact input, and disappeared selected Organizations.

## Test Results

- `cd backend && uv run pytest tests/unit/test_client_reconciliation_staleness_preflight.py tests/unit/test_client_reconciliation_artifact_validator.py -q` -> 21 passed.
- `cd backend && uv run pytest tests/integration/test_client_migration_preflight.py -q` -> 4 passed.
- `cd backend && uv run pytest -q` -> 577 passed, 21 skipped, 83 existing dependency/deprecation warnings.
- `cd backend && uv run ruff check src tests alembic` -> passed.
- `cd backend && uv run black --check src tests alembic` -> passed (223 files unchanged).
- `python scripts/governance_validate.py` -> passed (0 warnings, 0 errors).
- `python scripts/tests/test_governance_validate.py` -> 51 passed.
- `git diff --check` -> clean.

## Design Decisions

- T111 uses T110 as the frozen-input and selected-Organization validation boundary, then invokes T108's existing read-only report generator for authoritative current evidence.
- The only live comparison is the T109-authorized canonical comparison of Client snapshots and Client-anchor membership. No direct-live-graph mechanism, persistence model, or write-capable executor was introduced.

## Problems Encountered

- The full backend suite exposed a pre-existing flaky T108 test fixture: its random two-character Country ISO code could collide within a single test transaction. The helper now selects an unused code from the transaction before inserting; T108 production behavior and assertions are unchanged.

## Deferred Work

- Any future direct legacy-graph inspection, execution persistence, or write-capable Party migration remains separately unauthorized.

## Future Considerations

- A future executor may proceed only when this preflight reports both `valid` and `executable`; it must not reinterpret or repair stale reconciliation input.

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

Notes:

- ADR updated: □ - T111 implements the accepted T108/T109/T110 boundaries without changing architecture.
- AI_BOOTSTRAP updated: □ - no bootstrap or process rule changed.
- PROJECT_STATE updated: □ - project-wide status synchronization belongs after independent QA.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
