# Roadmap

Status values: `Not Started`, `Planned`, `In Progress`, `Completed`, `Deferred`, `Cancelled`.

## Stage 0 — Project Foundation

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Repo skeleton & dev tooling | High | — | Completed |
| Backend foundation (config, logging, errors) | High | Repo skeleton | Completed |
| Backend API + DB (FastAPI, SQLAlchemy, Alembic) | High | Backend foundation | Completed |
| Backend tests (pytest) | High | Backend API + DB | Completed |
| Electron shell | High | Repo skeleton | Completed |
| Frontend foundation (Vite/React/Tailwind/shadcn) | High | Repo skeleton | Completed |
| Frontend↔backend E2E proof (HealthCheckPage) | High | Frontend + backend foundations | Completed |
| Frontend tests (Vitest/RTL) | High | Frontend foundation | Completed |
| Full documentation pass | High | All of the above | Completed |

Stage 0 has no business features — see [KnownIssues.md](KnownIssues.md) for the two open
tooling caveats (shadcn CLI, react-router-dom advisory) carried forward.

## Stage 1 — Core Architecture & Domain Foundation

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Domain foundation (AggregateRoot, DomainEvent, Result) | High | Stage 0 | Completed |
| Dependency Injection Container | High | Domain foundation | Completed |
| Repository Pattern | High | DI Container | Completed |
| Base Service | High | Repository Pattern | Completed |
| Validation / Pagination / Query / Response frameworks | High | Base Service | Completed |
| Base Controller (CRUD router factory) | High | Above frameworks | Completed |
| Event System | High | DI Container | Completed |
| Background Job Framework | High | DI Container | Completed |
| File Storage Abstraction | High | DI Container | Completed |
| Notification Framework (backend) | Medium | DI Container | Completed |
| Auth + Authorization Frameworks (no login) | High | DI Container | Completed |
| Audit Logging Framework | Medium | Auth framework | Completed |
| Search Foundation | Medium | Query framework | Completed |
| Plugin Architecture | High | DI Container | Completed |
| Workflow Engine | Medium | — | Completed |
| Feature Flags + Config Service extension | Medium | Stage 0 config | Completed |
| Frontend Result + query types | Low | Backend query framework | Completed |
| Full documentation pass | High | All of the above | Completed |

Stage 1 has no business features either — every subsystem is a framework with exactly one minimal
default implementation. See [ProjectStatus.md](ProjectStatus.md) for the full checklist and
[ADR/0006](../ADR/0006-dependency-injection-container.md) /
[ADR/0007](../ADR/0007-audit-logging-without-database-table.md) for the two Stage 1-specific
architectural decisions.

## Stage 2 — Database Architecture & Data Model

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Schema conventions (naming convention, AuditMixin, OptimisticLockMixin) + Identity & Access | High | Stage 1 | Completed |
| Geography (Country→Village hierarchy) | High | Identity & Access | Completed |
| Clients | High | Geography | Completed |
| Properties | High | Clients | Completed |
| Matters & Workflow | High | Clients, Properties | Completed |
| Documents & File Storage | High | Matters | Completed |
| Financial | Medium | Matters, Clients | Completed |
| Activity, Audit & Notifications | Medium | Identity & Access | Completed |
| Scheduling & Tags | Medium | Matters, Clients | Completed |
| OCR, QR & Backups | Medium | Documents | Completed |
| System, Config, AI & Plugins | Low | Identity & Access | Completed |
| Seed lookup data | Medium | All schema sections | Completed |
| `docs/ERD.md` + full documentation pass | High | All of the above | Completed |

Stage 2 built the complete 49-table schema as pure schema — **no repositories, services, or API
routes wired to any table**. See [Database.md](Database.md), [ERD.md](ERD.md), and
[ProjectStatus.md](ProjectStatus.md) for the full checklist, and
[ADR/0008](../ADR/0008-persistence-models-not-domain-entities.md) /
[ADR/0009](../ADR/0009-audit-logs-table-reverses-adr-0007.md) for the two Stage 2-specific
architectural decisions.

## Post-Stage-2 — Standalone Framework Additions

Requested directly by the project owner outside the numbered-stage process — framework-only, same
"no business logic" charter as Stages 0–2. Each is a port + one minimal default implementation,
following the Stage 1 pattern.

