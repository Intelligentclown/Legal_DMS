# T4 QA Review

**Task:** T4 — Extend `AbstractRepository[T].list()`'s port signature for `SearchQuery`

**Scope:** `application/interfaces/repository.py` only — extend the `AbstractRepository[T].list()`
port signature to accept an optional `SearchQuery` (or the equivalent `filters`/`sort` parameters),
preserving existing callers' behavior when the new parameter is omitted. `T5` (`FilterSpec` → SQL
`WHERE`), `T6` (`SortSpec` → SQL `ORDER BY`), `T7` (`BaseService.list_page()` wiring), `T8`
(`build_crud_router()` list-route wiring), `T9` (tests), `T10` (documentation), and any Stage 4
business feature are explicitly out of scope. Full authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s
`T4` row.

**Authorization:** PR #93, merge `76cb959` (on `main`).

**Implementation:** commit `70aef60`, branch `feat/t4-repository-searchquery-port`, PR #94 (open,
unmerged at the time of this review).

**Reviewed:** `backend/src/app/application/interfaces/repository.py` (diff `main...70aef60`),
`backend/src/app/application/common/query.py` (the module the implementation claims `SearchQuery`
is reused from, not newly invented), and the two existing callers of `AbstractRepository.list()`
(`backend/src/app/infrastructure/persistence/sqlalchemy_repository.py`,
`backend/src/app/application/common/base_service.py`).

**Date:** 2026-08-24

---

## Verification performed

- **Diff scope** — confirmed via `git diff main...70aef60 --stat` and `gh pr view 94 --json
  files`: exactly one file changed
  (`backend/src/app/application/interfaces/repository.py`), +5/−1. The entire change is the
  `list()` signature gaining one new parameter and its supporting import; nothing else in the file
  was touched.
- **`SearchQuery` reuse, not invention** — confirmed via `git log --follow` on
  `backend/src/app/application/common/query.py`: the file was introduced in `46bede6` ("Stage 1:
  validation framework, pagination/query shapes, response wrapper"), long predating this PR, and is
  imported unmodified here (`from app.application.common.query import SearchQuery`) — not accepted
  on the implementation's word alone.
- **Backward compatibility** — confirmed directly, not inferred: the new parameter is
  `query: SearchQuery | None = None`, keyword-only (after the `*`) with a default. The sole existing
  caller, `BaseService.list_page()` (`base_service.py:37`,
  `self._repository.list(limit=request.limit, offset=request.offset)`), does not pass `query` and
  is therefore unaffected. `SqlAlchemyRepository.list()` (the concrete override,
  `sqlalchemy_repository.py:32`) was not touched by this PR and correctly does not yet accept
  `query` — T5 owns adding `FilterSpec`/`SortSpec` interpretation there. This is a deliberate,
  currently-inert gap (nothing in the codebase calls `.list(query=...)` yet), not a defect: no
  static type-checker is configured in this project (`backend/pyproject.toml`,
  `.github/workflows/backend.yml` both checked directly, neither references `mypy`/`pyright`), and
  Python's `ABC` does not enforce override-signature compatibility at runtime, so nothing breaks
  today. Noted here for completeness, not as a T4 finding — it is precisely the interim state T4's
  own authorization anticipates T5 will close.
- **Ruff** — independently re-run in an isolated worktree at `70aef60`
  (`uv run ruff check src/app/application/interfaces/repository.py`): **All checks passed!**
- **Black** — independently re-run in the same worktree
  (`uv run black --check src/app/application/interfaces/repository.py`): **1 file would be left
  unchanged.**
- **`git diff --check`** — clean, no whitespace errors.
- **Full backend test suite** — independently re-run in the same worktree against a live local
  Postgres (`legal_dms_dev`, `localhost:5433`, already running and healthy in this environment):
  **6 failed, 500 passed** — an exact match to the reported figures, reproduced directly rather than
  taken on faith. All six failures are confined to `tests/integration/test_bootstrap_admin.py`
  (`TestRunBootstrapNoExistingUser`/`TestRunBootstrapExistingUser`/`TestAsyncMainNoExistingUser`/
  `TestAsyncMainExistingUser`), none touching `repository.py`, `list()`, or `SearchQuery`. The
  captured failure detail (`assert len(remaining.scalars().all()) == 1` finding `2` instead) is
  consistent with the reported root cause: the local dev database already contains a real
  Administrator user (independently corroborated by this project's own history — T83 ran
  `bootstrap-admin` for real against this exact database), so these tests' "starts from zero `User`
  rows" assumption no longer holds. This is pre-existing database-state drift, unrelated to T4's
  actual change — **not a T4 defect** — and is recorded here as a non-blocking observation only.
- **Scope boundaries** — confirmed directly: `T5`–`T10` carry no authorization language in their
  `IMPLEMENTATION_QUEUE.md` rows (plain backlog entries only); no `T86` row exists; no Stage 4
  business-feature file was touched by this PR.

## Findings

None blocking. One non-blocking observation (the currently-inert `SqlAlchemyRepository.list()`
signature gap, above) and one non-blocking pre-existing test-environment issue (the six
`test_bootstrap_admin.py` failures, above) — neither originates in, nor is caused by, this batch's
actual change.

## QA Decision

```
☑ Approved
□ Approved with comments
□ Rework required
```

Approved without comments — the implementation is minimal, exactly scoped to the authorized
port-signature change, backward-compatible with its one existing caller, and its stated
verification (diff scope, `SearchQuery` provenance, ruff/black, and the full test suite) was
independently reproduced against the actual repository and a live database, not accepted on the
implementation's own word.
