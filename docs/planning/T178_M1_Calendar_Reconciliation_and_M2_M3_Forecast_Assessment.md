# T178 — M1 Calendar Reconciliation and M2/M3 Forecast Assessment

**Status:** Implementation candidate for Comprehensive / Risk Tier 1 Independent QA. This is an evidence and design package, not an authorization of product work, a calendar mutation, or a milestone acceptance decision.  
**Authority:** Project Owner Issue #377; authorization PR #378, protected merge `c0862cfa4f6eb60bc89f8f19562221ab9b004671`.  
**Evidence cut-off:** protected `main` `c0862cfa4f6eb60bc89f8f19562221ab9b004671`, 25 October 2026 (Asia/Kolkata).  
**Invariants preserved:** T177 is Done; T178 is Authorized/not Done; T167 remains Cancelled; Required ADRs `[12, 15, 16, 17, 20]` remain unresolved; ADR-0043/0047 remain Proposed; migration head remains `b155caa6d4e1`; M1 acceptance remains internal office dogfooding only.

## 1. Executive summary

M1 has a genuine, owner-authorized **Full Operational Acceptance for internal office dogfooding** dated 2026-10-25. The canonical decision is Issue #371 and its protected publication is PR #372, merge `b5ec4be7473556e1cd4c721f1a7b182649f56e75`; it reconciles protected T175 evidence and does not authorize unrestricted production release, M2, or Full V1 acceptance.

The current calendar correctly preserves M1's original baseline and historical forecast at 2026-11-15, but carries `actual: null`, `confidence: low`, and no completion provenance. The apparent 21-calendar-day early difference (`2026-10-25 - 2026-11-15`) is real as a comparison to the pre-existing forecast, but cannot safely become an official calendar variance under the present schema: milestone `actual` has no evidence tuple, no completed status, no completion-confidence semantics, and no immutable record of the forecast-at-completion. `scripts/delivery_calendar.py` only validates that an optional `actual` parses as a date; it does not verify acceptance provenance or distinguish a dogfooding acceptance from a release.

Accordingly, **no calendar field, milestone forecast, baseline, or history entry is changed by this PR**. The proposed controlled reconciliation is a separately approved calendar-schema/governance change, followed by a data-only M1 reconciliation. This avoids treating a bare date as evidence of a completed milestone.

The protected calendar yields exactly **20 completed tasks** from T157–T177 after excluding cancelled T167: 18 elapsed one inclusive calendar day, 2 elapsed two days; planned task-days sum to 77 and actual elapsed task-days sum to 22. The 55-day arithmetic difference is neither effort saved nor calendar acceleration: the dates record overlapping work, workflow/QA/closeout batching, and planning-task durations, while capacity and a complete downstream critical path remain unproven.

M2 and M3 official forecasts remain **2026-12-31** and **2027-02-28** with low confidence. No evidence supports replacing them. Scenario ranges below are non-official sensitivity outputs and show why a capacity-confirmed work network and ADR disposition are prerequisites to any official forecast movement.

## 2. Workstream A — M1 acceptance and calendar reconciliation

### 2.1 Verified provenance and boundary

| Fact | Evidence | Result |
| --- | --- | --- |
| Owner decision | GitHub Issue #371, 25 October 2026 | Full M1 operational acceptance approved only for internal office dogfooding. |
| Publication | PR #372, protected merge `b5ec4be…` | Durable acceptance publication, distinct from a product release. |
| Operational evidence | T175 implementation PR #369 and closeout #370; T175 QA/evidence records; M1 acceptance record | 35/35 operational scenarios and protected operational evidence are reconciled in the acceptance record. |
| Non-release boundary | `docs/acceptance/M1_Full_Operational_Acceptance.md` | Does not declare public production readiness, M2 acceptance, M3/Full V1 acceptance, or unrestricted commercial release. |

The only defensible accepted milestone date is **2026-10-25**, the date of the Project Owner's formal acceptance decision/publication. It is not the date each supporting task was merged.

### 2.2 Current contract and gap

Current M1 calendar record:

```json
{"baseline":"2026-11-15","forecast":"2026-11-15","actual":null,"confidence":"low","last_recalculated":"2026-10-19"}
```

`delivery_calendar.py` checks a milestone's baseline/forecast sequence and parses an optional `actual`, but does not:

