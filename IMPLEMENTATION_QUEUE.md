# Implementation Queue

Tracks the actionable task backlog for the *current* stage only — granular, estimated,
dependency-ordered work items, distinct from [docs/Roadmap.md](docs/Roadmap.md) (stage-level,
multi-session scope) and [PROJECT_STATE.json](PROJECT_STATE.json) (point-in-time snapshot). This
file is expected to be rewritten at the start of each new stage.

Status values: `Not Started`, `In Progress`, `Done`, `Deferred`, `Blocked`.

**Task IDs are immutable and permanently reserved.** A completed or cancelled task ID (e.g. `T44`)
is never reassigned to different work, even under direct instruction — see `AI_BOOTSTRAP.md`'s
"Non-negotiable rules." If scope changes after a task is done, cancel it in place and open a new
ID for the new scope; don't redefine the old one. (This rule was adopted after the T44/T45 ID-reuse
incident — see
[docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md](docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md)
— which predates the rule and is left as historical record, not renumbered.)

---

## Stage 2.5 — Architecture Hardening

**Status:** Not Started — backlog below is proposed, pending project-owner approval. No code has
been written for this stage yet.

### Scope

Stage 2.5 fixes structural gaps in the Stage 0/1 framework and the Stage 2 schema *before* Stage 3
builds a business feature on top of them. Everything below is a framework/infrastructure/test/doc
change — **no business entities, no new tables, no login mechanism, no UI.** Two items below
(F11/F12) border the "no auth yet" charter boundary and are explicitly flagged as **not scheduled**
pending confirmation, consistent with every prior stage's rule not to start Stage N+1 work by
guessing.

### How this backlog was built

Read, in order: `AI_BOOTSTRAP.md`, `PROJECT_STATE.json`, `docs/Architecture.md`,
`docs/ProjectStatus.md`, `CHANGELOG.md`, `docs/SessionReport.md`, `docs/AI_HANDOVER.md`,
`docs/KnownIssues.md`, `docs/Roadmap.md`, `ADR/0004`. Then went past the docs into the actual code
that Stage 1 built, since this stage's job is to find what the docs *don't* already say: the DI
container, `Settings`, `session.py`, `deps.py`, `main.py`, both auth stub implementations, the
repository port + `SqlAlchemyRepository`, `BaseService`, the query/pagination framework
(`query.py`), the CRUD router factory, `AuditMixin`/`OptimisticLockMixin`, the error handler, the
module registry, the workflow engine, `tests/conftest.py`, and the frontend `httpClient.ts` — plus
grepping the whole backend for `commit()`, `get_db`, `get_engine`, and `dispose` usage. All 216
backend / 9 frontend tests were not re-run as part of this review (no code changed); the review is
static.

### Findings (prioritized)

| # | Finding | Evidence | Risk if left alone | Priority |
|---|---|---|---|---|
| F1 | `get_db()` never commits. Repository `add`/`update`/`delete` only `flush()`; the only `session.commit()` calls in the entire backend are in two integration tests, which then immediately roll back for isolation. | `session.py:36-39`, `sqlalchemy_repository.py`, grep for `commit()` | **Silent data loss.** The first real write route built on this framework will appear to work (flush makes it visible within the same transaction) and then vanish, because the session closes without committing. Not caught by any existing test — they all read back inside the same uncommitted transaction. | **Critical (P0)** |
| F2 | `SearchQuery`/`FilterSpec`/`SortSpec` (`query.py`) are fully defined but nothing implements them: `SqlAlchemyRepository.list()` only takes `limit`/`offset`, `BaseService.list_page()` doesn't forward filters/sort, and `build_crud_router`'s list route doesn't expose them as query params. `Architecture.md` already documents this as a known extension point. | `query.py`, `sqlalchemy_repository.py:32-35`, `base_service.py:36-39`, `crud_router_factory.py:59-70` | The first real "list X" endpoint hits a dead end immediately — filtering/sorting has to be invented ad hoc per feature instead of using the framework built for it. | High (P1) |
| F3 | The cached SQLAlchemy engine (`get_engine()`, `lru_cache`d) is never disposed anywhere in the app lifecycle — no shutdown hook. | `session.py:24-29`, `main.py` | Connection-pool resources aren't released on graceful shutdown; harmless short-term, sloppy long-term. | Medium (P2) |
| F4 | `/docs` and `/redoc` are mounted unconditionally, including when `environment=production`. | `main.py:28-33` | Swagger/ReDoc exposed in production by default unless something downstream (reverse proxy, etc.) blocks it — should be an explicit choice, not the default. | Medium (P2) |
| F5 | CORS is configured with `allow_methods=["*"]`, `allow_headers=["*"]`, and `allow_credentials=True` together. | `main.py:35-41` | Broader than the app currently needs (only `GET` routes exist); worth a deliberate decision now while the surface is small, before it's load-bearing. | Medium (P2) |
| F6 | Nothing verifies the Alembic migration chain has a single head. | `backend/alembic/versions/` (12 files, never checked programmatically) | A future migration authored from a stale branch could silently fork the chain; would only surface as a confusing `alembic upgrade` error, possibly in CI/prod. | Medium (P2) |
| F7 | ~~`configure_container()` registers factories but nothing resolves them at startup — a broken factory (e.g. a typo'd env var) only fails the first time a request happens to need it.~~ **Resolved** — see T15. | `container.py:89-102` | Fails at request time in whatever environment hits it first, instead of failing fast at boot. | Low–Medium (P2) |
| F8 | `SqlAlchemyRepository.update()` is `flush()` only — it silently relies on the caller having mutated an entity that's already attached to *this* session's identity map. A detached/fresh entity passed in does nothing, with no error. | `sqlalchemy_repository.py:47-49` | Works today only because `crud_router_factory.apply_update()` happens to follow the right pattern by convention, not because anything enforces or documents it. A future feature's service can get this wrong with zero signal that anything went wrong. | Low–Medium (P3) |
| F9 | `BaseService.delete()` calls `get_by_id_or_raise()` and then `repository.delete()`, which internally calls `get_by_id()` again — two round-trips where one suffices. | `base_service.py:47-49`, `sqlalchemy_repository.py:51-55` | Minor inefficiency, not correctness. | Low (P3) |
| F10 | `frontend/httpClient.ts` only implements `get()`, and discards the backend's structured `{"error": {"code","message"}}` body in favor of a generic status-code string. | `httpClient.ts` | Fine today (no mutating routes exist to call), but whoever wires the first `POST`/`PUT`/`DELETE` from the frontend will have to extend this anyway — cheap to close now while it's isolated. | Low–Medium (P3) |
| F11 | No reusable "require this permission" FastAPI dependency exists yet — `AuthorizationService.require_permission()` (permissive stub) has zero callers anywhere. | `application/interfaces/auth.py`, grep for `require_permission` | Not a bug (no protected route exists yet), but the *pattern* for wiring it into a route doesn't exist either — Stage 3's first protected route would have to invent it under time pressure. | **Flagged, not scheduled** — borders the "no auth yet" boundary; needs explicit go-ahead. |
| F12 | No connection-pool sizing / statement-timeout tuning beyond `pool_pre_ping=True`. | `session.py:24-29` | No real workload exists yet to size against — tuning now would be guessing. | **Flagged, deferred** — revisit once a feature with real query patterns exists. |

---

### Task backlog

Complexity: **XS** (single small edit, <15 lines, one file) · **S** (one focused change, 1–2
files, straightforward) · **M** (touches 2–4 files and/or needs care, e.g. new translation logic).
No task here is larger than M — anything that looked bigger was split further.

#### P0 — Transaction correctness (do first, before anything else touches persistence)

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T1 | `get_db()`: commit on clean exit, rollback on exception, before the session closes. | XS | — |
| T2 | Add a regression test proving a write made in one `get_db()`-scoped session is durably visible from a **second, independent** session/connection — not just readable inside the same uncommitted transaction (the existing `conftest.py` `db_session` fixture deliberately rolls back, so it can't prove this; needs its own non-rolling-back fixture). | S | T1 |
| T3 | Document the commit/rollback contract in `docs/Architecture.md`'s session-plumbing note and add it to `docs/AI_HANDOVER.md`'s "patterns worth knowing" list, so it can't silently regress unnoticed again. | XS | T1 |

#### P1 — Query framework completion (do second; largest single body of work this stage)

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T4 | Extend `AbstractRepository[T].list()`'s port signature to accept an optional `SearchQuery` (or `filters`/`sort`) alongside `limit`/`offset`, defaulting to today's behavior. | S | — |
| T5 | Implement `FilterSpec` → SQLAlchemy `WHERE` translation in `SqlAlchemyRepository.list()` for the operators `query.py` already defines (`EQ`/`NEQ`/`GT`/`GTE`/`LT`/`LTE`/`CONTAINS`/`IN`). | M | T4 |
| T6 | Implement `SortSpec` → SQLAlchemy `ORDER BY` translation in the same method. | S | T4 |
| T7 | Wire `BaseService.list_page()` to accept an optional `SearchQuery` and forward it to the repository; keep the existing no-arg call path working via a default. | S | T5, T6 |
| T8 | Wire `build_crud_router`'s `list_items` route to accept `sort`/`filter` query parameters and assemble a `SearchQuery` — stays test-only per Stage 1's existing scope (still not mounted into the real app). Note: this file already carries a documented PEP-695/runtime-annotation caveat; read its docstring before touching it. | M | T7 |
| T9 | Tests: repository-level filter/sort tests against real Postgres, `BaseService.list_page()` unit tests with a fake repository, and a `test_crud_router_factory.py` extension covering the new query params. | M | T5, T6, T7, T8 |
| T10 | Update `docs/Architecture.md`'s query-framework note — it currently says `SqlAlchemyRepository`'s `list()`/`count()` "don't yet [interpret `SearchQuery`] — that's an extension point"; make it reflect that it now does. | XS | T9 |

#### P2 — Lifecycle & exposure hardening (independent of P0/P1 — safe to interleave)

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T11 | Add a FastAPI lifespan handler in `main.py` that disposes the cached SQLAlchemy engine on shutdown. | XS | — |
| T12 | Gate `docs_url`/`redoc_url` behind `settings.is_development` (`None` otherwise) in `create_app()`. | XS | — |
| T13 | Decide and act on CORS `allow_methods`/`allow_headers`: either replace the wildcards with an explicit list, or record a short justification (ADR note or code comment) for keeping them broad. Judgment call — see notes below. | XS–S | — |
| T14 | Add a test asserting `alembic`'s `ScriptDirectory` reports exactly one head, to catch a forked migration chain immediately instead of at some future `upgrade` failure. | S | — |
| T15 | ~~Add a startup self-check that resolves every interface registered in `configure_container()` once at boot, failing fast on a broken factory instead of at first request-time use.~~ **Done** (post-Stage-2, requested directly by the project owner ahead of the rest of this backlog — see [ADR/0015](ADR/0015-architecture-health-check.md)). | S | — |

#### P3 — Footguns & consistency (do last — smallest, safest, no dependents)

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T16 | Document `SqlAlchemyRepository.update()`'s "entity must already be attached to this session" contract in its docstring, and add a test that exercises both the correct pattern and the (asserted) no-op failure mode for a detached entity. | S | — |
| T17 | Remove `BaseService.delete()`'s redundant double-fetch (have the repository's delete report whether a row existed, or pass the already-fetched entity through). | S | — |
| T18 | Extend `frontend/httpClient.ts` with `post`/`put`/`delete`, and parse the backend's `{"error": {"code","message"}}` body into `HttpError` (carry the server's `code`/`message` instead of a generic status string). | S | — |

