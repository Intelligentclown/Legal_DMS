# Stage 3 - Phase 19

Status: In Progress (implementation PR pending independent QA)

Started: 2026-09-09

Related Tasks: T120

Related ADRs: [ADR-0033](../../../ADR/0033-tenant-isolation-and-rls-policy.md), [ADR-0034](../../../ADR/0034-party-client-migration-persistence-and-execution-ledger.md), [ADR-0035](../../../ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md)

Release:

---

## Objective

Add the reversible, nullable Client Organization staging foundation and make the
authorized legacy Client migration graph tenant-safe when both endpoint
Organization values are populated. Extend the existing T118 executor so each
governed per-anchor transaction stages Client ownership in dependency-safe
order without changing its immutable completion, replay, or fail-closed gates.

## Implemented Scope

- Added nullable `clients.organization_id`, its Organization FK and index, and
  the composite `uq_clients_organization_id_id` supporting key.
- Replaced only the authorized independent legacy FKs with nullable-safe
  `(organization_id, foreign_id)` same-Organization composite FKs: Client to
  Address; direct Client references; Property to Address; PropertyOwner to
  Property; Matter to Property; Appointment to Matter; Invoice to Matter; and
  Payment to Invoice and Matter.
- Updated the T118 executor to reject a pre-existing conflicting Client tenant,
  stage Client ownership with the source version/timestamp preserved, flush
  parent-to-dependent stages, and reject a completed ledger replay if Client
  staging is absent or inconsistent.
- Extended the T119 synthetic disposable-PostgreSQL rehearsal and focused
  metadata tests for tenant staging, cross-tenant rejection, rollback residue,
  clean retry, and replay fail-closed behavior.

## Data-Safety Decisions

- All newly introduced Client tenant state remains nullable. The migration does
  not backfill, synthesize ownership, or modify existing business rows.
- Composite foreign keys enforce tenant equality only when nullable staging
  values are present, preserving the ADR-0035 staged rollout.
- Executor staging occurs inside the existing per-anchor transaction; an
  injected final-flush failure leaves no Client, Party, bridge, MatterParty,
  downstream staging, or ledger residue.

## Files Modified

- `backend/alembic/versions/f3b7c9d1e2a4_client_tenant_staging_integrity.py`
  (new; parent `b7e8a4f2c6d0`)
- `backend/src/app/infrastructure/cli/client_migration_executor.py`
- `backend/src/app/infrastructure/persistence/models/client.py`
- `backend/src/app/infrastructure/persistence/models/property.py`
- `backend/src/app/infrastructure/persistence/models/matter.py`
- `backend/src/app/infrastructure/persistence/models/scheduling.py`
- `backend/src/app/infrastructure/persistence/models/financial.py`
- `backend/tests/conftest.py`
- `backend/tests/integration/test_client_migration_executor.py`
- `backend/tests/integration/test_synthetic_migration_rehearsal.py`
- `backend/tests/unit/test_client_tenant_staging_foundation.py` (new)

## Verification To Date

- Client model integrity, T118 executor, T108 preflight, all seven T119
  disposable-PostgreSQL rehearsal scenarios, and T120 structural regressions:
  **54 passed** on a newly provisioned database at Alembic head, then dropped.
- T110 validator, T111 staleness, and T115/T116 schema unit regressions:
  **36 passed**.
- Alembic graph: one head, `f3b7c9d1e2a4`.

## Exclusions Preserved

No real-data execution or reconciliation, `NOT NULL` finalization, RLS,
Party CRUD/API, compatibility-route/cutover work, Client retirement,
`matters.client_id` removal, bridge removal, broader domain redesign, Required
ADR #20 resolution, T121+ work, independent QA, or governance synchronization
occurred in this implementation phase.

## Deferred Work

Independent QA, documentation synchronization, and any follow-on task remain
outside this implementation phase and require their own governed lifecycle.
