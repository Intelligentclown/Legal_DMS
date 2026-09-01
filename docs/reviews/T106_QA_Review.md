# T106 Independent QA Review

**Task:** T106 -- ADR-0033 Governance / Architecture Lifecycle: Party/Client Migration and
Organization-Boundary Reconciliation.

**Role:** Independent QA Reviewer.

**PR reviewed:** #177 -- ADR-0033 Party/Client migration architecture.

**Remote head reviewed before this QA record:**
`b57f9caee168bb1e50b0f0add8485cb2f478bf85`.

## Authorization Ancestry

The authorization merge commit
`e6bcfef4f9a54c5328b5567460dbbdb280a5cfc2` is an ancestor of the reviewed remote
head. This was independently confirmed with `git merge-base --is-ancestor`.

The authorization-to-reviewed-head diff contains exactly:

- `ADR/0033-party-client-migration-organization-boundary.md`
- `docs/reviews/T106_Software_Architect_Report.md`

No implementation, schema, migration, frontend, backend, test, or unrelated governance artifact is
present in that range. ADR-0033 remains `Proposed`; `latestTaskDone` remains `T105`; there is no
unauthorized `inProgressTransitions` declaration, T107, or Party implementation task.

## Files Reviewed

- `ADR/0033-party-client-migration-organization-boundary.md`
- `docs/reviews/T106_Software_Architect_Report.md`
- `IMPLEMENTATION_QUEUE.md` (T106 authorization)
- `PROJECT_STATE.json`
- `PROJECT_WORKFLOW.md`, `AI_BOOTSTRAP.md`, `docs/prompts/QAReviewer.md`, and
  `docs/ImplementationLog/README.md`
- ADRs `0021`, `0023`, `0024`, `0028`, `0030`, `0031`, and `0032`
- Current persistence models for Client, Matter, Property, Scheduling, and Finance; model
  registration; relevant Alembic history; permission seeds/grants; model tests; and current ERD/
  database documentation.

## Findings

### Blocking findings

1. **Address is omitted from the direct tenant-boundary design.** ADR-0033 copies
   `clients.address_id` unchanged to Party (section 5.1), but its inventory, final tenant-boundary
   table, and implementation constraints omit `addresses`. The live `Address` table holds concrete
   address data and is referenced by both Client/Party and Property. It has no `organization_id`.
   Therefore, treating it as accessible only through a Party or Property join would make that join
   the sole tenant boundary for a table containing tenant data, contrary to ADR-0021's requirement
   for directly carried tenant ownership, mandatory scoped access, and forced default-deny RLS.

   Required rework: ADR-0033 must explicitly classify `addresses` and resolve its tenant treatment.
   If it remains tenant-scoped, add it to the dependency inventory, reconciliation/backfill plan,
   final-state table, and implementation constraints with direct `organization_id`, Organization FK,
   scoped access, and RLS. If it is intended to be globally reusable reference data, the ADR must
   establish a safe, non-join-based boundary and explain why its stored address fields are not
   tenant-scoped. The existing "copy unchanged" treatment leaves an unsafe gap.

### Non-blocking comments

None.

## Verification Notes

- The Client inventory is otherwise accurate: current direct FKs are `client_contacts`, `matters`,
  `property_owners`, `appointments`, `invoices`, and `payments`; the Client and proposed Party IDs
  are UUID/`uuid4`; and the identity-preservation preflight, ledger, collision failure, and retry
  rules are fail-closed.
- The proposed Matter migration correctly uses `matter_parties` rather than a long-lived
  `matters.party_id`, and its reconciliation, compatibility, contact-retention, scope, and
  no-heuristic requirements align with the accepted ADR constraints.
- Repository searches corroborated the absence of Charges, Expenses, Client repositories/services/
  routes/request-response schemas, production Client factories, and Client-record seed data.
- `python scripts/governance_validate.py` passed with 0 warnings and 0 errors; `git diff --check`
  passed. The governance-validator unit test command could not run because the root Python runtime
  has no `pytest` module. This is disclosed, not treated as a passing test.

## Reviewer Checklist

```text
Reviewer Checklist

□ Architecture preserved
□ Existing design patterns followed
□ Tests added
□ Existing tests pass
□ Documentation updated
☑ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
□ Ready for QA
```

The unchecked architecture, pattern, documentation, and readiness items reflect the blocking tenant
boundary omission above. Tests are not applicable to this architecture-only change; the attempted
governance-validator unit suite is unavailable in the root interpreter.

## QA Decision

```text
□ Approved
□ Approved with comments
☑ Rework required
```

ADR-0033 requires Software Architect rework before QA can clear PR #177. This record does not merge
the PR, perform Governance Closeout, authorize implementation, or create a follow-up task.
