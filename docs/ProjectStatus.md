# Project Status

**Current Stage:** Formally **Stage 3 — Authentication & Authorization** (`T41`–`T85`) — done and
merged in full, including `T82`'s Electron-runtime live smoke verification (closed **FAIL**,
QA-Approved-with-comments: the authenticated session did not survive a renderer reload or app
restart) and its `T83`–`T85` follow-up fix (test-account provisioning, the session-restoration
implementation, and a preload-script load-failure fix that had been blocking that implementation's
own native verification). `T86`–`T103` followed as pre-Stage-4 governance/architecture-preparation
work, not further Stage-3 implementation: `T86` adopted the governed Domain Model & Functional
Specification; `T87`–`T94`, `T98`, and `T101` each drafted and resolved a Required ADR (ten of the
specification's twenty planning-list items now resolved — see `PROJECT_STATE.json`'s
`governanceLedger.resolvedRequiredADRs`); `T102` resolved User↔Organization membership/tenant-context
semantics (`ADR/0031`), a gap outside that twenty-item list; `T103` resolved the narrow
pre-existing-data-reconciliation slice of Required ADR #20 that `ADR/0031` itself left open
(`ADR/0032`); `T95`/`T99`/`T100` built and then twice repaired the governance-validation tooling that
gates all of the above. See "Completed — Governance & Required-ADR Resolution Series (`T86`–`T103`)"
below for the full task-by-task record. **No Organization/Tenant Core implementation is authorized —
`ADR/0031` §15 and `T102`'s own authorization text both require a fresh Project Manager/Control
Tower re-assessment before any such implementation task can begin, and this file does not perform or
imply that re-assessment.** See [PROJECT_CHECKPOINT.md](../PROJECT_CHECKPOINT.md) for further
current-state detail as of its own last update (predates `T81`+ — not resynchronized by this pass,
out of this task's authorized file scope); this file is the maintained narrative version.
**Current Version:** 0.3.1 (see [CHANGELOG.md](../CHANGELOG.md)'s versioning note — the `v0.3.0`
tag already contains everything previously documented as 0.3.1 through 0.3.8; this version is only
what's genuinely new since that tag, previously mislabeled 0.3.9). No new tag has been cut since;
substantial work (`T41`–`T78`) has landed on `main` under this same version number.
**Last Updated:** 2026-09-25 (Documentation Manager, T140 governance closeout).
Fresh verification confirms T120 authorization merged at `main` `d14347df5cc8d78481c3af79f3516bc42472128b`;
PR #209 remains open at corrected QA-approved head `3c46bebbe75e956fd1be0bc157fe891ea8516ab9`.
Authorization `772e91f22be78f57970be867258d354c81024118` and reviewed implementation head
`48c8f7c5c87a9a1c0bc2ce92827e4f0a43c4672a` are ancestors. The QA-only evidence commit is Approved.
T120 is now Done: nullable Client tenant staging, composite same-Organization integrity constraints,
executor dependency-safe Client staging, and synthetic rollback/retry/replay coverage landed. QA records
630 backend passed/21 skipped plus structural, PostgreSQL, Alembic, formatting, governance, and CI success.
No real-data execution, cutover, RLS, ADR change, or Client retirement occurred. `latestTaskDone` and
`latestTaskAuthorized` are both `T120`; `inProgressTransitions` is empty; Required ADR #20 remains
unresolved; ADR-0033/0034/0035 are unchanged; T121+ remains unauthorized; PR #209 is unmerged.
T121 architecture is now Done and QA-approved on open PR #211 at `bf33f7eb23ae16db8ea3233d0a963d0c91830d94`.
ADR-0036 is **Proposed**, unchanged by this synchronization: it establishes a mechanical, fail-closed
fresh-installation path, requires disposable development/test data be reset or disposed before
qualifying, and leaves T108-T120 authoritative for non-fresh installations. Ordinary Party enablement
remains blocked until Address finalization/RLS, Party Organization scoping/default-deny RLS/non-owning
runtime role, and Party authorization capabilities exist. Required ADR #20 still governs legacy cutover
and retirement. `latestTaskDone` and `latestTaskAuthorized` are `T121`; transitions are empty; T122+
is unauthorized; ADR-0033/0034/0035 are unchanged; PR #211 is unmerged.
T122 is now Done after independent QA Approved on open PR #213 at QA evidence head
`0bbf9b4f69d007fe2c0cb3255bd58892a086dd16`, which reviewed implementation head
`443655fc899b19abee76e9fd12e29bc4eb9be146` and confirmed authorization ancestry.
The bounded result is Address `organization_id` finalization plus forced, Organization-scoped,
default-deny Address RLS under the non-owning `legal_dms_app` role, with fail-closed migration,
same-Organization integrity, and tenant-GUC isolation evidence. No ownership is inferred or
backfilled. The full-history Alembic offline JSONB rendering problem remains pre-existing and
outside T122; the T122 migration range renders correctly. PR #213 remains open pending the PM
pre-merge gate, not merged. `latestTaskDone` and `latestTaskAuthorized` are both `T122` and
transitions are empty; ADR-0036 remains Proposed, Required ADR #20 remains unresolved,
ADR-0033/0034/0035 are unchanged, and T123+ remains unauthorized.
T123 is now Done after independent QA Approved on open PR #215 at QA evidence head
`d0b9636782c22fa68ceb90c7b4e72ed1d7cf8263`, which reviewed implementation head
`4e7615b7544da7f3503e126137414076dca8491e` and confirmed authorization ancestry.
The bounded result is the Party database RLS backstop: migration `62cadaff2571`
(parent `9c4a7e2d1b5f`) enabling and forcing RLS on `parties` with exactly four
Organization-scoped default-deny policies (`parties_select`/`parties_insert`/
`parties_update`/`parties_delete`) enforced through the non-owning `NOBYPASSRLS`
`legal_dms_app` role, with default-deny behavior, cross-Organization denial,
Party-to-Address same-Organization integrity, T118 owning/admin-path compatibility,
and a symmetric downgrade restoring the pre-T123 no-RLS state. No data migration,
backfill, reset, or destructive operation occurred; the shared development database
remained at `f3b7c9d1e2a4`. QA accepted the T122 fixture pin to `9c4a7e2d1b5f` as
legitimate historical-era testing. The full-history Alembic offline JSONB rendering
limitation (around `9963e15f2752`) remains pre-existing and outside T123; the T123
range is valid. PR #215 remains open pending the PM pre-merge gate, not merged.
`latestTaskDone` and `latestTaskAuthorized` are both `T123` and transitions are
empty; ADR-0036 remains Proposed, Required ADR #20 remains unresolved,
ADR-0033/0034/0035 are unchanged, and T124+ remains unauthorized.
T124 is now Done after independent QA Approved on open PR #217 at QA evidence
head `a96ba0adb5465d6cd5afc2aaf3357ad053fd2308`, which reviewed implementation
head `72fd061729b30345d15a8a98be75634148a33cad` against authorization
baseline `01bae6f2aca43b41612da1ab3a818ddaa482ca06` (PR #216) and confirmed
ancestry. The bounded result is the tenant-safe Party application surface and
fresh-install enablement: migration `1b8f4a9c2e6d` (parent `62cadaff2571`)
seeding `parties:read`/`parties:write`/`parties:delete` with the approved role
grant matrix (18 to 21 permissions, 59 to 71 associations); an
Organization-scoped `/parties` CRUD API where Organization always comes from
the live auth context, `RequirePermission` is enforced per route, T123 Party
RLS is retained as the database-level backstop, and cross-Organization
payloads are rejected; and ADR-0036's live mechanical fresh-install
classifier (11-table per-write predicate excluding `parties`, no
operator/env/config proof) gating ordinary Party writes to FRESH state only,
with LEGACY/MIGRATED ordinary writes remaining blocked. Developer evidence:
full backend suite 724 passed/21 skipped; ruff/black/governance green;
exact-head CI green. QA recorded a process deviation: the retained shared
development database was upgraded `f3b7c9d1e2a4 -> 1b8f4a9c2e6d` without
durable evidence of an explicitly authorized exception to the disposable-DB
testing rule -- technically safe, not a code-correctness defect, and not
rewritten as though prior authorization existed. No Client cutover,
`clients` retirement, `client_id`/bridge removal, MatterParty redesign,
broader Matter/Property/Document migration, ledger/executor redesign, Party
RLS weakening, Address RLS redesign, ADR-0036 acceptance (remains
**Proposed**), Required ADR #20 resolution, frontend Party UI, or T125+ work
occurred. PR #217 remains open pending the PM pre-merge gate, not merged.
`latestTaskDone` and `latestTaskAuthorized` are both `T124` and transitions
are empty; ADR-0036 remains Proposed, Required ADR #20 remains unresolved,
ADR-0033/0034/0035 are unchanged, and T125+ remains unauthorized.
T125 is now Done after PR #219 merged as
`2de16906b163ff9988ea97378af980fe327a70b0`, with authorization/main baseline
`b8796b1e72da203dedb0dc39bb69e572e852a8e0` and final QA-evidence head
`837b9e440e13dc1995b763d751cdf7bbaee89416` as its two parents. Independent QA Approved the
architecture commit `d755cb70603a803c4a348d42e8da508ac1bca9ef`. The bounded result is the
ADR-0037 operational-fresh installation-provenance architecture only. ADR-0037 remains
**Proposed**, ADR-0036 remains **Proposed**, and Required ADR #20 remains unresolved. No
implementation, schema, migration, database mutation, provenance table, classifier/PartyWriteGate
change, bootstrap/install command, Party/Address/Matter API change, ADR acceptance, or future-task
work occurred. `latestTaskDone` and `latestTaskAuthorized` are both `T125`, transitions are empty,
and T126+ remains unauthorized.
**Overall Completion:** Stage 0 + Stage 1 + Stage 2 complete (100% of their scope).
`PROJECT_STATE.json`'s `completion.overallProjectPercent` remains **0% by design** — Stages 0–2 were
infrastructure/framework/schema only, and while Stage 3/4 has since wired a real, working
authentication/authorization/frontend surface to that schema (login, protected routes, RBAC, Electron
secure token storage), no business feature (Matter/Client/Property/Document Management, etc.) has
been built yet. `currentStageScopePercent` is tracked in `PROJECT_STATE.json` as a rough proxy, not a
precisely-weighted estimate. See [PROJECT_STATE.json](../PROJECT_STATE.json) for the machine-readable
version of this file, and [ArchitectureScorecard.md](ArchitectureScorecard.md) for a
capability-by-category architectural maturity dashboard (status, stage, notes, and future
improvements per capability, plus an Overall Architecture Health assessment). For a comprehensive,
point-in-time snapshot of each released version specifically (features, bug fixes, breaking
changes, migration notes, known issues, and what's next), see [releases/](releases/) — the current
release is [releases/v0.3.1.md](releases/v0.3.1.md), itself now stale relative to `T41`–`T78`'s
work; no new release note has been cut since. Before starting the next stage, complete
[templates/PreStageChecklist.md](templates/PreStageChecklist.md) — see
[templates/README.md](templates/README.md) for how it's used.

## Completed — Stage 0 (Project Foundation)

See the Stage 0 section of [CHANGELOG.md](CHANGELOG.md) for full detail. Summary: repo skeleton,
backend (FastAPI + SQLAlchemy + Alembic + Postgres), Electron shell, frontend (React + Vite +
Tailwind + shadcn/ui), tests on both sides (10 backend + 3 frontend at the time), full
documentation. Verified live end-to-end (Postgres + FastAPI + Vite + Electron all running
together).

## Completed — Stage 1 (Core Architecture & Domain Foundation)

The reusable cross-cutting platform every future business feature will plug into. All backend
except for one small frontend addition — see [Architecture.md](Architecture.md) for the full
folder-by-folder breakdown, and [ModuleRegistry.md](ModuleRegistry.md) for a module-by-module
catalog.

### Backend subsystems (all framework, zero business logic)
- Domain foundation: `AggregateRoot`, `DomainEvent`, `Result[T, E]`
- Dependency Injection Container (hand-rolled, `register`/`resolve`/`override`)
- Repository Pattern: `AbstractRepository[T]` port + generic `SqlAlchemyRepository[ModelT]`
- Base Service: CRUD convenience methods (`get_by_id_or_raise`, `list_page`, `create`, `update`,
  `delete`)
- Validation Framework: `Validator[T]` protocol + `validate_all()`
- Pagination / Filtering / Sorting / Search query shapes (`PageRequest`/`PageResult`,
  `SortSpec`/`FilterSpec`/`SearchQuery`)
- Response Wrapper: `ApiResponse[T]` envelope
- Base Controller: generic CRUD router factory (`build_crud_router`) — proven with a test-only
  entity, **never mounted into the real app**
- Event System: `EventBus` port + `InMemoryEventBus`
- Background Job Framework: `Job`/`JobQueue` ports + `InMemoryJobQueue` + `JobRegistry`
- File Storage Abstraction: `FileStorage` port + `LocalFileStorage` (path-traversal-safe)
- Notification Framework (backend): `Notifier` port + `LoggingNotifier`
- Authentication Framework (no login implemented): `AuthenticationProvider`/`CurrentUser` +
  `AnonymousAuthenticationProvider`
- Authorization Framework: `AuthorizationService` + `PermissiveAuthorizationService`
- Audit Logging Framework: `AuditLogger` port + `LoggingAuditLogger` (structured logs, no DB
  table yet — see ADR/0007)
- Search Foundation: `SearchIndex` port + `InMemorySearchIndex`
- Plugin Architecture: `AppModule` protocol + `ModuleRegistry` — global registry empty, proven via
  a throwaway test module
- Workflow Engine: `WorkflowDefinition`/`WorkflowEngine` — proven via a toy state graph, no real
  workflow definitions
- Feature Flags: `FeatureFlagProvider` + `Settings.feature_flags` (env-driven)

### Frontend addition
- `Result<T, E>` discriminated union (mirrors the backend's `Result`)
- Pagination/query TS types (`PageRequest`, `PaginatedResponse<T>`, `SortSpec`, `FilterSpec`,
  `SearchQuery`) mirroring the backend's query framework

### APIs
Unchanged from Stage 0 — `GET /api/v1/health` and `GET /api/v1/version` are still the only routes
in the real shipped app. The CRUD router factory and plugin registry were deliberately proven only
against throwaway test apps, per the charter's "no business functionality" instruction.

### Database
No business tables — same as Stage 0. Only `alembic_version` exists.

### Tests
- Backend: 130 Pytest tests passing (up from 10 at the end of Stage 0).
- Frontend: 9 Vitest/RTL tests passing (up from 3 at the end of Stage 0).
- Both: linters (ruff, black, eslint, prettier) clean throughout.

### Verified live
- Every backend section was smoke-tested against a live FastAPI `TestClient` after landing, and
  the DI-container-touching sections were specifically re-verified against `/api/v1/health` to
  catch any regression.
- The repository pattern's integration tests ran against a real Postgres container (isolated
  test-only schema, never touching the real `Base.metadata`).
- Confirmed the real app's route surface is unchanged from Stage 0 (`/api/v1/health`,
  `/api/v1/version` only) — the CRUD router factory and plugin module proofs stayed entirely
  test-only, as scoped.

## Completed — Stage 2 (Database Architecture & Data Model)

The complete production-ready database schema for the entire eventual application — 49 tables
across 11 domain sections plus a seed-data migration, as pure schema. **No business logic, no UI,
no repositories/services/API routes wired to any of these tables** — that's explicitly future-stage
work. Architecture proposal (overview, ER diagram, table list, relationships, index strategy,
migration strategy, performance considerations, future scalability) presented and approved before
any code was written, per the charter's explicit process. See [Database.md](Database.md) for the
full reference and [ERD.md](ERD.md) for the diagram.

### Schema sections (each its own Alembic migration)
1. Identity & Access — `users`, `roles`, `permissions`, `user_roles`, `role_permissions` (5 tables)
2. Geography — `countries`, `states`, `districts`, `talukas`, `villages` (5 tables)
3. Clients — `addresses`, `clients`, `client_contacts` (3 tables)
4. Properties — `properties`, `property_owners` (2 tables)
5. Matters & Workflow — `matter_types`, `matter_statuses`, `matters`, `workflow_definitions`,
   `workflow_states`, `workflow_history` (6 tables)
6. Documents & File Storage — `document_types`, `document_templates`, `document_variables`,
   `documents`, `document_versions`, `file_storage_records` (5 tables + file storage metadata)
7. Financial — `payment_methods`, `invoices`, `payments`, `receipts` (4 tables)
8. Activity, Audit & Notifications — `activity_logs`, `audit_logs`, `notifications` (3 tables) —
   `audit_logs` reverses [ADR/0007](../ADR/0007-audit-logging-without-database-table.md); see
   [ADR/0009](../ADR/0009-audit-logs-table-reverses-adr-0007.md)
9. Scheduling & Tags — `tasks`, `appointments`, `tags`, `matter_tags` (4 tables)
10. OCR, QR & Backups — `ocr_jobs`, `ocr_results`, `qr_code_records`, `backups` (4 tables) —
    includes a GIN full-text search index on OCR'd text, confirmed working against live Postgres
11. System, Config, AI & Plugins — `application_settings`, `feature_flags`, `ai_requests`,
    `ai_responses`, `plugin_registry`, `background_jobs`, `system_events` (7 tables)
12. Seed lookup data — India + all states/UTs + Gujarat's districts, roles, permissions, matter
    types/statuses, a starter workflow definition, document types, payment methods, default
    application settings and feature flags (no schema changes)

### Design decisions
- Persistence-layer ORM models, not domain entities — [ADR/0008](../ADR/0008-persistence-models-not-domain-entities.md)
- UUID PKs, `TIMESTAMPTZ` timestamps, a project-wide `naming_convention`, `AuditMixin` (soft
  delete + created/updated by + version) on substantive business tables, `OptimisticLockMixin`
  where concurrent edits are realistic, polymorphic `entity_type`+`entity_id` references for
  cross-cutting logs, lookup tables instead of native enums, file *metadata* only (never file
  content) in the database.

### Database
49 tables, 12 migrations, all verified against live Postgres including full chain reversibility
(`alembic downgrade base` → `alembic upgrade head`).

### Tests
- Backend: 216 Pytest tests passing (up from 130 at the end of Stage 1) — schema/migration-level:
  constraints reject invalid data, FKs navigate correctly, soft-delete/audit columns behave as
  expected, seed data row counts match.
- Frontend: unchanged at 9 (Stage 2 was backend-only, no UI).
- Both: linters (ruff, black — including `backend/alembic/versions/`) clean throughout.

### Verified live
- Every migration applied to and downgraded from a live Postgres container, individually and as a
  full chain.
- The GIN full-text search index was verified with an actual `to_tsvector`/`plainto_tsquery` query
  against inserted data, not just migration success.
- Seed data row counts spot-checked directly against the database via `psql`.
- Confirmed the real app's route surface is still unchanged from Stage 0
  (`/api/v1/health`, `/api/v1/version` only) — Stage 2 added zero routes.

## Completed — Command Bus (post-Stage-2 framework addition)

Requested directly by the project owner as standalone framework work, not part of a numbered
stage. A `CommandBus` port (`register`/`dispatch`) plus one in-memory default implementation
(`InMemoryCommandBus`), mirroring `EventBus`'s shape but dispatching a command to exactly one
registered handler and returning a `Result[R, AppError]` instead of fanning out to many
subscribers. Framework only — no business command ships with it. See
[ADR/0010](../ADR/0010-command-bus.md) for the full decision record.

- **Added:** `application/interfaces/command_bus.py` (`Command`, `CommandHandler`, `CommandBus`,
  `CommandBusError`), `infrastructure/commands/in_memory_command_bus.py` (`InMemoryCommandBus`),
  registered in `configure_container()`.
- **Tests:** 7 new Pytest tests (`tests/unit/test_command_bus.py`) — dispatch success, dispatch
  returning a handler failure `Result`, routing by command type, unregistered-dispatch error,
  double-registration error, handler-exception propagation, DI container resolution. Backend total
  216 → 223, all passing. Frontend unchanged at 9.
- **Lint:** ruff and black both clean after the change (one ruff `B024` finding — `Command` as an
  `ABC` with no abstract methods — fixed by making `Command` a plain marker class, not an `ABC`).
- **Verified:** full backend suite (223 tests) re-run after the fix; real app route surface
  unchanged (`/api/v1/health`, `/api/v1/version` only) — this addition touches no route.

## Completed — Query Bus (post-Stage-2 framework addition)

Requested directly by the project owner, resolving [ADR/0010](../ADR/0010-command-bus.md)'s
explicit deferral of a Query bus companion. A `QueryBus` port mirroring `CommandBus`'s shape
exactly (single handler per query type, `Result[R, AppError]` return) plus one in-memory default
implementation (`InMemoryQueryBus`). Framework only — no business query ships with it. See
[ADR/0011](../ADR/0011-query-bus.md).

- **Added:** `application/interfaces/query_bus.py` (`Query`, `QueryHandler`, `QueryBus`,
  `QueryBusError`), `infrastructure/queries/in_memory_query_bus.py` (`InMemoryQueryBus`),
  registered in `configure_container()`.
- **Tests:** 7 new Pytest tests (`tests/unit/test_query_bus.py`) — same coverage shape as
  `test_command_bus.py`: dispatch success, dispatch returning a handler failure `Result`, routing
  by query type, unregistered-dispatch error, double-registration error, handler-exception
  propagation, DI container resolution. Backend total 223 → 230, all passing. Frontend unchanged
  at 9.
- **Lint:** ruff and black both clean — no findings this time (the `B024` lesson from `Command`
  was applied up front: `Query` was written as a plain marker class from the start, not an `ABC`).
- **Verified:** full backend suite (230 tests) passing; real app route surface unchanged
  (`/api/v1/health`, `/api/v1/version` only) — this addition touches no route.

## Completed — Transaction Pipeline (post-Stage-2 framework addition)

Requested directly by the project owner, resolving the "transaction wrapping" trade-off both
[ADR/0010](../ADR/0010-command-bus.md) and [ADR/0011](../ADR/0011-query-bus.md) explicitly
deferred. Three options were presented before writing code (a `CommandBus` decorator, fixing the
unrelated `get_db()` commit bug, or a generic pipeline-behavior chain) — the project owner chose
the decorator. See [ADR/0012](../ADR/0012-transaction-pipeline.md).

- **Added:** `application/interfaces/unit_of_work.py` (`UnitOfWork`, `UnitOfWorkError`),
  `infrastructure/transactions/in_memory_unit_of_work.py` (`InMemoryUnitOfWork`),
  `infrastructure/commands/transaction_pipeline_behavior.py` (`TransactionPipelineBehavior`, a
  `CommandBus` decorator). `UnitOfWork` registered in `configure_container()` as **non-singleton**
  — the first port in this project registered that way, since a unit of work is per-operation
  state, not a shared service. `CommandBus`'s own container registration is unchanged; the
  pipeline is available but not applied by default.
- **Tests:** 13 new Pytest tests — `tests/unit/test_unit_of_work.py` (7: begin/commit/rollback
  lifecycle, double-begin/commit-without-begin/rollback-without-begin errors, DI resolution and
  non-singleton behavior) and `tests/unit/test_transaction_pipeline_behavior.py` (6: commit on
  success, rollback on failure `Result`, rollback-and-reraise on handler exception, `register()`
  delegation to the inner bus, a fresh `UnitOfWork` per dispatch). Backend total 230 → 243, all
  passing. Frontend unchanged at 9.
- **Lint:** ruff and black both clean, no findings.
- **Verified:** full backend suite (243 tests) passing; real app route surface unchanged
  (`/api/v1/health`, `/api/v1/version` only) — this addition touches no route.

## Completed — Caching Abstraction (post-Stage-2 framework addition)

Requested directly by the project owner. Read as a standalone capability (matching this project's
naming convention: "\<Thing\> Abstraction"/"Foundation" for standalone ports vs. "\<Thing\>
Pipeline"/"Bus" for pipeline behaviors and dispatchers) rather than a caching pipeline wrapping
`QueryBus` — the latter would have required deciding a cache-key scheme for arbitrary `Query`
objects, a design question this request's own wording didn't point at. See
[ADR/0013](../ADR/0013-caching-abstraction.md).

- **Added:** `application/interfaces/cache.py` (`Cache` — `get`/`set`/`delete`/`clear`, optional
  per-entry `ttl_seconds`), `infrastructure/cache/in_memory_cache.py` (`InMemoryCache` — dict-
  backed, lazy TTL expiry via `time.monotonic()`), registered as a singleton in
  `configure_container()`. Not wired to `QueryBus`, `CommandBus`, or anywhere else.
- **Tests:** 10 new Pytest tests (`tests/unit/test_cache.py`) — get on a missing key, set-then-get,
  overwrite, delete (present and missing), clear, an entry with no TTL never expiring, an entry
  expiring once its TTL elapses (clock monkeypatched, no real sleep), DI resolution, and singleton
  behavior (two resolves return the same instance — unlike `UnitOfWork`'s deliberate non-singleton
  registration). Backend total 243 → 253, all passing. Frontend unchanged at 9.
- **Lint:** ruff and black both clean, no findings.
- **Verified:** full backend suite (253 tests) passing; real app route surface unchanged
  (`/api/v1/health`, `/api/v1/version` only) — this addition touches no route.

## Completed — Module Manifest Loader (post-Stage-2 framework addition)

Requested directly by the project owner. Closes a gap `ModuleRegistry`'s own docstring left open:
it promised a future module "only needs to register itself; the core app never needs editing
again to pick it up," but nothing actually knew which packages to import to trigger that
registration side effect. See [ADR/0014](../ADR/0014-module-manifest-loader.md).

- **Added:** `infrastructure/modules/manifest.py` (`ModuleManifestEntry`, `ModuleManifest` with
  `from_dict()`, `ModuleManifestLoader` with `load_from_file()`/`import_enabled()`,
  `ModuleManifestError`). Exported from `infrastructure/modules/__init__.py` alongside the
  existing `AppModule`/`ModuleRegistry`. Not wired into `main.py`'s startup and not registered in
  the DI container — no real manifest file exists yet (zero business modules), and reading a file
  has real failure modes not worth adding to the live startup path without one.
- **Tests:** 12 new Pytest tests (`tests/unit/test_module_manifest_loader.py`) — manifest parsing
  (explicit fields, `enabled` defaulting to `true`, empty/missing `modules` key, a missing
  required field raising), file loading (a real `tmp_path` JSON file, a missing file, malformed
  JSON), and import behavior (only enabled entries imported in order via an injectable fake
  importer, a failure raises and stops rather than continuing, plus two tests against the real
  default `importlib.import_module` — one importing a real stdlib module, one wrapping a real
  `ImportError`). Backend total 253 → 265, all passing. Frontend unchanged at 9.
- **Lint:** ruff and black both clean (black auto-wrapped two over-long test lines).
- **Verified:** full backend suite (265 tests) passing; real app route surface unchanged
  (`/api/v1/health`, `/api/v1/version` only) — this addition touches no route.

## Completed — Architecture Health Check (post-Stage-2 framework addition)

Requested directly by the project owner. Resolves `IMPLEMENTATION_QUEUE.md`'s T15/F7 finding
specifically (a startup self-check resolving every DI registration, failing fast on a broken
factory) — not the rest of that still-unapproved Stage 2.5 backlog. See
[ADR/0015](../ADR/0015-architecture-health-check.md).

- **Added:** `infrastructure/di/health_check.py` (`check_container_health()` —
  returns every resolution failure; `assert_container_healthy()` — raises
  `ContainerHealthCheckError` listing them). `Container` gained a small `registered_interfaces()`
  accessor to enumerate what to check.
- **Modified:** `main.py`'s `create_app()` — calls `assert_container_healthy(container)`
  immediately after `configure_container()`. **Unlike every other post-Stage-2 addition, this one
  is wired into the real app's startup path** — every registration it checks was already proven
  working by the existing test suite, so the wiring is low-risk and is what "startup self-check"
  actually requires.
- **Tests:** 7 new Pytest tests (`tests/unit/test_container_health_check.py`) — a healthy
  container reports no failures, a broken factory is caught and reported (not raised) by
  `check_container_health`, multiple broken factories are all reported, an empty container is
  trivially healthy, `assert_container_healthy` raises with the failure detail included in the
  message, and the real `configure_container()` result is confirmed healthy. Backend total 265 →
  272, all passing. Frontend unchanged at 9.
- **Lint:** ruff and black both clean (one import-order fix via `ruff --fix`).
- **Verified:** full backend suite (272 tests) passing, including the existing health-endpoint
  integration tests that import `app.main` and therefore exercise the new startup check on every
  run; real app route surface unchanged (`/api/v1/health`, `/api/v1/version` only).

## Completed — Performance Metrics Service (post-Stage-2 framework addition)

Requested directly by the project owner. Unlike the six additions before it, this didn't map onto
an item already named in an existing ADR trade-off or `IMPLEMENTATION_QUEUE.md` finding — read as
a standalone port via this project's naming convention (`Cache`/`AuthorizationService`-style
"Service", not a `CommandBus`/`QueryBus`-wrapping pipeline, and no new `/metrics` HTTP route,
which would have broken every prior addition's "route surface unchanged" invariant). See
[ADR/0016](../ADR/0016-performance-metrics-service.md).

- **Added:** `application/interfaces/metrics.py` (`MetricsService` — `increment`/`gauge`/
  `record_duration` abstract methods, plus a concrete `timer()` context-manager convenience built
  on `record_duration`), `infrastructure/metrics/logging_metrics_service.py`
  (`LoggingMetricsService` — logs each event as structured JSON to an `app.metrics` channel,
  mirroring `LoggingNotifier`/`LoggingAuditLogger`'s "no real backend yet" posture rather than an
  in-memory-state one). Registered as a singleton in `configure_container()`. Not wired to
  `CommandBus`/`QueryBus` dispatch, HTTP middleware, or any route.
- **Tests:** 8 new Pytest tests (`tests/unit/test_metrics_service.py`) — increment (default and
  explicit value/tags), gauge, record_duration, all logging structured entries; `timer()` records
  a duration on normal exit and also on an exception (re-raising it, not swallowing it); DI
  resolution and singleton behavior. Backend total 272 → 280, all passing. Frontend unchanged at 9.
- **Lint:** ruff and black both clean (two `SIM117` nested-`with` findings in the test file fixed
  by combining context managers).
- **Verified:** full backend suite (280 tests) passing; real app route surface unchanged
  (`/api/v1/health`, `/api/v1/version` only) — this addition touches no route.

## Completed — QA Review Resolution (post-Stage-2 QA fixes)

A QA review ([docs/reviews/Stage_2_5_QA_Review.md](reviews/Stage_2_5_QA_Review.md), dated
2026-08-06) evaluated the seven post-Stage-2 framework additions above against Architecture,
Performance, SOLID, Maintainability, Security, Scalability, Thread Safety, Error Handling, and Code
Duplication. Nine findings (Q1–Q9) were classified in `IMPLEMENTATION_QUEUE.md`: two ("Fix
Immediately") were cheap, safe, and unblocked; the rest are either genuine gaps gated on a
dependency that doesn't exist yet (a real, non-in-memory `UnitOfWork`; the module manifest loader
being wired into `main.py`; an async-requiring implementation being proposed) or already-accepted,
ADR-documented trade-offs.

- **T20 (Q1) — Fixed:** `TransactionPipelineBehavior.dispatch()`
  (`infrastructure/commands/transaction_pipeline_behavior.py`) caught `except Exception`, which
  `asyncio.CancelledError` bypasses since it inherits from `BaseException`, not `Exception` — a
  cancelled dispatch (client disconnect, request timeout, shutdown grace period) would skip
  `rollback()` and leave the unit of work `_active=True`. Widened to `except BaseException`, with
  an inline comment explaining why, and still re-raises after rollback so cancellation propagates
  correctly. Two new regression tests added: `test_dispatch_rolls_back_and_reraises_on_cancellation`
  and `test_dispatch_rolls_back_and_reraises_on_a_base_exception`.
- **T21 (Q8) — Fixed:** `MetricsService`/`LoggingMetricsService` gained a docstring line each
  stating `tags` values are logged verbatim with no redaction, so a future caller doesn't tag a
  metric with sensitive data (an email, a document ID) expecting it to be scrubbed. No test changes
  needed — the existing `test_increment_accepts_an_explicit_value_and_tags` already asserted tags
  pass through unmodified.
- **Tests:** 2 new (`test_transaction_pipeline_behavior.py` grew from 5 to 7). Backend total 280 →
  **282**. Frontend unchanged at 9. Full unit suite (175/175) re-run and passing; the 107
  integration tests could not be re-run in this environment (no local Postgres/Docker available) —
  neither change touches persistence, so this is a documentation/verification gap, not a suspected
  regression.
- **Lint:** ruff and black both clean project-wide after the change.
- **Deferred, not yet actionable:** Q2, Q3, Q7 (need a real, non-in-memory `UnitOfWork` to exist
  first), Q5 (needs `ModuleManifestLoader` actually wired into `main.py`), Q9 (needs a real
  async-requiring `Cache`/`CommandBus` implementation to be proposed).
- **Accepted trade-offs, no action planned:** Q4 (`InMemoryCommandBus`/`InMemoryQueryBus`/
  `InMemoryEventBus` structural duplication — [ADR/0011](../ADR/0011-query-bus.md) already weighed
  and rejected a shared base class), Q6 (`InMemoryCache`'s lazy-only TTL expiry —
  [ADR/0013](../ADR/0013-caching-abstraction.md) already accepts this until a real caller exists).
- **Verified:** fixes match the findings; full unit suite plus the two new tests pass; no regression
  in the three pre-existing `test_transaction_pipeline_behavior.py` tests; real app route surface
  unchanged (`/api/v1/health`, `/api/v1/version` only) — neither fix touches a route.

## Completed — GitHub Actions CI (Stage 2.7)

A mini-stage, distinct from the numbered Stage 0–2 sequence and the post-Stage-2 framework
additions: continuous integration validating every push and pull request. Plan reviewed and
approved by the project owner with seven explicit decisions before implementation started. See
[ADR/0017](../ADR/0017-github-actions-ci.md) for the full design record and
`IMPLEMENTATION_QUEUE.md`'s Stage 2.7 section for the task-by-task detail.

- **Added:** `.github/workflows/backend.yml` (ruff, black --check, `pytest tests/unit`, an
  application-import/boot smoke test — Python 3.14), `.github/workflows/frontend.yml` (eslint,
  prettier --check, vitest — Node 24.13.1/npm 11.11.1), `.github/workflows/release.yml` (build
  verification only — compiles Electron TS + builds the frontend; **not** a packaging or deployment
  pipeline despite the name). All three trigger on push to `main`/`feature/**`/`hotfix/**`/
  `release/**` and on pull requests targeting `main`, with per-workflow `concurrency` cancellation
  and least-privilege `permissions: contents: read`. `engines` added to both `package.json` files
  (`node: >=24.13.1`, `npm: >=11.11.1`), which also raises the project's previously
  documentation-only "Node 20+" floor to match. `ADR/0017-github-actions-ci.md` records the full
  decision set, including three items the project owner explicitly deferred (integration tests,
  Docker, deployment) and three recorded as backlog-only, not implemented
  (Dependabot, a PR template, issue templates — `IMPLEMENTATION_QUEUE.md` T38–T40).
- **Verified locally before finalizing:** `ruff check`, `black --check`, `pytest tests/unit`
  (175 passed), and the import smoke test all confirmed passing in the actual `backend/` project;
  the frontend's dual-reporter vitest invocation confirmed working (9 passed); the root `npm run
  build` confirmed producing both `frontend/dist/` and `dist-electron/`.
- **Commit-prep verification (2026-08-06, same day):** re-ran the full backend suite with no path
  restriction — Postgres was reachable this time (`docker ps` confirmed `legal_dms_postgres`
  healthy, unlike the prior QA Review Resolution session) — **282/282 passed, zero skipped**,
  confirming the 107 integration tests (untouched by this stage) are still green. Re-ran backend
  ruff/black and frontend eslint/prettier: both clean (frontend's 3 pre-existing react-refresh
  warnings are the same expected ones, 0 errors). Re-ran frontend's full test script: 9/9. Confirmed
  via `git status --ignored` that no temporary/generated files (`dist/`, `dist-electron/`,
  `test-results/`, caches) are staged or untracked-and-uningored. **Still not verified: a real
  GitHub Actions run.** That requires a commit and push, which needs an explicit go-ahead per this
  project's standing rule on confirm-first git actions — tracked as the one open item
  (`IMPLEMENTATION_QUEUE.md` T35).
- **Lint:** N/A — no application code changed; only workflow YAML, two `package.json` `engines`
  additions, one new ADR, and documentation.

## Completed — Stage 3 (Authentication & Authorization) and Stage 4 (Frontend & Electron Fundamentals)

**Added by this Documentation Manager pass (2026-08-21) — this file had never covered Stage 3/4 at
all before now.** Full task-by-task technical detail lives in `docs/ImplementationLog/Stage3/` and
`docs/ImplementationLog/Stage4/`, and in `docs/AI_HANDOVER.md`'s `T52`–`T82` narrative — not
duplicated here; this section is the status-dashboard-level summary this file exists to give.

- **Backend authentication/authorization (`T41`–`T68`), done and merged.** Real
  `JwtAuthenticationProvider`/`RbacAuthorizationService` (Stage 1's `AuthenticationProvider`/
  `AuthorizationService` ports), `RequirePermission(...)`, the full `/api/v1/auth/*` and
  `/api/v1/users*` route surface, `role_permissions` seeded against a 59-entry authorized matrix, and
  a first-admin bootstrap CLI. Architecture approved D1–D7 ([ADR-0018](../ADR/0018-authentication-authorization-architecture.md),
  [0019](../ADR/0019-authentication-provider-interface-change.md),
  [0020](../ADR/0020-session-commit-rollback-policy.md)).
- **Frontend/Electron fundamentals (`T69`–`T78`), done and merged.** `httpClient.ts` gained
  `post`/`put`/`delete`, structured error parsing, a global `Authorization` header, and global 401
  handling; `AuthProvider`/`auth.ts` (React auth state); Electron `safeStorage`-backed secure token
  storage with IPC exposure ([ADR-0018](../ADR/0018-authentication-authorization-architecture.md)
  D6); a login page/form; a protected-route wrapper; current-user display + logout in the app header;
  `/docs`/`/redoc` gated to development only; CORS `allow_methods`/`allow_headers` tightened from
  wildcards.
- **`T79` (verification-only) — closed by the Project Owner as `INCOMPLETE / NOT VERIFIED`, not a
  PASS (2026-08-20).** Backend suite, frontend suite, lint/format, and a full live browser
  authentication walkthrough all confirmed passing. **The Electron-specific session-persistence
  requirement (ADR-0018 D6) remains unverified** — this environment can drive a browser tab but not
  an actual Electron `BrowserWindow`. A related static-analysis finding was recorded, not fixed:
  `electron/preload.ts`'s `getRefreshToken()` is not currently surfaced to `AuthProvider.tsx`, so no
  session-restoration-on-load path exists yet even inside Electron.
- **`T82` — Electron-runtime live smoke verification — reserved, scoped, NOT authorized, NOT
  started.** The direct follow-up to `T79`'s unresolved item. A Project Manager cycle must record
  explicit authorization before any implementation begins.
- **`T76`** was formally resolved as **Superseded/Distributed** (its intended test coverage was
  completed cumulatively within `T72`–`T75`), not implemented as its own task.

## Completed — Governance & Required-ADR Resolution Series (T86–T103)

**Added by a Documentation Manager pass (2026-08-28) covering `T83`–`T96`; extended by a further pass
(2026-08-31, GitHub Issue #167) covering `T97`'s actual completion and `T98`–`T103`, none of which
had been reflected here before now.** Full task-by-task detail lives in each task's own
`IMPLEMENTATION_QUEUE.md` row and, for `T87` onward, in `docs/reviews/T<N>_Software_Architect_Report.md` /
`T<N>_Implementation_Report.md` / `T<N>_QA_Review.md`; not duplicated here.

- **`T83`–`T85`, done and merged.** Closed out `T82`'s live-confirmed Electron session-restoration
  `FAIL` finding: `T83` provisioned a local Administrator test account; `T84` implemented the
  session-restoration fix; `T85` fixed an Electron preload-script load failure that was blocking
  `T84`'s own native verification.
- **`T86`, done and merged.** Adopted `docs/Legal_DMS — Domain Model & Functional Specification.md`
  as the governed pre-Stage-4 planning baseline — the source of the specification's own §21 Required
  ADR list that `T87`–`T94` then resolve against.
- **`T87`–`T94`, each done and merged.** Drafted and resolved eight of the specification's twenty
  Required ADRs — `ADR/0021` (#1 Organization tenant boundary + #19 tenant isolation), `ADR/0022`
  (#18 authorization architecture), `ADR/0023` (#2 Party vs Client), `ADR/0024` (#3/#4/#6
  Property/Land/Property-Unit boundary + record-reference architecture), `ADR/0025` (#5 Revenue vs
  City-Survey field architecture), `ADR/0026` (#7 Scheme hierarchy), `ADR/0027` (#9 File numbering
  algorithm and concurrency strategy), `ADR/0028` (#13 Financial ledger boundary). Nine Required
  ADRs (`#8`, `#10`, `#11`, `#12`, `#14`–`#17`, `#20`) remain unresolved — see
  `PROJECT_STATE.json`'s `governanceLedger.unresolvedRequiredADRs` for the current, mechanically
  computed list, not a hand-maintained one. Each task followed its own three-PR governance lifecycle
  (authorization PR → architecture/implementation+QA PR → governance closeout PR) — `T94`'s own
  history additionally surfaced and self-corrected two real governance defects (authorization
  recorded only conversationally at first; an architecture branch that had not actually incorporated
  its own later-recorded authorization), both independently caught by a Project Manager pre-merge
  gate rather than assumed clean.
- **`T95`, done and merged.** Context & Governance Hardening — added `scripts/governance_validate.py`
  (a stdlib-only checker for duplicate task IDs, missing authorization/QA evidence, ADR numbering and
  duplicate-resolution integrity, dangling ADR references, and `PROJECT_STATE.json` `governanceLedger`
  drift), its 35-test suite, a `governance.yml` CI workflow, an additive `governanceLedger` field on
  this project's `PROJECT_STATE.json`, and a new "Governance & Task Authorization Model" section in
  `AI_BOOTSTRAP.md`. See `docs/GOVERNANCE_VALIDATION.md` for exactly what it does and does not check.
- **`T96`, done and merged.** Codified the three-PR lifecycle `T87`–`T95` had already been following
  into `PROJECT_WORKFLOW.md` §3.1, and extended `docs/prompts/ProjectManager.md` §9's pre-merge gate
  with a required authorization-commit-ancestry check (`git merge-base --is-ancestor`), grounded
  explicitly in `T94`'s own incident history.
- **`T97`, done and merged.** Documentation Manager Sync: refreshed this file, `PROJECT_STATE.json`'s
  top-level snapshot, `docs/AI_HANDOVER.md`, `docs/SessionReport.md`, and `PROJECT_WORKFLOW.md` §6's
  CI-workflow count through the completed `T86`–`T96` series. Merged same day as authorized: PR #145
  (merge `c9438de`), QA Approved with comments.
- **`T98`, done and merged.** Drafted and resolved Required ADR #14 (Activity vs Audit architecture)
  as `ADR/0029` — `activity_logs` (descriptive business history) and `audit_logs` (immutable
  accountability) confirmed as two permanently distinct, non-substitutable mechanisms; discloses,
  without resolving, that neither table carries an `organization_id` column relative to `ADR/0021`'s
  mandate. QA Approved with comments. Merged PR #148 (merge `acd5125`).
- **`T99`, done and merged.** Governance Lifecycle / Required-CI Compatibility Remediation — added
  `governanceLedger.inProgressTransitions`, letting one legitimate, mechanically-verified in-progress
  Required-ADR transition pass the required Governance CI gate while genuine stale or unauthorized
  drift still fails it. 14 new validator tests (49 total). QA Approved with comments. Merged PR #151
  (merge `0387440d`).
- **`T100`, done and merged.** Generalized `T99`'s own frontier-equality constraint after it was
  found to wrongly reject `T98`'s still-open PR once `T99` itself closed out first — a design gap in
  the delivered mechanism, not a defect in `T98`. QA Approved. Merged PR #154 (merge `3768348e`).
  **Disclosed, unresolved as its own tracked governance item:** this closeout found the
  `main-required-ci` ruleset's `required_approving_review_count` had drifted from `1` to `0`, and
  three required status-check names no longer matched the workflows' actual job names — neither
  change caused by `T100`. `T101`'s and `T102`'s own QA records each independently re-fetched the
  ruleset and found `required_approving_review_count` back at `1` and the names matching, but no task
  ever formally closed this out as its own finding — see `PROJECT_STATE.json`'s `currentStage.note`
  for the fuller, dated disclosure.
- **`T101`, done and merged.** Drafted and resolved Required ADR #8 (Matter-vs-File lifecycle/identity
  boundary) as `ADR/0030` — the governed specification's layered Matter→File model confirmed to
  control over `docs/BusinessRequirementsPlan.md`'s superseded File-Number-as-Matter-identity
  language; Required ADR #10/#12/#20 disclosed as coupled-but-unresolved. Merged PR #158 (merge
  `e7a29fae`) on a single collaborator approval **before** a formal QA Decision document existed — a
  disclosed departure from the required pre-merge QA-persistence discipline every `T80`–`T100` task
  had followed. QA Decision Approved with comments recorded post-merge, independently re-verified
  against the actual merged `main` HEAD.
- **`T102`, done and merged.** Drafted and resolved User↔Organization membership, onboarding, and
  tenant-context semantics as `ADR/0031` — a gap the specification's own twenty-item Required-ADR list
  never named (it sits between already-resolved #1 and #18): one-to-one optional cardinality, first-
  Organization creation folded into the existing `bootstrap-admin` CLI, a nullable
  `users.organization_id` FK orthogonal to `UserRole`, and tenant-context resolution via a live
  database read, never a JWT claim. **`ADR/0031` §15 and this task's own authorization both explicitly
  state that accepting the ADR does not itself authorize Organization/Tenant Core implementation.**
  Same disclosed post-merge QA-sequencing departure as `T101`. Merged PR #162 (merge `8038e66d`).
- **`T103`, done and merged.** Drafted and resolved the narrow User/Organization
  pre-existing-data-reconciliation slice of Required ADR #20 as `ADR/0032` — how the one pre-`ADR-0031`
  `User` row (the `T83`-bootstrapped Administrator) is reconciled with the new `organization_id`
  column during migration. Explicitly does **not** claim to resolve the specification's own §21
  migration-strategy planning-list item as a whole — Required ADR #10, #11, #12, #15, #16, #17, and
  the general #20 remain unresolved. This task's own authorization required the QA Decision to be
  persisted and independently re-verified **before** merge, restoring the discipline `T101`/`T102`
  had departed from — and it was (review submitted 2026-08-31T12:17:44Z, merge 12:24:50Z). QA
  Decision Accepted with comments. Merged PR #165 (merge `106f2e9`); governance closeout PR #166
  (merge `d94d219`).

`T82` itself remains exactly as recorded above: closed **`FAIL`**, QA-Approved-with-comments, not
silently reinterpreted by this pass. No follow-up implementation task beyond `T84`/`T85` has been
authorized for it. **No Organization/Tenant Core implementation task, branch, or PR exists anywhere
in this repository as of this update** — that slice remains gated behind a fresh Project
Manager/Control Tower re-assessment against `ADR/0031`/`ADR/0032`, not authorized or implied by any
task recorded above.

## Pending

**Update (2026-08-31, Documentation Manager, post-`T103` synchronization, GitHub Issue #167):** the
two paragraphs below are now both stale — see "Completed — Governance & Required-ADR Resolution
Series (`T86`–`T103`)" above for what happened since. As of this update: `T97` is Done (not merely
authorized); a follow-up implementation task for `T82`'s Electron session-restoration finding remains
**not authorized** (unchanged since 2026-08-21 — no task has targeted it since `T84`/`T85` closed the
finding out); seven Required ADRs (`#10`, `#11`, `#12`, `#15`, `#16`, `#17`, `#20`, down from nine —
`#8` and `#14` resolved by `T101`/`T98`) remain unresolved per `PROJECT_STATE.json`'s
`governanceLedger` — not "pending" in the authorized-task sense, since no task currently targets any
of them; and Organization/Tenant Core implementation remains **not authorized**, gated behind a fresh
Project Manager/Control Tower re-assessment against `ADR/0031`/`ADR/0032` per `ADR/0031` §15 — no
such re-assessment, and no `T104`, has been performed or created by this synchronization pass.

**Update (2026-08-21):** Stage 3/4 are no longer undefined — see "Completed — Stage 3 ... and Stage
4 ..." above. The one genuinely open item is `T82` (Electron-runtime live smoke verification),
reserved and scoped but **not authorized**. The paragraph below is preserved as historical context
from before Stage 3 was scoped, not current reality.

Original note: Stage 3 is undefined — nothing planned in detail. See [Roadmap.md](Roadmap.md).
Separately, Stage 2.7's one open item (a live GitHub Actions run, `IMPLEMENTATION_QUEUE.md` T35)
needs an explicit go-ahead to commit and push before it can be marked fully done. **That item has
since closed** — a real GitHub Actions run has been observed, satisfying the original concern.
**Correction (2026-08-21, Independent Technical Verifier rework):** the previous wording here
("CI has run repeatedly, green, on every `T41`+ pull request since") overstated what this
documentation-only pass actually established. Individual `T41`+ implementation-log entries and QA
Decisions cite specific green CI runs for their own batches (see each batch's own phase log), and
`IMPLEMENTATION_QUEUE.md`/`docs/ImplementationLog/` batches reference passing suites, but this file
does not independently verify, and does not claim, that every single `T41`+ pull request completed
every CI workflow successfully — that would require re-querying `gh pr checks`/`gh api` for each of
the dozens of PRs individually, which was not done. Subsequent PRs have had CI activity since Stage
2.7 closed; this document does not establish that every `T41`+ PR completed every CI workflow
successfully.

## Blocked Tasks

None.

## Known Issues

The two open items carried since Stage 0, both still documented in [KnownIssues.md](KnownIssues.md):
1. shadcn/ui CLI (`init`/`add`) is broken on this Windows environment — worked around by hand
   authoring components.
2. `react-router-dom` has one open high-severity advisory not applicable to this project's usage
   (no RSC/framework mode) — accepted, documented, to be re-checked on upgrade.

**Plus one added during `T79`'s follow-up verification pass (2026-08-20), tracked in
`PROJECT_STATE.json`'s `knownIssues` as `electron-refresh-token-not-consumed`:**
3. `electron/preload.ts` exposes `getRefreshToken()` to the renderer, but
   `frontend/src/infrastructure/ipc/ipcBridge.ts`'s `ElectronApi` wrapper doesn't surface it, and
   `AuthProvider.tsx` has no mount-time effect calling it — no session-restoration-on-load path
   exists yet, even inside Electron. Static-analysis observation only, not independently
   runtime-verified, not fixed. Directly relevant to `T82`.

## Technical Debt

None accrued in Stages 0–2 proper. Every Stage 1 port still has exactly one minimal, tested default
implementation. Stage 2's schema is deliberately generic/minimal in the two areas with no consuming
feature yet (`ai_requests`/`ai_responses`, `plugin_registry`) rather than guessed at — documented as
intentionally incomplete, not a gap. The five polymorphic `entity_type`+`entity_id` tables trade
away DB-level referential integrity on that column by design — see [ERD.md](ERD.md) for the
accepted trade-off.

Five QA findings from the post-Stage-2 review remain open by design, gated on a dependency that
doesn't exist yet — not forgotten, tracked in `IMPLEMENTATION_QUEUE.md`: Q2/Q3/Q7 (transaction
pipeline correctness against a real, non-in-memory `UnitOfWork`; `Container.resolve()`'s
check-then-act race off the event-loop thread; `rollback()`-raises-during-handling edge case), Q5
(`ModuleManifestLoader`'s unrestricted dynamic import needs an allowlist once it's wired into
`main.py`), Q9 (`Container.resolve()` has no async-factory support, needed only once a real
async-requiring implementation is proposed). Two more (Q4, Q6) are accepted, ADR-documented
trade-offs, not debt.

## Upcoming Stage

**Update (2026-08-21):** the paragraph below predates Stage 3 being scoped and is preserved as
historical context, not current reality. The actual next item is `T82` (Electron-runtime live smoke
verification) — reserved and scoped in `IMPLEMENTATION_QUEUE.md`, **not authorized**. Beyond that,
the business-feature scope this project was originally chartered for (Matter/Client/Property
Management, Document Automation, OCR, QR, Search, Reports, Payments, AI — see
[Roadmap.md](Roadmap.md)'s "Stage 4+ — Not yet planned" table) remains entirely unscoped and requires
explicit project-owner direction before any of it starts.

Original note: Stage 3 is undefined — no plan exists yet. Whoever picks this up next should get
explicit direction from the user before choosing what Stage 3 covers (see
[AI_HANDOVER.md](AI_HANDOVER.md) and [AI_BOOTSTRAP.md](../AI_BOOTSTRAP.md)). The schema is now ready
for a feature to be wired to it — that's a strong candidate for what Stage 3 becomes, but confirm
rather than assume. Once scoped and approved, complete
[templates/PreStageChecklist.md](templates/PreStageChecklist.md) before writing any Stage 3 code —
see [templates/README.md](templates/README.md).

## Estimated Remaining Work

Not estimable yet — the full feature scope (Matter/Client/Property Management, Document
Automation, OCR, QR, Search, Reports, Payments, AI, Authentication) has no sizing or sequencing
decided. The database schema those features will sit on is now complete.

T126 is now Done in the ordinary pre-merge §3 synchronization sense after independent QA **Approved** on open PR #222. Reviewed implementation `929709e47ff85606fda5eb765b02d21bdac853da` introduced migration `c4e7a9b2d6f1` (parent `1b8f4a9c2e6d`) and the bounded ADR-0037 persistence/bootstrap foundation: immutable installation provenance, guarded fresh-install birth, one privileged serialized operational-fresh transition, runtime read-only provenance projection, revision/contract binding, a complete bootstrap predicate including `parties`, contradiction checks, and idempotent concurrent handling. QA evidence `7a97f7dd9fc832f0a3817d228735d6c14d4dbdc4` was the verified pre-sync PR head; exact-head Backend, Frontend, Governance, and Release workflows were successful. The retained/shared development database remained unchanged and unproven and the prior T124 process deviation remains preserved. The T124 classifier and `PartyWriteGate` remain unchanged; no production `OPERATIONAL_FRESH` classifier/precedence integration, Party eligibility change, Address CRUD, Matter/MatterParty/Property/File work, migrated Party-write enablement, Client cutover/retirement, Required ADR #20 resolution, ADR-0036/0037 acceptance, frontend work, or T127+ occurred. `latestTaskDone`/`latestTaskAuthorized` are `T126`, transitions are empty, ADR-0037/ADR-0036 remain Proposed, Required ADR #20 remains unresolved, and PR #222 remains open/unmerged awaiting the PM pre-merge gate.

T127 is now Done in the ordinary pre-merge §3 synchronization sense after independent QA **Approved** on open PR #224. Reviewed implementation `9ccea514d3a394a6718ad6fb28ab4ff530850f6d` makes T126 provenance authoritative for runtime operational-fresh classification: `OPERATIONAL_FRESH`, `MIGRATED`, `LEGACY_WITH_BUSINESS_DATA`, and `UNPROVEN` replace T124's `FRESH` runtime entitlement, and ordinary Party writes cross the installation-state gate only for valid `OPERATIONAL_FRESH`. Supported provenance is `adr-0037.v1` at revision `c4e7a9b2d6f1`; Party/Address growth preserves valid operational-fresh, while empty pre-T126 upgrades and Party-only T124-era databases are not grandfathered. Complete T118 migration remains `MIGRATED` and denied for ordinary Party writes pending Required ADR #20; legacy, partial, malformed, contradictory, unsupported and read-error states fail closed. Transaction-scoped SHARE locks on `clients` and `client_party_migration_ledger`, held across classification and Party mutation in the same request transaction, protect the relevant migration-evidence TOCTOU window without constituting a universal/global lock. No migration was created; runtime provenance remains read-only and Party/Address RLS, Organization scoping, ADR-0022 permissions and T118 separation remain intact. QA evidence `cbc5698a76e020fe2d2408c50ff8043d5c116e40` changed only the canonical QA review. `latestTaskDone`/`latestTaskAuthorized` are `T127`, transitions empty, ADR-0037/ADR-0036 Proposed, Required ADR #20 unresolved, T128+ unauthorized, and PR #224 remains open/unmerged awaiting the pre-merge gate.

T128 is now Done after architecture+QA PR #226 merged as `042ca4a78115ae15794db60841d8bd3740143132`. Independent QA **Approved** architecture commit `e212b4dcd3bb327322394975955e5108d5b48b89`; QA evidence is `9c1b54aaecc8bd590dc631cd7d9b1f564211539f`. ADR-0038 establishes the deterministic, derived, provenance-aware, fail-closed and non-authoritative Self-Context projection contract and remains **Proposed**; ADR-0037 and ADR-0036 remain Proposed, and Required ADR #20 remains unresolved. T128 produced architecture only: no compiler, Current Context Manifest, Task Context Package, renderer, bootstrap/CI integration, stale-document cleanup, governance-file restructuring, application/schema/migration/database work, or T129+ implementation exists. The recommended **Deterministic Current-Context Manifest Foundation** is a future candidate only and remains unnumbered and unauthorized. `latestTaskDone` and `latestTaskAuthorized` are both `T128`; transitions are empty and T129+ remains unauthorized.

T129 is now Done in the ordinary pre-merge §3 synchronization sense after independent QA **Approved** on open PR #229. Reviewed implementation/remediation `706e1fc9bf9332fa527e9665a58eff55878c0d0f` implements ADR-0038 Layer A only: an offline/on-demand deterministic Current Context Manifest with versioned context/derivation/source-set contracts, stable repository/local source-commit identity, shared governance-validator semantics, governance-frontier/Required-ADR/ADR-status projection, ledger cross-checking, deterministic structured diagnostics, dirty-authoritative-source protection, fail-closed conflict handling and canonical deterministic JSON. QA evidence `898c41a51fe19d54d0cbfb613fbb61383d6b22ed` changed only the independent review and records 7 focused manifest tests, 51 governance-regression tests, validator 0 warnings/0 errors, deterministic output and negative fail-closed coverage. Authoritative repository evidence remains authoritative; the generated manifest is disposable/non-authoritative and cannot authorize/select tasks, change ADR state, approve QA, supersede queue/state/ADRs/Git or become a second governance ledger. Layer B Task Context Packages, Layer C rendering, bootstrap/agent routing, stale-context cleanup, governance restructuring, CI freshness and automatic decisions remain deferred. No database/schema/migration or domain capability work occurred; migration frontier remains `c4e7a9b2d6f1`. `latestTaskDone`/`latestTaskAuthorized` are `T129`, transitions empty, ADR-0038/0037/0036 Proposed, unresolved Required ADRs `[10, 11, 12, 15, 16, 17, 20]`, T130+ unauthorized, and PR #229 remains open/unmerged awaiting final merge gates.


**Update (2026-09-22, Documentation Manager, T130 post-QA synchronization on PR #231):** Independent QA **Approved** exact reviewed implementation `64573ea053e62b1b82497f5d5c17f7d847104251`; QA-only evidence `5a641298f07d42f8c92251e612c60a1b7e71fa50` was the verified pre-sync PR head and changed only `docs/reviews/T130_QA_Review.md`. T130 is Done in the ordinary pre-merge §3 synchronization sense. The bounded result is authenticated Organization-scoped Address list/get/create/update/delete with pagination, tenant invisibility, existing-geography reference validation and controlled referenced-delete conflict behavior, backed by forced Organization-GUC Address RLS and the non-owning NOBYPASSRLS runtime role. Migration `5d8a3f2e9c6b` (parent `c4e7a9b2d6f1`) seeds `addresses:read`/`write`/`delete`, expands permissions 21→24 and role grants 71→83, and extends the established supported provenance/runtime revision to the new migration head while restoring the parent revision on downgrade; ADR-0037 semantics are unchanged. Party same-Organization Address compatibility remains valid, cross-Organization references remain rejected, PartyWriteGate was not generalized, and legitimate Address growth preserves `OPERATIONAL_FRESH`. QA evidence records 25 Address API, 2 migration, 12 Address-RLS, 13 classifier, 8 operational-fresh/T66, 26 Party-RLS tests, plus 84/84 affected auditing tests passing in isolation; the developer-observed six broad-run caplog/async-loop failures in unchanged auth/user modules are preserved as a non-T130 flake observation rather than rewritten as a full-suite pass. Required ADR #20 remains unresolved; ADR-0038/0037/0036 remain Proposed; unresolved Required ADRs remain `[10, 11, 12, 15, 16, 17, 20]`; `latestTaskDone`/`latestTaskAuthorized` are `T130`, transitions empty, T131+ unauthorized, and PR #231 remains open/unmerged pending final merge gates.

T131 is now Done after architecture+QA PR #233 merged as `8c33c7e28b8a9e5d7cc5de92be2cdccc7e98c6d4`, following authorization PR #232 merge `0933dc765693a62499be78d68256e8ea70988f71`. Independent QA **Approved** exact reviewed architecture head `7912cd73388f08e5cade9357827900dffec347e9`; QA evidence/final PR head is `fca91f02c071ebfc1bfce0c81d070816ce95a2f8`. ADR-0039 defines a staged canonical switch with compatibility shadows and remains **Proposed**: Party is canonical reusable identity for target/new business; Client remains transitional compatibility/source/evidence; operational-fresh workflows must not manufacture Client identity or dual-write Party back to Client; Matter client participation and Property ownership move toward MatterParty/Party relationships in later separately authorized slices. PartyWriteGate remains unchanged, MIGRATED alone does not authorize ordinary Party writes, tenant/RLS prerequisites precede applicable write surfaces, and destructive legacy retirement remains separately authorized. T131 implemented no cutover, schema, migration, runtime, application or database change. Required ADR #20 remains unresolved because broader current-schema migration seams remain; unresolved Required ADRs are `[10, 11, 12, 15, 16, 17, 20]`. ADR-0036/0037/0038/0039 remain Proposed. The recommended **Matter/Property Tenant-and-Canonical-Relationship Schema Foundation** is an unnumbered, unauthorized future candidate. `latestTaskDone`/`latestTaskAuthorized` are `T131`, transitions are empty, and T132+ remains unauthorized.


**Update (2026-09-22, Documentation Manager, T132 post-QA synchronization on PR #236):** T132 completed a genuine two-pass QA lifecycle. Initial implementation head `93b4d7e6791f7a9b9042b1ebfd1a57ffd70386fc` received **Rework required** at QA evidence `d2f2b076f0766ba843780d2576809664658ca526` for a stale `5d8a3f2e9c6b` operational-fresh test expectation. Bounded remediation `40b6c95789352614206fd1eb66361b170aff2923` changed only that test expectation to `7f1b9c3d4a2e`; production code and migration were unchanged. Independent re-QA **Approved** that remediation; final QA evidence `34e7ce2765792ef983e26d7fcbbd64c6a8fdb8fa` records 66/66 targeted regressions passing, ruff/black/diff clean, and exact-head Backend/Frontend/Governance/Release CI green. T132 is Done in the ordinary pre-merge §3 synchronization sense: migration `7f1b9c3d4a2e` finalizes Matter tenant ownership using deterministic Client-derived evidence only, keeps nullable legacy `Matter.client_id` compatibility/evidence, preserves Party-canonical MatterParty composition, forces Organization-GUC RLS on Matter/MatterParty, and advances operational-fresh supported revision. No full-backend-suite re-QA claim, Matter CRUD, Property change, Client retirement, PartyWriteGate change, Required ADR resolution, ADR status change, or T133+ work is claimed. Required ADR #20 remains unresolved; ADR-0039 remains Proposed; `latestTaskDone/latestTaskAuthorized = T132`; transitions empty; T133+ unauthorized; PR #236 remains open/unmerged pending final merge gates.

### T133 — Property Tenant and Party-Canonical Ownership Schema Foundation (post-QA synchronized, pre-merge)

Independent QA Approved implementation head `3f0f75eb7859ab14158daf3d3edf587ad307c89e`; QA evidence commit `5dd014365b046512ce598d1d472e8aa0f541a677` changes only the Phase28 QA artifact. T133 is recorded Done under the ordinary pre-merge §3 synchronization convention, with latest Done/authorized both T133 and no in-progress transitions. PR #238 remains open/unmerged pending final Git/CI merge verification. Required ADR #20 remains unresolved; ADR-0036/0037/0038/0039 remain Proposed; T134+ remains unauthorized.


### T134 — Party-Canonical Matter Application Surface and Organization-Scoped CRUD (post-QA synchronized, pre-merge)

Independent QA **Approved** implementation head `801a4682f30dbab9804b9d35f30dedd2f90fbcf9`. Original QA evidence `b452e3cb09a1d75bb34fb3003aaef77bbadf4c5d` and correction `a8540831d09e51047a1d49e1f28958ca31f88db9` are documentation-only descendants in `docs/ImplementationLog/Stage3/Phase29.md`; the corrected record preserves the independent provenance and evidence. T134 is Done under the ordinary pre-merge §3 synchronization convention. The bounded result is Organization-scoped Matter list/get/create/update using existing `matters:read`/`matters:write`, with canonical `Party → MatterParty(role="client") → Matter` creation, new `Matter.client_id = NULL`, zero Client manufacture, tenant-safe participant validation and legacy Client-linked Matter read compatibility. Participant mutation, Matter DELETE, Property/MatterProperty, classification/work-type redesign, File/Document transition, Enquiry/Quotation and Client retirement remain outside T134. No migration occurred; Alembic frontier remains `9e6a4b2c8d1f`; provenance/classifier/supported revision and PartyWriteGate are unchanged. Required ADR #20 remains unresolved; ADR-0036/0037/0038/0039 remain Proposed; latest Done/Authorized are T134, transitions are empty, T135+ remains unauthorized, and PR #240 remains open/unmerged pending final Git/CI verification.


**Update (2026-09-24, Documentation Manager, T135 post-QA synchronization on PR #242):** Independent QA **Approved** exact implementation `2e9226464a5497dc52487f0a333cb4c4c183e9bc`; QA evidence `5ea6f2982dbf8acdd6b616ebe1c06f081814f31a` is the documentation-only child in Phase30 with explicit independent role, exact reviewed SHA, independent tests/checks and no findings. T135 is Done in ordinary pre-merge §3: Organization-scoped Property list/get/create/update with Party-canonical `Party → PropertyOwner → Property`, fresh `client_id=NULL`, zero Client manufacture/dual-write, multiple owners/Party reuse, tenant-safe references, atomic creation, bounded owner-preserving update, legacy Client-owner read compatibility, and DELETE omitted. No migration/schema/RLS/PartyWriteGate/provenance/classifier change occurred; Alembic remains `9e6a4b2c8d1f`. Required ADR #20 remains unresolved; ADR-0036/0037/0038/0039 remain Proposed; `latestTaskDone/latestTaskAuthorized = T135`; transitions empty; T136+ unauthorized; PR #242 remains open/unmerged pending final Git/CI gates.

T136 is now Done after §3.1 architecture+QA PR #244 merged as `73bf20ba4c04b63d2580d8b41ec701ce19f21f5d`, following authorization PR #243 merge `09229cef3a4e31300edf31a904aa7a443fe80f4b`. Independent QA **Approved** exact architecture `c89a8ea6d7be72088fcd8d39188513077a779312`; primary QA evidence is `c77dfc3403b82b37e25a0afa4bd3a9e17ccb0836`, with no blocking or non-blocking findings. ADR-0040 remains **Proposed** and establishes the non-fabricating `Matter → File → Document` transition: no synthetic/default File, no heuristic legacy assignment, explicit legacy-unfiled retention, File-canonical new Documents, direct future Document Organization ownership, same-tenant/same-Matter integrity, preserved ADR-0027 numbering/ADR-0030 lifecycle, lossy-downgrade refusal and separately gated `documents.matter_id` retirement. Required ADR #10 is resolved at this closeout; Required ADR #20 remains unresolved, with unresolved set `[11, 12, 15, 16, 17, 20]`. No production/schema/migration/test work occurred; Alembic remains `9e6a4b2c8d1f`. `latestTaskDone`/`latestTaskAuthorized` are `T136`, transitions empty, and T137+ remains unauthorized; ADR-0040's future implementation slices remain unnumbered and unauthorized.

**Update (2026-09-24, Documentation Manager, T137 post-QA synchronization on PR #247):** Independent QA **Approved** exact implementation `42baef57ae5f305d84fbe4bcf28d83bd935d3f2f`; QA evidence `ce56815c5f9ebcae30c997214631ac60e6dfb44b` is its documentation-only child in Phase31 with Independent QA Reviewer / Antigravity provenance, 4 focused disposable PostgreSQL tests passed, Ruff clean, Black 257 files unchanged, governance validator clean, `git diff --check` clean, and no findings. T137 is Done in ordinary pre-merge §3: migration `b8c4d2e1f7a9` (parent `9e6a4b2c8d1f`) adds persistence-only File and Matter-scoped number-sequence foundations, direct File/Document Organization ownership, deterministic Document Organization backfill, nullable legacy-unfiled `file_id`, same-tenant/same-Matter database integrity, forced Organization-GUC RLS, fail-closed downgrade, and advances the supported operational-fresh revision to `b8c4d2e1f7a9`. File/Document CRUD, runtime allocation, synthetic/heuristic File assignment, legacy resolution tooling, compatibility-consumer retirement and other excluded seams remain unimplemented. Required ADR #10 stays resolved; Required ADR #20 stays unresolved with unresolved set `[11, 12, 15, 16, 17, 20]`; ADR-0036/0037/0038/0039/0040 remain Proposed; `latestTaskDone/latestTaskAuthorized = T137`; transitions empty; T138+ unauthorized; PR #247 remains open/unmerged pending final Git/CI gates.

**Update (2026-09-25, T140 §3.1 governance closeout):** T140 is Done after authorization PR #253 and architecture+QA PR #254 completed the governed architecture lifecycle. ADR-0041 remains **Proposed** and resolves Required ADR #11 after independent QA **Approved** and protected architecture merge `47a712d752762d933988ccad5427314f7f7f8da3`. Remaining unresolved Required ADRs are `[12, 15, 16, 17, 20]`. No DocumentVersion/FileStorageRecord application capability, upload/download orchestration, schema or migration was implemented; Alembic/provenance remains `be439c0d6fdb`. The two implementation slices recommended by ADR-0041 remain unnumbered and unauthorized. Latest Done/Authorized are T140, transitions are empty, and T141+ remains unauthorized.

**Update (2026-09-25, Documentation Manager, T141 post-QA synchronization on PR #257):** Independent QA **Approved** immutable implementation `3e96d41fd5d2953f872ea4748f68d1845d9dbe2c`; QA evidence `9505fd433c4e8319617373fa76da5c3bdf73648f` is documentation-only and changes only `docs/ImplementationLog/Stage3/Phase34.md`. T141 is Done in the ordinary pre-merge §3 sense. Migration `cdcfd7df5fde`, the sole direct child of `be439c0d6fdb`, adds the bounded ADR-0041 tenant/security/integrity foundation: direct DocumentVersion Organization ownership, staged nullable FileStorageRecord tenant ownership for shared consumers, authoritative canonical backfill, fail-closed shared/ambiguous storage handling, same-tenant/exclusive version-storage constraints, persisted Document-version idempotency, FORCE-RLS/default-deny Organization-GUC isolation, guarded downgrade, and operational-fresh revision advancement. DocumentTemplate, QrCodeRecord, Receipt and other non-version storage remain staged without guessed ownership. Runtime version allocation, DocumentVersion repository/service/API, upload/download, physical storage orchestration/compensation/recovery, runtime checksum workflow, legacy Document→File resolution, retention/deletion semantics and new RBAC remain unimplemented. The full PostgreSQL integration differential remains baseline-equivalent: baseline 424 passed/56 failed/21 skipped versus T141 434 passed/56 failed/21 skipped, with no T141-only failures. Required ADR #11 stays resolved by T140/ADR-0041; unresolved Required ADRs remain `[12, 15, 16, 17, 20]`; ADR-0041 remains Proposed; `latestTaskDone/latestTaskAuthorized = T141`; transitions empty; migration/provenance frontier `cdcfd7df5fde`; T142+ unauthorized. PR #257 remains open/unmerged pending final exact-head Git/CI verification.
