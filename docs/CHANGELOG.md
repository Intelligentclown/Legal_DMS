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
