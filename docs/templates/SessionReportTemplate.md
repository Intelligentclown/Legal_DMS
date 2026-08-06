# Session Report Template

**Purpose:** The skeleton for a new entry in [docs/SessionReport.md](../SessionReport.md), matching
the shape every existing session entry already uses (see that file's "Session: 2026-08-05 —
Performance Metrics Service" entry for a full worked example). Keeping every session entry in this
same shape is what lets a fresh AI session or new contributor read the log and understand exactly
what happened, in what order, without guessing at an inconsistent format.

**When to use:** At the end of every development session — a session being one coherent unit of
work (a stage, a standalone framework addition, a QA-fix-and-documentation-sync pass), not
necessarily one calendar sitting.

**Copy destination:** Append as a new `## Session: <date> — <Title>` section at the **end** of
[docs/SessionReport.md](../SessionReport.md) — the file is chronological, oldest first; never
insert out of order or edit a previous session's entry to reflect later reality (if later work
changes something a past entry said, note that in the *new* entry, don't rewrite history).

---

## Session: YYYY-MM-DD — \<Title\>

**Objectives:** What this session set out to do, and why — name the specific request or trigger
(a project-owner ask, a QA finding, a scoped stage) rather than a generic goal. If a design decision
had to be made along the way (which option, whether to ask a clarifying question or proceed), state
the reasoning here, matching this project's existing precedent of explaining *why* a judgment call
was made a particular way.

**Completed Tasks:**
1. ...
2. ...

_(A numbered list of concrete, specific deliverables — not vague summaries. Each item should be
identifiable against the actual diff.)_

**Problems Encountered & Solutions:** Anything that didn't go as expected and how it was resolved —
including environment constraints (e.g. "no Docker available, so integration tests could not be
re-run") stated as a fact, not glossed over. If nothing went wrong, say "None" rather than omitting
the section.

**Files Modified:** The actual file list touched this session (source, tests, docs, ADRs) — group
by category if it's long.

**Documentation Updated:** Which docs were updated as part of this session — this project's rule is
that a session isn't done until its documentation reflects reality, so this list should be
non-empty for any session that changed anything observable.

**Tests Executed:**
- Backend: \<suite\> — \<count\> passed \<+/- delta from before\>.
- Frontend: \<suite\> — \<count\> passed.
- Both: linter status.
- Any verification gap (e.g. a suite that couldn't be run in this environment) stated explicitly,
  not silently assumed passing.

**Next Session Goals:** What's left, if anything — or "None set" if this was a fully scoped,
standalone unit of work. If there's a note worth leaving for whoever picks this up next (a design
precedent to follow, a deferred decision, an explicit "don't assume X" warning), put it here — this
project's existing entries consistently do this and it's part of why the handover works.
