# Project Documentation

This is the project's persistent memory — kept up to date across every development stage so work
can continue seamlessly in a new session, or with a different AI model, without re-deriving
context. See the root [README.md](../README.md) for how to install/run/test the project itself.

## Start here

- **[/AI_BOOTSTRAP.md](../AI_BOOTSTRAP.md)** — picking this project up cold? Read this first (it
  points you to everything else in the right order).
- **[/PROJECT_STATE.json](../PROJECT_STATE.json)** — machine-readable status snapshot.
- **[AI_HANDOVER.md](AI_HANDOVER.md)** — the deep handover doc: completed work, open issues,
  warnings, what to do next.
- **[Context.md](Context.md)** — full narrative context in one place (goal, architecture, status,
  decisions, what's next) — written at the end of Stage 0; treat as historical background rather
  than current status.
- **[ProjectStatus.md](ProjectStatus.md)** — single source of truth for what's done/pending.
- **[ArchitectureScorecard.md](ArchitectureScorecard.md)** — architectural maturity dashboard:
  every capability's status, stage, and notes in one place, plus an Overall Architecture Health
  assessment.
- **[releases/](releases/)** — one comprehensive, frozen-in-time document per released version
  (features, fixes, breaking changes, known issues, what's next). Current release:
  [releases/v0.3.8.md](releases/v0.3.8.md).
- **[templates/](templates/)** — reusable document skeletons (currently: the pre-stage checklist
  that must be completed before starting any new stage).

## Reference

| Document | Covers |
|---|---|
| [ProjectOverview.md](ProjectOverview.md) | What this project is, who it's for, non-goals |
| [Roadmap.md](Roadmap.md) | Feature status by stage |
| [Architecture.md](Architecture.md) | Clean Architecture layering, folder-by-folder |
| [Database.md](Database.md) | Tables, migrations, local DB setup |
| [ERD.md](ERD.md) | Entity-relationship diagram for the full schema |
| [API.md](API.md) | Endpoints, request/response shapes, error format |
| [FolderStructure.md](FolderStructure.md) | Full annotated folder tree |
| [CodingStandards.md](CodingStandards.md) | Backend/frontend conventions |
| [TechStack.md](TechStack.md) | Every technology choice and why |
| [DevelopmentGuide.md](DevelopmentGuide.md) | Setup, running, testing, linting, migrations |
| [CHANGELOG.md](CHANGELOG.md) | Per-stage changelog (files added/modified, breaking changes) |
| [KnownIssues.md](KnownIssues.md) | Open tooling caveats and their workarounds |
| [FutureIdeas.md](FutureIdeas.md) | Parked ideas, not yet planned |
| [FeatureRegistry.md](FeatureRegistry.md) | One entry per business feature (empty — none built yet) |
| [ModuleRegistry.md](ModuleRegistry.md) | One entry per code module: purpose, status, owner |
| [SessionReport.md](SessionReport.md) | Log of each development session |
| [reviews/](reviews/) | Point-in-time QA/code review reports (e.g. the post-Stage-2 QA review) |

## Architecture Decision Records

See [`/ADR`](../ADR/) — one file per significant architectural decision, with the problem,
options considered, decision, reasoning, and trade-offs. Add a new one whenever a significant
architectural decision is made or reversed; never change architecture silently.

## The rule

**A development stage is not complete until this documentation reflects reality.** If code
changed and these documents didn't, treat the stage as unfinished.
