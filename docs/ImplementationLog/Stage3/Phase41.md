------------------------------------------------

# Stage 3 – Phase 41

Status: In Progress — implementation candidate complete; awaiting Independent QA.

Started: 2026-10-17

Completed:

Related Tasks: T155

Related ADRs: ADR-0044, ADR-0021, ADR-0039

Git Commit: 4dba68867aa5d4eda9e156fd09e9b9eee2e3214e

Pull Request:

Release:

------------------------------------------------

## Objective

Implement the authorized database/model foundation for canonical Organization-scoped
Matter–Property participation, without adding application association behavior or
changing the legacy Matter property shadow.

## Tasks Implemented

- Added the persistence-only `MatterProperty` model and model registration.
- Added a migration creating `matter_properties` with composite tenant-aware
  references to Matters and Properties, canonical-pair uniqueness, indexes, and
  trusted-context ENABLE/FORCE RLS policies.
- Advanced the operational-fresh provenance guard from `8d77007b9d7f` to the
  new sole revision `b155caa6d4e1`.
- Added disposable-PostgreSQL coverage for migration, integrity, tenant isolation,
  default-deny, FORCE RLS, and legacy-shadow coexistence.

## Files Modified

- `backend/alembic/versions/b155caa6d4e1_matter_property_tenant_integrity_foundation.py`
- `backend/src/app/infrastructure/persistence/models/__init__.py`
- `backend/src/app/infrastructure/persistence/models/matter_property.py`
- `backend/tests/integration/test_matter_property_tenant_integrity_foundation.py`
- `docs/ImplementationLog/Stage3/Phase41.md`

## Tests Added

- `test_matter_property_tenant_integrity_foundation.py` verifies migration from
  `8d77007b9d7f`, one head, same-tenant insert, duplicate rejection, composite-FK
  tenant rejection, no Party/ownership mutation, and trusted-context RLS behavior.

## Test Results

- `cd backend && uv run ruff check src tests alembic`: passed.
- `cd backend && uv run black --check src tests alembic`: passed.
- `cd backend && uv run pytest tests/unit/test_matter_service.py tests/unit/test_property_service.py`:
  11 passed, 1 existing dependency warning.
- `cd backend && alembic heads`: passed; one head, `b155caa6d4e1`.
- The focused disposable-PostgreSQL test command could not run because the local
  PostgreSQL endpoint refused connections (`WinError 1225`); this is an environment
  failure, not represented as a passing candidate test.

## Design Decisions

- Reused existing audited-association metadata and the repository-standard trusted
  Organization GUC RLS policy shape.
- The association intentionally has no relationship qualifier, status, ownership,
  API behavior, or ORM traversal semantics.

## Problems Encountered

- Local PostgreSQL was unavailable, blocking execution of the newly added real-
  PostgreSQL tests and broader database integration validation.

## Deferred Work

- Independent QA must execute the real-PostgreSQL migration/integrity/RLS coverage
  against the frozen candidate.
- Application association CRUD, authorization/audit orchestration, historical
  convergence, and all T156+ work remain outside this task.

## Future Considerations

- A later, separately authorized application task can consume this model for
  Matter-scoped operations without adding persistence semantics retrospectively.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
□ Existing tests pass — focused real-PostgreSQL coverage and the broad suite are
blocked by unavailable local PostgreSQL.
☑ Documentation updated
□ ADR updated (if required) — ADR-0044 remains unchanged and Proposed.
□ AI_BOOTSTRAP updated (if required) — no standing-process change.
□ PROJECT_STATE updated (if required) — post-QA synchronization belongs to the
Documentation Manager.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
