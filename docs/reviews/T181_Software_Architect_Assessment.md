# T181 — M2 Core V1 Acceptance Boundary, ADR Applicability and Execution Readiness

**Status:** implementation candidate for Comprehensive / Risk Tier 1 Independent QA; this is an assessment, not M2/M3 acceptance, product authorization, or an ADR decision.
**Authority:** Project Owner Issue #389; authorization PR #390, protected merge `4eb428e9a81bc7232481707b665e6bf0527024df`.
**Evidence cut-off:** protected `origin/main` at `4eb428e9a81bc7232481707b665e6bf0527024df`, 2026-10-25 Asia/Kolkata.
**Preserved invariants:** T181 remains Authorized/not Done; all milestone dates and forecasts are unchanged; Required ADRs #12, #15, #16, #17 and #20 remain unresolved; ADR-0043/0047 remain Proposed; the sole migration head remains `b155caa6d4e1`; T167 remains Cancelled; M1 acceptance remains internal-office dogfooding only.

## 1. Decision summary

**Recommendation: CONDITIONAL GO** for one separately owner-authorizable, verification-only successor: **physical document-storage durability and current-head regression certification for the already verified post-conversion journey**. It is the smallest package that closes a confirmed M2 evidence gap without recreating T177, changing domain semantics, or presuming an unresolved Required ADR is decided.

The go is conditional on an isolated PostgreSQL 16 environment, a real filesystem/object-store test target with controlled fault injection, an available backend verification executor, Independent QA, collaborator/PR support, and a supported Windows Electron operator for only the changed-path smoke (not a redundant replay of T177). Each resource is **Unknown** at this assessment cut-off; therefore the package cannot be scheduled or started merely from this recommendation.

Confirmed code exists for tenant/RBAC foundations, Party, Property, Matter, File, Document/Version, and Enquiry-to-Matter conversion. T175 and T177 provide valuable historical, bounded operational evidence. They are not a current-head full-suite certification. Workflow/government-process vertical slices, Gujarat records, Scheme, communications/timeline, finance, reporting/integrations, and advanced-security features are either absent from the API/UI inventory or have no demonstrated Core-V1 vertical slice.

## 2. Evidence and interpretation rules

| Evidence class | Meaning in this report | Not evidence of |
| --- | --- | --- |
| **Confirmed implemented** | Current source exposes a model/service/API/UI surface. | Full requirement completion or operational acceptance. |
| **Partially implemented** | A foundation exists but the frozen task’s full scope is not found. | Missing parts being implicitly excluded. |
| **Confirmed missing** | No corresponding route/UI/vertical-slice evidence was found in the inspected inventory. | Proof that no latent code exists outside the inspected tree. |
| **Operationally unverified** | Code or prior tests exist, but no current-head evidence covers the required environment/outcome. | A defect. |

Historical evidence is preserved at its original scope: T169 recorded two isolated PostgreSQL full-suite runs of **942 passed**; T175 verified conversion/retry/rollback/tenant-RBAC and Windows Electron operation; T177 verified the continuous accepted-quotation through DocumentVersion API journey. T177 also explicitly retained the real-storage durability limitation and Property-search/Party-detail usability advisories. None is re-run or claimed as fresh certification here.

## 3. Tasks A–O requirement-to-capability matrix

