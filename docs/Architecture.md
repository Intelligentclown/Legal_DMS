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
  rules live here once they exist (none yet in Stage 0).
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
domain/            pure entities & value objects (Entity, ValueObject base classes)
application/
  errors/          AppError hierarchy (ValidationError, NotFoundError, ConflictError, ...)
  interfaces/       ports for future use cases — empty in Stage 0
infrastructure/
  config/          pydantic-settings Settings, env-driven
  logging/         structured JSON logging (console + rotating file)
  database/        SQLAlchemy Base, async engine/session, get_db() dependency
  persistence/      future repository implementations — empty in Stage 0
presentation/
  api/v1/          health, version routers; aggregated in router.py
  middleware/      RequestIDMiddleware, LoggingMiddleware, exception handlers
workers/            placeholder for future background jobs (OCR, indexing)
main.py             FastAPI app factory — wires config, logging, CORS, middleware, routers
```

Dependency injection is FastAPI's own `Depends()` system: routes declare `SettingsDep` /
`DBSessionDep` (see [`presentation/api/deps.py`](../backend/src/app/presentation/api/deps.py))
rather than importing infrastructure singletons directly. When repository interfaces exist, they'll
follow the same pattern — a port in `application/interfaces`, a concrete implementation in
`infrastructure/persistence`, wired via `Depends`.

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
  types/              shared TS types (HealthStatus, AppVersion, ...)
infrastructure/
  api/                httpClient — fetch wrapper reading VITE_API_BASE_URL
  ipc/                ipcBridge — typed wrapper over window.api (Electron preload surface)
shared/
  config/             env.ts — typed import.meta.env access
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
