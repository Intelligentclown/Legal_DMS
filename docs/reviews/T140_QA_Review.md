# T140 Architecture QA Review

**Task:** T140 — Document Versioning and Storage Transaction Architecture  
**Role:** Independent QA Reviewer  
**Architecture PR:** [#254 — `docs(adr): define T140 document versioning and storage transaction architecture`](https://github.com/Intelligentclown/Legal_DMS/pull/254)  
**PR Branch:** `architecture/t140-document-version-storage`  
**Authorization Baseline:** `0f0d5aea73ea5d2313c6599e59f4128a34b484c9` (`origin/main`)  
**Exact Architecture Commit Reviewed:** `17f01b57162a17745483e423987d5c0bf9960eca`  
**PR Head Before QA Document:** `afa7ccab303efe4207ed27eb7804414834d5e275`  

---

## 1. Remote Repository State & Ancestry Verification

- **Authorization Baseline:** `0f0d5aea73ea5d2313c6599e59f4128a34b484c9` confirmed as exact merged T140 authorization base on `origin/main`.
- **PR State:** PR #254 is OPEN, non-draft, unmerged, targeting `main`.
- **Ancestry:** Architecture commit `17f01b57162a17745483e423987d5c0bf9960eca` and transition commit `afa7ccab303efe4207ed27eb7804414834d5e275` descend directly from baseline `0f0d5aea73ea5d2313c6599e59f4128a34b484c9`.
- **Changed Files:** Exactly 2 documentation/governance files:
  1. `ADR/0041-document-versioning-storage-transaction-architecture.md`
  2. `PROJECT_STATE.json`
- **Scope Integrity:** Diff is pure architecture/documentation. No production code, tests, schema models, or Alembic migrations were created or modified.
- **GitHub CI State:** Control Tower and live GitHub status confirm all check runs on head `afa7ccab303efe4207ed27eb7804414834d5e275` completed successfully (`success`).
- **Governance State:** `latestTaskDone = T139`, `latestTaskAuthorized = T140`, `inProgressTransitions = [{"task": "T140", "requiredAdrs": [11]}]`. Alembic frontier remains `be439c0d6fdb`. Unresolved Required ADRs remain `[11, 12, 15, 16, 17, 20]`.

---

## 2. Independent Model & Repository Fact Inspection

Independent verification against actual repository code, models, and interfaces confirms:
- **`Document` model (`backend/src/app/infrastructure/persistence/models/document.py`):** Has `id`, `organization_id`, `matter_id`, `file_id`, `document_type_id`, `title`, `status`, `AuditMixin`, `OptimisticLockMixin`. Deliberately carries no denormalized `current_version_id` pointer.
- **`DocumentVersion` model (`document.py`):** Has `id`, `document_id`, `version_number`, `file_storage_record_id`, `change_summary`, `created_at`, `created_by`. Unique constraint `(document_id, version_number)` exists. Currently lacks direct `organization_id`.
- **`FileStorageRecord` model (`backend/src/app/infrastructure/persistence/models/storage.py`):** Stores `storage_provider`, `file_path`, `original_filename`, `mime_type`, `size_bytes`, `checksum_sha256`, generic `version`, `retention_policy`, `uploaded_by`, `uploaded_at`, `deleted_at`. Shared across `DocumentVersion`, `DocumentTemplate`, and `QrCodeRecord`. Currently lacks direct `organization_id`.
- **`FileStorage` port (`backend/src/app/application/interfaces/file_storage.py`) & `LocalFileStorage` (`backend/src/app/infrastructure/storage/local_file_storage.py`):** Exposes `save`, `read`, `delete`, `exists`. Resolves relative paths under `settings.storage_root` with root escape containment checks.
- **Transaction & Tenant Conventions:** ADR-0020 request-scoped session transaction policy, ADR-0021 FORCE RLS / Organization GUC tenant isolation, T139 `documents:read` / `documents:write` RBAC boundaries confirmed.

---

## 3. Detailed Architectural Assessments

### A. Lifecycle & Scope Correctness
- **Approved.** T140 is strictly an architecture-only §3.1 task. ADR-0041 is correctly `Proposed`. Its proposed resolution of Required ADR #11 is conditional on independent QA approval and §3.1 closeout. No premature settlement of Required ADR #11 or #17 has occurred.

### B. Governing ADR Compatibility
- **Approved.** ADR-0041 composes cleanly with ADR-0020 (session transaction boundaries), ADR-0021 (tenant RLS), ADR-0022 (authorization), ADR-0027 (File numbering), ADR-0030 (Matter/File identity), ADR-0037 (provenance), ADR-0038 (Self-Context), and ADR-0040 (File/Document transition).

### C. Concurrency and Version Allocation
- **Approved.** Version allocation serializes on the canonical `Document` row using PostgreSQL `SELECT ... FOR UPDATE` inside the request SQL transaction after tenant/File/Document validation.
- `next_version = COALESCE(MAX(committed version_number for document), 0) + 1`.
- Unique constraint `(document_id, version_number)` acts as integrity backstop.
- Physical blob save occurs **before** acquiring the DB row lock, preventing slow external I/O from blocking the database critical section.
- Serialization on the Document row lock is concurrency-safe under the repository's transaction model. The choice not to reuse ADR-0027's `file_number_sequences` counter table is explicitly and correctly justified: version numbers are internal Document-scoped sequence ordinals, whereas File numbers are business work-package identifiers.

### D. Latest-Version Semantics
- **Approved.** Latest version is query-derived by `MAX(version_number)` among committed `DocumentVersion` rows visible to the caller's tenant. No `current_version_id` pointer is added to `Document`, avoiding circular foreign keys and stale denormalized pointers.

### E. Blob-First / Database-Second Transaction & Compensation Model
- **Approved.** Blobs are written to storage first, followed by single-transaction DB insert of `FileStorageRecord` and `DocumentVersion`.
- On database validation/alloc/flush/commit failure, the application orchestration layer catches the failure and performs compensating `FileStorage.delete(key)`.
- If an uncommitted orphan blob remains due to process crash, it is non-authoritative (DB is authoritative for committed versions) and reconcilable.
- The explicit STOP condition in ADR-0041 §6 ("Implementation must structure commit/compensation so ADR-0020 remains database transaction authority...") is sound and protects transaction boundary integrity.

### F. Deterministic Storage Key & Namespace
- **Approved.** Key format: `organizations/{organization_uuid}/document-versions/{document_version_uuid}/content`.
- Opaque, technical, provider-relative key generated from server UUIDs.
- Contains no business labels (no titles, File numbers, client names, dates), preventing path traversal and mutation bugs.

### G. Retry and Idempotency Architecture
- **Approved.** Requests require server-scoped idempotency token `(organization_id, document_id, idempotency_key)` persisted transactionally with the `DocumentVersion`.
- Includes content SHA-256 payload fingerprint.
- Idempotent retry after lost network response returns the committed `DocumentVersion` without duplicating blob or version record.

### H. Tenant Ownership, Integrity & Shared FileStorageRecord Handling
- **Approved.** Direct `organization_id NOT NULL` added to `DocumentVersion` and DocumentVersion-owned `FileStorageRecord`, backed by FORCE RLS and composite same-tenant FKs.
- Shared `FileStorageRecord` handling: Pre-existing records used by `DocumentTemplate` or `QrCodeRecord` must not have tenant ownership fabricated; if unassignable, implementation uses an additive staged/nullable column and fails closed on tenant application visibility.

### I. Checksum and Integrity Policy
- **Approved.** SHA-256 mandatory on version creation.
- On download/read, content returned by `FileStorage` is verified against stored SHA-256 and byte length before releasing to client. Checksum mismatch fails closed (HTTP 500 integrity error).

### J. Authorization & Legacy Boundary
- **Approved.** Reuses existing `documents:read` for list/metadata/download and `documents:write` for version creation. File/Matter permissions do not substitute.
- Legacy unfiled Documents (`file_id = NULL`) are ineligible for new version creation/download through canonical routes until explicitly filed via ADR-0040 operator resolution.

### K. Required ADR #17 Boundary
- **Approved.** Preserved. ADR-0041 defines normal immutable create/read/download and failure compensation for uncommitted orphan blobs. It does not resolve soft deletion, archival, retention, or legal hold for committed versions.

### L. Implementation Decomposition
- **Approved.** Recommends two sequential dependency-safe slices:
  1. *Slice 1:* Version/storage tenant + integrity schema foundation.
  2. *Slice 2:* Canonical DocumentVersion application + storage orchestration.

---

## 4. Static & Governance Validation Results

- **Governance Validator (`python scripts/governance_validate.py`):** `OK (0 warning(s), 0 errors)`.
- **Ruff Check (`ruff check backend`):** Passed (0 errors).
- **Black Check (`black --check backend/src backend/tests`):** Passed (268 files unchanged).
- **Git Diff Check (`git diff --check origin/main..HEAD`):** Passed (no whitespace errors).
- **GitHub Actions CI:** All check runs on PR #254 exact head completed successfully (`success`).

---

## 5. Required ADR Disposition

- **Required ADR #11 — Document/version architecture:**  
  **Proposed for Resolution by ADR-0041.** Settlement is conditional on independent QA approval and §3.1 governance closeout.
- **Required ADR #12, #15, #16, #17, #20:**  
  **Remain globally UNRESOLVED.**

---

## 6. Formal Verdict & Post-QA Directions

**Formal Verdict: `Approved`**

- PR #254 remains open and unmerged.
- T140 remains Authorized / not Done.
- T141+ remains unauthorized.
- Hand back to Control Tower / Documentation Manager for T140 post-QA governance synchronization under `PROJECT_WORKFLOW.md §3.1`.