#### Flagged, not scheduled (needs explicit project-owner confirmation first)

| ID | Task | Why it's held back |
|---|---|---|
| T19 (tentative) | Add a reusable `RequirePermission("...")` FastAPI dependency wrapping `AuthorizationService.require_permission()`, still backed by today's permissive stub — establishes the enforcement seam without implementing real auth, analogous to what ADR-0004 already did for error types. | Touches the auth boundary that every prior stage's charter has said not to cross without asking, even though no real auth logic would be added. |
| — | Connection-pool sizing / statement-timeout tuning (F12). | No real workload exists yet to size against; tuning now is guessing. Revisit once a feature with real query patterns exists. |

---

### Safest implementation order

1. **T1 → T2 → T3.** Fix the one true correctness bug first. Every later task in this stage (and every future feature) sits on top of `get_db()` — it should sit on a session that actually persists, not one that happens to look like it does.
2. **T11, T12, T13, T14, T15** (any order among themselves). Small, isolated hygiene items, independent of P0 and P1 — good to interleave between the bigger pushes rather than saved entirely for the end.
3. **T4 → (T5, T6 in either order) → T7 → T8 → T9 → T10.** The query-framework work, done after T1 so its new persistence-backed tests (T9) are exercising a repository that durably commits, not one riding on the pre-fix accidental-visibility behavior.
4. **T16, T17.** Backend footguns — smallest, safest, nothing depends on them.
5. **T18.** Frontend-only, fully independent of the entire backend track; sequenced last purely because it's the lowest priority, not because anything blocks it.

### Definition of done for Stage 2.5

- All P0–P2 tasks landed (P3 optional but recommended — low cost, closes real footguns).
- Each task committed separately after its own verification (tests + a live smoke check where
  relevant), per this project's existing "small, reviewed sections" discipline.
- Backend test count grows from 216 (new tests for T2, T9, T14, T16 at minimum); frontend grows
  from 9 (T18). Both suites still green; both linters still clean.
- Real app route surface still unchanged (`/api/v1/health`, `/api/v1/version` only) — this stage
  adds no routes to the shipped app, only capability to the (still-unmounted) CRUD router factory.
- `docs/Architecture.md`, `docs/AI_HANDOVER.md`, `docs/ProjectStatus.md`, `PROJECT_STATE.json`,
  `CHANGELOG.md`, `docs/CHANGELOG.md`, `docs/SessionReport.md` updated to match.
- Consider a new ADR for **T1** specifically (next available number — `0010`–`0016` are now taken
  by the post-Stage-2 framework additions below, so this would be `0017-session-commit-rollback-
  policy.md` or similar) — "every session commits on success / rolls back on exception" is exactly
  the kind of decision a future session needs to know was deliberate, not incidental, per this
  project's "every significant architectural decision gets an ADR" rule. T4–T10 (query framework)
  is arguably completing an already-documented extension point rather than a new decision — an ADR
  there is optional, not required.
- No business entities, tables, routes, or auth logic added — if implementation surfaces a genuine
  need for one of those, stop and ask before proceeding, per this project's standing rule.

---

## QA Review Findings — Post-Stage-2 Framework Additions

**Source:** [docs/reviews/Stage_2_5_QA_Review.md](docs/reviews/Stage_2_5_QA_Review.md), dated
2026-08-06. Covers the seven post-Stage-2 framework additions requested directly by the project
owner outside the numbered-stage process — Command Bus, Query Bus, Transaction Pipeline, Caching
Abstraction, Module Manifest Loader, Architecture Health Check, and Performance Metrics Service
(ADR-0010–0016). The QA review itself states this scope is **distinct** from the "Stage 2.5 —
Architecture Hardening" backlog above (T1–T18); nothing here has been folded into that backlog's
numbering except by explicit cross-reference.

**Status:** Findings reviewed and classified below. **T20 and T21 are done** — see
[docs/ProjectStatus.md](docs/ProjectStatus.md)'s "QA Review Resolution" section for the verified
fix detail (backend test count 280 → 282, full unit suite re-run green). Everything else in this
section (Future Stage / Accepted Trade-off items) is unchanged and not scheduled.

### Classification legend

1. **Fix Immediately** — cheap, safe, no blocking dependency; nothing about it needs a design
   decision or a prerequisite that doesn't exist yet.
2. **Future Stage** — a real, valid gap, but the fix is gated on something that doesn't exist yet
   (a real, non-in-memory `UnitOfWork`; the manifest loader actually being wired into `main.py`; an
   async-requiring implementation actually being proposed). Not scheduled now; revisit when the
   gating dependency lands.
3. **Accepted Trade-off** — already a deliberate, ADR-documented decision, not an open gap. Only
   revisit if the finding's own stated trigger condition occurs (e.g. "a third single-handler bus
   is requested," "the cache gets a real caller").
4. **Won't Fix** — the finding is invalid, out of scope, or not worth addressing even in principle.
   *(No finding below qualified — see the note after the table.)*

### Findings and classification

| # | Finding | Classification | Why |
|---|---|---|---|
| Q1 | `TransactionPipelineBehavior.dispatch()` catches `Exception`, not `BaseException` — `asyncio.CancelledError` (a `BaseException` since Python 3.8) bypasses `rollback()` on cancellation. `transaction_pipeline_behavior.py:43-47`. | **Fix Immediately** | The QA review's own priority ranking calls this "do soon, cheap... zero risk, closes a real gap." The fix (widen the `except` clause, still re-raise) needs no real backing resource to *implement* — only a real resource to *observe the consequence of skipping it* — so there's no reason to wait on one. |
| Q2 | The transaction pipeline's begin→dispatch→commit/rollback sequencing has never been exercised against anything that can fail in interesting ways — `InMemoryUnitOfWork` has no I/O, no partial commits, no connection contention; real transactional correctness is unproven. | **Future Stage** | ADR-0012 already names this trade-off ("proves orchestration, not persistence") and the QA review confirms it is "not a defect... not something to fix now." Its own suggested-improvements list explicitly times the real fix — "add tests against that real implementation" — to when the first real `UnitOfWork` lands, which doesn't exist yet. |
| Q3 | `Container.resolve()`'s singleton check-then-act isn't safe if ever called from a real OS thread (e.g. via `run_in_threadpool`) instead of the assumed single event-loop thread. No current registration triggers it — every factory in `configure_container()` today is cheap/idempotent even if duplicated. `container.py:69-78`. | **Future Stage** | Real but currently untriggered. The QA review's own suggested-improvements list explicitly bundles the fix (a docstring note) with "do when the first `UnitOfWork` implementation lands," rather than treating it as an isolated now-fix — followed here rather than overridden by a cheaper-looking read of the same finding. |
| Q4 | `InMemoryCommandBus`/`InMemoryQueryBus`/`InMemoryEventBus` are structurally near-identical (dict-backed registry, register-raises-on-duplicate, dispatch-raises-on-missing), no shared base class. | **Accepted Trade-off** | QA: "a deliberate, ADR-documented choice, not an oversight" — ADR-0011 explicitly weighed and rejected a shared base class. "Defensible at N=2, still defensible at N=3... not an action item now." |
| Q5 | `ModuleManifestLoader.import_enabled()` performs unrestricted dynamic import (`importlib.import_module`) with no allowlist on `import_path`. `manifest.py:88-104`. | **Future Stage** | No live attack surface today — the loader isn't wired into `main.py` (per ADR-0014, deliberately). QA's recommended mitigation (an allowlist prefix check) is explicitly scoped to "when this gets wired in," i.e. whenever a real module-loading feature is built — not before. |
| Q6 | `InMemoryCache` only expires lazily on read; a key set with a TTL and never re-read stays in the dict forever, and a key set with no TTL never expires at all. `in_memory_cache.py:30-37`. | **Accepted Trade-off** | QA: "Already flagged as an accepted trade-off in ADR-0013." The follow-up ("size-bound this implementation or move to the Redis-backed one") is explicitly conditional on "the first real caller" appearing — not scheduled work. |
| Q7 | If `unit_of_work.rollback()` itself raises inside `TransactionPipelineBehavior`'s exception handling, the original exception loses primacy (still chained via `__context__`, not lost), and the failure-`Result` path skips its trailing log line. | **Future Stage** | QA: "Cosmetic today (`InMemoryUnitOfWork.rollback()` can't fail)... worth keeping in mind once a real implementation's `rollback()` can genuinely throw." Nothing exists yet to verify a fix against. |
| Q8 | `MetricsService`/`LoggingMetricsService`'s `tags: dict[str, str]` is logged verbatim with no redaction — a future caller tagging a metric with something like a raw email or document ID would land in plaintext structured logs. | **Fix Immediately** | A one-line docstring/comment addition, no blocking dependency, no design decision required. QA lists it as its own standalone suggested improvement ("worth a one-line comment, not urgent") rather than tying it to any future milestone — cheap enough to just do. |
| Q9 | `Container.resolve()` is fully synchronous — no support for an async factory; a future Redis-backed `Cache` or broker-backed `CommandBus` needing awaited connection setup won't fit the current `Callable[[], T]` factory shape. | **Future Stage** | Purely forward-looking — no port registered today needs an async factory. Building support for it now would mean designing against a hypothetical requirement, which runs against this project's own stated discipline against speculative work. Revisit if and when a real implementation actually needs it. |

