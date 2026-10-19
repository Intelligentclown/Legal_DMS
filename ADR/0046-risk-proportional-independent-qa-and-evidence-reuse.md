# ADR-0046: Risk-Proportional Independent QA and Evidence Reuse Architecture

**Status:** Proposed  
**Date:** 2026-10-19  
**Task:** T161 — QA Proportionality & Evidence Reuse Governance  
**Resolves:** None  
**Scope:** Prospective QA governance architecture under `PROJECT_WORKFLOW.md §3.1`. Not yet executable QA policy.

## Problem

Current `docs/AI_EXECUTION_ROUTING.md §7` permits risk-scaled verification depth while always requiring an independently commissioned QA Reviewer, formal remote QA publication, fresh applicable CI, eligible collaborator approval, resolved review conversations and protected merge. Repeated wholesale review of a candidate whose previously QA-covered behavior remains byte-identical after a governance-only integration consumes effort without necessarily increasing assurance. T157's original QA, controlled integration and focused follow-up demonstrate both the possible savings and the need to reverify effective changes rather than trust a stale verdict. T151 established bounded context and QA role independence; T158/ADR-0045 and T159 established distinct protected implementation completion and closeout provenance. The architectural question is how to decide verification *depth*, evidence applicability and escalation deterministically without creating a self-approved QA waiver or retroactively changing T160 PR #306.

## Options Considered

1. **Re-run comprehensive QA on every remote-head change.** Simple and conservative but duplicates proven-unchanged tests and review work on QA-artifact-only, documentation-only and safely reconciled candidates; still does not substitute for fresh exact-head CI.
2. **Automatically waive QA on low-risk changes / accept any previously green checks.** Rejected: violates mandatory independent role, remote-publication and merge gates, ignores environment and contract drift, cannot prove candidate equivalence.
3. **Independent risk-proportional evaluation with evidence lineage and narrow proposed evidence-only depth. Selected as architecture.** Classification is justified by effective changed files, invariant/contract impact, baseline integration and evidence freshness. Reviewer retains unconditional escalation authority. The evidence-only tier is **not operative** until a separately authorized, independently reviewed and protected governance-enforcement change explicitly adopts it.

## Decision

### 1. Scope, authority and precedence

Maintain the *existing* risk-scaled QA depth immediately: focused review may already be used where appropriate, with all current mandatory stages intact. Evidence reuse is a reasoned input to fresh independent verification, not an approval proxy. **Comprehensive** and **focused** are permitted depth choices within existing rules; **evidence-only** is a newly proposed, narrowly scoped future depth choice, not an operative classification and never a waiver of the QA Reviewer or decision publication. The reviewer may reject any proposed reuse, expand tests or demand comprehensive QA, with documented risk rationale; the implementer, architect, project owner, CI bot and PR manager cannot assign a binding lower tier. Stop on conflicting authoritative policy instead of interpreting this proposed ADR as a rules amendment.

### 2. Provenance model and immutable identities

For every reviewed candidate record: repository/task/authorization PR and protected authorization merge SHA; protected base SHA; implementation PR/branch; immutable reviewed **implementation commit SHA** (the code/tree snapshot before QA publication); candidate Git tree SHA where available; full effective three-dot base-to-candidate diff and changed-path classifications; commit graph and merge-base ancestry; relevant contract/invariant identifiers; evidence source task/PR and original QA-reviewed SHA; exact QA decision and publication commit SHA, publication parent SHA, remote final PR head SHA and its verified QA-commit ancestry. If an integration merge exists, record both ordered parents and its effective changed-path inventory. Identify freshness against current protected main separately from original authorization ancestry. For reused evidence, compare content blob hashes of each covered artifact and the complete transitive impacted contract/invariant surface, not merely matching filenames or successful cherry-pick. Record test command, run ID, environment/DB revision/dependency lock, results, limitations and UTC timestamps. Never present the post-QA publication head as the original implementation candidate when they are distinct.

An unchanged blob alone is insufficient: changes in callers, shared libraries, migrations, settings, permissions, CI configuration, generated contracts, integration environment or assumed invariants can invalidate earlier conclusions. CI evidence is tied to exact checked revision and required GitHub check suite; a passing run for an older SHA does not become fresh exact-head CI.

### 3. Entry classification and decision matrix

