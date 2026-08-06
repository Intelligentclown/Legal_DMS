# Pre-Stage Checklist

**Purpose:** This checklist must be completed before beginning every development stage (and, per
[docs/templates/README.md](README.md), before every standalone post-stage framework addition too —
this project's stages aren't the only unit of work that deserves this gate). It exists so a new
stage never starts on top of an unverified assumption: a stale test count, an uncommitted change
nobody remembers, a QA finding quietly left unresolved, or a "next stage" nobody actually approved.

**How to use this:** Copy this file to `docs/reviews/PreStageChecklist_<target>_<YYYY-MM-DD>.md`
(e.g. `PreStageChecklist_Stage3_2026-09-01.md`), fill it in against the real, current state of the
repository — don't check a box from memory or from what a document *claims*; verify it — and get it
approved before writing the first line of the new stage's code. See
[docs/templates/README.md](README.md) for the full workflow.

---

## Repository

- [ ] Repository is clean — `git status` shows no unexpected uncommitted or untracked changes
      (anything present is understood and intentional, not leftover work)
- [ ] Current branch confirmed and matches [PROJECT_STATE.json](../../PROJECT_STATE.json)'s
      `git.branch`
- [ ] Latest commit confirmed and matches PROJECT_STATE.json's `git.latestCommitAtThisUpdate` (or
      the discrepancy is explained below in Notes)
- [ ] No stray or unexplained untracked files (`.claude/`, scratch files, local experiments) left
      in a state that would confuse the next session
- [ ] `.gitignore` still covers everything it should (`.env`, `__pycache__`, `node_modules`,
      `dist-electron/`, build output) — nothing sensitive or generated is at risk of being committed

## Documentation

- [ ] [docs/ProjectStatus.md](../ProjectStatus.md) reflects the real, current state of the
      previous stage — not what was planned, what actually happened
- [ ] [docs/AI_HANDOVER.md](../AI_HANDOVER.md) updated: completed work, open issues, warnings, and
      exactly what should (and should not) be assumed next
- [ ] [docs/SessionReport.md](../SessionReport.md) has a session entry for the most recent work,
      including problems encountered and how they were solved
- [ ] Root [CHANGELOG.md](../../CHANGELOG.md) **and** [docs/CHANGELOG.md](../CHANGELOG.md) both
      updated for the most recent release
- [ ] [docs/ArchitectureScorecard.md](../ArchitectureScorecard.md) reflects current capability
      statuses — no row silently stale relative to what actually shipped
- [ ] [docs/releases/](../releases/) has a `vX.Y.Z.md` for the current version (see
      [docs/releases/README.md](../releases/README.md))
- [ ] No open findings from the latest `docs/reviews/Documentation_Consistency_Report_*.md` (if one
      exists) — or every open finding is explicitly accepted as carried-forward debt, not forgotten
- [ ] Internal documentation links spot-checked — no broken references to a file that was renamed,
      moved, or never actually created

## Architecture

- [ ] Architecture reviewed against the upcoming stage's scope — confirmed the existing framework
      (DI container, repository pattern, buses, etc.) actually supports what the new stage needs,
      or the gap is named explicitly
- [ ] Every architectural decision the upcoming stage will require has an ADR planned, or an
      existing ADR already covers it — see [`/ADR`](../../ADR/)
- [ ] Previous stage's architecture confirmed unchanged since it was last verified (no silent drift)
- [ ] Real shipped app's route/schema surface confirmed to match what the documentation claims
      (e.g. still just `/api/v1/health` + `/api/v1/version` if no route work has landed)

## Testing

- [ ] Backend test suite run and passing (`pytest`) — actual count recorded, not copied from a doc
- [ ] Frontend test suite run and passing (Vitest or equivalent) — actual count recorded
- [ ] Test counts in [PROJECT_STATE.json](../../PROJECT_STATE.json) match what was actually run
      this session, not a prior session's numbers
- [ ] Linters clean (`ruff`, `black --check`, `eslint`, `prettier --check`)
- [ ] Any environment-specific test gap (e.g. integration tests needing Docker/Postgres that
      weren't available) is explicitly disclosed in Notes below, not silently treated as "passing"

## Implementation Queue

- [ ] [IMPLEMENTATION_QUEUE.md](../../IMPLEMENTATION_QUEUE.md) reviewed against the actual current
      state — no task marked `Done` that isn't, none marked `Not Started` that's actually landed
- [ ] Implementation Queue for the **next** stage is ready: tasks scoped, complexity-estimated, and
      dependency-ordered, following this project's existing XS/S/M sizing convention
- [ ] Acceptance criteria defined for the upcoming stage's scope — a reviewer could tell, from the
      queue alone, what "done" looks like
- [ ] No leftover items from the previous stage's queue silently dropped instead of explicitly
      marked `Done`, `Deferred`, or `Blocked`

## QA

- [ ] QA review complete for the previous stage/addition (if this project's process called for one)
- [ ] **No pending "Fix Immediately" QA findings** — every finding classified that way has actually
      been fixed, not just scheduled
- [ ] **No pending Critical/P0 bugs** anywhere in `IMPLEMENTATION_QUEUE.md` or a QA review that
      would block starting new work on top of them
- [ ] All QA findings are classified (Fix Immediately / Future Stage / Accepted Trade-off /
      Won't Fix) — nothing left unclassified
- [ ] Every deferred finding's gating condition re-checked — confirm it hasn't silently started
      applying (e.g. "revisit once a real `UnitOfWork` exists" — does one now exist?)

## Git

- [ ] Current branch matches this project's convention (`master`, no unapproved feature-branch
      workflow introduced without discussion)
- [ ] Latest commit message(s) follow this project's existing style
- [ ] No unpushed or unmerged work exists that should be included before the new stage starts
- [ ] Previous stage's work is fully committed — not left sitting as uncommitted working-tree
      changes that a fresh session could lose or misread as "not yet done"

## Project State

- [ ] [PROJECT_STATE.json](../../PROJECT_STATE.json) updated: `currentStage`, `currentVersion`,
      `tests`, `completion`, `git` all reflect reality as of right now
- [ ] Previous stage explicitly marked `"status": "completed"` in `PROJECT_STATE.json` — not left
      `"in_progress"` by omission
- [ ] **Next stage explicitly approved by the project owner** — not assumed, not inferred from "it's
      next on the original charter list." This project's standing rule (see
      [AI_BOOTSTRAP.md](../../AI_BOOTSTRAP.md)) is to ask, not guess.
- [ ] `openQuestions` in `PROJECT_STATE.json` reviewed — still-open questions are still actually
      open, and any that got answered are removed

## Release

- [ ] Current release note exists at `docs/releases/vX.Y.Z.md` for the version this stage starts
      from (see [docs/releases/README.md](../releases/README.md))
- [ ] That release note's "Next Planned Release" section matches what's actually about to start —
      or the mismatch is explained in Notes below
- [ ] Version number for the upcoming stage/work decided, following this project's existing
      semantic versioning convention (see the root [CHANGELOG.md](../../CHANGELOG.md) for
      precedent)
- [ ] No breaking changes from the previous release are left undocumented in that release's
      "Breaking Changes" section

---

## Sign-off

- [ ] **Approved to proceed to the next stage** — every section above is checked, or every
      unchecked item has an explicit, accepted reason recorded in Notes

**Date:** _____________________

**Reviewer:** _____________________

**Developer:** _____________________

**Notes:**

_(Record any unchecked item's reason here, any accepted risk, or anything a future session should
know about why this checklist was signed off the way it was. An unchecked box with no note here is
an unresolved gap, not an accepted one.)_
