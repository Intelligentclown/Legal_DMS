# Tech Stack

Versions below are what's actually pinned in the lockfiles as of Stage 0 (2026-08-05). Re-check
`backend/pyproject.toml` / `backend/uv.lock` and `frontend/package.json` / `package-lock.json`
before trusting exact versions later — they will drift.

## Desktop Shell

- **Electron** `43.3.0` — cross-platform desktop shell. Main process in [`electron/main.ts`](../electron/main.ts),
  preload bridge in [`electron/preload.ts`](../electron/preload.ts).
- **electron-builder** `26.x` — packages the app for Win/Mac/Linux (`electron-builder.yml`).

## Frontend

- **React** `19.2` + **TypeScript** `~6.0` — UI layer.
- **Vite** `8.x` — dev server and bundler (`frontend/vite.config.ts`).
- **Tailwind CSS** `4.3` — CSS-first config via `@tailwindcss/vite`, theme variables in
  `frontend/src/index.css` (no `tailwind.config.ts` needed in v4).
- **shadcn/ui** — component source lives in `frontend/src/presentation/components/ui/`. Copied-in
  components, not an npm dependency. See [KnownIssues.md](KnownIssues.md) for a CLI caveat on Windows.
- **react-router-dom** `7.18` — client-side routing.
- **class-variance-authority**, **clsx**, **tailwind-merge**, **radix-ui**, **lucide-react** —
  shadcn/ui's usual supporting libraries.
- **ESLint** `10.x` (flat config) + **Prettier** `3.x` — replaces the Vite scaffold's default oxlint,
  per the project's tooling requirements.
- **Vitest** `4.x` + **React Testing Library** `16.x` + **jsdom** — testing.

## Backend

- **Python** `>=3.12` (developed against 3.13/3.14 locally).
- **FastAPI** `0.115+` on **Uvicorn** — async web framework.
- **SQLAlchemy** `2.x` (async, `asyncpg` driver) — ORM.
- **Alembic** (async template) — migrations.
- **pydantic-settings** — typed, env-driven configuration.
- **uv** — package manager and virtualenv/lockfile tool (`backend/pyproject.toml`, `backend/uv.lock`).
- **Ruff** + **Black** — linting and formatting.
- **Pytest** + **pytest-asyncio** + **httpx** (via FastAPI's `TestClient`) — testing.

## Database

- **PostgreSQL 16** (Alpine image), run locally via the root [`docker-compose.yml`](../docker-compose.yml).

## Why these choices

See [ADR/0003-electron-react-fastapi-postgres-stack.md](../ADR/0003-electron-react-fastapi-postgres-stack.md)
for the reasoning, and [ADR/0002-clean-architecture-layering.md](../ADR/0002-clean-architecture-layering.md)
for why the codebase is layered the way it is.
