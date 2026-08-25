------------------------------------------------

# Stage 3 – Phase 9

Status: In Progress

Started: 2026-08-25

Completed:

Related Tasks: T8

Related ADRs: None explicitly named.

Git Commit: (pending — see PR)

Pull Request: (pending)

Release:

------------------------------------------------

## Objective

Wire `build_crud_router`'s `list_items` route to accept optional `sort`/`filter` query
parameters, assemble them into a `SearchQuery` using the existing `query.py` abstractions, and
forward that query through T7's existing `BaseService.list_page()` wiring — completing the
query-string-to-repository path for the test-only CRUD router factory.

## Tasks Implemented

- **T8** — `list_items` now accepts repeatable `sort` and `filter` query parameters, parses each
  into a `SortSpec`/`FilterSpec` via two small module-level helpers, assembles them into a
  `SearchQuery` only when at least one is supplied, and forwards it to `service.list_page(request,
  query=search_query)`.

## Files Modified

`backend/src/app/presentation/common/crud_router_factory.py` — the only file touched (per `git
diff --stat` against this phase's starting point, `647363a`): 39 insertions, 2 deletions.

- Added `_parse_sort_param(raw: str) -> SortSpec`: splits `"field"` or `"field:direction"` on the
  first `:`, defaulting to `SortSpec`'s own default direction (`ASC`) when no direction is given.
- Added `_parse_filter_param(raw: str) -> FilterSpec`: splits `"field:operator:value"` on `:`
  (max 2 splits, so a value may itself contain `:`), maps the operator string to `FilterOperator`,
  and splits the value on `,` into a list only for the `IN` operator (so `filter=status:in:a,b,c`
  produces `FilterSpec(value=["a", "b", "c"])` for `FilterOperator.IN.in_()`-style membership).
- Added `_build_search_query(sort, filters) -> SearchQuery | None`: returns `None` when both are
  empty/omitted, otherwise a `SearchQuery` with the parsed `sort`/`filters` tuples.
- `list_items` gained two new optional parameters: `sort: list[str] | None = Query(default=None)`
  and `filters: list[str] | None = Query(default=None, alias="filter")` — Python name `filters`
  avoids shadowing the `filter` builtin while the actual query-string key stays `filter`, matching
  T8's own "filter" wording.
- The route builds `search_query = _build_search_query(sort=sort, filters=filters)` and calls
  `service.list_page(request, query=search_query)` when it's not `None`, else
  `service.list_page(request)` — mirroring T7's own conditional-forwarding pattern exactly, so the
  no-params path makes the identical call it made before this phase.
- `page`/`page_size` handling, `PageRequest` construction, and the response-shaping code below are
  untouched.

## Tests Added

None. Per T8's own authorization in `IMPLEMENTATION_QUEUE.md`, T9 owns this query-framework
chain's test work — the same explicit carve-out T5, T6, and T7 established.

## Test Results

- `cd backend && uv run pytest`: **500 passed**, 6 failed — all 6 in
  `tests/integration/test_bootstrap_admin.py`, the same pre-existing failures already root-caused
  in T5's QA Decision (`docs/ImplementationLog/Stage3/Phase6.md`, a stale `users` row from an
  unrelated earlier session, T83) — mechanically unrelated to this diff.
- `cd backend && uv run ruff check src tests alembic`: all checks passed.
- `cd backend && uv run black --check src tests alembic`: all 206 files unchanged (after running
  `black` once directly on the modified file — see Problems Encountered).
- `git diff --check`: clean.
- **Not part of the shipped diff, but run to self-verify correctness given no test file ships with
  this phase:** a throwaway script (session scratchpad, executed, then deleted) built a real
  throwaway `FastAPI()` app — never mounted into the real app, same pattern
  `tests/integration/test_crud_router_factory.py` already uses — wired with `build_crud_router`
  over a real `SqlAlchemyRepository`/`BaseService` against local Postgres, driven via a real
  `TestClient`. Verified: no query params (existing page/page_size behavior, byte-identical
  response shape), filter only, sort only, filter+sort together, multiple `sort` params preserving
  precedence (primary ascending, secondary descending as a tiebreaker), the `IN` operator with a
  comma-separated value, pagination still correctly applied on top of filter+sort with `total`
  remaining unfiltered, and the documented raw-string-value limitation (see Design Decisions),
  confirmed in isolation at the repository layer. 11/11 passed.

## Design Decisions

