# Legal_DMS — Current Project Checkpoint

*A concise current-state snapshot for any AI picking up this project. Not an implementation log —
see [`docs/ImplementationLog/`](docs/ImplementationLog/) for execution history and
[`docs/SessionReport.md`](docs/SessionReport.md) for session-by-session narrative. If this file and
either of those disagree, trust the live repository (`git log`/`git status`), not this file — then
fix this file.*

## 1. Last Verified State

- **Verified:** 2026-08-13, this session — directly against `git`/`gh`, not from prior conversation.
- **Current branch:** `main`
- **HEAD commit:** `472f7cb`
- **`origin/main`:** `472f7cb` — synchronized with local `main`.
- **Working tree:** **not clean as of this update** — see the note immediately below.
- **Latest relevant merge/PR:** PR #20, `feature/stage3-t57-401-403` → `472f7cb` ("Merge pull
  request #20 from Intelligentclown/feature/stage3-t57-401-403") — carries two commits:
  `65dd563` ("docs(project): T57 architecture clarification and authorization" — governance/
  analysis only, no code) and `7c9fc3a` ("feat(auth): distinguish unauthorized and forbidden
  requests" — `T57`'s implementation). `gh pr view 20` independently confirms `MERGED`, its own
  description cross-checked against directly re-run test/lint/boot results — all matching.

**Important note on working-tree state:** this checkpoint is itself part of `T57`'s documentation
closeout pass, currently **uncommitted** in the working tree, along with `IMPLEMENTATION_QUEUE.md`,
`PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/ImplementationLog/Stage3/Phase2.md`,
`docs/Roadmap.md`, and `docs/SessionReport.md`. `T57`'s **code** is fully merged (`472f7cb`); `T57`'s
**documentation record** of that fact is drafted but not yet committed or pushed, per explicit
instruction not to commit/push/PR as part of this pass. See §11.

## 2. Current Stage

- **Stage:** 3 — Authentication & Authorization (`docs/Roadmap.md`, `IMPLEMENTATION_QUEUE.md`).
- **Phase:** 2 — wiring auth into the request pipeline (`T52`–`T57`) is **complete in full**
  (code-wise; documentation closeout pending, see §11). Phase 3 (routes, `T58`+) has not started.
- **Overall project progress:** Stages 0–2 complete (infrastructure/framework/schema only, 0
  business features by design). Stage 3 is the first business-adjacent feature; Phase 0–2 all done.
- **Completed task range (code merged into `main`):** `T41`–`T57`.
- **Documentation closeout status:** `T41`–`T56` fully reconciled and merged. `T57`'s closeout is
  drafted (this pass) but not yet committed/merged — see §11.
- **Next unfinished task:** `T58` — **not authorized**.

## 3. Completed Tasks

| Task | Status | Purpose | Commit/PR |
|---|---|---|---|
| T41–T51 | Done | Phase 0/1 — prerequisite fix, auth foundation, credential/token lifecycle | see `docs/ImplementationLog/Stage3/Phase0.md`/`Phase1.md` |
| T52 | Done | `JwtAuthenticationProvider` — real `AuthenticationProvider` | PR #9 (`baed936`) |
| T53 | Done | `RbacAuthorizationService` — real `AuthorizationService` | code PR #10 (`a103dca`); doc closeout PR #11 (`25a6078`) |
| T54 | Done | `RequirePermission(...)` FastAPI dependency factory | code+reconciliation PR #12 (`6396f6b`); doc closeout PR #13 (`512c91e`) |
| T55 | Done | Request-scoped `Depends()` wiring of real providers in `deps.py` | code+governance PR #15 (`b094436`); doc closeout PR #16 (`4e03e79`) |
| T56 | Done | Real bearer-token extraction (`get_bearer_token()`) in `get_current_user()` | authorization PR #17 (`89a3a5e`); implementation PR #18 (`d69c4eb`); doc closeout PR #19 (`47c854f`) |
| **T57** | **Code Done; doc closeout drafted, uncommitted** | Distinguish `UnauthorizedError`/401 (unauthenticated) from `ForbiddenError`/403 (authenticated-but-unpermitted) in `RequirePermission` | authorization commit `65dd563` + implementation `7c9fc3a`, both PR #20 (`472f7cb`) |

Full technical detail for `T52`–`T57` lives in `docs/ImplementationLog/Stage3/Phase2.md` — not
duplicated here.

## 4. Current Task

**Task:** `T57` — distinguish unauthorized (401) from forbidden (403) in `RequirePermission`.

- **Authorization status:** `T57`'s original test-only wording (including a `configure_container()`
  criterion `T55` had already made obsolete) was corrected by a pre-implementation architecture
  clarification, then authorized (Option 1: `_require_permission` checks `is_authenticated` before
  calling `AuthorizationService`) as its own dedicated commit (`65dd563`) **before** the
  implementation commit (`7c9fc3a`) existed — the **second** consecutive Stage 3 Phase 2 batch to
  satisfy this discipline, after `T56`. Confirmed by direct commit-timestamp comparison
  (`65dd563`: 15:13:48; `7c9fc3a`: 15:48:36, same day), not assumed.
