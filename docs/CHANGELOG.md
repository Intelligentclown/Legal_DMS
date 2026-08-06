# Changelog (detailed)

Per-stage detail. See root [CHANGELOG.md](../CHANGELOG.md) for the short pointer version.

## Stage 0 — Project Foundation

**Version:** 0.1.0
**Dates:** 2026-08-03 to 2026-08-05
**Summary:** Established the full project foundation — repo tooling, backend (FastAPI +
SQLAlchemy + Alembic + Postgres), Electron shell, frontend (React + Vite + Tailwind + shadcn/ui),
tests on both sides, and this documentation set. Zero business features, as scoped.
**Breaking changes:** None (greenfield).
**Migration notes:** None (greenfield; first-ever migration is just Alembic's own
`alembic_version` bookkeeping table).

### `80f7bae` — repo skeleton and dev tooling (2026-08-03)
- **Added:** `.gitignore`, `.editorconfig`, `.gitattributes`, `.vscode/settings.json`,
  `.vscode/extensions.json`, `docker-compose.yml`, root `.env.example`, `README.md`,
  `CHANGELOG.md`.

### `7b5413b` — backend foundation: config, logging, error handling (2026-08-03)
- **Added:** `backend/pyproject.toml`, `backend/ruff.toml`, `backend/.env.example`,
  `backend/src/app/` skeleton (domain/application/infrastructure Clean Architecture folders),
  `infrastructure/config/settings.py` (pydantic-settings), `infrastructure/logging/logger.py`
  (structured JSON logging), `application/errors/exceptions.py` (`AppError` hierarchy),
  `domain/common/entity.py` (base `Entity`/`ValueObject`).

### `d8a0b8e` — FastAPI app, DB layer, and Alembic wiring (2026-08-05)
- **Added:** `main.py` (app factory), `presentation/api/v1/` (health, version routers),
  `presentation/api/deps.py`, `presentation/middleware/` (request ID, logging, error handler),
  `infrastructure/database/` (SQLAlchemy `Base`, async engine/session), `backend/alembic/`
  (async template, `env.py` reads `DATABASE_URL` from `Settings`), `backend/alembic.ini`.
- **Fixed:** `cors_origins` startup crash — a bare `list[str]` settings field made
  `pydantic-settings` try to JSON-decode the comma-separated env value before the custom validator
  ran; fixed with `Annotated[list[str], NoDecode]`. Caught by testing against a real `.env` +
  live Postgres container.
- **Modified:** `infrastructure/config/settings.py`.

### `c528414` — backend test suite (2026-08-05)
- **Added:** `backend/pytest.ini`, `backend/tests/` (conftest, unit tests for `AppError` +
  Settings CORS parsing, integration tests for `/health`/`/version`). 10 tests, all passing.

### `568a53c` — Electron shell (2026-08-05)
- **Added:** `electron/main.ts`, `electron/preload.ts`, `electron/ipc/channels.ts`,
  `electron/tsconfig.json`, root `package.json` (Electron build/dev orchestration),
  `electron-builder.yml`.

### `7204c06` — frontend foundation (2026-08-05)
- **Added:** `frontend/` (Vite + React 19 + TypeScript scaffold), Tailwind v4 config, a
  hand-authored shadcn/ui `Button` (see [KnownIssues.md](KnownIssues.md) for why the CLI wasn't
  used), `app/providers/` (Theme, Notification), `presentation/components/`
  (ErrorBoundary, LoadingSpinner, Notification), `presentation/layouts/MainLayout.tsx`,
  `app/routes.tsx`, `infrastructure/api/httpClient.ts`, `infrastructure/ipc/ipcBridge.ts`,
  `shared/config/env.ts`, `shared/utils/cn.ts`.
- **Removed:** the Vite scaffold's default `oxlint` setup, replaced with ESLint (flat config) +
  Prettier per the project's tooling spec.

### `0f2905c` — frontend-backend E2E proof (2026-08-05)
- **Added:** `presentation/pages/HealthCheckPage.tsx`, `domain/types/health.ts`.
- **Modified:** `app/routes.tsx` (wired `HealthCheckPage` as the index route).
- Verified live: Postgres + FastAPI + Vite dev server + Electron running together, health data
  rendering correctly, CORS preflight succeeding, Electron loading and exiting cleanly.

### `454d7cf` — frontend test suite (2026-08-05)
- **Added:** `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`,
  `HealthCheckPage.test.tsx` (loading/success/error+retry states). 3 tests, all passing.
- **Modified:** `frontend/package.json` (`test`/`test:watch` scripts).

### Documentation pass (this commit)
- **Added:** full `docs/` set (this file included) and `ADR/` with the Stage 0 decision records.

## Stage 1 — Core Architecture & Domain Foundation

**Version:** 0.2.0
**Dates:** 2026-08-05 (one continuous session)
**Summary:** Built the reusable cross-cutting platform every future business feature will plug
into — DI container, repository pattern, base service, validation/pagination/query/response
frameworks, a generic CRUD router factory, event system, background job framework, file storage
abstraction, notification framework, auth/authorization/audit frameworks (no login), search
foundation, plugin architecture, workflow engine, feature flags. Every port got exactly one
minimal default implementation (in-memory/local/logging), no new dependencies. Zero business
features, as scoped.
**Breaking changes:** None — every extension to Stage 0 code (`Settings`, `deps.py`,
`AbstractRepository`, `BaseService`) kept its existing public shape.
**Migration notes:** None — no new database tables.

### `f4a5b0b` — domain foundation (AggregateRoot, DomainEvent, Result)
- **Added:** `domain/events/domain_event.py` (`DomainEvent`), `domain/common/result.py`
  (`Result[T, E]`).
