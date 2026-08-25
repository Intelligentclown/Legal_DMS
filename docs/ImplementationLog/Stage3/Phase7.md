------------------------------------------------

# Stage 3 – Phase 7

Status: In Progress

Started: 2026-08-25

Completed:

Related Tasks: T6

Related ADRs: None explicitly named.

Git Commit: (pending — see PR)

Pull Request: (pending)

Release:

------------------------------------------------

## Objective

Translate `SortSpec` into a SQLAlchemy `ORDER BY` clause inside `SqlAlchemyRepository.list()`,
so the `SearchQuery.sort` field T4's port change made available actually orders results for the
repository's concrete SQLAlchemy implementation, applied after T5's filtering and before pagination.

## Tasks Implemented

- **T6** — `SortSpec` → SQLAlchemy `ORDER BY` translation in `SqlAlchemyRepository.list()`,
  supporting both directions `app/application/common/query.py`'s `SortDirection` defines: `ASC`,
  `DESC`, including multiple `SortSpec`s with precedence preserved.

## Files Modified

`backend/src/app/infrastructure/persistence/sqlalchemy_repository.py` — the only file touched (per
`git diff --stat` against this phase's starting point, `54bc118`): 20 insertions, 1 deletion.

- Added a module-level `_sort_expression(column, spec) -> ColumnElement[Any]` helper, translating a
  single `SortSpec` via `match`/`case` over `SortDirection` into `column.asc()` or `column.desc()`.
- `list()` now also inspects `query.sort`: when non-empty, translates each `SortSpec` in declared
  order and applies them via `stmt.order_by(*order_by_clauses)`, inserted after the existing
  `.where(...)` filtering block (T5) and before `.limit(limit).offset(offset)` — preserving
  SQL's natural `WHERE` → `ORDER BY` → `LIMIT`/`OFFSET` evaluation order.
- T5's `_filter_predicate`/`.where(...)` block is unchanged.
- `count()` remains untouched — not named in T6's authorized scope.

## Tests Added

None. Per T6's own authorization in `IMPLEMENTATION_QUEUE.md`, T9 owns this query-framework
chain's test work (repository-level filter/sort tests against real Postgres, once T5–T8 all
exist) — the same explicit carve-out T5 established and the project owner previously confirmed.

## Test Results

- `cd backend && uv run pytest`: **500 passed**, 6 failed — all 6 in
  `tests/integration/test_bootstrap_admin.py`. Same failures already root-caused in T5's QA
  Decision (`docs/ImplementationLog/Stage3/Phase6.md`): a pre-existing single `users` row in the
  shared dev database from an earlier, unrelated session (T83), which that test file's own
  preconditions don't tolerate — mechanically unrelated to this diff, which that test file doesn't
  import.
- `cd backend && uv run ruff check src tests alembic`: all checks passed.
- `cd backend && uv run black --check src tests alembic`: all 206 files unchanged.
- `git diff --check`: clean.
- **Not part of the shipped diff, but run to self-verify correctness given no test file ships with
  this phase:** a throwaway script (session scratchpad, executed once, then deleted) exercised
  against a real local Postgres instance using the actual application code end-to-end: ASC on a
  string field, DESC on a string field, the dataclass's default direction (`ASC` when omitted),
  multi-field sort precedence (primary field ascending, secondary field descending as a tiebreaker
  within ties), filter+sort combined, sort applied before `limit`/`offset` pagination, `query=None`,
  an empty `SearchQuery()` (no sort specified), and a caller passing no `query` kwarg at all. 9/9
  passed. Disclosed as manual/exploratory verification, not a substitute for T9's own future
  automated coverage.

## Design Decisions

- `_sort_expression` mirrors T5's `_filter_predicate` shape exactly (module-level private helper,
  `match`/`case` over the spec's enum field) for consistency within the same file, per the Backend
  Developer role's "match this project's existing design patterns" rule — no new abstraction shape
  introduced.
