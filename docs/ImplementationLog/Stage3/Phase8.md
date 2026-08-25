------------------------------------------------

# Stage 3 – Phase 8

Status: In Progress

Started: 2026-08-25

Completed:

Related Tasks: T7

Related ADRs: None explicitly named.

Git Commit: (pending — see PR)

Pull Request: (pending)

Release:

------------------------------------------------

## Objective

Wire `BaseService.list_page()` to accept an optional `SearchQuery` and forward it to the
repository's `list()` port, so a service built on top of `SqlAlchemyRepository` can actually use
T5's filtering and T6's sorting, while every existing caller that doesn't pass a `SearchQuery`
keeps working exactly as before.

## Tasks Implemented

- **T7** — `BaseService.list_page()` now accepts `query: SearchQuery | None = None` and forwards
  it to `self._repository.list(...)`, reusing the existing T4/T5/T6 port and implementation.

## Files Modified

`backend/src/app/application/common/base_service.py` — the only file touched (per `git diff` against
this phase's starting point, `ad7871e`): 9 insertions, 2 deletions.

- Added `from app.application.common.query import SearchQuery`.
- `list_page(self, request: PageRequest, *, query: SearchQuery | None = None) -> PageResult[T]`.
- The repository call is conditional: when `query is not None`, calls
  `self._repository.list(limit=request.limit, offset=request.offset, query=query)`; when `query`
  is `None` (the default), calls `self._repository.list(limit=request.limit, offset=request.offset)`
  — the exact call it made before this change, byte-for-byte.

## Tests Added

None. Per T7's own authorization in `IMPLEMENTATION_QUEUE.md`, T9 owns this query-framework
chain's test work — the same explicit carve-out T5 and T6 established.

## Test Results

- `cd backend && uv run pytest`: **500 passed**, 6 failed — all 6 in
  `tests/integration/test_bootstrap_admin.py`, the same pre-existing failures root-caused in T5's
  QA Decision (`docs/ImplementationLog/Stage3/Phase6.md`, a stale `users` row from an unrelated
  earlier session, T83) — mechanically unrelated to this diff.
- `cd backend && uv run ruff check src tests alembic`: all checks passed.
- `cd backend && uv run black --check src tests alembic`: all 206 files unchanged.
- `git diff --check`: clean.
- **Not part of the shipped diff, but run to self-verify correctness given no test file ships with
  this phase:** a throwaway script (session scratchpad, executed once, then deleted) built a real
  `BaseService` over a real `SqlAlchemyRepository` against a local Postgres instance and confirmed:
  the existing no-`query`-arg call path (page size/total unaffected), `query=None` explicit
  (unaffected), a filter forwarded end-to-end, a sort forwarded end-to-end, and filter+sort+
  pagination all forwarded together while `count()`/`total` remained unfiltered as designed. 7/7
  passed.

## Design Decisions

- **Compatibility discrepancy found and resolved during implementation, documented here rather than
  silently worked around:** an unconditional `self._repository.list(limit=..., offset=..., query=query)`
  call (forwarding `query=None` when omitted) broke `tests/support/in_memory_repository.py`'s
  `InMemoryRepository.list()` — a second, pre-existing `AbstractRepository` implementation (used by
  `test_base_service.py` and `test_crud_router_factory.py`) that was never updated during T4/T5/T6
  to accept the port's `query` parameter, because those tasks' authorized scope only ever named
  `SqlAlchemyRepository`. Confirmed as a genuine regression, not a pre-existing failure, by
  reproducing both tests passing cleanly against unmodified `main` via `git stash` and failing only
  with the unconditional-forwarding version of this change.
  - This was flagged to the project owner rather than resolved unilaterally, since fixing
    `tests/support/in_memory_repository.py` directly would touch a file outside T7's authorized
    scope (`application/common/base_service.py` only) — one of this task's own explicit stop
    conditions ("unrelated files must be modified").
  - **Resolution, per the project owner's explicit direction:** `list_page()` forwards `query=`
    conditionally — only when a caller actually supplies one — so the call `list_page()` makes when
    `query` is omitted is identical to what it made before this phase, for every repository
    implementation, updated or not. This still fully satisfies all six of T7's acceptance criteria:
    `SearchQuery` is forwarded via the existing port whenever one is actually given (criterion 2);
    the no-arg path is untouched (criterion 3); no new query abstraction, router wiring, tests, or
    documentation were introduced (criteria 4–6).
  - **Not fixed under T7, flagged for whoever picks it up next:** `tests/support/in_memory_repository.py`
    still does not accept `query`, so a future caller that passes a non-`None` `SearchQuery` to a
    service backed by `InMemoryRepository` (rather than `SqlAlchemyRepository`) will still hit the
    same `TypeError`. Only reachable if/when a real caller starts passing a `SearchQuery` through a
    service under test with the in-memory fake — not currently the case anywhere in the repository.
- `query` is keyword-only (`*`), matching `SearchQuery | None = None`'s placement as an addition
  alongside the existing positional `request: PageRequest`, and mirroring the keyword-only style
  already used for `AbstractRepository.list()`'s own `query` parameter.

## Problems Encountered

- See the compatibility discrepancy under Design Decisions — the one non-trivial issue this phase
  surfaced, resolved via conditional forwarding after checking with the project owner rather than
  expanding scope into `tests/support/in_memory_repository.py`.

## Deferred Work

- **T8** (wire `build_crud_router`'s `list_items` route to accept `sort`/`filter` query params and
  assemble a `SearchQuery`) — depends on T7, now complete; still a separate, unauthorized task.
- **T9** (repository-level filter/sort tests against real Postgres, `BaseService.list_page()` unit
  tests with a fake repository, `test_crud_router_factory.py` extension) — depends on T5+T6+T7+T8;
  explicitly excluded from T7's own scope. Trigger condition: once T8 also lands. A future T9 pass
  should decide whether `tests/support/in_memory_repository.py` needs updating as part of adding
  `BaseService.list_page()` unit test coverage for the `query` parameter.
- **T10** (update `docs/Architecture.md`'s query-framework note) — depends on T9.
- `tests/support/in_memory_repository.py`'s missing `query` parameter (see Design Decisions) — not
  fixed here; a candidate for T9 (since it's test-support infrastructure) or a small, separately
  authorized task if the project owner wants it addressed sooner.
- T4's still-missing `ImplementationLog` entry (flagged in T5's and T6's phase logs, unresolved) —
  remains out of T7's authorized scope too.

## Future Considerations

- T8 is now fully dependency-satisfied (T5, T6, T7 all complete) — whoever implements it can wire
  `build_crud_router`'s `list_items` route to assemble and pass a `SearchQuery` through
  `list_page()` without further prerequisites.
- Whoever implements T8 should be aware that `list_page(query=...)` only works today against a
  `SqlAlchemyRepository`-backed service — any `build_crud_router` test wiring that uses
  `InMemoryRepository` (as `test_crud_router_factory.py` already does) will need
  `tests/support/in_memory_repository.py` updated first, or will need to keep exercising only the
  no-`query` path.

Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added — correctly none: T9 explicitly and separately owns test authorship for this task,
  per T7's own authorization text (same carve-out T5/T6 established).
☑ Existing tests pass
□ Documentation updated — correctly none: T10 explicitly owns the `docs/Architecture.md`
  query-framework note update, and depends on T9, not T7.
□ ADR updated (if required) — no architectural decision this phase; correctly none written.
□ AI_BOOTSTRAP updated (if required) — not required; no bootstrap-level rule affected.
□ PROJECT_STATE updated (if required) — Documentation Manager's role, not this one, and only after
  a QA Decision exists.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

QA Decision

□ Approved
□ Approved with comments
□ Rework required