| Task | Frozen required outcome | Current source/evidence | Classification | M2 boundary / remaining condition |
| --- | --- | --- | --- | --- |
| A | Organization, membership, teams, roles, permissions, tenant enforcement; no cross-org access. | Auth/users, Organization and RBAC routes/services; tenant/RLS tests; T169 suite evidence. | Implemented foundation; operationally unverified at current head. | Preserve tenant/RBAC negatives in every selected slice; legacy convergence invokes #20. |
| B | Party, relationships, representatives and role reuse across Matters. | Party API/UI, `MatterParty`, tenant tests; T177 proves canonical client Party for one journey. | Partially implemented / selectively verified. | Party-detail usability is advisory; relationship breadth and migrated-population behavior remain unverified. |
| C | Property, land, approved units and ownership distinctions. | Property API/service/UI, owner model; T177 verifies association of an existing Property. | Partially implemented / selectively verified. | Land/unit breadth and search/discovery are not established; Property search is an advisory, not a confirmed defect. |
| D | Gujarat revenue, city survey, TP/FP and non-conflation of record types. | No route in `api/v1/router.py`, no route/page evidence. | Confirmed missing vertical slice. | Separate domain contract and likely #15/#16 work before implementation. |
| E | Scheme and flexible Building/Block/Section/Unit structure. | No API/UI vertical-slice evidence. | Confirmed missing vertical slice. | Owner-selected scope and vocabulary/identifier decisions required. |
| F | Enquiry, quotation, acceptance/rejection and commercial proposal. | Enquiry/quotation API and UI; `AcceptanceService`; T175/T177 conversion proof. | Implemented and operationally verified for the bounded conversion path. | Do not broaden conversion or commercial/finance semantics; ADR-0043 remains Proposed. |
| G | Matter, parties/properties, classification/work type and lifecycle; accepted engagement before File. | Matter API/UI, `MatterParty`, `MatterProperty`; T175/T177 prove bounded conversion-to-Matter path. | Partially implemented / selectively verified. | Lifecycle, taxonomy, identifiers and migration boundaries remain gated. |
| H | Matter/File relation and concurrency-safe numbering. | File API/UI, allocator tests and T177 File creation. | Implemented / selectively verified. | Fresh concurrency and current-head regression evidence is required for changed-path work; #16/#17/#20 may apply. |
| I | Documents, types, versions, storage and security. | Document/version API/UI and storage port tests; T177 byte-integrity via `MemoryStorage`. | Implemented, but physically durable storage is operationally unverified. | This is the confirmed evidence gap selected for the recommended successor. |
| J | Workflow definitions, instances, stages, tasks and assignment. | Generic workflow model/engine tests; no API/UI vertical slice. | Confirmed missing M2 vertical slice. | #12 blocks any new workflow/state-machine contract; #15/#17 may also apply. |
| K | Government processes, authority/office/reference/events/status. | No route/UI vertical slice found. | Confirmed missing M2 vertical slice. | #12 blocks selection/implementation of a government-process flow. |
| L | Communications, participants, activity/follow-up/timeline. | Framework/schema traces only; no demonstrated Core-V1 surface. | Confirmed missing vertical slice. | Owner must explicitly include or defer; no silent scope reduction. |
| M | Commercial Scope, charges, expenses, invoice, payment, allocation/refund. | Financial models/tests exist, but no API/UI office workflow. | Partially implemented foundation; outside selected M2 evidence. | Do not infer finance acceptance from integrity tests; separate scope/ADR #13 decision needed. |
| N | Matter/file/document access, sensitivity, external sharing, advanced audit. | Baseline tenant/RBAC/audit foundations. | Partially implemented foundation. | Existing tenant/RBAC remains a required constraint, not proof of advanced-security completion. |
| O | Reports, dashboards and integrations. | No reported API/UI vertical slice. | Confirmed missing vertical slice. | External contract, privacy/security and owner selection required before work. |

The router exposes addresses, auth, documents, enquiries, files, lookups, matters, parties, properties, users and version—not Tasks D/E/J/K/L/M/O as a Core-V1 application surface. The frontend router analogously exposes login, parties, enquiries/quotations, matters/files/documents. This direct inventory is why absence above is called **missing vertical-slice evidence**, not an empty code-search conclusion.

## 4. Verified gap register and reconciliation

