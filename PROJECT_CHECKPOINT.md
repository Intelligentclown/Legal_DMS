# Legal_DMS — Current Project Checkpoint

*A concise current-state snapshot for any AI picking up this project. Not an implementation log —
see [`docs/ImplementationLog/`](docs/ImplementationLog/) for execution history and
[`docs/SessionReport.md`](docs/SessionReport.md) for session-by-session narrative. If this file and
either of those disagree, trust the live repository (`git log`/`git status`), not this file — then
fix this file.*

## 1. Last Verified State

- **Verified:** 2026-08-10, this session — directly against `git`, not from prior conversation.
- **Current branch:** `main`
- **HEAD commit:** `512c91e`
- **`origin/main`:** `512c91e` — synchronized with local `main`.
- **Working tree:** clean.
- **Latest relevant merge/PR:** PR #13, `docs/t54-closeout` → `512c91e` ("Merge pull request #13
  from Intelligentclown/docs/t54-closeout") — `T54`'s documentation closeout. Confirmed via
  `git show --stat --oneline HEAD`: exactly the six documentation files (`IMPLEMENTATION_QUEUE.md`,
  `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/ImplementationLog/Stage3/Phase2.md`,
  `docs/Roadmap.md`, `docs/SessionReport.md`), no source or test file.