- **Implementation status:** complete, merged into `main` (`presentation/api/deps.py`'s
  `_require_permission` gains an `is_authenticated` short-circuit; 3 new tests + 1 updated in
  `tests/unit/test_auth.py`). `AuthorizationService`'s port, `RbacAuthorizationService`, and
  `PermissiveAuthorizationService` were **not** modified.
- **QA status:** **Approved with comments** — no technical defects found. The comment preserves, as
  a non-blocking historical/forward-looking observation (already named in `65dd563`'s own
  authorization text, not a new QA finding), the deferral of true `TestClient`-level HTTP
  verification (a real request, a real bearer token, an actual `401`/`403` response) to `T58`+ —
  no protected route exists yet for such a test to exercise.
- **Documentation status:** drafted this session (`docs/ImplementationLog/Stage3/Phase2.md`'s T57
  batch, `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/Roadmap.md`,
  `docs/SessionReport.md`, this file) but **not yet committed or pushed** — see §11.
- **Dependencies:** `T55`, `T56` (both done).
- **Is `T57` finished?** **Code: yes, fully merged.** **Phase 2 as a whole: complete in code.**
  **Documentation: drafted, pending its own commit/PR** — not yet a closed loop the way `T52`–`T56`
  each eventually became.

## 5. Next Cycle

- **Next task:** `T58` — `POST /api/v1/auth/login` (email + password in, access + refresh tokens
  out, or a structured 401) — the first Phase 3 (routes) task.
- **Why it's next:** `IMPLEMENTATION_QUEUE.md`'s task table lists `T58`'s dependency as `T57` — now
  `Done` (code) on `main`, and the last task of Phase 2.
- **Dependencies:** `T57` (done, code; doc closeout pending).
- **Is it authorized? NO — verified directly, not assumed.** `IMPLEMENTATION_QUEUE.md`'s `T58` row
  on `main` carries no `Done`/authorization marker. No project-owner authorization for `T58` exists
  anywhere in the repository as of this checkpoint.
- **What must happen before implementation begins:**
  1. `T57`'s own documentation closeout (this pass) needs its own commit and PR, merged into `main`
     — mirroring exactly how `T52`–`T56` each eventually closed. See §11 for the exact file list.
  2. The project owner authorizes `T58` — and, since `T56`/`T57` have now **both** demonstrated this
     can be done correctly (authorization committed *before* implementation, two batches running),
     whoever authorizes `T58` should follow that pattern.
  3. The Backend Developer role performs the `docs/prompts/BackendDeveloper.md` §5 checkpoint before
     writing any code.
  4. `T58` is also the first point where the `TestClient`-level HTTP verification `T56`'s and `T57`'s
     shared QA comment named becomes buildable — worth planning for as part of `T58`'s own test
     coverage, not a separate task.

**`T57`'s code being merged and `T58` being unauthorized are two separate facts — do not conflate
them.** Nor does `T57`'s code merge, on its own, mean `T57` is fully closed — its documentation
record still needs its own commit/PR (§11).

## 6. Repository State

