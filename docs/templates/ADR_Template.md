# ADR Template

**Purpose:** The skeleton for a new Architecture Decision Record. **The authoritative copy used
for actually creating a new ADR is [`/ADR/template.md`](../../ADR/template.md)** — that file
predates this folder and is what `cp ADR/template.md ADR/00NN-title.md` should target. This file
exists so every template in the project is discoverable in one place from `docs/templates/`; keep
it byte-for-byte identical to `/ADR/template.md` whenever that file's shape changes, rather than
letting the two drift into two different "canonical" ADR shapes.

**When to use:** Any time a new significant architectural decision is made — a new port, a new
cross-cutting pattern, a reversal of a prior decision, anything [AI_BOOTSTRAP.md](../../AI_BOOTSTRAP.md)'s
"every significant architectural decision gets an ADR" rule covers. If the decision needs
project-owner approval *before* code is written (this project's standing charter for anything
beyond what's already scoped), fill out
[ArchitectureDecisionTemplate.md](ArchitectureDecisionTemplate.md) first — its "Recommended Option"
becomes this ADR's "Decision" once approved.

**Copy destination:** `ADR/00NN-title.md`, where `NN` is the next unused ADR number (see
[`/ADR`](../../ADR/) for the highest number currently in use) and `title` is a short kebab-case
slug.

---

# ADR-NNNN: <Title>

**Status:** Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
**Date:** YYYY-MM-DD

## Problem

What decision needs to be made, and why now? Name the specific trigger (a project-owner request, a
gap another ADR already flagged, a QA finding) rather than a generic motivation.

## Options Considered

1. **Option A** — description, pros/cons.
2. **Option B** — description, pros/cons.

If this decision was preceded by an approved [ArchitectureDecisionTemplate.md](ArchitectureDecisionTemplate.md)
proposal, this section can summarize it and link to the proposal's full detail rather than
repeating it verbatim.

## Decision

Which option was chosen, stated precisely enough that a future reader knows exactly what was built
(file/module names, port signatures, registration details) without opening the diff.

## Reasoning

Why this option over the others — the actual trade-offs weighed, not just a restatement of the
chosen option's description.

## Trade-offs

What we're giving up, and what risk we're accepting. Name the specific scenario where the trade-off
would start to matter (e.g. "fine with zero callers; becomes a real risk once X exists") so a future
reader can tell when to revisit this.

## Future Impact

What this constrains or enables for later decisions. When would this need revisiting — name the
trigger condition explicitly (a dependency landing, a caller appearing, a scale threshold) rather
than leaving "someday" implicit.