1. require an issue, PR, protected merge SHA, acceptance scope, or date provenance for a non-null milestone actual;
2. model `completed`, `accepted-for-dogfooding`, `production-ready`, or another milestone state;
3. preserve the forecast value as-of completion or calculate/validate milestone variance;
4. define whether `confidence` describes a forecast, a completion fact, or the evidence quality of an acceptance;
5. surface milestone completion provenance in `PROJECT_STATE.json` cross-checks.

`history` is a forecast-movement ledger only. Adding a synthetic no-movement event to record an actual would misuse that contract and make historical forecasting less auditable.

### 2.3 Proposed controlled design — not implemented

The smallest governance-safe design is a versioned calendar schema extension, approved before implementation:

| Field | Proposed semantics | Preservation rule |
| --- | --- | --- |
| `actual` | Formal accepted completion date, only when an approved milestone-completion evidence object exists. | Original `baseline` and `forecast` remain untouched. |
| `completion_evidence` | Object containing decision Issue, publication PR, protected merge SHA, effective local date, accepted scope, and explicit non-release boundary. | Immutable after completion except a separately governed correction with an audit record. |
| `forecast_at_completion` | The then-current official forecast (`2026-11-15` for M1). | Never overwrite when later forecasts are recalculated. |
| `completion_variance_days` | Calendar-day `actual - forecast_at_completion`; M1 would be `-21`, classified `Early`. | Derived/validated, not hand-authored independently. |
| `completion_confidence` | Evidence quality for a completed outcome, separate from the historical pre-completion forecast confidence. | Use a constrained enum; do not overload `confidence`. |
| `acceptance_scope` | Explicit enum/text constrained to `internal_office_dogfooding` for M1. | Prevents a calendar actual from implying production release. |

Validator additions would require schema-version migration/backward compatibility: version-2 files remain valid until deliberately migrated; version-3 requires the full completion tuple when `actual` is non-null and rejects a tuple when it is null. Tests must prove missing/invalid provenance, invalid scope, changed `forecast_at_completion`, variance mismatch, and accidental production-release implication fail validation. `governance_validate.py` should cross-check the protected merge tuple against a documented acceptance provenance mapping rather than merely trusting a free-form date.

### 2.4 Disposition

The date correction itself is factually supported, but the **durable representation policy is absent**. This is a stop condition for calendar mutation, not for the assessment. Required owner decision: approve the schema/policy above (or a different formal model) and authorize its implementation as a separate governance task. Until then, leave `actual: null`, retain `forecast: 2026-11-15` as historical forecast evidence, retain `confidence: low` as forecast confidence, and record `-21` only in this assessment—not as official calendar data.

## 3. Workstream B — protected historical delivery analysis

### 3.1 Reproducible derivation

Source: `docs/delivery_calendar.json` at the protected cut-off. Filter: T157–T177 with non-null `actual_completion`, excluding T167 (Cancelled).

| Metric | Derived result |
| --- | ---: |
| Completed tasks | 20 |
| One inclusive calendar day | 18 |
| Two inclusive calendar days | 2 (T166, T175) |
| Sum planned task-days | 77 |
| Sum actual elapsed task-days | 22 |
| Arithmetic planned-minus-actual duration difference | 55 task-days |

The sum of individual forecast-finish variance fields is `-68`, which is intentionally a different measure: it compares each completion against its planned finish date and includes overlapping schedule geometry. Neither number is a project elapsed duration.

### 3.2 Interpretation limits

- **Inclusive calendar elapsed** measures each task's start/end dates, not person-days. A one-day task can involve multiple roles and prior work.
- **Person-day effort is absent.** No timesheets or resource allocation evidence exists, so 22 elapsed task-days cannot be transformed into effort or velocity.
- **Parallelism is observed, not capacity-proven.** Lanes and close temporal commits demonstrate overlap in the record; they do not prove simultaneous staff/environment capacity for future work.
- **Lifecycle overhead is material.** Authorization, implementation, independent QA, collaborator review, CI, protected merge and separate closeout form part of delivery duration. The historical series batches many governance/assessment tasks and is not comparable to a multi-sprint product feature.
- **Critical-path impact is indeterminate.** The calendar explicitly lacked a complete downstream network and capacity model. Early noncritical work does not pull a milestone forward under `delivery_calendar.forecast()`.
- **Task mix is heterogeneous.** T157–T177 includes governance hardening, architecture, documentation/assessment, targeted remediation, verification, UI/package evidence, and some application integration. It is not a calibrated sample for finance, workflow/government, migration/cutover, or release work.