- **Query-string encoding chosen (no existing precedent in the codebase to follow — confirmed by
  search):** `sort=field` or `sort=field:direction` (repeatable for multi-field precedence, applied
  in the order received, matching `SearchQuery.sort`'s tuple-order semantics already established by
  T6); `filter=field:operator:value` (repeatable, ANDed together, matching T5's existing AND-only
  semantics), with `operator` matching `FilterOperator`'s own string values (`eq`, `neq`, `gt`,
  `gte`, `lt`, `lte`, `contains`, `in`) and `value` split on `,` only for `in`. This is the smallest
  representation that maps directly onto the existing `SortSpec`/`FilterSpec` fields with no
  invented intermediate model — parsing a query string into `SearchQuery` unavoidably requires
  *some* string encoding, so this counts as implementation detail within T8's authorized scope, not
  a second query abstraction (acceptance criterion 3).
- **Known, disclosed limitation — not fixed under T8:** `_parse_filter_param` forwards `value` as
  the literal string the client sent (except for `IN`, where it becomes a list of literal strings).
  `FilterSpec.value: object` accepts this without complaint, and T5's `_filter_predicate` compares
  it directly against the SQLAlchemy column with no type coercion. Verified directly: comparing a
  raw string against a non-string (integer) column fails at the database (Postgres:
  `operator does not exist: integer > character varying`) because asyncpg binds the Python `str`
  parameter with an explicit type the server won't implicitly cast for comparison operators.
  Comparisons against string-typed columns (the router's own throwaway verification entity's
  `name` field, and the project's `_Note.text` in the existing test file) are unaffected. This is
  not treated as a blocking regression — nothing that worked before this phase stopped working,
  and T8's nine acceptance criteria require only that parameters be accepted, assembled using the
  existing abstractions, and forwarded; none require value type coercion against the target
  column's actual type. Flagged as Deferred Work below rather than fixed here, since adding
  coercion logic keyed off column type would itself be new logic beyond T8's minimal wiring scope.
- `filters` (not `filter`) is the Python parameter name, with `Query(alias="filter")` supplying the
  actual wire-format key — avoids shadowing the `filter` builtin inside the route function's own
  body without changing the query-string key T8 describes.
- The file's documented PEP-695/runtime-annotation caveat was read first and respected: the two new
  parameters (`sort`, `filters`) use plain runtime-evaluable types (`list[str] | None`), not the
  function's own `ReadSchema`/`CreateSchema`/`UpdateSchema` type parameters, so they don't interact
  with the caveat at all — no change was needed to how `read_schema`/`create_schema`/`update_schema`
  are already annotated.

## Problems Encountered

- `black --check` initially flagged the new code (line-length wrapping differences) — resolved by
  running `uv run black` directly on the one modified file, then re-verifying with `--check`. Diff
  inspected afterward: purely a reformat (line-join), no semantic change.
- The throwaway verification script itself hit three unrelated, self-inflicted script bugs before
  producing a clean run (none reflect anything about the actual implementation): (1) an `async def
  record(...)` helper that was never awaited, silently discarding every recorded check — the same
  mistake made and caught in T6's own throwaway script; (2) a cross-event-loop asyncpg error from
  opening a connection on one `asyncio.run()` call and reusing it from `TestClient`'s own portal
  thread's loop — resolved by using a separate engine for schema setup/teardown vs. the engine
  backing the app's session; (3) after fixing (2), the script hung indefinitely — root-caused via
  `pg_stat_activity` to the shared session being left "idle in transaction" (never closed) after
  the `TestClient` block exited, blocking the teardown `DROP TABLE` on a table lock. Fixed by
  closing the session and disposing its engine from a FastAPI `lifespan` shutdown hook, so cleanup
  runs on the same event loop (`TestClient`'s own portal) that opened the connection, rather than a
  freshly created one. All three were script-only defects; none required touching the implementation
  file to resolve, and each is disclosed here for transparency about what the verification process
  actually took, not because any of them reflect an implementation defect.

## Deferred Work

- **T9** (repository-level filter/sort tests against real Postgres, `BaseService.list_page()` unit
  tests with a fake repository, `test_crud_router_factory.py` extension covering the new query
  params) — depends on T5+T6+T7+T8, all now complete; still a separate, unauthorized task. A future
  T9 pass should decide: (a) whether `tests/support/in_memory_repository.py` needs updating (T7's
  Phase8.md already flagged this) so `list_items` query-param tests can use the existing
  `InMemoryRepository` fixture rather than requiring real Postgres; (b) whether/how to add value
  type coercion for filter values against non-string columns (see Design Decisions' documented
  limitation) — genuinely a design decision (coerce based on the target column's Python/SQL type?
  require the caller to pre-format? reject with a 422?) that deserves its own consideration rather
  than being decided as a side effect of wiring work.
- **T10** (update `docs/Architecture.md`'s query-framework note) — depends on T9.
- The raw-string-filter-value-vs-typed-column limitation itself (see Design Decisions) — not fixed
  here; candidate for T9 (test coverage should at minimum document the current behavior) or a small,
  separately authorized follow-up task if the project owner wants it addressed before then.
- T4's still-missing `ImplementationLog` entry (flagged in T5's, T6's, and T7's phase logs,
  unresolved) — remains out of T8's authorized scope too.

## Future Considerations

- With T5, T6, T7, and T8 all complete, the query-framework chain (`T4`→`T8`) is now fully wired
  end-to-end for the test-only CRUD router factory. T9's test pass and T10's documentation update
  are the two remaining links.
- Whoever implements T9 should decide the filter-value-coercion question (see Deferred Work) before
  writing extensive filter-value test cases against numeric/non-string columns, since the current
  behavior (raw string forwarded, DB rejects type mismatches) may or may not be the intended final
  behavior once real business features start using this path.

Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added — correctly none: T9 explicitly and separately owns test authorship for this task,
  per T8's own authorization text (same carve-out T5/T6/T7 established).
☑ Existing tests pass
□ Documentation updated — correctly none: T10 explicitly owns the `docs/Architecture.md`
  query-framework note update, and depends on T9, not T8.
□ ADR updated (if required) — no architectural decision this phase; correctly none written.
□ AI_BOOTSTRAP updated (if required) — not required; no bootstrap-level rule affected.
□ PROJECT_STATE updated (if required) — Documentation Manager's role, not this one, and only after
  a QA Decision exists.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

QA Decision

□ Approved
☑ Approved with comments
□ Rework required

Independently verified by the QA Reviewer role (2026-08-25) against `be527fd`: diff scope
confirmed as exactly `crud_router_factory.py` (+39/−2) + this log; `build_crud_router` confirmed
not mounted anywhere in `main.py` or elsewhere in `backend/src/app/` (remains test-only, per
acceptance criterion 16). `SearchQuery`/`SortSpec`/`SortDirection`/`FilterSpec`/`FilterOperator`
all confirmed reused from `application/common/query.py`, no duplicate abstraction. `filters`
correctly aliased to the external `filter` query-string key via `Query(alias="filter")`.

Behavioral verification performed via targeted checks against the actual `_parse_sort_param`/
`_parse_filter_param`/`_build_search_query` functions plus a real `BaseService`/
`SqlAlchemyRepository`/Postgres stack (no full `TestClient`/FastAPI app needed to exercise this
logic directly): no-params → `None`; single sort (default `ASC`) and explicit `:desc`; multiple
sorts preserving precedence; all eight `FilterOperator` strings correctly mapped; `IN` correctly
splits on `,` into a list; a filter value containing `:` preserved intact (`maxsplit=2` protects
this); multiple filters both captured; combined filter+sort+pagination end-to-end through
`list_page()` with `total` correctly remaining the unfiltered `count()` (by design, per T5/T6/T7);
repeated-sort precedence honored live (`ORDER BY is_system_role DESC, name ASC`); no-query
compatibility through `list_page()` preserved. All checks passed.

**Limitation assessment (independently reproduced and extended, not merely accepted from the
report):** confirmed live that filtering `is_system_role` (a boolean column, not just the
integer/`version` case the report described) with a string value also fails —
`operator does not exist: boolean = character varying` — proving the root cause is general to any
non-text column, not narrowly integer-specific. Classification: **(B) an existing architectural
limitation, now reachable via a new surface, correctly treated as (D) acceptable deferred work** —
not (A) an acceptance-criteria failure (T8 requires only that parameters be accepted, assembled via
existing abstractions, and forwarded; none of the nine criteria require value-type coercion) and
not (C) a regression (`list_items` had zero filter capability before this phase; nothing that
previously worked now fails). The underlying gap (`FilterSpec.value: object` with no coercion) has
existed since T5 and is inherent to the query framework's current design, not something T8's
parsing logic introduced incorrectly. Correctly flagged as Deferred Work for T9/a future task
rather than fixed here — coercion logic would itself be new scope beyond T8's wiring.

`uv run pytest` independently re-run: 500 passed, 6 failed, identical failures/root cause already
established across T4–T7's phase logs (pre-existing shared-dev-database state from T83, unrelated
to this diff). `ruff`/`black --check`/`git diff --check` all independently reproduced clean. No
T9/T10 work, no Stage 4 feature, no unrelated refactoring found. `IMPLEMENTATION_QUEUE.md`/
`PROJECT_STATE.json` untouched.

**Comment (the reason for "with comments" rather than plain "Approved"):** the string-vs-typed-
column limitation, while correctly out of T8's scope to fix, is broader than the implementer's own
disclosure suggested (affects boolean columns too, not just integer) — worth naming explicitly for
whoever scopes T9 or a follow-up, so test coverage and any future coercion design account for the
full breadth of the gap, not just the one column type that happened to surface it during
implementation.
