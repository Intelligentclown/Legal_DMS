# T121 Software Architect Report

**Task:** T121 -- Fresh-Installation Party Enablement Boundary.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`.

**Artifact under review:** `ADR/0036-fresh-installation-party-enablement-boundary.md`.

**Status:** Initial architecture draft for PR 2 of T121's Required-ADR three-PR lifecycle. This
report does not perform independent QA, merge, governance closeout, or implementation.

## 1. Verified Baseline and Authorization Ancestry

- Fresh `git fetch origin` completed before any work.
- `origin/main` was verified at `3e18cb36016e9bfebcef231e1ecc0047aa42db32`, exactly the expected
  merge commit for PR #210, `docs(governance): authorize T121 fresh-install Party boundary`
  (merged 2026-09-10, mergedAt `2026-09-10T04:23:58Z`, confirmed via `gh pr view 210`).
- `git show` on `3e18cb36016e9bfebcef231e1ecc0047aa42db32` confirmed it is the merge of PR #210
  with parents `4cfb0c5b4d6a11617642439167e55027d2d70ce1` (main) and
  `1ab4137e4204d017e106fc4a8e393b0408f1e82d` (the T121 authorization commit), and that the
  authorization commit `1ab4137e4204d017e106fc4a8e393b0408f1e82d` is a direct parent of the merge.
- The authorizing T121 row in `IMPLEMENTATION_QUEUE.md` was re-read directly. It records the
  project-owner authorization (2026-09-10), the Required-ADR `PROJECT_WORKFLOW.md` section 3.1
  lifecycle, the exact authorized scope (fresh-installation/nothing-to-migrate definition;
  disposable dev/test vs. genuine empty; when the ADR-0035 migration-window prohibition is vacuous;
  coexistence with legacy Client->Party migration; exact ADR-0035 clauses superseded/qualified/
  unchanged; prerequisites for ordinary Party creation/application visibility), the mandatory
  preserved invariants (Organization ownership, same-Organization integrity, Address tenant
  finalization before normal Party writes, application-layer Organization scoping, forced
  default-deny RLS, non-owning runtime role, Party permission codes before API exposure, and what
  Required ADR #20 still blocks), and the stopping boundary (authorization only; a later separate
  Architect + independent-QA PR creates the next valid ADR; no merge, QA, Done marker, or T122+
  work by this pass).
- The authoring branch was created directly from `origin/main` (`3e18cb36`), so the authorization
  commit is in ancestry by construction.
- Governance state rechecked from repository artifacts before drafting:
  - `latestTaskAuthorized = T121`
  - `latestTaskDone = T120`
  - `inProgressTransitions = []`
  - Required ADR #20 remains unresolved globally (`unresolvedRequiredADRs` includes 20)
  - T121 exists and is authorized, but is not Done
  - T122+ remains unauthorized
- Remote-branch inspection found the T121 authorization branch
  (`origin/docs/t121-authorization-fresh-install-party-boundary`) was merged and deleted upstream;
  no T121 Architecture branch existed before this branch was created. Existing remote architecture
  branches (`origin/docs/t114-party-persistence-schema-architecture`,
  `origin/docs/t112-adr-0034-execution-ledger-architecture`) confirm the
  `docs/tNNN-<topic>-architecture` convention used here.
- ADR numbering rechecked from repository contents. `ADR/0035` was the highest existing ADR on
  `origin/main` and no `ADR/0036-*` file exists in `ADR/`, so this task correctly uses `ADR/0036`.
  The task's own instruction to "verify its number then" was satisfied by this direct directory
  listing plus `git ls-tree origin/main ADR`.

## 2. Sources Inspected

Read directly during this bounded architecture pass:

- `AI_BOOTSTRAP.md`
- `docs/AI_EXECUTION_ROUTING.md`
- `CONTEXT.md`
- `PROJECT_WORKFLOW.md` (including the Required-ADR/Governance-Hardening three-PR lifecycle,
  section 3.1)
- `PROJECT_STATE.json` (governanceLedger: quoted values)
- `IMPLEMENTATION_QUEUE.md` (the T121 row; context rows T117-T120)
- `docs/prompts/SoftwareArchitect.md`
- `docs/GOVERNANCE_VALIDATION.md` (validation obligations)
- `ADR/template.md`
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `ADR/0033-party-client-migration-organization-boundary.md`
- `ADR/0034-party-client-migration-persistence-and-execution-ledger.md`
- `ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md` (the primary
  artifact this ADR qualifies/supersedes in its fresh-installation clauses)
- `docs/reviews/T114_Software_Architect_Report.md` (standing Software Architect report format)
- `docs/PartyClientReconciliationContract.md` (referenced for the T109 basis; not modified)
- `backend/src/app/presentation/api/v1/router.py` and the `v1/` route directory (auth, health,
  users, version only -- no `parties` routes, confirmed)
- `backend/src/app/infrastructure/persistence/models/party.py` (current `parties` schema, including
  `organization_id NOT NULL` and the composite same-Organization ForeignKeyConstraint)
- `backend/src/app/infrastructure/persistence/models/client.py` (current `clients`/`addresses`
  schema with staged nullable `organization_id`; the composite
  `fk_clients_organization_id_addresses`)
- Alembic revisions:
  - `d8f4a6c9b3e1_tenant_supporting_address_foundation.py` (T115: staged nullable
    `organization_id` across downstream tables)
  - `e6a2d4c8f1b7_party_matterparty_ledger_foundation.py` (T116: `parties`/`matter_parties`/
    `client_party_migration_ledger`)
  - `b7e8a4f2c6d0_party_compatibility_bridge_foundation.py` (T117: nullable `party_id` bridges)
  - `f3b7c9d1e2a4_client_tenant_staging_integrity.py` (T120: nullable `clients.organization_id` and
    same-Organization guarding FKs)
  - `7192e84e9a2f_organization_tenant_isolation_rls.py` (T105: RLS enabled/forced on exactly
    `organizations` and `users`; `legal_dms_app` non-owning role grants, asymmetric)
- `backend/alembic/versions/224b650e5235_seed_role_permissions.py` (eighteen seeded permission
  codes; no `parties` resource codes yet, confirmed)
- `scripts/governance_validate.py` (full read; resolved-ADR parsing and ledger checks)
- `scripts/tests/test_governance_validate.py` (51 tests present)
- `git log --oneline -10` and `git show --stat` for the T120 merge (`4cfb0c5`, PR #209) to confirm
  the entity surface this ADR rests on

## 3. Current Repository State Verified

Freshly verified directly, not assumed, on the authoring baseline:

- `parties` exists with `organization_id NOT NULL` and the composite same-Organization
  `(organization_id, address_id)` -> `addresses (organization_id, id)` reference; no Party
  permission codes, `parties` routes, or ordinary Party write path exist anywhere.
- `client_party_migration_ledger` and `matter_parties` exist (T116); the five `party_id` bridge
  columns exist and are nullable (`property_owners`, `appointments`, `invoices`, `payments`,
  retained `client_contacts`) (T117).
- `addresses.organization_id`, `clients.organization_id`, and the downstream staged
  `organization_id` columns remain nullable (T115/T120) -- exactly the staging state `ADR/0035`
  section 6 fixes as a prerequisite.
- Row-Level Security is enabled and forced on exactly `organizations` and `users`; the
  `legal_dms_app` runtime role is non-owning in the sense `ADR/0021` requires (grants asymmetric;
  `organizations` SELECT only); no RLS policy exists on `parties` or `addresses`.
- The route surface is only `auth`, `health`, `users`, `version`; no Party/Client/Matter/Property
  business routes exist.
- The eighteen seeded permission codes are `matters:read/write/delete`, `clients:read/write/delete`,
  `properties:read/write/delete`, `documents:read/write/delete`, `financial:read/write`,
  `users:manage`, `roles:manage`, `settings:manage`, `reports:read`; no `parties:*` codes -- the
  exact gap `ADR/0036` Decision 6 fixes as a prerequisite.

All of the above confirms the T121 authorized scope has no implementation to reconcile against:
this is a decision-only boundary sitting on finished T115-T120 schema foundations.

## 4. Architecture Decisions Frozen by ADR-0036

`ADR/0036` freezes the following decision set:

- objective installation classification (Decision 1): genuinely fresh/empty (zero rows across the
  full migration-relevant/business set + never real customer data, verified mechanically), disposable
  dev/test-only (fresh only after governed disposal/reset), legacy-with-business-data (default;
  any ambiguity resolves to legacy), and migrated (T118-ledger-complete; legacy finalization still
  owed); no operator-declared reclassification;
- vacuous migration-window condition (Decision 2): `ADR/0035` sections 4 and 5 migration-window
  prohibitions are vacuous on, and only on, a genuinely fresh/empty installation, determined
  exclusively by the mechanical zero-row condition; never by operator assertion;
- fresh vs. legacy path split and switching (Decision 3): fresh path uses the same schema/ledger/
  RBAC surface, gains ordinary Party creation only behind the gate; legacy path untouched;
  a fresh install acquiring legacy-shaped data switches to legacy, fail closed;
- Address tenant finalization (Decision 4): `ADR/0035` section 6 fully applicable on the fresh
  path -- `NOT NULL`, same-Organization integrity, Address RLS active, tenant-owned creation; the
  only qualified clause is the reconciliation-stage framing (no reconciliation stage exists on a
  fresh path); no tenant-safety waiver either path;
- `ADR/0021` Party tenant-security prerequisites (Decision 5): mandatory app-layer Organization
  scoping, forced default-deny RLS on `parties` effective under the non-owning runtime role,
  runtime writes under the non-owning role, in the fixed order RLS/role/scoping then permission-
  then-API;
- `ADR/0022` authorization prerequisite (Decision 6): no redesign -- `parties` codes seeded and
  granted into the existing resource:action RBAC, `RequirePermission`-gated before any ordinary
  Party API exposure, on both paths;
- objective failure-closed enablement gate (Decision 7): five verifiable conditions; no "migration
  complete enough" criterion; unmet/unverifiable -> writes stay disabled;
- Required ADR #20 boundary (Decision 8): cutover, `client_id`/`clients` retirement, bridge
  removal, legacy staged-column final `NOT NULL` enforcement, legacy completion gate remain
  blocked; this ADR resolves none of it;
- coexistence and future compatibility (Decision 9): fresh path never invalidates, forks, or
  shadows T108-T120 tooling/ledger/surface; migration-era schema stays present and dormant, nothing
  retired; `matter_parties` keeps its `ADR/0035` section 11 ordinary role.

## 5. Exact ADR-0035 Clause Disposition

`ADR/0036` states, clause by clause, what `ADR/0035` keeps fully applicable versus what it
qualifies for fresh installations (the task required this explicitly; `ADR/0035`'s status is
**unchanged** -- still Proposed -- and this list is a disclosure, not a rewrite):

- Fully applicable everywhere (no change): section 1 discriminator vocabulary; section 2 Party
  table contract; section 3 subtype invariants; section 7 audit/version/deletion contract;
  section 8 execution-ledger schema; section 9 atomic migration unit; section 10 legacy bridge
  classifications (their final nullability stays legacy-path finalization under Required ADR #20);
  section 11 MatterParty bounded contract. None of these are qualified by `ADR/0036`.
- Qualified only in its reconciliation-stage framing, still substantively applicable on the fresh
  path: section 6 Address tenancy -- the final `NOT NULL`, same-Organization, and RLS conditions
  are prerequisites on the fresh path exactly as on the legacy path; only "nullable during the
  reconciliation/backfill stage" has no object on a fresh path (there is no such stage).
- Vacuous only under the mechanical zero-row classification, otherwise fully applicable
  (Decision 2): section 4 coexistence safety conditions and section 5 "ordinary Party creation
  must remain unavailable during the governed migration window" / "migration-time writes are the
  only allowed Party writes until governed backfill is complete." These are qualified only to the
  extent the migration window has no object on a genuinely fresh/empty installation.

No `ADR/0033`/`ADR/0034` clause is modified, reopened, or superseded. `ADR/0021` and `ADR/0022`
are referenced as prerequisites and are not modified.

## 6. Alternatives Considered

Per `ADR/0036`'s own "Options Considered": (1) keep ordinary Party creation disabled everywhere
until legacy migration fully closes -- rejected, permanently blocks a genuinely empty installation
from normal business; (2) trust the operator's stated classification -- rejected, assertion is not
proof and reproduces the failure class `ADR/0021` documented for `T79`; (3) mechanically classified
fresh path with identical install-agnostic prerequisites (adopted) -- fail-closed by construction
and legacy-neutral.

## 7. Explicitly Deferred / Not Resolved

Still outside T121 and deliberately left unresolved:

- any implementation of the gate, RLS, permission codes, route gating, or ordinary Party writes;
- the mechanical zero-row verification tooling (a later implementation slice);
- Address/Party schema changes, `NOT NULL` finalization, or RLS DDL;
- the legacy-path completion/cutover determinations already governed by T108-T120 and `ADR/0033`/
  `ADR/0034`/`ADR/0035`;
- `client_id`/`clients` retirement, bridge removal, application cutover;
- Required ADR #20's remaining scope (stated in full in `ADR/0036` Decision 8 and Future Impact).

Required ADR #20 therefore remains unresolved globally after this ADR.

## 8. Recommended Future Dependency Sequence

`ADR/0036`'s Future Impact section fixes the smallest safe order without assigning task numbers:
(1) install-agnostic prerequisites on both paths -- Address finalization + Address RLS, then Party
RLS effective under the non-owning runtime role + app-layer scoping, then Party permission codes +
route gating; (2) fresh-installation enablement -- mechanical classification/vacuity verification
wired as the Decision 7 gate, then ordinary Party creation behind it; (3) legacy migration
completion -- unchanged, governed by T108-T120 and `ADR/0033`/`ADR/0034`/`ADR/0035`; (4) cutover
and retirement -- blocked by Required ADR #20, unsequenced here.

## 9. Exact Files Changed

Exactly two architecture artifacts are added by this T121 Software Architect pass:

- `ADR/0036-fresh-installation-party-enablement-boundary.md`
- `docs/reviews/T121_Software_Architect_Report.md`

No application code, schema implementation, migration script, test, workflow, queue row,
`IMPLEMENTATION_QUEUE.md`, or `PROJECT_STATE.json` change was made.

## 10. Validation

The required validation set for this architecture draft is:

- `python scripts/governance_validate.py`
- `python -m pytest scripts/tests/test_governance_validate.py -q` (51 governance tests)
- `python scripts/governance_validate.py --report` (confirm no Required-ADR resolution state changes)
- `git diff --check`
- final diff inspection confirming no unauthorized implementation/schema/data mutation occurred

This report does not render the independent QA decision.

## 11. Confirmation No Unauthorized Implementation Occurred

This branch does **not** implement:

- Party CRUD/API/services or ordinary Party writes
- RLS policies/DCL or role provisioning on `parties`/`addresses`
- Address or Party schema changes or `NOT NULL` finalization
- Party permission codes/role grants/route gating
- any Alembic migration or data mutation
- bridge removal, `client_id`/`clients` retirement, or cutover
- real/customer migration or T118 executor execution
- QA approval
- merge or governance closeout
- T122 or later authorization

`ADR/0033`, `ADR/0034`, `ADR/0035`, `ADR/0021`, and `ADR/0022` statuses are unchanged (all remain
Proposed); no ADR status was altered. The untracked `backend/.tmp/` directory (local pytest
artifact, permission-denied) was left out of any commit.

## Reviewer Checklist

```text
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added
□ Existing tests pass
☑ Documentation updated
☑ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

`Tests added` and `Existing tests pass` remain correctly unchecked because this is an
architecture-only PR-2 deliverable. `AI_BOOTSTRAP.md` and `PROJECT_STATE.json` are correctly
untouched because no standing process changed and T121 has not reached governance closeout.

## QA Decision

```text
□ Approved
□ Approved with comments
□ Rework required
```

The next required role is the independent QA Reviewer, after this branch is validated, pushed, and
opened as the T121 Architecture+QA PR.