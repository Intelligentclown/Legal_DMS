# ADR-0005: Local PostgreSQL via Docker Compose

**Status:** Accepted
**Date:** 2026-08-03

## Problem

The backend needs a PostgreSQL instance for local development (running the app, running Alembic
migrations, running integration tests that eventually touch the DB). Stage 0 needed to pick how
that instance is provisioned on a developer's machine.

## Options Considered

1. **Docker Compose** — a root `docker-compose.yml` provisions Postgres with one command
   (`docker compose up -d`), consistent across machines, easy to reset (`docker compose down -v`).
   Requires Docker Desktop.
2. **Locally installed Postgres** — no Docker dependency, but connection details and version drift
   across developer machines, and setup isn't automated.
3. **Defer entirely** — wire up SQLAlchemy/Alembic config without deciding provisioning yet.

## Decision

Docker Compose. A root `docker-compose.yml` runs `postgres:16-alpine`, credentials/port
configurable via a root `.env` (copied from `.env.example`), with a named volume for data
persistence and a healthcheck (`pg_isready`).

## Reasoning

Asked directly (this was a genuine open question, not implied by the charter) — Docker Compose was
the explicit choice, on the reasoning that reproducibility across machines and easy reset/teardown
outweigh the Docker Desktop dependency for a project with an indefinite, multi-session development
horizon.

## Trade-offs

Requires Docker Desktop to be installed — Stage 0 development actually hit this: Docker wasn't
installed yet at one point mid-session, which blocked live DB verification until it was installed.
Documented as a real, encountered constraint, not just a hypothetical one — see
[SessionReport.md](../docs/SessionReport.md).

## Future Impact

Any future service dependency (Redis, a search index, etc.) should default to also being added to
this same `docker-compose.yml` for consistency, unless a specific reason argues otherwise.
