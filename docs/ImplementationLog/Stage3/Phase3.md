------------------------------------------------

# Stage 3 – Phase 3

Status: In Progress

Started: 2026-08-15

Completed:

Related Tasks: T58, T59, T60

Related ADRs:

Git Commit: T58 — e67da02 (merge; feature commit 76cd28f; authorization commit 58c8e40). T59 — 721cec5 (merge; feature commit 56eb7c2; authorization commit 163085d). T60 — 941ed42 (merge; feature commit 5b9bf57; authorization commit 726e8cf).

Pull Request: T58 — #22 (authorization recorded beforehand, commit `58c8e40`, 2026-08-13). T59 — #24 (authorization recorded beforehand, commit `163085d`, 2026-08-15). T60 — #26 (authorization recorded beforehand, commit `726e8cf`, 2026-08-15).

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

## Objective — T59 batch

Continue Stage 3 Phase 3 (routes) with `T59`: `POST /api/v1/auth/refresh` — refresh token in, rotated
access + refresh tokens out, or a structured 401. Reuses `T58`'s established route/schema/DI-wiring
conventions directly rather than inventing new ones.

**Authorization / Scope (recorded before implementation, commit `163085d`, 2026-08-15 11:06:35 IST —
implementation commit `56eb7c2` followed at 11:17:32 IST the same day, ~11 minutes later, confirmed by
commit order, not assumed):** the project owner explicitly authorized `T59`. Approved scope: the
refresh route itself, its request/response schemas, reuse of the existing per-request `AuthServiceDep`
(`T58`) — no new wiring — and tests covering successful refresh/rotation and invalid, expired,
revoked, or unknown refresh tokens. `T60`–`T67` remain explicitly out of scope and unauthorized. **This
is the fourth consecutive Stage 3 batch (after `T56`, `T57`, `T58`) where authorization was actually
recorded before implementation began.**

## Tasks Implemented — T59 batch