**On "Won't Fix":** no finding in this review was classified this way. Every item was assessed by
the QA reviewer as either a genuine, cheap, currently-actionable fix; a real gap correctly gated on
a future dependency that doesn't exist yet; or a decision already made deliberately and recorded in
an ADR. None were found invalid, out of scope, or not worth ever addressing.

### Resulting tasks

Only Q1 and Q8 are cheap, safe, and unblocked — queued below as very small tasks, same conventions
as the rest of this file. Everything else stays a **findings entry only** (no task ID): Q2/Q3/Q7's
fixes don't exist until a real `UnitOfWork` is built, Q5's until the manifest loader is wired in,
Q9's until an async-requiring implementation is proposed, and Q4/Q6 are accepted as-is per their
ADRs, revisited only if their stated trigger condition occurs.

| ID | Task | Complexity | Depends on | Finding |
|---|---|---|---|---|
| T20 | ~~Widen `TransactionPipelineBehavior.dispatch()`'s `except Exception` to also catch `BaseException`/`asyncio.CancelledError`, still roll back and re-raise so cancellation propagates correctly.~~ **Done** (2026-08-06 — `except BaseException`, with a WHY comment and two regression tests: `asyncio.CancelledError` and a generic `BaseException` subclass, both proving rollback + re-raise). | XS | — | Q1 |
| T21 | ~~Add a one-line docstring/comment on `MetricsService`/`LoggingMetricsService` stating that `tags` values are logged verbatim — no redaction — so the first real caller knows not to put sensitive data in a tag.~~ **Done** (2026-08-06 — docstring notes added to both; no test changes needed, existing `test_increment_accepts_an_explicit_value_and_tags` already asserts tags are logged verbatim). | XS | — | Q8 |

**Deferred, revisit when their gating dependency lands** (no task ID yet — nothing to schedule
until then): Q2, Q3, Q7 → when a real (non-in-memory) `UnitOfWork` implementation is built. Q5 →
when `ModuleManifestLoader` is actually wired into `main.py`'s startup. Q9 → if/when a real
async-requiring `Cache`/`CommandBus`/etc. implementation is proposed.

**Accepted, no action planned** (already-made ADR decisions, revisit only if their stated trigger
occurs): Q4 → [ADR/0011](ADR/0011-query-bus.md), revisit only if a third single-handler bus is ever
requested. Q6 → [ADR/0013](ADR/0013-caching-abstraction.md), revisit only once `InMemoryCache` gets
a real caller.

T20 and T21 are independent of the P0–P3 order already established for T1–T18 (no shared files, no
dependency either direction) — safe to do anytime, including before, interleaved with, or after
that backlog, since both are single-file, zero-risk changes with no open design decision.

---

## Stage 2.7 — GitHub Actions CI

**Status:** Implemented (T22–T34, T36–T37 done). **T35 (live verification) is the one remaining
step** — it requires an actual `git commit` + `git push` to a real branch/PR to observe GitHub
Actions run for real, which was deliberately not done automatically (commits/pushes are
confirm-first actions, not implied by "proceed with implementation"). See "Definition of done"
below for exactly what's left.

### Decisions finalized by the project owner (superseding this plan's original open questions)

1. **Trigger scope:** `push` on `main`, `feature/**`, `hotfix/**`, `release/**`; `pull_request`
   targeting `main` only. (Not literally every branch — scoped to this repo's branch-naming
   convention.)
2. **`engines` added** to both `package.json` files using the project's actual current versions:
   Node `>=24.13.1`, npm `>=11.11.1` (confirmed via `node --version` / `npm --version`).
3. **Python pinned to the project's current development version**, `3.14` (confirmed via `uv run
   python --version` inside `backend/`), not the `pyproject.toml` floor of `>=3.12` this plan had
   originally proposed.
4. **Three separate workflow files**, not one `ci.yml` with three jobs: `backend.yml`,
   `frontend.yml`, `release.yml`. `release.yml` covers what this plan called the "`build`" job —
   build verification only.
5. **No deployment** — confirmed out of scope, not just deferred-pending-a-question.
6. **No integration tests** — confirmed out of scope, matching this plan's own recommendation.
7. **Three items added to the backlog, explicitly not implemented this stage**: Dependabot, a pull
   request template, issue templates. See "Additional backlog items" below.

Full rationale for all of the above lives in
[ADR/0017-github-actions-ci.md](ADR/0017-github-actions-ci.md), written as part of implementing
this stage.

### Scope

A CI pipeline that validates every push and pull request: backend formatting/linting/unit tests,
frontend formatting/linting/unit tests, and build verification (backend boots, frontend/Electron
compile and bundle). Per the mini-stage charter, **integration tests, Docker, and deployment are
explicitly future expansion, not built now** — see that section below. This is tooling/process work,
not a business feature; it touches no application code.

### How this plan was built

Read, in order: `AI_BOOTSTRAP.md`, `PROJECT_STATE.json`, `docs/Architecture.md`,
`docs/ProjectStatus.md`, `CHANGELOG.md`, `docs/SessionReport.md`, `docs/DevelopmentGuide.md`,
`docs/TechStack.md`, `docs/CodingStandards.md`, `docs/FolderStructure.md`, `docs/KnownIssues.md`,
`docs/Roadmap.md`, this file (`IMPLEMENTATION_QUEUE.md`). Then reviewed the actual repository
structure directly rather than trusting docs alone: confirmed no `.github/` directory exists yet
(clean slate); read `package.json` (root), `frontend/package.json`, `backend/pyproject.toml`,
`backend/ruff.toml`, `backend/pytest.ini`, `.gitignore`, `docker-compose.yml`,
`frontend/src/shared/config/env.ts`, and two representative test files
(`tests/integration/test_health_endpoint.py`, `tests/integration/test_module_registry.py`) to
confirm which parts of the suite do and don't need a live Postgres connection.

### Repository facts this plan is built on

- **No existing CI** — `.github/` doesn't exist. Nothing to migrate or avoid breaking.
- **Backend:** Python `>=3.12` (pyproject; developed locally against newer point releases per
  `TechStack.md`), managed by `uv` with a committed `backend/uv.lock`. Lint/format: `ruff.toml`
  (line length 100, `E/W/F/I/UP/B/C4/SIM/RUF`) + `black` (line length 100). Tests: `pytest` +
  `pytest-asyncio` (`asyncio_mode = auto` in `pytest.ini`), split by directory —
  `tests/unit/` (~175 tests, no I/O) and `tests/integration/` (~107 tests). Backend total is 282
  passing as of the last recorded run.
- **Not every "integration" test needs Postgres.** `tests/integration/test_health_endpoint.py` and
  `test_module_registry.py` use `TestClient(app)` but touch no database — only the tests that pull
  in `conftest.py`'s `db_session` fixture (the schema/repository tests) need a live connection, and
  that fixture already skips gracefully (`pytest.skip(...)`) if Postgres is unreachable rather than
  failing. That means `tests/integration/` *could* technically run today with zero Postgres setup
  and mostly skip rather than fail — but a pipeline where most of a directory silently skips every
  single run is a worse signal than not running it at all (a broken service container would look
  identical to "everything passed"). This plan keeps the split clean: **`tests/unit/` only for
  now**, `tests/integration/` deferred to Future Expansion with a real Postgres service and an
  explicit check that nothing silently skipped.
- **`Settings` needs no environment setup for unit tests.** Every field in
  `infrastructure/config/settings.py` has a working default (including `database_url`), so
  constructing `Settings()` — and therefore importing `app.main` — succeeds with zero env vars set.
  No `.env` file or secrets are needed in CI for backend lint/test/import-smoke steps.
- **Frontend:** Node (now pinned via `engines: {"node": ">=24.13.1", "npm": ">=11.11.1"}` in both
  `package.json` files, added in this stage — see decision 2 above), npm (not pnpm/yarn), committed
  `frontend/package-lock.json`. Lint/format: `eslint` (flat config) + `prettier`
  (`format`/`format:check` scripts already exist). Tests: `vitest run` (`npm run test`), 9 tests,
  no I/O (RTL + jsdom, module-boundary mocks per `CodingStandards.md`). Build: `tsc -b && vite
  build` (`npm run build` inside `frontend/`).
- **`VITE_API_BASE_URL` has a safe fallback** (`frontend/src/shared/config/env.ts`:
  `import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"`) — the frontend build needs no
  `.env` file or injected secret in CI either.
