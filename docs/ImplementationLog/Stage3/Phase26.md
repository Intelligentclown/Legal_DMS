# Stage 3 - Phase 26

Status: Implementation complete; independent QA pending

Started: 2026-09-22

Completed: 2026-09-22

Related Tasks: T130

Related ADRs: [ADR-0022](../../../ADR/0022-authorization-architecture.md), [ADR-0021](../../../ADR/0021-organization-tenant-boundary-enforcement.md), [ADR-0037](../../../ADR/0037-operational-fresh-installation-provenance.md)

Git Commit: `4ccca9b7dc7ec0580bcc866a4fc49c9a0f588368`

Pull Request: `feature/t130-address-application-crud` (open/unmerged at post-implementation documentation handover)

Release:

------------------------------------------------

## Objective

Expose the already tenant-finalized/RLS-protected Address aggregate through the
normal backend architecture so authenticated Organization users can safely
create, read, list, update and delete Address records for later Party/Property
composition, proofing forced RLS/runtime-role posture and operational-fresh
durability at the new migration head.

## Tasks Implemented

- Added the `AddressRepository` port (`get_by_id_in_organization`,
  `list_in_organization`, `count_in_organization`) and the Organization-scoped
  `SqlAlchemyAddressRepository` mirroring `SqlAlchemyPartyRepository` (T124).
- Added `AddressService` with writable-field projection, bounded
  geographic-reference existence validation (Country required; State/District/
  Taluka/Village optional but must resolve), NOT-NULL clear guards on
  `country_id`/`line1`/`address_type`, and controlled referenced-delete
  (DB FK `IntegrityError` -> `ConflictError` 409).
- Added the `addresses` router (GET/POST `/addresses`, GET/PUT/DELETE
  `/addresses/{id}`) with `AddressRead` (no `organization_id`/audit fields),
  `AddressCreate`/`AddressUpdate` schemas, per-route `RequirePermission`, and
  router/v1 registration.
- Added the `seed_address_permissions_and_role_grants` migration
  (`5d8a3f2e9c6b`): seeds `addresses:read`/`write`/`delete` and role grants
  mirroring parties (`role_permissions` 71 -> 83, `permissions` 21 -> 24).
  Because it is the first migration past the T126 frontier, it also
  re-creates `record_fresh_birth`/`enter_operational_fresh` with the new
  supported revision (`alembic_version` guards), and restores the parent
  bodies on downgrade — the documented "future revision must explicitly
  extend the supported runtime contract" mechanism.
- Updated the SQLAlchemy classifier and fresh-install CLI supported-revision
  constants, and T66/T124/T126-era HEAD constants and permission-count
  assertions (t66 matrix, seed-data counts).

## Files Modified