**Correction from the previous version of this file:** that version was written while `T54`'s
documentation closeout (`docs/t54-closeout`, commit `0577960`) was still pushed but unmerged. It has
since been merged via PR #13 → `512c91e`. `main` now fully reflects `T54` as `Done` — verified by
reading `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, and
`docs/ImplementationLog/Stage3/Phase2.md` directly on `main`, not assumed from that prior state.

## 2. Current Stage

- **Stage:** 3 — Authentication & Authorization (`docs/Roadmap.md`, `IMPLEMENTATION_QUEUE.md`).
- **Phase:** 2 — wiring auth into the request pipeline (`T52`–`T57`).
- **Overall project progress:** Stages 0–2 complete (infrastructure/framework/schema only, 0
  business features by design). Stage 3 is the first business-adjacent feature, in progress.
- **Completed task range:** `T41`–`T54` — code merged **and** documentation closeout merged, both
  confirmed on `main`.
- **Next unfinished task:** `T55` — **not authorized**.

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
| **T54** | **Done** | `RequirePermission(...)` FastAPI dependency factory | code+reconciliation PR #12 (`6396f6b`); doc closeout PR #13 (`512c91e`) |

Full technical detail for `T52`–`T54` lives in `docs/ImplementationLog/Stage3/Phase2.md` — not
duplicated here.

## 4. Current Task

**There is no open current task.** `T54` (the last one worked) is fully `Done`; `T55` has not
started. This section documents `T54`'s final, closed state for reference:

- **Task:** `T54` — `RequirePermission(...)` FastAPI dependency factory (closes Stage 2.5's F11).
- **Authorization status:** given by the project owner in a Project Manager conversation; **not**
  recorded in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation began — the third
  consecutive batch with this exact gap (`T52`, `T53`, `T54`). **This governance finding is
  preserved as historical record and is not erased by `T54`'s closeout** —
  `docs/ImplementationLog/Stage3/Phase2.md`'s T54 batch (both the original and follow-up QA
  Decisions) states this explicitly.
- **Implementation status:** complete, merged into `main` (`presentation/api/deps.py` +
  `get_authorization_service()`; 5 tests in `tests/unit/test_auth.py`'s `TestRequirePermission`).
- **QA status — final disposition:** two decisions exist in `docs/ImplementationLog/Stage3/Phase2.md`,
  both preserved, neither overwriting the other:
  1. **Original (2026-08-08): `Rework required`** — process grounds only, explicitly "no code
     changes required." Preserved verbatim as the historical record.
  2. **Follow-up (2026-08-10): `Approved with comments`** — the **final QA disposition**, rendered
     once the branch/commit/PR gap closed (`feature/stage3-t54-require-permission` → `dbd6724` → PR
     #12 → `6396f6b`). Findings 2/3 (missing phase-log entry, no branch/commit/PR) resolved; finding
     1 (authorization not pre-recorded) remains open governance history, not erased.
- **Documentation status:** fully synchronized and merged into `main` (PR #13, `512c91e`).
- **Dependencies:** `T50` (done); the Backend Developer `docs/prompts/BackendDeveloper.md` §5
  checkpoint was performed and approved before implementation — the first Phase 2 batch to do so.
- **Is `T54` finished?** **Yes — fully.** Code, QA, and documentation are all merged into `main`.
  (Distinct from `T55`'s status below — see §5.)

## 5. Next Cycle

- **Next task:** `T55` — wire `JwtAuthenticationProvider`/`RbacAuthorizationService` into
  `configure_container()`, replacing the `Anonymous`/`Permissive` Stage-1 defaults.
- **Why it's next:** `IMPLEMENTATION_QUEUE.md`'s task table lists `T55`'s dependencies as `T52, T53`
  — both `Done` and merged on `main`. `T54` is thematically related (it's the first real caller of
  `AuthorizationService`) but not a listed hard dependency.
- **Dependencies:** `T52` (done), `T53` (done).
- **Is it authorized? NO — verified directly, not assumed.** `IMPLEMENTATION_QUEUE.md`'s `T55` row
  on `main` carries no `Done`/authorization marker (plain task description only); `PROJECT_STATE.json`'s
  `currentStage.note` explicitly ends "`T55-T57 remain not started, not authorized`." No
  project-owner authorization for `T55` exists anywhere in the repository as of this checkpoint.
- **What must happen before implementation begins:**
  1. The project owner authorizes `T55` — and, per the standing recommendation repeated in
     `T52`/`T53`/`T54`'s own QA Decisions (three consecutive violations so far), that authorization
     must be **written into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation
     starts**, not after.
  2. The Backend Developer role performs the `docs/prompts/BackendDeveloper.md` §5 checkpoint
     (reconstruct state, summarize understanding, wait for explicit approval of that summary) before
     writing any code.

**`T54` being finished and `T55` being unauthorized are two separate facts — do not conflate
them.** `T54`'s completion does not itself authorize `T55`; that pattern (assuming the next task is
authorized because the previous one just closed) is exactly what this project's own rules warn
against.

## 6. Repository State

- **`main`:** `512c91e`
- **`origin/main`:** `512c91e` (synchronized)
- **Latest merge commit:** `512c91e` (PR #13, `docs/t54-closeout`)
- **Latest feature branch relevant to the completed task:** `feature/stage3-t54-require-permission`
  (`dbd6724`) and `docs/t54-closeout` (`0577960`) — both merged, both safe to delete if not already.
- **Working-tree status:** clean.
- **Uncommitted files:** none.
- **Any task implementation sitting uncommitted?** No.
- **Any task documentation sitting unmerged?** No — the `docs/t54-closeout` gap this file previously
  flagged is closed; `main` now carries everything.
- **PR verifiable locally?** Yes — `git log --oneline --decorate -5` shows `512c91e (HEAD -> main,
  origin/main, origin/HEAD) Merge pull request #13 from Intelligentclown/docs/t54-closeout`, and
  `git show --stat --oneline HEAD` confirms its file list matches exactly what `T54`'s closeout
  commit (`0577960`) contained.

## 7. Test / Quality Status

Code is unchanged since the last verification (`512c91e` only added documentation on top of
`6396f6b` — confirmed via `git show --stat`), but the suite was **re-run this session on the current
`HEAD`**, not assumed carried-over:

- **Backend tests:** `uv run pytest -q` — **374 passed, 0 failed, 0 skipped** (includes
  Postgres-backed integration tests — `legal_dms_postgres` container confirmed healthy via
  `docker ps`).
- **Frontend tests:** `npm test -- --run` (Vitest) — **9 passed, 0 failed** (3 test files) — carried
  from the prior verification pass; unaffected by a documentation-only merge.
- **Lint:** `uv run ruff check src tests alembic` — clean (prior verification; no source file
  changed since).