- **Root (`package.json`) orchestrates Electron, not an npm workspace.** `npm run build` = `tsc -p
  electron/tsconfig.json` (compiles `electron/main.ts`/`preload.ts`) **then**
  `npm --prefix frontend run build`. Root and `frontend/` are independent installs (two separate
  `package-lock.json` files) — a job that runs the root `build` script needs `npm ci` in *both*
  places. `npm run dist` (full `electron-builder` packaging into installers) is a heavier,
  OS-matrix concern, out of scope here — Future Expansion.
- **Two known, already-accepted issues** (`docs/KnownIssues.md`) are irrelevant to CI as scoped:
  the shadcn CLI bug is Windows-specific and CI runs on Linux; the `react-router-dom` advisory is
  already accepted and documented — a future dependency-audit gate (Future Expansion) needs to
  carve this out explicitly so it doesn't immediately red the pipeline over an already-accepted
  risk.

### Design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Runner OS | `ubuntu-latest` for all three validation jobs | Fastest/cheapest standard GitHub-hosted runner; nothing being validated (lint, unit tests, TS compile, Vite bundle) is platform-specific. Local dev is Windows, but that's a dev-environment fact, not a CI requirement — the one Windows-specific issue in this repo (shadcn CLI) is an accepted, documented workaround, not something CI needs to reproduce. |
| Python version | Pin to `3.14` — the project's actual current development version (`uv run python --version`), per explicit project-owner direction, superseding this plan's original proposal to pin to the `3.12` floor | The floor-pinning rationale (catch 3.13+-only syntax early) was a reasonable default, but the project owner chose to match current development reality instead — see ADR/0017's Trade-offs for what's given up. |
| Node version | Pin to `24.13.1` / npm `11.11.1` — the project's actual current versions (`node --version`/`npm --version`), matching the new `engines` field | Both must agree — running CI on an older Node than `engines` declares as the floor would be internally inconsistent. |
| Job split | Three separate **workflow files** (not three jobs in one file), per explicit naming direction: `backend.yml`, `frontend.yml`, `release.yml` | Matches the bullet structure you gave (backend validation, frontend validation, build verification as distinct concerns) and gives three independently-failing GitHub status checks. `release.yml` is named ahead of its current scope (build verification only today) — see its own header comment and ADR/0017. |
| Formatting/linting placement | Sub-steps inside `backend.yml`/`frontend.yml`, not their own workflows | They're fast, share the same install/cache as that ecosystem's tests, and splitting them further would only add job-startup overhead without a clearer signal — a failed format-check step still fails the job distinctly in the GitHub UI. |
| Backend "build verification" | An import/boot smoke step (`uv run python -c "from app.main import app"`) inside `backend.yml`, not a separate workflow | Python has no compiled artifact, so "build" for the backend means "does the app construct cleanly" — which exercises `create_app()`, `configure_container()`, and `assert_container_healthy()` (the Architecture Health Check from the post-Stage-2 work) without needing Postgres, since every registered default implementation is in-memory/logging-only. Cheap, fast, and it's the single most valuable one-line check available for zero cost. |
| Integration tests | **Not included**, confirmed | Explicit per project-owner decision 6. See the repository-facts note above for why this is a clean line to draw, not an oversight. |
| Trigger | `push` to `main`/`feature/**`/`hotfix/**`/`release/**` + `pull_request` targeting `main` | Per project-owner decision 1. **Known, accepted trade-off:** a push to a branch with an open PR against `main` still fires both events for the same commit — mitigated, not eliminated, by the `concurrency` cancellation below. |
| Concurrency | Cancel superseded runs on the same ref (`concurrency: group / cancel-in-progress: true`) | Free to add, meaningfully cuts wasted CI minutes on rapid successive pushes (e.g. fixup commits during review) — standard practice, no downside. |
| Permissions | Least-privilege `permissions: contents: read` at the workflow level | The pipeline only reads code and runs checks — it doesn't need to write to the repo, comment on PRs, or touch packages. Costs nothing to set explicitly rather than inherit the (broader) repository default. |
| Artifact retention | Short (e.g. 7 days) for build outputs; test/lint output uploaded only `if: failure()` | Nothing produced here is a release artifact yet (no version is being published) — these exist purely to let a human inspect a CI run without reproducing it locally. Full detail in "Artifact strategy" below. |

### Artifact strategy

Nothing in this stage is a release artifact — no version is tagged or published, so retention stays
short and the goal is purely "let a human inspect *this* run without re-running it locally":

- **`build` job:** upload `frontend/dist/` (the built SPA) and `dist-electron/` (compiled Electron
  main/preload JS) on every run, 7-day retention. Small, useful for spot-checking a build without
  pulling the branch.
- **`backend`/`frontend` jobs:** no artifact on success. On failure (`if: failure()`), upload
  whatever test-runner output exists (pytest's own console output is already in the job log; a
  JUnit XML report via `pytest --junitxml=` / vitest's built-in reporter output is a cheap addition
  if machine-readable results are ever wanted for a future test-reporting integration, but isn't
  required just to see red/green).
- **Nothing is published anywhere** (no GitHub Release, no package registry, no deployment target)
  — that's explicitly Future Expansion, gated on a deployment decision that doesn't exist yet.

### Task backlog

Complexity: **XS** (a handful of YAML lines, one file) · **S** (one focused job/step group,
straightforward) · **M** (touches multiple files or needs care). Every task here is XS or S — this
is inherently small, incremental work.

| ID | Task | Complexity | Depends on | Status |
|---|---|---|---|---|
| T22 | Write `ADR/0017-github-actions-ci.md` recording this stage's design decisions. | S | — | **Done** |
| T23 | Create the three workflow skeletons — `backend.yml`, `frontend.yml`, `release.yml` (per decision 4, superseding the original single-`ci.yml` proposal) — each with name, `on: push`/`pull_request` triggers (per decision 1), `concurrency` group, least-privilege `permissions`. | XS | T22 | **Done** |
| T24 | `backend.yml`, part 1: checkout (`actions/checkout@v7`), `actions/setup-python@v7` pinned to `3.14` (per decision 3), `astral-sh/setup-uv` (pinned by commit hash, `v9.0.0` — this action no longer publishes moving tags) with caching enabled, `uv sync --locked` (working directory `backend/`). | S | T23 | **Done** |
| T25 | `backend.yml`, part 2: `ruff check src tests alembic` and `black --check src tests alembic` steps. | XS | T24 | **Done** |
| T26 | `backend.yml`, part 3: the `tests/unit`-only `pytest` step (`--junitxml` output for the failure-artifact upload). | XS | T24 | **Done** |
| T27 | `backend.yml`, part 4: the import/boot smoke step (`uv run python -c "from app.main import app"`). | XS | T24 | **Done** |
| T28 | `frontend.yml`, part 1: checkout, `actions/setup-node@v7` pinned to `24.13.1` (per decisions 2/3) with npm caching (`cache-dependency-path: frontend/package-lock.json`), `npm ci` (working directory `frontend/`). | S | T23 | **Done** |
| T29 | `frontend.yml`, part 2: `npm run lint` and `npm run format:check` steps. | XS | T28 | **Done** |
| T30 | `frontend.yml`, part 3: the vitest step (dual `default`+`junit` reporters for the failure-artifact upload). | XS | T28 | **Done** |
| T31 | `release.yml`, part 1: checkout, `actions/setup-node@v7`, `npm ci` at repo root **and** `npm ci` in `frontend/` (both needed — see repository-facts note above). | S | T23 | **Done** |
| T32 | `release.yml`, part 2: run `npm run build` (root script — compiles Electron TS, builds the frontend). | XS | T31 | **Done** |
| T33 | `release.yml`, part 3: `actions/upload-artifact@v7` for `frontend/dist/` and `dist-electron/`, 7-day retention. | XS | T32 | **Done** |
| T34 | `if: failure()` log/report upload added to `backend.yml` and `frontend.yml` (see Artifact strategy). | XS | T25–T27, T29–T30 | **Done** |
| T35 | Push a real commit and observe a live run of all three workflows — first actual verification, not just YAML review. Fix anything that only surfaces once it's really running. | S | T24–T34 | **Not done — needs a `git commit` + `git push`, a confirm-first action not taken automatically. All three workflow commands were verified to succeed locally first** (backend: ruff/black/pytest unit/import-smoke all pass; frontend: vitest with dual reporters confirmed working; root: `npm run build` confirmed producing `frontend/dist/` and `dist-electron/`) — but a local dry run is not the same claim as "the workflow YAML runs green on GitHub's runners." |
| T36 | Add CI status badges to `README.md` (one per workflow). | XS | T35 | **Done** (added ahead of T35 — cosmetic, no risk in doing it before the first live run) |
| T37 | Documentation pass: `docs/DevelopmentGuide.md`, `docs/ProjectStatus.md`, `PROJECT_STATE.json`, `CHANGELOG.md`, `docs/CHANGELOG.md`, `docs/SessionReport.md`, this file. | S | T35 | **Done** (also ahead of T35, for the same reason) |

### Additional backlog items (recorded per decision 7 — explicitly **not implemented** this stage)

