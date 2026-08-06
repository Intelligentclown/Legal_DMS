# Project Overview

## What this is

A production-grade **desktop application** — Legal Document & Matter Management System — for a
legal documentation office managing thousands of legal matters. Built to be developed over many
months, across many sessions and potentially different AI models, so maintainability and a
faithfully-maintained project memory (this `docs/` + `ADR/` set) matter as much as the code.

## Who it's for

A legal documentation office's internal staff, managing matters, clients, properties, and
documents. (No specific personas/workflows defined yet — that's Stage 3+ scope.)

## Non-goals (for now)

Stages 0–2 are infrastructure, core architecture, and database schema only — framework and
scaffolding, not business features. Post-Stage-2, seven standalone framework additions (Command
Bus, Query Bus, Transaction Pipeline, Caching Abstraction, Module Manifest Loader, Architecture
Health Check, Performance Metrics Service) extended that same scaffolding. None of this includes,
and Stage 3 has not yet been scoped to include: Matter Management, Client Management, Property
Management, Document Automation, OCR, QR, Search, Reports, Payments, AI, or a real login mechanism.
See [Roadmap.md](Roadmap.md).

## Tech stack (summary)

Electron desktop shell, React + TypeScript + Vite + Tailwind + shadcn/ui frontend, Python +
FastAPI backend, PostgreSQL + SQLAlchemy + Alembic. Full detail and rationale in
[TechStack.md](TechStack.md).

## Architecture (summary)

Clean Architecture, mirrored on both frontend and backend (domain / application / infrastructure /
presentation), so business logic never ends up trapped in a UI component or an API route. Full
detail in [Architecture.md](Architecture.md).

## Where to start

- Continuing development right now? Read [AI_HANDOVER.md](AI_HANDOVER.md) first.
- Want current status? Read [ProjectStatus.md](ProjectStatus.md).
- Want the full narrative context in one place? Read [Context.md](Context.md).