- **Modified:** `domain/common/entity.py` (added `AggregateRoot`).

### `c822a03` — dependency injection container
- **Added:** `infrastructure/di/container.py` (`Container`, `configure_container()`),
  `ADR/0006-dependency-injection-container.md`.
- **Modified:** `presentation/api/deps.py` (`SettingsDep` now container-backed, same public
  shape), `main.py` (calls `configure_container()`).

### `0203996` — repository pattern
- **Added:** `application/interfaces/repository.py` (`AbstractRepository[T]`, `SupportsId`),
  `infrastructure/persistence/sqlalchemy_repository.py` (`SqlAlchemyRepository[ModelT]`).
- Verified against live Postgres with an isolated test-only declarative base.

### `f8c82fe` — base service
- **Added:** `application/common/base_service.py` (`BaseService[T]`).

### `46bede6` — validation, pagination/query shapes, response wrapper
- **Added:** `application/common/validation.py` (`Validator[T]`, `validate_all()`),
  `application/common/pagination.py` (`PageRequest`, `PageResult[T]`), `application/common/query.py`
  (`SortSpec`, `FilterSpec`, `SearchQuery`), `presentation/common/response.py` (`ApiResponse[T]`,
  `paginated_response()`).

### `77df682` — base controller (CRUD router factory)
- **Added:** `presentation/common/crud_router_factory.py` (`build_crud_router()`),
  `tests/support/in_memory_repository.py` (shared test fake).
- **Fixed:** a request-body-becomes-query-parameter bug caused by using the factory's own PEP 695
  generic type parameters (TypeVar placeholders at runtime) as FastAPI route annotations — fixed
  by annotating with the actual runtime schema classes instead, documented in the module docstring.
- **Modified:** `application/interfaces/repository.py` (`+count()`),
  `infrastructure/persistence/sqlalchemy_repository.py` (`+count()`),
  `application/common/base_service.py` (`+list_page/create/update/delete`).

### `5e11da4` — event system
- **Added:** `application/interfaces/event_bus.py` (`EventBus`),
  `infrastructure/events/in_memory_event_bus.py` (`InMemoryEventBus`).

### `2fc9415` — background job framework
- **Added:** `application/interfaces/job_queue.py` (`Job`, `JobQueue`, `JobRecord`, `JobStatus`),
  `workers/registry.py` (`JobRegistry`, `NoOpJob`), `infrastructure/jobs/in_memory_job_queue.py`
  (`InMemoryJobQueue`).

### `fd94e5d` — file storage abstraction
- **Added:** `application/interfaces/file_storage.py` (`FileStorage`, `StoredFile`),
  `infrastructure/storage/local_file_storage.py` (`LocalFileStorage`, path-traversal-safe).
- **Modified:** `Settings` (`+storage_root`).

### `75c28a5` — backend notification framework
- **Added:** `application/interfaces/notifier.py` (`Notifier`, `Notification`),
  `infrastructure/notifications/logging_notifier.py` (`LoggingNotifier`).

### `c05c744` — auth, authorization, and audit logging frameworks (no login)
- **Added:** `application/interfaces/auth.py` (`CurrentUser`, `AuthenticationProvider`,
  `AuthorizationService`), `application/interfaces/audit.py` (`AuditLogger`),
  `infrastructure/auth/` (`AnonymousAuthenticationProvider`, `PermissiveAuthorizationService`),
  `infrastructure/audit/audit_logger.py` (`LoggingAuditLogger`),
  `ADR/0007-audit-logging-without-database-table.md`.
- **Modified:** `presentation/api/deps.py` (`+CurrentUserDep`).

### `f374fa6` — search foundation
- **Added:** `application/interfaces/search.py` (`SearchIndex`, `SearchHit`, `SearchResults`),
  `infrastructure/search/in_memory_search_index.py` (`InMemorySearchIndex`).

### `e10978b` — plugin architecture
- **Added:** `infrastructure/modules/registry.py` (`AppModule`, `ModuleRegistry`).
- **Modified:** `main.py` (calls `module_registry.mount_all()` unconditionally — a no-op today).
- Deliberate deviation from the original file plan: `AppModule` lives in `infrastructure/modules/`,
  not `application/interfaces/`, since it references FastAPI directly.

### `4338c56` — workflow engine
- **Added:** `application/workflow/engine.py` (`WorkflowDefinition`, `WorkflowEngine`,
  `Transition`, `WorkflowError`).

### `2527546` — feature flags + config service extension
- **Added:** `application/interfaces/feature_flags.py` (`FeatureFlagProvider`),
  `infrastructure/config/feature_flags.py` (`SettingsFeatureFlagProvider`).
- **Modified:** `Settings` (`+feature_flags`, env-driven `"name:true,other:false"`).

### `c18cef3` — frontend Result type and pagination/query types
- **Added:** `frontend/src/domain/types/result.ts` (`Result<T, E>`),
  `frontend/src/shared/types/query.ts` (`PageRequest`, `PaginatedResponse<T>`, `SortSpec`,
  `FilterSpec`, `SearchQuery`).

### Documentation pass (this commit)
- **Added:** `AI_BOOTSTRAP.md`, `PROJECT_STATE.json` (repo root).
- **Modified:** `docs/AI_HANDOVER.md`, `docs/Architecture.md`, `docs/ProjectStatus.md`,
  `docs/ModuleRegistry.md`, `docs/FeatureRegistry.md`, `docs/Roadmap.md`, `docs/CHANGELOG.md` (this
  file), `docs/SessionReport.md`.
