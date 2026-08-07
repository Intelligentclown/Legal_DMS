------------------------------------------------

# Stage 3 – Phase 1

Status: In Progress

Started: 2026-08-07

Completed:

Related Tasks: T46, T47

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
implement `T46` only. **T47 batch (this update):** add the JWT encode/decode token utility (D3/
`ADR-0018` — PyJWT, already a dependency since `T44`) that `T50`'s `AuthService` and `T52`'s
`JwtAuthenticationProvider` will depend on. Still no `AuthService`, refresh-token migration, routes,
or DB writes — those remain `T49`–`T51`+, per instruction to implement `T47` only.

## Tasks Implemented

- **T46 — Password hashing utility.** `infrastructure/security/password_hasher.py` (new):
  `hash_password(plain: str) -> str` and `verify_password(plain: str, hashed: str) -> bool`, both
  plain functions (not a port — no caller needs to swap the algorithm behind an interface, and
  `argon2-cffi` is fully encapsulated in this one module), using `argon2.PasswordHasher`.
  `verify_password()` catches `VerifyMismatchError`/`VerificationError`/`InvalidHash` and returns
  `False` rather than letting any of them propagate, so a malformed or tampered hash fails the same
  way a wrong password does, not with an unhandled exception.
- **T47 — JWT encode/decode utility.** `infrastructure/security/jwt_service.py` (new):
  `create_access_token(user_id, roles, settings) -> str`, `create_refresh_token(user_id, settings)
  -> str`, and `decode_token(token, settings) -> dict | None`, using `jwt.encode`/`jwt.decode`
  (PyJWT). Access tokens carry `sub`/`roles`/`exp`/`jti`; refresh tokens carry `sub`/`exp`/`jti`
  (no `roles` — a refresh only needs to prove identity; the reissued access token's roles come from
  a fresh DB lookup at `T50`/`T52`, not from data carried in the old refresh token).
  `decode_token()` catches `jwt.PyJWTError` (the base class covering
  `ExpiredSignatureError`/`InvalidSignatureError`/`DecodeError`/every other PyJWT failure mode) and
  returns `None` rather than propagating, mirroring `T46`'s `verify_password()` contract shape.
  Both TTLs and the signing secret/algorithm are read from the `Settings` instance passed in — never
  hardcoded.

## Files Modified

- `backend/src/app/infrastructure/security/password_hasher.py` *(new)*.
- `backend/src/app/infrastructure/security/__init__.py` *(new)* — re-exports `hash_password`/
  `verify_password`, matching the existing `infrastructure/storage/__init__.py` convention.
- `backend/tests/unit/test_password_hasher.py` *(new)*.
- `docs/ImplementationLog/Stage3/Phase1.md` — this file.

No other source file touched — `argon2-cffi` was already a dependency (`T44`), so `pyproject.toml`/
`uv.lock` needed no change.

**T47 batch:**
- `backend/src/app/infrastructure/security/jwt_service.py` *(new)*.
- `backend/src/app/infrastructure/security/__init__.py` — extended to also re-export
  `create_access_token`/`create_refresh_token`/`decode_token`.
- `backend/tests/unit/test_jwt_service.py` *(new)*.
- `docs/ImplementationLog/Stage3/Phase1.md` — this file.

No other source file touched — `PyJWT` was already a dependency (`T44`), so `pyproject.toml`/
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

**T47 batch:** 9 in `backend/tests/unit/test_jwt_service.py`:
1. `TestCreateAccessToken::test_round_trips_sub_and_roles` — encode then decode returns the same
   `sub`/`roles`.
2. `TestCreateAccessToken::test_has_a_jti_claim_unique_per_token` — two tokens for the same user get
   different `jti` values.
3. `TestCreateRefreshToken::test_round_trips_sub` — encode then decode returns the same `sub`, with
   a `jti` present.
4. `TestDecodeToken::test_expired_access_token_is_rejected` — an access token created with a
   negative TTL (already-past `exp`) decodes to `None`.
5. `TestDecodeToken::test_expired_refresh_token_is_rejected` — same, for a refresh token.
6. `TestDecodeToken::test_tampered_signature_is_rejected` — flipping one character of a valid
   token's signature segment makes it decode to `None`.
7. `TestDecodeToken::test_token_signed_with_a_different_secret_is_rejected` — a token signed with a
   different `jwt_secret_key` fails to decode against the real one.
8. `TestDecodeToken::test_malformed_token_is_rejected` — an arbitrary non-JWT string decodes to
   `None` instead of raising.
