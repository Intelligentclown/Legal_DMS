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
                     job_queue.py (Job/JobQueue), file_storage.py (FileStorage),
                     notifier.py (Notifier), auth.py (AuthenticationProvider/CurrentUser/
                     AuthorizationService), audit.py (AuditLogger), search.py (SearchIndex),
                     feature_flags.py (FeatureFlagProvider)
  workflow/          WorkflowDefinition/WorkflowEngine — generic state machine. No real
                     workflow definitions ship (framework only); proven with a toy graph
                     in tests, not the charter's Draft->Review->...->Completed example
infrastructure/
  config/          pydantic-settings Settings, env-driven (incl. feature_flags dict,
                     "name:true,other:false" — see SettingsFeatureFlagProvider)
  logging/         structured JSON logging (console + rotating file)
  database/        SQLAlchemy Base (naming_convention set for consistent constraint/index
                     names), async engine/session, get_db() dependency
  persistence/models/  Stage 2: the full database schema as SQLAlchemy models, persistence-
                     layer only (ADR/0008) — see docs/Database.md and docs/ERD.md
  audit/              LoggingAuditLogger — structured JSON audit entries, no DB table yet
                       (ADR/0007)
  auth/               AnonymousAuthenticationProvider (no login exists), PermissiveAuthorizationService
                       (denies anonymous callers, permissive once authenticated — no real
                       permission data model yet)
  di/               Container (register/resolve/override), configure_container()
  events/            InMemoryEventBus — in-process publish/subscribe
  modules/            AppModule protocol + ModuleRegistry — plugin architecture. Lives here
                       rather than application/interfaces because AppModule references FastAPI
                       directly (it mounts routes); the application layer's ports stay
                       framework-agnostic. The global registry is empty in Stage 1 and
                       main.py calls mount_all() unconditionally (a no-op today) so a future
                       module only needs to register itself — the core app never needs
                       editing again to pick it up.
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
