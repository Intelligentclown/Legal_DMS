# Architecture

## Overview

Clean Architecture, mirrored independently on both the backend and the frontend. Dependencies
only ever point inward:

```
Presentation  →  Application  →  Domain
                       ↑
                Infrastructure (implements Application's ports; talks to DB/OS/FS/network)
```

- **Domain** — pure entities, value objects, and port interfaces. No framework imports. Business
  rules live here once they exist (none yet — Stage 1 only added framework-level base types:
  `AggregateRoot`, `DomainEvent`, `Result[T, E]`).
- **Application** — use cases / services orchestrating domain logic through ports. No FastAPI,
  no SQLAlchemy, no React imports.
- **Infrastructure** — concrete implementations of Application's ports: SQLAlchemy repositories,
  logging, config loading, external services.
- **Presentation** — FastAPI routers/schemas (backend), React components/pages (frontend). Talks
  to Application, never straight to Infrastructure for business logic (DB *session plumbing* via
  `Depends` is the one pragmatic exception — see below).

The rule this protects: **business logic must never live in a router or a component**, and
**database code must never live directly in an API route**.

## Backend (`backend/src/app/`)

```
domain/
  common/           Entity, AggregateRoot (collects domain events), ValueObject, Result[T, E]
  events/            DomainEvent base class
application/
  common/           BaseService[T], Validator[T]/validate_all(), PageRequest/PageResult[T],
                     SortSpec/FilterSpec/SearchQuery (the shared query shape — InMemorySearchIndex
                     is the one Stage 1 implementation that interprets it; SqlAlchemyRepository's
                     list()/count() don't yet — that's an extension point for a real feature)
  errors/          AppError hierarchy (ValidationError, NotFoundError, ConflictError, ...)
  interfaces/       repository.py (AbstractRepository[T]), event_bus.py (EventBus),
                     command_bus.py (Command/CommandHandler/CommandBus/CommandBusError),
                     query_bus.py (Query/QueryHandler/QueryBus/QueryBusError),
                     unit_of_work.py (UnitOfWork/UnitOfWorkError), cache.py (Cache),
                     metrics.py (MetricsService), job_queue.py (Job/JobQueue),
                     file_storage.py (FileStorage), notifier.py (Notifier), auth.py
                     (AuthenticationProvider/CurrentUser/AuthorizationService),
                     audit.py (AuditLogger), search.py (SearchIndex),
                     feature_flags.py (FeatureFlagProvider)
  workflow/          WorkflowDefinition/WorkflowEngine — generic state machine. No real
                     workflow definitions ship (framework only); proven with a toy graph
                     in tests, not the charter's Draft->Review->...->Completed example
infrastructure/
  config/          pydantic-settings Settings, env-driven (incl. feature_flags dict,
                     "name:true,other:false" — see SettingsFeatureFlagProvider)
  logging/         structured JSON logging (console + rotating file)
  database/        SQLAlchemy Base (naming_convention set for consistent constraint/index
                     names), async engine/session, get_db() dependency -- commits the session
                     on a clean exit, rolls back on exception, before it closes (deliberate
                     policy, not incidental; repositories only flush() within the transaction
                     get_db() is what actually persists it -- Stage 3 Phase 0, ADR/0020)
  persistence/models/  Stage 2: the complete 49-table database schema as SQLAlchemy models,
                     persistence-layer only (ADR/0008), plus a seed-data migration for lookup
                     tables — see docs/Database.md and docs/ERD.md. No repositories/services/
                     routes wired to these tables yet.
  audit/              LoggingAuditLogger — structured JSON audit entries, no DB table yet
                       (ADR/0007)
  auth/               AnonymousAuthenticationProvider (no login exists), PermissiveAuthorizationService
                       (denies anonymous callers, permissive once authenticated — no real
                       permission data model yet)
  di/               Container (register/resolve/override/registered_interfaces),
                     configure_container(); health_check.py (check_container_health(),
                     assert_container_healthy() — resolves every registration once at boot,
                     wired into main.py's create_app(), post-Stage-2, ADR/0015)
  events/            InMemoryEventBus — in-process publish/subscribe
  commands/          InMemoryCommandBus — in-process single-handler command dispatch;
                     TransactionPipelineBehavior — CommandBus decorator, wraps dispatch in a
                     unit-of-work transaction (commit on success, rollback on failure/exception,
                     including asyncio.CancelledError — catches BaseException, not just Exception,
                     since CancelledError doesn't inherit from Exception; fixed post-QA-review,
                     see docs/reviews/Stage_2_5_QA_Review.md finding Q1 / IMPLEMENTATION_QUEUE.md T20)
  queries/           InMemoryQueryBus — in-process single-handler query dispatch
  transactions/      InMemoryUnitOfWork — tracks begin/commit/rollback state, no backing resource
                     yet; registered non-singleton (a fresh instance per transaction)
  cache/             InMemoryCache — dict-backed key-value store, optional per-entry TTL
                     (lazy expiry, time.monotonic-based), not wired to QueryBus/CommandBus
  metrics/           LoggingMetricsService — logs counters/gauges/durations as structured
                     JSON (app.metrics channel), no real backend wired, not wired to any
                     route/middleware/bus dispatch
  modules/            AppModule protocol + ModuleRegistry — plugin architecture. Lives here
                       rather than application/interfaces because AppModule references FastAPI
                       directly (it mounts routes); the application layer's ports stay
                       framework-agnostic. The global registry is empty in Stage 1 and
                       main.py calls mount_all() unconditionally (a no-op today) so a future
                       module only needs to register itself — the core app never needs
                       editing again to pick it up. ModuleManifest/ModuleManifestLoader
                       (post-Stage-2, ADR/0014) close the gap that promise left open: something
                       still has to know which packages to import so their registration side
                       effect runs. Not wired into main.py yet — no real manifest exists.
  jobs/               InMemoryJobQueue — asyncio-task-backed job execution + status tracking
  notifications/       LoggingNotifier — logs instead of sending; server-side, distinct from
                        the frontend's toast NotificationProvider
  persistence/      SqlAlchemyRepository[ModelT] — generic CRUD repository implementation
  search/             InMemorySearchIndex — naive substring/filter match proving SearchIndex;
                        real full-text/OCR/smart search deferred
  storage/            LocalFileStorage — filesystem-backed, path-traversal-safe FileStorage
presentation/
  api/v1/          health, version routers; aggregated in router.py
  common/           ApiResponse[T]/paginated_response(); build_crud_router() — generic
                     list/get/create/update/delete router factory ("Base Controller"),
                     proven with a test-only entity, never mounted into the real app
  middleware/      RequestIDMiddleware, LoggingMiddleware, exception handlers
workers/            JobRegistry (name -> Job) + NoOpJob proving the framework; real jobs
                     (OCR, PDF conversion, backups, ...) arrive with the feature that needs them
main.py             FastAPI app factory — wires config, logging, CORS, middleware, routers
```

