# Party/Client Reconciliation Contract

**Task:** T109 — Party/Client Migration Reconciliation Contract & Operator Workflow

**Status:** Proposed architecture/contract artifact

**Date:** 2026-09-02

**Governing ADRs:** `ADR/0033-party-client-migration-organization-boundary.md`, `ADR/0032-user-organization-pre-existing-data-reconciliation.md`

## 1. Purpose

This document defines the exact machine-readable reconciliation contract and operator workflow that
consumes T108's read-only Party/Client migration preflight output. It governs how deterministic
preflight results are carried forward, how ambiguous or unmappable Client-anchor graph sets are
explicitly reconciled by an operator, how stale or conflicting decisions fail closed, and what a
later write-capable migration executor must accept and reject.

This document does **not** authorize or implement a write-capable migration command, durable
reconciliation persistence, schema changes, Party/MatterParty creation, or any live data mutation.

## 2. Relationship to Existing Governance

- **ADR-0033 reuse, not replacement:** this contract operationalizes ADR-0033 SS6's reconciliation
  requirements without changing ADR-0033's migration architecture or status.
- **ADR-0032 precedent reuse:** like `reconcile_organizations.py`, unresolved legacy data is
  resolved only through explicit operator input; no heuristic grouping, naming, geography, or
  single-Organization assumption is allowed.
- **No new persistence decision here:** the governed artifact is an operator-authored JSON document
  plus the T108 evidence snapshot it cites. If a future implementation wants repository-managed
  durable storage such as a reconciliation table or ledger beyond the artifact itself, that is a
  separate architectural decision and requires its own ADR/task rather than being silently decided
  here.

## 3. Governing Workflow

1. Run T108 preflight and produce an immutable JSON evidence report.
2. Freeze the exact T108 report snapshot intended for reconciliation review.
3. Prepare one reconciliation artifact conforming to this document.
4. Pre-populate deterministic rows from the T108 report exactly as reported; do not let an operator
   override them.
5. Require explicit operator decisions only for unresolved graph sets (`ambiguous` or
   `unmappable`).
6. Before any later write-capable execution, re-verify that the live legacy graph still matches the
   cited T108 snapshot and that the reconciliation artifact itself is internally valid.
7. If the live graph, source fingerprints, or evidence snapshot changed, mark affected decisions
   stale and fail closed until a fresh T108 report and reconciliation artifact exist.

## 4. Machine-Readable Artifact

