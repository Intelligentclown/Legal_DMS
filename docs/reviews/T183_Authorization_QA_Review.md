# T183 Independent QA Review — PostgreSQL File-Number Allocator Concurrency Remediation (Authorization)

**Task:** T183 — PostgreSQL File-Number Allocator Concurrency Remediation  
**Lifecycle Stage:** Pre-implementation authorization and delivery-calendar registration (`PROJECT_WORKFLOW.md §3.1` — PR 1 of 3)  
**Candidate Evaluated (Substantive Head):** [`5a4496c772279e422338cb1babb2fa5c365a385b`](https://github.com/Intelligentclown/Legal_DMS/commit/5a4496c772279e422338cb1babb2fa5c365a385b)  
**Protected Base Commit:** [`6720bcd281533ec2badc3ee3e7b92a0c12c52cb2`](https://github.com/Intelligentclown/Legal_DMS/commit/6720bcd281533ec2badc3ee3e7b92a0c12c52cb2) (`origin/main`, merge PR #394 — T182 authorization and calendar registration)  
**Pull Request:** [#396 — `docs(governance): authorize T183 PostgreSQL file-number allocator concurrency remediation (#395)`](https://github.com/Intelligentclown/Legal_DMS/pull/396)  
**Branch:** `docs/t183-authorization-calendar`  
**Authorization Issue:** [#395 — `T183 — PostgreSQL File-Number Allocator Concurrency Remediation (Owner Authorization)`](https://github.com/Intelligentclown/Legal_DMS/issues/395)  
**Reviewer:** Independent QA Reviewer (Antigravity)  
**Review Tier:** Comprehensive / Risk Tier 1  
**Date:** 2026-10-28 (Asia/Kolkata)  

---

## 1. Executive Summary & Formal QA Decision

- **Formal QA Decision:** **Approved with comments**
- **Exact Substantive Candidate SHA Evaluated:** `5a4496c772279e422338cb1babb2fa5c365a385b`
- **Protected Baseline SHA:** `6720bcd281533ec2badc3ee3e7b92a0c12c52cb2` (Protected merge of T182 Authorization PR #394)
- **Reviewer Independence:** Verified. Substantive authorization candidate commit was authored by the Documentation Manager (`Intelligentclown / Documentation Manager`). Independent QA evaluation was conducted by Antigravity in an isolated QA review role without author bias.
- **Scope Audit:** Strictly seven (7) governance, planning, and documentation files modified (+194 / −4 lines against base `6720bcd281533ec2badc3ee3e7b92a0c12c52cb2`):
  1. [`IMPLEMENTATION_QUEUE.md`](../../IMPLEMENTATION_QUEUE.md) (+3 / −1)
  2. [`PROJECT_STATE.json`](../../PROJECT_STATE.json) (+1 / −1)
  3. [`docs/delivery_calendar.json`](../delivery_calendar.json) (+66 / −2)
  4. [`docs/DELIVERY_CALENDAR.md`](../DELIVERY_CALENDAR.md) (+4 / −0)
  5. [`docs/ProjectStatus.md`](../ProjectStatus.md) (+48 / −0)
  6. [`docs/SessionReport.md`](../SessionReport.md) (+27 / −0)
  7. [`docs/AI_HANDOVER.md`](../AI_HANDOVER.md) (+48 / −0)
- **Mandatory Review Determinations:**
  1. **Task Identity & Approval Authenticity:** Verified. T183 authorizes PostgreSQL file-number allocator concurrency remediation as approved by the Project Owner on 28 October 2026 in Issue #395 following root-cause reproduction during T182 certification. Task identifier T183 is the valid next sequential integer and is not duplicated.
  2. **Ancestry & Baseline Integrity:** The candidate branch cleanly forks from protected `main` at `6720bcd281533ec2badc3ee3e7b92a0c12c52cb2` (merge PR #394, T182 authorization). Exactly 1 commit ahead, 0 behind.
  3. **Governance Synchronization & Concurrent Tasks:** `PROJECT_STATE.json` correctly advances `latestTaskAuthorized` to `"T183"` while retaining `latestTaskDone="T181"` and `inProgressTransitions=[]`. `IMPLEMENTATION_QUEUE.md` registers T183 as `Authorized`. T182 remains `Authorized` and not `Done`. The repository governance framework permits authorizing a separate remediation task while a prior task remains open between `latestTaskDone` and `latestTaskAuthorized` (precedents T176/T175, T168/T167, T158–T159/T157, T99–T100/T98).
  4. **Calendar Registration & Scheduling Topology:** Registered under M2 `ux` lane, planned `2026-10-28` through `2026-10-31` (4 days), predecessor T181 (Done), defect evidence T182. T182's finish-to-start dependency is updated to `["T181", "T183"]`. Scheduling topology is an acyclic directed graph with zero cycles. Actuals and completion evidence are strictly null. Delivery Calendar Schema Version 3 remains intact.
  5. **Milestone Dates & Provenance Preservation:** M1 actual date `2026-10-25` and Schema V3 completion provenance (SHA-256 evidence digest `aed7462d9d90b9a97133e33166c536129df280568fa36f4a4b07261e0bb47131`, variance `-21` days Early) are fully preserved. M2 (`2026-12-31`, actual null) and M3 (`2027-02-28`, actual null) forecasts remain unchanged.
  6. **Technical Scope & ADR-0027 Alignment:** Root cause is accurately characterized: in `SqlAlchemyFileRepository.allocate_and_add`, the upsert conflict arbiter currently targets `uq_file_number_sequences_organization_id_matter_id`, causing concurrent first allocations for the same Matter to collide on the table's primary key `pk_file_number_sequences` (`matter_id`). ADR-0027 mandates Matter-scoped atomic counter initialization using `matter_id` conflict target (`ON CONFLICT (matter_id)`). Proposed alignment operates under the existing database schema and constraints without Alembic migrations.
  7. **Future Acceptance Criteria Verification:** AC-01 through AC-07 clearly define executable, testable requirements for conflict arbiter alignment, single-statement atomic allocation, transaction/rollback semantics under `get_db()`, concurrent first-allocation uniqueness on clean PostgreSQL 16, rollback/number reuse, live PostgreSQL 16 multi-session regression coverage, and full clean backend-suite certification.
  8. **Preserved Boundaries & Exclusions:** Strictly zero production application code, migrations, schema alterations, application-level locks, broad retry loops, route changes, or ADR status changes.
  9. **T182 Dependency & Preservation:** T182 final backend suite result (956 passed, 1 failed, 87 warnings, exit 1 due to T138 concurrent allocator test) is recorded accurately. T182 storage acceptance evidence remains preserved on branch `codex/t182-storage-durability`. T182 Implementation PR 2 remains unpublished until T183 completes and T182 recertification passes on clean isolated PostgreSQL 16.
- **Blocking Findings:** Zero (0).
- **Non-Blocking Advisories:** Four (4) advisories recorded.

---

## 2. Remote Provenance & Commit Ancestry

- **Repository:** `Intelligentclown/Legal_DMS`
- **Protected Baseline (main):** [`6720bcd281533ec2badc3ee3e7b92a0c12c52cb2`](https://github.com/Intelligentclown/Legal_DMS/commit/6720bcd281533ec2badc3ee3e7b92a0c12c52cb2) (Merge PR #394: `docs(governance): authorize T182 M2 document physical storage durability, restart recovery and current-head backend certification (#393)`)
- **Authorization PR Branch:** `docs/t183-authorization-calendar`
- **Candidate Commit (HEAD):** [`5a4496c772279e422338cb1babb2fa5c365a385b`](https://github.com/Intelligentclown/Legal_DMS/commit/5a4496c772279e422338cb1babb2fa5c365a385b)
- **Commit Subject:** `docs(governance): authorize T183 PostgreSQL file-number allocator concurrency remediation (#395)`
- **Merge Base:** `git merge-base origin/main HEAD` -> `6720bcd281533ec2badc3ee3e7b92a0c12c52cb2` (clean 1-commit linear fast-forward delta).
- **Author:** Dhimant Patel (`Intelligentclown`)
- **Reviewer Independence:** Verified. Independent QA review performed by Antigravity in separate QA reviewer capacity; no code authorship or PR creation performed by this reviewer role.

---

## 3. Detailed Review of Authorization Scope & Governance Invariants

### 3.1 Authorization Issue & Project Owner Scope Boundaries
Issue [#395](https://github.com/Intelligentclown/Legal_DMS/issues/395) records formal approval by the Project Owner on 28 October 2026 for **authorization publication only** under `PROJECT_WORKFLOW.md §3.1`. The approved bounded future PR 2 scope covers eight (8) specific implementation areas:
1. **Conflict arbiter alignment:** Align the PostgreSQL upsert conflict arbiter in `SqlAlchemyFileRepository` with the existing `matter_id` primary key constraint on `file_number_sequences` (`pk_file_number_sequences` / `ON CONFLICT (matter_id)`) per ADR-0027, replacing the misaligned `uq_file_number_sequences_organization_id_matter_id` conflict target.
2. **Single-statement atomic allocation:** Generate sequential file numbers in a single atomic SQL statement returning the allocated counter without application-level distributed or in-process locks.
3. **Transaction and rollback semantics:** Counter increment and File creation share the database transaction boundary under `get_db()` (`ADR/0020`); aborted or rolled back File creation does not burn sequence numbers.
4. **Concurrent first-allocation uniqueness:** Verify concurrent first-allocation attempts for the same Matter on clean PostgreSQL 16 allocate distinct sequential numbers without unique-constraint or primary-key collisions.
5. **Rollback and number reuse:** Verify rolled back allocation attempts allow subsequent allocation attempts to reuse the rolled-back sequence number.
6. **Repeated PostgreSQL 16 concurrency regression coverage:** Add multi-worker/multi-session concurrency regression tests passing repeatedly against live isolated PostgreSQL 16 without flakes or deadlocks.
7. **Clean full backend-suite certification:** Execute complete backend test suite cleanly with zero failures certified against isolated PostgreSQL 16 at candidate HEAD.
8. **Comprehensive / Risk Tier 1 Independent QA:** Require Comprehensive / Risk Tier 1 Independent QA with zero blocking findings before protected merge of PR 2.

### 3.2 Technical Defect Root Cause & ADR-0027 Conformance Analysis
The authorization accurately describes the physical and architectural mechanics of the failure:
- **Existing Implementation:** In `backend/src/app/infrastructure/persistence/sqlalchemy_file_repository.py:57-65`, the `allocate_and_add` method executes:
  ```sql
  INSERT INTO file_number_sequences (matter_id, organization_id, next_number)
  VALUES (:matter_id, :organization_id, 2)
  ON CONFLICT ON CONSTRAINT uq_file_number_sequences_organization_id_matter_id
  DO UPDATE ...
  ```
- **Physical Collision:** On table `file_number_sequences` (`backend/src/app/infrastructure/persistence/models/file.py:50-70`), `matter_id` is defined as `primary_key=True`, generating the primary key constraint `pk_file_number_sequences`. There is also a composite unique constraint `uq_file_number_sequences_organization_id_matter_id`.
- **Race Condition on First Allocation:** When concurrent transactions execute the initial insert for the same `matter_id` against an empty sequence table, PostgreSQL checks the primary key index. Because the upsert specifies `ON CONFLICT ON CONSTRAINT uq_file_number_sequences_organization_id_matter_id`, concurrent insertions collide on `pk_file_number_sequences`, raising a `UniqueViolation` (`Key (matter_id)=(...) already exists`) rather than executing the `DO UPDATE` branch.
- **ADR-0027 Specification:** Lines 124–129 and 197–200 of `ADR/0027-file-numbering-algorithm-and-concurrency-strategy.md` explicitly mandate targeting the `matter_id` primary key:
  ```sql
  ON CONFLICT (matter_id) DO UPDATE SET next_number = file_number_sequences.next_number + 1 RETURNING next_number
  ```
- **No Migration Required:** Because `matter_id` is already the primary key of `file_number_sequences`, aligning the upsert to target `pk_file_number_sequences` (`ON CONFLICT (matter_id)`) requires only a statement-level correction in `SqlAlchemyFileRepository`. No DDL or Alembic migration is necessary or authorized.

### 3.3 Acceptance Baseline (AC-01 through AC-07)
- **AC-01 (Conflict Arbiter Alignment):** The PostgreSQL upsert conflict arbiter in `SqlAlchemyFileRepository` targets the `matter_id` primary key (`pk_file_number_sequences` / `ON CONFLICT (matter_id)`) per ADR-0027, eliminating concurrent initialization collisions.
- **AC-02 (Single-Statement Atomic Allocation):** File-number generation executes in a single atomic SQL statement returning the allocated counter without application-level locks.
- **AC-03 (Transaction & Rollback Semantics):** Sequence counter increment and File creation share the same database transaction boundary; failed or rolled back File creation releases/rolls back the counter without burning numbers.
- **AC-04 (Concurrent First-Allocation Uniqueness):** Concurrent first-allocation attempts for the same Matter on clean PostgreSQL 16 allocate distinct sequential numbers without unique-constraint or primary-key collisions.
- **AC-05 (Rollback & Reuse Verification):** Rolled back allocation attempts allow subsequent allocation attempts to reuse the rolled-back sequence number.
- **AC-06 (Repeated Concurrency Regression Coverage):** Multi-worker/multi-session concurrency regression tests pass repeatedly against clean isolated PostgreSQL 16 without flakes or deadlocks.
- **AC-07 (Full Backend Suite Certification):** The complete backend test suite runs cleanly with zero failures and is certified against isolated PostgreSQL 16 at candidate HEAD.

### 3.4 Governance Frontier & Concurrent-Task Governance
- In `PROJECT_STATE.json`:
  ```json
  "latestTaskDone": "T181",
  "latestTaskAuthorized": "T183",
  "inProgressTransitions": []
  ```
- In `IMPLEMENTATION_QUEUE.md`:
  Row T183 is registered with status `| Authorized |`, predecessor `T181`, approved future PR 2 scope, acceptance criteria AC-01 through AC-07, explicit restrictions, resources, and candidate state.
- **Concurrent-Task Lifecycle Integrity:** T182 remains `Authorized` and not `Done`. The repository governance framework fully supports concurrent tasks between `latestTaskDone` and `latestTaskAuthorized` (precedents T176/T175, T168/T167, T158–T159/T157, T99–T100/T98). No repository rule prohibits authorizing a separate remediation task while a prior task remains open; rather, it is the established and documented governance mechanism for unblocking open tasks.
- In `docs/ProjectStatus.md`, `docs/SessionReport.md`, and `docs/AI_HANDOVER.md`:
  All documentation surfaces register the new authorization frontier, candidate state, approved scope, acceptance criteria, and non-authorization boundaries.

### 3.5 Preserved Invariants & Boundary Enforcement
- **M1 Actual Date Preservation:** `M1.actual` remains `2026-10-25` with full Schema V3 completion provenance, SHA-256 evidence package digest `aed7462d9d90b9a97133e33166c536129df280568fa36f4a4b07261e0bb47131`, and derived completion variance `-21` calendar days / `Early`.
- **Milestone Forecasts & Baselines:** M1 (`2026-11-15`, actual `2026-10-25`), M2 (`2026-12-31`, actual null), M3 (`2027-02-28`, actual null), and overall finalization (`2027-02-28`) remain unchanged.
- **Acceptance Boundary:** Full M1 Operational Acceptance is strictly internal office dogfooding and does not constitute commercial readiness, production release, or M2/M3 milestone acceptance.
- **Architectural & Migration Invariants:** Required ADRs `[12, 15, 16, 17, 20]` remain unresolved; Proposed ADR-0043 and ADR-0047 remain `Proposed`; sole Alembic migration frontier remains `b155caa6d4e1`. Zero changes to production application code or migrations.
- **No Successor Authorization:** T184 remains unauthorized.

### 3.6 T182 Evidence Preservation & Dependency Protocol
- T182's branch `codex/t182-storage-durability` is preserved without modifying its implementation or evidence.
- T182 final certification is recorded as blocked by the allocator defect (956 passed, 1 failed on T138 concurrent allocator test, 87 warnings, exit 1).
- Following T183 protected merge, T182 must reconcile against updated protected main and rerun full backend certification on clean isolated PostgreSQL 16 before T182 Implementation PR 2 may be published.

---

## 4. Delivery Calendar & Scheduling Audit

- **Calendar File:** `docs/delivery_calendar.json`
- **Schema Version:** 3 (validated and active).
- **Task Registration (T183):**
  ```json
  {
    "id": "T183",
    "title": "PostgreSQL File-Number Allocator Concurrency Remediation",
    "milestone": "M2",
    "lane": "ux",
    "dependencies": {
      "finish_to_start": [
        "T181"
      ],
      "defect_evidence": [
        "T182"
      ]
    },
    "critical_path": {
      "is_critical": false,
      "slack_days": 0
    },
    "planned_start": "2026-10-28",
    "planned_finish": "2026-10-31",
    "planned_duration": 4,
    "forecast_start": "2026-10-28",
    "forecast_finish": "2026-10-31",
    "forecast_impact": {
      "M1": { "old": "2026-11-15", "new": "2026-11-15", "movement": 0, "direction": "unchanged" },
      "M2": { "old": "2026-12-31", "new": "2026-12-31", "movement": 0, "direction": "unchanged" },
      "M3": { "old": "2027-02-28", "new": "2027-02-28", "movement": 0, "direction": "unchanged" },
      "overall_finalization": { "old": "2027-02-28", "new": "2027-02-28", "movement": 0, "direction": "unchanged" },
      "reason": "T183 is an owner-approved task addressing PostgreSQL file-number allocator concurrency remediation discovered during T182 certification. T181 is the completed finish-to-start predecessor; T182 is defect evidence; T183 remediation unblocks T182 backend certification. Milestone baselines, forecasts, actuals, and historical calendar events remain unchanged at authorization; no milestone actual is reconciled and no forecast changes occur."
    },
    "actual_start": null,
    "actual_completion": null,
    "actual_elapsed": null,
    "planned_finish_used": null,
    "variance": null,
    "classification": null,
    "critical_at_completion": null,
    "milestone_impact": null,
    "finalization_impact": null,
    "recalculated": null,
    "completion_evidence": null
  }
  ```
- **T182 Dependency Update:** In `docs/delivery_calendar.json`, T182's `finish_to_start` dependency is updated to `["T181", "T183"]`. T183's `finish_to_start` dependency is `["T181"]` with `defect_evidence: ["T182"]`. This forms an acyclic dependency graph (`T181 -> T183 -> T182`), verified clean by `delivery_calendar.py`.
- **Validation Outcome:** Validates cleanly under `scripts/delivery_calendar.py` and `scripts/governance_validate.py` against Schema Version 3.
- **Null Fields:** All actual, variance, classification, and completion fields remain strictly `null`.
- **Milestone Forecasts:** Movement is zero across all milestones. No milestone history entries have been appended.

---

## 5. Independent Validation & Test Execution Matrix

| Verification Check | Target / Command | Result | Details |
| :--- | :--- | :--- | :--- |
| **Governance Consistency** | `python scripts/governance_validate.py --report` | **PASS** | 0 warnings, 0 errors. `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, and `ADR` files are internally consistent. Required ADRs unresolved: `[12, 15, 16, 17, 20]`. |
| **Delivery Calendar Validation** | `python scripts/delivery_calendar.py` via `scripts/governance_validate.py` | **PASS** | Exited with code 0. Schema V3 validation succeeded; zero scheduling cycles. |
| **Current Context Manifest** | `python scripts/current_context_manifest.py` | **PASS** | `discrepancies: []`, `latest_authorized: "T183"`, `latest_done: "T181"`, `in_progress_transitions: []`, `unresolved: [12, 15, 16, 17, 20]`. |
| **Governance Unit Tests** | `python -m unittest scripts.tests.test_governance_validate` | **PASS** | 88/88 unit tests passed in 0.157s. |
| **Manifest Unit Test** | `python -m unittest scripts.tests.test_current_context_manifest -v` | **1 EXPECTED FAILURE** | 6 passed, 1 expected failure at line 30 (`AssertionError: 'T181' != 'T170'`). Documented baseline technical debt originating in T171; preserved untouched per scope-exclusion rules. |
| **Whitespace / Diff Hygiene** | `git diff --check 6720bcd..5a4496c` | **PASS (with comment)** | Flags 6 lines in `docs/SessionReport.md:4463-4468` due to intentional Markdown double-space line breaks. Cosmetic observation noted in advisory QA-T183-AUTH-ADV-01. |
| **GitHub Actions CI** | Exact candidate commit `5a4496c772279e422338cb1babb2fa5c365a385b` | **PASS** | All 5 remote workflow runs succeeded: Backend validation (26s), Frontend validation (40s), Governance consistency (8s & 8s), Release build verification (5s). |

---

## 6. Findings & Non-Blocking Advisories

### 6.1 Blocking Findings
**Zero (0) blocking findings.**

### 6.2 Non-Blocking Advisories

- **QA-T183-AUTH-ADV-01 (Markdown Line-Break Whitespace in Session Report):**  
  `git diff --check` flags lines 4463–4468 in `docs/SessionReport.md` for trailing whitespace. In GitHub Flavored Markdown, two trailing spaces are standard syntax for hard line breaks. While standard for Markdown rendering, it triggers `git diff --check`. Precedent across prior reviews (e.g., `QA-T181-AUTH-ADV-01`, `QA-T176-CLS-ADV-01`) classifies this strictly as an informational, non-blocking cosmetic observation.
- **QA-T183-AUTH-ADV-02 (Pre-existing Baseline Debt in Context Manifest Test):**  
  `scripts/tests/test_current_context_manifest.py:30` contains a hardcoded assertion `assertEqual(payload["governance_frontier"]["latest_done"], "T170")` and `latest_authorized == "T171"`, dating to T171 closeout. Running `python -m unittest scripts/tests/test_current_context_manifest.py` fails on this hardcoded check (`'T181' != 'T170'`). This is confirmed pre-existing test debt originating in T171 and documented across prior QA reviews (T172–T182). `scripts/current_context_manifest.py` itself generates valid, discrepancy-free JSON. The candidate PR properly refrained from editing this test to maintain documentation-only authorization boundaries.
- **QA-T183-AUTH-ADV-03 (Strict Implementation Boundary for Future PR 2):**  
  When PR 2 implementation is commissioned, it must remain strictly within conflict arbiter alignment in `SqlAlchemyFileRepository`, atomic single-statement allocation, transaction rollback verification, repeated multi-worker concurrency tests on PostgreSQL 16, and full clean backend-suite certification. It must not alter database schema or migrations (migration frontier remains `b155caa6d4e1`), introduce application-level locks (e.g., `asyncio.Lock`), add retry loops, introduce new routes, or modify ADR-0027.
- **QA-T183-AUTH-ADV-04 (T182 Dependency Unblocking and Recertification Protocol):**  
  T182 final certification is blocked by the independently reproduced PostgreSQL allocator defect. T182 storage durability evidence and implementation remain preserved on branch `codex/t182-storage-durability`. After T183 completes its three-PR lifecycle and merges into protected `main`, T182 must reconcile against the updated protected `main` and rerun full backend certification on clean isolated PostgreSQL 16 before T182 Implementation PR 2 is published.

---

## 7. Protected Merge Recommendation & Lifecycle Handoff

Candidate PR [#396](https://github.com/Intelligentclown/Legal_DMS/pull/396) satisfies all pre-implementation authorization requirements under `PROJECT_WORKFLOW.md §3.1`. It accurately records the Project Owner's authorization, cleanly updates governance and calendar ledgers, preserves all invariants, and passes all required CI checks.

**Recommendation:** **Merge PR [#396](https://github.com/Intelligentclown/Legal_DMS/pull/396)** into protected `main` under standard branch protection rules via the Git/CI PR Manager role.

---

## 8. Mandatory STOP Boundary

In strict accordance with `PROJECT_WORKFLOW.md §3.1`, `docs/prompts/QAReviewer.md`, and the standing Independent QA Reviewer instructions:
- **Do not merge PR #396 in this session.**
- **Do not begin T183 allocator implementation.**
- **Do not begin T182 Implementation PR 2 or modify the T182 worktree.**
- **Do not mark T182 or T183 Done.**
- **Do not authorize T184 or any successor tasks.**
- **Do not modify M2 or M3 official forecasts.**
- **Do not perform Documentation Manager or Git/CI PR Manager duties.**

Control is returned to the Project Owner / Control Tower for Git/CI PR Manager protected merge verification.
