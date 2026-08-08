------------------------------------------------

# Stage 3 – Phase 1

Status: In Progress

Started: 2026-08-07

Completed:

Related Tasks: T46, T47, T49

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
or DB writes — those remain `T49`–`T51`+, per instruction to implement `T47` only. **T49 batch
(this update):** add the `refresh_tokens` table (D1/`ADR-0018`) — an Alembic migration plus the
`RefreshToken` persistence model `T50`'s `AuthService` will read/write. Still no `AuthService`,
routes, or seed data — those remain `T50`+, per instruction to implement `T49` only.

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
- **T49 — `refresh_tokens` table.** New Alembic migration
  `2572cb3570d7_refresh_tokens.py`: `id` (UUID PK), `user_id` (FK → `users.id`), `token_hash`
  (unique, indexed — a hash of the token, never the raw value, same principle as
  `users.password_hash`), `issued_at`, `expires_at`, `revoked_at` (nullable). Paired with a new
  `RefreshToken` persistence model in `infrastructure/persistence/models/identity.py`, alongside
  `User`/`Role`/etc. — this project's convention is model + migration together (`ADR-0008`), and
  `T50`'s `AuthService` explicitly needs `SqlAlchemyRepository[RefreshToken]`. No `AuditMixin` on
  the model — see Design Decisions.

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

**T49 batch:**
- `backend/alembic/versions/2572cb3570d7_refresh_tokens.py` *(new)*.
- `backend/src/app/infrastructure/persistence/models/identity.py` — added the `RefreshToken` class.
- `backend/tests/integration/test_identity_models.py` — added `TestRefreshToken` (4 tests).
- `docs/Database.md` — new `refresh_tokens` row, a "Post-Stage-2 addition" subsection, updated
  migrations table, and an explicit note that this migration was hand-written (not
  `--autogenerate`d) and not yet run against a live database — see Test Results.
- `docs/ERD.md` — added `refresh_tokens` to the diagram and the Section 1 table list.
- `docs/ImplementationLog/Stage3/Phase1.md` — this file.

No dependency file touched — no new library needed for a migration + model.

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

**T49 batch:** 4 in `backend/tests/integration/test_identity_models.py`'s new `TestRefreshToken`
class:
1. `test_requires_existing_user` — inserting a `RefreshToken` with a non-existent `user_id` violates
   the FK constraint.
2. `test_create_succeeds_with_expected_defaults` — a valid row gets an `id`, an `issued_at` default,
   and `revoked_at` starts `None`.
3. `test_token_hash_must_be_unique` — two rows sharing a `token_hash` violate the unique constraint.
4. `test_revoked_at_can_be_set` — the one lifecycle transition this table supports (marking a token
   revoked) persists correctly.

Matches this project's existing per-model integration-test shape exactly (`TestUser`/`TestRole`/
`TestUserRole` in the same file) — FK requirement, uniqueness, and default/lifecycle behavior are
the three things every other model in this file is tested for, so `RefreshToken` gets the same
three plus the FK case, not a different template. **Not run this batch** — see Test Results.

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

**T49 batch:**
- `alembic heads` — **single head** (`2572cb3570d7`), confirming a clean, unforked chain.
- `alembic history` — confirms `2572cb3570d7` correctly chains onto `9963e15f2752` (the prior head).
- `python -c "from app.infrastructure.persistence.models.identity import RefreshToken; ..."` —
  the model constructs correctly; printed columns (`id`, `user_id`, `token_hash`, `issued_at`,
  `expires_at`, `revoked_at`) and constraints (`pk_refresh_tokens`, `fk_refresh_tokens_user_id_users`)
  match the naming convention exactly.
- Full unit suite: `pytest tests/unit -q` — **201 passed** (unaffected by this batch — no unit test
  touches persistence models — run as a sanity check, not because this batch's own tests live
  there).
- **Lint:** `ruff check src alembic tests` and `black --check src alembic tests` — clean (two
  formatting fixes needed, applied via `black`, then re-verified clean).
- **Import/boot smoke test:** `python -c "from app.main import app"` — succeeds.
- **`alembic revision --autogenerate` was not used** — Docker Desktop would not start in this
  environment (attempted directly: launched it, polled for the daemon for 4 minutes, it never came
  up), so no live Postgres connection was available to diff against. The migration was hand-written
  instead, matching the established `op.create_table()`/`op.f()`-naming style from every prior
  migration in this repository byte-for-byte in structure (verified by direct comparison against
  `4c661976b322_identity_and_access_users_roles_.py`'s `user_roles` table, which has the same
  shape: UUID PK, one FK, one plain index).