- **Format:** `uv run black --check src tests alembic` — clean (191 files unchanged; prior
  verification, no source file changed since).
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds (prior verification).
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
  `Depends(RequirePermission("matters:read"))` — composes `CurrentUserDep` and a new
  `get_authorization_service()` resolver. **No route calls it yet** — no route exists yet at all
  (Phase 3, `T58`+).
- **Dependency injection:** `JwtAuthenticationProvider`/`RbacAuthorizationService` are **NOT yet
  registered in `configure_container()`** — the running app still resolves the Stage-1 placeholder
  defaults (`AnonymousAuthenticationProvider`/`PermissiveAuthorizationService`) at runtime. Real
  wiring is `T55`.
- **Placeholder vs. real:** every auth *building block* (hashing, JWT, `AuthService`, both real
  provider/service implementations, the permission dependency) is real and tested — and, as of this
  checkpoint, fully merged. **Nothing is wired together into the live request pipeline yet** — that's
  the entire remaining scope of Phase 2 (`T55`–`T57`) and Phase 3 (`T58`+, routes).

## 9. Active Risks / Open Questions

| Issue | Impact | Blocks `T55`? | Owner |
|---|---|---|---|
| Authorization-recording gap recurred 3 consecutive batches (`T52`, `T53`, `T54`) despite each QA Decision naming it | Real risk of a 4th recurrence on `T55` | Yes, in spirit — `T55` should not start without this being done correctly first | Project Manager / whoever authorizes `T55` |
| `role_permissions` exact matrix (`T66`) needs project-owner sign-off before that migration is written | Blocks `T66` only | No | Project owner |
| `docs/ProjectStatus.md` / `docs/ArchitectureScorecard.md` stuck at pre-Stage-3 status | Documentation debt, repeatedly flagged, never fixed | No | Documentation Manager (whenever a dedicated pass is authorized) |

**Resolved since the previous version of this file, removed from this table:** `docs/t54-closeout`
being pushed but unmerged — PR #13 merged (`512c91e`); no longer an active risk.

Already-resolved items (T52/T53's own branch-commit gaps, T49's migration-verification gap, etc.)
are intentionally **not** repeated here — see the relevant `ImplementationLog`/`SessionReport`
entries for that history.

## 10. Governance Rules

From `AI_BOOTSTRAP.md`, `PROJECT_WORKFLOW.md`, and `docs/prompts/*.md` — summarized, not restated in
full:

- **Repository-First Rule:** the repository is always the source of truth; never rely on previous
  chat history; rebuild context from the repository before doing anything.