- Final state: 130 backend tests, 9 frontend tests, all passing; ruff/black/eslint/prettier clean;
  real app's route surface unchanged from Stage 0 (`/api/v1/health`, `/api/v1/version` only).

## Stage 2 — Database Architecture & Data Model

**Version:** 0.3.0
**Dates:** 2026-08-05 (one continuous session)
**Summary:** Designed and built the complete production-ready database schema for the entire
eventual application — 49 tables across 11 domain sections plus a seed-data migration, as pure
schema: SQLAlchemy models, Alembic migrations, constraints, and indexes. **No business logic, no
UI, no repositories/services/API routes wired to any of these tables** — that's explicitly
future-stage work. Architecture proposal (overview, ER diagram, table list, relationships, index
strategy, migration strategy, performance considerations, future scalability) presented and
approved before any code was written, per the charter's explicit process.
**Breaking changes:** None — the real app's route surface (`/api/v1/health`, `/api/v1/version`) is
unchanged.
**Migration notes:** 12 new Alembic revisions (11 schema + 1 seed data), all verified against live
Postgres including full chain reversibility (`alembic downgrade base` → `alembic upgrade head`).

### `39dcab5` — schema conventions + Identity & Access (5 tables)
- **Added:** `NAMING_CONVENTION` + `Base.metadata` naming convention
  (`infrastructure/database/base.py`), `AuditMixin`/`OptimisticLockMixin`
  (`infrastructure/persistence/models/mixins.py`), `infrastructure/persistence/models/identity.py`
  (`User`, `Role`, `Permission`, `UserRole`, `RolePermission`), migration `4c661976b322`,
  `ADR/0008-persistence-models-not-domain-entities.md`.
- **Fixed:** `alembic/env.py` never actually imported the models package (only a comment existed),
  so `Base.metadata` was empty at autogenerate time — added the real import.

### `53985a3` — geography (5 tables)
- **Added:** `geography.py` (`Country`, `State`, `District`, `Taluka`, `Village`), migration
  `198cbb4bbeb6`.

### `a3949f5` — clients (3 tables)
- **Added:** `client.py` (`Address`, `Client`, `ClientContact`), migration `ac077004afeb`.
- Documented the `CheckConstraint` naming double-prefix pitfall (pass a short logical name, not the
  full expected constraint name) inline for future sections.

### `d7cd7ae` — properties (2 tables)
- **Added:** `property.py` (`Property`, `PropertyOwner`), migration `7789f56da7f9`.
- `village_id` denormalized directly onto `properties` (in addition to via `address_id`) so
  village-based search doesn't require a join — documented as deliberate.

### `1723722` — matters & workflow (6 tables)
- **Added:** `matter.py` (`MatterType`, `MatterStatus`, `Matter`), `workflow.py`
  (`WorkflowDefinition`, `WorkflowState`, `WorkflowHistory` — polymorphic `entity_type`+`entity_id`),
  migration `c52ee7c83023`.

### `4c814d0` — documents (5 tables) + file storage records
- **Added:** `document.py` (`DocumentType`, `DocumentTemplate`, `DocumentVariable`, `Document`,
  `DocumentVersion`), `storage.py` (`FileStorageRecord` — pulled forward from its originally
  planned Section 10 slot because `document_templates`/`document_versions` need it), migration
  `9a68ef4298ae`.
- **Design decision:** `documents.current_version_id` dropped entirely rather than fighting a
  circular FK with `document_versions` — "latest version" derived via
  `ORDER BY version_number DESC LIMIT 1` instead.

### `04e784c` — financial (4 tables)
- **Added:** `financial.py` (`PaymentMethod`, `Invoice`, `Payment`, `Receipt`), migration
  `cf6b0519b74c`.

### `7f3f0c6` — activity, audit & notifications (3 tables) + ADR-0009
- **Added:** `activity.py` (`ActivityLog`, `AuditLog`, `Notification`), migration `40ce220538c1`,
  `ADR/0009-audit-logs-table-reverses-adr-0007.md`.
