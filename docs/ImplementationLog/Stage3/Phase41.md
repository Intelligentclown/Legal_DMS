------------------------------------------------

# Stage 3 – Phase 41

Status: In Progress — post-QA remediation candidate complete; awaiting Independent QA re-verification.

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
- Post-QA narrow remediation synchronized the operational-fresh revision constants
  to `b155caa6d4e1` and added permanent downgrade regression coverage.

## Files Modified

- `backend/alembic/versions/b155caa6d4e1_matter_property_tenant_integrity_foundation.py`
- `backend/src/app/infrastructure/persistence/models/__init__.py`
- `backend/src/app/infrastructure/persistence/models/matter_property.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/tests/integration/test_operational_fresh_provenance.py`
- `backend/tests/integration/test_matter_property_tenant_integrity_foundation.py`
- `docs/ImplementationLog/Stage3/Phase41.md`

## Tests Added

- `test_matter_property_tenant_integrity_foundation.py` verifies migration from
  `8d77007b9d7f`, one head, same-tenant insert, duplicate rejection, composite-FK
  tenant rejection, no Party/ownership mutation, trusted-context RLS behavior,
  populated downgrade refusal, empty downgrade cleanup, provenance restoration,
  and re-upgrade.

## Test Results

- `cd backend && uv run ruff check src tests alembic`: passed.
- `cd backend && uv run black --check src tests alembic`: passed.
- `cd backend && uv run pytest tests/integration/test_matter_property_tenant_integrity_foundation.py -v`:
  5 passed, 1 existing dependency warning.
- `cd backend && uv run pytest tests/integration/test_operational_fresh_provenance.py -v`:
  7 passed, 1 existing dependency warning.
- `cd backend && uv run pytest tests/unit -q`: 342 passed, 60 existing dependency warnings.
- `cd backend && alembic heads`: passed; one head, `b155caa6d4e1`.
- `python scripts/governance_validate.py --report`: passed; unresolved Required
  ADRs remain `[12,15,16,17,20]`.

## Design Decisions

- Reused existing audited-association metadata and the repository-standard trusted
  Organization GUC RLS policy shape.
- The association intentionally has no relationship qualifier, status, ownership,
  API behavior, or ORM traversal semantics.

## Problems Encountered

- The initial helper for reading PostgreSQL provenance function definitions used
  an invalid async generator expression. The focused suite exposed the error;
  replacing it with an explicit async loop restored the intended test-only helper.

## Deferred Work

- Independent QA must re-verify this post-QA-remediated candidate, including its
  two new downgrade regression cases.
- Application association CRUD, authorization/audit orchestration, historical
  convergence, and all T156+ work remain outside this task.

## Future Considerations

- A later, separately authorized application task can consume this model for
  Matter-scoped operations without adding persistence semantics retrospectively.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
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