- **Genuinely not verified this batch, disclosed rather than assumed:** `alembic upgrade head`/
  `alembic downgrade -1` against a real Postgres database; the 4 new `TestRefreshToken` integration
  tests were never executed (only collected — `pytest --collect-only` confirms they're discovered
  and import cleanly, not that they pass against a real schema). Both require the same unreachable
  Postgres. Flagged explicitly in `docs/Database.md` itself, not just here, so this doesn't get
  lost the next time someone reads that file instead of this log.

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

**T49 batch:**
- **Model added alongside the migration, even though `T49`'s own one-line description only names
  "New Alembic migration."** Justified as the minimal necessary addition per this batch's own scope
  instructions: this project's established convention is persistence model + migration together for
  every table (`ADR-0008`; every existing table in `identity.py` has both), and `T50`'s own
  description explicitly requires `SqlAlchemyRepository[RefreshToken]` — a migration with no
  corresponding model would leave `T50` unable to start without first inventing the model anyway,
  under a different task's name. Not adding it would just move the "genuinely required" work one
  task later without actually reducing it.
- **No `AuditMixin` on `RefreshToken`.** `T49`'s column list (`id`, `user_id`, `token_hash`,
  `issued_at`, `expires_at`, `revoked_at`) matches exactly what's needed for a system-issued,
  high-volume security record — the same category `UserRole`/`RolePermission` (join/associative
  tables, no `AuditMixin`) already fall into, not the same category as `User`/`Role`/`Permission`
  (human-managed business entities that do use it). `revoked_at` already is this table's one
  lifecycle transition; `AuditMixin`'s `deleted_at`/`created_by`/`updated_by` would add columns
  `T49` never asked for and that don't map to anything meaningful for a token row nothing
  soft-deletes or attributes to an editor.
- **`token_hash` given both `unique=True` and `index=True`**, though `T49`'s text doesn't say
  "unique" explicitly. `T50`/`T52` will look up a presented refresh token by the hash of it to
  validate/revoke — a duplicate hash would mean either an astronomically unlikely collision or a
  bug, and the existing schema already enforces exactly this kind of natural-uniqueness rule
  elsewhere (`permissions.code`, `roles.name`) as a standard defensive constraint, not a
  speculative addition.
- **Hand-written migration, not `--autogenerate`d** — see Test Results for why (Docker unreachable).
  Followed the exact structural precedent of the most similar existing migration
  (`user_roles`: one UUID PK, one FK, one plain non-unique index) rather than inventing a new shape,
  and cross-checked every generated name (`pk_refresh_tokens`, `fk_refresh_tokens_user_id_users`,
  `ix_refresh_tokens_user_id`, `ix_refresh_tokens_token_hash`, `uq_refresh_tokens_token_hash`)
  against `base.py`'s `NAMING_CONVENTION` formula directly, then confirmed the model produces the
  identical set of constraint names at runtime (see Test Results) as a second, independent check.

## Problems Encountered

None. `argon2-cffi` was already installed and importable (proven by `T44`'s
`TestArgon2CffiIsInstalled` tests in `test_auth_dependencies.py`), so this batch was a
straightforward, single-file addition with no environment surprises.

**T47 batch:** One test needed a `black` reformat after first being written (line-wrapping only, no
logic change) — caught and fixed by the normal lint step before considering the batch done, not a
functional problem.

**T49 batch:** Docker Desktop would not start in this environment — launched directly via
`Start-Process`, polled `docker info` every 10s for 4 minutes, the daemon never became reachable.
Same limitation disclosed in every prior batch/session this conversation touched a DB-dependent
task. Worked around by hand-writing the migration against the documented naming convention instead
of `--autogenerate`, and disclosing the unrun-migration/unrun-tests gap explicitly rather than
presenting either as verified.

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

**T49 batch:**
- **Running the migration and its 4 new tests against a real Postgres instance** — trigger: the
  next time this project is worked on in an environment where Docker/Postgres is reachable. Until
  then, `2572cb3570d7` is unverified against a live database; flagged prominently in
  `docs/Database.md`, not just here.
- **`T50`–`T51`** (`AuthService`, its tests) — explicitly not started, per instruction to implement
  `T49` only.

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

**T49 batch:**
- `T50`'s `AuthService` is the real consumer of `RefreshToken` — it will need either a plain
  `SqlAlchemyRepository[RefreshToken]` (this project's generic repository already works with zero
  new code, per `docs/Stage3_Backend_Handoff.md`) or a small dedicated lookup-by-hash method if the
  generic repository's `get_by_id`-only shape doesn't fit "find by `token_hash`" cleanly — that
  decision belongs to `T50`, not pre-made here.
