# T109 Software Architect Report

**Task:** T109 — Party/Client Migration Reconciliation Contract & Operator Workflow.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`.

**Artifact under review:** `docs/PartyClientReconciliationContract.md`.

**Status:** Drafted for independent QA. This report does not perform QA, merge, governance closeout,
or implementation.

## 1. Authorization and Baseline

- Fresh `git fetch origin` completed successfully.
- `origin/main` was verified at `22ea5732d48afa1705e6f8451c9c587f6027cc50`, exactly matching the
  expected T109 authorization merge.
- That merge was independently verified as a two-parent merge of
  `c942686a351ad4819550a2e66b2e406dddf68121` and
  `e8baf48ca1e479b78f9341a6c0ea97797755f3df`.
- Authorization ancestry was mechanically verified before drafting:
  `e8baf48ca1e479b78f9341a6c0ea97797755f3df` is an ancestor of this branch through the merged
  authorization now present on `origin/main`.
- The T109 authorization row in `IMPLEMENTATION_QUEUE.md` was read directly and followed exactly:
  architecture/contract only, no persistence implementation, no write-capable migration, no Party
  implementation, no QA decision by this role, and no merge.

## 2. Repository Evidence Inspected

Read directly before drafting:

- `AI_BOOTSTRAP.md`
- `docs/AI_EXECUTION_ROUTING.md`
- `PROJECT_WORKFLOW.md`
- `PROJECT_STATE.json`
- T109's `IMPLEMENTATION_QUEUE.md` row
- `docs/prompts/SoftwareArchitect.md`
- `ADR/template.md`
- `ADR/0032-user-organization-pre-existing-data-reconciliation.md`
- `ADR/0033-party-client-migration-organization-boundary.md`
- `backend/src/app/infrastructure/cli/client_migration_preflight.py`
- `backend/src/app/infrastructure/cli/reconcile_organizations.py`
- `docs/ImplementationLog/README.md`

This was enough to ground the contract in the repository's actual current preflight output,
reconciliation precedent, governance lifecycle, and Software Architect conventions without expanding
into unrelated implementation work.

## 3. Why No New ADR Was Drafted

T109's authorized scope is narrower than a new ADR. ADR-0033 already decides the Party/Client
migration architecture and explicitly requires deterministic or operator-reconciled Organization
assignment before cutover. ADR-0032 already decides the operator-reconciliation precedent for legacy
tenantless data. The missing piece was the exact machine-readable contract and workflow that binds
T108's read-only output to a future write-capable executor.

That gap can be filled by a governed architecture/contract artifact without reopening ADR-0033,
changing ADR-0032, or silently deciding a new durable persistence model. Accordingly, this task
produces a repository contract document plus this report, not a new ADR.

## 4. Contract Decisions Made

`docs/PartyClientReconciliationContract.md` decides:

- the exact JSON artifact envelope that consumes T108 output;
- stable identifiers for each Client-anchor reconciliation set and its affected graph members;
- the allowed states: `deterministic`, `ambiguous`, `unmappable`, `operator_reconciled`, `stale`,
  and `rejected`;
- which states are executable by a later migration tool and which are not;
- the only allowed operator action for unresolved sets: explicit selection of one Organization UUID;
- fail-closed validation for missing, duplicate, conflicting, malformed, stale, or unknown entries;
- required provenance linking every decision back to one T108 report hash, repository commit, graph
  snapshot, actor identity, and timestamp;
- stale-reconciliation protection when the underlying legacy graph changes after T108;
- resumability and idempotency expectations for a future write-capable executor;
- the downstream handoff contract a future migration task must consume.

## 5. Alternatives Considered

1. **Create a new ADR for T109.** Rejected. The task does not need a new architectural decision if
   it stays within ADR-0033/0032 and avoids deciding durable persistence.
2. **Update ADR-0033 directly with the whole contract.** Rejected. That would overload ADR-0033's
   migration architecture with a large operational contract artifact and make later contract
   revisions look like architecture changes.
3. **Define only a prose workflow and leave the machine-readable shape to implementation.**
   Rejected. The task explicitly authorizes and requires the exact contract now, to prevent a later
   implementation from inventing format, validation, and stale-handling rules mid-flight.
4. **Define a file-based governed contract artifact plus a separate report.** Selected. It matches
   the authorized scope, reuses existing ADR authority, and keeps the persistence question open
   rather than silently deciding it.

## 6. Composition Check

- **ADR-0033:** preserved. This contract operationalizes its reconciliation boundary and cutover
  prerequisites; it does not alter its migration sequence, Address treatment, or status.
- **ADR-0032:** preserved. The contract reuses its explicit-operator-input and fail-closed legacy
  reconciliation precedent, but for Client-anchor graph sets rather than pre-Organization Users.
- **ADR-0021/0031:** preserved indirectly through ADR-0033. Organization remains the tenant
  boundary, and the contract requires explicit Organization UUIDs rather than inferred groupings.
- **Required ADR #20 outside the Party/Client slice:** untouched. Matter `property_id` /
  `matter_type_id` retirement, Document `matter_id -> file_id`, and other migration seams remain
  unresolved.

## 7. Architecture Stop Boundary

No stop condition was triggered inside T109's authorized scope. The contract is intentionally
artifact-based and does not require this task to decide a new database table, reconciliation ledger,
or repository-managed durable storage mechanism.

However, one boundary is now explicit for the future: if the eventual write-capable executor cannot
meet auditability, resumability, or replay guarantees using the governed artifact plus its own
existing migration-run outputs, and therefore requires a new durable reconciliation persistence model,
that later task must stop for a separate ADR rather than treat this report as implicit approval.

## 8. Exact Files Changed

Exactly two documentation files were added:

- `docs/PartyClientReconciliationContract.md`
- `docs/reviews/T109_Software_Architect_Report.md`

No ADR status field, implementation code, schema, tests, `IMPLEMENTATION_QUEUE.md`,
`PROJECT_STATE.json`, or governance-closeout document was modified.

## 9. Validation

The branch must pass, and did pass, the repository-standard governance/documentation checks listed
below before handoff:

- `python scripts/governance_validate.py`
- `python scripts/tests/test_governance_validate.py -v`
- `git diff --check`

No application implementation tests were added or run as a substitute for QA, because this task is
architecture/contract only and the user explicitly instructed me not to perform independent QA.

## Reviewer Checklist

```text
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added
□ Existing tests pass
☑ Documentation updated
□ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

`ADR updated` is correctly unchecked because T109 did not require a new ADR once the contract was
kept within ADR-0033/0032's existing authority. `PROJECT_STATE.json` is correctly untouched because
this task has not reached governance closeout.

## QA Decision

```text
□ Approved
□ Approved with comments
□ Rework required
```

Independent QA must review the actual remote PR head. This Software Architect pass stops here, per
T109's authorized boundary.
