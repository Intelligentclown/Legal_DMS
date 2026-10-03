# T152 Independent QA Review — Acceptance & Party-Canonical Matter Conversion Application Surface

**Frozen Candidate Reviewed:** `19a5f1ca1b399c2bb5e2f87de84609fb53796428`  
**Protected Base Commit:** `0cfc44743f798424abcb9e1b8844e577c5de5aa7` (`main`)  
**Pull Request:** #284 (`feat(preengagement): T152 acceptance matter conversion`)  
**Branch:** `feature/t152-acceptance-matter-conversion`  
**Reviewer:** Independent QA Reviewer (Antigravity)  
**Date:** 2026-10-03  

---

## 1. Executive Summary & Formal Verdict

- **Formal Verdict:** **Approved**
- **Exact Candidate SHA Evaluated:** `19a5f1ca1b399c2bb5e2f87de84609fb53796428`
- **Scope & Governance:** 6 changed files (+554 / -6 lines). Pure application layer, service orchestration, REST API routes, and integration tests. Zero migrations, schema changes, seed data modifications, RLS policy changes, or ADR mutations. Preserves unresolved Required ADRs `[12, 15, 16, 17, 20]`. ADR-0043 remains unchanged and `Proposed`.
- **Migration Frontier:** Preserved at `8d77007b9d7f` (T150).
- **Operational-Fresh Provenance:** Preserved at `8d77007b9d7f`.

---

## 2. Baseline & Candidate Verification

