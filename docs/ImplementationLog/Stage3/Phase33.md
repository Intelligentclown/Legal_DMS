------------------------------------------------

# Stage 3 – Phase 33

Status: Ready for independent QA

Started: 2026-09-25

Completed: 2026-09-25

Related Tasks: T139

Related ADRs: ADR-0020, ADR-0021, ADR-0022, ADR-0030, ADR-0040

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Provide the bounded File-canonical Document metadata surface authorized by T139 without changing schema, storage, versioning, File allocation, or legacy-unfiled state.

## Tasks Implemented

- Added an Organization/Matter/File-scoped Document repository port and SQLAlchemy implementation.
- Added Document service and nested API routes for list, get, File-canonical create, and metadata-only update.
- Derived Document Organization and compatibility Matter from authenticated/nested canonical context; ordinary creation has no unfiled path.
- Enforced existing `documents:read` and `documents:write`; no DELETE route or new permission/migration exists.

## Files Modified

- `backend/src/app/application/interfaces/document_repository.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_document_repository.py`
- `backend/src/app/application/document_service.py`
- `backend/src/app/presentation/api/v1/documents.py`
- `backend/src/app/presentation/api/v1/router.py`
- `backend/tests/unit/test_document_service.py`
- `backend/tests/integration/test_document_routes.py`
- `docs/ImplementationLog/Stage3/Phase33.md`

## Tests Added

- Unit service coverage for canonical relationship derivation, invalid nested File/type rejection, legacy-unfiled exclusion, immutable relationships, and stale-version conflicts.
- Disposable PostgreSQL API coverage for create/list/get/update, legacy preservation, and the fact that File/Matter permissions do not substitute for Document permissions.

## Test Results

- Focused T139 unit/API, T137 foundation, and T138 allocator suites passed.
- Matter, Property, Party, and Address regression selection passed.
- Ruff, Black, compile validation, Alembic heads, `git diff --check`, and governance validation passed.
- Alembic remains sole head `be439c0d6fdb`; no migration or provenance/classifier change was made.

## Design Decisions

- The nested route validates Matter then File under the authenticated Organization; Document fields never accept Organization, Matter, or File identity.
- `documents.matter_id` is written only from the validated File/Matter route context. List/get predicates require `file_id`, so legacy-unfiled Documents are never represented as members of a File.
- Update exposes only `title`, existing string `status`, and `document_type_id`; relationship fields are absent. The existing model version is returned and an optional supplied version gives a 409 stale-write guard.

## Problems Encountered

- The initial PostgreSQL API fixture inserted Matter and File in one unordered flush. The composite File/Matter FK correctly rejected that fixture; it was corrected to flush Matter before File. No production behavior changed.

## Deferred Work

- DocumentVersion, storage/upload/download/OCR, File lifecycle changes, legacy-unfiled resolution, synthetic Files, relationship reassignment, and Document DELETE remain excluded pending separate authority.

## Future Considerations

- Independent QA should review the immutable implementation commit and re-run real PostgreSQL RLS coverage, including no-GUC/wrong-GUC behavior already supplied by the unchanged T137 forced-RLS foundation.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no new decision or ADR change is authorized.
□ AI_BOOTSTRAP updated (if required) — no standing process changed.
□ PROJECT_STATE updated (if required) — T139 is not Done; post-QA synchronization belongs to the Documentation Manager.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
