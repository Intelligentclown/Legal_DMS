# AI Bootstrap

*Read this first if you're a fresh AI session picking up this project. It's a short pointer, not
the full picture — follow the links in the order given.*

## Read in this order

1. **This file** — orientation and rules.
2. **[PROJECT_STATE.json](PROJECT_STATE.json)** — machine-readable snapshot: current stage,
   completion, test counts, open issues. Check this first for a fast "where are we" answer.
3. **[docs/ProjectStatus.md](docs/ProjectStatus.md)** — the human-readable version of the same
   thing, with more narrative detail.
4. **[docs/Architecture.md](docs/Architecture.md)** — how the codebase is laid out and why.
5. **[docs/SessionReport.md](docs/SessionReport.md)** — what happened in the most recent session(s),
   including problems hit and how they were resolved.
6. **[docs/AI_HANDOVER.md](docs/AI_HANDOVER.md)** — the deep handover doc: completed work, open
   issues, warnings, and exactly what to do (and not assume) next.
7. **[IMPLEMENTATION_QUEUE.md](IMPLEMENTATION_QUEUE.md)** — the actionable task backlog for the
   current stage (granular, dependency-ordered), including any pending QA review findings and their
   classification/resolution status.

If anything in `PROJECT_STATE.json` or `docs/ProjectStatus.md` disagrees with what you find in the
actual code (`git log`, file contents), **trust the code and report the discrepancy** — don't
silently proceed on stale documentation.

## New Session Protocol

When starting a new AI session:

1. Ignore previous chat history.
2. Read [`AI_BOOTSTRAP.md`](AI_BOOTSTRAP.md) first.
3. Read [`PROJECT_STATE.json`](PROJECT_STATE.json).
4. Read the relevant handoff document (e.g. [`docs/Stage3_Backend_Handoff.md`](docs/Stage3_Backend_Handoff.md)).
5. Read the active [`ImplementationLog`](docs/ImplementationLog/).
6. Read related ADRs.
7. Use the repository as the source of truth.
8. Do not infer project state from previous conversations.
9. Summarize understanding before making changes.
10. Wait for approval before implementation.

## Non-negotiable rules for this project

- **Never implement a business feature without an explicit go-ahead.** As of Stage 2, this project
  has zero business logic by design (no Matter/Client/Property Management, no Document Automation,
  OCR, QR, Search implementation, Reports, Payments, AI, or Authentication). That's not an
  oversight — it's the charter for Stages 0–2. Stage 2 built the complete 49-table database schema,
  but **nothing is wired to it** — no repositories, services, or API routes touch it yet. Don't
  start Stage "N+1" work (including wiring the schema to a real feature) by guessing what it should
  be; ask.
- **Before writing any code**, read the docs listed above, verify the current project status
  against the actual code (run the tests, check `git log`), and report any inconsistency you find
  before proceeding.
- **Documentation is part of the codebase.** A stage isn't done until `docs/`, `ADR/`,
  `PROJECT_STATE.json`, and this file (if it needs updating) all reflect reality. See
  `docs/DevelopmentGuide.md`'s "Documentation discipline" section.
- **Task IDs are immutable.** Once a task ID has been assigned, it must never be reused for a
  different task. If scope changes:
  - Cancel the original task.
  - Create a new task ID.
  - Preserve historical references.

  Never overwrite or redefine an existing task ID. See
  [`docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md`](docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md)
  for the incident that prompted this rule.
- **Every significant architectural decision gets an ADR** in [`/ADR`](ADR/). Don't change
  architecture silently.
- **Process changes are versioned.** Any change to the project's development workflow —
  documentation standards, QA process, AI conventions, implementation workflow, release workflow,
  etc. — should be proposed, reviewed, and documented before adoption, using the same review and
  documentation discipline as architectural decisions. Process changes do not necessarily require an
  ADR, but they must be proposed, reviewed, approved, and documented before adoption. Don't silently
  start following a different process (or silently revert to an old one) just because it seems
  reasonable in the moment; propose the change, get it reviewed, and update the document that
  defines that process (e.g. this file, `docs/ImplementationLog/README.md`,
  `docs/DevelopmentGuide.md`, `docs/templates/README.md`) as part of adopting it, not after the fact.
- **When implementation of a phase actually begins, create its Implementation Log entry.** See
  [`docs/ImplementationLog/README.md`](docs/ImplementationLog/README.md) for the full standard —
  in short: `docs/ImplementationLog/Stage<N>/Phase<M>.md`, created only when that phase's
  implementation starts (never in advance, never retroactively), with the metadata block and eleven
  required sections the README defines, ending with a Reviewer Checklist (implementer
  self-assessment) and a **QA Decision** (the formal gate). This convention began 2026-08-06 with
  nothing backfilled — all prior work stays documented only in the ADRs, `docs/SessionReport.md`,
  both `CHANGELOG.md` files, `docs/ProjectStatus.md`, and `IMPLEMENTATION_QUEUE.md`, per the
  README's own scope note.