Conclusion: the series proves fast protected-governance execution under the observed conditions. It does **not** prove 55 days saved, a 2.75-day average product-task duration, a resourcing level, or feasibility of either existing milestone forecast.

## 4. Workstream C — remaining capability inventory

| Capability | Current protected evidence | Classification | Remaining condition |
| --- | --- | --- |
| Matter workspace | Routes, frontend pages, tenant tests, M1 evidence | Implemented; operationally bounded | Selected M2 workflow/restart/regression acceptance. |
| Party and Property associations | Routes/UI/foundations and T177 journey evidence | Implemented; selectively verified | Property discovery/usability and fresh/migrated population boundary. |
| Enquiry/Quotation conversion | ADR-0043, routes/UI, T175/T177 evidence | Implemented; operationally verified for bounded journey | ADR-0043 remains Proposed; no new identifier/taxonomy/lifecycle expansion without gates. |
| Files/Documents/Versions | Routes/UI, integration and T177 byte evidence | Implemented; selectively verified | Real storage durability, full Electron operation, migration/cutover and retention boundaries. |
| Tasks/follow-ups | Framework artifacts only | Missing M2 vertical slice | Required ADR #12 and an authorized selected flow. |
| Workflow/government processes | Generic framework tests | Missing | Required ADR #12 plus selected domain/process contract. |
| Property completeness/UX | Foundation and associations exist | Partially implemented | Search/discovery, broader land/record behavior and office usability are not established. |
| Commercial/finance workflows | Schema/integrity traces; not M2 selected | Missing/out of M2 bounded slice | Separate product scope, finance boundary and operational evidence. |
| Electron integration/stability | Packaged shell/login plus T175/T176 evidence | Implemented; selectively operationally verified | Supported-host repeatability, selected workflow smoke, release packaging ownership. |
| Security/testing/migration/release | Tenant/RLS/RBAC foundation and test evidence | Partially implemented | Full capacity-backed regression policy, legacy convergence, storage/release readiness. |

No model, API, or page is treated as product-complete merely because it exists.

## 5. Architecture dependency matrix

| Dependency | Affected capability | Blocking condition | Avoidable/parallel work | Earliest safe sequence |
| --- | --- | --- | --- | --- |
| Required ADR #12 | Tasks/follow-ups; workflow/government processes | Blocks any new governed workflow/state-machine contract. | Avoid only by excluding those flows. | Resolve ADR, then authorize one finite vertical slice. |
| Required ADR #15 | Vocabulary/configuration changes | Blocks new/enlarged configurable taxonomy. | Existing fixed values can be reused in a narrow slice. | Prove fixed-value boundary or resolve before expansion. |
| Required ADR #16 | Human identifiers/references | Blocks new number/display contract. | Reuse existing identifiers unchanged. | Resolve before identifier redesign. |
| Required ADR #17 | Delete/archive/retention/history | Blocks lifecycle/retention behavior. | Create/read-only bounded flows can avoid it. | Resolve before lifecycle expansion. |
| Required ADR #20 | Legacy convergence/migration | Blocks legacy cutover/migrated-population claims. | Fresh-record-only bounded proof may avoid it. | Resolve before migration/cutover. |
| ADR-0043 Proposed | Conversion expansion | Current verified conversion is bounded; its architecture is not Accepted. | Preserve existing contract only. | Formal disposition before changing conversion semantics. |
| ADR-0047 Proposed | Operational-fresh schema compatibility | Blocks claims beyond reviewed compatibility scope. | Existing protected evidence can be consumed without changing compatibility policy. | Formal disposition before broader operational/migration work. |

## 6. Proposed executable remaining-work network

Planning labels below are not task IDs and do not authorize work. Estimates are sensitivity inputs, not commitments. Every package includes authorization, independent QA, CI/review, protected merge and closeout overhead.

