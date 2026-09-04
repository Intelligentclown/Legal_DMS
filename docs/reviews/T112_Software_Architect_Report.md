# T112 Software Architect Report

**Task:** T112 -- Party/Client Migration Persistence & Execution-Ledger Architecture.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`.

**Artifact under review:** `ADR/0034-party-client-migration-persistence-and-execution-ledger.md`.

**Status:** Initial architecture draft for PR 2 of T112's three-PR lifecycle. This report does not
perform QA, merge, governance closeout, or implementation.

## 1. Authorization and Verified Baseline

- Fresh `git fetch origin` completed successfully.
- `origin/main` was independently verified at `2f27712109753fce0cd83ad4b8b5b397d11fec66`, exactly the
  expected post-PR-196 T113 closeout merge.
- `git merge-base --is-ancestor 63251e4210bc5d97e739d570d8d614941eca08e6 HEAD` confirmed the T112
  authorization commit remains in this branch's ancestry. The authorization merge path is PR #194,
  merge `98cb4b383c58e61f0d99521fa9046840c1366633`.
- Repository governance state was rechecked directly before drafting:
  - `T112` remains authorized and not Done.
  - `T113` is Done.
  - `T114` is not authorized anywhere in the repository.
  - Required ADR #20 remains unresolved globally.
  - `PROJECT_STATE.json` still reports `latestTaskDone = T113`, `latestTaskAuthorized = T113`, and
    `inProgressTransitions = []`.
- GitHub PR search found no existing T112 Architecture+QA PR; only the merged authorization PR #194
  exists for T112 at draft start.
- ADR numbering was rechecked from the repository contents at branch creation time. `ADR/0033` was the
  highest existing ADR on `origin/main`, so this branch correctly uses `ADR/0034`.

## 2. Repository Evidence Read

Read directly before drafting:

- `AI_BOOTSTRAP.md`
- `PROJECT_WORKFLOW.md` (especially §3.1)
- `PROJECT_STATE.json`
- T112's exact authorization row in `IMPLEMENTATION_QUEUE.md`
- `docs/prompts/SoftwareArchitect.md`
- `docs/ImplementationLog/README.md`
- `ADR/template.md`
- `ADR/0020-session-commit-rollback-policy.md`
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0023-party-vs-client-architecture.md`
- `ADR/0028-financial-ledger-boundary-charge-expense-invoice-payment-allocation.md`
- `ADR/0032-user-organization-pre-existing-data-reconciliation.md`
- `ADR/0033-party-client-migration-organization-boundary.md`
- `docs/PartyClientReconciliationContract.md`
- `backend/src/app/infrastructure/cli/client_migration_preflight.py`
- `backend/src/app/infrastructure/cli/client_reconciliation_artifact_validator.py`
- `backend/src/app/infrastructure/cli/client_reconciliation_staleness_preflight.py`
- `backend/src/app/infrastructure/persistence/models/mixins.py`
- `docs/reviews/T109_Software_Architect_Report.md`
- `docs/reviews/T110_QA_Review.md`
- `docs/reviews/T111_QA_Review.md`

This was the minimal set needed to ground the decision in the repository's already-governed
Party/Client migration chain without drifting into unauthorized implementation planning.

## 3. Architectural Decision Summary

`ADR/0034` selects a **dedicated, append-only execution ledger** as the durable persistence mechanism a
future write-capable Party/Client migration executor must use.

The decision made there is:

- the future executor's durable completion proof is **not** the existence of a `Party` row alone and
  **not** the frozen T109 artifact alone;
- one immutable ledger completion record is required per migrated legacy Client anchor, bound to the
  exact accepted T109/T111 basis and executor version;
- the ledger identity must include at minimum `legacy_client_id`, `party_id`, `organization_id`,
  `executor_version`, T109 `set_id`, T108 `report_sha256`, decision-state/selection outcome, and a
  source fingerprint strong enough to prove the exact accepted legacy Client version;
- deterministic and operator-reconciled mappings share one ledger structure but retain explicit
  distinction in the record;
- one migration unit's business writes and its completion ledger record commit atomically or roll back
  together;
- retry may skip only a ledger-proven identical completion; any mismatch is fail-closed stale input or
  hard collision, never silent repair;
- interrupted-run recovery is ledger-driven, not inferred heuristically from partially-present business
  rows;
- the ledger survives legacy-table retirement as immutable migration audit history.

## 4. Alternatives Considered

The ADR evaluates three genuine alternatives:

