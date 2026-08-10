# Legal_DMS — Current Project Checkpoint

*A concise current-state snapshot for any AI picking up this project. Not an implementation log —
see [`docs/ImplementationLog/`](docs/ImplementationLog/) for execution history and
[`docs/SessionReport.md`](docs/SessionReport.md) for session-by-session narrative. If this file and
either of those disagree, trust the live repository (`git log`/`git status`), not this file — then
fix this file.*

## 1. Last Verified State

- **Verified:** 2026-08-10, this session — directly against `git`, not from prior conversation.
- **Current branch:** `main`
- **HEAD commit:** `b094436`
- **`origin/main`:** `b094436` — synchronized with local `main`.
- **Working tree:** clean.
- **Latest relevant merge/PR:** PR #15, `feature/stage3-t55-auth-wiring` → `b094436` ("Merge pull
  request #15 from Intelligentclown/feature/stage3-t55-auth-wiring") — carries two commits:
  `86a3d5d` ("feat(auth): wire real authentication and authorization services" — `T55`'s code) and
  `f070e28` ("docs(auth): reconcile T55 governance record" — the authorization-provenance
  correction). Confirmed via `git show --stat` on all three commits, not assumed.

**Correction from the previous version of this file:** that version was written at `512c91e` (`T54`
closed). Since then: `PROJECT_CHECKPOINT.md` itself was added (PR #14, `90c5bf2`), and `T55` was
implemented, its governance record reconciled, QA-reviewed twice, and closed out — all merged
through `b094436`. `main` now fully reflects `T55` as `Done`, including the preserved,
**unresolved** authorization-recording governance finding — verified by reading
`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, and `docs/ImplementationLog/Stage3/Phase2.md`
directly on `main`, not assumed.

## 2. Current Stage

- **Stage:** 3 — Authentication & Authorization (`docs/Roadmap.md`, `IMPLEMENTATION_QUEUE.md`).
- **Phase:** 2 — wiring auth into the request pipeline (`T52`–`T57`).
- **Overall project progress:** Stages 0–2 complete (infrastructure/framework/schema only, 0
  business features by design). Stage 3 is the first business-adjacent feature, in progress.
- **Completed task range:** `T41`–`T55` — code merged **and** documentation/governance closeout
  merged, both confirmed on `main`.
- **Next unfinished task:** `T56` — **not authorized**.

## 3. Completed Tasks

| Task | Status | Purpose | Commit/PR |
|---|---|---|---|
| T41–T43 | Done | `get_db()` commit/rollback fix — hard prerequisite for all of Stage 3 | PR #2 (`78f2677`) |
| T44–T45 | Done | Auth dependencies/config + `AuthenticationProvider` interface change (D7) | PR #3 (`815cc26`) |
| T46 | Done | Password hashing utility (`hash_password`/`verify_password`, Argon2id) | PR #4 (`2e5ce80`) |
| T47 | Done | JWT encode/decode utility (`create_access_token`/`create_refresh_token`/`decode_token`) | PR #5 (`4d739d2`) |
| T48 | Done | Auth `Settings` config — satisfied incidentally by `T44`'s redefined scope | no separate PR |
| T49 | Done | `refresh_tokens` migration + `RefreshToken` model | PR #7 (`26702b6`) |
| T50/T51 | Done | `AuthService` (authenticate/issue_tokens/refresh/revoke) + 28 tests | PR #8 (`204c098`) |
| T52 | Done | `JwtAuthenticationProvider` — real `AuthenticationProvider` | PR #9 (`baed936`) |
| T53 | Done | `RbacAuthorizationService` — real `AuthorizationService` | code PR #10 (`a103dca`); doc closeout PR #11 (`25a6078`) |
| T54 | Done | `RequirePermission(...)` FastAPI dependency factory | code+reconciliation PR #12 (`6396f6b`); doc closeout PR #13 (`512c91e`) |
| **T55** | **Done** | Request-scoped `Depends()` wiring of real `JwtAuthenticationProvider`/`RbacAuthorizationService` in `presentation/api/deps.py`, replacing the planned `configure_container()` registration approach | code+governance PR #15 (`b094436`, commits `86a3d5d`/`f070e28`) |

Full technical detail for `T52`–`T55` lives in `docs/ImplementationLog/Stage3/Phase2.md` — not
duplicated here.

## 4. Current Task

**There is no open current task.** `T55` (the last one worked) is fully `Done`; `T56` has not
started. This section documents `T55`'s final, closed state for reference:

- **Task:** `T55` — request-scoped construction of `JwtAuthenticationProvider`/
  `RbacAuthorizationService`, replacing the originally-authorized `configure_container()` registration
  approach once it proved technically unworkable (`container.resolve()` is synchronous/zero-argument;
  both real providers need a request-scoped `AsyncSession`).
- **Authorization status:** given by the project owner conversationally (original scope, then an
  architectural clarification, then an expanded scope) — **never recorded in a committed repository
  state before implementation began.** This is the **fourth consecutive** Stage 3 Phase 2 batch with
  this exact governance gap (`T52`, `T53`, `T54`, `T55`). **This finding is preserved as permanent
  governance history and is explicitly NOT resolved by `T55`'s closeout** — it cannot be; a commit
  cannot retroactively predate the code it's supposed to authorize.
- **Implementation status:** complete, merged into `main` (`presentation/api/deps.py`'s
  `get_authentication_provider()`/`get_authorization_service()`; `infrastructure/di/container.py`'s
  two obsolete registrations removed; 6 new integration tests in
  `tests/integration/test_auth_dependency_wiring.py`).
- **QA status — final disposition:** two decisions exist in `docs/ImplementationLog/Stage3/Phase2.md`,
  both preserved, neither overwriting the other:
  1. **Original (2026-08-10): `Rework required`** — governance/process grounds only, explicitly "no
     code changes required." Preserved verbatim as the historical record.
  2. **Follow-up (2026-08-10, same day): `Approved with comments`** — the **final QA disposition**,
     rendered once the branch/commit/PR gap closed (`feature/stage3-t55-auth-wiring` → `86a3d5d`/
     `f070e28` → PR #15 → `b094436`). The authorization-recording finding itself is **not** claimed
     resolved by this follow-up — only the git-provenance gap is.
- **Documentation status:** fully synchronized and merged into `main` (PR #15, `b094436`).
- **Dependencies:** `T52`, `T53` (both done).
- **Is `T55` finished?** **Yes — fully.** Code, both QA decisions, and documentation are all merged
  into `main`. (Distinct from `T56`'s status below — see §5.)

## 5. Next Cycle

- **Next task:** `T56` — update `presentation/api/deps.py`'s `CurrentUserDep` for the new provider
  signature.
- **Why it's next:** `IMPLEMENTATION_QUEUE.md`'s task table lists `T56`'s dependency as `T55` — now
  `Done` and merged on `main`.
- **Dependencies:** `T55` (done).
- **Is it authorized? NO — verified directly, not assumed.** `IMPLEMENTATION_QUEUE.md`'s `T56` row
  on `main` carries no `Done`/authorization marker; `PROJECT_STATE.json`'s `currentStage.note`
  explicitly ends "`T56-T57 remain not started, not authorized`." No project-owner authorization for
  `T56` exists anywhere in the repository as of this checkpoint.
- **What must happen before implementation begins:**
  1. The project owner authorizes `T56` — and, given `T52`/`T53`/`T54`/`T55` have **all four**
     demonstrated the same authorization-recording gap, that authorization must actually be
     **written into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation starts** —
     a fifth recurrence would no longer read as an isolated incident anywhere in this project's own
     documents.
  2. The Backend Developer role performs the `docs/prompts/BackendDeveloper.md` §5 checkpoint
     (reconstruct state, summarize understanding, wait for explicit approval of that summary) before
     writing any code.

**`T55` being finished and `T56` being unauthorized are two separate facts — do not conflate them.**
`T55`'s completion does not itself authorize `T56`; that pattern (assuming the next task is
authorized because the previous one just closed) is exactly what produced four consecutive
governance findings in this project's own history.

## 6. Repository State

- **`main`:** `b094436`
- **`origin/main`:** `b094436` (synchronized)
- **Latest merge commit:** `b094436` (PR #15, `feature/stage3-t55-auth-wiring`)
- **Latest feature branch relevant to the completed task:** `feature/stage3-t55-auth-wiring`
  (`86a3d5d`, `f070e28`) — merged, safe to delete if not already.
- **Working-tree status:** clean.
- **Uncommitted files:** none.
- **Any task implementation sitting uncommitted?** No.
- **Any task documentation sitting unmerged?** No — everything through `T55` is on `main`.
- **PR verifiable locally?** Yes — `git log --oneline --decorate -8` shows `b094436 (HEAD -> main,
  origin/main, origin/HEAD) Merge pull request #15 from Intelligentclown/feature/stage3-t55-auth-wiring`,
  and `git show --stat` on `b094436`/`86a3d5d`/`f070e28` confirms the exact file lists (code commit:
  `container.py`, `deps.py`, `test_auth.py`, new `test_auth_dependency_wiring.py`; governance commit:
  the six documentation/project-management files).

## 7. Test / Quality Status

All figures below **re-verified this session, directly on `main` at `b094436`**:

- **Backend tests:** `uv run pytest -q` — **380 passed, 0 failed, 0 skipped** (includes
  Postgres-backed integration tests — `legal_dms_postgres` container confirmed healthy).
- **Frontend tests:** `npm test -- --run` (Vitest) — **9 passed, 0 failed** (3 test files) — carried
  from the prior verification pass; unaffected by `T55` (backend-only change).
- **Lint:** `uv run ruff check src tests alembic` — clean.
- **Format:** `uv run black --check src tests alembic` — clean.
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds.
- **Database/integration status:** live Postgres reachable and healthy.
- **Environmental issues:** none.

## 8. Current Architecture Snapshot

- **`AuthenticationProvider` (Stage 1 port):** real implementation is `JwtAuthenticationProvider`
  (`T52`) — decodes the bearer token (`T47`'s `decode_token()`), re-derives identity/roles live from
  the DB via `T50`'s `UserRepository` (never trusts the token's own `roles` claim), resolves every
  failure mode to the anonymous `CurrentUser()` default, never raises.
- **`AuthorizationService` (Stage 1 port):** real implementation is `RbacAuthorizationService`
  (`T53`) — `require_permission()` checks a pre-loaded role→permission-code snapshot
  (`RolePermissionRepository`, `T53`), reuses `PermissiveAuthorizationService`'s anonymous-denial
  check.
- **`AuthService` (`T50`, application layer):** `authenticate`/`issue_tokens`/`refresh`/`revoke` —
  the credential/token lifecycle, built on `T46` (password hashing), `T47` (JWT), `T49`
  (`refresh_tokens` table).
- **`RequirePermission(...)` (`T54`, `presentation/api/deps.py`):** a FastAPI dependency *factory* —
  `Depends(RequirePermission("matters:read"))` — composes `CurrentUserDep` and
  `get_authorization_service()`. **No route calls it yet** — no route exists yet at all (Phase 3,
  `T58`+).
- **Dependency injection (`T55`, NEW):** `JwtAuthenticationProvider`/`RbacAuthorizationService` are
  **now real and wired — but via request-scoped FastAPI `Depends()` in `presentation/api/deps.py`,
  NOT via the DI container.** `get_authentication_provider()`/`get_authorization_service()` build
  both fresh per request, directly from `DBSessionDep` (through `SqlAlchemyUserRepository`/
  `SqlAlchemyRolePermissionRepository`) — the container's `AuthenticationProvider`/
  `AuthorizationService` registrations were **removed** (confirmed unused elsewhere by inspection),
  since `container.resolve()` is synchronous/zero-argument and has no mechanism to inject a
  request-bound session into a factory. The running app now resolves **real** auth/authz on every
  request — no route exists yet to actually exercise this end-to-end.
- **Placeholder vs. real:** every auth building block is now real, tested, wired, and merged. The
  Stage-1 `Anonymous`/`Permissive` stub classes still exist in the codebase (used directly,
  unregistered, by some tests) but are no longer reachable via the container. **The only missing
  piece for a working login flow is routes** — Phase 3 (`T58`+), not started.

## 9. Active Risks / Open Questions

| Issue | Impact | Blocks `T56`? | Owner |
|---|---|---|---|
| Authorization-recording gap recurred **4** consecutive batches (`T52`, `T53`, `T54`, `T55`) despite every QA Decision naming it | Real risk of a 5th recurrence on `T56` | Yes, in spirit — `T56` should not start without this actually being fixed as a process, not re-disclosed again | Project Manager / whoever authorizes `T56` |
| `role_permissions` exact matrix (`T66`) needs project-owner sign-off before that migration is written | Blocks `T66` only | No | Project owner |
| `docs/ProjectStatus.md` / `docs/ArchitectureScorecard.md` stuck at pre-Stage-3 status | Documentation debt, repeatedly flagged, never fixed | No | Documentation Manager (whenever a dedicated pass is authorized) |

**Resolved since the previous version of this file, removed from this table:** `T55`'s own
branch/commit/PR gap — PR #15 merged (`b094436`); no longer an active risk. (The authorization-
*recording* gap, distinct from the git-provenance gap, is **not** resolved — see the first row above.)

Already-resolved items (`T52`/`T53`/`T54`'s own branch-commit gaps, `T49`'s migration-verification
gap, etc.) are intentionally **not** repeated here — see the relevant `ImplementationLog`/
`SessionReport` entries for that history.

## 10. Governance Rules

From `AI_BOOTSTRAP.md`, `PROJECT_WORKFLOW.md`, and `docs/prompts/*.md` — summarized, not restated in
full:

- **Repository-First Rule:** the repository is always the source of truth; never rely on previous
  chat history; rebuild context from the repository before doing anything.
- **Every implementation cycle begins with the Project Manager**, who identifies the next unfinished
  task from `IMPLEMENTATION_QUEUE.md`, verifies prerequisites, and waits for explicit project-owner
  approval — authorization must be **written into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`
  before implementation begins**, not reconstructed afterward (a rule this project's own history has
  now violated **four** times running: `T52`, `T53`, `T54`, `T55`).
- **Backend Developer** must reconstruct state, **summarize understanding, and wait for explicit
  approval of that summary** (`docs/prompts/BackendDeveloper.md` §5) before writing any code — a
  distinct checkpoint from project-owner task authorization.
- **One task (or an explicitly-scoped combined/expanded batch) per implementation batch** — minimal
  scope, no "while I'm in here" additions.
- **QA Reviewer** independently reviews and renders a **QA Decision** — `Approved` /
  `Approved with comments` / `Rework required` — never pre-filled by the implementer. "An honest
  unchecked box beats a falsely checked one."
- **Documentation Manager** performs closeout **only after** a QA Decision of `Approved`/`Approved
  with comments` exists — never before.
- **`main` is protected.** Branch strategy: `feature/<name>` (or `docs/<topic>`) off `main` → commit
  → PR → merge (standard merge commit, no squash/rebase) → delete branch → update local `main`.
- **Do not start the next task before the previous task reaches a clean merged checkpoint** — `T55`
  now satisfies this; `T56` must not start until it independently earns the same standard.
- **Preserve historical governance deviations rather than rewriting history** — corrections are
  appended with a date, originals are never silently edited or deleted. `T55`'s own record is the
  sharpest example yet in this repository: an intermediate documentation pass *itself* overclaimed
  that an authorization had been recorded before implementation began, and that overclaim was later
  found, disclosed, and corrected — without erasing either the original wrong claim or the underlying
  true finding.
- **Task IDs are immutable** — a scope change gets a new ID, never a redefinition of an old one.

## 11. Safe Breakpoint

**SAFE TO STOP: YES.**

`T55` is genuinely complete: implementation merged, both QA decisions recorded and preserved (the
original `Rework required` verbatim, the follow-up `Approved with comments` as final disposition),
documentation/governance closeout merged (PR #15, `b094436`), `main`/`origin/main` synchronized,
working tree clean. No task implementation or documentation is sitting uncommitted or unmerged
anywhere in this repository as of this verification. `T56` has not been started, authorized, or
touched — it correctly remains open work for a future session, not a half-finished one.

The only change in this exact session was this checkpoint file itself, updated in place per its own
maintenance rules (§14) — not committed as part of this pass, since no commit/push was authorized;
not committing it does not compromise the breakpoint, since it carries no project state of its own,
only a snapshot description of state that already exists, verified, on `main`.

**Next cycle begins with: T56** — **not authorized.** Do not start it without an explicit go-ahead
recorded the right way (see §5, §10) — four prior batches show what happens when that discipline
slips.

## 12. AI Continuation Instructions

Before doing anything:

1. Read this file (`PROJECT_CHECKPOINT.md`).
2. Verify the live Git state yourself (`git status`, `git branch --show-current`, `git log`,
   `git rev-parse HEAD origin/main`) — do not trust this file's numbers without re-checking; they are
   only as fresh as this file's own §15.
3. Read `T56`'s row in `IMPLEMENTATION_QUEUE.md` directly.
4. Read the relevant `PROJECT_STATE.json` state directly.
5. Verify authorization for `T56` — in the repository, not from this file's summary and not from any
   prior conversation.
6. Do not assume `T56` is authorized just because `T55` is `Done`.
7. Follow the project's role workflow (`PROJECT_WORKFLOW.md` §3, §7).

**Which role should act next: Project Manager.** `T55` needs no further action from any role. The
next real work is `T56`, and per this project's own lifecycle, that starts with the Project Manager
identifying it, verifying `T55` is genuinely satisfied (it is), and — critically — getting and
*actually recording* explicit project-owner authorization in
`IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` **before** any Backend Developer work begins. Four
consecutive batches have now failed at exactly this step; breaking that pattern is the single most
important thing whoever picks up `T56` can do differently.

## 13. Authoritative Files

| File | Authoritative for |
|---|---|
| `AI_BOOTSTRAP.md` | Non-negotiable rules, required-reading order, new-session protocol |
| `PROJECT_WORKFLOW.md` | The full development lifecycle, branch/PR/git workflow, AI role definitions, documentation ownership |
| `PROJECT_STATE.json` | Machine-readable point-in-time snapshot (stage, tests, git state) |
| `IMPLEMENTATION_QUEUE.md` | The task backlog — what's planned, in what order, current status per task |
| `docs/AI_HANDOVER.md` | Deep narrative handover — completed work, open issues, what to do next |
| `docs/Roadmap.md` | Stage-by-stage roadmap pointer (defers to `IMPLEMENTATION_QUEUE.md` for detail) |
| `docs/SessionReport.md` | Chronological session-by-session summary |
| `docs/ImplementationLog/Stage3/Phase2.md` | Full technical execution record for `T52`–`T55` (and future Phase 2 batches) |
| `docs/ImplementationLog/README.md` | The ImplementationLog standard itself — Canonical Document Roles, Documentation Ownership, QA Decision meaning |
| `docs/prompts/*.md` | Canonical per-role AI prompts (Project Manager, Backend Developer, QA Reviewer, Documentation Manager) |
| `docs/Stage3_Backend_Handoff.md` | File-by-file implementation brief for Stage 3's remaining phases |

## 14. Checkpoint Maintenance Rules

- This file represents **current state**, not historical narrative — it is rewritten in place, not
  appended to.
- Update it whenever a task reaches a meaningful lifecycle boundary (implemented, QA-decided,
  merged, closed out).
- Update it after every merge/closeout.
- **Never** claim a task is `Done` merely because code exists — a task is `Done` only when its QA
  Decision(s) and documentation closeout are both actually merged into `main`.
- **Never** claim QA approval unless the QA Decision is recorded in the repository (an
  `ImplementationLog` phase log), not merely asserted.
- **Never** claim a clean breakpoint while uncommitted or unmerged task work remains — see §11's
  exact standard.
- **Never** claim an authorization was "recorded before implementation began" without a commit to
  point to — `T55`'s own history in this repository is the cautionary example.
- Preserve historical detail in `docs/ImplementationLog/`/`docs/SessionReport.md` rather than
  bloating this file — this file links out, it doesn't duplicate.
- **Always** verify Git state directly (`git status`/`git log`/`git rev-parse`) before declaring this
  checkpoint current — never trust a prior version of this file's own numbers without re-checking.

## 15. Checkpoint Integrity

- **Last verified commit:** `b094436` (`main`, synchronized with `origin/main`)
- **Last verified branch:** `main`
- **Working tree status:** clean
- **Verification performed:** `git status`; `git branch --show-current`; `git rev-parse HEAD
  origin/main`; `git log --oneline --decorate -8`; `git show --stat --oneline` on `b094436`,
  `86a3d5d`, and `f070e28` (confirmed exact file lists for the merge and both constituent commits);
  direct read of `T55`/`T56` rows in `IMPLEMENTATION_QUEUE.md` on `main`; direct read of
  `PROJECT_STATE.json`'s `git` block and `currentStage.note` on `main`; direct read of both QA
  Decision sections (original and follow-up) in `docs/ImplementationLog/Stage3/Phase2.md` on `main`;
  full backend suite re-run (`uv run pytest -q`, 380/380, live Postgres); `ruff`/`black`/boot smoke
  test re-run, all clean.
- **Generated/updated by:** Documentation Manager
- **Date:** 2026-08-10