- **`main`:** `472f7cb`
- **`origin/main`:** `472f7cb` (synchronized)
- **Latest merge commit:** `472f7cb` (PR #20, `feature/stage3-t57-401-403`)
- **Latest feature branch relevant to the completed task:** `feature/stage3-t57-401-403`
  (`65dd563`, `7c9fc3a`) — merged, safe to delete if not already.
- **Working-tree status:** **not clean** — seven documentation/project-management files modified in
  place by this session's `T57` closeout pass, none committed (`IMPLEMENTATION_QUEUE.md`,
  `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/ImplementationLog/Stage3/Phase2.md`,
  `docs/Roadmap.md`, `docs/SessionReport.md`, `PROJECT_CHECKPOINT.md` — this file).
- **Any task implementation sitting uncommitted?** No — `T57`'s code is fully committed and merged.
- **Any task documentation sitting uncommitted?** **Yes — this session's own `T57` closeout**, per
  explicit instruction not to commit/push/PR as part of this pass.
- **PR verifiable locally and via `gh`?** Yes — `git log --oneline --decorate -10` shows `472f7cb
  (HEAD -> main, origin/main, origin/HEAD) Merge pull request #20 …`, and `gh pr view 20` confirms
  `MERGED` with a description matching the technical claims recorded here.

## 7. Test / Quality Status

All figures **re-verified this session, directly on `main` at `472f7cb`**:

- **Backend tests:** `uv run pytest -q` — **386 passed, 0 failed, 0 skipped** (includes
  Postgres-backed integration tests). PR #20's own description additionally cites 127/127
  integration tests specifically — consistent with, not contradicted by, this total.
- **Frontend tests:** carried from the prior verification pass (9 passed) — unaffected by `T57`
  (backend-only change).
- **Lint:** `uv run ruff check src tests alembic` — clean.
- **Format:** `uv run black --check src tests alembic` — clean.
- **Boot smoke test:** `python -c "from app.main import app"` — succeeds.
- **Database/integration status:** live Postgres reachable and healthy.
- **Environmental issues:** none.

## 8. Current Architecture Snapshot

- **`AuthenticationProvider` (Stage 1 port):** real implementation `JwtAuthenticationProvider`
  (`T52`), constructed request-scoped in `deps.py` (`T55`), fed a real bearer token (`T56`).
- **`AuthorizationService` (Stage 1 port):** real implementation `RbacAuthorizationService` (`T53`),
  also request-scoped (`T55`) — **untouched by `T57`**.
- **`AuthService` (`T50`):** `authenticate`/`issue_tokens`/`refresh`/`revoke`.
- **`RequirePermission(...)` (`T54`, extended by `T57`):** the dependency factory now distinguishes
  **`UnauthorizedError`/401** (caller not authenticated at all — checked first, before
  `AuthorizationService` is even invoked) from **`ForbiddenError`/403** (authenticated but lacking
  the specific permission — still `AuthorizationService`'s call, unchanged). **No route calls it
  yet** — no route exists anywhere in the app (Phase 3, `T58`+).
- **The full identity/permission chain is now real and correctly differentiated end-to-end at the
  dependency level:** header → `get_bearer_token()` (`T56`) → `AuthenticationProvider` → `CurrentUser`
  → `RequirePermission`'s `is_authenticated` check (`T57`, 401) → `AuthorizationService.require_permission()`
  (`T53`, 403) → allow. **Stage 3 Phase 2 is complete.** The only missing piece for a working,
  request-driven login/permission flow is **routes** — none exist yet. That's Phase 3.

## 9. Active Risks / Open Questions

| Issue | Impact | Blocks `T58`? | Owner |
|---|---|---|---|
| `T57`'s own documentation closeout (this session's edits) is drafted but uncommitted | The repository's committed state doesn't yet reflect `T57` as fully closed, even though its code is merged | Not a hard blocker for `T58`'s code dependency (`T57` is merged), but this project's own rule against starting the next task before the previous one reaches a clean merged checkpoint applies | Whoever has commit/push authorization — needs to commit and PR the seven files listed in §6 |
| Deferred `TestClient`-level end-to-end HTTP verification (401/403 against a real route) — named by both `T56` and `T57`'s QA decisions | Not yet buildable (no route exists); becomes buildable at `T58` | No — explicitly deferred, not blocking | Whoever implements `T58`, as part of its own test coverage |
| `role_permissions` exact matrix (`T66`) needs project-owner sign-off before that migration is written | Blocks `T66` only | No | Project owner |
| `docs/ProjectStatus.md` / `docs/ArchitectureScorecard.md` stuck at pre-Stage-3 status | Documentation debt, repeatedly flagged, never fixed | No | Documentation Manager (whenever a dedicated pass is authorized) |

