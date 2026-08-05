# Module Registry

## Backend

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `domain.common` | `backend/src/app/domain/common/` | Base `Entity`/`ValueObject` patterns | `Entity`, `ValueObject` | Complete (pattern only) | AI |
| `application.errors` | `backend/src/app/application/errors/` | Deliberate exception hierarchy | `AppError`, `ValidationError`, `NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`, `UnexpectedError` | Complete | AI |
| `application.interfaces` | `backend/src/app/application/interfaces/` | Future repository ports | — (empty) | Placeholder | AI |
| `infrastructure.config` | `backend/src/app/infrastructure/config/` | Env-driven settings | `Settings`, `get_settings()` | Complete | AI |
| `infrastructure.logging` | `backend/src/app/infrastructure/logging/` | Structured logging | `configure_logging()`, `get_logger()` | Complete | AI |
| `infrastructure.database` | `backend/src/app/infrastructure/database/` | SQLAlchemy engine/session | `Base`, `get_db()` | Complete | AI |
| `infrastructure.persistence` | `backend/src/app/infrastructure/persistence/` | Future repository implementations | — (empty) | Placeholder | AI |
| `presentation.api.v1` | `backend/src/app/presentation/api/v1/` | Versioned HTTP routes | `router` (health, version) | Complete for Stage 0 scope | AI |
| `presentation.middleware` | `backend/src/app/presentation/middleware/` | Cross-cutting HTTP concerns | `RequestIDMiddleware`, `LoggingMiddleware`, `register_exception_handlers()` | Complete | AI |
| `workers` | `backend/src/app/workers/` | Future background jobs | — (empty) | Placeholder | AI |

## Frontend

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `app.providers` | `frontend/src/app/providers/` | Composition root | `ThemeProvider`, `NotificationProvider`, `AppProviders` | Complete | AI |
| `presentation.layouts` | `frontend/src/presentation/layouts/` | Page chrome | `MainLayout` | Complete for Stage 0 scope | AI |
| `presentation.pages` | `frontend/src/presentation/pages/` | Route-level pages | `HealthCheckPage` | Complete for Stage 0 scope | AI |
| `presentation.components` | `frontend/src/presentation/components/` | Shared UI | `ErrorBoundary`, `LoadingSpinner`, `Notification` | Complete for Stage 0 scope | AI |
| `presentation.components.ui` | `frontend/src/presentation/components/ui/` | shadcn/ui primitives | `Button` | Minimal (one component) | AI |
| `application.services` | `frontend/src/application/services/` | Future use-case orchestration | — (empty) | Placeholder | AI |
| `domain.types` | `frontend/src/domain/types/` | Shared TS types | `HealthStatus`, `AppVersion` | Complete for Stage 0 scope | AI |
| `infrastructure.api` | `frontend/src/infrastructure/api/` | Backend HTTP client | `httpClient`, `HttpError` | Complete | AI |
| `infrastructure.ipc` | `frontend/src/infrastructure/ipc/` | Electron IPC bridge | `ipcBridge` | Complete for Stage 0 scope | AI |
| `shared` | `frontend/src/shared/` | Config/utils/constants | `env`, `cn()` | Complete for Stage 0 scope | AI |

## Electron

| Module | Location | Purpose | Public Interface | Status | Owner |
|---|---|---|---|---|---|
| `main` | `electron/main.ts` | App lifecycle, secure `BrowserWindow` | — (entrypoint) | Complete | AI |
| `preload` | `electron/preload.ts` | contextBridge API surface | `window.api.getAppInfo()` | Minimal (one method) | AI |
| `ipc.channels` | `electron/ipc/channels.ts` | IPC channel whitelist | `IpcChannels` | Complete for Stage 0 scope | AI |

"Owner: AI" reflects that Stage 0 was built by an AI coding assistant in collaboration with the
project's human owner — update this column if/when human contributors own specific modules.
