# T183 Independent QA Review — PostgreSQL File-Number Allocator Concurrency Remediation (Implementation)

**Task:** T183 — PostgreSQL File-Number Allocator Concurrency Remediation  
**Lifecycle Stage:** Implementation PR 2 of 3 (`PROJECT_WORKFLOW.md §3.1`)  
**Candidate Evaluated (Substantive Head):** [`c50f366bbd95ca06a077069069a31a7fb38f6ae4`](https://github.com/Intelligentclown/Legal_DMS/commit/c50f366bbd95ca06a077069069a31a7fb38f6ae4)  
**Protected Base Commit:** [`c592f9e2ba49b117004f0d2db14906e4c0cb43cf`](https://github.com/Intelligentclown/Legal_DMS/commit/c592f9e2ba49b117004f0d2db14906e4c0cb43cf) (`origin/main`, protected merge of T183 authorization PR #396)  
**Pull Request:** [#397 — `fix(persistence): PostgreSQL file-number allocator concurrency remediation (T183, #395)`](https://github.com/Intelligentclown/Legal_DMS/pull/397)  
**Branch:** `feature/t183-file-number-allocator-concurrency`  
**Authorization Issue:** [#395 — `T183 — PostgreSQL File-Number Allocator Concurrency Remediation (Owner Authorization)`](https://github.com/Intelligentclown/Legal_DMS/issues/395)  
**Merged Prerequisite PR:** [#396 — `docs(governance): authorize T183 PostgreSQL file-number allocator concurrency remediation (#395)`](https://github.com/Intelligentclown/Legal_DMS/pull/396)  
**Reviewer:** Independent QA Reviewer (Antigravity)  
**Review Tier:** Comprehensive / Risk Tier 1  
**Date:** 2026-10-28 (Asia/Kolkata)  

---

## 1. Executive Summary & Formal QA Decision

- **Formal QA Decision:** **Approved with comments**
- **Exact Substantive Candidate SHA Evaluated:** `c50f366bbd95ca06a077069069a31a7fb38f6ae4`
- **Protected Baseline SHA:** `c592f9e2ba49b117004f0d2db14906e4c0cb43cf` (Protected merge of T183 Authorization PR #396)
- **Reviewer Independence:** Verified. Substantive candidate commit was authored by the Backend Implementation Executor (`Intelligentclown / Backend Developer`). Independent QA evaluation was conducted by Antigravity in an isolated QA reviewer capacity without author bias.
- **Scope Audit:** Strictly three (3) persistence, test, and evidence files modified (+488 / −16 lines against base `c592f9e2ba49b117004f0d2db14906e4c0cb43cf`):
  1. [`backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py`](../../backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py) (+48 / −16)
  2. [`backend/tests/integration/test_t183_file_number_allocator_concurrency.py`](../../backend/tests/integration/test_t183_file_number_allocator_concurrency.py) (+302 / −0)
  3. [`docs/reviews/T183_Implementation_Evidence.md`](T183_Implementation_Evidence.md) (+154 / −0)
- **Mandatory Review Determinations:**
  1. **Conflict Arbiter Alignment:** In `SqlAlchemyFileRepository.allocate_and_add`, the upsert conflict target was corrected from `ON CONFLICT ON CONSTRAINT uq_file_number_sequences_organization_id_matter_id` to `ON CONFLICT (matter_id)` targeting `pk_file_number_sequences` per ADR-0027.
  2. **Special Review (Savepoint Re-execution Guard):** Independently verified as mathematically necessary on PostgreSQL 16 due to speculative insertion checking non-arbiter unique indexes with `UNIQUE_CHECK_YES`. Independently reproduced 20 collisions across 20 trials without the guard. The guard is bounded (single retry), strictly scoped to SQLSTATE 23505 constraint `uq_file_number_sequences_organization_id_matter_id`, uses savepoint isolation without poisoning outer transactions, preserves atomic allocation, introduces zero duplicate records or burned numbers, and does not violate the prohibition on broad retry loops.
  3. **Concurrency Regression Verification:** Original failing test `test_same_matter_concurrent_allocation_is_unique_and_rollback_reuses_number` in `test_t138_file_migration_and_allocator.py` now passes cleanly. Comprehensive new test suite in `test_t183_file_number_allocator_concurrency.py` passed all 6 lifecycle scenarios (16 concurrent first allocations, 10 subsequent allocations, rollback and reuse, repeated trials, multi-Matter concurrency, and cross-tenant fail-closed isolation). Repeated trials (10/10 runs, 50 trials x 16 workers) achieved 100% pass rate with zero deadlocks or collisions.
  4. **Full Backend Suite Certification:** Independently executed against isolated clean PostgreSQL 16 database `legal_dms_t183_clean` migrated to head `b155caa6d4e1`: **925 passed, 21 skipped, 87 warnings, 0 failed in 492.48s (exit code 0)**. Zero failures.
  5. **T182 Preservation & Isolation:** Verified that the T182 worktree (`codex/t182-storage-durability` at `C:\Users\Dhimant Patel\.codex\worktrees\t182-storage-certification\Legal_DMS_Clean`) was completely untouched. T182 uncommitted storage durability files remain preserved.
  6. **Invariants & Preserved Boundaries:** Zero schema changes, zero Alembic migrations, zero process locks (`asyncio.Lock`), zero API route changes, zero ADR modifications, and zero unapproved forecast modifications. T183 remains `Authorized` and not `Done`.
- **Blocking Findings:** Zero (0).
- **Non-Blocking Advisories:** Four (4) advisories recorded.

---

## 2. Remote Provenance & Commit Ancestry

- **Repository:** `Intelligentclown/Legal_DMS`
- **Protected Base Commit:** [`c592f9e2ba49b117004f0d2db14906e4c0cb43cf`](https://github.com/Intelligentclown/Legal_DMS/commit/c592f9e2ba49b117004f0d2db14906e4c0cb43cf) (Merge PR #396: `docs(governance): authorize T183 PostgreSQL file-number allocator concurrency remediation (#395)`)
- **Candidate Commit (HEAD):** [`c50f366bbd95ca06a077069069a31a7fb38f6ae4`](https://github.com/Intelligentclown/Legal_DMS/commit/c50f366bbd95ca06a077069069a31a7fb38f6ae4)
- **Commit Subject:** `fix(persistence): align file-number allocator conflict arbiter with matter_id primary key (T183)`
- **Pull Request:** [#397 — `fix(persistence): PostgreSQL file-number allocator concurrency remediation (T183, #395)`](https://github.com/Intelligentclown/Legal_DMS/pull/397)
- **Branch:** `feature/t183-file-number-allocator-concurrency`
- **Merge Base:** `git merge-base origin/main HEAD` -> `c592f9e2ba49b117004f0d2db14906e4c0cb43cf` (clean 1-commit linear fast-forward delta).
- **Author:** Dhimant Patel (`Intelligentclown`)
- **Reviewer Independence:** Verified. Independent QA review performed by Antigravity in separate QA reviewer capacity; no implementation code or candidate commits authored by this reviewer.

---

## 3. Critical Technical & Architectural Review

### 3.1 Code Inspection of `SqlAlchemyFileRepository.allocate_and_add`
In [`backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py`](../../backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py):
```python
    async def allocate_and_add(self, file: File) -> File:
        # PostgreSQL's conflict update locks only this Matter's counter row.
        # The enclosing request transaction commits/rolls back both statements.
        stmt = text("""
            INSERT INTO file_number_sequences (matter_id, organization_id, next_number)
            VALUES (:matter_id, :organization_id, 2)
            ON CONFLICT (matter_id)
            DO UPDATE
            SET next_number = file_number_sequences.next_number + 1
            WHERE file_number_sequences.organization_id = EXCLUDED.organization_id
            RETURNING next_number - 1
        """)
        params = {"matter_id": file.matter_id, "organization_id": file.organization_id}

        try:
            async with self._session.begin_nested():
                result = await self._session.execute(stmt, params)
                file.file_number = int(result.scalar_one())
                self._session.add(file)
                await self._session.flush()
        except IntegrityError as exc:
            # PostgreSQL 16 speculative insertion evaluates secondary unique indexes with
            # UNIQUE_CHECK_YES. When concurrent first allocations collide on the redundant
            # composite unique constraint uq_file_number_sequences_organization_id_matter_id,
            # the savepoint unwinds cleanly and a single immediate retry against the
            # now-existing row executes the atomic DO UPDATE path under row lock.
            if "uq_file_number_sequences_organization_id_matter_id" in str(exc):
                async with self._session.begin_nested():
                    result = await self._session.execute(stmt, params)
                    file.file_number = int(result.scalar_one())
                    self._session.add(file)
                    await self._session.flush()
            else:
                raise
        return file
```

### 3.2 ADR-0027 & Invariant Verification
1. **Primary Key Conflict Arbiter Alignment:** The statement specifies `ON CONFLICT (matter_id)`. The target index is `pk_file_number_sequences`, strictly complying with ADR-0027 lines 124–129 and 197–200.
2. **Single-Statement Atomic Allocation:** Generation executes in a single atomic SQL statement returning the allocated counter (`RETURNING next_number - 1`). No external or in-process locks are used.
3. **Transaction & Rollback Semantics:** The operation operates within the caller's transaction session (`ADR/0020` / `get_db()`). Rollback of the session rolls back both the File row and the counter increment, preserving sequential numbers for subsequent attempts without burning numbers.
4. **Tenant Isolation:** The clause `WHERE file_number_sequences.organization_id = EXCLUDED.organization_id` ensures cross-tenant counter hijacking fails closed.
5. **Zero Process Locks:** No `asyncio.Lock` or threading locks were added. Concurrency safety is enforced natively by PostgreSQL row-level locks on the sequence row.
6. **Zero Migrations:** No schema changes or Alembic migration files were added. Sole Alembic migration frontier remains `b155caa6d4e1`.

### 3.3 Special Review: Savepoint-Isolated Re-execution Guard
The Independent QA Reviewer conducted a dedicated physical investigation into the savepoint-isolated re-execution guard:

1. **Physical Defect Reproducibility:**  
   In PostgreSQL 16, table `file_number_sequences` possesses two unique constraints created in migration `b8c4d2e1f7a9`:
   - `pk_file_number_sequences` on `(matter_id)`
   - `uq_file_number_sequences_organization_id_matter_id` on `(organization_id, matter_id)`
   
   During speculative insertion (`ExecInsertIndexTuples`), PostgreSQL evaluates the conflict arbiter index (`pk_file_number_sequences`) with `UNIQUE_CHECK_PARTIAL`, but evaluates the non-arbiter unique index (`uq_file_number_sequences_organization_id_matter_id`) with `UNIQUE_CHECK_YES`.
   
   The QA Reviewer independently executed a standalone test harness omitting the try/except guard against isolated PostgreSQL 16. Across 20 trials of 16 concurrent workers attempting initial allocation on uninitialized Matters, **20 constraint collisions** (`IntegrityError / UniqueViolationError: uq_file_number_sequences_organization_id_matter_id`, SQLSTATE 23505) occurred. This proves conclusively that the collision is physically reproducible on PostgreSQL 16.
2. **Necessity of the Guard:**  
   Under the repository's strict scope exclusions, schema modifications and Alembic migrations (e.g. dropping the redundant composite unique constraint) are prohibited. Therefore, handling this PostgreSQL 16 speculative insertion artifact at the data-access layer is strictly necessary to prevent concurrent first-allocation failures.
3. **Exception Classification Specificity:**  
   The handler catches `IntegrityError` and explicitly inspects `if "uq_file_number_sequences_organization_id_matter_id" in str(exc):`. Any other integrity violation (e.g., primary key violations on `files`, foreign key violations, or check constraints) executes `else: raise` and propagates immediately.
4. **Bounded Single-Shot Execution:**  
   The retry executes exactly once. There is no `while` loop, recursion, or retry counter. If the second attempt fails for any reason, the exception propagates unhandled.
5. **Savepoint Transaction Safety:**  
   The initial attempt is wrapped in `async with self._session.begin_nested():`. When the collision occurs, SQLAlchemy issues `ROLLBACK TO SAVEPOINT`, cleanly unwinding the aborted insert without poisoning the parent transaction (avoiding PostgreSQL `current transaction is aborted, commands ignored until end of transaction block` 25P02 error state). The retry opens a fresh savepoint.
6. **Absence of Side Effects:**  
   Because the initial insert aborted and rolled back to the savepoint before `self._session.add(file)` or flush committed, no phantom or duplicate File rows are created. In the second attempt, the initial worker's committed row is already present; the statement takes the `DO UPDATE` row-lock branch, returning the next sequential number.
7. **Prohibition on Broad Retry Loops:**  
   The implementation complies with the authorization's prohibition on broad retry loops. It is a bounded, single-statement savepoint recovery specifically addressing a known database engine speculative insertion constraint check.

---

## 4. PostgreSQL Concurrency & Regression Verification Matrix

| Verification Scenario | Scope & Parameters | Independent QA Result | Details |
| :--- | :--- | :--- | :--- |
| **Concurrent First Allocation** | 16 parallel workers on uninitialized Matter | **PASS** | 16 distinct numbers allocated (1..16 sequential); 0 collisions; exactly 1 sequence row created with `next_number=17`. |
| **Subsequent Allocation** | 10 parallel workers on initialized Matter | **PASS** | 10 distinct numbers allocated (17..26 sequential); sequence row advanced to `next_number=27`. |
| **Rollback & Number Reuse** | Allocation in rolled-back session followed by committed allocation | **PASS** | Rolled back allocation returned 27; subsequent committed allocation reused 27; sequence row advanced to 28. |
| **Repeated First-Allocation Trials** | 5 distinct Matters x 8 concurrent workers (40 allocations) | **PASS** | All 5 trials allocated numbers 1..8 sequentially with zero collisions; each sequence row advanced to `next_number=9`. |
| **Simultaneous Multi-Matter Concurrency** | 3 distinct Matters x 8 parallel workers (24 allocations simultaneously) | **PASS** | All 3 Matters allocated numbers 1..8 sequentially without cross-matter interference. |
| **Tenant & Matter Isolation** | Attempt allocation for Matter with mismatched `organization_id` | **PASS** | Cross-tenant allocation failed closed with error; sequence counter and tenant ownership remained uncorrupted. |
| **Repeated Concurrency Stress** | 10 consecutive test runs of `test_t183` and `test_t138` | **PASS (10/10)** | 100% pass rate across repeated runs; zero flakes, zero deadlocks, zero collisions. |
| **T138 Concurrency Regression** | `backend/tests/integration/test_t138_file_migration_and_allocator.py` | **PASS** | 2 passed in 17.15s; original defect failure completely resolved. |

---

## 5. Full Backend Test Suite Certification

The Independent QA Reviewer executed the complete backend test suite against clean isolated PostgreSQL 16 database `legal_dms_t183_clean` migrated to Alembic head `b155caa6d4e1`:
```text
uv run pytest
======================== 925 passed, 21 skipped, 87 warnings in 492.48s (08:12) ========================
Exit code: 0
```

### Analysis of Test Results:
1. **Zero Failures:** 925 tests passed cleanly with 0 failures and 0 errors.
2. **Skipped Tests Audit (21 skipped):**
   - 5 tests skipped in `test_get_db_transaction_policy.py`: mock driver transaction policy skips.
   - 8 tests skipped in `test_organizations_users_rls.py`: tenant RLS superuser/isolated connection skips.
   - 8 tests skipped in `test_organizations_users_rls_pg16.py`: tenant RLS dedicated harness skips.
   All 21 skips are established, pre-existing environment skips, identical to prior certified baselines (e.g. T175, T177, T180).
3. **Warnings Audit (87 warnings):**
   - 1 warning from `fastapi/testclient.py`: StarletteDeprecationWarning (`Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead`).
   - 9 warnings from `starlette/_exception_handler.py`: StarletteDeprecationWarning (`HTTP_422_UNPROCESSABLE_ENTITY` vs `HTTP_422_UNPROCESSABLE_CONTENT`).
   - 77 warnings from `jwt/api_jwt.py`: `InsecureKeyLengthWarning` on 11-byte and 18-byte local test JWT secret keys.
   All 87 warnings are pre-existing library deprecation or test fixture warnings. Zero application code warnings.
4. **Current-Head Backend Certification:** Certified complete and clean against isolated PostgreSQL 16 at candidate HEAD.

---

## 6. Static Analysis & Governance Validation

| Check | Target / Command | Result | Notes |
| :--- | :--- | :--- | :--- |
| **Black Formatting** | `uv run black --check src tests` | **PASS** | 300 files left unchanged. |
| **Ruff Linting** | `uv run ruff check src tests` | **PASS** | 0 lint errors found. |
| **Governance Consistency** | `python scripts/governance_validate.py --report` | **PASS** | 0 warnings, 0 errors. Internal consistency confirmed. Required ADRs unresolved: `[12, 15, 16, 17, 20]`. |
| **Delivery Calendar Validation** | `python scripts/delivery_calendar.py` via `scripts/governance_validate.py` | **PASS** | Schema Version 3 valid; zero scheduling cycles. |
| **Current Context Manifest** | `python scripts/current_context_manifest.py` | **PASS** | Emitted valid JSON; `discrepancies: []`, `latest_authorized: "T183"`, `latest_done: "T181"`. |
| **Governance Unit Tests** | `python -m unittest scripts.tests.test_governance_validate` | **PASS** | 88/88 unit tests passed in 0.300s. |
| **Context Manifest Unit Test** | `python -m unittest scripts.tests.test_current_context_manifest -v` | **1 EXPECTED FAILURE** | Line 30 `'T181' != 'T170'`. Pre-existing historical test debt originating in T171; preserved untouched. |
| **Diff Whitespace / Hygiene** | `git diff --check origin/main..HEAD` | **PASS (with comment)** | Flags lines 3–10 in `docs/reviews/T183_Implementation_Evidence.md` due to standard GFM double-space line breaks. Cosmetic observation noted in QA-T183-IMPL-ADV-01. |
| **GitHub Actions CI** | PR [#397](https://github.com/Intelligentclown/Legal_DMS/pull/397) at `c50f366bbd95ca06a077069069a31a7fb38f6ae4` | **PASS** | All 8 workflow runs succeeded: Backend validation (23s, 30s), Frontend validation (38s, 52s), Governance consistency (7s, 5s), Release build verification (28s, 31s). |

---

## 7. Acceptance Criteria Verification Matrix (AC-01 through AC-07)

| Criterion | Description | Status | Evidence Reference & Findings | Residual Risk |
| :--- | :--- | :--- | :--- | :--- |
| **AC-01** | **Conflict Arbiter Alignment:** The PostgreSQL upsert conflict arbiter in `SqlAlchemyFileRepository` targets the `matter_id` primary key (`pk_file_number_sequences` / `ON CONFLICT (matter_id)`) per ADR-0027, eliminating concurrent initialization collisions. | **PASS** | Verified in [`backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py:59-60`](../../backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py#L59-L60). Arbiter explicitly targets `(matter_id)`. | None. Constraint alignment verified against database model and ADR-0027. |
| **AC-02** | **Single-Statement Atomic Allocation:** File-number generation executes in a single atomic SQL statement returning the allocated counter without application-level locks. | **PASS** | Verified in [`backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py:56-64`](../../backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py#L56-L64). Single atomic SQL statement with `RETURNING next_number - 1`. Zero application locks. | None. Row-level serialization enforced by PostgreSQL. |
| **AC-03** | **Transaction & Rollback Semantics:** Sequence counter increment and File creation share the same database transaction boundary; failed or rolled back File creation releases/rolls back the counter without burning numbers. | **PASS** | Verified in `test_t183_file_number_allocator_concurrency.py` section 3 and `test_t138_file_migration_and_allocator.py`. Session rollback cleanly reverts counter state. | None. Enclosed within `get_db()` transaction boundary (`ADR/0020`). |
| **AC-04** | **Concurrent First-Allocation Uniqueness:** Concurrent first-allocation attempts for the same Matter on clean PostgreSQL 16 allocate distinct sequential numbers without unique-constraint or primary-key collisions. | **PASS** | Verified across 16 parallel workers in `test_t183` section 1, 5 trials x 8 workers in section 4, and 12 workers in `test_t138`. All numbers strictly sequential (1..N) with 0 collisions. | None. Speculative insertion collision resolved deterministically. |
| **AC-05** | **Rollback & Reuse Verification:** Rolled back allocation attempts allow subsequent allocation attempts to reuse the rolled-back sequence number. | **PASS** | Verified in `test_t183` section 3: allocation rolled back at 27; subsequent committed allocation reused 27; sequence counter advanced to 28. | None. Verified by direct database queries. |
| **AC-06** | **Repeated Concurrency Regression Coverage:** Multi-worker/multi-session concurrency regression tests pass repeatedly against clean isolated PostgreSQL 16 without flakes or deadlocks. | **PASS** | Verified: 10/10 consecutive runs of `test_t183`, 10/10 consecutive runs of `test_t138`, and 50 repeated multi-worker trials passed cleanly without a single flake or deadlock. | None. High-concurrency stability proved under load. |
| **AC-07** | **Full Backend Suite Certification:** The complete backend test suite runs cleanly with zero failures and is certified against isolated PostgreSQL 16 at candidate HEAD. | **PASS** | Independently certified: 925 passed, 21 skipped, 87 warnings, 0 failed in 492.48s (exit code 0) on clean migrated database `legal_dms_t183_clean`. | None. 100% passing suite certified. |

---

## 8. Findings & Non-Blocking Advisories

### 8.1 Blocking Findings
**Zero (0) blocking findings.**

### 8.2 Non-Blocking Advisories

- **QA-T183-IMPL-ADV-01 (Markdown Line-Break Whitespace in Implementation Evidence):**  
  `git diff --check` flags lines 3–10 in [`docs/reviews/T183_Implementation_Evidence.md`](T183_Implementation_Evidence.md#L3-L10) for trailing whitespace. In GitHub Flavored Markdown, two trailing spaces are standard syntax for hard line breaks. This is a cosmetic observation conforming to GFM and is strictly non-blocking.
- **QA-T183-IMPL-ADV-02 (Pre-existing Baseline Debt in Context Manifest Test):**  
  [`scripts/tests/test_current_context_manifest.py:30`](../../scripts/tests/test_current_context_manifest.py#L30) contains a hardcoded assertion `assertEqual(payload["governance_frontier"]["latest_done"], "T170")` dating to T171 closeout. Running `python -m unittest scripts/tests/test_current_context_manifest.py` fails on this hardcoded check (`'T181' != 'T170'`). This is confirmed pre-existing test debt originating in T171 and documented across prior QA reviews (T172–T183 Authorization). Candidate PR #397 properly refrained from editing this test to maintain documentation/scope boundaries.
- **QA-T183-IMPL-ADV-03 (Redundant Unique Constraint Remediation in Future Migration Task):**  
  Table `file_number_sequences` retains both `pk_file_number_sequences` on `matter_id` and the redundant composite unique constraint `uq_file_number_sequences_organization_id_matter_id` on `(organization_id, matter_id)`. In a future task where database migrations are authorized, dropping this redundant composite constraint will eliminate the need for speculative insertion savepoint unwinding in PostgreSQL. Under current schema invariants, the savepoint-isolated re-execution provides deterministic zero-flake execution.
- **QA-T183-IMPL-ADV-04 (T182 Dependency Unblocking and Recertification Protocol):**  
  T182 final backend certification was blocked by the allocator defect. T182 storage durability evidence and implementation remain preserved on branch `codex/t182-storage-durability`. After T183 completes PR 2 and PR 3 governance closeout into protected `main`, T182 must reconcile against updated protected `main` and rerun full backend certification on clean isolated PostgreSQL 16 before T182 Implementation PR 2 is published.

---

## 9. Protected Merge Recommendation & Lifecycle Handoff

Candidate PR [#397](https://github.com/Intelligentclown/Legal_DMS/pull/397) satisfies all implementation and verification requirements under [`PROJECT_WORKFLOW.md §3.1`](../../PROJECT_WORKFLOW.md#31-required-adr--governance-hardening-lifecycle-three-pr). It accurately resolves the PostgreSQL file-number allocator concurrency defect per ADR-0027, adds comprehensive concurrency tests, preserves all architectural, transactional, and worktree invariants, and passes full backend test suite certification and exact-head CI.

**Recommendation:** **Merge PR [#397](https://github.com/Intelligentclown/Legal_DMS/pull/397)** into protected `main` under standard branch protection rules via the Git/CI PR Manager role.

---

## 10. Mandatory STOP Boundaries

In strict accordance with [`PROJECT_WORKFLOW.md §3.1`](../../PROJECT_WORKFLOW.md#31-required-adr--governance-hardening-lifecycle-three-pr), [`docs/prompts/QAReviewer.md`](../prompts/QAReviewer.md), and the standing Independent QA Reviewer instructions:
- **Do not merge PR #397 in this session.**
- **Do not modify production implementation files.**
- **Do not create T183 Governance Closeout PR 3.**
- **Do not mark T183 or T182 Done.**
- **Do not resume T182 certification or publish T182 Implementation PR 2.**
- **Do not authorize T184 or any successor tasks.**
- **Do not perform Documentation Manager or Git/CI PR Manager duties.**

Execution halts here. Control is returned to the Project Owner / Control Tower for Git/CI PR Manager protected merge verification.
