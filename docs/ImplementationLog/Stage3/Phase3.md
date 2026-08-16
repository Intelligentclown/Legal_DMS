------------------------------------------------

# Stage 3 – Phase 3

Status: In Progress

Started: 2026-08-15

Completed:

Related Tasks: T58, T59, T60, T61, T62, T63

Related ADRs:

Git Commit: T58 — e67da02 (merge; feature commit 76cd28f; authorization commit 58c8e40). T59 — 721cec5 (merge; feature commit 56eb7c2; authorization commit 163085d). T60 — 941ed42 (merge; feature commit 5b9bf57; authorization commit 726e8cf). T61 — bdffb5e (merge; feature commit fa57e28; authorization commit 520026f). T62 — 3a4a21c (merge; feature commit a3e8810; authorization commit e10bdc8). T63 — ef419c3 (merge; feature commit 3cea676; QA-approval commit 6a8608f; authorization commit 93cda84).

Pull Request: T58 — #22 (authorization recorded beforehand, commit `58c8e40`, 2026-08-13). T59 — #24 (authorization recorded beforehand, commit `163085d`, 2026-08-15). T60 — #26 (authorization recorded beforehand, commit `726e8cf`, 2026-08-15). T61 — #30 (authorization recorded beforehand, commit `520026f`, 2026-08-15; merged `bdffb5e`, 2026-08-15). T62 — #32 (authorization, commit `e10bdc8`, 2026-08-16, merged `ea80b74`); implementation #33 (merged `3a4a21c`, 2026-08-16) — merged before its QA Decision was recorded in this file; see the QA Decision — T62 batch section's named governance finding. T63 — #35 (authorization, commit `93cda84`, 2026-08-16, merged `97ab953`); implementation #36 (merged `ef419c3`, 2026-08-16) — **QA Decision (commit `6a8608f`) was committed and pushed *before* PR #36 merged**, the deliberate correction of `T62`'s own governance finding; see the QA Decision — T63 batch section and the Post-Merge Verification note appended after it.

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

## Objective — T61 batch

Continue Stage 3 Phase 3 (routes) with `T61`: `GET /api/v1/auth/me` — return the current
authenticated caller's own profile (`id`/`display_name`/`roles`), or a `401` if unauthenticated.
Unlike `T58`–`T60`, this route needs `CurrentUserDep` (`T52`–`T57`), not `AuthServiceDep` — the first
point where a `T56`/`T57`-style 401 (missing/invalid/expired/malformed bearer token, or an inactive/
unknown user) becomes reachable via a real HTTP request rather than only `RequirePermission`'s
unit-level coverage.

