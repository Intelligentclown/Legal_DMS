# AI Handover

*Assume you are a fresh AI model with no memory of this project's prior sessions. This document
should let you continue immediately without asking clarifying questions about what already
exists. If you haven't already, read [`/AI_BOOTSTRAP.md`](../AI_BOOTSTRAP.md) and
[`/PROJECT_STATE.json`](../PROJECT_STATE.json) first — this file is the deep-dive that follows them.
For a fast, at-a-glance view of what's built and how solid each piece is, see
[ArchitectureScorecard.md](ArchitectureScorecard.md) — a capability-by-category maturity dashboard
complementary to this file's narrative. For the full picture of the current version specifically
(features, fixes, breaking changes, known issues, what's next), see
[releases/v0.3.1.md](releases/v0.3.1.md) — see [releases/README.md](releases/README.md) for how
this project's release notes system works. **Before starting a new stage**, complete
[templates/PreStageChecklist.md](templates/PreStageChecklist.md) — see
[templates/README.md](templates/README.md) for how.*

## Project Summary

Legal Document & Matter Management System — a desktop app (Electron + React/TS frontend, Python
FastAPI backend, PostgreSQL database) for a legal documentation office. Built to be developed over
many months across many sessions. **Stage 0 (infrastructure), Stage 1 (core architecture), and
Stage 2 (database schema) are all complete**, plus seven post-Stage-2 framework additions (the
Command Bus, Query Bus, Transaction Pipeline, Caching Abstraction, Module Manifest Loader,
Architecture Health Check, and Performance Metrics Service — see
[ADR/0010](../ADR/0010-command-bus.md), [ADR/0011](../ADR/0011-query-bus.md),
[ADR/0012](../ADR/0012-transaction-pipeline.md), [ADR/0013](../ADR/0013-caching-abstraction.md),
[ADR/0014](../ADR/0014-module-manifest-loader.md), [ADR/0015](../ADR/0015-architecture-health-check.md),
and [ADR/0016](../ADR/0016-performance-metrics-service.md)). Read [Context.md](Context.md) for
fuller
narrative if this handover isn't enough — note Context.md was written at the end of Stage 0 and
hasn't been rewritten since; treat its "Current Stage"/"Pending Work" sections as stale relative to
this file and `ProjectStatus.md`.

## Current Architecture

Clean Architecture on both sides (domain/application/infrastructure/presentation), detailed in
[Architecture.md](Architecture.md). As of Stage 1, the backend has a full reusable platform:
a hand-rolled DI container, repository pattern, base service, validation/pagination/query/response
frameworks, a generic CRUD router factory, an event bus, a background job framework, file storage/
notification/search/auth/audit abstractions (each with exactly one minimal default
implementation), a plugin/module registry, a workflow engine, and feature flags. Post-Stage-2, a
**command bus** and a **query bus** were added the same way (`CommandBus`/`QueryBus` ports +
`InMemoryCommandBus`/`InMemoryQueryBus`, both single-handler dispatch — see
[ADR/0010](../ADR/0010-command-bus.md) and [ADR/0011](../ADR/0011-query-bus.md)), followed by a
**transaction pipeline** (`UnitOfWork` port + `InMemoryUnitOfWork`, registered non-singleton, plus
`TransactionPipelineBehavior` — a `CommandBus` decorator that commits/rolls back based on the
handler's `Result` — see [ADR/0012](../ADR/0012-transaction-pipeline.md)), a **caching
abstraction** (`Cache` port + `InMemoryCache`, singleton, TTL-aware, not wired to `QueryBus` — see
[ADR/0013](../ADR/0013-caching-abstraction.md)), a **module manifest loader**
(`ModuleManifest`/`ModuleManifestLoader` in `infrastructure/modules/`, closing a gap
`ModuleRegistry`'s own docstring left open — see [ADR/0014](../ADR/0014-module-manifest-loader.md)),
an **architecture health check** (`assert_container_healthy()` in `infrastructure/di/`,
resolving `IMPLEMENTATION_QUEUE.md`'s T15 — **wired into `main.py`'s startup**, unlike the other
additions, since every registration it checks was already proven working — see
[ADR/0015](../ADR/0015-architecture-health-check.md)), and a **performance metrics service**
(`MetricsService` port + `LoggingMetricsService` in `infrastructure/metrics/`, mirroring
`Notifier`/`AuditLogger`'s "logs structurally, no real backend yet" posture — see
[ADR/0016](../ADR/0016-performance-metrics-service.md)). As of Stage 2, the
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
checklist. **No Stage 3 plan existed at this point in the project's timeline** — see below for
Stage 3's current, since-scoped status. Seven standalone post-Stage-2 additions (Command Bus, Query
Bus, Transaction Pipeline, Caching Abstraction, Module Manifest Loader, Architecture Health Check,
Performance Metrics Service) have since landed, followed by a QA review of those seven additions
(`docs/reviews/Stage_2_5_QA_Review.md`) that fixed two findings (T20/T21 in
`IMPLEMENTATION_QUEUE.md`) — **282 backend tests passing**, still 9 frontend, still lint clean. Of
the seven additions, only Architecture Health Check is wired into the real app's startup path
(`main.py`). See [ADR/0010](../ADR/0010-command-bus.md), [ADR/0011](../ADR/0011-query-bus.md),
[ADR/0012](../ADR/0012-transaction-pipeline.md), [ADR/0013](../ADR/0013-caching-abstraction.md),
[ADR/0014](../ADR/0014-module-manifest-loader.md),
[ADR/0015](../ADR/0015-architecture-health-check.md), and
[ADR/0016](../ADR/0016-performance-metrics-service.md). Separately, **Stage 2.7 — GitHub Actions
CI** has since landed: three workflows (`backend.yml`/`frontend.yml`/`release.yml`) validating
every push and pull request — see [ADR/0017](../ADR/0017-github-actions-ci.md). No application
code changed; test counts are unaffected (still 282 backend / 9 frontend).

**Stage 3 — Authentication & Authorization is now in progress.** Architecture approved (D1–D7).
Phase 0 (T41–T45) is done across three batches — `get_db()` commit/rollback fix
([ADR/0020](../ADR/0020-session-commit-rollback-policy.md)), auth dependencies/config, and the
finalized `AuthenticationProvider` interface ([ADR/0019](../ADR/0019-authentication-provider-interface-change.md))
— with a batch-3 re-verification pass against a more precise T44/T45 spec that confirmed batch 2
already satisfied it exactly and closed two test-coverage gaps. **QA Decision: Approved.** 298
backend tests passing (up from 282), still 9 frontend. Full technical detail:
[docs/ImplementationLog/Stage3/Phase0.md](ImplementationLog/Stage3/Phase0.md) — not
repeated here per this project's canonical-document rules. Two items remain open and untracked
under a task ID (the `docs/templates/PreStageChecklist.md` sign-off and `ADR-0018`, D1–D6 — the
*original* content of the T44/T45 IDs, reused for different content per direct instruction), so
Phase 0's own status stays **In Progress**, not Done, even though every task ID shows complete.

**Update (2026-08-08): Phase 1 (`T46`–`T51`) is now complete.** Password hashing (`T46`), JWT
encode/decode (`T47`), the `refresh_tokens` migration (`T49`), and `AuthService` plus its tests
(`T50`/`T51`, one combined batch) are all done — `AuthService.authenticate()`/`issue_tokens()`/
`refresh()`/`revoke()` is the first real consumer of the credential/token foundation the earlier
Phase 1 tasks built, via two new narrow repository ports (`UserRepository`,
`RefreshTokenRepository`). QA Decision: Approved with comments (345/345 full suite passing against
live PostgreSQL, no rework required). Full detail:
[docs/ImplementationLog/Stage3/Phase1.md](ImplementationLog/Stage3/Phase1.md).

**Update (2026-08-08): Phase 2's `T52` (`JwtAuthenticationProvider`) is Done.** `T52` was explicitly
authorized by the project owner in a Project Manager conversation and implemented
(`infrastructure/auth/jwt_authentication_provider.py`, 11 tests, full suite 356/356 passing,
ruff/black clean) — but that authorization was initially never recorded in
`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`, and no `docs/ImplementationLog/Stage3/Phase2.md`
existed yet either. QA independently verified `T52`'s code and tests as technically correct
throughout; once a documentation-synchronization pass created
[docs/ImplementationLog/Stage3/Phase2.md](ImplementationLog/Stage3/Phase2.md) and corrected the
authorization text, QA rendered **Approved with comments** on the process gate itself (2026-08-08)
— the comment: authorization given in conversation should land in the repository *before*
implementation starts, not be reconstructed afterward. The third originally-flagged gap (no feature
branch, direct-to-`main` implementation) closed independently of any of this: `git log` shows
`feature/stage3-t52-jwt-authentication` merged via PR #9 (`baed936`). `Phase2.md`'s QA Decision is
now recorded in-repository (not just in conversation) with that commit/PR referenced, and `T52` is
marked `Done` in `IMPLEMENTATION_QUEUE.md`. `AuthService`/`JwtAuthenticationProvider` are still
**not wired into `configure_container()` or any route.**

**Correction (2026-08-08, T53 documentation/process transparency pass):** `T53`
(`RbacAuthorizationService`) is **technically implemented**, not "not started" as this section
previously read — `infrastructure/auth/rbac_authorization_service.py` plus a new
`RolePermissionRepository` port and its SQLAlchemy implementation, 13 new tests, full suite 369/369
passing, ruff/black clean (see `docs/ImplementationLog/Stage3/Phase2.md`'s T53 batch). It was
authorized by the project owner in conversation, **documented in the repository only
retrospectively** — not before implementation began, which is itself a process gap, the same
failure mode `T52` already demonstrated once. Two further governance gaps, recorded in full in
`Phase2.md`'s Problems Encountered: the Backend Developer role's own required approval checkpoint
(`docs/prompts/BackendDeveloper.md` §5) was skipped, and `T53` was implemented directly on `main` (no
branch, commit, or PR). **All four are process/governance deviations, not technical defects.**

**Closeout (2026-08-08): `T53` is now Done.** A QA Reviewer role subsequently reviewed `T53` and
rendered **Approved with comments** — the code/tests approved on the merits, and all four
process/governance deviations above named explicitly, none disputed. The git-action deviations (no
branch, uncommitted) have since closed: `feature/stage3-t53-rbac-authorization` was branched,
committed (`dd754f5`), opened as PR #10, and merged (`a103dca`) — `main`/`origin/main` both verified
at `a103dca`, working tree clean. The authorization-recording and approval-checkpoint deviations
remain on record in `Phase2.md`'s Problems Encountered as governance history, not erased by this
closeout.

**Governance reconciliation (2026-08-08): `T54` is implemented and QA-reviewed, but NOT `Done`.**
`RequirePermission(...)` (`presentation/api/deps.py`, plus a new `get_authorization_service()`
resolver) closes Stage 2.5's F11 finding. 5 new tests, full suite 374/374 passing, ruff/black clean,
independently re-verified — see `docs/ImplementationLog/Stage3/Phase2.md`'s T54 batch. QA rendered
**Rework required, process grounds only — no code changes needed.** Three governance findings, the
same shape as `T52`/`T53`'s own: authorization exists in a Project Manager conversation but wasn't
recorded in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation began (the third
consecutive batch with this gap); `Phase2.md` had no `T54` batch entry until this pass; `T54`'s
changes exist directly on `main`, uncommitted, unbranched. **One important correction, stated
explicitly:** unlike `T53`, the Backend Developer role's `docs/prompts/BackendDeveloper.md` §5
approval checkpoint **was performed and explicitly approved before implementation began** for `T54`
— `T53`'s own QA Decision had called this checkpoint's absence "overdue for an actual fix," and this
batch is that fix.

**Closeout (2026-08-10): `T54` is now Done.** A QA Reviewer role subsequently re-reviewed the process
gate and rendered a **follow-up decision — Approved with comments** — the original `Rework required`
above is preserved verbatim as the historical record, not erased. The branch/commit/PR gap has
closed: `feature/stage3-t54-require-permission` → feature commit `dbd6724` → PR #12 → merged
`6396f6b` — `main`/`origin/main` both verified at `6396f6b`. The authorization-not-pre-recorded
finding remains on record as governance history, not erased by this closeout.

**`T55` authorized conversationally (2026-08-10).** Original scope: "replace the two
`container.register(...)` registrations in `configure_container()`."

**Correction (2026-08-10, same day, after QA review):** this section previously claimed the
authorization was "recorded before implementation began, breaking the pattern `T52`/`T53`/`T54` each
demonstrated." **That claim is inaccurate and is corrected here, not silently removed.** The
committed `HEAD` at the time still read `T55` as unauthorized, and nothing about this authorization —
original, clarified, or expanded — was ever committed before `T55`'s implementation existed. The
pattern was **not** broken; it recurred a **fourth** time (`T52`, `T53`, `T54`, `T55`). This is a
permanent governance finding, not something a later correction can retroactively fix — only disclose
accurately.

Same day, also conversationally, an architectural clarification and expanded authorization followed:
the Backend Developer's required §5 checkpoint found the literal registration wording technically
unworkable — `container.resolve()` is synchronous/zero-arg, but both real providers need a
request-scoped `AsyncSession`. The project owner additionally authorized request-scoped `Depends()`
construction in `presentation/api/deps.py` instead (via `DBSessionDep` →
`SqlAlchemyUserRepository`/`SqlAlchemyRolePermissionRepository` → the real provider/service; fresh
RBAC mapping per request, no caching policy). `T52`/`T53`/`T54` implementation files, `T56`, `T57`,
and routes remained explicitly out of scope, and no scope creep into any of them was found.

**Closeout (2026-08-10): `T55` is now Done.** Request-scoped construction in `deps.py`, obsolete
container registrations removed after inspection confirmed them unused; 6 new integration tests, full
suite 380/380 passing, ruff/black clean, request-scoped session usage independently verified — see
`docs/ImplementationLog/Stage3/Phase2.md`'s T55 batch. **QA Decision:** original `Rework required` —
governance/process grounds only, no code changes needed (the authorization-recording gap above) —
preserved verbatim as historical record; a **follow-up decision, `Approved with comments`**, is the
final disposition, rendered once the branch/commit/PR gap closed:
`feature/stage3-t55-auth-wiring` → implementation commit `86a3d5d` → governance commit `f070e28` →
PR #15 → merged `b094436`. `main`/`origin/main` both verified at `b094436`. **The
authorization-recording finding is NOT resolved by this closeout** — it remains permanent governance
history, the fourth consecutive occurrence (`T52`, `T53`, `T54`, `T55`), not erased.

**`T56` closeout (2026-08-12): Done, and the first Stage 3 Phase 2 batch to get the
authorization-recording discipline right.** `presentation/api/deps.py` gained `get_bearer_token()`
(FastAPI `HTTPBearer(auto_error=False)`), replacing `get_current_user()`'s hardcoded `token=None`
placeholder with the caller's real bearer token. Authorization was recorded as its own dedicated,
documentation-only commit (`91e0785`, PR #17, merged `89a3a5e`) **before** the implementation commit
(`fcc68e0`, PR #18, merged `d69c4eb`) — confirmed directly by commit timestamp order, breaking the
pattern `T52`/`T53`/`T54`/`T55` each demonstrated. 3 new tests, full suite 383/383 passing,
`ruff`/`black` clean, boot smoke test passed, Postgres-backed verification completed. **QA Decision:
Approved with comments** — no technical defects; the comment is a non-blocking future observation
about an end-to-end `TestClient`-level bearer-token test once a real protected route exists
(`T58`+), not a gap in `T56` itself. `T57` remains not started, not authorized. Backend test count
is 383, still 9 frontend.

## Pending Work

Everything past Stage 2. **Nothing is scoped yet** — see [Roadmap.md](Roadmap.md). The most likely
next step is wiring a real feature (repository → service → route) to a slice of the Stage 2 schema,
but that must be confirmed with the project owner, not assumed. Separately, **Stage 2.7 has one open
item**: `IMPLEMENTATION_QUEUE.md` T35 — a real GitHub Actions run has not been observed yet, since
that requires a `git commit` + `git push`, a confirm-first action not taken as part of
implementation. If you're picking this up next and have the go-ahead to push, that's the fastest
way to close Stage 2.7 out completely; if something looks wrong once it actually runs on GitHub's
runners (cache paths, working-directory typos, an action version that's moved on), fix it there —
everything was verified by running the underlying commands locally, which is not the same claim as
"the YAML itself runs green on GitHub's infrastructure."

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

Post-Stage-2 pattern worth knowing:
8. **`UnitOfWork` is registered `singleton=False`** — the one exception to this project's "every
   container registration is a singleton" default. Don't copy the plain `container.register(X,
   Y)` form for it if you ever re-register it elsewhere; a shared unit-of-work instance across
   concurrent command dispatches would let one operation's commit/rollback affect another's. See
   [ADR/0012](../ADR/0012-transaction-pipeline.md).
9. **Catch `BaseException`, not `Exception`, around anything that must roll back on cancellation.**
   `asyncio.CancelledError` inherits from `BaseException` (since Python 3.8), not `Exception` — a
   plain `except Exception` around an `await` lets a cancelled task (client disconnect, request
   timeout, shutdown grace period) skip cleanup entirely. Found in QA review
   (`docs/reviews/Stage_2_5_QA_Review.md`, finding Q1) against
   `TransactionPipelineBehavior.dispatch()` and fixed (T20) — copy that file's `except BaseException`
   pattern for any future code with the same "must clean up even on cancellation" shape.

Stage-3-specific pattern worth knowing:
10. **`get_db()` now commits on success and rolls back on exception** (Stage 3 Phase 0, T42/T43,
    [ADR/0020](../ADR/0020-session-commit-rollback-policy.md)) — before this fix it never
    committed at all, so every write silently vanished once the session closed (visible only
    within the same uncommitted transaction). Repositories still only `flush()`; `get_db()` is the
    actual transaction boundary. **Deliberately still `except Exception`, not `BaseException`** —
    unlike pattern #9 above, this fix intentionally didn't widen the catch to cover
    `asyncio.CancelledError` yet, to keep the hard-prerequisite fix minimal; see ADR-0020's
    Trade-offs for why, and its Future Impact for the flagged follow-up. Don't "fix" this to match
    #9 without reading that ADR first — it's a recorded, deliberate scope limit, not an oversight.

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
- **0010–0011** (post-Stage-2): the Command Bus and Query Bus — why each is a plain marker class +
  single-handler dispatch, not an `ABC`, and why no shared base class between them (see AI_HANDOVER
  pattern 9's sibling note and QA finding Q4 in `IMPLEMENTATION_QUEUE.md` for why that duplication
  stays accepted).
- **0012** (post-Stage-2): the Transaction Pipeline — why `UnitOfWork` is the first non-singleton
  container registration, and why `TransactionPipelineBehavior` is a `CommandBus` decorator rather
  than a change to `CommandHandler`'s signature.
- **0013** (post-Stage-2): the Caching Abstraction — why it's a standalone `Cache` port, not a
  pipeline wrapping `QueryBus`.
- **0014** (post-Stage-2): the Module Manifest Loader — why it reads/imports but doesn't register,
  and why it isn't wired into `main.py` yet.
- **0015** (post-Stage-2): the Architecture Health Check — the only post-Stage-2 addition wired into
  the real app's startup path.
- **0016** (post-Stage-2): the Performance Metrics Service — why it's a standalone "Service" port,
  not an HTTP `/metrics` route or a bus-wrapping pipeline.
- **0017** (Stage 2.7): GitHub Actions CI — three separate workflow files over one; pinning CI to
  the project's actual current Python/Node versions rather than the documented supported floors,
  per explicit project-owner direction; why `release.yml` does build verification only today
  despite its name; and why integration tests/Docker/deployment are deferred rather than guessed
  at.

If you make a new significant architectural decision, **add a new ADR** (`0018-...`), don't just
change things silently.

## Current Branch

`feature/github-actions-ci` — a feature branch was in use for Stage 2.7's work (unlike every prior
stage, which worked directly on `master`/`main`); confirm with the project owner whether this
becomes the project's standing workflow or was scoped to this one stage before assuming either way.

## Files Recently Modified

Stage 2 added `backend/src/app/infrastructure/persistence/models/` (11 model modules + mixins),
12 new files under `backend/alembic/versions/`, and one `backend/tests/integration/test_*.py` per
schema section plus `test_seed_data.py`. See `git log` for the exact commit sequence (11 schema
commits + 1 seed-data commit + this documentation commit), or [CHANGELOG.md](CHANGELOG.md) for the
per-commit file breakdown. (Stage 1, for reference, touched
`backend/src/app/{domain,application,infrastructure,presentation,workers}/**` and added
`frontend/src/domain/types/result.ts` + `frontend/src/shared/types/query.ts`.)

## What Should Be Implemented Next

**Stage 3 (Authentication & Authorization) is scoped, and Phase 0, Phase 1 (`T46`–`T51`), `T52`,
`T53`, and `T54` are all done. `T55` is the next unfinished task and awaits a further explicit
go-ahead — see the Current Stage section's 2026-08-08/2026-08-10 entries above for the
process/governance gaps `T52`, `T53`, and `T54` each carried (now recorded, and in every case,
closed out) before assuming that go-ahead is a formality.** `T52`
(`JwtAuthenticationProvider`) was authorized by the project owner in a Project Manager conversation;
the repository wasn't updated to reflect that before implementation started, and QA's process-gate
review (see [docs/ImplementationLog/Stage3/Phase2.md](ImplementationLog/Stage3/Phase2.md)) caught
that plus two related gaps (a missing phase log, an undocumented direct-to-`main` implementation) —
all three are now closed: the phase log exists, the authorization text is corrected, and
`feature/stage3-t52-jwt-authentication` was in fact branched, committed, opened as PR #9, and merged
(`baed936`). QA's decision — **Approved with comments** — is recorded in `Phase2.md` itself, not
just asserted.

`T53` (`RbacAuthorizationService`) was, in fact, also authorized by the project owner in
conversation and implemented — but that authorization was **not** written into the repository
before implementation began, unlike the discipline `T52`'s own QA comment called for. Recorded as a
correction, not silently absorbed: `T53`'s code/tests are real (369/369 full suite) and its process
gaps (authorization recorded only retrospectively, the Backend Developer role's approval checkpoint
skipped, implemented directly on `main`) are equally real — see
`docs/ImplementationLog/Stage3/Phase2.md`'s T53 batch, Problems Encountered. **Closeout (2026-08-08):
`T53` is now `Done`, QA Decision Approved with comments** (code/tests approved on the merits, all
four deviations named). The two git-action deviations have since closed —
`feature/stage3-t53-rbac-authorization` branched, committed (`dd754f5`), opened as PR #10, and
merged (`a103dca`); `main`/`origin/main` both verified at `a103dca` — while the authorization-recording
and approval-checkpoint deviations remain on record as governance history, not erased.

**`T54` (`RequirePermission(...)` FastAPI dependency factory) followed — the predicted third
recurrence of the authorization-recording gap did happen (`T52`, `T53`, `T54`, three consecutive
batches), but not the approval-checkpoint gap: unlike `T53`, the Backend Developer role's §5
checkpoint was actually performed and approved before `T54`'s implementation began.** `T54` was
technically implemented and QA-reviewed (374/374 full suite, no code issues); QA's original decision
was **Rework required, process grounds only**, superseded by a **follow-up decision (2026-08-10):
Approved with comments** once the branch/commit/PR gap closed the same way `T52`/`T53`'s equivalent
gaps did — `feature/stage3-t54-require-permission` → feature commit `dbd6724` → PR #12 → merged
`6396f6b`. Both QA decisions are preserved in `docs/ImplementationLog/Stage3/Phase2.md`'s T54 batch,
the original verbatim, not erased; the authorization-not-pre-recorded finding remains open governance
history.

**`T55` was implemented next, authorized conversationally on 2026-08-10 — but, contrary to what an
earlier version of this section claimed, its authorization was NOT actually recorded in the
repository before implementation began.** Original scope: the two `container.register(...)`
replacements. Same day, the Backend Developer's §5 checkpoint found that literal approach technically
unworkable (`container.resolve()` is synchronous/zero-arg; both real providers need a request-scoped
`AsyncSession` the container can't inject into a sync factory) and correctly stopped rather than
implement or reinterpret it unilaterally. **The project owner then authorized an expanded,
technically-correct boundary, same day, also conversationally:** request-scoped `Depends()`
construction in `presentation/api/deps.py` through `DBSessionDep`
(`SqlAlchemyUserRepository`/`SqlAlchemyRolePermissionRepository` → `JwtAuthenticationProvider`/
`RbacAuthorizationService`), a fresh-per-request RBAC mapping with no caching policy, and removal of
the existing `Anonymous`/`Permissive` registrations (confirmed unused elsewhere by direct inspection,
so actually removed). `T52`/`T53`/`T54`'s files, `T56`, `T57`, and routes remained explicitly out of
scope, and no scope creep into any of them was found. **`T55` is now Done.** Technically correct
(380/380 full suite, 6 new integration tests, `ruff`/`black` clean, request-scoped session usage
independently verified); original QA Decision **Rework required — governance/process grounds only**
(the committed repository state never actually contained this authorization before the code existed —
the **fourth** consecutive occurrence of the exact authorization-recording gap `T52`/`T53`/`T54` each
already demonstrated once) preserved verbatim; **follow-up decision `Approved with comments`** is the
final disposition, once `feature/stage3-t55-auth-wiring` → PR #15 → merged `b094436` closed the
branch/commit/PR gap. `main`/`origin/main` both verified at `b094436`. The authorization-recording
finding itself remains open governance history, not resolved or erased by this closeout — it cannot
be.

**`T56` followed, and — for the first time in five Stage 3 Phase 2 batches — the authorization-
recording discipline actually held.** The project owner's authorization for `T56` (extract the real
bearer token in `get_current_user()`, replacing the `token=None` placeholder) was recorded as its own
dedicated, documentation-only commit (`91e0785`, PR #17, merged `89a3a5e`) **before** any
implementation commit existed — confirmed directly by commit timestamp order (`91e0785` at 15:10:37,
`fcc68e0` at 15:35:54, same day), not merely asserted. `T56` is now **Done**: `presentation/api/deps.py`
gained `get_bearer_token()` (FastAPI `HTTPBearer(auto_error=False)`), 3 new tests, full suite
383/383 passing, `ruff`/`black` clean, boot succeeds, Postgres-backed verification completed — merged
`fcc68e0` → PR #18 → `d69c4eb`. **QA Decision: Approved with comments** — no technical defects; a
non-blocking comment recommends an end-to-end `TestClient`-level bearer-token test once a real
protected route exists (`T58`+). `T57` is now the next unfinished task, not yet started, not
authorized. See
[docs/Stage3_Backend_Handoff.md](Stage3_Backend_Handoff.md) for Phase 2–4's
full file-by-file map. Two smaller open items: (1) the `role_permissions` exact matrix (`T66`) still
needs its own sign-off before that migration is written; (2) the authorization-recording discipline
`T52`/`T53`/`T54`/`T55` each failed at, four batches running — `T56` broke that streak, but a single
success doesn't retire the lesson; `T57`+ should hold the same standard `T56` just set. Outside of
Stage 3, do not add business entities, new major dependencies, or
any repository/service/route touching the other Stage 2 tables (Matter/Client/Property/Document/
Financial) without separate explicit direction.

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

0. **Complete [docs/templates/PreStageChecklist.md](templates/PreStageChecklist.md) first** — copy
   it, verify every section against the real current state of the repository (not what a document
   claims), and get it signed off before writing any code for the new stage. See
   [docs/templates/README.md](templates/README.md) for the full workflow.
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
   [PROJECT_STATE.json](../PROJECT_STATE.json), [ArchitectureScorecard.md](ArchitectureScorecard.md)
   (new capability rows, and re-check the Overall Architecture Health ratings),
   [CHANGELOG.md](CHANGELOG.md), and this file before considering the work done. If this bumps
   `PROJECT_STATE.json`'s `currentVersion`, also create a matching
   [releases/vX.Y.Z.md](releases/README.md) — see that folder's `README.md` for the required
   sections and template.
