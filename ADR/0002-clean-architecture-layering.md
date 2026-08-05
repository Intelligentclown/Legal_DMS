# ADR-0002: Clean Architecture layering on both frontend and backend

**Status:** Accepted
**Date:** 2026-08-03

## Problem

The project's charter requires maintainability, scalability, and testability over a many-month
development horizon, explicitly stating: "Business logic must never exist inside UI. Database code
must never exist inside API routes. Every module must be replaceable." Stage 0 has to establish a
structure that supports this before any business logic exists — retrofitting layering onto an
already-tangled codebase is much more expensive than starting with it.

## Options Considered

1. **No enforced layering** — a typical small-FastAPI/small-React structure (routes call the DB
   directly, components fetch data directly). Fast to start, but business logic and I/O concerns
   tend to end up mixed into routes/components as the app grows, exactly what the charter warns
   against.
2. **Clean Architecture (Domain / Application / Infrastructure / Presentation)**, mirrored
   independently on both backend and frontend, with dependencies only pointing inward.
3. **A different layered pattern** (e.g. classic MVC, hexagonal/ports-and-adapters without the
   explicit 4-layer split) — conceptually similar to Clean Architecture but less prescriptive
   about where things go, which risks inconsistency across a project touched by many sessions.

## Decision

Clean Architecture, applied the same way on both sides:

```
Presentation → Application → Domain
                    ↑
             Infrastructure (implements Application's ports)
```

Backend: `domain/`, `application/` (with `errors/` and `interfaces/`), `infrastructure/` (with
`config/`, `logging/`, `database/`, `persistence/`), `presentation/` (with `api/` and
`middleware/`). Frontend: `domain/types/`, `application/services/`, `infrastructure/` (`api/`,
`ipc/`), `presentation/` (`layouts/`, `pages/`, `components/`), plus an `app/` composition root
and a cross-cutting `shared/`.

## Reasoning

- Directly satisfies the charter's explicit requirements (no business logic in UI, no DB code in
  routes, every module replaceable).
- The same mental model on both frontend and backend reduces the cognitive cost of a session (AI
  or human) switching between them.
- Empty seams (`application/interfaces/`, `infrastructure/persistence/`, `workers/`,
  `application/services/`) are cheap to create now and mark exactly where future feature code
  belongs, rather than requiring future sessions to invent the pattern.

## Trade-offs

- Real overhead for a Stage 0 with no business logic yet — several folders exist that are
  currently empty or near-empty. This is accepted as the explicit point of Stage 0: pay the
  structural cost while it's free (nothing to migrate) rather than later (when it's expensive).
- FastAPI's `DBSessionDep` gives routes a raw `AsyncSession` directly rather than routing every DB
  access through a repository interface from day one — a pragmatic exception for session
  *plumbing*, not business logic. Actual queries still belong in a repository/use case once one
  exists for a given feature.

## Future Impact

Every future business feature should add its domain entities first, then application use cases,
then infrastructure repository implementations, then presentation (routes/components) last —
inside-out, matching the dependency direction. If this layering starts causing friction once real
features land, that's worth a new ADR re-evaluating it — but the default going forward is: use the
existing seams, don't invent parallel structure.
