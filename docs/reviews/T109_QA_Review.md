# T109 Independent QA Review

**Task:** T109 -- Party/Client Migration Reconciliation Contract & Operator Workflow

**Role:** Independent QA Reviewer

**PR reviewed:** #186

**Remote head reviewed before this QA record:**
`9e1760f858675677007d7fda013fc81709b90eef`
**Base branch reviewed:** `main`

## Authorization Ancestry

The authorization commit `e8baf48ca1e479b78f9341a6c0ea97797755f3df` is an ancestor of the reviewed
remote head `9e1760f858675677007d7fda013fc81709b90eef` through merge
`22ea5732d48afa1705e6f8451c9c587f6027cc50`. This was independently confirmed after a fresh
`git fetch origin --prune`.

## Files Reviewed

- `AI_BOOTSTRAP.md`
- `docs/AI_EXECUTION_ROUTING.md`
- `PROJECT_WORKFLOW.md`
- `PROJECT_STATE.json`
- `IMPLEMENTATION_QUEUE.md` (`T109` row)
- `docs/prompts/QAReviewer.md`
- `ADR/0032-user-organization-pre-existing-data-reconciliation.md`
- `ADR/0033-party-client-migration-organization-boundary.md`
- `backend/src/app/infrastructure/cli/client_migration_preflight.py`
- `backend/src/app/infrastructure/cli/reconcile_organizations.py`
- `backend/src/app/infrastructure/persistence/models/mixins.py`
- `docs/PartyClientReconciliationContract.md`
- `docs/reviews/T109_Software_Architect_Report.md`

## Findings

1. **Blocking -- the contract requires snapshot fields and stale-check inputs that T108 does not
   actually emit.** The contract treats `anchor.fingerprint` as something that must match the T108
   snapshot exactly, requires `snapshot.graph_node_ids` to be reproduced from that snapshot, and
   marks entries stale when graph-member fingerprints or graph membership change
   (`docs/PartyClientReconciliationContract.md`: 64-70, 74-95, 142-149, 205-218, 230-237,
   265-288). The actual T108 output shape does not include any of those fields: `NodeReport`
   contains only `node_type`, `node_id`, `classification`, `candidate_organization_ids`,
   `evidence`, and `note`; `ClientPreflightReport` contains only top-level per-type lists plus
   `generated_for_client_ids`/`classifications`; and the CLI prints only `json.dumps(asdict(report))`
   (`backend/src/app/infrastructure/cli/client_migration_preflight.py`: 52-74, 421-480). The code
   does compute fingerprints internally for optional incoming ledger validation
   (`backend/src/app/infrastructure/cli/client_migration_preflight.py`: 77-95, 387-398), but it does
   not serialize anchor fingerprints, graph-member fingerprints, or per-client closed graph
   membership into the emitted report. As written, the T109 contract claims direct composability with
   a T108 report that cannot actually satisfy the contract's own validation and stale-detection
   rules.

2. **Blocking -- the contract silently narrows ADR-0033's operator-reconciliation boundary.**
   ADR-0033 explicitly allows unresolved sets to map a legacy client to an **existing or
   operator-created** Organization (`ADR/0033-party-client-migration-organization-boundary.md`:
   479-489). T109 instead allows `operator_reconciled` only by choosing one existing Organization
   UUID and rejects any non-existent Organization ID
   (`docs/PartyClientReconciliationContract.md`: 183-195, 224-226). If that narrowing is intended,
   it needs an explicit architectural justification and a truthful account of how deployments that
   need a newly created Organization are expected to complete reconciliation without inventing an
   out-of-band step. As written, it changes the operator workflow relative to ADR-0033 without
   documenting that boundary.

3. **Verified correct -- diff scope is documentation-only and stays within the T109 no-implementation
   boundary.** The reviewed PR diff contains exactly two added files,
   `docs/PartyClientReconciliationContract.md` and `docs/reviews/T109_Software_Architect_Report.md`,
   with no Party/MatterParty/schema/Alembic/backfill/data/RLS/permission/API/frontend/cutover
   implementation.

4. **Verified correct -- repository-standard validation passes cleanly.** `python
   scripts/governance_validate.py`, `python scripts/tests/test_governance_validate.py -v`, and
   `git diff --check` all passed during this QA review.

## Required Changes

- Rework the contract so every field it claims is reproducible from the cited T108 snapshot is
  either:
  - actually present in T108's emitted report shape; or
  - explicitly declared as future wrapper/executor metadata that is **not** claimed to come from
    T108 itself.
- Make the stale-check algorithm truthful and mechanically derivable from the real T108 artifact.
  If per-anchor graph membership and fingerprint comparison are required, they must come from an
  actually emitted authoritative source rather than being assumed.
- Resolve the ADR-0033 mismatch around unresolved sets and newly created Organizations: either
  preserve ADR-0033's "existing or operator-created" allowance in the contract, or explicitly stop
  and govern that narrowing as a separate architectural decision.
- Update the Software Architect report so its description of T108 compatibility is factually
  accurate after the contract is corrected.

## Non-Blocking Comments

None.

## Reviewer Checklist

```text
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☐ Tests added (docs-only batch)
☑ Existing tests pass
☑ Documentation updated
☐ ADR updated (not required for this QA record itself)
☐ AI_BOOTSTRAP updated (not required)
☐ PROJECT_STATE updated (not required before governance closeout)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

## QA Decision

```text
□ Approved
□ Approved with comments
☑ Rework required
```

The branch stays correctly within T109's documentation-only scope, but the contract is not yet
truthful about what T108 actually emits or what can be mechanically revalidated from that output.
That incompatibility is blocking, so PR #186 is **Rework required** at reviewed head
`9e1760f858675677007d7fda013fc81709b90eef`.
