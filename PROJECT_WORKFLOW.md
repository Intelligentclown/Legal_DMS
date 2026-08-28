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
- **Every implementation cycle begins with the Project Manager.** No feature branch is created until the Project Manager has identified the next unfinished task, verified prerequisites, and the project owner has approved implementation.
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

```text
Project Manager
        ↓
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
Update Local main
        ↓
Next Task
```

| Step | Purpose |
|---|---|
| **Project Manager** | Rebuilds repository state, identifies the next unfinished task from
`IMPLEMENTATION_QUEUE.md`, verifies dependencies, phase gates,documentation consistency, implementation status, and blockers, then waits for explicit project-owner approval before implementation begins. |
| **Backend Developer** | Implements the approved task, writes or extends tests, records the work in an `ImplementationLog` phase log, and self-assesses against the Reviewer Checklist. |
| **QA Reviewer** | Independently reviews the implementation against the Reviewer Checklist and renders a QA Decision (`Approved` / `Approved with comments` / `Rework required`). `Rework required` sends the work back to the Developer — nothing downstream happens until it clears this gate. |
| **Documentation Manager** | Once QA approves, synchronizes the project-wide documents this task affects (`PROJECT_STATE.json`, `docs/SessionReport.md`, `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, changelogs, release notes, etc.) without duplicating what the `ImplementationLog` already records. |
| **Git Commit** | The implementation and documentation synchronization are committed using the project's commit-message conventions (see [§5](#5-git-workflow)). |
| **Push** | Push the feature branch to GitHub, triggering CI. |
| **GitHub Actions** | The project's CI workflows validate the change. |
| **Pull Request** | Opened against `main`, triggering another CI run for the merge target. |
| **Merge** | Merge into `main` after all required checks pass. |
| **Delete Branch** | Delete the feature branch after merge. |
| **Update Local main** | Update the local repository (`git checkout main && git pull`) before beginning new work. |
| **Next Task** | Start the next cycle by identifying the next unfinished task from `IMPLEMENTATION_QUEUE.md`. Never assume the next task number from previous conversations. |

### 3.1 Required-ADR / Governance-Hardening Lifecycle (Three-PR)

*(Added by T96, documenting a practice already in use since `T87` — not a new process.)*

For tasks whose authorized deliverable is a Required-ADR resolution or a governance/context-hardening
change tracked directly by its own `IMPLEMENTATION_QUEUE.md` row (rather than a Backend/Frontend
Developer implementation batch that already has its own `ImplementationLog`-based flow), this
project's actual practice — every `T87`–`T95` task, without exception, verified directly against
merged PR history, not asserted from memory — has been a **three-PR lifecycle** instead of the
single-PR flow in [§3](#3-standard-development-lifecycle):

```text
1. Authorization PR
        ↓ (merged into main)
2. Architecture/Implementation + QA PR
        ↓ (merged into main)
3. Governance Closeout PR
```

| PR | Purpose |
|---|---|
| **1. Authorization PR** | A dedicated `IMPLEMENTATION_QUEUE.md` commit, on its own branch, recording the task's identity, project-owner authorization, approved scope, and explicit exclusions — as its own documentation-only commit, before any implementation exists. No implementation branch is created until this PR has merged. Example: `T87`'s PR #113 (`docs(governance): authorize T87`). |
| **2. Architecture/Implementation + QA PR** | The actual deliverable (an ADR draft, or governance tooling/documentation) plus its formal QA Decision, persisted as a commit on the same branch and independently re-verified against the PR's actual remote HEAD — the same QA remote-publication gate [§6](#6-pull-request-workflow) requires generally. Example: `T87`'s PR #114 (`docs(adr): ADR-0021 -- ...`). |
| **3. Governance Closeout PR** | Opened only after PR 2 has merged. Updates the task's `IMPLEMENTATION_QUEUE.md` row to record it as Done — citing the implementation PR number, its merge commit, and the QA decision commit — and, where separately authorized, synchronizes any structured governance state (e.g. `PROJECT_STATE.json`'s `governanceLedger`, added by `T95`). Example: `T87`'s PR #115 (`docs(governance): close out T87 as Done after PR #114 merge`). |

**When this applies:** Required-ADR resolution tasks and governance/context-hardening tasks whose
scope is defined directly in `IMPLEMENTATION_QUEUE.md` rather than an `ImplementationLog` phase.
`T87`–`T96` are the verified precedent.

**This does not replace or invalidate [§3](#3-standard-development-lifecycle).** Ordinary backend/
frontend implementation work continues to use the single-PR Standard Development Lifecycle — that
flow already has its own QA/Documentation-Manager sequencing appropriate to a code change with tests
and an `ImplementationLog` entry, which most Required-ADR/governance tasks don't produce.

**This is not, by this addition alone, a universal policy for all future work.** It documents an
already-proven pattern for the specific class of task named above. Broadening it into the mandatory
process for other task categories is a separate project-owner decision, not implied here.

**Authorization-ancestry verification:** before merging PR 2 (or PR 3) of this lifecycle, the Project
Manager's pre-merge gate additionally verifies that the task's authorization commit (from PR 1) is a
genuine git ancestor of the PR's actual remote HEAD — see
[`docs/prompts/ProjectManager.md`](docs/prompts/ProjectManager.md)'s Pre-Merge Governance Gate for the
exact mechanism and the incident history that motivated it.

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
- **QA remote-publication gate:** a QA Decision only counts toward merge-readiness once its
  recording commit has been pushed to the implementation PR's own remote branch and the checked box
  has been independently re-read from that remote PR HEAD — a QA Decision committed only locally is
  not yet a completed approval (`LOCAL QA COMMIT ≠ REMOTE QA APPROVAL`). The QA Reviewer owns
  pushing that commit; the Project Manager independently verifies it before merging and must not be
  expected to discover or repair an unpushed QA record. Full rule:
  `docs/ImplementationLog/README.md#qa-decision`; the corresponding checklists live in
  `docs/prompts/QAReviewer.md`'s Required Output and `docs/prompts/ProjectManager.md`'s Pre-Merge
  Governance Gate.
- **After merge:** update the local `main` branch (`git checkout main && git pull`) before starting the next implementation cycle.
- **Protected branch workflow:** requiring these checks to pass before merge is a GitHub
  repository setting, not something this repository's files configure — it must be enabled
  separately by whoever has admin access, and can only be required once the checks have reported
  at least once.

## 7. AI Roles

The project defines six standard AI roles. One development session may perform all six
sequentially, but each role has distinct responsibilities and boundaries. Backend Developer and
Frontend Developer are peer roles occupying the same lifecycle position — a task is assigned to
exactly one of the two, selected by the authorized task's domain (backend/Python vs. frontend/
TypeScript/Electron-renderer), never both, and neither is a subordinate or a merged variant of the
other. Frontend Developer was formally adopted 2026-08-22 (project-owner decision); see
[`docs/prompts/FrontendDeveloper.md`](docs/prompts/FrontendDeveloper.md). Software Architect is a
specialist role, not a mandatory lifecycle stage — it is invoked only when a task's authorized
scope is architectural decision work (drafting or resolving an ADR), not for every implementation
task; see [`docs/prompts/SoftwareArchitect.md`](docs/prompts/SoftwareArchitect.md).

| Role | Owns | Must never |
|---|---|---|
| **Project Manager** | Repository state, implementation planning, dependency validation, task sequencing, stage gates, documentation consistency checks, pre-merge QA-remote verification, and merging approved implementation PRs. | Implement code, review implementation, bypass stage gates, assume task numbers, approve implementation, or merge a PR without independently verifying its QA Decision on the actual remote PR HEAD. |
| **Software Architect** | Architectural investigation, ADR drafting and ownership (`/ADR/`), architectural alternatives analysis, architectural decisions, trade-offs, dependencies, and future impact, for a task whose authorized scope is architectural decision work. | Authorize implementation, determine project priority, act as Project Manager, merge PRs, render a QA Decision, implement production code merely because an ADR exists, modify a frozen business rule, reopen an accepted ADR without explicit scope/authorization, or synchronize project-wide documentation. |
| **Backend Developer** | Implementation, unit/integration tests, `ImplementationLog` phase entries, Reviewer Checklist self-assessment — for backend/Python-domain tasks. | Skip tests, expand scope, perform unrelated refactoring, continue automatically to the next task, authorize implementation, render a QA Decision, or act as a merge gate. |
| **Frontend Developer** | Implementation, unit/integration tests (RTL/Vitest), `ImplementationLog` phase entries, Reviewer Checklist self-assessment — for frontend/TypeScript/React/Electron-renderer-domain tasks. | Skip tests, expand scope, perform unrelated refactoring, continue automatically to the next task, authorize implementation, change an approved task's scope, render a QA Decision, act as a merge gate, or weaken Electron's `sandbox`/`contextIsolation`/`nodeIntegration` posture without separate explicit authorization. |
| **QA Reviewer** | Independent implementation review, QA Decision, architecture validation, regression review, documentation impact review — the sole independent review gate for both Developer roles (and for Software Architect's ADR output). | Implement features, redesign architecture during review, or approve without verification. |
| **Documentation Manager** | Synchronization of `PROJECT_STATE.json`, `docs/SessionReport.md`, `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, changelogs, release notes, and other project documentation after QA approval. | Duplicate `ImplementationLog` content, synchronize documentation before QA approval, or rewrite historical records instead of appending updates when required. |

An "Independent Technical Verifier" role has operated informally in this project's history (see
[`docs/prompts/README.md`](docs/prompts/README.md)) but is **not** formally adopted — per explicit
project-owner decision (2026-08-21), it is not listed here, and no ad hoc verification pass
following it should be treated as mandatory unless a future governance proposal defines and
authorizes it.

Full ownership assignments are defined in:

`docs/ImplementationLog/README.md`

## 8. Documentation Ownership

Summarized from [`docs/ImplementationLog/README.md`](docs/ImplementationLog/README.md#canonical-document-roles)
and [`#documentation-ownership`](docs/ImplementationLog/README.md#documentation-ownership) — that
document is authoritative; this is a pointer, not a second copy.

| Document | Canonical role | Primary owner |
|---|---|---|
| `docs/ImplementationLog/` | Implementation history | Backend Developer and Frontend Developer — two separate peer roles, each owning only its own phase logs |
| `docs/SessionReport.md` | Session summary | Documentation Manager |
| `IMPLEMENTATION_QUEUE.md` | Planning backlog | Project Manager |
| ADRs (`/ADR/`) | Architectural decisions | Software Architect — see [`docs/prompts/SoftwareArchitect.md`](docs/prompts/SoftwareArchitect.md) |
| `CHANGELOG.md` / `docs/CHANGELOG.md` | Release summary | Documentation Manager |
| `docs/releases/` | Per-version release notes | Documentation Manager |
| `README.md` / `docs/README.md` | Project entry points | Documentation Manager |
| `PROJECT_STATE.json` | Point-in-time snapshot | Documentation Manager — maintains the project's synchronized point-in-time state after implementation, QA, releases, and documentation updates. |

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
- Local `main` synchronized (`git checkout main && git pull`) before beginning the next task.

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

The canonical AI role prompts are maintained under:

`docs/prompts/`

These prompts are version-controlled alongside the repository and are the canonical instructions for each AI role.

Current standard prompts:

- `ProjectManager.md`
- `SoftwareArchitect.md`
- `BackendDeveloper.md`
- `QAReviewer.md`
- `DocumentationManager.md`

Contributors should use these repository-local prompts instead of relying on previous chat history or external prompt copies.

Changes to these prompts are governed by the project's **Process Changes are Versioned** rule and should be proposed, reviewed, and documented before adoption.