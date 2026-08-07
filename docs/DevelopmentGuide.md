# Development Guide

## Prerequisites

- Docker Desktop (local Postgres)
- Node.js 24+ and npm 11+ (see `engines` in `package.json`/`frontend/package.json` — bumped from
  the previously-undeclared "20+" as of Stage 2.7's CI work, see
  [ADR/0017](../ADR/0017-github-actions-ci.md))
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (CI is pinned to 3.14, the actual development
  version — the package's own supported floor is unchanged)

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

## Continuous Integration

Three GitHub Actions workflows run on every push to `main`/`feature/**`/`hotfix/**`/`release/**`
and every pull request targeting `main` — see [ADR/0017](../ADR/0017-github-actions-ci.md) for the
full design record:

- **`.github/workflows/backend.yml`** — exactly the "Running tests" and "Linting & formatting"
  backend commands above, plus an application-boot smoke test, against Python 3.14. Runs
  `tests/unit` only (`tests/integration` needs a live Postgres connection — deferred, see
  `IMPLEMENTATION_QUEUE.md`'s Future Expansion list).
- **`.github/workflows/frontend.yml`** — exactly the "Running tests" and "Linting & formatting"
  frontend commands above, against Node 24.13.1.
- **`.github/workflows/release.yml`** — build verification only (`npm run build`): compiles
  `electron/*.ts` and builds the frontend. **Not** a packaging or deployment pipeline yet, despite
  the name — see the file's own header comment and ADR/0017.

If a check fails in CI but passes locally, first confirm you're on the same tool versions CI pins
(Python 3.14, Node 24.13.1/npm 11.11.1 — see each workflow file) before assuming it's
environment-specific.

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

**Canonical document roles and ownership:** each document above has exactly one canonical purpose
and one primary editor — see
[`docs/ImplementationLog/README.md`](ImplementationLog/README.md#canonical-document-roles) for the
full no-duplication rules (implementation detail belongs in `docs/ImplementationLog/`, never
copied into `SessionReport`/`CHANGELOG`/an ADR) and
[Documentation Ownership](ImplementationLog/README.md#documentation-ownership) for who's routinely
responsible for what. Not repeated here — that document is authoritative for both.

**QA gate:** an implementation batch doesn't count as done — and doesn't get documentation
synchronized or merged — until it has a recorded QA Decision (`Approved` /
`Approved with comments` / `Rework required`). See
[`docs/ImplementationLog/README.md`](ImplementationLog/README.md#qa-decision) for the workflow.

## QA review discipline

Every QA/architecture review (whether covering a numbered stage or a set of standalone post-stage
additions) writes its findings to `docs/reviews/<Stage>_QA_Review.md` — e.g.
[`docs/reviews/Stage_2_5_QA_Review.md`](reviews/Stage_2_5_QA_Review.md), and going forward
`Stage_3_QA_Review.md`, `Stage_4_QA_Review.md`, etc. One file per review, named after the stage (or
addition batch) it covers. This is the durable record of what was evaluated, what was found, and
what was deliberately deferred — don't let review findings live only in chat history.
