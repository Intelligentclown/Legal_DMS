# T171 — M2 Scope, Dependency and Capacity Baseline

**Status:** Implementation candidate for Independent QA; not an authorization, completion, or operational-readiness decision.  
**Task authority:** T171 queue row; Project Owner Issue #347; authorization PR #348, protected merge `884ba8a5523bc9fff15e3fb8290107c024d28ffa`.  
**Evidence cut-off:** protected `main` `884ba8a5523bc9fff15e3fb8290107c024d28ffa`, 2026-10-20 (Asia/Kolkata).  
**Scope boundary:** planning evidence only. No production code, migration, ADR-status, validator, forecast, task-status, or historical-record change is made by this document.

## 1. Purpose and method

This baseline makes three deliberately separate statements:

1. a source-backed view of Core V1/M2 capability evidence;
2. a typed dependency graph based only on the schedule authority; and
3. a capacity and scenario model whose assumptions are visible rather than implied.

`IMPLEMENTATION_QUEUE.md` remains the sole authority for task authorization and Done state. `docs/delivery_calendar.json` is the schedule authority, but its lanes and provisional slack fields are not staffing commitments or certified slack. The source inventory was inspected at the evidence cut-off: the frozen Domain Model & Functional Specification (especially §§18 and 21), `PROJECT_STATE.json`, `docs/DELIVERY_CALENDAR.md`, `docs/delivery_calendar.json`, accepted/proposed ADRs, M1 acceptance evidence, implementation/QA records, and the backend, frontend, Electron, migration, and integration-test surfaces.

## 2. Capability baseline

“Implemented” below means code or schema is present on the evidence-cut-off tree. It does **not** mean independently demonstrated operational readiness. “Test evidence” names available automated or recorded evidence; it is not a claim that the capability has a production-release acceptance.

| Core V1 capability | Authority | Existing implementation at cut-off | Available evidence | Known gap / blocking dependency | Remaining verification | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Identity, tenant context and RBAC | Specification Task A; ADR-0021, ADR-0022, ADR-0031; `backend/.../auth.py`, `users.py` | Auth, user, organization, permission and tenant-scoped route surfaces exist. | Auth/RBAC unit and integration tests; T169 QA records a 942-pass isolated backend-suite certification. | Required ADR #20 remains unresolved for legacy convergence; operational capacity unknown. | Fresh tenant/RLS, role-boundary and Electron-backed operational scenarios for the selected M2 slice. | Medium (implementation), low (operational readiness) |
| Party and relationship foundation | Specification Task B; ADR-0023 and ADR-0033–0039; `parties.py` | Tenant-scoped Party routes and Party frontend pages exist. | Party route/RLS/schema tests; M1 dogfooding evidence. | Client-to-Party cutover and legacy migration remain gated by Required ADR #20; ADR-0036/0037/0047 are Proposed. | Current-head operational-fresh and migrated-installation compatibility acceptance. | Medium / low |
| Property and land foundation | Specification Task C; ADR-0024; `properties.py` | Property route/service/schema foundation exists. | Property model, route and tenant-integrity tests; T169 reconciliation. | Property-record, land and wider domain behavior are not complete; Required ADR #12/#15/#16/#17/#20 remain open where applicable. | Integrated Matter–Property workflows and cross-tenant operational evidence. | Medium / low |
| Matter workspace | Specification Task G; ADR-0030 and ADR-0044; `matters.py` | Matter routes, Matter frontend list/create/detail pages, tenant and association foundations exist. | Matter unit/integration tests and T163/T166 acceptance evidence. | M1 acceptance is conditional dogfooding only; DEF-T163-02 must be verified resolved before relying on duplicate-number handling. | Full selected-office workflow, negative integrity, restart and regression evidence. | Medium / low |
| File and safe numbering | Specification Task H; ADR-0027, ADR-0030, ADR-0040; `files.py` | Matter-file route/service and file-detail UI exist. | File migration/allocator integration tests. | Numbering concurrency and legacy/file transition need slice-specific confirmation; Required ADR #16/#17/#20 remain unresolved. | Concurrent allocation, tenant authorization, migration and UI operational tests. | Medium / low |
| Document/version/storage | Specification Task I; ADR-0040 and ADR-0041; `documents.py` | Document and version routes plus document-detail UI exist. | Document/version route and storage integration tests. | File/document transition and version/storage ADRs are Proposed; no M2 operational acceptance for document workflows. | Upload/download/version, failure/rollback, authorization and Electron smoke evidence. | Medium / low |
| Enquiry and quotation conversion | Specification Task F; ADR-0043; `enquiries.py` and enquiry/quotation UI pages | Enquiry and quotation route/UI surface exists. | T148/T149 integration tests and quotation UI tests. | Conversion to Matter has architecture but not independent M2 operational proof; sequencing with Matter/File must be selected explicitly. | End-to-end conversion, authorization, retry and cross-capability tests. | Medium / low |
| Workflow, follow-up and applicable government processes | Specification Tasks J and K; Required ADR #12 | No verified M2-ready workflow/government vertical slice was found in the current route/UI inventory. | Framework/workflow-engine unit tests only. | Required ADR #12 is unresolved; capability is an explicit M2 scope item in the calendar. | ADR resolution, authorized vertical slice, integration and operational acceptance. | Low |
| Communications, timeline, reporting and integrations | Specification Tasks L and O | Framework/schema artifacts may exist, but no independently demonstrated Core V1 operational slice was found. | Isolated model/framework tests where present. | Scope and dependencies are not decomposed; reporting/integration contracts are not scheduled. | Product contracts, security boundaries, authorized slices and operational evidence. | Low |
| Finance and advanced security | Specification Tasks M and N; Required ADR #13/#18 | Financial schema and some integrity tests exist; baseline RBAC exists. | T169 QA confirms financial-ledger integrity tests remained in suite. | Finance is outside M2 regular-office scope; advanced security is not a substitute for tenant isolation. | Keep excluded from M2 selection unless separately authorized; assess for M3 only. | Low for Core V1 completion; out of M2 scope |
| Desktop/Electron operational surface | Stack ADR-0003; `electron/main.ts`, `electron/preload.ts` | Electron shell and secure preload/token handling exist. | Historical Electron smoke work and T163/T166 evidence. | Native full-restart/session evidence was previously blocked in headless execution (BLK-T163-01); M1 conditional acceptance is not production approval. | Native Electron restart/session and selected workflow smoke tests on a supported host. | Medium (code), low (operational readiness) |

