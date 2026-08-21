# Implementation Log

A per-phase execution record: what was actually done while implementing a specific phase of a
specific stage, written as the work happens rather than reconstructed afterward. Distinct from
this project's other documentation — see "How this differs from existing docs" below before
assuming it duplicates something else.

## When to create a phase log

**Only when implementation of that phase actually begins.** Not in advance, not as a placeholder,
and never retroactively for work that was already done and documented before this convention
existed. This convention started on 2026-08-06 with zero files under it — the project's prior
work (Stages 0–2, the post-Stage-2 framework additions, the Stage 2.5 QA review resolution, Stage
2.7 CI) is **not** backfilled here. It remains fully documented where it already lives: the ADRs,
`docs/SessionReport.md`, both `CHANGELOG.md` files, `docs/ProjectStatus.md`, and
`IMPLEMENTATION_QUEUE.md`.

The first real file under this folder is created automatically the moment Phase 0 implementation
actually starts (as of this writing, that's Stage 3 Phase 0, covering T41–T43) — not before, and
not as part of setting up this convention.

## File layout

```
docs/ImplementationLog/
  README.md              <- this file — the standard, not a log entry itself
  Stage<N>/
    Phase<M>.md           <- one file per phase, created only when that phase's
                              implementation starts
```

`<N>` and `<M>` are plain integers (`Stage3/Phase0.md`, `Stage3/Phase1.md`, ...). A stage's phases
are numbered from 0. Each phase gets exactly one file, appended to as the phase progresses — don't
split a single phase's log across multiple files, and don't create a new phase file until the
previous phase is either complete or explicitly superseded.

## Metadata block

Every phase log starts with exactly this block, before any other content:

```
------------------------------------------------

# Stage X – Phase Y

Status:

Started:

Completed:

Related Tasks:

Related ADRs:

Git Commit:

Pull Request:

Release:

------------------------------------------------
```

Field notes:

- **Status** — `Not Started` / `In Progress` / `Done` / `Blocked` (or equivalent). Update this
  live as the phase progresses, not only when it finishes — a phase log that's `In Progress` is
  more useful mid-work than one left blank until the end.
- **Started** / **Completed** — dates (`YYYY-MM-DD`). Leave `Completed` blank until the phase
  actually finishes; don't pre-fill it.
- **Related Tasks** — task IDs from `IMPLEMENTATION_QUEUE.md` (e.g. `T41–T43`) or the named
  feature(s)/finding(s) this phase covers.
- **Related ADRs** — every ADR this phase creates or is governed by, linked.
- **Git Commit** — the commit hash(es) once the phase's work actually lands. Leave blank until
  then; don't reference a commit that hasn't happened yet.
- **Pull Request** — link/number once opened. Leave blank until one exists.
- **Release** — the version/tag this phase ships in, once released. Leave blank until then — see
  `docs/releases/README.md`'s versioning convention (`currentVersion` only advances with a real
  `git tag`).

Leave a field blank rather than guess or pre-fill it — the same "an honest unchecked box beats a
falsely checked one" discipline `docs/templates/README.md` already applies to checklists applies
here to metadata fields.

**Task IDs are immutable** (see `AI_BOOTSTRAP.md`'s "Non-negotiable rules"), and that applies here
too: an Implementation Log must record the task IDs exactly as they existed at the time that phase
was actually implemented, and a completed phase log is never edited later to relabel, renumber, or
reassign those IDs if a later task reuses similar wording or a later convention changes — if a task
ID's scope was genuinely redefined mid-implementation (as happened once, see
`docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md`), the log documents that
redefinition in place, in prose, rather than silently presenting the final state as if it had been
true from the start.

## Required sections

After the metadata block, every phase log must contain these eleven sections, in this order, even
when a section is short or genuinely empty (write "None" explicitly rather than omitting a
heading — an omitted section reads as an oversight, not a deliberate "nothing to report," per the
same convention `docs/releases/README.md` uses):

