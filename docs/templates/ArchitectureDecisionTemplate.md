# Architecture Decision Proposal Template

**Purpose:** This project's charter requires an architecture proposal to be presented and
explicitly approved by the project owner **before any code is written** for anything beyond what's
already scoped (see Stage 0's and Stage 2's proposal-first process in
[docs/SessionReport.md](../SessionReport.md), and [ADR/0012](../../ADR/0012-transaction-pipeline.md)'s
"three options presented before writing any code" precedent). This template is that proposal
document — distinct from [ADR_Template.md](ADR_Template.md), which records the decision *after* it's
made. A proposal precedes an ADR; an ADR doesn't precede a proposal.

**How this differs from [ADR_Template.md](ADR_Template.md):** A proposal is written to get a
yes/no/revise answer from the project owner and may present multiple live options with no decision
yet made. An ADR is written once a decision exists, to record what was decided and why, for future
readers — not to solicit approval. Once a proposal is approved, its "Recommended Option" becomes the
ADR's "Decision," and the proposal's "Options Considered" can be summarized (or linked) rather than
re-derived.

**When to use:** Before starting a new stage, a standalone framework addition, or any change that
touches multiple modules, introduces a new pattern, or could plausibly mean several different
things (the same ambiguity that drove [ADR/0012](../../ADR/0012-transaction-pipeline.md)'s three
options). Not needed for a small, single-file, no-open-design-decision fix — see this project's own
QA review classification ("Fix Immediately" findings skip this) for the boundary.

**Copy destination:** `docs/reviews/ArchitectureProposal_<target>_<YYYY-MM-DD>.md` while awaiting
approval. Once approved, keep the file where it is (it's a review record, don't move or delete it)
and reference it from the resulting ADR's "Options Considered" section.

---

## Title

_<short, specific — e.g. "Transaction Pipeline" not "Improve transactions">_

## Date

YYYY-MM-DD

## Proposer

_<who is proposing this — a name, or "AI session per project-owner request">_

## Context / Problem

What situation makes a decision necessary right now? Name the concrete trigger: a project-owner
request, a gap another ADR already flagged and deferred, a QA finding, a Stage requirement.

## Goals

What this proposal must achieve. Be specific enough that "did we achieve this" is checkable later.

## Non-Goals

What this proposal deliberately does **not** attempt — the boundary that keeps scope from creeping.
Name anything a reader might reasonably expect this to also solve, and say explicitly why it
doesn't.

## Options Considered

For each option: a short description, then explicit pros and cons. Include at least the "don't do
this" option if declining is genuinely viable — a proposal that only presents one real option isn't
a proposal, it's an announcement.

1. **Option A** — description.
   - Pros: ...
   - Cons: ...
2. **Option B** — description.
   - Pros: ...
   - Cons: ...

## Recommended Option

Which option is recommended, and why, in one or two sentences — the detailed reasoning belongs in
the option's own pros/cons above, not repeated here.

## Impact on Existing Architecture

What this touches that already exists: ports, registrations, routes, tables, other ADRs' stated
trade-offs. If nothing existing is touched, say so explicitly ("purely additive, no existing port
or route affected") — this project's convention is to state that invariant, not leave it implicit.

## Testing / Verification Plan

How the chosen option will be proven once approved — new tests, a live smoke check, which existing
suite it must not regress.

---

## Approval

- [ ] **Approved** — proceed with the Recommended Option as-is
- [ ] **Approved with changes** — see Notes
- [ ] **Rejected** — see Notes
- [ ] **Needs revision** — see Notes, resubmit

**Date:** _____________________

**Reviewer:** _____________________

**Notes:**

_(Any changes required before proceeding, or the reason for rejection. If approved, this is also
the place to note which option was actually chosen if it differs from the recommendation.)_

## Resulting ADR

_(Filled in after implementation — link to the ADR this proposal became, e.g.
`ADR/0012-transaction-pipeline.md`.)_
