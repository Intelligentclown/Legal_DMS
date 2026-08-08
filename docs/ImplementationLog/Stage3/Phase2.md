------------------------------------------------

# Stage 3 – Phase 2

Status: In Progress

Started: 2026-08-08

Completed:

Related Tasks: T52

Related ADRs: ADR-0019

Git Commit:

Pull Request:

Release:

------------------------------------------------

## Objective

Begin Stage 3 Phase 2 (wiring auth into the request pipeline) with `T52` only: a real
`JwtAuthenticationProvider` implementing `AuthenticationProvider`'s approved D7 signature
(`async def get_current_user(self, token: str | None) -> CurrentUser`, `ADR-0019`). No
`RbacAuthorizationService`, `RequirePermission` dependency, `configure_container()` wiring, or
`deps.py` changes — those are `T53`–`T57`, not started this batch.

**Provenance note (recorded by the Documentation Manager role, not the implementer):** this section
of the log is being written after the fact, reconstructing what the repository actually shows
(`git status`, the files themselves, a fresh test run) rather than from a Backend Developer's own
self-authored account, because no such account exists anywhere in the repository — see Problems
Encountered for why. Every fact below was independently verified against the repository, not copied
from a claim.

## Tasks Implemented

- **T52 — `JwtAuthenticationProvider`.** `infrastructure/auth/jwt_authentication_provider.py`: decodes
  the presented bearer token via `T47`'s `decode_token()`, then re-derives the caller's identity and
  roles live from the database via `T50`'s `UserRepository` (`get_by_id`, `get_role_names`) — the
  token's own `roles` claim is never trusted as the source of truth, matching the defense-in-depth
  pattern `AuthService.refresh()` already established. `token=None`, a `None` decode result (expired/
  malformed/tampered/wrong-secret token — all of which `decode_token()` already collapses to `None`
  per `T47`), a non-UUID/missing `sub` claim, an unknown user id, or an inactive user all resolve to
  the same anonymous default (`CurrentUser()`) — the method never raises.

## Files Modified

- `backend/src/app/infrastructure/auth/jwt_authentication_provider.py` *(new)*.
- `backend/tests/unit/test_jwt_authentication_provider.py` *(new)*.

Both files are **untracked** in the working tree as of this log entry (confirmed via `git status`) —
not merely "on a branch instead of main," but not committed anywhere at all yet. See Problems
Encountered.

## Tests Added

11 in `backend/tests/unit/test_jwt_authentication_provider.py`:

`TestNoOrInvalidToken` (6): `token=None` returns anonymous; a malformed (non-JWT) token returns
anonymous; an expired token returns anonymous; a tampered-signature token returns anonymous; a token
signed with a different secret returns anonymous; a token with a non-UUID `sub` claim returns
anonymous rather than raising.

`TestDatabaseResolution` (5): a well-formed token for an unknown user id returns anonymous; a token
for a since-deactivated user returns anonymous; a valid token for an active, known user returns a
populated, authenticated `CurrentUser` with the correct id/display name/roles; roles are re-derived
from the database rather than trusted from the token's own `roles` claim (a token carrying a stale
role, checked against a database role that has since changed, reflects the database's current value);
a user deactivated *after* token issuance returns anonymous on the next call, not just at next login.

## Test Results

- New tests: `pytest tests/unit/test_jwt_authentication_provider.py -v` — **11/11 passing**.
- Full backend suite: `pytest -q` — **356 passed** (345 prior + 11 new), 0 failed, 0 skipped. Re-run
  directly by the Documentation Manager role during this synchronization pass, not assumed from a
  prior claim.
- **Lint:** `ruff check src tests alembic` and `black --check src tests alembic` — both clean,
  re-verified directly.