| Effective risk / change | Minimum independent verification depth | Reuse eligibility | Mandatory action |
| --- | --- | --- | --- |
| New or modified tenant isolation, RLS, RBAC/authz/authn, cryptography, secrets, migrations/schema, transactions, concurrency, storage, data integrity, trust boundaries or security-critical dependencies | **Comprehensive**, for affected high-risk subsystem and relevant integration/failure boundaries (not automatically unrelated whole-repository replay) | Previously approved evidence may inform regression baseline, never substitute for validating affected invariants | Deep adversarial/negative, rollback, cross-tenant and integrity testing as applicable; STOP if environment cannot exercise required safeguards |
| Product/application behavior, API/contract, frontend permissions/actions, integration wiring, test logic, dependency/runtime/config or security-sensitive CI changes | **Focused or comprehensive**, sized by actual impact; escalate on uncovered cross-boundary risk | Only provably unchanged, independent sub-surfaces with no transitive contract changes | Fresh impacted tests and negative/regression checks; review test adequacy; comprehensive on high-risk impact |
| Pure documentation, comments, governance status/ledger/calendar or QA-artifact publication with unchanged product/test/contract behavior | **Focused** under today's rules; **proposed evidence-only** only if all §4 conditions pass after future adoption | Can cite prior QA for unchanged behavior, but verify provenance, semantics and cross-references afresh | Fresh current-head required CI, independent QA Decision/remote publication, review and protected merge |
| Merge/rebase/main advance with originally reviewed product/test blobs unchanged | **Focused integration** under today's rules; evidence-only only prospectively if all §4 conditions pass | Per-file hash equality plus no semantic effect from intervening commits, effective diff/ancestry check | Check merge parents, intervening changes, dependencies/contracts, exact-head CI and compatibility; escalate if uncertain |
| Conflicting, missing, stale, unverifiable, partially failed evidence or candidate mutation after QA | **Focused minimum; comprehensive when risk/impact is unknown or high** | Not eligible for evidence-only | Reject reuse, obtain fresh evidence and independent re-review before merge |

The tier is a *floor*, not a ceiling; critical cross-boundary impact always raises it. A security-sensitive area cannot be downgraded solely by a small diff, “docs-only” label, previous approval or a green CI check. Test-only changes can weaken assurance and require genuine review of test correctness and unchanged production behavior.

### 4. Proposed evidence-only admission test (all conditions required)

(a) Separately adopted governance policy enables this tier for the class of PR; (b) a separately commissioned independent QA Reviewer positively elects it with written reasons; (c) task/authorization and protected-base ancestry are independently checked; (d) entire effective diff and all intervening main changes are enumerated and confined to non-behavioral review/provenance/governance material; (e) original production and test blob identities match, including relevant generated/runtime artifacts; (f) no affected invariant, interface/contract, dependency, environment, authorization, migration or cross-task integration changes; (g) prior QA is formally Approved or Approved with comments with zero unresolved blocking findings, is remotely published and tied to an immutable original SHA; (h) previous tests and limitations still apply to unchanged behavior; (i) all fresh required checks for the current head pass, review conversations resolve and an eligible collaborator approves that head; (j) new Independent QA decision is published on the actual PR branch and reread from remote head. Where QA publication itself advances HEAD, reread and verify its sole diff, publication parent, freshness and required checks/approval on the final head under current branch protection. No circular assertion that QA approves its own unchecked publication head.

**Any missing condition disqualifies evidence-only.** Default to focused verification, or comprehensive where missing evidence affects high-risk or unknown behavior. Recording a justification cannot manufacture evidence. An evidence-only review still independently checks authority, provenance, changed-file scope, invariant mapping, prior QA chain, applicability, governance consistency and actual current-head checks; it is not a rubber-stamp.

### 5. Change taxonomy and re-review triggers

- Product, backend/frontend source, migrations, security settings, models, persisted state, API schemas, generated interfaces or runtime dependencies: new impact analysis and appropriate focused/comprehensive QA; high-risk entries always comprehensive.
- Tests/fixtures/mocks: audit assertions, non-vacuity, affected behavior and regression; rerun relevant tests. Deleted tests or weaker assertions never qualify as evidence-only.
- Integration merge/rebase: verify exact merge-base, ordered parents, complete incoming commit changes, content-hash equality and contract compatibility; no inherited blanket approval.
- QA artifact or review-only commit: verify publication-only diff, original candidate ancestry, verdict accurately bound to reviewed SHA, and remote reread. No new product behavior is assumed merely from this review artifact.
- Documentation-only changes: inspect whether normative workflow, permissions, contracts, calendar, authorization or ADR status changed. Substantive governance/policy change requires independent design review and relevant validators; “.md” extension does not prove low risk.
- Governance metadata (queue, project state, delivery calendar, ADR references): independently check consistency, protected merge provenance and parser/validator outcome. A change to validator/CI/ruleset itself is **not** evidence-only.
- Any new blocking finding, materially changed diff, environment/lockfile, unexplained base drift, failed check, dismissed collaborator review or unresolved thread: freeze merge, reclassify and re-review as needed.

