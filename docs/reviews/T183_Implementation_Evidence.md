# T183 Implementation Evidence — PostgreSQL File-Number Allocator Concurrency Remediation

**Task:** T183 — PostgreSQL File-Number Allocator Concurrency Remediation  
**Lifecycle Stage:** Implementation PR 2 of 3 (`PROJECT_WORKFLOW.md §3.1`)  
**Authorization Issue:** [#395](https://github.com/Intelligentclown/Legal_DMS/issues/395)  
**Authorization PR:** [#396](https://github.com/Intelligentclown/Legal_DMS/pull/396) — MERGED  
**Expected & Verified Protected Main Baseline:** `c592f9e2ba49b117004f0d2db14906e4c0cb43cf`  
**Execution Date:** 2026-10-28 (Asia/Kolkata)  
**Role:** Backend Implementation Executor  
**Review Tier:** Comprehensive / Risk Tier 1  

---

## 1. Executive Summary & Defect Root Cause

### 1.1 Verified Protected-Main Baseline
- Protected main SHA: `c592f9e2ba49b117004f0d2db14906e4c0cb43cf` (Merge pull request #396).
- Implementation branch `feature/t183-file-number-allocator-concurrency` branched directly from `c592f9e2ba49b117004f0d2db14906e4c0cb43cf`.

### 1.2 Root Cause Analysis
During T182 backend certification on protected-main-identical code, `test_t138_file_migration_and_allocator.py` failed with:
```text
IntegrityError: (sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class 'asyncpg.exceptions.UniqueViolationError'>: duplicate key value violates unique constraint "pk_file_number_sequences"
DETAIL: Key (matter_id)=(...) already exists.
```

Table `file_number_sequences` carries two unique constraints created in migration `b8c4d2e1f7a9`:
1. `pk_file_number_sequences` on `(matter_id)` (Primary Key).
2. `uq_file_number_sequences_organization_id_matter_id` on `(organization_id, matter_id)` (redundant composite unique constraint).

The original implementation in `backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py` targeted:
`ON CONFLICT ON CONSTRAINT uq_file_number_sequences_organization_id_matter_id`.

In PostgreSQL 16:
- An upsert conflict arbiter can only target one index/constraint.
- During speculative insertion (`ExecInsert` / `ExecInsertIndexTuples`), the targeted arbiter index is evaluated with `UNIQUE_CHECK_PARTIAL`, while all non-arbiter unique indexes are evaluated with `UNIQUE_CHECK_YES`.
- When targeting `uq_file_number_sequences_organization_id_matter_id`, concurrent initial allocations collided on the non-arbiter primary key `pk_file_number_sequences`, raising `UniqueViolationError`.
- Conversely, when targeting `ON CONFLICT (matter_id)` per ADR-0027, the primary key is evaluated as the arbiter with `UNIQUE_CHECK_PARTIAL`, but the secondary redundant constraint `uq_file_number_sequences_organization_id_matter_id` is evaluated with `UNIQUE_CHECK_YES`. In concurrent first-allocation stampedes before the initial row is committed, speculative insertion checks on the secondary index can collide, raising `UniqueViolationError: uq_file_number_sequences_organization_id_matter_id`.

### 1.3 Exact Production Correction
In `backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py`:
1. Updated the conflict arbiter from `ON CONFLICT ON CONSTRAINT uq_file_number_sequences_organization_id_matter_id` to `ON CONFLICT (matter_id)` strictly matching the primary key and ADR-0027 specifications.
2. Preserved the savepoint boundary (`async with self._session.begin_nested():`).
3. Added isolated handling for the PostgreSQL 16 speculative insertion collision on `uq_file_number_sequences_organization_id_matter_id`: if and only if concurrent initial workers encounter the secondary constraint collision on the uninitialized row, the savepoint rolls back the collided statement cleanly without poisoning the outer request transaction, and immediately re-executes the exact same atomic upsert statement. Because the initial row is now inserted, the re-execution cleanly takes the `DO UPDATE` row-lock path without speculative insertion.
4. Preserved single-statement atomic counter allocation, transaction boundaries (`get_db()` / `ADR/0020`), tenant isolation (`WHERE file_number_sequences.organization_id = EXCLUDED.organization_id`), and rollback/number-reuse semantics.
5. Strictly zero process locks (`asyncio.Lock`), zero broad retry loops, zero schema modifications, and zero Alembic migrations.

---

## 2. ADR-0027 Conformance

| ADR-0027 Requirement | Conformance Status | Implementation Detail |
| --- | --- | --- |
| Dedicated generator-row table (`file_number_sequences`) | **Conformant** | Utilizes existing `file_number_sequences` table without schema modifications. |
| Single atomic upsert targeting `matter_id` | **Conformant** | Executes `INSERT INTO file_number_sequences ... ON CONFLICT (matter_id) DO UPDATE SET next_number = file_number_sequences.next_number + 1 WHERE ... RETURNING next_number - 1`. |
| Multi-process concurrency safe via row locks | **Conformant** | Database-level row locking serializes concurrent allocations across independent worker processes. No in-process Python locks. |
| Correct rollback behavior (no burned gaps on aborted allocation) | **Conformant** | Shares the session transaction boundary under `get_db()`. Aborted/rolled-back allocations roll back the counter row; subsequent allocations reuse the exact same number. |
| Tenant boundary enforcement | **Conformant** | Verified `organization_id = EXCLUDED.organization_id` prevents cross-tenant hijacking; cross-tenant allocations fail closed. |

---

## 3. Environment & Isolation

| Parameter | Configuration / Value |
| --- | --- |
| Host OS | Windows (PowerShell) |
| Python Environment | Python 3.14.4 via `uv` virtual environment in `backend/` |
| PostgreSQL Database Server | PostgreSQL 16.15 (Docker container `legal_dms_postgres`) on `localhost:5433` |
| Isolated Clean Database | `legal_dms_t183_clean` (freshly provisioned and migrated to Alembic head `b155caa6d4e1`) |
| Disposable Test Databases | `legal_dms_t183_allocator`, etc., provisioned and dropped automatically during integration tests |
| Main Repo Baseline | `D:\Code\Legal_dms` (`main` at `c592f9e2ba49b117004f0d2db14906e4c0cb43cf`) |
| T183 Worktree | `D:\Code\Legal_DMS_T183` (`feature/t183-file-number-allocator-concurrency`) |
| T182 Worktree Isolation | `C:\Users\Dhimant Patel\.codex\worktrees\t182-storage-certification\Legal_DMS_Clean` (preserved completely unmodified) |

---

## 4. Verification Evidence & Test Execution

### 4.1 Focused Concurrency Regression Suite
Added comprehensive regression coverage in `backend/tests/integration/test_t183_file_number_allocator_concurrency.py`:
- Concurrent first allocation on uninitialized Matter (16 parallel workers).
- Subsequent concurrent allocation on initialized Matter (10 parallel workers).
- Transaction rollback and sequence number reuse.
- Repeated first-allocation trials across distinct Matters (5 trials x 8 workers).
- Concurrent allocations across multiple Matters simultaneously (3 matters x 8 workers).
- Cross-tenant fail-closed isolation guard.

**Execution:**
```text
uv run pytest tests/integration/test_t183_file_number_allocator_concurrency.py -v
1 passed, 1 warning in 8.15s (exit code 0)
```

**Repeated Execution Certification:**
- Ran 10 consecutive executions of `test_t183_file_number_allocator_concurrency.py`: **10/10 passed, 0 flakes**.
- Ran 10 consecutive executions of `test_t138_file_migration_and_allocator.py`: **10/10 passed, 0 flakes**.
- Ran 50 repeated stress trials with 16 concurrent workers (800 total allocations): **50/50 passed, 0 failures**.

### 4.2 Related File & Tenant Regression Tests
- `tests/integration/test_t137_file_document_tenant_foundation.py`: **4 passed in 30.28s**.
- `tests/integration/test_t138_file_migration_and_allocator.py`: **2 passed in 17.47s**.

### 4.3 Code Quality, Linting & Governance Checks
- `uv run black --check src tests`: **All done! 300 files left unchanged (exit code 0)**.
- `uv run ruff check src tests`: **All checks passed! (exit code 0)**.
- `python scripts/governance_validate.py --report`: **OK (exit code 0)**.
- `python scripts/delivery_calendar.py`: **OK (exit code 0)**.
- `python scripts/current_context_manifest.py`: **Emitted valid JSON, 0 discrepancies (exit code 0)**.

### 4.4 Full Backend Test Suite Certification
Executed against clean isolated database `legal_dms_t183_clean` migrated to head `b155caa6d4e1`:
```text
uv run pytest -v
========== 925 passed, 21 skipped, 87 warnings in 487.15s (08:07) ==========
Exit code: 0
```
**Zero failures. Full backend test suite certified cleanly.**

---

## 5. Acceptance Criteria Evidence Matrix

| Criterion | Description | Status | Evidence Reference |
| --- | --- | --- | --- |
| **AC-01** | Conflict Arbiter Alignment: Targets `matter_id` primary key (`pk_file_number_sequences` / `ON CONFLICT (matter_id)`) per ADR-0027. | **PASS** | `backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py:60` |
| **AC-02** | Single-Statement Atomic Allocation: Sequential file numbers generated in single atomic SQL statement without application distributed/in-process locks. | **PASS** | `backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py:54-65` |
| **AC-03** | Transaction & Rollback Semantics: Sequence counter and File creation share transaction boundary under `get_db()`; aborted creation does not burn numbers. | **PASS** | Verified in `test_t183` (step 3) and `test_t138`. Rollback followed by allocation yields identical number. |
| **AC-04** | Concurrent First-Allocation Uniqueness: Concurrent first allocation for same Matter on clean PostgreSQL 16 allocates distinct sequential numbers without collision. | **PASS** | Verified in `test_t183` (16 workers: 1..16 sequential, 0 duplicates) and `test_t138` (12 workers: 1..12 sequential). |
| **AC-05** | Rollback & Reuse Verification: Rolled back allocation allows subsequent allocation to reuse rolled-back number. | **PASS** | `test_t183` step 3: rollback on counter 27 reuses 27 on subsequent committed allocation. |
| **AC-06** | Repeated Concurrency Regression Coverage: Multi-worker concurrency regression tests pass repeatedly against live isolated PostgreSQL 16 without flakes. | **PASS** | 10 repeated runs of `test_t183` and 10 repeated runs of `test_t138` all passed cleanly (100% pass rate). |
| **AC-07** | Full Backend Suite Certification: Complete backend test suite runs cleanly with zero failures on isolated PostgreSQL 16. | **PASS** | 925 passed, 21 skipped, 87 warnings, 0 failed in 487.15s (exit code 0) on `legal_dms_t183_clean`. |

---

## 6. Worktree & Task Isolation Evidence

- **T182 Worktree Status:**
  `git -C "C:\Users\Dhimant Patel\.codex\worktrees\t182-storage-certification\Legal_DMS_Clean" status`
  Output confirms:
  - Branch: `codex/t182-storage-durability`
  - Uncommitted changes in `local_file_storage.py`, `test_local_file_storage.py`, `test_t182_physical_document_storage.py`, `Phase57.md`, and `T182_Implementation_Evidence.md` remain completely unmodified and preserved.
  - Zero T182 files touched by T183.
- **T183 Commit Boundaries:**
  Only T183-authorized implementation (`sqlalchemy_file_repository.py`), test (`test_t183_file_number_allocator_concurrency.py`), and evidence (`T183_Implementation_Evidence.md`) are modified/staged.
  No schema files or Alembic migration files modified.
  No governance closeout files modified (PR 3 is strictly excluded).

---

## 7. Residual Risks & Advisories

- **Advisory (Redundant Unique Constraint):** Table `file_number_sequences` retains the redundant composite unique constraint `uq_file_number_sequences_organization_id_matter_id` alongside the primary key `pk_file_number_sequences` on `matter_id`. In a future task where Alembic migrations are authorized, dropping this redundant constraint will allow standard speculative insertion without savepoint unwind. Under current schema invariants, the savepoint-isolated re-execution provides deterministic zero-flake execution.
- **Starlette Deprecation Warning:** Starlette `TestClient` / HTTPX deprecation warning (`Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead`) is pre-existing across all test runs.
- **HMAC Key Length Warning:** InsecureKeyLengthWarning in JWT tests is pre-existing for local testing secret fixtures.
