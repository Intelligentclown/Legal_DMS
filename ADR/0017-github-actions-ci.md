# ADR-0017: GitHub Actions CI

**Status:** Accepted
**Date:** 2026-08-06

## Problem

The project has no continuous integration. Every check that exists today (backend lint/format/
test, frontend lint/format/test, Electron/frontend build) is run manually per `DevelopmentGuide.md`
— nothing verifies a push or pull request automatically. The project owner requested this as
"Stage 2.7 — GitHub Actions CI," a mini-stage distinct from the numbered Stage 0–2 sequence and
from the post-Stage-2 framework additions (Command Bus, Query Bus, etc.), with an explicit,
narrower charter: validate every push and pull request (backend validation, frontend validation,
formatting, linting, unit tests, build verification, an artifact strategy if needed), while
explicitly deferring integration tests, Docker, and deployment to a documented future-expansion
list rather than guessing at them now.

## Options Considered

1. **One workflow file with three jobs** (`ci.yml`: `backend`, `frontend`, `build` jobs). Simpler
   to navigate as a single file; still gives three independent status checks via job names.
2. **Three separate workflow files** (`backend.yml`, `frontend.yml`, `release.yml`), each
   self-contained with its own triggers. More files, but each is independently readable, and a
   future change to one concern's triggers (e.g. `release.yml` eventually gaining a
   tag-triggered packaging job) doesn't require touching the other two.
3. **A monorepo-style matrix workflow** dynamically detecting which paths changed and running only
   the relevant checks. Rejected as premature optimization — this repo has exactly two independent
   projects (`backend/`, `frontend/`) plus a small Electron shell; a static three-file split already
   gives full parallelism without the added complexity of path-filtering logic.

## Decision

Option 2, per explicit project-owner direction: three workflow files —

- **`backend.yml`** — backend validation: `ruff check`, `black --check`, `pytest tests/unit`, and an
  application-import smoke test (`from app.main import app`), against Python **3.14** (the actual
  version `uv` resolves and runs locally today — confirmed via `uv run python --version` inside
  `backend/`, not the `pyproject.toml` floor of `>=3.12`).
- **`frontend.yml`** — frontend validation: `eslint`, `prettier --check`, `vitest run`, against
  Node **24.13.1** / npm **11.11.1** (the versions actually installed and in use today, per `node
  --version` / `npm --version`).
- **`release.yml`** — build verification only: `npm run build` (compiles `electron/*.ts`, then
  builds the frontend via `tsc -b && vite build`), with build outputs uploaded as short-retention
  artifacts. **No packaging (`electron-builder`) and no deployment** — the name anticipates where
  this file grows once a release process is actually scoped, but today it does exactly what
  `backend.yml`/`frontend.yml` do for their concerns: prove the code builds, nothing more.

All three trigger identically:

```yaml
on:
  push:
    branches: [main, "feature/**", "hotfix/**", "release/**"]
  pull_request:
    branches: [main]
```

Per explicit project-owner direction: **integration tests and deployment are not implemented in
this stage** (see Future Impact). Three more items — Dependabot, a pull request template, and issue
templates — are recorded as backlog entries in `IMPLEMENTATION_QUEUE.md` but also explicitly not
implemented now.

## Reasoning

- **Three files over one:** matches the project owner's explicit naming instruction
  (`backend.yml`/`frontend.yml`/`release.yml`), and keeps each concern's future evolution isolated
  — `release.yml` is the one most likely to grow (packaging, then eventually deployment) without
  that growth touching files that validate unrelated code.
- **Python 3.14, not the 3.12 floor:** the project owner's instruction was to pin CI to "the
  project's current development version," not the package's minimum-supported version — a
  deliberate change from this ADR's own draft plan (which had proposed the 3.12 floor, to catch
  compatibility drift). Trade-off accepted below.
- **Node 24.13.1 / npm 11.11.1, matching the new `engines` field:** the project owner's separate
  instruction to add `engines` to both `package.json` files using current versions means CI must
  not contradict that constraint — running CI on an older Node than `engines` declares as the floor
  would be internally inconsistent. Both decisions are pinned to the same discovered versions for
  that reason, even though only the Python pin was explicitly called out as a CI instruction.
