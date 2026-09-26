# T144 Architecture QA Review

**Task:** T144 — Pre-Response Request Transaction Finalization Architecture  
**Role:** Independent QA Reviewer  
**Architecture PR:** [#263 — `docs(adr): define T144 pre-response transaction finalization`](https://github.com/Intelligentclown/Legal_DMS/pull/263)  
**PR Branch:** `architecture/t144-pre-response-transaction-finalization`  
**Authorization Baseline:** `ce698126127259019a65e8b74531fa34e3fc5493` (`origin/main`)  
**Exact Architecture Candidate Commit Reviewed:** `4506b5c85307d689f94aeef839859257cbb07b81`  
**PR Head Before QA Document:** `4506b5c85307d689f94aeef839859257cbb07b81`  

---

## 1. Remote Repository State & Ancestry Verification

- **Authorization Baseline:** `ce698126127259019a65e8b74531fa34e3fc5493` confirmed as `origin/main`.
- **PR State:** PR #263 is OPEN, non-draft, unmerged, targeting `main`.
- **Ancestry:** Architecture candidate `4506b5c85307d689f94aeef839859257cbb07b81` descends directly from baseline `ce698126127259019a65e8b74531fa34e3fc5493`.
- **Changed Files:** Exactly 1 documentation file:
  1. `ADR/0042-request-transaction-outcome-external-side-effect-compensation.md`
- **Scope Integrity:** Diff is +368 additions, 0 deletions (Section 8 addendum). Pure architecture/documentation only. No production code, tests, schema models, or Alembic migrations were modified.
- **Governance State:** `latestTaskDone = T143`, `latestTaskAuthorized = T144`, `inProgressTransitions = []`. Required ADR #11 is resolved (by ADR-0041). Unresolved Required ADRs remain `[12, 15, 16, 17, 20]`. Migration frontier remains `cdcfd7df5fde`. T145+ remains unauthorized.

---

## 2. Framework Authority & Dependency Scope Inspection

- **Pinned Environment:** FastAPI `0.141.1`, Starlette `1.3.1`.
- **Default Yield Dependency Scope (`scope=None` / `"request"`):** Teardown code in yield dependencies (after `yield session`) executes in Starlette's response background / exit stack AFTER `http.response.start` and response body transmission have completed. If transaction finalization (commit/rollback/compensation) fails post-`yield`, the HTTP response status (e.g. 200 OK) has ALREADY been transmitted to the client.
- **Explicit Function Scope (`scope="function"`):** Under `DBSessionDep = Annotated[AsyncSession, Depends(get_db, scope="function")]`, FastAPI's dependency solver binds the yield dependency teardown to the path operation function execution stack. Teardown (including `session.commit()`, outcome classification, and compensation execution) runs immediately after the route function returns provisionally and BEFORE Starlette issues `http.response.start`.

---

## 3. Empirical Experimental Proofs (ASGI Harness Verification)

An independent, bounded ASGI experiment harness (`scratch/test_fastapi_scope_experiment.py`) was executed against the pinned environment (`FastAPI 0.141.1`):

### A. Old Failure Reproduction (Default Scope)
- **Behavior:** Simulated route returns provisional success -> ASGI middleware captures `http.response.start (200 OK)` -> `get_db()` resumes and raises commit failure.
- **Result:** Client receives HTTP 200 OK despite DB commit failure! Proved that default scope suffers from the prohibited ordering bug.

### B. Positive Proof (Function Scope)
- **Behavior:** Explicit `scope="function"` with successful commit.
- **Trace Sequence:** `['db_start', 'route_exec', 'db_commit_success', 'http.response.start (200)', 'http.response.body']`.
- **Result:** `db_commit_success` completes BEFORE `http.response.start (200)`. Invariant holds strictly.

### C. Definitive Non-Commit Proof (Function Scope)
- **Behavior:** Explicit `scope="function"` with commit failure / non-commit condition.
- **Trace Sequence:** `['db_start', 'route_exec', 'db_commit_attempt', 'db_rollback']` (NO `http.response.start` sent by app handler).
- **Result:** Exception raised during dependency teardown causes Starlette exception handler to catch the error prior to response header send, returning HTTP 500 Internal Server Error to client. No successful response started. Registered compensations run prior to exception bubbling.

### D. Commit Outcome Uncertain Proof
- **Behavior:** Commitment attempt encounters generic timeout / unclassifiable error.
- **Result:** `TransactionOutcomeContext` sets outcome to `COMMIT_OUTCOME_UNCERTAIN`. Destructive compensations (e.g., blob deletion) are strictly suppressed. No 200 OK response starts; failure status returned to client. Durable T141 idempotency reconciliation handles retry.

---

## 4. Key Architectural Assessments

1. **ADR-0020 Compatibility:** Function scope changes transaction **lifetime** (completing before response send) rather than **ownership**. `get_db()` remains sole transaction owner. Repositories and services remain flush-only. ADR-0020 remains Accepted.
2. **ADR-0041 Compatibility:** Preserves blob-first / DB-second ordering, Document locking (`SELECT ... FOR UPDATE`), `MAX+1` allocation, exclusive FileStorageRecord, and idempotency rules.
3. **Session Identity & Dependency Graph:** FastAPI dependency caching (`use_cache=True`) ensures all dependent services (`CurrentUser`, `RequirePermission`, repositories) share the exact same `AsyncSession` instance within the request.
4. **Commit Count Invariant:** Exactly 1 commit per successful request during `get_db()` teardown. No route, service, or repository commits.
5. **PostgreSQL GUC / RLS Security:** Session teardown and finalization occur within the active session lifecycle while the Organization transaction-local GUC (`app.current_organization_id`) and FORCE RLS remain active.
6. **Response Materialization (JSON & Byte Download):**
   - JSON endpoints fully serialize DTOs before route handler return, preventing post-finalization lazy ORM loads.
   - Raw-byte downloads (`FileStorage.read(path) -> bytes`) read and verify bytes into memory before route return and transaction finalization, ensuring no DB session access during byte transmission.
7. **Streaming & Background Work Constraints:** Lazy `StreamingResponse` and `BackgroundTask` instances are strictly prohibited from using the finalized request `AsyncSession`, tenant GUC, or `TransactionOutcomeContext`.
8. **Cancellation & Disconnects:** `BaseException`-aware teardown handles `asyncio.CancelledError`. Disconnects or send failures after `CONFIRMED_COMMIT` do not trigger compensation or delete committed DB content.

---

## 5. Static & Governance Validation Results

- **Governance Validator (`python scripts/governance_validate.py`):** `OK (0 warning(s), 0 errors)`.
- **Ruff Check (`ruff check backend`):** Passed (0 errors).
- **Black Check (`black --check backend/src backend/tests`):** Passed (269 files unchanged).
- **Git Diff Check (`git diff --check origin/main..HEAD`):** Passed (no whitespace errors).

---

## 6. Formal QA Verdict

**Formal Verdict: `Approved`**

- PR #263 candidate `4506b5c85307d689f94aeef839859257cbb07b81` is architecturally verified and approved.
- PR #263 remains open and unmerged.
- T144 remains Authorized / not Done.
- T142 remains Authorized / blocked / not Done.
- T145+ remains unauthorized.
- Hand back to Control Tower for T144 governance processing under `PROJECT_WORKFLOW.md §3.1`.
