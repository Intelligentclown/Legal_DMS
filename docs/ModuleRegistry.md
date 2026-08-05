# Module Registry

## Backend — Stage 0 (foundation)

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `infrastructure.config` | `backend/src/app/infrastructure/config/` | Env-driven settings | `Settings`, `get_settings()` | Complete | AI |
| `infrastructure.logging` | `backend/src/app/infrastructure/logging/` | Structured logging | `configure_logging()`, `get_logger()` | Complete | AI |
| `infrastructure.database` | `backend/src/app/infrastructure/database/` | SQLAlchemy engine/session | `Base`, `get_db()` | Complete | AI |
| `presentation.api.v1` | `backend/src/app/presentation/api/v1/` | Versioned HTTP routes | `router` (health, version) | Complete for current scope | AI |
| `presentation.middleware` | `backend/src/app/presentation/middleware/` | Cross-cutting HTTP concerns | `RequestIDMiddleware`, `LoggingMiddleware`, `register_exception_handlers()` | Complete | AI |

## Backend — Stage 1 (core architecture)

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `domain.common` | `backend/src/app/domain/common/` | Base entity/value/result types | `Entity`, `AggregateRoot`, `ValueObject`, `Result[T, E]` | Complete (pattern only) | AI |
| `domain.events` | `backend/src/app/domain/events/` | Domain event base | `DomainEvent` | Complete (pattern only) | AI |
| `application.common` | `backend/src/app/application/common/` | Reusable app-layer building blocks | `BaseService[T]`, `Validator[T]`/`validate_all()`, `PageRequest`/`PageResult[T]`, `SortSpec`/`FilterSpec`/`SearchQuery` | Complete | AI |
| `application.errors` | `backend/src/app/application/errors/` | Deliberate exception hierarchy | `AppError`, `ValidationError`, `NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`, `UnexpectedError` | Complete | AI |
| `application.interfaces` | `backend/src/app/application/interfaces/` | Framework-agnostic ports | `AbstractRepository`, `EventBus`, `JobQueue`/`Job`, `FileStorage`, `Notifier`, `AuthenticationProvider`/`AuthorizationService`/`CurrentUser`, `AuditLogger`, `SearchIndex`, `FeatureFlagProvider` | Complete for Stage 1 scope | AI |
| `application.workflow` | `backend/src/app/application/workflow/` | Generic state machine | `WorkflowDefinition`, `WorkflowEngine`, `Transition`, `WorkflowError` | Complete (framework only) | AI |
| `infrastructure.di` | `backend/src/app/infrastructure/di/` | Dependency injection container | `Container`, `configure_container()` | Complete | AI |
| `infrastructure.persistence` | `backend/src/app/infrastructure/persistence/` | Repository implementations | `SqlAlchemyRepository[ModelT]` | Complete (generic base) | AI |
| `infrastructure.events` | `backend/src/app/infrastructure/events/` | Event bus implementation | `InMemoryEventBus` | Complete (Stage 1 default) | AI |
| `infrastructure.jobs` | `backend/src/app/infrastructure/jobs/` | Job queue implementation | `InMemoryJobQueue` | Complete (Stage 1 default) | AI |
| `infrastructure.storage` | `backend/src/app/infrastructure/storage/` | File storage implementation | `LocalFileStorage` | Complete (Stage 1 default) | AI |
| `infrastructure.notifications` | `backend/src/app/infrastructure/notifications/` | Notifier implementation | `LoggingNotifier` | Complete (Stage 1 default) | AI |
| `infrastructure.auth` | `backend/src/app/infrastructure/auth/` | Auth/authz implementations | `AnonymousAuthenticationProvider`, `PermissiveAuthorizationService` | Complete (no-login default) | AI |
| `infrastructure.audit` | `backend/src/app/infrastructure/audit/` | Audit logger implementation | `LoggingAuditLogger` | Complete (Stage 1 default, no DB table — ADR/0007) | AI |
| `infrastructure.search` | `backend/src/app/infrastructure/search/` | Search index implementation | `InMemorySearchIndex` | Complete (Stage 1 default) | AI |
| `infrastructure.modules` | `backend/src/app/infrastructure/modules/` | Plugin/module registry | `AppModule`, `ModuleRegistry`, `registry` | Complete (empty registry) | AI |
| `presentation.common` | `backend/src/app/presentation/common/` | Response wrapper + CRUD router factory | `ApiResponse[T]`, `paginated_response()`, `build_crud_router()` | Complete (factory proven test-only) | AI |
| `workers` | `backend/src/app/workers/` | Job registry | `JobRegistry`, `NoOpJob`, `registry` | Complete (no business jobs) | AI |

## Frontend — Stage 0 (foundation)

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `app.providers` | `frontend/src/app/providers/` | Composition root | `ThemeProvider`, `NotificationProvider`, `AppProviders` | Complete | AI |
| `presentation.layouts` | `frontend/src/presentation/layouts/` | Page chrome | `MainLayout` | Complete for current scope | AI |
| `presentation.pages` | `frontend/src/presentation/pages/` | Route-level pages | `HealthCheckPage` | Complete for current scope | AI |
| `presentation.components` | `frontend/src/presentation/components/` | Shared UI | `ErrorBoundary`, `LoadingSpinner`, `Notification` | Complete for current scope | AI |
| `presentation.components.ui` | `frontend/src/presentation/components/ui/` | shadcn/ui primitives | `Button` | Minimal (one component) | AI |
| `infrastructure.api` | `frontend/src/infrastructure/api/` | Backend HTTP client | `httpClient`, `HttpError` | Complete | AI |
| `infrastructure.ipc` | `frontend/src/infrastructure/ipc/` | Electron IPC bridge | `ipcBridge` | Complete for current scope | AI |
| `shared` | `frontend/src/shared/` | Config/utils/constants | `env`, `cn()` | Complete for current scope | AI |

## Frontend — Stage 1

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `domain.types` | `frontend/src/domain/types/` | Shared TS types | `HealthStatus`, `AppVersion`, `Result<T, E>` | Complete | AI |
| `shared.types` | `frontend/src/shared/types/` | Query/pagination TS types | `PageRequest`, `PaginatedResponse<T>`, `SortSpec`, `FilterSpec`, `SearchQuery` | Complete | AI |

## Electron

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `main` | `electron/main.ts` | App lifecycle, secure `BrowserWindow` | — (entrypoint) | Complete | AI |
| `preload` | `electron/preload.ts` | contextBridge API surface | `window.api.getAppInfo()` | Minimal (one method) | AI |
| `ipc.channels` | `electron/ipc/channels.ts` | IPC channel whitelist | `IpcChannels` | Complete for current scope | AI |

"Owner: AI" reflects that this project has been built by an AI coding assistant in collaboration
with the project's human owner — update this column if/when human contributors own specific
modules. "Complete for Stage 1 scope" / "Stage 1 default" labels mean: the port is stable, but the
concrete implementation is deliberately minimal (in-memory/local/logging) and expected to be
swapped for a real backend once a feature needs one — that swap should never require touching the
port itself or its callers.
