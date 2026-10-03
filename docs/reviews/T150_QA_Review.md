# T150 Independent QA Review — QuotationRevision One-Time Issuance Persistence Correction

**Frozen Candidate Reviewed:** `c7f1a4aa05abe950445444559528d9c0fd4068bc`  
**Protected Base Commit:** `27f0f1289995ee86d56695fcf6ab176e3a9f2f93` (`main`)  
**Pull Request:** #278 (`https://github.com/Intelligentclown/Legal_DMS/pull/278`)  
**Branch:** `feature/t150-quotation-revision-issuance-persistence`  
**Reviewer:** Independent QA Reviewer  
**Date:** 2026-10-03  

---

## 1. Executive Summary & Formal Verdict

- **Formal Verdict:** **Approved**
- **Exact Candidate SHA Evaluated:** `c7f1a4aa05abe950445444559528d9c0fd4068bc`
- **Scope & Governance:** 5 changed files (+471 / -3 lines). Zero application routes, REST API endpoints, T149 pre-engagement service orchestration, Acceptance-to-Matter conversions, or frontend changes introduced. Unresolved Required ADRs remain `[12, 15, 16, 17, 20]`. ADR-0043 remains unchanged.
- **Alembic Revision:** `8d77007b9d7f` (Parent: `e148c0f5a8b2`).
- **Operational-Fresh Provenance Frontier:** Advanced to `8d77007b9d7f`.

---

## 2. Baseline & Candidate Verification

- **Protected Base SHA (`main`):** `27f0f1289995ee86d56695fcf6ab176e3a9f2f93`
- **Frozen Implementation SHA:** `c7f1a4aa05abe950445444559528d9c0fd4068bc`
- **PR #278 Verification:** OPEN, unmerged, non-draft, mergeable against `main` (2 commits ahead, 0 behind).
- **Governance Ledger Baseline:**
  - `latestTaskDone`: T148
  - `latestTaskAuthorized`: T150
  - `inProgressTransitions`: `[]`
  - `unresolvedRequiredAdrs`: `[12, 15, 16, 17, 20]`
  - Validator: `python scripts/governance_validate.py --report` returns `OK (0 errors)`.

---

## 3. Scope & Diff Audit

Changed files (exactly 5 files):
1. `backend/alembic/versions/8d77007b9d7f_permit_quotation_revision_issuance.py` (+72 lines)
2. `backend/src/app/infrastructure/cli/fresh_install_provenance.py` (+1 / -1 lines)
3. `backend/tests/integration/test_operational_fresh_provenance.py` (+1 / -1 lines)
4. `backend/tests/integration/test_t148_enquiry_quotation_postgres.py` (+288 / -1 lines)
5. `docs/ImplementationLog/Stage3/Phase37.md` (+109 lines)

Total stats: 5 changed files, 471 additions, 3 deletions.

Audit confirmed: NO T149 application code, NO routes, NO services, NO Acceptance-to-Matter conversion, NO Party/Client manufacture, NO frontend changes, NO ADR modifications, NO status enum additions.

---

## 4. Persistence Invariant & Trigger Analysis

### 4.1 Permitted Transition
- OLD state: `issued_at IS NULL AND issued_by IS NULL`
- NEW state: `issued_at IS NOT NULL AND issued_by IS NOT NULL`
- Enforced atomically in a single `UPDATE` statement.

### 4.2 Immutable Evidence Protection
Non-issuance columns are extracted and compared using JSONB subtraction:
```sql
(to_jsonb(NEW) - ARRAY['issued_at', 'issued_by']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['issued_at', 'issued_by'])
```
This guarantees that `id`, `organization_id`, `quotation_id`, `ordinal`, `proposal_snapshot`, `created_at`, `created_by`, and any future schema columns cannot be mutated during issuance or at any other time.