- **T59 — `POST /api/v1/auth/refresh`.** `presentation/api/v1/auth.py` extended (not `deps.py` or
  `router.py` — `T58`'s `AuthServiceDep` and router mount are reused unchanged): `RefreshRequest`
  (`refresh_token`) and `RefreshResponse` (`access_token`/`refresh_token`/`token_type`), co-located
  and bare, matching `login`'s convention exactly. `refresh()` calls `AuthService.refresh()`
  (`T50`/`T51`, unmodified), which already collapses an invalid, expired, revoked, or unknown token
  into one identical `UnauthorizedError` — the route raises `result.error` directly on failure, the
  same pattern `login` established, no route-level `try`/`except`.

## Files Modified — T59 batch

- `backend/src/app/presentation/api/v1/auth.py` — modified: `RefreshRequest`/`RefreshResponse`,
  `refresh()` appended after `login()`; module docstring updated to describe both routes.
- `backend/tests/integration/test_auth_refresh.py` — **new**: `TestRefresh` class, 7 tests (see
  below), reusing `test_auth_login.py`'s `client` fixture/`_make_user()` helper pattern verbatim plus
  a local `_login()` helper.
- `IMPLEMENTATION_QUEUE.md` — the `T59` row corrected (authorization commit `163085d`, before this
  closeout).
- `docs/ImplementationLog/Stage3/Phase3.md` — this file (T59 batch appended).

No new dependency; no other route; `deps.py`, `router.py`, `AuthService`, repository implementations,
JWT/security code, `main.py`, `container.py`, and every `T52`–`T58` file otherwise untouched.

## Tests Added — T59 batch

7 in `backend/tests/integration/test_auth_refresh.py`'s `TestRefresh`, against a real mounted `app`
and real Postgres via `httpx.AsyncClient`/`ASGITransport` (reusing `T58`'s `get_db`-override pattern):

- `test_valid_refresh_token_returns_a_new_token_pair` — a real login's refresh token exchanged for a
  new, *different* access/refresh pair.
- `test_rotated_token_cannot_be_reused` — the token consumed by one successful refresh fails a second
  attempt with it.
- `test_invalid_token_returns_401` — a syntactically bogus string.
- `test_expired_token_returns_401` — a syntactically valid, correctly-signed token whose *stored row*
  has already expired (defense in depth, independent of the JWT's own `exp` claim) — mirrors
  `test_auth_service.py`'s `test_jwt_valid_but_db_row_expired_fails`.
- `test_revoked_token_returns_401` — a token already consumed by a prior refresh (rotation revokes it).
- `test_unknown_token_returns_401` — a syntactically valid, correctly-signed token that was never
  actually issued (no matching stored row).
- `test_malformed_request_body_returns_422` — an empty body.

## Test Results — T59 batch

- New tests in isolation: `tests/integration/test_auth_refresh.py` — **7/7 passed**, per PR #24's own
  test plan.
- Full backend suite: **398 passed** (391 prior + 7 new), 0 failed, 0 skipped. **Personally re-run
  this session** — `uv run pytest -q` against live Postgres (`docker ps` confirmed `legal_dms_postgres`
  healthy this session, unlike `T58`'s closeout where it was unreachable) — matching PR #24's own
  reported count exactly, not merely transcribed from it.
- **Lint:** `uv run ruff check src tests alembic` — clean, re-verified directly.
- **Format:** `uv run black --check src tests alembic` — clean (195 files unchanged), re-verified
  directly.
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds, re-verified directly;
  `app.openapi()["paths"]` independently confirmed to contain exactly `/api/v1/auth/login`,
  `/api/v1/auth/refresh`, `/api/v1/health`, `/api/v1/version` — no `T60`+ route present.
- **Scope check:** `git show --stat 56eb7c2` confirms exactly two files changed
  (`presentation/api/v1/auth.py`, `tests/integration/test_auth_refresh.py` (new)) — no `deps.py`,
  `router.py`, or other `T52`–`T58` file touched.

## Design Decisions — T59 batch

- **No new DI wiring.** `T58`'s `AuthServiceDep` already builds a request-scoped `AuthService` with
  both repositories `refresh()` needs (`SqlAlchemyUserRepository`, `SqlAlchemyRefreshTokenRepository`)
  — `refresh()` is just a second consumer of the same dependency, not a reason to add a second one.
- **Single generic failure message reused, not re-derived.** `AuthService.refresh()` already collapses
  invalid/expired/revoked/unknown tokens into one `UnauthorizedError` (same no-enumeration reasoning
  as `login`'s identical wrong-password/unknown-email message) — the route doesn't attempt to
  distinguish those cases in its response, and structurally can't without reopening that design.
- **Test file reuses `T58`'s `client` fixture pattern verbatim** rather than factoring out a shared
  fixture module — no such shared test-fixture convention exists elsewhere in this codebase to extend
  instead, and the duplication is small (a fixture plus a user-creation helper).

## Problems Encountered — T59 batch

**None on the technical side.** First-run tests, no lint/format fixes, no mid-implementation design
question deferred — a smaller, lower-risk batch than `T58`, reusing rather than inventing.

**Governance side — continuing, not restarting, the streak `T56`/`T57`/`T58` began:** authorization
commit `163085d` (11:06:35 IST) precedes implementation commit `56eb7c2` (11:17:32 IST) the same day,
confirmed by commit order and timestamp, not assumed. This is the **fourth** consecutive Stage 3 batch
to get this right, after `T52`–`T55`'s four consecutive misses. Those four findings remain on record
in `Phase2.md`, unerased.

**Documentation-verification side — one gap worth naming plainly:** PR #24's own body states `QA
independently reviewed: Approved with comments, no technical defects` but, unlike `T58`'s PR #22
(which itemized two specific non-blocking comments), does not itemize what the comment(s) actually
are anywhere in the repository — checked the PR body, both commit messages, and `gh api
.../pulls/24/reviews` (empty). This closeout records the QA Decision and the phrase "no technical
defects" exactly as given, and does not invent comment text to fill the gap.

## Deferred Work — T59 batch

- **`T60`–`T67`** — not started, per `T59`'s own scope: `T60` (logout), `T61` (`/me`), `T62`/`T63`
  (user management, role assignment), `T64` (cross-route integration tests), `T65` (audit-log wiring).
- **A feature branch, commit, and PR for `T59`'s changes** — already resolved by the time this section
  is written: `feature/stage3-t59-refresh-token` → `56eb7c2` → PR #24 → merged `721cec5`. Recorded
  here for consistency with every prior batch's Deferred Work section, not because it was ever
  actually open.

## Future Considerations — T59 batch

- **The QA-comment-text gap named above** — if a future session or the project owner can supply the
  actual non-blocking comment text QA rendered for `T59` (beyond "no technical defects"), it should be
  added here as a correction, not silently assumed to match `T58`'s comments just because the same
  Starlette deprecation warning was independently observed firing in this session's own test run for
  `test_malformed_request_body_returns_422` (both `login`'s and `refresh`'s copies) — that observation
  is this session's own, not a transcription of a QA finding.
- `T60` (logout) is the next natural consumer of the refresh-token infrastructure this batch didn't
  touch — `AuthService.revoke()` (`T50`/`T51`) already exists and is unused by any route yet.

## Reviewer Checklist — T59 batch

Self-assessed by the Documentation Manager role against the repository's actual current state, since
no separate Backend Developer self-assessment exists in the repository for this batch (the same
situation every prior Phase 2/3 batch's own Reviewer Checklist notes).

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

- **ADR updated (if required):** `□` — not required: a second route reusing already-approved (`T50`/
  `T51`/`T58`) infrastructure, no new architectural decision.
- **No scope creep:** `☑` — the code stayed exactly within `T59`'s authorized scope (verified above:
  two files, no `deps.py`/`router.py`/other-route touch), and — for the fourth consecutive batch — so
  did the authorization-recording process.
- **Ready for QA:** `☑` — this log states every fact a reviewer would need: the authorized scope, the
  implementation, test evidence, and the authorization-provenance record, all in one place.

## QA Decision — T59 batch

```
QA Decision (T59 batch)

□ Approved
☑ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role (reported for this closeout, transcribed into the repository, not
invented here — this Documentation Manager pass renders no new technical QA decision). **Technical
review: no defects found**, per PR #24's own report. `T59`'s implementation is correct — 398/398 full
suite (391 prior + 7 new, personally re-run against live Postgres this session), `ruff`/`black` clean,
boot smoke test passed (`/api/v1/auth/refresh` confirmed in `app.openapi()["paths"]`), no
`T52`–`T58`/other-route scope creep (`git show --stat 56eb7c2` independently confirms the file list).
Authorization provenance independently confirmed: `163085d` (2026-08-15, 11:06:35 IST) precedes
implementation commit `56eb7c2` (2026-08-15, 11:17:32 IST, PR #24) by commit order and timestamp.

**Comment (why "with comments," not a plain `Approved`):** PR #24's body states "no technical defects"
but, unlike `T58`'s PR, does not itemize the non-blocking comment text anywhere in the repository —
preserved here exactly as given, not invented. Recorded transparently as a documentation-provenance
gap rather than silently filled in.

`T60`+ was not started, authorized, or touched by this review. `T59` is now marked `Done` — code, QA
decision, and documentation are all reconciled. See this file's own metadata block (`Status: In
Progress` — Phase 3 continues with `T60`–`T65`, not yet started or authorized).

## Objective — T60 batch

Continue Stage 3 Phase 3 (routes) with `T60`: `POST /api/v1/auth/logout` — refresh token in, `204 No
Content` out. Reuses `T58`'s established route/schema/DI-wiring conventions directly, as `T59` did.

**Authorization / Scope (recorded before implementation, commit `726e8cf`, 2026-08-15 11:57:59 IST —
implementation commit `5b9bf57` followed at 12:05:34 IST the same day, ~8 minutes later, confirmed by
commit order, not assumed):** the project owner explicitly authorized `T60`. Approved scope: the
logout route in the existing `presentation/api/v1/auth.py`, using the existing `AuthServiceDep` and
`AuthService.revoke()`, with appropriate request/response handling and tests explicitly verifying
idempotent behavior — a valid refresh token is revoked, an already-revoked token succeeds without
error, and an unknown token also succeeds without error. **Must not modify** `AuthService`,
`deps.py`, `router.py`, or the existing login/refresh behavior — an explicit constraint, not merely an
expected reuse pattern like `T59`'s. `T61`–`T67` remain explicitly out of scope and unauthorized.
**This is the fifth consecutive Stage 3 batch (after `T56`, `T57`, `T58`, `T59`) where authorization
was actually recorded before implementation began.**

## Tasks Implemented — T60 batch

- **T60 — `POST /api/v1/auth/logout`.** `presentation/api/v1/auth.py` extended (not `deps.py`,
  `router.py`, or `AuthService` — the authorization's explicit "must not modify" constraint honored
  exactly): `LogoutRequest` (`refresh_token`), co-located. `logout()` calls `AuthService.revoke()`
  (`T50`/`T51`, unmodified) — which returns `None`, never a `Result`, since an unknown or
  already-revoked token is a silent no-op, not a failure — so the route has no error branch, unlike
  `login`/`refresh`. Returns `204 No Content` with no body, mirroring
  `presentation/common/crud_router_factory.py`'s `delete_item`, the only existing precedent in this
  codebase for "the action succeeded, there's nothing to return."

## Files Modified — T60 batch

- `backend/src/app/presentation/api/v1/auth.py` — modified: `LogoutRequest`, `logout()` appended
  after `refresh()`; module docstring updated to describe all three routes.
- `backend/tests/integration/test_auth_logout.py` — **new**: `TestLogout` class, 5 tests (see below),
  reusing `test_auth_login.py`/`test_auth_refresh.py`'s `client` fixture/`_make_user()`/`_login()`
  helper pattern verbatim, plus a local `_get_stored_token()` helper.
- `IMPLEMENTATION_QUEUE.md` — the `T60` row corrected (authorization commit `726e8cf`, before this
  closeout).
- `docs/ImplementationLog/Stage3/Phase3.md` — this file (T60 batch appended).

No new dependency; no other route; `deps.py`, `router.py`, `AuthService`, repository implementations,
JWT/security code, `main.py`, `container.py`, and every `T52`–`T59` file otherwise untouched — verified
against the authorization's explicit constraint, not just the usual "no scope creep" check.

## Tests Added — T60 batch

5 in `backend/tests/integration/test_auth_logout.py`'s `TestLogout`, against a real mounted `app` and
real Postgres via `httpx.AsyncClient`/`ASGITransport` (reusing `T58`/`T59`'s `get_db`-override
pattern):

- `test_valid_refresh_token_is_revoked` — a real login's refresh token, logged out → `204`, empty
  body, and the stored `RefreshToken` row's `revoked_at` is independently verified non-`null`.
- `test_already_revoked_token_succeeds` — logging out twice with the same token: both calls return
  `204`, proving the idempotent no-op behavior the authorization explicitly required.
- `test_unknown_token_succeeds` — a syntactically valid, correctly-signed token that was never
  actually issued (no matching stored row) → `204`.
- `test_malformed_token_string_succeeds` — a syntactically bogus string → `204` (no JWT-decode error
  surfaces as a failure, since `revoke()` never raises).
- `test_malformed_request_body_returns_422` — an empty body.

## Test Results — T60 batch

- New tests in isolation: `tests/integration/test_auth_logout.py` — **5/5 passed**, per PR #26's own
  test plan.
- Full backend suite: **403 passed** (398 prior + 5 new), 0 failed, 0 skipped. **Personally re-run
  this session** — `uv run pytest -q` against live Postgres (`docker ps` confirmed
  `legal_dms_postgres` healthy) — matching PR #26's own reported count exactly.
- **Lint:** `uv run ruff check src tests alembic` — clean, re-verified directly.
- **Format:** `uv run black --check src tests alembic` — clean (196 files unchanged), re-verified
  directly.
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds, re-verified directly;
  `app.openapi()["paths"]` independently confirmed to contain exactly `/api/v1/auth/login`,
  `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/health`, `/api/v1/version` — no `T61`+
  route present.
- **Scope check:** `git show --stat 5b9bf57` confirms exactly two files changed
  (`presentation/api/v1/auth.py`, `tests/integration/test_auth_logout.py` (new)) — no `deps.py`,
  `router.py`, `AuthService`, or other `T52`–`T59` file touched, honoring the authorization's explicit
  "must not modify" constraint, not just the general scope boundary.

## Design Decisions — T60 batch

- **`204 No Content`, not a token pair or a wrapped response.** `AuthService.revoke()` has nothing to
  return — mirrors `delete_item`'s existing "action succeeded, nothing to return" precedent rather
  than inventing a new response shape for the one route in this codebase with genuinely nothing to
  report back.
- **No error branch, by design, not by omission.** `AuthService.revoke()`'s `None`-returning,
  never-raising contract (established at `T50`/`T51`) makes logout structurally different from
  `login`/`refresh` — there is no `Result.error` to raise, so `logout()` doesn't have (and shouldn't
  invent) a failure path. `test_malformed_token_string_succeeds` and `test_unknown_token_succeeds`
  exist specifically to prove this holds through the real route, not just at the service layer.
- **Test file reuses `T58`/`T59`'s fixture pattern verbatim**, plus one new helper
  (`_get_stored_token()`) to assert directly against the database row rather than trusting the HTTP
  response alone — necessary here since a `204` alone can't distinguish "actually revoked" from "silently
  ignored," the same ambiguity the idempotent-no-op design intentionally creates.

## Problems Encountered — T60 batch

**None on the technical side.** First-run tests, no lint/format fixes, no mid-implementation design
question deferred — the smallest, lowest-risk Phase 3 batch so far, reusing rather than inventing, and
touching fewer files than either `T58` or `T59`.

**Governance side — continuing, not restarting, the streak `T56`/`T57`/`T58`/`T59` began:**
authorization commit `726e8cf` (11:57:59 IST) precedes implementation commit `5b9bf57` (12:05:34 IST)
the same day, confirmed by commit order and timestamp, not assumed. This is the **fifth** consecutive
Stage 3 batch to get this right, after `T52`–`T55`'s four consecutive misses. Those four findings
remain on record in `Phase2.md`, unerased.

**Documentation-verification side — a different gap than `T59`'s, named plainly rather than
conflated with it:** PR #26's own body states `QA independently reviewed: no defects` — this phrasing
**omits** the "with comments" qualifier `T58`'s and `T59`'s PR bodies both carried, and (like `T59`)
itemizes no specific comment text anywhere (checked the PR body, both commit messages, and `gh api
.../pulls/26/reviews`, empty). Read literally, "no defects" without "with comments" is most
consistent with a plain `Approved` disposition, not `Approved with comments` — this closeout records
`Approved`, not inheriting `T58`/`T59`'s "with comments" label by pattern-matching on the two prior
batches rather than on this batch's own actual wording.

## Deferred Work — T60 batch

- **`T61`–`T67`** — not started, per `T60`'s own scope: `T61` (`/me`), `T62`/`T63` (user management,
  role assignment), `T64` (cross-route integration tests), `T65` (audit-log wiring).
- **A feature branch, commit, and PR for `T60`'s changes** — already resolved by the time this section
  is written: `feature/stage3-t60-logout` → `5b9bf57` → PR #26 → merged `941ed42`. Recorded here for
  consistency with every prior batch's Deferred Work section, not because it was ever actually open.

## Future Considerations — T60 batch

- **The QA-decision-wording distinction named above** — if a future session or the project owner can
  confirm whether `T60`'s QA review genuinely differed in outcome from `T58`/`T59` (plain `Approved`
  vs. `Approved with comments`) or whether "no defects" was simply shorthand for the same disposition,
  correct this record accordingly rather than leaving two closeouts silently disagreeing on what the
  wording difference means.
- `T61` (`GET /api/v1/auth/me`) is the next natural route — unlike `T58`/`T59`/`T60`, it will need
  `CurrentUserDep`/`RequirePermission` (`T52`–`T57`), not just `AuthServiceDep`, since it requires an
  authenticated caller rather than accepting arbitrary credentials/tokens in the body. This is also
  the first point where a `T56`/`T57`-style 401 (missing/invalid bearer token) becomes reachable via a
  real HTTP request, not just `T58`'s login-failure 401 or `T59`'s refresh-failure 401.

## Reviewer Checklist — T60 batch

Self-assessed by the Documentation Manager role against the repository's actual current state, since
no separate Backend Developer self-assessment exists in the repository for this batch (the same
situation every prior Phase 2/3 batch's own Reviewer Checklist notes).

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

- **ADR updated (if required):** `□` — not required: a third route reusing already-approved (`T50`/
  `T51`/`T58`) infrastructure, no new architectural decision.
- **No scope creep:** `☑` — the code stayed exactly within `T60`'s authorized scope, including the
  explicit "must not modify `AuthService`/`deps.py`/`router.py`" constraint (verified above: two
  files, no other touch), and — for the fifth consecutive batch — so did the authorization-recording
  process.
- **Ready for QA:** `☑` — this log states every fact a reviewer would need: the authorized scope, the
  implementation, test evidence, and the authorization-provenance record, all in one place.

## QA Decision — T60 batch

```
QA Decision (T60 batch)

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role (reported for this closeout, transcribed into the repository, not
invented here — this Documentation Manager pass renders no new technical QA decision). **Technical
review: no defects found**, per PR #26's own report. `T60`'s implementation is correct — 403/403 full
suite (398 prior + 5 new, personally re-run against live Postgres this session), `ruff`/`black` clean,
boot smoke test passed (`/api/v1/auth/logout` confirmed in `app.openapi()["paths"]`), no
`T52`–`T59`/other-route scope creep (`git show --stat 5b9bf57` independently confirms the file list),
and the authorization's explicit "must not modify `AuthService`/`deps.py`/`router.py`" constraint was
honored exactly. Authorization provenance independently confirmed: `726e8cf` (2026-08-15, 11:57:59
IST) precedes implementation commit `5b9bf57` (2026-08-15, 12:05:34 IST, PR #26) by commit order and
timestamp.

**Why `Approved`, not `Approved with comments` (a deliberate distinction from `T58`/`T59`, not an
oversight):** PR #26's body states "no defects" without the "with comments" qualifier `T58`'s and
`T59`'s PR bodies both carried, and — like `T59` — itemizes no comment text anywhere in the
repository. Rather than defaulting to `Approved with comments` by pattern-matching on the two
immediately preceding batches, this closeout records the disposition its own source material actually
states: a plain `Approved`.

`T61`+ was not started, authorized, or touched by this review. `T60` is now marked `Done` — code, QA
decision, and documentation are all reconciled. See this file's own metadata block (`Status: In
Progress` — Phase 3 continues with `T61`–`T65`, not yet started or authorized).