- `column.asc()`/`column.desc()` (SQLAlchemy's `ColumnElement` expression API) is used rather than
  the module-level `sqlalchemy.asc()`/`desc()` functions or any raw SQL string — consistent with
  T5's use of column-level operators (`column ==`, `column.contains(...)`, etc.) rather than
  standalone SQL-construction helpers.
- Multiple `SortSpec`s are applied in the order `SearchQuery.sort` declares them, via
  `stmt.order_by(*order_by_clauses)` — SQLAlchemy (and SQL's `ORDER BY` generally) already treats
  multiple `order_by` arguments as primary/secondary/... precedence, so no explicit precedence
  logic was needed beyond preserving the tuple's iteration order.
- `order_by(...)` is placed after `where(...)` and before `limit(...).offset(...)` in the method
  body, matching both the required WHERE → ORDER BY → LIMIT/OFFSET evaluation order and this
  method's existing top-to-bottom structure.
- No default/implicit sort was added when `query.sort` is empty or `query` is `None` — matches T6's
  acceptance criterion that existing behavior is preserved when no sort is supplied (result order is
  then whatever Postgres/the existing `.limit().offset()` naturally returns, as it always was).

## Problems Encountered

None. This phase's shape closely followed T5's established pattern (same file, same method, same
per-operator/per-direction `match`/`case` helper style, same throwaway-verification-script
approach), so no new problems surfaced beyond what T5 already resolved.

## Deferred Work

- **T7** (wire `BaseService.list_page()` to accept and forward `SearchQuery`) — depends on T5+T6,
  both now complete; still a separate, unauthorized task.
- **T8** (wire `build_crud_router`'s `list_items` route to accept `sort`/`filter` query params) —
  depends on T7.
- **T9** (repository-level filter/sort tests against real Postgres, `BaseService.list_page()` unit
  tests, `test_crud_router_factory.py` extension) — depends on T5+T6+T7+T8; explicitly excluded
  from T6's own scope, same as T5's. Trigger condition: once T7–T8 also land.
- **T10** (update `docs/Architecture.md`'s query-framework note) — depends on T9.
- T4's still-missing `ImplementationLog` entry (flagged in T5's Phase6.md, unresolved) — not fixed
  here either; remains out of T6's authorized scope.

## Future Considerations

- With both T5 (filter) and T6 (sort) now implemented, T7 is fully dependency-satisfied — whoever
  picks up T7 can wire `BaseService.list_page()` to forward a `SearchQuery` without further
  repository-layer prerequisites.
- Same open question T5's Phase6.md raised still applies here: `getattr(self._model, spec.field)`
  (used identically for both `FilterSpec.field` and `SortSpec.field`) raises a raw `AttributeError`
  on an unknown field name; worth deciding at T8, the first layer where `field` names could
  originate from untrusted external query parameters.

Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added — correctly none: T9 explicitly and separately owns test authorship for this task,
  per T6's own authorization text (same carve-out T5 established).
☑ Existing tests pass
□ Documentation updated — correctly none: T10 explicitly owns the `docs/Architecture.md`
  query-framework note update, and depends on T9, not T6.
□ ADR updated (if required) — no architectural decision this phase; correctly none written.
□ AI_BOOTSTRAP updated (if required) — not required; no bootstrap-level rule affected.
□ PROJECT_STATE updated (if required) — Documentation Manager's role, not this one, and only after
  a QA Decision exists.
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

QA Decision

☑ Approved
□ Approved with comments
□ Rework required

Independently verified by the QA Reviewer role (2026-08-25) against `d1d38b3`: diff scope
confirmed as exactly `sqlalchemy_repository.py` (+20/−1) + this log — no unauthorized file
touched, `base_service.py` byte-identical to `origin/main`, no `.list(query=`/`order_by`/
`SortSpec` reference anywhere outside this one file (no hidden T7/T8 wiring). `SortSpec`/
`SortDirection`/`SearchQuery` confirmed reused from `application/common/query.py`, not
duplicated. `_sort_expression()` confirmed to mirror T5's `_filter_predicate()` shape exactly.
`ORDER BY` confirmed positioned after `WHERE` (T5) and before `LIMIT`/`OFFSET` in the method body.

Behavioral verification performed live against real Postgres seed data (the `roles` table, 6
rows), via a throwaway non-committed script, not merely accepted from the report: ASC by `name`
(`['Accountant', 'Administrator', ...]`, correctly sorted); DESC (exact reverse of ASC); omitting
`direction` on `SortSpec` produced results identical to explicit `ASC` (default respected);
`query=None` and an empty `SearchQuery()` both returned the unsorted baseline unchanged; a
`FilterSpec` + `SortSpec` combined correctly filtered then sorted; two `SortSpec`s
(`is_system_role DESC, name ASC`) correctly grouped by the primary key with the secondary key
ascending within each group, proving precedence; `limit=1` with `sort=DESC` returned the true
last-sorted row ("Read Only"), not an arbitrary row — proving sort is applied before pagination,
not after; an existing no-`query` caller (`limit=100, offset=0`) remained compatible. All 9 live
checks passed, generated SQL inspected directly for each.

`uv run pytest` independently re-run: 500 passed, 6 failed, identical failures/root cause already
established in T5's `Phase6.md` QA Decision (pre-existing shared-dev-database state from T83, not
this diff — `test_bootstrap_admin.py` doesn't import `sqlalchemy_repository.py`).
`ruff`/`black --check`/`git diff --check` all independently reproduced clean. No T7/T8/T9/T10
work, no Stage 4 feature, no unrelated refactoring found. `IMPLEMENTATION_QUEUE.md`/
`PROJECT_STATE.json` untouched by the implementation.
