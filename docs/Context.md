# Project Context

*A self-contained summary for anyone (human or AI) picking up this project cold. If you only read
one document before starting work, read this one — then [AI_HANDOVER.md](AI_HANDOVER.md) for the
immediate next steps.*

## Project Goal

Build a production-grade **desktop application** — a Legal Document & Matter Management System —
for a legal documentation office that will eventually manage thousands of legal matters. The
project is expected to run over many months, developed across many separate sessions and possibly
different AI models. That's why this `docs/` + `ADR/` set exists: it's the project's persistent
memory, and it must be kept accurate as work progresses.

## Business Rules

None defined yet. Stage 0 (the only stage completed so far) is pure infrastructure — no Matter,
Client, Property, or Document concepts exist in code. Business rules will be defined stage by
stage as those features are scoped; do not invent them speculatively.

## Architecture

Clean Architecture, applied independently to both the backend and the frontend:

```
Presentation → Application → Domain
                    ↑
             Infrastructure (implements Application's ports)
```

Backend: FastAPI (presentation) → use cases (application, currently empty) → entities (domain,
currently just base patterns) ← SQLAlchemy repositories (infrastructure, currently empty).
Frontend: React components/pages (presentation) → use-case orchestration (application, currently
empty) → shared types (domain) ← API/IPC clients (infrastructure).

The rule this protects: business logic never lives inside a UI component or an API route handler,
and database code never lives directly inside a route. See [Architecture.md](Architecture.md) for
the full folder-by-folder breakdown, and
[ADR/0002-clean-architecture-layering.md](../ADR/0002-clean-architecture-layering.md) for why this
was chosen for Stage 0 specifically (paying the layering cost now, while there's no business logic
to migrate, is deliberate).

## Folder Structure

See [FolderStructure.md](FolderStructure.md) for the full annotated tree. Top-level: `backend/`
(Python/FastAPI, its own uv-managed venv/lockfile), `frontend/` (React/Vite, its own npm
lockfile), `electron/` (thin desktop shell, TS compiled via the root `package.json`), `docs/` +
`ADR/` (this project-memory system).

## Coding Standards

Backend: Black + Ruff, full type hints, `AppError` subclasses for deliberate errors, no business
logic in routers. Frontend: strict TypeScript, ESLint (flat config) + Prettier, function
components only (except the necessarily-class-based `ErrorBoundary`), path alias `@/*` → `src/*`.
Full detail in [CodingStandards.md](CodingStandards.md).

## Current Stage

**Stage 0 — Project Foundation. Complete.** Electron launches, React renders, FastAPI serves,
PostgreSQL connects, Alembic is wired, frontend and backend communicate through a live health
check, logging and error handling work, tests pass on both sides, and this documentation set is
up to date. No business features exist by design.

## Completed Work

- Repo skeleton, dev tooling (`.editorconfig`, `.gitignore`, VS Code settings), Postgres via
  `docker-compose.yml`.
- Backend: Clean Architecture folders, `pydantic-settings` config, structured JSON logging
  (console + rotating file), `AppError` hierarchy → consistent JSON error responses, FastAPI app
  factory with CORS/request-ID/logging middleware, SQLAlchemy async engine/session, Alembic (async
  template, DB URL sourced from `Settings`), `/api/v1/health` and `/api/v1/version` endpoints, 10
  passing Pytest tests.
- Electron: secure `BrowserWindow` (`contextIsolation`, no `nodeIntegration`, `sandbox`), locked
  navigation, a minimal typed `contextBridge` IPC surface (`getAppInfo`).
- Frontend: Vite + React 19 + TS, Tailwind v4 (CSS-first config) + a hand-authored shadcn/ui
  `Button`, `ThemeProvider`/`NotificationProvider`/`ErrorBoundary`/`LoadingSpinner`/`MainLayout`,
  react-router-dom routing, `httpClient` + `ipcBridge` infrastructure wrappers,
  `HealthCheckPage` proving the whole stack live, 3 passing Vitest/RTL tests.
- This full documentation set (`docs/` + `ADR/`).

All of the above was verified **live**, not just via unit tests: Postgres (Docker) + Alembic
migration + FastAPI + Vite dev server + Electron were all run together and the health check page
showed real backend data with no console errors.

## Pending Work

Everything past Stage 0. No Stage 1 plan exists yet — see [Roadmap.md](Roadmap.md)'s "Not yet
planned" table for the eventual named scope (Matter/Client/Property Management, Document
Automation, OCR, QR, Search, Reports, Payments, AI, Authentication), none of which has been
scoped, prioritized, or sequenced.

## Important Decisions

Recorded as ADRs in [`/ADR`](../ADR/) — read those for full reasoning:
1. Architecture Decision Records themselves, as a practice.
2. Clean Architecture layering on both frontend and backend.
3. The Electron + React + FastAPI + PostgreSQL stack choice.
4. Security foundation placeholders (what's prepared now vs. deferred to a real auth stage).
5. Local Postgres via Docker Compose.

Also worth knowing (documented in [KnownIssues.md](KnownIssues.md), not ADRs since they're
workarounds rather than architecture decisions): the shadcn/ui CLI is broken on this Windows setup
(worked around by hand-authoring components), and `react-router-dom` carries one open advisory
judged not applicable to this project's usage.

## Known Issues

See [KnownIssues.md](KnownIssues.md) — currently just the two items above. No bugs in shipped
Stage 0 code; both items are tooling caveats with documented workarounds.

## Next Stage Objectives

Undefined. **Do not start any business feature (Matter/Client/Property Management, Document
Automation, OCR, QR, Search, Reports, Payments, AI, or Authentication) without explicit direction
from the project owner first** — Stage 0's charter was explicit that business features are
out of scope until a human decides otherwise. See [AI_HANDOVER.md](AI_HANDOVER.md) for exactly
what to ask before proceeding.
