# Legal Document & Matter Management System

A production-grade desktop application for managing legal matters, clients, and documents,
built with Electron, React, FastAPI, and PostgreSQL.

> **Status:** Stage 1 — Core Architecture & Domain Foundation complete. No business features exist
> yet. See [`docs/ProjectStatus.md`](docs/ProjectStatus.md) for the current state,
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
- [Node.js](https://nodejs.org/) 20+ and npm
- [Python](https://www.python.org/) 3.12+
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