| ID | Type | Evidence-backed finding | Disposition |
| --- | --- | --- | --- |
| GAP-01 | Operational verification | T177 AC-07 uses `MemoryStorage`; physical filesystem/object-store durability, restart persistence, and storage fault behavior were deliberately out of scope. | Confirmed unverified, not a product defect. First successor target. |
| GAP-02 | Current-head certification | T169’s 942-pass runs are historical; T177 did not claim a complete observed backend run. | Unverified at current head; run full suite in isolated PostgreSQL for the selected verification package. |
| GAP-03 | Workflow/government | No selected API/UI vertical slice for Tasks J/K. | Confirmed missing functionality; #12 gate before any new contract. |
| GAP-04 | Property/Party usability | T177 records no server-side Property search and no Party-detail UI. | Non-blocking advisory; owner may authorize UX work separately. |
| GAP-05 | Legacy/migrated installations | Fresh operational path has evidence, but legacy convergence is unresolved. | Unverified/blocked for migrated-population claims by #20. |
| GAP-06 | Capacity and operations | No durable current allocation/reservation evidence exists. | Unknown, not an implementation gap or schedule commitment. |

## 5. Required-ADR applicability matrix

Required ADR numbers are specification planning-list identifiers, not repository ADR filenames. “Avoidable” means only that a strictly bounded package can exclude the decision; it does not resolve it.

| Gate | Storage verification (recommended) | Existing F/G bounded verification | New J/K workflow/government | D/E/L/M/N/O expansion | Why |
| --- | --- | --- | --- | --- | --- |
| #12 Workflow vs government status | Non-blocking | Conditionally avoidable | **Blocking** | Blocking where workflow/government status is introduced | New state-machine/government contract needs the decision. |
| #15 Core vs configurable vocabulary | Conditionally avoidable | Conditionally avoidable | Blocking if stages/statuses are added | Usually blocking | Existing fixed values may be exercised; new taxonomy cannot be invented. |
| #16 UUID vs human-readable identifiers | Non-blocking if existing IDs unchanged | Conditionally avoidable | Conditionally avoidable | Usually blocking | Existing ID contracts may be reused; new references/numbers may not be designed by implication. |
| #17 Soft deletion/history | Non-blocking | Conditionally avoidable | Blocking for lifecycle/history behavior | Usually blocking | Read/write verification does not decide retention, restore or deletion. |
| #20 Migration strategy | Non-blocking for operational-fresh storage target | Blocking for legacy/migrated claims; avoidable only with explicit fresh boundary | Conditionally avoidable | Blocking for legacy/cutover | It governs legacy client/party/schema convergence, not ordinary fresh-target tests. |

**Proposed ADR-0043:** relevant to conversion semantics only. Existing T175/T177 conversion evidence may be consumed unchanged, but conversion behavior must not expand or claim acceptance of ADR-0043 while it is Proposed.

**Proposed ADR-0047:** relevant to operational-fresh schema-revision compatibility. The recommended task may use the protected `b155caa6d4e1` frontier, but must not alter compatibility policy or claim migrated-installation support. It remains Proposed.

## 6. Test and operational acceptance evidence

| Obligation | Historical evidence that may be reused | Fresh evidence required before a current-head claim |
| --- | --- | --- |
| Conversion/retry/rollback | T175 focused PostgreSQL scenarios; T177 journey. | Only if the selected change touches conversion or its dependencies. Do not rerun solely for duplication. |
| Authenticated Windows Electron | T175 human-operated restart/session evidence; T177 fresh packaged-login observation and unchanged-path rationale. | Changed-path Windows smoke; a full T177 replay only if auth/Electron/journey code changes or QA identifies a concrete reason. |
| PostgreSQL/tenant/RBAC | T169 isolated suite; T175/T177 negative scenarios. | Selected package’s positive, cross-tenant and role-denied cases on isolated PostgreSQL 16. |
| Document bytes/storage | T177 API byte-integrity with `MemoryStorage`. | Real storage persistence across restart plus write/read/delete-failure handling and cleanup/fail-closed behavior. |
| Regression | Historical 942-pass T169 result. | Complete backend suite at candidate head, with exact environment and result recorded; relevant frontend/Electron checks for changed paths. |
| M2 acceptance | None. | Separate owner decision after selected outcomes and operational evidence; this assessment does not supply it. |

## 7. Resource and environment readiness