**Resolved since the previous version of this file, removed from this table:** `T56`'s own
documentation-closeout gap — PR #19 merged (`47c854f`); no longer active. The four-batch
authorization-recording gap (`T52`–`T55`) — `T56` and `T57` have now both broken the pattern; not
removed from history (still recorded in `Phase2.md`), but no longer listed here as an *active* risk
in the same way, since two consecutive successes is a real trend, not a fluke.

## 10. Governance Rules

From `AI_BOOTSTRAP.md`, `PROJECT_WORKFLOW.md`, and `docs/prompts/*.md` — summarized, not restated in
full:

- **Repository-First Rule:** the repository is always the source of truth; never rely on previous
  chat history; rebuild context from the repository before doing anything.
- **Every implementation cycle begins with the Project Manager**, who identifies the next unfinished
  task, verifies prerequisites, and waits for explicit project-owner approval — authorization must be
  **written into `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` before implementation begins**.
  Violated four times running (`T52`–`T55`); `T56` and `T57` are now two consecutive batches that got
  this right — real, repeated proof this discipline is achievable.
- **Backend Developer** must reconstruct state, **summarize understanding, and wait for explicit
  approval of that summary** (`docs/prompts/BackendDeveloper.md` §5) before writing any code.
- **One task (or an explicitly-scoped batch) per implementation batch** — minimal scope.
- **QA Reviewer** independently reviews and renders a **QA Decision** — `Approved` /
  `Approved with comments` / `Rework required` — never pre-filled by the implementer.
- **Documentation Manager** performs closeout **only after** a QA Decision of `Approved`/`Approved
  with comments` exists — never before.
- **`main` is protected.** Branch strategy: `feature/<name>` (or `docs/<topic>`) off `main` → commit
  → PR → merge → delete branch → update local `main`.
- **Do not start the next task before the previous task reaches a clean merged checkpoint** — `T57`'s
  code satisfies this; its documentation record does not yet (see §11); `T58` must not start until
  both do.
- **Preserve historical governance deviations rather than rewriting history** — corrections are
  appended with a date, originals never silently edited or deleted. `T57`'s own record additionally
  shows the *positive* case: a genuinely correct architecture-clarification-then-authorization
  sequence, recorded plainly, not needing any correction at all.
- **Task IDs are immutable.**

## 11. Safe Breakpoint

**SAFE TO STOP: NO.**

`T57`'s **code** is genuinely complete and merged (`472f7cb`), technically approved by QA, and
completes Stage 3 Phase 2 in full. But `T57`'s **documentation closeout — this exact session's
work** — is drafted and sitting uncommitted in the working tree. Per explicit instruction, this
session did not commit, push, or open a PR for it. Until that happens, the repository's own
committed state (what `git log` on `main` actually shows) does not yet reflect `T57` — or Phase 2—
as closed, even though this checkpoint file (once committed) will say so.

**Exact files requiring their own documentation-closeout commit/PR:**
- `IMPLEMENTATION_QUEUE.md`
- `PROJECT_STATE.json`
- `docs/AI_HANDOVER.md`
- `docs/ImplementationLog/Stage3/Phase2.md`
- `docs/Roadmap.md`
- `docs/SessionReport.md`
- `PROJECT_CHECKPOINT.md` (this file)

**Next cycle begins with: T58** — **not authorized**, and should not start even after `T57`'s
documentation closeout lands without its own recorded go-ahead, following the pattern `T56`/`T57`
themselves just demonstrated twice (authorization committed before implementation).