### 4.3 Required Rejection Matrix Verification
Independently verified that the trigger rejects all 20 specified unauthorized mutations:
1. `issued_at` becoming non-NULL while `issued_by` remains NULL — **REJECTED**
2. `issued_by` becoming non-NULL while `issued_at` remains NULL — **REJECTED**
3. Partial issuance — **REJECTED**
4. Substantive/evidence mutation during issuance — **REJECTED**
5. `proposal_snapshot` mutation before issuance — **REJECTED**
6. `proposal_snapshot` mutation during issuance — **REJECTED**
7. `proposal_snapshot` mutation after issuance — **REJECTED**
8. Arbitrary pre-issuance UPDATE — **REJECTED**
9. Second issuance — **REJECTED**
10. Changing issued timestamp after issuance — **REJECTED**
11. Changing issued actor after issuance — **REJECTED**
12. Clearing `issued_at` — **REJECTED**
13. Clearing `issued_by` — **REJECTED**
14. Issued → unissued reversal — **REJECTED**
15. Parent `quotation_id` mutation — **REJECTED**
16. `ordinal` mutation — **REJECTED**
17. `organization_id` mutation — **REJECTED**
18. Provenance/creator mutation — **REJECTED**
19. QuotationRevision DELETE before issuance — **REJECTED**
20. QuotationRevision DELETE after issuance — **REJECTED**

---

## 5. Acceptance Integrity

- The original `acceptances_immutable` trigger on the `acceptances` table remains completely untouched and continues to execute `legal_dms_prevent_t148_evidence_mutation()`.
- Independent integration tests confirm that `UPDATE acceptances` and `DELETE FROM acceptances` remain strictly rejected with `'T148 quotation/acceptance evidence is immutable'`.

---

## 6. Migration & Downgrade Semantics

- **Revision ID:** `8d77007b9d7f` (Parent: `e148c0f5a8b2`).
- **Alembic Heads:** `uv run alembic heads` yields sole head `8d77007b9d7f`.
- **Populated Upgrade:** Verified upgrade from populated `e148c0f5a8b2` target.
- **Downgrade:** `downgrade()` drops `quotation_revisions_immutable`, drops function `legal_dms_permit_t150_quotation_revision_issuance()`, re-attaches `quotation_revisions_immutable` executing `legal_dms_prevent_t148_evidence_mutation()`, and rewinds operational-fresh provenance guard to `e148c0f5a8b2`. Data legitimately issued under T150 is structurally identical to T148 schema and remains immutable under T148 trigger rules.
- **Empty Downgrade:** Cleanly tested and verified.

---

## 7. Operational-Fresh Provenance

- Frontier advanced from `e148c0f5a8b2` to `8d77007b9d7f`.
- `fresh_install_provenance.py` updated to `8d77007b9d7f`.
- All 7 integration tests in `test_operational_fresh_provenance.py` passed cleanly.

---

## 8. Tenant & RLS Security

- All 4 pre-engagement tables (`enquiries`, `quotations`, `quotation_revisions`, `acceptances`) remain configured with `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
- `organization_id` cannot be mutated by issuance or trigger operations.
- Default-deny RLS policies and tenant isolation intact.

---

## 9. Test Execution & Empirical Evidence

All independent validation commands executed directly against local PostgreSQL instance and verified:

1. **Unit Test Suite:**
   `uv run pytest tests/unit -q`  
   → **339 passed**, 60 warnings in 6.25s.

2. **PostgreSQL Migration & RLS Integration Suite:**
   `uv run pytest tests/integration/test_t148_enquiry_quotation_postgres.py -q -rA`  
   → **3 passed**, 1 warning in 23.21s.

3. **Operational-Fresh Provenance Integration Suite:**
   `uv run pytest tests/integration/test_operational_fresh_provenance.py -q -rA`  
   → **7 passed**, 1 warning in 17.27s.

4. **Code Quality Tools:**
   `uv run ruff check src tests alembic` → **All checks passed!**  
   `uv run black --check src tests alembic` → **315 files left unchanged.**  

5. **Alembic Head Verification:**
   `uv run alembic heads` → **8d77007b9d7f (head)**

6. **Governance Validation:**
   `python scripts/governance_validate.py --report` → **OK (0 errors)**. Unresolved Required ADRs: `[12, 15, 16, 17, 20]`.

---

## 10. Control Tower Exact-Head CI Verification

GitHub Action runs verified on frozen candidate `c7f1a4aa05abe950445444559528d9c0fd4068bc`:
- **Backend:** Run `36996300574` — **SUCCESS**
- **Frontend:** Run `36996300586` — **SUCCESS**
- **Governance:** Run `36996300571` — **SUCCESS**
- **Release:** Run `36996300619` — **SUCCESS**

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

*(Note: PR #278 remains unmerged. Independent QA does not merge PRs, perform Documentation Manager synchronization, or authorize T149+.)*
