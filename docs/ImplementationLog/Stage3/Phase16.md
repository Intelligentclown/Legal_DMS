------------------------------------------------

# Stage 3 - Phase 16

Status: In Progress

Started: 2026-09-08

Completed:

Related Tasks: T117

Related ADRs: [ADR-0034](../../../ADR/0034-party-client-and-representative-migration-architecture.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md)

Git Commit:

Pull Request: (implementation PR opened after this commit; number recorded once created)

Release:

------------------------------------------------

## Objective

Establish only ADR-0035 sequence step 3: nullable direct `party_id` compatibility bridge columns, composite same-Organization foreign keys to `parties`, and matching ORM metadata for `property_owners`, `appointments`, `invoices`, `payments`, and retained `client_contacts`.

## Tasks Implemented

- Added a reversible Alembic revision (`b7e8a4f2c6d0`, parent `e6a2d4c8f1b7`) adding a nullable `party_id UUID`, a composite `FOREIGN KEY (organization_id, party_id) REFERENCES parties (organization_id, id)` supported by T116's `uq_parties_organization_id_id`, and an `ix_<table>_party_id` index for each of the five governed bridge tables.
- Updated the `PropertyOwner`, `Appointment`, `Invoice`, `Payment`, and `ClientContact` ORM models with a bare `party_id` column (`mapped_column(index=True)`) and the matching composite `ForeignKeyConstraint` in `__table_args__`. No standalone single-column `party_id -> parties.id` reference exists.
- Added focused structural and behavioral tests. No Party values are fabricated, no rows are backfilled, and no bridge column is made `NOT NULL`.

## Files Modified

- `backend/src/app/infrastructure/persistence/models/property.py`
- `backend/src/app/infrastructure/persistence/models/scheduling.py`
- `backend/src/app/infrastructure/persistence/models/financial.py`
- `backend/src/app/infrastructure/persistence/models/client.py`
- `backend/alembic/versions/b7e8a4f2c6d0_party_compatibility_bridge_foundation.py`
- `backend/tests/unit/test_party_compatibility_bridge_foundation.py`
- `docs/ImplementationLog/Stage3/Phase16.md`

## Tests Added

- `test_party_compatibility_bridge_foundation.py` verifies every bridge table's ORM contract (nullable `party_id`, composite same-Organization Party foreign key, no standalone `party_id` reference, matching index, retained `client_id` and nullable `organization_id`), records the exact additive upgrade/downgrade operation sequences, and live-probes the composite foreign key on SQLite: `NULL` accepted, same-Organization pairing accepted, cross-Organization pairing rejected.

## Test Results

- Focused T117 bridge tests plus T115/T116 schema regressions: 16 passed.
- Full backend unit suite: 593 passed, 21 skipped.
- Ruff and Black passed on all six changed backend files. `git diff --check` passed.
- `alembic heads` reports only `b7e8a4f2c6d0`. Offline PostgreSQL SQL generation passed for both `alembic upgrade e6a2d4c8f1b7:head --sql` and `alembic downgrade head:e6a2d4c8f1b7 --sql`.
- Live PostgreSQL (dockerized `postgres:16-alpine`, healthy on `:5433`): `alembic upgrade head` applied the revision; `alembic downgrade -1` reverted all five `party_id` columns; `alembic upgrade head` re-applied and left the schema at `b7e8a4f2c6d0` (head). Live reflection confirms five `FOREIGN KEY (organization_id, party_id) REFERENCES parties (organization_id, id)` constraints, five nullable `party_id` columns, five `ix_<table>_party_id` indexes, and zero standalone single-column `party_id` foreign keys.
- Rollback-only PostgreSQL temporary-table probe: a `NULL`-`NULL` bridge row and a same-Organization pairing were accepted; a cross-Organization pairing raised the composite foreign-key violation, confirming tenant-integrity enforcement.
- Governance validation passed, including its 51-test suite. `alembic check` reports only the pre-existing T116 local-state drift described in Problems Encountered; none of the five T117 bridge tables appear in the detected diff.

## Design Decisions

- Every `party_id` bridge column is deliberately nullable. ADR-0035 requires `NOT NULL` only after governed reconciliation/backfill, so this migration does not fabricate Party values, silently backfill rows, or stage any column for future `NOT NULL` enforcement.
- Tenant integrity is enforced through composite Organization-leading foreign keys referencing `parties (organization_id, id)`, relying on T116's `uq_parties_organization_id_id` as the parent key and mirroring the T116 ledger remediation pattern. No standalone single-column `party_id` FK is created.
- The new migration is a single reversible revision appended after `e6a2d4c8f1b7`; no existing revision was edited, keeping the chain single-headed and replayable.
- ORM `party_id` columns are bare `mapped_column(index=True)` (as `MatterParty.party_id` already is), with the composite FK declared in `__table_args__`; the naming convention yields exactly the migration's `ix_<table>_party_id` index names.
- `client_id` columns and the T115 `organization_id` staging columns are untouched; `client_contacts` is retained exactly as governed.

## Problems Encountered

- `alembic check` detects a remaining diff on `client_party_migration_ledger` (`remove_fk fk_client_party_migration_ledger_party_id_parties` / `add_fk fk_client_party_migration_ledger_organization_id_parties`). This is the pre-existing, disclosed T116 local-dev schema drift from the pre-remediation revision that was already applied to the shared development database; it was not mutated in place then and is not touched by T117. The five T117 tables produce no autogenerate diff.
- Ruff flagged import wrapping, one over-length docstring, and missing trailing newlines on first pass; these were resolved with Black, `ruff check --fix`, and a docstring shortening. No test or migration behavior changed.

## Deferred Work

- Reconciliation/backfill, `NOT NULL` enforcement on existing staged columns, Party business rows/CRUD/API, Client-to-Party backfill, the write-capable migration executor and execution ledger, Organization backfill, RLS/permission rollout, cutover, T109 execution, Required ADR #20 resolution, and T118+ authorization or implementation all remain deferred to separately authorized work per the T117 authorization record.

## Future Considerations

- The composite bridge foreign key only enforces tenant equality when both columns are non-null; while `organization_id` and `party_id` remain nullable for legacy rows, a row with one set and the other null bypasses `MATCH FULL`-style enforcement by design (per ADR-0035 staging).
- The independent QA Reviewer should re-run the live PostgreSQL cross-tenant probe (and the full unit suite) from the exact remote PR head, and Documentation Manager synchronization must follow only after a QA Decision exists.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass - 593 passed, 21 skipped; live PostgreSQL DDL and rollback-only probe both confirmed tenant-integrity behavior.
☑ Documentation updated - this phase log, plus the T117 authorization record and `PROJECT_STATE.json` `latestTaskAuthorized`.
□ ADR updated (if required) - no new architecture decision was made; ADR-0035 step 3 is implemented as governed.
□ AI_BOOTSTRAP updated (if required) - no standing convention changed.
□ PROJECT_STATE updated (if required) - T117 authorization is recorded; the Done synchronization is Documentation Manager work, after QA.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA - an independent QA Reviewer can verify this batch from the log and the remote PR head alone.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required

QA pending: independent QA Reviewer review is the next lifecycle step. Per the T117 authorization's stopping boundary, this implementation is not to be merged, self-QA'd, marked Done, or proceeded-from into T118. Required ADR #20 remains unresolved globally, and T118+ remains unauthorized.