------------------------------------------------

# Stage 3 – Phase 31

Status: Approved by independent QA

Started: 2026-09-24

Completed: 2026-09-24

Related Tasks: T137

Related ADRs: ADR-0027, ADR-0030, ADR-0037, ADR-0040

Git Commit: 42baef57ae5f305d84fbe4bcf28d83bd935d3f2f

Pull Request: #247

Release:

------------------------------------------------

## Objective

Implement only T137's additive File/Document tenant and compatibility schema foundation.

## Tasks Implemented

- Added audited business `files` persistence and Matter-scoped `file_number_sequences` persistence.
- Added direct Document Organization ownership, nullable `file_id`, deterministic Matter-only Organization backfill, composite tenant/Matter FKs, forced Organization-GUC RLS, and lossless downgrade refusal.
- Advanced the operational-fresh revision guard to `b8c4d2e1f7a9`.
- Added no File/Document service, repository, route, CRUD, or runtime number allocation.

## Files Modified

- `backend/alembic/versions/b8c4d2e1f7a9_file_document_tenant_foundation.py`
- `backend/src/app/infrastructure/persistence/models/file.py`
- `backend/src/app/infrastructure/persistence/models/document.py`
- `backend/src/app/infrastructure/persistence/models/__init__.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/tests/integration/test_t137_file_document_tenant_foundation.py`
- Existing Document/provenance test fixtures updated for the new schema head.

## Tests Added

- `test_t137_file_document_tenant_foundation.py` covers parent-head upgrade/backfill/no synthesis, composite integrity, safe and refused downgrades, and File/Document forced RLS/default denial.

## Test Results

- Focused disposable PostgreSQL T137 suite: 4 passed.
- Ruff: clean for changed backend files.
- Black: clean for changed backend files.
- `git diff --check`: clean.
- Full backend suite was not run because the retained shared development database is still at the parent migration head; the T137 tests use disposable databases and do not mutate it.

## Design Decisions

- The Document-to-File constraint is the ADR-0040 composite FK `(organization_id, matter_id, file_id) → files(organization_id, matter_id, id)`; nullable `file_id` preserves explicit legacy-unfiled Documents.
- Any File, assignment, or sequence row makes downgrade fail closed because the parent schema cannot preserve that business meaning or number history.

## Problems Encountered

- The restricted workspace could not initialize uv's external cache; checks were re-run through the approved environment. Disposable migration tests passed.

## Deferred Work

- The later authorized File application slice owns atomic counter allocation and File CRUD.
- The later Document application slice owns File-canonical writes and legacy-resolution tooling.

## Future Considerations

- Independent QA must review the exact remote implementation head and re-run migration/RLS/provenance checks before any documentation synchronization or merge.

## Independent QA Verification

- **QA Role:** Independent QA Reviewer / Antigravity
- **Formal Verdict:** Approved
- **Exact Implementation Commit Reviewed:** `42baef57ae5f305d84fbe4bcf28d83bd935d3f2f`
- **QA Evidence Log Update Target:** `Phase31.md`

### Architectural Acceptance & Schema Invariants
- **Schema Foundation:** Migration `b8c4d2e1f7a9` creates `files` table (audited business files with Organization, Matter, Matter-scoped `file_number`, title, tenant composite keys/FKs, and forced GUC RLS) and `file_number_sequences` table (Matter-scoped, tenant-safe sequence persistence foundation).
- **No File CRUD / Allocation:** No runtime File CRUD or sequence allocation was introduced; reserved for later slices.
- **Direct Document Tenant Ownership:** `documents.organization_id NOT NULL` is added and deterministically backfilled from `documents.matter_id → matters.organization_id`. Backfill failure raises `RuntimeError` if missing or contradictory.
- **Explicit Legacy Unfiled State:** `documents.file_id` is nullable. Existing Documents remain `file_id = NULL`. Zero synthetic Files are created; zero File numbers consumed.
- **Database Integrity & Composite FKs:** Composite FK `(organization_id, matter_id, file_id) → files(organization_id, matter_id, id)` and `(organization_id, matter_id) → matters(organization_id, id)` enforce same-Organization and same-Matter consistency in PostgreSQL.
- **Tenant Isolation & Forced RLS:** ENABLE and FORCE RLS installed on `files`, `file_number_sequences`, and `documents` with `organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid` policies. RLS flags (`relrowsecurity`, `relforcerowsecurity`) verified `True` for `files` and `documents`. Default-deny (no GUC) and correct-Org GUC isolation verified in disposable PostgreSQL tests.
- **Provenance Revision Guard:** Operational-fresh provenance functions advanced from `9e6a4b2c8d1f` to `b8c4d2e1f7a9`.
- **Lossless Downgrade Refusal:** Migration downgrade checks if `files`, `file_number_sequences`, or `documents WHERE file_id IS NOT NULL` contain rows. Raises `RuntimeError` refusing lossy downgrade if data exists; succeeds cleanly on empty foundation.
- **Boundary Audits:**
  - `PartyWriteGate` is unchanged.
  - `documents.matter_id` remains mandatory.
  - No File/Document application routes, services, repositories, CRUD, or storage/OCR redesign added.
  - Unresolved Required ADRs remain `[11, 12, 15, 16, 17, 20]`.

### Independent Test & Quality Evidence
- **Focused disposable PostgreSQL suite:** 4 passed (`test_t137_file_document_tenant_foundation.py`).
- **Ruff:** All checks passed clean.
- **Black:** Clean (`257 files left unchanged`).
- **Governance Validator:** `python scripts/governance_validate.py` returned `OK (0 warning(s), 0 errors)`.
- **`git diff --check`:** Clean (0 whitespace issues).
- **Exact-Head GitHub CI (`42baef57ae5f305d84fbe4bcf28d83bd935d3f2f`):** All 4 check runs completed with `conclusion: success` (Backend, Frontend, Governance, Release build).

### QA Findings
- **Blocking Findings:** None.
- **Non-Blocking Findings:** None.
- **Verdict Application:** Approval applies specifically to commit `42baef57ae5f305d84fbe4bcf28d83bd935d3f2f`.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass — full suite not run; focused disposable migration/RLS suite passed.
☑ Documentation updated
□ ADR updated (if required) — no new architecture decision.
□ AI_BOOTSTRAP updated (if required) — no standing bootstrap rule changed.
□ PROJECT_STATE updated (if required) — T137 is not Done; synchronization belongs after QA.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required

