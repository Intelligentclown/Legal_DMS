# T156 Independent QA Review — Calendar Delivery Governance & Dynamic Forecasting

**Task:** T156 — Calendar-Based Delivery Governance & Dynamic Forecasting  
**Candidate Reviewed:** `3fbd611c664f9764393a610b54c89bf3a6c2411c`  
**Protected Base Commit:** `a4877dd28440073bbfd64d15753d3976608fbb45` (`origin/main`, merge PR #292)  
**Pull Request:** [#293 — `feat(governance): T156 calendar delivery forecasting and prospective validation`](https://github.com/Intelligentclown/Legal_DMS/pull/293)  
**Branch:** `docs/t156-calendar-delivery-governance`  
**Lifecycle Stage:** `PROJECT_WORKFLOW.md §3.1` — PR 2 of 3 (Governance Implementation + Independent QA)  
**Reviewer:** Independent QA Reviewer (Antigravity)  
**Date:** 2026-10-17  

---

## 1. Executive Summary & Formal QA Decision

- **Formal QA Decision:** **Changes requested**
- **Exact Candidate SHA Evaluated:** `3fbd611c664f9764393a610b54c89bf3a6c2411c`
- **Scope Audit:** Exactly 10 changed files (+313 / −0 lines), located strictly within documentation, governance workflow prompts, and validation scripts. Zero backend, frontend, database schema, migration, or product code changed.
- **Blocking Defects Identified:**
  1. **Done-Task Queue Parser Defect:** `scripts/delivery_calendar.py` line 105 uses `rowmap[task_id].text.split("|")[-2]` to determine if a task is marked `Done`. In `IMPLEMENTATION_QUEUE.md`, table rows have 4 columns (`| Task | Description | Status | Predecessor |`), where `split("|")[-2]` selects the **Predecessor** column (e.g. `' T156 '`), NOT the Status column. Consequently, every real post-activation task marked `Done` in `IMPLEMENTATION_QUEUE.md` evaluates to `False`, completely evading Done-task calendar validation (allowing missing or bogus actuals, elapsed days, variance, and classification to pass without error).
  2. **CI Test Runner Placement Defect:** In `scripts/tests/test_governance_validate.py`, the entire test suite `class TestT156Calendar` is defined *after* the `if __name__ == "__main__": unittest.main()` block (lines 581–584). In CI (`.github/workflows/governance.yml`), `python scripts/tests/test_governance_validate.py -v` executes `unittest.main()` and immediately exits after running the pre-existing 51 tests. The 7 newly added T156 calendar tests are never executed by CI.
- **Milestone Baseline Status:**
  **Current recorded overall finalization forecast: 2027-02-28 — provisional/unvalidated.**
- **Lifecycle Disposition:** Requires implementation remediation before PR #293 can proceed to §3.1 PR 3 governance closeout.

---

## 2. Baseline & Provenance Verification

- **Protected `main` Baseline:** `a4877dd28440073bbfd64d15753d3976608fbb45` (Merge pull request #292 — T156 authorization).
- **PR #293 State:** OPEN, non-draft, unmerged, mergeable against `main`.
- **Exact Candidate Head:** `3fbd611c664f9764393a610b54c89bf3a6c2411c` (10 commits ahead of `main`, 0 behind).
- **Governance Ledger Baseline:**
  - `latestTaskDone`: T155
  - `latestTaskAuthorized`: T156
  - `inProgressTransitions`: `[]`
  - `unresolvedRequiredAdrs`: `[12, 15, 16, 17, 20]`

---

## 3. Scope & Diff Audit

Changed files (exactly 10 files, +313 / −0 lines):
1. `AI_BOOTSTRAP.md` (+4 lines)
2. `PROJECT_WORKFLOW.md` (+5 lines)
3. `docs/DELIVERY_CALENDAR.md` (+17 lines)
4. `docs/GOVERNANCE_VALIDATION.md` (+4 lines)
5. `docs/delivery_calendar.json` (+70 lines)
6. `docs/prompts/DocumentationManager.md` (+4 lines)
7. `docs/prompts/ProjectManager.md` (+4 lines)
8. `scripts/delivery_calendar.py` (+121 lines)
9. `scripts/governance_validate.py` (+2 lines)
10. `scripts/tests/test_governance_validate.py` (+82 lines)

**Prohibited Scope Confirmed Absent:**
- Zero backend, frontend, or domain product implementation.
- Zero Alembic migrations, database models, RLS policies, or seed modifications.
- Zero ADR resolutions or status alterations (`[12, 15, 16, 17, 20]` remain unresolved; ADR-0044 remains Proposed).
- Zero T157+ task selection or authorization.
- Zero premature declaration of T156 as Done (reserved for §3.1 PR 3).

---

## 4. Calendar Authority & Arithmetic Model Review

- **Authority Boundary:** Confirmed that `IMPLEMENTATION_QUEUE.md` remains the sole authority for task authorization and completion. `docs/delivery_calendar.json` operates strictly as a structured schedule and forecasting authority. Calendar planning metadata cannot authorize a numbered task.
- **Activation Boundary:** Prospective enforcement strictly begins at **T157**. Historical tasks T1–T155 and bootstrap task T156 are correctly exempted.
- **Date Arithmetic:**
  - Standard inclusive calendar-day math: `planned_duration = finish - start + 1` day.
  - Actual elapsed: `actual_elapsed = actual_completion - actual_start + 1` day.
  - Variance: `actual_completion - planned_finish` in calendar days.
  - Classification: `< 0` → `Early`, `0` → `On Time`, `> 0` → `Late`.
  - Date validation enforces strict ISO `YYYY-MM-DD`.

---

## 5. Milestone & Finalization Review

- **Milestone Targets:**
  - M1 Office Dogfooding: baseline `2026-11-15`, forecast `2026-11-15`, confidence `low`
  - M2 Core V1: baseline `2026-12-31`, forecast `2026-12-31`, confidence `low`
  - M3 Full V1: baseline `2027-02-28`, forecast `2027-02-28`, confidence `low`
- **Overall Finalization Forecast:**
  **Current recorded overall finalization forecast: 2027-02-28 — provisional/unvalidated.**
- **Assessment:** The candidate explicitly discloses that these targets are provisional planning baselines because no authorized T157+ task dependency network exists yet. This treatment is honest and compliant with T156 authorization requirements.

---

## 6. Detailed Findings

### 6.1. Blocking Finding 1: Done-Task Table Parser Column Offset Bug
- **Severity:** Blocking
- **Location:** `scripts/delivery_calendar.py`, line 105:
  ```python
  if "Done" in rowmap[task_id].text.split("|")[-2]:
  ```
- **Evidence:**
  In `IMPLEMENTATION_QUEUE.md`, every table row follows the 4-column format:
  `| Task | Description | Status | Predecessor |`
  Splitting by `|` yields:
  `['', Task, Description, Status, Predecessor, '']`
  Here, `split("|")[-2]` inspects `Predecessor` (e.g. `' T156 '`), NOT `Status` (`' Done '`).
  Independent verification confirmed:
  ```python
  row = gv.TaskRow("T157", 1, "| T157 | T157 is now Done. Authorized by the project owner | Done | T156 |")
  check_calendar(data, [row])  # returns [] even with invalid/missing actuals, elapsed, variance, or classification!
  ```
- **Expected Behavior:** A task row with Status `Done` in `IMPLEMENTATION_QUEUE.md` must trigger the `DONE` validation block (lines 106–112).
- **Actual Behavior:** The check evaluates to `False` on all valid 4-column rows, completely evading Done-task calendar validation.
- **Remediation Required:** Correct the parser column index (e.g. `split("|")[-3].strip() == "Done"` or inspecting the row's parsed status column) and update the unit test fixture in `scripts/tests/test_governance_validate.py` to use realistic 4-column rows.

---

### 6.2. Blocking Finding 2: Test Placement Bug Bypasses CI Execution
- **Severity:** Blocking
- **Location:** `scripts/tests/test_governance_validate.py`, lines 581–584:
  ```python
  if __name__ == "__main__":
      unittest.main()

  class TestT156Calendar(unittest.TestCase):
  ```
- **Evidence:**
  `TestT156Calendar` is defined after `if __name__ == "__main__": unittest.main()`.
  When `.github/workflows/governance.yml` runs:
  `python scripts/tests/test_governance_validate.py -v`
  Python executes `unittest.main()` at line 582 and terminates.
  GitHub Actions Run #39036774852 log confirmed:
  `Ran 51 tests in 0.060s OK` (exact pre-T156 test count; 0 T156 tests ran).
  Local execution confirmed `python scripts/tests/test_governance_validate.py` executes only 51 tests.
- **Expected Behavior:** `python scripts/tests/test_governance_validate.py -v` must execute all 58 unit tests (51 pre-existing + 7 T156 tests).
- **Actual Behavior:** All 7 new T156 tests are skipped by CI when run via `python scripts/tests/test_governance_validate.py -v`.
- **Remediation Required:** Relocate `class TestT156Calendar` to be defined before `if __name__ == "__main__": unittest.main()`.

---

### 6.3. Non-Blocking Observations
1. **Critical Path & Slack Dynamic Recomputation:** `check_calendar` validates the presence, data types, and non-negative bounds of `is_critical` and `slack_days`, but does not re-derive the mathematical critical path across the task network. The standalone `forecast()` helper models finish-to-start predecessor DAGs, but is not invoked by `check_calendar()`. This is acceptable for the prospective schema stage, but should be documented.
2. **Cross-Milestone Dependencies in `forecast()`:** `forecast()` filters nodes strictly by `t["milestone"] == milestone_id`. If a task in M2 has a dependency in M1, `forecast()` raises `ValueError("missing milestone dependency: ...")`. Cross-milestone predecessor support should be considered if future task networks span milestone boundaries.
3. **Unchanged Forecast History Recording:** `check_calendar` enforces history entries when `movement != 0`, but permits empty history when a recalculation leaves milestone forecast unchanged.

---

## 7. Next Lifecycle Action

PR #293 cannot be approved in its current state.

**STOP — T156 implementation candidate requires remediation before proceeding: Done-task queue parsing bug in `scripts/delivery_calendar.py` and test runner placement bug in `scripts/tests/test_governance_validate.py`.**