| Section | What goes here |
|---|---|
| **Objective** | What this phase set out to accomplish, in a sentence or two — the goal, not the task list. |
| **Tasks Implemented** | The concrete work completed, ideally cross-referenced to `IMPLEMENTATION_QUEUE.md` task IDs or named findings. |
| **Files Modified** | The actual file list (source, tests, docs) touched by this phase — generate from `git diff --stat` or equivalent against the phase's starting point, don't reconstruct from memory. |
| **Tests Added** | New or modified tests, named, with a one-line description of what each proves. |
| **Test Results** | The actual pass/fail counts and command(s) run, plus anything that couldn't be verified in the current environment (say so explicitly rather than omit it — same "trust the code, report the discrepancy" discipline as `AI_BOOTSTRAP.md`). |
| **Design Decisions** | Choices made during implementation worth recording — link out to a new or existing ADR rather than duplicating its reasoning here if the decision is significant enough to warrant one. |
| **Problems Encountered** | What went wrong and how it was resolved (or wasn't) — mirrors the "Problems Encountered & Solutions" section already used in `docs/SessionReport.md` entries. |
| **Deferred Work** | Anything identified but deliberately not done in this phase, with a named trigger condition for revisiting it (not a vague "someday") — same style `IMPLEMENTATION_QUEUE.md` already uses for its deferred QA findings. |
| **Future Considerations** | Forward-looking notes for whoever picks up the next phase — open questions, things to watch, follow-on work this phase's decisions imply. |
| **Reviewer Checklist** | The fixed eleven-item checklist below, self-assessed honestly by the implementer at the point the phase log is written — see "Reviewer Checklist" below for the exact format and what each item means. |
| **QA Decision** | The formal QA gate that closes out the batch — see "QA Decision" below. Filled in by the QA Reviewer (see Documentation Ownership), not the implementer; leave blank until QA actually reviews rather than pre-filling it. |

## Reviewer Checklist

The implementer's own self-assessment, always this exact eleven-item list in this order:

```
Reviewer Checklist

□ Architecture preserved
□ Existing design patterns followed
□ Tests added
□ Existing tests pass
□ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
□ No unrelated refactoring
□ No scope creep
□ Ready for QA
```

Mark each box `☑` only if it's actually true, `□` (left unchecked) otherwise — same "an honest
unchecked box beats a falsely checked one" discipline `docs/templates/README.md` already applies
to checklists. An unchecked box isn't a failure; it's information — say why in a short note under
the checklist if the reason isn't already obvious from the rest of the log (e.g. "ADR updated: □ —
no architectural decision this phase, correctly none written").

| Item | What it's actually asking |
|---|---|
| **Architecture preserved** | This phase didn't violate Clean Architecture layering (`docs/Architecture.md`) or change a port/contract silently. |
| **Existing design patterns followed** | New code matches this project's established shape for the kind of thing it is (a port + one default implementation + a `container.register(...)` line for a new capability, the repository/service/route layering for a new entity, etc.) rather than inventing a new pattern where an existing one already fits — see `docs/Stage3_Backend_Handoff.md`'s "use Command Bus as your pattern template" for a worked example of this expectation. |
| **Tests added** | New behavior has new tests — not just relying on existing coverage happening to exercise it. |
| **Existing tests pass** | The full suite was actually re-run this phase, not assumed — cite the pass count. |
| **Documentation updated** | Every doc this phase's changes affect was actually updated (this file, plus whichever of `docs/Architecture.md`/`docs/AI_HANDOVER.md`/`PROJECT_STATE.json`/etc. applied) — not just this phase log in isolation. |
| **ADR updated (if required)** | A significant architectural decision got an ADR; check `□` (not failed, just N/A) if this phase made no such decision — don't leave it ambiguous which case applies. |
| **AI_BOOTSTRAP updated (if required)** | If this phase changed a non-negotiable rule, the required-reading order, or another standing convention `AI_BOOTSTRAP.md` states, that file was updated to match; check `□` (N/A) if nothing at that level changed — most phases won't touch it, and that's correctly `□`, not a gap. |
| **PROJECT_STATE updated (if required)** | If this phase changed current stage/version/test counts/completion percentage/open questions, `PROJECT_STATE.json` reflects it; check `□` (N/A) only if genuinely nothing in that file's scope changed. |
| **No unrelated refactoring** | Nothing was touched outside this phase's actual scope "while we were in there." |
| **No scope creep** | The phase delivered exactly what was asked, not more — extra ideas belong in Future Considerations/Deferred Work, not silently implemented. |
| **Ready for QA** | Someone other than the implementer could pick this phase log up and verify the work from it alone, without needing to ask clarifying questions first — this box being checked is what makes it valid to move to the QA Decision step below. |

## QA Decision

Every completed implementation batch ends with a formal QA Decision — a separate, later step from
the Reviewer Checklist above. The Reviewer Checklist is the implementer's own self-assessment; the
QA Decision is the QA Reviewer's independent judgment on top of it (see Documentation Ownership for
who that is). Don't skip straight from "Ready for QA: ☑" to treating a batch as done — the QA
Decision is what actually closes it out.