| Item | Priority | Dependencies | Status |
|---|---|---|---|
| Command Bus (`CommandBus`, `InMemoryCommandBus`) | — | Stage 2 | Completed |
| Query Bus (`QueryBus`, `InMemoryQueryBus`) | — | Command Bus | Completed |
| Transaction Pipeline (`UnitOfWork`, `InMemoryUnitOfWork`, `TransactionPipelineBehavior`) | — | Command Bus, Query Bus | Completed |
| Caching Abstraction (`Cache`, `InMemoryCache`) | — | Stage 2 | Completed |
| Module Manifest Loader (`ModuleManifest`, `ModuleManifestLoader`) | — | Stage 1 Plugin Architecture | Completed |
| Architecture Health Check (`check_container_health`, `assert_container_healthy`) | — | DI Container | Completed |
| Performance Metrics Service (`MetricsService`, `LoggingMetricsService`) | — | Stage 2 | Completed |
| QA review of the seven additions above + resolution of its two immediately-actionable findings | — | All of the above | Completed |

See [ProjectStatus.md](ProjectStatus.md) for the full checklist, [ADR/0010](../ADR/0010-command-bus.md)
through [ADR/0016](../ADR/0016-performance-metrics-service.md) for the decision records, and
[docs/reviews/Stage_2_5_QA_Review.md](reviews/Stage_2_5_QA_Review.md) plus
[IMPLEMENTATION_QUEUE.md](../IMPLEMENTATION_QUEUE.md)'s "QA Review Findings" section for the review
itself — five findings remain deferred pending a gating dependency, two are accepted ADR-documented
trade-offs, none are outstanding action items.

## Stage 3 — Authentication & Authorization (in progress)

Scoped, architecture-approved (D1–D7, `ADR-0018`/`0019`/`0020`), and under active implementation —
see `IMPLEMENTATION_QUEUE.md`'s "Stage 3" section for the full task list (`T41`–`T80`), acceptance
criteria, and current status; this row is a pointer, not a duplicate. As of 2026-08-08: **Phase 0
(`T41`–`T45`) and Phase 1 (`T46`–`T51`) are both complete.** `T46`/`T47` (password hashing, JWT
encode/decode) merged to `main`; `T48` satisfied by `T44`'s work; `T49` (the `refresh_tokens`
migration) independently QA-approved after one rework round; `T50`/`T51` (`AuthService` — `authenticate`/
`issue_tokens`/`refresh`/`revoke` — plus its 28 tests) QA Decision: Approved with comments, 2026-08-08
(see `docs/ImplementationLog/Stage3/Phase1.md`). `T50`/`T51`'s work was in fact branched, opened as
PR #8, and merged (`204c098`) — the "uncommitted on `main`" note this section previously carried was
itself stale by the time of this correction; see `PROJECT_STATE.json`'s `git` block.

**Phase 2 — `T52` is Done:** `T52` (`JwtAuthenticationProvider`) was authorized by the project owner
in a Project Manager conversation and implemented 2026-08-08 (356/356 full suite passing, 11 new
tests — see `docs/ImplementationLog/Stage3/Phase2.md`), but that authorization wasn't recorded in
the repository before implementation began. QA verified the code as technically correct throughout
and, once a documentation pass closed the authorization-recording and missing-phase-log gaps,
rendered **Approved with comments** on the process gate (2026-08-08) — recorded in `Phase2.md`
itself. The third gap (no feature branch, direct-to-`main` work) closed independently: `git log`
confirms `feature/stage3-t52-jwt-authentication` merged via PR #9 (`baed936`).

**`T53` (`RbacAuthorizationService`) is Done:** 13 new tests, full suite 369/369 passing, ruff/black
clean (`docs/ImplementationLog/Stage3/Phase2.md`'s T53 batch). Also authorized by the project owner
in conversation, and that authorization was **not** recorded in
`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation began — documented only
retrospectively. Two further process/governance gaps, not technical defects, recorded in
`Phase2.md`'s Problems Encountered: the Backend Developer role's own required approval checkpoint
was skipped, and `T53` was implemented directly on `main`. QA rendered **Approved with comments**
weighing all four deviations (2026-08-08). **Closeout:** the git-action deviation has since closed —
`feature/stage3-t53-rbac-authorization` branched, committed (`dd754f5`), opened as PR #10, and
merged (`a103dca`); the authorization-recording and approval-checkpoint deviations remain on record
as governance history, not erased.

**`T54` (`RequirePermission(...)` FastAPI dependency factory) is Done:** closes Stage 2.5's F11
finding. 5 new tests, full suite 374/374 passing, ruff/black clean
(`docs/ImplementationLog/Stage3/Phase2.md`'s T54 batch). Also authorized by the project owner in
conversation, and that authorization was **not** recorded in
`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation began — the third consecutive
batch with this exact gap (`T52`, `T53`, `T54`), preserved as governance history, not erased.
**Unlike `T53`, the Backend Developer role's required approval checkpoint *was* performed and
explicitly approved before implementation began** — recorded so `T54` isn't mistakenly assumed to
carry `T53`'s same deviation. QA's original decision (2026-08-08) was **Rework required, process
grounds only — no code changes needed**; preserved verbatim. **Closeout:** a follow-up QA decision
(2026-08-10) — **Approved with comments** — superseded it once the branch/commit/PR gap closed:
`feature/stage3-t54-require-permission` branched, committed (`dbd6724`), opened as PR #12, and
merged (`6396f6b`); `main`/`origin/main` both verified at `6396f6b`.

**`T55` was authorized conversationally, 2026-08-10.** Original scope: the two
`container.register(...)` replacements in `configure_container()`.

**Correction (2026-08-10, same day, after QA review):** this section previously claimed the
authorization was "recorded ... before implementation began (the first Phase 2 batch to get this
recording right the first time)." **That claim is inaccurate and is corrected here:** nothing about
`T55`'s authorization was ever committed before its implementation existed — the committed `HEAD` at
the time still read `T55` as unauthorized. This is the **fourth** consecutive Stage 3 Phase 2 batch
with this exact governance gap (`T52`, `T53`, `T54`, `T55`), not an exception to the pattern.

