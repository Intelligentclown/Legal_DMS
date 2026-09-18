# Stage 3 - Phase 24

Status: Implementation complete; independent QA pending

Started: 2026-09-18

Completed:

Related Tasks: T127

Related ADRs: [ADR-0037](../../../ADR/0037-operational-fresh-installation-provenance.md), [ADR-0036](../../../ADR/0036-fresh-installation-party-enablement-boundary.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md), [ADR-0021](../../../ADR/0021-organization-tenant-boundary-enforcement.md), [ADR-0022](../../../ADR/0022-authorization-architecture.md)

Git Commit: Pending implementation commit

Pull Request: Pending implementation PR

Release:

------------------------------------------------

## Objective

Make ADR-0037 operational-fresh provenance authoritative for normal runtime
installation classification and ordinary Party-write eligibility, replacing
T124's continuing empty-database `FRESH` entitlement.

## Tasks Implemented

- Added `OPERATIONAL_FRESH` and `UNPROVEN` runtime states and retired `FRESH`
  as a Party-write-authorizing state.
- Made the SQLAlchemy classifier consume only T126's runtime-readable
  provenance projection for operational-fresh entitlement, with contract and
  revision compatibility checks, migration precedence, and fail-closed
  contradictory/unreadable evidence handling.
- Limited `PartyWriteGate` eligibility to `OPERATIONAL_FRESH`; migrated,
  legacy, unproven, and classifier-error paths remain denied.
- Added short transaction-scoped PostgreSQL locks for Client and migration-ledger
  evidence while the request session evaluates the gate and writes a Party.

## Files Modified

- `backend/src/app/application/interfaces/install_classifier.py`
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
- `backend/src/app/application/party_write_gate.py`
- `backend/src/app/presentation/api/v1/parties.py`
- `backend/tests/integration/test_install_classifier.py`
- `backend/tests/integration/test_party_routes.py`
- `docs/ImplementationLog/Stage3/Phase24.md`

## Tests Added

- Disposable PostgreSQL classification coverage for T126-created and bootstrapped
  installations, Party/Address growth, empty upgraded and Party-only T124-era
  databases, migration completion and contradiction precedence, unsupported or
  unreadable runtime projection, and transaction-scoped evidence locks.
- Party API regression now boots a real disposable T126 operational-fresh target
  rather than relying on the retired empty-row entitlement.

## Test Results

- Focused classifier, Party API, and T126 provenance PostgreSQL regression
  group: passed locally.
- T118/T119/T120 migration and Party/Address tenant-RLS regression group:
  passed locally.
- Final full-backend, lint/format, governance, and Alembic validation results
  are recorded with the implementation commit after the remaining developer
  checks complete.

## Design Decisions

- T126's `legal_dms_provenance.runtime_state` remains the sole runtime
  provenance input. T127 creates no schema migration, provenance DML grant, or
  bootstrap privilege.
- Supported evidence is exactly `adr-0037.v1` bound to T126 revision
  `c4e7a9b2d6f1`. Unknown contract/revision, multiple projection rows, read
  failures, and Client/ledger evidence that contradicts operational freshness
  deny ordinary Party writes.
- A valid operational-fresh transition survives legitimate Party and Address
  growth. Client or T118 ledger evidence remains contradictory legacy/migration
  evidence; a valid complete migration remains `MIGRATED` and non-writable
  pending Required ADR #20.

## Problems Encountered

- The former T124 Party API fixture modeled freshness by a zero-row upgraded
  database. It was changed to a T126 installer-created and bootstrapped
  disposable database so integration tests prove the current production rule.

## Deferred Work

- Required ADR #20 remains unresolved; T127 does not enable ordinary Party
  writes for migrated installations.
- ADR-0036 and ADR-0037 remain Proposed. No classifier extension for future
  provenance contract/revision is implied by this slice.

## Future Considerations

- A later explicitly authorized supported-schema revision must extend the
  classifier's compatibility list alongside the provenance contract; it must
  never be accepted implicitly.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing regressions run
☑ Documentation updated
☑ No migration or runtime provenance privilege expansion
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for independent QA

## QA Decision

Pending independent QA. This implementation record does not mark T127 Done,
does not claim QA approval, and does not authorize T128 or later work.