```
QA Decision

□ Approved
□ Approved with comments
□ Rework required
```

Exactly one box gets checked, by the QA Reviewer, once they've actually reviewed the batch against
its Reviewer Checklist and the log itself — not pre-filled by the implementer, and not left blank
once review happens (a QA Decision section with every box unchecked means review hasn't happened
yet, not that it happened and passed).

| Status | Meaning |
|---|---|
| **Approved** | The batch is correct as-is. Implementation may proceed to the Documentation Manager for final documentation synchronization and merge. |
| **Approved with comments** | Minor comments only — worth recording (add them as a short note under the checklist), but **no implementation changes are required**. Proceeds to the Documentation Manager the same as a plain Approved. |
| **Rework required** | The implementation returns to the Developer. **Documentation synchronization and merge must wait until QA approves** — don't let the Documentation Manager's pass or a merge happen on a batch that hasn't cleared this gate. |

A `Rework required` decision doesn't mean starting a new phase log — the same phase log gets
updated in place once rework lands (new Files Modified/Tests/Design Decisions entries appended, a
fresh Reviewer Checklist self-assessment, then a new QA Decision), the same way Phase 0's batch 2
extended batch 1's log rather than starting a new file.

## How this differs from existing docs

This project already records implementation history several other ways. A phase log is not a
fourth (or eighth) copy of the same information — it's a narrower, execution-focused shape that
none of the others provide:

- **ADRs** (`/ADR/`) — the *decision* record: what was decided architecturally and why, durable
  and rarely revisited once accepted. A phase log links to the ADRs it produced or relied on; it
  doesn't restate their reasoning.
- **`docs/SessionReport.md`** — a chronological log of *development sessions* (a session and a
  phase don't always line up 1:1 — one session can span multiple phases, or a phase can span
  multiple sessions).
- **`CHANGELOG.md` / `docs/CHANGELOG.md`** — the *release-facing* change log: added/modified
  files, new tests, lint fixes, organized by version, not by implementation phase.
- **`docs/ProjectStatus.md`** — a *point-in-time snapshot* of overall project status, rewritten to
  stay current, not a history of how any one piece of work actually happened.
- **`IMPLEMENTATION_QUEUE.md`** — the *task backlog*: what's planned and in what order, not a
  record of what happened while doing it.
- **`docs/ImplementationLog/`** (this folder) — the *execution* record for one phase of one stage
  specifically: what was actually done, in what files, with what tests, what went wrong, and what
  was deliberately deferred — written during or immediately after that phase's implementation, not
  reconstructed later from the other five documents above.

If information belongs in one of the documents above, put it there — don't duplicate it into a
phase log for convenience. A phase log may (and often should) *link* to the ADR, session report
entry, or changelog entry it corresponds to, rather than repeating their content.

## Canonical Document Roles

Formalizing the split above into an explicit project rule, since "which document is authoritative
for X" has to be unambiguous for the no-duplication discipline above to actually hold:

- **`docs/ImplementationLog/` is the canonical implementation history.** Every technical detail of
  *how* a phase was actually built — files touched, tests added, exact test results, design
  decisions made mid-implementation, problems hit and how they were resolved — has exactly one home
  here.
- **`docs/SessionReport.md` is the canonical session summary.** What happened in a given sitting,
  at the level a project owner would want to skim, not the level a reviewer would need to verify
  the work.
- **`CHANGELOG.md` / `docs/CHANGELOG.md` is the canonical release summary.** What shipped, organized
  by version, for a reader who wants to know what changed between releases.
- **An ADR is the canonical architectural decision record.** Why a decision was made, what
  alternatives were considered, and what it constrains going forward — durable, rarely revisited.
- **`IMPLEMENTATION_QUEUE.md` is the canonical planning backlog.** What's planned, in what order,
  with what acceptance criteria — before it's built, not a record of what happened while building
  it.

**Explicit no-duplication rules, following directly from the above:**

- Implementation details must **never** be duplicated inside `docs/SessionReport.md`. A session
  entry summarizes; it doesn't re-list every file touched or every test added if a phase log already
  exists for that work — it links to the phase log instead (see the Stage 3 Phase 0 session entries
  in `docs/SessionReport.md` for the pattern: a summary in prose, `docs/ImplementationLog/Stage3/Phase0.md`
  for the full detail).
