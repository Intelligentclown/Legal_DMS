------------------------------------------------

# Stage 3 – Phase 1

Status: In Progress

Started: 2026-08-07

Completed:

Related Tasks: T46

Related ADRs: ADR-0018

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Begin Stage 3 Phase 1 (credentials & token foundation) with `T46` only: add the password-hashing
utility (D2/`ADR-0018` — Argon2id via `argon2-cffi`, already a dependency since `T44`) that `T50`'s
`AuthService` and `T62`'s user-creation route will depend on. No JWT, refresh tokens, `AuthService`,
routes, or DB writes — those are `T47`–`T51`, explicitly not started this batch, per instruction to
implement `T46` only.

## Tasks Implemented

- **T46 — Password hashing utility.** `infrastructure/security/password_hasher.py` (new):
  `hash_password(plain: str) -> str` and `verify_password(plain: str, hashed: str) -> bool`, both
  plain functions (not a port — no caller needs to swap the algorithm behind an interface, and
  `argon2-cffi` is fully encapsulated in this one module), using `argon2.PasswordHasher`.
  `verify_password()` catches `VerifyMismatchError`/`VerificationError`/`InvalidHash` and returns
  `False` rather than letting any of them propagate, so a malformed or tampered hash fails the same
  way a wrong password does, not with an unhandled exception.

## Files Modified

- `backend/src/app/infrastructure/security/password_hasher.py` *(new)*.
- `backend/src/app/infrastructure/security/__init__.py` *(new)* — re-exports `hash_password`/
  `verify_password`, matching the existing `infrastructure/storage/__init__.py` convention.
- `backend/tests/unit/test_password_hasher.py` *(new)*.
- `docs/ImplementationLog/Stage3/Phase1.md` — this file.

No other source file touched — `argon2-cffi` was already a dependency (`T44`), so `pyproject.toml`/
`uv.lock` needed no change.

## Tests Added

All 6 in `backend/tests/unit/test_password_hasher.py`:
1. `TestHashPassword::test_hash_is_never_plaintext_equal_to_input` — the hash is never equal to the
   plaintext input.
2. `TestHashPassword::test_hash_uses_argon2id` — the hash string starts with `$argon2id$`, proving
   D2's chosen variant is actually what's produced, not just "some Argon2 mode."
