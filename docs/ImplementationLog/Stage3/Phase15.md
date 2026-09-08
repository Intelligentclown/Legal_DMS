------------------------------------------------

# Stage 3 - Phase 15

Status: Done

Started: 2026-09-05

Completed: 2026-09-08

Related Tasks: T116

Related ADRs: [ADR-0034](../../../ADR/0034-party-client-and-representative-migration-architecture.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md)

Git Commit: `4ab657dc860c716438f5b58872ec7aa284efd37c`; remediation `c6faca8552692969d90b92e37bb4b40ee9714763`

Pull Request: #203 (open; documentation synchronization head pending PM pre-merge gate)

Release:

------------------------------------------------

## Objective

Establish only ADR-0035 sequence step 2: the Party, bounded MatterParty, and Client-to-Party migration execution-ledger schema foundation.

## Tasks Implemented

- Added the tenant-scoped `parties` table and ORM model with the governed Party fields, checks, tenant-leading indexes, and nullable same-Organization Address reference.
- Added only the bounded migration-era `matter_parties` contract needed for the legacy Matter client relationship, with composite same-Organization Matter and Party foreign keys.
- Added the immutable `client_party_migration_ledger` persistence shape, its provenance fields, governed identity and resolution checks, uniqueness constraints, lookup indexes, and composite same-Organization Party foreign key.
- Added a reversible Alembic migration and focused structural tests. No rows are created, reconciled, or backfilled.

## Files Modified

- `backend/src/app/infrastructure/persistence/models/__init__.py`
- `backend/src/app/infrastructure/persistence/models/party.py`
- `backend/alembic/versions/e6a2d4c8f1b7_party_matterparty_ledger_foundation.py`
- `backend/tests/unit/test_party_schema_foundation.py`
- `docs/ImplementationLog/Stage3/Phase15.md`

## Tests Added

- `test_party_schema_foundation.py` verifies the governed Party fields, tenant-safe composite foreign keys, bounded MatterParty shape, immutable ledger identity constraints, and migration operation order.

## Test Results

- Focused T116 plus T110/T111/T115 regressions: 33 passed, including the ledger cross-tenant rejection and same-Organization acceptance checks.
- Full backend unit suite: 297 passed.
- Ruff and Black passed.
- `alembic heads` reports only `e6a2d4c8f1b7`.
- Offline PostgreSQL SQL generation passed for both `alembic upgrade d8f4a6c9b3e1:head --sql` and `alembic downgrade head:d8f4a6c9b3e1 --sql`.
- A rollback-only PostgreSQL temporary-table probe rejected a cross-tenant ledger Party pairing and accepted the matching Organization pairing.
- Governance validation passed, including 51 governance tests. `git diff --check` passed.

## Design Decisions

- The pre-existing T115 `organization_id` staging columns remain nullable. This migration does not infer Organization ownership or make staged legacy data non-null.
- Party-to-Address, MatterParty-to-Matter, and MatterParty-to-Party tenant safety is enforced through composite Organization-leading foreign keys supported by the T115 and T116 composite unique keys.
- The ledger deliberately has no audit mixin, version column, soft deletion, or application write path, preserving its append-only execution-record shape without implementing an executor.
- The QA-identified ledger tenant-boundary defect is remediated by `(organization_id, party_id) -> parties(organization_id, id)` while retaining the direct Organization foreign key and all original ledger identity constraints.

## Problems Encountered

- Docker Desktop's daemon is not running, but the configured PostgreSQL server was available for a rollback-only temporary-table probe of the composite FK. `alembic check` correctly detected the pre-remediation Party-only FK in the already-applied local development schema; it was not mutated in place because this unmerged PR deliberately corrects its original migration. Offline PostgreSQL SQL generation and structural tests passed without weakening tests.

## Deferred Work

- T116 does not create Party, MatterParty, or ledger rows; reconcile/backfill Clients; add downstream `party_id` bridges; expose Party CRUD; remove legacy Client fields; or perform cutover.

## Future Considerations

- Developer performed a rollback-only PostgreSQL temporary-table probe demonstrating cross-tenant ledger/Party pairing rejection and matching-Organization acceptance. QA did not perform live PostgreSQL verification because its Docker/environment was unavailable. The `alembic check` drift against the Developer's pre-existing local database is expected local-state drift from editing an unmerged revision already applied there, not a product or production-migration failure. Offline Alembic SQL, focused tests, and exact QA-head CI passed.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing unit tests pass
☑ Documentation updated
□ ADR updated (if required) - no new architecture decision was made.
□ AI_BOOTSTRAP updated (if required) - no standing convention changed.
☑ PROJECT_STATE updated (if required) - Documentation Manager synchronization records T116 as Done.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for PM pre-merge gate - final independent QA Approved and documentation synchronization completed.

## QA Decision

☑ Approved
□ Approved with comments
□ Rework required

QA history: initial evidence `222541d2ea19ffdd37af3c249eee3e8fd68fc12f` recorded **Rework required** because
the ledger `organization_id` was not structurally tied to its referenced Party. Remediation
`c6faca8552692969d90b92e37bb4b40ee9714763` added the composite same-Organization ledger-to-Party
foreign key. Final QA re-review evidence `a3b5388c48e29e4fc0ff6f0a50792e89835cfc83` is **Approved**.
Required ADR #20 remains unresolved, and T117+ remains unauthorized.