| Resource / environment | Status | Evidence / required corrective action |
| --- | --- | --- |
| Software Architect | Unknown | Role exists; no availability commitment. Confirm before ADR-sensitive scope. |
| Backend executor | Unknown | Existing code is not allocation evidence. Confirm for verification/fix ownership. |
| Frontend executor | Unknown | Not required unless a changed UI path is selected. |
| Independent QA | Unknown | Mandatory Comprehensive/Risk Tier 1 exact-head review; obtain commitment. |
| Documentation Manager / Git-CI PR manager / collaborator | Unknown | Required by three-PR lifecycle; obtain named availability. |
| Isolated PostgreSQL 16 and reset policy | Unknown | Historical environments existed; reserve current disposable target. |
| Real storage target and fault controls | Unknown | Mandatory for GAP-01; provide filesystem/object-store fixture, cleanup and controlled failure method. |
| Windows Electron operator/host | Unknown | Required only for changed-path smoke; historical T175 evidence is not a booking. |
| M2 acceptance participants / Owner decision | Unknown | No participant pool or acceptance window is recorded. |

## 8. Finite successor network and feasibility

Planning labels are not task IDs and do not authorize work.

```text
Owner scope + resource confirmation
          ↓
P1 Storage durability/current-head verification ──→ P2 selected M2 vertical slice
          ↓                                              ↓
   Independent QA / protected merge                 applicable ADR decision(s)
                                                         ↓
                                              integration / Windows evidence
                                                         ↓
                                                  Owner M2 acceptance
```

| Package | Dependency | Outcome / acceptance | Exclusions | Risk / estimate |
| --- | --- | --- | --- | --- |
| P0 — confirm scope/resources | None | Owner selects P1; every matrix resource is Confirmed or Unknown. | Product work, forecast changes. | Tier 1; 2–4 person-days, estimate requires owner confirmation. |
| P1 — storage durability/current-head verification | P0; real storage + PostgreSQL + QA available | Real-storage upload/download survives restart; fault paths leave no false success/orphan metadata; selected tenant/RBAC negatives; full backend suite result recorded; changed-path Windows smoke. | No schema, storage-provider redesign, conversion redesign, ADR change, M2 acceptance. | Tier 1; 6–12 person-days including QA/governance/ops, conditional on environment. |
| P2 — owner-selected missing vertical slice | P1 only as evidence prerequisite where document path is involved; applicable ADRs decided/avoided | One finite J/K, property UX, or other owner-selected outcome with tests and operating evidence. | Unselected Tasks A–O, finance/reporting/legacy cutover unless expressly selected. | Tier 1; **Unknown** until selection/ADR/capacity. |
| P3 — integrated M2 acceptance package | Selected P2 slices, resolved/avoided gates, confirmed participants | Current-head regression, supported Windows operations, evidence record and owner acceptance input. | Production/M3 acceptance. | Tier 1; **Unknown**. |

No complete duration-bearing finish-to-start graph, capacity allocation, or accepted scope exists. T171/T172 sensitivity bands (36–48 / 65–85 / 110–150 working days) remain context only. Thus **M2 2026-12-31 is feasible only under unverified favorable assumptions and is not currently defensible as a delivery commitment**. M3 2027-02-28 is likewise indeterminate because its remaining scope and M2 completion are not defined. Official forecasts remain unchanged.

## 9. Publication/QA boundary and reproduction

This PR-2 candidate adds assessment evidence only. It does not perform independent QA, authorize P0/P1/P2, mark T181 Done, alter an ADR, change application code, migration, calendar forecast, or milestone acceptance.

Reproduce the assessment from the cut-off with:

```text
git rev-parse origin/main
python scripts/governance_validate.py --report
python scripts/delivery_calendar.py --validate
python scripts/current_context_manifest.py
python -m unittest scripts.tests.test_governance_validate -v
python -m unittest scripts.tests.test_current_context_manifest -v
```

The context-manifest unit test’s hardcoded `T170` frontier assertion is historical baseline debt and is expected to fail against the current T180/T181 frontier; it is intentionally not changed by this task.
