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

## Test Results (Developer Self-Assessment)

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

## Independent QA Verification

- **QA Role:** Independent QA Reviewer / Antigravity
- **Formal Verdict:** Approved
- **Exact Implementation Commit Reviewed:** `801a4682f30dbab9804b9d35f30dedd2f90fbcf9`
- **Original QA Evidence Commit:** `b452e3cb09a1d75bb34fb3003aaef77bbadf4c5d` (Documentation-only descendant)

### Architectural Acceptance & Domain Invariants
- **Party-Canonical Creation:** `POST /matters` creates a `Matter` with `client_id = NULL` and an atomic `MatterParty(role="client", party_id=<Party>)`.
- **Zero Client Manufacture:** Proven independently via disposable PostgreSQL test `test_canonical_create_has_no_client_and_is_scoped`. Client row count before and after `POST /matters` is verified identical (`clients_before == clients_after`).
- **Atomicity:** `SqlAlchemyMatterRepository.add_with_participants` executes inside an `async with self._session.begin_nested():` savepoint. Invalid/cross-tenant participants fail closed before aggregate persistence with HTTP 422 (`ValidationError`), leaving 0 Matter and 0 MatterParty rows.
- **Organization Authority:** `_require_organization(current_user)` derives tenant identity strictly from `current_user.organization_id` (JWT context). Callers cannot override tenant identity. All participant Parties must belong to the caller's Organization; cross-Organization references fail closed (`ValidationError`).
- **Tenant Isolation:** `list_matters` and `get_matter` scope queries strictly by `organization_id`. Cross-tenant Matter IDs return HTTP 404 (`NotFoundError`), rendering them invisible across tenants.
- **Bounded Updates:** `PUT /matters/{id}` permits updating authorized scalar fields (`matter_type_id`, `matter_status_id`, `title`, `description`, `opened_at`, `closed_at`). Canonical `client_id` remains `NULL`, existing `MatterParty` rows are preserved, participant mutation is omitted, and extraneous request body fields (e.g. `client_id`) are ignored.
- **Permission Enforcement:** `matters:read` for GET endpoints, `matters:write` for POST and PUT endpoints. Requests lacking write permission return HTTP 403 (`ForbiddenError`).
- **Legacy Read Compatibility:** Reads legacy `Matter` (`client_id != NULL`) safely without canonical rewrite, Client deletion, or manufactured `MatterParty` rows. `client_id` is exposed only as `legacy_client_id` for read compatibility.
- **Participant Semantics:** Supports canonical client-role Party (`(client_party_id, "client")`) plus optional additional participants `[(party_id, role)]`. Validates non-empty role strings, duplicate `(party_id, role)` pairs, and same-Organization membership for all parties.
- **Boundary Audits:**
  - Property is omitted from the Matter application surface (no Property CRUD or MatterProperty changes).
  - DELETE endpoint omission is justified due to unmanaged downstream cascade/conflict lifecycle contracts.
  - Classification uses existing `matter_type_id` and `matter_status_id` lookup models; no `MatterClassification` or `MatterWorkType` added.
  - Matter creation requires no File; no File/Document changes.
  - `PartyWriteGate` is unchanged and remains Party-specific.
  - No Alembic migration added or modified; Alembic head remains `9e6a4b2c8d1f`.
  - `get_db()` connects as `legal_dms_app` (`NOBYPASSRLS`). Forced PostgreSQL RLS on `matters` and `matter_parties` remains active.

### Independent Test Evidence
- **T134 Matter routes/service suite:** 5 passed (`test_matter_routes.py` [3], `test_matter_service.py` [2]).
- **Matter/MatterParty RLS foundation suite:** 3 passed (`test_matter_tenant_party_foundation.py`).
- **Party tenant/RLS suite:** 26 passed (`test_party_tenant_finalization_and_rls.py`).
- **Address tenant/RLS suite:** 25 passed (`test_address_tenant_finalization_and_rls.py`).
- **Auth/authorization regressions:** 84 passed (`test_auth_login.py` & `test_users.py`).
- **Backend unit suite:** 317 passed, 60 warnings, 0 failed.
- **Key integration regression partition:** 61 passed (0 failed).
- **Broader integration execution:** 481+ passed across file partitions.

### Independent Quality & Governance Evidence
- **Ruff:** All checks passed clean on 7 changed Python files.
- **Black:** 7 changed Python files clean (`0 files modified`).
- **Governance Validator:** `python scripts/governance_validate.py` returned `OK (0 warning(s), 0 errors)`.
- **`git diff --check`:** Clean (0 whitespace or syntax issues).
- **Exact-Head GitHub CI (`801a4682f30dbab9804b9d35f30dedd2f90fbcf9`):** Backend, Frontend, Release build, and Governance workflows green.

### QA Findings
- **Blocking Findings:** None.
- **Non-Blocking Findings:** None.
- **Verdict Application:** Approval applies specifically to commit `801a4682f30dbab9804b9d35f30dedd2f90fbcf9`.

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required
