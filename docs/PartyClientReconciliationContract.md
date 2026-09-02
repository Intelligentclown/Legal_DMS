# Party/Client Reconciliation Contract

**Task:** T109 -- Party/Client Migration Reconciliation Contract & Operator Workflow

**Status:** Proposed architecture/contract artifact

**Date:** 2026-09-02

**Governing ADRs:** `ADR/0033-party-client-migration-organization-boundary.md`,
`ADR/0032-user-organization-pre-existing-data-reconciliation.md`

## 1. Purpose

This document defines the machine-readable reconciliation contract and operator workflow that
consumes T108's read-only Party/Client migration preflight output. It governs how deterministic
preflight results are carried forward, how ambiguous or unmappable Client-anchor sets are
explicitly reconciled by an operator, how stale or conflicting decisions fail closed, and what a
later write-capable migration executor must accept and reject.

This document does **not** authorize or implement a write-capable migration command, durable
reconciliation persistence, schema changes, Party/MatterParty creation, or any live data mutation.

## 2. Repository Truth About T108

T108's authoritative emitted artifact is the JSON serialization of
`ClientPreflightReport`/`NodeReport` from
`backend/src/app/infrastructure/cli/client_migration_preflight.py`, produced by
`json.dumps(asdict(report), indent=2)`.

That emitted JSON contains only:

- top-level `generated_for_client_ids`;
- top-level `classifications`;
- per-node-type arrays (`clients`, `addresses`, `properties`, `property_owners`, `matters`,
  `appointments`, `invoices`, `payments`, `client_contacts`);
- for each node in those arrays: `node_type`, `node_id`, `classification`,
  `candidate_organization_ids`, `evidence`, and optional `note`;
- for each evidence item: `source_type`, `source_id`, `path`, and `organization_id`.

T108 does **not** emit any of the following in its current report shape:

- per-node or per-anchor fingerprints;
- per-anchor closed graph-member lists;
- report-wrapper metadata such as `git_commit`, `report_sha256`, or `generated_by`;
- execution-time "live graph still matches" results.

Whenever this contract requires metadata beyond the emitted T108 JSON, that metadata is defined
here as **reconciliation artifact metadata** or **executor-computed validation data**. It must not
be misrepresented as a field that T108 itself serialized.

## 3. Relationship to Existing Governance

- **ADR-0033 reuse, not replacement:** this contract operationalizes ADR-0033 SS6's reconciliation
  requirements without changing ADR-0033's migration architecture or status.
- **ADR-0032 precedent reuse:** like `reconcile_organizations.py`, unresolved legacy data is
  resolved only through explicit operator input; no heuristic grouping, naming, geography, or
  single-Organization assumption is allowed.
- **No new persistence decision here:** the governed artifact is an operator-authored JSON document
  plus the exact T108 evidence report it cites. If a future implementation wants repository-managed
  durable storage such as a reconciliation table or ledger beyond the artifact itself, that is a
  separate architectural decision and requires its own ADR/task rather than being silently decided
  here.

## 4. Governing Workflow

1. Run T108 preflight and produce a JSON evidence report.
2. Freeze the exact T108 report snapshot intended for reconciliation review.
3. Prepare one reconciliation artifact conforming to this document.
4. Copy into that artifact only T108 fields that T108 actually emitted; do not synthesize fake
   "snapshot" fields and then claim they came from T108.
5. Pre-populate deterministic rows from the T108 report exactly as reported; do not let an operator
   override them.
6. Require explicit operator decisions only for unresolved Client anchors (`ambiguous` or
   `unmappable`).
7. If ADR-0033's unresolved set must map to a newly created Organization, create that Organization
   first through an already-governed existing write-capable Organization-creation path, then place
   the resulting valid Organization UUID into the reconciliation artifact. The artifact itself does
   not create Organizations.
8. Before any later write-capable execution, re-verify that the T108 report cited by the artifact
   is still the authoritative baseline and that the reconciliation artifact itself is internally
   valid.