| ID | Item | Notes |
|---|---|---|
| T38 | **Dependabot** — `.github/dependabot.yml` for `npm` (root + `frontend/`) and a Python ecosystem equivalent for `backend/uv.lock`/`pyproject.toml`. | Needs its own small design pass (update schedule, grouping, which ecosystems) before implementation — not just a copy-paste config. |
| T39 | **Pull request template** — `.github/pull_request_template.md`. | Should reflect this project's actual review discipline (small reviewed sections, tests + docs updated, ADR if architectural) rather than a generic template. |
| T40 | **Issue templates** — `.github/ISSUE_TEMPLATE/` (bug report, feature request at minimum, as YAML forms). | No issue-tracking convention exists yet in this project's docs to model these on — worth a short design pass, not just defaults. |

These three are tracked here so they aren't forgotten, per explicit project-owner instruction to add
them to the backlog without building them now.

### Safest implementation order

1. **T22 → T23.** Record the design decision, then lay the three empty workflow skeletons
   (triggers/concurrency/permissions only) — nothing that can fail yet, so there's a stable base
   before any job logic lands.
2. **T24–T27, T28–T30, T31–T33** (each group sequential within itself; the three groups are
   independent of each other and safe to build/commit in any order or interleaved). These are the
   three parallel jobs — none shares a file with another.
3. **T34.** Small addition to jobs that already exist from step 2.
4. **T35.** The one step that actually matters most: a real push/PR is the only way to know the
   workflow works — GitHub Actions YAML has enough runner-specific behavior (cache key resolution,
   working-directory scoping, action version pinning) that "looks right" and "runs green" are
   different claims until observed.
5. **T36 → T37.** Cosmetic/documentation, last, lowest risk, nothing depends on them.

### Future expansion (not scheduled — explicitly out of scope for this stage)

- **Integration tests.** A fourth job (or a step group added to `backend`): a Postgres 16
  (`postgres:16-alpine`, matching `docker-compose.yml`) GitHub Actions **service container**, an
  `alembic upgrade head` step against it, then `pytest tests/integration`. Should explicitly assert
  zero tests were skipped (rather than trusting a green run), since `conftest.py`'s `db_session`
  fixture silently skips on an unreachable database — a misconfigured service container would
  otherwise look identical to "everything passed."
- **Docker.** No Dockerfile exists yet for the backend itself (`docker-compose.yml` only provisions
  Postgres for local dev). Building one (multi-stage: `uv`/hatchling wheel build, slim runtime
  image) and a CI job to build — and, later, push — it is future work, gated on that Dockerfile
  being designed and approved first, not something this stage invents implicitly.
- **Full Electron packaging.** `npm run dist` (`electron-builder`) across a `windows-latest` /
  `macos-latest` / `ubuntu-latest` matrix, producing real installers. Heavier and slower than
  everything above — a release-triggered workflow (e.g. on a version tag), not an every-push job.
- **Deployment.** No target, environment, or mechanism has been decided for this project at all —
  it's a desktop app; "deployment" might mean auto-publishing installers to GitHub Releases, or
  something else entirely. Per this project's standing rule not to guess at unscoped work, this
  needs an explicit decision from you before any automation is built around it — flagged, not
  planned.
- **Test coverage reporting.** Neither `pytest-cov` nor a Vitest coverage provider is currently a
  dependency on either side. Adding one is a small tooling decision beyond pure CI plumbing — noted
  as a nice-to-have, not bundled into this stage's scope.
- **Dependency audit gate** (`npm audit`, a Python equivalent like `pip-audit`). Useful eventually,
  but the already-accepted `react-router-dom` advisory (`docs/KnownIssues.md`) means a naive
  `--audit-level=high` gate would fail on day one over a risk this project has already evaluated and
  accepted — needs an explicit allowlist/ignore decision before it's added, not a default-on gate.
- **Branch protection requiring these checks.** This is a GitHub *repository setting*
  (Settings → Branches → protection rules), not a file this plan can produce — whoever has admin
  access to the GitHub repo needs to enable "require status checks to pass" manually once the
  workflow exists and has run at least once (checks can't be required before GitHub has seen them
  report at least once).

### Definition of done for Stage 2.7

- [x] T22–T34, T36–T37 landed.
- [ ] **T35 — a real push and a real pull request have both been observed triggering all three
  workflows (`backend.yml`, `frontend.yml`, `release.yml`), all green, in the GitHub Actions UI** —
  not just YAML that looks correct and commands that succeed locally. **This is the one open item.**
  Needs an explicit go-ahead to `git commit` + `git push` (and, to exercise the `pull_request`
  trigger specifically, open a PR) — per this project's standing rule that commits/pushes are
  confirm-first actions, not assumed by "proceed with implementation."
- [x] `docs/DevelopmentGuide.md`, `docs/ProjectStatus.md`, `PROJECT_STATE.json`, `CHANGELOG.md`,
  `docs/CHANGELOG.md`, `docs/SessionReport.md`, `README.md` (badges + prerequisites), and this file
  all reflect reality.
- [x] `ADR/0017-github-actions-ci.md` exists, recording the decisions.
- [x] No application code changed — this stage touched only `.github/`, `ADR/`, `README.md`,
  `package.json` (root + `frontend/`, `engines` field only), and the documentation set.

---

*T1–T18 (Stage 2.5 hardening) remain not started, awaiting approval — except T1–T3, pulled forward
into Stage 3 below as a hard prerequisite (see T41–T43). T20–T21 (QA-review fixes) and T22–T37
(Stage 2.7 CI) are all done — **`git log`/`git tag` confirm a merged PR (`2db48d4`) and two tags
(`v0.3.0`, `v0.3.1`) exist, so T35's live verification did happen**, even though `PROJECT_STATE.json`
and this file hadn't been updated to say so before this section was written; see the discrepancy
note at the top of Stage 3 below. T38–T40 (Dependabot, PR template, issue templates) remain recorded
backlog only — not scheduled, not implemented.*

---

## Stage 3 — Authentication & Authorization

