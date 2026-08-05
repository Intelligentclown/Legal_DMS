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