- **Protected Base SHA (`main`):** `0cfc44743f798424abcb9e1b8844e577c5de5aa7` (contains merged T152 authorization PR #283).
- **Frozen Implementation Candidate SHA:** `19a5f1ca1b399c2bb5e2f87de84609fb53796428`
- **PR #284 Verification:** OPEN, unmerged, non-draft, mergeable against `main` (1 commit ahead, 0 behind).
- **Governance Ledger Baseline:**
  - `latestTaskDone`: T151
  - `latestTaskAuthorized`: T152
  - `inProgressTransitions`: `[]`
  - `unresolvedRequiredAdrs`: `[12, 15, 16, 17, 20]`
  - Validator: `python scripts/governance_validate.py --report` returns `OK (0 errors)`.

---

## 3. Scope & Diff Audit

Changed files (exactly 6 files):
1. `backend/src/app/application/acceptance_service.py` (+113 lines)
2. `backend/src/app/application/interfaces/enquiry_repository.py` (+18 / -1 lines)
3. `backend/src/app/infrastructure/persistence/sqlalchemy_enquiry_repository.py` (+34 / -1 lines)
4. `backend/src/app/presentation/api/v1/enquiries.py` (+79 / -4 lines)
5. `backend/tests/integration/test_t149_enquiry_quotation_routes.py` (+197 lines)
6. `docs/ImplementationLog/Stage3/Phase39.md` (+119 lines)

Total stats: 6 changed files, 554 additions, 6 deletions.

Audit confirmed: NO Alembic migrations, NO schema changes, NO seed modifications, NO RLS changes, NO Client manufacture, NO automatic File creation, NO fuzzy-matched Party creation, NO frontend components, NO ADR modifications, NO status enum additions.

---

## 4. Code & Architecture Assessment

### 4.1 Pre-Engagement Hierarchy & Eligibility
- **Hierarchy Validation:** `AcceptanceService.accept()` validates the full `Organization -> Enquiry -> Quotation -> QuotationRevision` chain using `EnquiryService.quotation()` and `EnquiryService.revision()`. Cross-tenant or mismatched hierarchy IDs raise non-enumerating `NotFoundError` (404).
- **Revision Eligibility:** Eligibility is strictly derived from persisted paired issuance facts (`revision.issued_at is not None and revision.issued_by is not None`). Unissued revisions raise `ValidationError` (422). Paired T150 issuance evidence remains immutable.

### 4.2 Canonical Party Prerequisite & Matter Outcome
- **Party Prerequisite:** Requires `enquiry.party_id is not None`. An unlinked prospect-only enquiry raises `ValidationError` (422) rather than manufacturing a Party.
- **Matter Contract:** Calls `MatterService.create_in_organization(organization_id, fields, enquiry.party_id, [])`.
  - Creates `Matter(client_id=None)`.
  - Creates `MatterParty(role="client", party_id=enquiry.party_id)`.
  - Does NOT manufacture a Client row.
  - Does NOT create a File row.
  - Validates `matter_type_id` and `matter_status_id` against active reference data; invalid inputs cause atomic rollback.

### 4.3 Provenance & Idempotency
- **Acceptance Provenance:** Immutable `Acceptance` record links `quotation_revision_id`, `matter_id`, `enquiry_id`, `quotation_id`, `accepted_by=actor_id`, and `organization_id`.
- **Deterministic Fingerprinting:** Computes SHA-256 hash over `enquiry_id`, `quotation_id`, `revision_id`, and accepted matter creation fields (`matter_number`, `matter_type_id`, `matter_status_id`, `title`, `description`, `opened_at`).
- **Deterministic Replay Behavior:**
  - Same `Idempotency-Key` + identical request: Returns original `(Acceptance, Matter)` tuple with `replayed=True` (HTTP 200 OK).
  - Same `Idempotency-Key` + changed request: Raises `ConflictError` (HTTP 409).
  - Different `Idempotency-Key` after conversion: Raises `ConflictError` (HTTP 409, "Enquiry has already been converted").

### 4.4 Concurrency & Transaction Safety
- **Serialization Point:** `SqlAlchemyEnquiryRepository.lock_enquiry(organization_id, enquiry_id)` executes `SELECT ... FOR UPDATE` on the Organization-scoped Enquiry before checking existing Acceptance state.
- **Locking & Re-check:** Competing conversion requests block on the Enquiry row lock. After acquiring the lock, `acceptance_for_enquiry()` re-checks state so the second request receives HTTP 409 Conflict.
- **Transaction Ownership:** `AcceptanceService` and repositories perform `flush()` only, never `commit()`. Transaction ownership remains strictly with FastAPI's request-scoped `get_db()` lifecycle. In case of failure or exception, the entire request rolls back cleanly, leaving no partial Matter, MatterParty, or Acceptance row.

### 4.5 RBAC & Security
- **Dual Authority Required:** `POST /api/v1/enquiries/{enquiry_id}/quotations/{quotation_id}/revisions/{revision_id}/accept` requires BOTH `Depends(RequirePermission("quotations:accept"))` and `Depends(RequirePermission("matters:write"))`.
- **RBAC Matrix Enforcement:** Requests missing either permission return HTTP 403 Forbidden.
- **Tenant Isolation:** `organization_id` is derived exclusively from trusted caller context (`_organization(current_user)`). Non-enumerating responses prevent information disclosure.

---

## 5. Independent Test Evidence & Verification

### 5.1 Verification Commands Executed
- `cd backend && uv run pytest tests/unit -q` -> **342 passed** (60 pre-existing dependency warnings).
- `cd backend && uv run ruff check src tests alembic` -> **All checks passed!**
- `cd backend && uv run black --check src tests alembic` -> **322 files unchanged.**
- `python scripts/governance_validate.py --report` -> **0 errors, 0 warnings.**

### 5.2 GitHub Actions CI Verification
All four GitHub CI workflows ran on exact candidate `19a5f1ca1b399c2bb5e2f87de84609fb53796428` and PASSED:
- **Governance** (`37108834592`): SUCCESS
- **Backend** (`37108834604`): SUCCESS
- **Frontend** (`37108834579`): SUCCESS
- **Release** (`37108834614`): SUCCESS

### 5.3 Full-Suite Integration Environment Assessment
The local developer environment note regarding `cd backend && uv run pytest -x -q` encountering PostgreSQL database configuration differences was investigated. In the local environment, `DATABASE_URL` in `.env` targets port 5433 (docker postgres default), while a local Windows PostgreSQL 18 service runs on port 5432 with separate credentials. In CI (which uses an isolated PostgreSQL service container running fresh migrations), all backend integration tests pass 100% cleanly.

---

## 6. Excluded Domains & Governance Audit

- **No Alembic migrations or schema changes:** Migration frontier remains `8d77007b9d7f`.
- **No seed/permission mutations:** Role and permission seeds remain untouched.
- **No ADR mutations:** `ADR-0043` remains `Status: Proposed` and `Resolves: None`.
- **Required ADRs state:** Unresolved Required ADRs remain `[12, 15, 16, 17, 20]`.
- **No domain leakage:** No Client manufacture, automatic File creation, financial ledger expansion, or frontend work occurred.

---

## 7. QA Decision & Marker

- **QA Verdict:** **Approved**
- **Candidate SHA:** `19a5f1ca1b399c2bb5e2f87de84609fb53796428`

**T152 INDEPENDENT QA APPROVED — AWAITING CONTROL TOWER VERIFICATION**
