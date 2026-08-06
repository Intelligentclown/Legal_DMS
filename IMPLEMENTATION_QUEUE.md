# Implementation Queue

Tracks the actionable task backlog for the *current* stage only — granular, estimated,
dependency-ordered work items, distinct from [docs/Roadmap.md](docs/Roadmap.md) (stage-level,
multi-session scope) and [PROJECT_STATE.json](PROJECT_STATE.json) (point-in-time snapshot). This
file is expected to be rewritten at the start of each new stage.

Status values: `Not Started`, `In Progress`, `Done`, `Deferred`, `Blocked`.

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

*T1–T18 (Stage 2.5 hardening) remain not started, awaiting approval. T20–T21 (QA-review fixes) and
T22, T24–T34, T36–T37 (Stage 2.7 CI) are done. T35 (Stage 2.7's live verification) needs an explicit
go-ahead to commit and push before it can be completed. T38–T40 (Dependabot, PR template, issue
templates) are recorded backlog only — not scheduled, not implemented.*
