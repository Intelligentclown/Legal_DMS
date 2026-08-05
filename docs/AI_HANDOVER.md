# AI Handover

*Assume you are a fresh AI model with no memory of this project's prior sessions. This document
should let you continue immediately without asking clarifying questions about what already
exists. If you haven't already, read [`/AI_BOOTSTRAP.md`](../AI_BOOTSTRAP.md) and
[`/PROJECT_STATE.json`](../PROJECT_STATE.json) first — this file is the deep-dive that follows them.*

## Project Summary

Legal Document & Matter Management System — a desktop app (Electron + React/TS frontend, Python
FastAPI backend, PostgreSQL database) for a legal documentation office. Built to be developed over
many months across many sessions. **Stage 0 (infrastructure), Stage 1 (core architecture), and
Stage 2 (database schema) are all complete.** Read [Context.md](Context.md) for fuller narrative if
this handover isn't enough — note Context.md was written at the end of Stage 0 and hasn't been
rewritten since; treat its "Current Stage"/"Pending Work" sections as stale relative to this file
and `ProjectStatus.md`.

## Current Architecture

Clean Architecture on both sides (domain/application/infrastructure/presentation), detailed in
[Architecture.md](Architecture.md). As of Stage 1, the backend has a full reusable platform:
a hand-rolled DI container, repository pattern, base service, validation/pagination/query/response
frameworks, a generic CRUD router factory, an event bus, a background job framework, file storage/
notification/search/auth/audit abstractions (each with exactly one minimal default
implementation), a plugin/module registry, a workflow engine, and feature flags. As of Stage 2, the
backend also has the **complete 49-table database schema** (persistence-layer SQLAlchemy models +
Alembic migrations + seed data — see [Database.md](Database.md) and [ERD.md](ERD.md)) — but that
schema is **not wired to anything**: no repository, service, or route reads or writes through it
yet. Every framework piece and every table is scaffolding — no business feature has been built on
top of any of it yet.

## Completed Features

None — Stages 0–2 are infrastructure/framework/schema only. See
[FeatureRegistry.md](FeatureRegistry.md) (currently just the "System Health Check" plumbing
feature, not a business feature).

## Current Stage

Stage 2 — Database Architecture & Data Model. **Complete and verified** (216 backend + 9 frontend
tests passing, lint clean, all 12 migrations reversible individually and as a full chain, no
regression in the real app's route surface). See [ProjectStatus.md](ProjectStatus.md) for the full
checklist. **No Stage 3 plan exists.**

## Pending Work

Everything past Stage 2. **Nothing is scoped yet** — see [Roadmap.md](Roadmap.md). The most likely
next step is wiring a real feature (repository → service → route) to a slice of the Stage 2 schema,
but that must be confirmed with the project owner, not assumed.

## Open Issues / Known Bugs

Two tooling caveats, no code bugs — full detail in [KnownIssues.md](KnownIssues.md):
1. shadcn/ui CLI (`init`/`add`) doesn't work on this Windows environment (writes to a literal `@`
   folder instead of resolving the path alias). Add new shadcn components by hand-copying from
   ui.shadcn.com into `frontend/src/presentation/components/ui/` and fixing the `cn` import path
   to `@/shared/utils/cn`.
2. `react-router-dom` has one open `npm audit` advisory (RSC-mode CSRF) not applicable to this
   project (no RSC/framework mode used). Re-verify on any `react-router-dom` upgrade.

Stage-1-specific patterns worth knowing (not bugs, but easy to trip over if copied wrong):
3. **pytest-asyncio + cached SQLAlchemy engines don't mix.** The app's `get_engine()` singleton is
   `lru_cache`d for production (one process, one event loop). Tests get a fresh event loop per
   function by default, so an async-DB test must create and dispose its own engine — see
   `tests/conftest.py`'s shared `db_session` fixture for the pattern (used by every Stage 2 model
   test too).
4. **Generic FastAPI route factories can't use their own PEP 695 type parameters as runtime
   annotations.** `ReadSchema`/`CreateSchema`/etc. in `build_crud_router[T, ReadSchema, ...]`'s
   signature are `TypeVar` placeholders at runtime, not the concrete classes — annotating a nested
   route handler's body parameter with them (under postponed evaluation) makes FastAPI silently
   treat the JSON body as an unresolvable query parameter. `presentation/common/crud_router_factory.py`
   documents the fix (annotate with the actual runtime arguments, drop `from __future__ import
   annotations` in that one file) — read its docstring before writing a similar factory.

Stage-2-specific patterns worth knowing:
5. **`CheckConstraint(name=...)` double-prefixes if given the full expected name.** Pass a short
   logical name (`name="address_type"`), not the full constraint name — the project's
   `naming_convention` builds the `ck_<table>_` prefix itself. Does not apply to `Index(name=...)`,
   which is used verbatim.
6. **Never name a mapped attribute `metadata`.** It shadows SQLAlchemy's own `Base.metadata` class
   attribute. See `AuditLog.audit_metadata` (Python name) mapped to the `"metadata"` DB column via
   `mapped_column("metadata", ...)` for the pattern.