### 6. Audit record / evidence ledger (conceptual, not yet a schema)

Each QA publication includes (1) task and PR authority; (2) selected classification and reasons, alternatives and disqualifier checklist; (3) original implementation SHA, effective diff inventory, base/merge-base/ancestry, intervening commits and QA-publication head; (4) evidence reused by immutable QA artifact commit, original reviewed SHA, test run IDs and blob/contract equality results; (5) changed-to-invariant/test mapping and explicit excluded areas; (6) fresh execution/check IDs, pass/fail/environment limitations; (7) escalation/decision authority, blocking vs nonblocking findings and unresolved risks; (8) independently published Approved / Approved with comments / Rework required decision with remote reread; (9) final exact-head collaborator/protection verification to be performed by Git/CI PR Manager. An absence must be recorded as an absence, not as an assumed pass. Existing `docs/reviews/` remains decision authority; a future typed manifest is a separately authorized implementation choice, not an invented second source of truth.

### 7. Worked decisions

- **Positive, focused today:** T157-like integration where previously approved application and test blobs are identical, 27 intervening commits are examined, no backend changes are found and fresh current-head CI is green. Focused independent integration QA can reuse the original high-depth behavior tests while checking new governance compatibility. Evidence-only would require future adoption and *all* admission conditions.
- **Positive, eligible prospectively only:** an added QA decision artifact whose only delta from frozen candidate is review text; original code/test blobs and contract graph identical, original independently approved evidence and ancestry verified. Independent QA still publishes a fresh decision and the new head still passes gates.
- **Negative:** one-line RLS or tenant predicate modification, even with unchanged endpoint contract: comprehensive tenant-crossing negative tests.
- **Negative:** apparently documentation-only ADR or workflow amendment changing who may merge: normative policy change, at least focused independent design verification; not evidence-only.
- **Negative:** existing test suite hash unchanged but shared auth dependency changes on protected main: previous coverage does not establish current invariant.
- **Negative:** PR adds only a test fixture reducing isolation or deleting assertion: test/evidence contract changed, focused/comprehensive review required.
- **Negative:** earlier QA Approved but a review thread remains unresolved, required check failed, reviewer approval dismissed, or branch head changed without fresh publication: block merge regardless of classification.

## Reasoning

Objective immutable identity, content-hash and invariant impact checks target repeated **work**, not mandatory checks or authority. A tier floor plus unconditional reviewer escalation prevents a “small diff” from concealing deep risk. Reusing T157-style evidence requires examining drift and compatibility rather than the hazardous shortcut of treating the old QA head as the new one. The existing remote publication and protected-merge protocol remains the final safety boundary.

## Trade-offs

The evidence map/metadata adds reviewer and tooling overhead and can be incomplete; full transitive equivalence is difficult to prove in a dynamic system. Conservative fallback intentionally sacrifices some efficiency. A prospective evidence-only tier risks social pressure for shallow reviews, countered through disqualifiers, reviewer veto, structured audit records, metrics and independent samples. Existing CI may not expose every environment change; the reviewer explicitly records gaps and escalates.

## Composition with repository authority

- **T151 / `docs/AI_EXECUTION_ROUTING.md`:** preserves its present risk-scaled focused/comprehensive review and one-role-per-assignment independence; proposes no bypass of fresh QA.
- **T157 QA + integration QA:** treats original reviewed SHA and later integration SHA as distinct; preserves blob-identity and effective-diff/CI rechecks rather than retroactive approval.
- **ADR-0045 / T158:** retains §3.1 PR 1 authorization → PR 2 architecture plus independent QA → PR 3 closeout; technical completion occurs only at protected PR-2 merge. Does not declare T161 Done.
- **T159:** retains exact protected-merge provenance, calendar, role and CI enforcement; this ADR does not mutate implementation validators.
- **Current QA Reviewer instructions:** preserves reviewer independent rejection, checked-box publication, remote HEAD reread and no self-repair.
- **T160:** PR #306 remains under currently operative QA rules. No T161 dependency, rule change, scheduling adjustment, reviewer replacement, inherited approval or retroactive evidence-only classification.

