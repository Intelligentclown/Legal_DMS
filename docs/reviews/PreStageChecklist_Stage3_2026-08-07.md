# Pre-Stage Checklist — Stage 3 (gating Phase 1, T46+)

**Purpose:** This checklist must be completed before beginning every development stage (and, per
[docs/templates/README.md](../templates/README.md), before every standalone post-stage framework
addition too — this project's stages aren't the only unit of work that deserves this gate). It
exists so a new stage never starts on top of an unverified assumption: a stale test count, an
uncommitted change nobody remembers, a QA finding quietly left unresolved, or a "next stage" nobody
actually approved.

**Scope note:** Stage 3 itself already began (Phase 0, `T41`–`T45`, done and QA-Approved — see
`docs/ImplementationLog/Stage3/Phase0.md`) without this checklist being completed first, since
Phase 0 was pulled forward under direct instruction before this gate was filled in. This checklist
is being completed now, retroactively for Phase 0 and prospectively for **Phase 1 (`T46`+)**,
closing the orphaned original-`T44` content (this checklist's own sign-off) per
`IMPLEMENTATION_QUEUE.md`'s Phase 0 acceptance criteria. Everywhere below, "the upcoming
stage"/"next stage" means **Stage 3 Phase 1**, not a new numbered stage.

**Completed by:** AI session, 2026-08-07 — every box below reflects direct verification against
the repository as of this date, not copied from another document. **Not self-approved** — see
Sign-off.

---

## Repository

- [ ] Repository is clean — `git status` shows no unexpected uncommitted or untracked changes
      (anything present is understood and intentional, not leftover work)

  **Not clean, and this is a real finding, not a formality.** Beyond this session's own expected
  changes (`PROJECT_STATE.json`, `docs/ImplementationLog/Stage3/Phase0.md` from the prior
  session's documentation sync; this file and `ADR/0018-...md`, new, from this session), `git
  status` shows **pre-existing, not-committed-by-this-session** modifications to `AI_BOOTSTRAP.md`,
  `IMPLEMENTATION_QUEUE.md`, `docs/ImplementationLog/README.md`, and
  `docs/Stage3_Backend_Handoff.md`, plus an untracked file,
  `docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md`. Inspected each diff directly:
  all five together adopt a "Task IDs are immutable" rule into `AI_BOOTSTRAP.md`'s non-negotiable
  rules and `docs/ImplementationLog/README.md`'s metadata-block guidance, and update
  `IMPLEMENTATION_QUEUE.md`/`docs/Stage3_Backend_Handoff.md` to cross-reference it. **This
  contradicts the migration note's own text**, which describes that exact rule as "Recommended,
  not adopted... **Not implemented as part of this note or this session** — this is a
  recommendation only, awaiting separate approval." Either a later, uncommitted session went
  further than the note it's sitting alongside describes (without updating the note to say so), or
  this is stray work-in-progress. Per this task's explicit instruction ("do not perform any
  additional T44/T45 reconciliation," "documentation only: `ADR-0018` + this checklist"), **these
  five files were left untouched** — not committed, not reverted, not extended. Flagging for your
  review: either commit this pre-existing work as an intentional adoption of the rule, or discard
  it if it wasn't meant to be there.

- [x] Current branch confirmed and matches [PROJECT_STATE.json](../../PROJECT_STATE.json)'s
      `git.branch` — both `main`.
- [x] Latest commit confirmed and matches PROJECT_STATE.json's `git.latestCommitAtThisUpdate` —
      both `78f2677` (merge commit, PR #2).
- [ ] No stray or unexplained untracked files (`.claude/`, scratch files, local experiments) left
      in a state that would confuse the next session

  Two untracked files exist: `ADR/0018-authentication-authorization-architecture.md` (this
  session's own deliverable — expected, will be committed) and
  `docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md` (pre-existing, not created this
  session — part of the same finding above).

- [x] `.gitignore` still covers everything it should (`.env`, `__pycache__`, `node_modules`,
      `dist-electron/`, build output) — confirmed via direct inspection: `.env`, `node_modules/`,
      `dist-electron/`, `__pycache__/` all present.

## Documentation

- [ ] [docs/ProjectStatus.md](../ProjectStatus.md) reflects the real, current state of the
      previous stage — not what was planned, what actually happened

  **Internally inconsistent.** Its own "Stage 3" narrative section (around line 91) correctly says
  "Stage 3 — Authentication & Authorization is now in progress... Phase 0 is done." But its
  "Pending" and "Upcoming Stage" sections (lines 398–443) were never updated and still read "Stage
  3 is undefined — nothing planned in detail" / "no plan exists yet." Stale since Stage 3 was
  scoped; not fixed here (out of scope for this documentation-only task — flagging, not silently
  correcting).

- [x] [docs/AI_HANDOVER.md](../AI_HANDOVER.md) updated: completed work, open issues, warnings, and
      exactly what should (and should not) be assumed next — correctly states Phase 0 is done and
      Phase 1 (`T46`+) awaits an explicit go-ahead (lines ~253–261).
- [x] [docs/SessionReport.md](../SessionReport.md) has a session entry for the most recent work,
      including problems encountered and how they were solved — the batch-4 CI hotfix entry is the
      most recent, present and complete.
- [x] Root [CHANGELOG.md](../../CHANGELOG.md) **and** [docs/CHANGELOG.md](../CHANGELOG.md) both
      updated for the most recent release — the most recent actual release is `v0.3.1`; both files
      correctly document it. Stage 3 Phase 0 work is intentionally **not** in either changelog yet,
      consistent with this project's convention that changelogs track releases (`git tag`), not
      every phase — no new tag has been cut since `v0.3.1`.
- [x] [docs/ArchitectureScorecard.md](../ArchitectureScorecard.md) reflects current capability
      statuses — the Authentication/Authorization Framework rows still correctly say "no login
      mechanism implemented" / "no real permission data model wired" — still accurate, Phase 0
      added no login or RBAC.
- [x] [docs/releases/](../releases/) has a `vX.Y.Z.md` for the current version — `v0.3.1.md`
      exists.
- [x] No open findings from the latest `docs/reviews/Documentation_Consistency_Report_*.md` — the
      one that exists (`Documentation_Consistency_Report_2026-08-06.md`, pre-dates Stage 3) has
      three carried-forward debt items (the three-independent-version-numbers scheme, accepted;
      `docs/FolderStructure.md` drift risk, a process note; five gated QA findings Q2/Q3/Q5/Q7/Q9,
      still correctly gated — re-verified this session: no real `UnitOfWork` implementation exists
      yet (`infrastructure/transactions/` has only `in_memory_unit_of_work.py`), `main.py` has no
      `ModuleManifestLoader` wiring). None are new, none block Stage 3.
- [ ] Internal documentation links spot-checked — no broken references to a file that was renamed,
      moved, or never actually created

  Spot-checked only (this checklist's own links, `ADR-0018`'s cross-references, `Phase0.md`'s
  links) — not an exhaustive site-wide link audit. All spot-checked links resolve.

## Architecture

- [x] Architecture reviewed against the upcoming stage's scope — confirmed the existing framework
      actually supports what Phase 1 needs, or the gap is named explicitly —
      `docs/Stage3_Backend_Handoff.md`'s Phase 1–4 file-by-file map covers this in detail and is
      still current (its own "Status" line is stale in the pre-existing uncommitted diff described
      above, not touched by this session).
- [x] Every architectural decision the upcoming stage will require has an ADR planned, or an
      existing ADR already covers it — **all seven decisions (D1–D7) now have an ADR**: `ADR-0018`
      (D1–D6, written this session), `ADR-0019` (D7), `ADR-0020` (session commit/rollback policy,
      the Phase-0 prerequisite). This was the one open item this checklist is closing.
- [x] Previous stage's architecture confirmed unchanged since it was last verified — confirmed via
      `git diff --stat` on `c84a339`/`d80815d`: no Stage 2 schema or Stage 2.7 CI file was touched
      beyond the one documented `JWT_SECRET_KEY` CI env-var addition.
- [x] Real shipped app's route/schema surface confirmed to match what the documentation claims —
      `presentation/api/v1/router.py` still mounts only `health` and `version` routers, matching
      `docs/Architecture.md`'s claim exactly.

## Testing

- [x] Backend test suite run and passing (`pytest`) — actual count recorded, not copied from a doc
      — `tests/unit`: **186 passed**, fresh run this session (2026-08-07).
- [x] Frontend test suite run and passing (Vitest or equivalent) — actual count recorded —
      **9 passed** (3 test files), fresh run this session.
- [ ] Test counts in [PROJECT_STATE.json](../../PROJECT_STATE.json) match what was actually run
      this session, not a prior session's numbers

  Partial. This session directly re-confirms **186 unit + 9 frontend**, matching
  `PROJECT_STATE.json`. The full **298** figure (186 unit + 112 integration) could **not** be
  independently re-run this session — Docker Desktop is not running in this environment
  (`docker ps` fails to reach the daemon), so the 112 Postgres-backed integration tests are
  unverifiable here. The 298 figure is carried forward from when it was last actually run (recorded
  in `Phase0.md`/`PROJECT_STATE.json` as verified with Postgres reachable at merge time), not
  freshly confirmed today.

- [x] Linters clean (`ruff`, `black --check`, `eslint`, `prettier --check`) — all four re-run this
      session: backend `ruff`/`black` clean; frontend `eslint` clean (3 pre-existing
      `react-refresh` warnings, 0 errors, matching the documented baseline);
      `prettier --check` clean.
- [x] Any environment-specific test gap (e.g. integration tests needing Docker/Postgres that
      weren't available) is explicitly disclosed in Notes below, not silently treated as "passing"
      — see the unchecked item immediately above; disclosed, not hidden.

## Implementation Queue

- [x] [IMPLEMENTATION_QUEUE.md](../../IMPLEMENTATION_QUEUE.md) reviewed against the actual current
      state — no task marked `Done` that isn't, none marked `Not Started` that's actually landed —
      `T41`–`T45` correctly shown done; `T46`+ correctly shown not started.
- [x] Implementation Queue for the **next** phase is ready: tasks scoped, complexity-estimated, and
      dependency-ordered — Phase 1 (`T46`–`T51`) is fully specified with complexity estimates
      (S/S/XS/S/M/M) and dependencies in `IMPLEMENTATION_QUEUE.md`.
- [x] Acceptance criteria defined for the upcoming scope — a reviewer could tell, from the queue
      alone, what "done" looks like — "Phase 1 done when..." exists in
      `IMPLEMENTATION_QUEUE.md`.
- [x] No leftover items from the previous stage's queue silently dropped instead of explicitly
      marked `Done`, `Deferred`, or `Blocked` — the two items orphaned by the `T44`/`T45` ID reuse
      (this checklist's sign-off; `ADR-0018`) are exactly what this session addresses (`ADR-0018`
      written; this checklist itself prepared). The sign-off itself remains open — see Sign-off
      below, not this box.

## QA

- [x] QA review complete for the previous stage/addition — Phase 0's QA Decision across all four
      batches is **Approved** (`docs/ImplementationLog/Stage3/Phase0.md`).
- [x] **No pending "Fix Immediately" QA findings** — `T20`/`T21` (Q1/Q8 from the post-Stage-2 QA
      review) are done; nothing new since.
- [x] **No pending Critical/P0 bugs** anywhere in `IMPLEMENTATION_QUEUE.md` or a QA review that
      would block starting new work on top of them — none flagged.
- [x] All QA findings are classified (Fix Immediately / Future Stage / Accepted Trade-off /
      Won't Fix) — nothing left unclassified — Q1–Q9 all classified in `IMPLEMENTATION_QUEUE.md`'s
      table.
- [x] Every deferred finding's gating condition re-checked — confirm it hasn't silently started
      applying — re-verified this session: Q2/Q3/Q7 (real `UnitOfWork`) — still only
      `InMemoryUnitOfWork` exists; Q5 (`ModuleManifestLoader` wired into `main.py`) — still not
      wired (confirmed, no `manifest` reference in `main.py`); Q9 (async factory) — no
      async-requiring implementation proposed. None have started applying.

## Git

- [x] Current branch matches this project's convention (`master`, no unapproved feature-branch
      workflow introduced without discussion) — `main`, via the same PR-merge workflow already
      established for Stage 2.7 (`feature/stage3-phase0` → `main` via PR #2, matching PR #1's
      precedent).
- [x] Latest commit message(s) follow this project's existing style — `feat(auth): ...`,
      `test: ...`, consistent with the existing `ci: ...` convention.
- [ ] No unpushed or unmerged work exists that should be included before the new stage starts

  Committed history is fully merged and even with `origin/main` (`git status` shows
  `main...origin/main`, no ahead/behind). However, **uncommitted working-tree changes exist** — see
  the Repository section's first finding. Cross-referenced here, not re-explained.

- [x] Previous stage's work is fully committed — not left sitting as uncommitted working-tree
      changes that a fresh session could lose or misread as "not yet done" — Phase 0 (`T41`–`T45`,
      all four batches) is fully committed and merged (`c84a339`, `d80815d`).

## Project State

- [ ] [PROJECT_STATE.json](../../PROJECT_STATE.json) updated: `currentStage`, `currentVersion`,
      `tests`, `completion`, `git` all reflect reality as of right now

  `currentStage`, `currentVersion`, `git`, and `completion` are current. `tests.backend.total`
  (298) could not be freshly re-verified end-to-end this session — see the Testing section's
  unchecked item. Not re-marked stale (the last real run that produced 298 is legitimately
  recorded), but also not independently reconfirmed today.

- [x] Previous stage explicitly marked `"status": "completed"` in `PROJECT_STATE.json` — not left
      `"in_progress"` by omission — `stage-2` is `"completed"`. (`stage-3` is correctly
      `"in_progress"`, not `"completed"` — Stage 3 overall isn't done, only Phase 0 is.)
- [ ] **Next stage explicitly approved by the project owner** — not assumed, not inferred from
      "it's next on the original charter list."

  **Deliberately left unchecked.** Per this session's explicit instruction: do not mark Phase 1
  approved. This is the one item that gates `T46` starting — see Sign-off below.

- [x] `openQuestions` in `PROJECT_STATE.json` reviewed — still-open questions are still actually
      open, and any that got answered are removed — all three remain genuinely open (`T66` matrix
      sign-off; Phase 1 go-ahead — still open, consistent with this session's instruction; `T44`/
      `T45` ID reconciliation — per this session's explicit instruction, "the existing migration
      note is sufficient," so no further reconciliation was attempted, but the underlying
      tracking-ID question the note itself flags as open in its Recommendation #4 remains
      technically unresolved).

## Release

- [x] Current release note exists at `docs/releases/vX.Y.Z.md` for the version this stage starts
      from — `docs/releases/v0.3.1.md` exists.
- [ ] That release note's "Next Planned Release" section matches what's actually about to start —
      or the mismatch is explained in Notes below

  Stale: `v0.3.1.md`'s "Next Planned Release" section still says "Not yet planned... Stage 3
  remains undefined beyond that." Written before Stage 3 was scoped; not corrected here (same
  category as the `docs/ProjectStatus.md` finding above — out of scope for this documentation-only
  task, flagged rather than silently fixed).

- [ ] Version number for the upcoming stage/work decided, following this project's existing
      semantic versioning convention

  Not decided, and correctly so — per this project's corrected versioning convention
  (`docs/releases/README.md`: version bumps happen in step with an actual `git tag`, not every
  phase), no version number needs deciding until Stage 3 actually ships something tag-worthy.
  Leaving unchecked rather than marking N/A, since the template doesn't distinguish the two and an
  honest unchecked box is safer than a silently-assumed pass.

- [x] No breaking changes from the previous release are left undocumented in that release's
      "Breaking Changes" section — `v0.3.1` (CI/tooling only) had none. The `AuthenticationProvider`
      signature break (D7) happened in unreleased Stage 3 Phase 0 work, after `v0.3.1` — it's
      documented in `ADR-0019`, not a `v0.3.1` gap.

---

## Sign-off

- [x] **Approved to proceed to the next stage** — every section above is checked, or every
      unchecked item has an explicit, accepted reason recorded in Notes

  **AI self-assessment (2026-08-07, at the time this checklist was drafted): Not checked. Not
  self-approved, per explicit instruction.** Nine items above are unchecked, each with its reason
  recorded inline rather than left as a bare gap. The most material of the nine, for your
  attention: (1) the pre-existing uncommitted "Task IDs are immutable" changes sitting in the
  working tree, contradicting their own migration note's "not adopted" text; (2) two stale "Stage 3
  is undefined" sections (`docs/ProjectStatus.md`, `v0.3.1.md`) never updated when Stage 3 was
  scoped; (3) the 112 integration tests unverifiable this session (no local Docker/Postgres); (4)
  Phase 1 itself, deliberately left unapproved. **This self-assessment stands as the historical
  record of that moment — superseded below by the reviewer's actual sign-off.**

  **Reviewer sign-off (2026-08-07):**
  - ☑ Phase 0 Approved
  - ☑ Approved to begin Stage 3 Phase 1

**Date:** 2026-08-07

**Reviewer:** Dhimant Patel

**Developer:** AI session (2026-08-07) — self-assessed only, per this checklist's own "don't check
a box from memory or from what a document claims; verify it" instruction. Reviewer sign-off (above)
is the separate, later step this instruction anticipated.

**Notes:**

See the inline notes under each unchecked box above — every one has its reason recorded there
rather than repeated here, per this file's own instruction that an unchecked box with no note is an
unresolved gap, not an accepted one. No item above was left unchecked without an explanation. The
nine items the AI self-assessment flagged as open were not re-verified or resolved as part of
recording this sign-off — they remain exactly as documented above.
