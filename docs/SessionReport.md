# Session Report

## Session: 2026-08-03 to 2026-08-05 — Stage 0 (Project Foundation)

**Objectives:** Build the complete Stage 0 foundation per the project charter — architecture
proposal approved first, then repo skeleton, backend, Electron shell, frontend, tests on both
sides, and full documentation, with zero business features.

**Completed Tasks:**
1. Presented architecture proposal (overview, folder tree, tech decisions, workflows, standards,
   dependencies, risks, scalability considerations) and got explicit approval before writing code.
2. Repo skeleton & dev tooling.
3. Backend foundation: config, logging, error handling.
4. Backend API + DB: FastAPI app, health/version routes, SQLAlchemy, Alembic.
5. Backend tests: pytest setup + 10 passing tests.
6. Electron shell: main process, secure preload, IPC scaffold.
7. Frontend foundation: Vite/React/TS/Tailwind/shadcn.
8. Frontend-backend E2E proof: HealthCheckPage, verified live.
9. Frontend tests: Vitest/RTL setup + 3 passing tests.
10. Full documentation pass (this document included).

**Problems Encountered & Solutions:**

- **`cors_origins` startup crash.** A `list[str]` settings field made `pydantic-settings` try to
  JSON-decode a comma-separated env value before the custom validator ran, crashing on startup
  with a real `.env` file (in-process smoke tests hadn't caught it because no `.env` existed yet).
  **Fixed** with `Annotated[list[str], NoDecode]`. Caught while verifying against a real `.env` +
  live Postgres container — a reminder that in-process tests without real config files can miss
  this class of bug.
- **Docker not installed initially.** Postgres/Alembic connectivity couldn't be verified in the
  first pass; flagged explicitly as an unverified gap rather than claimed as done. Docker was
  installed mid-session and the gap was closed with a full live verification (migration run,
  `alembic_version` table confirmed via `psql`).
- **shadcn/ui CLI broken on Windows.** `shadcn init` and `shadcn add` both failed — `add` wrote
  files to a literal `@` directory instead of resolving the path alias. **Worked around** by
  installing the underlying dependencies directly and hand-authoring the `Button` component,
  consistent with shadcn's own copy-the-code philosophy. Documented in
  [KnownIssues.md](KnownIssues.md) so future component additions don't hit the same wall
  unprepared.
- **`react-router-dom` audit advisory.** One high-severity advisory (RSC-mode CSRF) has no patched
  release across the entire currently-published `7.x` line. Downgrading to the last unaffected
  version reintroduced several worse, already-patched advisories, so that was reverted. **Accepted**
  as not applicable (no RSC/framework mode used) and documented for re-check on upgrade.
- **TypeScript `baseUrl` deprecation** and **`erasableSyntaxOnly`** disallowing constructor
  parameter-property shorthand — both hit during the frontend build and fixed by removing
  `baseUrl` (kept `paths` alone) and rewriting `HttpError`'s constructor without the shorthand.
- **React `set-state-in-effect` lint rule** flagged synchronous `setState` calls at the top of
  `HealthCheckPage`'s data-fetching effect. Fixed by moving the reset calls into the retry button's
  click handler instead of the effect body.

**Files Modified:** See [CHANGELOG.md](CHANGELOG.md) for the full per-commit breakdown (8 commits
across repo/backend/electron/frontend, plus this documentation commit).

**Documentation Updated:** All of `docs/` and `ADR/` created fresh this session (this is the first
session).

**Tests Executed:**
- Backend: `uv run pytest` — 10 passed.
- Frontend: `npm run test` — 3 passed.
- Both: linters (`ruff`, `black --check`, `eslint`, `prettier --check`) clean throughout.
- Live E2E: Postgres (Docker) + FastAPI + Vite dev server + Electron run together; health check
  renders real data; Electron loads and exits cleanly.

**Next Session Goals:** None set at the time — Stage 0 was complete and Stage 1 was undefined.
The next session should start by asking the project owner what Stage 1 covers rather than assuming
scope. (Resolved: the user provided a full Stage 1 charter — see the session below.)

## Session: 2026-08-05 — Stage 1 (Core Architecture & Domain Foundation)

**Objectives:** Build the reusable cross-cutting platform (DI container, repository pattern, base
service, validation/pagination/query/response frameworks, CRUD router factory, event system, job
framework, storage/notification/auth/audit/search abstractions, plugin architecture, workflow
engine, feature flags) with zero business features, per the user's Stage 1 charter. Architecture
proposal presented and approved before any code was written, per the charter's explicit process.

**Completed Tasks:** All 17 planned sections landed, each verified (tests + a live smoke check)
and committed separately — see [CHANGELOG.md](CHANGELOG.md)'s Stage 1 section for the full
per-commit breakdown. Backend test count grew from 10 to 130; frontend from 3 to 9.

**Problems Encountered & Solutions:**

- **Doc-naming gaps found before starting.** The Stage 1 prompt referenced `AI_BOOTSTRAP.md` and
  `PROJECT_STATE.json`, neither of which existed (Stage 0 had created `AI_HANDOVER.md` instead,
  and status lived only in `ProjectStatus.md`). Reported explicitly before proceeding, per the
  prompt's own "report inconsistencies" instruction, then resolved by creating both files fresh as
  part of this session's documentation pass — `AI_BOOTSTRAP.md` as a concise entry point distinct
  from the deeper `AI_HANDOVER.md`.
- **pytest-asyncio event-loop / connection-pool mismatch.** The app's cached `get_engine()`
  singleton can't be reused across pytest-asyncio's per-test event loops (asyncpg connections are
  loop-bound) — surfaced as "Event loop is closed" errors in the repository integration tests.
  **Fixed** by having the test fixture create and dispose its own engine instead of reusing the
  app's cached one.
- **CRUD router factory silently mis-parsed request bodies.** The generic router factory's own
  PEP 695 type parameters (`ReadSchema`, `CreateSchema`, ...) are `TypeVar` placeholder objects at
  runtime, not the concrete Pydantic classes passed in. Annotating nested route handlers with those
  names — combined with `from __future__ import annotations` postponing evaluation to strings —
  made FastAPI silently treat a JSON request body as an unresolvable query parameter instead.
  **Fixed** by dropping the postponed-annotations import from that one file and annotating with
  the actual runtime schema arguments instead; documented prominently in the module docstring so
  the pattern isn't miscopied into a future feature's router.
- **Ruff PEP 695 generic-syntax nudge.** `class Result(Generic[T, E])` was flagged (`UP046`) in
  favor of the native `class Result[T, E]` syntax — adopted throughout Stage 1's generic types for
  consistency (`Container.register[T]`, `AbstractRepository[T]`, `SqlAlchemyRepository[ModelT]`,
  etc.).
- **Architectural correction mid-stage:** the plan originally placed `AppModule` (plugin
  architecture) in `application/interfaces/`, but it necessarily references FastAPI directly to
  mount routes — which would break the framework-agnostic-ports convention every other Stage 1
  port had followed. **Corrected** by moving it to `infrastructure/modules/` instead, documented
  as a deliberate deviation from the approved plan in both the commit message and
  `Architecture.md`, rather than silently diverging.

**Files Modified:** See [CHANGELOG.md](CHANGELOG.md) for the full per-commit breakdown (16
commits for the subsystems, plus this documentation commit).

**Documentation Updated:** `AI_BOOTSTRAP.md`, `PROJECT_STATE.json` (new, repo root),
`docs/AI_HANDOVER.md`, `docs/Architecture.md` (updated incrementally after each section, plus a
final coherence pass), `docs/ProjectStatus.md`, `docs/ModuleRegistry.md`, `docs/FeatureRegistry.md`,
`docs/Roadmap.md`, `docs/CHANGELOG.md`, `docs/SessionReport.md` (this file), plus
`ADR/0006-dependency-injection-container.md` and
`ADR/0007-audit-logging-without-database-table.md`.

**Tests Executed:**
- Backend: `uv run pytest` — 130 passed (up from 10).
- Frontend: `npm run test` — 9 passed (up from 3).
- Both: linters (`ruff`, `black --check`, `eslint`, `prettier --check`) clean after every section.
- After every section that touched the DI container, re-verified `GET /api/v1/health` still
  returned 200 via a live `TestClient` — no regression across 20 subsystem additions.
- Confirmed the real shipped app's route surface is unchanged from Stage 0 (`/api/v1/health`,
  `/api/v1/version` only) — the CRUD router factory and plugin module proofs stayed test-only.