The reconciliation artifact is a UTF-8 JSON file with one document-level header plus one entry per
Client-anchor reconciliation set.

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
    "report_sha256": "<sha256>",
    "report_generated_at": "2026-09-02T18:55:00Z",
    "preflight_code_ref": "backend/src/app/infrastructure/cli/client_migration_preflight.py",
    "git_commit": "<commit-sha>"
  },
  "entries": [
    {
      "set_id": "client-set:<legacy_client_id>:<report_sha256_prefix>",
      "anchor": {
        "node_type": "client",
        "node_id": "<legacy_client_uuid>",
        "fingerprint": "Client:<uuid>:<version>:<updated_at>"
      },
      "snapshot": {
        "classification": "ambiguous",
        "candidate_organization_ids": [
          "<organization_uuid_1>",
          "<organization_uuid_2>"
        ],
        "graph_node_ids": {
          "clients": ["<uuid>"],
          "addresses": ["<uuid>"],
          "properties": ["<uuid>"],
          "property_owners": ["<uuid>"],
          "matters": ["<uuid>"],
          "appointments": ["<uuid>"],
          "invoices": ["<uuid>"],
          "payments": ["<uuid>"],
          "client_contacts": ["<uuid>"]
        },
        "evidence": [
          {
            "source_type": "user",
            "source_id": "<uuid>",
            "path": "Client.created_by -> users.organization_id",
            "organization_id": "<organization_uuid_1>"
          }
        ]
      },
      "decision": {
        "state": "operator_reconciled",
        "selected_organization_id": "<organization_uuid_1>",
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

## 5. Stable Identifiers

### 5.1 Set identity

Each entry's `set_id` is the stable reconciliation identifier for one T108 Client-anchor graph set:

`client-set:<legacy_client_id>:<report_sha256_prefix>`

This ID is stable for repeated edits of the same reconciliation artifact against the same T108
report snapshot, and intentionally changes when the underlying report snapshot changes. That makes
staleness visible instead of silently reusing an old decision against new evidence.

### 5.2 Anchor identity

The Client anchor is identified by:

- `anchor.node_type = "client"`
- `anchor.node_id = <legacy clients.id UUID>`
- `anchor.fingerprint = Client:<id>:<version>:<updated_at>`

The anchor fingerprint must match the T108 report snapshot exactly.

### 5.3 Affected graph identity

`snapshot.graph_node_ids` records the full affected graph set by node type and UUID, using the same
node taxonomy T108 already emits: `client`, `address`, `property`, `property_owner`, `matter`,
`appointment`, `invoice`, `payment`, and `client_contact`.

The later execution tool must treat this graph set as closed for validation purposes: any live
additional dependency discovered for the anchor that was not present in the cited snapshot makes the
entry stale and non-executable.

## 6. Allowed States

Allowed entry `decision.state` values are:

- `deterministic`
  The source T108 snapshot classified the set as deterministic. `selected_organization_id` is
  required and must equal the single candidate from T108. Operator override is forbidden.
- `ambiguous`
  Snapshot-only state used before a decision exists. Not executable.
- `unmappable`
  Snapshot-only state used before a decision exists. Not executable.
- `operator_reconciled`
  An operator explicitly chose one Organization for a snapshot that was `ambiguous` or
  `unmappable`.
- `stale`
  A previously prepared entry no longer matches the cited snapshot or live graph. Not executable.
- `rejected`
  The artifact or entry failed validation and must not be used for migration execution.

No other states are valid.

## 7. Allowed Operator Decisions

Operators may do only the following:

- Confirm a T108-deterministic set as `deterministic` with the exact same single
  `selected_organization_id`.
- Resolve an `ambiguous` set as `operator_reconciled` by choosing one existing Organization UUID.
- Resolve an `unmappable` set as `operator_reconciled` by choosing one existing Organization UUID.
- Record a free-text `operator_note`.
- Replace an entry with a new artifact version after rerunning T108 if the old one became `stale`.

Operators may **not**:

- change any deterministic classification into another Organization;
- omit `selected_organization_id` for executable states;
- supply a non-existent or syntactically invalid Organization ID;
- remove graph members from the cited snapshot;
- mark an unresolved set executable without an explicit Organization choice;
- reconcile against a different report snapshot while keeping the old `set_id`.

## 8. Validation Rules

The entire artifact fails closed if any rule below is violated.

### 8.1 Document-level validation

- `schema_version` must equal `t109.party-client-reconciliation.v1`.
- `task` must equal `T109`.
- `source_report.report_type` must equal `t108.client-migration-preflight.v1`.
- `source_report.report_sha256` must match the exact T108 JSON report being consumed.
- `entries` must be present and contain exactly one entry per T108 Client anchor in the source
  report.
- No duplicate `set_id`, `anchor.node_id`, or graph-member UUID may appear in inconsistent entries.

### 8.2 Entry-level validation

- `anchor.node_type` must be `client`.
- `anchor.node_id` must exist in `source_report`.
- `anchor.fingerprint` must match the source snapshot exactly.
- `snapshot.classification` must equal the T108 classification for that anchor exactly.
- `snapshot.candidate_organization_ids`, `snapshot.graph_node_ids`, and `snapshot.evidence` must be
  byte-for-byte reproducible from the cited T108 snapshot after canonical JSON normalization.
- `decision.state = deterministic` is valid only when `snapshot.classification = deterministic`.
- `decision.state = operator_reconciled` is valid only when `snapshot.classification` is
  `ambiguous` or `unmappable`.
- `decision.selected_organization_id` is required for `deterministic` and `operator_reconciled`,
  forbidden for `ambiguous`, `unmappable`, `stale`, and `rejected`.
- `decision.selected_organization_id` must be one of:
  - the sole T108 candidate for `deterministic`; or
  - an existing Organization UUID explicitly supplied by the operator for `operator_reconciled`.

### 8.3 Fail-closed stale checks

An entry becomes `stale` and non-executable if any of the following changed after the T108 report:

- the anchor fingerprint changed;
- any graph member fingerprint changed;
- any graph member was added or removed for that anchor;
- the T108 classification or candidate-Organization set changed;
- any Organization UUID referenced by the entry no longer exists;
- the artifact cites a different report hash than the evidence snapshot the executor loaded.

### 8.4 Conflict checks

The artifact is `rejected` if:

- two entries claim the same `anchor.node_id`;
- one graph-member UUID appears in two entries with conflicting selected Organizations;
- a deterministic entry names an Organization other than T108's sole candidate;
- an operator-reconciled entry names two Organizations or none;
- any UUID is malformed;
- any node type is unknown;
- any required field is missing.

## 9. Audit and Provenance Requirements

Each entry must retain enough evidence to answer:

- what was classified;
- what T108 originally reported;
- which Organization was selected, if any;
- whether the result was deterministic or operator-reconciled;
- who or what prepared the artifact;
- when it was prepared;
- which T108 report snapshot and repository commit it was based on.

Minimum required provenance fields are:

- `source_report.report_sha256`
- `source_report.report_generated_at`
- `source_report.git_commit`
- `anchor.node_id`
- `anchor.fingerprint`
- `snapshot.classification`
- `snapshot.candidate_organization_ids`
- `snapshot.graph_node_ids`
- `snapshot.evidence`
- `decision.state`
- `decision.selected_organization_id` where applicable
- `decision.operator_note`
- `provenance.entered_at`
- `provenance.entered_by.actor_type`
- `provenance.entered_by.actor_id`

## 10. Resumability and Idempotency for a Later Execution Tool

A future write-capable executor must treat this artifact as declarative input, not as advisory text.

- Re-running the executor with the same valid artifact against the same unchanged legacy snapshot
  must produce no new interpretation differences.
- The executor may skip already-completed units only if it can prove the same anchor fingerprint,
  same selected Organization, and same graph-set membership were already applied.
- The executor must not partially reinterpret an entry after a stale check fails; it must stop and
  require a fresh T108 report plus fresh artifact.
- The executor must not "repair" missing or conflicting decisions by heuristic.

This contract does **not** decide how a future executor persists its own completion state. If that
requires a new durable reconciliation or migration ledger beyond current ADR authority, that future
task must stop for a separate ADR.

## 11. Downstream Handoff Contract

The future write-capable migration task may proceed only when it receives:

- a valid T108 source report;
- a valid T109 reconciliation artifact following this schema;
- proof that every Client anchor is in an executable state (`deterministic` or
  `operator_reconciled`);
- a clean stale-check result against the live legacy graph.

Its minimum consumption contract is:

- trust `deterministic` and `operator_reconciled` only after validation;
- reject `ambiguous`, `unmappable`, `stale`, and `rejected`;
- apply one selected Organization per anchor graph set;
- preserve enough execution output to prove which entry was consumed for which migrated graph set.

## 12. Explicit Non-Scope

This document does not:

- introduce a new table, ledger, or repository-managed durable persistence mechanism;
- decide Party backfill transaction chunking;
- define the exact CLI/GUI used to author the artifact;
- implement validation code;
- implement the later write-capable executor;
- authorize any schema, migration, RLS, permission, API, frontend, or cutover change;
- resolve non-Party slices of Required ADR #20.
