# T148 Independent Schema Foundation QA Review

**Candidate Reviewed:** `cb609c47afcbbfd968eb43d54ad18cde511961b4`  
**Base Commit:** `b306aaf42dcb865b97a932fb2c422e30b05f71a5` (`main`)  
**Pull Request:** #275 (`feat(preengagement): add T148 schema foundation`)  
**Architecture Authority:** `ADR/0043-enquiry-quotation-acceptance-matter-conversion-architecture.md`  
**Reviewer:** Independent QA Reviewer  
**Date:** 2026-09-30  

---

## 1. Executive Summary & Formal Verdict

- **Formal Verdict:** **Approved**
- **Target Immutable Candidate:** `cb609c47afcbbfd968eb43d54ad18cde511961b4`
- **Scope & Governance:** 8 files (+882 / -2 lines). Zero application routes, REST API CRUD, Acceptance-to-Matter application orchestration, or client/file auto-generation introduced. Preserves unresolved Required ADRs `[12, 15, 16, 17, 20]`.
- **Migration Head:** `e148c0f5a8b2` (Parent: `cdcfd7df5fde`).
- **Operational-Fresh Provenance:** Correctly advanced to `e148c0f5a8b2`.

---

## 2. Baseline & Candidate Verification

- **Protected `main` Baseline:** `b306aaf42dcb865b97a932fb2c422e30b05f71a5`
- **PR #275 State:** OPEN, unmerged, targeting `main` at head `cb609c47afcbbfd968eb43d54ad18cde511961b4`.
- **Governance Frontier Before QA:**
  - `latestTaskDone`: T147
  - `latestTaskAuthorized`: T148
  - `inProgressTransitions`: `[]`
  - `unresolvedRequiredAdrs`: `[12, 15, 16, 17, 20]`
  - Validator: `python scripts/governance_validate.py --report` returns `OK (0 warnings, 0 errors)`.

---

## 3. Schema & Data Integrity Analysis

### 3.1 Enquiry Model
- Primary Key: UUID. Mandatory `organization_id`.
- Optional `party_id` (FK to `parties` with composite `(organization_id, party_id)` same-tenant check).
- Prospect evidence fields: `prospect_display_name`, `prospect_phone`, `prospect_email`, `prospect_description`, `prospect_source`.
- Check constraint `ck_enquiries_party_or_prospect_evidence` enforces that either `party_id IS NOT NULL` or `prospect_display_name IS NOT NULL`.

### 3.2 Quotation Model
- Primary Key: UUID. Mandatory `organization_id`.
- Composite FK `fk_quotations_organization_id_enquiries` enforces parent Enquiry belongs to the same Organization.

### 3.3 QuotationRevision Model
- Primary Key: UUID. Mandatory `organization_id`.
- Check constraint `ck_quotation_revisions_ordinal_positive` (`ordinal > 0`).
- Unique constraint `uq_quotation_revisions_quotation_id_ordinal` enforces revision ordering per Quotation.
- Proposal snapshot stored in JSONB.
- Trigger `quotation_revisions_immutable`: BEFORE UPDATE OR DELETE raises exception, preventing alteration of issued/relied commercial evidence.

### 3.4 Acceptance Model
- Mandatory `organization_id`. Foreign keys enforce same-Organization relationship to Enquiry, Quotation, QuotationRevision, and Matter.
- Database uniqueness constraints enforce:
  - `uq_acceptances_organization_id_enquiry_id`: At most one Acceptance per Enquiry.
  - `uq_acceptances_organization_id_matter_id`: At most one Acceptance per Matter.
  - `uq_acceptances_organization_id_quotation_revision_id`: Exact revision accepted at most once.
  - `uq_acceptances_organization_id_enquiry_id_idempotency_key`: Idempotency key scoped to tenant and Enquiry.
- Trigger `acceptances_require_party`: BEFORE INSERT checks `party_id IS NOT NULL` on target Enquiry, failing closed if acceptance is attempted on a prospect-only Enquiry without canonical Party linkage.
- Trigger `acceptances_immutable`: BEFORE UPDATE OR DELETE raises exception, preserving immutable acceptance evidence.

---

## 4. Multi-Tenancy, RLS & Security

- **Row Level Security (RLS):** All four new tables (`enquiries`, `quotations`, `quotation_revisions`, `acceptances`) explicitly configure `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`.
- **Policy Isolation:** Default-deny policies using `organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid` for SELECT, INSERT, UPDATE, DELETE.
- **RBAC Permissions:** Seeded 5 new permission codes (`enquiries:read`, `enquiries:write`, `quotations:read`, `quotations:write`, `quotations:accept`). Granted cleanly across Administrator, Advocate, Paralegal, Clerk, Accountant, and Read Only roles without misuse of `matters:write`.

---

## 5. Migration & Operational-Fresh Provenance

- **Alembic Revision:** `e148c0f5a8b2` (Parent: `cdcfd7df5fde`).
- **Downgrade Safety:** `downgrade()` verifies whether evidence exists in `enquiries`, `quotations`, `quotation_revisions`, or `acceptances`. If evidence exists, downgrade is refused (`RuntimeError`). If empty, cleans up seeded role permissions, drops RLS policies, drops triggers/functions, and drops tables.
- **Provenance Advancement:** Advanced `legal_dms_provenance.record_fresh_birth` and `enter_operational_fresh` functions to `e148c0f5a8b2`.

---

## 6. Required ADR Boundary Assessment

| Required ADR | State | QA Assessment |
| :--- | :--- | :--- |
| **ADR-0012** (Workflow Engine) | **Preserved** | No generic workflow/government status engine introduced. |
| **ADR-0015** (Configurable Vocabulary) | **Preserved** | No tenant-configurable vocabulary policy decided. |
| **ADR-0016** (Readable Numbering) | **Preserved** | UUID technical identities and integer ordinals used; business-readable numbering left open. |
| **ADR-0017** (Soft Delete / Retention) | **Preserved** | Immutable commercial evidence triggers applied without establishing general deletion/retention policies. |
| **ADR-0020** (Current-Schema Migration) | **Preserved** | No Client/File table retirement or current-schema migration convergence performed. |

---

## 7. Scope Audit

Explicitly verified that the candidate contains **NO**:
- REST/API routes for Enquiry, Quotation, or Acceptance
- Acceptance→Matter application orchestration service
- Client auto-generation or fuzzy Party matching
- File creation or legacy conversion logic
- Financial ledger, Charge, Invoice, or Payment tables
- Frontend components
- Modifications to ADR-0043 or resolution of Required ADRs

---

## 8. Test Execution Results

- **Unit Test Suite:** 339 passed (0 failures)
- **Focused PostgreSQL Integration Test:** 1 passed (`test_t148_new_tables_force_rls_and_isolate_enquiries`)
- **Operational-Fresh Provenance Integration Suite:** 7 passed (0 failures)
- **Ruff Lint & Black Format:** All 314 files checked clean (0 errors)

---

## 9. Next Lifecycle Action

Independent QA review is complete. The next lifecycle step is:

**Control Tower independent verification of QA provenance/verdict.**

*Note: PR #275 must remain unmerged pending Control Tower verification. QA does not perform post-QA governance synchronization or authorize T149+.*