3. `TestHashPassword::test_hashing_the_same_password_twice_yields_different_hashes` — proves the
   hash is salted (Argon2's per-call random salt), not a deterministic digest.
4. `TestVerifyPassword::test_correct_password_verifies` — the right password against its own hash
   returns `True`.
5. `TestVerifyPassword::test_wrong_password_fails` — a different password against that hash returns
   `False`.
6. `TestVerifyPassword::test_malformed_hash_fails_rather_than_raising` — a garbage string passed as
   the "hash" returns `False` instead of raising `argon2.exceptions.InvalidHash`, proving
   `verify_password()`'s contract holds even for corrupt input, not just the two expected cases.

Matches `T46`'s own acceptance criteria verbatim (`docs/Stage3_Backend_Handoff.md`/
`IMPLEMENTATION_QUEUE.md`: "correct password verifies, wrong password fails, hash is never
plaintext-equal to input") plus two extra tests (Argon2id variant, salting) that came from directly
inspecting what `argon2.PasswordHasher` actually produces rather than only the three named cases.

## Test Results

- New tests: `pytest tests/unit/test_password_hasher.py -v` — **6/6 passing**.
- Full unit suite: `pytest tests/unit -q` — **192 passed** (186 prior + 6 new), 0 failed, 0 skipped.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean.
- **Import/boot smoke test:** `python -c "from app.main import app"` — succeeds (this module isn't
  wired into `main.py`/the DI container yet — plain functions, no port to register — so this only
  confirms the new module doesn't break anything on import path resolution).
- **Not re-verified this batch:** the 112 Postgres-backed integration tests — not touched by this
  change (no DB code), and Docker/Postgres was not confirmed reachable in this session; disclosed
  per this project's own testing-gap convention rather than assumed passing.

## Design Decisions

- **Plain functions, not a port/interface.** `docs/Stage3_Backend_Handoff.md`'s file map specifies
  `hash_password()`/`verify_password()` as functions, not a class implementing an
  `application/interfaces/` ABC — unlike `AuthenticationProvider`/`AuthorizationService`, nothing in
  this stage's approved scope needs to swap the hashing algorithm at runtime or fake it via DI for a
  test (tests call the real functions directly, same as any pure utility). Adding a port here would
  be exactly the kind of speculative abstraction this project's "no speculative abstractions,
  minimal implementation" instruction rules out.
- **`verify_password()` swallows the three argon2-cffi exceptions its own `verify()` call can
  raise**, returning `False` for all of them, rather than letting `InvalidHash`/
  `VerificationError` propagate. A caller (`T50`'s `AuthService.authenticate()`) needs "did this
  password match" as a boolean, not a maze of exception types to handle at the call site — the
  three-way catch keeps that contract simple and matches how `argon2-cffi`'s own docs describe
  `VerifyMismatchError` as the expected-failure case, with the other two as defensive coverage for a
  corrupted/foreign hash string.
- **No `check_needs_rehash()`/rehash-on-login logic.** Argon2 supports detecting when a stored hash
  was made with outdated parameters and re-hashing transparently on next successful login — genuinely
  useful eventually, but nothing in `T46`'s scope needs it yet (no stored hashes exist until `T50`/
  `T62` create some). Not built now; a natural `T50`-or-later addition if it comes up, not deferred
  here as a promise.

## Problems Encountered

None. `argon2-cffi` was already installed and importable (proven by `T44`'s
`TestArgon2CffiIsInstalled` tests in `test_auth_dependencies.py`), so this batch was a
straightforward, single-file addition with no environment surprises.

## Deferred Work

- **`T47`–`T51`** (JWT utility, `Settings` TTL wiring — already done under `T44`, `refresh_tokens`
  migration, `AuthService`, and `AuthService` tests) — explicitly not started, per instruction to
  implement `T46` only.
- **Rehash-on-login** (see Design Decisions) — trigger: if/when `T50`'s `AuthService.authenticate()`
  is implemented and a rehash policy is actually wanted; not a currently-scoped requirement.

## Future Considerations

- `T50`'s `AuthService.authenticate()` and `T62`'s user-creation route are the two consumers this
  utility exists for — both should import `hash_password`/`verify_password` directly from
  `infrastructure.security`, not reach into `argon2` themselves.
- `T47` (JWT utility) is independent of this task and was already noted in
  `IMPLEMENTATION_QUEUE.md`'s "Recommended implementation order" as buildable in either order
  relative to `T46` — nothing here blocks or is blocked by it.

## Reviewer Checklist

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

- **Existing design patterns followed:** matches `docs/Stage3_Backend_Handoff.md`'s own file map for
  `T46` exactly (function names, module path, library choice) — no invented shape.
- **ADR updated (if required):** `□` — correctly not required. `ADR-0018` already records D2
  (Argon2id via `argon2-cffi`) as the approved decision; this batch implements it, it doesn't decide
  anything new. No new ADR needed for "we wrote the function the ADR already specified."
- **AI_BOOTSTRAP updated (if required):** `□` — no non-negotiable rule, required-reading order, or
  standing convention changed.
- **PROJECT_STATE updated (if required):** `☑` — updated as the Documentation Manager step this log
  hands off to below: test count (298 → 304), a new `backendSubsystems` entry for `T46`, and
  `currentStage`/`stages[]` notes reflecting Phase 1's start. A follow-up documentation-sync pass
  (2026-08-07) also corrected `Phase0.md`'s own `Status` field (`In Progress` → `Done`), which had
  lagged behind its blocking sign-off — see that file's Closure note.
- **No scope creep:** implemented exactly `T46` — no JWT, no `AuthService`, no routes, no DB
  writes, matching the explicit "implement T46 only" instruction.
- **Ready for QA:** this log, plus the six named tests and their one-line rationale, are meant to be
  sufficient for a reviewer to verify this batch without asking what happened or why.

## QA Decision

```
QA Decision

☑ Approved
□ Approved with comments
□ Rework required
```

Single-session, playing both roles in sequence per `AI_BOOTSTRAP.md`'s documented allowance.
**Approved:** matches `T46`'s acceptance criteria exactly (correct password verifies, wrong
password fails, hash never plaintext-equal to input), plus two additional tests earned by directly
inspecting the library's actual output (Argon2id variant, per-call salting) rather than stopping at
the three named cases. 192/192 unit tests passing; ruff/black clean; app still boots. No scope
creep — `T47` onward genuinely untouched. Proceeding to documentation synchronization
(`PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, `docs/SessionReport.md`).