1. artifact-only persistence;
2. inferring completion from `parties` and retargeted business rows alone;
3. a dedicated execution ledger (selected).

The first two were rejected because neither one can provide a durable, unambiguous proof that the same
governed legacy Client mapping already completed safely under the same reconciliation basis. The
selected ledger is the narrowest option that makes idempotency, collision handling, and restart
semantics explicit without implementing schema or executor code in this task.

## 5. Composition Check

- **`ADR/0033`**: preserved and extended, not reopened. `ADR/0034` supplies the execution-side durable
  proof mechanism `ADR/0033` intentionally left open, while keeping `ADR/0033`'s Party migration shape,
  unresolved-set stop rule, and compatibility-first cutover intact.
- **`ADR/0032`**: preserved. Operator-reconciled legacy ambiguity remains an explicit human decision,
  not a heuristic. `ADR/0034` only requires that the execution ledger remember whether the accepted
  basis was deterministic or operator-reconciled.
- **T109 contract**: preserved. The ledger consumes T109's governed artifact identity (`set_id`,
  `report_sha256`, decision state/selection) as input basis; it does not modify the artifact schema or
  claim the artifact itself proves execution completion.
- **T110 validator**: preserved. T110 remains the contract-validation gate for the frozen artifact.
  `ADR/0034` relies on it and does not broaden its boundary into write-capable execution.
- **T111 staleness preflight**: preserved. T111 remains the live fail-closed gate before execution.
  `ADR/0034` requires execution to use that verified basis; it does not weaken or replace T111's
  stale-check role.
- **`ADR/0020`**: composed with directly. The ADR's atomicity rule extends the repository's existing
  commit-or-rollback discipline to one migration unit's business writes plus ledger completion record.
- **`ADR/0021`**: preserved. `organization_id` remains a load-bearing identity component, and any
  collision or stale mismatch fails closed rather than risking cross-tenant reinterpretation.
- **Required ADR #20 outside the Party/Client slice**: untouched. No Matter `property_id` /
  `matter_type_id`, Document `matter_id` -> `file_id`, frontend, cutover, or global migration strategy
  decision was made here.

## 6. Explicitly Unresolved Questions

- The future implementation's exact physical schema shape for the dedicated ledger table or equivalent
  persistence mechanism is intentionally not designed here beyond the architectural invariants the ADR
  requires.
- Whether a future implementation proves that one legacy Client anchor is always the correct minimum
  atomic execution unit, or whether some unresolved anchor-sets must commit as a larger governed unit,
  remains open to future implementation so long as this ADR's atomicity and immutable-ledger invariants
  hold.
- Whether dependent rows need richer per-row source fingerprints beyond the anchor-level fingerprint is
  left open; this ADR only requires that the accepted anchor basis be durably provable.
- Retention may later be operationally archived, but the architecture requires immutability and audit
  survivability; the repository has not yet decided the operational storage lifecycle for that archive.

## 7. Exact Files Changed

Exactly two documentation files were added in this T112 architecture draft:

- `ADR/0034-party-client-migration-persistence-and-execution-ledger.md`
- `docs/reviews/T112_Software_Architect_Report.md`

No `backend/`, `frontend/`, `electron/`, Alembic, schema, API, test, `IMPLEMENTATION_QUEUE.md`, or
`PROJECT_STATE.json` file was changed by this draft.

## 8. Confirmation No Unauthorized Implementation Occurred

This branch does **not** implement:

- Party or `MatterParty` models
- ledger schema or Alembic migrations
- bridge columns
- reconciliation execution
- Party backfill or data writes
- API/frontend/Electron changes
- permission/RLS changes
- governance closeout
- T113 follow-up work
- T114 authorization or any later task

The branch is architecture-only, exactly as T112 authorized.

## 9. Validation

The following validation set was run for this architecture draft:

- `python scripts/governance_validate.py`
- `python -m unittest scripts.tests.test_governance_validate -v`
- `git diff --check`

Results are reported after the commands complete. This report still does not perform or pre-render the
independent QA Decision required before merge.

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

`Tests added` and `Existing tests pass` remain correctly unchecked because this was a documentation-only
architecture task with no code changes. `PROJECT_STATE.json` remains correctly untouched because T112 is
not at governance closeout.

## QA Decision

```text
□ Approved
□ Approved with comments
□ Rework required
```

Independent QA is next. This Software Architect pass stops at the ADR plus self-assessed report, per
T112's authorized PR-2 boundary.
