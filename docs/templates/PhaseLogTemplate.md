# Phase Log Template

**Purpose:** The skeleton for a new [docs/ImplementationLog/](../ImplementationLog/) phase log,
matching the standard [docs/ImplementationLog/README.md](../ImplementationLog/README.md) defines —
metadata block, eleven required sections, a Reviewer Checklist, and a QA Decision. Extracted here
per that README's own "Relationship to `docs/templates/`" note, now that the shape has recurred
(Stage 3 Phase 0, across two batches) and matured (the checklist grew to eleven items and gained the
QA Decision gate). **[docs/ImplementationLog/README.md](../ImplementationLog/README.md) remains the
authoritative standard** — if this template and that README ever disagree, trust the README and
treat this file as stale, needing a sync.

**When to use:** The moment implementation of a phase actually begins — never in advance, never
retroactively. See [docs/ImplementationLog/README.md](../ImplementationLog/README.md#when-to-create-a-phase-log)
for the full rule (this convention has zero backfilled history by design).

**Copy destination:** `docs/ImplementationLog/Stage<N>/Phase<M>.md`. One file per phase, appended to
as the phase progresses (including across multiple batches, the same way
[Stage3/Phase0.md](../ImplementationLog/Stage3/Phase0.md) handles its two) — don't split a phase
across files, and don't create a new phase file until the previous one is complete or explicitly
superseded.

---

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

Leave every metadata field blank rather than guess or pre-fill it — `Completed`, `Git Commit`, and
`Pull Request` in particular must stay empty until they're actually true, not filled in ahead of
time. See the README's "Metadata block" section for what each field means.

## Objective

\<What this phase set out to accomplish, in a sentence or two — the goal, not the task list.\>

## Tasks Implemented

\<The concrete work completed, cross-referenced to `IMPLEMENTATION_QUEUE.md` task IDs or named
findings.\>

## Files Modified

\<The actual file list (source, tests, docs) touched by this phase — generate from `git diff --stat`
or equivalent, don't reconstruct from memory.\>

## Tests Added

\<New or modified tests, named, with a one-line description of what each proves.\>

## Test Results

\<Actual pass/fail counts and the command(s) run, plus anything that couldn't be verified in the
current environment — say so explicitly rather than omit it.\>

## Design Decisions

\<Choices made during implementation worth recording — link out to a new or existing ADR rather than
duplicating its reasoning here if the decision is significant enough to warrant one.\>

## Problems Encountered

\<What went wrong and how it was resolved (or wasn't). Write "None" if genuinely nothing did.\>

## Deferred Work

\<Anything identified but deliberately not done in this phase, each with a named trigger condition
for revisiting it — not a vague "someday."\>

## Future Considerations

\<Forward-looking notes for whoever picks up the next phase — open questions, things to watch,
follow-on work this phase's decisions imply.\>

## Reviewer Checklist

The implementer's own self-assessment — mark `☑` only if actually true, leave `□` otherwise, and
say why under the checklist if the reason for an unchecked (or N/A) box isn't already obvious from
the rest of the log:

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

## QA Decision

Filled in by the QA Reviewer (see [Documentation Ownership](../ImplementationLog/README.md#documentation-ownership)),
not the implementer — leave every box unchecked until QA actually reviews the batch against the
Reviewer Checklist and the log itself:

```
QA Decision

□ Approved
□ Approved with comments
□ Rework required
```

`Approved`/`Approved with comments` → proceeds to the Documentation Manager for final documentation
synchronization and merge. `Rework required` → returns to the Developer; **documentation
synchronization and merge must wait** until a later QA Decision clears it. See
[docs/ImplementationLog/README.md#qa-decision](../ImplementationLog/README.md#qa-decision) for full
detail.
