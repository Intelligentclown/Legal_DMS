# Project Status

**Current Stage:** Backend authentication/authorization (`T41`–`T68`) and frontend/Electron
fundamentals (`T69`–`T78`) are both done and merged. `PROJECT_STATE.json` labels the latter half
`stage-4` ("Frontend & Electron Fundamentals"); `IMPLEMENTATION_QUEUE.md`/`docs/Roadmap.md` still
file the whole `T41`–`T82` range under one "Stage 3 — Authentication & Authorization" heading —
this is a genuine, disclosed naming inconsistency between Project-Manager-owned planning documents
and `PROJECT_STATE.json`/`docs/ImplementationLog/`, not resolved by this update (see
`PROJECT_CHECKPOINT.md` §2 for the full disclosure). `T79`, a verification-only pass intended to
close this surface out, was **closed by the Project Owner as INCOMPLETE / NOT VERIFIED** — its
Electron-specific session-persistence requirement (ADR-0018 D6) could not be exercised in this
environment. `T82` (Electron-runtime live smoke verification, the direct follow-up) is reserved and
scoped but **not authorized, not started**. See [PROJECT_CHECKPOINT.md](../PROJECT_CHECKPOINT.md)
for the fullest current-state detail; this file gives the narrative version.
**Current Version:** 0.3.1 (see [CHANGELOG.md](../CHANGELOG.md)'s versioning note — the `v0.3.0`
tag already contains everything previously documented as 0.3.1 through 0.3.8; this version is only
what's genuinely new since that tag, previously mislabeled 0.3.9). No new tag has been cut since;
substantial work (`T41`–`T78`) has landed on `main` under this same version number.
**Last Updated:** 2026-08-28 (Documentation Manager, `T97` snapshot refresh — this file had gone
stale again after the 2026-08-21 batch below, thirteen tasks behind: `T83`–`T96` were not reflected
at all. See "Completed — Governance & Required-ADR Resolution Series (`T86`–`T96`)" below.
`T97` (this refresh) is authorized, not yet Done — see `PROJECT_STATE.json`'s `governanceLedger` for
the current, mechanically-validated authorized/Done state rather than re-deriving it here by hand).
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

## Completed — Governance & Required-ADR Resolution Series (T86–T96)

**Added by this Documentation Manager pass (2026-08-28) — this file had never covered `T83`–`T96` at
all before now.** Full task-by-task detail lives in each task's own `IMPLEMENTATION_QUEUE.md` row
and, for `T87` onward, in `docs/reviews/T<N>_Software_Architect_Report.md` /
`T<N>_Implementation_Report.md`; not duplicated here.

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
- **`T97` — Documentation Manager Sync (this task) — authorized, not yet Done.** Refreshes this
  file, `PROJECT_STATE.json`'s top-level snapshot, `docs/AI_HANDOVER.md`, `docs/SessionReport.md`,
  and `PROJECT_WORKFLOW.md` §6's stale CI-workflow count through the completed `T86`–`T96` series.
  Ordinary Documentation Manager maintenance, not a Required-ADR/governance-hardening task — see
  `PROJECT_WORKFLOW.md` §3.1 for that distinction.

`T82` itself remains exactly as recorded above: closed **`FAIL`**, QA-Approved-with-comments, not
silently reinterpreted by this pass. No follow-up implementation task beyond `T84`/`T85` has been
authorized for it.

## Pending

**Update (2026-08-28):** the paragraph below is now itself stale in one respect — see "Completed —
Governance & Required-ADR Resolution Series (`T86`–`T96`)" above for what happened since. As of this
update, two items are open, not one: a follow-up implementation task for `T82`'s Electron
session-restoration finding remains **not authorized** (unchanged since 2026-08-21), and `T97`
(this Documentation Manager sync) is **authorized, not yet Done** — the difference between the two
being that `T97` has actual repository-recorded authorization (`IMPLEMENTATION_QUEUE.md`'s `T97`
row, PR #144) where `T82`'s follow-up has none. Nine Required ADRs (`#8`, `#10`, `#11`, `#12`,
`#14`–`#17`, `#20`) also remain unresolved, per `PROJECT_STATE.json`'s `governanceLedger` — not
"pending" in the authorized-task sense, since no task currently targets them.

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