> Stage 1 added the reusable cross-cutting platform shown above (DI container, repository
> pattern, base service, validation/pagination/query/response frameworks, CRUD router factory,
> event bus, job framework, storage/notification/search/auth/audit abstractions, plugin
> architecture, workflow engine, feature flags) — all framework, zero business features. See
> [ADR/0006](../ADR/0006-dependency-injection-container.md) and
> [ADR/0007](../ADR/0007-audit-logging-without-database-table.md) for the two Stage 1-specific
> architectural decisions, and [ProjectStatus.md](ProjectStatus.md) for the full checklist.
>
> A **Command Bus** (`CommandBus` port + `InMemoryCommandBus`) was added after Stage 2 as a
> standalone, Stage-1-style framework addition — same shape as `EventBus`, but dispatches a
> command to exactly one registered handler and returns a `Result[R, AppError]`, rather than
> fanning out to many subscribers. Framework only, zero business commands. See
> [ADR/0010](../ADR/0010-command-bus.md).
>
> A **Query Bus** (`QueryBus` port + `InMemoryQueryBus`) followed as its symmetric sibling — same
> single-handler dispatch contract as `CommandBus`, for reads instead of writes. Framework only,
> zero business queries. See [ADR/0011](../ADR/0011-query-bus.md).
>
> A **Transaction Pipeline** resolves the "transaction wrapping" trade-off both bus ADRs deferred:
> `UnitOfWork` port + `InMemoryUnitOfWork` (registered non-singleton — the first port in this
> project registered that way, since a transaction's state must not be shared across concurrent
> operations) plus `TransactionPipelineBehavior`, a `CommandBus` decorator that begins a unit of
> work before dispatching to the inner bus and commits/rolls back based on the handler's `Result`.
> Not wired as `CommandBus`'s own container registration — a future feature opts in explicitly. See
> [ADR/0012](../ADR/0012-transaction-pipeline.md).
>
> A **Caching Abstraction** (`Cache` port + `InMemoryCache`) followed as a standalone capability —
> same category as `FileStorage`/`SearchIndex`, not a pipeline behavior wrapping `QueryBus` (that
> would be a distinct "Caching Pipeline" decision, deliberately not made here — see ADR-0013 for
> why the naming pointed to a standalone port rather than a `QueryBus` decorator). Framework only,
> not wired to anything yet. See [ADR/0013](../ADR/0013-caching-abstraction.md).
>
> A **Module Manifest Loader** (`ModuleManifest`/`ModuleManifestLoader`, in
> `infrastructure/modules/`) closes a gap the plugin architecture's own docstring left open: it
> promised a future module "only needs to register itself," but nothing actually knew which
> packages to import to trigger that. The loader reads a JSON manifest and imports its enabled
> entries — registration still happens as each import's own side effect, unchanged. Not wired into
> `main.py`'s startup — no real manifest exists yet. See
> [ADR/0014](../ADR/0014-module-manifest-loader.md).
>
> An **Architecture Health Check** resolves `IMPLEMENTATION_QUEUE.md`'s T15 finding directly:
> `assert_container_healthy(container)` (`infrastructure/di/health_check.py`) resolves every
> interface registered in `configure_container()` once, raising `ContainerHealthCheckError`
> listing every failure if any registration is broken. Unlike every other post-Stage-2 addition,
> this one **is** wired into `main.py`'s `create_app()` — right after `configure_container()` —
> since every registration it checks is already proven working by the existing test suite, making
> the wiring low-risk and central to what "startup self-check" actually means. See
> [ADR/0015](../ADR/0015-architecture-health-check.md).
>
> A **Performance Metrics Service** (`MetricsService` port + `LoggingMetricsService`) followed as
> a standalone capability — `increment`/`gauge`/`record_duration` plus a concrete `timer()`
> convenience, logging each event as structured JSON (`LoggingNotifier`/`LoggingAuditLogger`'s "no
> real backend wired yet" precedent, not `Cache`'s in-memory-state precedent — a metric event has
> no read-back need). Not wired into `CommandBus`/`QueryBus` dispatch, HTTP middleware, or a
> `/metrics` route. See [ADR/0016](../ADR/0016-performance-metrics-service.md).

