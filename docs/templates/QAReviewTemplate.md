# QA Review Template

**Purpose:** The skeleton for a QA review report, matching the shape of
[docs/reviews/Stage_2_5_QA_Review.md](../reviews/Stage_2_5_QA_Review.md) — this project's existing
precedent for how a review is structured, findings are ranked, and each finding is eventually
classified and resolved (or explicitly deferred/accepted). Keeping every QA review in this same
shape is what makes [IMPLEMENTATION_QUEUE.md](../../IMPLEMENTATION_QUEUE.md)'s "QA Review Findings"
section able to summarize any of them consistently.

**When to use:** Before starting a new stage, or after a batch of related standalone additions ship
— a review of what actually landed against Architecture, Performance, SOLID, Maintainability,
Security, Scalability, Thread Safety, Error Handling, and Code Duplication (adapt the dimension list
to what's actually relevant; not every review needs all nine).

**Copy destination:** `docs/reviews/<Scope>_QA_Review.md` — name the scope specifically (e.g.
`Stage_2_5_QA_Review.md`, not `QA_Review.md`), since multiple reviews will accumulate in
`docs/reviews/` over time and each needs to be identifiable by its scope alone.

---

# \<Scope\> QA Review

**Scope:** What was reviewed — name the specific modules/files/features, and what's explicitly
**out of scope** (this project's precedent explicitly separates a QA review's scope from the
formal `IMPLEMENTATION_QUEUE.md` backlog when they're not the same thing — say so if that applies
here too).

**Reviewed:** The exact file paths/modules examined, so a future reader can tell what was and
wasn't actually looked at.

**Evaluated against:** The dimensions this review checked (Architecture, Performance, SOLID,
Maintainability, Security, Scalability, Thread Safety, Error Handling, Code Duplication, or a
narrower subset relevant to this scope).

**Date:** YYYY-MM-DD

**Resolution status:** Update this line as findings get fixed — state which finding IDs are
resolved, what was verified (tests passing, no regression), and which remain open. Leave as "No
code has been changed; findings below are as originally scoped" until the first fix lands.

---

## Summary judgment

2–4 sentences: the overall verdict. What's solid, what's the one or two things that actually need
real attention versus everything else being lower-severity or forward-looking. Be honest about
scope creep or ambiguity encountered while reviewing (this project's precedent explicitly notes when
a review "took longer to do correctly" because of a specific reason — that's useful signal, not
noise).

---

## Findings, ranked by severity

For each finding: a numbered heading naming the defect and its category in parentheses, the file
and line reference, a code excerpt if it clarifies the issue, an explanation of *why* it matters and
under what condition it would actually bite (not just that it theoretically could), and a suggested
fix with a note on urgency/blocking dependencies.

### 1. \<Finding title\> (\<Category\>)

`path/to/file.py:NN-NN`:

```python
# relevant excerpt
```

Explanation of the defect and its real-world trigger condition.

**Suggested fix:** ...

_(Repeat per finding, most severe first.)_

---

## Dimension-by-dimension notes

One paragraph per dimension evaluated (Architecture, Performance, SOLID, Maintainability, Security,
Scalability, Thread Safety, Error Handling, Code Duplication, or whichever subset applies) — what
was checked and the verdict, even for dimensions with nothing wrong (say so explicitly rather than
omitting a dimension silently).

---

## Test coverage assessment

What the existing tests actually prove versus what they don't — this project's convention is to be
precise about the difference (e.g. "tested" is not the same claim as "proven correct against a real
resource" until one exists).

---

## Suggested improvements (not applied — review only)

A numbered, priority-ordered list distinguishing "do soon, cheap" from "do when \<dependency\>
lands" from "watch, don't act." Each item should name its own trigger condition for when it becomes
actionable, not just "someday."

---

*(As fixes land, add a `> **RESOLVED (Txx, YYYY-MM-DD):** ...` blockquote directly under the
relevant finding, describing what was actually fixed and how it was verified — matching
[docs/reviews/Stage_2_5_QA_Review.md](../reviews/Stage_2_5_QA_Review.md)'s precedent. Don't delete
or rewrite the original finding — the resolution note sits alongside it as a permanent record.)*
