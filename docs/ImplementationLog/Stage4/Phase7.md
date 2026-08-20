------------------------------------------------

# Stage 4 – Phase 7

Status: In Progress

Started: 2026-08-20

Completed:

Related Tasks: T77

Related ADRs: None explicitly named (Stage 2.5's F4).

Git Commit: 64540de (Implementation)

Pull Request: None yet

Release:

---

---

## T77 Batch: Gate `/docs`/`/redoc` behind `settings.is_development`

**Authorization / Scope:** The project owner authorized T77 on 2026-08-20 (Stage 2.5's F4, bundled now since API docs exposure is meaningfully more sensitive once real auth/user data exists), recorded in `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` as its own documentation-only commit (`60d07f0`) before any implementation existed. Approved scope: gate `/docs` and `/redoc` based on the existing `settings.is_development` configuration; reuse the existing settings/configuration mechanism; no new authentication mechanisms; no changes to unrelated API routes; `T78+` and any other future task explicitly out of scope and unauthorized.

### Objective

Stop exposing the interactive Swagger UI (`/docs`) and ReDoc (`/redoc`) pages outside development, using the `is_development` property `Settings` (`backend/src/app/infrastructure/config/settings.py`) already exposes, without introducing any new configuration mechanism.

### Tasks Implemented

- `T77` — `backend/src/app/main.py`'s `create_app()` now passes `docs_url="/docs" if settings.is_development else None` and `redoc_url="/redoc" if settings.is_development else None` to the `FastAPI(...)` constructor, in place of the two previously-hardcoded string literals. `settings.is_development` (already implemented, backed by `environment: Environment = "development"`, sourced from the existing `ENVIRONMENT` env var / `.env` mechanism) is the sole condition — no new settings field, no new env var, no new configuration surface. FastAPI's own documented behavior is that passing `None` for `docs_url`/`redoc_url` disables that page's route entirely (404, not merely hidden from a menu). `openapi_url` (not previously passed, defaulting to `/openapi.json`) was deliberately left untouched, per this batch's explicit authorization boundary — confirmed unchanged by direct inspection after the change (`app.openapi_url == "/openapi.json"`).

### Files Modified

Per `git diff --stat` against this batch's starting point (`545d00b`):

- `backend/src/app/main.py` (Modified) — 2 lines changed inside `create_app()`; nothing else in the file touched (middleware registration, router mounting, DI/container wiring, logging, and the module-level `app = create_app()` singleton are all untouched).
- `backend/tests/integration/test_docs_redoc_gating.py` (New) — 6 tests covering enabled/disabled behavior across all three `environment` values.

### Tests Added

`backend/tests/integration/test_docs_redoc_gating.py` (6 new tests). Since the shared `client`/`app` fixture in `tests/conftest.py` wraps the module-level `app` singleton built once at import time (and therefore can't exercise a different `environment` per test), each test instead builds its own isolated `FastAPI` instance: `app.main.get_settings` is monkeypatched (via `monkeypatch.setattr`) to return a `Settings(_env_file=None, jwt_secret_key="test-secret", environment=<value>)` instance — the same `Settings(_env_file=None, ...)` isolation idiom already established in `tests/unit/test_feature_flags.py` — then `create_app()` is called fresh and wrapped in its own `TestClient`. This leaves the shared `app` fixture, `configure_container()`'s module-level container, and every other test file's global state untouched.

- `test_docs_available_in_development` / `test_redoc_available_in_development` — `environment="development"` (`is_development=True`) → `GET /docs` and `GET /redoc` both return `200`.
- `test_docs_not_exposed_in_production` / `test_redoc_not_exposed_in_production` — `environment="production"` (`is_development=False`) → both return `404`.
- `test_docs_not_exposed_in_testing` / `test_redoc_not_exposed_in_testing` — `environment="testing"` (`is_development=False`) → both return `404`, confirming the gate is specifically `is_development`, not merely "not production."

### Test Results

Run against this batch's working tree (`feature/T77-docs-redoc-development-gate`):

- **Backend full suite:** 496/496 passing (490 prior + 6 new) — `uv run pytest`.
- **Backend lint:** clean — `uv run ruff check .` → "All checks passed!".
- **Backend format:** clean — `uv run black --check .` → "All done! 205 files would be left unchanged."
- **Backend type checks:** no separate type-checker (mypy/pyright) is configured for this backend — `ruff`'s `UP`/`F` rule sets and `black` are the only static checks this repository runs for `backend/`, consistent with every prior Stage 3/4 batch's recorded verification. None flagged any issue.
- **Boot smoke test:** `app.openapi()["paths"]` confirmed unchanged — still exactly the eleven routes `T63` established (`/api/v1/auth/{login,logout,me,refresh}`, `/api/v1/health`, `/api/v1/users`, `/api/v1/users/{user_id}`, `/api/v1/users/{user_id}/deactivate`, `/api/v1/users/{user_id}/roles`, `/api/v1/users/{user_id}/roles/{role_id}`, `/api/v1/version`) — no route added, removed, or modified. Against the real `.env` (`ENVIRONMENT=development`), `app.docs_url == "/docs"`, `app.redoc_url == "/redoc"`, and `app.openapi_url == "/openapi.json"` — all three confirmed directly, proving development-mode behavior is unchanged from before this batch.
- Frontend suite not run — this batch touches only `backend/`, no frontend file is part of its diff.

### Design Decisions

- **`docs_url`/`redoc_url` set inline via a conditional expression at the `FastAPI(...)` call site, not a separate `if` block or helper function.** The gate is a single boolean read (`settings.is_development`) feeding two constructor kwargs — introducing a helper or a branch would be indirection this two-line change doesn't need, consistent with this project's stated preference against premature abstraction.
- **`openapi_url` left unmodified.** Flagged during planning as a related but explicitly out-of-scope concern: gating `docs_url`/`redoc_url` alone leaves the raw OpenAPI schema (`/openapi.json`) reachable regardless of environment, since FastAPI serves it independently of the two UI pages. The authorized scope names only `/docs` and `/redoc`; changing `openapi_url`'s behavior would be a third, unauthorized route change. Recorded here as a known follow-up candidate, not acted on.
- **Test isolation via monkeypatched `app.main.get_settings` + a locally-built `create_app()`/`TestClient`, not a shared fixture change.** `create_app()` calls `get_settings()` (module-level `@lru_cache`d) directly and isn't parameterized by an injected `Settings` instance; the shared `client` fixture in `conftest.py` imports the already-built singleton `app`. Rebuilding a fresh app per test via a monkeypatched `get_settings` avoids touching `conftest.py` (out of this batch's necessary scope) and avoids mutating the process-wide `lru_cache`, so it can't leak into any other test file's `client`/`app` fixture usage.

### Problems Encountered

None. The first test run passed cleanly; no rework was needed.

### Deferred Work

- `/openapi.json` gating (see Design Decisions above) — explicitly out of scope for `T77`, left for a future task if the project owner decides the raw schema should also be hidden outside development.
- `T78+` remains explicitly out of scope and unauthorized, per this batch's own authorization text.

### Reviewer Checklist

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — no architectural decision rose to ADR-level; the openapi_url
  scope boundary is recorded above as a Design Decision instead
□ AI_BOOTSTRAP updated (if required) — N/A, no standing convention changed
□ PROJECT_STATE updated (if required) — out of scope for this role/session per explicit
  instruction; left to the Documentation Manager after QA
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

### QA Decision — T77 batch

- **Date:** 2026-08-20
- **Decision:** [x] Approved | [ ] Approved with comments | [ ] Rework required
- **Comments / Rework items:**
  - No rework required.
  - Non-blocking observation: A cosmetic observation about test naming was noted during QA, but required no rework.

## T78 Batch: Tighten CORS `allow_methods`/`allow_headers` from wildcards

### Implementation

- **Git Commit:** 07fe8e1
- **Verification Results:**
  - 10/10 T78 tests passed
  - 506/506 backend tests passed
  - Ruff clean
  - Black clean

### QA Decision - T78 batch

- **Date:** 2026-08-20
- **Decision:** [ ] Approved | [x] Approved with comments | [ ] Rework required
- **Comments / Rework items:**
  - No rework required.
  - Non-blocking observation: The test `test_disallowed_method_is_rejected_by_cors_preflight` uses `TRACE`. Starlette rejects TRACE even under the previous wildcard `allow_methods=["*"]`, so that particular negative-path assertion does not itself discriminate the T78 tightening (it does not prove the tightening by itself). However, the positive exact-list assertions and the X-Custom-Header rejection test genuinely discriminate the tightened configuration.
