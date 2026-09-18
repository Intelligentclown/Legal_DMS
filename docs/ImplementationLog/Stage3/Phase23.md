------------------------------------------------

# Stage 3 - Phase 23

Status: In Progress (implementation awaiting independent QA)

Started: 2026-09-18

Completed:

Related Tasks: T126

Related ADRs: [ADR-0037](../../../ADR/0037-operational-fresh-installation-provenance.md), [ADR-0036](../../../ADR/0036-fresh-installation-party-enablement-boundary.md), [ADR-0021](../../../ADR/0021-organization-tenant-boundary-enforcement.md), [ADR-0022](../../../ADR/0022-authorization-architecture.md)

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Implement ADR-0037's durable provenance, privilege, fresh-install birth, and
serialized operational-bootstrap foundation without activating it in T124's
normal runtime classifier or Party write gate.

## Tasks Implemented

- Added installation-wide append-only provenance events and guarded database
  routines for immutable birth plus one operational-fresh transition.
- Added a serializable blank-target installer path and restricted bootstrap
  operation with retry-safe concurrent behavior.
- Added the dedicated bootstrap-role provisioning command and minimal runtime
  read projection; ordinary runtime has no provenance mutation or bootstrap
  execution privilege.

## Files Modified

- `backend/alembic/env.py`
- `backend/alembic/versions/c4e7a9b2d6f1_operational_fresh_provenance.py`
- `backend/pyproject.toml`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/src/app/infrastructure/cli/operational_fresh_bootstrap.py`
- `backend/src/app/infrastructure/cli/provision_bootstrap_role.py`
- `backend/tests/support/synthetic_migration.py`
- `backend/tests/integration/test_operational_fresh_provenance.py`
- `backend/tests/integration/test_install_classifier.py`
- `backend/tests/integration/test_party_tenant_finalization_and_rls.py`

## Tests Added

- `test_operational_fresh_provenance.py`: real disposable PostgreSQL coverage
  for blank-target birth, upgrade non-grandfathering, Party-inclusive bootstrap
  predicate, idempotent retry, concurrent bootstrap serialization, immutable
  provenance, and runtime privilege denial.

## Test Results

- T126 disposable PostgreSQL integration: 7 passed.
- T124 classifier plus Party/Address RLS regression group: 59 passed.
- Alembic head and generated PostgreSQL upgrade/downgrade SQL: passed.

## Design Decisions

- Ordinary Alembic upgrade creates only structure and privileges. Birth exists
  only through the separate installer, which requires a blank public schema,
  a transaction-scoped advisory lock, serializable isolation, and the full
  migration chain plus birth record in one transaction.
- The ongoing T124 classifier and `PartyWriteGate` remain unchanged by design;
  the runtime projection is inert until separately authorized integration.

## Problems Encountered

- Two concurrent serializable bootstrap calls can both obtain snapshots before
  one waits on the advisory lock. The bootstrap command now retries the one
  expected serialization/uniqueness conflict and observes the committed event
  idempotently; this is proven by the concurrent PostgreSQL test.

## Deferred Work

- ADR-0037 classifier precedence and `PartyWriteGate` integration require a
  separately authorized follow-on task.

## Future Considerations

- Future supported schema revisions must explicitly extend the revision-bound
  provenance contract rather than silently accepting newer migrations.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☐ Existing tests pass
☑ Documentation updated
☐ ADR updated (if required)
☐ AI_BOOTSTRAP updated (if required)
☐ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☐ Ready for QA

Full backend and all required T118-T124 regressions remain to be run before
the implementation is marked ready for independent QA. No ADR, bootstrap
rule, or project-state change is required by this bounded implementation.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required
