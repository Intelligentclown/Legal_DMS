------------------------------------------------

# Stage 3 – Phase 34

Status: Approved (Independent QA)

Started: 2026-09-25

Completed: 2026-09-25

Related Tasks: T141

Related ADRs: ADR-0020, ADR-0021, ADR-0037, ADR-0040, ADR-0041

Git Commit: 3e96d41fd5d2953f872ea4748f68d1845d9dbe2c (Immutable Implementation Candidate)

Pull Request: #257

Release:

------------------------------------------------

## Objective

Implement the bounded T141 database, SQLAlchemy, RLS, idempotency, and provenance foundation for a later DocumentVersion/storage application slice, without adding that application slice.

## Tasks Implemented

- Added direct DocumentVersion Organization identity, staged nullable FileStorageRecord Organization identity, tenant-aware composite integrity, and exclusive canonical storage ownership.
- Added persisted DocumentVersion idempotency evidence scoped by Organization, Document, and idempotency key.
- Added the single direct Alembic child `cdcfd7df5fde` of `be439c0d6fdb`, including authoritative backfill, shared-consumer rejection, forced RLS, guarded downgrade, and operational-fresh revision synchronization.

## Files Modified

- `backend/alembic/versions/cdcfd7df5fde_document_version_storage_tenant_.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/src/app/infrastructure/persistence/models/document.py`
- `backend/src/app/infrastructure/persistence/models/storage.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
- `backend/tests/integration/test_t141_document_version_storage_foundation.py`
- `docs/ImplementationLog/Stage3/Phase34.md`

## Tests Added

- Disposable PostgreSQL migration coverage for canonical DocumentVersion storage backfill, Template/QR/Receipt preservation, and shared-consumer rejection.
- PostgreSQL RLS, tenant-integrity, canonical-storage exclusivity, idempotency uniqueness, fresh-install, and guarded-downgrade coverage.
- Current-head Document and OCR/QR model fixtures now establish transaction-scoped Organization context and derive canonical Version/Storage tenant identity from their legitimate Organization graph.

## Test Results

- Final dedicated disposable-PostgreSQL T141 suite: **10 passed** (65.70s). It covers clean full-chain installation, parent-to-head upgrade/backfill, Template/QR/Receipt preservation, shared-consumer rejection, FORCE RLS and no/wrong/correct-GUC behavior, tenant/exclusivity/idempotency integrity, operational-fresh revision advancement, and representable/refused downgrade behavior.
- Explicit final disposable cases for clean installation, parent-to-T141 upgrade, and guarded downgrade: **3 passed**.
- The modernized `test_document_models.py` and `test_ocr_qr_backup_models.py` pass together against an isolated T141-head database: **11 passed** (1.20s). The fixture modernization uses Organization-derived identity and transaction-scoped GUC context only; it does not relax production RLS or FORCE RLS.
- Final full unit suite: **330 passed** (4.77s).
- Ruff passed; Black passed (269 files unchanged); `py_compile` passed; the required Backend CI boot-smoke command passed (`Booted OK: Legal Document & Matter Management System 0.2.0`); Alembic reported the sole head `cdcfd7df5fde`; governance validation and `git diff --check` passed.
- Full PostgreSQL integration differential is settled: baseline `cd814972f94eff7c5204385d690442481d210513` at `be439c0d6fdb` was **424 passed, 56 failed, 21 skipped**; T141 at `cdcfd7df5fde` was **434 passed, 56 failed, 21 skipped**. Mechanical result: COMMON 56, BASELINE_ONLY 0, T141_ONLY 0, materially different COMMON 0. The 56 failures are baseline-equivalent legacy integration-harness debt. PostgreSQL integration is explicitly excluded from required Backend CI; this is not a claim that the full suite passes.

## Design Decisions

- FileStorageRecord Organization ownership is assigned only for an unambiguous DocumentVersion-owned row through `DocumentVersion → Document → Organization`; all non-version storage remains staged with NULL tenant identity.
- Template, QRCodeRecord, Receipt, and multiple-DocumentVersion sharing fail closed rather than receiving guessed or destructive treatment.
- The downgrade refuses when post-T141 tenant, version, storage, or idempotency evidence cannot be represented by the parent schema.

## Problems Encountered

- Parent-schema fixtures initially omitted required `storage_provider` and Receipt's parent-required Payment `status`; fixtures were repaired without altering production schema semantics.
- Generated migration formatting was corrected. A PostgreSQL identifier-length failure for an idempotency FK was fixed with concise, matching model/migration constraint names.

## Deferred Work

- DocumentVersion repository/service/API, version allocation, upload/download, physical storage orchestration, checksum workflow, retention, and legacy Document-to-File resolution remain explicitly excluded pending separate authority.

## Future Considerations

- Independent QA has inspected the immutable implementation commit, executed the real-PostgreSQL matrix independently, and recorded the formal QA decision before Documentation Manager synchronization or merge.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing required tests pass — dedicated PostgreSQL suite, focused current-head modules, unit suite, and CI boot smoke pass. The full PostgreSQL suite remains 434 passed / 56 baseline-equivalent failures / 21 skipped; it is not a required Backend CI gate.
☑ Documentation updated
□ ADR updated (if required) — no ADR change is authorized.
□ AI_BOOTSTRAP updated (if required) — no standing process changed.
□ PROJECT_STATE updated (if required) — T141 is not Done; post-QA synchronization belongs to the Documentation Manager.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA — frozen implementation candidate reviewed by Independent QA Reviewer.

## Independent QA Evidence & Findings

- **Immutable Implementation Candidate Reviewed:** `3e96d41fd5d2953f872ea4748f68d1845d9dbe2c`
- **Authorized Baseline:** `cd814972f94eff7c5204385d690442481d210513` (`origin/main`)
- **Ancestry Verification:** Implementation commit `3e96d41fd5d2953f872ea4748f68d1845d9dbe2c` directly descends from baseline `cd814972f94eff7c5204385d690442481d210513`. T140 is latest Done, T141 is Authorized/inProgress, T142+ is unauthorized.
- **Migration Topology:** Single direct child `be439c0d6fdb -> cdcfd7df5fde`. `cdcfd7df5fde` is sole Alembic head.
- **Changed Files (9):**
  - `backend/alembic/versions/cdcfd7df5fde_document_version_storage_tenant_.py`
  - `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
  - `backend/src/app/infrastructure/persistence/models/document.py`
  - `backend/src/app/infrastructure/persistence/models/storage.py`
  - `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
  - `backend/tests/integration/test_document_models.py`
  - `backend/tests/integration/test_ocr_qr_backup_models.py`
  - `backend/tests/integration/test_t141_document_version_storage_foundation.py`
  - `docs/ImplementationLog/Stage3/Phase34.md`
- **Independent Test Verification:**
  - `test_t141_document_version_storage_foundation.py`: 10/10 passed against disposable PostgreSQL.
  - `test_document_models.py` & `test_ocr_qr_backup_models.py`: 11/11 passed against PostgreSQL.
  - Full unit test suite (`pytest backend/tests/unit/`): 330/330 passed.
  - Alembic fresh install (`upgrade head` from empty DB to `cdcfd7df5fde`): Passed.
  - Alembic parent upgrade (`be439c0d6fdb -> cdcfd7df5fde`): Passed.
  - PostgreSQL RLS Matrix: Default-deny (no GUC) -> 0 rows, Wrong GUC -> 0 rows, Correct GUC -> expected rows. Tested on `document_versions`, `file_storage_records`, and `document_version_idempotency_keys`.
  - Guarded Downgrade: Refuses downgrade when tenant-owned evidence exists; succeeds on empty foundation state.
- **Static Validation Verification:**
  - Ruff check: Passed (0 errors).
  - Black check: Passed (269 files unchanged).
  - Python py_compile: Passed.
  - Alembic heads: `cdcfd7df5fde` (sole head preserved).
  - `git diff --check`: Passed.
  - `governance_validate.py`: Passed (OK, 0 warnings, 0 errors).
- **GitHub CI Verification:** PR #257 exact implementation SHA `3e96d41fd5d2953f872ea4748f68d1845d9dbe2c` passed all 4 required CI workflows (Backend, Frontend, Governance, Release).

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required
