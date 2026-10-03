# T149 Independent QA Review — Enquiry & Quotation Application Surface and Revision Lifecycle

**Frozen Candidate Reviewed:** `cd678767515a8c9a118f65f8919c77f89c3af5ad`  
**Protected Base Commit:** `af96fc1dbff622a0762245793efb2fb9f801747b` (`main`)  
**Pull Request:** #279 (`feat(preengagement): add T149 enquiry quotation application surface`)  
**Branch:** `feature/t149-enquiry-quotation-application`  
**Reviewer:** Independent QA Reviewer  
**Date:** 2026-10-03  

---

## 1. Executive Summary & Formal Verdict

- **Formal Verdict:** **Approved**
- **Exact Candidate SHA Evaluated:** `cd678767515a8c9a118f65f8919c77f89c3af5ad`
- **Scope & Governance:** 8 changed files (+1,196 / -0 lines). Pure application layer, service orchestration, REST API routes, unit, and PostgreSQL route integration tests. Zero migrations, schema changes, seed data modifications, RLS policy changes, or ADR mutations. Preserves unresolved Required ADRs `[12, 15, 16, 17, 20]`. ADR-0043 remains unchanged.
- **Migration Frontier:** Preserved at `8d77007b9d7f` (T150).
- **Operational-Fresh Provenance:** Preserved at `8d77007b9d7f`.

---

## 2. Baseline & Candidate Verification

