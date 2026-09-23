# Stage 3 - Phase 28

Status: Implementation complete; awaiting independent QA

Started: 2026-09-23

Related Tasks: T133

Related ADRs: ADR-0021, ADR-0037, ADR-0039

## Objective

Finalize the Property and PropertyOwner tenant/security foundation and allow
Party-canonical operational-fresh ownership without manufacturing Client data.

## Tasks Implemented

- Added `9e6a4b2c8d1f` (parent `7f1b9c3d4a2e`): deterministic direct-evidence
  Property Organization derivation, fail-closed ambiguity checks, mandatory
  Property/PropertyOwner ownership, optional legacy `client_id`, and forced
  Organization-GUC RLS on both tables.
- Preserved Client as a same-Organization compatibility/evidence shadow and
  refused downgrade when Party-only owners cannot be represented safely.
- Advanced only the established supported-revision constants and current-head
  fixtures to `9e6a4b2c8d1f`; provenance/classifier semantics are unchanged.

## Files Modified

- T133 migration/model/classifier/fresh-install implementation and focused
  migration tests under `backend/`.
- Current-head provenance fixtures and the two historical staged-schema unit
  contracts intentionally superseded by Property finalization.

## Tests Added

- Disposable PostgreSQL coverage for deterministic Client evidence, conflicting
  evidence rejection, Party-only ownership without Client manufacture,
  same-Organization Party/Client ownership rejection, forced RLS on both
  Property tables, and safe downgrade refusal.

## Test Results

- Focused T133: 3 passed. Final unit suite: 315 passed, 61 warnings, exit 0,
  using pytest's supported external writable `--basetemp`.
- Integration validation was partitioned deterministically by all 48 files:
  466 passed, 21 skipped, 0 failed, 0 errors. This includes classifier (13),
  Matter foundation (3), Party tenant/RLS (26), Address tenant/RLS (25),
  Address RLS preservation (12), and the complete operational-fresh
  provenance file (7). The full invocation was not used because this local
  execution wrapper does not reliably return large-process summaries.
- Intentional/environment-dependent integration skips were 5 transaction
  policy tests, 8 Organization/User RLS tests, 7 tenant-context GUC tests,
  and 1 User Organization end-to-end test. The 7 GUC skips specifically
  require a runtime-role/GUC fixture environment unavailable locally.

## Design Decisions

- Consumed ADR-0039's staged canonicalization; no new ADR or Required ADR #20
  resolution.

## Problems Encountered

- Windows default pytest temp permissions failed unrelated tmp_path tests.
  `--basetemp` at a writable external temporary location produced the final
  315-passing unit run.

## Deferred Work

- Property CRUD, Client retirement, PartyWriteGate changes and downstream
  cutovers remain out of scope.

## Future Considerations

- Independent QA should exercise runtime-role/GUC fixtures, especially the
  seven locally skipped tenant-context GUC tests.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing affected/regression tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
