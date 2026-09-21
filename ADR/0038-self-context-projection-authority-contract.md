# ADR-0038: Self-Context Projection Authority Contract

**Status:** Proposed  
**Date:** 2026-09-21

**Related task:** T128 — Self-Context Projection Architecture and Authority Contract.

**Does not resolve:** any Required ADR. In particular, Required ADR #20 remains unresolved. This
ADR does not change ADR-0036 or ADR-0037 status and does not authorize Self-Context implementation,
application work, database work, or T129+.

## Problem

Legal_DMS deliberately keeps durable repository evidence for task authorization and completion,
architectural decisions, QA, domain rules, point-in-time state, and Git history. That recoverability
has become expensive to consume and easy to misread as current state. On the T128 authorization
baseline, `IMPLEMENTATION_QUEUE.md` is a large current-task registry plus historical archive,
`PROJECT_STATE.json` combines structured current state with long historical narrative, and manually
maintained orientation documents contain materially obsolete current-state assertions. The existing
governance validator already derives some facts mechanically, but it is a validation tool with
explicit epistemic limits, not a compact context interface.

A generated context artifact can reduce retrieval cost only if it cannot become a second governance
ledger, silently upgrade weak evidence into stronger evidence, or choose among contradictory
authoritative sources. The repository therefore needs a durable contract before any compiler or
manifest is implemented.

## Options Considered

### 1. Continue manual orientation only

Keep the existing bootstrap and periodically synchronize narrative documents. This avoids new
tooling but preserves duplicated volatile facts, high context-consumption cost, and recurring
staleness. Rejected.

### 2. Commit a generated context snapshot as another maintained state file

A committed snapshot is easy for remote consumers to read, but it creates synchronization and
source-of-truth ambiguity immediately. It can be stale even when its inputs are correct. Rejected
for the foundation; a later task may revisit a tiny committed bootstrap artifact only with evidence
that on-demand generation is insufficient.

### 3. Deterministic, on-demand, non-authoritative projection over existing authority

Derive a small versioned current-context projection from existing authoritative evidence, with
explicit provenance and conflict behavior. Keep the source evidence authoritative and make the
projection disposable/regenerable. Selected.

### 4. LLM-generated context synthesis

An LLM can summarize broad history, but semantic inference is nondeterministic and can collapse
documented, mechanically verified, and inferred claims into one voice. Rejected for the deterministic
core. LLMs may consume the projection later.

## Decision

### 1. Projection, not authority

The Self-Context output is a **projection**: a derived, reproducible, disposable/regenerable,
source-linked, versioned view of repository evidence. It is neither a governance ledger nor an
architectural decision record.

The invariant is:

```text
authoritative repository evidence
        ↓
deterministic derivation
        ↓
non-authoritative context projection
        ↓
human / AI consumption
```

Generated context may reproduce an already-recorded decision with provenance. It must never create
or independently decide task authorization, task selection, architecture, ADR status/acceptance, QA
approval, implementation permission, governance transitions, or project priority.

If a projection conflicts with its source, the source wins and the projection is disposable.

### 2. Authority map

The first implementation must derive from the repository's existing ownership rules rather than
inventing replacements:

- numbered task identity, scope, authorization, and completion narrative:
  `IMPLEMENTATION_QUEUE.md` task rows;
- current latest-authorized/latest-Done convenience values: mechanically derived from those rows,
  cross-checked with `PROJECT_STATE.json.governanceLedger`;
- architecture decisions: numbered ADR files and their recorded status;
- Required-ADR resolution: numbered ADR `Resolves:` metadata as interpreted by the existing
  governance rules;
- business/domain baseline: the governed Domain Model & Functional Specification;
- QA result: canonical repository QA/review record; a projection may report that result but does
  not reproduce QA;
- point-in-time project snapshot: `PROJECT_STATE.json` remains the compatibility snapshot during
  migration, with its governance ledger explicitly a derived convenience view under existing rules;
- application/runtime capability: production code/schema, not roadmap or stale orientation prose;
- commit ancestry, merge identity, and remote PR facts: Git/GitHub evidence, not static prose.

Where existing repository rules leave overlapping authority genuinely ambiguous, the projection
must expose the ambiguity rather than invent precedence.

### 3. Minimum Current Context Manifest

The first future layer is a deliberately small **Current Context Manifest**. Its logical contract is:

- **identity**: `context_schema_version`, repository identity, `source_commit`,
  `derivation_version`, and `source_set_version`; an optional deterministic source/input digest
  may be added;
- **governance frontier**: latest Done task, latest Authorized task, and bounded in-progress
  transitions, only when mechanically derivable;
- **ADR state**: unresolved/resolved Required ADRs and explicitly relevant ADR status when derivable
  from governed metadata;
- **active authorized work**: recorded authorization state only; no recommendation of what should
  happen next;
- **provenance**: source references and evidence classification at the minimum useful granularity;
- **discrepancies**: only deterministic findings supported by defined rules.

