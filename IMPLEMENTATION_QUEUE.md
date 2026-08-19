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
QA Decision section). **Phase 1 (`T46`–`T51`) is now complete.**

**Phase 2 (`T52` onward) — correction, 2026-08-08:** `T52` (`JwtAuthenticationProvider`) was
explicitly authorized by the project owner in a Project Manager conversation, and was subsequently
implemented (`infrastructure/auth/jwt_authentication_provider.py`, 11 tests, full suite 356/356
passing, ruff/black clean) — but that authorization was never recorded in this file or
`PROJECT_STATE.json` before implementation began, so both incorrectly read "not authorized yet"
until this correction. That prior text did not mean the work was actually unapproved; it meant the
repository had fallen behind a real decision made elsewhere. QA independently reviewed `T52`'s code
and tests and found them technically correct, but rendered **Rework required** on process grounds
only: the stale "not authorized" text, a missing `docs/ImplementationLog/Stage3/Phase2.md`, and an
undocumented direct-to-`main` implementation (no feature branch, unlike every prior Stage 3 batch).
A documentation synchronization pass created `docs/ImplementationLog/Stage3/Phase2.md` and closed
the first two findings; a QA Reviewer pass then reviewed that synchronization and rendered
**Approved with comments** for the process gate specifically (2026-08-08) — the two documentation
findings were confirmed closed, and the third (branch/commit) was accepted as disclosed-but-open
per this project's own established precedent for the same class of deviation on the `T50`/`T51`
batch.

**Project Manager cross-check (2026-08-08):** rebuilding repository state fresh (per this role's own
rule not to trust a prior conversation) found that `T52`'s branch/commit gap had closed
independently — `git log` shows `feature/stage3-t52-jwt-authentication` merged via PR #9
(`baed936`), carrying `T52`'s code and the prior documentation-sync commit together. All three of
QA's original process findings were therefore substantively resolved, but the "Approved with
comments" process-gate decision itself was still only recorded in conversation, not in
`docs/ImplementationLog/Stage3/Phase2.md`'s own QA Decision section — flagged rather than treated as
satisfied.

**T52 administrative closeout (2026-08-08, Documentation Manager):** the gap the cross-check above
flagged is now closed — `Phase2.md`'s QA Decision section records **Approved with comments**
in-repository (not just in conversation), with `Git Commit: baed936` (feature commit `003ab15`) and
`Pull Request: #9` filled into its metadata block, and its `Status`/`Completed` fields updated to
`Done`/`2026-08-08`. **`T52` is now marked `Done` below**, per the Developer/QA record in `Phase2.md`
(`docs/prompts/DocumentationManager.md` §2 — marking a task done per that record is this role's
job, not a re-scoping). No implementation code was touched and no new implementation decision was
made as part of this closeout.