Same day, also conversationally, an architectural clarification + expanded authorization followed:
the literal registration approach is technically unworkable — `container.resolve()` is
synchronous/zero-argument, but `JwtAuthenticationProvider`/`RbacAuthorizationService` both need a
request-scoped `AsyncSession`. The project owner additionally authorized request-scoped `Depends()`
construction in `presentation/api/deps.py` (`DBSessionDep` → `SqlAlchemyUserRepository`/
`SqlAlchemyRolePermissionRepository` → the real provider/service), a fresh-per-request RBAC mapping
with no caching policy, and removal of the existing `Anonymous`/`Permissive` registrations (confirmed
unused elsewhere by inspection, so actually removed). `T52`/`T53`/`T54` files, `T56`, `T57`, and
routes remained out of scope, and no scope creep into any of them was found. **`T55` is now Done**
(380/380 full suite, ruff/black clean, request-scoped session usage independently verified — see
`docs/ImplementationLog/Stage3/Phase2.md`'s T55 batch). Original **QA Decision: Rework required —
governance/process grounds only** (not a technical issue) preserved verbatim; **follow-up decision
Approved with comments** is the final disposition, once `feature/stage3-t55-auth-wiring` → PR #15 →
merged `b094436` closed the branch/commit/PR gap — `main`/`origin/main` both verified at `b094436`.
The authorization-recording finding (the fourth consecutive occurrence, `T52`/`T53`/`T54`/`T55`)
remains open governance history, not resolved or erased.

**`T56` (bearer-token extraction in `get_current_user()`) is Done — the first Stage 3 Phase 2 batch
to actually record authorization before implementation.** `presentation/api/deps.py` gained
`get_bearer_token()` (FastAPI `HTTPBearer(auto_error=False)`), replacing the `token=None` placeholder
with the caller's real token. Authorization commit `91e0785` (PR #17, merged `89a3a5e`) predates
implementation commit `fcc68e0` (PR #18, merged `d69c4eb`), confirmed by timestamp order — breaking
the pattern `T52`/`T53`/`T54`/`T55` each demonstrated. 3 new tests, full suite 383/383 passing,
ruff/black clean, boot smoke test passed, Postgres-backed verification completed. **QA Decision:
Approved with comments** — no technical defects; a non-blocking comment recommends an end-to-end
`TestClient`-level bearer-token test once a real protected route exists (`T58`+).

**`T57` (distinguish unauthorized from forbidden) is Done — Stage 3 Phase 2 (`T52`–`T57`) is now
complete in full.** `RequirePermission`'s `_require_permission` now raises `UnauthorizedError`/401
directly for an unauthenticated caller, before `AuthorizationService` is consulted at all — closing
the gap where anonymous and authenticated-but-unpermitted callers both surfaced as `ForbiddenError`/
403. `AuthorizationService`'s port, `RbacAuthorizationService`, and `PermissiveAuthorizationService`
were not modified. Authorization commit `65dd563` predates implementation commit `7c9fc3a` (PR #20,
merged `472f7cb`), confirmed by timestamp order — the second consecutive batch to get this right. 3
new tests + 1 updated, full suite 386/386 passing, ruff/black clean, boot smoke test passed, 127/127
integration tests against live Postgres. **QA Decision: Approved with comments** — no technical
defects; the comment preserves, as a non-blocking historical observation, the deferral of true
`TestClient`-level HTTP verification to `T58`+ (no protected route exists yet — already flagged in
the authorization commit itself, not a new finding).

**Phase 3 (routes) begins with `T58` (`POST /api/v1/auth/login`) — Done, and the first route anywhere
in this project.** Email + password in, access + refresh tokens out, or a structured 401 via the
existing global `AppError` handler. `presentation/api/v1/auth.py` (new) co-locates
`LoginRequest`/`LoginResponse` (no `ApiResponse[T]` wrapper — a token pair isn't a fetchable
resource); `deps.py` gains `get_auth_service()`/`AuthServiceDep`, request-scoped construction
mirroring `T55`'s pattern. This is also the first task to exercise Phase 2's entire dependency chain
(`T52`–`T57`) via a real HTTP request, not just a direct call into `RequirePermission`'s inner
function — the very `TestClient`-level verification `T56`'s and `T57`'s QA comments had deferred.
Authorization commit `58c8e40` (2026-08-13) predates implementation commit `76cd28f` (PR #22, merged
`e67da02`, 2026-08-15), confirmed by commit order — the **third** consecutive batch to get this right.
5 new integration tests against a real mounted app and live Postgres via `httpx.AsyncClient`/
`ASGITransport` (`TestClient`'s separate event-loop thread proved incompatible with the required
`get_db` override). Full suite 391/391 passing (386 prior + 5 new) per PR #22's own report and CI's
6/6 green run, ruff/black clean, boot smoke test passed. **QA Decision: Approved with comments** — no
technical defects; two non-blocking comments preserved verbatim: Starlette's
`HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning is framework-internal, and the test-local
`app.dependency_overrides[get_db]` pattern is safe only under sequential test execution.

**`T59` (`POST /api/v1/auth/refresh`) is Done — the second route in this project, reusing `T58`'s
infrastructure directly.** Refresh token in, rotated access + refresh tokens out, or a structured 401.
`presentation/api/v1/auth.py` was extended, not `deps.py`/`router.py` — `T58`'s `AuthServiceDep` and
router mount are reused unchanged. `RefreshRequest`/`RefreshResponse` are co-located, bare, matching
`login`'s convention; `AuthService.refresh()` (`T50`/`T51`, unmodified) already collapses
invalid/expired/revoked/unknown tokens into one generic `UnauthorizedError`, raised directly on
failure. Authorization commit `163085d` (2026-08-15, 11:06:35 IST) predates implementation commit
`56eb7c2` (11:17:32 IST, ~11 minutes later same day, PR #24, merged `721cec5`), confirmed by commit
order — the **fourth** consecutive batch to get this right. 7 new integration tests against a real
mounted app and live Postgres, reusing `T58`'s `httpx.AsyncClient`/`ASGITransport`/`get_db`-override
test pattern verbatim. Full suite **398/398 passing (391 prior + 7 new) — personally re-run against
live Postgres this session** (unlike `T58`'s closeout, where Docker was unreachable locally),
ruff/black clean, boot smoke test passed; `app.openapi()["paths"]` independently confirmed to contain
only `login`/`refresh`/`health`/`version` — no `T60`+ scope creep. **QA Decision: Approved with
comments** — "no technical defects" per PR #24's own report; unlike `T58`'s PR, PR #24 does not
itemize specific non-blocking comment text anywhere in the repository — recorded here exactly as
given, not invented.

**`T60` (`POST /api/v1/auth/logout`) is Done — the third route in this project, reusing `T58`'s
infrastructure directly, and the fifth consecutive batch to hold the authorization-recording
discipline.** Refresh token in, `204 No Content` out. `presentation/api/v1/auth.py` was extended;
`deps.py`, `router.py`, and `AuthService` itself were **not modified** — an explicit "must not modify"
constraint the authorization stated outright. `LogoutRequest` is co-located; `AuthService.revoke()`
(`T50`/`T51`, unmodified) returns `None`, never a `Result` — an unknown or already-revoked token is a
silent no-op, not a failure — so the route mirrors `presentation/common/crud_router_factory.py`'s
`delete_item`, the only existing "action succeeded, nothing to return" precedent. Authorization commit
`726e8cf` (2026-08-15, 11:57:59 IST) predates implementation commit `5b9bf57` (12:05:34 IST, ~8
minutes later same day, PR #26, merged `941ed42`), confirmed by commit order — the **fifth**
consecutive batch to get this right. 5 new integration tests against a real mounted app and live
Postgres, reusing `T58`/`T59`'s test pattern verbatim, including one that verifies revocation directly
against the stored `RefreshToken` row. Full suite **403/403 passing (398 prior + 5 new) — personally
re-run against live Postgres this session**, ruff/black clean, boot smoke test passed;
`app.openapi()["paths"]` independently confirmed to contain only
`login`/`refresh`/`logout`/`health`/`version` — no `T61`+ scope creep. **QA Decision: Approved** — a
deliberate distinction from `T58`/`T59`'s "with comments," not an oversight: PR #26's body states "no
defects" without the "with comments" qualifier the two prior batches both carried, and itemizes no
comment text anywhere — recorded as the disposition its own source material actually states.

**`T61` (`GET /api/v1/auth/me`) followed — the fourth route in this project, the first needing
`CurrentUserDep` rather than just `AuthServiceDep`, and the sixth consecutive batch to hold the
authorization-recording discipline.** Returns the caller's own `id`/`display_name`/`roles`, wrapped in
`ApiResponse[MeResponse]` (a departure from `login`/`refresh`/`logout`'s bare convention, since `/me`
fetches a resource). `me()` raises `UnauthorizedError` directly when `CurrentUserDep` resolves to an
unauthenticated caller — no permission code required. `deps.py`, `router.py`, `AuthService`,
`CurrentUser`, `JwtAuthenticationProvider`, and `RbacAuthorizationService` all untouched. 7 new
integration tests. Full suite **410/410 passing (403 prior + 7 new)**, ruff/black clean, boot smoke
test passed, `app.openapi()["paths"]` confirmed to contain exactly the six expected routes — no scope
creep. **QA Decision: Approved** (plain, no comments), recorded in
`docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision — T61 batch` section, rendered against the
working tree before it was committed. **`T61` is now Done — merged.** Feature commit `fa57e28`, PR
#30, merged `bdffb5e` (2026-08-15); independently re-verified post-merge this session (`main`/
`origin/main` both at `bdffb5e`, exactly the nine expected files, 6/6 CI checks green, full suite
410/410 re-run against merged `main`).

**`T62` (five user-management routes) followed — the fifth Phase 3 route-group, the first to gate on
`RequirePermission`'s 403 half via a real HTTP request, and the seventh consecutive batch to hold the
authorization-recording discipline.** New `presentation/api/v1/users.py`, gated by one router-level
`RequirePermission("users:manage")`; `crud_router_factory.py`/`deps.py`/`AuthService`/`CurrentUser` all
untouched. Reuses `BaseService[User]`/`SqlAlchemyUserRepository`/`hash_password()` directly.
`deactivate_user()` soft-disables via `service.update()`, never deletes. 28 new integration tests. Full
suite **438/438 passing (410 prior + 28 new)**, ruff/black clean, boot smoke test passed,
`app.openapi()["paths"]` confirmed to contain exactly the nine expected routes. **`T62` is now Done —
merged.** Feature commit `a3e8810`, PR #33, merged `3a4a21c` (2026-08-16). **QA Decision: Approved with
comments** — a named governance finding, not a code defect: `T62` merged before its QA Decision was
recorded in the repository, violating `PROJECT_WORKFLOW.md`'s standard lifecycle; a pre-merge QA pass
had already reached the same disposition on the merits, only its recording was skipped. Recorded as
permanent governance history in `docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision — T62 batch`
section, independently re-verified this session (`main`/`origin/main` both at `3a4a21c`, exactly four
files across the full authorization-to-merge range, 6/6 CI checks green). `T63`–`T67` remain not
started, not authorized.

| Feature | Status |
|---|---|
| Authentication / login | In Progress — see `IMPLEMENTATION_QUEUE.md` |
| Authorization (RBAC) | In Progress — see `IMPLEMENTATION_QUEUE.md` |

## Stage 4+ — Not yet planned

Nothing below has an estimated stage, priority, or dependency graph yet. Listed here only because
the original project charter named them as the eventual scope; **do not implement any of these
without an explicit go-ahead** — see [FutureIdeas.md](FutureIdeas.md) for why Stages 0–2 stayed
deliberately business-logic-free. The database schema each of these would sit on already exists
(Stage 2) — the work here is wiring a repository/service/route to it, not schema design.

| Feature | Status |
|---|---|
| Matter Management | Not Started |
| Client Management | Not Started |
| Property Management | Not Started |
| Document Automation | Not Started |
| OCR | Not Started |
| QR codes | Not Started |
| Search (real implementation) | Not Started |
| Reports | Not Started |
| Payments | Not Started |
| AI features | Not Started |
| Cloud synchronization | Not Started |

This table should be rewritten with real priorities/dependencies/stages once Stage 4 planning
actually starts — with explicit direction from the project owner on what Stage 4 covers.
