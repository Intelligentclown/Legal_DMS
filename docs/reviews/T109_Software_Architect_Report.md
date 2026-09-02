# T109 Software Architect Report

**Task:** T109 -- Party/Client Migration Reconciliation Contract & Operator Workflow.

**Role:** Software Architect, per `docs/prompts/SoftwareArchitect.md`.

**Artifact under review:** `docs/PartyClientReconciliationContract.md`.

**Status:** Architect rework response after prior QA returned `Rework required`. This report does
not perform QA, merge, governance closeout, or implementation.

## 1. Authorization and Baseline

- Fresh `git fetch origin` completed successfully.
- `origin/main` was verified at `22ea5732d48afa1705e6f8451c9c587f6027cc50`, exactly matching the
  authorization merge lineage provided for this rework.
- `origin/docs/t109-architecture-contract` was verified at
  `9db037479055850552487e39f1d52a98aa6da65e` before editing, exactly matching the expected current
  remote PR head and QA evidence commit.
- The task request required stopping if the branch had moved; it had not moved, so bounded
  rework proceeded.
- The T109 authorization row in `IMPLEMENTATION_QUEUE.md` was read directly and followed exactly:
  architecture/contract only, no persistence implementation, no write-capable migration, no Party
  implementation, no QA decision by this role, and no merge.

## 2. Repository Evidence Inspected

Read directly before rework:

- `AI_BOOTSTRAP.md`
- `docs/AI_EXECUTION_ROUTING.md`
- `PROJECT_WORKFLOW.md`
- T109's `IMPLEMENTATION_QUEUE.md` row
- `docs/prompts/SoftwareArchitect.md`
- `ADR/template.md`
- `ADR/0032-user-organization-pre-existing-data-reconciliation.md`
- `ADR/0033-party-client-migration-organization-boundary.md`
- `backend/src/app/infrastructure/cli/client_migration_preflight.py`
- `backend/src/app/infrastructure/cli/reconcile_organizations.py`
- `docs/reviews/T109_QA_Review.md`
- `docs/ImplementationLog/README.md`

This was enough to ground the rework in the repository's actual current preflight output,
reconciliation precedent, QA findings, and Software Architect constraints without expanding into
unrelated implementation work.

## 3. Prior QA Finding and Rework Scope

The prior independent QA review at architecture head
`9e1760f858675677007d7fda013fc81709b90eef`, preserved in
`docs/reviews/T109_QA_Review.md`, returned **`Rework required`**.

That review raised two mandatory rework findings:

1. the contract claimed T108 emitted snapshot and stale-check fields that the actual
   `client_migration_preflight.py` JSON does not serialize; and
2. the contract narrowed ADR-0033's unresolved-set rule from "existing or operator-created
   Organization" to "existing Organization only."

This rework response changes only the architect-owned T109 contract and this report, and does not
delete, rewrite, or overwrite the QA evidence file.

## 4. What T108 Actually Emits

Direct inspection of `backend/src/app/infrastructure/cli/client_migration_preflight.py` shows that
T108 emits only `json.dumps(asdict(report), indent=2)`, where `report` is a
`ClientPreflightReport`.

That means the emitted T108 JSON contains:

- top-level `generated_for_client_ids`;
- top-level `classifications`;
- per-node-type arrays;
- for each node: `node_type`, `node_id`, `classification`, `candidate_organization_ids`,
  `evidence`, and optional `note`;
- for each evidence item: `source_type`, `source_id`, `path`, and `organization_id`.

It does **not** emit:

- anchor fingerprints;
- graph-member fingerprints;
- per-anchor graph closure lists;
- wrapper metadata such as `git_commit`, `report_sha256`, or `generated_by`;
- executor-time live-graph comparison results.

The reworked contract now states that truth explicitly and distinguishes between:

- data serialized by T108 today; and
- reconciliation-artifact metadata or later executor-computed validation inputs that are outside
  T108's current JSON shape.

## 5. Contract Decisions After Rework

`docs/PartyClientReconciliationContract.md` now decides:

- the exact JSON artifact envelope that cites one frozen T108 report by hash;
- that each entry embeds only the corresponding T108-emitted client snapshot fields
  (`classification`, `candidate_organization_ids`, `evidence`, `note`);
- stable identifiers per Client anchor tied to the cited T108 report hash;
- the allowed states: `deterministic`, `ambiguous`, `unmappable`, `operator_reconciled`, `stale`,
  and `rejected`;
- which states are executable by a later migration tool and which are not;
- how ADR-0033's "existing or operator-created Organization" rule is preserved without claiming the
  artifact itself creates Organizations;