- **Modified:** `ADR/0007-audit-logging-without-database-table.md` (added a "Superseded by
  ADR-0009" status line).
- **Fixed:** `AuditLog.metadata` as a Python attribute would shadow SQLAlchemy's own
  `Base.metadata` — renamed to `audit_metadata`, kept the DB column named `"metadata"` via
  `mapped_column("metadata", ...)`.

### `0d1f65f` — scheduling & tags (4 tables)
- **Added:** `scheduling.py` (`Task`, `Appointment`, `Tag`, `MatterTag`), migration `07150e442816`.
- **Fixed:** `Appointment` initially redeclared `created_by` explicitly, duplicating `AuditMixin`'s
  own — removed the redundant declaration, then grepped all model files to confirm no other section
  made the same mistake.

### `544b142` — OCR, QR & backups (4 tables)
- **Added to `storage.py`:** `OcrJob`, `OcrResult` (GIN expression index on
  `to_tsvector('english', extracted_text)`), `QrCodeRecord` (polymorphic), `Backup`; migration
  `ac2214fdce03`.
- Verified the GIN full-text search index actually works against live Postgres with a real
  `to_tsvector`/`plainto_tsquery` query, not just that the migration ran.

### `ed89ee4` — system, config, AI & plugins (7 tables)
- **Added:** `system.py` (`ApplicationSetting`, `FeatureFlag`, `AiRequest`, `AiResponse`,
  `PluginRegistryEntry`, `BackgroundJobRecord`, `SystemEvent`), migration `5c13f11da784`.
- Several tables shaped to match existing Stage 1 in-memory frameworks (`feature_flags` mirrors
  `Settings.feature_flags`, `background_jobs` mirrors `JobRecord`/`JobStatus`, `system_events`
  mirrors a future persisted `EventBus`, `plugin_registry` persists state for modules already
  registered via `ModuleRegistry`) so a future implementation can satisfy the existing port without
  changing it — no wiring done yet.

### `fb24b01` — seed lookup data migration
- **Added:** migration `9963e15f2752` (`op.bulk_insert` against `sa.table()` shadows, not the ORM
  models): India + all Indian states/UTs, Gujarat's 33 districts, 6 roles, 18 permissions, 8 matter
  types, 6 matter statuses, a starter `matter_lifecycle` workflow (6 states), 10 document types, 6
  payment methods, 6 application settings defaults, 5 feature flags (all disabled).
- **Fixed:** seeding real values surfaced 4 existing tests that reused the same fixed names/codes
  now taken by seed data (`"India"`, `"matters:read"`, `"ocr_pipeline"`, ...) — updated those tests
  to generate unique per-run values instead.

### Documentation pass (this commit)
- **Added:** `docs/ERD.md`.
- **Modified:** `docs/Database.md` (full rewrite), `docs/Architecture.md`, `AI_BOOTSTRAP.md`,
  `PROJECT_STATE.json`, `docs/ProjectStatus.md`, `CHANGELOG.md`, `docs/CHANGELOG.md` (this file),
  `docs/FeatureRegistry.md`, `docs/ModuleRegistry.md`, `docs/SessionReport.md`,
  `docs/FolderStructure.md`, `docs/AI_HANDOVER.md`, `docs/Roadmap.md`.
- Final state: 216 backend tests, 9 frontend tests, all passing; ruff/black clean (including
  `backend/alembic/versions/`); 49 tables across 12 migrations, full chain reversibility verified;
  real app's route surface unchanged from Stage 0 (`/api/v1/health`, `/api/v1/version` only).

> **Versioning note (added retroactively):** the sections from here through "Post-Stage-2 —
> Performance Metrics Service" plus "Post-Stage-2 — QA Review Resolution" were each originally
> stamped with their own incrementing patch version (0.3.1 through 0.3.8) as they landed. None of
> those were ever individually `git tag`-released — the `v0.3.0` tag was actually cut on the commit
> that already includes all of this work, so every `**Version:**` field in those sections now reads
> `0.3.0` to match what that tag actually contains (see the root [`CHANGELOG.md`](../CHANGELOG.md)'s
> corrected `[0.3.0]` entry). The one section below that's genuinely a separate, later unit of work —
> "Post-Stage-2 — GitHub Actions CI" — is correctly `0.3.1`, the first tag since `v0.3.0`. Section
> structure and dates throughout are otherwise unchanged — this corrects version *labels* only, not
> the historical record of what happened when.

## Post-Stage-2 — Command Bus

**Version:** 0.3.0 (originally stamped 0.3.1 — see versioning note above)
**Date:** 2026-08-05
**Summary:** Standalone framework addition requested directly by the project owner — not part of a
numbered stage. Adds a `CommandBus` port (single-handler command dispatch, distinct from
`EventBus`'s many-subscriber model) with one in-memory default implementation, following Stage 1's
existing port + default-implementation pattern exactly. Zero business commands. See
[ADR/0010](../ADR/0010-command-bus.md) for the full decision record.
**Breaking changes:** None — purely additive; no existing port, route, or table touched.
**Migration notes:** None — no schema change.

### Command Bus
- **Added:** `backend/src/app/application/interfaces/command_bus.py` (`Command` marker class,
  `CommandHandler` type, `CommandBus` ABC with `register`/`dispatch`, `CommandBusError`),
  `backend/src/app/infrastructure/commands/in_memory_command_bus.py` (`InMemoryCommandBus`),
  `backend/src/app/infrastructure/commands/__init__.py`.
- **Modified:** `backend/src/app/infrastructure/di/container.py` — registers
  `CommandBus -> InMemoryCommandBus` in `configure_container()`, alongside `EventBus`.
- **Added tests:** `backend/tests/unit/test_command_bus.py` (7 tests) — dispatch to the registered
  handler, dispatch returning the handler's failure `Result`, routing by command type,
  unregistered-dispatch raises `CommandBusError`, double-registration raises `CommandBusError`,
  handler exceptions propagate rather than being swallowed, DI container resolves `CommandBus` to
  `InMemoryCommandBus`.
- **Fixed:** ruff `B024` (`Command` declared as an `ABC` with no abstract methods) — `Command` is a
  plain marker class, not an `ABC`, since a command declares only data.
- Final state: 223 backend tests (up from 216), 9 frontend tests (unchanged — no frontend
  involvement), all passing; ruff/black clean; real app's route surface unchanged
  (`/api/v1/health`, `/api/v1/version` only) — this addition touches no route.

## Post-Stage-2 — Query Bus

**Version:** 0.3.0 (originally stamped 0.3.2 — see versioning note above)
**Date:** 2026-08-05
**Summary:** Standalone framework addition requested directly by the project owner — not part of a
numbered stage. Adds a `QueryBus` port mirroring `CommandBus`'s shape exactly (single-handler
dispatch per query type, `Result[R, AppError]` return), resolving [ADR/0010](../ADR/0010-command-bus.md)'s
explicit deferral of a Query bus companion. Zero business queries. See
[ADR/0011](../ADR/0011-query-bus.md) for the full decision record.
**Breaking changes:** None — purely additive; no existing port, route, or table touched.
**Migration notes:** None — no schema change.

### Query Bus
- **Added:** `backend/src/app/application/interfaces/query_bus.py` (`Query` marker class,
  `QueryHandler` type, `QueryBus` ABC with `register`/`dispatch`, `QueryBusError`),
  `backend/src/app/infrastructure/queries/in_memory_query_bus.py` (`InMemoryQueryBus`),
  `backend/src/app/infrastructure/queries/__init__.py`.
- **Modified:** `backend/src/app/infrastructure/di/container.py` — registers
  `QueryBus -> InMemoryQueryBus` in `configure_container()`, alongside `CommandBus`.
- **Added tests:** `backend/tests/unit/test_query_bus.py` (7 tests) — same coverage shape as the
  Command Bus's tests: dispatch to the registered handler, dispatch returning the handler's
  failure `Result`, routing by query type, unregistered-dispatch raises `QueryBusError`,
  double-registration raises `QueryBusError`, handler exceptions propagate, DI container resolves
  `QueryBus` to `InMemoryQueryBus`.
- No lint findings this time — `Query` was written as a plain marker class (not an `ABC`) from the
  start, applying the `B024` lesson learned while building `Command`.
- Final state: 230 backend tests (up from 223), 9 frontend tests (unchanged), all passing;
  ruff/black clean; real app's route surface unchanged (`/api/v1/health`, `/api/v1/version` only).

## Post-Stage-2 — Transaction Pipeline

**Version:** 0.3.0 (originally stamped 0.3.3 — see versioning note above)
**Date:** 2026-08-05
**Summary:** Standalone framework addition requested directly by the project owner — not part of a
numbered stage. Resolves the "transaction wrapping" trade-off both [ADR/0010](../ADR/0010-command-bus.md)
and [ADR/0011](../ADR/0011-query-bus.md) explicitly deferred. Three candidate designs were
presented before writing code; the project owner chose a `CommandBus` decorator over changing
`CommandHandler`'s signature or fixing the unrelated `get_db()` commit bug. See
[ADR/0012](../ADR/0012-transaction-pipeline.md) for the full decision record.
**Breaking changes:** None — purely additive; `Command`/`CommandHandler`/`CommandBus`'s existing
container registration are both untouched.
**Migration notes:** None — no schema change.

### Transaction Pipeline
- **Added:** `backend/src/app/application/interfaces/unit_of_work.py` (`UnitOfWork` ABC with
  `begin`/`commit`/`rollback`, `UnitOfWorkError`),
  `backend/src/app/infrastructure/transactions/in_memory_unit_of_work.py` (`InMemoryUnitOfWork`),
  `backend/src/app/infrastructure/transactions/__init__.py`,
  `backend/src/app/infrastructure/commands/transaction_pipeline_behavior.py`
  (`TransactionPipelineBehavior` — a `CommandBus` decorator taking an inner bus and a `UnitOfWork`
  factory).
- **Modified:** `backend/src/app/infrastructure/di/container.py` — registers `UnitOfWork ->
  InMemoryUnitOfWork` with `singleton=False` (the first non-singleton registration in this
  project — a unit of work is per-operation state, not a shared service). `CommandBus`'s own
  registration is unchanged; the pipeline is available but not applied by default.
  `backend/src/app/infrastructure/commands/__init__.py` — exports `TransactionPipelineBehavior`
  alongside `InMemoryCommandBus`.
- **Added tests:** `backend/tests/unit/test_unit_of_work.py` (7 tests) — begin/commit/rollback
  lifecycle, double-begin raises, commit/rollback-without-begin raise, a new transaction can begin
  after a commit, DI resolves `UnitOfWork` to `InMemoryUnitOfWork`, and resolving it twice returns
  two different instances (proving non-singleton registration).
  `backend/tests/unit/test_transaction_pipeline_behavior.py` (6 tests) — dispatch commits the unit
  of work on a successful `Result`, rolls it back on a failure `Result`, rolls back and re-raises
  on a handler exception, `register()` delegates to the inner bus, and each dispatch gets its own
  fresh unit of work (two distinct instances, each committed exactly once).
- No lint findings.
- Final state: 243 backend tests (up from 230), 9 frontend tests (unchanged), all passing;
  ruff/black clean; real app's route surface unchanged (`/api/v1/health`, `/api/v1/version` only).

## Post-Stage-2 — Caching Abstraction

**Version:** 0.3.0 (originally stamped 0.3.4 — see versioning note above)
**Date:** 2026-08-05
**Summary:** Standalone framework addition requested directly by the project owner — not part of a
numbered stage. Adds a `Cache` port + `InMemoryCache` default, read as a standalone capability
(matching this project's "\<Thing\> Abstraction"/"Foundation" naming convention for standalone
ports) rather than a pipeline behavior wrapping `QueryBus`. See
[ADR/0013](../ADR/0013-caching-abstraction.md) for the full decision record, including why the
`QueryBus`-wrapping reading was set aside.
**Breaking changes:** None — purely additive; no existing port, route, or table touched.
**Migration notes:** None — no schema change.

### Caching Abstraction
- **Added:** `backend/src/app/application/interfaces/cache.py` (`Cache` ABC —
  `get`/`set`/`delete`/`clear`, `set` takes an optional `ttl_seconds`),
  `backend/src/app/infrastructure/cache/in_memory_cache.py` (`InMemoryCache` — dict-backed, lazy
  TTL expiry checked against `time.monotonic()`), `backend/src/app/infrastructure/cache/__init__.py`.
- **Modified:** `backend/src/app/infrastructure/di/container.py` — registers `Cache ->
  InMemoryCache` as a singleton (the default; unlike `UnitOfWork`, a shared cache instance is the
  correct semantics).
- **Added tests:** `backend/tests/unit/test_cache.py` (10 tests) — get on a missing key returns
  `None`, set-then-get, overwrite, delete (present and missing key), clear removes every entry, an
  entry with no TTL never expires, an entry expires once its TTL elapses (clock monkeypatched, no
  real sleep), DI resolves `Cache` to `InMemoryCache`, and two resolves return the same instance
  (singleton).
- No lint findings.
- Final state: 253 backend tests (up from 243), 9 frontend tests (unchanged), all passing;
  ruff/black clean; real app's route surface unchanged (`/api/v1/health`, `/api/v1/version` only).

## Post-Stage-2 — Module Manifest Loader

**Version:** 0.3.0 (originally stamped 0.3.5 — see versioning note above)
**Date:** 2026-08-05
**Summary:** Standalone framework addition requested directly by the project owner — not part of a
numbered stage. Closes a gap `ModuleRegistry`'s own docstring left open: it promised a future
module "only needs to register itself; the core app never needs editing again to pick it up," but
nothing actually knew which packages to import to trigger that registration side effect. See
[ADR/0014](../ADR/0014-module-manifest-loader.md) for the full decision record, including why a
DB-backed loader reading the `plugin_registry` table was set aside as out-of-scope schema-wiring.
**Breaking changes:** None — purely additive; `ModuleRegistry`/`AppModule` and `main.py`'s startup
are both untouched.
**Migration notes:** None — no schema change.

### Module Manifest Loader
- **Added:** `backend/src/app/infrastructure/modules/manifest.py` (`ModuleManifestEntry`,
  `ModuleManifest` with `from_dict()`, `ModuleManifestLoader` with `load_from_file()`/
  `import_enabled()`, `ModuleManifestError`).
- **Modified:** `backend/src/app/infrastructure/modules/__init__.py` — exports the new names
  alongside the existing `AppModule`/`ModuleRegistry`/`registry`.
- **Added tests:** `backend/tests/unit/test_module_manifest_loader.py` (12 tests) — manifest
  parsing (explicit fields, `enabled` defaulting to `true`, empty/missing `modules` key, a missing
  required field raising `ModuleManifestError`), file loading (a real `tmp_path` JSON file, a
  missing file, malformed JSON), and import behavior (only enabled entries imported in manifest
  order via an injectable fake importer, an import failure raises and stops rather than continuing,
  plus two tests against the real default `importlib.import_module` — one importing a real stdlib
  module, one wrapping a real `ModuleNotFoundError`).
- **Fixed:** two test lines exceeded the 100-character limit; `black` auto-wrapped them, no manual
  changes needed.
- Final state: 265 backend tests (up from 253), 9 frontend tests (unchanged), all passing;
  ruff/black clean; real app's route surface unchanged (`/api/v1/health`, `/api/v1/version` only).

## Post-Stage-2 — Architecture Health Check

**Version:** 0.3.0 (originally stamped 0.3.6 — see versioning note above)
**Date:** 2026-08-05
**Summary:** Standalone framework addition requested directly by the project owner — not part of a
numbered stage. Resolves `IMPLEMENTATION_QUEUE.md`'s T15/F7 finding: `configure_container()`
registered factories but nothing resolved them at startup, so a broken factory only failed the
first time a request happened to need it. See [ADR/0015](../ADR/0015-architecture-health-check.md)
for the full decision record, including why this is the one post-Stage-2 addition wired directly
into `main.py`'s startup path (unlike Command Bus, Query Bus, Transaction Pipeline, Caching
Abstraction, and Module Manifest Loader, all left unwired).
**Breaking changes:** None — additive to `Container`/`main.py`; the app's route surface and every
existing registration's factory are untouched. A container that was already broken before this
change would now fail at startup instead of at first request — a behavior change in the direction
T15 asked for, not a regression.
**Migration notes:** None — no schema change.