## Validator-semantic limitation

The existing `scripts/governance_validate.py` derives `governanceLedger.latestTaskAuthorized` from specific narrative wording (particularly “Authorized by the project owner”), rather than taking the queue's explicit `Authorized` status token as sole semantic authority. Consequently T160/T161 rows may be explicitly `Authorized` while the derived snapshot still says T159, and green current CI does **not** establish that narrative and structured authorization interpretations are equivalent. Authorization provenance used for evidence reuse must include direct queue row/status, owner authorization record, protected PR-1 merge and commit ancestry; the derived frontier field alone is insufficient. Record conflicting interpretations as an audit limitation and STOP if they affect eligibility. A **separately owner-authorized numbered governance-enforcement task** should define typed authorization semantics, migration/backward compatibility for existing historic rows, deterministic errors for narrative/status disagreement, positive/negative tests, and a protected review/CI rollout. Do not modify historical rows, validator, ledger or CI within T161 PR 2.

## Future Impact, implementation sequencing and validation

1. **T161 PR 2 only:** publish this Proposed ADR; Independent QA evaluates it as architecture under current rules; no operative tier change, validator change or QA waiver.
2. **T161 PR 3 only after protected PR-2 merge:** independently authorized Documentation Manager closeout and QA; accept ADR only through repository-governed closeout and record actual protected completion. No hidden adoption of evidence-only by merging this proposal.
3. **Separately authorize future governance enforcement** before enabling evidence-only: update authoritative workflow/QA Reviewer instructions and, if needed, typed evidence-manifest validation; derive evidence chain from immutable Git objects and GitHub checks with fail-closed checks; protect unaltered records and test mandatory publication. This implementation task should also separately consider (not opportunistically fix) the validator-semantic issue above.
4. **Positive tests:** doc-only, QA-publication-only and identical-blob integration with no contract drift; valid original QA chain; focused or prospective evidence-only justified case; current-head CI and review gates enforced.
5. **Negative tests:** one high-risk RLS/RBAC/migration/transaction/storage change; test assertion deletion; transitive contract/dependency drift; false blob match; wrong SHA/merge parent; stale original verdict; insufficient QA ancestry; missed auth wording; missing CI/review; unresolved thread; conflicting governance ledger; attempted retroactive T160 downgrade. Confirm rejected reuse and comprehensive escalation when appropriate.
6. **Metrics:** establish a baseline of reviewer time by risk tier, duplicate commands/tests rerun, proportion of evidence claims verified, fallback/escalation rate, reopened blocking defects and post-merge regression/incident rate, false-low-risk classifications and time from candidate freeze to QA publication. Measure within comparable risk classes before/after adoption; require independent periodic sampling, disclose small sample sizes and environment variance. Speed gains never override zero skipped mandatory reviews/checks; incident or misclassification increase triggers pause/reassessment.

**Open decisions:** whether to store a machine-readable manifest in `docs/reviews/` or derive from GitHub; approved evidence age/retention limits; independent reviewer sampling cadence; policy roll-out/rollback owner; portable environment-signature rules; scope and task identity for semantic validator correction. These must be resolved through separate authorization, not inferred from ADR acceptance.

**Boundaries:** no Required ADR #12/#15/#16/#17/#20 resolution; repository ADR-0020 differs from Required ADR #20. ADR-0044 status unchanged. No production code, Alembic migration, RLS/RBAC/auth/security, review automation, QA CI workflow, repository branch-protection modification, T160 implementation/QA or schedule edit. Migration frontier remains `b155caa6d4e1`.

## Software Architect self-assessment / QA handoff

Reviewer Checklist (architect self-assessment):
- ☑ Architecture preserved
- ☑ Existing design patterns followed
- □ Tests added (architecture-only; future enforcement tests expressly deferred)
- □ Existing tests pass (not asserted before GitHub Actions executes)
- ☑ Documentation updated (this proposed ADR only)
- ☑ ADR updated (if required)
- □ AI_BOOTSTRAP updated (not required; no operative rules change)
- □ PROJECT_STATE updated (not required; PR 3 only)
- ☑ No unrelated refactoring
- ☑ No scope creep
- ☑ Ready for Independent QA of architectural content

QA Decision (reserved exclusively for separately commissioned Independent QA):
- [ ] Approved
- [ ] Approved with comments
- [ ] Rework required