The manifest must not contain project history merely because the source files contain it. Historical
narrative remains reachable through provenance/source links.

### 4. Determinism and input identity

Canonical invariant:

> Same authoritative repository state plus the same context schema, derivation contract, and
> source-set version produces the same logical context.

Canonical output therefore uses stable ordering and deterministic serialization. A wall-clock
`generatedAt` value is excluded from the canonical payload because it changes without an input
change. A consumer may add noncanonical presentation metadata outside the signed/compared logical
payload.

`source_commit` identifies the checked-out repository state. `source_set_version` identifies
which source classes and parsing contracts participate. `derivation_version` identifies semantic
derivation behavior independently of the output schema. `context_schema_version` identifies the
consumer-visible shape.

### 5. Provenance model

No confidence score is permitted in the deterministic core. Use a hybrid model: manifest-level
input identity plus assertion/section provenance where epistemic strength materially differs.

The minimum vocabulary is:

- `mechanically_verified`: a deterministic repository rule proves the assertion within that rule's
  declared boundary;
- `repository_derived`: deterministically computed from repository content but not equivalent to a
  stronger external/mechanical proof;
- `git_verified`: established from Git object/history evidence; live remote facts require an
  explicitly remote evidence source rather than this label by implication;
- `qa_recorded`: the canonical repository record says QA rendered the stated result; the context
  derivation did not reproduce QA;
- `documented`: a designated document states the assertion but no stronger derivation is claimed;
- `unverified`: recorded or requested information is outside the available verification boundary;
- `conflicting`: governed inputs needed for an assertion are incompatible and no repository rule
  establishes precedence.

A projection must never promote `documented` or `qa_recorded` to `mechanically_verified`.

### 6. Discrepancy and fail-closed semantics

Adopt five discrepancy classes:

- **stale**: a non-authoritative volatile projection/narrative contradicts newer authoritative
  evidence under a deterministic freshness rule;
- **conflicting**: authoritative inputs required for the same assertion are incompatible and no
  governed precedence resolves them;
- **unsupported**: the requested assertion cannot be derived from permitted sources/rules;
- **invalid**: an authoritative input violates a required structural contract;
- **unverified**: the assertion is recorded but outside the available mechanical evidence boundary.

For **conflicting** or **invalid** authoritative inputs, canonical generation fails with non-zero
status and must not emit an apparently healthy manifest. Diagnostic output may identify the
conflict, but disputed canonical values are omitted.

A **stale** non-authoritative orientation/snapshot document may produce a warning while generation
continues if authoritative values are unambiguous. **Unverified** facts may be represented only with
that provenance. **Unsupported** values are omitted or explicitly represented as unsupported; they
are never inferred.

The system must not select the newest-looking, most plausible, or most convenient source unless a
repository rule explicitly defines that precedence.

### 7. On-demand generation

The Current Context Manifest is generated **on demand** in the foundation. It is not initially
committed to Git. This avoids a second stale artifact, generated-diff noise, and source-of-truth
confusion. The source commit is the freshness identity.

Future CI may run generation/checks to prove deterministic derivation succeeds. Committed-artifact
synchronization is a separate later decision and is not required for the first implementation.

### 8. Offline, Git, and network boundary

The deterministic foundation is repository-local and offline. It may parse checked-out files and,
when available, inspect local Git objects needed for `source_commit` or Git-derived evidence.
Generation must not require GitHub/network access.

Live PR state, remote branch state, protected-branch state, or remote ancestry verification is a
separate evidence class and may be added later only with explicit provenance. Absence of network
evidence must not be disguised as remote verification.

### 9. No-LLM deterministic core

No LLM is required or permitted for canonical derivation, conflict resolution, provenance
classification, or CI pass/fail behavior in the foundation. LLMs may consume the resulting context,
follow its provenance to sources, summarize it, or request broader evidence. They may not convert
their interpretation back into canonical project decisions.

### 10. Shared derivation with governance validation

Long term there must be one semantic implementation for governance facts shared by validation and
context projection:

```text
authoritative parsers / derivation
        ├── governance validation
        └── context projection
```

Two independent parsers for task rows, latest authorization/Done state, ADR numbering, `Resolves:`,
or Required-ADR state are prohibited as a steady-state architecture.

The first implementation does **not** require a broad validator rewrite. It should extract only the
small reusable parser/derivation units required by the manifest while preserving
`governance_validate.py` behavior and tests. Directly consuming the validator's CLI/report text is
not the durable interface because presentation output is not a semantic API.

The validator's current epistemic boundary remains binding: text-pattern checks prove only what
their rules actually check; they do not prove Git ancestry, business correctness, or QA execution.

### 11. Layering

Future Self-Context uses three layers:

1. **Current Context Manifest** — cheap answer to “Where is the repository now?”
2. **Task Context Package** — later bounded projection answering “What governed context does this
   already-authorized task need?”