9. If stale detection requires proving that the legacy graph still matches the earlier review
   baseline, a later executor must obtain that proof from authoritative inputs at execution time,
   such as rerunning T108 and comparing canonicalized outputs and/or directly querying the legacy
   graph. That live-validation step is future executor work, not T108-emitted metadata.

## 5. Machine-Readable Artifact

The reconciliation artifact is a UTF-8 JSON file with one document-level header plus one entry per
Client anchor in the cited T108 report.

```json
{
  "schema_version": "t109.party-client-reconciliation.v1",
  "task": "T109",
  "generated_at": "2026-09-02T19:30:00Z",
  "generated_by": {
    "actor_type": "operator",
    "actor_id": "user@example.com",
    "display_name": "Example Operator"
  },
  "source_report": {
    "report_type": "t108.client-migration-preflight.v1",
    "report_path": "client-migration-preflight-2026-09-02.json",
    "report_sha256": "<sha256-of-exact-json-file>"
  },
  "entries": [
    {
      "set_id": "client-set:<legacy_client_id>:<report_sha256_prefix>",
      "anchor": {
        "node_type": "client",
        "node_id": "<legacy_client_uuid>"
      },
      "t108_snapshot": {
        "classification": "ambiguous",
        "candidate_organization_ids": [
          "<organization_uuid_1>",
          "<organization_uuid_2>"
        ],
        "evidence": [
          {
            "source_type": "user",
            "source_id": "<uuid>",
            "path": "Client.created_by -> users.organization_id",
            "organization_id": "<organization_uuid_1>"
          }
        ],
        "note": "Conflicting authoritative evidence found."
      },
      "decision": {
        "state": "operator_reconciled",
        "selected_organization_id": "<organization_uuid_1>",
        "organization_source": "existing",
        "resolution_basis": "operator_confirmed_from_legacy_records",
        "operator_note": "Explained from matter ownership file review."
      },
      "provenance": {
        "entered_at": "2026-09-02T19:28:00Z",
        "entered_by": {
          "actor_type": "operator",
          "actor_id": "user@example.com"
        }
      }
    }
  ]
}
```

## 6. Stable Identifiers

### 6.1 Set identity

Each entry's `set_id` is the stable reconciliation identifier for one T108 Client anchor in one
specific frozen T108 report snapshot:

`client-set:<legacy_client_id>:<report_sha256_prefix>`

This ID is stable for repeated edits of the same reconciliation artifact against the same T108
report snapshot, and intentionally changes when the underlying T108 report snapshot changes. That
makes staleness visible instead of silently reusing an old decision against new evidence.

### 6.2 Anchor identity

The Client anchor is identified only by values T108 actually emits:

- `anchor.node_type = "client"`
- `anchor.node_id = <legacy clients.id UUID>`

No per-anchor fingerprint is required in the artifact, because T108 does not emit one today.

### 6.3 Snapshot identity

Each entry's `t108_snapshot` is the embedded copy of the corresponding T108 `clients[]` node for
that anchor:

- `classification`
- `candidate_organization_ids`
- `evidence`
- `note`

Those fields must be copied truthfully from the cited T108 report and validated against that report
at consumption time.

## 7. Allowed States

Allowed entry `decision.state` values are:

- `deterministic`
  The source T108 snapshot classified the anchor as deterministic. `selected_organization_id` is
  required and must equal the single candidate from T108. Operator override is forbidden.
- `ambiguous`
  Snapshot-only state used before a decision exists. Not executable.
- `unmappable`
  Snapshot-only state used before a decision exists. Not executable.
- `operator_reconciled`
  An operator explicitly chose one Organization for a T108 snapshot that was `ambiguous` or
  `unmappable`.
- `stale`
  A previously prepared entry no longer matches the cited T108 report or a later executor's
  authoritative live-validation inputs. Not executable.
- `rejected`
  The artifact or entry failed validation and must not be used for migration execution.

No other states are valid.

## 8. Allowed Operator Decisions

Operators may do only the following:

- Confirm a T108-deterministic anchor as `deterministic` with the exact same single
  `selected_organization_id`.
