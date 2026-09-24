# T136 QA Review

**Task:** T136 — File/Document Transition and Current-Schema Migration Architecture  
**Role:** Independent QA Reviewer  
**PR:** #244 — `T136: File/Document transition and migration architecture`  
**Authorization Baseline:** `09229cef3a4e31300edf31a904aa7a443fe80f4b` (PR #243 T136 authorization merged)  
**Exact Architecture SHA Reviewed:** `c89a8ea6d7be72088fcd8d39188513077a779312`  

---

## 1. Remote Repository State & Ancestry Verification

- **Authorization Baseline:** `09229cef3a4e31300edf31a904aa7a443fe80f4b` confirmed as exact merged authorization base.
- **PR State:** PR #244 is OPEN, non-draft, unmerged, targeting `main`.
- **Ancestry:** Architecture commit `c89a8ea6d7be72088fcd8d39188513077a779312` directly descends from baseline `09229cef3a4e31300edf31a904aa7a443fe80f4b`.
- **Changed Files:** Exactly 2 documentation files:
  1. `ADR/0040-file-document-transition-current-schema-migration.md`
  2. `docs/reviews/T136_Software_Architect_Report.md`
- **Scope Integrity:** Diff is +477 additions, 0 deletions. Pure architecture/documentation only. No production code, tests, schema models, or Alembic migrations were modified.
- **GitHub CI State:** All 5 check runs on exact head `c89a8ea6d7be72088fcd8d39188513077a779312` completed successfully (`success`).
- **Governance State:** `latestTaskDone = T135`, `latestTaskAuthorized = T136`, `inProgressTransitions = []`. Alembic frontier remains `9e6a4b2c8d1f`.

---

## 2. Independent Model & Repository Inspection

- **Current Repository State Inspected:**
  - `Document` model currently has mandatory `matter_id`, mandatory `document_type_id`, `title`, and `status`. It carries **no** `file_id` and **no** direct `organization_id`.
  - `DocumentVersion` model belongs to `Document` (`document_id`, `version_number`) and references `file_storage_record_id`.
  - `FileStorageRecord` model is physical blob/storage metadata (`file_storage_records` table).
  - Code search confirms no business `File` or `files` aggregate exists in the codebase. Physical storage records are distinct from the legal business File aggregate.

---

## 3. Architectural Assessments

### A. Target Aggregate Model & Cardinality
- **Approved.** Target state `Organization 1 ── 0..N Matter 1 ── 0..N File 1 ── 0..N Document 1 ── 0..N DocumentVersion ── 1 FileStorageRecord` accurately models the domain. Each File belongs to one Matter; each target-state Document belongs to one File only. `DocumentVersion` remains Document-owned; `FileStorageRecord` remains storage metadata.

### B. No-Synthetic-File Strategy
- **Approved.** Rejecting automatic/default compatibility Files per Matter prevents asserting historical work-package grouping that does not exist in current data. Existing Documents remain explicitly legacy-unfiled (`file_id = NULL`, `matter_id != NULL`) until an operator assigns them to a genuine File.

### C. No Heuristic Migration
- **Approved.** Architecture strictly forbids inferring File membership from titles, filenames, document types, upload order, or storage paths. Operator-driven resolution is correctly required for legacy Documents.

### D. Direct Document Organization Ownership
- **Approved.** `documents.organization_id NOT NULL → organizations.id` is justified because legacy unfiled Documents have `file_id = NULL`. Direct Organization ownership ensures uniform, simple, fail-closed PostgreSQL RLS without multi-path policy complexity. Backfill is 100% deterministic from `documents.matter_id → matters.organization_id`.

### E. Composite Consistency Enforcement
- **Approved.** Composite FK from Document `(organization_id, matter_id, file_id)` to candidate key on File `(organization_id, matter_id, id)` is database-enforceable in PostgreSQL when `file_id` is present, guaranteeing same-Matter and same-Organization alignment without application-level guesswork.

### F. Dual-Column Compatibility & Write Authority
- **Approved.** For operational-fresh and new business, `file_id` is canonical and `matter_id` is a derived compatibility shadow. Caller-supplied matter disagreement is rejected. Legacy unfiled Documents preserve `matter_id` for historical Matter evidence. No ambiguous dual-authority paths exist.

### G. File Numbering & ADR-0027 Integration
- **Approved.** Operates strictly via ADR-0027's Matter-scoped atomic counter table (`file_number_sequences`). Allocation and File insertion occur in a single transaction. Automatic migration creates no File and consumes no number.

### H. ADR-0030 Compatibility
- **Approved.** Preserves Matter as root (`Matter 1 ── 0..N File`), File existence dependency on Matter, and File's distinct identity as a work package.

### I. Tenant Isolation, RLS & Security
- **Approved.** Direct `organization_id` on `files` and `documents`, FORCE RLS enabled, default-deny GUC policies, and runtime role `legal_dms_app` (`NOBYPASSRLS`) enforce strict tenant boundaries.

### J. Downgrade & Refusal Boundaries
- **Approved.** Schema downgrade must refuse once any genuine File exists or any Document assignment is recorded, preventing lossy collapse of multiple Files into Matter-only linkage.

### K. Retirement Gate for `documents.matter_id`
- **Approved.** 11-point evidence gate strictly governs the future removal of `documents.matter_id`, requiring 100% File assignment, consumer migration, and independent QA evidence.

---

## 4. Required ADR Conclusions

### Required ADR #10
- **Conclusion: #10 Fully Resolved by ADR-0040.**
- **Reasoning:** ADR-0040 answers all required questions regarding the Document/File relationship, coexistence, authority, allowed states, migration mechanics, tenant scoping, downgrade refusal, and retirement gate. Resolution is proposed subject to independent QA approval and §3.1 governance closeout.

### Required ADR #20
- **Conclusion: Globally Unresolved.**
- **Reasoning:** ADR-0040 settles only the File/Document seam. Remaining current-schema migration seams (Matter `property_id`, `matter_type_id`, MatterProperty, classification/work-type, remaining Client consumers, ClientContact, Appointment, Invoice, Payment, and final Client retirement) remain unresolved.

---

## 5. Formal QA Verdict

**Formal Verdict: Approved**

- The architecture is internally coherent, technically sound, fully compliant with governing ADRs (ADR-0021, ADR-0027, ADR-0030, ADR-0037, ADR-0039), and strictly bounded within authorized T136 scope.

---

## 6. Post-QA Directions

- PR #244 remains open and unmerged.
- T136 remains Authorized / not Done.
- Control Tower may proceed with post-QA governance synchronization, merging PR #244, marking T136 Done, resolving Required ADR #10 in governance ledgers, and authorizing successor tasks.
