# T185 Software Architect Report — Required ADR #12: Workflow vs Government Status

**Task:** T185 — Required ADR #12: Workflow vs Government Status
**Role:** Software Architect
**Lifecycle Stage:** `PROJECT_WORKFLOW.md §3.1` — PR 2 of 3 (Architecture Candidate)
**Proposed Architecture Decision Record:** [`ADR/0048-workflow-vs-government-status-boundary.md`](file:///d:/Code/Legal_DMS_Clean/ADR/0048-workflow-vs-government-status-boundary.md)
**Protected Base Commit:** `3e902bd978d9655cb6942e4ed5a1213cd145eb65` (`origin/main`, merge PR #406)
**Branch:** `architecture/t185-workflow-vs-government-status`
**Date:** 2026-10-31

---

## 1. Verified Baseline and Authorization

1. **Protected `main` Verification:**
   - Fresh remote query independently verified protected `main` at `3e902bd978d9655cb6942e4ed5a1213cd145eb65`.
   - Merge PR #406 (`docs(governance): authorize T185 Required ADR #12 (#405)`) is the exact head commit of protected `main`.
   - Parent 1: `b2ea94e817c5afd9088ba47dd3b5d5650f60383a` (Merge PR #404 — T184 dedicated governance closeout).
   - Parent 2: `70c763c7d1c1c3e8a3d5f5b1e6e4c7d9a8f2b4e5` (PR #406 reviewed candidate head containing Independent QA review `docs/reviews/T185_Authorization_QA_Review.md`).
2. **Governance State Verified:**
   - `latestTaskDone = T184`
   - `latestTaskAuthorized = T185`
   - `inProgressTransitions = []`
   - Unresolved Required ADRs: `[12, 15, 16, 17, 20]` (strictly preserved).
   - Database migration frontier: strictly `b155caa6d4e1`.
   - No conflicting T185 architecture work present.
3. **Execution Environment Gate Established:**
   - Authenticated, writable repository checkout on Windows: verified.
   - GitHub CLI (`gh`) available: verified.
   - Complete repository tree accessible: verified.
   - Governance and ADR validators executable: verified.

---

## 2. Problem Statement & Evidence Reconciliation

Required ADR #12 asks for the architectural boundary that separates the firm's **internal workflow** from **external government-process status**. The governed specification freezes this separation as three Confirmed Business Rules:

- **Rule 32:** Internal workflow status is distinct from government status.
- **Rule 33:** Government Process is its own domain concept.
- **Rule 34:** Government events must retain historical information.

### Repository evidence relevant to the boundary

1. **Internal workflow machinery already exists but is unwired.**
   - `backend/src/app/application/workflow/engine.py` provides a pure, framework-free state machine (`WorkflowDefinition` / `Transition` / `WorkflowEngine`). It validates transitions but persists no instance state.
   - `backend/src/app/infrastructure/persistence/models/workflow.py` provides `workflow_definitions`, `workflow_states`, and `workflow_history` (polymorphic `entity_type` + `entity_id`).
   - `backend/alembic/versions/9963e15f2752_seed_lookup_data.py` seeds a starter `matter_lifecycle` workflow with six states.
   - Confirmed by direct inspection: no service, route, or feature currently wires the engine to these tables.

2. **Government Process machinery does not exist.**
   - Full-repository search found no `government_processes`, `government_events`, authority-process, or government-status table, model, service, or route.
   - This matches §24.11's own finding that Government Process is a genuinely new domain area.

3. **A pre-existing `matter_statuses` lookup table exists.**
   - `backend/src/app/infrastructure/persistence/models/matter.py` defines `MatterStatus` and `Matter.matter_status_id`.
   - This is a simple lookup-driven column, not a workflow state machine and not a government-status record. It is noted only as a boundary marker; this ADR does not redesign it.

The architectural gap is not a missing engine — the engine exists. The gap is the absence of a durable, recorded decision that the existing engine and tables are for **internal workflow only**, and that Government Process requires a **separate domain model and append-only event history**.

---

## 3. Evaluation of Alternatives

### Alternative 1: Reuse the workflow engine and tables for both Workflow and Government Process

- **Description:** Treat government status as just another workflow definition loaded into `WorkflowEngine`, with `workflow_history` recording authority-reported transitions.
- **Rejected:** Directly violates rule 32 by collapsing two distinct state machines into one mechanism. It also misapplies a firm-controlled transition validator to an authority-controlled observation domain.

### Alternative 2: Two state-machine engines (Workflow + Government Process)

- **Description:** Build a parallel `GovernmentProcessEngine`/`GovernmentProcessDefinition` with the same state-machine semantics as the workflow engine.
- **Rejected:** Government status does not follow a firm-controlled transition graph. Encoding transitions like `PENDING → APPROVED` in code would falsely assert control and break whenever an authority introduces an unmodeled intermediate state.

### Alternative 3: Shared history table with a discriminator

- **Description:** Extend `workflow_history` with a `source` discriminator (`internal` / `government`) to store both workflow transitions and government events.
- **Rejected:** Re-collapses the distinction rule 32 protects. The table name itself would become semantically wrong for authority events, and a shared flag is a future conflation risk.

### Alternative 4: Separate domains, separate persistence (selected)

- **Description:** Keep the existing `WorkflowEngine` and `workflow_*` tables for internal workflow only. Create a separate `government_processes` entity and append-only `government_events` history for external authority processing.
- **Selected:** Matches rules 32–34, respects external-authority unpredictability, allows each table to model its own domain accurately, and composes cleanly with existing ADRs.

---

## 4. Architectural Decision Summary (Proposed ADR-0048)

[`ADR/0048-workflow-vs-government-status-boundary.md`](file:///d:/Code/Legal_DMS_Clean/ADR/0048-workflow-vs-government-status-boundary.md) establishes:

1. **Permanent domain separation.**
   Workflow and Government Process are distinct domains. They are not two views of one state machine, not two vocabularies in one table, and not two event streams in one history table.

2. **Internal workflow remains the existing engine's only responsibility.**
   `WorkflowEngine`, `workflow_definitions`, `workflow_states`, and `workflow_history` are reserved for firm-controlled internal workflow. Future workflow implementation wires these existing pieces together; it does not absorb government behavior.

3. **Government Process is a new, separate domain model.**
   Future implementation will create `government_processes` (the owning process record) and `government_events` (append-only observations). The event stream is the authoritative record; any "current status" is a derived read-side view.

4. **Ownership / control semantics.**
   - Workflow transitions are firm-controlled and validated against a `WorkflowDefinition`.
   - Government-event recordings are authority-observed and not validated against a firm-defined transition graph.

5. **Correlation without coupling.**
   A workflow transition may be triggered in response to a government event, but the two records remain independent: the transition is recorded in `workflow_history`; the event is recorded in `government_events`.

6. **Attachment granularity is deferred.**
   Both domains may attach to `Matter` or `File` (once `File` exists), independently. This ADR does not decide the default or required attachment points; that remains a future business/configuration decision respecting `ADR/0030`.

7. **Composition with accepted ADRs.**
   - `ADR/0030`: Matter→File boundary is context, not reopened.
   - `ADR/0029`: Workflow transitions and government-event recordings are both "status changes" requiring independent `AuditLogger.record()` coverage.
   - `ADR/0021` / `ADR/0022`: Future tables are tenant-scoped and permission-gated, unchanged.
   - `ADR/0012` / `ADR/0020`: Future writes participate in existing transaction/session boundaries.

8. **Explicitly unresolved adjacent questions.**
   Vocabulary (Required ADR #15), identifiers (Required ADR #16), soft-deletion/history (Required ADR #17), and migration strategy (Required ADR #20) remain untouched.

---

## 5. Scope Audit & Strict Exclusions

This architecture deliverable strictly adheres to `PROJECT_WORKFLOW.md §3.1` PR 2 boundaries:

- **Files Added / Modified:** Exactly three (3) files:
  1. [`ADR/0048-workflow-vs-government-status-boundary.md`](file:///d:/Code/Legal_DMS_Clean/ADR/0048-workflow-vs-government-status-boundary.md) (new)
  2. [`docs/reviews/T185_Software_Architect_Report.md`](file:///d:/Code/Legal_DMS_Clean/docs/reviews/T185_Software_Architect_Report.md) (new)
  3. [`PROJECT_STATE.json`](file:///d:/Code/Legal_DMS_Clean/PROJECT_STATE.json) — `governanceLedger.inProgressTransitions` updated with the T185 Required ADR #12 transition declaration per `PROJECT_WORKFLOW.md §3.1` and `docs/GOVERNANCE_VALIDATION.md`.
- **Zero Product Implementation:** Zero modifications to backend, frontend, Electron, or database source code.
- **Zero Schema / Database Changes:** Zero migrations created or altered; zero database rows modified; migration frontier strictly preserved at `b155caa6d4e1`.
- **Zero Required ADR Resolutions Beyond #12:** Required ADRs `[15, 16, 17, 20]` remain unresolved.
- **Zero Accepted ADR Modifications:** `ADR/0001` through `ADR/0047` are untouched.
- **Zero Proposed ADR Promotions:** `ADR-0043`, `ADR-0044`, and `ADR-0047` remain Proposed.
- **Zero Downstream Authorizations:** No successor task is authorized.
- **Zero Closeout Actions:** `PROJECT_STATE.json` and `IMPLEMENTATION_QUEUE.md` are untouched; PR 3 alone records governance closeout after PR 2 merges.

---

## 6. Validation Commands and Results

| Command | Target / Purpose | Result |
|---|---|:---:|
| `python scripts/governance_validate.py` | Repository governance consistency & ADR integrity | **PASSED** (0 warnings, 0 errors) |
| `python scripts/governance_validate.py --report` | Required ADR resolution status | **PASSED** — Required ADR #12 remains unresolved (as expected for Proposed ADR-0048); `[15, 16, 17, 20]` also unresolved. |
| `python scripts/tests/test_governance_validate.py -v` | Governance validator unit tests | **PASSED** (88/88 passed) |
| `python scripts/delivery_calendar.py --check` | Delivery calendar schema & schedule integrity | **PASSED** (clean exit 0) |
| `git diff --check` | Whitespace and syntax diff checks | **PASSED** (clean exit 0) |

---

## 7. Reviewer Checklist

Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☐ Tests added — N/A; documentation-only architecture deliverable, no code/tests written.
☐ Existing tests pass — N/A; documentation-only deliverable. Full governance/validator test suites pass (see §6).
☑ Documentation updated
☑ ADR updated (if required)
☐ AI_BOOTSTRAP updated (if required) — N/A; no standing convention changed.
☑ PROJECT_STATE updated (if required) — `governanceLedger.inProgressTransitions` declared for T185 Required ADR #12 per the three-PR lifecycle; no other state synchronized (PR 3 closeout responsibility).
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA

---

## 8. QA Decision

**Formal QA Decision:** **Pending** — every box below is intentionally unchecked. The Independent QA Reviewer will render the QA Decision after reviewing this candidate against the authorized AC-01 through AC-10 acceptance criteria.

```
QA Decision

□ Approved
□ Approved with comments
□ Rework required

Reviewed by: _________________________
Date: _________________________
Blocking findings (none if blank):
Non-blocking comments (none if blank):
```

---

## 9. Handoff to Independent QA

The Software Architect role is complete. Candidate commit on branch `architecture/t185-workflow-vs-government-status` is ready for independent review by the Independent QA Reviewer role under `PROJECT_WORKFLOW.md §3.1`. The architect does not self-review, approve, or merge this pull request.