- Resolve an `ambiguous` anchor as `operator_reconciled` by choosing one Organization UUID.
- Resolve an `unmappable` anchor as `operator_reconciled` by choosing one Organization UUID.
- Mark `decision.organization_source` as either:
  - `existing`, meaning the selected UUID already existed when the decision was entered; or
  - `operator_created`, meaning the selected UUID was created beforehand through an already-governed
    Organization-creation capability and is now being referenced by this artifact.
- Record a free-text `operator_note`.
- Replace an entry with a new artifact version after a fresh T108 run if the old one became
  `stale`.

Operators may **not**:

- change any deterministic classification into another Organization;
- omit `selected_organization_id` for executable states;
- supply a non-existent or syntactically invalid Organization ID;
- claim that the artifact itself creates an Organization;
- reconcile against a different report snapshot while keeping the old `set_id`.

## 9. Validation Rules

The entire artifact fails closed if any rule below is violated.

### 9.1 Document-level validation

- `schema_version` must equal `t109.party-client-reconciliation.v1`.
- `task` must equal `T109`.
- `source_report.report_type` must equal `t108.client-migration-preflight.v1`.
- `source_report.report_sha256` must match the exact T108 JSON report being consumed.
- `entries` must be present and contain exactly one entry per T108 client anchor in the source
  report.
- No duplicate `set_id` or duplicate `anchor.node_id` may appear.

### 9.2 Entry-level validation

- `anchor.node_type` must be `client`.
- `anchor.node_id` must exist in the cited T108 `generated_for_client_ids` set and in the cited
  T108 `clients[]` list.
- `t108_snapshot.classification`, `t108_snapshot.candidate_organization_ids`,
  `t108_snapshot.evidence`, and `t108_snapshot.note` must match the corresponding T108 `clients[]`
  entry exactly after canonical JSON normalization.
- `decision.state = deterministic` is valid only when `t108_snapshot.classification =
  deterministic`.
- `decision.state = operator_reconciled` is valid only when `t108_snapshot.classification` is
  `ambiguous` or `unmappable`.
- `decision.selected_organization_id` is required for `deterministic` and `operator_reconciled`,
  forbidden for `ambiguous`, `unmappable`, `stale`, and `rejected`.
- `decision.selected_organization_id` must be one of:
  - the sole T108 candidate for `deterministic`; or
  - an existing Organization UUID for `operator_reconciled`, whether that Organization existed
    already or was operator-created beforehand through a separate governed capability.
- `decision.organization_source` must be absent for non-executable states and must be either
  `existing` or `operator_created` for `operator_reconciled`.

### 9.3 Fail-closed stale checks

An entry becomes `stale` and non-executable if any of the following is true:

- the executor loaded a different T108 report than the one identified by
  `source_report.report_sha256`;
- rerunning T108 for the same target legacy dataset produces a different canonicalized `clients[]`
  entry for that anchor than the embedded `t108_snapshot`;
- rerunning T108 changes the anchor's `classification`, `candidate_organization_ids`, `evidence`,
  or `note`;
- a selected Organization UUID no longer exists at execution time;
- the later executor's direct legacy-graph inspection finds that the authoritative graph state no
  longer matches the basis on which the T108 rerun was accepted.

This contract deliberately leaves open **which** later authoritative live-validation mechanism is
selected by the eventual execution task. The acceptable architectural rule is narrower: stale
detection must come from authoritative inputs such as a fresh T108 rerun and/or direct live-graph
inspection, not from fictional fields claimed to have been serialized by T108.

### 9.4 Conflict checks

The artifact is `rejected` if:

- two entries claim the same `anchor.node_id`;
- a deterministic entry names an Organization other than T108's sole candidate;
- an operator-reconciled entry names two Organizations or none;
- any UUID is malformed;
- any node type is unknown;
- any required field is missing.

## 10. ADR-0033 Operator-Created Organization Handling

ADR-0033 allows an unresolved set to map to an **existing or operator-created Organization**. This
contract preserves that rule.

