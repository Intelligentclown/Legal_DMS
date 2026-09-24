------------------------------------------------

# Stage 3 – Phase 32

Status: Ready for independent QA

Started: 2026-09-24

Completed: 2026-09-24

Related Tasks: T138

Related ADRs: ADR-0020, ADR-0021, ADR-0022, ADR-0027, ADR-0030, ADR-0037, ADR-0040

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement the bounded T138 File application surface and Matter-scoped PostgreSQL number allocator.

## Tasks Implemented

- Added File repository port and SQLAlchemy implementation, File service, Matter-nested router, schemas, and v1 registration.
- Allocates canonical integer `file_number` with PostgreSQL `INSERT ... ON CONFLICT ... RETURNING` and inserts the File in the same request transaction; the repository only flushes and never commits.
- Added only `files:read` and `files:write` through the allocated T138 revision, with the authorized six-role matrix.
- Synchronized operational-fresh support to `be439c0d6fdb` without changing provenance semantics.

## Files Modified

- `backend/alembic/versions/be439c0d6fdb_seed_file_permissions_and_role_grants.py`
- `backend/src/app/application/interfaces/file_repository.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py`
- `backend/src/app/application/file_service.py`
- `backend/src/app/presentation/api/v1/files.py`
- `backend/src/app/presentation/api/v1/router.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/tests/integration/test_t138_file_migration_and_allocator.py`

## Tests Added

- Disposable PostgreSQL upgrade/downgrade test verifies exact File permission metadata and grants.
- Disposable PostgreSQL concurrent same-Matter burst verifies 12 unique ordered allocations; rollback reuses the uncommitted number.

## Test Results

- Focused T138 disposable PostgreSQL suite: passed.
- Existing T137 File foundation suite: 2 passed.
- Matter/Property regression selection: 8 passed.
- Ruff and Black: clean for source, tests, and migrations.
- Governance validator reports unresolved Required ADRs `[11, 12, 15, 16, 17, 20]`.

## Design Decisions

- Organization derives only from `CurrentUser`; request schemas accept neither Organization nor File number.
- Reads and writes resolve the Matter under the authenticated Organization before accessing a File. No DELETE route is registered.
- Title is the only service-level mutable field; Matter, Organization, and number are immutable.

## Problems Encountered

- The generated migration was an incomplete skeleton: it had an undefined annotation and omitted required provenance synchronization. It was completed in place; no second migration was generated.
- The schema has both a primary key and tenant composite unique key for a sequence row. The allocator therefore targets the tenant composite named constraint, which safely serializes concurrent first allocation.

## Deferred Work

- Document CRUD, File deletion/archive, display-number formatting, File moves, renumbering, and legacy resolution remain outside T138.

## Future Considerations

- Independent QA must verify the exact immutable implementation commit, especially migration downgrade/fresh parity, RLS application-role behavior, and route/security coverage.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass — focused PostgreSQL and selected regressions passed; full suite not run.
☑ Documentation updated
□ ADR updated (if required) — no ADR decision is made here.
□ AI_BOOTSTRAP updated (if required) — no process change.
□ PROJECT_STATE updated (if required) — T138 is not Done and synchronization belongs after QA.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
