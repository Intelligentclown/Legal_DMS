# T174 Architecture Assessment — M2-V3 Enquiry / Quotation Conversion Contract and Gates

**Task:** T174 — M2-V3 Enquiry / Quotation Conversion Contract and Architectural Gate Assessment
**Role:** Software Architect
**Lifecycle:** `PROJECT_WORKFLOW.md` §3.1 PR 2 of 3 — assessment candidate, pending independent QA
**Authorization:** Issue #359; authorization PR #360, merged as `725e6395b741ee06677468ff4ddacd599ec6f32d`
**Assessment baseline:** protected `origin/main` at `725e6395b741ee06677468ff4ddacd599ec6f32d` on 2026-10-23 (Asia/Kolkata)
**Scope:** Planning and architectural assessment only. This document makes no application, schema, migration, ADR-status, calendar, forecast, task-status, or capacity-allocation change.

## 1. Decision summary and readiness recommendation

The source tree already contains a bounded enquiry-to-quotation-to-acceptance-to-Matter conversion implementation. It is not merely a proposed M2 capability: its persistence schema, API, application service, UI, and focused PostgreSQL/API tests are present. This is a material repository fact that a future M2 package must not obscure or re-implement by assumption.

The existing implementation is a sound **contract candidate**, not an M2 operational-acceptance claim. It demonstrates Party-canonical Matter creation, exact issued-revision acceptance, idempotent replay, a PostgreSQL row-lock serialization point, database uniqueness backstops, tenant/RBAC boundaries, and a frontend flow. It does not itself establish supported-native-Electron evidence, named operational participants, confirmed capacity, a current isolated full-suite result, or a release/M2 acceptance decision.

**Implementation-readiness recommendation: Conditional / not yet executable as an M2 delivery claim.** The smallest next executable task is a narrowly authorized **existing-conversion evidence and operational-verification package**, not a second conversion implementation. It may execute only after an owner commissions it and the STOP conditions in section 10 are satisfied. It must verify the existing contract against an isolated PostgreSQL target and supported native Electron host, close or explicitly accept the identified evidence gaps, and must not add new conversion behavior by default.

## 2. Governance and prerequisite verification

