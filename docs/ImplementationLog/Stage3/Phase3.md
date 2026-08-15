------------------------------------------------

# Stage 3 – Phase 3

Status: In Progress

Started: 2026-08-15

Completed:

Related Tasks: T58

Related ADRs:

Git Commit: T58 — e67da02 (merge; feature commit 76cd28f; authorization commit 58c8e40).

Pull Request: T58 — #22 (authorization recorded beforehand, commit `58c8e40`, 2026-08-13).

Release:

------------------------------------------------

## Objective

Begin Stage 3 Phase 3 (routes) with `T58` only: `POST /api/v1/auth/login` — email + password in,
access + refresh tokens out, or a structured 401. The first route anywhere in this project, and the
first task to exercise Phase 2's entire dependency chain (`T52`–`T57`: `JwtAuthenticationProvider`,
`RbacAuthorizationService`, `RequirePermission`, request-scoped DI wiring, bearer-token extraction,
the 401/403 split) via a real HTTP request rather than a direct call into `RequirePermission`'s inner
function. `T59`–`T67` (refresh, logout, `/me`, user management, role assignment, cross-route
integration tests, audit wiring) are explicitly out of scope for this batch.

**Authorization / Scope (recorded before implementation, commit `58c8e40`, 2026-08-13 —
implementation commit `76cd28f` followed 2026-08-15, confirmed by commit order, not assumed):** the
project owner explicitly authorized `T58`. Approved scope: the login route itself, its
request/response schemas, per-request `AuthService` wiring (constructed from `DBSessionDep`, the same
pattern already established for `AuthenticationProvider`/`AuthorizationService` in `T55`), and router
registration in `router.py`, plus tests. Tests may create users directly against the test database —
this task does not depend on `T67`'s bootstrap CLI existing. `T59`–`T67` remain explicitly out of
scope and unauthorized. **This is the third consecutive Stage 3 batch (after `T56`, `T57`) where
authorization was actually recorded before implementation began** — the pattern `T52`–`T55` each
failed at is now three-for-three broken.

## Tasks Implemented — T58 batch

- **T58 — `POST /api/v1/auth/login`.** `presentation/api/v1/auth.py` (new): `LoginRequest`
  (`email`/`password`) and `LoginResponse` (`access_token`/`refresh_token`/`token_type`) co-located in
  the router module — no separate schema module exists elsewhere in this codebase to follow instead,
  and no `ApiResponse[T]` envelope (`presentation/common/response.py`), since a token pair isn't a
  fetchable resource. `login()` calls `AuthService.authenticate()` (`T50`); on failure it raises
  `result.error` directly (already an `AppError` instance) — the existing global `AppError` exception
  handler renders the standard `{"error": {...}}` 401 response, no route-level `try`/`except` needed.
  On success, `AuthService.issue_tokens()` (`T50`) produces the access/refresh pair.

## Files Modified — T58 batch

- `backend/src/app/presentation/api/v1/auth.py` — **new**: `LoginRequest`/`LoginResponse`, `router`
  (prefix `/auth`), `login()`.
- `backend/src/app/presentation/api/deps.py` — modified: new `get_auth_service()` (builds `AuthService`
  from `SqlAlchemyUserRepository`/`SqlAlchemyRefreshTokenRepository`/`Settings`, all request-scoped via
  `DBSessionDep`, mirroring `get_authentication_provider()`/`get_authorization_service()`'s shape from
  `T55`) and `AuthServiceDep` type alias; new imports (`AuthService`, `SqlAlchemyRefreshTokenRepository`).
- `backend/src/app/presentation/api/v1/router.py` — modified: `auth` module imported, `auth.router`
  included with `tags=["auth"]`.
- `backend/tests/integration/test_auth_login.py` — **new**: `TestLogin` class, 5 tests (see below),
  plus a local `client` fixture and `_make_user()` helper.
- `IMPLEMENTATION_QUEUE.md` — the `T58` row corrected (authorization commit `58c8e40`, before this
  closeout).
- `docs/ImplementationLog/Stage3/Phase3.md` — this file (new).

No new dependency; no other route; `AuthService`, repository implementations, JWT/security code,
`main.py`, `container.py`, `health.py`/`version.py`, and every `T52`–`T57` file untouched.

## Tests Added — T58 batch

5 in `backend/tests/integration/test_auth_login.py`'s `TestLogin`, run against a real mounted `app`
and real Postgres via `httpx.AsyncClient`/`ASGITransport` (not `fastapi.testclient.TestClient` — see
Design Decisions), with `get_db` overridden to yield the test's own `db_session` fixture:

- `test_valid_credentials_returns_tokens` — a real user, correct password → `200`, non-empty
  `access_token`/`refresh_token`, `token_type == "bearer"`.
- `test_wrong_password_returns_401` — real user, wrong password → `401`.
- `test_unknown_email_returns_401_with_the_same_generic_message` — proves the route doesn't undo
  `AuthService.authenticate()`'s existing "wrong password" vs. "no such account" message collapse: an
  unknown email and a wrong password on a real account return the identical error message.
- `test_inactive_user_returns_401` — a real user with `is_active=False`, correct password → `401`.
- `test_malformed_request_body_returns_422` — a body missing `password` → `422`.

## Test Results — T58 batch

- New tests in isolation: `tests/integration/test_auth_login.py` — **5/5 passed**, per PR #22's own
  test plan.
- Full backend suite: **391 passed** (386 prior + 5 new), 0 failed, 0 skipped — per PR #22's own
  reported test plan and CI's own run. **Not re-run locally against Postgres during this closeout**:
  this session's local environment has no reachable Docker/Postgres daemon (`docker ps` fails to
  connect), so the DB-backed integration suite could not be personally re-executed here; recorded
  transparently rather than silently assumed. Independently corroborated instead via `gh pr view 22`'s
  `statusCheckRollup` — **6/6 CI checks green** (two "Lint, format, and test" runs each for Backend and
  Frontend, two "Build verification" runs), and via PR #22's own description/test-plan, both queried
  directly, not taken on faith from the task instructions alone.
- **Lint:** `uv run ruff check src tests alembic` — clean, re-verified directly (no DB required).
- **Format:** `uv run black --check src tests alembic` — clean (194 files unchanged), re-verified
  directly (no DB required).
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds, re-verified directly (no DB
  required); PR #22 additionally confirms `/api/v1/auth/login` present in `app.openapi()["paths"]`.
- **Scope check:** `git show --stat 76cd28f` confirms exactly four files changed
  (`presentation/api/deps.py`, `presentation/api/v1/auth.py` (new), `presentation/api/v1/router.py`,
  `tests/integration/test_auth_login.py` (new)) — no other route, no `T52`–`T57` file touched.

## Design Decisions — T58 batch

- **No `ApiResponse[T]` wrapper for `LoginResponse`.** That envelope (`presentation/common/response.py`)
  is for resource-returning endpoints; a token pair isn't a fetchable resource, so it's returned bare
  — matching the project's only existing schema precedent, not inventing a new convention.
- **`AuthService` built fresh per request in `deps.py` (`get_auth_service()`), not resolved from the
  DI container** — mirrors `T55`'s established rationale exactly: both of `AuthService`'s repositories
  need *this* request's `AsyncSession`, which `container.resolve()` (synchronous, zero-argument) has
  no mechanism to inject.
- **Failure path raises `result.error` directly, no route-level exception handling.**
  `AuthService.authenticate()` already returns a `Result[User, AppError]`, not a raised exception;
  the failed branch's `error` is already a constructed `AppError` (`UnauthorizedError`), so raising it
  lets the project's existing global `AppError` handler do the response-shaping work, consistent with
  every other error path in the codebase.
