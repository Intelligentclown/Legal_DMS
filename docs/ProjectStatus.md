# Project Status

**Current Stage:** Stage 2 — Database Architecture & Data Model
**Current Version:** 0.3.0
**Last Updated:** 2026-08-05
**Overall Completion:** Stage 0 + Stage 1 + Stage 2 complete (100% of their scope). 0% of the
overall project — Stages 0–2 are infrastructure/framework/schema only, no business features exist
and nothing is wired to the new schema yet. See [PROJECT_STATE.json](../PROJECT_STATE.json) for the
machine-readable version of this file.

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

## Pending

Stage 3 is undefined — nothing planned in detail. See [Roadmap.md](Roadmap.md).

## Blocked Tasks

None.

## Known Issues

Same two open items carried since Stage 0, both documented in [KnownIssues.md](KnownIssues.md):
1. shadcn/ui CLI (`init`/`add`) is broken on this Windows environment — worked around by hand
   authoring components.
2. `react-router-dom` has one open high-severity advisory not applicable to this project's usage
   (no RSC/framework mode) — accepted, documented, to be re-checked on upgrade.

No new issues from Stage 2.

## Technical Debt

None accrued. Every Stage 1 port still has exactly one minimal, tested default implementation.
Stage 2's schema is deliberately generic/minimal in the two areas with no consuming feature yet
(`ai_requests`/`ai_responses`, `plugin_registry`) rather than guessed at — documented as
intentionally incomplete, not a gap. The five polymorphic `entity_type`+`entity_id` tables trade
away DB-level referential integrity on that column by design — see [ERD.md](ERD.md) for the
accepted trade-off.

## Upcoming Stage

Stage 3 is undefined — no plan exists yet. Whoever picks this up next should get explicit
direction from the user before choosing what Stage 3 covers (see [AI_HANDOVER.md](AI_HANDOVER.md)
and [AI_BOOTSTRAP.md](../AI_BOOTSTRAP.md)). The schema is now ready for a feature to be wired to
it — that's a strong candidate for what Stage 3 becomes, but confirm rather than assume.

## Estimated Remaining Work

Not estimable yet — the full feature scope (Matter/Client/Property Management, Document
Automation, OCR, QR, Search, Reports, Payments, AI, Authentication) has no sizing or sequencing
decided. The database schema those features will sit on is now complete.
