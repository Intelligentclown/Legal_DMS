------------------------------------------------

# Stage 3 - Phase 14

Status: Done

Started: 2026-09-05

Completed: 2026-09-05

Related Tasks: T115

Related ADRs: [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md)

Git Commit: `4aca7d9b944067423faf3dd4585183b95f14e9d8`

Pull Request: #202 (open; documentation synchronization head pending PM pre-merge gate)

Release:

------------------------------------------------

## Objective

Establish only the first ADR-0035 tenant-supporting schema foundation for Address and downstream legacy Client graph tables, without reconciling or changing legacy data.

## Tasks Implemented

- Added nullable `organization_id` staging columns, Organization foreign keys, direct indexes, and `(organization_id, id)` unique keys for `addresses`, `properties`, `matters`, `property_owners`, `appointments`, `invoices`, `payments`, and retained `client_contacts`.
- Added matching SQLAlchemy persistence-model metadata and a reversible Alembic revision. No migration data statements, Party schema, Party bridge, or tenant enforcement cutover was added.

## Files Modified

- `backend/src/app/infrastructure/persistence/models/client.py`
- `backend/src/app/infrastructure/persistence/models/property.py`
- `backend/src/app/infrastructure/persistence/models/matter.py`
- `backend/src/app/infrastructure/persistence/models/financial.py`
- `backend/src/app/infrastructure/persistence/models/scheduling.py`
- `backend/alembic/versions/d8f4a6c9b3e1_tenant_supporting_address_foundation.py`
- `backend/tests/unit/test_tenant_schema_foundation.py`
- `docs/ImplementationLog/Stage3/Phase14.md`

## Tests Added

- `test_tenant_schema_foundation.py` verifies the nullable Organization-column ORM contract and records every additive migration upgrade/downgrade operation for all eight governed tables.

## Test Results

- Focused T115 tests: 3 passed.
- Full backend unit suite: 288 passed.
- T110/T111 unit regressions: 21 passed.
- T108 integration regressions and database-backed integration tests could not run because PostgreSQL refused connections and Docker Desktop was unavailable.
- `alembic upgrade 7192e84e9a2f:head --sql` and `alembic downgrade head:7192e84e9a2f --sql` both passed. Online Alembic verification could not connect to PostgreSQL.
- Ruff and Black passed. Governance validation passed, including 51 governance tests.

## Design Decisions

- Every new `organization_id` is deliberately nullable. ADR-0035 permits `NOT NULL` only after governed reconciliation/backfill, so this migration does not fabricate or infer Organization ownership.
- Composite same-Organization foreign keys remain deferred with the Party and bridge schema phases explicitly scheduled later by ADR-0035.

## Problems Encountered

- The local PostgreSQL service was unavailable and Docker Desktop was not running. This prevented online migration checks and database-backed tests; no repository code or test fixture was changed to hide the condition.

## Deferred Work

- Governed reconciliation/backfill, non-null enforcement, Party/MatterParty/ledger schema, Party bridges, and all write-capable migration behavior remain deferred to separately authorized ADR-0035 steps.

## Future Considerations

- Live PostgreSQL/Docker verification remains unperformed because both Developer and QA environments lacked it. SQLite/offline Alembic verification and CI passed; the persisted QA Decision is Approved, so this is a disclosed environment limitation rather than a remaining pre-merge requirement.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
□ Existing tests pass - database-backed tests are blocked by unavailable PostgreSQL; all 288 unit tests pass.
☑ Documentation updated
□ ADR updated (if required) - no new architecture decision was made.
□ AI_BOOTSTRAP updated (if required) - no standing convention changed.
☑ PROJECT_STATE updated (if required) - Documentation Manager synchronization records T115 as Done.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for PM pre-merge gate - independent QA Approved and documentation synchronization completed.

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required

QA evidence: `5209c11404cb7ba61aa12485b8aa66aff72f369c`. Required ADR #20 remains unresolved, and
T116+ remains unauthorized.
