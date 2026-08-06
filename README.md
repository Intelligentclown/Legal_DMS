# Legal Document & Matter Management System

[![Backend](https://github.com/Intelligentclown/Legal_DMS/actions/workflows/backend.yml/badge.svg)](https://github.com/Intelligentclown/Legal_DMS/actions/workflows/backend.yml)
[![Frontend](https://github.com/Intelligentclown/Legal_DMS/actions/workflows/frontend.yml/badge.svg)](https://github.com/Intelligentclown/Legal_DMS/actions/workflows/frontend.yml)
[![Release](https://github.com/Intelligentclown/Legal_DMS/actions/workflows/release.yml/badge.svg)](https://github.com/Intelligentclown/Legal_DMS/actions/workflows/release.yml)

A production-grade desktop application for managing legal matters, clients, and documents,
built with Electron, React, FastAPI, and PostgreSQL.

> **Status:** Stage 2 — Database Architecture & Data Model complete, plus seven post-Stage-2
> framework additions (Command Bus, Query Bus, Transaction Pipeline, Caching Abstraction, Module
> Manifest Loader, Architecture Health Check, Performance Metrics Service), their QA review
> resolution, and Stage 2.7 (GitHub Actions CI). No business features exist yet. See
> [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for the current state,
> [`PROJECT_STATE.json`](PROJECT_STATE.json) for a machine-readable snapshot, and
> [`docs/Roadmap.md`](docs/Roadmap.md) for what's planned. Picking this project up fresh? Start at
> [`AI_BOOTSTRAP.md`](AI_BOOTSTRAP.md).

## Tech Stack

- **Desktop shell:** Electron
- **Frontend:** React + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL + SQLAlchemy 2.x + Alembic
- **Testing:** Pytest (backend), Vitest + React Testing Library (frontend)

See [`docs/TechStack.md`](docs/TechStack.md) for the full rationale behind each choice, and
[`docs/Architecture.md`](docs/Architecture.md) for how the Clean Architecture layers fit together.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for local PostgreSQL)
- [Node.js](https://nodejs.org/) 24+ and npm 11+ (see `engines` in `package.json` — bumped from the
  previously-undeclared "20+" as of Stage 2.7, to match the CI pipeline)
- [Python](https://www.python.org/) 3.12+ (CI is pinned to 3.14, the actual development version —
  see `ADR/0017-github-actions-ci.md`; the package's own supported floor is unchanged)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Getting Started

### 1. Start PostgreSQL

```bash
cp .env.example .env
docker compose up -d
```

### 2. Configure and run the backend

```bash
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Health check: `GET /api/v1/health`.
Interactive docs: `http://localhost:8000/docs`.

### 3. Configure and run the frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### 4. Run the Electron shell

```bash
npm install    # from the repo root, installs Electron + orchestration deps
npm run electron:dev
```

This launches Electron pointed at the Vite dev server, giving you the full desktop app with
hot reload.

## Running Tests

```bash
# Backend
cd backend
uv run pytest

# Frontend
cd frontend
npm run test
```

## Creating Database Migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "describe your change"
uv run alembic upgrade head
```

## Project Structure

See [`docs/FolderStructure.md`](docs/FolderStructure.md) for the full annotated folder tree.

## Documentation

This project maintains a full documentation set in [`docs/`](docs/) and architecture decisions
in [`ADR/`](ADR/), kept up to date at the end of every development stage so work can continue
seamlessly across sessions. Start with [`docs/AI_HANDOVER.md`](docs/AI_HANDOVER.md) if you're
picking this project up fresh.

## Coding Standards

See [`docs/CodingStandards.md`](docs/CodingStandards.md).

## Contributing / Development Workflow

See [`docs/DevelopmentGuide.md`](docs/DevelopmentGuide.md).
## Writing Rules

- Record only implementation that actually happened.
- Never record planned work as completed.
- Never duplicate ADR content.
- Never duplicate CHANGELOG entries.
- Always reference related ADRs, commits, pull requests, and releases.
- One Phase file per implementation phase.
- Once a Phase is completed, it should never be rewritten except to correct factual errors.
