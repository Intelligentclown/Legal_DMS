# Documentation Consistency Report

**Date:** 2026-08-06
**Scope:** Full documentation sync following the 2026-08-06 QA review resolution (T20/T21 —
`docs/reviews/Stage_2_5_QA_Review.md`, `IMPLEMENTATION_QUEUE.md`). Documentation only — no source
code, tests, or ADRs were modified in this pass.

---

## Method

Read the full repository (backend `src`/`tests`/`alembic`, frontend `src`, all of `docs/`, `ADR/`,
root-level docs). Verified specific claims against source rather than trusting existing docs:
re-ran the backend unit suite (175/175 pass), collected the full backend test count via
`pytest --collect-only` (282), ran the frontend suite (9/9 pass), ran `ruff check` / `black --check`
(clean), counted database tables via `grep __tablename__` (49) and migration files (12), inspected
`transaction_pipeline_behavior.py` and `metrics.py`/`logging_metrics_service.py` directly to confirm
the T20/T21 fixes are actually in source, and delegated a second independent pass (a research
subagent) to cross-check 16 secondary docs against source for factual drift. Findings below combine
both passes; every item was verified against the file, not just cited from the other pass.

---

## Files Updated (17 documentation files, 1 new report)

| File | What changed |
|---|---|
| `PROJECT_STATE.json` | Version 0.3.7 → 0.3.8; test count 280 → 282 with a note on why (T20 added 2 tests); new backendSubsystems entry for the QA review resolution; `lastUpdated` bumped. |
| `docs/ProjectStatus.md` | Version/date bump; new "QA Review Resolution" section (T20/T21 detail, deferred/accepted findings); Technical Debt section extended to list the 5 still-deferred QA findings. |
| `docs/AI_HANDOVER.md` | Test count 280 → 282; new "pattern worth knowing" #9 (catch `BaseException` for cancellation-safe cleanup); ADR-0010–0016 added to the "Important Decisions" list (previously only referenced inline, not itemized there). |
| `CHANGELOG.md` (root) | New `[0.3.8]` entry for the QA review resolution. |
| `docs/CHANGELOG.md` | New detailed "Post-Stage-2 — QA Review Resolution" section (T20/T21 full detail, matching the file's existing per-addition format). |
| `docs/SessionReport.md` | New session entry documenting this QA-fix-verification + documentation-sync session. |
| `docs/API.md` | Fixed stale example response: `/api/v1/version` showed `"version": "0.1.0"`, actual `settings.app_version` is `"0.2.0"`. |
| `docs/FolderStructure.md` | Root file list was missing `AI_BOOTSTRAP.md`, `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `docs/reviews/`; `infrastructure/` subtree was missing all 5 post-Stage-2 directories (`commands/`, `queries/`, `transactions/`, `cache/`, `metrics/`) and the `di/health_check.py` / `modules/manifest.py` additions. |
| `README.md` (root) | Status banner still said "Stage 1 — Core Architecture & Domain Foundation complete"; actual state is Stage 2 + 7 post-Stage-2 additions + QA resolution. |
| `docs/ProjectOverview.md` | "Non-goals" section still framed the project as Stage 0/"Stage 1+ scope"; updated to reflect Stages 0–2 + post-Stage-2 additions complete. |
| `docs/Roadmap.md` | Had no entry at all for the 7 post-Stage-2 additions or the QA review; added a "Post-Stage-2 — Standalone Framework Additions" section. |
| `docs/README.md` | Reference table was missing `ERD.md` and `docs/reviews/`. |
| `AI_BOOTSTRAP.md` | Read-order list didn't mention `IMPLEMENTATION_QUEUE.md`; added as step 7. |
| `docs/Architecture.md` | Transaction Pipeline description didn't mention the `BaseException`/cancellation fix; added a brief clause + pointer to Q1/T20. |
| `docs/KnownIssues.md` | Added a note that the "can't verify against Postgres without Docker" issue recurred during this session, and what was/wasn't re-verified as a result. |
| `docs/reviews/Documentation_Consistency_Report_2026-08-06.md` | This file (new). |

`docs/DevelopmentGuide.md` and `docs/ModuleRegistry.md` showed as already modified in the working
tree at session start (from the prior session that landed the 7 post-Stage-2 additions) — reviewed
and confirmed accurate; no further change needed from this pass.

---

## Inconsistencies Found

### Fixed in this pass
1. **Backend test count stale everywhere.** 280 was accurate the moment the Performance Metrics
   Service work landed, but T20 added 2 more tests afterward without the headline count being
   updated anywhere. Actual current count: **282** (175 unit, re-run and confirmed passing; 107
   integration, not re-run — no Postgres/Docker in this environment, consistent with the QA review's
   own stated constraint). Was wrong in `PROJECT_STATE.json`, `docs/ProjectStatus.md`,
   `docs/AI_HANDOVER.md`, `docs/CHANGELOG.md`, `docs/SessionReport.md`, and the root `CHANGELOG.md`.
2. **The QA review's resolution (T20/T21) was invisible outside `IMPLEMENTATION_QUEUE.md`.** The
   fixes are real and correctly applied in source (verified directly), and `IMPLEMENTATION_QUEUE.md`
   itself already tracked them correctly — but nothing in `PROJECT_STATE.json`,
   `docs/ProjectStatus.md`, either `CHANGELOG.md`, or `docs/SessionReport.md` mentioned the review
   happened or that anything was fixed. A reader of any of those files alone would have no idea the
   QA pass occurred.
3. **`docs/API.md`'s example response was stale.** Showed `"version": "0.1.0"` for
   `GET /api/v1/version`; the actual `settings.app_version` (and what the endpoint really returns)
   is `"0.2.0"`, matching `backend/pyproject.toml`.
4. **`docs/FolderStructure.md` hadn't been updated for any of the 7 post-Stage-2 additions.** Missing
   5 whole `infrastructure/` subdirectories and 3 root-level files that have existed since before
   this session started.
5. **Root `README.md` and `docs/ProjectOverview.md` were two stages behind.** Both still described
   the project as Stage 0/Stage 1 despite Stage 2 and 7 further additions being complete — the kind
   of stale banner a new reader would hit first and be misled by.
6. **`docs/Roadmap.md` never gained a section for the 7 post-Stage-2 additions**, despite every other
   completed unit of work in the project having a Roadmap row.

### Investigated, no fix needed (false leads or already correct)
- **`ArchitectureScorecard.md`** — does not exist anywhere in the repository (checked by filename
  search and by content grep for "scorecard"/"architecture score", including full git history for a
  deleted file). No prior session ever created it, and nothing else in the doc set references it by
  that name. Not fabricated — task item 9 in the original request was conditional ("if any score
  changed"), and there is no score to change because the artifact was never created. If a scoring
  rubric is wanted going forward, that's a new-feature decision for the project owner, not a
  documentation-sync task.
- **`IMPLEMENTATION_QUEUE.md`** — already fully in sync (T20/T21 correctly marked Done with accurate
  detail, dated 2026-08-06; the QA findings table already correctly classifies all 9 findings). No
  changes made.
- **`docs/Context.md`** — contains stale Stage-0-era claims, but is explicitly self-labeled
  historical in `docs/README.md` ("written at the end of Stage 0; treat as historical background").
  Not a bug.
- **`docs/Database.md`, `docs/ERD.md`, `docs/TechStack.md`, `docs/CodingStandards.md`,
  `docs/FeatureRegistry.md`, `docs/DevelopmentGuide.md`, `docs/ModuleRegistry.md`,
  `docs/FutureIdeas.md`, `AI_BOOTSTRAP.md`** — checked against source (tech versions, ruff/tsconfig
  rules, table/migration counts, module list) and found accurate.

### Noted, not corrected (out of scope for a documentation-only pass)
- **Three different "version" numbers coexist by design, not by accident**, but nothing previously
  explained that: `PROJECT_STATE.json`'s `currentVersion` (0.3.8, tracks project/stage progress),
  `backend/pyproject.toml`'s `version` / `settings.app_version` (0.2.0, the backend package/API
  version, bumped separately), and root `package.json`'s `version` (0.1.0, the Electron shell
  version, never bumped since Stage 0). These are three legitimately independent version schemes,
  not a single inconsistency — but no document says so explicitly. Flagged here as documentation
  debt rather than silently resolved, since picking one canonical scheme is a project-owner decision,
  not a documentation-sync task. `docs/API.md` was still corrected (item 3 above) because that one
  was a genuine factual error (the doc claimed a value the code doesn't produce), not a
  version-scheme ambiguity.

---

## Documentation Quality Score

**9/10.**

The documentation set is unusually disciplined for a project this size: every architectural decision
has an ADR, every session has a report, `IMPLEMENTATION_QUEUE.md` already tracked the QA review
findings correctly before this pass started, and the majority of secondary reference docs (Database,
ERD, TechStack, CodingStandards, ModuleRegistry) were already accurate against source with zero
drift. The one point held back reflects a real, recurring pattern across three separate sessions
(Performance Metrics Service, then T20/T21, and likely earlier additions too, going by the git
history): the *headline* tracking docs (test counts, version numbers, status banners) reliably lag
one addition behind whatever most recently landed, and a couple of "first impression" docs
(root `README.md`, `ProjectOverview.md`) lagged by a full two stages. Nothing found was a
fabrication or a contradiction between two current docs — every issue was staleness (a true-when-
written claim that wasn't revisited), which is the cheaper failure mode to have.

## Remaining Documentation Debt

1. **No single canonical "project version"** — three independently-versioned files (see "Noted, not
   corrected" above). Low urgency; worth a one-time decision and a short explanatory note wherever
   version numbers are first introduced to a new reader (`README.md` or `docs/TechStack.md`), not an
   urgent fix.
2. **`docs/FolderStructure.md` and similar structural docs will keep drifting** unless updating them
   becomes a checklist item at the end of each addition, the same way `docs/CHANGELOG.md` already is
   — it was 5 directories behind by the time this pass caught it, and it's a plain-text tree with no
   mechanism to catch drift automatically.
3. **Five QA findings remain open by design** (Q2, Q3, Q5, Q7, Q9 in `docs/reviews/Stage_2_5_QA_Review.md`),
   correctly gated on dependencies that don't exist yet (a real `UnitOfWork`, the module manifest
   loader being wired in, a real async-requiring implementation being proposed). Now cross-referenced
   from `docs/ProjectStatus.md`'s Technical Debt section and `docs/Roadmap.md` — not a gap, but
   worth re-checking each time one of those gating dependencies actually lands, since that's exactly
   the kind of trigger condition that's easy to miss if nobody's specifically watching for it.
4. **The 107 integration tests have not been run against a live Postgres since before T20/T21
   landed** — this environment has no Docker. Not a documentation gap so much as a verification gap
   that documentation now honestly discloses (see `PROJECT_STATE.json`'s test note and
   `docs/KnownIssues.md`) rather than papering over. Whoever next has Docker available should run the
   full 282-test suite once to close it.