**`T53` documentation/process correction (2026-08-08, Documentation Manager — transparency pass,
not a closeout):** the statement this row previously carried ("T53–T57 remain not started, not
authorized") was itself stale and is corrected here. `T53` (`RbacAuthorizationService`) **is
technically implemented** — five new files (`role_permission_repository.py` port,
`sqlalchemy_role_permission_repository.py`, `rbac_authorization_service.py`, plus 13 new tests
across a unit and an integration file), 369/369 full suite passing, ruff/black clean — see
`docs/ImplementationLog/Stage3/Phase2.md`'s T53 batch sections. It was authorized by the project
owner in conversation; **that authorization was not recorded in this file or `PROJECT_STATE.json`
before implementation began** — it is being documented here only after the fact, not backdated to
imply otherwise. Two further process gaps, recorded in full in `Phase2.md`'s Problems Encountered
(T53 batch): the Backend Developer role's required approval checkpoint
(`docs/prompts/BackendDeveloper.md` §5 — summarize understanding, then wait for explicit approval of
*that summary* — distinct from the project owner's task-level authorization) was skipped, and `T53`
was implemented directly on `main` (no feature branch, no commit, no PR). **All four are
process/governance deviations, not technical defects** — `T53`'s code and tests are not in question.
**`T53` is NOT marked `Done` below and has NOT received a QA Decision** — its row is corrected to
reflect "implemented, QA pending," a distinct state from `Done`, per this project's own "an honest
unchecked box beats a falsely checked one" discipline. `T54`–`T57` remain genuinely not started, not
authorized.

**`T53` final closeout (2026-08-08, Documentation Manager):** since the correction above was
written, a QA Reviewer role independently reviewed `T53` — code/tests confirmed correct on the
merits (369/369 full suite, `ruff`/`black` clean, no scope creep into `T54`–`T57`) — and rendered
**QA Decision: Approved with comments** on both the technical review and the four process/governance
deviations named above, preserved as `docs/ImplementationLog/Stage3/Phase2.md`'s QA Decision — T53
batch records it, not altered here. The two governance deviations that were still open at that
decision (implemented directly on `main`; consequently uncommitted) have since closed:
`feature/stage3-t53-rbac-authorization` was branched, committed (`dd754f5`), opened as PR #10, and
merged (`a103dca`) — `main`/`origin/main` both verified at `a103dca`, working tree clean. The other
two deviations (authorization not pre-recorded; Backend Developer approval checkpoint skipped)
remain exactly as they happened — governance history, not erased by this closeout, which resolves
only the git-action gap. **`T53` is now marked `Done` below**, per the Developer/QA record in
`Phase2.md`, mirroring exactly how `T52` closed (branch → commit → PR → merge → then `Done`). No
implementation code was touched and no new implementation decision was made as part of this
closeout.

**`T54` governance reconciliation (2026-08-08, Documentation Manager):** this row previously read
"`T54`–`T57` remain not started, not authorized," which is now stale for `T54` specifically and is
corrected here. `T54` (`RequirePermission(...)` FastAPI dependency factory) **is technically
implemented and QA-reviewed** — `presentation/api/deps.py` extended with `get_authorization_service()`
and `RequirePermission(...)`, 5 new tests in `tests/unit/test_auth.py`'s `TestRequirePermission`
class, full suite 374/374 passing, `ruff`/`black` clean, no scope creep into `T53`/`T55`/`T56`/routes
— see `docs/ImplementationLog/Stage3/Phase2.md`'s new T54 batch sections. QA independently confirmed
all of this and rendered **QA Decision: Rework required, on process grounds only** — no code changes
needed. Three governance findings: (1) authorization exists in a Project Manager conversation, not
recorded in this file or `PROJECT_STATE.json` before implementation began — the third consecutive
Stage 3 Phase 2 batch with this exact gap (`T52`, `T53`, `T54`); (2) `Phase2.md` had no `T54` batch
entry until this pass; (3) `T54`'s changes exist directly on `main`, uncommitted, unbranched. **One
explicit non-finding, stated to avoid misrepresenting the record:** unlike `T53`, the Backend
Developer role's required approval checkpoint (`docs/prompts/BackendDeveloper.md` §5 — summarize
understanding, then wait for explicit approval of *that summary*) **was performed and explicitly
approved before implementation began** for `T54`. **`T54` is NOT marked `Done` below** — it stays
"implemented, technically approved, administratively open," the same state `T52`/`T53` each passed
through before their own branch/commit/PR closed the gap. `T55`–`T57` remain genuinely not started,
not authorized.

**`T54` final closeout (2026-08-10, Documentation Manager):** since the reconciliation above was
written, a QA Reviewer role independently re-reviewed `T54`'s process gate and rendered a **follow-up
QA Decision (2026-08-10): Approved with comments** — the original `Rework required` decision is
preserved verbatim in `docs/ImplementationLog/Stage3/Phase2.md` as the historical record, not erased.
Findings 2 (missing phase-log entry) and 3 (no branch/commit/PR) are resolved, independently
re-verified: `feature/stage3-t54-require-permission` → feature commit `dbd6724` → PR #12 → merged
`6396f6b`; `main`/`origin/main` both confirmed at `6396f6b`. Finding 1 (authorization not recorded
before implementation) remains open as permanent governance history, not erased — the same
disposition already applied to `T52`/`T53`'s identical finding. `T54`'s code and tests required no
changes at any point. **`T54` is now marked `Done` below**, per the Developer/QA record in
`Phase2.md`, mirroring exactly how `T52` and `T53` each closed. `T55`–`T57` remain not started, not
authorized.

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

**Resolved:** The exact `role_permissions` matrix proposed in T66 below has been officially approved by the project owner (2026-08-17), replacing the prior ambiguity.

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
| T52 | ~~Real `JwtAuthenticationProvider` implementing `AuthenticationProvider`'s approved new signature — `async def get_current_user(self, token: str \| None) -> CurrentUser` (D7/`ADR-0019`) — validates the bearer token, loads the `User` + roles, returns a populated `CurrentUser` (or the anonymous default for `token=None`/invalid).~~ **Done** (2026-08-08 — `infrastructure/auth/jwt_authentication_provider.py`; 11 tests in `tests/unit/test_jwt_authentication_provider.py`; full suite 356/356 passing, ruff/black clean. QA Decision: Approved with comments (process gate only — code/tests were independently confirmed correct from the start; see `docs/ImplementationLog/Stage3/Phase2.md`). Merged: PR #9, commit `baed936`.) | M | T50, ADR-0019 |
| T53 | ~~Real `RbacAuthorizationService` implementing `AuthorizationService` — checks `require_permission()` against the caller's roles → `role_permissions`.~~ **Done** (2026-08-08 — `infrastructure/auth/rbac_authorization_service.py` + `application/interfaces/role_permission_repository.py` + `infrastructure/persistence/sqlalchemy_role_permission_repository.py`; 13 tests; full suite 369/369 passing, ruff/black clean. QA Decision: Approved with comments — code/tests approved on the merits; four process/governance deviations named (authorization not pre-recorded, Backend Developer approval checkpoint skipped, implemented directly on `main`, consequently uncommitted). The latter two are now resolved: merged via PR #10, commit `dd754f5`, merge `a103dca`. The former two remain recorded as governance history, not erased — see `docs/ImplementationLog/Stage3/Phase2.md`'s T53 batch, Problems Encountered and QA Decision.) | S | T52 |
| T54 | ~~Real `RequirePermission(...)` FastAPI dependency factory (closes Stage 2.5's flagged-not-scheduled F11 — now explicitly in scope).~~ **Done** (implemented 2026-08-08, closed out 2026-08-10 — `presentation/api/deps.py` + `get_authorization_service()`; 5 tests in `tests/unit/test_auth.py`'s `TestRequirePermission`; full suite 374/374 passing, ruff/black clean. QA Decision: Approved with comments (follow-up, 2026-08-10) — the original Rework required (2026-08-08, process grounds only, no code changes) is preserved as historical record. Authorization not pre-recorded remains an open governance finding; branch/commit/PR closed via PR #12, feature commit `dbd6724`, merged `6396f6b`. The Backend Developer approval checkpoint was performed and approved this time, unlike `T53`. See `docs/ImplementationLog/Stage3/Phase2.md`'s T54 batch.) | S | T53 |
| T55 | ~~Wire `JwtAuthenticationProvider`/`RbacAuthorizationService` into `configure_container()`, replacing the `Anonymous`/`Permissive` defaults.~~ **Done** (2026-08-10). **Authorized by the project owner, conversationally, 2026-08-10** — scope originally limited to this row's own literal description (the two `container.register(...)` replacements). **Correction (2026-08-10, same day, after QA review):** this row previously claimed the authorization was "recorded here before implementation begins" — that claim was inaccurate and was corrected: the committed `HEAD` at the time still read `T55` as unauthorized, and nothing about this authorization was ever committed before implementation existed. This is the **fourth consecutive** occurrence of the authorization-recording gap already seen on `T52`/`T53`/`T54` — preserved as permanent governance history, not erased by this closeout. **Architectural clarification + expanded scope (also conversational, same day):** the literal `container.register(...)` approach is technically unworkable (`container.resolve()` is synchronous/zero-arg; both real implementations need a request-scoped `AsyncSession`) — the project owner additionally authorized request-scoped `Depends()` construction in `presentation/api/deps.py` (via `DBSessionDep` → `SqlAlchemyUserRepository`/`SqlAlchemyRolePermissionRepository` → the real provider/service, fresh permission mapping per request, no caching policy) as the technically-correct implementation of this same task. **Implemented** (2026-08-10 — see `docs/ImplementationLog/Stage3/Phase2.md`'s T55 batch: 6 new integration tests, full suite 380/380 passing, ruff/black clean, request-scoped session usage independently verified, no `T52`/`T53`/`T54`/`T56`/`T57`/route scope creep). **QA Decision: original Rework required (2026-08-10 — governance/process grounds only, no code changes required) preserved verbatim; follow-up Approved with comments (2026-08-10, same day) is the final disposition, once branch/commit/PR closed: PR #15, feature commit `86a3d5d`, governance commit `f070e28`, merged `b094436`.** | XS | T52, T53 |
| T56 | ~~Update `presentation/api/deps.py`'s `CurrentUserDep` for the new provider signature.~~ **Done** (2026-08-12). **Authorized by the project owner, recorded as its own documentation-only commit (`91e0785`, PR #17, merged `89a3a5e`) before implementation began** — the first Stage 3 Phase 2 batch where this actually held, after four consecutive misses (`T52`–`T55`). Implemented `get_bearer_token()` (FastAPI `HTTPBearer(auto_error=False)`) and wired it into `get_current_user()`, replacing the `token=None` placeholder; 3 new tests, full suite 383/383 passing, ruff/black clean, boot smoke test passed, Postgres-backed verification completed. QA Decision: Approved with comments — no technical defects; comment is a non-blocking future observation about an end-to-end `TestClient`-level bearer-token test once a real protected route exists (`T58`+). Merged: PR #18, feature commit `fcc68e0`, merge `d69c4eb`. `T57` and any route remain explicitly unauthorized. | XS | T55 |
| T57 | Close the 401/403 gap in the request-authorization pipeline. **Corrected objective (2026-08-12, architecture clarification pass — see `docs/ImplementationLog/Stage3/Phase2.md`'s T57 pre-implementation section for the full analysis) — the original "Tests: ..." wording, including its `configure_container() resolves the real implementations` bullet, is superseded by this row.** The stale `configure_container()` criterion is **removed outright**, not reworded — `T55` deliberately removed `AuthenticationProvider`/`AuthorizationService` from `configure_container()` in favor of request-scoped construction in `deps.py`, and `tests/unit/test_auth.py`'s `TestConfigureContainer` already asserts the opposite of what that criterion demanded; satisfying it would mean undoing already-approved `T55` architecture, which is explicitly out of scope. <br><br>**Acceptance criteria:** (1) an unauthenticated caller (no token, expired token, malformed token, or tampered token — `CurrentUser.is_authenticated is False`, regardless of which of these four caused it) passing through `RequirePermission` must result in `UnauthorizedError`/401, not `ForbiddenError`/403 as today. (2) An authenticated caller lacking the required permission must still result in `ForbiddenError`/403 — unchanged. (3) "valid token → correct `CurrentUser`" is **already proven by `T55`** (`tests/integration/test_auth_dependency_wiring.py`) — `T57` adds regression coverage under its own task ID, not new authentication architecture. (4) "authenticated-but-unpermitted → 403" is **already covered by `T54`/`T55`** — regression coverage only. (5) True `TestClient`-level HTTP-status verification against a real protected route is **explicitly deferred to `T58`+** — no route exists yet to test against; only dependency-level verification (calling `RequirePermission`'s inner function directly, the same pattern `T54`/`T55`/`T56` already established) is in scope now. <br><br>**Authorized architectural approach (approved by the project owner, 2026-08-12, Option 1 of the architecture clarification pass — recorded here before implementation begins):** `RequirePermission`'s inner dependency function in `presentation/api/deps.py` will check `user.is_authenticated` **before** calling `authorization_service.require_permission()`. If the caller is not authenticated, it raises `UnauthorizedError` directly. Otherwise, it delegates to `AuthorizationService` exactly as today, preserving `ForbiddenError` for the authenticated-but-unpermitted case. <br><br>**Explicitly not authorized as part of this:** `AuthorizationService`'s port contract (`application/interfaces/auth.py`) is **not** being changed; `RbacAuthorizationService` is **not** being modified; `PermissiveAuthorizationService` is **not** being modified; every other `T52`–`T56` implementation file remains untouched; no route is created; `T58`+ remains out of scope. **No ADR is required for this option** — a single-file, non-port-breaking addition, unless this project's existing governance rules (`AI_BOOTSTRAP.md`'s "every significant architectural decision gets an ADR") are separately determined to require one. ~~Not yet implemented.~~ **Done** (2026-08-13 — `presentation/api/deps.py`'s `_require_permission` gains the `is_authenticated` short-circuit exactly as authorized above; 3 new tests + 1 updated, full suite 386/386 passing, ruff/black clean, boot smoke test passed, 127/127 integration tests against live Postgres per PR #20. QA Decision: Approved with comments — no technical defects; comment preserves the already-flagged deferral of true `TestClient`-level HTTP verification to `T58`+, not a new finding. Merged: PR #20, feature commit `7c9fc3a`, authorization commit `65dd563`, merge `472f7cb`. See `docs/ImplementationLog/Stage3/Phase2.md`'s T57 batch.) | S | T55, T56 |

#### Phase 3 — Backend: routes

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T58 | `POST /api/v1/auth/login` — email + password in, access + refresh tokens out (or a structured 401). **Authorized by the project owner, 2026-08-13, recorded here — as its own documentation-only commit (`58c8e40`) — before any implementation exists.** Approved scope: the login route itself, its request/response schemas, per-request `AuthService` wiring (constructed from `DBSessionDep`, the same pattern already established for `AuthenticationProvider`/`AuthorizationService`), and router registration in `router.py`, plus tests. Tests may create users directly against the test database — this task does not depend on `T67`'s bootstrap CLI existing. `T59`–`T67` remain explicitly out of scope and unauthorized. **Done** (2026-08-15 — `presentation/api/v1/auth.py` (new): `LoginRequest`/`LoginResponse` co-located, no `ApiResponse[T]` wrapper since a token pair isn't a fetchable resource; `login()` calls `AuthService.authenticate()`, raising `result.error` directly on failure so the existing global `AppError` handler renders the structured 401. `presentation/api/deps.py` gains `get_auth_service()`/`AuthServiceDep`, building `AuthService` fresh per request from `DBSessionDep`, mirroring `T55`'s construction pattern exactly. Router mounted in `router.py`. 5 new integration tests in `tests/integration/test_auth_login.py` (valid credentials, wrong password, unknown email — same generic message as wrong password, inactive user, malformed body → 422), against a real mounted app and real Postgres via `httpx.AsyncClient`/`ASGITransport` with a `get_db` dependency-override, needed because `fastapi.testclient.TestClient` runs the app on a separate event-loop thread that breaks this exact override. Full suite 391/391 passing (386 prior + 5 new), ruff/black clean, boot smoke test passed (`/api/v1/auth/login` confirmed in `app.openapi()["paths"]`). QA Decision: **Approved with comments** — no technical defects; two non-blocking comments: (1) Starlette's `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning surfaced in test output is framework-internal, not a `T58` defect; (2) the test-local `app.dependency_overrides[get_db]` pattern is safe under the current sequential test execution and should only be reconsidered if parallel test execution is introduced. Authorization commit `58c8e40` (2026-08-13) precedes implementation commit `76cd28f` (2026-08-15) — confirmed by commit order, the third consecutive Stage 3 batch to record authorization before implementation, extending the streak `T56`/`T57` started. Merged: PR #22, feature commit `76cd28f`, authorization commit `58c8e40`, merge `e67da02`. See `docs/ImplementationLog/Stage3/Phase3.md`'s T58 batch.) | S | T57 |
| T59 | `POST /api/v1/auth/refresh` — refresh token in, new access (+ rotated refresh) token out. **Authorized by the project owner, 2026-08-15, recorded here — as its own documentation-only commit (`163085d`) — before any implementation exists.** Approved scope: the refresh route itself, its request/response schemas, reuse of the existing per-request `AuthServiceDep` (`T58`), router integration, and tests covering successful refresh/rotation and invalid, expired, revoked, or unknown refresh tokens. `T60`–`T67` remain explicitly out of scope and unauthorized. **Done** (2026-08-15 — `presentation/api/v1/auth.py` extended (not `deps.py`/`router.py` — `T58`'s `AuthServiceDep` reused unchanged): `RefreshRequest`/`RefreshResponse` co-located, bare (no `ApiResponse[T]`), matching `login`'s convention; `refresh()` calls `AuthService.refresh()` (`T50`/`T51`, unmodified), which already collapses invalid/expired/revoked/unknown tokens into one generic `UnauthorizedError` — raised directly on failure, same pattern as `login`. 7 new integration tests in `tests/integration/test_auth_refresh.py` (valid refresh returns a new, different token pair; a rotated token can't be reused; invalid/expired/revoked/unknown tokens each → 401; malformed body → 422), reusing `T58`'s `httpx.AsyncClient`/`ASGITransport`/`get_db`-override test pattern verbatim. Full suite 398/398 passing (391 prior + 7 new) — personally re-run against live Postgres this session (reachable this time), ruff/black clean, boot smoke test passed (`/api/v1/auth/refresh` confirmed in `app.openapi()["paths"]`); `git show --stat 56eb7c2` independently confirms exactly two files changed, no `deps.py`/`router.py`/other-route touch. QA Decision: **Approved with comments** — "no technical defects" per PR #24; unlike `T58`'s PR, PR #24's own body does not itemize specific non-blocking comment text beyond that phrase — recorded here exactly as given, not invented. Authorization commit `163085d` (2026-08-15, 11:06:35 IST) precedes implementation commit `56eb7c2` (2026-08-15, 11:17:32 IST) — confirmed by commit order, the fourth consecutive Stage 3 batch to record authorization before implementation, extending the streak `T56`/`T57`/`T58` started. Merged: PR #24, feature commit `56eb7c2`, authorization commit `163085d`, merge `721cec5`. See `docs/ImplementationLog/Stage3/Phase3.md`'s T59 batch.) | S | T57 |
| T60 | `POST /api/v1/auth/logout` — revokes the presented refresh token. **Authorized by the project owner, 2026-08-15, recorded here — as its own documentation-only commit (`726e8cf`) — before any implementation exists.** Approved scope: the logout route in the existing `presentation/api/v1/auth.py`, using the existing `AuthServiceDep` and `AuthService.revoke()`, with appropriate request/response handling and tests. Tests must explicitly verify logout's idempotent behavior: a valid refresh token is revoked, an already-revoked token succeeds without error, and an unknown token also succeeds without error. **Must not modify** `AuthService`, `deps.py`, `router.py`, or the existing login/refresh behavior. `T61`–`T67` remain explicitly out of scope and unauthorized. **Done** (2026-08-15 — `presentation/api/v1/auth.py` extended (not `deps.py`/`router.py`/`AuthService` — the "must not modify" constraint honored exactly): `LogoutRequest` co-located; `logout()` calls `AuthService.revoke()` (`T50`/`T51`, unmodified — returns `None`, never a `Result`, since an unknown or already-revoked token is a silent no-op, not a failure) and returns `204 No Content` with no body, mirroring `presentation/common/crud_router_factory.py`'s `delete_item` — the only existing "action succeeded, nothing to return" precedent in this codebase. 5 new integration tests in `tests/integration/test_auth_logout.py` (a valid token is actually revoked, verified against the stored `RefreshToken` row's `revoked_at`; an already-revoked token still succeeds; an unknown token succeeds; a malformed token string succeeds; a malformed body → 422), reusing `T58`/`T59`'s `httpx.AsyncClient`/`ASGITransport`/`get_db`-override pattern verbatim. Full suite 403/403 passing (398 prior + 5 new) — personally re-run against live Postgres this session, ruff/black clean, boot smoke test passed (`/api/v1/auth/logout` confirmed in `app.openapi()["paths"]`, alongside `login`/`refresh`/`health`/`version` only — no `T61`+ scope creep); `git show --stat 5b9bf57` independently confirms exactly two files changed. QA Decision: **Approved** — PR #26's own body states "no defects" without the "with comments" qualifier `T58`/`T59` carried, and no comment text exists anywhere in the repository (PR body, both commit messages, and `gh api pulls/26/reviews`, empty, all checked) — recorded here as a plain `Approved`, not assumed to be "with comments" just because the two prior batches were. Authorization commit `726e8cf` (2026-08-15, 11:57:59 IST) precedes implementation commit `5b9bf57` (12:05:34 IST, ~8 minutes later same day) — confirmed by commit order, the fifth consecutive Stage 3 batch to record authorization before implementation, extending the streak `T56`/`T57`/`T58`/`T59` started. Merged: PR #26, feature commit `5b9bf57`, authorization commit `726e8cf`, merge `941ed42`. See `docs/ImplementationLog/Stage3/Phase3.md`'s T60 batch.) | XS–S | T57 |
| T61 | `GET /api/v1/auth/me` — current user's profile + roles, from `CurrentUserDep`. **Authorized by the project owner, 2026-08-15, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope: the route returns exactly `CurrentUser`'s existing three fields (`id`, `display_name`, `roles`) — no additional profile fields (`email`/`phone`/`is_active`/`last_login_at` from the `User` row) are in scope. Requires authentication via `CurrentUserDep` only — **no specific RBAC permission is required**; any authenticated user may access their own profile. `RequirePermission(...)` is explicitly **not** used for this route (none of the 18 seeded permission codes represents "view own profile," and none is being invented here). `AuthService`, `deps.py`'s existing dependencies (reuse only), `router.py`'s existing mount (reuse only, already includes `auth.router`), `CurrentUser`'s dataclass shape (unchanged), `JwtAuthenticationProvider`, `RbacAuthorizationService`, and every other `T52`–`T60` file remain unmodified. `T62`–`T67` remain explicitly out of scope and unauthorized. **Done** (2026-08-15 — `presentation/api/v1/auth.py` extended with a co-located `MeResponse` and `me()` route handler taking `CurrentUserDep` directly; no `deps.py`/`router.py`/`AuthService`/`CurrentUser`/`JwtAuthenticationProvider`/`RbacAuthorizationService` change. `CurrentUserDep` never raises; `me()` itself raises `UnauthorizedError` when `is_authenticated` is `False` — the same check `RequirePermission` already makes, no permission code required. On success, returns `ApiResponse(data=MeResponse(...))` with `roles` sorted for deterministic output. 7 new integration tests in `tests/integration/test_auth_me.py` (valid token, missing token, malformed token, expired token, inactive-user token, unknown-user token, multiple roles). Full suite 410/410 passing (403 prior + 7 new) — personally re-run against live Postgres post-merge, ruff/black clean, boot smoke test passed, `app.openapi()["paths"]` confirmed to contain exactly the six expected routes — no scope creep, no forbidden file touched, per `docs/HANDOFF/T61_HANDOFF.md` §4/§5. **QA Decision: Approved** (plain, no comments) — rendered by the QA Reviewer role independently against the working tree before it was committed, recorded in `docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision — T61 batch` section. **Merged: PR #30, feature commit `fa57e28`, authorization commit `520026f`, merge `bdffb5e`** — `main` and `origin/main` both verified at `bdffb5e`; `git show bdffb5e --stat` independently confirms exactly the nine files this batch's own scope covers, no forbidden file touched. See `docs/ImplementationLog/Stage3/Phase3.md`'s T61 batch, including its Post-Merge Verification note.) | XS | T57 |
| T62 | User management routes (admin-only, `users:manage`): list, get, create (hashes password), update, deactivate. **Authorized by the project owner, 2026-08-16, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope: five hand-written routes in a new `presentation/api/v1/users.py` (not the CRUD factory — `crud_router_factory.py` remains unmodified) — `GET /api/v1/users` (paginated via existing `limit`/`offset` only, no search/filter/sort), `GET /api/v1/users/{id}`, `POST /api/v1/users` (hashes the incoming plaintext password via existing `hash_password()`, T46), `PUT /api/v1/users/{id}`, and `POST /api/v1/users/{id}/deactivate` (sets `is_active=False` via `service.update()`, never `service.delete()`/a hard delete; idempotent; `200` returning the updated user, not `204`). All five gated by `RequirePermission("users:manage")` (T54). New co-located schemas: `UserRead` (`id`, `email`, `full_name`, `phone`, `is_active`, `last_login_at` — **must never include `password_hash`**), `UserCreate` (`email`, `full_name`, `phone: str \| None = None`, `password`), `UserUpdate` (`email: str`, `full_name: str`, `phone: str \| None` — **all three required keys, no defaults**, matching this codebase's only existing full-replacement-PUT/request-schema convention; **excludes `password` and `is_active`** — no password update and no reactivation are part of this task). Duplicate email on create → `409` via the existing, previously-unused `ConflictError`. Unknown id on get/update/deactivate → `404` via existing `NotFoundError`. `T63` (role assignment) is explicitly out of scope — created users have zero roles. No change to `deps.py`, `router.py` beyond mounting the new router, `AuthService`, `CurrentUser`, or any `T52`–`T61` file. **Done** (2026-08-16 — new `presentation/api/v1/users.py`: router-level `RequirePermission("users:manage")` covering all five routes; `get_user_repository()`/`get_user_service()` local to this module (not `deps.py`); `create_user()` hashes via existing `hash_password()`, never persists plaintext; `deactivate_user()` calls `service.update()`, never `delete()`, idempotent, row/relationships preserved. 28 new integration tests in `tests/integration/test_users.py` (authorization 401/403 per route, list/pagination, get, create incl. hashing and duplicate-email 409, full-replacement `PUT` incl. rejecting smuggled `password`/`is_active`, deactivate incl. idempotency and relationship preservation). Full suite 438/438 passing (410 prior + 28 new) — personally re-run against live Postgres on merged `main`, ruff/black clean, boot smoke test passed, `app.openapi()["paths"]` confirmed to contain exactly the nine expected routes, no forbidden file touched, per `IMPLEMENTATION_QUEUE.md`'s own row above. **QA Decision: Approved with comments** — no technical defects; the one comment is a named governance finding, not a code finding: `T62` was merged (PR #33 → `3a4a21c`) **before** its QA Decision was recorded in `docs/ImplementationLog/Stage3/Phase3.md`, violating `PROJECT_WORKFLOW.md`'s standard lifecycle and this batch's own stated intent ("QA review — not performed by this batch... before any documentation sync **or merge** proceeds"). A pre-merge QA pass had in fact already reached this same disposition on the merits — only its repository-visible recording was skipped, which is what let the merge proceed unblocked. Recorded as permanent governance history, not erased, the same discipline this project applied to `T52`–`T55`'s authorization-recording gaps. **Merged: PR #33, feature commit `a3e8810`, authorization commit `e10bdc8`/PR #32/`ea80b74`, merge `3a4a21c`** — `main` and `origin/main` both verified at `3a4a21c`; `git diff ea80b74 3a4a21c --name-only` independently confirms exactly the four files this batch's own scope covers, no forbidden file touched across the full authorization-to-merge range. See `docs/ImplementationLog/Stage3/Phase3.md`'s T62 batch, including its `QA Decision — T62 batch` section. | M | T54, T46 |
| T63 | Role-assignment routes: assign/remove a role for a user (`users:manage` or `roles:manage`). **Authorized by the project owner, 2026-08-16, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope, resolving the T63 Scope Assessment's open items: **`POST /api/v1/users/{user_id}/roles`** (body `{"role_id": UUID}`) — `201` returning a new `RoleAssignmentRead` (`user_id`, `role_id`, `assigned_at`, `assigned_by` — populated from the calling admin's `CurrentUserDep` id), `404` if the user or role doesn't exist, `409` via the existing `ConflictError` if the assignment already exists (matching `UserRole`'s own `UniqueConstraint(user_id, role_id)` and T62's duplicate-email-on-create precedent — **not** idempotent, unlike `deactivate`). **`DELETE /api/v1/users/{user_id}/roles/{role_id}`** — `204`, `404` if the user, role, or the specific assignment doesn't exist (matching `crud_router_factory.delete_item`'s only existing DELETE-verb precedent, not `logout`/`deactivate`'s idempotent-`POST` pattern). Both routes gated by **`RequirePermission("users:manage", "roles:manage")`** — `RequirePermission` (`deps.py`, T54) is extended to accept multiple permission codes via `*permissions: str`, granting access if the caller holds *any* one of them; every existing single-argument call site (T54/T58–T62) continues to work unchanged; the existing `is_authenticated` 401-before-403 check (T57) is preserved, unchanged, ahead of the (now possibly multiple) permission check. New repository methods `assign_role(user_id, role_id, assigned_by)`/`remove_role(user_id, role_id)` added to `UserRepository`/`SqlAlchemyUserRepository` (not a new repository class — narrow, concrete, immediate-caller-driven, matching `get_by_email()`/`get_role_names()`'s existing precedent); role existence is validated via the generic `AbstractRepository[Role].get_by_id()` (no new `Role`-specific repository). `UserRead`/`UserCreate`/`UserUpdate` (T62) are **not** modified — role display remains out of this schema, matching T61's own separation of `/me`'s roles from any user-profile schema. No role *creation*, no `role_permissions`/permission-matrix change (`T66`'s territory), no password/reactivation/deletion/search/audit/frontend work — all explicitly out of scope, per the T63 Scope Assessment's boundary table. No migration — `user_roles` already supports this fully. `crud_router_factory.py`, `AuthService`, `CurrentUser`, and every `T52`–`T62` file besides `deps.py`'s `RequirePermission` extension and `UserRepository`/`SqlAlchemyUserRepository`'s two new methods remain unmodified. **Done** (2026-08-16 — `presentation/api/v1/users.py` extended with `POST /api/v1/users/{id}/roles` and `DELETE /api/v1/users/{id}/roles/{role_id}`, gated by `RequirePermission("users:manage", "roles:manage")`; `deps.py`'s `RequirePermission(permission: str)` extended to `RequirePermission(*permissions: str)`, granting on any one supplied permission — every existing single-argument call site unaffected, confirmed by the unchanged `TestRequirePermission` suite, 8/8 still passing. New `assign_role()`/`remove_role()` on `UserRepository`/`SqlAlchemyUserRepository`; role existence checked via the existing generic `AbstractRepository[Role]`. One file outside the originally authorized scope, flagged before editing and independently confirmed genuinely necessary and minimal by QA, not a scope expansion: `tests/support/in_memory_user_repository.py` needed the same two new methods to keep satisfying the now-larger `UserRepository` ABC it implements — a mechanical consequence of the interface extension. 21 new integration tests in `tests/integration/test_users.py`. Full suite 459/459 passing (438 prior + 21 new) — personally re-run against live Postgres on merged `main`, `ruff`/`black` clean, boot smoke test passed, `app.openapi()["paths"]` confirmed to contain exactly the eleven expected route/method combinations — no forbidden file touched. **QA Decision: Approved** (plain, no comments) — rendered and committed (`6a8608f`) **before** PR #36 merged, recorded in `docs/ImplementationLog/Stage3/Phase3.md`'s `QA Decision — T63 batch` section: no technical defects, no unresolved scope issue — the deliberate correction of `T62`'s own named governance finding (which was merged before its QA Decision existed); `T63`'s QA Decision was durably committed and pushed first this time. **Authorization: commit `93cda84`, PR #35, merge `97ab953`. Implementation: feature commit `3cea676`, QA-approval commit `6a8608f`, PR #36, merge `ef419c3`.** `main`/`origin/main` both independently verified at `ef419c3`; `git diff 97ab953..ef419c3 --name-only` confirms exactly the seven files this batch's own scope covers, no forbidden file touched. See `docs/ImplementationLog/Stage3/Phase3.md`'s T63 batch, including its `QA Decision — T63 batch` section and its Post-Merge Verification note. | S | T54 |
| T64 | Integration tests for every route above — happy path, wrong credentials, missing/invalid token, wrong permission, each asserting the exact status code and error shape. **Authorized by the project owner, 2026-08-16, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope: Add missing exact error-shape and invalid-token integration-test coverage for T58–T63 routes. Permitted files: `test_auth_login.py`, `test_auth_refresh.py`, `test_auth_logout.py`, `test_auth_me.py`, `test_users.py`. Required implementation: Update every existing negative test covering 401, 403, 404, 409, or 422 to explicitly assert `response.json()["error"]["code"]` and `response.json()["error"]["message"]`. Add explicit invalid-token coverage alongside missing-token coverage for all 7 T62/T63 user/resource routes in `test_users.py`. Preserve the established logout contract (no missing-token 401 assertions for logout). Preserve the established login contract (no bearer-token requirements to login). Forbidden: Any production-code modification under `backend/src/app/**`, any new file, any API/production contract change, any migration, any audit logging or T65 work, any T65 authorization. **Done** (2026-08-16 — `test_auth_login.py`, `test_auth_refresh.py`, `test_auth_logout.py`, `test_auth_me.py`, and `test_users.py` updated with exact error-shape assertions; explicit invalid-token tests added to all 7 `T62`/`T63` routes in `test_users.py`. Login tokenless contract and logout no-401 contract preserved. No production code or frontend files modified. **QA Decision: Approved** (pre-merge, commit `fc9fb0b`) — test execution constrained by a pre-existing infrastructure issue on `main` (multiple alembic heads), but static verification passed. **Authorization: commit `b63bc6d`. Implementation: feature commit `f321065`, PR #38, merge `fab2933`.** `main`/`origin/main` both verified at `fab2933`.) | M | T58–T63 |
| T65 | Wire login success/failure and permission-denied events into the existing `AuditLogger`. **Authorized by the project owner, 2026-08-16, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope: Wire exactly two categories of events into `AuditLogger`: (1) Login outcomes (successful login, failed login), and (2) Permission-denied events (authenticated requests rejected with HTTP 403). Use authorized action names: `login_success`, `login_failure`, `permission_denied`. Use `resource_type = "auth"` for login and `resource_type = "endpoint"` for 403s (subject to existing `AuditLogger` contract compatibility, no schema modifications allowed). Explicitly excluded: 401 unauthenticated requests (missing/malformed/invalid/expired/revoked bearer tokens), 422 validation errors, successful authorization, refresh, and logout outcomes. The authenticated user must remain the audit actor for 403s, and existing HTTP behavior/responses (including OR permission semantics and generic 401s for login failures) must remain unchanged. No plaintext passwords or authentication secrets may be logged. Permitted implementation areas: `auth_service.py`, `deps.py`, `test_auth_login.py`, `test_auth_service.py`, `test_users.py`. Forbidden: T66, T67, audit schema redesign/migrations, frontend changes, new tables/endpoints, password reset/logout/refresh/401/422/success auditing, role/permission matrix changes, global exception-handler or middleware redesign. **Done** (2026-08-17 — `AuthService.authenticate()` records exactly one `login_success`/`login_failure` event per call via a new required `audit_logger` constructor parameter (`resource_type="auth"`; failure `reason` — `unknown_user`/`wrong_password`/`inactive_account` — distinguished only in the audit trail, the HTTP response staying the single generic 401 it always was). `RequirePermission`'s final-candidate denial (`deps.py`) records exactly one `permission_denied` event (`resource_type="endpoint"`) via `container.resolve(AuditLogger)` — not a new parameter, so `tests/unit/test_auth.py::TestRequirePermission`'s existing two-positional-argument direct calls stay unaffected (8/8 confirmed unchanged) — then re-raises the identical `ForbiddenError`; `T63`'s OR-permission semantics preserved exactly, so a denial a later candidate then grants is never audited. No new `AuditLogger` implementation, no schema/migration change, no route added. 15 new tests across `test_auth_service.py`/`test_auth_login.py`/`test_users.py`. **Governance history, preserved not collapsed:** implementation PR #41 (`fab38e3`) shipped without a `Phase3.md` batch entry; a first independent QA pass found the code itself defect-free but blocked on that missing narrative; documentation-only commit `d270828` added it and, in doing so, independently caught and corrected a factual error in the rework instructions (`b63bc6d` is `T64`'s authorization commit, not `T65`'s — the real one is `095ac91`); a second independent QA pass then re-verified the batch end to end. **QA Decision: Approved** (plain) — 23/23 targeted tests (unit + integration + the `TestRequirePermission` regression), 481/481 full suite, `ruff`/`black` clean, boot smoke passed, `app.openapi()["paths"]` unchanged (no route added) — committed as `9ac7191` **before** PR #41 merged, continuing `T63`'s pre-merge-QA-Decision discipline. One disclosed, unrelated environment issue: a stale `.env` `DATABASE_URL` port versus the actually-running Postgres container, corrected locally via an environment-variable override only, no project file changed. **Authorization: commit `095ac91`, PR #40, merge `61e64d3`. Implementation: feature commit `fab38e3`, documentation-correction commit `d270828`, QA-approval commit `9ac7191`, PR #41, merge `d91d00c`.** `main`/`origin/main` both independently verified at `d91d00c`; `git diff 61e64d3..d91d00c --name-only` confirms exactly the six files this batch's own scope covers (five implementation files plus `Phase3.md`), no forbidden file touched. See `docs/ImplementationLog/Stage3/Phase3.md`'s T65 batch, including its QA Decision and Post-Merge Verification note.) | S | T58, T54 |

#### Phase 4 — Data: seed & bootstrap

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T66 | New migration seeding `role_permissions` — map the 18 existing permissions to the 6 existing roles against the owner-approved matrix. **Authorized by the project owner, 2026-08-17, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope: exact matrix sign-off: Administrator (all 18 permissions); Advocate (`matters:read`, `matters:write`, `matters:delete`; `clients:read`, `clients:write`, `clients:delete`; `properties:read`, `properties:write`, `properties:delete`; `documents:read`, `documents:write`, `documents:delete`; `financial:read`; `reports:read`); Paralegal (`matters:read`, `matters:write`; `clients:read`, `clients:write`; `properties:read`, `properties:write`; `documents:read`, `documents:write`; `financial:read`; `reports:read` — explicitly no delete permissions and no `financial:write`, superseding any previously ambiguous wording); Clerk (`matters:read`, `matters:write`; `clients:read`, `clients:write`; `documents:read`, `documents:write`); Accountant (`financial:read`, `financial:write`; `matters:read`; `clients:read`; `reports:read`); Read Only (every `:read` permission). T66 must independently verify exactly one Alembic head after the migration. T67 remains not authorized. **Done** (2026-08-17 — a new migration seeds exactly 59 authorized `role_permission` associations against the owner-approved matrix above, UUIDs dynamically resolved from the existing `roles`/`permissions` rows, not hardcoded; downgrade removes only the T66-created associations and preserves any unrelated ones; exactly one Alembic head (`224b650e5235`) confirmed after the migration. Exhaustive matrix-validation tests added; `T63`/`T65` regression behavior confirmed preserved. `ruff`/`black` clean. **Governance history, preserved not collapsed:** the initial QA review returned substantive rework findings (resolved in a follow-up commit), followed by a formatting correction, before the final QA pass. **QA Decision: Approved** (plain) — rendered pre-merge, directly against PR #44, recorded in `docs/ImplementationLog/Stage4/Phase0.md`'s `QA Decision — T66 batch` section. **Authorization: commit `66f94bf`, PR #43, merge `81bf99f`. Implementation: commit `533226d`; QA-rework commit `b2b86b6`; formatting-correction commit `0239d80`; QA-approval commit `5ab88a5`, committed before PR #44 merged; PR #44, merge `2edc23e`.** `main`/`origin/main` both verified at `2edc23e`. See `docs/ImplementationLog/Stage4/Phase0.md`'s T66 batch, including its QA Decision and Post-Merge Verification section.) | S | T45 |
| T67 | First-admin bootstrap: one-time CLI command, interactive password prompt (`getpass` or equivalent — never argv/env/a config file) per approved D4. **Authorized by the project owner, 2026-08-17, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope, per this row and `ADR-0018`'s D4: a one-time CLI command, registered via `backend/pyproject.toml`'s `[project.scripts]` (no such section exists yet — this task adds it), placed wherever fits this codebase's existing layout (e.g. `infrastructure/cli/bootstrap.py`). Checks whether any `User` row already exists in the database; if none exists, interactively prompts for an email and a password via `getpass` (never argv, an environment variable, or a config file); hashes the password using the existing `hash_password()` (T46); creates exactly one `User`, assigned the `Administrator` role. **Idempotent:** running it again once a user already exists prints a clear message and exits cleanly — no error, no second admin created. Includes tests. `T68` (seed-count/bootstrap-idempotency test coverage, depends on this task) remains **explicitly out of scope and unauthorized** — not to be implemented as part of this batch. No change to any existing route, schema, `deps.py`, `AuthService`, or any `T52`–`T66` file beyond the new CLI module and `pyproject.toml`'s new `[project.scripts]` entry. **Implemented and QA-approved** (2026-08-17 — `backend/src/app/infrastructure/cli/bootstrap.py` (new): `run_bootstrap(session, *, email, password)` is the testable core — no-op if any `User` row already exists; otherwise looks up the seeded `Administrator` role by name, creates the `User` via `hash_password()` (`T46`), assigns the role via `UserRole` with `assigned_by=user.id` (self-attributed — no other actor exists at bootstrap time), `flush()`es only, never commits (the caller owns the transaction boundary). `main()`/`_async_main()` is the interactive entry point: checks for an existing user before prompting, reads the email via `input()` and the password via `getpass.getpass()` — never `argv`/an environment variable/a config file, genuinely satisfying `ADR-0018`'s D4 — then commits on success. New `backend/pyproject.toml` `[project.scripts]` entry: `bootstrap-admin = "app.infrastructure.cli.bootstrap:main"` (the section didn't exist before this batch, exactly as the approved scope anticipated). 5 new integration tests in `backend/tests/integration/test_bootstrap_admin.py`, against the real migrated schema via the shared `db_session` fixture: admin created with a genuinely hashed (never plaintext-equal) password, `Administrator` role assigned, exactly one `User` row created; with an existing user, `run_bootstrap()` returns `None` without creating a duplicate and leaves the pre-existing row unmodified. Full suite **487/487 passing (482 prior + 5 new)** — this batch's QA review disclosed a previously-undiagnosed +1 baseline drift (`PROJECT_STATE.json`'s last-recorded count was 481; the actual pre-`T67` baseline was 482) — reconciled in `PROJECT_STATE.json`, not silently absorbed. `ruff`/`black` clean. **QA Decision: Approved with comments** — rendered against feature commit `b409f78` (`feature/stage4-t67-first-admin-bootstrap`), independently re-verified, not taken on the Developer's word: `D4` compliance confirmed by reading the file directly (no `sys.argv`/`os.environ`/config-file access anywhere); idempotency genuinely proven at the `run_bootstrap()` level by two non-vacuous tests; `git diff main...feature/stage4-t67-first-admin-bootstrap --stat` independently confirms exactly five files changed — no route, schema, `deps.py`, `AuthService`, or `T52`–`T66` file touched, `T68` not implemented. Two non-blocking comments, not rework: (1) `run_bootstrap()` hand-rolls user/role-assignment persistence instead of reusing `SqlAlchemyUserRepository.assign_role()` — functionally immaterial here (bootstrap always operates on a brand-new `user_id`, so no `(user_id, role_id)` collision is possible) but a real, minor divergence from this codebase's repository-layer convention for user/role mutations; (2) the missing-`Administrator`-role `RuntimeError` guard has zero test coverage. Authorization commit `119d612` (2026-08-17, PR #46, merged `65b737a`) precedes implementation commit `b409f78` — confirmed by commit order. **`T67` is now Done — merged.** Feature commit `b409f78`, QA-approval commit `790b778`, PR #47, merge commit `fc0b142` (2026-08-18, parents `65b737a` and `a73d1c5`) — `main`/`origin/main` both independently re-verified at `fc0b142` this session via `git log`/`git show` and `gh pr view 47` (state `MERGED`), not taken on faith. Full suite **487/487 passing, personally re-run against merged `main` with live Postgres this session** (482 prior + 5 new); `ruff`/`black` clean (204 files unchanged); boot smoke test passed; `app.openapi()["paths"]` confirmed unchanged — still exactly the eleven routes `T63` established, since `T67` adds a CLI entry point, not a route; `backend/pyproject.toml`'s `[project.scripts]` `bootstrap-admin` entry independently confirmed present. See `docs/ImplementationLog/Stage4/Phase0.md`'s T67 batch, including its `QA Decision — T67 batch` section, for full detail. | S | T46, T62 |
| T68 | Tests: seed row counts match the approved matrix; bootstrap creates exactly one admin and is idempotent on re-run (doesn't create a second one, doesn't error). **Authorized by the project owner, 2026-08-18, recorded here — as its own documentation-only commit — before any implementation exists.** **Scope narrowed to what a direct pre-authorization check found genuinely missing — not the task's full one-line description, and not re-testing what's already proven:** (1) **Already fully satisfied, not re-authorized:** `backend/tests/integration/test_t66_role_permissions.py::test_t66_role_permissions_matrix_exact_match` already asserts the seeded `role_permissions` table has exactly 59 associations, no duplicates, and an exact role-by-role match against the full 6-role/59-entry approved matrix — confirmed by direct read, non-vacuous, already passing on `main`. No new test is authorized for this part. (2) **Genuinely missing, authorized:** no existing test exercises `infrastructure/cli/bootstrap.py`'s actual entry point (`main()`/`_async_main()`) — `test_bootstrap_admin.py`'s own docstring confirms it deliberately tests only `run_bootstrap()`, the in-memory core, not the process-level wrapper; this is the exact gap T67's QA Decision named as a non-blocking comment, still open. Approved scope for this part only: a new test (or test class, same file or a new one) that mocks `input()`/`getpass()` (patched at `app.infrastructure.cli.bootstrap.getpass`, matching how the module imports it) and `get_session_factory()` (patched to yield the test's own `db_session`-backed session, mirroring `get_db`-override patterns already established elsewhere in this codebase's integration tests) to invoke `_async_main()`/`main()` directly — covering: a first invocation with no existing user creates the admin and actually commits (not just flushes); a second invocation, or an invocation when a user already exists, prints the "already exists" message, does not prompt for credentials it would discard, and does not create a duplicate user. No production code changes are authorized or expected — `bootstrap.py`, `run_bootstrap()`, and every other `T52`–`T67` file remain unmodified; this is test-file-only work. No migration, no route, no schema change. **Implemented and QA-approved** (2026-08-18 — `backend/tests/integration/test_bootstrap_admin.py` extended with two new test classes exercising `_async_main()` directly, not `main()` — `main()`'s only addition beyond `_async_main()` is `asyncio.run(...)`, which cannot be called from inside an already-running event loop, and every `asyncio_mode = auto` async test function in this suite runs inside one. `TestAsyncMainNoExistingUser` (2 tests): with zero existing users, `_async_main()` is invoked with `input()`/`getpass()` mocked; the created row and its `Administrator` role assignment are each verified through a **second, independent** engine/connection — not `db_session` — proving `session.commit()` genuinely ran, since a same-session read can't distinguish "committed" from "merely flushed." `TestAsyncMainExistingUser` (1 test): with one existing user, `_async_main()` is invoked with `input()`/`getpass()` mocked as uncalled `MagicMock`s; asserts both are never called, the "already exists" message is printed, and the user count stays at exactly one. Three new test-file-local helpers: `_FakeSessionFactory`/`_install_fake_session_factory()` (mirrors `get_db`-override, handing `_async_main()` the test's own `db_session`) and `_fetch_and_delete_committed_user()` (a throwaway second connection that reads back, then `finally`-cleans up, the row a real `commit()` leaves behind — since `db_session`'s own rollback can't undo it). `bootstrap.py` is byte-for-byte unchanged; the 5 pre-existing `T67` tests are untouched. Full suite **490/490 passing (487 prior + 3 new)**, `ruff`/`black` clean (204 files unchanged; one `UP037` finding and one formatting reflow were caught and fixed during this batch, not left for QA). Database hygiene independently verified: a direct `psql` user count returned `0` both before and after the full suite ran, confirming the two committing tests clean up after themselves. **QA Decision: Approved** (plain, no comments) — rendered against feature commit `33c728b` (`feature/stage4-t68-bootstrap-entrypoint-tests`), independently re-verified, not taken on the Developer's word: `git diff main...feature/stage4-t68-bootstrap-entrypoint-tests --stat` confirms exactly two files changed (the test file and the phase log), and a diff scoped to `backend/src/` returns nothing — `bootstrap.py` genuinely untouched. QA went further than the Developer's own disclosed limitation and ran a mutation test: `session.commit()` was temporarily removed from `bootstrap.py`'s `_async_main()`, the two "actually commits" tests were re-run and both failed exactly as expected, the change was reverted (`git diff --stat` on `bootstrap.py` confirmed zero diff afterward), and the full suite (490/490) plus a direct `psql` user count (0) were re-verified clean post-revert — proving the new tests are genuinely non-vacuous, not merely plausible by construction. Authorization commit `d6b6b45` (2026-08-18, PR #49, merged `5bca735`) precedes implementation commit `33c728b` — confirmed by commit order. **`T68` is now Done — merged.** Feature commit `33c728b`, QA-approval commit `5b5c9b9`, PR #50, merge commit `43aa0a7` (2026-08-18, parents `5bca735` and `1ced5f2`) — `main`/`origin/main` both independently re-verified at `43c8ddb` this session via `git log`/`git show` and `gh pr view 50` (state `MERGED`), not taken on faith (an unrelated documentation merge, PR #51, landed on top of `43aa0a7` and doesn't touch any `T68` file). Full suite **490/490 passing, personally re-run against merged `main` with live Postgres this session**; `ruff`/`black` clean (204 files unchanged); boot smoke test passed; `app.openapi()["paths"]` confirmed unchanged — still exactly the eleven routes `T63` established, since `T68` is test-file-only. **Stage 4 Phase 0 (`T66`–`T68`) is now complete in full and merged.** See `docs/ImplementationLog/Stage4/Phase0.md`'s T68 batch, including its `QA Decision — T68 batch` section, for full detail.) | S | T66, T67 |

#### Phase 5 — Frontend

| ID | Task | Complexity | Depends on |
|---|---|---|---|
| T69 | `post`/`put`/`delete` added to `httpClient.ts` (closes Stage 2.5's F10 — now actually needed, since login is a `POST`), parsing the backend's structured `{"error":{"code","message"}}` body. **Authorized by the project owner, 2026-08-18, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope: `post`/`put`/`delete` methods added to `frontend/src/infrastructure/api/httpClient.ts` alongside the existing `get()`; `HttpError` extended to carry the backend's structured error code/message when the response body matches `{"error":{"code": ..., "message": ...}}`, falling back to the current generic `Request to <path> failed with status <status>` message only when the response body doesn't match that shape. Confirmed directly before this authorization: `httpClient.ts` currently has only `get()`, and every non-OK response throws the generic message regardless of the response body's actual contents. This is frontend/TypeScript work — to be implemented in a separate Frontend Developer chat, not the Backend Developer role used for `T58`–`T68`. `T70`–`T76` remain explicitly out of scope and unauthorized. **Implemented and QA-approved** (2026-08-18 — `frontend/src/infrastructure/api/httpClient.ts` gained `post`/`put`/`delete` alongside the existing `get()`, sharing a new `requestWithBody()` helper (method passed straight through to `fetch`'s `init.method`; body `JSON.stringify()`-serialized only when `body !== undefined`, so `delete()`'s no-body call never sends the string `"undefined"`); `HttpError` gained an optional `code?: string`, populated by a new `buildHttpError()` when the response body matches the approved `{"error":{"code","message"}}` shape via a strict type-guard, `isStructuredErrorBody()` (rejects `error: null`, non-string `code`/`message`, or a non-object body), falling back to the existing generic `Request to <path> failed with status <status>` message on any mismatch or an unparseable body (`response.json()` wrapped in `try`/`catch`, never an unhandled rejection). `get()` and `request<T>()`'s success path are byte-for-byte unchanged. 8 new tests in a new `httpClient.test.ts` (the four verbs' method/body serialization, plus four error-parsing cases: structured body, non-matching body, unparseable body, non-object JSON body) — full suite **17/17 passing** (9 prior + 8 new), `eslint` 0 errors (3 pre-existing warnings, all in unrelated files), `prettier --check` clean. **QA Decision: Approved** (plain, no comments) — rendered against feature commit `cca729f` (`feature/stage4-t69-http-client-methods`), independently re-verified, not taken on the Developer's word: `git diff main...feature/stage4-t69-http-client-methods --name-only` confirms exactly three files changed (`httpClient.ts`, `httpClient.test.ts`, `docs/ImplementationLog/Stage4/Phase1.md`); tests/lint/format independently re-run, not taken on the reported counts; the HTTP-method/body-serialization and structured-error-validation logic read directly, not assumed. One non-blocking observation, already disclosed by the Developer and re-confirmed, not a new finding: `delete()`'s success path still calls `response.json()` unconditionally, inherited unchanged from `request<T>()`, which would throw on a real `204 No Content` response — correctly out of scope, since no caller of `delete()` exists yet (`T70`+ is unauthorized). Authorization commit `cf7a570` (`PROJECT_STATE.json` sync `0a9ad12`, PR #52, merged `5abceee`) precedes implementation commit `cca729f` — confirmed by commit order. See `docs/ImplementationLog/Stage4/Phase1.md`'s T69 batch, including its `QA Decision — T69 batch` section, for full detail. **`T69` is now Done — merged.** Merged: PR #54, feature commit `cca729f`, QA-approval commit `6b90ede`, documentation-synchronization commit `79af7ac`, merge `5196fdf` (2026-08-18, parents `b544135` and `79af7ac`) — `main`/`origin/main` both independently verified at `5196fdf` this session via `git log`/`git show`/`gh pr view 54` (state `MERGED`), not taken on faith. `git show --stat 5196fdf` confirms the file set matches this batch plus its own documentation sync exactly — no backend file touched. Frontend suite **17/17 passing**, `eslint`/`prettier` clean, personally re-run against merged `main` this session, not carried over from the pre-merge figure. **Stage 4 Phase 5 (`T69`) is complete in full.** See `docs/ImplementationLog/Stage4/Phase1.md`'s Post-Merge Verification — T69 batch section for full detail. | S | — |
| T70 | Auth state management — a React context/provider holding the current user + tokens, `login()`/`logout()` actions. **Authorized by the project owner, 2026-08-19, recorded here — as its own documentation-only commit — before any implementation exists.** Approved scope: new `frontend/src/app/providers/AuthProvider.tsx` — an `AuthContext`/`AuthProvider` matching the existing `ThemeProvider.tsx`/`NotificationProvider.tsx` pattern (`createContext`/`useContext`/custom hook); state holds `currentUser` (`id`, `display_name`, `roles`) and `tokens` (access, refresh), in React memory only — no persistence (`T71` owns that). `login(email, password)` calls `httpClient.post("/api/v1/auth/login", { email, password })` for the token pair, then a one-off `httpClient.get("/api/v1/auth/me", { headers: { Authorization: \`Bearer ${access_token}\` } })` to populate `currentUser` — reading the result from the `ApiResponse<MeResponse>` envelope's `.data` field (`response.data.id`/`.display_name`/`.roles`), since `/me` is wrapped unlike `/login`/`/refresh`/`/logout`. `logout()` calls the existing, unmodified `httpClient.post("/api/v1/auth/logout", { refresh_token })` signature, then clears context state. Exposes a `useAuth()` hook. New `frontend/src/domain/types/auth.ts` — `CurrentUser`/`LoginCredentials`/`AuthTokens` interfaces, alongside the existing `health.ts`/`result.ts` in that directory. Modify `frontend/src/app/providers/AppProviders.tsx` — adds `<AuthProvider>` into the existing `ErrorBoundary` → `ThemeProvider` → `NotificationProvider` composition. Modify `frontend/src/infrastructure/api/httpClient.ts` — adds an optional `headers` parameter to `httpClient.get()` ONLY, for the one-off `/me` call's `Authorization` header; `post()`/`put()`/`delete()` remain unmodified, since `/login`, `/refresh`, and `/logout` all take their credentials/token in the JSON body per the actual route contracts, not a bearer header. No UI (`T72`, `T75`), no routing/redirect (`T73`), no global header injection or 401 handling (`T74`), no persistent storage (`T71`), no automated tests (`T76` owns test coverage for `T70`–`T75`) — verification for this batch is manual/local only. No change to any `T52`–`T69` file beyond the two modifications named above. **Implemented and QA-approved.** Original QA Decision (commit `6493408`): Rework required, process grounds only -- a named governance finding (approval-checkpoint skipped between authorization `2cf052c` and implementation `da29014`, 5 seconds apart, 2026-08-19), plus a `prettier --check` failure on 3 files. Rework closed same day: commit `d54b0a3` ran `prettier --write` on exactly those 3 files -- confirmed formatting-only, zero semantic change. QA Re-Review (commit `d5cba34`): **Approved with comments** -- 17/17 tests passing, `eslint` 0 errors/4 warnings, `prettier --check` clean. Sole comment, non-blocking: `httpClient.ts`'s `request<T>()` success path calls `response.json()` unconditionally on any 2xx response, so `logout()`'s first real call to `POST /api/v1/auth/logout` (returns `204`) deterministically throws and is masked by `AuthProvider.tsx`'s own `try`/`catch`, misreporting a successful logout as a console error client-side -- confirmed out of `T70`'s authorized scope and explicitly carried forward to `T74`/`T76`. The approval-checkpoint governance finding remains on permanent record, not resolved by the rework. **`T70` is now Done -- merged.** Merged: PR #58, feature commit `da29014`, QA-Rework-required commit `6493408`, rework-fix commit `d54b0a3`, QA-Re-Review-approval commit `d5cba34`, documentation-synchronization commit `0ac5f1b`, merge `551e900` (2026-08-19 11:20:33 +0530, parents `4198568` and `0ac5f1b`) -- main/origin/main both independently verified at `551e900` this session via `git log`/`git show`, not taken on faith (no live `gh` access from this session's environment -- disclosed, not assumed). `git diff 0ac5f1b 551e900 --stat` is empty, confirming the merge commit's tree is byte-identical to the feature branch tip. `git show --stat 551e900` confirms exactly the seven files the QA re-review's own accounting named -- no scope creep. Frontend suite NOT independently re-run this session (this device-bridge environment's vitest/rolldown native binding is broken, a known pre-existing environment quirk, not a code defect; `eslint`/`prettier --check` both timed out) -- the QA re-review's own pre-merge figures are carried forward here, disclosed rather than assumed. **Stage 4 Phase 2 (`T70`) is complete in full.** See `docs/ImplementationLog/Stage4/Phase2.md`'s Post-Merge Verification -- T70 batch section for full detail. | M | T69 |
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
complete and approved (`docs/reviews/PreStageChecklist_Stage3_2026-08-07.md`). Phase 1 (`T46`–`T51`)
is complete (`docs/ImplementationLog/Stage3/Phase1.md`, QA Decision: Approved with comments).
**Phase 2 is under way: `T52` (`JwtAuthenticationProvider`) is Done** — implemented, technically
verified, merged (356/356 full suite, ruff/black clean, PR #9/`baed936`), and its process-gate QA
Decision (Approved with comments) is now recorded in-repository
(`docs/ImplementationLog/Stage3/Phase2.md`, Status: Done). **`T53` (`RbacAuthorizationService`) is
also Done** — QA Decision: Approved with comments (code/tests approved on the merits, 369/369 full
suite; four process/governance deviations named — authorization not pre-recorded, Backend Developer
approval checkpoint skipped, implemented directly on `main`, consequently uncommitted). The git-action
deviations have since closed: merged via PR #10, commit `dd754f5`, merge `a103dca` — `main`/`origin/main`
both verified at `a103dca`. The authorization-recording and approval-checkpoint deviations remain on
record as governance history in `docs/ImplementationLog/Stage3/Phase2.md`'s T53 batch, Problems
Encountered — not erased by this closeout. **`T54` (`RequirePermission`) is also Done** — original
QA Decision (2026-08-08): Rework required, process grounds only, preserved verbatim; follow-up QA
Decision (2026-08-10): Approved with comments, once the branch/commit/PR gap closed (PR #12, feature
commit `dbd6724`, merged `6396f6b`). Authorization not pre-recorded remains an open governance
finding, not erased; the Backend Developer approval checkpoint *was* performed and approved for
`T54`, unlike `T53` — see `Phase2.md`'s T54 batch. **`T55` is authorized, conversationally, by the
project owner (2026-08-10).**

**Correction (2026-08-10, same day, after QA review):** the two sentences above previously claimed
this authorization was "recorded here … before any implementation began, breaking the pattern
`T52`/`T53`/`T54` each demonstrated." **That claim is inaccurate and is corrected here, not silently
edited away:** the committed `HEAD` at the time this file was last committed still read `T55` as "not
started, not authorized," and nothing about this authorization — original, clarified, or expanded —
was ever committed before `T55`'s implementation existed. The pattern was **not** broken; it
recurred a **fourth** time (`T52`, `T53`, `T54`, `T55`). This is a permanent governance finding, the
same category as `T52`/`T53`/`T54`'s own authorization-recording gaps, and it cannot be retroactively
fixed by rewording it — only disclosed accurately, which is what this correction does.

**`T55` architectural scope clarification and expanded authorization (also 2026-08-10, also
conversational):** the Backend Developer role performed its
`docs/prompts/BackendDeveloper.md` §5 approval checkpoint against `T55`'s original authorization
("replace the two `container.register(...)` registrations in `configure_container()`") and found that
literal wording technically unworkable, not merely inconvenient — `container.resolve()` is
synchronous and zero-argument, but `JwtAuthenticationProvider` needs a request-scoped `UserRepository`
backed by the current request's `AsyncSession` (`DBSessionDep`), and `RbacAuthorizationService` needs
an asynchronously-loaded `permission_codes_by_role_name` mapping from that same request's session. The
container has no mechanism to inject a request-bound `AsyncSession` into a synchronous factory; opening
a separate database session or freezing a startup-time snapshot would both be architecturally
incorrect (the same request-scoped-construction constraint `docs/ImplementationLog/Stage3/Phase2.md`
already flagged for both `AuthService`/`T50` and `RequirePermission`/`T54`). The Backend Developer
correctly stopped rather than implementing the literal wording or silently reinterpreting it.

**The project owner, in this same session, authorizes the following expanded `T55` scope — additive
to the original authorization, not a redefinition of it (the original text above is preserved
verbatim as the historical record of what was first approved):**

- Request-scoped construction via FastAPI `Depends()` in `presentation/api/deps.py`, through the
  existing `DBSessionDep`, replacing (not supplementing) the literal `configure_container()`
  registration approach the original authorization named:
  - Authentication chain: `DBSessionDep` → `SqlAlchemyUserRepository(session)` →
    `JwtAuthenticationProvider(user_repository, settings)`.
  - Authorization chain: `DBSessionDep` → `SqlAlchemyRolePermissionRepository(session)` →
    `await get_permission_codes_by_role_name()` → `RbacAuthorizationService(permission_codes_by_role_name)`.
- The RBAC permission mapping is loaded **fresh on every request** — no caching/invalidation policy
  is authorized as part of `T55`; the existing `Cache` abstraction has no real callers and no
  approved permission-cache policy, and none is being approved here either.
- The existing `AuthenticationProvider`/`AuthorizationService` container registrations
  (`Anonymous`/`Permissive` defaults) may be **removed only if direct repository inspection confirms
  they are no longer referenced anywhere else** — if still required elsewhere, they must be preserved
  and that reason documented, not silently dropped.
- Tests must verify the real request-scoped construction chain, including database-backed
  integration coverage where appropriate — not just the same unit-level shape `T52`/`T53`/`T54`'s
  tests already used.

**Explicitly still out of scope, unchanged by this expansion:** `T52`, `T53`, and `T54`'s own
implementation files; `T56`; `T57`; any route; any unrelated refactoring.

**`T55` is now Done** (closed out 2026-08-10 — request-scoped `Depends()` construction in
`presentation/api/deps.py`, obsolete container registrations removed; 6 new integration tests, full
suite 380/380 passing, ruff/black clean, request-scoped session usage independently verified, no
scope creep — see `docs/ImplementationLog/Stage3/Phase2.md`'s T55 batch). **QA Decision:** original
`Rework required` — governance/process grounds only (the authorization-recording gap above; no
technical issue) — preserved verbatim; follow-up `Approved with comments` is the final disposition,
rendered once `feature/stage3-t55-auth-wiring` → PR #15 → merged `b094436` closed the branch/
commit/PR gap. `main`/`origin/main` both verified at `b094436`. The authorization-recording finding
itself is **not** resolved by this closeout — it is permanent governance history (a fourth
consecutive occurrence, `T52`/`T53`/`T54`/`T55`), not erased.

**`T56` is Done** (closed out 2026-08-12 — see `docs/ImplementationLog/Stage3/Phase2.md`'s T56 batch:
`get_bearer_token()`/`get_current_user()` in `presentation/api/deps.py`, 3 new tests, full suite
383/383 passing, ruff/black clean, boot smoke test passed, Postgres-backed verification completed;
merged PR #18, feature commit `fcc68e0`, merge `d69c4eb`). **QA Decision: Approved with comments** —
no technical defects; the comment is a non-blocking future observation about adding an end-to-end
`TestClient`-level bearer-token test once a real protected route exists (`T58`+), not a gap in `T56`
itself. **`T56` is the first Stage 3 Phase 2 batch where authorization was actually recorded in the
repository (`91e0785`, PR #17, merged `89a3a5e`) before implementation began** — confirmed directly
by commit timestamp order, breaking the pattern `T52`/`T53`/`T54`/`T55` each demonstrated; those four
prior findings remain on record above, unerased, since this one batch getting it right doesn't
retroactively fix them.

**`T57` is Done** (closed out 2026-08-13 — see `docs/ImplementationLog/Stage3/Phase2.md`'s T57 batch:
`RequirePermission`'s `_require_permission` now raises `UnauthorizedError`/401 for an unauthenticated
caller before `AuthorizationService` is even consulted, closing the 401/403 gap; `ForbiddenError`/403
for an authenticated-but-unpermitted caller is unchanged. 3 new tests + 1 updated, full suite 386/386
passing, ruff/black clean, boot smoke test passed, 127/127 integration tests against live Postgres
per PR #20; merged PR #20, feature commit `7c9fc3a`, merge `472f7cb`). **QA Decision: Approved with
comments** — no technical defects; the comment preserves, as a non-blocking historical/forward-looking
observation, the already-flagged deferral of true `TestClient`-level HTTP verification (a real
request, a real bearer token, an actual `401`/`403` response) to `T58`+, since no protected route
exists yet. **`T57` is the second consecutive Stage 3 Phase 2 batch where authorization was actually
recorded in the repository (`65dd563`) before implementation began (`7c9fc3a`)** — confirmed by
commit timestamp order, extending the streak `T56` started; `T52`–`T55`'s four findings remain on
record above, unerased. **With `T57` closed, Stage 3 Phase 2 (`T52`–`T57`) is complete in full**, and
Phase 3 (routes) begins.

**`T58` is Done** (closed out 2026-08-15 — see `docs/ImplementationLog/Stage3/Phase3.md`'s T58 batch,
the first entry under Phase 3: `POST /api/v1/auth/login` — `presentation/api/v1/auth.py` (new) adds
the route plus co-located `LoginRequest`/`LoginResponse` schemas, no `ApiResponse[T]` wrapper; on
failure `AuthService.authenticate()`'s `Result.error` is raised directly, handled by the existing
global `AppError` handler; `presentation/api/deps.py` gains `get_auth_service()`/`AuthServiceDep`,
request-scoped construction mirroring `T55`'s pattern; router mounted in `router.py`. 5 new
integration tests in `tests/integration/test_auth_login.py` against a real mounted app and live
Postgres via `httpx.AsyncClient`/`ASGITransport` with a `get_db` override — `TestClient` was tried
first and rejected, since its separate event-loop thread breaks that exact override. Full suite
391/391 passing (386 prior + 5 new), ruff/black clean, boot smoke test passed; merged PR #22, feature
commit `76cd28f`, merge `e67da02`). **QA Decision: Approved with comments** — no technical defects;
two non-blocking comments preserved verbatim: (1) Starlette's `HTTP_422_UNPROCESSABLE_ENTITY`
deprecation warning is framework-internal, not a `T58` defect; (2) the test-local
`app.dependency_overrides[get_db]` pattern is safe under current sequential test execution, to be
reconsidered only if parallel test execution is introduced. **`T58` is the third consecutive Stage 3
batch where authorization was recorded in the repository (`58c8e40`, 2026-08-13) before implementation
began (`76cd28f`, 2026-08-15)** — confirmed by commit order, extending the streak `T56`/`T57` started;
`T52`–`T55`'s four findings remain on record above, unerased. `T58` is also the first route in the
project and the first task to exercise the full auth chain (`T52`–`T57`) end-to-end via a real HTTP
request.

**`T59` is Done** (closed out 2026-08-15 — see `docs/ImplementationLog/Stage3/Phase3.md`'s T59 batch:
`POST /api/v1/auth/refresh` — `presentation/api/v1/auth.py` extended with `RefreshRequest`/
`RefreshResponse` (co-located, bare, matching `login`'s convention) and `refresh()`, reusing `T58`'s
`AuthServiceDep` unchanged — no `deps.py`/`router.py` edits. `AuthService.refresh()` (`T50`/`T51`,
unmodified) already collapses invalid/expired/revoked/unknown tokens into one generic
`UnauthorizedError`; the route raises `result.error` directly, same pattern as `login`. 7 new
integration tests in `tests/integration/test_auth_refresh.py` (valid refresh, rotation prevents reuse,
invalid/expired/revoked/unknown token → 401 each, malformed body → 422), reusing `T58`'s
`httpx.AsyncClient`/`ASGITransport`/`get_db`-override pattern verbatim. Full suite 398/398 passing
(391 prior + 7 new) — personally re-run against live Postgres this session, ruff/black clean, boot
smoke test passed (`/api/v1/auth/refresh` confirmed in `app.openapi()["paths"]`); merged PR #24,
feature commit `56eb7c2`, merge `721cec5`). **QA Decision: Approved with comments** — "no technical
defects" per PR #24's own report; unlike `T58`'s PR, PR #24 does not itemize specific non-blocking
comment text beyond that phrase, recorded here exactly as given, not invented. **`T59` is the fourth
consecutive Stage 3 batch where authorization was recorded in the repository (`163085d`, 2026-08-15)
before implementation began (`56eb7c2`, 2026-08-15, ~11 minutes later same day)** — confirmed by
commit order, extending the streak `T56`/`T57`/`T58` started; `T52`–`T55`'s four findings remain on
record above, unerased. Scope check (`git show --stat 56eb7c2`) confirms exactly two files changed
(`presentation/api/v1/auth.py`, new `tests/integration/test_auth_refresh.py`) and
`app.openapi()["paths"]` shows only `login`/`refresh`/`health`/`version` — no `T60`+ (logout, `/me`,
user management) work slipped in.

**`T60` is Done** (closed out 2026-08-15 — see `docs/ImplementationLog/Stage3/Phase3.md`'s T60 batch:
`POST /api/v1/auth/logout` — `presentation/api/v1/auth.py` extended with a co-located `LogoutRequest`
and `logout()`, reusing `T58`'s `AuthServiceDep` unchanged; `deps.py`, `router.py`, and `AuthService`
itself were **not modified**, honoring the authorization's explicit "must not modify" constraint.
`AuthService.revoke()` (`T50`/`T51`, unmodified) returns `None`, never a `Result` — an unknown or
already-revoked token is a silent no-op, not a failure — so `logout()` has no error branch, unlike
`login`/`refresh`; it returns `204 No Content` with no body, mirroring
`presentation/common/crud_router_factory.py`'s `delete_item`. 5 new integration tests in
`tests/integration/test_auth_logout.py` (a valid token is actually revoked, verified against the
stored `RefreshToken` row's `revoked_at`; an already-revoked token, an unknown token, and a malformed
token string all still succeed; a malformed body → 422), reusing `T58`/`T59`'s
`httpx.AsyncClient`/`ASGITransport`/`get_db`-override pattern verbatim. Full suite 403/403 passing
(398 prior + 5 new) — personally re-run against live Postgres this session, ruff/black clean, boot
smoke test passed (`/api/v1/auth/logout` confirmed in `app.openapi()["paths"]`, alongside only
`login`/`refresh`/`health`/`version` — no `T61`+ scope creep); merged PR #26, feature commit
`5b9bf57`, merge `941ed42`). **QA Decision: Approved** — PR #26's own body states "no defects" without
the "with comments" qualifier `T58`/`T59` carried, and no comment text exists anywhere in the
repository — recorded here as a plain `Approved`, not assumed to be "with comments" just because the
two prior batches were. **`T60` is the fifth consecutive Stage 3 batch where authorization was
recorded in the repository (`726e8cf`, 2026-08-15, 11:57:59 IST) before implementation began
(`5b9bf57`, 12:05:34 IST, ~8 minutes later same day)** — confirmed by commit order, extending the
streak `T56`/`T57`/`T58`/`T59` started; `T52`–`T55`'s four findings remain on record above, unerased.
Scope check (`git show --stat 5b9bf57`) confirms exactly two files changed
(`presentation/api/v1/auth.py`, new `tests/integration/test_auth_logout.py`) and
`app.openapi()["paths"]` shows only `login`/`refresh`/`logout`/`health`/`version` — no `T61`+ (`/me`,
user management, role assignment) work slipped in. **Correction (2026-08-17, T67 documentation sync):**
this note previously read "`T61`–`T67` remain not started, not authorized," which was only accurate
at the time `T60` closed (2026-08-15) and was never updated as `T61`–`T66` completed — each of those
tasks' own row above already carries its accurate closeout detail; this stale trailing sentence simply
wasn't corrected alongside them. `T61`–`T67` are all Done and merged (see each task's own row above, including `T67`'s post-merge
closeout: PR #47, merge `fc0b142`, 2026-08-18). `T68` is also Done and merged (PR #50, merge
`43aa0a7`, 2026-08-18) — see `T68`'s own row above. Stage 4 Phase 0 (`T66`–`T68`) is now complete in
full. See
`docs/Stage3_Backend_Handoff.md` for the backend-scoped implementation brief (T41–T68). T1–T18
(Stage 2.5, minus T1–T3 now folded into T41–T43 above) remain separately pending. T38–T40
(Dependabot, PR template, issue templates) and T81 (stray README content) remain backlog-only.*
