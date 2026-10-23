# T172 — M2 Executable Task-Network and Capacity Evidence Capture

**Status:** Implementation candidate for Independent QA. This is planning evidence, not task authorization, a staffing commitment, a delivery forecast, an ADR decision, or an operational-acceptance decision.

**Authority and cut-off:** T172 queue row; Project Owner Issue #351; authorization PR #352, protected merge `751f016cdaf999163f22c225538a1e216c586f96`; inspected 2026-10-23 (Asia/Kolkata). T171's protected completion and closeout are the immediate planning predecessor.

**Invariants:** `IMPLEMENTATION_QUEUE.md` alone authorizes numbered work and records Done. The identifiers below are planning labels, never task numbers. Required ADRs `[12, 15, 16, 17, 20]` remain unresolved; ADR-0047 remains Proposed. Forecasts remain unchanged. T167 remains Cancelled and its `T169` / `proposed_unapproved` evidence is historical provenance, not a finish-to-start predecessor. M1 conditional acceptance is dogfooding-only, not production or M2 acceptance.

## 1. Method and authority boundary

This finite candidate network refines—but does not replace—the T171 baseline. Its evidence sources are the frozen Domain Model & Functional Specification (Tasks A–O, §§18, 21, 26), `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, calendar sources, T171 planning/closeout records, M1 conditional acceptance, ADRs, and cited implementation/QA records. “Existing evidence” means evidence was found at cut-off; it does not mean M2 readiness.

A future Project Manager must select a bounded package, obtain owner authorization and register a separately numbered task before execution. Nothing here reserves an identifier, authorizes a task, resolves a gate, or assigns a person.

## 2. Candidate work packages

| Planning ID | Requirement/source | Existing evidence; remaining work | Exclusions | Testable acceptance and technical/operational verification | Role; QA/governance overhead | Confidence and gap |
| --- | --- | --- | --- | --- | --- | --- |
| `M2-P0` — outcome and capacity confirmation | T172 C/E; calendar capacity boundary; selection across Tasks A–O remains open. | T171/T172 establish candidates and no allocation evidence. Obtain owner-selected office outcome, written availability and estimate basis. | Product work, forecast change, inferred staffing, downstream authorization. | Record one selected outcome, exclusions, every role/environment as confirmed or **Unknown**, and estimate source/owner. | PM/Control Tower + Software Architect; independent QA; collaborator review, CI, protected merge, closeout. | **Low**—outcome, allocation, throughput and estimates Unknown. |
| `M2-G12` — workflow/government architecture and selected slice | Tasks J/K; Required ADR #12; M2 includes follow-up/applicable government processes. | Framework/workflow tests exist, not an M2 vertical slice. Decide ADR then authorize one selected flow. | Finance, universal government integration, unselected processes. | ADR #12 decision before dependent contract; tenant/role-negative, transition/validation, integration and supported-host workflow tests pass. | Architect; Backend/Frontend after authorization; independent QA and normal lifecycle. | **Low**—flow, ADR result, effort, host availability Unknown. |
| `M2-G15` — core/configurable vocabulary boundary | Required ADR #15; specification §26 item 16. | No evidence selects the M2 vocabulary/configuration boundary. Decide it, then implement only selected behavior. | Whole catalogue build, finance taxonomy, business-rule reinterpretation. | ADR decision; selected values receive tenant/authorization/validation tests and selected UI/workflow evidence. | Architect then appropriate developer; independent QA and protected lifecycle. | **Low**—owner selection and ADR result Unknown. |
| `M2-G16` — identifier/human-reference contract | Required ADR #16; §26 identifier concern. | File allocator evidence exists, but no cross-domain UUID/human contract is accepted. | Global rewrite, migration, claim existing IDs are final. | ADR decision; selected-contract collision/format/authorization negative tests; File allocator regression protection. | Architect and Backend where authorized; independent QA. | **Low**—affected domains, compatibility and effort Unknown. |
| `M2-G17` — lifecycle/history contract | Required ADR #17; §26 lifecycle/history concern. | Audit/history components exist, but no accepted cross-domain deletion/history rule. | Blanket deletion policy, purge, migration, legal-retention claim. | ADR states selected lifecycle/restore/retention/audit boundaries; transition, visibility and audit tests pass. | Architect, applicable Backend/Frontend; independent QA. | **Low**—policy, entity choice, migration impact Unknown. |
| `M2-G20` — legacy convergence/migration strategy | Required ADR #20; §26 items 7/10; Party/File/Document/Matter evidence. | Components/tests exist; legacy client/party and matter/file/document convergence is unresolved. Decide migration strategy and only then authorize a bounded cutover. | Schema/Alembic change in planning, bulk production migration, assumption current code resolves legacy. | ADR names population, cutover/rollback, validation and compatibility; any later work proves tenant isolation, idempotence/rollback and migrated-installation scenarios. | Architect + Backend; migration/integrity QA; normal protected lifecycle. | **Low**—legacy inventory, data quality, downtime and rollback Unknown. |
| `M2-V1` — Party/Property/Matter office workflow | Tasks A/B/C/G; ADR-0021/22/23/24/30/44; T171 inventory. | Routes/UI/foundations exist; T169 records isolated 942-pass suite; T163/T166 give conditional M1 evidence. Select one cross-domain workflow and prove it freshly. | Government workflow, finance, broad cutover, production release. | Selected persona completes allowed associations; tenant/RBAC-negative, integrity/restart/regression, supported-native-Electron tests pass. G15/G16/G17/G20 must be decided or explicitly avoided. | Backend + Frontend; Architect gate review; Comprehensive/Risk Tier 1 independent QA and lifecycle. | **Medium** code / **Low** operations—flow, gate applicability, host/capacity Unknown. |
| `M2-V2` — Matter/File/Document controlled lifecycle | Tasks G/H/I; ADR-0027/30/40/41. | Routes/UI, allocator and storage tests exist. Select an end-to-end lifecycle with failure/authorization/concurrency proof. | Unbounded document platform, storage-provider selection, global migration, source-only acceptance. | Selected flow passes tenant/authorization, version/rollback, storage-failure and applicable concurrent-numbering tests; supported-host upload/download/version smoke evidence. Evaluate G16/G17/G20 and Proposed ADR status. | Backend + Frontend; Architect review; independent QA/lifecycle. | **Medium** component evidence / **Low** selected-flow readiness. |
| `M2-V3` — Enquiry/quotation conversion | Task F plus G; ADR-0043; T148/T149 evidence named in T171. | Route/UI/integration evidence exists. Select conversion with retry, authorization, duplicate/integrity and Matter proof. | CRM expansion, communications/reporting, finance, presumed ADR acceptance. | Conversion links/creates permitted Matter exactly once or fails safely; retry/authorization/tenant negatives and UI evidence pass; ADR-0043 and G20 explicitly dispositioned. | Backend + Frontend; Architect review; independent QA/lifecycle. | **Medium** implementation / **Low** operation—contract/duplicate rule/capacity Unknown. |
| `M2-V4` — regression, native Electron and operational acceptance | T172 A/E/F; M1 decision; BLK-T163-01. | Electron shell/preload and M1 dogfooding evidence exist; headless native host is blocked. Run only after selected slices integrate. | Production release, reclassification of M1, unauthorized defect remediation. | Supported-host restart/session and selected workflows pass; selected integration/regression suites run in identified DB environment; QA records all pass/fail/blocked; owner makes separate M2 acceptance decision. | Independent QA leads; native-host operator, developers only under authorized defects, PM/owner decision; protected lifecycle. | **Low**—host, operator, environment, scenarios, acceptance availability Unknown. |
| `M2-S1` — communications/timeline/reporting/integrations disposition | Tasks L/O; T171 found no demonstrated Core-V1 operational slice. | Some framework/schema evidence, no M2 contract. Owner must exclude or authorize a bounded contract. | Implementation merely because frozen V1 mentions it; forecast implication. | Planning record maps M2 outcome to inclusion/exclusion; inclusion names contract, tenant/security boundary, acceptance tests/dependencies before build. | PM + Architect; independent QA for planning, normal lifecycle for later execution. | **Low**—M2 inclusion, external contract/privacy/capacity Unknown. |

Tasks A–I map to V1–V3 subject to G-series gates. Tasks J/K map to G12. Tasks L/O map to S1. Task M (finance) and Task N (advanced security beyond established tenant/RBAC) remain outside regular-office M2 unless later selected; this is an exclusion, not a deletion of V1 requirements.

## 3. Typed dependencies and gates

| From | To | Type | Evidence/rule | Scheduling meaning |
| --- | --- | --- | --- | --- |
| T171 | T172 | Finish-to-start | T171 is Done; T172 calendar lists T171. | Only verified execution predecessor of this planning task. |
| T167 (Cancelled) | T172 | Historical defect evidence | T172 calendar lists T167 only as `defect_evidence`; immutable cancellation provenance retained. | Never participates in topology or completes a predecessor. |
| `M2-P0` | every selected package | Capacity/selection prerequisite | Capacity matrix below. | Conditional; cannot become an execution edge until authorized/evidenced. |
| `M2-G12` | selected workflow/government package and V4 | Required ADR gate | ADR #12 unresolved. | Gate, no duration/completion known. |
| `M2-G15`/`G16`/`G17`/`G20` | impacted selected package | Architectural prerequisite | Required ADRs unresolved; applicability is package-specific. | Gate, not a declared finish-to-start edge. |
| V1/V2/V3 | V4 | Integration/acceptance dependency | M2 needs selected integrated slices; M1 is insufficient. | V4 only after selected prerequisite candidates clear their QA/lifecycle. |
| V1/V2/V3 | each other | Conditional parallelization | Components may separate, but people, DB environment, review and gate capacity are Unknown. | No parallel schedule is asserted. |
| ADR-0047, DEF-T163-01/02, BLK-T163-01 | selected package | Historical architecture/defect evidence | T171/M1 records. | Risk/acceptance input; not automatic authorization or satisfied predecessor. |

The only fully evidenced completed path is `T171 → T172`. No candidate package has an authorized estimate, selected scope, resolved gate, allocation or completion evidence. Therefore this network produces no executable project path, critical path, float/slack or milestone-feasibility result.

### Conditional safe sequence

1. Select M2 outcome and confirm inputs (`M2-P0`).
2. Authorize only the smallest necessary decision or vertical slice.
3. Resolve applicable G-series gates—or document why the bounded package avoids them.
4. Execute selected slices with integration/negative/regression evidence.
5. Run V4 after selected candidates clear their own independent QA and protected lifecycle; seek a separate owner acceptance decision.

## 4. Capacity evidence matrix

“Required” never means allocated. Calendar lanes are planning hypotheses, not staffing proof.

| Domain | Evidence | Availability/allocation | Model constraint |
| --- | --- | --- | --- |
| Software Architect / architecture | Role separation and unresolved G-series gates. | **Unknown** | No ADR-gated start/duration calculation. |
| Backend execution | Existing backend components; T169 isolated suite evidence. | **Unknown** | Code is not throughput/commitment evidence. |
| Frontend execution | Existing relevant UIs. | **Unknown** | No concurrent frontend stream assumed. |
| Independent QA | Exact-head independent QA is mandatory. | **Unknown** | Sequential QA stage, not overlap promise. |
| Documentation/governance | Authorization, QA publication, merge, closeout required. | **Unknown** | No same-day lifecycle assumption. |
| Collaborator approval | Protected review mandatory. | **Unknown** | Review latency uncertain. |
| Native Electron host/operator | BLK-T163-01 headless limitation; historical evidence. | **Unknown** | Operational acceptance unschedulable/inferable from headless checks. |
| Database/integration environment | T169 isolated PostgreSQL runs; Known Issues requires available Postgres/Docker for DB tests. | **Unknown** | No reservation, reset policy or simultaneous-test capacity. |
| Parallel execution | Lanes may overlap. | **Unknown** | Lane overlap is not evidence of people/reviewer/environment capacity. |

## 5. Reproducible scheduling model

For each future selected, authorized package `p`, retain source-backed inputs:

```text
I[p] = implementation effort                 = Unknown
A[p] = applicable ADR/architecture effort    = Unknown
Q[p] = independent QA/rework allowance        = Unknown
G[p] = authorization/review/CI/merge/closeout = Unknown
R[p] = integration/regression environment     = Unknown
O[p] = supported-host operational acceptance  = Unknown
C[p] = discovery/migration contingency        = Unknown
E[p] = I[p] + A[p] + Q[p] + G[p] + R[p] + O[p] + C[p]
```

For edge `u → v`, feasible start requires `finish(u) ≤ start(v)` and all applicable gates complete. Parallel starts require independently confirmed role, reviewer, environment and integration capacity. Until then, use `candidate elapsed effort = Σ E[p]` for selected packages. Every input is currently Unknown, so no duration/date follows. Critical path/slack needs selected finite nodes, durations, complete finish-to-start topology, fixed constraints and capacity evidence; none is available.

T171’s non-official sensitivity bands are retained, not promoted: optimistic **36–48**, base **65–85**, conservative **110–150 working days**. They assume respectively 4/5/6 slices at 5/7/10 implementation days with QA, governance/closeout, integration, operational acceptance and contingency included. They are not package estimates and cannot yield dates.

## 6. Delivery readiness and next recommendation

| Area | Assessment |
| --- | --- |
| Candidate sequence | P0 → applicable G-series decisions → owner-selected V1/V2/V3 → V4; S1 explicitly includes/excludes L/O. |
| Bottlenecks | Owner selection; ADR gates; migration boundary; absent role/reviewer/environment capacity; native host; integration/acceptance. |
| Confidence | High for bounded historical facts; Medium for component evidence; Low for sequence, duration, parallelism, M2 readiness and dates. |
| Optimistic | Four already-architected small slices, no new defect/gate, supported host/roles available; 36–48 day sensitivity only. |
| Base | Five slices, two contract/dependency discoveries, sequential lifecycle; 65–85 day sensitivity only. |
| Conservative | Six slices, ADR/replanning and operational remediation, excluding unbounded legacy cutover/finance/reporting; 110–150 day sensitivity only. |
| Official forecasts | None changed: M1/M2/M3/finalization remain provisional 2026-11-15 / 2026-12-31 / 2027-02-28 / 2027-02-28. |
| Missing for reliable schedule | Selected packages/exclusions; gate outcomes; estimate bases; role/reviewer/environment/native-host availability; integration order; accepted contingency; owner acceptance availability. |

**Smallest safe next task recommendation:** a planning-only task to obtain owner selection and documented capacity/estimate inputs for **one** candidate vertical slice. It must not authorize product work, reserve a task number, resolve an ADR by implication, change forecasts or claim capacity before those inputs are durable and independently reviewed.

## 7. Advisory tracking and reproduction

| Advisory | Candidate treatment | Future handling |
| --- | --- | --- |
| Incomplete downstream network/capacity (QA-T171-ADV-02 / QA-T172-AUTH-ADV-02) | Carried forward. | Obtain selected scope, estimates and explicit capacity before schedule certification. |
| Native Electron limitation (BLK-T163-01 / QA-T171-ADV-03 / QA-T172-AUTH-ADV-03) | Carried forward. | Use supported native host for selected M2 operations; headless checks are insufficient. |
| Stale `T170` assertion in `scripts/tests/test_current_context_manifest.py` (QA-T171-CLS-ADV-01 / QA-T172-AUTH-ADV-01) | Carried forward unchanged. | Repair only under separate authorization; this task does not edit unrelated tests. |

Reproduce against the stated baseline with:

```text
git rev-parse origin/main
python scripts/governance_validate.py --report
python scripts/delivery_calendar.py
python scripts/current_context_manifest.py
python -m unittest scripts.tests.test_governance_validate -v
python -m unittest scripts.tests.test_current_context_manifest -v
Get-Content -Raw docs/planning/T171_M2_Scope_Dependency_and_Capacity_Baseline.md
Get-Content -Raw docs/acceptance/M1_Conditional_Operational_Acceptance.md
```

The context-manifest test is expected to retain its pre-existing stale-frontier failure until separately authorized repair; its generator output is not changed by this candidate.
