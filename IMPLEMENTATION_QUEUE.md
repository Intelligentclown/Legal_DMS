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

**Status:** Findings reviewed and classified below. No code has been changed. Pending approval
before either "Fix Immediately" task is started.

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

*Awaiting project-owner approval before any task in this file is started — both the T1–T18 Stage
2.5 hardening backlog and the T20–T21 QA-review fixes above.*