- **Tests use `httpx.AsyncClient` + `ASGITransport`, not `fastapi.testclient.TestClient`.**
  `tests/conftest.py`'s `client` and `db_session` fixtures normally use independent `AsyncSession`s; a
  user created via `db_session` (flush-only, rolled back at teardown) would be invisible to a request
  made through the ordinary `client` fixture, since its own `get_db()` opens an unrelated
  session/transaction. Overriding `app.dependency_overrides[get_db]` to yield `db_session` instead
  fixes that, but only works with an async-native HTTP client sharing `db_session`'s own event loop.
  `TestClient` was tried first and confirmed (not assumed) to run the ASGI app on a separate
  thread/event loop via anyio's blocking portal — the override raised `RuntimeError: ... attached to a
  different loop` the moment a request touched the database. `httpx.AsyncClient` against an
  `ASGITransport` wrapping the same `app`, run in the current pytest-asyncio event loop, makes the same
  kind of genuine, real-routing-and-middleware request and the override works. Test-infrastructure
  only — production `get_db()` untouched.

## Problems Encountered — T58 batch

**One test-infrastructure obstacle, resolved during implementation, not deferred:** the `TestClient`
event-loop mismatch described above under Design Decisions — discovered by directly trying the
straightforward approach first, not assumed in advance, then fixed with `httpx.AsyncClient`/
`ASGITransport`. No production code was affected. No lint/format fixes needed; no design question
deferred to QA.

**Governance side — continuing, not restarting, the streak `T56`/`T57` began:** authorization commit
`58c8e40` (2026-08-13) precedes implementation commit `76cd28f` (2026-08-15), confirmed by commit
order, not assumed. This is the **third** consecutive Stage 3 batch to get this right, after
`T52`–`T55`'s four consecutive misses. Those four findings remain on record in `Phase2.md`, unerased
— three clean batches don't retroactively fix them, but do show the discipline holding.

## Deferred Work — T58 batch

- **`T59`–`T67`** — not started, per `T58`'s own scope: `T59` (refresh), `T60` (logout), `T61`
  (`/me`), `T62`/`T63` (user management, role assignment), `T64` (cross-route integration tests), `T65`
  (audit-log wiring for login success/failure and permission-denied events).
- **A feature branch, commit, and PR for `T58`'s changes** — already resolved by the time this section
  is written: `feature/stage3-t58-auth-login` → `76cd28f` → PR #22 → merged `e67da02`. Recorded here
  for consistency with every prior batch's Deferred Work section, not because it was ever actually
  open.

## Future Considerations — T58 batch

- **The `TestClient`-level HTTP-status verification `T56`'s and `T57`'s QA decisions both deferred to
  "once a real protected route exists" is now buildable** — `T58`'s own tests are the first instance
  of it (real HTTP requests, real routing/middleware, real Postgres), though scoped to login only;
  `T64` is where equivalent coverage for every other Phase 3 route is planned.
- Starlette's `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning, surfaced incidentally in this
  batch's test output, is framework-internal (not raised by any code this batch touched) — worth a
  dependency-version note if/when Starlette's replacement constant is adopted project-wide, not a
  `T58`-scoped fix.
- The `app.dependency_overrides[get_db]` test pattern introduced here is reusable by future route
  batches (`T59`–`T63`) needing the same real-app-plus-test-session setup — safe only under the
  current sequential test execution; would need reassessment if parallel test execution is ever
  introduced (see QA Decision below).

## Reviewer Checklist — T58 batch

Self-assessed by the Documentation Manager role against the repository's actual current state, since
no separate Backend Developer self-assessment exists in the repository for this batch (the same
situation `T52`'s, `T55`'s, `T56`'s, and `T57`'s own Reviewer Checklists note).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
☑ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

Notes on the less-obvious ones:

- **ADR updated (if required):** `□` — not required: a route wired to already-approved (`ADR-0018`/
  `0019`/`0020`) infrastructure, no new architectural decision.
- **No scope creep:** `☑` — the code stayed exactly within `T58`'s authorized scope (verified above:
  four files, no other route, no `T52`–`T57` file touched), and — for the third consecutive batch —
  so did the authorization-recording process.
- **Ready for QA:** `☑` — this log states every fact a reviewer would need: the authorized scope, the
  implementation, test evidence, and the authorization-provenance record, all in one place.

## QA Decision — T58 batch

```
QA Decision (T58 batch)

□ Approved
☑ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role (reported for this closeout, transcribed into the repository, not
invented here — this Documentation Manager pass renders no new technical QA decision). **Technical
review: no defects found.** `T58`'s implementation is correct — 391/391 full suite (386 prior + 5
new, per PR #22's own test plan and CI's 6/6 green run, independently queried via `gh pr view 22`;
this session's own environment had no reachable Postgres to personally re-run the DB-backed suite
against, disclosed under Test Results rather than silently assumed), `ruff`/`black` clean and boot
smoke test passed (both re-verified directly this session, no DB required), no `T52`–`T57`/other-route
scope creep (`git show --stat 76cd28f` independently confirms the file list). Authorization provenance
independently confirmed: `58c8e40` (2026-08-13) precedes implementation commit `76cd28f`
(2026-08-15, PR #22) by commit order.

**Comments (why "with comments," not a plain `Approved`) — preserved here verbatim, both non-blocking:**

1. Starlette's `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning, surfaced in test output, is
   framework-internal and not a `T58` defect.
2. The test-local `app.dependency_overrides[get_db]` pattern (used so the async HTTP test client
   shares the test's own DB session) is safe under the current sequential test execution and should
   only be reconsidered if parallel test execution is introduced.

`T59`+ was not started, authorized, or touched by this review. `T58` is now marked `Done` — code, QA
decision, and documentation are all reconciled. **`T58` is Stage 3 Phase 3's first task and the first
route in this project** — see this file's own metadata block (`Status: In Progress` — Phase 3 as a
whole continues with `T59`–`T65`, not yet started or authorized).
