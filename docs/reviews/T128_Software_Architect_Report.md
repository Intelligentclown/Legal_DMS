# T128 Software Architect Report

**Task:** T128 — Self-Context Projection Architecture and Authority Contract.  
**Role:** Software Architect.  
**Artifact:** `ADR/0038-self-context-projection-authority-contract.md`.  
**Status:** Architecture draft for step 2 of the `PROJECT_WORKFLOW.md §3.1` lifecycle. No QA
Decision, merge, closeout, or implementation is performed by this report.

## 1. Verified baseline and authorization

Fresh remote inspection found `origin/main` at
`67e0e7d0942c494281a1a15593d9ce992bb779ae`, the merge of authorization PR #225. The merge
commit's first parent is the prior T127 main
`498bb553eb629d4211e212cc44f072f07a8580c9`; its authorization-side parent is
`80542e6fc9f8c66e753fb0fd63100987e036d793`.

The merged T128 row records Project Owner authorization dated 2026-09-21. Starting governance is:
`latestTaskDone = T127`, `latestTaskAuthorized = T128`, `inProgressTransitions = []`;
ADR-0036 and ADR-0037 remain Proposed; Required ADR #20 remains unresolved; T129+ is unauthorized.

The architecture branch was created from the exact authorization merge.

## 2. Authorization boundary

T128 permits architecture only: authority/source mapping, projection/non-authority semantics,
Current Context Manifest contract, provenance/discrepancy/fail-closed semantics, determinism and
input identity, generated-vs-on-demand strategy, validator/parser relationship, context layering,
future roles of `docs/Context.md` and `PROJECT_STATE.json`, offline/network and no-LLM
boundaries, automatic-decision prohibition, and decomposition of the smallest later implementation
slice. It permits at most one new Proposed ADR if needed.

It excludes compiler/manifest implementation, generated artifacts, task packages/renderers,
governance-file restructuring, bootstrap cutover, stale-doc cleanup, CI freshness enforcement,
GitHub API/LLM integration, application/domain/database work, Required-ADR resolution,
ADR-0036/0037 status changes, T128 closeout, and T129+ authorization.

## 3. Repository evidence inspected

The architecture pass inspected the current versions of `AGENTS.md`, `AI_BOOTSTRAP.md`,
`docs/AI_EXECUTION_ROUTING.md`, `PROJECT_WORKFLOW.md`, `PROJECT_STATE.json`,
`IMPLEMENTATION_QUEUE.md`, `docs/Context.md`, `docs/ProjectStatus.md`,
`PROJECT_CHECKPOINT.md`, `docs/GOVERNANCE_VALIDATION.md`,
`scripts/governance_validate.py`, the Software Architect prompt, documentation ownership rules,
the ADR template, ADR-0036, ADR-0037, and prior Software Architect/QA lifecycle precedent.

## 4. Re-established problem

The motivating problem is confirmed and is not file-size-only. The queue and state artifacts mix
current facts with substantial historical material, while task-scoped executors generally need a
small frontier plus one task's evidence. More importantly, manually maintained volatile context is
stale:

- `docs/Context.md` still says Stage 0 is the only completed stage, that no Matter/Client/Property
  concepts exist, backend application/domain/repository layers are empty, no business features
  exist, and no Stage 1 plan exists.
- `AI_BOOTSTRAP.md` remains structurally useful but still says the project has zero business logic
  and no repositories/services/routes touch the schema, despite the current Party surface.
- `PROJECT_CHECKPOINT.md` is explicitly historical around T80/T82 and still describes T82 as the
  next unauthorized cycle.
- `PROJECT_STATE.json` contains a mechanically useful governance ledger but also very long
  chronological narrative; its `asOfCommit` convenience value is older than current main.
- `IMPLEMENTATION_QUEUE.md` is both the authoritative numbered-task ledger and a historical
  execution archive.

This confirms high recoverability but growing retrieval-density and volatile-freshness risk.

## 5. Existing authority and validator findings

Repository rules already establish that `IMPLEMENTATION_QUEUE.md` is the sole authoritative
numbered-task ledger; ADRs own architecture; the governed Domain Model & Functional Specification
owns frozen domain/business baseline; QA/review artifacts record QA; `PROJECT_STATE.json` is a
point-in-time synchronization document whose `governanceLedger` is explicitly derived rather than
a second source of truth.

`scripts/governance_validate.py` already implements deterministic task-row parsing, duplicate-ID
checks, authorization/Done heuristics, latest frontier derivation, ADR numbering, `Resolves:`
parsing, Required-ADR state derivation, dangling-reference checks, and bounded transition
validation. Its own documentation explicitly says it does not prove Git ancestry or business
correctness. T128 preserves that epistemic boundary.

## 6. Why a new ADR is required