- `docs/SessionReport.md` should **summarize** the work completed during the session — objectives,
  what got done at a glance, problems hit, what's next — not restate implementation detail that
  belongs in an `ImplementationLog` phase log.
- `docs/ImplementationLog/` should contain **all** technical implementation detail for the phase it
  covers — if a session entry and a phase log disagree on a technical fact, the phase log is
  authoritative for that fact.
- `CHANGELOG.md`/`docs/CHANGELOG.md` should **never** duplicate implementation details — a changelog
  entry states *what* shipped and points to the phase log/ADR for *how*, it doesn't re-explain the
  mechanism.
- ADRs should **never** duplicate implementation history — an ADR records the *decision*, not the
  step-by-step account of building it; that account belongs in the phase log that implemented the
  decision, cross-linked back to the ADR.

**Responsibilities, one line each:** `ImplementationLog` answers "what actually happened, in
enough detail to verify it." `SessionReport` answers "what happened in this sitting, at a glance."
`CHANGELOG` answers "what shipped, by version." An ADR answers "why was this decided, and what does
it constrain." `IMPLEMENTATION_QUEUE` answers "what's planned, and in what order." If a piece of
information doesn't clearly answer one of these five questions, it probably belongs in whichever
document's question it's closest to — not copied into more than one.

## Documentation Ownership

Every document in this project has a primary editor — the role best positioned to keep it accurate,
because they're the one doing the work it records. This assigns **primary responsibility, not
exclusive ownership**: any role may update any document when it's genuinely necessary (a Developer
fixing a stale test count in `PROJECT_STATE.json`, a Documentation Manager correcting a typo in an
ADR), but the primary owner is who should be doing so routinely, and who a reviewer should ask if a
document in their column looks wrong.

| Role | Owns (primary editor) |
|---|---|
| **Project Manager** | `IMPLEMENTATION_QUEUE.md`; `docs/Roadmap.md`; planning documents generally (scoping, sequencing, acceptance criteria before work starts). |
| **Software Architect** | ADRs (`/ADR/`); `docs/Architecture.md`; interface/port documentation; architecture decisions generally. |
| **Backend Developer** | `docs/ImplementationLog/` (its own phase logs, backend/Python-domain tasks); developer notes; technical implementation documentation. |
| **Frontend Developer** | `docs/ImplementationLog/` (its own phase logs, frontend/TypeScript/React/Electron-renderer-domain tasks); developer notes; technical implementation documentation. Peer role to Backend Developer, not a subordinate or merged variant — see [`docs/prompts/FrontendDeveloper.md`](../prompts/FrontendDeveloper.md), formally adopted 2026-08-22. |
| **QA Reviewer** | `docs/ArchitectureScorecard.md`; QA reports (`docs/reviews/*_QA_Review.md`); test verification records; the **QA Decision** on each implementation batch (see above). |
| **Documentation Manager** | `docs/AI_HANDOVER.md`; `docs/ProjectStatus.md`; `docs/SessionReport.md`; both `CHANGELOG.md` files; release notes (`docs/releases/`); README updates project-wide; [`PROJECT_STATE.json`](../../PROJECT_STATE.json) (assigned 2026-08-07 — a synchronization document that changes after implementation, QA, releases, and documentation updates, the same consistency-maintenance role this row already covers for everything else in it). |

This maps directly onto the QA Decision workflow above: a Developer's phase log reaches "Ready for
QA," a QA Reviewer records the QA Decision, and only once it's `Approved`/`Approved with comments`
does work proceed to the Documentation Manager for final synchronization (`docs/AI_HANDOVER.md`,
`docs/ProjectStatus.md`, `docs/SessionReport.md`, the changelogs) and merge. A single AI session
often plays every role in sequence on a given piece of work — this table still applies; it says
*which hat you're wearing* when you touch a given document, not that five different people must be
involved.

## Relationship to `docs/templates/`

Extracted into [`docs/templates/PhaseLogTemplate.md`](../templates/PhaseLogTemplate.md), following
the process `docs/templates/README.md` describes ("only extract something into a template here once
the same document shape has actually recurred") — the shape had recurred (Stage 3 Phase 0, across
two batches) and matured (the checklist grew to eleven items and gained the QA Decision gate) by the
time it was extracted. **This README remains the authoritative standard** — if the template and this
file ever disagree, trust this file and treat the template as needing a sync.