The bounded T109 workflow is:

1. T108 identifies the unresolved Client anchor and its evidence.
2. The operator decides whether the correct target is an already-existing Organization or a newly
   created one.
3. If a new Organization is needed, the operator must create it first through an already-governed
   Organization-creation capability that exists outside this artifact.
4. The operator then records the resulting valid Organization UUID in
   `decision.selected_organization_id` and marks `decision.organization_source =
   "operator_created"`.

T109 does **not** define a new UI, API, schema change, or artifact-side creation mechanism for that
step. It only preserves ADR-0033's allowance truthfully by requiring the artifact to reference the
resulting Organization after creation has already happened through a separately governed path.

Repository evidence shows at least one governed existing capability already creates Organizations:
`backend/src/app/infrastructure/cli/reconcile_organizations.py` creates Organization rows during
ADR-0032 user reconciliation. T109 does not extend, modify, or repurpose that command here; it is
evidence that "operator-created Organization" is not architecturally fictional in this repository.
Whether a future Party/Client migration workflow reuses that exact path or another already-governed
Organization-creation path remains implementation work outside T109.

## 11. Audit and Provenance Requirements

Each entry must retain enough evidence to answer:

- what was classified;
- what T108 originally reported for that anchor;
- which Organization was selected, if any;
- whether the result was deterministic or operator-reconciled;
- whether the selected Organization pre-existed or was operator-created beforehand;
- who or what prepared the artifact;
- when it was prepared;
- which exact T108 report snapshot it was based on.

Minimum required provenance fields are:

- `source_report.report_sha256`
- `anchor.node_id`
- `t108_snapshot.classification`
- `t108_snapshot.candidate_organization_ids`
- `t108_snapshot.evidence`
- `t108_snapshot.note`
- `decision.state`
- `decision.selected_organization_id` where applicable
- `decision.organization_source` where applicable
- `decision.operator_note`
- `provenance.entered_at`
- `provenance.entered_by.actor_type`
- `provenance.entered_by.actor_id`

Additional wrapper metadata such as a filesystem path, repository commit, report-generation
timestamp, executor identity, or execution-run reference may be captured by future tooling, but
those are wrapper/execution metadata rather than T108-emitted fields.

## 12. Resumability and Idempotency for a Later Execution Tool

A future write-capable executor must treat this artifact as declarative input, not as advisory
text.

- Re-running the executor with the same valid artifact against the same unchanged authoritative
  T108 baseline must produce no new interpretation differences.
- The executor may skip already-completed units only if it can prove that the same anchor, same
  accepted T108 snapshot, and same selected Organization were already applied.
- The executor must not partially reinterpret an entry after a stale check fails; it must stop and
  require a fresh T108 report plus fresh artifact.
- The executor must not "repair" missing or conflicting decisions by heuristic.

This contract does **not** decide how a future executor persists its own completion state. If that
requires a new durable reconciliation or migration ledger beyond current ADR authority, that future
task must stop for a separate ADR.

## 13. Downstream Handoff Contract

The future write-capable migration task may proceed only when it receives:

- a valid T108 source report;
- a valid T109 reconciliation artifact following this schema;
- proof that every Client anchor is in an executable state (`deterministic` or
  `operator_reconciled`);
- a clean stale-check result from authoritative inputs.

Its minimum consumption contract is:

- trust `deterministic` and `operator_reconciled` only after validation;
- reject `ambiguous`, `unmappable`, `stale`, and `rejected`;
- apply one selected Organization per Client anchor;
- preserve enough execution output to prove which entry was consumed for which migrated anchor.

## 14. Explicit Non-Scope

This document does not:

- introduce a new table, ledger, or repository-managed durable persistence mechanism;
- decide Party backfill transaction chunking;
- define the exact CLI/GUI used to author the artifact;
- implement validation code;
- implement the later write-capable executor;
- authorize any schema, migration, RLS, permission, API, frontend, or cutover change;
- resolve non-Party slices of Required ADR #20.