- The migration's live-database verification gap (see Deferred Work) should be the first thing
  re-checked before `T50` starts writing real rows through it.

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

*The `T46`/`T47` Reviewer Checklist and QA Decision above are the historical record for that batch
and are not revised here — per this project's "phase log is authoritative for its own technical
facts at the time" convention, corrections get a new dated entry, not a silent rewrite. `T49`'s own
self-assessment and QA gate follow below, kept separate rather than folded into the text above.*

## Reviewer Checklist — T49 batch

Self-assessed by the Backend Developer role only, per `docs/prompts/BackendDeveloper.md` — this
role renders the Reviewer Checklist, never the QA Decision (see below).

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
□ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
□ Ready for QA
```

Notes on the less-obvious ones:

- **Architecture preserved:** model in `infrastructure/persistence/models/`, migration in
  `alembic/versions/` — no port/interface touched, no layering violation.
- **Existing design patterns followed:** migration structure matches `user_roles`'s exactly (see
  Design Decisions); model matches `UserRole`/`RolePermission`'s "plain `Base`, no `AuditMixin`"
  shape for the same category of table.
- **Tests added:** 4 new integration tests, matching this file's existing per-model shape.
- **Existing tests pass:** `□` — **not fully verifiable this batch.** The unit suite (201/201,
  unaffected by this change) was re-run and passes, but the *relevant* existing suite for a schema
  change — the integration suite, including this batch's own 4 new tests — could not be run at all
  (Docker/Postgres unreachable). Checking this box would overstate what was actually verified;
  see Test Results for the full disclosure.
- **Documentation updated:** `docs/Database.md`/`docs/ERD.md` (this migration's own required
  documentation, per `docs/templates/DatabaseMigrationTemplate.md`) and this phase log. Per
  `docs/prompts/BackendDeveloper.md`'s ownership rules, `PROJECT_STATE.json`/
  `IMPLEMENTATION_QUEUE.md`/`docs/SessionReport.md` are explicitly **not** touched this batch —
  that synchronization belongs to the Project Manager (`IMPLEMENTATION_QUEUE.md`) and Documentation
  Manager (the rest) roles, after a QA Decision exists.
- **ADR updated (if required):** `□` — correctly not required. `ADR-0018` already records D1 (the
  refresh-token design this table implements); this batch builds what's already decided.
- **PROJECT_STATE updated (if required):** `□` — deliberately not this role's job this batch; see
  Documentation updated above.
- **Ready for QA:** `□` — left unchecked specifically because the migration's live-database
  behavior and the new tests' actual pass/fail are unverified, not because the implementation
  itself is believed incomplete. A QA Reviewer should treat this as "review the code and tests as
  written, but the DB-verification gap is real and must be closed — by this role or the reviewer —
  before this batch can be called done," not as an oversight to silently wave through.

## QA Decision — T49 batch

```
QA Decision (T49 batch)

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, after one rework round, on 2026-08-07 — not by the Backend
Developer role that left it unselected above (see `docs/prompts/BackendDeveloper.md`: "Never
render the QA Decision — that belongs to the QA Reviewer").

**Rework history:** the QA Reviewer's first pass found a schema mismatch between the migration and
the `RefreshToken` model's `token_hash` column. That mismatch is resolved — the migration
(`sa.Column("token_hash", sa.String(length=255), nullable=False)` plus a unique index) and the
model (`token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)`) now agree,
confirmed directly by `alembic check` reporting no new upgrade operations detected (the exact check
that verifies model metadata matches what the migration chain produces).

**Approved — closing the gap the Backend Developer role explicitly left open** (`Existing tests
pass: □`, `Ready for QA: □` in the Reviewer Checklist above, disclosed as unverifiable because
Docker/Postgres was unreachable in that environment). This review ran in an environment where
Postgres was reachable and verified, independently:
- Live PostgreSQL verification: pass.
- `alembic upgrade head` → `downgrade -1` → `upgrade head`: clean round-trip, no errors.
- `alembic check`: no schema drift.
- `test_identity_models.py` (includes the 4 new `TestRefreshToken` cases): 12/12 passing.
- Full backend suite: 317/317 passing (0 failed, 0 skipped).
- `ruff check` / `black --check`: clean.

No scope creep — `T50` (`AuthService`) is not authorized or touched by this review. Proceeding to
documentation synchronization (`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`,
`docs/SessionReport.md`, `docs/Database.md`, `docs/Roadmap.md`) per the Documentation Manager role.