## 12. AI Continuation Instructions

Before doing anything:

1. Read this file (`PROJECT_CHECKPOINT.md`).
2. Verify the live Git state yourself (`git status`, `git log`, `git rev-parse HEAD origin/main`) —
   do not trust this file's numbers without re-checking.
3. **Check whether the seven files listed in §11 are still uncommitted.** If they are, the priority
   before any new task is getting `T57`'s documentation closeout committed and merged (a
   Documentation Manager action, not a new implementation task) — not starting `T58`.
4. Read `T58`'s row in `IMPLEMENTATION_QUEUE.md` directly.
5. Read the relevant `PROJECT_STATE.json` state directly.
6. Verify authorization for `T58` — in the repository, not from this file's summary.
7. Do not assume `T58` is authorized just because `T57`'s code is merged, or because Phase 2 as a
   whole just completed — a phase finishing is not the same thing as the next phase being approved.
8. Follow the project's role workflow (`PROJECT_WORKFLOW.md` §3, §7).

**Which role should act next: Documentation Manager first** (commit/PR the seven files in §11, if
authorized to do so), **then Project Manager** for `T58` — the first Phase 3 task, a genuine
transition point (routes, not just wiring) worth treating with the same care Phase 2's own start
received (an architecture proposal per `PROJECT_WORKFLOW.md` §11, not just a task-row authorization).

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
| `docs/ImplementationLog/Stage3/Phase2.md` | Full technical execution record for `T52`–`T57` (Phase 2, complete) |
| `docs/ImplementationLog/README.md` | The ImplementationLog standard itself — Canonical Document Roles, Documentation Ownership, QA Decision meaning |
| `docs/prompts/*.md` | Canonical per-role AI prompts (Project Manager, Backend Developer, QA Reviewer, Documentation Manager) |
| `docs/Stage3_Backend_Handoff.md` | File-by-file implementation brief for Stage 3's remaining phases |

## 14. Checkpoint Maintenance Rules

- This file represents **current state**, not historical narrative — it is rewritten in place, not
  appended to.
- Update it whenever a task reaches a meaningful lifecycle boundary (implemented, QA-decided,
  merged, closed out).
- Update it after every merge/closeout.
- **Never** claim a task is `Done` merely because code exists — a task is fully `Done` only when its
  QA Decision(s) *and* documentation closeout are both actually merged into `main`. `T57` is the
  worked example this session: code `Done`, Phase 2 complete in code, documentation closeout drafted
  but explicitly not yet merged — this file says so plainly rather than rounding up.
- **Never** claim QA approval unless the QA Decision is recorded in the repository, not merely
  asserted.
- **Never** claim a clean breakpoint while uncommitted or unmerged work remains — see §11's exact
  standard, which this update itself is bound by.
- **Never** claim an authorization was "recorded before implementation began" without a commit to
  point to — `T55`'s history in this repository is the cautionary example; `T56`'s and `T57`'s are
  the corrected practice, now repeated twice.
- Preserve historical detail in `docs/ImplementationLog/`/`docs/SessionReport.md` rather than
  bloating this file.
- **Always** verify Git state directly before declaring this checkpoint current.

## 15. Checkpoint Integrity

- **Last verified commit:** `472f7cb` (`main`, synchronized with `origin/main`)
- **Last verified branch:** `main`
- **Working tree status:** **not clean** — this file and six other documentation/project-management
  files are modified, uncommitted, as part of `T57`'s (not-yet-finalized) documentation closeout.
- **Verification performed:** `git status`; `git log --oneline --decorate -10`; `git show --stat` on
  `7c9fc3a` and `65dd563`; `gh pr view 20` (confirmed `MERGED`, body cross-checked against directly
  re-run verification results); direct read of `65dd563`'s full commit message and `7c9fc3a`'s
  actual diff (not paraphrased); full backend suite re-run (`uv run pytest -q`, 386/386, live
  Postgres); `ruff`/`black`/boot smoke test re-run, all clean.
- **Generated/updated by:** Documentation Manager
- **Date:** 2026-08-13