**Next Session Goals:** None set — Stage 1 is complete and Stage 2 is undefined. The next session
should start by asking the project owner what Stage 2 covers (see
[AI_HANDOVER.md](AI_HANDOVER.md) and [AI_BOOTSTRAP.md](../AI_BOOTSTRAP.md)) rather than assuming
scope — this is now the second stage in a row where that's been true; don't let it become an
assumption that "the next stage is always infrastructure."

## Session: 2026-08-05 — Stage 2 (Database Architecture & Data Model)

**Objectives:** Design and build the complete production-ready database schema for the entire
eventual application — 49 tables across 11 domain sections plus seed data — as pure schema
(SQLAlchemy models, Alembic migrations, constraints, indexes), per the user's Stage 2 charter. No
business logic, UI, or repositories/services/routes wired to the new tables. Architecture proposal
(overview, ER diagram, table list, relationships, index strategy, migration strategy, performance
considerations, future scalability) presented via plan mode and approved before any code was
written.

**Completed Tasks:** All 13 planned sections landed (11 schema sections + seed data + this
documentation pass), each verified against live Postgres (migration up/down reversibility,
integration tests) and committed separately — see [CHANGELOG.md](CHANGELOG.md)'s Stage 2 section
for the full per-commit breakdown. Backend test count grew from 130 to 216.

