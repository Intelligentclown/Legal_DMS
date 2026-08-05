# Project Status

**Current Stage:** Stage 1 — Core Architecture & Domain Foundation
**Current Version:** 0.2.0
**Last Updated:** 2026-08-05
**Overall Completion:** Stage 0 + Stage 1 complete (100% of their scope). 0% of the overall
project — Stages 0–1 are infrastructure/framework only, no business features exist. See
[PROJECT_STATE.json](../PROJECT_STATE.json) for the machine-readable version of this file.

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

## Pending

Stage 2 is undefined — nothing planned in detail. See [Roadmap.md](Roadmap.md).

## Blocked Tasks

None.

## Known Issues

Same two open items carried since Stage 0, both documented in [KnownIssues.md](KnownIssues.md):
1. shadcn/ui CLI (`init`/`add`) is broken on this Windows environment — worked around by hand
   authoring components.
2. `react-router-dom` has one open high-severity advisory not applicable to this project's usage
   (no RSC/framework mode) — accepted, documented, to be re-checked on upgrade.

No new issues from Stage 1.

## Technical Debt

None accrued — every Stage 1 port has exactly one minimal, tested default implementation, and
every deliberate scope limitation (e.g. audit logging without a DB table, search sort not applied
by the in-memory index, CRUD router factory not mounted anywhere real) is documented rather than
silently left as a gap.

## Upcoming Stage

Stage 2 is undefined — no plan exists yet. Whoever picks this up next should get explicit
direction from the user before choosing what Stage 2 covers (see [AI_HANDOVER.md](AI_HANDOVER.md)
and [AI_BOOTSTRAP.md](../AI_BOOTSTRAP.md)).

## Estimated Remaining Work

Not estimable yet — the full feature scope (Matter/Client/Property Management, Document
Automation, OCR, QR, Search, Reports, Payments, AI, Authentication) has no sizing or sequencing
decided.
