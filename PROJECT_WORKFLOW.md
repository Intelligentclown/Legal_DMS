# Project Workflow

**The Legal_DMS Development Operating Manual** — how this project is built, reviewed, documented,
and released. Read this once to understand the entire development lifecycle; you shouldn't need
anything else to understand *how* work happens here (you'll still need the documents this manual
points to for *what's* been built and *why* specific decisions were made).

---

## 1. Purpose

This document exists because the project's other core documents each answer a narrower question —
none of them, alone or together, explains the *lifecycle* a piece of work moves through from "next
task" to "merged and released." This document is that missing narrative layer. It is not an AI
instruction file, not a changelog, and not a planning document — those already exist, and this
document defers to them rather than repeating them:

| Document | What it answers | How this document differs |
|---|---|---|
| [`AI_BOOTSTRAP.md`](AI_BOOTSTRAP.md) | What must an AI session do at startup, and what rules are non-negotiable? | Procedural and AI-facing — a checklist and rule set. This document explains the *why* and the *shape* of the process those rules enforce, for any reader, human or AI. |
| [`IMPLEMENTATION_QUEUE.md`](IMPLEMENTATION_QUEUE.md) | What's planned, in what order, with what acceptance criteria? | The backlog for the *current* stage only, rewritten each stage. This document describes the process that backlog is worked through, and doesn't change stage to stage. |
| [`PROJECT_STATE.json`](PROJECT_STATE.json) | Where does the project stand *right now*? | A point-in-time, machine-readable snapshot. This document describes the stable process that produces each snapshot, not any snapshot itself. |
| [`docs/ImplementationLog/`](docs/ImplementationLog/README.md) | What actually happened while building one specific phase? | The execution record for *one unit of work*. This document explains where that record fits in the larger lifecycle, not its own internal format (that standard is authoritative on its own terms). |
| [`docs/SessionReport.md`](docs/SessionReport.md) | What happened in a given development sitting? | A chronological session log. This document explains *why* sessions follow the shape they do. |
| ADRs (`/ADR/`) | Why was a specific architectural decision made? | One decision each, durable and rarely revisited. This document explains *when* in the lifecycle an ADR gets written, not what any particular one decided. |

If information belongs in one of the documents above, it stays there — this document links out
rather than duplicating.

## 2. Repository Principles

These hold regardless of who (or what) is doing the work:

- **The repository is the single source of truth.** Not chat history, not memory, not assumption.
- **Never rely on previous chat history.** Every new unit of work starts by rebuilding
  understanding from the repository itself.
- **Rebuild context before implementation.** Read `AI_BOOTSTRAP.md`, `PROJECT_STATE.json`, the
  relevant `IMPLEMENTATION_QUEUE.md` section, and the active `ImplementationLog` phase before
  writing anything.
- **Never assume task numbers.** Identify the next unfinished task from
  `IMPLEMENTATION_QUEUE.md`'s actual current content, not from a prior conversation or a guess.
- **Trust code over documentation if they disagree.** Report the discrepancy, then fix the
  documentation — don't silently proceed on stale docs, and don't silently let the mismatch stand.
- **Documentation must be synchronized after implementation.** A task isn't done when the code
  works; it's done when the record of it matches reality. See [§9](#9-definition-of-done).
- **Task IDs are immutable.** Once assigned, a task ID's meaning never changes — scope changes get
  a new ID, not a redefinition of the old one.
- **Process changes are versioned.** Changing how this project works is itself governed by
  [§12](#12-future-improvements).
- **Small, reviewed sections.** One subsystem or task at a time, verified, then committed — not
  one giant diff.
- **Documents have a primary owner, not an exclusive one.** See [§8](#8-documentation-ownership).

## 3. Standard Development Lifecycle

```
Backend Developer
        ↓
QA Reviewer
        ↓
Documentation Manager
        ↓
Git Commit
        ↓
Push
        ↓
GitHub Actions
        ↓
Pull Request
        ↓
Merge
        ↓
Delete Branch
        ↓
Next Task
```

| Step | Purpose |
|---|---|
| **Backend Developer** | Implements the identified task, writes or extends tests, records the work in an `ImplementationLog` phase log, and self-assesses against the Reviewer Checklist. |
| **QA Reviewer** | Independently reviews the implementation against that checklist and renders a QA Decision (`Approved` / `Approved with comments` / `Rework required`). `Rework required` sends the work back to the Developer — nothing downstream happens until it clears this gate. |
| **Documentation Manager** | Once QA approves, synchronizes the project-wide documents this task affects — `PROJECT_STATE.json`, `docs/SessionReport.md`, `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, changelogs — without duplicating what the `ImplementationLog` already records. |
| **Git Commit** | The implementation and its documentation sync are committed, following this project's existing commit-message conventions (see [§5](#5-git-workflow)). |
| **Push** | The commit(s) go to the task's feature branch, which triggers the branch's own CI run. |
| **GitHub Actions** | The three workflows (`backend.yml`, `frontend.yml`, `release.yml`) validate the change — see [§6](#6-pull-request-workflow). |
| **Pull Request** | Opened against `main`, re-triggering the same three workflows against the merge target. |
| **Merge** | Once checks are green, the PR is merged into `main`. |
| **Delete Branch** | The feature branch is removed post-merge — branches are disposable, `main` is not. |
| **Next Task** | Identify the next unfinished task from `IMPLEMENTATION_QUEUE.md`'s current state (per [§2](#2-repository-principles)) and begin again. |

## 4. Branch Strategy

| Prefix | Use |
|---|---|
| `feature/<feature-name>` | New capability or task implementation — e.g. `feature/stage3-t46-password-hashing`, `feature/github-actions-ci`. |
| `docs/<topic>` | Documentation-only work — e.g. `docs/stage3-phase0-finalization`. |
| `bugfix/<bug-name>` | A defect fix that isn't urgent enough to bypass the normal PR flow. |
| `hotfix/<issue>` | An urgent fix, typically against a release branch. |
| `refactor/<module>` | Structural change with no behavior change. |

`feature/`, `docs/`, and `hotfix/` are already in active use in this repository's history;
`bugfix/`/`refactor/` are reserved conventions, not yet exercised — follow the same naming shape
when the need arises rather than improvising a new one.

**Created:** off `main`, at the start of a task or phase, before implementation begins.
**Deleted:** after the branch's pull request merges into `main` — see [§3](#3-standard-development-lifecycle).

## 5. Git Workflow

Standard commands, matching this project's actual history and [`docs/DevelopmentGuide.md`](docs/DevelopmentGuide.md):

```bash
# Create the feature branch (off an up-to-date main)
git checkout main
git pull
git checkout -b feature/<task-name>

# Implement, then run the project's own checks before committing
cd backend && uv run pytest && uv run ruff check src tests alembic && uv run black --check src tests alembic
cd frontend && npm run test && npm run lint && npm run format:check

# Commit — conventional-commit-style prefixes, matching this repo's existing history
git add <files>
git commit -m "feat(auth): add Argon2 password hashing utility"
# other prefixes observed in this repo: ci:, test:, docs:

# Push
git push -u origin feature/<task-name>

# Open PR (GitHub CLI or web UI) — targets main
gh pr create --title "..." --body "..."

# After review and green checks, merge (standard merge commit — this project does not squash or rebase-merge)
# Then, locally:
git checkout main
git pull
git branch -d feature/<task-name>

# Begin the next task
git checkout -b feature/<next-task-name>
```

## 6. Pull Request Workflow

- **When PRs are created:** once a task's implementation, tests, and QA Decision (`Approved` or
  `Approved with comments`) are in place — not before QA has reviewed.
- **Required checks:** all three GitHub Actions workflows —`backend.yml`, `frontend.yml`,
  `release.yml` — must pass. See [ADR/0017](ADR/0017-github-actions-ci.md) for what each validates.
- **Review expectations:** the PR description should reference the corresponding
  `ImplementationLog` phase log and its QA Decision, not restate their content.
- **Merge policy:** standard merge commits (`Merge pull request #N from ...`), preserving the
  branch's own commit history rather than squashing or rebasing it.
- **Protected branch workflow:** requiring these checks to pass before merge is a GitHub
  repository setting, not something this repository's files configure — it must be enabled
  separately by whoever has admin access, and can only be required once the checks have reported
  at least once.

## 7. AI Roles

The same three roles from [§3](#3-standard-development-lifecycle), with what each owns and must
never do. One session commonly plays all three in sequence — the boundaries still apply to which
hat is on at a given moment.

| Role | Owns | Must never |
|---|---|---|
| **Backend Developer** | Implementing the identified task; tests; the `ImplementationLog` phase log; the Reviewer Checklist self-assessment. | Skip writing tests for new behavior; skip the Reviewer Checklist; expand scope beyond the approved task; merge without a QA Decision. |
| **QA Reviewer** | Independent review against the Reviewer Checklist; the QA Decision; `docs/ArchitectureScorecard.md`; QA reports. | Approve without actually reviewing; hide a verification gap instead of disclosing it; let `Rework required` work proceed to documentation sync or merge. |
| **Documentation Manager** | Post-approval synchronization of `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, `docs/SessionReport.md`, changelogs, release notes. | Duplicate `ImplementationLog`'s technical detail; synchronize documentation before a QA Decision exists; rewrite a completed phase log or a past session entry to reflect later knowledge (append a new dated note instead). |

Full assignment detail: [`docs/ImplementationLog/README.md#documentation-ownership`](docs/ImplementationLog/README.md#documentation-ownership).

## 8. Documentation Ownership

Summarized from [`docs/ImplementationLog/README.md`](docs/ImplementationLog/README.md#canonical-document-roles)
and [`#documentation-ownership`](docs/ImplementationLog/README.md#documentation-ownership) — that
document is authoritative; this is a pointer, not a second copy.

| Document | Canonical role | Primary owner |
|---|---|---|
| `docs/ImplementationLog/` | Implementation history | Backend / Frontend Developer |
| `docs/SessionReport.md` | Session summary | Documentation Manager |
| `IMPLEMENTATION_QUEUE.md` | Planning backlog | Project Manager |
| ADRs (`/ADR/`) | Architectural decisions | Software Architect |
| `CHANGELOG.md` / `docs/CHANGELOG.md` | Release summary | Documentation Manager |
| `docs/releases/` | Per-version release notes | Documentation Manager |
| `README.md` / `docs/README.md` | Project entry points | Documentation Manager |
| `PROJECT_STATE.json` | Point-in-time snapshot | Documentation Manager — assigned 2026-08-07; it's a synchronization document, changing after implementation, QA, releases, and documentation updates, matching this role's existing consistency-maintenance responsibility |

Ownership is primary, not exclusive: any role may correct any document when genuinely necessary,
but routine updates belong to the assigned owner, and a reader should ask that owner first if a
document looks wrong.

## 9. Definition of Done

A task is complete only when every one of the following holds — full checklist and rationale in
[`docs/DefinitionOfDone.md`](docs/DefinitionOfDone.md), not repeated here:

- Implementation complete
- Tests passing
- QA approved
- Documentation synchronized
- GitHub Actions green
- PR merged
- Branch cleaned up

## 10. Release Workflow

- **Version tags:** `PROJECT_STATE.json`'s `currentVersion` only advances together with an actual
  `git tag` — not per completed task or phase. See [`docs/releases/README.md`](docs/releases/README.md).
- **Release notes:** one frozen `docs/releases/vX.Y.Z.md` per tagged version, plus
  `docs/releases/LATEST.md` as a stable pointer to whichever is current.
- **CHANGELOG:** both the root `CHANGELOG.md` (a short, version-indexed pointer list) and
  `docs/CHANGELOG.md` (the detailed per-item log) are updated for every release.
- **Documentation synchronization:** a release is a checkpoint where `PROJECT_STATE.json`,
  `docs/ProjectStatus.md`, `docs/AI_HANDOVER.md`, and the changelogs are all confirmed consistent
  with each other, not just with the code.
- **When releases occur:** at a coherent, shippable checkpoint — historically a stage's
  completion or a significant standalone addition (e.g. `v0.3.0`, `v0.3.1`) — not automatically at
  every merge.

## 11. Quality Standards

- **Minimal scope** — implement exactly what was asked; extra ideas go to Deferred Work, not into
  the diff.
- **No speculative abstraction** — build the concrete thing a real caller needs; add a port or
  interface only when something actually needs to swap behind it.
- **Architecture first** — a proposal and, where warranted, an ADR precede implementation for any
  non-trivial decision; nothing architectural changes silently.
- **Framework independence** — business and application logic depend on ports
  (`application/interfaces/`), not directly on a specific library or framework.
- **Tests required** — new behavior ships with tests that prove it, not just reliance on existing
  coverage happening to exercise it.
- **Documentation updated** — see [§9](#9-definition-of-done); a task isn't done until its record
  is.
- **No hidden behavior** — discrepancies between documentation and code, or between an instruction
  and the existing plan, are reported and resolved visibly, never silently papered over.

## 12. Future Improvements

**Workflow changes are versioned, the same as architectural decisions.** Any change to how this
project is developed — this document, the branch strategy, the PR/CI requirements, the AI role
definitions, the Definition of Done — must be proposed, reviewed, and documented before adoption,
not adopted silently because it seemed reasonable in the moment. See `AI_BOOTSTRAP.md`'s
"Process changes are versioned" rule for the full statement of this principle.

This document itself is meant to stay stable across ordinary implementation work — if a change here
feels necessary because the *process* has genuinely changed, propose it explicitly; if it's just
that a snapshot fact changed, that belongs in `PROJECT_STATE.json` or `docs/ProjectStatus.md`
instead, not here.

## Repository-First Rule

The repository is always the source of truth.

Every implementation batch must begin by rebuilding context from the repository.

AI assistants must:

- Read the required project documents.
- Verify the current implementation.
- Identify the next unfinished task from IMPLEMENTATION_QUEUE.md.
- Never rely solely on previous conversation history.
- If documentation and implementation disagree, report the discrepancy and follow the repository.

## Standard Prompts

The project uses standard prompts for:

- Backend Developer
- QA Reviewer
- Documentation Manager

These prompts are maintained outside this document to allow evolution without changing the
workflow itself.