- `backend/src/app/application/interfaces/address_repository.py` (new)
- `backend/src/app/infrastructure/persistence/sqlalchemy_address_repository.py` (new)
- `backend/src/app/application/address_service.py` (new)
- `backend/src/app/presentation/api/v1/addresses.py` (new)
- `backend/src/app/presentation/api/v1/router.py`
- `backend/alembic/versions/5d8a3f2e9c6b_seed_address_permissions_and_role_grants.py` (new)
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py`
- `backend/src/app/infrastructure/cli/fresh_install_provenance.py`
- `backend/tests/integration/test_address_routes.py` (new)
- `backend/tests/integration/test_address_permission_migration.py` (new)
- `backend/tests/integration/test_address_rls_preservation_at_t130.py` (new)
- `backend/tests/integration/test_t66_role_permissions.py`
- `backend/tests/integration/test_seed_data.py`
- `backend/tests/integration/test_install_classifier.py`
- `backend/tests/integration/test_operational_fresh_provenance.py`
- `backend/tests/integration/test_party_tenant_finalization_and_rls.py`
- `docs/ImplementationLog/Stage3/Phase26.md` (this file)

## Tests Added

- 25-route API suite (authorization fail-closed per permission, org fail-closed
  without context, cross-org invisibility/update/delete denial, CRUD + list +
  pagination + partial update + nullable clear, default `registered` type,
  geography reference validation, referenced-delete 409s and post-unlink 204).
- 2-test permission-migration suite (upgrade/downgrade/re-upgrade with
  provenance-function supported-revision guards at head and after downgrade).
- 12-test RLS/runtime-role preservation suite at the new head (forced RLS,
  exactly four GUC-driven policies, non-owning/non-superuser `/BYPASSRLS`
  runtime role, default-deny and org scoping behavior).
- Classifier address-only growth operational-fresh durability test.

## Test Results

- `pytest tests/integration/test_address_routes.py`: 25 passed.
- `pytest tests/integration/test_address_permission_migration.py`: 2 passed.
- `pytest tests/integration/test_address_rls_preservation_at_t130.py`: 12 passed.
- `pytest tests/integration/test_t66_role_permissions.py
  tests/integration/test_operational_fresh_provenance.py`: 8 passed.
- `pytest tests/integration/test_install_classifier.py`: 13 passed.
- `pytest tests/integration/test_party_tenant_finalization_and_rls.py`: 26 passed.
- `pytest tests/unit`: 315 passed.
- `pytest tests/integration` full farm: 397 passed excluding the two
  pre-existing `test_auth_login`/`test_users` `caplog`+`asyncio_mode=auto`
  loop-share flakes (their 84 tests pass when run as that pair in isolation;
  neither module nor its assertions were modified).
- `uv run ruff check src tests alembic`: clean. `uv run black --check src tests
  alembic`: clean. `git diff --check`: clean.

## Design Decisions

- Permission migration is required: the architecture seeds permission
  codes/grants exclusively through Alembic migrations, and without
  `addresses:*` codes `RequirePermission` could never match (fail-closed 403).
  Follows T124's `1b8f4a9c2e6d` matrix convention exactly.
- No `PartyWriteGate` copy/generalization for Address (explicit T130 scope).
- "Bounded geographic-reference validation" = reference existence only; no
  hierarchy-consistency traversal, no new geography architecture.
- Referenced delete converts FK `IntegrityError` to `ConflictError` (409); no
  cascades/reassignment.
- `AddressRead` omits `organization_id` and audit fields (read scoping must
  not rely on RLS alone).
- The provenance functions are re-created byte-identical to T126 except the
  supported-revision literal; the `runtime_state` view, predicates, grants
  and policy surface are untouched.

## Problems Encountered

- First fresh-install run at the new head failed: T126's `record_fresh_birth`
  guard still demanded `c4e7a9b2d6f1`. Resolved by extending the supported
  runtime contract in the T130 migration (the documented required mechanism
  for the first post-frontier migration) and aligning the classifier/CLI/test
  constants; `test_address_permission_migration.py` now guards this surface
  on upgrade, downgrade, and re-upgrade.
- Test harness: the shared-session API override leaves the session in failed
  transaction state after a blocked delete; the referenced-delete test now
  commits its fixture and rolls back the failed request transaction, matching
  real `get_db` semantics.

## Deferred Work

- Frontend Address UI; Party redesign/nested Address creation; Client CRUD;
  Matter/MatterParty and Property/PropertyOwner cutover; File/work-package;
  Address deduplication/geocoding/maps/external verification/new hierarchy;
  Client<->Party cutover; migrated Party writes; bridge/`client_id` removal;
  Required ADR resolution; ADR-0036/0037/0038 status changes; self-context
  Layer B/C; T131+ (all unauthorized).

## Future Considerations

- The next migration must again extend the supported runtime contract (the
  T130 migration re-binds `record_fresh_birth`/`enter_operational_fresh` to
  `5d8a3f2e9c6b`); the classifier/CLI constants and relevant HEAD-pinned
  tests must move with it.

## Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no new decision
□ AI_BOOTSTRAP updated (if required) — excluded
□ PROJECT_STATE updated (if required) — QA/closeout owned
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

## QA Decision

□ Approved
□ Approved with comments
□ Rework required