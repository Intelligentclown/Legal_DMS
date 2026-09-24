# Stage 3 - Phase 30

Status: Implementation complete; awaiting independent QA

Related Tasks: T135

Related ADRs: ADR-0021, ADR-0022, ADR-0023, ADR-0036, ADR-0039

## Objective

Provide the bounded, Organization-scoped Property application surface and
Party-canonical ownership CRUD authorized by T135 over the T133 tenant-
finalized schema, without creating or manufacturing legacy Client identity.

## Tasks Implemented

- Added an Organization-scoped Property repository and application service.
- Added `GET /properties`, `GET /properties/{id}`, `POST /properties`, and
  `PUT /properties/{id}` using the already-seeded `properties:read` and
  `properties:write` permissions (no permission or Alembic migration).
- Creates Party-canonical `PropertyOwner` rows atomically with a Property:
  `party_id` is set and `client_id` remains `NULL` — Client identity is never
  manufactured and never accepted on the write surface.
- Preserves legacy non-null `PropertyOwner.client_id` links for read
  compatibility, exposed only as `legacy_client_id`, never rewritten and
  never offered as a write control.
- Bounded update mutates only the ordinary scalar Property fields
  (`property_type`, `survey_number`, `sub_division_number`, `area_value`,
  `area_unit`, `address_id`, `village_id`, `registration_number`) and never
  touches owner rows.
- DELETE is deliberately omitted (no governed Property lifecycle/deletion
  contract exists; no cascade or soft-delete behavior is introduced).

## Files Modified

- Property repository port, SQLAlchemy repository, service, v1 router and its
  registration (`presentation/api/v1/router.py`).
- Focused unit/API integration tests and this implementation log.

## Tests Added

- Service tests prove Client-free Party-canonical creation, invalid/cross-Org
  owner and cross-Org Address rejection before aggregate persistence,
  duplicate Party ownership rejection, unknown Village reference rejection,
  required/uncorrectable `survey_number`, and bounded update that preserves
  owner rows.
- Disposable PostgreSQL API tests prove canonical writes with zero Client
  manufacture, tenant isolation (cross-Org Property reads 404 / list empty),
  update permission behavior, extraneous `client_id` body fields being
  ignored, DELETE omission (405), cross-tenant owner/Address fail-closed 422
  with no partial Property or PropertyOwner rows, and safe legacy reads
  without canonical rewrite or Party manufacture.

## Test Results (Developer Self-Assessment)

- Focused Property service/API: 12 passed.
- T133 Property/MatterParty-adjacent foundation/RLS: 3 passed.
- T134 Matter routes: 3 passed; Matter/MatterParty foundation/RLS: 3 passed.
- Party tenant/RLS: 26 passed.
- Address tenant/RLS: 25 passed.
- Backend unit suite: 326 passed, 60 warnings.

## Design Decisions

- Ownership is a canonical-creation concern only: `owners` are accepted on
  create, each requiring a same-Organization `party_id`, a `from_date`, and
  bounded ownership metadata (`ownership_share` within the model CHECK's
  `(0, 100]`, `to_date` never before `from_date`, duplicate Party ownership
  rejected). Update intentionally has no `owners` field.
- `PropertyRead.owners[]` keeps Party and legacy Client identity in separate
  fields — `party_id` (canonical) and `legacy_client_id` (compatibility
  shadow) — so the API contract never collapses the two into one ambiguous
  field (mirrors T134's `legacy_client_id` precedent).
- No installation-state write gate is introduced: T135 explicitly does not
  copy or generalize `PartyWriteGate`, mirroring T130's AddressService
  reasoning. Reads and writes are protected by permission + Organization
  scoping + T133 forced RLS.
- No Alembic migration, no RLS changes, no schema changes, no PartyWriteGate
  changes; the Alembic head remains `9e6a4b2c8d1f`.
- `MatterProperty`, Scheme/Revenue/CitySurvey/TP/FP, File/Document,
  `survey_number` redesign, and Client retirement remain out of scope.

## Problems Encountered

- None. (The existing Windows PowerShell/console-encoding quirks were handled
  with the repository's established temp-file pattern; no impact on output.)

## Deferred Work

- Owner mutation after create, Property deletion/lifecycle, MatterProperty,
  village/address hierarchy-consistency traversal, Scheme/Revenue architecture,
  and Client retirement remain out of scope for T135.

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