- fail-closed validation for missing, duplicate, conflicting, malformed, or stale entries;
- audit/provenance requirements truthful to the actual T108 baseline;
- resumability and idempotency expectations for a future write-capable executor;
- the downstream handoff contract a future migration task must consume.

## 6. How Stale Detection Works After Correction

The contract no longer claims stale detection can be proven from fictional T108-emitted
fingerprints or graph-closure fields.

Instead, it now states the truthful architectural rule:

1. the artifact must cite the exact T108 report hash it was prepared against;
2. the embedded `t108_snapshot` for each Client anchor must match the cited T108 `clients[]` entry
   exactly after canonical JSON normalization; and
3. a later executor must derive stale/non-stale status from authoritative inputs at execution
   time, such as rerunning T108 and comparing the canonicalized results and/or directly inspecting
   the live legacy graph.

That keeps stale detection mechanically executable in principle without silently expanding T108's
implementation scope or modifying T108 code under T109.

## 7. ADR-0033 Existing-or-Operator-Created Rule

ADR-0033 explicitly allows unresolved sets to map to an **existing or operator-created
Organization**, and the reworked contract now preserves that rule.

The contract's bounded workflow is:

- the artifact may reference either an already-existing Organization UUID or a UUID for an
  Organization the operator created beforehand through an already-governed Organization-creation
  capability;
- `decision.organization_source` records whether the chosen Organization was `existing` or
  `operator_created`;
- the artifact itself does not create Organizations, define a new UI/API, or authorize any schema
  or mutation work.

Repository truth also shows an existing governed capability that creates Organizations:
`backend/src/app/infrastructure/cli/reconcile_organizations.py` creates Organization rows during
ADR-0032 user reconciliation. This report does **not** claim that T109 reuses or modifies that
exact CLI; it cites it only as repository evidence that "operator-created Organization" is already
real and governed rather than fictional.

## 8. Why No New ADR Was Drafted

T109's authorized scope remains narrower than a new ADR. ADR-0033 already decides the Party/Client
migration architecture and explicitly requires deterministic or operator-reconciled Organization
assignment before cutover. ADR-0032 already decides the operator-reconciliation precedent for
legacy tenantless data. The missing piece was the exact machine-readable contract and workflow that
binds T108's read-only output to a future write-capable executor.

That gap can still be filled by a governed architecture/contract artifact without reopening
ADR-0033, changing ADR-0032, or silently deciding a new durable persistence model. Accordingly,
this task still produces a repository contract document plus this report, not a new ADR.

## 9. Composition Check

- **ADR-0033:** preserved. The reworked contract now explicitly preserves both its unresolved-set
  cutover block and its "existing or operator-created Organization" allowance.
- **ADR-0032:** preserved. The contract reuses its explicit-operator-input and fail-closed legacy
  reconciliation precedent, but for Client anchors rather than pre-Organization Users.
- **T108 implementation reality:** preserved. The contract now mirrors only the actual emitted
  `ClientPreflightReport`/`NodeReport` JSON shape and truthfully labels any additional metadata as
  wrapper or executor data.
- **Required ADR #20 outside the Party/Client slice:** untouched. Matter `property_id` /
  `matter_type_id` retirement, Document `matter_id -> file_id`, and other migration seams remain
  unresolved.

## 10. Architecture Stop Boundary

No architecture-stop condition was discovered during this rework.

The repository already contains at least one governed existing capability that creates Organization
rows, so preserving ADR-0033's "operator-created Organization" allowance did not require inventing
a fictional capability or forcing a new ADR inside T109.

The future stop boundary remains unchanged: if a later write-capable executor requires a new durable
reconciliation ledger or another new architectural mechanism beyond the governed artifact and
existing authority, that later task must stop for a separate ADR rather than treating T109 as
implicit approval.

## 11. Exact Files Changed

Exactly two architect-owned documentation files were modified:

- `docs/PartyClientReconciliationContract.md`
- `docs/reviews/T109_Software_Architect_Report.md`

The preserved QA evidence file `docs/reviews/T109_QA_Review.md` was not edited.

## 12. Validation

The required validation set for this rework is:

- `python scripts/governance_validate.py`
- `python scripts/tests/test_governance_validate.py -v`
- `git diff --check`
- focused source/contract consistency checks against T108 actual dataclass fields and serialized
  output shape

Results are reported after those checks run. This Software Architect pass still does not perform an
independent QA decision.

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

`ADR updated` remains correctly unchecked because T109 still does not require a new ADR once the
contract is kept within ADR-0033/0032's existing authority. `PROJECT_STATE.json` remains correctly
untouched because this task has not reached governance closeout.

## QA Decision

```text
□ Approved
□ Approved with comments
□ Rework required
```

Independent QA must review the actual remote PR head after this rework commit is pushed. This
Software Architect pass stops here, per T109's authorized boundary.