3. **Human-readable rendering** — later presentation over the same derived model.

Only Layer 1 is the first implementation target. Layer 2 may later include task identity,
authorization, scope/exclusions, dependencies, ADR references, relevant files/tests/lifecycle gates,
QA evidence, and provenance, but it must not choose the task. Layer 3 must not become a new authority.

### 12. Existing-document compatibility

`docs/Context.md` should become, in a separately authorized cleanup, durable manually maintained
background: project purpose, stable terminology, durable architectural philosophy, and directions
to authoritative current state. Volatile stage/task/test-count/current-capability claims should be
removed rather than generated into that file.

`PROJECT_STATE.json` is not restructured by this architecture. Compatibility-first evolution is:
consume it unchanged; prove deterministic reconstruction of narrow current facts; migrate bootstrap
consumers only after the projection is stable; separately authorize any later reduction of duplicated
historical narrative.

`IMPLEMENTATION_QUEUE.md` remains authoritative and historically complete. The context system
adapts to its existing row convention and provides narrow projections; queue restructuring is not a
Self-Context prerequisite.

### 13. Bootstrap and CI adoption

Existing `AGENTS.md` / `AI_BOOTSTRAP.md` repository-first rules remain authoritative. A later,
separately authorized adoption may let bootstrap read the Current Context Manifest first for cheap
orientation, but consumers must retain a path to authoritative sources and expand/verify them when a
decision requires it.

Conceptual future commands may separate generation from verification (for example, `context build`
and `context check`), but T128 does not define command names or implement CI. CI freshness
enforcement and committed-artifact synchronization are explicitly later concerns.

### 14. Security and trust boundary

The deterministic source set is allow-listed repository content, not arbitrary local files,
environment variables, credentials, build output, or network responses. The foundation must not
ingest secrets or machine-specific state into canonical output.

Repository text is evidence, not executable instruction to the derivation engine. Parsers must
treat paths and content as data, prevent traversal outside the repository/source allow-list, and
bound parsing/resource use. Generated text is untrusted presentation for downstream agents; it must
not be treated as commands or permission.

Local Git metadata may identify repository state but must not cause network fetches implicitly.

### 15. Versioning and consumer behavior

Start with a simple major-versioned schema. Additive fields within a supported major version may be
ignored by tolerant consumers. A consumer encountering an unsupported major
`context_schema_version` must fail closed rather than guess field meaning.

Changes to derivation semantics that can change a fact without changing source inputs increment
`derivation_version`. Changes to the authoritative source set/parsing contract increment
`source_set_version`. Canonical ordering is part of the serialization contract, not authority.

### 16. First later implementation slice

The smallest later implementation slice is **Deterministic Current-Context Manifest Foundation**:

- a versioned manifest model/schema;
- repository identity and source-commit identity;
- shared/extracted deterministic governance parsing needed for latest Authorized/Done,
  in-progress transitions, ADR numbering/status, and Required-ADR resolution;
- cross-checks against the existing governance ledger without making that ledger authoritative;
- minimal hybrid provenance;
- explicit invalid/conflict diagnostics and non-zero failure;
- deterministic canonical JSON serialization;
- focused unit/governance regression tests.

It explicitly excludes task packages, human-readable rendering, bootstrap cutover,
`PROJECT_STATE.json` or queue restructuring, stale-document cleanup, GitHub API/network evidence,
LLMs, automatic decisions, application/domain/database work, and CI freshness enforcement.

Shared parser extraction is part of this slice only to the extent required to avoid duplicating
existing semantic parsing; broad refactoring remains deferred.

## Reasoning

The selected architecture reduces context-consumption cost without weakening the repository-first
model. Keeping authority in existing artifacts makes the projection safely disposable. Determinism,
source identity, and fail-closed conflicts make it auditable. Reusing shared semantic derivation
prevents the context system and governance validator from drifting into contradictory definitions.
Starting on demand avoids creating the very stale-state problem the subsystem is meant to reduce.

## Trade-offs

- Consumers still need to follow provenance for high-stakes decisions; the manifest is an index, not
  a substitute for evidence.
- Initial implementation must carefully separate reusable derivation logic from validator
  presentation without changing validator semantics.
- Offline generation cannot prove live GitHub state; that limitation is explicit rather than hidden.
- Keeping existing large governance files unchanged preserves compatibility but does not immediately
  reduce repository size.
- Fail-closed conflict handling may make context unavailable exactly when governance is inconsistent;
  that is preferable to publishing a plausible but false current state.

## Future Impact

A later, separately authorized implementation can build the Current Context Manifest foundation
described above. After it proves stable, separate tasks may consider task packages, bootstrap
integration, durable-background cleanup of `docs/Context.md`, human-readable rendering, and
optional CI checks.

This ADR does not authorize any of those tasks, does not select the next task, and does not change
application, database, migration, Required-ADR, or ADR-0036/ADR-0037 state.