9. `TestDecodeToken::test_does_not_leak_the_underlying_pyjwt_exception` — explicitly asserts
   `decode_token()` never lets a `jwt.PyJWTError` escape for the malformed-input case, not just that
   it happens to return the right value.

Matches `T47`'s own acceptance criteria verbatim (`IMPLEMENTATION_QUEUE.md`: "round-trip, expired
token rejected, tampered signature rejected") plus tests earned by inspecting the actual failure
modes `decode_token()` must cover (wrong secret, malformed input, jti uniqueness, and both token
kinds' expiry) rather than stopping at the three named cases — same "close real coverage gaps, not
just the letter of the spec" approach `T46` and Stage 3 Phase 0's batch 3 already established.

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

**T47 batch:**
- New tests: `pytest tests/unit/test_jwt_service.py -v` — **9/9 passing**.
- Full unit suite: `pytest tests/unit -q` — **201 passed** (192 prior + 9 new), 0 failed, 0 skipped.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean (one
  formatting fix needed in the new test file, applied via `black` itself, then re-verified clean).
- **Import/boot smoke test:** `python -c "from app.main import app"` — succeeds; same caveat as
  `T46` — this module isn't wired into `main.py`/the DI container (plain functions, no port).
- **Not re-verified this batch:** same as `T46` — the 112 integration tests, for the same reason
  (no DB code touched, Docker/Postgres unreachable in this environment).

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

**T47 batch:**
- **Plain functions again, not a port/interface** — same reasoning as `T46`: `docs/
  Stage3_Backend_Handoff.md`'s file map describes "encode/decode functions or a small class," and
  nothing in this stage's approved scope needs to swap the JWT library behind an interface at
  runtime.
- **`Settings` passed explicitly as a parameter, not resolved internally via `get_settings()`.**
  Keeps the functions pure and trivially testable — tests construct a throwaway `Settings(
  _env_file=None, jwt_secret_key=...)` directly, the same pattern `test_auth.py`'s
  `TestSettingsAuthConfig` already established, rather than needing to patch a module-level
  singleton to exercise expiry/wrong-secret cases.
- **Refresh tokens omit the `roles` claim.** `T47`'s own acceptance-criteria text lists `sub`/
  `roles`/`exp`/`jti` as the claim set across "access & refresh tokens" collectively, not a
  requirement that every claim appears in every token type. A refresh token's only job is proving
  "this is still a valid, unrevoked session for this user" — `T50`/`T52` re-derive current roles
  from the database at the point a new access token is actually issued, so carrying possibly-stale
  roles in the refresh token would be dead data at best and a staleness bug at worst (a role
  revoked mid-session would still appear in an old refresh token's claims, though not in
  practice used for authorization anywhere, since nothing reads roles off a refresh token).
- **`decode_token()` catches `jwt.PyJWTError` (the base class), not each subclass individually** —
  `ExpiredSignatureError`/`InvalidSignatureError`/`DecodeError`/`InvalidTokenError` etc. all inherit
  from it, and `T47`'s contract ("expired token rejected, tampered signature rejected") doesn't
  need the caller to distinguish *why* a token failed, only *that* it did — mirrors `T46`'s
  `verify_password()` boolean-outcome shape at the exception-handling level, generalized to "catch
  the one base class that covers every real failure mode this library defines" rather than
  enumerating them.

## Problems Encountered

None. `argon2-cffi` was already installed and importable (proven by `T44`'s
`TestArgon2CffiIsInstalled` tests in `test_auth_dependencies.py`), so this batch was a
straightforward, single-file addition with no environment surprises.

**T47 batch:** One test needed a `black` reformat after first being written (line-wrapping only, no
logic change) — caught and fixed by the normal lint step before considering the batch done, not a
functional problem.

## Deferred Work

- **`T47`–`T51`** (JWT utility, `Settings` TTL wiring — already done under `T44`, `refresh_tokens`
  migration, `AuthService`, and `AuthService` tests) — explicitly not started, per instruction to
  implement `T46` only.
- **Rehash-on-login** (see Design Decisions) — trigger: if/when `T50`'s `AuthService.authenticate()`
  is implemented and a rehash policy is actually wanted; not a currently-scoped requirement.

**T47 batch:**
- **`T48`** (Extend `Settings` with auth config) — already satisfied by `T44`'s redefined scope
  (`jwt_secret_key`/`jwt_algorithm`/`access_token_ttl_minutes`/`refresh_token_ttl_days` all exist),
  confirmed again while building `T47` since this batch is the first real consumer of those fields.
  Its `IMPLEMENTATION_QUEUE.md` row is still unmarked — a pre-existing discrepancy flagged before
  this batch started, not something this batch's scope covers fixing.
- **`T49`–`T51`** (`refresh_tokens` migration, `AuthService`, `AuthService` tests) — explicitly not
  started, per instruction to implement `T47` only.

## Future Considerations

- `T50`'s `AuthService.authenticate()` and `T62`'s user-creation route are the two consumers this
  utility exists for — both should import `hash_password`/`verify_password` directly from
  `infrastructure.security`, not reach into `argon2` themselves.
- `T47` (JWT utility) is independent of this task and was already noted in
  `IMPLEMENTATION_QUEUE.md`'s "Recommended implementation order" as buildable in either order
  relative to `T46` — nothing here blocks or is blocked by it.

**T47 batch:**
- `T50`'s `AuthService.issue_tokens()`/`refresh()` and `T52`'s `JwtAuthenticationProvider.
  get_current_user()` are the two consumers this utility exists for — both should import
  `create_access_token`/`create_refresh_token`/`decode_token` directly from
  `infrastructure.security`, not reach into `jwt` themselves.
- `T49`'s `refresh_tokens` migration will need a `token_hash` of whatever `create_refresh_token()`
  produces (per D1 — the raw token is never stored, only a hash of it) — this batch doesn't hash
  anything itself, that's `T49`/`T50`'s job when the table and the service that writes to it exist.
- Whoever picks up `T50` should decide there (not retroactively here) whether `AuthService` re-reads
  `Settings` via `get_settings()` or receives it via constructor injection — this batch's functions
  only require *a* `Settings` instance be passed in, not any particular resolution mechanism.

## Reviewer Checklist

Self-assessed for Phase 1 as it stands (`T46` + `T47`), updated in place rather than duplicated per
batch — see `docs/ImplementationLog/README.md`'s "phase log is authoritative for its own technical
facts" convention (the same one `Phase0.md` follows across its four batches).

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

- **Existing design patterns followed:** both `T46` and `T47` match `docs/Stage3_Backend_Handoff.md`'s
  own file map exactly (function names, module paths, library choices) — no invented shape either
  time. `T47` also reuses `T46`'s own precedent directly (plain functions over a port, a single
  base-exception catch collapsing to a boolean/`None` outcome) rather than inventing a different
  shape for a sibling utility in the same `infrastructure/security/` module.
