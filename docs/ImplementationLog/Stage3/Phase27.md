# Stage 3 - Phase 27

Status: Implementation complete; awaiting independent Antigravity QA

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

□ Approved
□ Approved with comments
□ Rework required
