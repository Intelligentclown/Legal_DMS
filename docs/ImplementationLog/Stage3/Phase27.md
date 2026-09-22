# Stage 3 - Phase 27

Status: Implementation complete; independent re-QA Approved after bounded rework; post-QA governance synchronized; PR #236 pending final merge

Started: 2026-09-22

Related Tasks: T132

Related ADRs: ADR-0021, ADR-0037, ADR-0039

## Objective

Deliver the bounded Matter/MatterParty tenant and Party-canonical schema
foundation without a Matter application write surface or Client retirement.

## Tasks Implemented

- Added migration `7f1b9c3d4a2e`, which derives a NULL Matter Organization
  only from its existing Client Organization and fails closed on absent or
  contradictory evidence before finalizing Matter ownership.
- Retained `matters.client_id` and its compatibility/same-Organization FK,
  while making it nullable so operational-fresh Matters can use MatterParty
  without fabricated Client identity.
- Added forced, default-deny Organization-GUC RLS policies to `matters` and
  `matter_parties`.
- Extended the established T126/T130 provenance-function revision guard and
  classifier/fresh-install revision constants to this migration head.

## Files Modified

- `backend/alembic/versions/7f1b9c3d4a2e_matter_tenant_party_foundation.py`
- `backend/src/app/infrastructure/persistence/models/matter.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- focused and historical migration/provenance regression tests.

## Tests Added

- Disposable-child tests for deterministic Client-only Matter backfill,
  fail-closed missing derivation, Party-canonical nullable Client composition,
  and restricted-role default-deny/Organization-scoped RLS.

## Deferred Work

- Matter CRUD, Property/PropertyOwner changes, Client retirement, and
  PartyWriteGate evolution remain separately governed future work.

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
□ Ready for QA

The full regression suite and independent QA remain outstanding.

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required

### QA lifecycle

- **QA pass #1 — Rework required.** Independent QA reviewed `93b4d7e6791f7a9b9042b1ebfd1a57ffd70386fc`; evidence commit `d2f2b076f0766ba843780d2576809664658ca526` recorded the blocking stale operational-fresh provenance expectation (`5d8a3f2e9c6b` instead of T132 head `7f1b9c3d4a2e`).
- **Bounded remediation.** Commit `40b6c95789352614206fd1eb66361b170aff2923` changed exactly that stale test-head expectation in `backend/tests/integration/test_operational_fresh_provenance.py`; no production implementation or migration changed.
- **QA pass #2 — Approved.** Independent re-QA reviewed remediation head `40b6c95789352614206fd1eb66361b170aff2923`; final QA evidence commit `34e7ce2765792ef983e26d7fcbbd64c6a8fdb8fa` records 66/66 targeted affected/historical PostgreSQL regression tests passing, ruff clean, black clean and diff-check clean. The complete backend suite was not independently run in entirety, so no full-suite-pass claim is made.
- Exact pre-synchronization QA-head CI was green for Backend, Frontend, Governance and Release.
