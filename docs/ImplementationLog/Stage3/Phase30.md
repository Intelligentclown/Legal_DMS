# Stage 3 - Phase 30

Status: Approved by independent QA

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

## Independent QA Verification

- **QA Role:** Independent QA Reviewer / Antigravity
- **Formal Verdict:** Approved
- **Exact Implementation Commit Reviewed:** `2e9226464a5497dc52487f0a333cb4c4c183e9bc`
- **QA Evidence Log Update Target:** `Phase30.md`

### Architectural Acceptance & Domain Invariants
- **Party-Canonical Creation:** `POST /properties` creates a `Property` with an atomic `PropertyOwner` row setting `party_id = <Party>` and `client_id = NULL`.
- **Zero Client Manufacture:** Proven independently via disposable PostgreSQL test `test_canonical_create_has_party_only_owners_and_is_scoped`. Count of `Client` rows before and after canonical `POST /properties` is verified identical (`clients_before == clients_after`).
- **Atomicity:** `SqlAlchemyPropertyRepository.add_with_owners` executes within an `async with self._session.begin_nested():` savepoint. Cross-Organization Party/Address references, invalid Parties, unknown Villages, or duplicate Parties fail closed before aggregate persistence with HTTP 422 (`ValidationError`), leaving 0 Property and 0 PropertyOwner rows.
- **Organization Authority:** `_require_organization(current_user)` derives tenant identity strictly from `current_user.organization_id` (JWT context). Callers cannot select or override tenant identity. Foreign-tenant owner Parties or Address references fail closed.
- **Tenant Isolation:** `GET /properties` and `GET /properties/{id}` scope queries strictly by `organization_id`. Cross-tenant Property IDs return HTTP 404 (`NotFoundError`), rendering them invisible across tenants.
- **Bounded Updates:** `PUT /properties/{id}` permits updating authorized scalar fields (`property_type`, `survey_number`, `sub_division_number`, `area_value`, `area_unit`, `address_id`, `village_id`, `registration_number`). Existing `PropertyOwner` rows are preserved, owner mutation is omitted, `survey_number` cannot be cleared/nullified, and extraneous body fields (e.g., `client_id`) cannot mutate state.
- **Permission Enforcement:** `properties:read` for GET endpoints, `properties:write` for POST and PUT endpoints. Requests lacking write permission return HTTP 403 (`ForbiddenError`).
- **Legacy Read Compatibility:** Reads legacy `PropertyOwner` (`client_id != NULL`, `party_id = NULL`) safely without canonical rewrite, Client deletion, or manufactured `Party` rows. `client_id` is exposed only as `legacy_client_id` for read compatibility.
- **DELETE Omission:** DELETE endpoint is omitted (HTTP 405 `MethodNotAllowedError`), as no governed Property deletion/lifecycle contract exists.
- **Generic `survey_number` Boundary:** `survey_number` is required on create and non-clearable on update per existing generic Property schema constraints (`NOT NULL`). T135 makes no final domain architectural claim that survey numbers universally identify all Gujarat properties or resolve City Survey/TP/FP records.
- **Boundary Audits:**
  - `MatterProperty`, Scheme/Revenue/CitySurvey/TP/FP, File/Document, and Client retirement remain out of scope.
  - `PartyWriteGate` is unchanged and remains Party-specific.
  - No Alembic migration added or modified; Alembic head remains `9e6a4b2c8d1f`.
  - `get_db()` connects as `legal_dms_app` (`NOBYPASSRLS`). Forced PostgreSQL RLS on `properties` and `property_owners` remains active.

### Independent Test Evidence
- **Focused Property unit & integration suite:** 12 passed (`test_property_routes.py` [3], `test_property_service.py` [9]).
- **T133 Property foundation & RLS suite:** 3 passed (`test_property_tenant_party_foundation.py`).
- **T134 Matter routes & foundation suite:** 6 passed (`test_matter_routes.py` [3], `test_matter_tenant_party_foundation.py` [3]).
- **Party tenant/RLS suite:** 26 passed (`test_party_tenant_finalization_and_rls.py`).
- **Address tenant/RLS suite:** 25 passed (`test_address_tenant_finalization_and_rls.py`).
- **Backend unit suite:** 326 passed, 60 warnings, 0 failed.
- **Key integration regression suite:** 63 passed, 7 skipped (0 failed).

### Independent Quality & Governance Evidence
- **Ruff:** Clean on all 8 changed files.
- **Black:** Clean on `backend/src` and `backend/tests` (`255 files left unchanged`).
- **Governance Validator:** `python scripts/governance_validate.py` returned `OK (0 warning(s), 0 errors)`.
- **`git diff --check`:** Clean (0 whitespace or syntax issues).
- **Exact-Head GitHub CI (`2e9226464a5497dc52487f0a333cb4c4c183e9bc`):** All 8 check runs completed successfully.

### QA Findings
- **Blocking Findings:** None.
- **Non-Blocking Findings:** None.
- **Verdict Application:** Approval applies specifically to commit `2e9226464a5497dc52487f0a333cb4c4c183e9bc`.

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required