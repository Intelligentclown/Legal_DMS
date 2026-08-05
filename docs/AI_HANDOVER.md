# AI Handover

*Assume you are a fresh AI model with no memory of this project's prior sessions. This document
should let you continue immediately without asking clarifying questions about what already
exists. If you haven't already, read [`/AI_BOOTSTRAP.md`](../AI_BOOTSTRAP.md) and
[`/PROJECT_STATE.json`](../PROJECT_STATE.json) first — this file is the deep-dive that follows them.*

## Project Summary

Legal Document & Matter Management System — a desktop app (Electron + React/TS frontend, Python
FastAPI backend, PostgreSQL database) for a legal documentation office. Built to be developed over
many months across many sessions. **Stage 0 (infrastructure) and Stage 1 (core architecture) are
both complete.** Read [Context.md](Context.md) for fuller narrative if this handover isn't enough
— note Context.md was written at the end of Stage 0 and hasn't been rewritten for Stage 1; treat
its "Current Stage"/"Pending Work" sections as stale relative to this file and `ProjectStatus.md`.

## Current Architecture

Clean Architecture on both sides (domain/application/infrastructure/presentation), detailed in
[Architecture.md](Architecture.md). As of Stage 1, the backend also has a full reusable platform:
a hand-rolled DI container, repository pattern, base service, validation/pagination/query/response
frameworks, a generic CRUD router factory, an event bus, a background job framework, file storage/
notification/search/auth/audit abstractions (each with exactly one minimal default
implementation), a plugin/module registry, a workflow engine, and feature flags. Every one of
these is framework-only — no business feature has been built on top of any of it yet.

## Completed Features

None — Stages 0–1 are infrastructure/framework only. See
[FeatureRegistry.md](FeatureRegistry.md) (currently just the "System Health Check" plumbing
feature, not a business feature).

## Current Stage

Stage 1 — Core Architecture & Domain Foundation. **Complete and verified** (130 backend + 9
frontend tests passing, lint clean, no regression in the real app's route surface). See
[ProjectStatus.md](ProjectStatus.md) for the full checklist. **No Stage 2 plan exists.**

## Pending Work

Everything past Stage 1. **Nothing is scoped yet** — see [Roadmap.md](Roadmap.md).

## Open Issues / Known Bugs

Two tooling caveats, no code bugs — full detail in [KnownIssues.md](KnownIssues.md):
1. shadcn/ui CLI (`init`/`add`) doesn't work on this Windows environment (writes to a literal `@`
   folder instead of resolving the path alias). Add new shadcn components by hand-copying from
   ui.shadcn.com into `frontend/src/presentation/components/ui/` and fixing the `cn` import path
   to `@/shared/utils/cn`.
2. `react-router-dom` has one open `npm audit` advisory (RSC-mode CSRF) not applicable to this
   project (no RSC/framework mode used). Re-verify on any `react-router-dom` upgrade.

Two Stage-1-specific patterns worth knowing (not bugs, but easy to trip over if copied wrong):
3. **pytest-asyncio + cached SQLAlchemy engines don't mix.** The app's `get_engine()` singleton is
   `lru_cache`d for production (one process, one event loop). Tests get a fresh event loop per
   function by default, so an async-DB test must create and dispose its own engine — see
   `tests/integration/test_sqlalchemy_repository.py`'s `db_session` fixture for the pattern.
4. **Generic FastAPI route factories can't use their own PEP 695 type parameters as runtime
   annotations.** `ReadSchema`/`CreateSchema`/etc. in `build_crud_router[T, ReadSchema, ...]`'s
   signature are `TypeVar` placeholders at runtime, not the concrete classes — annotating a nested
   route handler's body parameter with them (under postponed evaluation) makes FastAPI silently
   treat the JSON body as an unresolvable query parameter. `presentation/common/crud_router_factory.py`
   documents the fix (annotate with the actual runtime arguments, drop `from __future__ import
   annotations` in that one file) — read its docstring before writing a similar factory.

## Database Status

No business tables. Only Alembic's own `alembic_version` table exists. See
[Database.md](Database.md) (not yet updated for Stage 1 — still accurate since Stage 1 added no
tables).

## API Status

`GET /api/v1/health` and `GET /api/v1/version` only — unchanged since Stage 0. See
[API.md](API.md) (not yet updated for Stage 1 — still accurate; the CRUD router factory added in
Stage 1 was deliberately never mounted into the real app).

## Folder Structure

