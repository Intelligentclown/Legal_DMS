# Stage 3 - Phase 22

Status: Implementation complete; pending independent QA

Started: 2026-09-15

Completed: 2026-09-15

Related Tasks: [T124](IMPLEMENTATION_QUEUE.md) (Tenant-safe Party application surface & fresh-install enablement)

Related ADRs: [ADR-0021](../../../ADR/0021-organization-tenant-boundary-enforcement.md) (Organization is the tenant boundary), [ADR-0036](../../../ADR/0036-fresh-installation-party-enablement-boundary.md) (Proposed; T124 implements T120's Decision 4 prerequisite but does not accept the ADR itself)

Git Commit: implementation `2ae0dbfb2e5b9ae1678eedc38b378f8d530022c6`

Pull Request: #217 (open; implementation ready; not merged)

Release:

---

## Objective

Implement T124: make the Party table a normal application surface only for a
genuinely fresh installation. Add the `parties:read` / `parties:write` /
`parties:delete` permission codes with the approved role grant matrix,
expose an Organization-scoped `/parties` CRUD HTTP API where the Organization
is always sourced from the live auth context (never client input), and gate
every write (create/update/delete) on a live mechanical fresh-install
classifier (ADR-0036) that fails closed on any legacy business data -- with
the full test, quality-gate, implementation-log, PR, and hand-off-to-QA
sequence, without merge, without T125+ work, and without changing ADR-0036's
status.

## Tasks Implemented

- **Alembic migration `1b8f4a9c2e6d`** (parent `62cadaff2571`, reversible):
  - Inserts `parties:read`, `parties:write`, `parties:delete` into
    `permissions` with `description` and `category` (category is NOT NULL;
    follows the `9963e15f2752`/`224b650e5235` seed precedent).
  - Adds the T124 role grants (59 -> 71 `role_permissions`): Administrator
    and Advocate get read+write+delete; Paralegal and Clerk get read+write;
    Accountant and Read Only get read only.
  - Downgrade removes the grant rows then the permission rows.
- **Fresh-install classifier (ADR-0036 Decision 4 "Fresh-data context"):**
  - `ApplicationInstallationState` (`FRESH` / `LEGACY_WITH_BUSINESS_DATA` /
    `MIGRATED`) + `InstallationClassifier` application port
    (`backend/src/app/application/interfaces/install_classifier.py`).
  - `SqlAlchemyInstallationClassifier` infrastructure implementation:
    FRESH iff the 11 governed business tables (`clients`, `client_contacts`,
    `addresses`, `properties`, `property_owners`, `matters`, `appointments`,
    `invoices`, `payments`, `matter_parties`, `client_party_migration_ledger`)
    have zero rows (the per-write predicate; `parties` is excluded because it
    cannot be non-empty in a legitimately fresh system outside this surface's
    own writes -- the ADR-0036 full 12-table zero-row definition is retained
    conceptually); MIGRATED iff the migration ledger is non-empty and every
    `clients` row is covered by a distinct ledger `legacy_client_id`; any
    other non-empty shape is LEGACY.
  - `PartyWriteGate` raises `ForbiddenError` unless the installation is
    FRESH; it is evaluated per Party write, on the live DB only, with no
    env-name/config/test-flag proof and no hardcoded repo history.
- **Party application layer** (org-scoped, gate-first):
  - `PartyRepository` port + `SqlAlchemyPartyRepository`
    (get/list/count scoped by `organization_id`).
  - `PartyService.create/update/delete/list/get`: gate first, then Address
    same-Organization validation (`ValidationError` -> HTTP 422), then
    write-through (delete is a real `DELETE`, mirroring `clients`).
- **HTTP surface** (`/api/v1/parties`, registered in `router.py`):
  - `PartyRead` / `PartyCreate` / `PartyUpdate` pydantic schemas (no
    client-supplied `organization_id`; PUT is partial via `model_fields_set`).
  - Per-route `RequirePermission`: `parties:read` on GET list/get,
    `parties:write` on POST/PUT, `parties:delete` on DELETE; 401 without a
    token, 403 without the code.
  - `_require_organization()` resolves the Organization from the live
    `CurrentUser` DB row (never the JWT claim), fail-closed 403; reads and
    writes outside the caller's Organization behave as 404 (find first,
    then filter by org), consistent with `users`/`clients` routes.
  - Local dependencies (`PartyRepositoryDep`, `get_install_classifier`,
    `get_party_service`) so route tests can override the classifier; the
    real `SqlAlchemyInstallationClassifier` is the default.
- **Shared dev DB** upgraded `f3b7c9d1e2a4` -> `1b8f4a9c2e6d` (verified safe
  first: every business table empty, zero NULL-org Addresses, `legal_dms_app`
  reachable). Probe confirms head `1b8f4a9c2e6d`, 21 permissions,
  71 role_permissions, RLS on {addresses, organizations, parties, users}.

## Files Modified

