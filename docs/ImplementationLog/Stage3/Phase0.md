------------------------------------------------

# Stage 3 – Phase 0

Status: In Progress

Started: 2026-08-06

Completed:

Related Tasks: T41, T42, T43, T44, T45

Related ADRs: ADR-0019, ADR-0020

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Unblock Stage 3 implementation: synchronize `PROJECT_STATE.json`/`IMPLEMENTATION_QUEUE.md`'s stale
fields with actual repository state (T41), fix `get_db()` so it commits on a successful request and
rolls back on exception instead of silently discarding every write (T42), and prove that fix with
regression tests plus a recorded policy decision (T43) — the hard prerequisite every later Stage 3
phase's writes (users, tokens, role assignments) depend on. **Batch 2:** add the approved
authentication dependencies and configuration (T44), and create the finalized
`AuthenticationProvider` interface per D7 (T45) — foundation only, no login/JWT/hashing/routes/DB
writes. **Batch 3:** a rigorous re-verification pass against a more precise T44/T45
spec (exact dependency/config/interface requirements, an explicit "no framework types in the port"
constraint) — confirmed batch 2's implementation already satisfies it exactly, and closed two
genuine test-coverage gaps (dependency importability, the framework-free-port constraint) rather
than re-implementing anything already correct. **Batch 4 (this update, CI hotfix):** fixed a
CI-only failure in `tests/unit/test_auth.py::TestSettingsAuthConfig::test_jwt_secret_key_has_no_default`
— the test itself was not hermetic against the process environment, not a defect in `Settings` or
the D3 "no default" design. See below.

## ⚠ Task-ID discrepancy (batch 2) — read before trusting "T44"/"T45" elsewhere in this repo

`IMPLEMENTATION_QUEUE.md`'s own Phase 0 table defines **T44 = "Complete
`docs/templates/PreStageChecklist.md`, signed off"** and **T45 = "Write `ADR-0018` and
`ADR-0019`"**. The project owner's batch-2 instruction described completely different content
under those same IDs: "add the approved authentication dependencies and configuration" (T44) and
"create the authentication foundation interfaces... including the finalized
`AuthenticationProvider` interface" (T45). Flagged to the project owner before implementing, per
this project's discrepancy-reporting rule; proceeded on the explicit, detailed instruction given
(the more authoritative source — direct instruction over a static document), and updated
`IMPLEMENTATION_QUEUE.md` to record what actually happened under these IDs. **Net effect: the
*original* T44 (checklist sign-off) and the `ADR-0018` half of the *original* T45 remain not
done** — see Deferred Work.

## ⚠ Reading-list discrepancy (batch 3) — `ADR-0018` does not exist

Batch 3's instruction listed `ADR-0018` as required reading (item 7). Checked `ADR/` directly:
it does not exist — unchanged since the batch-2 discrepancy above (`ADR-0018` was never part of
batch 2's scope, since nothing in that batch manifested D1–D6 in code). Not a new problem, just
re-confirmed rather than silently assumed to exist because it was named in a reading list.

## Tasks Implemented

- **T41 — Documentation synchronization.** (Batch 1 — see below, unchanged.)
- **T42 — Fixed `get_db()`.** (Batch 1 — see below, unchanged.)
- **T43 — Regression tests, `ADR-0020`, commit-contract documentation.** (Batch 1 — see below,
  unchanged.)
- **T44 (batch 2, redefined) — Authentication dependencies & configuration.** Added `argon2-cffi`
  (D2) and `PyJWT` (D3) to `backend/pyproject.toml`'s runtime dependencies, ran `uv lock` (48
  packages resolved, 5 new: `argon2-cffi`, `argon2-cffi-bindings`, `cffi`, `pycparser`, `pyjwt`).
  Extended `Settings` with `jwt_secret_key: str` (**no default**, per D-decision — a signing secret
  must never have a code-level fallback), `jwt_algorithm: str = "HS256"`,
  `access_token_ttl_minutes: int = 20`, `refresh_token_ttl_days: int = 14`. No password hashing or
  JWT encode/decode logic written — only the dependency and its configuration shape.
