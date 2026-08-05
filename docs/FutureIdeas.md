# Future Ideas

Not planned/scheduled — parked here so they aren't forgotten. Promote to
[Roadmap.md](Roadmap.md) with a real stage/priority when they're actually being considered.

## Packaging & distribution

- How does the Python backend ship inside the Electron desktop installer? Options not yet
  evaluated: bundling a Python runtime (PyInstaller/Nuitka), requiring a system Python + venv setup
  step, or running the backend as a separate installed service. Currently the backend runs as a
  standalone process during development only.
- pgAdmin (or similar) as an optional service in `docker-compose.yml` for local DB inspection.

## Backend

- Task queue / background worker (the `workers/` folder is a placeholder) — needed once OCR,
  indexing, or any long-running job exists. No dependency chosen yet (Celery vs. arq vs. something
  else) — decide when there's an actual job to run.
- `/health` could grow a `/health/ready` variant that *does* check DB connectivity, once there's a
  real operational need (e.g. container orchestration readiness probes) — deliberately not added
  in Stage 0 to keep liveness DB-independent.

## Frontend

- Re-attempt the shadcn CLI once a fixed version ships (see [KnownIssues.md](KnownIssues.md)) —
  would let `shadcn add` work directly instead of manual copy-paste.
- A `Card` shadcn primitive (and others) as real UI needs them — Stage 0 only added `Button`,
  the minimum needed to prove the pattern.

## Explicitly out of scope until later stages

Per the Stage 0 charter: Matter Management, Client Management, Property Management, Document
Automation, OCR, QR, Search, Reports, Payments, AI, and Authentication/login. Do not start any of
these without an explicit go-ahead — see [Roadmap.md](Roadmap.md).
