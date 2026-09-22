# Stage 3 - Phase 25

Status: Implementation complete; independent QA pending

Started: 2026-09-22

Completed:

Related Tasks: T129

Related ADRs: [ADR-0038](../../../ADR/0038-self-context-projection-authority-contract.md)

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement ADR-0038 Layer A: an on-demand, offline, non-authoritative Current
Context Manifest derived deterministically from existing repository evidence.

## Tasks Implemented

- Added canonical JSON manifest generation with schema, derivation, and source-set versions.
- Reused governance validator semantic functions for task frontier, Required ADR, ADR metadata,
  and governance-ledger consistency rather than parsing validator presentation output.
- Added fail-closed diagnostics for invalid/conflicting authoritative evidence, including dangling
  queue ADR references and modified authoritative source files that cannot truthfully be labelled
  as local Git `HEAD`.

## Files Modified

- `scripts/current_context_manifest.py`
- `scripts/tests/test_current_context_manifest.py`
- `docs/ImplementationLog/Stage3/Phase25.md`

## Tests Added

- Determinism, no wall-clock field, source commit, frontier, Required ADR, ledger-drift, duplicate
  task, dangling ADR reference, missing ADR status, dirty authoritative source, and offline/no-fetch
  coverage for the manifest generator.

## Test Results

- `python scripts/tests/test_current_context_manifest.py -v`: 7 passed.
- `python scripts/tests/test_governance_validate.py -v`: 51 passed.
- `python scripts/governance_validate.py`: passed. `git diff --check`: clean.

## Design Decisions

- The allow-listed source set is `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, numbered ADRs,
  and local Git `HEAD` only. The output is disposable and never committed as a generated artifact.
- Dirty checking is intentionally limited to the authoritative file classes above, so irrelevant
  untracked/generated files do not prevent an otherwise truthful manifest source identity.

## Problems Encountered

- Initial test import and Markdown-emphasis status parsing were corrected before validation.

## Deferred Work

- Task context packages, human-readable rendering, bootstrap adoption, and CI freshness checks
  remain separately authorized future layers.

## Future Considerations

- New supported schema majors must be handled by a future consumer validation task; T129 owns
  generation only.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no new decision
□ AI_BOOTSTRAP updated (if required) — excluded
□ PROJECT_STATE updated (if required) — QA/closeout owned
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