- **Protected Base SHA (`main`):** `af96fc1dbff622a0762245793efb2fb9f801747b` (contains merged T150 #278).
- **Frozen Implementation Candidate SHA:** `cd678767515a8c9a118f65f8919c77f89c3af5ad`
- **PR #279 Verification:** OPEN, unmerged, non-draft, mergeable against `main` (1 commit ahead, 0 behind).
- **Governance Ledger Baseline:**
  - `latestTaskDone`: T150
  - `latestTaskAuthorized`: T150
  - `inProgressTransitions`: `[]`
  - `unresolvedRequiredAdrs`: `[12, 15, 16, 17, 20]`
  - Validator: `python scripts/governance_validate.py --report` returns `OK (0 errors)`.

---

## 3. Scope & Diff Audit

Changed files (exactly 8 files):
1. `backend/src/app/application/enquiry_service.py` (+173 lines)
2. `backend/src/app/application/interfaces/enquiry_repository.py` (+68 lines)
3. `backend/src/app/infrastructure/persistence/sqlalchemy_enquiry_repository.py` (+177 lines)
4. `backend/src/app/presentation/api/v1/enquiries.py` (+343 lines)
5. `backend/src/app/presentation/api/v1/router.py` (+2 lines)
6. `backend/tests/integration/test_t149_enquiry_quotation_routes.py` (+178 lines)
7. `backend/tests/unit/test_enquiry_service.py` (+132 lines)
8. `docs/ImplementationLog/Stage3/Phase38.md` (+123 lines)

Total stats: 8 changed files, 1,196 additions, 0 deletions.

Audit confirmed: NO Alembic migrations, NO schema changes, NO seed modifications, NO RLS changes, NO Acceptance endpoints, NO Matter creation, NO Acceptance-to-Matter conversion, NO Party/Client manufacture, NO frontend components, NO ADR modifications, NO status enum additions.

---

## 4. Enquiry Surface QA

- **CRUD Operations:** List (`GET /enquiries`), Get (`GET /enquiries/{id}`), Create (`POST /enquiries`), Bounded Update (`PUT /enquiries/{id}`), Party Link (`PUT /enquiries/{id}/party`).
- **Tenant Isolation:** Organization ID is obtained solely from authenticated token context (`_organization(current_user)`). Payloads cannot supply or override Organization ID.
- **Party Linkage:** Direct Party creation (`party_id` in create payload) and explicit linking (`PUT /enquiries/{id}/party`) validate same-Organization membership via `PartyRepository.get_by_id_in_organization(party_id, organization_id)`. Cross-tenant Party linking raises `ValidationError`.
- **Prospect Evidence:** `prospect_display_name` is required when `party_id` is absent at creation, and until a Party is linked during updates.
- **Bounded Updates:** Updates are restricted to `_ENQUIRY_FIELDS` (`prospect_display_name`, `prospect_phone`, `prospect_email`, `prospect_description`, `prospect_source`). `party_id` cannot be altered through general update payloads.
- **Non-Enumeration:** Requests targeting non-existent or cross-tenant Enquiry IDs return `404 Not Found`.

---

## 5. Quotation & Revision Surface QA

- **Hierarchy Enforcement:** All queries strictly enforce `Organization → Enquiry → Quotation → QuotationRevision`. Mismatches across parent aggregate levels return `404 Not Found`.
- **Quotation Routes:** List (`GET /enquiries/{id}/quotations`), Get (`GET /enquiries/{id}/quotations/{quotation_id}`), Create (`POST /enquiries/{id}/quotations`).
- **Revision Routes:** List (`GET /enquiries/{id}/quotations/{quotation_id}/revisions`), Get (`GET /enquiries/{id}/quotations/{quotation_id}/revisions/{revision_id}`), Create (`POST /enquiries/{id}/quotations/{quotation_id}/revisions`), Issue (`POST /enquiries/{id}/quotations/{quotation_id}/revisions/{revision_id}/issue`).
- **Snapshot Validation:** `proposal_snapshot` requires non-empty dictionary (`Field(min_length=1)`).

---

## 6. Concurrency & Revision Allocation QA

- **Parent Locking:** `lock_quotation()` executes `SELECT ... FROM quotations WHERE id = ... AND organization_id = ... AND enquiry_id = ... WITH FOR UPDATE`.
- **Transaction Lifecycle:** Row lock on parent `Quotation` is acquired *before* calculating `next_revision_ordinal()` (`SELECT COALESCE(MAX(ordinal), 0) + 1`).
- **Request-Scoped Ownership:** Repositories call `await session.flush()`, holding row locks within the FastAPI request transaction without early commits.
- **Database Backstop:** Database unique constraint `uq_quotation_revisions_quotation_id_ordinal` serves as immutable concurrency backstop.
- **Concurrent Request Verification:** Route tests verify concurrent revision creation via `asyncio.gather()`: both requests succeed with HTTP 201 Created and receive distinct ordinals `[1, 2]`.

---

## 7. T150 Issuance Integration

- `issue()` method sets `issued_at = datetime.now(UTC)` and `issued_by = actor_id`.
- T150 database trigger `legal_dms_permit_t150_quotation_revision_issuance()` enforces paired atomic NULL → non-NULL transition.
- Service level rejects already-issued revisions with `ConflictError` (HTTP 409 Conflict).
- Repeated issuance, partial issuance, evidence modification during/after issuance, and revision deletion remain strictly rejected by persistence.

---

## 8. Security & RBAC Matrix Audit

- **Enquiry Reads:** Require `enquiries:read`.
- **Enquiry Writes & Party Linkage:** Require `enquiries:write`.
- **Quotation Reads:** Require `quotations:read`.
- **Quotation Writes & Issuance:** Require `quotations:write`.
- **Acceptance Permission Check:** Callers holding only `quotations:accept` are denied access to all Enquiry and Quotation routes (HTTP 403 Forbidden).

---

## 9. Test Execution & Empirical Evidence

All independent validation commands executed directly against local PostgreSQL instance and verified:

1. **Focused T149 Unit Tests:**
   `uv run pytest tests/unit/test_enquiry_service.py -q`  
   → **3 passed** in 0.15s.

2. **Full Unit Test Suite:**
   `uv run pytest tests/unit -q`  
   → **342 passed**, 60 warnings in 7.80s.

3. **Focused T149 PostgreSQL Integration Suite:**
   `uv run pytest tests/integration/test_t149_enquiry_quotation_routes.py -q -rA`  
   → **2 passed**, 1 warning in 5.38s.

4. **T148/T150 PostgreSQL Integration Suite:**
   `uv run pytest tests/integration/test_t148_enquiry_quotation_postgres.py -q -rA`  
   → **3 passed**, 1 warning in 23.21s.

5. **Operational-Fresh Provenance Integration Suite:**
   `uv run pytest tests/integration/test_operational_fresh_provenance.py -q -rA`  
   → **7 passed**, 1 warning in 17.27s.

6. **Selected Integration Regression Suites:**
   `uv run pytest tests/integration/test_matter_tenant_party_foundation.py -q` → **3 passed**.  
   `uv run pytest tests/integration/test_t141_document_version_storage_foundation.py tests/integration/test_t137_file_document_tenant_foundation.py -q` → **14 passed**.

7. **Code Quality Tools:**
   `uv run ruff check src tests alembic` → **All checks passed!**  
   `uv run black --check src tests alembic` → **321 files left unchanged.**  

8. **Alembic Head Verification:**
   `uv run alembic heads` → **`8d77007b9d7f (head)`**

9. **Governance Validation:**
   `python scripts/governance_validate.py --report` → **OK (0 errors)**. Unresolved Required ADRs: `[12, 15, 16, 17, 20]`.

---

## 10. Control Tower Exact-Head CI Verification

GitHub Action runs verified on frozen candidate `cd678767515a8c9a118f65f8919c77f89c3af5ad`:
- **Backend:** Run `37099618603` — **SUCCESS**
- **Frontend:** Run `37099618600` — **SUCCESS**
- **Governance:** Run `37099618602` — **SUCCESS**
- **Release:** Run `37099618678` — **SUCCESS**

---

## 11. Reviewer Checklist

☑ Architecture preserved  
☑ Existing design patterns followed  
☑ Tests added  
☑ Existing tests pass  
☑ Documentation updated  
☐ ADR updated (if required) — N/A (no ADR change authorized)  
☐ AI_BOOTSTRAP updated (if required) — N/A  
☐ PROJECT_STATE updated (if required) — belongs to Documentation Manager post-QA  
☑ No unrelated refactoring  
☑ No scope creep  
☑ Ready for QA  

---

## 12. Formal QA Decision

- [x] **Approved**
- [ ] Approved with comments
- [ ] Rework required

---

## 13. Next Lifecycle Step

**Control Tower independent QA-verdict/provenance verification.**

*(Note: PR #279 remains unmerged. Independent QA does not merge PRs, perform Documentation Manager synchronization, or authorize T151+.)*
