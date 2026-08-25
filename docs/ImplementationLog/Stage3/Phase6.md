------------------------------------------------

# Stage 3 – Phase 6

Status: In Progress

Started: 2026-08-25

Completed:

Related Tasks: T5

Related ADRs: None explicitly named.

Git Commit: 2047403 (Implementation)

Pull Request: #98 (open, unmerged)

Release:

------------------------------------------------

## Objective

Translate `FilterSpec` into a SQLAlchemy `WHERE` clause inside `SqlAlchemyRepository.list()`, so
the `query: SearchQuery | None` parameter T4 added to the port actually does something for the
repository's concrete SQLAlchemy implementation.

## Tasks Implemented

- **T5** — `FilterSpec` → SQLAlchemy `WHERE` translation in `SqlAlchemyRepository.list()`, for all
  eight operators `app/application/common/query.py` already defines: `EQ`, `NEQ`, `GT`, `GTE`,
  `LT`, `LTE`, `CONTAINS`, `IN`.

Note on a pre-existing gap found while starting this phase: **T4** (the port-signature change this
task depends on, merged via PR #94 / `965b55e`) has no `ImplementationLog` entry anywhere under
`docs/ImplementationLog/` — confirmed by search, not assumed. That gap predates this phase and is
outside T5's authorized scope to fix; flagged here rather than silently backfilled.

## Files Modified

`backend/src/app/infrastructure/persistence/sqlalchemy_repository.py` — the only file touched (per
`git diff --stat` against this phase's starting point, `46ce7d2`): 33 insertions, 3 deletions.

- Added a module-level `_filter_predicate(column, spec) -> ColumnElement[bool]` helper, translating
  a single `FilterSpec` via `match`/`case` over `FilterOperator` into the corresponding SQLAlchemy
  column expression.
- `list()` now accepts `query: SearchQuery | None = None` (matching T4's port signature exactly)
  and, when `query.filters` is non-empty, ANDs the translated predicates onto the `select()` via
  `.where(*conditions)` before `limit`/`offset` are applied.
- `count()` is untouched — not named in T5's authorized scope.

## Tests Added

None. T5's own authorized scope in `IMPLEMENTATION_QUEUE.md` explicitly and repeatedly states that
**T9 (tests) is outside this row's scope — "not implied by this row"** — T9 is a separate,
still-unauthorized task, dependent on T5+T6+T7+T8 together, scoped for a consolidated
repository/service/router test pass once the whole chain exists. Confirmed with the project owner
before implementing (see Problems Encountered) rather than assumed.

## Test Results

- `cd backend && uv run pytest`: **500 passed**, 6 failed — all 6 in
  `tests/integration/test_bootstrap_admin.py`, confirmed pre-existing by reproducing the identical
  failures against unmodified `main` via `git stash`; a local Postgres/bootstrap-fixture issue
  unrelated to this change, not a regression it introduced.
- `cd backend && uv run ruff check src tests alembic`: all checks passed.
- `cd backend && uv run black --check src tests alembic`: all 206 files unchanged (after running
  `black` once directly to reformat the new code — see Problems Encountered).
- `git diff --check`: clean.
- **Not part of the shipped diff, but run to self-verify correctness given no test file ships with
  this phase:** a throwaway script (written to the session scratchpad, executed once, then deleted)
  exercised all 8 operators, a combined-AND multi-filter case, and unchanged `query=None`/no-filter
  behavior against a real local Postgres instance using the actual application code end-to-end. All
  11 checks passed. This is disclosed as manual/exploratory verification, not a substitute for T9's
  own future automated coverage.

## Design Decisions

- The translation helper mirrors an existing, already-established pattern in this codebase almost
  exactly: `app/infrastructure/search/in_memory_search_index.py`'s `_matches_filter(value,
  filter_spec)` (module-level private function, `match`/`case` over `FilterOperator`). This phase's
  `_filter_predicate` follows that same shape rather than inventing a new one, per the Backend
  Developer role's "match this project's existing design patterns" rule.
- Multiple `FilterSpec`s are combined with AND only (via `.where(*conditions)`), matching
  `SearchQuery`'s shape (a flat tuple of filters, no explicit boolean-combinator field) — no OR/NOT
  support exists in `query.py` today, so none was added here.
- `getattr(self._model, spec.field)` is used directly, with no explicit "unknown field" validation
  or error handling — `T5`'s acceptance criteria don't require it, and adding speculative validation
  for a scenario not in scope would conflict with the role's "no speculative abstraction" rule. An
  unknown `field` name raises `AttributeError` naturally.
- `count()` deliberately left unmodified — T5's authorized scope names `list()` only.

## Problems Encountered

- `black --check` initially flagged the new code (a list comprehension line exceeding the line
  length limit) — resolved by running `uv run black` directly on the one modified file, then
  re-verifying with `--check`.
- Before implementing, identified a direct conflict between the standing Backend Developer role
  instructions ("never skip writing tests for new behavior") and T5's own authorization text
  (explicitly excludes T9/tests from this row's scope). Stopped at the required approval checkpoint
  and asked the project owner directly rather than guessing; the project owner confirmed: no new
  tests under T5, per the literal authorization — T9 owns test authorship once T5–T8 all exist.

## Deferred Work

- **T6** (`SortSpec` → SQL `ORDER BY` translation, same method) — separate, still-unauthorized task.
- **T7** (wire `BaseService.list_page()` to accept and forward `SearchQuery`) — depends on T5+T6.
- **T8** (wire `build_crud_router`'s `list_items` route to accept `sort`/`filter` query params) —
  depends on T7.
- **T9** (repository-level filter/sort tests against real Postgres, `BaseService.list_page()` unit
  tests, `test_crud_router_factory.py` extension) — depends on T5+T6+T7+T8; explicitly excluded
  from T5's own scope, trigger condition: once T5–T8 all land.
- **T10** (update `docs/Architecture.md`'s query-framework note) — depends on T9.
- T4's missing `ImplementationLog` entry (see Tasks Implemented note above) — not fixed here, out of
  T5's authorized scope; a candidate for a small, separately-authorized documentation task if the
  project owner wants it backfilled.

## Future Considerations

- Once T6 (sort) lands alongside this phase's filter work, T9's future test pass should exercise
  both together against real Postgres, per its own scope description.
- `getattr(self._model, spec.field)` raising a raw `AttributeError` on an unknown field is the
  current behavior; whether a later task should turn that into a more caller-friendly error (e.g.
  a validation error at the API boundary) is an open question for whoever implements T8 (the first
  layer where `field` names could originate from untrusted external query parameters).

Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added — correctly none: T9 explicitly and separately owns test authorship for this task per
  T5's own authorization text, confirmed with the project owner before implementing.
☑ Existing tests pass
□ Documentation updated — correctly none: T10 explicitly owns the `docs/Architecture.md`
  query-framework note update, and depends on T9, not T5.
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
