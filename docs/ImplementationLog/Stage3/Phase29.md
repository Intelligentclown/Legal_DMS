# Stage 3 - Phase 29

Status: Implementation complete; awaiting independent QA

Related Tasks: T134

Related ADRs: ADR-0021, ADR-0022, ADR-0023, ADR-0039

## Objective

Provide the bounded Party-canonical, Organization-scoped Matter application
surface authorized by T134, without creating legacy Client identity.

## Tasks Implemented

- Added an Organization-scoped Matter repository and application service.
- Added `GET /matters`, `GET /matters/{id}`, `POST /matters`, and
  `PUT /matters/{id}` using existing `matters:read` and `matters:write`
  permissions.
- Creates canonical `MatterParty(role="client")` participation atomically
  with a Matter whose `client_id` remains `NULL`.
- Preserves legacy non-null `Matter.client_id` for read compatibility; it is
  exposed only as `legacy_client_id`, never as a write control.

## Files Modified

- Matter repository port, SQLAlchemy repository, service, v1 router and its
  registration.
- Focused unit/API integration tests and this implementation log.

## Tests Added

- Service tests prove Client-free canonical creation and invalid participant
  rejection before aggregate persistence.
- Disposable PostgreSQL API tests prove canonical writes, zero Client
  manufacture, tenant isolation, update permission behavior, and safe legacy
  reads without automatic MatterParty backfill.

## Test Results

- Focused Matter service/API: 5 passed.
- T132 Matter/MatterParty foundation/RLS: 3 passed.
- Party tenant/RLS: 26 passed.
- Address tenant/RLS: 25 passed.
- Backend unit suite: 317 passed, 61 warnings.

## Design Decisions

- Multiple additional participants can be supplied on create only; participant
  mutation is intentionally not exposed by update.
- `property_id` is deliberately not exposed. Matter creation requires no
  Property and does not decide MatterProperty architecture.
- DELETE is intentionally omitted: existing downstream Matter references need
  a separately governed lifecycle/conflict decision; no cascade or soft-delete
  behavior is introduced.

## Problems Encountered

- Large combined pytest output exceeded the interactive capture boundary.
  Matter, Party, and Address regression files were rerun independently with
  redirected logs and definitive exit status.

## Deferred Work

- Participant mutation, MatterProperty, classification/work-type redesign,
  File/Document work, Client retirement, and PartyWriteGate evolution remain
  out of scope.

## Future Considerations

- Independent QA should rerun the full application/integration ledger and
  runtime-role/GUC fixtures on the exact implementation head.

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

☑ Approved
□ Approved with comments
□ Rework required