- **T45 (batch 2, redefined) — Finalized `AuthenticationProvider` interface (D7).**
  `application/interfaces/auth.py`: `AuthenticationProvider.get_current_user()` now takes an
  explicit `token: str | None` parameter — the exact approved D7 signature, a genuine breaking
  change to an existing Stage 1 port. Cascaded to both existing callers so nothing was left broken:
  `AnonymousAuthenticationProvider` now accepts-and-ignores `token`;
  `presentation/api/deps.py`'s `get_current_user()` wrapper now calls
  `auth_provider.get_current_user(token=None)` as an explicit, documented Phase-0 placeholder
  (real bearer-token extraction is `T56`, Phase 2). Wrote `ADR/0019-authentication-provider-interface-change.md`
  recording this decision — not explicitly requested by name in the batch-2 instruction, but
  required by this project's own "every significant architectural decision gets an ADR" rule for a
  breaking port change.

- **Batch 3 — Re-verification against a precise T44/T45 spec.** Read all nine required documents
  fresh (including re-confirming `ADR-0018`'s non-existence). Directly re-read
  `application/interfaces/auth.py`, `anonymous_auth_provider.py`, `presentation/api/deps.py`, and
  `settings.py` against the new instruction's exact requirements (dependency list, `Settings`
  fields, the literal `get_current_user(token: str | None)` signature, "keep framework types
  outside the port") — confirmed batch 2 already satisfies every one of them exactly, no code
  changes needed. Reviewed T41–T43 (`session.py`, `ADR-0020`, the regression test file) for
  critical defects — found none, left unmodified per instruction. Closed two test-coverage gaps
  instead of re-implementing anything (see Tests Added).

Explicitly **not** done, per instruction ("stop after T45"): Phase 1 onward (`T46`+); the
*original* T44/T45 content (`PreStageChecklist` sign-off, `ADR-0018`) — see the discrepancy note
above and Deferred Work.

- **Batch 4 — CI hotfix.** GitHub Actions' `backend.yml` job reported
  `tests/unit/test_auth.py::TestSettingsAuthConfig::test_jwt_secret_key_has_no_default` failing:
  `Settings()` constructed without raising `ValidationError` even though `jwt_secret_key` has no
  default. Root cause: `.github/workflows/backend.yml` sets a job-level `JWT_SECRET_KEY` env var
  (added in batch 2, `ci-only-fake-secret-not-used-for-anything-real`) so the rest of the suite and
  the import-smoke step can construct `Settings()`. That env var is visible to every step in the
  job, including this test. The test called `Settings(_env_file=None)`, but `_env_file=None` only
  suppresses `pydantic-settings`' `.env`-file source — it does **not** suppress the OS-environment
  source, so in CI the field resolved from `os.environ["JWT_SECRET_KEY"]` and validation correctly
  succeeded (no bug in `Settings`). Locally this passed only because the developer's shell has no
  `JWT_SECRET_KEY` exported (only the gitignored `.env` file does, correctly bypassed by
  `_env_file=None`). Confirmed by reproducing locally with `JWT_SECRET_KEY=<value>` set in the
  process environment — the test failed identically outside CI, proving it was an environment
  condition, not a CI-specific fluke. Fixed by making the test explicitly hermetic:
  `monkeypatch.delenv("JWT_SECRET_KEY", raising=False)` before constructing `Settings(_env_file=None)`,
  so the test's outcome no longer depends on what the ambient process environment happens to
  contain. `Settings.jwt_secret_key`'s "no code-level default" behavior itself was not touched —
  confirmed still correct, matching D3/`docs/Stage3_Backend_Handoff.md` §6 and
  `docs/ImplementationLog/Stage3/Phase0.md`'s own batch-2 record.

## Files Modified

**Batch 1 (T41–T43):**
- `backend/src/app/infrastructure/database/session.py`, `backend/tests/integration/test_get_db_transaction_policy.py` *(new)*,
  `ADR/0020-session-commit-rollback-policy.md` *(new)*, `docs/Architecture.md`, `docs/AI_HANDOVER.md`,
  `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`.

**Batch 2 (T44–T45):**
- `backend/pyproject.toml` — two new runtime dependencies.
- `backend/uv.lock` — relocked (5 new packages).
- `backend/src/app/infrastructure/config/settings.py` — four new fields.
- `backend/.env.example` — `JWT_SECRET_KEY`/`JWT_ALGORITHM`/`ACCESS_TOKEN_TTL_MINUTES`/`REFRESH_TOKEN_TTL_DAYS`
  documented with placeholder/default values, never a real secret.
- `backend/.env` *(gitignored, not committed)* — local-dev-only `JWT_SECRET_KEY` so local test runs
  construct `Settings()` successfully.
- `.github/workflows/backend.yml` — job-level `JWT_SECRET_KEY` env var (explicitly fake, CI-only),
  otherwise every unit test and the import-smoke step would fail to construct `Settings()`. See
  Design Decisions.
- `backend/src/app/application/interfaces/auth.py` — `AuthenticationProvider.get_current_user()`
  signature change (D7) + docstring.
- `backend/src/app/infrastructure/auth/anonymous_auth_provider.py` — updated to match.
- `backend/src/app/presentation/api/deps.py` — `get_current_user()` wrapper updated to match
  (`token=None` placeholder).
- `backend/tests/unit/test_auth.py` — fixed the one test broken by the signature change, added 5
  new tests (see Tests Added).
- `backend/tests/unit/test_example.py`, `backend/tests/unit/test_feature_flags.py` — every
  `Settings(_env_file=None, ...)` call site updated to also pass `jwt_secret_key="test-secret"`
  (now a required field).
- `ADR/0019-authentication-provider-interface-change.md` *(new)*.
- `docs/ImplementationLog/Stage3/Phase0.md` — this file.
- `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `docs/SessionReport.md` — updated to close this
  batch out (see those files directly for exact diffs).

**Batch 3 (re-verification):**
- `backend/tests/unit/test_auth.py` — added `TestAuthenticationProviderPortHasNoFrameworkImports`
  (1 test).
- `backend/tests/unit/test_auth_dependencies.py` *(new)* — 4 tests.
- `docs/ImplementationLog/Stage3/Phase0.md` — this file.
- `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `docs/SessionReport.md` — updated to close this
  batch out.
- No source (non-test) files changed — batch 2's implementation already matched the precise spec
  exactly.

**Batch 4 (CI hotfix):**
- `backend/tests/unit/test_auth.py` — `TestSettingsAuthConfig::test_jwt_secret_key_has_no_default`
  modified to accept `monkeypatch: pytest.MonkeyPatch` and call
  `monkeypatch.delenv("JWT_SECRET_KEY", raising=False)` before constructing `Settings(_env_file=None)`.
- `docs/ImplementationLog/Stage3/Phase0.md` — this file.
- `docs/SessionReport.md` — new session entry.
- No source (non-test) files changed — `Settings.jwt_secret_key` was already correct; only the
  test's isolation was fixed. `PROJECT_STATE.json` not touched — test count and stage status are
  unchanged by this hotfix.

## Tests Added

**Batch 1:** 5 tests in `test_get_db_transaction_policy.py` (see prior entry below, unchanged).

**Batch 2:** 6 new tests, all in `backend/tests/unit/test_auth.py` except where noted:
1. `TestAuthenticationProviderSignature::test_a_conforming_implementation_accepts_a_token_argument` —
   a minimal fake `AuthenticationProvider` subclass proves the port's new signature is usable and
   the `token` value can actually influence the result, independent of any real implementation.
2. `TestAnonymousAuthenticationProvider::test_returns_an_anonymous_current_user_with_no_token` —
   the existing test, updated to pass `None` explicitly (was previously the no-arg call).
3. `TestAnonymousAuthenticationProvider::test_ignores_a_present_token_and_still_returns_anonymous` —
   new: proves the stub doesn't pretend to validate a token it has no way to check.
4. `TestSettingsAuthConfig::test_jwt_secret_key_has_no_default` — constructing `Settings()` without
   it raises `pydantic.ValidationError`.
5. `TestSettingsAuthConfig::test_jwt_secret_key_is_accepted_when_provided`,
   `test_algorithm_and_ttl_fields_have_sensible_defaults`, `test_ttl_fields_are_overridable` — the
   new config fields' shape and defaults.

**Batch 3:** 5 new tests, closing two coverage gaps the new precise spec's explicit requirements
exposed:
1. `TestAuthenticationProviderPortHasNoFrameworkImports::test_the_port_module_imports_nothing_from_fastapi`
   (`test_auth.py`) — an AST-based static check (not a runtime behavior test) that
   `application/interfaces/auth.py` imports nothing from `fastapi`. Directly verifies "keep
   framework types outside the port," and catches a future edit that violates it regardless of
   whether any other test happens to exercise that import path.
2. `TestArgon2CffiIsInstalled` (2 tests, `test_auth_dependencies.py`) — `argon2.PasswordHasher` and
   `argon2.exceptions.VerifyMismatchError` are importable. Proves T44's dependency addition is real
   and usable without hashing anything (that's `T46`).
3. `TestPyJWTIsInstalled` (2 tests, `test_auth_dependencies.py`) — `jwt.encode`/`jwt.decode` and the
   `ExpiredSignatureError`/`InvalidSignatureError` exceptions are importable. Proves T44's other
   dependency addition without encoding/decoding a token (that's `T47`).

**Batch 4 (CI hotfix):** No new tests — one existing test modified for hermeticity (see Files
Modified). Test count is unchanged (298 before and after).

## Test Results

**Batch 1:** 287 passed (282 existing + 5 new) — see prior entry below.

**Batch 2:**
- New/modified tests: all passing (`pytest tests/unit/test_auth.py tests/unit/test_example.py
  tests/unit/test_feature_flags.py -v` — 29/29).
- **Full backend suite: 293 passed** (287 prior + 6 net new), 0 failed, 0 skipped.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean (one
  `E501` line-length finding in the reformatted feature-flags test, fixed via `black` itself).
- **Import/boot smoke test:** `python -c "from app.main import app; ..."` — succeeds, confirming
  `Settings()` construction (with the new required field) and the whole DI/health-check startup
  path still work end to end.
- Postgres was reachable throughout (not that this batch needed it — no DB-touching code was
  added).

**Batch 3:**
- New tests: `pytest tests/unit/test_auth.py tests/unit/test_auth_dependencies.py -v` — 17/17
  passing.
- **Full backend suite: 298 passed** (293 prior + 5 net new), 0 failed, 0 skipped.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean, no
  findings this time.
- **Import/boot smoke test:** re-verified, succeeds.
- No T41–T43 files were touched, so no re-verification of `get_db()`'s own behavior was needed
  beyond confirming its existing tests still pass as part of the full-suite run.

**Batch 4 (CI hotfix):**
- Reproduced the CI failure locally first: `JWT_SECRET_KEY=<value> uv run python -c
  "from app.infrastructure.config.settings import Settings; Settings(_env_file=None)"` constructed
  successfully (no `ValidationError`) with the env var set, matching the CI failure exactly.
- `pytest tests/unit/test_auth.py -v` — 13/13 passing (including the fixed test, run under the
  developer's normal shell with no `JWT_SECRET_KEY` set).
- `pytest tests/unit/test_auth.py::TestSettingsAuthConfig -v` re-run with
  `JWT_SECRET_KEY=ci-only-fake-secret-not-used-for-anything-real` explicitly set in the process
  environment (reproducing the exact CI condition) — 4/4 passing, confirming the fix holds under
  the condition that broke CI, not just in the developer's own shell.
- **Full backend suite: 298 passed** (unchanged — no test added, one fixed), 0 failed, 0 skipped.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean.

## Design Decisions

**Batch 1:** see prior entry below (get_db() commits, not each repository method; `except
Exception` not `BaseException`; regression tests drive `get_db()` directly).

**Batch 2:**
- **`jwt_secret_key` has no code-level default, but CI/local dev both need *a* value.** Resolved by
  injecting an explicitly-fake value via `.github/workflows/backend.yml`'s job `env:` block (CI)
  and the gitignored local `backend/.env` (dev) — never a Pydantic field default. This preserves
  the actual security property the architecture review wanted (a real deployment can't accidentally
  run with a baked-in secret) while keeping the existing "zero .env/secrets needed for CI" invariant
  from breaking outright — it now needs exactly one, explicitly fake, clearly-labeled value.
- **`deps.py`'s `get_current_user()` passes `token=None` unconditionally**, not real header
  extraction. This is `T56`'s job (Phase 2), explicitly out of scope here ("do not implement API
  routes" — token extraction from the request is request-handling logic, not a port/interface).
  Documented as a placeholder in both the code comment and `ADR-0019`, not left silent.
  `AnonymousAuthenticationProvider` ignoring the value either way means behavior is externally
  identical to before this change — zero regression risk from the placeholder.
- **`ADR-0019` written even though not explicitly named in the batch-2 instruction.** A breaking
  port signature change is exactly what this project's "every significant architectural decision
  gets an ADR" rule exists for — treated as implied by "create the finalized interface," not
  optional. `ADR-0018` (the broader D1–D6 record) was *not* written, since nothing in this batch
  manifests D1/D4/D5/D6 in code, and `ADR-0018` was never part of the batch-2 description.

**Batch 3:**
- **Verify-then-close-gaps, not reimplement.** Given batch 2 already matched the new, more precise
  spec exactly on direct inspection, the choice was between (a) leaving the phase log as-is with a
  note saying "already done," or (b) using the spec's extra precision (the explicit "no framework
  types in the port" line, the exhaustive dependency list) to find and close genuine test-coverage
  gaps. Chose (b) — the two new test files/additions have real, independent value (they'd catch a
  future regression the batch-2 tests wouldn't), so treating this as "nothing to do" would have
  wasted the more rigorous spec's actual signal.
- **No new ADR.** Nothing architecturally new was decided this batch — only test coverage was
  added against an already-recorded decision (`ADR-0019`). Writing a new ADR for "we added tests"
  would misuse the ADR mechanism.

**Batch 4 (CI hotfix):**
- **Fixed the test's isolation, not `Settings`.** The failure was diagnosed as a test-hermeticity
  bug, not an architecture or implementation defect: `jwt_secret_key: str` having no code-level
  default is exactly the approved D3/D-decision design
  (`docs/Stage3_Backend_Handoff.md` §6, "no default at all for the actual signing secret"), and it
  still has none after this fix. The only thing that changed is that the test no longer trusts
  `_env_file=None` to mean "no env source at all" — it explicitly clears the one OS-level env var
  (`JWT_SECRET_KEY`) that CI legitimately sets for unrelated reasons (letting the rest of the suite
  and the import-smoke step construct `Settings()`), via `monkeypatch.delenv(..., raising=False)`.
  `monkeypatch` is pytest's own fixture for exactly this — scoped to the single test, restored
  automatically afterward, no risk of leaking into other tests.
- **No new ADR.** This is a test-hermeticity bug fix, not an architectural decision — nothing about
  `Settings`, the D1–D7 decisions, or `ADR-0019`/`ADR-0020` changed.
- **Did not widen the CI env var removal, touch `.github/workflows/backend.yml`, or change any
  other `Settings(_env_file=None, ...)` call site.** The other call sites
  (`test_example.py`, `test_feature_flags.py`, and this file's own other three
  `TestSettingsAuthConfig` tests) all pass `jwt_secret_key="test-secret"` explicitly, so an ambient
  `JWT_SECRET_KEY` env var can't change their outcome — only the one test asserting *absence* was
  actually exposed to this class of bug.

## Problems Encountered

**Batch 1:** see prior entry below (`get_engine()` lru_cache vs. per-test event loops).

**Batch 2:**
- **The `jwt_secret_key` "no default" requirement cascaded further than expected.** Adding a
  required `Settings` field broke: (a) CI's unit-test and import-smoke steps (no env var set), (b)
  every existing test that constructs `Settings(_env_file=None, ...)` directly (10 call sites
  across `test_example.py` and `test_feature_flags.py`), and (c) local test runs (until the
  gitignored `.env` got the new key). All three fixed (CI env var, per-call-site
  `jwt_secret_key="test-secret"`, local `.env` addition) and re-verified — full suite green
  afterward.
- **The `AuthenticationProvider` signature change broke exactly one existing test**
  (`AnonymousAuthenticationProvider().get_current_user()` called with no args) — caught immediately
  by running `test_auth.py` right after the interface edit, before touching anything else. Fixed
  and extended with the new coverage described above.

**Batch 3:** None. Verification confirmed batch 2's implementation, no defects found in T41–T43,
and both new test additions passed on the first attempt.

**Batch 4 (CI hotfix):** The test passed locally in every prior batch and only failed in GitHub
Actions specifically, because only the CI job's `backend.yml` sets a job-level `JWT_SECRET_KEY` env
var — no local developer shell has that set. This made the bug invisible to `uv run pytest` on a
normal developer machine and visible only in CI, which is exactly why it wasn't caught in batches
2/3 despite the test having been written and reviewed twice already. Resolved by reproducing the
exact CI condition locally (setting `JWT_SECRET_KEY` in the shell before invoking pytest) before
writing the fix, then re-confirming the fix under that same reproduced condition — not just
re-running the test in its normal (bug-masking) local environment.

## Deferred Work

**Carried from batch 1:** widening `get_db()`'s `except Exception` to `BaseException`; the
`role_permissions` exact matrix (T66) sign-off. Both unchanged — see prior entry below.

**New from batch 2:**
- **The *original* T44 (`docs/templates/PreStageChecklist.md` sign-off) remains not done.** The ID
  was reused for different content this batch per direct instruction — the checklist itself still
  needs to be filled in and signed off at some point before Stage 3 is considered to have passed
  this project's own required pre-stage gate. Needs a decision on how to track it now that its
  original ID is spent (a new ID, or restore it once T44's redefinition is reconciled).
- **The *original* T45's `ADR-0018` half (Authentication & Authorization Architecture, D1–D6)
  remains not written.** Only `ADR-0019` (D7 specifically) was produced this batch. Same
  ID-reconciliation question as above.
- **`T56`** must replace `deps.py`'s hardcoded `token=None` with real bearer-token extraction from
  the request — named explicitly in `ADR-0019` so it isn't silently forgotten once Phase 2 starts.
- Phase 1 onward (`T46`+: password hashing utility, JWT encode/decode utility, `refresh_tokens`
  migration, `AuthService`) — awaits a further explicit go-ahead, per instruction to stop after T45.

**New from batch 3:** None beyond what batch 2 already deferred — this batch was verification and
test-coverage only, it found no new work to defer.

**New from batch 4:** None. This was a self-contained hotfix with no follow-on work identified —
the one other place an ambient-env-var assumption could theoretically bite (a hypothetical future
test asserting absence of some other required setting) doesn't exist yet, so there's nothing
concrete to defer against.

## Future Considerations

**Carried from batch 1:** every later Stage 3 write depends on the `get_db()` fix; read `ADR-0020`
before touching session/transaction code again.

**New from batch 2:**
- Whoever picks up Phase 1 should read `ADR-0019` before implementing `JwtAuthenticationProvider`
  (`T52`) — the port contract (`token=None` → anonymous, never raise) is already fixed; `T52` fills
  in real decoding, it doesn't get to redesign the signature.
- The task-ID discrepancy flagged above should be resolved explicitly with the project owner before
  Phase 1 numbering is trusted blindly — either by renumbering, or by confirming the original
  T44/T45 content should be picked up under new IDs.
- `jwt_secret_key`'s CI/local-dev fake values are clearly labeled as such in both places
  (`ci-only-fake-secret-not-used-for-anything-real`, `local-dev-only-not-a-real-secret-...`) —
  worth a final grep-for-real-secret sanity check before this project ever actually deploys, so
  neither placeholder is mistaken for a real one.

**New from batch 3:**
- This phase log's Status stays `In Progress`, not `Done`, even though T41–T45 are all complete —
  `IMPLEMENTATION_QUEUE.md`'s own Phase 0 acceptance criteria (separate from the task table)
  explicitly requires the `PreStageChecklist.md` sign-off, which remains open. Don't mark this
  phase `Done` until that's resolved one way or another, even if every task ID shows complete.
- The two new test files establish a pattern worth reusing in Phase 1: an explicit "no framework
  types in this port" AST check, and "is the dependency actually importable" checks, both cheap and
  high-signal for exactly the kind of drift that's easy to introduce silently later.

**New from batch 4:**
- **General lesson for Phase 1+:** any future test asserting "a required `Settings` field has no
  usable value" must explicitly clear the relevant env var(s) via `monkeypatch.delenv(...)` rather
  than relying on `Settings(_env_file=None)` alone — that argument only suppresses the `.env`-file
  source, not the OS-environment source, and this project's CI already sets at least one
  required-field env var (`JWT_SECRET_KEY`) at job level for unrelated reasons. Worth keeping in
  mind if/when `T47`'s token utility or any later required config field grows its own
  "has no default" test.
- This phase log's Status remains `In Progress`, unchanged by this hotfix — the open
  `PreStageChecklist.md`/`ADR-0018` items are still what's blocking `Done`, not anything this batch
  touched.

---

## Appendix: Batch 1 (T41–T43) full original entries

### Tasks Implemented (batch 1)

- **T41 — Documentation synchronization.** Verified the discrepancy `IMPLEMENTATION_QUEUE.md`
  itself flagged: `git log`/`git branch`/`git tag` showed branch `main`, merge commit `2db48d4`,
  tags `v0.3.0`/`v0.3.1` — but `PROJECT_STATE.json` still said `currentStage: stage-2`,
  `git.branch: feature/github-actions-ci`, and carried a resolved `openQuestion` about T35. Synced
  `PROJECT_STATE.json` (`currentStage` → stage-3/in_progress, `stages[].stage-3`, `completion`,
  `openQuestions`, `git` block) and `IMPLEMENTATION_QUEUE.md` (marked its own "Discrepancy found"
  note resolved, updated the Stage 3 status header) to match reality.
- **T42 — Fixed `get_db()`.** `backend/src/app/infrastructure/database/session.py`: wrapped the
  dependency's `yield` in `try`/`except` — commits on clean exit, rolls back and re-raises on any
  `Exception`, before the session closes.
- **T43 — Regression tests, `ADR-0020`, and the commit-contract documentation note.** Added 5
  integration tests proving the fix; wrote `ADR/0020-session-commit-rollback-policy.md`; updated
  `docs/Architecture.md`'s session-plumbing note and `docs/AI_HANDOVER.md`'s "patterns worth
  knowing" list (entry #10).

### Tests Added (batch 1)

All 5 in `backend/tests/integration/test_get_db_transaction_policy.py`: durable commit visible from
a second independent session; rollback on exception (write absent when read independently); the
original exception (not a broken-rollback artifact) propagates; pre-existing same-session
`flush()`-visibility unchanged; a read-only session still completes cleanly.

### Test Results (batch 1)

5/5 new tests passing; sanity-checked non-vacuous by temporarily reverting the fix (one test failed
as expected, four passed vacuously) and restoring it. Full suite: 287 passed (282 + 5). Lint clean.

### Design Decisions (batch 1)

`get_db()` commits (not each repository method, not a request-scoped `UnitOfWork`) — full reasoning
in `ADR-0020`. `except Exception`, not `BaseException`, deliberately kept minimal — widening is a
named follow-up, not applied silently. Regression tests drive `get_db()`'s generator directly
(`anext()`/`athrow()`), the only way to test both the commit and rollback paths deterministically.

### Problems Encountered (batch 1)

`get_engine()`'s `lru_cache` singleton doesn't survive across pytest-asyncio's per-test event
loops — resolved by having the test fixture call `get_engine.cache_clear()` before/after each test.

### Deferred Work (batch 1)

Widening `get_db()` to `except BaseException` (trigger: once Stage 3 routes exist and cancellation
under real load is worth testing). The *original* T44 (`PreStageChecklist` sign-off) and T45
(`ADR-0018`/`ADR-0019`) — at the time batch 1 was written, both were simply "not yet done"; batch 2
above is where the ID-reuse discrepancy actually surfaced.

### Future Considerations (batch 1)

Every later Stage 3 write sits on a `get_db()` that now actually persists. The `role_permissions`
exact matrix (T66) still needs explicit sign-off before that migration is written.

---

## Reviewer Checklist

Self-assessed for Phase 0 as a whole (T41–T45, four batches — batch 4 a CI hotfix, no new task ID),
updated to this project's current eleven-item standard (matured after batch 2 was first written —
see `docs/ImplementationLog/README.md`; the original eight-item self-assessment from batch 2 is
superseded by this one, not kept alongside it, per the "phase log is authoritative for its own
technical facts" rule).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
☑ ADR updated (if required)
☑ AI_BOOTSTRAP updated (if required)
☑ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

Notes on the less-obvious ones:

- **Existing design patterns followed:** `AuthenticationProvider` stayed a plain ABC in
  `application/interfaces/` with one default implementation in `infrastructure/auth/`, registered
  via the existing `container.register(...)` line — the same port/implementation/registration shape
  `docs/Stage3_Backend_Handoff.md` names Command Bus as the template for. No new abstraction was
  introduced (batch 3 added tests only, not new code shapes).
- **ADR updated (if required):** `ADR-0019` (D7) and `ADR-0020` (session commit/rollback) cover the
  two decisions actually made in code across all three batches. `ADR-0018` (the broader D1–D6
  record) was *not* written — checked `☑` anyway because nothing across any batch manifested
  D1/D4/D5/D6 in code, so `ADR-0018` was never actually required by this phase's own changes; it
  remains a separately tracked open item (see Deferred Work), not a gap in this box.
- **AI_BOOTSTRAP updated (if required):** checked `□` would also have been defensible, but `☑`
  because batch 1 didn't need it and batches 2–3 didn't either — no non-negotiable rule, required-
  reading order, or standing convention changed as a result of this phase's own work (the
  Reviewer-Checklist/QA-Decision convention itself was a separate, later process change, not
  something this phase's T41–T45 work caused).
- **PROJECT_STATE updated (if required):** `☑` — `currentStage`, test counts, `completion`,
  `openQuestions`, and the ADR list were all updated across the three batches as they changed.
- **No scope creep:** the CI workflow env-var addition, the `.env`/`.env.example` updates, and
  `ADR-0019` itself (batch 2) weren't named explicitly in their instruction — checked `☑` because
  all three were disclosed, necessary, mechanical consequences of what *was* asked. Batch 3's two
  new test files weren't named explicitly either, but directly verify requirements the batch-3
  instruction *did* state explicitly ("keep framework types outside the port," the exact dependency
  list) — closing a proof gap for a stated requirement, not adding an unstated one.
- **Ready for QA:** this log plus `ADR-0019`/`ADR-0020` are meant to be sufficient for a reviewer to
  verify all of Phase 0 without needing to ask what happened or why.
- **Tests added (batch 4):** no new test was added — the one existing test with a hermeticity gap
  was fixed in place. Checked `☑` for the phase as a whole since batches 1–3 did add real coverage
  for their own new behavior; batch 4's fix is recorded distinctly in Problems
  Encountered/Design Decisions rather than claimed as "new coverage."

## QA Decision

```
QA Decision

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered in the same pass as the Reviewer Checklist above (single-session, playing both roles in
sequence per `AI_BOOTSTRAP.md`'s documented allowance). **Approved:** T41–T45 all verified against
their respective specs (T41–T43 by review, no defect found, left unmodified; T44–T45 by direct
re-inspection against a precise, exhaustive spec, confirmed already-correct); 298/298 tests
passing; ruff/black clean; app boots. The only open items (`PreStageChecklist.md` sign-off,
`ADR-0018`) are explicitly tracked as deferred, not silently dropped, and don't block this batch's
own correctness. Proceeding to documentation synchronization (`PROJECT_STATE.json`,
`docs/SessionReport.md`) per the Documentation Manager step below.

### QA Decision — Batch 4 (CI hotfix)

```
QA Decision (batch 4)

☑ Approved
□ Approved with comments
□ Rework required
```

**Approved.** Root cause correctly isolated to test hermeticity, not `Settings`/architecture — the
D3 "`jwt_secret_key` has no code-level default" design remains exactly as approved and unchanged by
this fix. Fix is minimal (one test method, one `monkeypatch.delenv` call), verified both in a normal
local shell and under the exact CI condition that caused the failure (reproduced by setting
`JWT_SECRET_KEY` in the process environment before re-running the test). Full backend suite:
298/298 passing (unchanged count); ruff/black clean. No unrelated files touched. This phase log's
Status correctly remains `In Progress` — this hotfix doesn't resolve the still-open
`PreStageChecklist.md`/`ADR-0018` items blocking `Done`.
