# T173 — M2 Outcome Selection and Capacity Baseline Confirmation

**Status:** Implementation candidate for Independent QA. This is planning evidence and a conditional technical recommendation. It neither records a Project Owner outcome selection nor authorizes product work, staffing, ADR resolution, a schedule commitment, or M2 acceptance.

**Authority and cut-off:** Project Owner approval recorded by Issue [#355](https://github.com/Intelligentclown/Legal_DMS/issues/355); authorization PR [#356](https://github.com/Intelligentclown/Legal_DMS/pull/356), protected merge `9dccb34466a9cb612a6c190944e7237ab76f7478`; inspected 2026-10-23 (Asia/Kolkata). T172 is the completed planning predecessor.

**Preserved invariants:** T167 remains terminal `Cancelled`, with immutable `T169` / `proposed_unapproved` successor provenance; T168–T172 remain Done; T173 remains Authorized, not Done. Required ADRs `[12, 15, 16, 17, 20]` remain unresolved; ADR-0047 remains Proposed; the migration frontier remains `b155caa6d4e1`. M1 is conditional dogfooding acceptance, not production or M2 acceptance. Official provisional forecasts remain M1 2026-11-15, M2 2026-12-31, M3 2027-02-28 and finalization 2027-02-28.

## 1. Evidence classification and decision boundary

| Classification | Evidence / conclusion | Boundary |
| --- | --- | --- |
| Verified repository evidence | T171 inventories existing Party/Property/Matter, File/Document and Enquiry/Quotation surfaces and their test evidence. T172 records `M2-V1`, `M2-V2` and `M2-V3` as planning candidates and records capacity as Unknown. T173’s calendar dependency is `finish_to_start: ["T172"]`; T167 is `defect_evidence`, not a schedule predecessor. | Existing code/tests are not independent M2 operational readiness evidence. |
| Project Owner decision | Issue #355 approves T173 planning work. It does **not** select `M2-V1`, `M2-V2`, or `M2-V3`. No distinct selection decision was found in the authorization issue/PR, queue, calendar, T171 or T172 evidence at cut-off. | Outcome selection is **Pending**. No selection is inferred from approval of T173 or from a technical recommendation. |
| Technical recommendation | Subject to the missing Owner decision and gates below, `M2-V3` is the smallest evidence-backed candidate to take into a bounded pre-implementation definition package. | This is not authorization to implement `M2-V3`, assign a task ID, or accept ADR-0043. |
| Assumption | A future selected vertical slice can be constrained to fresh, tenant-scoped records and can explicitly exclude legacy migration, new vocabulary/configuration, identifier-contract changes and lifecycle-policy changes. | This requires future scope confirmation; it is not demonstrated by the current repository. |
| Unknown / unavailable evidence | Owner outcome selection, staffed roles, reviewer/collaborator availability, environment reservation, native-host operator, operational-acceptance participants, package durations and usable contingency are all Unknown. | Unknown is not converted into a commitment, concurrency claim, date or critical-path value. |

## 2. M2 outcome comparison

The candidate labels originate in T172 and map to frozen specification work, not numbered executable tasks. “Readiness” below is only an assessment of traceable implementation/test evidence; it is not a readiness approval.

| Candidate | Business value and existing evidence | Readiness and unresolved dependencies | Required verification / operational constraints | Assessment |
| --- | --- | --- | --- | --- |
| `M2-V1` — Party / Property / Matter workflow | A cross-domain regular-office flow aligns with Tasks A/B/C/G. T171 records tenant-scoped routes, Party/Property/Matter UI and tests; T169 records an isolated 942-pass backend-suite run. | Broadest package: association semantics and G15/G16/G17/G20 applicability must be determined. T171 retains conditional M1 evidence and duplicate-number follow-up concerns. | Persona workflow, association integrity, tenant/RBAC negatives, restart/regression and supported-native-Electron proof. | High business coherence, but it spans several foundations and has the largest unresolved architecture surface. Not the smallest initial package. |
| `M2-V2` — Matter / File / Document lifecycle | Tasks G/H/I have Matter/File/Document routes, UI, allocator and storage evidence. | A lifecycle requires selected version/storage/failure rules; G16/G17/G20 and Proposed ADR-0040/0041 applicability need disposition. | Tenant authorization, version/rollback, storage failure, concurrency/numbering, upload/download and native-host smoke proof. | Useful controlled-record outcome, but the lifecycle and operational verification are wider than a first bounded conversion. |
| `M2-V3` — Enquiry / Quotation conversion | Task F plus Matter linkage has existing enquiry/quotation routes/UI and T148/T149 evidence recorded by T171/T172. Its business outcome can be bounded to one conversion path. | Conversion contract, duplicate/retry behavior, Matter linkage, ADR-0043 and G20 must be explicitly handled. No independent M2 operating proof exists. | One allowed conversion creates/links a Matter exactly once or fails safely; tenant/RBAC negatives, retry/duplicate/integrity, UI integration, PostgreSQL regression and supported-host evidence. | Narrowest candidate with identifiable end-to-end business outcome, provided the Owner selects it and gates can be avoided or resolved. |

### Conditional technical recommendation

Recommend `M2-V3` **only as the technical starting point for a future Owner decision and bounded package-definition task**. It has a contained conversion boundary and existing surface evidence, whereas V1 combines Party/Property/Matter semantics and V2 combines lifecycle, storage and versioning concerns. The recommendation excludes CRM expansion, communications/reporting, finance, legacy cutover, schema/migration work, new identifiers, new configurable vocabulary, deletion/history policy, production release and any inference that existing tests prove operational readiness.

The Project Owner has not selected an initial M2 outcome in durable evidence available to T173. The decision remains **Pending**; no implementation may rely on this recommendation until a separately authorized selection and scope boundary exist.

## 3. Capacity evidence matrix

“Required capacity” describes a future package need, not an allocation. Calendar lanes and previous completion velocity are not capacity evidence.

| Capacity category | Required capacity for a selected package | Confirmed availability | Evidence source | Limitation / confidence |
| --- | --- | --- | --- | --- |
| Software Architect | Scope/gate review and contract boundary before implementation. | **Unknown** | T171/T172 show unresolved architecture gates; no availability record. | No allocation or turnaround evidence. **Low**. |
| Backend developer | Tenant-safe conversion/service and regression work if authorized. | **Unknown** | Existing backend surfaces show code evidence only. | Existing code is not a person commitment. **Low**. |
| Frontend developer | Selected conversion UI/integration work if authorized. | **Unknown** | Existing enquiry/quotation UI is implementation evidence only. | No staffing or parallel-stream evidence. **Low**. |
| Independent QA Reviewer | Independent exact-head comprehensive/Risk Tier 1 review and rework verification. | **Unknown** | Workflow requires independent QA. | Mandatory role does not establish reviewer availability. **Low**. |
| Documentation Manager | QA publication, synchronization and closeout after a future implementation candidate. | **Unknown** | §3.1 workflow. | No availability or lifecycle turnaround commitment. **Low**. |
| Git/CI PR Manager and collaborator approval | PR operation, CI observation and protected collaborator approval. | **Unknown** | Protected lifecycle and historical PR records. | Historical successful PRs do not reserve reviewer/CI capacity. **Low**. |
| PostgreSQL / integration-test environment | Isolated database, reset/fixture policy and integration execution. | **Unknown** | T169 records isolated PostgreSQL evidence; Known Issues documents environment constraints. | No current reservation, operator, reset or concurrent-use evidence. **Low**. |
| Supported native Electron host and operator | Native session/restart and selected workflow verification. | **Unknown** | BLK-T163-01 and M1 conditional acceptance record headless limitation. | Headless evidence cannot substitute for a supported host/operator. **Low**. |
| Operational acceptance participants | Independent operational scenario execution and later Owner decision. | **Unknown** | M1 record and §3.1 boundaries. | M1 dogfooding is not a committed M2 participant pool. **Low**. |

No concurrency, throughput, staffing allocation, reviewer slot, environment reservation or operational-acceptance window is confirmed. Consequently, no schedule feasibility or critical-path certification follows.

## 4. Reproducible estimate baseline

The following is a reproducible input model for the conditional `M2-V3` recommendation. It intentionally contains no numerical estimate: neither T171’s sensitivity bands nor historical task elapsed time is credible package effort evidence.

| Component | Value | Required source / assumption | Estimate owner | Confidence |
| --- | --- | --- | --- | --- |
| `A` — architecture and ADR effort | **Unknown** | Owner-selected outcome; ADR-0043/G20 disposition; applicability findings below. | Software Architect after selection. | Low |
| `B` — backend implementation effort | **Unknown** | Approved conversion contract, tenant/RBAC boundaries, duplicate/retry semantics and available backend capacity. | Backend lead/assigned developer. | Low |
| `F` — frontend implementation effort | **Unknown** | Approved UX boundary, error/retry behavior and available frontend capacity. | Frontend lead/assigned developer. | Low |
| `I` — integration and regression effort | **Unknown** | PostgreSQL environment, fixtures/reset policy and selected cross-surface scenarios. | Technical lead + integration environment owner. | Low |
| `Q` — independent QA and rework allowance | **Unknown** | Reviewer availability, Risk Tier 1 plan, defect/rework history for this selected contract. | Independent QA Reviewer. | Low |
| `G` — governance/review/CI/protected-merge overhead | **Unknown** | Collaborator and Documentation Manager availability; actual CI/review timing. | Project Manager / PR manager. | Low |
| `H` — supported-host operational verification | **Unknown** | Native host/operator and named operational participants. | Operational acceptance coordinator. | Low |
| `C` — contingency | **Unknown** | Risk register after gate disposition and environment/capacity evidence. | Project Manager with delivery roles. | Low |

```text
E(M2-V3) = A + B + F + I + Q + G + H + C
```

`E(M2-V3)` remains **Unknown** because every input is Unknown. A future estimate record must name the evidence date, source, assumptions, owner and confidence for each input, then independently confirm capacity before translating effort into duration. T171’s 36–48 / 65–85 / 110–150 working-day planning sensitivity bands remain non-official scenario context only and are not used here as package estimates or milestone forecasts.

## 5. Dependency and architecture assessment

This classification describes what a future bounded `M2-V3` package would need to demonstrate. It does not resolve, promote or modify any ADR.

| Gate / record | Classification for a strictly bounded V3 package | Required reasoning / boundary |
| --- | --- | --- |
| Required ADR #12 — workflow versus government | Applicable only to later work | Avoid only by excluding follow-up/government workflow/state-machine behavior. It becomes required before adding either. |
| Required ADR #15 — core versus configurable vocabulary | Avoidable through bounded scope | Use existing approved-in-code values only; no new vocabulary/configuration model. Any new/enlarged conversion status taxonomy makes it a pre-implementation gate. |
| Required ADR #16 — UUID versus human identifiers | Avoidable through bounded scope | Reuse existing identifiers without altering identifier contracts, generation or display rules. New Matter/reference behavior makes it a gate. |
| Required ADR #17 — lifecycle/history | Avoidable through bounded scope | Limit to create/link and safe failure/retry behavior; exclude deletion, archival, restoration and policy changes. Extending lifecycle behavior makes it a gate. |
| Required ADR #20 — legacy convergence/migration | Avoidable only with explicit fresh-record boundary | No legacy client/party conversion, data migration, cutover or compatibility claim. If V3 touches legacy population/convergence, ADR #20 is required before implementation. |
| ADR-0043 — enquiry/quotation conversion | Unresolved pending further evidence | T171/T172 identify it as the relevant conversion architecture, but it remains Proposed and cannot be treated as accepted. A future package must obtain an authorized architectural disposition or avoid the decision it governs. |
| ADR-0047 — operational-fresh party revision compatibility | Unresolved pending further evidence | It remains Proposed. V3 should exclude Party revision/compatibility changes; if conversion depends on them, architecture and supported-environment evidence are required. |
| ADR-0021/0022 and existing tenant/RBAC implementation | Required before implementation as constraints | No status promotion is implied. Future acceptance must prove tenant isolation and role-denial behavior for the selected conversion at API and UI boundaries. |
| Migration frontier `b155caa6d4e1` | Required environmental constraint | No schema or Alembic work is in scope. Integration evidence must use the supported frontier without implying migration readiness. |

The only completed typed task edge relevant to T173 is `T172 → T173` finish-to-start. T167 is historical defect evidence, never a predecessor. A later selected package cannot obtain a critical-path value, slack, or date from this analysis because outcome selection, finite work nodes, estimates, capacity and gate disposition are incomplete.

## 6. Smallest safe successor recommendation (not authorization)

**Proposed objective:** a planning-and-architecture package that records the Project Owner’s selection (or explicit deferral) of one M2 candidate and, if `M2-V3` is selected, produces a bounded conversion contract and gate-applicability record before feature work.

| Area | Recommendation boundary |
| --- | --- |
| Scope | Owner selection record; one V3 conversion persona/use case; Matter creation/linking rule; duplicate/retry/failure semantics; explicit ADR #12/#15/#16/#17/#20, ADR-0043 and ADR-0047 applicability; evidence/estimate-input plan. |
| Exclusions | Product code, schema/migrations, ADR approval, staffing allocation, schedule/forecast changes, CRM/communications/reporting/finance, legacy cutover, production/M2 acceptance and a numbered task authorization. |
| Dependencies | Durable Owner selection; T173 evidence; architecture-role availability; access to current ADR/specification evidence. Any legacy, identifier, vocabulary, lifecycle, Party revision or government-workflow expansion invokes the applicable gate above. |
| Capacity requirement | Software Architect and Project Owner decision availability are required; all other roles remain Unknown until scope and evidence plan establish a need. |
| Acceptance criteria | A reviewer can identify the Owner’s decision; exact selected and excluded behavior; conversion input/output and failure/retry/duplicate rules; each ADR’s required/avoided/later/unresolved status; tenant/RBAC test obligations; named estimate inputs/owners; and every capacity field confirmed or Unknown. |
| Security and tenant isolation | Define positive and cross-tenant/role-denied conversion tests at API and UI boundaries; prove no unauthorized enquiry, quotation or Matter linkage/visibility. |
| Integration and operational evidence | Define PostgreSQL integration, regression and supported-native-Electron scenarios, environment prerequisites and named acceptance participants; do not substitute headless checks or M1 dogfooding. |
| Principal risks | Owner selection remains absent; ADR-0043/0047 Proposed; required-ADR applicability may expand scope; duplicate/retry semantics may reveal integrity constraints; all staffing/environment/native-host evidence is Unknown. |

This recommendation deliberately has no task number and does not authorize T174 or any other successor.

## 7. Advisory carry-forward and validation boundary

| Advisory | T173 treatment |
| --- | --- |
| `QA-T172-ADV-01` — stale hardcoded T170 context-manifest assertion | Carried forward unchanged. The assertion is unrelated to planning evidence and must be repaired only under separate authority. |
| `QA-T172-ADV-02` — unverified downstream M2 capacity and scheduling inputs | Carried forward. This document makes the missing inputs explicit; it does not resolve them. |
| `QA-T172-ADV-03` — native Electron host and operational-acceptance limitations | Carried forward. A supported native host/operator remains required for selected-workflow operational evidence. |

Reproduce the planning evidence against the stated baseline with:

```text
python scripts/governance_validate.py
python scripts/governance_validate.py --report
python scripts/delivery_calendar.py
python scripts/current_context_manifest.py
python -m unittest scripts.tests.test_governance_validate -v
python -m unittest scripts.tests.test_current_context_manifest -v
git diff --check
```

Passing automation supports consistency only. It does not demonstrate outcome selection, capacity availability, schedule feasibility, native-host readiness, independent QA approval or M2 operational acceptance.