| Package | Measurable outcome | Dependencies | Indicative implementation + QA/governance person-days | Roles/capacity | Parallelism |
| --- | --- | --- | --- | --- |
| P0 — scope/capacity confirmation | Owner-selected M2 boundary, environment/role availability and finite estimates | None | 3–5 | PM, Architect, QA; all availability Unknown | Prerequisite to capacity-backed schedule. |
| G12 — workflow/government ADR | Accepted decision and one scoped flow contract | P0 | 5–10 | Architect + QA; availability Unknown | May run with G15/16/17/20 only if separate reviewers available. |
| G15/16/17/20 — applicable gates | Only gates actually triggered by selected slice | P0 | 5–15 each | Architect, domain/QA; Unknown | Some are avoidable; do not assume parallel capacity. |
| V1 — selected office-workflow hardening | One cross-domain Matter/Party/Property/File/Document path with operations evidence | P0; only applicable gates | 10–18 | Backend, frontend, Electron host, QA; Unknown | Backend/frontend can overlap after contract freeze. |
| V2 — tasks/follow-up workflow slice | Role-safe follow-up flow and UI | G12; likely G15/17 | 15–30 | Architect, backend, frontend, QA; Unknown | After G12; could overlap V1 only with confirmed capacity. |
| V3 — property UX/completeness | Explicitly bounded discovery/association workflow | P0; possible G15/16/20 | 10–25 | Frontend/backend/QA; Unknown | Potentially parallel after contracts/capacity. |
| V4 — stabilization/release evidence | Cross-slice regression, native Electron, security/migration/release gates | V1–V3 | 15–30 | QA, operators, release owner; Unknown | Integration gate; generally serial. |

The network deliberately does not include finance/commercial expansion or unbounded government integrations. It needs owner-selected scope, ADR applicability decisions, named capacity, and task-level authorization before it can become an official schedule or critical-path calculation.

## 7. Scenario sensitivity — not official calendar forecasts

Assumption: one sequential delivery stream, Monday–Friday working calendar, start no earlier than 2026-10-26, no holiday adjustment, and no hidden capacity. These dates are transparent ranges, not commitments.

| Scenario | M2 sensitivity range | M3 / Full V1 conclusion | Key assumptions and drivers | Confidence |
| --- | --- | --- | --- | --- |
| Earliest plausible | 36–48 working days: approximately 2026-12-14 to 2026-12-30 | Indeterminate; any date requires a defined M3 scope after M2. | P0 immediate, only V1-sized scope, applicable gates avoided/resolved without delay, parallel roles available, no material defect/rework. | Very low. Meets the M2 baseline only under unconfirmed favorable assumptions. |
| Most likely | 65–85 working days: approximately 2027-01-23 to 2027-02-20 | Indeterminate; current 2027-02-28 baseline has no evidence-backed remaining-work model. | One stream, selected V1/V2/V3 work, normal governance cycles, some integration/rework, limited but available host/QA support. | Low. Indicates M2 baseline risk, not an official slip. |
| Conservative | 110–150 working days: approximately 2027-03-27 to 2027-05-22 | Indeterminate and cannot responsibly retain/replace 2027-02-28. | One or more ADR decisions, capacity waits, operational defect remediation, native-host availability constraints, stabilization and migration discovery. | Very low. Does not include unbounded legacy cutover, finance, reporting, or post-V1 work. |

The estimates follow T171/T172's published bands and are deliberately not converted into calendar changes. They demonstrate that official M2/M3 dates are not currently defensible, not that a particular revised date is correct.

## 8. Risks, decisions, and recommended governance action

1. **Owner decision — calendar policy:** approve or reject a versioned milestone-completion provenance/variance model before changing M1 `actual`.
2. **Owner decision — scope:** choose the finite M2 outcome and exclusions; M2 cannot be forecast as the entire Core V1 label without decomposition.
3. **Capacity confirmation:** identify availability for architecture, backend, frontend, independent QA, documentation/governance, native Windows operation and PostgreSQL/test environments.
4. **ADR sequencing:** decide which unresolved ADRs are genuinely triggered by the selected slice; do not resolve them by implication.
5. **Forecast policy:** after decisions 1–4, authorize a PM-owned schedule recalculation using the finite network. Until then retain all official forecasts and baselines unchanged.

Recommended next governance action: a separately authorized, policy-scoped calendar completion-provenance task if the owner wants M1 formally reconciled; in parallel or afterward, a Project Manager capacity/scope-confirmation task before any official M2/M3 forecast alteration. Neither action authorizes T179, application work, or a milestone acceptance.

## 9. Reproduction and validation

```text
git rev-parse origin/main
python scripts/governance_validate.py --report
python scripts/delivery_calendar.py
python scripts/current_context_manifest.py
python -m unittest scripts.tests.test_governance_validate -v
Get-Content -Raw docs/delivery_calendar.json
Get-Content -Raw docs/acceptance/M1_Full_Operational_Acceptance.md
```

The completed-task statistics can be reproduced by filtering T157–T177 calendar entries to non-null `actual_completion` and summing `planned_duration` and `actual_elapsed`; exclude T167 because its status is Cancelled and all completion fields are null.