Existing bootstrap/governance documents describe repository-first behavior and validator
boundaries, but no existing ADR defines the authority status of generated context, source
precedence, provenance vocabulary, conflict/fail-closed behavior, determinism/input identity,
schema/derivation/source-set versioning, generated-vs-on-demand strategy, shared-parser invariant,
or automatic-decision prohibition.

Those are durable architectural constraints on a future subsystem. `AI_BOOTSTRAP.md` requires
significant architecture to be recorded as an ADR. The next repository ADR number is mechanically
0038: ADR-0037 is the current highest numbered ADR and no ADR-0038 exists on the authorization
baseline.

Therefore ADR-0038 is warranted and remains Proposed.

## 7. Architecture decision summary

ADR-0038 selects an on-demand, deterministic, repository-local **projection**, not a cache that can
become authoritative and not a committed state ledger. Canonical output is disposable and
regenerable.

Authority remains in existing repository evidence. The first manifest is intentionally small:
identity/version fields, governance frontier, Required-ADR/relevant ADR state, recorded active
authorization, provenance, and deterministic discrepancies.

Canonical determinism is “same authoritative repository state + same schema/derivation/source-set
contract => same logical output.” `generatedAt` is excluded from canonical output.

The provenance model is hybrid and uses mechanically defined classes:
`mechanically_verified`, `repository_derived`, `git_verified`, `qa_recorded`,
`documented`, `unverified`, and `conflicting`. There are no AI confidence scores.

Discrepancies are `stale`, `conflicting`, `unsupported`, `invalid`, or `unverified`.
Conflicting/invalid authoritative inputs fail canonical generation non-zero; stale
non-authoritative narrative can warn; unsupported values are omitted/labelled; unverified values
remain explicitly unverified.

The deterministic core is offline and no-LLM. Live GitHub evidence is a later, separately
provenanced concern.

Long term, shared governance facts must come from one semantic parser/derivation layer consumed by
both governance validation and context projection. The first implementation may extract only the
small units it needs; no broad parser refactor is required first.

The layered future is Current Context Manifest → later Task Context Package → later human-readable
rendering. Only the Current Context Manifest is the first implementation candidate.

`docs/Context.md` should later become durable manually maintained background with volatile current
state removed. `PROJECT_STATE.json` and `IMPLEMENTATION_QUEUE.md` remain unchanged and
authoritative/compatible during the foundation.

## 8. First later implementation decomposition

Recommended later slice, without authorization:

**Deterministic Current-Context Manifest Foundation**

In scope:
- versioned manifest model/schema;
- repository/source-commit identity;
- minimal shared governance parser extraction;
- latest Authorized/Done and in-progress transition derivation;
- ADR numbering/status and Required-ADR resolution derivation;
- ledger cross-checking without granting ledger authority;
- minimal provenance;
- invalid/conflict diagnostics with non-zero failure;
- deterministic canonical JSON;
- focused unit/governance regression tests.

Out of scope:
- task packages;
- human-readable rendering;
- bootstrap cutover;
- `PROJECT_STATE`/queue restructuring;
- stale-doc cleanup;
- GitHub API/network;
- LLMs;
- automatic recommendations/authorization/QA/ADR decisions;
- application/domain/database work;
- CI freshness enforcement.

Advisory executor classification: **Codex**. The mechanics are bounded Python/parsing work, but
authority-integrity and regression consequences are high enough that a strong repository-aware
executor is preferable. This is advisory only and authorizes nothing.

## 9. Security and versioning

Canonical sources must be allow-listed repository content; no environment variables, credentials,
arbitrary local paths, build artifacts, or implicit network data. Repository/generated text is data,
not executable instruction. Local Git inspection must not trigger network access.

Consumers fail closed on unsupported major context-schema versions. Additive fields within a
supported major may be ignored by tolerant consumers. Derivation and source-set versions change
independently when semantic rules or participating sources change.

## 10. Exact architecture files

This Software Architect pass adds exactly:

- `ADR/0038-self-context-projection-authority-contract.md`
- `docs/reviews/T128_Software_Architect_Report.md`

No implementation, generated context, parser refactor, workflow/bootstrap change, governance
closeout, application code, schema, migration, database operation, or stale-doc cleanup is included.

## 11. Validation and QA boundary

Required architecture validation is governance validation, governance-validator regression tests,
report mode confirming Required-ADR state is unchanged, `git diff --check`, and final diff/scope
inspection. The branch is then published for independent QA.

This report renders no QA Decision.

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

The unchecked test items reflect an architecture-only artifact; the existing governance-validator
suite is a validation gate, not new T128 implementation testing. AI_BOOTSTRAP and PROJECT_STATE are
deliberately unchanged by authorization scope.

## QA Decision

```text
□ Approved
□ Approved with comments
□ Rework required
```

STOP for independent QA.
