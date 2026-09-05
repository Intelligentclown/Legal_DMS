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

**Correction (2026-08-22, Documentation Manager): the "None" claim below describes Stages 0–2 only
and is now materially stale as a top-level status statement** — a real, working authentication/
authorization/frontend/Electron surface exists and is merged (`T41`–`T78`): login, logout, token
refresh, `/api/v1/users*` management routes, RBAC permission checks, a frontend login page,
protected routes, current-user display, Electron `safeStorage`-backed secure token storage, `/docs`/
`/redoc` gated by environment, and tightened CORS. This is **not yet a business feature** in this
project's charter sense (Matter/Client/Property Management, Document Automation, etc. — see
[Roadmap.md](Roadmap.md)'s "Stage 4+ — Not yet planned" table, still accurate) — but "Completed
Features: None" is too strong to describe the current repository. See the `T52`–`T82` narrative
under "Current Stage" below, and [ProjectStatus.md](ProjectStatus.md)'s "Completed — Stage 3 ... and
Stage 4 ..." section, for the actual current substance.

Original note, preserved for continuity (accurate for Stages 0–2 specifically, not the whole
project): None — Stages 0–2 are infrastructure/framework/schema only. See
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
(`T58`+), not a gap in `T56` itself.

**`T57` closeout (2026-08-13): Done — the second consecutive batch to get the authorization-recording
discipline right, and Stage 3 Phase 2 (`T52`–`T57`) is now complete in full.** `T57`'s original
"Tests: ..." wording (including a `configure_container()` criterion `T55` had already made obsolete)
was corrected before implementation: the real objective is closing the 401/403 gap —
`RequirePermission` previously surfaced an anonymous caller and an authenticated-but-unpermitted
caller identically as `ForbiddenError`/403. `_require_permission` now checks `user.is_authenticated`
**before** calling `AuthorizationService`, raising `UnauthorizedError`/401 directly if not
authenticated (Option 1 — `AuthorizationService`'s port, `RbacAuthorizationService`, and
`PermissiveAuthorizationService` were **not** modified). Authorization was recorded as its own commit
(`65dd563`) **before** the implementation commit (`7c9fc3a`, PR #20, merged `472f7cb`) — confirmed
directly by commit timestamp order, extending `T56`'s streak. 3 new tests + 1 updated, full suite
386/386 passing, `ruff`/`black` clean, boot smoke test passed, 127/127 integration tests against live
Postgres per PR #20. **QA Decision: Approved with comments** — no technical defects; the comment
preserves, as a non-blocking historical/forward-looking observation (not a new finding — already
named in `65dd563`'s own authorization text), the deferral of true `TestClient`-level HTTP
verification to `T58`+, since no protected route exists yet. Backend test count is 386, still 9
frontend.

**`T58` closeout (2026-08-15): Done — the third consecutive batch to get the authorization-recording
discipline right, and the first route anywhere in this project.** `presentation/api/v1/auth.py` (new)
adds `POST /api/v1/auth/login`: `LoginRequest`/`LoginResponse` co-located, no `ApiResponse[T]`
wrapper since a token pair isn't a fetchable resource; on failure, `AuthService.authenticate()`'s
`Result.error` is raised directly, handled by the existing global `AppError` handler. `deps.py` gains
`get_auth_service()`/`AuthServiceDep`, request-scoped construction mirroring `T55`'s pattern exactly.
5 new integration tests in `tests/integration/test_auth_login.py`, run against a real mounted app and
live Postgres via `httpx.AsyncClient`/`ASGITransport` with a `get_db` override — `TestClient`'s
separate event-loop thread was tried first and confirmed incompatible with that override. Authorization
was recorded as its own commit (`58c8e40`, 2026-08-13) **before** the implementation commit (`76cd28f`,
PR #22, merged `e67da02`, 2026-08-15) — confirmed by commit order, extending `T56`/`T57`'s streak. Full
suite 391/391 passing (386 prior + 5 new) per PR #22's own report and CI's 6/6 green run
(independently queried via `gh pr view 22`); `ruff`/`black` clean and the boot smoke test passing were
re-verified directly this session — the DB-backed suite itself was not personally re-run, since no
Docker/Postgres was reachable locally. **QA Decision: Approved with comments** — no technical defects;
two non-blocking comments preserved verbatim: (1) Starlette's `HTTP_422_UNPROCESSABLE_ENTITY`
deprecation warning is framework-internal, not a `T58` defect; (2) the test-local
`app.dependency_overrides[get_db]` pattern is safe under current sequential test execution only.
**`T59` closeout (2026-08-15): Done — the fourth consecutive batch to get the authorization-recording
discipline right.** `presentation/api/v1/auth.py` extended (not `deps.py`/`router.py` — `T58`'s
`AuthServiceDep` reused unchanged) with `POST /api/v1/auth/refresh`: `RefreshRequest`/`RefreshResponse`
co-located, bare, matching `login`'s convention; `refresh()` calls `AuthService.refresh()`
(`T50`/`T51`, unmodified), which already collapses invalid/expired/revoked/unknown tokens into one
generic `UnauthorizedError`, raised directly on failure, same pattern as `login`. 7 new integration
tests in `tests/integration/test_auth_refresh.py` (valid refresh returns a new/different token pair,
rotation prevents reuse, invalid/expired/revoked/unknown token each → 401, malformed body → 422),
reusing `T58`'s `httpx.AsyncClient`/`ASGITransport`/`get_db`-override pattern verbatim. Authorization
was recorded as its own commit (`163085d`, 2026-08-15 11:06:35 IST) **before** the implementation
commit (`56eb7c2`, 11:17:32 IST, ~11 minutes later same day, PR #24, merged `721cec5`) — confirmed by
commit order, extending `T56`/`T57`/`T58`'s streak to four. Full suite **398/398 passing (391 prior +
7 new) — personally re-run against live Postgres this session** (Docker was reachable this time,
unlike `T58`'s closeout); `ruff`/`black` clean and the boot smoke test passing re-verified directly;
`app.openapi()["paths"]` independently confirmed to contain only `login`/`refresh`/`health`/`version`
— no `T60`+ scope creep. **QA Decision: Approved with comments** — "no technical defects" per PR #24's
own report; unlike `T58`'s PR, PR #24 does not itemize specific non-blocking comment text anywhere in
the repository (PR body, both commit messages, and `gh api .../pulls/24/reviews` all checked) —
recorded here exactly as given, not invented.

**`T60` closeout (2026-08-15): Done — the fifth consecutive batch to get the authorization-recording
discipline right.** `presentation/api/v1/auth.py` extended (`deps.py`, `router.py`, and `AuthService`
itself **not modified** — the authorization's explicit "must not modify" constraint, honored exactly)
with `POST /api/v1/auth/logout`: `LogoutRequest` co-located; `logout()` calls `AuthService.revoke()`
(`T50`/`T51`, unmodified — returns `None`, never a `Result`, since an unknown or already-revoked
token is a silent no-op, not a failure) and returns `204 No Content` with no body, mirroring
`presentation/common/crud_router_factory.py`'s `delete_item`. 5 new integration tests in
`tests/integration/test_auth_logout.py` (a valid token is actually revoked, verified against the
stored `RefreshToken` row's `revoked_at`; an already-revoked token, an unknown token, and a malformed
token string all still succeed; a malformed body → 422), reusing `T58`/`T59`'s
`httpx.AsyncClient`/`ASGITransport`/`get_db`-override pattern verbatim. Authorization was recorded as
its own commit (`726e8cf`, 2026-08-15 11:57:59 IST) **before** the implementation commit (`5b9bf57`,
12:05:34 IST, ~8 minutes later same day, PR #26, merged `941ed42`) — confirmed by commit order,
extending `T56`–`T59`'s streak to five. Full suite **403/403 passing (398 prior + 5 new) — personally
re-run against live Postgres this session**; `ruff`/`black` clean and the boot smoke test passing
re-verified directly; `app.openapi()["paths"]` independently confirmed to contain only
`login`/`refresh`/`logout`/`health`/`version` — no `T61`+ scope creep. **QA Decision: Approved** — a
deliberate distinction from `T58`/`T59`'s "with comments," not an oversight: PR #26's body states "no
defects" without the "with comments" qualifier the two prior batches both carried, and itemizes no
comment text anywhere in the repository — recorded here as the disposition its own source material
actually states, not inherited from the immediately preceding pattern.

**`T61` (`GET /api/v1/auth/me`) followed — the sixth consecutive batch to hold the
authorization-recording discipline, and the first Phase 3 route needing `CurrentUserDep` rather than
just `AuthServiceDep`.** `presentation/api/v1/auth.py` was extended (`deps.py`, `router.py`,
`AuthService`, `CurrentUser`, `JwtAuthenticationProvider`, and `RbacAuthorizationService` all
untouched) with a co-located `MeResponse` and a `me()` handler taking `CurrentUserDep` directly.
`CurrentUserDep` never raises — an anonymous caller just resolves to `is_authenticated=False` — so
`me()` itself raises `UnauthorizedError` when unauthenticated, the same check `RequirePermission`
already makes, with no permission code required (none of the 18 seeded permissions represents "view
own profile," and none was invented). Unlike `login`/`refresh`/`logout`, the response is wrapped in
`ApiResponse[MeResponse]` — a deliberate, authorized departure, since `/me` fetches a resource and
those three don't — with `roles` sorted before emission (`CurrentUser.roles` is an unordered
`frozenset`). 7 new integration tests in `tests/integration/test_auth_me.py` (valid token, missing
token, malformed token, expired token, inactive-user token, unknown-user token, multiple roles). Full
suite **410/410 passing (403 prior + 7 new)**, `ruff`/`black` clean, boot smoke test passed,
`app.openapi()["paths"]` confirmed to contain exactly the six expected routes — no scope creep, no
forbidden file touched. **QA Decision: Approved** (plain, no comments) — recorded in
`docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision — T61 batch` section, rendered by the QA
Reviewer role independently against the working tree before it was committed. **`T61` is now Done —
merged.** Feature commit `fa57e28`, PR #30, merged `bdffb5e` (2026-08-15); `main`/`origin/main` both
independently re-verified at `bdffb5e` this session, `git show bdffb5e --stat` confirms exactly the
nine files this batch's scope covers, and `gh pr view 30` confirms 6/6 CI checks green.

**`T62` followed — five hand-written user-management routes, the seventh consecutive batch to hold the
authorization-recording discipline, and the first Phase 3 batch to exercise `RequirePermission`'s 403
half via a real HTTP request, not just its 401 half.** New `presentation/api/v1/users.py`:
`GET`/`POST /api/v1/users`, `GET`/`PUT /api/v1/users/{id}`, `POST /api/v1/users/{id}/deactivate`, all
gated by one router-level `RequirePermission("users:manage")`. `crud_router_factory.py`, `deps.py`,
`AuthService`, `CurrentUser` all untouched; `router.py` changed only to mount the new router. Reuses
`BaseService[User]`/`SqlAlchemyUserRepository` (`T50`)/`hash_password()` (`T46`) directly.
`deactivate_user()` calls `service.update()`, never `delete()` — row and `UserRole`/`RefreshToken`
relationships preserved, idempotent. 28 new integration tests in `tests/integration/test_users.py`.
Full suite **438/438 passing (410 prior + 28 new)**, `ruff`/`black` clean, boot smoke test passed,
`app.openapi()["paths"]` confirmed to contain exactly the nine expected routes. **QA Decision: Approved
with comments** — no technical defect; the comment is a **named governance finding**: `T62` was merged
(PR #33 → `3a4a21c`) **before** any QA Decision existed in the repository, violating
`PROJECT_WORKFLOW.md`'s standard lifecycle. A pre-merge QA pass had already reached the same
disposition on the merits — only its repository-visible recording was skipped, letting the merge
proceed unblocked. A Documentation Manager closeout attempt correctly halted on discovering this before
the QA Decision was recorded; it has since been recorded in
`docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision — T62 batch` section and independently
re-verified this session (`main`/`origin/main` both at `3a4a21c`, exactly four files across the full
authorization-to-merge range, 6/6 CI checks green).

**`T63` followed — role-assignment routes, extending `RequirePermission(*permissions: str)` to grant on
any one of multiple permissions.** New `POST`/`DELETE /api/v1/users/{id}/roles[/{role_id}]`, gated by
`RequirePermission("users:manage", "roles:manage")`; every existing single-permission call site
unaffected (`TestRequirePermission` 8/8 unchanged). New `assign_role()`/`remove_role()` on
`UserRepository`/`SqlAlchemyUserRepository`; no new `Role`/`RolePermission` row, no migration. One
flagged, independently-confirmed-necessary file outside the original scope:
`tests/support/in_memory_user_repository.py` (a mechanical ABC consequence). 21 new integration tests.
**QA Decision: Approved** (plain), committed (`6a8608f`) and pushed to
`feature/stage3-t63-role-assignment` **before** PR #36 merged — the deliberate correction of `T62`'s
own named governance finding. **`T63` is now Done — merged.** Feature commit `3cea676`, QA-approval
commit `6a8608f`, PR #36, merged `ef419c3` (2026-08-16); `main`/`origin/main` both independently
re-verified at `ef419c3` this session, `git diff 97ab953..ef419c3 --name-only` confirms exactly the
seven files this batch's scope covers, no forbidden file touched. Full suite **459/459 passing**
personally re-run against live Postgres on merged `main`, `ruff`/`black` clean, boot smoke test
passed, `app.openapi()["paths"]` confirmed to contain exactly the eleven expected route/method
combinations. Backend test count is 459, still 9 frontend.

**`T64` followed — integration tests for explicit error shapes and invalid-token coverage across
`T58`–`T63`'s routes, no production code touched.** Every existing negative test covering 401/403/404/
409/422 in `test_auth_login.py`/`test_auth_refresh.py`/`test_auth_logout.py`/`test_auth_me.py`/
`test_users.py` now explicitly asserts `response.json()["error"]["code"]`/`["message"]`; explicit
invalid-token coverage (distinct from missing-token coverage) added alongside for all seven `T62`/`T63`
user/resource routes. The established login (no bearer-token requirement) and logout (no missing-token
401) contracts were preserved unchanged. No `backend/src/app/**` file, no new file, no migration, no
audit/`T65` work. **QA Decision: Approved** — pre-merge, commit `fc9fb0b`; test execution was
constrained that session by a pre-existing infrastructure issue on `main` (multiple alembic heads,
unrelated to `T64`'s own changes), but static verification passed. **`T64` is now Done — merged.**
Authorization commit `b63bc6d`, feature commit `f321065`, PR #38, merged `fab2933` (2026-08-16);
`main`/`origin/main` both independently re-verified at `fab2933`.

**`T65` followed — wiring the existing, previously-unused `AuditLogger` port into login outcomes and
permission-denied events, no new audit capability or schema.** `AuthService.authenticate()` records
exactly one `login_success`/`login_failure` event per call (`resource_type="auth"`; failure reason —
`unknown_user`/`wrong_password`/`inactive_account` — distinguished only in the audit trail, never in
the still-single-generic-401 HTTP response); `RequirePermission`'s final-candidate denial records
exactly one `permission_denied` event (`resource_type="endpoint"`) before re-raising the identical
`ForbiddenError` — `T63`'s OR-permission semantics preserved exactly, so a denial a later candidate
then grants is never audited. No new `AuditLogger` implementation; `AuditLoggerDep` in `deps.py` mirrors
the file's existing `get_settings_dependency()` pattern; `RequirePermission` resolves `AuditLogger`
directly via `container.resolve()` rather than a new parameter, specifically so
`tests/unit/test_auth.py::TestRequirePermission`'s existing direct two-argument calls (outside this
batch's file scope) stay unaffected (confirmed 8/8 unchanged). 15 new tests across three files. **This
batch's own governance history is worth stating plainly, not smoothed over:** the original
implementation PR (#41, commit `fab38e3`) was opened without an accompanying `Phase3.md` batch
narrative — the first independent QA pass found the implementation itself defect-free but blocked on
that missing entry; a documentation-only correction (`d270828`) added the standard eleven-section batch
and, in writing it, caught and fixed a separate factual error the rework instructions had introduced
(citing `b63bc6d` — actually `T64`'s authorization commit — instead of `T65`'s real one, `095ac91`); a
second, independent QA pass then re-verified everything end-to-end and rendered **QA Decision:
Approved**, committed as `9ac7191` **before** PR #41 merged, continuing the discipline `T63` established
of recording the QA Decision ahead of merge, not after. 23/23 targeted tests (unit + integration +
regression) and 481/481 full suite passing, `ruff`/`black` clean, boot smoke passed, `app.openapi()["paths"]` unchanged (no route added). One unrelated environment issue disclosed, not worked
around by changing any project file: the session's local `.env` `DATABASE_URL` pointed at a stale host
port versus the actually-running Postgres container — corrected locally via an environment-variable
override, not a repository change. **`T65` is now Done — merged.** Authorization commit `095ac91`
(PR #40, merged `61e64d3`), implementation commit `fab38e3`, documentation-correction commit `d270828`,
QA-approval commit `9ac7191`, PR #41, merged `d91d00c` (2026-08-17); `main`/`origin/main` both
independently re-verified at `d91d00c`. Backend test count is 481, still 9 frontend.

**`T66` followed — a new migration under `docs/ImplementationLog/Stage4/Phase0.md` (Stage 4, not
Stage 3 — the first task past the routes phase), seeding `role_permissions` against the owner-approved
matrix.** Exactly 59 authorized `role_permission` associations, UUIDs dynamically resolved from the
existing `roles`/`permissions` rows rather than hardcoded; downgrade removes only the T66-created
associations and preserves any unrelated ones; exactly one Alembic head (`224b650e5235`) confirmed
after the migration. Exhaustive matrix-validation tests added; `T63`/`T65` regression behavior
confirmed preserved. **Governance history, preserved not collapsed:** the initial QA review returned
substantive rework findings, resolved in a follow-up commit, followed by a separate formatting
correction, before the final QA pass. **QA Decision: Approved** (plain) — rendered pre-merge, directly
against PR #44, recorded in `docs/ImplementationLog/Stage4/Phase0.md`'s `QA Decision — T66 batch`
section. **`T66` is now Done — merged.** Authorization commit `66f94bf` (PR #43, merged `81bf99f`),
implementation commit `533226d`, QA-rework commit `b2b86b6`, formatting-correction commit `0239d80`,
QA-approval commit `5ab88a5` (committed before PR #44 merged), PR #44, merged `2edc23e` (2026-08-17);
`main`/`origin/main` both independently re-verified at `2edc23e`.

**`T67` followed — the first-admin bootstrap CLI, the first task past Stage 4 Phase 0's seed
migration.** New `infrastructure/cli/bootstrap.py`: `run_bootstrap(session, *, email, password)` is
the testable core (no-op if any `User` row exists; otherwise creates the `User` via `hash_password()`
(`T46`) and assigns the seeded `Administrator` role (`T66`) via `UserRole`, self-attributed since no
other actor exists yet, `flush()`-only, never commits); `main()`/`_async_main()` is the interactive
entry point, reading the password via `getpass.getpass()` only — never `argv`/an environment
variable/a config file, genuinely satisfying `ADR-0018`'s D4. New `backend/pyproject.toml`
`[project.scripts]` entry: `bootstrap-admin`. 5 new integration tests in
`tests/integration/test_bootstrap_admin.py`. Full suite **487/487 passing (482 prior + 5 new)** —
reconciling a previously-undiagnosed +1 baseline drift this batch's QA review disclosed (this file's
last-recorded 481 was one behind the actual pre-`T67` baseline of 482) — `ruff`/`black` clean.
**QA Decision: Approved with comments** — `D4` compliance verified by reading the file directly (no
`sys.argv`/`os.environ`/config-file access anywhere) and idempotency independently proven by two
non-vacuous tests, not taken on the Developer's word; two non-blocking comments: `run_bootstrap()`
hand-rolls user/role-assignment persistence instead of reusing
`SqlAlchemyUserRepository.assign_role()` (functionally immaterial — bootstrap always operates on a
brand-new `user_id` — but a real, minor divergence from this codebase's repository-layer convention),
and the missing-`Administrator`-role `RuntimeError` guard has zero test coverage. Authorization commit
`119d612` (2026-08-17, PR #46, merged `65b737a`) precedes implementation commit `b409f78` — confirmed
by commit order. **`T67` is now Done — merged.** Feature commit `b409f78`, QA-approval commit
`790b778`, PR #47, merge commit `fc0b142` (2026-08-18, parents `65b737a` and `a73d1c5`) —
`main`/`origin/main` both independently re-verified at `fc0b142` this session via `git log`/`git show`
and `gh pr view 47` (state `MERGED`), not taken on faith. Full suite **487/487 passing, personally
re-run against merged `main` with live Postgres this session** (482 prior + 5 new), `ruff`/`black`
clean, boot smoke test passed, `app.openapi()["paths"]` confirmed unchanged — still exactly the eleven
routes `T63` established, since `T67` adds a CLI entry point, not a route. See
`docs/ImplementationLog/Stage4/Phase0.md`'s T67 batch for full detail.

**`T68` followed — closing the one gap `T67`'s own QA Decision named as a non-blocking comment:**
`test_bootstrap_admin.py` covered `run_bootstrap()`, the in-memory core, but nothing exercised
`bootstrap.py`'s actual entry point. Authorization was narrowed by a direct pre-authorization check —
the seed-row-count/matrix-match half of `T68`'s original description was found already covered by
`test_t66_role_permissions.py::test_t66_role_permissions_matrix_exact_match` and was **not**
re-authorized or re-tested. The genuinely missing half: two new test classes in
`test_bootstrap_admin.py` exercise `_async_main()` directly (not `main()`, since `asyncio.run()` can't
be called from inside `pytest-asyncio`'s already-running event loop) — `TestAsyncMainNoExistingUser`
proves a first invocation actually `commit()`s (verified through a **second, independent** database
connection, since a same-session read can't distinguish "committed" from "merely flushed") and assigns
the `Administrator` role; `TestAsyncMainExistingUser` proves a second/existing-user invocation prints
the "already exists" message without prompting for or discarding credentials, and without creating a
duplicate. `bootstrap.py` itself is byte-for-byte unchanged — test-file-only. 3 new tests, full suite
**490/490 passing (487 prior + 3 new)**, `ruff`/`black` clean. **QA Decision: Approved** (plain, no
comments) — QA went further than the Developer's own disclosed limitation and ran a mutation test:
temporarily removed `bootstrap.py`'s `session.commit()` call, re-ran the two "actually commits" tests
and watched both fail exactly as expected, then reverted and re-confirmed the full suite clean —
proving the new tests are genuinely non-vacuous, not merely plausible by construction. Authorization
commit `d6b6b45` (PR #49, merged `5bca735`) precedes implementation commit `33c728b` — confirmed by
commit order. **`T68` is now Done — merged.** Feature commit `33c728b`, QA-approval commit `5b5c9b9`,
PR #50, merge commit `43aa0a7` (2026-08-18, parents `5bca735` and `1ced5f2`) — `main`/`origin/main`
both independently re-verified at `43c8ddb` this session via `git log`/`git show` and `gh pr view 50`
(state `MERGED`), not taken on faith — an unrelated documentation merge, PR #51, landed on top of
`43aa0a7` and doesn't touch any `T68` file. Full suite **490/490 passing, personally re-run against
merged `main` with live Postgres this session**, `ruff`/`black` clean (204 files unchanged), boot smoke
test passed, `app.openapi()["paths"]` confirmed unchanged — still exactly the eleven routes `T63`
established, since `T68` is test-file-only. **Stage 4 Phase 0 (`T66`–`T68`) is now complete in full and
merged.** See `docs/ImplementationLog/Stage4/Phase0.md`'s T68 batch for full detail.

**`T69` (`httpClient.ts` `post`/`put`/`delete` + structured error parsing) followed — closing Stage
2.5's finding F10, the first Stage 4 Phase 1 (Frontend) task.** `frontend/src/infrastructure/api/httpClient.ts`
gained `post`/`put`/`delete` alongside the existing `get()`, sharing a new `requestWithBody()` helper
(method passed straight through to `fetch`'s `init.method`; body `JSON.stringify()`-serialized only
when `body !== undefined`); `HttpError` gained an optional `code?: string`, populated by a new
`buildHttpError()` when the response body matches the approved `{"error":{"code","message"}}` shape
via a strict type-guard, `isStructuredErrorBody()` (rejects `error: null`, non-string fields, or a
non-object body), falling back to the existing generic `Request to <path> failed with status <status>`
message on any mismatch or an unparseable body (`response.json()` wrapped in `try`/`catch`, never an
unhandled rejection). `get()` and `request<T>()`'s success path are byte-for-byte unchanged. 8 new
tests in a new `httpClient.test.ts`, full suite **17/17 passing** (9 prior + 8 new), `eslint` 0 errors
(3 pre-existing warnings, unrelated files), `prettier --check` clean. **QA Decision: Approved** (plain,
no comments) — scope independently re-verified (`git diff main...feature/stage4-t69-http-client-methods
--name-only`: exactly three files — `httpClient.ts`, `httpClient.test.ts`,
`docs/ImplementationLog/Stage4/Phase1.md`), authorization (`cf7a570`/`0a9ad12`, PR #52, merged
`5abceee`) confirmed to precede implementation (`cca729f`) by commit order, tests/lint/format
independently re-run. One non-blocking, already-disclosed observation, re-confirmed not a new finding:
`delete()`'s success path still calls `response.json()` unconditionally, inherited unchanged from
`request<T>()`, which would throw on a real `204 No Content` response — correctly out of scope, since
no caller of `delete()` exists yet (`T70`+ is unauthorized). **`T69` is now Done — merged.** Feature
commit `cca729f`, QA-approval commit `6b90ede`, documentation-synchronization commit `79af7ac`, PR #54,
merge commit `5196fdf` (2026-08-18, parents `b544135` and `79af7ac`) — `main`/`origin/main` both
independently re-verified at `5196fdf` this session via `git log`/`git show` and `gh pr view 54` (state
`MERGED`), not taken on faith. `git show --stat 5196fdf` confirms the file set matches the T69 batch
plus its own documentation sync exactly — no backend file touched. Frontend suite **17/17 passing**,
`eslint`/`prettier` clean, personally re-run against merged `main` this session, not carried over from
the pre-merge figure. **Stage 4 Phase 5 (`T69`) is now complete in full.** See
`docs/ImplementationLog/Stage4/Phase1.md`'s Post-Merge Verification — T69 batch note for full detail.

**Catch-up (2026-08-21, Documentation Manager current-state/governance reconciliation batch): this
section had gone stale after `T69` and is corrected here to cover `T70`–`T79`/`T82` without
duplicating each batch's own technical record — see the cited phase log or `PROJECT_STATE.json`'s
`currentStage.note` for full detail, not repeated here.** `main`'s current tip, independently
re-verified this session via `git log`/`git status`/`gh pr view`, is `95bfae1`.

**`T70` (auth state management) is Done — merged.** New `AuthProvider.tsx`/`auth.ts` (React
context/provider holding user + tokens, `login()`/`logout()`); `httpClient.ts`'s `get()` gained an
optional `headers` parameter. **Named governance finding, preserved as permanent history:** the
required approval-checkpoint pause between authorization (`2cf052c`) and implementation (`da29014`)
was skipped (~5 seconds apart) — original **QA Decision: Rework required** (process grounds only,
plus a `prettier --check` failure on 3 files), closed by a formatting-only rework commit (`d54b0a3`),
then **QA Re-Review: Approved with comments**. See `docs/ImplementationLog/Stage4/Phase2.md`. Merged:
PR #58 (`551e900`); doc closeout PR #59 (`fd74573`).

**`T71` (Electron secure token storage, ADR-0018 D6) is Done — merged.** `safeStorage` in the Electron
main process, IPC exposure to the renderer. **QA Decision: Approved with comments** — three
non-blocking comments (no tests, no manual verification, default file permissions). See
`docs/ImplementationLog/Stage4/Phase3.md`. Merged: PR #61 (`b770505`); doc closeout PR #62
(`e36fee4`).

**`T72` (Login page/form) is Done — merged.** Integrates `T70`/`T71`'s auth infrastructure. **QA
Decision: Approved with comments; Independent Technical Verification: Approved with comments**
(non-blocking IPC-persistence test-coverage gap recorded — see the Independent Technical Verifier
governance note under "Important Decisions" below for what this second review step is and isn't).
See `docs/ImplementationLog/Stage4/Phase4.md`. Merged: PR #64 (`a8ad712`).

**`T73` (Protected-route wrapper) is Done — merged.** Redirects unauthenticated users to `/login`
using `T70`'s auth state. **QA Decision: Approved with comments; Independent Technical Verification:
Approved with comments** — non-blocking: `<Navigate replace>` semantics verified by source inspection,
not automated-tested; the phase log was created post-QA. See `docs/ImplementationLog/Stage4/
Phase5.md`. Merged: PR #65 (`ecfd4a4`).

**`T74` (global `Authorization` header / 401 handling) is Done — merged.** Attaches the current access
token to outgoing authenticated requests; a 401 clears the session and redirects to `/login` (no
automatic refresh, retry, or rotation — explicitly prohibited in this batch's authorized scope);
resolves `httpClient.ts`'s pre-existing `204 No Content` parsing issue, flagged since `T70`. **QA
Decision: Approved with comments.** See `docs/ImplementationLog/Stage4/Phase5.md`. Merged: PR #66
(`312361a`).

**`T75` (current-user display + logout) is Done — merged.** Adds the authenticated-user display and
logout action to `MainLayout`'s header; wires `ipcBridge.clearRefreshToken()` into the user-facing
logout flow, completing `T74`'s deferred work. **QA Decision: Approved with comments.** See
`docs/ImplementationLog/Stage4/Phase6.md`. Merged: PR #67 (`193bc8a`).

**`T76` was formally resolved as Superseded/Distributed** (2026-08-20, commit `60d07f0`) — its
intended RTL test coverage was completed cumulatively within `T72`–`T75`, so it was closed rather than
separately implemented. Not a cancellation for cause. PR #68, merge `545d00b`.

**`T77` (gate `/docs`/`/redoc` behind `settings.is_development`) is Done — merged**, closing Stage
2.5's F4 finding. `openapi_url` deliberately left ungated, named as Deferred Work. **QA Decision:
Approved** (plain). See `docs/ImplementationLog/Stage4/Phase7.md` in full. Merged: PR #69 (`9cb420f`).

**`T78` (tighten CORS `allow_methods`/`allow_headers`) is Done — merged.** Wildcards replaced with an
explicit allow-list; 10/10 new tests, full backend suite 506/506 passing, ruff/black clean. **QA
Decision: Approved with comments** — one non-blocking observation: the `TRACE`-method negative test
doesn't itself discriminate the tightening (Starlette already rejects `TRACE` under the prior
wildcard), though the positive exact-list and `X-Custom-Header` rejection tests do. Authorization
`713a866`, implementation `07fe8e1`, PR #70, merge `e7943e8`. **This batch's record was appended
directly to `docs/ImplementationLog/Stage4/Phase7.md`** (a second "T78 Batch" section following
`T77`'s full entry), **but that file's metadata block was never updated to reflect it** — `Related
Tasks` still reads only `T77`, `Status` still reads `In Progress`, `Git Commit` still cites only
`T77`'s `64540de`, not `T78`'s `07fe8e1` — and the `T78` section itself is missing most of the
standard's eleven required sections. Flagged as documentation debt during this catch-up pass, not
corrected — that's Developer/QA-owned content, outside this role's routine remit.

**`T79` (verification-only pass) is CLOSED — but explicitly as `INCOMPLETE / NOT VERIFIED`, not as a
PASS.** Project Owner final governance decision, 2026-08-20 (commit `d134862`). Confirmed PASS:
backend suite, frontend suite, both lint/format suites, and the full unauthenticated-redirect →
login → protected-route access → logout → cleared-state browser walkthrough, all independently
re-verified live. **Unresolved: the Electron refresh/session-persistence requirement is NOT VERIFIED**
— this environment can drive a browser tab but not an actual Electron `BrowserWindow`, so ADR-0018
D6's `safeStorage`-backed persistence could not be exercised in its documented target runtime; the
browser-tab result obtained (session clears on refresh) is architecturally expected there and is
explicitly not evidence for or against the Electron-specific behavior. Four untracked debug files
(`backend/insert_admin*.py`, `smoke_test.py`) found during this pass were investigated, confirmed
disposable and non-functional against current `main`, and deleted by explicit Project Owner
authorization — not project tooling. A static-analysis-only finding was recorded, not fixed:
`electron/preload.ts`'s `getRefreshToken()` is not surfaced by `ipcBridge.ts`'s `ElectronApi` wrapper,
and `AuthProvider.tsx` has no mount-time effect calling it — no session-restoration-on-load path
exists yet, even inside Electron. **`T79` also has no `ImplementationLog` phase log** (verification-
only, no implementation) — its full record lives in `PROJECT_STATE.json`'s `currentStage.note` and
`IMPLEMENTATION_QUEUE.md`'s own `T79` row. Published: PR #71/#72, merge `95bfae1`.

**`T82` (Electron-runtime live smoke verification) is opened as the direct follow-up to `T79`'s
unresolved item — reserved and scoped only.** `IMPLEMENTATION_QUEUE.md`'s `T82` row records the
intended scope: launch the actual Electron application (not a browser tab); confirm the
unauthenticated-redirect, login, protected-route-access, and logout flows; specifically exercise
refresh/reload inside the Electron window to confirm (or refute) session restoration through
ADR-0018 D6's `safeStorage`-backed mechanism. **`T82` is NOT authorized, NOT started, and NOT
implemented** — no Project Manager cycle has recorded authorization for it, and this catch-up pass
does not authorize it either.

**Update (2026-08-22, Documentation Manager, fresh current-state synchronization against actual
`main` at `b5505bb` — this file had gone stale again after the 2026-08-21 catch-up above, six more
merges behind: `T80` is Done and merged.** Authorized by the project owner (PR #77, `a66160b`),
narrowed to `docs/ArchitectureScorecard.md` only. Implemented (commit `b7b2095`): every existing
capability row reassessed against current `main` — source, tests, ADRs, `docs/ImplementationLog/`,
`PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md` — not inferred from merged-PR/task-Done status
alone; obsolete Stage 2/2.5/3/4 terminology corrected to the Stage 3 classification throughout; the
Electron refresh-token-not-consumed gap (ADR-0018 D6) explicitly re-confirmed against current source
and flagged as unresolved, not marked complete. A reviewer (communicated directly in the authorizing
chat session, not a formally-adopted Independent Technical Verifier role — see the governance note
below) found one narrow arithmetic defect: the Technical Debt paragraph's Stage 2.5 finding count
("Four of twelve") didn't match the five resolved IDs and six open IDs it itself listed. Rework
commit `fcd8c47` reconciled it against `IMPLEMENTATION_QUEUE.md`'s own findings table — `F7`
(resolved pre-Stage-3, via `T15`/ADR-0015) had been omitted — to the correct 6 resolved (`F1`, `F4`,
`F5`, `F7`, `F10`, `F11`) + 6 open (`F2`, `F3`, `F6`, `F8`, `F9`, `F12`) = 12, without changing any
classification to force the arithmetic. `git diff --check` confirmed clean and the cumulative PR diff
confirmed to touch only `docs/ArchitectureScorecard.md`. Merged: PR #78, commits `b7b2095`/`fcd8c47`,
merge `b5505bb` — independently re-verified this session via `git log`/`git show` and
`gh pr view 78` (state `MERGED`), not taken on faith. **`T81`/`T82` remain untouched and
unauthorized** throughout `T80`'s entire cycle — confirmed directly, not assumed. Separately, between
the 2026-08-21 catch-up above and this update, four more governance PRs merged and are recorded here
for continuity: PR #74 (`e4d2f18`) resolved the Stage-numbering inconsistency the catch-up above
disclosed — the project is now formally, consistently Stage 3 throughout `PROJECT_STATE.json`'s
`stages[]` array (the superseded `stage-4` entry preserved as historical record, not deleted); PR
#75 (`3a1dae7`) formally adopted Frontend Developer as a standing role; PR #76 (`13d8871`) corrected
the dangling `Legal_DMS_Process_Supervision.md` citation at its source; PR #73 (`4480f3b`, rework
`630d970`) was this file's own prior current-state synchronization pass.

**Correction (2026-08-22, continued, Documentation Manager, one-merge current-state fix):** the
paragraph above's own "`main` at `b5505bb`" framing was accurate when written, but that paragraph
was itself the synchronization performed by PR #79 — its eventual merge commit couldn't be
"current" before it existed. `main`'s actual current HEAD is now `a0c7a05` (`Merge pull request #79
from Intelligentclown/docs/t80-t82-current-state-sync`), independently confirmed via `git
rev-parse`/`gh pr view 79` this session. `T80`'s substance above (Done, merged, `docs/
ArchitectureScorecard.md` reassessed) is unaffected — only the "current main" pointer needed
correcting. `T79` remains `INCOMPLETE / NOT VERIFIED`; `T82` remains unauthorized, unimplemented.

**Update (2026-08-28, Documentation Manager, `T97` sync — this file had gone stale again, fourteen
tasks behind: `T83`–`T96` were not reflected here at all before now).** Brief bridge, then the main
series:

- **`T83`–`T85`, done and merged.** Closed out `T82`'s live-confirmed Electron
  session-restoration `FAIL` (Administrator test-account provisioning; the session-restoration
  fix itself; a preload-script load-failure fix that had been blocking that fix's own native
  verification). `T82`'s own disposition remains `FAIL`, unchanged by this — see
  `docs/SessionReport.md`'s `2026-08-22` entry for the full execution record.
- **`T86`, done and merged.** Adopted `docs/Legal_DMS — Domain Model & Functional Specification.md`
  as the governed pre-Stage-4 planning baseline.
- **`T87`–`T94`, each done and merged.** Resolved eight of the specification's twenty Required
  ADRs (`ADR/0021`–`0028`, covering #1/#19, #18, #2, #3/#4/#6, #5, #7, #9, #13) — full detail in
  each task's own `IMPLEMENTATION_QUEUE.md` row and `docs/reviews/T<N>_*.md` report, not
  duplicated here. Each followed a three-PR governance lifecycle (authorization →
  architecture/implementation+QA → governance closeout), now formally documented in
  `PROJECT_WORKFLOW.md` §3.1 (added by `T96`, below). `T94`'s own history is worth reading
  directly (`docs/reviews/T94_Software_Architect_Report.md`) — it surfaced and self-corrected two
  real governance defects (authorization recorded only conversationally at first; an architecture
  branch that had not actually incorporated its own later-recorded authorization), both caught by
  independent pre-merge verification rather than assumed clean.
- **`T95`, done and merged.** Added `scripts/governance_validate.py` (duplicate task IDs, missing
  authorization/QA evidence, ADR integrity, `PROJECT_STATE.json` `governanceLedger` drift), its
  35-test suite, and a `governance.yml` CI workflow — see
  [docs/GOVERNANCE_VALIDATION.md](GOVERNANCE_VALIDATION.md) for exactly what it checks and does
  not. Also added the "Governance & Task Authorization Model" section now in
  [`/AI_BOOTSTRAP.md`](../AI_BOOTSTRAP.md) and the `governanceLedger` field now in
  [`/PROJECT_STATE.json`](../PROJECT_STATE.json) — the fastest, mechanically-validated way to check
  which Required ADRs are resolved and which task was most recently authorized/Done, rather than
  re-deriving either by hand from this file.
- **`T96`, done and merged.** Codified the three-PR lifecycle into
  [`/PROJECT_WORKFLOW.md`](../PROJECT_WORKFLOW.md) §3.1 and extended
  [`/docs/prompts/ProjectManager.md`](prompts/ProjectManager.md) §9 with a required
  authorization-commit-ancestry pre-merge check, grounded explicitly in `T94`'s incident history.
- **`T97`, done and merged.** Documentation Manager Sync: refreshed this file, `docs/ProjectStatus.md`,
  `docs/SessionReport.md`, `PROJECT_STATE.json`'s top-level snapshot, and `PROJECT_WORKFLOW.md` §6's
  CI-workflow count through the completed `T86`–`T96` series. Merged same day as authorized: PR #145
  (merge `c9438de`), QA Approved with comments.

`T86`–`T97` was pre-Stage-4 governance/architecture-preparation work, not Stage-3 implementation —
`PROJECT_STATE.json`'s `currentStage` is not being reinterpreted to claim Stage 3 status changed.

**Update (2026-08-31, Documentation Manager, post-`T103` synchronization, authorized by GitHub Issue
#167 — a narrow documentation-only pass, not its own numbered task; no `T104` created).** This section
had gone stale again at `T97`'s own authorization — its actual completion and all of `T98`–`T103` were
not reflected here before now:

- **`T98`, done and merged.** Drafted and resolved Required ADR #14 (Activity vs Audit architecture)
  as [`ADR/0029`](../ADR/0029-activity-vs-audit-architecture-boundary-and-coverage.md) — `activity_logs`
  (descriptive) and `audit_logs` (accountability) confirmed as two permanently distinct mechanisms,
  composed with, not modified by, `ADR/0007`/`ADR/0009`; discloses, without resolving, that neither
  table carries `organization_id` relative to `ADR/0021`'s mandate. QA Approved with comments
  (`docs/reviews/T98_Software_Architect_Report.md`; a later delta re-review independently reconfirmed
  the merged content byte-identical). Merged PR #148 (merge `acd5125`).
- **`T99`, done and merged.** Governance Lifecycle / Required-CI Compatibility Remediation — added
  `governanceLedger.inProgressTransitions` to `scripts/governance_validate.py`, letting one legitimate,
  mechanically-verified in-progress Required-ADR transition pass Governance CI while genuine stale or
  unauthorized drift still fails it (14 new tests, 49 total). QA Approved with comments
  (`docs/reviews/T99_Governance_Transition_Mechanism_QA_Review.md`). Merged PR #151 (merge `0387440d`).
- **`T100`, done and merged.** Generalized `T99`'s own frontier-equality constraint after direct
  reproduction showed it wrongly rejected `T98`'s still-open PR once `T99` itself closed out first — a
  design gap in the delivered mechanism, not in `T98`. 51 tests total. QA Approved
  (`docs/reviews/T100_Frontier_Generalization_QA_Review.md`). Merged PR #154 (merge `3768348e`).
  **Disclosed, not concealed, and not yet closed out as its own governance item:** this closeout found
  the `main-required-ci` ruleset's `required_approving_review_count` had drifted from `1` to `0`, and
  three required status-check contexts no longer matched the workflows' actual job names — neither
  change caused or authorized by `T100`. `T101`'s and `T102`'s own QA records each independently
  re-fetched the ruleset afterward and found `required_approving_review_count` back at `1` and the
  names matching (`T99`'s own PR #150, `ci/t99-required-check-naming`, is the disclosed source of the
  naming fix) — but no task has ever formally adopted closing this specific finding as its own scope.
- **`T101`, done and merged.** Drafted and resolved Required ADR #8 (Matter-vs-File lifecycle/identity
  boundary) as [`ADR/0030`](../ADR/0030-matter-file-lifecycle-and-identity-boundary.md) — the governed
  specification's layered Matter→File model confirmed to control over
  `docs/BusinessRequirementsPlan.md`'s superseded File-Number-as-Matter-identity language; Required
  ADR #10/#12/#20 disclosed as coupled-but-unresolved. Merged PR #158 (merge `e7a29fae`) on a single
  collaborator approval **before** a formal QA Decision document existed — a disclosed departure from
  the pre-merge QA-persistence discipline every `T80`–`T100` task had actually followed. QA Decision
  Approved with comments recorded post-merge (`docs/reviews/T101_QA_Review.md`), independently
  re-verified against the actual merged `main` HEAD, not accepted from any prior report.
- **`T102`, done and merged.** Drafted and resolved User↔Organization membership, onboarding, and
  tenant-context semantics as [`ADR/0031`](../ADR/0031-user-organization-membership-onboarding-tenant-context.md)
  — a gap the specification's own twenty-item Required-ADR list never named (it sits between
  already-resolved #1 and #18): one-to-one optional cardinality; first-Organization creation folded
  into the existing `bootstrap-admin` CLI; a nullable `users.organization_id` FK orthogonal to
  `UserRole` (Roles/Permissions stay global); active tenant-context resolution via a live database
  read in `JwtAuthenticationProvider`, never a JWT claim; one new `CurrentUser.organization_id` field.
  **`ADR/0031` §15, and this task's own authorization text, both explicitly state that accepting the
  ADR does not itself authorize Organization/Tenant Core implementation.** Same disclosed post-merge
  QA-sequencing departure as `T101`. Merged PR #162 (merge `8038e66d`).
- **`T103`, done and merged.** Drafted and resolved the narrow User/Organization
  pre-existing-data-reconciliation slice of Required ADR #20 as
  [`ADR/0032`](../ADR/0032-user-organization-pre-existing-data-reconciliation.md) — how the one
  pre-`ADR-0031` `User` row (the `T83`-bootstrapped Administrator) is reconciled with the new
  `organization_id` column during migration. Explicitly does **not** claim to resolve the
  specification's own §21 migration-strategy planning-list item as a whole — Required ADR #10, #11,
  #12, #15, #16, #17, and the general #20 remain unresolved. This task's own authorization required
  the QA Decision to be persisted and independently re-verified **before** merge, restoring the
  discipline `T101`/`T102` had departed from — and it was (review submitted
  2026-08-31T12:17:44Z, merge 12:24:50Z). QA Decision Accepted with comments
  (`docs/reviews/T103_QA_Review.md`). Merged PR #165 (merge `106f2e9`); governance closeout PR #166
  (merge `d94d219`).

Current settled governance state, per `PROJECT_STATE.json`'s `governanceLedger` (mechanically
validated, not hand-derived): `latestTaskDone`/`latestTaskAuthorized` both `T103`; ten of the
specification's twenty Required ADRs resolved (`#1`–`#9`, `#13`, `#14`, `#18`, `#19` — the exact set
is `resolvedRequiredADRs`); seven unresolved (`#10`, `#11`, `#12`, `#15`, `#16`, `#17`, `#20`). **No
Organization/Tenant Core implementation task, branch, or PR exists anywhere in this repository** —
that slice remains gated behind a fresh Project Manager/Control Tower re-assessment against
`ADR/0031`/`ADR/0032`, per `ADR/0031` §15 and `T102`'s own "crucial control" clause; this
synchronization pass (GitHub Issue #167, documentation-only, no `T104` created) does not perform or
imply that re-assessment. `T86`–`T103` was pre-Stage-4 governance/architecture-preparation work, not
Stage-3 implementation — `PROJECT_STATE.json`'s `currentStage` is not reinterpreted to claim Stage 3
status changed by any of it.

## Pending Work

**Update (2026-08-31, Documentation Manager, post-`T103` synchronization, GitHub Issue #167):** the
2026-08-28 paragraph immediately below is itself now stale — `T97` is Done (not merely authorized),
and `T98`–`T103` have all since completed (see "Current Stage" above for the full record). As of this
update: a follow-up implementation task for `T82`'s Electron session-restoration finding remains
**not authorized** (unchanged since 2026-08-21); seven Required ADRs (`#10`, `#11`, `#12`, `#15`,
`#16`, `#17`, `#20`) remain unresolved per `PROJECT_STATE.json`'s `governanceLedger`; and
Organization/Tenant Core implementation remains **not authorized**, gated behind a fresh Project
Manager/Control Tower re-assessment against `ADR/0031`/`ADR/0032` — that is the next governance gate,
not performed or implied by this synchronization pass.

**Update (2026-09-04, Documentation Manager, same-PR T113 synchronization on PR #195):** fresh
remote verification before editing confirmed PR #195 (`ci/t113-optimize-release-build-verification`)
remained open and unmerged at head `08e9d3e7d4b2e79e5f3339e652dac421cc22709c`, based on
`98cb4b383c58e61f0d99521fa9046840c1366633`; QA Approved evidence exists in
`docs/reviews/T113_QA_Review.md`; reviewed implementation head
`2e27f1baa043e4a4359fd032cf4b82dbad058875` and authorization commit
`3845a8975219b6b3efc1b2a05928e06e9dd13f19` both remain genuine ancestors of that current branch head;
and the only post-QA branch change before this pass was the QA evidence file itself. T113's bounded
CI optimization is now implemented and QA-approved but **not Done** pending this synchronization
commit, push, and a fresh CI run on the resulting exact head. `latestTaskDone` remains `T111`;
`latestTaskAuthorized` remains `T113`; `T112` remains authorized but untouched with no
Architecture+QA work started; `T114` remains unauthorized; and Required ADR #20 remains unresolved.

**Update (2026-09-04, Documentation Manager, T113 post-merge completion):** fresh remote verification
confirms PR #195 merged to `main` as `cbef9307484b8792899e090705a8610c76453bf2`, with parents
`98cb4b383c58e61f0d99521fa9046840c1366633` and final PR head
`2dc15bd631239e3d72233779f67b0c39b0974c9d`. The QA Approved commit
`08e9d3e7d4b2e79e5f3339e652dac421cc22709c` remains in that merge's ancestry. T113 is Done and
merged; `governanceLedger.latestTaskDone` and `latestTaskAuthorized` are both `T113`, and
`inProgressTransitions` remains empty. T112 remains authorized but not Done, with no architecture work
started; T114 remains unauthorized; Required ADR #20 remains unresolved.

**Update (2026-09-04, Documentation Manager, T112 governance closeout):** fresh remote verification
confirmed `origin/main` at `534e469d67ffad0b255903762cd166dcc401a4cd`, the merge commit for PR #197,
with parents `2f27712109753fce0cd83ad4b8b5b397d11fec66` and final PR head
`44e2b1eaade649d2eeead93ecd34680ca9d56a4a`. T112's reviewed architecture commit
`f68e8e3d5e47435a032ae5b32ec5961ba2ee4b6a`, QA Approved evidence commit/head
`44e2b1eaade649d2eeead93ecd34680ca9d56a4a`, and authorization commit
`63251e4210bc5d97e739d570d8d614941eca08e6` via PR #194 all remain in ancestry. T112 is now Done and
merged as the ADR-0034 architecture-only outcome. `governanceLedger.latestTaskDone` and
`latestTaskAuthorized` correctly remain `T113` by validator semantics because T113 is already the
higher-numbered Done/authorized task. T114 remains unauthorized, `inProgressTransitions` remains
empty, and Required ADR #20 remains unresolved globally except for already-bounded prior slices.

**Update (2026-09-05, Documentation Manager, T114 governance closeout):** fresh remote verification
confirmed `origin/main` at `663dba0ef3cb85b9e517e23f218696536783da8f`, the merge commit for PR #200,
with parents `ff9deacfbb7125ed47866a1e564442bfe5edb98b` and final QA-approved PR head
`3b287b37b503f9be4e6f1265b76d751d8f2f5ec5`. PR #199 authorization commit
`855aec1afb07f56ac26c18f5804191f49bfe494f` and the final QA head remain in merge ancestry. T114 is
now Done as the ADR-0035 architecture-only outcome; ADR-0035 remains `Proposed`, unchanged by this
closeout. `governanceLedger.latestTaskDone` and `latestTaskAuthorized` are both `T114`,
`inProgressTransitions` remains empty, Required ADR #20 remains unresolved globally, and T115+ is
not authorized. No implementation, schema, migration, RLS, backfill, API, frontend, Electron, or
future-task work was performed.

**Update (2026-08-28, Documentation Manager, `T97` sync), preserved for continuity:** the 2026-08-21
paragraph below is itself now stale in one respect — a follow-up implementation task for `T82`'s
Electron session-restoration finding remains **not authorized** (unchanged), but it is no longer the
only open item: `T97` (this sync) is **authorized, not yet Done** (`IMPLEMENTATION_QUEUE.md`'s `T97`
row, PR #144), and nine Required ADRs (`#8`, `#10`, `#11`, `#12`, `#14`–`#17`, `#20`) remain
unresolved per `PROJECT_STATE.json`'s `governanceLedger` — see "Current Stage" above for the full
`T83`–`T96` record.

**Update (2026-08-21, Documentation Manager catch-up):** the paragraph below describes the state as
of Stage 2's close and is preserved as historical context, not current reality — see the `T70`–`T82`
catch-up under "Current Stage" above for what's actually pending now. In short: `T41`–`T78` are done
and merged; `T79` (verification-only) is closed as `INCOMPLETE / NOT VERIFIED`; `T82` (Electron-
runtime live smoke verification) is the only open, scoped item, and it is **not authorized**. A
Project Manager cycle must record explicit authorization before any `T82` implementation begins. See
[PROJECT_CHECKPOINT.md](../PROJECT_CHECKPOINT.md) for the fullest current-state detail.

Everything past Stage 2, as originally written here. **Nothing is scoped yet** — see
[Roadmap.md](Roadmap.md). The most likely next step is wiring a real feature (repository → service →
route) to a slice of the Stage 2 schema, but that must be confirmed with the project owner, not
assumed. Separately, **Stage 2.7 has one open item**: `IMPLEMENTATION_QUEUE.md` T35 — a real GitHub
Actions run has not been observed yet, since that requires a `git commit` + `git push`, a
confirm-first action not taken as part of
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

**Governance note, not an ADR (2026-08-21, Documentation Manager catch-up) — "Independent Technical
Verification" and the "Frontend Developer" role, disclosed rather than resolved:** `T69`–`T75`'s own
records (and `PROJECT_STATE.json`'s `git.note`) refer to a "Frontend Developer" role distinct from
"Backend Developer," and `T72`/`T73` record a second review step, "Independent Technical
Verification," alongside the normal QA Decision. Neither is documented as a formal role in
`PROJECT_WORKFLOW.md` §7's AI Roles table or as a prompt under `docs/prompts/`. One `PROJECT_STATE.json`
note additionally cites a governing document, `Legal_DMS_Process_Supervision.md`, for the Independent
Technical Verifier's role-fallback procedure — **that file does not exist anywhere in this repository
or its git history**, confirmed by direct search this session. Both are operational practices that
have not been through this project's "process changes are versioned" proposal/review/sign-off
discipline (`AI_BOOTSTRAP.md`). See [`docs/prompts/README.md`](prompts/README.md)'s own governance
note (mirroring the existing disclosure it already carries for `GitCI_PR_Manager.md`) for the full
disclosure.

**Update (2026-08-22, Project Manager, project-owner authorized).** Both items are now resolved.
Frontend Developer is formally adopted as a standing role, kept strictly separate from Backend
Developer — see [`docs/prompts/FrontendDeveloper.md`](prompts/FrontendDeveloper.md) and
`PROJECT_WORKFLOW.md` §7. The `Legal_DMS_Process_Supervision.md` citation named above has been
corrected at its source (`PROJECT_STATE.json`'s `git.note`) to state plainly that no such document
exists and that the fallback it referenced was never a documented procedure. Independent Technical
Verifier remains explicitly **not** formally adopted, per the project owner's 2026-08-21 decision —
no further ad hoc verification pass should be treated as mandatory unless a future governance
proposal defines and authorizes it.

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

**Update (2026-08-22, continued):** `main`, at `a0c7a05`, independently re-verified via `git
rev-parse`/`gh pr view 79` this session — one merge ahead of the paragraph immediately below,
whose `b5505bb` was accurate at the time but is now superseded: that paragraph's own synchronization
work was PR #79, merged as `a0c7a05` (`docs/t80-t82-current-state-sync`) after the paragraph itself
was written. `main` is once again the correct current branch to work from.

**Update (2026-08-22):** `main`, at `b5505bb`, independently re-verified via `git fetch`/`git log`/
`gh pr list` this session — six merges ahead of the 2026-08-21 note below (PR #73–#78). This
session's own edits are on `docs/t80-t82-current-state-sync`.

**Update (2026-08-21), preserved for continuity:** `main`, at `95bfae1`, independently re-verified via `git status`/`git log`
this session — `feature/<name>`/`docs/<topic>` branches off `main`, merged via PR, is now this
project's settled standing workflow (confirmed by every `T52`–`T79` batch since), not merely scoped
to Stage 2.7 as the paragraph below once asked to confirm.

Original note, preserved for continuity: `feature/github-actions-ci` — a feature branch was in use
for Stage 2.7's work (unlike every prior stage, which worked directly on `master`/`main`); confirm
with the project owner whether this becomes the project's standing workflow or was scoped to this one
stage before assuming either way.

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
protected route exists (`T58`+).

**`T57` followed, and the authorization-recording discipline held a second consecutive time.**
`T57`'s original test-only wording (including a `configure_container()` criterion `T55` had already
made obsolete) was corrected before implementation: the real objective was closing the 401/403 gap —
`RequirePermission` previously returned `ForbiddenError`/403 for both an anonymous caller and an
authenticated-but-unpermitted one, indistinguishably. The authorized fix (Option 1, recorded in
`65dd563` **before** implementation commit `7c9fc3a`, confirmed by timestamp order) has
`_require_permission` check `user.is_authenticated` first, raising `UnauthorizedError`/401 directly
if not authenticated — `AuthorizationService`'s port, `RbacAuthorizationService`, and
`PermissiveAuthorizationService` were **not** touched. `T57` is now **Done**: 3 new tests + 1
updated, full suite 386/386 passing, `ruff`/`black` clean, boot succeeds, 127/127 integration tests
against live Postgres — merged `7c9fc3a` → PR #20 → `472f7cb`. **QA Decision: Approved with
comments** — no technical defects; the comment preserves, as a non-blocking historical observation,
the already-flagged deferral of true `TestClient`-level HTTP verification to `T58`+ (no protected
route exists yet). **With `T57` closed, Stage 3 Phase 2 (`T52`–`T57`) is complete in full**, and
Phase 3 (routes) begins.

**`T58` followed — the first route in this project, and the third consecutive batch to hold the
authorization-recording discipline.** `presentation/api/v1/auth.py` (new) adds
`POST /api/v1/auth/login`: email + password in, access + refresh tokens out, or a structured 401 via
the existing global `AppError` handler (`AuthService.authenticate()`'s `Result.error` raised
directly, no route-level exception handling). `LoginRequest`/`LoginResponse` are co-located, no
`ApiResponse[T]` wrapper — a token pair isn't a fetchable resource. `deps.py` gains
`get_auth_service()`/`AuthServiceDep`, request-scoped construction from `DBSessionDep` mirroring
`T55`'s pattern exactly. The authorized scope (recorded in `58c8e40` **before** implementation commit
`76cd28f`, confirmed by commit order) was: the route, its schemas, per-request `AuthService` wiring,
router registration, and tests — `T59`–`T67` explicitly out of scope. `T58` is now **Done**: 5 new
integration tests in `tests/integration/test_auth_login.py` (valid credentials, wrong password,
unknown email — same generic message, inactive user, malformed body → 422) against a real mounted app
and live Postgres via `httpx.AsyncClient`/`ASGITransport` — `fastapi.testclient.TestClient` was tried
first and found incompatible with the `get_db` dependency-override this required, since it runs the
app on a separate event-loop thread. Full suite 391/391 passing (386 prior + 5 new), `ruff`/`black`
clean, boot smoke test passed — merged `76cd28f` → PR #22 → `e67da02`. **QA Decision: Approved with
comments** — no technical defects; two non-blocking comments preserved verbatim: Starlette's
`HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning is framework-internal, and the test-local
`app.dependency_overrides[get_db]` pattern is safe only under sequential test execution.

**`T59` followed — the second route in this project, reusing `T58`'s infrastructure directly, and the
fourth consecutive batch to hold the authorization-recording discipline.** `presentation/api/v1/auth.py`
was extended (not `deps.py`/`router.py` — `T58`'s `AuthServiceDep` and router mount reused unchanged)
with `POST /api/v1/auth/refresh`: refresh token in, rotated access + refresh tokens out, or a
structured 401 via the same `result.error`-raised-directly pattern `login` established.
`RefreshRequest`/`RefreshResponse` are co-located, bare, matching `login`'s convention. The authorized
scope (recorded in `163085d`, 2026-08-15 11:06:35 IST, **before** implementation commit `56eb7c2`,
11:17:32 IST, ~11 minutes later same day, confirmed by commit order) was: the route, its schemas,
reuse of the existing `AuthServiceDep`, and tests covering successful refresh/rotation and
invalid/expired/revoked/unknown tokens — `T60`–`T67` explicitly out of scope. `T59` is now **Done**:
7 new integration tests in `tests/integration/test_auth_refresh.py`, reusing `T58`'s
`httpx.AsyncClient`/`ASGITransport`/`get_db`-override pattern verbatim. Full suite **398/398 passing
(391 prior + 7 new) — personally re-run against live Postgres this session** (Docker was reachable
this time, unlike `T58`'s closeout), `ruff`/`black` clean, boot smoke test passed — merged `56eb7c2` →
PR #24 → `721cec5`. `app.openapi()["paths"]` independently confirmed to contain only
`login`/`refresh`/`health`/`version` — no `T60`+ scope creep. **QA Decision: Approved with comments**
— "no technical defects" per PR #24's own report; unlike `T58`'s PR, PR #24 does not itemize specific
non-blocking comment text anywhere in the repository (PR body, both commit messages, and
`gh api .../pulls/24/reviews` all checked) — recorded here exactly as given, not invented.

**`T60` followed — the third route in this project, and the fifth consecutive batch to hold the
authorization-recording discipline.** `presentation/api/v1/auth.py` was extended (`deps.py`,
`router.py`, and `AuthService` itself **not modified** — an explicit "must not modify" constraint the
authorization stated outright, not merely an expected reuse convention like `T59`'s) with
`POST /api/v1/auth/logout`: `LogoutRequest` co-located; `logout()` calls `AuthService.revoke()`
(`T50`/`T51`, unmodified — returns `None`, never a `Result`, since an unknown or already-revoked
token is a silent no-op, not a failure) and returns `204 No Content` with no body, mirroring
`presentation/common/crud_router_factory.py`'s `delete_item`. The authorized scope (recorded in
`726e8cf`, 2026-08-15 11:57:59 IST, **before** implementation commit `5b9bf57`, 12:05:34 IST, ~8
minutes later same day, confirmed by commit order) was: the logout route, request/response handling,
reuse of the existing `AuthServiceDep`, and tests explicitly proving idempotent behavior — `T61`–`T67`
explicitly out of scope. `T60` is now **Done**: 5 new integration tests in
`tests/integration/test_auth_logout.py` (a valid token actually revoked, verified against the stored
`RefreshToken` row; an already-revoked token, an unknown token, and a malformed token string all still
succeed; a malformed body → 422), reusing `T58`/`T59`'s
`httpx.AsyncClient`/`ASGITransport`/`get_db`-override pattern verbatim. Full suite **403/403 passing
(398 prior + 5 new) — personally re-run against live Postgres this session**, `ruff`/`black` clean,
boot smoke test passed — merged `5b9bf57` → PR #26 → `941ed42`. `app.openapi()["paths"]` independently
confirmed to contain only `login`/`refresh`/`logout`/`health`/`version` — no `T61`+ scope creep.
**QA Decision: Approved** — a deliberate distinction from `T58`/`T59`'s "with comments," not an
oversight: PR #26's body states "no defects" without the "with comments" qualifier the two prior
batches both carried, and itemizes no comment text anywhere in the repository — recorded as the
disposition its own source material actually states, not inherited from the immediately preceding
pattern. `T61`+ (`/me`, user management, role assignment, cross-route tests, audit wiring) is now the
next unfinished work, not yet started, not
authorized. See
[docs/Stage3_Backend_Handoff.md](Stage3_Backend_Handoff.md) for Phase 2–4's
full file-by-file map. Two smaller open items: (1) the `role_permissions` exact matrix (`T66`) still
needs its own sign-off before that migration is written; (2) the authorization-recording discipline
`T52`/`T53`/`T54`/`T55` each failed at, four batches running — `T56`, `T57`, `T58`, `T59`, and now
`T60` have all held it, five consecutive successes now; `T61`+ should keep holding the same standard.

**`T61` followed — the sixth consecutive batch to hold the authorization-recording discipline, and the
first Phase 3 route needing `CurrentUserDep`/`RequirePermission`'s `is_authenticated` check rather than
just `AuthServiceDep`.** `presentation/api/v1/auth.py` was extended with a co-located `MeResponse` and
a `me()` handler taking `CurrentUserDep` directly — `deps.py`, `router.py`, `AuthService`, `CurrentUser`,
`JwtAuthenticationProvider`, and `RbacAuthorizationService` all untouched. `CurrentUserDep` never
raises, so `me()` itself raises `UnauthorizedError` when `is_authenticated` is `False`, requiring no
permission code. Unlike `login`/`refresh`/`logout`, the response is wrapped in `ApiResponse[MeResponse]`
— an authorized departure, since `/me` fetches a resource — with `roles` sorted before emission. 7 new
integration tests in `tests/integration/test_auth_me.py`. Full suite **410/410 passing (403 prior + 7
new)**, `ruff`/`black` clean, boot smoke test passed, `app.openapi()["paths"]` confirmed to contain
exactly the six expected routes — no scope creep. **QA Decision: Approved** (plain, no comments) —
recorded in `docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision — T61 batch` section, rendered by
the QA Reviewer role independently against the working tree before it was committed. **`T61` is now
Done — merged.** Feature commit `fa57e28`, PR #30, merged `bdffb5e` (2026-08-15); independently
re-verified post-merge this session: `main`/`origin/main` both at `bdffb5e`, `git show bdffb5e --stat`
confirms exactly the nine files this batch's scope covers (no forbidden file touched), 6/6 CI checks
green, and the full suite (410/410) re-run against merged `main` with live Postgres.

**`T62` followed — five hand-written user-management routes, the seventh consecutive batch to hold the
authorization-recording discipline, and the first Phase 3 batch to reach `RequirePermission`'s 403 half
(authenticated-but-unpermitted) via a real HTTP request, not just `T61`'s 401 half.** New
`presentation/api/v1/users.py`: `GET`/`POST /api/v1/users`, `GET`/`PUT /api/v1/users/{id}`,
`POST /api/v1/users/{id}/deactivate`, all gated by one router-level
`RequirePermission("users:manage")` — `crud_router_factory.py`, `deps.py`, `AuthService`, `CurrentUser`
all untouched, `router.py` changed only to mount the new router. Reuses `BaseService[User]`
(`T55`)/`SqlAlchemyUserRepository` (`T50`)/`hash_password()` (`T46`) directly; a local, module-only
`get_user_repository()`/`get_user_service()` pair, not added to `deps.py`. `deactivate_user()` calls
`service.update()`, never `delete()` — row and `UserRole`/`RefreshToken` relationships preserved,
idempotent. `T63` (role assignment) explicitly out of scope — created users have zero roles. 28 new
integration tests in `tests/integration/test_users.py`. The authorized scope (recorded in `e10bdc8`,
2026-08-16, **before** implementation commit `a3e8810`, confirmed by commit order) matches exactly what
merged — `git diff ea80b74 3a4a21c --name-only` confirms exactly four files across the full
authorization-to-merge range, no forbidden file touched. Full suite **438/438 passing (410 prior + 28
new)**, `ruff`/`black` clean, boot smoke test passed, `app.openapi()["paths"]` confirmed to contain
exactly the nine expected routes. **`T62` is now Done — merged.** Feature commit `a3e8810`, PR #33,
merged `3a4a21c` (2026-08-16). **QA Decision: Approved with comments** — no technical defect; the
comment is a **named governance finding**: `T62`'s merge (PR #33 → `3a4a21c`) happened **before** any
QA Decision existed anywhere in the repository, violating `PROJECT_WORKFLOW.md`'s standard lifecycle
and this batch's own explicitly stated intent that merge wait for it. A pre-merge QA pass had already
reached this identical disposition on the merits — only its repository-visible recording was skipped,
which is what let the merge proceed unblocked. A Documentation Manager closeout attempt correctly
halted on discovering no QA Decision existed for `T62` despite the code already being merged; the QA
Decision was subsequently recorded directly in `docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision
— T62 batch` section and independently re-verified this session before this record was written. This
finding is preserved as permanent governance history, the same discipline this project applied to
`T52`–`T55`'s authorization-recording gaps — not a reason to reopen or rework the code.

**`T63` followed — role-assignment routes, the eighth consecutive batch to hold the
authorization-recording discipline, and the first to extend `RequirePermission` itself.** New
`POST /api/v1/users/{id}/roles` (assign) and `DELETE /api/v1/users/{id}/roles/{role_id}` (remove),
gated by a router-level `RequirePermission("users:manage", "roles:manage")`.
`RequirePermission(permission: str)` was extended to `RequirePermission(*permissions: str)` — grants
access on any one supplied permission; every existing single-argument call site is unaffected (the new
"try all but the last" loop never runs for one argument, confirmed by the unchanged
`TestRequirePermission` suite, 8/8 still passing). New narrow `assign_role()`/`remove_role()` on
`UserRepository`/`SqlAlchemyUserRepository` (no new repository class), role existence checked via the
existing generic `AbstractRepository[Role]`. `UserRead`/`UserCreate`/`UserUpdate` (`T62`) untouched; no
`Role`/`RolePermission` creation; no migration. One file outside the originally-listed scope, flagged
before editing: `tests/support/in_memory_user_repository.py` needed the same two new methods to keep
satisfying the now-larger `UserRepository` ABC — a mechanical consequence of the interface extension,
independently confirmed genuinely necessary and minimal, not a scope expansion. 21 new integration
tests. **QA Decision: Approved** (plain) — rendered pre-merge, directly against PR #36
(`feature/stage3-t63-role-assignment` at `3cea676`, base `main` at `97ab953`) — no technical defects,
no unresolved scope issue — its QA-approval commit (`6a8608f`) was committed and pushed to the feature
branch **before** PR #36 merged, the deliberate correction of `T62`'s own named governance finding.
Full suite **459/459 passing** (438 prior + 21 new), `ruff`/`black` clean, boot smoke test passed,
`app.openapi()["paths"]` confirmed to contain exactly the eleven expected route/method combinations —
personally re-run against merged `main`, not just the PR branch. **`T63` is now Done — merged.**
Feature commit `3cea676`, QA-approval commit `6a8608f`, PR #36, merged `ef419c3` (2026-08-16);
`main`/`origin/main` both independently re-verified at `ef419c3`, `git diff 97ab953..ef419c3
--name-only` confirms exactly the seven files this batch's scope covers, no forbidden file touched.
`T64` is now Done — merged. Feature commit `f321065`, QA-approval commit `fc9fb0b`, PR #38, merged `fab2933` (2026-08-16); `main`/`origin/main` both independently re-verified at `fab2933`.

**`T65` followed — wiring the existing `AuditLogger` port (unused since Stage 1) into login outcomes
and permission-denied events, no new audit capability or schema.** `AuthService.authenticate()` records
`login_success`/`login_failure` (`resource_type="auth"`, failure `reason` distinguished only in the
audit trail, never in the still-generic-401 response); `RequirePermission`'s final-candidate denial
records `permission_denied` (`resource_type="endpoint"`) before re-raising the identical
`ForbiddenError`, `T63`'s OR-permission semantics preserved exactly. **This batch's governance history
is worth stating in full, not collapsed into a clean single-pass story:** implementation PR #41
(`fab38e3`) was opened without a `Phase3.md` batch narrative; a first independent QA pass found the
implementation itself defect-free but blocked on that missing entry (no formal `Rework required`
checkbox was rendered — the finding was communicated narratively and left the QA Decision pending); a
documentation-only correction (`d270828`) added the standard batch and, while writing it, independently
caught and fixed a factual error in the rework instructions themselves (they cited `b63bc6d` — actually
`T64`'s authorization commit — instead of `T65`'s real one, `095ac91`); a second, independent QA pass
then re-verified everything end-to-end (23/23 targeted tests, 481/481 full suite, `ruff`/`black` clean,
boot smoke + unchanged `OpenAPI` surface, PR #41 CI 6/6 green) and rendered **QA Decision: Approved**,
committed as `9ac7191` **before** PR #41 merged — continuing, not breaking, the pre-merge-QA-Decision
discipline `T63` established. One unrelated environment issue disclosed rather than worked around by
changing any project file: a stale `.env` `DATABASE_URL` port versus the actually-running Postgres
container, corrected locally via an environment-variable override only. **`T65` is now Done — merged.**
Authorization commit `095ac91` (PR #40, merged `61e64d3`), implementation commit `fab38e3`,
documentation-correction commit `d270828`, QA-approval commit `9ac7191`, PR #41, merged `d91d00c`
(2026-08-17); `main`/`origin/main` both independently re-verified at `d91d00c`.

**`T66` followed — the first task past Stage 3's routes phase, tracked in a new
`docs/ImplementationLog/Stage4/Phase0.md` rather than `Phase3.md`.** A new migration seeds exactly 59
authorized `role_permission` associations against the owner-approved matrix, UUIDs dynamically
resolved from the existing `roles`/`permissions` rows; downgrade removes only the T66-created
associations; exactly one Alembic head (`224b650e5235`) confirmed after the migration. Exhaustive
matrix-validation tests added, `T63`/`T65` regression preserved. **Governance history, preserved not
collapsed:** the initial QA review returned substantive rework findings, resolved in a follow-up
commit, followed by a separate formatting correction, before the final QA pass rendered **QA Decision:
Approved** (plain), committed (`5ab88a5`) **before** PR #44 merged. **`T66` is now Done — merged.**
Authorization commit `66f94bf` (PR #43, merged `81bf99f`), implementation commit `533226d`,
QA-rework commit `b2b86b6`, formatting-correction commit `0239d80`, QA-approval commit `5ab88a5`,
PR #44, merged `2edc23e` (2026-08-17); `main`/`origin/main` both independently re-verified at
`2edc23e`.

**`T67` (first-admin bootstrap CLI) followed.** New `infrastructure/cli/bootstrap.py`:
`run_bootstrap(session, *, email, password)` is the testable core (no-op if any `User` row exists;
otherwise creates the `User` via `hash_password()` and assigns the seeded `Administrator` role via
`UserRole`, `flush()`-only); `main()`/`_async_main()` reads the password via `getpass.getpass()` only
— never `argv`/env/a config file (`ADR-0018` D4). New `[project.scripts]` entry `bootstrap-admin` in
`backend/pyproject.toml`. 5 new integration tests in `tests/integration/test_bootstrap_admin.py`. Full
suite **487/487 passing (482 prior + 5 new)**, `ruff`/`black` clean. **QA Decision: Approved with
comments** — `D4` compliance and idempotency independently re-verified, not taken on the Developer's
word; two non-blocking comments (hand-rolled persistence instead of reusing
`SqlAlchemyUserRepository.assign_role()`; an untested missing-role `RuntimeError` guard). Authorization
commit `119d612` (PR #46, merged `65b737a`) precedes implementation commit `b409f78` — confirmed by
commit order. **`T67` is now Done — merged.** Feature commit `b409f78`, QA-approval commit `790b778`,
PR #47, merge commit `fc0b142` (2026-08-18) — `main`/`origin/main` both independently re-verified at
`fc0b142` this session, full suite **487/487 passing** personally re-run against merged `main` with
live Postgres, `ruff`/`black` clean, boot smoke passed, `app.openapi()["paths"]` unchanged (still
exactly the eleven routes `T63` established — `T67` adds a CLI entry point, not a route). See
`docs/ImplementationLog/Stage4/Phase0.md`'s T67 batch for full detail.

**`T68` (bootstrap CLI entry-point test coverage) followed** — closes the gap `T67`'s QA Decision
flagged: two new test classes in `test_bootstrap_admin.py` exercise `_async_main()` directly, proving
a first invocation actually commits (via a second, independent database connection) and a
second/existing-user invocation is a clean, non-prompting no-op. `bootstrap.py` itself byte-for-byte
unchanged — test-file-only. 3 new tests, full suite **490/490 passing**, `ruff`/`black` clean. **QA
Decision: Approved** (plain) — QA independently ran a mutation test (temporarily removed
`bootstrap.py`'s `commit()` call, confirmed both "actually commits" tests fail, reverted), proving the
tests non-vacuous. Authorization commit `d6b6b45` (PR #49, merged `5bca735`) precedes implementation
commit `33c728b`. **`T68` is now Done — merged.** Feature commit `33c728b`, QA-approval commit
`5b5c9b9`, PR #50, merge commit `43aa0a7` (2026-08-18) — `main`/`origin/main` both independently
re-verified at `43c8ddb` this session, full suite **490/490 passing** personally re-run against merged
`main` with live Postgres, `ruff`/`black` clean, boot smoke passed, `app.openapi()["paths"]` unchanged.
**Stage 4 Phase 0 (`T66`–`T68`) is now complete in full and merged.** See
`docs/ImplementationLog/Stage4/Phase0.md`'s T68 batch for full detail.

**`T69` (`httpClient.ts` `post`/`put`/`delete` + structured error parsing) followed.** `post`/`put`/
`delete` added to `httpClient.ts` alongside `get()`, sharing a new `requestWithBody()` helper;
`HttpError` gained an optional `code` populated from the backend's structured
`{"error":{"code","message"}}` body when present, falling back to the existing generic message
otherwise; `get()`/`request<T>()`'s success path unchanged. 8 new tests, full suite **17/17 passing**
(9 prior + 8 new), `eslint`/`prettier` clean. **QA Decision: Approved** (plain) — scope and
authorization-before-implementation commit order independently re-verified. **`T69` is now Done —
merged.** Feature commit `cca729f`, QA-approval commit `6b90ede`, PR #54, merge commit `5196fdf`
(2026-08-18) — `main`/`origin/main` both independently re-verified at `5196fdf` this session, full
suite **17/17 passing** personally re-run against merged `main`, `eslint`/`prettier` clean. **Stage 4
Phase 5 (`T69`) is now complete in full.** See `docs/ImplementationLog/Stage4/Phase1.md`'s Post-Merge
Verification — T69 batch note for full detail.

Outside of Stage 3, do not add business entities, new major dependencies, or
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