- **Every implementation cycle begins with the Project Manager**, who identifies the next unfinished
  task from `IMPLEMENTATION_QUEUE.md`, verifies prerequisites, and waits for explicit project-owner
  approval — authorization must be **written into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`
  before implementation begins**, not reconstructed afterward (a rule this project's own history has
  violated three times running: `T52`, `T53`, `T54`).
- **Backend Developer** must reconstruct state, **summarize understanding, and wait for explicit
  approval of that summary** (`docs/prompts/BackendDeveloper.md` §5) before writing any code — a
  distinct checkpoint from project-owner task authorization.
- **One task (or an explicitly-scoped combined batch) per implementation batch** — minimal scope,
  no "while I'm in here" additions.
- **QA Reviewer** independently reviews and renders a **QA Decision** — `Approved` /
  `Approved with comments` / `Rework required` — never pre-filled by the implementer. "An honest
  unchecked box beats a falsely checked one."
- **Documentation Manager** performs closeout **only after** a QA Decision of `Approved`/`Approved
  with comments` exists — never before.
- **`main` is protected.** Branch strategy: `feature/<name>` (or `docs/<topic>`) off `main` → commit
  → PR → merge (standard merge commit, no squash/rebase) → delete branch → update local `main`.
- **Do not start the next task before the previous task reaches a clean merged checkpoint** — `T54`
  now satisfies this; `T55` must not start until it independently earns the same standard.
- **Preserve historical governance deviations rather than rewriting history** — corrections are
  appended with a date, originals are never silently edited or deleted. (`T54`'s original `Rework
  required` decision and its authorization-not-pre-recorded finding are the live example of this
  rule in this exact repository.)
- **Task IDs are immutable** — a scope change gets a new ID, never a redefinition of an old one.

## 11. Safe Breakpoint

**SAFE TO STOP: YES.**

`T54` is genuinely complete: implementation merged, both QA decisions recorded and preserved (the
original `Rework required` verbatim, the follow-up `Approved with comments` as final disposition),
documentation closeout merged (PR #13, `512c91e`), `main`/`origin/main` synchronized, working tree
clean. No task implementation or documentation is sitting uncommitted or unmerged anywhere in this
repository as of this verification. `T55` has not been started, authorized, or touched — it correctly
remains open work for a future session, not a half-finished one.

The only change in this exact session was this checkpoint file itself, which is intentionally left
**uncommitted** (untracked) per this task's own instructions — not committing it does not compromise
the breakpoint, since it carries no project state of its own, only a snapshot description of state
that already exists, verified, on `main`.

**Next cycle begins with: T55** — **not authorized.** Do not start it without an explicit go-ahead
recorded the right way (see §5, §10).

## 12. AI Continuation Instructions

Before doing anything:

1. Read this file (`PROJECT_CHECKPOINT.md`).
2. Verify the live Git state yourself (`git status`, `git branch --show-current`, `git log`,
   `git rev-parse HEAD origin/main`) — do not trust this file's numbers without re-checking; they are
   only as fresh as this file's own §15.
3. Read `T55`'s row in `IMPLEMENTATION_QUEUE.md` directly.
4. Read the relevant `PROJECT_STATE.json` state directly.
5. Verify authorization for `T55` — in the repository, not from this file's summary and not from any
   prior conversation.
6. Do not assume `T55` is authorized just because `T54` is `Done`.
7. Follow the project's role workflow (`PROJECT_WORKFLOW.md` §3, §7).

**Which role should act next: Project Manager.** `T54` needs no further action from any role. The
next real work is `T55`, and per this project's own lifecycle, that starts with the Project Manager
identifying it, verifying `T52`/`T53` are genuinely satisfied (they are), and — critically — getting
and *recording* explicit project-owner authorization in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`
**before** any Backend Developer work begins, breaking the three-batch pattern this checkpoint's
§9/§10 both flag.

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
| `docs/ImplementationLog/Stage3/Phase2.md` | Full technical execution record for `T52`–`T54` (and future Phase 2 batches) |
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
  Decision and documentation closeout are both actually merged into `main`.
- **Never** claim QA approval unless the QA Decision is recorded in the repository (an
  `ImplementationLog` phase log), not merely asserted.
- **Never** claim a clean breakpoint while uncommitted or unmerged task work remains — see §11's
  exact standard.
- Preserve historical detail in `docs/ImplementationLog/`/`docs/SessionReport.md` rather than
  bloating this file — this file links out, it doesn't duplicate.
- **Always** verify Git state directly (`git status`/`git log`/`git rev-parse`) before declaring this
  checkpoint current — never trust a prior version of this file's own numbers without re-checking.

## 15. Checkpoint Integrity

- **Last verified commit:** `512c91e` (`main`, synchronized with `origin/main`)
- **Last verified branch:** `main`
- **Working tree status:** clean (this file itself is the sole untracked entry)
- **Verification performed:** `git status`; `git branch --show-current`; `git rev-parse HEAD
  origin/main`; `git log --oneline --decorate -5`; `git show --stat --oneline HEAD` (confirmed PR
  #13's file list matches `T54`'s closeout exactly); direct read of `T54`/`T55` rows in
  `IMPLEMENTATION_QUEUE.md` on `main`; direct read of `PROJECT_STATE.json`'s `git` block and
  `currentStage.note` on `main`; direct read of both QA Decision sections (original and follow-up)
  in `docs/ImplementationLog/Stage3/Phase2.md` on `main`; full backend suite re-run
  (`uv run pytest -q`, 374/374, live Postgres).
- **Generated/updated by:** Documentation Manager
- **Date:** 2026-08-10