**Status:** Architecture Approved — decisions D1–D7 below are locked in. **Phase 0 (T41–T45) done as
of 2026-08-06**, across two batches, both per explicit project-owner go-ahead (see
`docs/ImplementationLog/Stage3/Phase0.md`). `ADR-0020` written as part of T43; `ADR-0019` (D7 only)
written as part of T45; `ADR-0018` (D1–D6) subsequently written 2026-08-07, outside any task ID —
see the Phase 0 task table's discrepancy note for why (batch 2 reused the T44/T45 IDs for
different content per direct instruction). The `docs/templates/PreStageChecklist.md` sign-off is
now complete and approved (`docs/reviews/PreStageChecklist_Stage3_2026-08-07.md`, Reviewer sign-off
2026-08-07: Phase 0 Approved, approved to begin Phase 1). **`Phase0.md`'s own `Status` field has
since been updated to `Done` (2026-08-07, during Phase 1/`T46` documentation synchronization) —
the lag this note previously flagged is closed.** **Phase 1 under way: `T46` and `T47` done**
(2026-08-07 — see `docs/ImplementationLog/Stage3/Phase1.md`, QA Decision: Approved). **`T48`'s
previously-flagged discrepancy is now resolved** — a Project Manager cross-check (2026-08-07)
confirmed its content is genuinely satisfied by `T44`'s redefined scope and marked its row `Done`
accordingly (see T48's row below); this is a correction to this planning document, not new
implementation. **`T49` (the `refresh_tokens` migration) is now done too**, independently
QA-approved after one rework round (2026-08-07 — see T49's row below and
`docs/ImplementationLog/Stage3/Phase1.md`); **`T50` (`AuthService`) is the next unfinished task.**
`git log`/`git status` (Project Manager cross-check, second pass) confirm `T49`'s work has since
also merged (PR #7, "feat(auth): add refresh token persistence", commit `7bd6836`, merged via
`26702b6`) — `main` is now at `26702b6`, working tree clean, no branch left over from `T49`. The
previous note above (written mid-`T49`) is superseded by this one. **`T50` and `T51` are now both
done** (2026-08-08, Backend Developer session, one batch — `AuthService` plus its own tests,
implemented together per this project's established T46/T47/T49 precedent even though they're
separate task IDs; see `docs/ImplementationLog/Stage3/Phase1.md`). **QA Decision: Approved with
comments** (2026-08-08 — implementation sound, 345/345 full suite passing against live PostgreSQL,
28/28 new tests passing, ruff/black clean, no rework required; see `docs/ImplementationLog/Stage3/Phase1.md`'s
QA Decision section). **Phase 1 (`T46`–`T51`) is now complete. `T52` (`JwtAuthenticationProvider`,
Phase 2) is the next unfinished task; not authorized yet.**

**Process note (2026-08-08, Documentation Manager, per QA's comment on the T50/T51 batch):** the
`T50`/`T51` batch's Backend Developer role edited this file directly to mark `T50`/`T51` done,
ahead of a QA Decision and outside this file's own Project-Manager ownership
(`docs/ImplementationLog/README.md`'s Documentation Ownership table) — a deviation from the `T49`
batch's own pattern immediately above, which left this file to the Project Manager/Documentation
Manager roles after QA. QA reviewed the resulting content and found it accurate, so it was **not
reverted**. Recorded here as the formal correction: routine edits to this file belong to the
Project Manager role (or the Documentation Manager, marking a task done per the Developer/QA
record, per `docs/prompts/DocumentationManager.md` §2), exercised only *after* a QA Decision exists
— the same discipline the `T49` batch followed and every batch after this one should return to.
**T42–T43 (the
`get_db()`
commit/rollback fix) were the highest-priority implementation work and had to land before any
authentication code** — explicit project-owner instruction, consistent with this section's own
"Hard blocker" note. **A batch-3 re-verification pass (2026-08-06)** confirmed T44/T45 against
a more precise, exhaustive spec (exact dependency/config/interface requirements, an explicit "no
framework types in the port" constraint) — already correct, no code changes needed; closed 2
test-coverage gaps instead. QA Decision: Approved — see
`docs/ImplementationLog/Stage3/Phase0.md`. Backend total is 304 tests passing as of `T46`
(2026-08-07) — see `docs/ImplementationLog/Stage3/Phase1.md`.

### Discrepancy found before proceeding (per `AI_BOOTSTRAP.md`'s "trust the code" rule) — Resolved by T41

`PROJECT_STATE.json` used to say `currentStage: stage-2`, `git.branch: feature/github-actions-ci`,
and listed an `openQuestion` about T35 not being done. The actual repository disagreed: `git log`
showed a merge commit (`2db48d4`, "Merge pull request #1 from Intelligentclown/feature/github-actions-ci"),
the current branch was `main`, the working tree was clean, and **two** tags existed
(`v0.3.0`, `v0.3.1`). This confirmed the project owner's statement that Stage 2.7 was fully complete —
the docs just weren't synced after the merge. **T41 closed this out** (2026-08-06): `PROJECT_STATE.json`'s
`currentStage`, `git.branch`, `git.latestCommitAtThisUpdate`, and `openQuestions` now match reality.

### Scope

Real authentication (login) and authorization (permission-checked routes) for the Legal DMS,
wired to the Identity & Access schema Stage 2 already built (`users`, `roles`, `permissions`,
`user_roles`, `role_permissions`) and the `AuthenticationProvider`/`AuthorizationService` ports
Stage 1 already defined. This is the **first real business-adjacent feature** in the project —
everything through Stage 2.7 has been framework/schema/tooling only. Strictly scoped to
authentication and authorization: **no Matter/Client/Property/Document/Financial management, no
OCR/QR/Search/Reports/Payments/AI** — those remain future stages, not assumed or started here.

### How this roadmap was built

Read, in order: `AI_BOOTSTRAP.md`, `PROJECT_STATE.json`, `docs/Architecture.md`,
`docs/ProjectStatus.md`, this file's existing sections, `docs/SessionReport.md`,
`docs/ArchitectureScorecard.md`. Then reviewed the actual code rather than trusting docs alone:
`backend/src/app/infrastructure/persistence/models/identity.py` (the real `User`/`Role`/
`Permission`/`UserRole`/`RolePermission` columns), `application/interfaces/auth.py` (the exact
`CurrentUser`/`AuthenticationProvider`/`AuthorizationService` shapes already committed to),
`infrastructure/auth/*` (the two Stage 1 stub implementations), `application/errors/exceptions.py`
(confirmed `UnauthorizedError`/`ForbiddenError` already exist, unused), `tests/unit/test_auth.py`
(what's already tested), the seed-data migration
(`backend/alembic/versions/9963e15f2752_seed_lookup_data.py`, to see exactly what identity data
already exists), `backend/pyproject.toml`/`uv.lock` (confirmed no password-hashing or JWT library
is installed yet), `electron/preload.ts`/`ipc/channels.ts` (confirmed zero secure-storage IPC
surface exists), `ADR/0004` (what Stage 0 deliberately prepared vs. deferred for this exact stage),
and `docs/templates/PreStageChecklist.md` (this project's own required gate before stage code
starts).

### What already exists to build on (don't rebuild these)

- **Schema, fully ready:** `users` (`email` unique, `full_name`, `phone`, `password_hash` nullable
  `String(255)`, `is_active`, `last_login_at`, plus `AuditMixin`), `roles`, `permissions`,
  `user_roles`, `role_permissions` — all five tables exist, Stage 2, no migration needed for the
  core model.
- **Seed data, partially ready:** 6 roles already seeded (Administrator, Advocate, Paralegal,
  Clerk, Accountant, Read Only) and 18 permissions already seeded across 6 categories
  (`matters:*`, `clients:*`, `properties:*`, `documents:*`, `financial:*`, plus
  `users:manage`/`roles:manage`/`settings:manage`/`reports:read`). **Deliberately NOT seeded:**
  `role_permissions` (which permissions each role gets — the seed migration's own docstring says
  this is "an authorization business decision... better made by the stage that actually implements
  authorization") and `users` (no auth existed to log in with). Both are this stage's job.
- **Ports, already defined (Stage 1):** `CurrentUser` (`id`, `display_name`, `roles: frozenset[str]`,
  `is_authenticated`), `AuthenticationProvider.get_current_user()`, `AuthorizationService.
  require_permission(user, permission)`. `permissions.code`'s string convention
  (`"matters:read"`) already matches what `require_permission()` expects — the schema was
  deliberately designed to slot into this port without changing it.
- **Errors, already defined:** `UnauthorizedError` (401) and `ForbiddenError` (403) in the `AppError`
  hierarchy — currently unused anywhere, ready to raise.
- **Repository, already generic:** `SqlAlchemyRepository[User]` works today with zero new code —
  Stage 1's repository pattern is entity-agnostic.
- **What's genuinely missing:** any password-hashing library, any JWT/session-token library, any
  route, any real `AuthenticationProvider`/`AuthorizationService` implementation, any
  frontend auth state/login UI, any Electron secure-storage IPC surface, and (depending on the
  token-design decision below) possibly one new table.

### Hard blocker: fix before anything else in this stage

**Finding F1 from the (still otherwise unapproved) Stage 2.5 backlog — `get_db()` never
commits — is no longer optional hardening once this stage starts.** Every meaningful thing Stage 3
does is a database write: creating the first user, hashing and storing a password, recording
`last_login_at`, assigning a role, seeding `role_permissions`. `get_db()` currently only lets
`SqlAlchemyRepository` `flush()` within a request's transaction and never calls `session.commit()`
— the session closes at the end of the request without persisting anything. Every write in this
stage would appear to succeed and then silently vanish. This is pulled forward as **T41–T43** below,
verbatim from the existing Stage 2.5 design (already fully specified, never implemented) — see the
"Stage 2.5 — Architecture Hardening" section above for the original finding writeup (F1) if you want
the full context.

### Architecture decisions — APPROVED

Per this project's own charter (every stage's architecture proposal presented and approved before
code), these were the real decisions this stage couldn't proceed without. **All seven approved by
the project owner, with two refinements beyond the original recommendation (D4, D7) — final,
locked-in values below.** Nothing has been implemented yet; these are recorded here so
implementation has exactly one unambiguous spec to build against.

| # | Decision | **Approved** | Why |
|---|---|---|---|
| D1 | Token mechanism | **JWT access token (short-lived) + DB-backed, revocable refresh token.** One new migration (`refresh_tokens`). | A legal-document system has real confidentiality obligations — "logout" that can't actually revoke a token is a meaningful gap for a lost/stolen device. Short-lived access tokens (~15–30 min) limit exposure if one leaks; the refresh token is what's actually revocable. |
| D2 | Password hashing | **Argon2id via `argon2-cffi`.** | OWASP's current default recommendation for new applications. |
| D3 | JWT library | **`PyJWT`.** | More actively maintained currently than `python-jose`; fully encapsulated behind the token utility (T47) so swappable later at low cost if that changes. |
| D4 | First-admin bootstrap | **A one-time CLI command with an *interactive* password prompt** (`getpass`-style — the password is never a command-line argument, environment variable, or anything that would land in shell history or a process list). | Refines the original recommendation with the specific detail that matters most: a plaintext password must never pass through argv or env. |
| D5 | Self-registration | **None** — only admin-created users, via a `users:manage`-protected endpoint. | Every seeded role is internal staff; no client-facing portal exists or is planned. |
| D6 | Frontend token storage (Electron) | **Refresh token in OS-level encrypted storage via Electron's `safeStorage` API** (main process only, new IPC channel); **access token held in-memory only** (React state, never persisted — lost on app restart, forcing a silent refresh or re-login). | Matches this project's existing security posture (`contextIsolation`, no generic IPC passthrough). |
| D7 | `AuthenticationProvider` port signature | **`async def get_current_user(self, token: str | None) -> CurrentUser`** — exact approved signature. A genuine breaking change to an existing Stage 1 port, done explicitly and documented in `ADR-0019` rather than silently. | The only way a real implementation can know which request's token to validate; every alternative (hidden request-scoped global, constructor injection of a request-bound object) would be worse. |

**ADRs approved:**
- **`ADR-0018` — Authentication & Authorization Architecture** (records D1–D6: token mechanism,
  password hashing, JWT library, bootstrap strategy, self-registration, frontend token storage).
- **`ADR-0019` — `AuthenticationProvider` interface change** (records D7 specifically — the port
  signature break, why it's necessary, and what it constrains for any future
  `AuthenticationProvider` implementation).
- **`ADR-0020` — Session commit/rollback policy** (records the `get_db()` fix, T42–T43 below — "every
  session commits on success, rolls back on exception" as a deliberate policy, not an incidental
  patch; this is the ADR the Stage 2.5 section above had flagged as worth writing once T1 landed).

**Still open, distinct from D1–D7 — needs your sign-off before T66 specifically (not blocking
anything else):** the exact `role_permissions` matrix proposed in T66 below (which of the 18
permissions each of the 6 roles gets) was a proposal, not one of the seven approved decisions —
flagging so it isn't assumed approved by association.

### Task breakdown

Complexity: **XS** / **S** / **M**, same convention as Stage 2.5/2.7 — nothing here is larger than
M; anything that looked bigger was split further.

#### Phase 0 — Unblock & prerequisites (before any Phase 1 code)

| ID | Task | Complexity | Depends on | Priority |
|---|---|---|---|---|
| T41 | ~~Sync `PROJECT_STATE.json`/this file's stale fields to match reality (`currentStage`, `git.branch`, remove the resolved T35 `openQuestion`).~~ **Done** (2026-08-06). | S | — | — |
| T42 | ~~**Fix `get_db()`: commit on clean exit, rollback on exception** (Stage 2.5's F1/T1, pulled forward — see that section for the exact design).~~ **Done** (2026-08-06). | XS | — | **Highest priority — must land before any Phase 1 code, per explicit instruction.** |
| T43 | ~~Regression test proving a write survives across two independent sessions (Stage 2.5's T2), the commit-contract documentation note (T3), **and `ADR-0020` (session commit/rollback policy)** recording this as deliberate policy.~~ **Done** (2026-08-06 — 5 regression tests in `tests/integration/test_get_db_transaction_policy.py`; `ADR-0020` written; `docs/Architecture.md`/`docs/AI_HANDOVER.md` updated). | S | T42 | **Highest priority, same as T42.** |
| T44 | ~~Complete `docs/templates/PreStageChecklist.md` for Stage 3, signed off, stored at `docs/reviews/PreStageChecklist_Stage3_<date>.md` — this project's own required gate.~~ **Superseded 2026-08-06** — see discrepancy note below. What was actually done under the ID "T44": add the approved auth dependencies (`argon2-cffi`, `PyJWT`) and `Settings` config (`jwt_secret_key`, `jwt_algorithm`, `access_token_ttl_minutes`, `refresh_token_ttl_days`) — no hashing/JWT logic. **The `PreStageChecklist` sign-off itself remains not done.** | S | T41, T42, T43 | — |
| T45 | ~~Write `ADR-0018` (Authentication & Authorization Architecture — D1–D6) and `ADR-0019` (`AuthenticationProvider` interface change — D7).~~ **Partially superseded 2026-08-06** — see discrepancy note below. What was actually done under the ID "T45": the `AuthenticationProvider.get_current_user()` signature change (D7) in `application/interfaces/auth.py`, cascaded to `AnonymousAuthenticationProvider`/`presentation/api/deps.py`, plus `ADR-0019` (written, matching this row's original scope for D7). **`ADR-0018` (D1–D6) was not written** — outside batch-2's described scope. | S | D1–D7 (✅ approved) | — |

**Discrepancy note (2026-08-06):** the project owner's batch-2 instruction described different
content under the IDs "T44"/"T45" than this table originally defined (dependencies/config for T44;
the finalized `AuthenticationProvider` interface for T45, versus this table's original checklist-
sign-off / ADR-writing tasks). Flagged before implementing; proceeded on the explicit instruction
given (direct instruction is the more authoritative source), documented in full in
`docs/ImplementationLog/Stage3/Phase0.md`'s "⚠ Task-ID discrepancy" section. **Net open items this
left behind, untracked by any task ID:** the `PreStageChecklist.md` sign-off (T44's original
content) and `ADR-0018` (T45's original D1–D6 half). **Update (2026-08-07):** `ADR-0018` has since
been written (`ADR/0018-authentication-authorization-architecture.md`), closing that half — still
outside any task ID, but no longer an unwritten gap. **Further update (2026-08-07):** the
`PreStageChecklist.md` sign-off is also now complete and formally approved
(`docs/reviews/PreStageChecklist_Stage3_2026-08-07.md` — Reviewer: Dhimant Patel, 2026-08-07: Phase
0 Approved, approved to begin Phase 1). Both originally-orphaned items are closed; the only
remaining loose end is that neither was ever given its own task ID (the "task IDs are immutable"
rule below means this is now permanent — a closed gap, not an open one, so no tracking decision is
actually needed). See
[docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md](docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md)
for the canonical disambiguation reference (what each ID means before/after this reuse) and a
recommended (not yet adopted) "task IDs are immutable" rule to prevent this recurring.

#### Phase 1 — Backend: credentials & token foundation

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T46 | ~~Add the chosen password-hashing dependency (D2); `hash_password()`/`verify_password()` utility + unit tests (correct password verifies, wrong password fails, hash is never plaintext-equal to input).~~ **Done** (2026-08-07 — `infrastructure/security/password_hasher.py`, plain functions using `argon2.PasswordHasher`; 6 tests in `tests/unit/test_password_hasher.py`. See `docs/ImplementationLog/Stage3/Phase1.md`.) | S | T45 |
| T47 | ~~Add the chosen JWT dependency (D3); token utility — encode/decode access & refresh tokens (claims: `sub`, `roles`, `exp`, `jti`) + unit tests (round-trip, expired token rejected, tampered signature rejected).~~ **Done** (2026-08-07 — `infrastructure/security/jwt_service.py`: `create_access_token()`/`create_refresh_token()`/`decode_token()` using PyJWT; 9 tests in `tests/unit/test_jwt_service.py`. See `docs/ImplementationLog/Stage3/Phase1.md`.) | S | T45 |
| T48 | ~~Extend `Settings` with auth config: JWT signing secret (env-driven, no default in code), algorithm, access-token TTL, refresh-token TTL.~~ **Done — satisfied incidentally by T44's redefined scope, confirmed by the Project Manager cross-check on 2026-08-07** (`jwt_secret_key`/`jwt_algorithm`/`access_token_ttl_minutes`/`refresh_token_ttl_days` all exist in `Settings`, verified directly against `backend/src/app/infrastructure/config/settings.py`, and independently confirmed as T47's real consumer of those fields per `docs/ImplementationLog/Stage3/Phase1.md`). This is not a T44 scope-redefinition under the "task IDs are immutable" rule — T48's own originally-scoped content simply already exists, done as a side effect, not reassigned. | XS | T47 |
| T49 | ~~New Alembic migration: `refresh_tokens` table (`id`, `user_id` FK, `token_hash`, `issued_at`, `expires_at`, `revoked_at` nullable) — per approved D1.~~ **Done** (2026-08-07 — `backend/alembic/versions/2572cb3570d7_refresh_tokens.py` + `RefreshToken` model in `infrastructure/persistence/models/identity.py`; 4 new integration tests in `tests/integration/test_identity_models.py`. Independent QA approval after rework: live PostgreSQL verification pass, `alembic upgrade`/`downgrade`/`upgrade` round-trip pass, `alembic check` — no schema drift, 12/12 `test_identity_models.py` pass, full suite 317/317, ruff/black clean. The `token_hash` migration/model mismatch an earlier review round found is resolved. QA Decision: Approved. See `docs/ImplementationLog/Stage3/Phase1.md`.) | S | T45 |
| T50 | ~~`AuthService` (application layer): `authenticate(email, password) -> Result[User, AppError]`, `issue_tokens(user)`, `refresh(refresh_token)`, `revoke(refresh_token)`.~~ **Done** (2026-08-08 — `application/auth_service.py`, plus two small new ports it needed (`UserRepository`, `RefreshTokenRepository`, each `AbstractRepository` + one lookup method) and a `token_hasher.py` utility (SHA-256, not Argon2 — deterministic hashing needed for exact-match lookup). See `docs/ImplementationLog/Stage3/Phase1.md`.) | M | T46, T47, T49 |
| T51 | ~~Tests for `AuthService`: correct credentials, wrong password, unknown email, inactive user, expired/invalid/already-revoked refresh token, refresh rotation (old token revoked, new one issued).~~ **Done** (2026-08-08 — implemented in the same batch as T50 per this project's established T46/T47/T49 precedent and the Backend Developer role's "never skip tests for new behavior" rule; 28 tests in `tests/unit/test_auth_service.py` + `tests/unit/test_token_hasher.py`, covering every named scenario plus DB-level-expiry and stale-roles-on-refresh edge cases. See `docs/ImplementationLog/Stage3/Phase1.md`.) | M | T50 |

#### Phase 2 — Backend: wiring auth into the request pipeline

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T52 | Real `JwtAuthenticationProvider` implementing `AuthenticationProvider`'s approved new signature — `async def get_current_user(self, token: str \| None) -> CurrentUser` (D7/`ADR-0019`) — validates the bearer token, loads the `User` + roles, returns a populated `CurrentUser` (or the anonymous default for `token=None`/invalid). | M | T50, ADR-0019 |
| T53 | Real `RbacAuthorizationService` implementing `AuthorizationService` — checks `require_permission()` against the caller's roles → `role_permissions`. | S | T52 |
| T54 | `RequirePermission(...)` FastAPI dependency factory (closes Stage 2.5's flagged-not-scheduled F11 — now explicitly in scope). | S | T53 |
| T55 | Wire `JwtAuthenticationProvider`/`RbacAuthorizationService` into `configure_container()`, replacing the `Anonymous`/`Permissive` defaults. | XS | T52, T53 |
| T56 | Update `presentation/api/deps.py`'s `CurrentUserDep` for the new provider signature. | XS | T55 |
| T57 | Tests: valid token → correct `CurrentUser`; missing/expired/malformed/tampered token → 401; authenticated-but-unpermitted → 403; `configure_container()` resolves the real implementations. | M | T55, T56 |

#### Phase 3 — Backend: routes

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T58 | `POST /api/v1/auth/login` — email + password in, access + refresh tokens out (or a structured 401). | S | T57 |
| T59 | `POST /api/v1/auth/refresh` — refresh token in, new access (+ rotated refresh) token out. | S | T57 |
| T60 | `POST /api/v1/auth/logout` — revokes the presented refresh token. | XS–S | T57 |
| T61 | `GET /api/v1/auth/me` — current user's profile + roles, from `CurrentUserDep`. | XS | T57 |
| T62 | User management routes (admin-only, `users:manage`): list, get, create (hashes password), update, deactivate. | M | T54, T46 |
| T63 | Role-assignment routes: assign/remove a role for a user (`users:manage` or `roles:manage`). | S | T54 |
| T64 | Integration tests for every route above — happy path, wrong credentials, missing/invalid token, wrong permission, each asserting the exact status code and error shape. | M | T58–T63 |
| T65 | Wire login success/failure and permission-denied events into the existing `AuditLogger`. | S | T58, T54 |

#### Phase 4 — Data: seed & bootstrap

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T66 | New migration seeding `role_permissions` — map the 18 existing permissions to the 6 existing roles against a concrete proposed matrix (e.g. Administrator: all 18; Advocate: matters/clients/properties/documents `read`+`write`, financial `read`, reports `read`; Paralegal: same minus `write` on financial and minus `delete` everywhere; Clerk: matters/clients/documents `read`+`write`, no financial; Accountant: financial `read`+`write`, matters/clients `read`, reports `read`; Read Only: every `:read` permission, nothing else) — **the exact matrix is itself worth a quick sign-off, not just accepted silently**, since it's a real access-control decision. | S | T45 |
| T67 | First-admin bootstrap: one-time CLI command, interactive password prompt (`getpass` or equivalent — never argv/env/a config file) per approved D4. | S | T46, T62 |
| T68 | Tests: seed row counts match the approved matrix; bootstrap creates exactly one admin and is idempotent on re-run (doesn't create a second one, doesn't error). | S | T66, T67 |

#### Phase 5 — Frontend

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T69 | `post`/`put`/`delete` added to `httpClient.ts` (closes Stage 2.5's F10 — now actually needed, since login is a `POST`), parsing the backend's structured `{"error":{"code","message"}}` body. | S | — |
| T70 | Auth state management — a React context/provider holding the current user + tokens, `login()`/`logout()` actions. | M | T69 |
| T71 | Electron secure token storage (D6): new IPC channel(s), preload surface, main-process handlers using `safeStorage`. | M | — |
| T72 | Login page/form. | S | T70 |
| T73 | Protected-route wrapper — redirects unauthenticated users to `/login`. | S | T70 |
| T74 | Attach `Authorization` header to outgoing requests; handle a 401 response globally (clear session, redirect to login). | S | T70, T71 |
| T75 | Current-user display + logout action in `MainLayout`'s header. | XS | T70 |
| T76 | Frontend tests (RTL) for T70–T75: login form validation/submission, protected route redirect, 401 handling, logout clears state. | M | T72–T75 |

#### Phase 6 — Hardening & close-out

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T77 | Gate `/docs`/`/redoc` behind `settings.is_development` (Stage 2.5's F4 — bundled now since API docs exposure is meaningfully more sensitive once real auth/user data exists). | XS | — |
| T78 | Tighten CORS `allow_methods`/`allow_headers` from wildcards, or record an explicit ADR-note decision not to (Stage 2.5's F5 — same bundling rationale as T77). | XS–S | — |
| T79 | Full backend + frontend suite run, lint clean, and a live smoke walkthrough (login → access a protected route → refresh → logout, exercised for real, not just via tests). | S | All of the above |
| T80 | Full documentation pass: `docs/Architecture.md`, `docs/API.md`, `docs/FeatureRegistry.md`, `docs/ArchitectureScorecard.md`, `docs/ProjectStatus.md`, `PROJECT_STATE.json`, both `CHANGELOG.md` files, `docs/SessionReport.md`, this file. | M | T79 |

### Explicitly out of scope for this stage (flagged, not silently dropped)

- **Password reset / forgot-password** — needs real email sending; only `LoggingNotifier` exists
  today (no real backend implements `Notifier`). A future stage's decision, not assumed here.
- **Multi-factor authentication (MFA)** — not requested; would be additive on top of this stage's
  token design if scoped later.
- **OAuth/SSO / social login** — not requested; this schema/design doesn't preclude it later.
- **Rate limiting / account lockout on repeated failed logins** — genuinely worth having eventually,
  needs its own small design pass (in-memory vs. `Cache`-backed vs. a dedicated dependency); flagged
  as a near-term follow-up, not bundled into this already-large stage.
- **Session-management UI** (viewing/revoking active sessions/devices) — D1(a)'s `refresh_tokens`
  table makes this possible later without a schema change; not built now.
- **Row-level / column-level access control** — `ArchitectureScorecard.md` already names this as
  Stage 3+ only once a real permission model *and* real routes exist; this stage delivers the
  permission model and its first routes, but per-row scoping (e.g. "Advocate X can only see their
  own matters") is a business-feature-stage decision, not an auth-stage one.
- **Wiring any non-identity business schema** (Matters/Clients/Properties/Documents/Financial/etc.)
  — explicitly a later stage; this one only touches the Identity & Access tables.

### Recommended implementation order

1. **T41 → T42 → T43 → T44.** Close the doc discrepancy, fix the one correctness bug that would
   silently break everything else in this stage, gate the stage properly per this project's own
   process.
2. **Your decisions on D1–D7 → T45.** Nothing in Phase 1 onward should start until these are
   answered — several (D1, D7) change what gets built, not just how.
3. **Phase 1 (T46–T51), sequential within itself** — password hashing and JWT utilities are
   independent of each other and can be built in parallel; `AuthService` needs both.
4. **Phase 2 (T52–T57), sequential** — each step wires on top of the last; this is the "real auth
   exists" milestone.
5. **Phase 3 (T58–T65) and Phase 4 (T66–T68) in parallel** — routes and seed/bootstrap data don't
   depend on each other, both depend on Phase 2 being done (T62/T67 specifically need T46/T54).
6. **Phase 5 (T69–T76)** — can start as soon as Phase 3's login/refresh/me routes (T58, T59, T61)
   exist; doesn't need user-management or role-assignment routes (T62/T63) to begin.
7. **Phase 6 (T77–T80)** last — hardening and the live end-to-end walkthrough only make sense once
   backend and frontend both work together.

### Acceptance criteria

**Phase 0 done when:** `get_db()` commits on success/rolls back on exception, proven by a test that
writes in one session and reads in a genuinely separate one; `PreStageChecklist.md` is filled in and
signed off with no unexplained unchecked box; `PROJECT_STATE.json` matches real repository state.

**Phase 1 done when:** a wrong password never verifies against a correct hash and vice versa; a
JWT with a tampered signature or past its `exp` claim is rejected by the decode utility, not just
"probably rejected downstream"; `AuthService.authenticate()` returns a failure `Result` (never
raises) for every wrong-credential case and a success `Result` carrying a real `User` for the
right one.

**Phase 2 done when:** hitting any endpoint using `CurrentUserDep` with no token, an expired token,
or a tampered token returns 401 with the project's standard `{"error":{"code","message"}}` shape —
never a 500; hitting a `RequirePermission("x")`-guarded route as an authenticated user who lacks
`x` returns 403; the same route with `x` returns 200.

**Phase 3 done when:** `POST /auth/login` with real seeded-admin credentials (once T67's bootstrap
has run) returns a working access + refresh token pair; `POST /auth/refresh` with a valid refresh
token returns a new access token and the old refresh token can no longer be reused (per D1's
revocation design); `POST /auth/logout` followed by another `/auth/refresh` with the same token
fails; every user-management route enforces `users:manage` and returns 403 without it.

**Phase 4 done when:** querying `role_permissions` shows every role has exactly the permission set
the approved matrix (T66) specifies — no more, no less; running the bootstrap command twice creates
exactly one admin user, not two, and doesn't error on the second run.

**Phase 5 done when:** a fresh Electron launch with no stored token redirects straight to `/login`;
entering correct credentials lands on the app's main view with the current user's name visible;
closing and reopening the app (within the refresh token's validity) does **not** require logging in
again; an expired/revoked session redirects back to `/login` automatically on the next API call
that gets a 401; logging out clears the stored token such that a relaunch also requires login again.

**Stage 3 overall done when:** every phase's criteria above hold; the full backend + frontend test
suites are green; ruff/black/eslint/prettier are clean; a real, live walkthrough (not just automated
tests) of login → protected action → token refresh (or natural expiry) → logout has been performed
and observed; every architecture decision (D1–D7) has a matching ADR; all documentation listed in
T80 reflects reality; `IMPLEMENTATION_QUEUE.md` and `PROJECT_STATE.json` mark Stage 3 complete.

---

## Documentation Backlog (flagged, not scheduled — unrelated to any single stage)

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T81 | Root `README.md` has a stray "## Writing Rules" section appended at its end (rules about `ImplementationLog` phase files, ADR/CHANGELOG duplication) — reads as `docs/ImplementationLog/README.md` content misplaced into the root README rather than genuine root-README material. Investigate and, if confirmed misplaced, move or remove it. Flagged during the `PROJECT_WORKFLOW.md` review (2026-08-07); deliberately not fixed immediately, to keep that review focused. | XS | — |

---

*Stage 3's architecture (D1–D7, `ADR-0018`/`0019`/`0020`) is approved. **Implementation is
under way**: Phase 0 (T41–T45) is done (`docs/ImplementationLog/Stage3/Phase0.md`, Status: Done,
QA Decision: Approved) and the `docs/templates/PreStageChecklist.md` sign-off that gated Phase 1 is
complete and approved (`docs/reviews/PreStageChecklist_Stage3_2026-08-07.md`). Phase 1 is under
way — `T46`, `T47`, `T48` (satisfied by `T44`'s redefinition, confirmed 2026-08-07), and `T49`
(the `refresh_tokens` migration, independently QA-approved after rework, 2026-08-07) are all done
— see `docs/ImplementationLog/Stage3/Phase1.md`. `T50` (`AuthService`) is the next unfinished
task; not authorized this batch. See
`docs/Stage3_Backend_Handoff.md` for the backend-scoped implementation brief (T41–T68). T1–T18
(Stage 2.5, minus T1–T3 now folded into T41–T43 above) remain separately pending. T38–T40
(Dependabot, PR template, issue templates) and T81 (stray README content) remain backlog-only.*
