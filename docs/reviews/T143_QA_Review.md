# T143 Architecture QA Review

**Task:** T143 — Request Transaction Outcome and External-Side-Effect Compensation Architecture  
**Role:** Independent QA Reviewer  
**Architecture PR:** [#260 — `docs(adr): define T143 transaction outcome compensation architecture`](https://github.com/Intelligentclown/Legal_DMS/pull/260)  
**PR Branch:** `architecture/t143-request-transaction-outcome`  
**Authorization Baseline:** `cc112be9babdd0eb3b70dc499754ec6b3fa27841` (`origin/main`)  
**Exact Architecture Commit Reviewed:** `574f9644434e71cb9b92b571d6664a28b275a85c`  
**PR Head Before QA Document:** `574f9644434e71cb9b92b571d6664a28b275a85c`  

---

## 1. Remote Repository State & Ancestry Verification

- **Authorization Baseline:** `cc112be9babdd0eb3b70dc499754ec6b3fa27841` confirmed as exact merged T143 authorization base on `origin/main`.
- **PR State:** PR #260 is OPEN, non-draft, unmerged, targeting `main`.
- **Ancestry:** Architecture commit `574f9644434e71cb9b92b571d6664a28b275a85c` descends directly from baseline `cc112be9babdd0eb3b70dc499754ec6b3fa27841`.
- **Changed Files:** Exactly 1 documentation file:
  1. `ADR/0042-request-transaction-outcome-external-side-effect-compensation.md`
- **Scope Integrity:** Diff is +439 additions, 0 deletions. Pure architecture/documentation only. No production code, tests, schema models, or Alembic migrations were modified.
- **GitHub CI State:** Control Tower and live GitHub status confirm all check runs on exact head `574f9644434e71cb9b92b571d6664a28b275a85c` completed successfully (`success`).
- **Governance State:** `latestTaskDone = T141`, `latestTaskAuthorized = T143`, `inProgressTransitions = []`. Required ADR #11 is resolved (by ADR-0041). Unresolved Required ADRs remain `[12, 15, 16, 17, 20]`. Migration frontier remains `cdcfd7df5fde`. T144+ remains unauthorized.

---

## 2. Independent Model & Repository Fact Inspection

Independent verification against actual repository code, models, and interfaces confirms:
- **`get_db()` Transaction Policy (`backend/src/app/infrastructure/database/session.py`):** `get_db()` yields `session`, route/service executes, then `session.commit()` is called on success, `session.rollback()` on exception. Repositories and services flush only.
- **`UnitOfWork` & Pipeline abstractions (`backend/src/app/application/common/`):** `UnitOfWork` and `TransactionPipelineBehavior` exist in `application/common/` but are not request-scoped or wired to `get_db()`.
- **SQLAlchemy `AsyncSession.info`:** Provides instance-bound session-local dictionary tied 1-to-1 to the request `AsyncSession`.
- **T141 Idempotency Foundation (`document_version_idempotency_keys`):** Unique constraint `(organization_id, document_id, idempotency_key)` and composite same-tenant FKs exist in schema (`cdcfd7df5fde`).
- **`LocalFileStorage` (`backend/src/app/infrastructure/storage/local_file_storage.py`):** Operates on provider-relative paths with root escape containment checks.

---

## 3. Detailed Architectural Assessments

### A. ADR-0020 Transaction Ownership Compatibility
- **Approved.** ADR-0042 strictly preserves ADR-0020. `get_db()` remains the sole transaction owner. Repositories and services remain flush-only. No secondary commit caller or application-level commit is introduced.

### B. Terminal Outcome Classification Model
- **Approved.** Three terminal states are precise, mutually coherent, and conservative:
  1. `CONFIRMED_COMMIT`: `session.commit()` returns normally. All registered compensations are discarded.
  2. `DEFINITIVE_NON_COMMIT`: Pre-COMMIT failure followed by successful rollback, or explicit proven abort. LIFO compensations run best-effort.
  3. `COMMIT_OUTCOME_UNCERTAIN`: Generic commit exception, timeout, or connection loss around commit. Destructive compensation is SUPPRESSED. Discard in-memory callbacks; durable T141 idempotency reconciliation handles subsequent retries.

### C. Conservative Commit-Exception Rule
- **Approved.** Generic `session.commit()` exceptions default to `COMMIT_OUTCOME_UNCERTAIN`. This deliberately prevents deleting stored external bytes when PostgreSQL may have actually committed the transaction.

### D. FastAPI Teardown & Lifecycle Integration
- **Approved.** `get_db()` creates `TransactionOutcomeContext` attached to `session.info`. A companion dependency `TransactionOutcomeContextDep` reads it for `DBSessionDep`. Teardown executes commit and context finalization before request completion. The requirement to test FastAPI dependency teardown error surfacing is explicit.

### E. Session-Local State via `AsyncSession.info`
- **Approved.** Uses `session.info` tied to the active request `AsyncSession`. Requires no global registries, no ContextVar inheritance bugs, and no modification to FastAPI route signatures.

### F. Registration, Ordering, and Domain Neutrality
- **Approved.** Trusted application code registers async no-argument callables after external side-effect success. Execution is LIFO. Callbacks are domain-neutral (context knows no storage or document concepts). All eligible callbacks execute best-effort even if one fails.

### G. Cancellation & BaseException Handling
- **Approved.** Requires `BaseException`-aware finalization so `asyncio.CancelledError` does not cause registered compensation to silently disappear. Bounded shielding (`asyncio.shield`) is recommended for cleanup without shielding whole DB operations.

### H. T141 Idempotency Reconciliation & Orphan Safety
- **Approved.** Uses T141's `(organization_id, document_id, idempotency_key)` table. Uncertain outcomes leave external blobs intact as non-authoritative orphan candidates; subsequent retries evaluate idempotency to determine if the version exists.

### I. Security, RLS & Observability
- **Approved.** Preserves ADR-0021 FORCE RLS, Organization GUC, restricted runtime role `legal_dms_app`, and RBAC. Compensation runs under trusted server-created state, never caller-controlled targets. Logging contract requires structured technical metrics without logging bytes or credentials.

### J. Implementation Decomposition
- **Approved.** Recommends Path 1 (implementing the small generic `TransactionOutcomeContext` infrastructure as the first bounded portion of resumed T142).

---

## 4. Static & Governance Validation Results

- **Governance Validator (`python scripts/governance_validate.py`):** `OK (0 warning(s), 0 errors)`.
- **Ruff Check (`ruff check backend`):** Passed (0 errors).
- **Black Check (`black --check backend/src backend/tests`):** Passed (269 files unchanged).
- **Git Diff Check (`git diff --check origin/main..HEAD`):** Passed (no whitespace errors).
- **GitHub Actions CI:** All check runs on PR #260 exact head completed successfully (`success`).

---

## 5. Required ADR Disposition

- **Required ADR #11:** Remains resolved by ADR-0041.
- **Required ADR #12, #15, #16, #17, #20:**  
  **Remain globally UNRESOLVED.** ADR-0042 resolves no Required ADR.

---

## 6. Formal QA Verdict

**Formal Verdict: `Approved`**

- PR #260 remains open and unmerged.
- T143 remains Authorized / not Done.
- T142 remains Authorized / blocked / not Done.
- T144+ remains unauthorized.
- Hand back to Control Tower / Documentation Manager for T143 post-QA governance synchronization under `PROJECT_WORKFLOW.md §3.1`.
