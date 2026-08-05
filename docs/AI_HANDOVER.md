# AI Handover

*Assume you are a fresh AI model with no memory of this project's prior sessions. This document
should let you continue immediately without asking clarifying questions about what already
exists.*

## Project Summary

Legal Document & Matter Management System — a desktop app (Electron + React/TS frontend, Python
FastAPI backend, PostgreSQL database) for a legal documentation office. Built to be developed over
many months across many sessions. **Stage 0 (pure infrastructure, zero business features) is
complete.** Read [Context.md](Context.md) for the full narrative if this handover isn't enough.

## Current Architecture

Clean Architecture on both sides (domain/application/infrastructure/presentation), detailed in
[Architecture.md](Architecture.md). Backend at `backend/src/app/`, frontend at `frontend/src/`,
Electron shell at `electron/`.

## Completed Features

None — Stage 0 is infrastructure only. See [FeatureRegistry.md](FeatureRegistry.md) (currently
just the "System Health Check" plumbing feature, not a business feature).

## Current Stage

Stage 0 — Project Foundation. **Complete and verified live** (see
[ProjectStatus.md](ProjectStatus.md) for the full checklist). No Stage 1 plan exists.

## Pending Work

Everything past Stage 0. **Nothing is scoped yet** — see [Roadmap.md](Roadmap.md).

## Open Issues / Known Bugs

Two tooling caveats, no code bugs — full detail in [KnownIssues.md](KnownIssues.md):
1. shadcn/ui CLI (`init`/`add`) doesn't work on this Windows environment (writes to a literal `@`
   folder instead of resolving the path alias). Add new shadcn components by hand-copying from
   ui.shadcn.com into `frontend/src/presentation/components/ui/` and fixing the `cn` import path
   to `@/shared/utils/cn`.
2. `react-router-dom` has one open `npm audit` advisory (RSC-mode CSRF) not applicable to this
   project (no RSC/framework mode used). Re-verify on any `react-router-dom` upgrade.

## Database Status

No business tables. Only Alembic's own `alembic_version` table exists (created once, verified
against a live Postgres container). See [Database.md](Database.md).

## API Status

`GET /api/v1/health` and `GET /api/v1/version` only. See [API.md](API.md).

## Folder Structure

See [FolderStructure.md](FolderStructure.md) for the full annotated tree.

## Important Decisions

Read the ADRs in [`/ADR`](../ADR/) before making architectural changes — especially before
touching the layering (ADR 0002) or the stack choice (ADR 0003). If you make a new significant
architectural decision, **add a new ADR**, don't just change things silently.

## Current Branch

`master` (this project has not yet adopted a feature-branch workflow — confirm with the project
owner before changing that).

## Files Recently Modified

Everything under `backend/`, `frontend/`, `electron/`, `docs/`, and `ADR/` was created fresh in
Stage 0 (this is a greenfield project — check `git log` for the exact commit sequence, one commit
per Stage 0 section).

## What Should Be Implemented Next

**Nothing, until the project owner decides what Stage 1 is.** The original Stage 0 charter was
explicit: *"Do NOT implement any business features. Do NOT create Matter Management, Client
Management, Property Management, Document Automation, OCR, QR, Search, Reports, Payments, or AI."*
That instruction governed Stage 0; it does not automatically expire — treat it as still in force
until the user explicitly scopes Stage 1. If asked to continue development, **ask the user what
Stage 1 should cover** rather than guessing. Do not add authentication, business entities, or new
major dependencies without that explicit direction.

## Important Warnings

- Don't run `shadcn add`/`shadcn init` expecting it to work — see Known Issues above.
- Don't hardcode a database URL anywhere — everything reads from `Settings`
  (`backend/.env`) or `VITE_API_BASE_URL` (`frontend/.env`). Copy from the respective
  `.env.example` files; the real `.env` files are gitignored and won't exist in a fresh checkout.
- Postgres must be running (`docker compose up -d` from repo root) before `alembic upgrade head`
  or any DB-touching backend work.
- The backend (`uv`) and frontend (`npm`) are two independent projects with separate lockfiles —
  don't try to unify them into an npm workspace without a deliberate reason.
- Keep this documentation set (`docs/` + `ADR/`) up to date as you work — per the project's
  explicit rule, a stage isn't done until its documentation reflects reality. See
  [DevelopmentGuide.md](DevelopmentGuide.md)'s "Documentation discipline" section.

## Recommended Implementation Order (once Stage 1 is scoped)

1. Confirm the first business feature with the project owner (don't assume it's Matter Management
   just because it's listed first in the original charter).
2. Add an ADR if the feature requires an architectural decision beyond what's already established.
3. Domain entities first (pure, in `domain/`), then application use cases (`application/`), then
   infrastructure implementations (`infrastructure/persistence/`), then presentation
   (routes/components) last — inside-out, matching the Clean Architecture dependency direction.
4. Add the Alembic migration for any new tables; update [Database.md](Database.md).
5. Update [API.md](API.md), [FeatureRegistry.md](FeatureRegistry.md),
   [ModuleRegistry.md](ModuleRegistry.md), [ProjectStatus.md](ProjectStatus.md),
   [CHANGELOG.md](CHANGELOG.md), and this file before considering the work done.