- **Import/boot smoke test:** `python -c "from app.main import app"` — succeeds. `JwtAuthenticationProvider`
  is not wired into `main.py`/`configure_container()` this batch (that's `T55`), so this only confirms
  the new modules don't break import resolution.

## Design Decisions

- **Never raises, always resolves to a `CurrentUser`.** Every failure mode (no token, expired,
  malformed, tampered, wrong secret, unparseable `sub`, unknown user, inactive user) collapses to the
  same anonymous default rather than distinct exceptions — matches the port's own documented contract
  (`application/interfaces/auth.py`: "must resolve the same as an invalid/expired token would — the
  anonymous default — never raise") and keeps "is this caller authenticated" a decision entirely
  local to whatever reads `CurrentUser.is_authenticated`, not scattered across a catch-every-exception
  block at each call site.
- **Roles re-derived from the database on every call, not read from the token's `roles` claim.**
  Consistent with `T50`'s `AuthService.refresh()`, which already re-derives current role names rather
  than trusting a token's claims — a role granted or revoked after token issuance takes effect
  immediately on the next request, not only after the access token naturally expires. Covered
  explicitly by `test_roles_are_re_derived_from_the_database_not_the_token_claims`.
- **No `configure_container()` registration this batch.** Same reasoning `T50`/`Phase1.md` already
  recorded for `AuthService`: `JwtAuthenticationProvider` needs a per-request `UserRepository` (backed
  by a per-request `AsyncSession`), which the container doesn't hold. That wiring is `T55`'s job.

## Problems Encountered

**The core issue this log entry exists to resolve, stated plainly and without inventing anything not
actually true:**

- **Authorization occurred, but not inside the repository.** The project owner explicitly authorized
  `T52` in a separate Project Manager conversation. That authorization is real — it is not being
  fabricated or backdated here — but it was never written into `IMPLEMENTATION_QUEUE.md` or
  `PROJECT_STATE.json` before implementation began, so both documents still read "not authorized yet"
  as of this session's start, directly contradicting what had actually been approved. This violates
  this project's own Repository-First Rule in spirit (the repository is supposed to be able to answer
  "was this authorized" on its own, without relying on a conversation elsewhere) even though the
  underlying decision was legitimate. This log does not retroactively insert a fake in-repository
  approval record predating implementation — it records, honestly, that the approval happened
  out-of-band and the repository is only catching up to that fact now.
- **No `docs/ImplementationLog/Stage3/Phase2.md` existed until this pass.** Per
  `docs/ImplementationLog/README.md`, a phase log is supposed to be created "the moment Phase 0
  [here, Phase 2] implementation actually starts," not after the fact. It wasn't. This file is that
  missing entry, created now rather than left permanently absent.
- **`T52` was implemented directly on `main`, and is currently uncommitted.** `git status` shows
  `jwt_authentication_provider.py` and its test file as **untracked** — no `feature/stage3-t52-*`
  branch was ever created, unlike every completed Stage 3 batch before it (`T46`, `T47`, `T49`,
  `T50`/`T51` all went through a feature branch + PR). This is a real deviation from
  `PROJECT_WORKFLOW.md` §4's branch strategy, not a formality — flagged here, not corrected, since
  creating a branch, committing, and pushing are git actions outside this role's scope (§8: "Never
  implement or modify source code" extends in spirit to not taking git actions on someone else's
  behalf without separate authorization) and none of those was authorized as part of this
  documentation-synchronization pass.

None of the three items above reflects a defect in `T52`'s actual code or tests — QA's independent
review found both technically correct (see this log's QA Decision section once rendered). All three
are process/documentation gaps, and this pass closes the first two directly; the third remains open
and is recorded as such rather than silently implied to be resolved.

## Deferred Work

- **`T53`–`T57`** (`RbacAuthorizationService`, `RequirePermission` dependency, `configure_container()`
  wiring, `deps.py` update, Phase 2 tests) — not started, per `T52`'s own scope.
- **A feature branch, commit, and PR for `T52`'s existing code** — not created this pass. `T52`'s
  files remain untracked, uncommitted, directly on `main`. Trigger: the next session with explicit
  authorization to take git actions should branch, commit, and push this already-implemented, already
  independently QA-verified code before continuing to `T53`, so the deviation doesn't compound further.

## Future Considerations

- Whoever picks up `T53` should also resolve the standing branch/commit gap for `T52` first (or
  alongside), rather than adding a second uncommitted batch on top of the first — see Deferred Work.
- `T55`'s `configure_container()` wiring is the first point at which `JwtAuthenticationProvider` needs
  a concrete resolution strategy for its per-request `UserRepository` dependency — the same
  request-scoped-construction question `Phase1.md` already flagged for `AuthService`.

## Reviewer Checklist

Self-assessed by the Documentation Manager role against the repository's actual current state, since
no separate Backend Developer self-assessment exists in the repository for this batch (see Problems
Encountered — this is itself part of the process gap being closed, not a new omission introduced
here).

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
□ Ready for QA
```

Notes on the less-obvious ones:

- **Architecture preserved:** `JwtAuthenticationProvider` lives in `infrastructure/auth/`, implements
  `application/interfaces/auth.py`'s `AuthenticationProvider` port with no changes to the port itself,
  imports `UserRepository` (a port) rather than a concrete SQLAlchemy class directly — no layering
  violation found on direct inspection.
- **Existing design patterns followed:** matches `AnonymousAuthenticationProvider`'s shape (one class,
  one method, same port) and reuses `T50`/`AuthService`'s "never trust token claims for anything the
  database can answer fresher" pattern rather than inventing a different one.
- **Documentation updated:** *this* pass (`Phase2.md` created; `IMPLEMENTATION_QUEUE.md`,
  `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/SessionReport.md` synchronized) is what makes
  this box honestly checkable — it was not true before this session.
- **ADR updated (if required):** `□` — correctly not required. `ADR-0019` already records D7; this
  batch implements what's already decided.
- **AI_BOOTSTRAP updated (if required):** `□` — no non-negotiable rule or standing convention changed.
- **No scope creep:** `☑` for the *code* (exactly `T52`, nothing from `T53`+ touched) — but see
  Problems Encountered for the two process gaps (authorization-recording, phase-log timing) that are
  a different kind of deviation, not scope creep in the technical sense.
- **Ready for QA:** `□` — left unchecked deliberately. This checklist covers the documentation
  synchronization itself; whether the *process gate* (the three items QA originally found) is now
  satisfied is QA's independent judgment to render, not this role's to presume. The branch/commit
  deviation also remains genuinely open, not resolved — a reviewer should weigh that explicitly
  rather than see a checked box implying otherwise.

## QA Decision

```
QA Decision

□ Approved
□ Approved with comments
□ Rework required
```

Pending — to be rendered by the QA Reviewer role re-reviewing the process gate specifically, after
this documentation-synchronization pass. Not pre-filled here.