- **ADR updated (if required):** `□` — correctly not required for either batch. `ADR-0018` already
  records D2 (Argon2id) and D3 (`PyJWT`) as approved decisions; both batches implement what's
  already decided, neither decides anything new.
- **AI_BOOTSTRAP updated (if required):** `□` — no non-negotiable rule, required-reading order, or
  standing convention changed by either batch (the "Task IDs are immutable" rule now present in
  `AI_BOOTSTRAP.md` was adopted separately, outside this phase's own work).
- **PROJECT_STATE updated (if required):** `☑` — `T46`'s batch updated test count (298 → 304) and
  added a `backendSubsystems` entry; `T47`'s batch does the same again (304 → 313, a new entry) as
  part of this same documentation-synchronization pass.
- **No scope creep:** `T46`'s batch implemented exactly `T46`; `T47`'s batch implemented exactly
  `T47` — no `AuthService`, no `refresh_tokens` migration, no routes, no DB writes in either,
  matching each batch's explicit "implement `T4X` only" instruction. The pre-existing `T48`
  discrepancy (already satisfied by `T44`, row unmarked) was noted, not silently absorbed into
  `T47`'s scope or fixed without being asked.
- **Ready for QA:** this log, plus the fifteen named tests across both batches and their one-line
  rationale, are meant to be sufficient for a reviewer to verify Phase 1's work so far without
  asking what happened or why.

## QA Decision

```
QA Decision

☑ Approved
□ Approved with comments
□ Rework required
```

Single-session, playing both roles in sequence per `AI_BOOTSTRAP.md`'s documented allowance.
**Approved:** `T46` matches its acceptance criteria exactly (correct password verifies, wrong
password fails, hash never plaintext-equal to input) plus two earned extra tests; `T47` matches its
acceptance criteria exactly (round-trip, expired token rejected, tampered signature rejected) plus
six earned extra tests (wrong secret, malformed input, jti uniqueness, both token kinds' expiry,
exception-leak check). 201/201 unit tests passing; ruff/black clean; app still boots. No scope
creep in either batch — `T48`'s pre-existing discrepancy was flagged, not fixed unbidden; `T49`
onward genuinely untouched. Proceeding to documentation synchronization (`PROJECT_STATE.json`,
`IMPLEMENTATION_QUEUE.md`, `docs/SessionReport.md`).
