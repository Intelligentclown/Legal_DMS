# ADR-0001: Record architecture decisions as ADRs

**Status:** Accepted
**Date:** 2026-08-03

## Problem

This project will be developed over many months, across many separate sessions, potentially by
different AI models and/or human contributors. Architectural decisions made early (stack choice,
layering, tooling trade-offs) need to survive beyond any one session's context window, with their
reasoning intact — not just the outcome.

## Options Considered

1. **No formal record** — rely on commit messages and code comments alone.
2. **A wiki or external doc tool** — decouples decisions from the repo, risks drifting out of sync
   or being inaccessible to whoever (or whatever) picks up the project next.
3. **Architecture Decision Records (ADRs) in-repo**, one file per significant decision, following
   the lightweight Nygard-style format (problem, options, decision, reasoning, trade-offs, future
   impact).

## Decision

Use in-repo ADRs, stored in `/ADR`, one file per decision, numbered sequentially.

## Reasoning

- Lives with the code, versioned alongside it — never goes stale relative to a separate wiki.
- Cheap to write, cheap to read — a future session (AI or human) can scan `/ADR` and understand
  *why* the codebase looks the way it does, not just *what* it looks like.
- Explicitly required by this project's own charter: "Never change architecture without
  documenting why."

## Trade-offs

Adds a small amount of overhead per significant decision. Worth it given the project's expected
lifespan and the number of times a fresh session will need to reconstruct context.

## Future Impact

Every future significant architectural decision (or reversal of one) gets a new ADR. See
[`ADR/template.md`](template.md) for the format.