- **Every completed implementation batch needs a QA Decision before it's treated as done.** Once a
  phase log's Reviewer Checklist is filled in, record a QA Decision (`Approved` /
  `Approved with comments` / `Rework required`) — see
  [`docs/ImplementationLog/README.md`](docs/ImplementationLog/README.md#qa-decision) for exactly
  what each means. **`Rework required` blocks documentation synchronization and merge** — don't
  update `docs/AI_HANDOVER.md`/`docs/ProjectStatus.md`/`docs/SessionReport.md`/the changelogs or
  merge a batch's work until it's `Approved` or `Approved with comments`. A single AI session
  commonly plays every role in sequence (implement, self-assess, render the QA Decision, then
  synchronize documentation) — do these steps in that order, don't skip the QA Decision step just
  because one session is doing all of them.
- **Documents have a primary owner, not an exclusive one.** See
  [`docs/ImplementationLog/README.md`](docs/ImplementationLog/README.md#documentation-ownership)
  for the full assignment (Project Manager → planning docs, Software Architect → ADRs/Architecture.md,
  Developer → ImplementationLog, QA Reviewer → ArchitectureScorecard.md/QA reports/QA Decision,
  Documentation Manager → AI_HANDOVER.md/ProjectStatus.md/SessionReport.md/CHANGELOG/releases). Any
  role may update any document when genuinely necessary — this assigns who's routinely responsible,
  not who's allowed to touch it.
- **Small, reviewed sections.** When implementing multi-part work, build one subsystem/section at a
  time, verify it (tests + a live smoke check where relevant), commit, then move on — don't
  generate everything in one giant diff.

## Governance & Task Authorization Model

*(Added by T95 — Context & Governance Hardening.)* A fresh agent should be able to answer the
following from repository artifacts alone, without any conversation history:

- **What is authoritative for what?** `IMPLEMENTATION_QUEUE.md` (task backlog, authorization, and
  completion narrative — Project Manager owned) · `ADR/*.md` (accepted architecture decisions) ·
  `docs/Legal_DMS — Domain Model & Functional Specification.md` (frozen business/domain baseline,
  including the §21 Required-ADR planning list) · `docs/reviews/*.md` (per-task architecture
  self-review and QA Decision history) · `PROJECT_STATE.json` (point-in-time snapshot — its
  narrative `note` fields are the authoritative history; its optional `governanceLedger` field is a
  derived, mechanically-validated convenience view, not a second source of truth — see
  [`docs/GOVERNANCE_VALIDATION.md`](docs/GOVERNANCE_VALIDATION.md)).
- **"Required ADR #N" vs. `ADR/NNNN`.** These are two different numbering spaces. "Required ADR #N"
  is a *planning-list position* inside the specification's own §21 (1–20, e.g. "Required ADR #13,
  Financial boundary") — it is never a repository filename number. `ADR/NNNN-slug.md` is a
  *repository ADR file number*, assigned sequentially as decisions are actually written, in
  whatever order they're tackled. The two numbers coinciding (e.g. `ADR/0018` existing and also
  being unrelated to planning-list item 18) is a coincidence, not a mapping. To see which Required
  ADRs are currently resolved, by which file, run `python scripts/governance_validate.py --report`
  rather than grepping ADR files by hand — this is mechanically computed from each ADR's own
  `**Resolves:**` field, not asserted.
- **Task lifecycle.** Every task in this series follows the same repository-recorded state machine:
  *Authorized* (a row exists in `IMPLEMENTATION_QUEUE.md` containing "Authorized by the project
  owner") → *Architecture/Implementation Drafted* (its own branch/commit/PR) → *QA Decision
  Persisted* (an independent QA pass, recorded in `docs/reviews/`, re-verified against the PR's
  actual remote HEAD, not assumed) → *Merged* → *Governance Closeout* (a separate PR marks the task
  "is now Done" in its own `IMPLEMENTATION_QUEUE.md` row) → *Done*. A step is only real once it is
  independently verifiable in the repository — an authorization or QA decision that exists only in
  conversation is not sufficient (this is not hypothetical: it happened during `T94`, was caught,
  and was remediated as its own repository-recorded governance event — see `T94`'s row for the full,
  disclosed history).
- **Mechanically-checkable governance invariants** (duplicate task IDs, a "Done" task missing its
  authorization phrase, ADR numbering/filename integrity, two ADRs claiming to resolve the same
  Required ADR, dangling ADR references, `PROJECT_STATE.json`'s `governanceLedger` drifting from the
  ADR files) are enforced by `scripts/governance_validate.py` in CI
  (`.github/workflows/governance.yml`) on every push/PR. **This does not replace independent QA, and
  it does not check git ancestry** (whether a PR branch actually contains its authorization commit —
  a materially different, unresolved class of check; see
  [`docs/GOVERNANCE_VALIDATION.md`](docs/GOVERNANCE_VALIDATION.md#what-this-deliberately-does-not-validate)
  for the full, honest boundary of what this tool does and does not guarantee).

## Quick facts

- **Stack:** Electron + React/TypeScript/Vite/Tailwind/shadcn (frontend), Python/FastAPI +
  PostgreSQL/SQLAlchemy/Alembic (backend). Full rationale in
  [docs/TechStack.md](docs/TechStack.md).
- **Architecture:** Clean Architecture, mirrored on both sides. See
  [docs/Architecture.md](docs/Architecture.md).
- **Two known tooling caveats** (not bugs in this project's own code) are tracked in
  [docs/KnownIssues.md](docs/KnownIssues.md) — check there before assuming a tool "just works."
