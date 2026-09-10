# T121 QA Review

**Task:** T121 -- Fresh-Installation Party Enablement Boundary
**Role:** QA Reviewer, per `docs/prompts/QAReviewer.md`
**Artifacts under review:** PR #211 (Architecture only)

## 1. Verified Baseline and Authorization Ancestry
- Evaluated against base `3e18cb36016e9bfebcef231e1ecc0047aa42db32`.
- Reviewed exact PR HEAD `00751de8ab1cd76514515bc910d67ba177f37934`.
- Confirmed authorization commit `1ab4137e4204d017e106fc4a8e393b0408f1e82d` is a genuine ancestor.

## 2. Independent Governance Checks
- `PROJECT_STATE.json` correctly declares `latestTaskAuthorized = T121` and `latestTaskDone = T120`.
- Required ADR #20 remains unresolved globally.
- T122+ remains unauthorized.
- `ADR/0033`, `ADR/0034`, and `ADR/0035` remain structurally unchanged.

## 3. Scope and Implementation Validation
- Verified changed files: `ADR/0036-fresh-installation-party-enablement-boundary.md` and `docs/reviews/T121_Software_Architect_Report.md`.
- No implementation, migration, RLS, test, permission, runtime role, or unrelated governance changes are present. The PR is strictly scoped to architecture documentation as authorized.

## 4. Mandatory Decision Checks

1. **Fresh-installation classification:** Meets requirements. It relies entirely on a mechanical zero-row set (covering all 12 migration-relevant tables and beyond) and objectively precludes "operator label" bypass. Ambiguity explicitly fails closed to legacy.
2. **Disposable development/test reset semantics:** Clearly distinguishes disposable origin from fresh state. Moving disposable test data to "fresh" classification explicitly requires a governed destruction/reset or deletion of all business rows. 
3. **Vacuous migration-window rule:** ADR-0035's prohibition is explicitly declared vacuous *only* upon fulfilling the mechanical zero-row verification. The default resolves to legacy/blocked, which securely protects the T108-T120 requirements.
4. **ADR-0035 interaction:** Correctly scoped. The enablement qualifies only the vacuous migration/reconciliation framing. Section 6's final Address tenant constraints remain unqualified prerequisites on all paths.
5. **Address prerequisites:** Safely incorporated. Enforces `addresses.organization_id` `NOT NULL`, same-Organization integrity, tenant-scoped creation, and Address RLS *before* ordinary Party writes.
6. **Party tenant isolation:** Reaffirms ADR-0021. Demands mandatory Party Organization ownership, application-layer scoping, default-deny Party RLS, and writes performed solely under the non-owning `legal_dms_app` runtime role prior to API exposure.
7. **Authorization boundary:** Reaffirms ADR-0022. Demands explicit Party permission codes, grants, and route-level `RequirePermission` gating before normal exposure. No authorization model redesign was introduced.
8. **Normal-write gate:** Provides a robust five-condition gate that must be objectively satisfied prior to exposing ordinary Party writes. Unmet conditions definitively block Party creation.
9. **Required ADR #20 boundary:** Precise. It meticulously separates fresh-install enablement from global legacy cutover, explicitly confirming cutover, retirement, and bridging removal remain governed by Required ADR #20.
10. **Coexistence with T108-T120:** Safe. It strictly affirms that fresh installations do not invalidate reconciliation artifacts, T118 executor mechanics, or compatibility bridges. It explicitly bans synthesizing fake migration evidence.

## 5. Implementation-readiness
- The "Future Impact" section outlines a logical, implementable sequential progression for future tasks: 
    1. Address/Party RLS + authorization prerequisites.
    2. Fresh-installation verification gate.
    3. Legacy migration completion.
    4. Cutover (ADR #20).
- This yields a clear scaffold for future implementation slices without illegitimately bleeding into T122+.

## 6. Verification Tools and Artifacts
- Ran `governance_validate.py` locally: 0 warnings, 0 errors.
- Exact-head CI run: Backend, Frontend, and Governance checks are all cleanly passing.
- `git diff --check` reported no whitespace or formatting errors.

## 7. QA Decision

**Decision: Approved**
