# AI Bootstrap

*Read this first if you're a fresh AI session picking up this project. It's a short pointer, not
the full picture — follow the links in the order given.*

## Read in this order

1. **This file** — orientation and rules.
2. **[PROJECT_STATE.json](PROJECT_STATE.json)** — machine-readable snapshot: current stage,
   completion, test counts, open issues. Check this first for a fast "where are we" answer.
3. **[docs/ProjectStatus.md](docs/ProjectStatus.md)** — the human-readable version of the same
   thing, with more narrative detail.
4. **[docs/Architecture.md](docs/Architecture.md)** — how the codebase is laid out and why.
5. **[docs/SessionReport.md](docs/SessionReport.md)** — what happened in the most recent session(s),
   including problems hit and how they were resolved.
6. **[docs/AI_HANDOVER.md](docs/AI_HANDOVER.md)** — the deep handover doc: completed work, open
   issues, warnings, and exactly what to do (and not assume) next.

If anything in `PROJECT_STATE.json` or `docs/ProjectStatus.md` disagrees with what you find in the
actual code (`git log`, file contents), **trust the code and report the discrepancy** — don't
silently proceed on stale documentation.

## Non-negotiable rules for this project

- **Never implement a business feature without an explicit go-ahead.** As of Stage 2, this project
  has zero business logic by design (no Matter/Client/Property Management, no Document Automation,
  OCR, QR, Search implementation, Reports, Payments, AI, or Authentication). That's not an
  oversight — it's the charter for Stages 0–2. Stage 2 built the complete 49-table database schema,
  but **nothing is wired to it** — no repositories, services, or API routes touch it yet. Don't
  start Stage "N+1" work (including wiring the schema to a real feature) by guessing what it should
  be; ask.
- **Before writing any code**, read the docs listed above, verify the current project status
  against the actual code (run the tests, check `git log`), and report any inconsistency you find
  before proceeding.
- **Documentation is part of the codebase.** A stage isn't done until `docs/`, `ADR/`,
  `PROJECT_STATE.json`, and this file (if it needs updating) all reflect reality. See
  `docs/DevelopmentGuide.md`'s "Documentation discipline" section.
- **Every significant architectural decision gets an ADR** in [`/ADR`](ADR/). Don't change
  architecture silently.
- **Small, reviewed sections.** When implementing multi-part work, build one subsystem/section at a
  time, verify it (tests + a live smoke check where relevant), commit, then move on — don't
  generate everything in one giant diff.

## Quick facts

- **Stack:** Electron + React/TypeScript/Vite/Tailwind/shadcn (frontend), Python/FastAPI +
  PostgreSQL/SQLAlchemy/Alembic (backend). Full rationale in
  [docs/TechStack.md](docs/TechStack.md).
- **Architecture:** Clean Architecture, mirrored on both sides. See
  [docs/Architecture.md](docs/Architecture.md).
- **Two known tooling caveats** (not bugs in this project's own code) are tracked in
  [docs/KnownIssues.md](docs/KnownIssues.md) — check there before assuming a tool "just works."