| Check | Result | Evidence |
| --- | --- | --- |
| Protected baseline | Verified | `origin/main` and `HEAD` began at `725e6395b741ee06677468ff4ddacd599ec6f32d`, merge PR #360. |
| Authorization ancestry | Verified | `a08572f216ae261a759a1f61536e011c0abea679` (PR #360’s authorization-side parent) is an ancestor of this candidate branch. |
| T173 predecessor | Verified Done | `IMPLEMENTATION_QUEUE.md` T173 row and `docs/closeout/T173_Governance_Closeout.md`; T174 has only T173 as finish-to-start predecessor. |
| Governance frontier | Verified | T174 is `Authorized`, not Done; `latestTaskDone=T173`, `latestTaskAuthorized=T174`, transitions empty. |
| Required ADR frontier | Verified | `python scripts/governance_validate.py --report` reports unresolved `[12, 15, 16, 17, 20]`. |
| Historic/forecast preservation | Preserved | No edit to T167 cancellation provenance, calendar actuals/history, or M1/M2/M3/finalization forecasts. |

`python scripts/governance_validate.py --report` completed without governance errors. It is a consistency check, not evidence of runtime conversion behavior or operational readiness.

## 3. Evidence traceability matrix

| Surface | Existing state | Source / symbol | Assessment relevance |
| --- | --- | --- | --- |
| Enquiry, Quotation, revision, Acceptance schema | Implemented | `backend/src/app/infrastructure/persistence/models/enquiry.py`: `Enquiry`, `Quotation`, `QuotationRevision`, `Acceptance` | Direct tenant keys, composite hierarchy FKs, acceptance uniqueness and idempotency-key uniqueness are present. |
| Enquiry/quotation migration and RLS | Implemented | `backend/alembic/versions/e148c0f5a8b2_enquiry_quotation_acceptance_foundation.py` | Creates tables, FORCE RLS/default-deny policies, evidence-immutability and party-required acceptance triggers, and narrow permissions. |
| One-time issuance | Implemented | `backend/alembic/versions/8d77007b9d7f_permit_quotation_revision_issuance.py`; `EnquiryService.issue` | An issued revision is eligible; issuance is a paired, one-time transition. |
| Conversion application operation | Implemented | `backend/src/app/application/acceptance_service.py`: `AcceptanceService.accept` | Locks enquiry, checks prior conversion/replay, requires Party and issued revision, creates Matter then immutable Acceptance. |
| Persistence serialization | Implemented | `backend/src/app/infrastructure/persistence/sqlalchemy_enquiry_repository.py`: `lock_enquiry`, `acceptance_for_enquiry`, `add_acceptance` | `SELECT … FOR UPDATE` on same-tenant Enquiry serializes competing conversions. |
| Matter creation / Party linkage | Implemented | `backend/src/app/application/matter_service.py`: `create_in_organization`; `backend/src/app/infrastructure/persistence/models/matter.py`; `party.py`: `MatterParty` | New Matter uses `client_id=None`; the Enquiry Party becomes `MatterParty(role="client")`. No Client or File is created. |
| Matter number boundary | Implemented but constrained | `Matter.matter_number` global `unique=True`; `MatterService._is_matter_number_unique_violation` | Caller supplies existing Matter fields. Global uniqueness is current behavior, not a new numbering decision. |
| HTTP/RBAC boundary | Implemented | `backend/src/app/presentation/api/v1/enquiries.py`: `accept_revision` | Requires both `quotations:accept` and `matters:write`; trusted Organization/actor derive from authenticated user. |
| Transaction owner | Implemented | `backend/src/app/infrastructure/database/session.py`: `get_db` | Repositories/services flush; request dependency owns final commit/rollback and outcome finalization. |
| Frontend API/UI | Implemented | `frontend/src/infrastructure/api/enquiriesApi.ts`: `acceptQuotationRevision`; `frontend/src/presentation/pages/QuotationDetailPage.tsx`: `accept` | UI selects an issued revision, requires Party and Matter fields, uses a stable in-page idempotency key, then opens the resulting Matter. |
| Unit/API/integration tests | Partially evidenced | `backend/tests/unit/test_t148_enquiry_quotation_foundation.py`; `backend/tests/integration/test_t148_enquiry_quotation_postgres.py`; `backend/tests/integration/test_t149_enquiry_quotation_routes.py`; `frontend/src/infrastructure/api/enquiriesApi.test.ts` | Focused evidence exists, including replay, concurrent requests, RBAC, tenant denial and immutability. This assessment does not claim a fresh complete execution result. |
| Native Electron | Unknown | No source-backed supported-host run located in this assessment | Browser/frontend tests cannot replace a native Electron operational scenario. |

## 4. Existing versus proposed conversion behavior matrix

“Proposed” below means a future verification/contract boundary, not a request to change the current implementation.

| Concern | Existing verified behavior | Required future evidence / proposed boundary |
| --- | --- | --- |
| Intake | Party-linked or prospect-only Enquiry permitted; prospect evidence required if no Party. | Keep prospect-only intake distinct from Party identity. Do not infer/auto-create/dedupe Party during conversion. |
| Quote evidence | A non-empty snapshot is revisioned; issuance is one-time. | Prove exact issued revision is accepted and no post-issue mutation is possible on current PostgreSQL. |
| Eligible source state | Party-linked Enquiry + hierarchy-matching issued revision. | Treat absence of Party, missing/mismatched hierarchy, unissued revision and already-converted Enquiry as fail-closed transitions. |
| Conversion output | One Matter and one immutable Acceptance; no Client and no File. | Verify all rows are in tenant and MatterParty uses the Enquiry Party with role `client`. |
| Existing Matter linkage | Not provided by conversion route; it always creates a Matter. | Do not add a “link existing Matter” variant without separately authorized design: it changes exactly-one/provenance/retry semantics. |
| Idempotent retry | Same `(organization, enquiry, key)` and same fingerprint returns existing result, HTTP 200. | Test loss-of-response/uncertain-commit recovery with the same key; key reuse with changed material payload must remain 409. |
| Concurrent requests | Enquiry lock plus uniqueness constraints; focused API test expects one 201 and one 409. | Re-run on isolated PostgreSQL with separate sessions and inspect no orphan Matter is left after losing race/failure. |
| UI | Existing Quotation detail page submits same conversion shape. | Execute supported-native-Electron happy path, Party-missing/permission-denied/conflict/replay messaging, restart and navigation proof. |

## 5. Explicit conversion eligibility contract

### 5.1 Allowed conversion

The currently implemented operation is eligible only when all statements are true:

1. The caller is authenticated, has a resolved trusted Organization, and has both `quotations:accept` and `matters:write`.
2. The Enquiry is visible in that Organization and has a canonical same-Organization `party_id`.
3. The requested Quotation belongs to that Enquiry and Organization; the requested revision belongs to that Quotation and Organization.
4. The exact revision has both `issued_at` and `issued_by`; the implementation does not invent a broader configurable status model.
5. No Acceptance exists for the Enquiry, unless it has the same scoped idempotency key and exact request fingerprint.
6. The request supplies fields required by the existing Matter contract: `matter_number`, type, status, title and `opened_at` (with optional description).

The successful effect is exactly one tenant-owned Acceptance and one Party-canonical Matter. The acceptance records Enquiry, Quotation, exact revision, Matter, actor, timestamp, request fingerprint and idempotency key. The Matter has no legacy Client (`client_id=NULL`), records the Enquiry Party as its client participant, and does not create a File.

### 5.2 Invalid transitions and required response class

| Condition | Contract outcome |
| --- | --- |
| Anonymous / no Organization / missing permission | Authentication or authorization denial; no existence leakage and no mutation. |
| Cross-tenant or hierarchy-mismatched identifier | Non-enumerating not-found behavior; no mutation. |
| Prospect-only Enquiry | Validation failure; caller must explicitly create/select/link a Party through the Party capability first. |
| Revision not issued | Validation failure; no Matter or Acceptance. |
| Same idempotency key, different fingerprint | Conflict; no second conversion. |
| Different key after an Acceptance | Conflict; no second Matter. |
| Duplicate Matter number or other database constraint failure | Fail closed; request transaction rolls back. No partial Acceptance/Matter pair may persist. |
| Commit outcome uncertain / response lost | Client must retry the identical request with the same key and fingerprint; result is either deterministic replay if committed or a single safe retry attempt if no record exists. Do not issue a new key merely because the client did not receive a response. |

### 5.3 Contract alternatives and recommendation

| Alternative | Assessment |
| --- | --- |
| Create a Party automatically for prospect-only intake | Rejected: violates Party reuse/explicit identity resolution and would introduce duplicate matching rules. |
| Link to an existing Matter during acceptance | Deferred: it needs an explicit provenance/cardinality/idempotency design and could undermine the one-Enquiry/one-result invariant. |
| Allow any revision/status flag | Rejected: exact issued evidence is the narrow existing eligibility rule; broader vocabulary crosses Required ADR #15. |
| Application pre-checks only | Rejected: concurrency-safe integrity requires database unique constraints and a serialization point. |
| Existing bounded contract (recommended validation target) | Preserves ADR-0043 intent and current source behavior without a new architectural decision. |

## 6. Matter, Party, tenant, transaction and recovery assessment

### Matter and Party boundary

The supported current path is **new Matter only**. `AcceptanceService.accept` delegates to `MatterService.create_in_organization`, which validates the existing Matter type/status and Party in the same Organization. `MatterService` creates the Matter with no legacy Client and persists a single `MatterParty(role="client")`. This is consistent with ADR-0023/ADR-0039 Party-canonical direction and ADR-0030’s independent-Matter/no-File boundary.

Party reuse is explicit. The Enquiry service can link an existing Party only after same-Organization lookup; it does not fuzzy-match prospective contact data. A future task must retain that separation. The current `matter_number` is globally unique and user-supplied; it is a current persistence contract, not proof that Required ADR #16 is resolved or that a new numbering policy can be introduced.

### Tenant boundaries and database invariants

All four pre-engagement tables directly carry `organization_id`; composite FKs enforce same-Organization hierarchy and the Acceptance table provides unique `(organization_id, enquiry_id)`, `(organization_id, matter_id)`, `(organization_id, quotation_revision_id)` and scoped idempotency-key constraints. The migration creates RLS/FORCE RLS and the runtime uses the restricted application role and trusted Organization context. This is defense in depth; application hierarchy checks and RBAC remain mandatory.

### Transaction, rollback and uncertain outcome

`get_db` is the single request transaction owner; repositories and application services only flush. The Matter aggregate is protected by a nested transaction in `SqlAlchemyMatterRepository.add_with_participants`; the outer request dependency commits or rolls back the whole conversion. The conversion service locks the Enquiry before looking for an existing Acceptance, so competing requests serialize. Constraints remain the final backstop against a process-level race or an implementation regression.

The request dependency explicitly models `CONFIRMED_COMMIT`, `DEFINITIVE_NON_COMMIT` and `COMMIT_OUTCOME_UNCERTAIN`. Therefore a caller must treat a timeout, disconnect, or outcome-uncertain response as unresolved, not as permission to generate another key. Recovery is a repeat of the same request/key/fingerprint followed by deterministic replay or one committed conversion. A future verification task must fault-inject post-handler/commit/response-send failure paths because source inspection alone cannot prove the actual ASGI ordering or client-visible outcome.

## 7. Architectural gate dispositions

| Gate | Disposition for validation of the existing bounded path | Source-backed reasoning / STOP boundary |
| --- | --- | --- |
| ADR-0043 (Proposed) | **Applicable constraint; not accepted** | It specifies the exact Party, acceptance, idempotency and one-Matter direction that existing T148/T152 source substantially reflects. Its Proposed status means it cannot be promoted or cited as accepted authority. Any requested behavior beyond evidence verification needs an authorized ADR disposition. |
| ADR-0047 (Proposed) | **Operational environment gate** | It names `b155caa6d4e1` as current compatible frontier and requires operational-fresh compatibility. No Party write/conversion verification may claim eligibility without a supported classification/environment result. No status promotion here. |
| Required ADR #12 (Workflow vs Government Status) | **Avoided by current scope** | Current conversion uses issued evidence only and does not wire workflow or government process state. STOP if a task adds either lifecycle. |
| Required ADR #15 (Core vs configurable vocabulary) | **Avoided only while bounded** | No new conversion/status/configuration vocabulary may be added. STOP for configurable acceptance/rejection/status taxonomy. |
| Required ADR #16 (UUID vs human identifiers) | **Constraint / unresolved** | Existing UUID keys and current Matter number are reused. STOP for Enquiry/Quotation/Acceptance numbering or changes to Matter-number semantics. |
| Required ADR #17 (soft deletion/history) | **Avoided by immutable evidence boundary** | Current revisions/acceptances are immutable; no delete/archive/purge/reversal policy is assessed. STOP for correction, cancellation, deletion, retention or reversal features. |
| Required ADR #20 (migration strategy) | **Avoided only for operational-fresh existing path** | No legacy Client cutover/backfill/compatibility claim is permitted. STOP for migrated/legacy installations, `clients` retirement, or a schema migration. |
| ADR-0020 / ADR-0042 | **Required composition constraints** | Preserve request-owned one-commit lifecycle and outcome/compensation boundaries. STOP for external side effects, background dispatch or transaction-owner changes. |
| ADR-0021 / ADR-0022 | **Required constraints** | Trusted tenant context, RLS and narrow RBAC are required on every verification scenario. |
| ADR-0023 / ADR-0030 / ADR-0039 | **Required constraints** | Party remains canonical; new Matter does not fabricate Client or File. STOP for Client conversion, File creation or legacy relationship changes. |

## 8. Verification obligations for a future authorized evidence task

| Layer | Mandatory scenarios |
| --- | --- |
| Unit | Fingerprint determinism; all eligibility guards; same-key/different-payload conflict; different-key/already-converted conflict; Matter-number integrity translation; no Party manufacture. |
| PostgreSQL integration | Fresh isolated database at supported head; RLS/FORCE RLS; composite hierarchy-FK violations; trigger immutability; Party-required trigger; uniqueness; two real connections attempting conversion concurrently; rollback after Matter failure; one resulting Matter/Acceptance only. |
| Tenant isolation | Cross-tenant Enquiry, Quotation, revision, Party and Matter identifiers must be non-enumerating and create no rows. Confirm GUC is request-scoped and pool reuse cannot leak tenant context. |
| RBAC | Deny each missing `quotations:accept`/`matters:write` combination; prove the allowed pair is necessary, not merely one broad permission. |
| Retry / uncertain outcome | Simulate client timeout/disconnect and commit/response-send boundary failure; retry exact same key and fingerprint. Record whether committed state is replayed and no duplicate Matter exists. |
| API / regression | Exact hierarchy, unissued revision, Party-missing, duplicate number, malformed key, request validation and existing enquiry/Matter regressions. |
| Frontend | Form validation; Party-missing visibility; issued revision choice; 201 navigation; 200 replay navigation; 403/404/409/422 rendering; key stability across in-page retry. |
| Native Electron | Supported host and named operator execute a fresh install/operational-fresh scenario, conversion, restart, Matter navigation and denied/replay paths. Headless/browser evidence is supplementary only. |

## 9. Capacity, dependencies, estimates and evidence owners

All availability and effort values remain **Unknown**. Historical commits, calendar lanes, or existing code do not constitute staffing, environment, reviewer, operator or schedule commitments.

| Need | Evidence owner | Availability / estimate | Dependency / proof needed |
| --- | --- | --- | --- |
| Architecture gate confirmation | Software Architect | **Unknown** | Scope remains within section 7; explicit ADR disposition if it expands. |
| Backend/integration execution | Assigned backend executor | **Unknown** | Isolated PostgreSQL environment and current operational-fresh compatibility. |
| Frontend/Electron execution | Assigned frontend/desktop executor | **Unknown** | Supported host and operator, not a browser-only substitute. |
| Independent QA | QA Reviewer, different executor where practical | **Unknown** | Comprehensive / Risk Tier 1 exact-head review. |
| Documentation/governance | Documentation Manager / PR manager | **Unknown** | QA publication and separate closeout only after PR 2 merge. |
| Review/protection | Collaborator / GitHub controls | **Unknown** | Required review, CI and protected merge state. |
| Operational participants | Project Owner / operational coordinator | **Unknown** | Named scenario participant and acceptance boundary. |

The reproducible effort model remains qualitative: `architecture + backend + frontend + PostgreSQL/integration + native-host verification + independent QA/rework + governance/CI + contingency`. Every term is **Unknown**, so this assessment makes no duration, critical-path, slack, staffing, or forecast claim.

## 10. Smallest next executable task recommendation (not authorization)

**Candidate objective:** independently verify and document the already implemented M2-V3 bounded conversion contract on a current isolated PostgreSQL database and supported native Electron host, with no behavior expansion.

**Acceptance criteria:**

1. A source/diff review proves the candidate changes no application behavior, migration, schema, vocabulary, identifier policy, legacy cutover or ADR status unless separately authorized.
2. Isolated PostgreSQL evidence proves the contract in sections 5 and 6, including two-session concurrency, database constraints/RLS, rollback, and same-key recovery.
3. Tenant and RBAC negative tests cover the exact API hierarchy and both required permissions.
4. Supported native Electron evidence covers create/link Party, issue exact revision, accept to Matter, replay/duplicate handling, restart and navigation; operator/host identity and limitations are recorded.
5. Commit/response-outcome uncertainty is tested or explicitly evidenced as unavailable; if unavailable, operational acceptance is STOPPED rather than inferred.
6. Capacity, environment and participant records are confirmed or retained as **Unknown**; no numeric forecast is produced from missing evidence.
7. Independent Comprehensive / Risk Tier 1 QA reviews the exact remote candidate head before protected merge.

**Exclusions:** no new endpoint, schema/migration, new identifier or vocabulary, existing-Matter linkage, Party auto-creation/deduplication, legacy cutover, external side effect, release certification, M2 acceptance, forecast revision, successor authorization, or T174 Done marker.

**STOP conditions:** stop and return to Project Owner/Control Tower before implementation if (a) the work needs an existing-Matter path, a new status/identifier/history policy, legacy/migrated-installation behavior, Party matching/creation, File creation, or external side effect; (b) ADR-0043/0047 must be accepted or altered; (c) operational-fresh compatibility, isolated PostgreSQL, supported native Electron host/operator, or independent QA is unavailable; (d) a test exposes duplicate conversion, cross-tenant access, incomplete rollback, or ambiguous retry semantics; or (e) the candidate would change forecasts, capacity allocations, task/ADR state, or historical governance evidence.

## 11. Architect self-assessment and QA handoff

- [x] Protected main, authorization ancestry, T173 prerequisite and governance frontier independently checked.
- [x] Actual models, migrations, services, APIs, repositories, frontend and tests inventoried with source references.
- [x] Existing/proposed matrix, explicit eligibility contract, alternatives, gate matrix, test matrix and capacity matrix supplied.
- [x] Existing implementation evidence distinguished from unproven operational/capacity evidence.
- [x] Required ADRs remain unresolved; ADR-0043/ADR-0047 remain Proposed; no ADR status changes made.
- [x] Provisional forecasts and historical governance evidence preserved.
- [x] No product, schema, migration, frontend, Electron, calendar or task-state change introduced.
- [x] Ready for Independent QA as a documentation-only architecture assessment.

## QA Decision

□ Approved
□ Approved with comments
□ Rework required

The Software Architect does not render this decision, perform Independent QA, merge this candidate, create PR 3, or authorize a successor.
