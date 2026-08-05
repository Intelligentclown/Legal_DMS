# Development Guide

## Prerequisites

- Docker Desktop (local Postgres)
- Node.js 20+ and npm
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)

## First-time setup

```bash
# 1. Database
cp .env.example .env
docker compose up -d

# 2. Backend
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
cd ..

# 3. Frontend
cd frontend
cp .env.example .env
npm install
cd ..

# 4. Electron/root
npm install
```

## Running everything

Three processes, three terminals:

```bash
# Terminal 1 — backend
cd backend && uv run uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev

# Terminal 3 — Electron (waits for the Vite dev server, then launches)
npm run electron:dev
```

Or `npm run dev` from the repo root runs frontend + Electron together via `concurrently` (start
the backend separately — different toolchain/venv).

## Running tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm run test        # single run
cd frontend && npm run test:watch   # watch mode
```

## Linting & formatting

```bash
# Backend
cd backend && uv run ruff check src tests alembic
cd backend && uv run black --check src tests alembic

# Frontend
cd frontend && npm run lint
cd frontend && npm run format:check   # or `format` to auto-fix
```

## Database migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "describe your change"
uv run alembic upgrade head
```

`alembic/env.py` reads the connection string from the app's own `Settings` (i.e. your `.env`), not
from `alembic.ini` — never hardcode a URL there.

## Building for production

```bash
npm run build     # compiles electron/*.ts and builds the frontend
npm run dist       # build + electron-builder packaging (Win/Mac/Linux per electron-builder.yml)
```

The backend is not currently bundled into the Electron package — it runs as a standalone service.
See [FutureIdeas.md](FutureIdeas.md) for the deferred packaging story.

## Documentation discipline

Whenever a stage of work finishes:

1. Update [ProjectStatus.md](ProjectStatus.md) — the single source of truth for what's done/pending.
2. Update [CHANGELOG.md](CHANGELOG.md) with what was added/modified.
3. Update [AI_HANDOVER.md](AI_HANDOVER.md) so a fresh session/model can continue without asking
   questions.
4. If an architectural decision was made (or reversed), add/update an ADR in [`/ADR`](../ADR/).
5. Update [Database.md](Database.md) / [API.md](API.md) if the schema or endpoints changed.

A stage isn't done until its documentation is. See [KnownIssues.md](KnownIssues.md) for anything
discovered but not (yet) fixed.