### Operational-readiness boundary

The protected M1 record is **conditional operational acceptance for dogfooding**, not production-release approval (`docs/acceptance/M1_Conditional_Operational_Acceptance.md`). It retains open limitations: no independent current full-suite certification in that record, QA-T166-NB-01 and T165 advisories, unresolved Required ADRs `[12, 15, 16, 17, 20]`, Proposed ADR-0047, and no unrestricted release claim. T169 later independently recorded two isolated full-suite runs of 942 passed / 0 failed / 0 errors, but that automated evidence does not replace M2 end-to-end, native Electron, or operational acceptance evidence.

## 3. Dependency verification

### Verified T171 predecessors

| Edge | Type | Verified result | Interpretation |
| --- | --- | --- | --- |
| T169 -> T171 | Finish-to-start | T169 is Done; protected implementation merge `78ae3513227d90a2b20e309792708d03201ef477`; calendar records T169 before T171. | Valid scheduling predecessor. |
| T170 -> T171 | Finish-to-start | T170 is Done; protected implementation merge `7fac6572e40ee35c5eec11550d1866fa9edac313`; calendar records T170 before T171. | Valid scheduling predecessor. |
| T167 -> T171 | Defect evidence | T167 is terminally Cancelled. Its immutable cancellation record names T169 as `proposed_unapproved` at cancellation time and references PR #332's 897 passed / 45 failed evidence. | Diagnostic provenance only. It is **not** a scheduling predecessor and cannot satisfy finish-to-start. |

The compact, reproducible dependency graph is:

```text
T166 -> T168 -> T169 -> T171
             \-> T170 -/
T165 -evidence-> T167 (Cancelled) -evidence-> {T168, T169, T170, T171}
```

Only solid finish-to-start edges participate in topology. The calendar has no complete downstream, estimated M2 work network after T171. Therefore a project/M2 critical path, total float, or a milestone-feasibility conclusion cannot be certified.

### Architectural prerequisites and safe execution sequence

The governed specification identifies Tasks A–O as dependency-oriented implementation units. The current accepted/proposed ADR landscape supplies prerequisites, not implementation authority. A safe prospective sequence is: (1) turn the chosen M2 office-use outcome into authorized, finite vertical-slice tasks; (2) resolve or explicitly avoid the applicable unresolved ADR gates; (3) establish/verify tenant, Party, Property, Matter and file/document prerequisites in the selected order; (4) perform integrated backend/frontend/Electron verification; (5) conduct independent QA and operational acceptance. This is a planning sequence only.

Specific gates needing a future task-level decision are Required ADR #12 (workflow vs government status), #15 (core vs configurable vocabulary), #16 (UUID vs human identifiers), #17 (soft deletion/history), and #20 (migration strategy). ADR-0047 remains Proposed and must not be treated as an accepted replacement for those gates.

## 4. Capacity baseline