### Architecture Health Check
- **Added:** `backend/src/app/infrastructure/di/health_check.py` (`ContainerHealthCheckFailure`,
  `ContainerHealthCheckError`, `check_container_health()`, `assert_container_healthy()`).
- **Modified:** `backend/src/app/infrastructure/di/container.py` — `Container` gained
  `registered_interfaces() -> list[type]`. `backend/src/app/infrastructure/di/__init__.py` —
  exports the new names. `backend/src/app/main.py` — `create_app()` calls
  `assert_container_healthy(container)` immediately after `configure_container()`.
  `IMPLEMENTATION_QUEUE.md` — T15 and finding F7 marked done/resolved, pointing at ADR-0015.
- **Added tests:** `backend/tests/unit/test_container_health_check.py` (7 tests) — a healthy
  container reports no failures, a broken factory is caught and reported (not raised) rather than
  propagating, multiple broken factories are all reported in one pass, an empty container is
  trivially healthy, `assert_container_healthy` raises `ContainerHealthCheckError` with the
  failure detail included in the exception message, and the real `configure_container()` result is
  confirmed healthy against the actual app container.
- **Fixed:** one import-order lint finding in the new test file, auto-fixed via `ruff --fix`.
- Final state: 272 backend tests (up from 265), 9 frontend tests (unchanged), all passing;
  ruff/black clean; real app's route surface unchanged (`/api/v1/health`, `/api/v1/version` only)
  — confirmed via the existing health-endpoint integration tests, which import `app.main` and
  therefore exercise the new startup check on every run.