- `backend/alembic/versions/1b8f4a9c2e6d_seed_party_permissions_and_role_grants.py` (new)
- `backend/src/app/application/interfaces/install_classifier.py` (new)
- `backend/src/app/infrastructure/persistence/sqlalchemy_install_classifier.py` (new)
- `backend/src/app/application/party_write_gate.py` (new)
- `backend/src/app/application/interfaces/party_repository.py` (new)
- `backend/src/app/infrastructure/persistence/sqlalchemy_party_repository.py` (new)
- `backend/src/app/application/party_service.py` (new)
- `backend/src/app/presentation/api/v1/parties.py` (new)
- `backend/src/app/presentation/api/v1/router.py` (register `/parties`)
- `backend/tests/integration/test_t66_role_permissions.py` (matrix 59 -> 71)
- `backend/tests/integration/test_party_tenant_finalization_and_rls.py` (HEAD -> `1b8f4a9c2e6d`)
- `backend/tests/integration/test_install_classifier.py` (new)
- `backend/tests/integration/test_party_routes.py` (new)
- `backend/tests/support/static_install_classifier.py` (new)
- Legacy db_session tests aligned to the tenant-finalized head (T122 made
  `addresses.organization_id` NOT NULL; the dev DB, now at head, no longer
  accepts org-less Addresses):
  - `backend/tests/support/synthetic_migration.py` (`seed_client_graph`
    seeds an org-scoped Address when an org is supplied, with a
    `legacy_org_less_address` opt-out for the legacy-head rehearsal)
  - `backend/tests/integration/test_client_migration_executor.py`,
    `test_client_migration_preflight.py`, `test_client_models.py` (org-scope
    Address fixtures)
  - `backend/tests/integration/test_organizations_users_rls.py` (RLS catalog
    set is now {addresses, organizations, parties, users})
  - `backend/tests/integration/test_seed_data.py` (permission count 21;
    parties codes present)
  - `backend/tests/integration/test_synthetic_migration_rehearsal.py`
    (`legacy_org_less_address=True` on legacy-shaped seeds)

## Tests Added

- `test_install_classifier.py` (integration, disposable DB at head):
  fresh-upgrade evidence (`current == 1b8f4a9c2e6d`); an empty installation
  classifies FRESH and the gate admits; `parties` rows alone never flip the
  classifier; a single governed row (Address) flips to LEGACY and the gate
  blocks (create/update/delete); a `clients` row without a ledger is LEGACY
  and blocked; a fully ledger-covered client set with ledger rows classifies
  MIGRATED and blocks; a parally-covered set classifies LEGACY and blocks.
- `test_party_routes.py` (integration, disposable DB at head, real mounted
  app via `ASGITransport`):
  - Authorization: 401 without token and 403 without the required code for
    every route/permission (including read-after-write).
  - Organization scoping: no-org fail-closed 403; cross-org reads are 404 /
    empty lists; cross-org writes/deletes are 404.
  - CRUD happy path: create (201) -> get (200) -> list (200, pagination
    meta) -> partial PUT (merges, exclusive field semantics) -> explicit-null
    address update -> delete (204) -> 404 after delete; PUT/DELETE on missing
    ids are 404; validation failures are 422.
  - Address same-Organization validation (via a forced-FRESH classifier):
    same-org accepted; cross-org/nonexistent address on create and
    create-then-update are 422; reads stay 200.
  - Real fresh-install gate: a legacy Address row flips the real classifier,
    so create/update/delete fail closed with 403 while reads still return 200.

## Test Results

Implementation-phase validation, run 2026-09-15 (QA is a separate,
independent step; none of this substitutes for it):

- Tooling: `uv run ruff check src tests alembic` -- All checks passed;
  `uv run black --check src tests alembic` -- 254 files unchanged;
  `git diff --check` -- clean.
- New integration: `test_install_classifier.py` -- passed; `test_party_routes.py`
  -- 23 passed (one pagination-meta correction made during development).
- Updated suites all green together: `test_t66_role_permissions.py`
  (71-grant matrix), `test_party_tenant_finalization_and_rls.py` (at the new
  head), `test_organizations_users_rls.py`, `test_seed_data.py`,
  `test_client_models.py`, `test_client_migration_executor.py` (21 tests),
  `test_client_migration_preflight.py`, `test_synthetic_migration_rehearsal.py`
  (legacy seeds preserved org-less via the flag).
- Full backend suite: **724 passed, 21 skipped** (Phase 21 baseline was
  693 passed / 21 skipped; +31 -- incl. 4 classifier, 23 route, and the
  updated matrix/head modules minus the dev-DB-alignment churn).
- Migration applied to the shared dev DB and re-verified:
  `uv run alembic current` -> `1b8f4a9c2e6d` (head); probe confirms
  21 permissions, 71 role_permissions, parties codes present, RLS on
  {addresses, organizations, parties, users}.
- Governance: `python scripts/governance_validate.py` -- OK (0 warnings, 0
  errors); `scripts/tests/test_governance_validate.py` -- 51 passed (6
  subtests).