- **Branch scope (`main`, `feature/**`, `hotfix/**`, `release/**` on push; `main` only on PR):**
  explicit project-owner direction, and a reasonable read of "every push and pull request" scoped
  to the branch-naming convention this repo is expected to use, rather than literally every branch
  name that could ever exist.
- **Integration tests deferred:** most of `tests/integration/` needs a live Postgres connection
  (`conftest.py`'s `db_session` fixture), which needs a service container, migrations applied, and
  a decision about how failures there should be reported — meaningfully more setup than
  `tests/unit/`, and explicitly out of scope for this stage per direction.
- **No deployment:** no deployment target, mechanism, or environment has been decided for this
  project at all (it's a desktop app) — building deployment automation now would mean guessing at
  an unscoped decision, which this project's standing rule explicitly prohibits.

## Trade-offs

- **Pinning to the exact current dev version (Python 3.14, Node 24.13.1) instead of the documented
  floors (Python `>=3.12`, "Node.js 20+")** means CI no longer catches "does this still work on the
  oldest version we claim to support" — it only proves "does this work on what's actually installed
  today." If the project ever needs to support the older floor again, that's a separate, undetected
  risk this pipeline does not cover. Accepted per explicit direction; worth revisiting if the
  supported-version floor is ever load-bearing (e.g. before a public release).
- **The new `engines` field silently raises the project's effective minimum Node version** from the
  previously documentation-only "20+" (never enforced anywhere) to `>=24.13.1` (now declared in
  both `package.json` files, and what `npm install`/`npm ci` will warn about if violated). This is a
  real, if minor, backward-compatibility change, not just a CI detail — `README.md` and
  `docs/DevelopmentGuide.md`'s Prerequisites sections were updated in the same pass so the
  documented floor doesn't contradict the new `engines` field. Python's documented floor
  (`>=3.12` in `pyproject.toml`) is unaffected — only the CI-tested version changed, not the
  package's own supported-version declaration.
- **`push` on every branch matching the four patterns plus `pull_request` targeting `main`** means a
  commit on a `feature/**` branch with an open PR against `main` triggers the pipeline twice for the
  same commit (once per event). Mitigated with a `concurrency` group per workflow/ref, which cancels
  a superseded in-progress run but doesn't eliminate the double-trigger itself. Accepted as a minor,
  well-known GitHub Actions cost, not a correctness problem.
- **`release.yml` does not yet do anything a "release" workflow implies** (no packaging, no
  publishing, no versioning) — the name is intentionally ahead of the implementation, which could
  read as misleading until Future Expansion catches up. Mitigated with an explicit header comment in
  the file itself stating its current scope.
- **No integration-test signal in CI at all yet** — a change that passes `backend.yml` could still
  break schema/repository-level behavior that only the deferred `tests/integration/` suite would
  catch. Accepted per explicit scope; tracked as Future Expansion, not silently dropped.

## Future Impact

- **Integration tests:** add a Postgres 16 (`postgres:16-alpine`, matching `docker-compose.yml`)
  GitHub Actions service container — most likely as a fourth job/step group in `backend.yml` — plus
  an `alembic upgrade head` step, then `pytest tests/integration`, with an explicit check that no
  tests were silently skipped (the `db_session` fixture skips gracefully on an unreachable database,
  which would otherwise make a broken service container look identical to "everything passed").
- **Docker:** no Dockerfile exists yet for the backend. Designing one (and a CI job to build it) is
  separate future work, not implied by this ADR.
- **Full Electron packaging / deployment:** `release.yml` growing to run `electron-builder` across
  an OS matrix, and any actual publishing/deployment mechanism, both require their own explicit
  scoping decision from the project owner first — not assumed here.
- **Dependabot, PR template, issue templates:** recorded as backlog items in
  `IMPLEMENTATION_QUEUE.md`, explicitly not built in this stage. A future dependency-audit CI gate
  (if ever added) needs to explicitly carve out the already-accepted `react-router-dom` advisory
  (`docs/KnownIssues.md`) so it doesn't immediately fail on an already-evaluated, accepted risk.
- **Branch protection requiring these checks to pass** is a GitHub repository *setting*, not
  something this ADR or any commit can configure — it needs to be enabled manually (Settings →
  Branches) by whoever has admin access, and only after the workflows have run at least once.