| Evidence | Confirmed fact | Not established |
| --- | --- | --- |
| Role routing and workflow | Independent QA, collaborator approval, protected merge and a separate closeout are mandatory lifecycle overhead. | A named individual’s available hours, allocation, leave, throughput, or simultaneous task capacity. |
| Delivery calendar | Calendar schema permits independent lanes to overlap and labels current lanes as planning hypotheses. | An exclusive-lane or team-capacity rule; overlap is not proof of parallel resourcing. |
| Existing evidence | Software Architect/implementation, Independent QA, Documentation Manager and Git/CI responsibilities are distinct roles. | That separate people/executors are concurrently available for every role or that any work may be parallelized. |
| Test environment records | T169 used isolated PostgreSQL environments; prior native Electron verification had a headless limitation. | Persistent test-environment reservation, CI capacity, supported native-host availability, or release-operation staffing. |

Capacity conclusion: no resource allocation is confirmed. Scheduling must use a single-sequence assumption until a Project Manager obtains explicit availability information. Calendar dates are planning targets, not capacity-backed commitments.

## 5. Critical-path assessment and delivery scenarios

The calendar's `is_critical: false` / `slack_days: 0` values for T169–T171 cannot be read as a certified network calculation, because the calendar itself says the downstream dependency and capacity network is incomplete. T171 therefore certifies **no** critical path and **no** slack value. Official M1/M2/M3/finalization forecasts remain unchanged: 2026-11-15 / 2026-12-31 / 2027-02-28 / 2027-02-28.

The following are intentionally non-official planning scenarios, not forecast replacements. They illustrate the information required to turn M2 into an estimable plan. They start only after separate authorization of a successor task and assume one sequential delivery stream because capacity is unverified.

| Scenario | Explicit modelling assumptions | Illustrative effort band | Required overhead included | What would invalidate it |
| --- | --- | --- | --- | --- |
| Optimistic | 4 small, already-architected vertical slices; 5 implementation days each; no newly found defect or ADR gate. | 36–48 working days | 20 implementation + 8 independent QA + 4 governance/closeout + 4 integration + 4 operational-acceptance days; contingency 0–8. | Any unresolved ADR applies, native evidence is unavailable, or defects need remediation. |
| Base case | 5 slices; 7 implementation days each; two dependency/contract discoveries; sequential roles. | 65–85 working days | 35 implementation + 10 independent QA + 5 governance/closeout + 8 integration + 5 operational acceptance; 2–22 days discovery/rework. | Missing capacity data or a newly necessary migration/cutover can increase scope. |
| Conservative | 6 slices; 10 implementation days each; one ADR-resolution/replanning cycle and operational defect remediation. | 110–150 working days | 60 implementation + 18 independent QA + 12 governance/closeout + 15 integration + 10 operational acceptance;  -5 to +35 days schedule uncertainty from capacity and environment. | This band still excludes unbounded legacy cutover, finance, reporting, and post-V1 scope. |

These bands are a transparent sensitivity model, not an assertion that staff are committed, work can overlap, or M2 can meet its existing provisional date. They must not be inserted into the calendar without separate authority and a complete task graph.

## 6. Recommended next task (not authorized)

**Recommendation:** a smallest-scope, planning-only “M2 executable task-network and capacity evidence capture” task.

- **Purpose:** convert this capability baseline into a finite set of candidate vertical-slice tasks with typed predecessors, explicit ADR gates, test/operational acceptance obligations, and verified resource-availability inputs.
- **Prerequisites:** T171 protected implementation merge and its ordinary §3 closeout; Project Manager confirmation that no newer protected-main evidence supersedes this baseline.
- **Boundaries:** no product implementation, schema/migration, ADR promotion/resolution, forecast change, staffing commitment, or successor authorization. It may propose but cannot authorize tasks.
- **Acceptance criteria:** each proposed task has an authoritative scope source, finish-to-start versus evidence references, ADR preconditions, independently testable acceptance criteria, role/QA/governance overhead, and an explicit `unknown` where capacity or estimates are absent; the dependency graph either supports a reproducible calculation or states why it cannot.
- **Recommended execution role:** Project Manager / Control Tower with Software Architect input, because authorization sequencing, portfolio-level capacity evidence, and milestone forecasts are outside this implementation executor’s authority.

## 7. Reproduction checklist

At the stated protected baseline, a reviewer can reproduce this baseline with:

```text
git rev-parse origin/main
python scripts/governance_validate.py --report
python scripts/delivery_calendar.py
Get-Content -Raw PROJECT_STATE.json
Get-Content -Raw docs/delivery_calendar.json
Get-Content -Raw docs/acceptance/M1_Conditional_Operational_Acceptance.md
Get-Content -Raw docs/reviews/T169_QA_Review.md
Get-Content -Raw backend/src/app/presentation/api/v1/router.py
Get-Content -Raw frontend/src/app/routes.tsx
```

The results must be interpreted with the limitations above: successful validators or automated tests demonstrate their own checks, not full M2 readiness.