## Design Decisions

- **Classifier computed live per write, over the DB only.** No env name,
  config flag, or test marker is ever read by application code; "freshness"
  is a mechanical property of the rows present. This satisfies ADR-0036
  Decision 4's "no operator/env/tooling proof" constraint and the T124
  authorization scope (DB row-presence is the only signal).
- **`parties` excluded from the per-write predicate.** A legitimately fresh
  installation can only ever reach a non-empty `parties` through this
  surface's own (gated) writes, so including it would make FRESH
  unreachable; the ADR-0036 full 12-table zero-row definition is retained in
  concept and the exclusion is documented in the classifier port. Any row in
  the other 11 tables still fails closed.
- **MIGRATED is its own state.** A non-empty ledger with full `clients`
  coverage is a completed T118 migration -- ordinary Party writes remain
  blocked (migration path exists), but the classifier distinguishes it from
  an unmigrated legacy heap.
- **409 would lie; use 404 for cross-org reads/writes.** Mirrors the
  established `users.py`/`clients.py` "find first, then org-filter" pattern
  (avoid leaking another Organization's existence). Missing/no-org auth
  fails closed with 403 before any lookup.
- **Dev DB jumped f3b7 -> head in one step.** Safe because the DB was
  empty (all business tables 0 rows, zero NULL-org Addresses). This is what
  exposed the dormant misalignment of the legacy db_session tests with
  T122/T123's tenant finalization; per the extension approved in this phase,
  those tests were aligned to head rather than the DB being downgraded.
- **Test seams are local FastAPI dependencies, not env flags.** The
  classifier dependency is injectable per-route so tests can pin FRESH only
  for the address-validation scenarios that need it; the real classifier is
  exercised against disposal DBs everywhere else.

## Problems Encountered

- **31 previously-green tests broke the moment the dev DB reached head.**
  The db_session suite assumed the legacy-head schema: executor/preflight/
  client_models seeded org-less Addresses (T122 made `addresses.organization_id`
  NOT NULL), the RLS catalog asserted exactly {organizations, users} (T122/
  T123 added addresses and parties), and `test_seed_data` asserted 18
  permissions. T122/T123 had never bumped the dev DB, so the misalignment
  was latent. Decision (user-approved): keep the DB at head and update the
  legacy fixtures/assertions, which the user chose over downgrading the DB.
- **`seed_client_graph` org-scoping conflicted with the legacy rehearsal.**
  The rehearsal asserts legacy Addresses stay org-less after rollback, so
  attaching the org whenever one was passed broke it. Resolved with an
  explicit `legacy_org_less_address` opt-out used only by the rehearsal.
- **One pagination assertion assumed a flat `meta.total`**, but the app's
  envelope is `meta.pagination.total` (`presentation/common/response.py`);
  corrected in `test_party_routes.py`.
- Unused imports / long lines in new test files were cleared by the
  project's own ruff + black gates (no unrelated reformatting).

## Deferred Work

- The PM pre-merge gate, QA, and merge of PR #217 remain pending.
- ADR-0036 remains **Proposed**; T124 implements its fresh-install
  enablement but a subsequent task must accept the ADR itself.
- Client cutover / role retirement, MatterParty re-staging, ledger and
  executor redesign, and broad (non-Party) Admin API surfaces remain
  unauthorized (explicit T124 exclusions).
- The pre-existing full-history Alembic `--sql` JSONB literal-rendering
  limitation (around the `9963e15f2752` seed migration) remains outside T124;
  migration-range behavior was verified on real disposable databases and the
  shared dev DB.

## Future Considerations

- `parties` now has left OAuth/tenant context for free; any future Party
  endpoint inherits RLS scoping via the existing tenant-GUC plumbing.
- When `clients` etc. later gain RLS or `matter_parties`/ledger finalize,
  the "exactly N tenant tables" catalog assertions will need similar
  era-pin treatment.
- The 8 behavioral `legal_dms_app` RLS tests still skip in this environment
  (role not provisioned on the configured port) -- a pre-existing,
  environment-only gap, unchanged by T124.

## Reviewer Checklist

- [x] Architecture preserved
- [x] Existing design patterns followed
- [x] Tests added
- [x] Existing tests pass
- [x] Documentation updated
- [ ] ADR updated (if required)
- [ ] AI_BOOTSTRAP updated (if required)
- [ ] PROJECT_STATE updated (if required)
- [x] No unrelated refactoring
- [x] No scope creep
- [x] Ready for QA

Notes on unchecked boxes: "ADR updated" -- no architectural decision was
created or changed this phase (ADR-0036 status unchanged, per scope);
"AI_BOOTSTRAP updated" -- no standing convention changed (N/A);
"PROJECT_STATE updated" -- closeout synchronization is the Documentation
Manager's responsibility after QA, per `docs/ImplementationLog/README.md`.

## QA Decision

To be completed by independent QA.