## Post-Stage-2 — Performance Metrics Service

**Version:** 0.3.0 (originally stamped 0.3.7 — see versioning note above)
**Date:** 2026-08-05
**Summary:** Standalone framework addition requested directly by the project owner — not part of a
numbered stage. Unlike the six additions before it, didn't map onto an item already named in an
existing ADR trade-off or `IMPLEMENTATION_QUEUE.md` finding — read as a standalone port via this
project's naming convention (`Cache`/`AuthorizationService`-style "Service", not a pipeline
wrapping `CommandBus`/`QueryBus`, and no new `/metrics` route). See
[ADR/0016](../ADR/0016-performance-metrics-service.md) for the full decision record, including the
three options considered.
**Breaking changes:** None — purely additive; no existing port, route, or table touched.
**Migration notes:** None — no schema change.

### Performance Metrics Service
- **Added:** `backend/src/app/application/interfaces/metrics.py` (`MetricsService` — abstract
  `increment`/`gauge`/`record_duration`, each accepting optional `tags: dict[str, str] | None`,
  plus a concrete `timer()` context-manager convenience built on `record_duration`, the same
  pattern as `EventBus.publish_all()`), `backend/src/app/infrastructure/metrics/logging_metrics_service.py`
  (`LoggingMetricsService` — logs each event as structured JSON to an `app.metrics` logger
  channel, mirroring `LoggingAuditLogger`'s `app.audit` channel), `backend/src/app/infrastructure/metrics/__init__.py`.
- **Modified:** `backend/src/app/infrastructure/di/container.py` — registers `MetricsService ->
  LoggingMetricsService` as a singleton.
- **Added tests:** `backend/tests/unit/test_metrics_service.py` (8 tests) — increment logs a
  structured counter entry (default value 1, and an explicit value + tags), gauge logs a
  structured gauge entry, record_duration logs a structured duration entry, `timer()` records a
  duration on normal exit and also records one then re-raises on an exception (not swallowing
  it), DI resolves `MetricsService` to `LoggingMetricsService`, and two resolves return the same
  instance (singleton).
- **Fixed:** two `ruff` `SIM117` findings (nested `with` statements) in the new test file, fixed by
  combining the context managers into single `with` statements.
- Final state: 280 backend tests (up from 272), 9 frontend tests (unchanged), all passing;
  ruff/black clean; real app's route surface unchanged (`/api/v1/health`, `/api/v1/version` only)
  — this addition touches no route.

## Post-Stage-2 — QA Review Resolution

**Version:** 0.3.0 (originally stamped 0.3.8 — see versioning note above)
**Date:** 2026-08-06
**Summary:** A QA review ([docs/reviews/Stage_2_5_QA_Review.md](reviews/Stage_2_5_QA_Review.md))
evaluated the seven post-Stage-2 framework additions above (Command Bus, Query Bus, Transaction
Pipeline, Caching Abstraction, Module Manifest Loader, Architecture Health Check, Performance
Metrics Service) against Architecture, Performance, SOLID, Maintainability, Security, Scalability,
Thread Safety, Error Handling, and Code Duplication. Nine findings (Q1–Q9) were classified in
`IMPLEMENTATION_QUEUE.md`; two ("Fix Immediately") were cheap, safe, and unblocked, and are fixed
here as T20/T21. The rest are either genuine gaps correctly gated on a dependency that doesn't
exist yet, or already-accepted ADR-documented trade-offs — see `IMPLEMENTATION_QUEUE.md`'s "QA
Review Findings" section for the full classification and rationale.
**Breaking changes:** None — both fixes are behavior-preserving except for the specific bug closed
(cancellation now rolls back where it previously didn't); no port signature, route, or table
touched.
**Migration notes:** None — no schema change.

### T20 — `TransactionPipelineBehavior` rolls back on cancellation (Q1)
- **Problem:** `dispatch()`'s `try`/`except Exception` block did not catch `asyncio.CancelledError`
  (a `BaseException` subclass since Python 3.8, not an `Exception` subclass) — a cancelled dispatch
  (client disconnect, request timeout, server shutdown grace period) skipped `rollback()` entirely,
  leaving the unit of work `_active=True`. Invisible today because `InMemoryUnitOfWork` backs no
  real resource; would become a real leaked-connection/held-lock risk once a resource-backed
  `UnitOfWork` (e.g. wrapping a SQLAlchemy `AsyncSession`) is plugged in.
- **Fixed:** `backend/src/app/infrastructure/commands/transaction_pipeline_behavior.py:47` — widened
  to `except BaseException:`, with an inline comment explaining why `Exception` alone was wrong;
  still re-raises after `rollback()` so cancellation propagates correctly to the caller.
- **Added tests:** `backend/tests/unit/test_transaction_pipeline_behavior.py` grew from 5 to 7 —
  `test_dispatch_rolls_back_and_reraises_on_cancellation` (proves rollback + re-raise for
  `asyncio.CancelledError` specifically) and `test_dispatch_rolls_back_and_reraises_on_a_base_exception`
  (proves the same for an arbitrary `BaseException` subclass generally). The 5 pre-existing tests in
  that file are unchanged and still pass.

### T21 — `MetricsService`/`LoggingMetricsService` document unredacted tags (Q8)
- **Problem:** `tags: dict[str, str]` on `MetricsService.increment/gauge/record_duration` is logged
  verbatim by `LoggingMetricsService` with no redaction — undocumented, so a future caller tagging a
  metric with something like a raw email or document ID would land in plaintext structured logs
  with no warning.
- **Fixed:** `backend/src/app/application/interfaces/metrics.py` and
  `backend/src/app/infrastructure/metrics/logging_metrics_service.py` — one docstring line added to
  each stating `tags` values are not redacted. No behavior change.
- **Added tests:** None needed — the existing `test_increment_accepts_an_explicit_value_and_tags`
  already asserted tags pass through the logger unmodified; the documented behavior and the tested
  behavior now agree.
- Final state: 282 backend tests (up from 280), 9 frontend tests (unchanged). Full unit suite
  (175/175) re-run and passing; the 107 integration tests could not be re-run in this environment
  (no local Postgres/Docker available) — neither T20 nor T21 touches persistence. ruff/black clean
  project-wide; no regression in the three pre-existing `test_transaction_pipeline_behavior.py`
  tests; real app's route surface unchanged (`/api/v1/health`, `/api/v1/version` only) — neither fix
  touches a route.

## Documentation templates — database migration template

**Version:** 0.3.1
**Date:** 2026-08-06
**Summary:** Small documentation-tooling addition, committed directly to `main` (commit `73df68c`)
between the QA Review Resolution above and the Stage 2.7 CI work below — not part of either. Adds
`docs/templates/DatabaseMigrationTemplate.md`, the skeleton for documenting a new Alembic migration
in `docs/Database.md`/`docs/ERD.md` (documents a migration, doesn't generate one — the migration
file itself is source code). Updates `docs/templates/README.md`'s template table with 8 rows that
had been missing (`ADR_Template.md`, `ArchitectureDecisionTemplate.md`, `Feature_Template.md`,
`Module_Template.md`, `QAReviewTemplate.md`, `SessionReportTemplate.md`, `ReleaseTemplate.md`,
`DatabaseMigrationTemplate.md` itself) and generalizes its "how to use a template" guidance beyond
just review-type documents.
**Files:** `docs/templates/DatabaseMigrationTemplate.md` (new), `docs/templates/README.md`
(modified).
**Breaking changes:** None. **Migration notes:** None — no schema/code change, documentation only.

## Stage 2.7 — GitHub Actions CI

**Version:** 0.3.1 (originally stamped 0.3.9 — this one's correct as its own release, see versioning note above)
**Date:** 2026-08-06
**Summary:** A mini-stage, distinct from the numbered Stage 0–2 sequence and the post-Stage-2
framework additions above: continuous integration for every push and pull request. Plan reviewed
and iterated in two passes (an initial proposal, then seven explicit project-owner decisions
overriding several of its defaults) before any implementation. See
[ADR/0017](../ADR/0017-github-actions-ci.md) for the full decision record and
`IMPLEMENTATION_QUEUE.md`'s Stage 2.7 section for the task-by-task detail.
**Breaking changes:** None — no application code touched. `engines` in both `package.json` files is
new and raises the project's previously-undeclared "Node 20+" floor to `>=24.13.1`; anyone
developing on an older Node version will now see an `npm` engine-mismatch warning (not a hard
block, by npm's default behavior).
**Migration notes:** None — no schema, port, or route change.

### GitHub Actions CI
- **Added:** `.github/workflows/backend.yml` (checkout, `setup-python` pinned to 3.14, `setup-uv`
  pinned by commit hash to v9.0.0, `uv sync --locked`, `ruff check`, `black --check`,
  `pytest tests/unit` with JUnit output, an application-import/boot smoke test
  `from app.main import app`, failure-only test-result artifact upload),
  `.github/workflows/frontend.yml` (checkout, `setup-node` pinned to 24.13.1 with npm caching,
  `npm ci`, `eslint`, `prettier --check`, `vitest run` with dual default+junit reporters,
  failure-only test-result artifact upload), `.github/workflows/release.yml` (build verification
  only — `npm ci` at root and in `frontend/`, `npm run build`, uploads `frontend/dist/` and
  `dist-electron/` as 7-day artifacts; explicitly **not** a packaging or deployment pipeline despite
  the name), `ADR/0017-github-actions-ci.md`. All three workflows share identical triggers (`push`
  to `main`/`feature/**`/`hotfix/**`/`release/**`, `pull_request` targeting `main`), a
  per-workflow-per-ref `concurrency` cancellation group, and least-privilege
  `permissions: contents: read`.
- **Modified:** `package.json` and `frontend/package.json` — added `engines: {"node": ">=24.13.1",
  "npm": ">=11.11.1"}` to both, matching the project's actual current tool versions. `README.md` —
  three workflow status badges, updated Prerequisites. `docs/DevelopmentGuide.md` — new
  "Continuous Integration" section, updated Prerequisites.
- **Explicitly out of scope, recorded not implemented:** integration tests and Docker and
  deployment (all per direct project-owner decision — see ADR/0017's Future Impact), and three
  backlog items recorded but not built: Dependabot (`IMPLEMENTATION_QUEUE.md` T38), a pull request
  template (T39), issue templates (T40).
- **Verified locally, not yet verified live:** every command each workflow runs was confirmed
  passing directly in this environment first — `ruff check`/`black --check`/`pytest tests/unit`
  (175 passed)/the import smoke test all succeeded in `backend/`; the dual-reporter `vitest`
  invocation succeeded in `frontend/` (9 passed) and correctly wrote a JUnit report; the root
  `npm run build` succeeded, producing both `frontend/dist/` and `dist-electron/`. **A real GitHub
  Actions run has not been observed** — that requires a commit and push, a confirm-first action not
  taken as part of implementation; tracked as `IMPLEMENTATION_QUEUE.md` T35, the one open item in
  this stage.
- Final state: 282 backend tests / 9 frontend tests, both unchanged by this stage (no application
  code touched). ruff/black/eslint/prettier all still clean, confirmed by the same manual runs used
  to verify the workflow commands themselves.