**Problems Encountered & Solutions:**

- **Empty Alembic autogenerate migration.** `alembic/env.py` only had a *comment* about importing
  models, never an actual import, so `Base.metadata` was empty at autogenerate time and the first
  migration attempt generated nothing. **Fixed** by adding the real
  `from app.infrastructure.persistence import models  # noqa: F401` import.
- **`CheckConstraint` naming double-prefix bug.** Passing a check constraint's *full* expected name
  (e.g. `name="ck_addresses_address_type"`) produced the actual DB name
  `ck_addresses_ck_addresses_address_type`, because the naming convention combines the given name
  with its own `ck_%(table_name)s_` prefix. **Fixed** by always passing a short logical name
  (`name="address_type"`) and letting the convention build the rest — confirmed this does *not*
  apply to `Index(name=...)`, which is used as-is. Documented inline for future sections.
- **Circular FK risk between `documents` and `document_versions`.** A `documents.current_version_id`
  pointer back to `document_versions` would create a circular FK between two tables created in the
  same migration. **Resolved** by dropping the column entirely — "latest version" is derived via
  `ORDER BY version_number DESC LIMIT 1`, with no proven query need yet for the denormalized
  pointer.
- **`AuditLog.metadata` would shadow SQLAlchemy's own `Base.metadata`.** A well-known SQLAlchemy
  gotcha: naming a mapped attribute `metadata` collides with the declarative base's own class
  attribute. **Fixed** by naming the Python attribute `audit_metadata` while keeping the actual
  database column named `"metadata"` via `mapped_column("metadata", JSONB)`, matching
  `AuditLogger.record()`'s parameter shape at the DB level.
