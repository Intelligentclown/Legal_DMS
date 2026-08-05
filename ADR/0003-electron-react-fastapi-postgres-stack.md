# ADR-0003: Electron + React/TypeScript + FastAPI + PostgreSQL stack

**Status:** Accepted
**Date:** 2026-08-03

## Problem

The project charter specified the tech stack directly (Electron, React/TypeScript/Vite/Tailwind/
shadcn, Python/FastAPI, PostgreSQL/SQLAlchemy/Alembic). This ADR records *why* that stack fits the
project, not just that it was mandated — so a future session understands the reasoning rather than
treating it as an arbitrary constraint.

## Options Considered

For each layer, the realistic alternatives at the time:

- **Desktop shell:** Electron vs. Tauri (smaller binaries, Rust-based, less mature ecosystem for a
  team without Rust experience) vs. a pure web app (no offline/desktop-native story).
- **Frontend framework:** React vs. Vue/Svelte — React has the largest ecosystem overlap with
  shadcn/ui specifically, which the charter also mandated.
- **Backend framework:** FastAPI vs. Django (heavier, batteries-included in ways this project
  doesn't need yet) vs. Flask (less structure, no built-in async/typed validation).
- **Database:** PostgreSQL vs. SQLite (too limited for a multi-user, thousands-of-matters system
  with the relational/audit complexity legal data implies) vs. a NoSQL store (legal matter data is
  inherently relational — clients, matters, documents, parties — a poor fit for document stores).

## Decision

Electron + React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui for the desktop/frontend;
Python + FastAPI + SQLAlchemy 2.x (async) + Alembic + PostgreSQL for the backend; uv for Python
dependency management; Ruff + Black (backend) and ESLint + Prettier (frontend) for linting/
formatting; Pytest and Vitest + React Testing Library for testing.

## Reasoning

- **Electron**: mature, cross-platform, and the ecosystem's default choice for shipping a web-tech
  UI as a desktop app — matches the charter directly.
- **React + Vite**: fast HMR, strong typing story with TS, and Vite is the current standard over
  older tooling (CRA is effectively legacy). shadcn/ui specifically targets React + Tailwind.
- **Tailwind v4 + shadcn/ui**: utility CSS avoids stylesheet sprawl at scale; shadcn/ui gives
  owned, editable component source rather than a black-box component library dependency — fits a
  project expected to have a highly specific, evolving UI (legal matter workflows) rather than a
  generic admin dashboard.
- **FastAPI**: async-first, Pydantic-typed request/response validation, automatic OpenAPI docs,
  and pairs cleanly with SQLAlchemy 2.x's async API.
- **PostgreSQL + SQLAlchemy + Alembic**: legal matter data (matters, clients, documents, parties,
  audit trails) is fundamentally relational; Postgres is the production-grade default for that
  shape of data. SQLAlchemy 2.x's typed `Mapped[]` API plus Alembic gives a reviewable, versioned
  schema history — important for a system that will accumulate real client data over time.
- **uv**: substantially faster than pip for install/lock, pyproject-native.

## Trade-offs

- Two independent toolchains (Python venv via uv, Node via npm) to keep running side by side
  during development — documented in [DevelopmentGuide.md](../docs/DevelopmentGuide.md) rather
  than unified, since unifying them (e.g. forcing everything through one process manager) adds
  complexity without a clear benefit at this stage.
- The backend isn't currently bundled into the Electron installer — it runs as a standalone
  process. That packaging story is deliberately deferred (see
  [FutureIdeas.md](../docs/FutureIdeas.md)) rather than solved prematurely.

## Future Impact

This stack is the baseline for all future stages. A future ADR should be written if any layer of
it changes (e.g. adopting Tauri instead of Electron, or a different state-management library on
the frontend) — don't swap technologies silently.
