# Legal_DMS — Project Owner Briefing & Multi-Agent Handoff Protocol

**Purpose of this file:** equip an incoming AI session (ChatGPT, or any other model) to act as
**Project Owner** for the Legal_DMS project, and to define the handoff protocol between Claude Code
and any fallback agent. This file was compiled by an extensive, direct read of every governance
document, ADR, template, prompt, and status file in this repository (not summarized from memory or
from a prior conversation) — see §12 for the full list of source documents consulted.

**This file is a briefing, not a replacement for the repository.** The repository is always the
source of truth (see §2's Repository-First Rule). Whoever acts as Project Owner should still verify
live state (`git log`, `git status`, `IMPLEMENTATION_QUEUE.md`'s actual current content,
`PROJECT_STATE.json`) rather than trusting this document's snapshot indefinitely — it will go stale
the moment more work lands. Treat it as a fast-start map, not a permanent oracle.

---

## 1. What "Project Owner" means in this project

Legal_DMS runs a deliberately strict, role-separated AI development workflow (see §5 for the full
lifecycle). **Project Owner** is not one of the four AI roles (Project Manager, Backend Developer,
QA Reviewer, Documentation Manager) — it is the **human-equivalent authority above all of them**.
Nothing in this workflow proceeds to implementation without the Project Owner's explicit approval.
Concretely, the Project Owner:

- **Approves or rejects scope before any code is written.** The Project Manager role identifies the
  next unfinished task and recommends it; the Project Owner is the one who says yes.
- **Approves architecture proposals** (`docs/templates/ArchitectureDecisionTemplate.md` submissions)
  before an ADR is written recording the decision.
- **Signs off on Pre-Stage Checklists** (`docs/templates/PreStageChecklist.md`) before a new stage
  or standalone framework addition begins.
- **Resolves ambiguity** the AI roles are required to flag rather than guess at (e.g. task-ID
  discrepancies, out-of-charter requests, the `role_permissions` exact matrix still needing sign-off
  — see §9).
- **Authorizes confirm-first actions** — commits, pushes, PRs, anything the project's own rules
  treat as requiring a human go-ahead rather than being implied by "proceed."
- **Is the audience for every "flagged, not scheduled" item** this project's documents accumulate —
  those exist specifically because an AI role isn't authorized to decide them unilaterally.

**A hard governance rule this project enforces on itself, repeatedly, with real historical
failures and fixes (see §10):** authorization must be **recorded in the repository, as its own
commit, before implementation begins** — not merely stated in a conversation. If you are acting as
Project Owner and you approve something, the correct next step (performed by the Project Manager
role) is a documentation-only commit recording that approval in `IMPLEMENTATION_QUEUE.md` and
`PROJECT_STATE.json`, committed *before* any implementation commit exists. This project has a
five-batch-and-counting streak (T56–T61) of getting this right after four consecutive failures
(T52–T55) — don't be the session that breaks the streak.

---

## 2. Repository-First Rule (applies to every role, including Project Owner)

- The repository is always the single source of truth — not chat history, not memory, not this
  file.
- Never rely on previous conversation history to reconstruct project state.
- Rebuild context from the repository (`git log`, `git status`, `git branch`, actual file contents)
  before approving or recommending anything.
- Never assume a task number — read `IMPLEMENTATION_QUEUE.md`'s actual current content.
- If documentation and implementation disagree, trust the code, then report (and fix) the
  discrepancy — this project has done this correction publicly and repeatedly (see
  `docs/reviews/Documentation_Consistency_Report_2026-08-06.md`), which is a sign of a healthy
  process, not a red flag.

---

## 3. Project Identity

**What it is:** A production-grade **desktop application** — a Legal Document & Matter Management
System — for a legal documentation office managing thousands of legal matters. Built to be
developed over many months, across many sessions and potentially different AI models, which is why
this exhaustive `docs/`/`ADR/` governance system exists at all: it is the project's persistent
memory.

**Who it's for:** A legal documentation office's internal staff — matters, clients, properties,
documents. No client-facing portal is planned (see D5, §9).

**Non-goals so far:** Stages 0–2 were infrastructure, core architecture, and database schema only —
zero business features. Stage 3 (in progress) is the *first* business-adjacent feature:
Authentication & Authorization. Matter Management, Client Management, Property Management, Document
Automation, OCR, QR, Search, Reports, Payments, AI features, and Cloud Sync are all named in the
original charter but **not started, not scoped, and must not be assumed** — see
`docs/Roadmap.md`'s "Stage 4+ — Not yet planned" table.

**Repository:** GitHub, `Intelligentclown/Legal_DMS`, branch `main` protected, PR-based workflow
(see §5).

---

## 4. Tech Stack & Architecture (summary — full detail in `docs/TechStack.md`, `docs/Architecture.md`)

| Layer | Choice |
|---|---|
| Desktop shell | Electron 43 (`contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`) |
| Frontend | React 19 + TypeScript + Vite 8 + Tailwind CSS v4 + shadcn/ui (hand-copied components — CLI broken on Windows, see `docs/KnownIssues.md`) |
| Backend | Python ≥3.12 (CI pinned to 3.14) + FastAPI on Uvicorn |
| ORM / Migrations | SQLAlchemy 2.x (async) + Alembic |
| Database | PostgreSQL 16 (Alpine), local via `docker-compose.yml` |
| Package managers | `uv` (backend), `npm` (frontend) — two independent projects, separate lockfiles, deliberately not unified |
| Testing | Pytest + pytest-asyncio + httpx (backend), Vitest + React Testing Library (frontend) |
| CI | GitHub Actions — `backend.yml`, `frontend.yml`, `release.yml` (see ADR-0017) |

**Architecture:** Clean Architecture, mirrored independently on backend and frontend — dependencies
point inward only:

```
Presentation → Application → Domain
                    ↑
             Infrastructure (implements Application's ports)
```

The backend has a genuinely elaborate **framework layer** built entirely before any business
feature: a hand-rolled DI container, repository pattern, base service, validation/pagination/query/
response frameworks, a generic CRUD router factory (never mounted), an event bus, a command bus, a
query bus, a transaction pipeline, a caching abstraction, a module manifest loader, an architecture
health check (the one piece wired into real startup), a performance metrics service, a background
job framework, file storage/notification/search/auth/audit abstractions, a plugin architecture, a
workflow engine, and feature flags. **Almost all of it is scaffolding with zero business callers by
design** — see `docs/ArchitectureScorecard.md` for a capability-by-capability maturity dashboard.

---

## 5. Standard Development Lifecycle

```
Project Manager → Backend Developer → QA Reviewer → Documentation Manager
    → Git Commit → Push → GitHub Actions → Pull Request → Merge
    → Delete Branch → Update Local main → Next Task
```

| Step | What happens |
|---|---|
| **Project Manager** | Rebuilds repository state from scratch, identifies the next unfinished task from `IMPLEMENTATION_QUEUE.md`'s actual current content, verifies dependencies/phase-gates/blockers, then **waits for explicit Project Owner approval** before anything proceeds. |
| **Backend Developer** | Implements exactly the approved task — nothing more. Writes/extends tests. Records the work in a `docs/ImplementationLog/Stage<N>/Phase<M>.md` entry. Self-assesses against the eleven-item Reviewer Checklist. Stops — does not review its own work or continue to the next task automatically. |
| **QA Reviewer** | Independently re-verifies the implementation (re-reads the diff, re-runs tests, checks scope) — does not just transcribe the Developer's self-assessment. Renders a **QA Decision**: `Approved` / `Approved with comments` / `Rework required`. `Rework required` sends it back — nothing downstream happens until it clears. |
| **Documentation Manager** | Only after `Approved`/`Approved with comments` exists: synchronizes `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md` (marking the task done, not re-scoping it), `docs/SessionReport.md`, `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, changelogs, release notes — without duplicating what the phase log already records. |
| **Git Commit → Push → CI → PR → Merge → Branch cleanup → Local sync** | Standard mechanics — see §6. |
| **Next Task** | Cycle restarts with the Project Manager — never assume the next task number from a prior conversation. |

**One AI session commonly plays every role in sequence** within a single sitting — this workflow
still applies; it defines which "hat" is worn at each step, not that five separate people/sessions
must be involved.

### The Four AI Roles — responsibilities and hard boundaries

Full canonical prompts live in `docs/prompts/*.md` (copy-ready, meant to be pasted verbatim to start
a session in that role). Summarized:

**Project Manager** (`docs/prompts/ProjectManager.md`)
- Owns: repository state reconstruction, task identification, dependency validation, sequencing,
  stage gates, documentation-consistency detection (reporting only).
- Must never: implement code, review code, render a QA Decision, modify any document besides
  planning documents (`IMPLEMENTATION_QUEUE.md`, `docs/Roadmap.md`), assume a task number, or
  proceed to implementation without explicit Project Owner approval.

**Backend Developer** (`docs/prompts/BackendDeveloper.md`)
- Owns: implementing the approved task, tests, its own phase-log entry, Reviewer Checklist
  self-assessment.
- **Required approval checkpoint (§5 of that prompt):** must summarize its understanding of the
  approved scope and **wait for explicit approval of that summary** before writing any code — this
  is distinct from, and in addition to, the Project Owner's task-level authorization. This
  checkpoint has been skipped at least once in this project's history (T53) and is explicitly
  tracked as a governance deviation, not silently forgiven.
- Must never: implement without that checkpoint, expand scope, skip tests, render the QA Decision,
  or synchronize project-wide documentation (that's the Documentation Manager's job, after QA).

**QA Reviewer** (`docs/prompts/QAReviewer.md`)
- Owns: independent architecture/scope/regression/test review, the QA Decision itself.
- Must never: implement or fix code during a review (findings get reported, not silently patched),
  pre-approve, or let a `Rework required` batch proceed to documentation sync or merge.

**Documentation Manager** (`docs/prompts/DocumentationManager.md`)
- Owns: `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md` task-done marking, `docs/SessionReport.md`,
  `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, changelogs, release notes.
- Must never: implement code, redesign architecture, duplicate `ImplementationLog` technical detail
  elsewhere, or synchronize documentation for a batch that doesn't yet have a QA Decision of
  `Approved`/`Approved with comments`.

### Documentation Ownership (primary, not exclusive)

| Document | Primary owner |
|---|---|
| `docs/ImplementationLog/` (phase logs) | Backend/Frontend Developer |
| `docs/SessionReport.md`, `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, both `CHANGELOG.md` files, `docs/releases/`, `PROJECT_STATE.json` | Documentation Manager |
| `IMPLEMENTATION_QUEUE.md`, `docs/Roadmap.md` | Project Manager |
| `/ADR/`, `docs/Architecture.md` | Software Architect (a role not otherwise separately defined in this project's prompt set — architecture decisions still flow through the Project Owner for approval) |
| `docs/ArchitectureScorecard.md`, `docs/reviews/*_QA_Review.md`, the QA Decision itself | QA Reviewer |

Any role may correct any document when genuinely necessary — this assigns routine responsibility,
not exclusive permission.

### QA Decision meanings

- **Approved** — proceeds to the Documentation Manager and merge.
- **Approved with comments** — minor notes only, no implementation changes required, proceeds the
  same as Approved.
- **Rework required** — returns to the Backend Developer. Documentation sync and merge must wait.

### Definition of Done (`docs/DefinitionOfDone.md`)

A task is not done until **all** of: implementation complete, acceptance criteria met, tests added
and the full suite re-run (cite the actual count, never assume), QA Decision is `Approved`/`Approved
with comments`, documentation synchronized, ADR created if the work made an architectural decision,
all three GitHub Actions workflows green, PR merged, branch deleted, local `main` updated, release
notes updated if applicable.

---

## 6. Branch, Git, and Release Mechanics

- **Branch prefixes:** `feature/<name>` (task implementation), `docs/<topic>` (documentation-only),
  `bugfix/<name>`, `hotfix/<issue>`, `refactor/<module>`.
- Created off an up-to-date `main`, before implementation begins; deleted after merge.
- **Commits:** conventional-commit-style prefixes (`feat(auth): ...`, `docs(project): ...`, `test:
  ...`, `ci: ...`), matching this repo's actual history.
- **PRs** are opened only once a task's implementation, tests, and QA Decision (`Approved`/`Approved
  with comments`) exist. All three GitHub Actions workflows must pass. **Standard merge commits** —
  this project does not squash or rebase-merge.
- **Releases:** `PROJECT_STATE.json`'s `currentVersion` and a new `docs/releases/vX.Y.Z.md` only
  advance together with an actual `git tag` — not per completed task/phase. Current tagged version:
  **v0.3.1**. Intermediate work between tags is still fully recorded in `docs/CHANGELOG.md`/
  `docs/SessionReport.md`, just not given its own version number.

---

## 7. Non-Negotiable Rules (from `AI_BOOTSTRAP.md` and `PROJECT_WORKFLOW.md`)

- **Never implement a business feature without an explicit go-ahead.** Zero business logic exists by
  design through Stage 2; Stage 3 (auth) is the first exception, and it proceeds task-by-task, each
  requiring its own authorization.
- **Task IDs are immutable, permanently reserved.** Once assigned (e.g. `T44`), a task ID's meaning
  never changes — a scope change gets a *new* ID, the old one is cancelled/deferred/superseded in
  place, never silently redefined. This rule exists **because it was violated once** (the T44/T45 ID
  reuse incident, 2026-08-06 — see `docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md`)
  and was formally adopted afterward specifically to prevent recurrence.
- **Every significant architectural decision gets an ADR** in `/ADR/` — 20 exist today (see §11).
  Don't change architecture silently.
- **Process changes are versioned** — the same discipline as architecture: propose, review, document
  before adoption, never silently start (or revert to) a different process.
- **Every completed implementation batch needs a recorded QA Decision before it's treated as done.**
  `Rework required` blocks documentation sync and merge.
- **Small, reviewed sections.** One subsystem/task at a time, verified, committed — never one giant
  diff.
- **Documents have a primary owner, not an exclusive one** (§5).

---

## 8. Document Map — everything in this repository

### Root governance
| File | Purpose |
|---|---|
| `AI_BOOTSTRAP.md` | Entry point for any fresh AI session — required reading order, non-negotiable rules. |
| `PROJECT_WORKFLOW.md` | The full development-lifecycle operating manual (this file's §5–§7 summarize it). |
| `PROJECT_STATE.json` | Machine-readable point-in-time snapshot — stage, version, test counts, git state, open questions. |
| `PROJECT_CHECKPOINT.md` | Human-readable current-state snapshot, rewritten in place (not appended) at every meaningful checkpoint — the fastest "where are we right now" read. |
| `IMPLEMENTATION_QUEUE.md` | The actionable, dependency-ordered task backlog for the *current* stage — 1,101 lines as of this writing, covering Stage 2.5 (unapproved hardening backlog), the QA-review-findings-turned-tasks, Stage 2.7 (CI), and the full Stage 3 task table (T41–T81) with narrative history of every authorization/implementation/QA/closeout cycle. |
| `CHANGELOG.md` (root) | Short, version-indexed pointer list. |
| `README.md` | Project entry point — stack, setup instructions, CI badges. |

### `docs/` — narrative & reference
| File | Purpose |
|---|---|
| `AI_HANDOVER.md` | The deep handover doc — completed work, open issues, warnings, exactly what to do next. Currently carries the full T41–T60 narrative. |
| `ProjectStatus.md` | Single source of truth for done/pending — **flagged stale**, stuck describing pre-Stage-3 status (known documentation debt, see §13). |
| `ArchitectureScorecard.md` | Capability-by-category maturity dashboard — **also flagged stale**, same reason. |
| `Context.md` | Full narrative written at the end of Stage 0 — explicitly self-labeled historical, not current. |
| `Roadmap.md` | Stage-by-stage feature status pointer. |
| `Architecture.md` | Clean Architecture layering, folder-by-folder. |
| `TechStack.md` | Every technology choice and why. |
| `Database.md` / `ERD.md` | Full 50-table schema reference (49 Stage-2 tables + `refresh_tokens`) and Mermaid ER diagram. |
| `API.md` | Endpoint reference — **stale**, still only documents `/health`/`/version`; the six real Stage-3 auth routes aren't reflected here yet. |
| `FolderStructure.md` | Full annotated folder tree. |
| `CodingStandards.md` | Backend/frontend conventions. |
| `DevelopmentGuide.md` | Setup, running, testing, linting, migrations, CI. |
| `DefinitionOfDone.md` | The outer completion gate (§5). |
| `KnownIssues.md` | Open tooling caveats (shadcn CLI on Windows, one accepted npm advisory, Docker-dependency for integration tests). |
| `FutureIdeas.md` | Parked, unscheduled ideas. |
| `FeatureRegistry.md` | One entry per real business feature — currently empty except infrastructure. |
| `ModuleRegistry.md` | One entry per code module — purpose, status, owner. |
| `SessionReport.md` | Chronological development-session log (1,922 lines) — narrative, not implementation detail. |
| `CHANGELOG.md` (docs/) | Detailed, per-addition changelog (648 lines). |
| `Stage3_Backend_Handoff.md` | File-by-file implementation brief for Stage 3 Phases 0–4 (T41–T68) — the granular "what file, what shape" reference the Backend Developer role reads before coding. |

### `docs/ImplementationLog/` — the canonical execution record
| File | Purpose |
|---|---|
| `README.md` | The standard itself — metadata block, eleven required sections, Reviewer Checklist, QA Decision, Documentation Ownership, Canonical Document Roles (no-duplication rules across ImplementationLog/SessionReport/CHANGELOG/ADR/IMPLEMENTATION_QUEUE). |
| `Stage3/Phase0.md` | T41–T45 — the `get_db()` commit fix (hard prerequisite), auth deps/config, `AuthenticationProvider` interface change. Four batches, including a CI hotfix. Status: Done. |
| `Stage3/Phase1.md` | T46–T51 — password hashing, JWT utility, `refresh_tokens` migration, `AuthService`. Status: Done. |
| `Stage3/Phase2.md` | T52–T57 — real `AuthenticationProvider`/`AuthorizationService`, `RequirePermission`, DI wiring, bearer-token extraction, 401/403 distinction. 1,529 lines — carries the full governance-failure/recovery narrative (T52–T55 authorization-recording failures, T56 onward fixed). Status: Done. |
| `Stage3/Phase3.md` | T58–T60 (and, once implemented, T61) — the actual HTTP routes: login, refresh, logout. 627 lines. Status: In Progress. |

### `docs/prompts/` — canonical AI role instructions
`README.md`, `ProjectManager.md`, `BackendDeveloper.md`, `QAReviewer.md`, `DocumentationManager.md`
— see §5 for full summary. These are meant to be copied verbatim to start a session in that role,
not re-derived from scratch each time.

### `docs/templates/` — reusable document skeletons
| Template | Use it for | Copy destination |
|---|---|---|
| `PreStageChecklist.md` | The gate every stage/standalone addition must pass before its first line of code. | `docs/reviews/PreStageChecklist_<target>_<date>.md` |
| `ADR_Template.md` (mirrors `/ADR/template.md`, the authoritative copy) | Recording an architectural decision after it's made. | `ADR/00NN-title.md` |
| `ArchitectureDecisionTemplate.md` | Proposing a decision *before* code, to get Project Owner approval — precedes an ADR. | `docs/reviews/ArchitectureProposal_<target>_<date>.md` |
| `Feature_Template.md` | Documenting a new real business feature. | Append to `docs/FeatureRegistry.md` |
| `Module_Template.md` | Documenting a substantial new code module. | Expand `docs/ModuleRegistry.md` / `docs/Architecture.md` |
| `QAReviewTemplate.md` | Running and recording a QA review. | `docs/reviews/<Scope>_QA_Review.md` |
| `SessionReportTemplate.md` | Logging a development session. | Append to `docs/SessionReport.md` |
| `ReleaseTemplate.md` | Writing a release note for a version bump. | `docs/releases/vX.Y.Z.md` |
| `APIEndpointTemplate.md` | Documenting a new route mounted into the real app. | Append to `docs/API.md` |
| `DatabaseMigrationTemplate.md` | Documenting a new Alembic migration. | `docs/Database.md` / `docs/ERD.md` |
| `PhaseLogTemplate.md` | Starting a new `docs/ImplementationLog/` phase entry. | `docs/ImplementationLog/Stage<N>/Phase<M>.md` |

**Discipline every template shares:** copy it, never edit the template in place; fill every section
against verified reality, not memory; leave a box unchecked rather than falsely mark it done — "an
honest unchecked box beats a falsely checked one" is a repeated, explicit principle across this
project's documentation system.

### `docs/reviews/` — point-in-time review artifacts (never edited after sign-off)
| File | Purpose |
|---|---|
| `Stage_2_5_QA_Review.md` | QA review of 7 post-Stage-2 framework additions — 9 findings (Q1–Q9) classified and mostly resolved/deferred/accepted. |
| `Documentation_Consistency_Report_2026-08-06.md` | Full documentation-drift audit — found and fixed 6 stale-doc issues, scored the doc set 9/10. |
| `Documentation_Migration_Note_T44_T45_2026-08-06.md` | Canonical disambiguation record for the T44/T45 task-ID reuse incident — the origin of the "task IDs are immutable" rule. |
| `PreStageChecklist_Stage3_2026-08-07.md` | The completed, signed-off Stage 3 pre-stage checklist (several boxes honestly left unchecked with reasons) — Reviewer: Dhimant Patel. |

### `docs/releases/`
`README.md` (the release-notes system explained), `v0.3.1.md` (current, only tagged release beyond
the corrected `v0.3.0`).

### `ADR/` — 20 Architecture Decision Records
See §11 for the full index with one-line summaries.

### `docs/HANDOFF/` (this folder — untracked as of this writing)
| File | Purpose |
|---|---|
| `CHATGPT_PROJECT_HANDOFF.md` | This file. |
| `T61_HANDOFF.md` | The full implementation-scope handoff for the currently-authorized-but-unimplemented task, `GET /api/v1/auth/me` — see §10. |

---

## 9. Locked-In Architecture Decisions Relevant to Current Work (D1–D7, ADR-0018/0019/0020)

Stage 3 (Authentication & Authorization) required seven concrete design decisions, all approved by
the Project Owner and recorded:

| # | Decision | Approved choice | ADR |
|---|---|---|---|
| D1 | Token mechanism | JWT access token (~15–30 min) + DB-backed, revocable refresh token (`refresh_tokens` table) | ADR-0018 |
| D2 | Password hashing | Argon2id via `argon2-cffi` | ADR-0018 |
| D3 | JWT library | `PyJWT` | ADR-0018 |
| D4 | First-admin bootstrap | One-time CLI command, interactive `getpass`-style password prompt — **never** argv/env/file | ADR-0018 |
| D5 | Self-registration | None — only admin-created users via a `users:manage`-protected route | ADR-0018 |
| D6 | Frontend token storage (Electron) | Refresh token in `safeStorage` (OS-encrypted); access token in-memory only, lost on restart | ADR-0018 |
| D7 | `AuthenticationProvider` signature | `async def get_current_user(self, token: str \| None) -> CurrentUser` — a deliberate breaking change to a Stage-1 port | ADR-0019 |

Plus **ADR-0020** — the `get_db()` session commit/rollback policy (a hard prerequisite fixed before
any Stage 3 writes could persist at all: the session previously never committed, only `flush()`ed,
so every write silently vanished — this was the very first thing Stage 3 had to fix, T42/T43).

**Still open, not one of D1–D7, needs explicit Project Owner sign-off before it's implemented:** the
exact `role_permissions` matrix (T66) — which of the 18 seeded permissions each of the 6 seeded
roles gets. A proposed matrix exists in `IMPLEMENTATION_QUEUE.md` but was never formally approved.

---

## 10. Current State (as verified this session)

- **Branch:** `main`, clean working tree except `docs/HANDOFF/` (untracked).
- **Latest commit:** `cca1077` — "Merge pull request #29 from Intelligentclown/docs/t61-authorization".
- **Stage:** 3 — Authentication & Authorization, Phase 3 (routes).
- **Done and merged:** T41–T60 in full. Three real routes exist:
  `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` (plus
  `/health`/`/version`). 403/403 backend tests passing, 9/9 frontend, lint clean throughout.
- **T61 (`GET /api/v1/auth/me`)** — **authorized** (commit `520026f`, merged as `cca1077`, *before*
  any implementation exists — the sixth consecutive batch to record authorization before code, after
  T52–T55's four consecutive failures to do so). **Not yet implemented.** A full implementation
  handoff exists at `docs/HANDOFF/T61_HANDOFF.md` (currently untracked/uncommitted) specifying exact
  scope: return only `id`/`display_name`/`roles` from the existing `CurrentUser`, wrapped in
  `ApiResponse[MeResponse]`, requiring authentication only (no specific RBAC permission), touching
  only `presentation/api/v1/auth.py` and a new `tests/integration/test_auth_me.py`.
- **T62–T67 remain not started, not authorized** (user management routes, role assignment, cross-
  route integration tests, audit-log wiring, the `role_permissions` seed migration, the bootstrap
  CLI).
- **Governance streak worth knowing about:** T52, T53, T54, and T55 each shipped without their
  authorization being committed to the repository *before* implementation began — a real, repeatedly
  disclosed process failure, not erased from the record even after being fixed. Starting with T56,
  five consecutive batches (T56, T57, T58, T59, T60) got this right, and T61's authorization also
  landed correctly. **If you are approving T61's implementation (or any future task) as Project
  Owner, the expectation is that this authorization gets committed to the repo before code exists —
  that discipline is now the proven norm, not the exception.**

---

## 11. ADR Index (20 total, `/ADR/`)

| # | Title | One-line summary |
|---|---|---|
| 0001 | Record architecture decisions as ADRs | Established the ADR practice itself. |
| 0002 | Clean Architecture layering | Domain/Application/Infrastructure/Presentation, mirrored on both sides, dependencies point inward. |
| 0003 | Electron + React/TS + FastAPI + Postgres stack | Why the charter-mandated stack fits. |
| 0004 | Security foundation placeholders | What Stage 0 prepared for future auth (error types, CORS, middleware) without building auth itself. |
| 0005 | Docker Compose for local Postgres | Reproducibility over a bare local install. |
| 0006 | Hand-rolled DI container | ~70 lines, no new dependency, covers exactly what's needed; `DBSessionDep` deliberately stays outside it. |
| 0007 | Audit logging without a DB table | *Superseded by 0009.* Structured logs only, Stage 1. |
| 0008 | Persistence models, not domain entities | Stage 2's 49 tables are plain SQLAlchemy models — no separate domain layer, no `relationship()` until a feature needs one. |
| 0009 | `audit_logs` table reverses 0007 | Stage 2's explicit schema request was the "concrete driving need" 0007 said to wait for. |
| 0010 | Command Bus | Single-handler dispatch port + `InMemoryCommandBus`, framework only. |
| 0011 | Query Bus | Symmetric sibling to Command Bus. |
| 0012 | Transaction Pipeline | `UnitOfWork` (first non-singleton registration) + `TransactionPipelineBehavior`, a `CommandBus` decorator. |
| 0013 | Caching Abstraction | Standalone `Cache` port, not a `QueryBus`-wrapping pipeline. |
| 0014 | Module Manifest Loader | Reads/imports a JSON manifest; doesn't register (registration stays each module's own import-time side effect). |
| 0015 | Architecture Health Check | The only post-Stage-2 addition wired into real app startup — resolves every DI registration at boot. |
| 0016 | Performance Metrics Service | Standalone `MetricsService` port, logs structured JSON, no real backend wired. |
| 0017 | GitHub Actions CI | Three workflow files, pinned to actual dev-environment tool versions, integration tests/Docker/deployment explicitly deferred. |
| 0018 | Authentication & Authorization Architecture | Records D1–D6 (see §9). |
| 0019 | `AuthenticationProvider` interface change | Records D7 — the breaking port signature change. |
| 0020 | Session commit/rollback policy | `get_db()` now commits on success, rolls back on exception — the hard prerequisite for every Stage 3 write. |

---

## 12. Source Documents Consulted for This Briefing

Every file below was read in full (not skimmed, not inferred) as part of compiling this briefing:
`AI_BOOTSTRAP.md`, `PROJECT_WORKFLOW.md`, `PROJECT_STATE.json`, `PROJECT_CHECKPOINT.md`,
`IMPLEMENTATION_QUEUE.md` (full, both halves), `CHANGELOG.md`, `README.md`; every file in
`docs/prompts/`; every file in `docs/templates/`; all 20 files in `ADR/` plus `ADR/template.md`; all
four files in `docs/reviews/`; both files in `docs/releases/`; `docs/ImplementationLog/README.md`
plus `Stage3/Phase0.md` and `Stage3/Phase1.md` in full (`Phase2.md`/`Phase3.md` were cross-verified
via their exhaustive summaries already carried in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json`/
`docs/AI_HANDOVER.md` rather than re-read line-by-line, given those summaries were independently
confirmed consistent); `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, `docs/ArchitectureScorecard.md`,
`docs/Architecture.md`, `docs/TechStack.md`, `docs/Roadmap.md`, `docs/Stage3_Backend_Handoff.md`,
`docs/CodingStandards.md`, `docs/DefinitionOfDone.md`, `docs/DevelopmentGuide.md`,
`docs/FolderStructure.md`, `docs/FutureIdeas.md`, `docs/ModuleRegistry.md`, `docs/README.md`,
`docs/API.md`, `docs/Context.md`, `docs/FeatureRegistry.md`, `docs/Database.md`, `docs/ERD.md`,
`docs/KnownIssues.md`; both files currently in `docs/HANDOFF/`. `docs/SessionReport.md` (1,922
lines) and `docs/CHANGELOG.md` (648 lines) were not read line-by-line for this pass — they are
chronological narrative logs whose substance is already carried, in condensed and cross-checked
form, by the documents above; treat that as a known gap in this briefing's coverage, not a claim
those files were read.

---

## 13. Known Documentation Debt (disclosed, not hidden)

- **`docs/ProjectStatus.md` and `docs/ArchitectureScorecard.md` are stale**, still describing
  pre-Stage-3 status — flagged repeatedly in `PROJECT_CHECKPOINT.md`'s Active Risks table, never
  fixed. If you're relying on either for current status, cross-check against `PROJECT_STATE.json`/
  `PROJECT_CHECKPOINT.md` instead.
- **`docs/API.md` doesn't yet document the three real Stage 3 routes** (`login`/`refresh`/`logout`)
  — still shows only `/health`/`/version`.
- **Three "version" numbers coexist by design**, not accident: `PROJECT_STATE.json`'s
  `currentVersion` (project/stage progress), `backend/pyproject.toml`'s package version, and root
  `package.json`'s Electron-shell version — independently tracked, no single canonical scheme.
- **The T44/T45 orphaned original content is closed but permanently unnumbered** — see
  `docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md`.
- **`docs/HANDOFF/` itself is currently untracked** in git — worth committing given this project's
  own rule that governance/authorization records belong in the repository, not left as working-tree
  state.

---

## 14. Multi-Agent Handoff Protocol

### 14.1 Strict Single-Agent Rule

- **Claude Code is the PRIMARY AI coding/review agent** for this project.
- **Antigravity is FALLBACK ONLY** — used when Claude Code's usage limit is exhausted or Claude Code
  is unavailable.
- Claude Code and Antigravity must **never** operate concurrently on this repository.
- Before switching agents, the current agent must stop, the repository must be checked
  (`git status`, `git log`/HEAD), and a handoff record created or updated before the next agent
  begins.
- The incoming agent must independently verify the repository before continuing — never trust the
  outgoing agent's self-report at face value.
- Handoff files (this one included) never override authoritative repository governance
  (`AI_BOOTSTRAP.md`, `PROJECT_WORKFLOW.md`, `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`).

### 14.2 Temporary Baton-Pass File (`docs/HANDOFF/AI_SESSION_HANDOFF.md`)

Used only for a real Claude Code ↔ Antigravity session handoff — do not create this file unless an
actual agent switch is occurring. Does not exist as of this writing.

### 14.3 Task-Specific Handoff Files (`docs/HANDOFF/T<N>_HANDOFF.md`)

Created only after a task is formally authorized (never in advance). Contains: authorization record
and its commit, exact scope, allowed files, forbidden files, acceptance criteria, required tests,
stop conditions, implementation constraints, QA requirements, documentation requirements. `T61_HANDOFF.md`
is the current live example — see §10.

### 14.4 Core Governance Rules (this protocol's own list, consistent with §7 above)

1. Repository governance is authoritative.
2. `IMPLEMENTATION_QUEUE.md` controls implementation authorization.
3. `PROJECT_CHECKPOINT.md` and `PROJECT_STATE.json` must remain synchronized.
4. No implementation work may begin without explicit task authorization.
5. The Backend Developer must receive and acknowledge the exact implementation scope before coding.
6. QA Reviewer must not implement fixes while performing review.
7. Documentation Manager must not silently change application behavior.
8. Every role must independently verify repository state before acting.
9. Never assume another agent's report is correct without verification.
10. Preserve the existing checkpoint state — don't regress a closed task.
11. A task remains **not authorized** until the Project Owner explicitly approves it.
12. Never create a new governance mechanism merely because it seems useful, unless explicitly
    authorized.
13. Do not modify governance files merely to record process changes unless existing governance
    explicitly permits it.

---

## 15. If You Are Picking This Up as Project Owner Right Now

1. Verify §10's "Current State" against the live repository yourself — don't trust this snapshot
   past the moment more work has landed.
2. The next decision point is **T61** — it's authorized and handed off
   (`docs/HANDOFF/T61_HANDOFF.md`), but not yet implemented. You don't need to re-authorize it; the
   Backend Developer role can proceed once it performs its own required understanding-checkpoint
   (§5's Backend Developer boundary).
3. Consider whether `docs/HANDOFF/` should be committed — it currently sits untracked, which this
   project's own discipline (governance belongs in the repository) would flag as a gap if left
   indefinitely.
4. Do not authorize T62 or later out of sequence — this project's own rule is one task/batch at a
   time, each individually authorized, never "and also start the next one."
5. If anything in this file conflicts with the live repository, the repository wins — update this
   file to match, don't silently act on the stale version.