- **`OptimisticLockMixin` construction bug.** An initial attempt to set
  `Client.__mapper__.version_id_col` *after* the class body executed was fragile — a plain mixin
  column isn't a real `InstrumentedAttribute` yet at that point. **Fixed** by using
  `@declared_attr def __mapper_args__(cls)`, which defers evaluation until the table is fully
  built, then generalized into a reusable `OptimisticLockMixin`.
- **`Appointment` duplicated `AuditMixin`'s `created_by` column** by re-declaring it explicitly.
  Caught before generating the migration; fixed, then grepped every model file for the same
  `created_by`/`updated_by` pattern to confirm no other section made the same mistake.
- **Cross-section table dependency not in the original plan.** `document_templates` and
  `document_versions` (Section 6) both need `file_storage_records`, originally planned for Section
  10. **Resolved** by creating `file_storage_records` in Section 6 instead, documented as a
  deliberate deviation in both code comments and commit messages.
- **Seeding real lookup data collided with existing tests.** Populating `countries`/`permissions`/
  `feature_flags` etc. with real values (Section 12) surfaced 4 pre-existing tests that used the
  same fixed names/codes (`"India"`, `"matters:read"`, `"ocr_pipeline"`) now taken by seed rows,
  failing on the DB's unique constraints. **Fixed** by switching those tests to generate unique
  per-run values, consistent with the uuid-suffixed pattern already used elsewhere in the suite.
- **Black reformatting multi-name imports breaks `# noqa` placement** (carried pattern from Stage
  1, re-confirmed here): `models/__init__.py` uses one `from X import name as name` line per module
  instead of a grouped import, so black's reformatting never disturbs a trailing noqa comment.

**Files Modified:** See [CHANGELOG.md](CHANGELOG.md) for the full per-commit breakdown (11 schema
commits + 1 seed-data commit + this documentation commit).

**Documentation Updated:** `docs/ERD.md` (new), `docs/Database.md` (full rewrite),
`docs/Architecture.md`, `AI_BOOTSTRAP.md`, `PROJECT_STATE.json`, `docs/ProjectStatus.md`,
`CHANGELOG.md`, `docs/CHANGELOG.md`, `docs/FeatureRegistry.md`, `docs/ModuleRegistry.md`,
`docs/SessionReport.md` (this file), `docs/FolderStructure.md`, `docs/AI_HANDOVER.md`,
`docs/Roadmap.md`, plus `ADR/0008-persistence-models-not-domain-entities.md` and
`ADR/0009-audit-logs-table-reverses-adr-0007.md` (with a "Superseded by ADR-0009" line added to
`ADR/0007`).

**Tests Executed:**
- Backend: `uv run pytest` — 216 passed (up from 130).
- Frontend: unchanged, 9 passed (Stage 2 was backend/schema-only).
- Both: linters (`ruff`, `black --check`) clean after every section, including
  `backend/alembic/versions/` (every autogenerated migration needed `black` + `ruff --fix` to pass).
- Every migration applied to and downgraded from a live Postgres container, individually
  (`alembic upgrade head` / `downgrade -1` / `upgrade head` per section) and as a full chain
  (`downgrade base` → `upgrade head`) at the end of the stage.
- The OCR full-text search GIN index was verified with a real `to_tsvector`/`plainto_tsquery` query
  against inserted rows, not just migration success.
- Seed data row counts spot-checked directly against the live database via `psql`.
- Confirmed the real shipped app's route surface is unchanged from Stage 0
  (`/api/v1/health`, `/api/v1/version` only) — Stage 2 added zero routes, as scoped.

**Next Session Goals:** None set — Stage 2 is complete and Stage 3 is undefined. The database
schema is now ready for a feature to be wired to it (repository → service → route, inside-out per
Clean Architecture), but the next session should confirm that's actually what Stage 3 is with the
project owner rather than assuming — this is now the third stage in a row where scope had to be
given explicitly rather than inferred.