Dependency injection is FastAPI's own `Depends()` system: routes declare `SettingsDep` /
`DBSessionDep` / `CurrentUserDep` (see
[`presentation/api/deps.py`](../backend/src/app/presentation/api/deps.py)) rather than importing
infrastructure singletons directly. `SettingsDep` and `CurrentUserDep` resolve through the DI
container (see [ADR/0006](../ADR/0006-dependency-injection-container.md)); `DBSessionDep` stays on
FastAPI's native generator pattern for request-scoped teardown. Every future port
(`application/interfaces/...`) with a concrete implementation
(`infrastructure/...`) follows the same container-registration pattern established for `Settings`.

**Pragmatic exception:** `DBSessionDep` gives routes an `AsyncSession` directly. That's session
*plumbing*, not business logic — actual query/business logic still belongs in a
repository/use-case, not inline in a route handler, once those exist.

**Commit/rollback contract:** `get_db()` commits the session when the request handler returns
normally and rolls back if it raises, immediately before the session closes — see
[ADR/0020](../ADR/0020-session-commit-rollback-policy.md). This is why `SqlAlchemyRepository`'s
`add()`/`update()`/`delete()` only need to `flush()`, never `commit()` themselves: `get_db()` is
the transaction boundary, not the repository. A route/service performing several repository calls
against the same request's session gets them all committed — or all rolled back — together as one
transaction. `except Exception` (not `BaseException`) is a known, deliberate scope limit of this
fix — see the ADR's Trade-offs for why `asyncio.CancelledError` isn't covered yet.

## Frontend (`frontend/src/`)

```
app/
  App.tsx           root component: providers + router
  routes.tsx         react-router-dom route tree
  providers/         ThemeProvider, NotificationProvider, AppProviders (composition root)
presentation/
  layouts/           MainLayout (header + <Outlet />)
  pages/              route-level pages (HealthCheckPage)
  components/          shared UI; components/ui/ is shadcn/ui primitives
application/
  services/           future use-case orchestration — empty in Stage 0
domain/
  types/              shared TS types (HealthStatus, AppVersion, Result<T, E> — mirrors the
                       backend's Result[T, E] as a discriminated union)
infrastructure/
  api/                httpClient — fetch wrapper reading VITE_API_BASE_URL
  ipc/                ipcBridge — typed wrapper over window.api (Electron preload surface)
shared/
  config/             env.ts — typed import.meta.env access
  types/               query.ts — PageRequest/PaginatedResponse/SortSpec/FilterSpec/SearchQuery,
                        mirroring the backend's query framework for future paginated-list pages
  utils/               cn() (Tailwind class merging), general utilities
  constants/            (empty placeholder)
test/                 Vitest setup (jsdom, jest-dom matchers, RTL cleanup)
```

## Electron (`electron/`)

Thin shell, no business logic:

- `main.ts` — app lifecycle, one `BrowserWindow` with `contextIsolation: true`,
  `nodeIntegration: false`, `sandbox: true`. Loads the Vite dev server in development or
  `frontend/dist/index.html` in production. Restricts navigation/new-window creation to trusted
  origins (`setWindowOpenHandler`, `will-navigate`).
- `preload.ts` — exposes a minimal, explicitly-named API via `contextBridge` (e.g. `getAppInfo()`),
  never a generic `invoke(channel, ...)` passthrough.
- `ipc/channels.ts` — the whitelist of IPC channel names shared between main and preload.

## Why Clean Architecture before there's a business feature to justify it

See [ADR/0002-clean-architecture-layering.md](../ADR/0002-clean-architecture-layering.md). Short
version: this codebase is expected to grow over many months across many sessions/models — paying
the layering cost now, while it's cheap (no business logic to migrate), is the whole point of
Stage 0.