See [FolderStructure.md](FolderStructure.md) for the Stage-0-era tree (not yet updated for Stage
1's many new backend folders — see [Architecture.md](Architecture.md) instead, which *is* current,
for the accurate Stage 1 folder layout under `backend/src/app/`).

## Important Decisions

Read the ADRs in [`/ADR`](../ADR/) before making architectural changes:
- **0001–0005** (Stage 0): ADR practice itself, Clean Architecture layering, the tech stack
  choice, security foundation placeholders, Docker Compose for local Postgres.
- **0006** (Stage 1): why the DI container is hand-rolled rather than a library, and why
  `DBSessionDep` deliberately stays outside it.
- **0007** (Stage 1): why audit logging writes structured logs rather than a database table.

If you make a new significant architectural decision, **add a new ADR** (`0008-...`), don't just
change things silently.

## Current Branch

`master` (no feature-branch workflow adopted yet — confirm with the project owner before changing
that).

## Files Recently Modified

Stage 1 touched `backend/src/app/{domain,application,infrastructure,presentation,workers}/**` and
added `frontend/src/domain/types/result.ts` + `frontend/src/shared/types/query.ts`. See `git log`
for the exact commit sequence (16 subsystem commits + this documentation commit), or
[CHANGELOG.md](CHANGELOG.md) for the per-commit file breakdown.

## What Should Be Implemented Next

**Nothing, until the project owner decides what Stage 2 is.** Both Stage 0's and Stage 1's
charters were explicit that business features are out of scope. That pattern held for two stages
in a row — don't let that turn into an assumption that "the next stage is always more
infrastructure" either. **Ask the user what Stage 2 covers** rather than guessing. Do not add
business entities, a real auth mechanism, or new major dependencies without that explicit
direction.

## Important Warnings

- Don't run `shadcn add`/`shadcn init` expecting it to work — see Known Issues above.
- Don't hardcode a database URL, storage path, or feature flag anywhere — everything reads from
  `Settings` (`backend/.env`) or `VITE_API_BASE_URL` (`frontend/.env`). Copy from the respective
  `.env.example` files; the real `.env` files are gitignored.
- Postgres must be running (`docker compose up -d` from repo root) before `alembic upgrade head`,
  the repository integration tests, or any other DB-touching backend work.
- Every Stage 1 port (`application/interfaces/*.py`) has exactly **one** default implementation,
  chosen to require **zero new dependencies** (in-memory, local filesystem, or logging). When a
  real feature needs a real backend (Redis queue, S3 storage, a real email provider, Postgres
  full-text search, ...), implement it behind the existing port and register it in
  `infrastructure/di/container.py`'s `configure_container()` — don't change the port itself unless
  the feature genuinely can't be expressed through it.
- The backend (`uv`) and frontend (`npm`) are two independent projects with separate lockfiles —
  don't try to unify them into an npm workspace without a deliberate reason.
- Keep this documentation set (`docs/`, `ADR/`, `AI_BOOTSTRAP.md`, `PROJECT_STATE.json`) up to date
  as you work — a stage isn't done until its documentation reflects reality. See
  [DevelopmentGuide.md](DevelopmentGuide.md)'s "Documentation discipline" section.

## Recommended Implementation Order (once Stage 2 is scoped)

1. Confirm the first business feature with the project owner (don't assume it's Matter Management
   just because it's listed first in the original charter).
2. Add an ADR if the feature requires an architectural decision beyond what Stage 1 already
   established.
3. Domain entities first (pure, in `domain/`, extending `Entity`/`AggregateRoot` as needed), then
   application use cases (`application/`, likely extending `BaseService`), then infrastructure
   implementations (a real repository via `SqlAlchemyRepository` or a subclass, a real
   `FileStorage`/`Notifier`/etc. if the feature needs one beyond what's already registered), then
   presentation (routes via `build_crud_router` or hand-written, components) last — inside-out,
   matching the Clean Architecture dependency direction.
4. Add the Alembic migration for any new tables; update [Database.md](Database.md) (bring it
   current — it's been accurate-by-no-change since Stage 0, this will be its first real update).
5. Update [API.md](API.md), [FolderStructure.md](FolderStructure.md) (also due for its first
   real update), [FeatureRegistry.md](FeatureRegistry.md), [ModuleRegistry.md](ModuleRegistry.md),
   [ProjectStatus.md](ProjectStatus.md), [PROJECT_STATE.json](../PROJECT_STATE.json),
   [CHANGELOG.md](CHANGELOG.md), and this file before considering the work done.