**Authorization / Scope (recorded before implementation, commit `520026f`, 2026-08-15 — merged as
`cca1077` via PR #29, confirmed by `git rev-parse HEAD origin/main` both resolving to `cca1077` before
this batch's implementation began, not assumed):** the project owner explicitly authorized `T61`.
Approved scope, recorded in full in `docs/HANDOFF/T61_HANDOFF.md`: the `/me` route itself, reusing the
existing `CurrentUserDep` unchanged (no `RequirePermission`/permission code — any authenticated user
may view their own profile), returning exactly `id`/`display_name`/`roles` taken from the resolved
`CurrentUser` with no transformation, wrapped in `ApiResponse[MeResponse]` (a deliberate departure
from `login`/`refresh`/`logout`'s bare-response convention, since `/me` fetches a resource and those
three don't), plus tests. `T62`–`T67` remain explicitly out of scope and unauthorized. **This is the
sixth consecutive Stage 3 batch (after `T56`–`T60`) where authorization was actually recorded before
implementation began.**

## Tasks Implemented — T61 batch

- **T61 — `GET /api/v1/auth/me`.** `presentation/api/v1/auth.py` extended (not `deps.py`, `router.py`,
  `AuthService`, `CurrentUser`, or `JwtAuthenticationProvider` — all reused exactly as they exist
  today, per the handoff's explicit forbidden-files list): `MeResponse` (`id`/`display_name`/`roles`),
  co-located, and a `me()` route handler taking `CurrentUserDep` directly. `CurrentUserDep` never
  raises — an unauthenticated caller (no token, or a malformed/expired/tampered token, or an unknown/
  inactive user) resolves to the anonymous `CurrentUser` default (`is_authenticated=False`, per `T52`)
  — so `me()` raises `UnauthorizedError` itself when `is_authenticated` is `False`, the same check
  `RequirePermission` (`T54`) already makes, rather than requiring a specific permission code. On
  success, the response is `ApiResponse(data=MeResponse(...))`, with `roles` sorted for deterministic
  output (`CurrentUser.roles` is an unordered `frozenset`).

## Files Modified — T61 batch

- `backend/src/app/presentation/api/v1/auth.py` — modified: `MeResponse`, `me()` appended after
  `logout()`; module docstring updated to describe all four routes and the `ApiResponse` departure.
- `backend/tests/integration/test_auth_me.py` — **new**: `TestMe` class, 7 tests (see below), reusing
  `test_auth_login.py`/`test_auth_refresh.py`/`test_auth_logout.py`'s `client` fixture/`_make_user()`/
  `_login()` helper pattern verbatim (`_login()` adapted to return the access token, not the refresh
  token), plus a local `_assign_role()` helper.
- `docs/ImplementationLog/Stage3/Phase3.md` — this file (T61 batch appended; header's `Related Tasks`/
  `Git Commit`/`Pull Request` lines updated to record `T61`'s authorization commit and note that
  implementation has not yet been committed/pushed/PR'd, per this batch's stop condition).

No new dependency; no other route; `deps.py`, `router.py`, `AuthService`, `CurrentUser`,
`JwtAuthenticationProvider`, `RbacAuthorizationService`, repository implementations, `main.py`,
`container.py`, any `alembic/` migration, any frontend file, and every `T52`–`T60` file otherwise
untouched — verified against the handoff's explicit forbidden-files list, not just the usual
"no scope creep" check. No governance file (`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`,
`PROJECT_CHECKPOINT.md`) touched, per the same list and per this role's own instructions.

## Tests Added — T61 batch

7 in `backend/tests/integration/test_auth_me.py`'s `TestMe`, against a real mounted `app` and real
Postgres via `httpx.AsyncClient`/`ASGITransport` (reusing `T58`–`T60`'s `get_db`-override pattern):

- `test_valid_token_returns_profile_and_roles` — a real login's access token → `200`, `data.id`/
  `data.display_name`/`data.roles` match the specific user (one assigned role).
- `test_missing_token_returns_401` — no `Authorization` header at all.
- `test_malformed_token_returns_401` — a syntactically bogus bearer token string.
- `test_expired_token_returns_401` — a syntactically valid, correctly-signed access token whose own
  `exp` claim has already passed (`settings.model_copy(update={"access_token_ttl_minutes": -1})`,
  preserving the running app's real `jwt_secret_key` rather than constructing an unrelated `Settings`
  instance, so the signature still verifies and only the expiry fails).
- `test_inactive_user_token_returns_401` — a real login's access token, then the user is deactivated
  (`is_active = False`, flushed on the same `db_session` the request's `get_db` override yields) before
  the `/me` call — proves `JwtAuthenticationProvider`'s live re-check, not just the token's own claims.
- `test_unknown_user_token_returns_401` — a syntactically valid, correctly-signed access token for a
  `sub` with no matching user row.
- `test_multiple_roles_all_returned` — a user with two assigned roles gets both back in `roles`, sorted.

No "revoked token" case, per the handoff's explicit instruction — access tokens aren't DB-revocable by
design (`D1`); that concern belongs to `/refresh`, not `/me`.

## Test Results — T61 batch

- New tests in isolation: `tests/integration/test_auth_me.py` — **7/7 passed**, personally run this
  session (`uv run pytest tests/integration/test_auth_me.py -v` against live Postgres —
  `legal_dms_postgres` confirmed healthy via `docker ps`). One first-run failure surfaced and fixed
  before this count: the first version of `test_valid_token_returns_profile_and_roles`/
  `test_multiple_roles_all_returned` assigned the literal role names `"Advocate"`/`"Administrator"`,
  which collided with this project's already-seeded roles of the same name (`uq_roles_name` unique
  violation) — fixed by switching to unique `f"Role-{uuid4()}"`-style names, the same pattern
  `test_auth_dependency_wiring.py` already uses for the identical reason.
- Full backend suite: **410 passed** (403 prior + 7 new), 0 failed, 0 skipped. Personally re-run this
  session — `uv run pytest -q` against the same live Postgres instance.
- **Lint:** `uv run ruff check src tests alembic` — clean, re-verified directly.
- **Format:** `uv run black --check src tests alembic` — clean (197 files unchanged; one reformat
  applied to `test_auth_me.py` itself before this final check, both re-verified directly).
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds, re-verified directly;
  `app.openapi()["paths"]` independently confirmed to contain exactly `/api/v1/auth/login`,
  `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/health`, `/api/v1/version`
  — nothing else.
- **Scope check:** `git status --short` / `git diff --stat` confirm exactly one file modified
  (`presentation/api/v1/auth.py`) and one new file (`tests/integration/test_auth_me.py`) — no
  `deps.py`, `router.py`, `AuthService`, `CurrentUser`, migration, frontend, or governance file
  touched. (No commit exists yet for this batch — see this file's header — so `git show --stat` against
  a specific commit isn't yet available; the working-tree diff serves the same verification purpose.)

## Design Decisions — T61 batch

- **`ApiResponse[MeResponse]`, not a bare schema.** A deliberate departure from `login`/`refresh`/
  `logout`'s convention, per the handoff's explicit instruction: those three don't return a fetchable
  resource (a token pair, or nothing), while `/me` returns the caller's own resource — exactly the case
  `presentation/common/response.py`'s own docstring says `ApiResponse` exists for, matching
  `crud_router_factory.py`'s `GET /{item_id}` → `ApiResponse[ReadSchema]` precedent instead.
- **`CurrentUserDep`, not `AuthServiceDep`, and no `RequirePermission`.** Resolving "who is the caller"
  from the bearer token is exactly what `CurrentUserDep` (`T52`–`T57`) already does; `/me` needs no
  service-layer call beyond that. No permission code represents "view own profile" — inventing one was
  explicitly out of scope — so the route checks `user.is_authenticated` directly and raises
  `UnauthorizedError` itself, the same check `RequirePermission`'s inner function already makes,
  without requiring a specific permission.
- **Roles returned sorted.** `CurrentUser.roles` is a `frozenset[str]` (unordered by construction);
  sorting before emitting `MeResponse.roles` gives deterministic API output without changing
  `CurrentUser`'s own type — no change to `application/interfaces/auth.py`, per the forbidden-files
  list.
- **No route-level `try`/`except`.** `UnauthorizedError` is raised directly and handled by the
  project's existing global `AppError` exception handler, the same pattern every other Phase 3 route
  already follows — no new error-handling code introduced.

## Problems Encountered — T61 batch

**One test-data collision, resolved during implementation, not deferred:** the first draft of two
tests used the seeded role names `"Advocate"`/`"Administrator"` directly, which collided with this
project's actual seed data (`uq_roles_name` unique constraint) — discovered by running the tests, not
assumed in advance, then fixed by switching to unique generated role names
(`test_auth_dependency_wiring.py`'s established pattern for the same reason). No production code was
affected; no lint/format fixes needed.

**Governance side — continuing, not restarting, the streak `T56`–`T60` began:** authorization commit
`520026f` was independently re-verified this session (`git rev-parse HEAD origin/main`, both
`cca1077`, confirmed to already carry `520026f` in its ancestry via PR #29's merge) as preceding any
implementation — no implementation, test, or migration file for `T61` existed anywhere in the tree
before this batch's own changes. This is the **sixth** consecutive Stage 3 batch to get this right,
after `T52`–`T55`'s four consecutive misses. Those four findings remain on record in `Phase2.md`,
unerased.

## Deferred Work — T61 batch

- **`T62`–`T67`** — not started, per `T61`'s own scope: `T62`/`T63` (user management, role
  assignment), `T64` (cross-route integration tests beyond `/me`'s own), `T65` (audit-log wiring), `T66`
  (`role_permissions` matrix sign-off), `T67` (bootstrap CLI).
- **A feature branch, commit, and PR for `T61`'s changes** — deliberately not created as part of this
  batch, per this role's own stop conditions (Backend Developer implements and stops; commit/push/PR/
  merge are separate, explicitly out of scope here). Recorded as genuinely open, unlike the equivalent
  line in `T58`/`T59`/`T60`'s own Deferred Work sections, which were already resolved by the time those
  entries were written.
- **QA review** — not performed by this batch; the QA Reviewer role must independently re-verify per
  `T61_HANDOFF.md` §9 before any documentation sync or merge proceeds.

## Reviewer Checklist — T61 batch

Self-assessed by the Backend Developer role against this session's own verified work (unlike `T58`–
`T60`'s checklists, each self-assessed retrospectively by the Documentation Manager role in the absence
of a contemporaneous Backend Developer record).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

Notes on the less-obvious ones:

- **ADR updated (if required):** `□` — not required: a fourth route reusing already-approved
  (`T52`–`T57`) infrastructure, no new architectural decision.
- **PROJECT_STATE updated (if required):** `□` — deliberately not updated by this batch: per the
  handoff's explicit forbidden-files list and this role's own instructions, `IMPLEMENTATION_QUEUE.md`/
  `PROJECT_STATE.json`/`PROJECT_CHECKPOINT.md` are Project Manager/Documentation Manager owned and are
  synchronized only after a QA Decision exists — not a gap, a boundary honored.
- **No scope creep:** `☑` — the code stayed exactly within `T61`'s authorized scope (verified above:
  one file modified, one new test file, every forbidden file confirmed untouched), and — for the sixth
  consecutive batch — so did the authorization-recording process.
- **Ready for QA:** `☑` in the sense that implementation, tests, and this log entry are complete and
  the full suite is green; **T61 is explicitly not being claimed as done here** — no QA Decision exists
  yet, and this batch does not render one (that is the QA Reviewer role's own next step, per
  `T61_HANDOFF.md` §9).

`T61`'s QA Decision, `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/`PROJECT_CHECKPOINT.md`
synchronization, commit, branch, PR, and merge are all **not yet done** and intentionally outside this
batch's scope — see Deferred Work above. See this file's own metadata block (`Status: In Progress` —
Phase 3 continues with `T62`–`T65`, not yet started or authorized).

## QA Decision — T61 batch

```
QA Decision (T61 batch)

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, independently, against the repository state as it actually stood
(uncommitted, on `main`, per this batch's own Deferred Work note above) — not transcribed from the
Backend Developer's Reviewer Checklist. Verified directly, not assumed:

- **Scope:** `git diff --stat` confirmed exactly two tracked files changed
  (`presentation/api/v1/auth.py`, `docs/ImplementationLog/Stage3/Phase3.md`) plus one new file
  (`tests/integration/test_auth_me.py`). `git diff` against every file `T61_HANDOFF.md` §4 forbids
  (`deps.py`, `application/auth_service.py`, `router.py`, `application/interfaces/auth.py`
  (`CurrentUser`), `jwt_authentication_provider.py`, `rbac_authorization_service.py`,
  `permissive_authorization_service.py`) returned zero lines — none were touched. No `alembic/`,
  frontend, or governance file (`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/
  `PROJECT_CHECKPOINT.md`) was touched.
- **Tests:** `uv run pytest tests/integration/test_auth_me.py -v` — **7/7 passed**, re-run personally
  against live Postgres (`legal_dms_postgres` container, confirmed healthy via `docker ps`). Full
  suite: `uv run pytest -q` — **410 passed**, 0 failed, 0 skipped. Tests are non-vacuous: each 401 case
  (missing/malformed/expired/inactive-user/unknown-user) exercises a distinct branch of
  `JwtAuthenticationProvider`, and `test_multiple_roles_all_returned` asserts alphabetically-ordered
  output, not merely presence.
- **Lint/format:** `uv run ruff check src tests alembic` — clean. `uv run black --check src tests
  alembic` — clean (197 files unchanged).
- **Boot smoke test:** `python -c "from app.main import app"` succeeded; `app.openapi()["paths"]`
  independently confirmed to contain exactly `/api/v1/auth/login`, `/api/v1/auth/refresh`,
  `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/health`, `/api/v1/version` — no scope creep.
- **Behavior:** `me()` uses `CurrentUserDep` (not `AuthServiceDep`), raises `UnauthorizedError` (401,
  via the existing global `AppError` handler) when `is_authenticated` is `False`, requires no
  `RequirePermission(...)`/permission code, returns `ApiResponse(data=MeResponse(...))` with `meta`
  defaulting to `null`, and sorts `roles` before emission (`CurrentUser.roles` is an unordered
  `frozenset`, itself unmodified) — satisfying the deterministic-sorted-roles requirement without
  changing the port.
- **Documentation:** this file's T61 batch section (Objective through Reviewer Checklist) was checked
  against the actual diff and test run and found accurate — no discrepancy between the log's claims and
  the repository.

**No technical defects found.** No implementation changes required. This is a plain `Approved`, not
`Approved with comments` — nothing surfaced in this review that rises to a recorded comment; the
absence of a branch/commit/PR at review time is expected process for this batch (per this batch's own
Deferred Work note and this review's own instructions), not a defect.

This entry itself is the correction of a prior gap: an earlier QA review of `T61` was performed and
independently reached the same `Approved` disposition and the same verification results recorded
above, but that decision was never written into this file's canonical `QA Decision — T61 batch`
section — the Documentation Manager role correctly halted rather than synchronizing project-wide
documentation against a QA Decision that did not yet exist in the repository. This section is that
missing record, not a new or repeated review. Per this review's own scope: `IMPLEMENTATION_QUEUE.md`,
`PROJECT_STATE.json`, `PROJECT_CHECKPOINT.md`, commit, branch, PR, and merge remain **not done** —
documentation synchronization and closeout are the Documentation Manager's next step, not performed
here.

## Post-Merge Verification — T61 batch (2026-08-16)

Recorded as an append, not a rewrite of the QA Decision above — that section's own account of what
was true at review time (uncommitted working tree, no PR yet) remains accurate history and is left
untouched.

**`T61`'s working tree was subsequently committed, branched, opened as a PR, and merged**, closing the
gap the QA Decision and Reviewer Checklist above both named as outstanding: feature branch
`feature/stage3-t61-me`, feature commit `fa57e28` ("feat(auth): add GET /api/v1/auth/me"), PR #30
("feat(auth): add GET /api/v1/auth/me (T61)"), merged into `main` as `bdffb5e` on 2026-08-15 (commit
authored 2026-08-15T19:33:59Z, merged 2026-08-15T19:39:55Z per `gh pr view 30`).

Independently re-verified this session, directly against the merged repository state (`main` at
`bdffb5e`, `origin/main` confirmed identical via `git rev-parse`), not transcribed from the PR body:

- **Scope:** `git show bdffb5e --stat` / `git diff cca1077..fa57e28 --name-only` both confirm exactly
  the nine files this PR's own description claims (`IMPLEMENTATION_QUEUE.md`, `PROJECT_CHECKPOINT.md`,
  `PROJECT_STATE.json`, `presentation/api/v1/auth.py`, `tests/integration/test_auth_me.py`,
  `docs/AI_HANDOVER.md`, this file, `docs/Roadmap.md`, `docs/SessionReport.md`) — no forbidden file
  (`deps.py`, `router.py`, `AuthService`, `CurrentUser`, `JwtAuthenticationProvider`,
  `RbacAuthorizationService`, `PermissiveAuthorizationService`, any `alembic/` migration, any frontend
  file) appears in either diff.
- **Implementation vs. authorization:** the merged `presentation/api/v1/auth.py` contains exactly
  `MeResponse` and `me()`, reusing `CurrentUserDep` directly, wrapped in `ApiResponse[MeResponse]`,
  raising `UnauthorizedError` when unauthenticated, `roles` sorted — matching
  `docs/HANDOFF/T61_HANDOFF.md` §3/§5's approved scope exactly, with no addition beyond it.
- **CI:** `gh pr view 30 --json statusCheckRollup` — 6/6 checks `SUCCESS` (Backend Lint/format/test
  ×2, Frontend Lint/format/test ×2, Release build verification ×2 — the expected double-trigger per
  [ADR/0017](../../../ADR/0017-github-actions-ci.md), not a re-run or a flake).
- **Local re-verification against merged `main` (`bdffb5e`), live Postgres (`legal_dms_postgres`
  confirmed healthy via `docker ps`):** `uv run pytest -q` → **410 passed, 0 failed, 0 skipped**;
  `uv run ruff check src tests alembic` → clean; `uv run black --check src tests alembic` → clean
  (197 files unchanged); `python -c "from app.main import app"` boot smoke → succeeds;
  `app.openapi()["paths"]` → exactly `/api/v1/auth/login`, `/api/v1/auth/refresh`,
  `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/health`, `/api/v1/version`.
- **Documentation:** this file's own T61 batch (Objective through QA Decision) read in full against
  the merged diff — internally consistent, no discrepancy found between what it claims and what
  actually merged.

**`T61` is now `Done`** — code, tests, QA Decision, and documentation are all merged into `main`.
`T62`–`T67` remain not started, not authorized by this verification pass. `docs/HANDOFF/`,
`docs/prompts/GitCI_PR_Manager.md`, and `docs/prompts/README.md` are separate, unrelated,
still-uncommitted changes — correctly excluded from PR #30, per its own stated scope — and are not
addressed by this verification pass.

## Objective — T62 batch

Continue Stage 3 Phase 3 (routes) with `T62`: admin-only user management — `GET /api/v1/users`
(paginated list), `GET /api/v1/users/{id}`, `POST /api/v1/users` (hashes the incoming password),
`PUT /api/v1/users/{id}` (full-replacement `email`/`full_name`/`phone`), and
`POST /api/v1/users/{id}/deactivate` (soft-disable, never a hard delete). Unlike `T58`–`T61`, all five
routes are gated by `RequirePermission("users:manage")` (`T54`) rather than any degree of
self-service — the first Phase 3 batch to exercise the permission-checking half of `RequirePermission`
(403), not just its authentication half (401), via real HTTP requests.

**Authorization / Scope (recorded before implementation, commit `e10bdc8`, 2026-08-16 — merged as
`ea80b74` via PR #32, confirmed by `git rev-parse HEAD origin/main` both resolving to `ea80b74` before
this batch's implementation began, not assumed):** the project owner explicitly authorized `T62`.
Approved scope, recorded in full in `IMPLEMENTATION_QUEUE.md`'s `T62` row: five hand-written routes in
a **new** `presentation/api/v1/users.py` — `crud_router_factory.py` remains unmodified and unused —
co-located `UserRead`/`UserCreate`/`UserUpdate` schemas (`UserRead` excludes `password_hash`; `UserUpdate`
excludes `password`/`is_active`, all three of its own fields required, no defaults), duplicate email on
create/update → `409` via the existing, previously-unused `ConflictError`, unknown id → `404` via
existing `NotFoundError`. `T63` (role assignment) explicitly out of scope — created users have zero
roles; no password reset/change, no reactivation, no search/filter/sort. No change to `deps.py`,
`AuthService`, `CurrentUser`, or any `T52`–`T61` file; `router.py` changes only to mount the new
router. **This is the seventh consecutive Stage 3 batch (after `T56`–`T61`) where authorization was
actually recorded before implementation began.**

## Tasks Implemented — T62 batch

- **T62 — user management routes.** New `presentation/api/v1/users.py`: `router = APIRouter(prefix=
  "/users", dependencies=[Depends(RequirePermission("users:manage"))])` — one router-level dependency
  covers all five routes (approved explicitly, rather than repeating it per-route), since none of the
  five needs a different permission. Two local, per-request dependencies declared in this module only
  (not added to `deps.py`, per the authorized scope): `get_user_repository()` builds a fresh
  `SqlAlchemyUserRepository` (`T50`, reused as-is) from `DBSessionDep`; `get_user_service()` wraps it in
  the existing, generic `BaseService[User]` (`T55`'s framework layer) — no `UserService` subclass
  needed, since `get_by_id_or_raise()`/`list_page()`/`update()` already do exactly what `list_users()`/
  `get_user()`/`deactivate_user()` need. `create_user()`/`update_user()` reach for the repository
  directly instead, since only `UserRepository.get_by_email()` (not anything `BaseService` exposes) can
  answer "does this email already belong to someone else." `create_user()` hashes the incoming
  plaintext password via the existing `hash_password()` (`T46`) and stores only the resulting
  `password_hash` — the plaintext value is never persisted, returned, or logged. `deactivate_user()`
  sets `is_active = False` and calls `service.update()`, never `service.delete()` — the database row and
  its `user_roles`/`refresh_tokens` relationships are untouched, and calling it twice succeeds both
  times (unconditional assignment, not a state-transition check).

## Files Modified — T62 batch

- `backend/src/app/presentation/api/v1/users.py` — **new**: `UserRead`/`UserCreate`/`UserUpdate`,
  `get_user_repository()`/`get_user_service()` (+ their `Annotated` `Dep` aliases), `_to_read()`, and
  the five route handlers.
- `backend/src/app/presentation/api/v1/router.py` — modified: `users` module imported, `users.router`
  included with `tags=["users"]` — the one explicitly authorized change to this file.
- `backend/tests/integration/test_users.py` — **new**: `TestAuthorization`/`TestListUsers`/
  `TestGetUser`/`TestCreateUser`/`TestUpdateUser`/`TestDeactivateUser`, 28 tests (see below), reusing
  `T58`–`T61`'s `client` fixture/`_make_user()`/`_login()` pattern verbatim, plus local
  `_grant_users_manage()`/`_authorized_headers()`/`_unauthorized_headers()` helpers.
- `docs/ImplementationLog/Stage3/Phase3.md` — this file (T62 batch appended; header's `Related Tasks`/
  `Git Commit`/`Pull Request` lines updated).

No new dependency; `deps.py`, `AuthService`, `CurrentUser`, `JwtAuthenticationProvider`,
`RbacAuthorizationService`, `crud_router_factory.py`, repository implementations (beyond reusing
`SqlAlchemyUserRepository` unmodified), any `alembic/` migration, any frontend file, and every
`T52`–`T61` file otherwise untouched — verified against the authorized scope's explicit constraints,
not just the usual "no scope creep" check. No governance file (`IMPLEMENTATION_QUEUE.md`,
`PROJECT_STATE.json`, `PROJECT_CHECKPOINT.md`) touched, per this role's own instructions. The
pre-existing, unrelated uncommitted changes present in the working tree before this batch began
(`docs/prompts/README.md`, `docs/prompts/GitCI_PR_Manager.md`, `docs/HANDOFF/`) were left exactly as
found — not staged, not committed, not cleaned — per this role's explicit instruction not to touch
unrelated working-tree state.

## Tests Added — T62 batch

28 in `backend/tests/integration/test_users.py`, against a real mounted `app` and real Postgres via
`httpx.AsyncClient`/`ASGITransport` (reusing `T58`–`T61`'s `get_db`-override pattern):

- **`TestAuthorization` (10)** — one `test_<route>_requires_authentication` (401, no token) and one
  `test_<route>_requires_permission` (403, a real authenticated caller never granted `users:manage`)
  for each of the five routes — the first real-HTTP-request proof in this project that
  `RequirePermission`'s 401/403 split (`T54`/`T57`) is reachable end-to-end, not just at the unit level.
- **`TestListUsers` (2)** — `test_list_returns_paginated_users` (created users appear in the response,
  wrapped in `ApiResponse`'s `{"data": ..., "meta": {"pagination": {...}}}` shape, no password field on
  any item); `test_pagination_limit_and_offset` (`page_size=1` returns exactly one item per page, and
  page 1 vs. page 2 return different rows — proves `offset` actually advances, not just that `limit`
  caps).
- **`TestGetUser` (2)** — existing user → `200` with every `UserRead` field correct; unknown id → `404`.
- **`TestCreateUser` (3)** — valid create → `201`, full profile in the response, no `password`/
  `password_hash` key and no plaintext-password substring anywhere in the response body;
  `test_password_is_hashed_in_database` — the stored `password_hash` differs from the plaintext and
  independently `verify_password()`s correctly; duplicate email → `409`.
- **`TestUpdateUser` (7)** — valid full `PUT` updates all three fields; updating to the user's own
  *unchanged* email succeeds (not a false `409`, proving the duplicate check excludes the record being
  updated); a `PUT` body missing a required key (`phone` omitted entirely) → `422` (full-replacement
  semantics enforced, not `PATCH`-style optionality); a `password` key smuggled into the body is
  silently ignored — the stored hash still verifies against the *original* password afterward; an
  `is_active` key smuggled into the body is silently ignored — the response still reflects the
  pre-existing value; unknown id → `404`; a `PUT` setting one user's email to *another* user's existing
  email → `409`.
- **`TestDeactivateUser` (4)** — active user → `is_active` becomes `False` in the response;
  `test_database_row_and_relationships_are_preserved` — after deactivation, the `User` row is still
  fetchable directly, and both a `UserRole` row (granted via `_grant_users_manage()`) and a
  `RefreshToken` row (created via a real `_login()`) for that user are still present, proving no
  cascade/hard-delete occurred; a second deactivate call on an already-inactive user still returns
  `200` with `is_active: False` (idempotent); unknown id → `404`.

`_grant_users_manage()` attaches a uniquely-named `Role` to the **existing, already-seeded**
`Permission(code="users:manage")` row (fetched, not duplicated — the seed migration deliberately does
not seed `role_permissions` itself; `T66`'s exact matrix is still pending sign-off) via `RolePermission`,
then assigns that role to a user via `UserRole` — the same grant pattern
`test_auth_dependency_wiring.py` already established, reused rather than reinvented.

## Test Results — T62 batch

- New tests in isolation: `tests/integration/test_users.py` — **28/28 passed** on first run, personally
  run this session (`uv run pytest tests/integration/test_users.py -v` against live Postgres —
  `legal_dms_postgres` confirmed healthy via `docker ps`).
- Full backend suite: **438 passed** (410 prior + 28 new), 0 failed, 0 skipped. Personally re-run this
  session — `uv run pytest -q` against the same live Postgres instance.
- **Lint:** `uv run ruff check src tests alembic` — clean, re-verified directly.
- **Format:** `uv run black --check src tests alembic` — clean (199 files unchanged; `users.py` and
  `test_users.py` were both reformatted once by `black` itself before this final check, both
  re-verified directly afterward).
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds, re-verified directly;
  `app.openapi()["paths"]` independently confirmed to contain exactly `/api/v1/auth/login`,
  `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/health`,
  `/api/v1/users` (`GET`, `POST`), `/api/v1/users/{user_id}` (`GET`, `PUT`),
  `/api/v1/users/{user_id}/deactivate` (`POST`), `/api/v1/version` — no stray `DELETE
  /api/v1/users/{id}`, no reactivation route, nothing else.
- **Scope check:** `git status --short` / `git diff --stat` on the feature branch confirm exactly one
  file modified (`presentation/api/v1/router.py`, mount-only) and two new files
  (`presentation/api/v1/users.py`, `tests/integration/test_users.py`) — no `deps.py`, `AuthService`,
  `CurrentUser`, `crud_router_factory.py`, migration, frontend, or governance file touched; the
  pre-existing unrelated working-tree changes (`docs/prompts/README.md`,
  `docs/prompts/GitCI_PR_Manager.md`, `docs/HANDOFF/`) remain untouched and unstaged.

## Design Decisions — T62 batch

- **One router-level `RequirePermission("users:manage")`, not five per-route copies.** All five routes
  require the exact identical permission — `deps.py`'s own docstring already documents both a
  per-route and a router-level `dependencies=[...]` usage as equally valid; router-level is the
  non-repetitive choice here, and was explicitly approved before implementation.
- **`BaseService[User]` reused directly, no `UserService` subclass.** `list_page()`/
  `get_by_id_or_raise()`/`update()` already do exactly what three of the five routes need; adding a
  subclass with no overridden behavior would be a pure indirection with no behavioral payoff.
- **`UserRepositoryDep` alongside `UserServiceDep`, not instead of it.** `get_by_email()` — needed by
  `create_user()`/`update_user()` for the duplicate-email check — isn't part of `BaseService`'s generic
  surface; both dependencies resolve from the same per-request `DBSessionDep`-backed session (FastAPI's
  own dependency caching within one request), so using both where a route needs both capabilities adds
  no extra session/connection, just two thin wrappers around it.
- **`_to_read()` mirrors `crud_router_factory._to_read()` exactly** (`UserRead.model_validate(user,
  from_attributes=True)`) — `password_hash` is absent from every response not because it's filtered
  out, but because `UserRead` never declares the field for `model_validate` to pick up in the first
  place, the same structural guarantee the factory's own read schemas rely on.
- **Update's duplicate-email check excludes the record being updated.** A full-replacement `PUT` that
  resubmits a user's own unchanged email must not 409 against itself — `existing.id != user.id` is the
  one piece of update-specific logic beyond "reuse the create-path check," covered explicitly by
  `test_updating_to_its_own_unchanged_email_succeeds`.
- **`password`/`is_active` are structurally, not defensively, excluded from `UserUpdate`.** Neither
  field is declared on the schema, so extra keys in the request body are silently ignored by Pydantic
  rather than rejected — proven, not assumed, by
  `test_password_cannot_be_updated_through_this_route`/`test_is_active_cannot_be_changed_through_this_route`
  asserting the stored/returned values are unchanged after submitting a body that tries to smuggle them
  in.

## Problems Encountered — T62 batch

**None on the technical side.** All 28 new tests passed on their first run against live Postgres; no
lint/format fixes beyond `black`'s own two auto-reformats (whitespace/line-length only, no logic
change); no mid-implementation design question deferred.

**Governance side — continuing, not restarting, the streak `T56`–`T61` began:** authorization commit
`e10bdc8` was independently re-verified this session (`git rev-parse HEAD origin/main`, both `ea80b74`,
confirmed to already carry `e10bdc8` in its ancestry via PR #32's merge) as preceding any
implementation — no implementation or test file for `T62` existed anywhere in the tree before this
batch's own changes. This is the **seventh** consecutive Stage 3 batch to get this right, after
`T52`–`T55`'s four consecutive misses. Those four findings remain on record in `Phase2.md`, unerased.

## Deferred Work — T62 batch

- **`T63`–`T67`** — not started, per `T62`'s own scope: `T63` (role assignment), `T64` (cross-route
  integration tests beyond each route's own), `T65` (audit-log wiring), `T66` (`role_permissions`
  matrix sign-off), `T67` (bootstrap CLI — notably depends on `T62`, per `IMPLEMENTATION_QUEUE.md`'s
  own dependency table).
- **QA review** — not performed by this batch; the QA Reviewer role must independently re-verify before
  any documentation sync or merge proceeds.
- **Merge, branch cleanup, local `main` sync** — deliberately not performed by this batch, per this
  role's own stop conditions (Backend Developer implements, tests, opens the PR, and stops; merging is
  explicitly reserved for a later step in the established workflow, not this role).

## Reviewer Checklist — T62 batch

Self-assessed by the Backend Developer role against this session's own verified work.

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

Notes on the less-obvious ones:

- **ADR updated (if required):** `□` — not required: five routes reusing already-approved
  (`T46`/`T50`/`T54`/`T55`) infrastructure, no new architectural decision.
- **PROJECT_STATE updated (if required):** `□` — deliberately not updated by this batch, for the same
  reason `T61`'s own checklist gave: `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/
  `PROJECT_CHECKPOINT.md` are Project Manager/Documentation Manager owned, synchronized only after a QA
  Decision exists — a boundary honored, not a gap.
- **No scope creep:** `☑` — the code stayed exactly within `T62`'s authorized scope (verified above:
  one file modified — mount-only — two new files, every forbidden file/behavior confirmed untouched:
  no `DELETE` route, no reactivation, no role assignment, no password reset, no search/filter/sort),
  and — for the seventh consecutive batch — so did the authorization-recording process.
- **Ready for QA:** `☑` in the sense that implementation, tests, and this log entry are complete, the
  full suite is green, and a PR exists for review; **`T62` is explicitly not being claimed as done
  here** — no QA Decision exists yet, and this batch does not render one.

`T62`'s QA Decision, `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/`PROJECT_CHECKPOINT.md`
synchronization, and merge are all **not yet done** and intentionally outside this batch's scope — see
Deferred Work above. See this file's own metadata block (`Status: In Progress` — Phase 3 continues with
`T63`–`T65`, not yet started or authorized).

## QA Decision — T62 batch

```
QA Decision (T62 batch)

□ Approved
☑ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, independently, in two passes against two different repository
states — first against PR #33 pre-merge (`feature/stage3-t62-users` at `a3e8810`, base `main` at
`ea80b74`), then re-verified in full a second time against merged `main`/`origin/main` at `3a4a21c`
(`Merge pull request #33 ... Merge: ea80b74 a3e8810`) — after a Documentation Manager closeout attempt
correctly halted on discovering no QA Decision existed anywhere in the repository for `T62` despite the
implementation already being merged. Both passes independently verified, not transcribed from the
Backend Developer's Reviewer Checklist:

- **Scope:** `git show 3a4a21c --stat` confirms exactly four files in the merge
  (`presentation/api/v1/router.py`, new `presentation/api/v1/users.py`, new
  `tests/integration/test_users.py`, this file). `git diff ea80b74 3a4a21c` against every file
  `T62`'s authorization forbids (`deps.py`, `application/auth_service.py`,
  `application/interfaces/auth.py` (`CurrentUser`), `presentation/common/crud_router_factory.py`,
  `infrastructure/auth/*`, `infrastructure/persistence/models/*`, `alembic/`, `frontend/`) returned
  zero lines across the entire authorization-to-merge range, not just the feature commit alone. No
  `T63`/role-assignment code present.
- **Tests:** `uv run pytest tests/integration/test_users.py -v` — **28/28 passed**, re-run against
  merged `main` on live Postgres (`legal_dms_postgres`, confirmed healthy). Full suite:
  `uv run pytest -q` — **438 passed**, 0 failed, 0 skipped — identical to the pre-merge count, as
  expected for a merge that introduced no new commits beyond the feature branch itself.
- **Lint/format:** `uv run ruff check src tests alembic` — clean. `uv run black --check src tests
  alembic` — clean (199 files unchanged).
- **Boot smoke test:** `python -c "from app.main import app"` succeeded on merged `main`;
  `app.openapi()["paths"]` independently re-confirmed to contain exactly `/api/v1/auth/login`,
  `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/health`,
  `/api/v1/users` (`GET`, `POST`), `/api/v1/users/{user_id}` (`GET`, `PUT`),
  `/api/v1/users/{user_id}/deactivate` (`POST`), `/api/v1/version` — no stray `DELETE`, no
  reactivation route. `UserRead`/`UserCreate`/`UserUpdate`'s OpenAPI schema fields independently
  inspected: `UserRead` has no `password_hash`/`roles`; `UserUpdate` has no `password`/`is_active`.
- **CI:** all six GitHub Actions checks on PR #33 (`Build verification` ×2, `Lint, format, and test`
  ×4) passed, independently confirmed via `gh pr checks 33` before merge.
- **Behavior:** router-level `RequirePermission("users:manage")` (`T54`, unmodified) correctly gates
  all five routes (401 unauthenticated, 403 authenticated-without-permission, both independently
  reasoned from `deps.py`'s unmodified source and confirmed by the 10 `TestAuthorization` tests);
  `create_user()` persists only `hash_password()`'s output, never the plaintext, confirmed by
  `test_password_is_hashed_in_database` reading the row directly; `deactivate_user()` calls
  `service.update()` (traced through `BaseService`/`SqlAlchemyRepository` source — `flush()` only,
  never `session.delete()`), row and `UserRole`/`RefreshToken` relationships confirmed still present
  post-deactivation, and calling it twice remains idempotent; `UserUpdate`'s duplicate-email check
  correctly excludes the record being updated (`existing.id != user.id`).

**No technical defects found; the implementation is correct on the merits.** This is
`Approved with comments`, not a plain `Approved`, for exactly one reason — a governance finding, not a
code finding:

**Named governance deviation: `T62` was merged into `main` (PR #33 → `3a4a21c`) before any QA Decision
existed anywhere in the repository.** This is a genuine violation of `PROJECT_WORKFLOW.md`'s standard
lifecycle (QA Reviewer → Documentation Manager → Git Commit/Push/PR/Merge) and of this file's own
T62 batch record, which explicitly stated the opposite intent in three places (Deferred Work: "QA
review — not performed by this batch; the QA Reviewer role must independently re-verify before any
documentation sync **or merge** proceeds"; Reviewer Checklist: "no QA Decision exists yet, and this
batch does not render one"; closing line: "`T62`'s QA Decision, ... and merge are all not yet done").
Unlike `T61`'s equivalent gap (this file's own `QA Decision — T61 batch` section records that the QA
review there ran against the *working tree before it was committed* — merge simply hadn't happened
yet), `T62`'s merge already happened, irreversibly, before this gate cleared. A pre-merge QA pass by
this same role did occur (against PR #33 at `a3e8810`) and reached this identical disposition on the
merits — so the technical review itself was not skipped, only its recording in this canonical file,
which is what let the merge proceed without a repository-visible gate. This is recorded here as
permanent governance history, not erased or smoothed over, the same discipline this project applied to
`T52`–`T55`'s authorization-recording gaps. No code change is required or requested — the finding is
procedural: the QA Decision must be recorded in this file *before* a merge happens, not reconstructed
after the fact.

`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/`PROJECT_CHECKPOINT.md` synchronization is the
Documentation Manager's next step, now that a QA Decision exists in the repository — not performed by
this entry. This QA review did not merge, branch, commit, push, modify source/tests/migrations, modify
governance files, or touch the pre-existing unrelated working-tree items
(`docs/prompts/README.md`, `docs/prompts/GitCI_PR_Manager.md`, `docs/HANDOFF/`).

## Objective — T63 batch

Continue Stage 3 Phase 3 (routes) with `T63`: role assignment/removal for existing users and existing
roles — `POST /api/v1/users/{user_id}/roles` (assign) and `DELETE /api/v1/users/{user_id}/roles/{role_id}`
(remove). Unlike `T62`'s five routes (`users:manage` only), both new routes must accept *either*
`users:manage` **or** `roles:manage` — the first Stage 3 batch to need an "any of several permissions"
authorization check, not a single fixed one.

**Authorization / Scope (recorded before implementation, commit `93cda84`, 2026-08-16 — merged as
`97ab953` via PR #35, confirmed by `git rev-parse HEAD origin/main` both resolving to `97ab953` before
this batch's implementation began, not assumed):** the project owner explicitly authorized `T63`.
Approved scope, recorded in full in `IMPLEMENTATION_QUEUE.md`'s `T63` row: the two routes above; a new
`RoleAssignmentRead` schema (`user_id`, `role_id`, `assigned_at`, `assigned_by`) and `RoleAssignmentCreate`
(`role_id`); `RequirePermission` (`deps.py`, T54) extended from `RequirePermission(permission: str)` to
`RequirePermission(*permissions: str)`, authorizing on any one supplied code, every existing
single-argument call site continuing to behave identically; new narrow `assign_role()`/`remove_role()`
methods on the existing `UserRepository`/`SqlAlchemyUserRepository` (no new repository class); role
existence validated via the existing generic `SqlAlchemyRepository[Role].get_by_id()` (no `Role`-specific
repository, no role creation). Explicitly out of scope: role creation, `role_permissions`/permission-matrix
changes (`T66`'s territory), password reset/change, reactivation, hard user deletion, audit logging,
search/filter/sort, any frontend or migration change, and any change to `UserRead`/`UserCreate`/`UserUpdate`
(T62), `AuthService`, `CurrentUser`, or `crud_router_factory.py`. **This is the eighth consecutive Stage 3
batch (after `T56`–`T62`) where authorization was actually recorded before implementation began.**

## Tasks Implemented — T63 batch

- **`RequirePermission(*permissions: str)`** (`presentation/api/deps.py`) — the `is_authenticated` → 401
  check (T57) runs once, unchanged, ahead of any permission check, regardless of how many codes are
  supplied. Every permission except the last is tried inside a `try`/`except ForbiddenError: continue`,
  returning on the first one that doesn't raise; the *last* code is called unguarded, letting its own
  `ForbiddenError` propagate naturally if every permission was denied. For a single supplied permission
  (every call site before `T63`), the loop body never executes and the sole code is checked directly —
  the exact same call, in the exact same way, as before this change. No change to `AuthorizationService`,
  `RbacAuthorizationService`, `CurrentUser`, or `PermissiveAuthorizationService` — the "any of several"
  behavior lives entirely inside `RequirePermission` itself, since `AuthorizationService.require_permission()`
  already only ever needed to check one permission at a time.
- **`assign_role()`/`remove_role()`** (`application/interfaces/user_repository.py` +
  `infrastructure/persistence/sqlalchemy_user_repository.py`) — `assign_role(user_id, role_id,
  assigned_by) -> UserRole | None` pre-checks for an existing `(user_id, role_id)` row and returns `None`
  without inserting if one exists; otherwise inserts and returns the new row. **Concurrency hardening
  beyond the pre-check, per explicit instruction:** the insert's own `flush()` is wrapped in `try`/`except
  IntegrityError: return None` — if a concurrent request wins a race and inserts the identical
  `(user_id, role_id)` row first, the database's own `UniqueConstraint(user_id, role_id)` rejects the
  second `INSERT`, and that rejection is translated into the same `None` signal the pre-check gives,
  rather than letting an unhandled `IntegrityError` surface as a `500`. `remove_role(user_id, role_id) ->
  bool` deletes the exact row if present and reports whether anything was actually deleted. Both stay
  narrow lookups/mutations returning `Optional`/`bool` — neither raises an `AppError` itself, matching
  `get_by_email()`'s existing "narrow method, caller decides the HTTP status" convention; the routes are
  what turn `None`/`False` into `409`/`404`.
- **`assign_role()`/`remove_role()` routes** (`presentation/api/v1/users.py`) — both reuse the router-level
  `RequirePermission("users:manage", "roles:manage")` (no per-route dependency needed). Both resolve the
  target user via the existing `UserServiceDep.get_by_id_or_raise()` (404) and the role via a new local
  `RoleRepositoryDep` wrapping the existing *generic* `SqlAlchemyRepository[Role]` (404, `get_by_id()`
  only — no new repository class). `assign_role()` populates `assigned_by` from `CurrentUserDep.id`
  (guaranteed non-`None`: the router-level `RequirePermission` already enforced authentication before
  either handler runs, per T57's 401-before-403 order) and returns `201`; a `None` from the repository
  method raises `409 ConflictError`. `remove_role()` returns `204` on a real deletion; `False` from the
  repository method raises `404 NotFoundError` — missing-assignment is never treated as success.

## Files Modified — T63 batch

- `backend/src/app/presentation/api/deps.py` — modified: `RequirePermission` signature/body (above);
  new `ForbiddenError` import.
- `backend/src/app/application/interfaces/user_repository.py` — modified: `assign_role()`/`remove_role()`
  added as abstract methods; new `UserRole` import.
- `backend/src/app/infrastructure/persistence/sqlalchemy_user_repository.py` — modified: the two methods
  implemented; new `IntegrityError` import.
- `backend/src/app/presentation/api/v1/users.py` — modified: router-level dependency now carries two
  permission codes; new `get_role_repository()`/`RoleRepositoryDep`; new `RoleAssignmentCreate`/
  `RoleAssignmentRead` schemas; new `assign_role()`/`remove_role()` route handlers; module docstring
  updated to describe all seven routes.
- `backend/tests/integration/test_users.py` — extended: new `_grant_permissions()`/
  `_headers_with_permissions()`/`_make_role()` helpers (additive only — T62's own `_grant_users_manage()`
  and its existing tests untouched) and three new test classes, 21 tests (see below).
- `backend/tests/support/in_memory_user_repository.py` — modified, **not in the originally listed file
  scope, flagged and implemented after explicit instruction to proceed** (see Problems Encountered):
  `assign_role()`/`remove_role()` added so this test-only fake keeps satisfying the now-larger
  `UserRepository` ABC — a mechanical consequence of extending the interface, not a scope expansion.
- `docs/ImplementationLog/Stage3/Phase3.md` — this file (T63 batch appended; header's `Related Tasks`/
  `Git Commit`/`Pull Request` lines updated).

No new dependency; `AuthService`, `CurrentUser`, `crud_router_factory.py`, `Role`/`RolePermission`
models, any `alembic/` migration, any frontend file, `UserRead`/`UserCreate`/`UserUpdate`, and every
`T52`–`T62` file otherwise untouched. No governance file (`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/
`PROJECT_CHECKPOINT.md`) touched. The pre-existing, unrelated uncommitted changes present in the working
tree before this batch began (`docs/prompts/README.md`, `docs/prompts/GitCI_PR_Manager.md`,
`docs/HANDOFF/`) were left exactly as found.

## Routes — T63 batch

- `POST /api/v1/users/{user_id}/roles` — `201` → `ApiResponse[RoleAssignmentRead]`; `404` unknown user;
  `404` unknown role; `409` duplicate assignment.
- `DELETE /api/v1/users/{user_id}/roles/{role_id}` — `204` no body; `404` unknown user; `404` unknown
  role; `404` assignment doesn't exist.

`app.openapi()["paths"]` independently confirmed to contain exactly these two new entries alongside the
prior nine — no role-creation route, no reactivation route, no password route, no user `DELETE` route,
no search/filter/sort route, no `T66` route.

## Schemas — T63 batch

- `RoleAssignmentCreate` — `role_id: UUID`.
- `RoleAssignmentRead` — `user_id: UUID`, `role_id: UUID`, `assigned_at: datetime`, `assigned_by: UUID
  | None`. `UserRead`/`UserCreate`/`UserUpdate` (T62) unmodified; `UserRead` still does not carry `roles`.

## Tests Added — T63 batch

21 new tests in `backend/tests/integration/test_users.py`, against a real mounted `app` and real Postgres
via `httpx.AsyncClient`/`ASGITransport` (reusing `T58`–`T62`'s `get_db`-override pattern):

- **`TestRoleAssignmentAuthorization` (10)** — 401 on both routes with no token; 403 on both routes for a
  caller with neither permission; `users:manage` alone allowed on both routes; `roles:manage` alone
  allowed on both routes; both permissions together still allowed; a regression test proving T62's own
  `GET /api/v1/users` (still gated by the same, now two-permission, router-level dependency) continues
  denying an unpermitted caller and allowing a `users:manage` one exactly as before.
- **`TestAssignRole` (5)** — valid assignment → `201` with correct `user_id`/`role_id`/`assigned_at`/
  `assigned_by` (the latter asserted equal to the *authenticated caller's own* id, not the target user's);
  unknown user → `404`; unknown role → `404`; a duplicate assignment → `409`, with a direct query
  confirming exactly one matching `UserRole` row exists afterward (not two); a direct row-count check that
  neither a `Role` nor a `RolePermission` row was created by the assign call itself (counted *after* the
  authorized caller's own grant setup, so only the assignment's own side effects are measured).
- **`TestRemoveRole` (6)** — existing assignment → `204` with an empty body; removing one of two
  assignments leaves the `User` row, the `Role` row, and the *other* `UserRole` row all present
  (`remaining_role_ids == {other_role.id}` — the join-row-only deletion proven directly, not just
  inferred from the status code); a missing (never-created) assignment → `404`, not a silent success;
  unknown user → `404`; unknown role → `404`; a direct row-count check that removal creates no `Role`/
  `RolePermission` row either.

## Test Results — T63 batch

- New tests in isolation: `tests/integration/test_users.py` (T62's 28 + T63's 21) — **49/49 passed**,
  personally run this session (`uv run pytest tests/integration/test_users.py -v` against live
  Postgres — `legal_dms_postgres` confirmed healthy via `docker ps`).
- Full backend suite: **459 passed** (438 prior + 21 new), 0 failed, 0 skipped. Personally re-run this
  session — `uv run pytest -q` against the same live Postgres instance. **One first-run failure surfaced
  and fixed before this count** (see Problems Encountered): 35 `tests/unit/test_jwt_authentication_provider.py`
  errors from `InMemoryUserRepository` no longer satisfying the (now larger) `UserRepository` ABC.
- `tests/unit/test_auth.py::TestRequirePermission` (the existing single-permission suite) — re-run in
  isolation, **8/8 still passing unchanged**, including
  `test_passes_the_configured_permission_and_user_through_unchanged`'s exact-call assertion
  (`service.calls == [(user, "clients:write")]`) — direct proof the single-permission path is
  byte-for-byte the same call as before `T63`.
- **Lint:** `uv run ruff check src tests alembic` — clean, re-verified directly.
- **Format:** `uv run black --check src tests alembic` — clean (199 files unchanged; `test_users.py` was
  reformatted once by `black` itself before this final check, re-verified directly afterward).
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds, re-verified directly;
  `app.openapi()["paths"]` independently confirmed to contain exactly the eleven route/method
  combinations across the nine prior paths plus the two new `T63` paths — both `RoleAssignmentCreate` and
  `RoleAssignmentRead` present in `components.schemas`.
- **Scope check:** `git status --short` / `git diff --stat` on the feature branch confirm exactly six
  files modified (the five originally listed, plus `tests/support/in_memory_user_repository.py`, flagged
  before editing) — no `AuthService`, `CurrentUser`, `crud_router_factory.py`, `Role`/`RolePermission`
  model, migration, frontend, or governance file touched; the pre-existing unrelated working-tree changes
  remain untouched and unstaged.

## Design Decisions — T63 batch

- **The "any of several permissions" logic lives entirely in `RequirePermission`, not
  `AuthorizationService`.** `AuthorizationService.require_permission()`'s existing single-permission
  signature and every implementation of it (`RbacAuthorizationService`, `PermissiveAuthorizationService`)
  stay untouched — `RequirePermission` just calls it once per candidate permission until one succeeds
  (or the last one's own failure propagates), which is sufficient to express "any of" without touching
  the port at all, matching the explicit "prefer implementing the OR logic entirely inside
  `RequirePermission`" instruction.
- **`assign_role()`/`remove_role()` return `Optional`/`bool`, never raise `AppError` themselves.** Matches
  `get_by_email()`'s existing convention exactly — every HTTP-status decision (`404`/`409`) stays in the
  route, not the repository, consistent with how `create_user()`/`update_user()` (T62) already decide
  `409` from a `None` lookup rather than the repository raising it.
- **`IntegrityError` is caught only around `assign_role()`'s own `flush()`, narrowly** — not a new
  general-purpose error-translation layer, just the one place this batch's own pre-check-then-insert
  pattern has a real, explicitly-flagged TOCTOU race the database's `UniqueConstraint(user_id, role_id)`
  can actually hit. No equivalent wrapping was added to `remove_role()` (not required by the authorized
  contract) or anywhere else in the repository.
- **No dedicated true-concurrency test for the `IntegrityError` path.** A real two-connection race is
  inherently non-deterministic to trigger reliably in a test, and a single shared `AsyncSession` (this
  project's `db_session` fixture) isn't safe for concurrent use from two coroutines at once — attempting
  to simulate it would either be flaky or would test something other than the real race. The `409`-on-
  duplicate path is proven end-to-end via the ordinary sequential pre-check case
  (`test_duplicate_assignment_returns_409_and_creates_no_second_row`); the `IntegrityError` branch itself
  is covered by direct code reading, not a dedicated test — recorded here plainly rather than silently
  omitted.
- **`get_role_repository()` returns the existing generic `SqlAlchemyRepository[Role]` directly** — no
  `RoleRepository` port/class introduced, since `get_by_id()` is the only capability role-assignment needs
  and the generic repository already provides it, per the explicit "no new repository class" instruction.

## Problems Encountered — T63 batch

**One test-infrastructure break, flagged and fixed, not silently absorbed:** extending the
`UserRepository` ABC with `assign_role()`/`remove_role()` as abstract methods broke
`tests/support/in_memory_user_repository.py`'s `InMemoryUserRepository` — a test-only fake used by
`test_jwt_authentication_provider.py` and others, unrelated to `test_users.py` — which no longer satisfied
the (now larger) interface and raised `TypeError: Can't instantiate abstract class ... without an
implementation for abstract methods 'assign_role', 'remove_role'` at fixture setup, surfacing as 35 errors
on the first full-suite run. This file wasn't in the originally authorized file list; per this role's own
"if you believe an additional file is required, STOP and report it before modifying it" instruction, the
blocker, cause, and exact proposed two-method fix were reported before editing. This is a mechanical,
unavoidable consequence of the authorized interface extension itself (any concrete `UserRepository`
implementation must implement whatever the ABC declares), not a scope expansion — no new capability was
added to the fake beyond satisfying the same interface `SqlAlchemyUserRepository` now also satisfies.

**Governance side — continuing, not restarting, the streak `T56`–`T62` began:** authorization commit
`93cda84` was independently re-verified this session (`git rev-parse HEAD origin/main`, both `97ab953`,
confirmed to already carry `93cda84` in its ancestry via PR #35's merge) as preceding any implementation —
no implementation or test file for `T63` existed anywhere in the tree before this batch's own changes.
This is the **eighth** consecutive Stage 3 batch to get this right, after `T52`–`T55`'s four consecutive
misses. Those four findings remain on record in `Phase2.md`, unerased.

## Deferred Work — T63 batch

- **`T64`–`T67`** — not started, per `T63`'s own scope: `T64` (cross-route integration tests beyond each
  route's own), `T65` (audit-log wiring), `T66` (`role_permissions` matrix sign-off), `T67` (bootstrap
  CLI).
- **QA review** — not performed by this batch; the QA Reviewer role must independently re-verify before
  any documentation sync or merge proceeds.
- **Merge, branch cleanup, local `main` sync** — deliberately not performed by this batch, per this
  role's own stop conditions.

## Reviewer Checklist — T63 batch

Self-assessed by the Backend Developer role against this session's own verified work.

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

Notes on the less-obvious ones:

- **ADR updated (if required):** `□` — not required: extending an existing dependency factory
  (`RequirePermission`) and an existing repository interface with narrow, already-approved-shape methods,
  no new architectural decision.
- **PROJECT_STATE updated (if required):** `□` — deliberately not updated by this batch, for the same
  reason `T61`/`T62`'s own checklists gave: `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/
  `PROJECT_CHECKPOINT.md` are Project Manager/Documentation Manager owned, synchronized only after a QA
  Decision exists — a boundary honored, not a gap.
- **No scope creep:** `☑` — the code stayed exactly within `T63`'s authorized scope (verified above: six
  files modified, one of them flagged before editing as a mechanical necessity; no role creation, no
  `role_permissions` change, no password/reactivation/hard-delete/audit/search work, no `T66` behavior).
- **Ready for QA:** `☑` in the sense that implementation, tests, and this log entry are complete, the full
  suite is green, and a PR exists for review; **`T63` is explicitly not being claimed as done here** — no
  QA Decision exists yet, and this batch does not render one. `T63` is **not merged**.

`T63`'s QA Decision, `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/`PROJECT_CHECKPOINT.md`
synchronization, and merge are all **not yet done** and intentionally outside this batch's scope — see
Deferred Work above. See this file's own metadata block (`Status: In Progress` — Phase 3 continues with
`T64`–`T65`, not yet started or authorized).

## QA Decision — T63 batch

```
QA Decision (T63 batch)

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, independently, against PR #36 (`feature/stage3-t63-role-assignment`
at `3cea676`, base `main` at `97ab953`) — **PR #36 is not merged; this decision is recorded pre-merge**,
unlike `T61`/`T62`'s post-hoc corrections. Verified directly, not transcribed from the Backend
Developer's Reviewer Checklist:

- **Authorization:** `93cda84` (merged `97ab953`, PR #35) independently confirmed as an ancestor of
  `origin/main` and as preceding the implementation commit `3cea676`. `IMPLEMENTATION_QUEUE.md`'s `T63`
  row and `PROJECT_STATE.json`'s `currentStage.note` both read and confirmed to match the implementation
  exactly.
- **Scope:** `git diff 97ab953...3cea676 --stat` confirms exactly seven files: the six originally
  authorized plus `tests/support/in_memory_user_repository.py`. Zero diff independently confirmed
  against `AuthorizationService`, `RbacAuthorizationService`, `PermissiveAuthorizationService`,
  `CurrentUser`, `crud_router_factory.py`, `alembic/`, and `frontend/` across the full
  authorization-to-implementation range. `UserRead`/`UserCreate`/`UserUpdate` confirmed byte-identical
  in the diff (only new classes appended after `deactivate_user()`). No `Role`/`RolePermission` model
  change; no migration.
- **Deviation assessment (`tests/support/in_memory_user_repository.py`):** confirmed genuinely necessary,
  not a scope-creep convenience. `InMemoryUserRepository` is directly instantiated by two pre-existing,
  T63-unrelated unit-test fixtures (`test_auth_service.py:43`, `test_jwt_authentication_provider.py:24`);
  extending the `UserRepository` ABC with two new `@abstractmethod`s makes any concrete subclass missing
  them fail to instantiate (`TypeError`) — a mechanical Python ABC consequence, not a design choice.
  The added implementation (12 lines) is minimal and mirrors the real repository's exact contract
  (dict-keyed "already exists → `None`" / "popped → `bool`"), adding no capability beyond satisfying the
  interface. Correctly flagged and reported before editing, per the log's own account.
- **Tests (independently re-run, live Postgres):** `tests/integration/test_users.py` — **49/49 passed**
  (28 T62 + 21 T63). Full suite — **459/459 passed**, 0 failed, 0 skipped, matching the batch's own
  reported count exactly (one transient failure surfaced on this reviewer's first full-suite run,
  traced to four stray `Role`/`User` rows left in the live database by this reviewer's own ad hoc
  diagnostic scripts used to test the `IntegrityError` race path below — not a `T63` defect; the rows
  were identified by name/timestamp, deleted, and the suite re-run clean before this decision was
  recorded). `tests/unit/test_auth.py::TestRequirePermission` — **8/8 passed** in isolation, confirming
  the single-permission call sites are unaffected. `ruff check`/`black --check` — both clean.
- **Boot/route/schema surface:** `python -c "from app.main import app"` succeeds; `app.openapi()["paths"]`
  contains exactly the nine prior routes plus `POST /api/v1/users/{user_id}/roles` and
  `DELETE /api/v1/users/{user_id}/roles/{role_id}` — no role-creation/list/update route, no reactivation
  route, no user `DELETE` route. `RoleAssignmentCreate` (`role_id` only) and `RoleAssignmentRead`
  (`user_id`/`role_id`/`assigned_at`/`assigned_by`) independently inspected via the live OpenAPI schema
  and confirmed to carry exactly those fields, nothing more.
- **`RequirePermission` OR-logic:** read directly — `permissions[:-1]` tried under `try/except
  ForbiddenError: continue`, `permissions[-1]` called unguarded so its failure propagates if every
  candidate was denied; for one supplied argument the loop body never executes, so the single-permission
  call is the identical call it was before `T63`. Confirmed both by source reading and by the full
  `TestRoleAssignmentAuthorization` matrix (401 unauthenticated, 403 neither permission, 201 with
  `users:manage` alone, 201 with `roles:manage` alone, 201 with both, and a regression proving `T62`'s
  own `GET /api/v1/users` is unaffected) plus `TestRequirePermission`'s unchanged 8/8.
- **`assign_role()`/`remove_role()` concurrency handling — independently verified empirically, not just
  read:** wrote and ran a standalone script against live Postgres reproducing the genuine race
  `assign_role()`'s `IntegrityError` catch is meant to handle (a second session committing the identical
  `(user_id, role_id)` row between the first session's pre-check and its own `INSERT`). Confirmed the
  caught `IntegrityError` leaves the session in SQLAlchemy's "pending rollback" state, and that this is
  safe in context: the route always turns a `None` result into a raised `ConflictError`, which propagates
  through `get_db()`'s `except Exception: await session.rollback(); raise` — `rollback()`, not `commit()`,
  is what actually runs on that path, and `rollback()` is confirmed (empirically, not just by
  documentation) to fully clear the pending-rollback state. The `409` response is not at risk of becoming
  an unhandled `500` under a genuine race. This required going beyond the code-reading level of review to
  settle, and the result confirms the batch's own "handled safely" claim rather than the initial concern
  it could raise.
- **POST/DELETE route behavior:** every required case independently confirmed passing —
  unknown-user-404, unknown-role-404, duplicate-409 (with a direct row-count proving no second `UserRole`
  row), `assigned_by` equal to the authenticated caller's own id (not the target user's), no `Role`/
  `RolePermission` row created by either route, existing/removed-204, missing-assignment-404 (not a
  silent idempotent success, correctly matching the DELETE-verb precedent rather than `deactivate`'s
  idempotent-POST one), and unrelated `UserRole`/`User`/`Role` rows surviving a removal.
- **Security/regression:** `UserRead` unchanged from `T62` (still excludes `password_hash`); no plaintext
  password touched by this batch at all; no authorization bypass found in either 401/403 ordering or the
  OR-logic; no unintended role-management route surface; no accidental `Role`/`RolePermission` mutation on
  either route, independently confirmed via direct row counts in both directions (assign and remove).

**No technical defects found. No unresolved scope issue.** This is a plain `Approved` — the one
candidate process concern (the file-scope deviation) was correctly flagged and disclosed by the
implementer before editing, verified independently here as genuinely necessary and minimal, and does
not rise to a comment; nothing else surfaced worth recording as a caveat.

`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/`PROJECT_CHECKPOINT.md` synchronization is the
Documentation Manager's next step. This QA review did not merge PR #36, did not authorize or start
`T64`, did not modify source/tests/migrations/governance files, and did not touch the pre-existing
unrelated working-tree items (`docs/prompts/README.md`, `docs/prompts/GitCI_PR_Manager.md`,
`docs/HANDOFF/`).

## Post-Merge Verification — T63 batch (2026-08-16)

Recorded as an append, not a rewrite of the QA Decision above — that section's own account of what
was true at review time (QA Decision committed to the feature branch, PR #36 still open) remains
accurate history and is left untouched.

**`T63`'s QA Decision (commit `6a8608f`, "docs(qa): record T63 approval") was committed and pushed to
`feature/stage3-t63-role-assignment` *before* PR #36 merged** — the deliberate correction of `T62`'s
own named governance finding (merge before a durably-recorded QA Decision). PR #36 subsequently merged
into `main` as `ef419c3` on 2026-08-16, carrying both the implementation commit (`3cea676`) and the
QA-approval commit (`6a8608f`) together, in that order — confirmed directly via `git log --oneline
--decorate`, not assumed.

Independently re-verified this session, directly against the merged repository state (`main` at
`ef419c3`, `origin/main` confirmed identical via `git rev-parse`), not transcribed from the PR body:

- **Scope:** `git diff 97ab953..ef419c3 --name-only` confirms exactly seven files changed in the
  merge — the six originally authorized plus `tests/support/in_memory_user_repository.py` — matching
  the pre-merge QA Decision's own account exactly. No forbidden file (`AuthorizationService`,
  `RbacAuthorizationService`, `PermissiveAuthorizationService`, `CurrentUser`,
  `crud_router_factory.py`, any `alembic/` migration, any frontend file) present in the diff.
- **Lint/format:** `uv run ruff check src tests alembic` — clean. `uv run black --check src tests
  alembic` — clean (199 files unchanged).
- **Boot/route surface:** `python -c "from app.main import app"` succeeds on merged `main`;
  `app.openapi()["paths"]` independently re-confirmed to contain exactly eleven paths:
  `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`,
  `/api/v1/health`, `/api/v1/users`, `/api/v1/users/{user_id}`,
  `/api/v1/users/{user_id}/deactivate`, `/api/v1/users/{user_id}/roles`,
  `/api/v1/users/{user_id}/roles/{role_id}`, `/api/v1/version` — nothing else.
- **Tests:** `uv run pytest -q` — **459 passed, 0 failed, 0 skipped**, personally re-run against live
  Postgres (`legal_dms_postgres` confirmed healthy via `docker ps`) directly on merged `main`, matching
  the pre-merge QA Decision's own figure exactly.

**`T63` is now `Done`** — authorization, implementation, QA Decision, and documentation are all merged
into `main`. Unlike `T62`, this batch's QA Decision was recorded *before* merge, not after — the named
governance finding from `T62`'s own closeout did not recur. `T64`–`T67` remain not started, not
authorized by this verification pass. `docs/prompts/README.md`, `docs/prompts/GitCI_PR_Manager.md`,
and `docs/HANDOFF/` are separate, unrelated, still-uncommitted changes, untouched by this pass.