7. **`alembic/env.py` must actually import the models package**, not just reference it in a
   comment — otherwise `Base.metadata` is empty and `alembic revision --autogenerate` silently
   generates nothing. Already fixed and in place; don't remove the
   `from app.infrastructure.persistence import models` import.

## Database Status

**Complete 49-table schema** (Stage 2) — see [Database.md](Database.md) and [ERD.md](ERD.md) for
full detail. **Nothing is wired to it yet**: no repository, service, or API route reads or writes
through any of these tables. `SqlAlchemyRepository[ModelT]` (Stage 1) already works against any of
them generically without new code, if a future feature needs to start there.

## API Status

`GET /api/v1/health` and `GET /api/v1/version` only — unchanged since Stage 0. See
[API.md](API.md) (not yet updated for Stage 1/2 — still accurate; the CRUD router factory added in
Stage 1 was deliberately never mounted, and Stage 2 added zero routes).

## Folder Structure

[FolderStructure.md](FolderStructure.md) is current as of Stage 2 (updated in this session's
documentation pass). [Architecture.md](Architecture.md) has the fuller narrative for what goes
where and why.

## Important Decisions

Read the ADRs in [`/ADR`](../ADR/) before making architectural changes:
- **0001–0005** (Stage 0): ADR practice itself, Clean Architecture layering, the tech stack
  choice, security foundation placeholders, Docker Compose for local Postgres.
- **0006** (Stage 1): why the DI container is hand-rolled rather than a library, and why
  `DBSessionDep` deliberately stays outside it.
- **0007** (Stage 1): why audit logging writes structured logs rather than a database table.
  **Superseded by 0009.**
- **0008** (Stage 2): why Stage 2's SQLAlchemy models are persistence-layer models, not domain
  entities, and why no `relationship()` navigation is declared yet.
- **0009** (Stage 2): why `audit_logs` reverses ADR-0007's "no DB table" decision — Stage 2's
  explicit ask was the concrete driving need ADR-0007 said to wait for.

If you make a new significant architectural decision, **add a new ADR** (`0010-...`), don't just
change things silently.

## Current Branch

`master` (no feature-branch workflow adopted yet — confirm with the project owner before changing
that).

## Files Recently Modified

Stage 2 added `backend/src/app/infrastructure/persistence/models/` (11 model modules + mixins),
12 new files under `backend/alembic/versions/`, and one `backend/tests/integration/test_*.py` per
schema section plus `test_seed_data.py`. See `git log` for the exact commit sequence (11 schema
commits + 1 seed-data commit + this documentation commit), or [CHANGELOG.md](CHANGELOG.md) for the
per-commit file breakdown. (Stage 1, for reference, touched
`backend/src/app/{domain,application,infrastructure,presentation,workers}/**` and added
`frontend/src/domain/types/result.ts` + `frontend/src/shared/types/query.ts`.)

## What Should Be Implemented Next

**Nothing, until the project owner decides what Stage 3 is.** Stage 0, Stage 1, and Stage 2's
charters were all explicit that business features are out of scope. That pattern has now held for
three stages in a row — don't let that turn into an assumption that "the next stage is always more
scaffolding" either. **Ask the user what Stage 3 covers** rather than guessing — the most likely
candidate is wiring a real feature to the Stage 2 schema, but confirm it, and confirm *which*
feature, rather than assuming Matter Management just because it's listed first in the original
charter. Do not add business entities, a real auth mechanism, new major dependencies, or any
repository/service/route touching the Stage 2 tables without that explicit direction.

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

## Recommended Implementation Order (once Stage 3 is scoped)

1. Confirm the first business feature with the project owner (don't assume it's Matter Management
   just because it's listed first in the original charter).
2. Add an ADR if the feature requires an architectural decision beyond what Stages 1–2 already
   established.
3. The schema likely already exists (Stage 2 built all 49 tables) — check [Database.md](Database.md)
   and the relevant `infrastructure/persistence/models/*.py` file before adding new columns/tables;
   only extend the schema if the feature genuinely needs something the design didn't anticipate.
4. Domain entities first (pure, in `domain/`, extending `Entity`/`AggregateRoot` as needed), then
   application use cases (`application/`, likely extending `BaseService`), then infrastructure
   implementations (a real repository via `SqlAlchemyRepository[ModelT]` against the existing Stage
   2 model — likely no new repository code needed at all, just instantiate the generic one — plus a
   real `FileStorage`/`Notifier`/etc. only if the feature needs one beyond what's already
   registered), then presentation (routes via `build_crud_router` or hand-written, components)
   last — inside-out, matching the Clean Architecture dependency direction.
5. If the feature does need a new Alembic migration (new table/column), update
   [Database.md](Database.md) and [ERD.md](ERD.md) to match.
6. Update [API.md](API.md), [FolderStructure.md](FolderStructure.md),
   [FeatureRegistry.md](FeatureRegistry.md) (this will be its first real entry beyond the System
   Health Check), [ModuleRegistry.md](ModuleRegistry.md), [ProjectStatus.md](ProjectStatus.md),
   [PROJECT_STATE.json](../PROJECT_STATE.json), [CHANGELOG.md](CHANGELOG.md), and this file before
   considering the work done.
