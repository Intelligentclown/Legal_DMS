# ADR-0045: Protected-Merge Completion and Post-Merge Governance Closeout

**Status:** Proposed
**Date:** 2026-10-18
**Task:** T158
**Resolves:** None
**Scope:** Repository governance only; ordinary PROJECT_WORKFLOW.md §3 and distinct §3.1

## Context and authority

T156 introduced a prospective delivery calendar (T157 onward): Done means protected-merge completion, with actual dates, signed variance, classification and append-only forecast history. Ordinary §3 presently places Documentation Manager synchronization after independent QA but before implementation PR merge. The future merge event cannot be truthfully recorded at that point; validators reject Done without actuals. T157 PR #296 is QA-reviewed and frozen but unmerged. No task may be declared Done based on QA or anticipated merge.

Authoritative order: GitHub protected merge record (PR merged_at, merge_commit_sha and ancestry) for integration event; IMPLEMENTATION_QUEUE.md for task authorization and durable Done declaration; docs/delivery_calendar.json for schedule and completion facts derived from that event; QA review artifact and exact remote candidate for QA; PROJECT_STATE.json for derived snapshot, not competing task authority. ADRs and workflow define policy, not actual occurrence.

## Decision: ordinary §3 split into pre-merge readiness and post-merge closeout

Adopt an additional, dedicated protected **completion-closeout PR** for T157+ ordinary §3 tasks. This is the smallest robust approach preserving immutable protected-merge evidence and existing validation without pretending the implementation PR's future merge has occurred. No new numbered task state or schema enum is required. Operational phases **QA-approved / merge-ready**, **implementation merged / closeout pending**, and **Done / closeout merged** are derived from independently verifiable evidence, not new queue status tokens. A separate PR is required because a merged implementation PR cannot subsequently modify itself and direct writes to protected main are forbidden.

The ordinary §3 prospective sequence is:
1. Project Manager: authorize task and calendar plan in protected authorization PR; commission separate roles.
2. Implementer: create implementation candidate and log; no Done claim.
3. Independent QA: review exact frozen candidate, publish decision to implementation PR branch and independently verify publication. Rework blocks progression.
4. Documentation Manager (pre-merge): synchronize implementation/QA descriptions, handover, release notes as applicable **on implementation PR**; leave queue task Authorized and calendar completion actuals null; do not append completion history or advance latestTaskDone. May document 'QA-approved, pending protected merge' without creating a Done marker. Validate with pending-state checks.
5. Git/CI PR Manager: verify latest remote head, exact-head required CI, independent QA/reviews, all active classic/ruleset protections, resolved threads, ancestry, branch, base, scope and mergeability. Use protected merge endpoint with expected head; never bypass. Record PR number, merge SHA and GitHub merged_at. STOP on stale/failed/uncertain result; re-fetch instead of assuming success.
6. Project Manager / Control Tower: independently verify merge record, protected main ancestry, and commission Documentation Manager for completion closeout.
7. Documentation Manager (post-merge): branch from current protected main; create **closeout-only PR** updating task row with the exact 'TNN is now Done' marker and QA/authorization/merge evidence; set calendar actuals and append forecast history; synchronize PROJECT_STATE governanceLedger and documentation as required. No product code or QA edits. Do not merge own PR.
8. Independent QA: separately review closeout PR for factual GitHub evidence, calendar arithmetic, scope and consistency; publish QA artifact, verify remote head.
9. Git/CI PR Manager: separately protected-merge closeout PR after fresh exact-head gates. Control Tower independently verifies; only then is task durably Done.

The implementation merge is **technical completion** and the event supplying the actual completion date; the closeout merge is **governance finalization**. The task's durable Done state exists only after closeout PR merge, but its calendar actual_completion is the earlier implementation merge's project-local date, never the closeout merge date. This distinction avoids circularity.

§3.1 remains its already authorized **three-PR** lifecycle (authorization, architecture/QA, governance closeout). Its PR 3 derives protected completion evidence from PR 2's protected merge; no fourth PR is introduced. T158 itself follows §3.1. This ADR is a proposal until independently QA-reviewed and protected-merged through T158 PR 2 and closed out through PR 3.

## Calendar algorithm and provenance

Use the canonical GitHub PR merged_at UTC timestamp, converted into the repository's explicitly configured project-local time zone (India/Asia-Kolkata if confirmed by implementation authority; do not infer from operator workstation). Store/describe the original UTC timestamp, PR URL/number, merge commit SHA, source branch/head SHA and timezone conversion in auditable closeout narrative or supported provenance fields. Validate merge SHA reachable from protected main and that it integrates the approved candidate. If timestamp, timezone, or ancestry cannot be established, STOP rather than substitute commit author date, QA date, closeout date or current clock.

actual_start: existing repository-defined evidenced work start, not authorization date by default; if evidence cannot establish it, STOP for reconciliation. actual_completion: local date of implementation protected merge. actual_elapsed = (actual_completion - actual_start).days + 1 (inclusive), requiring nonnegative. Preserve original planned_start and planned_finish. variance_days = (actual_completion - original planned_finish).days, signed. Negative Early; zero On Time; positive Late. Keep task forecast fields distinct from original plan and immutable actuals.

At the **post-implementation-merge closeout**, recompute dependency-constrained task and milestone forecasts once using the newly completed task actuals. Preserve fixed milestone targets as baseline; record for each affected milestone including unchanged outcomes old forecast, new forecast, signed movement, direction, trigger task/PR/merge SHA, rationale, recalculation date, and explicit completeness/confidence limits. Append to history, never overwrite; avoid double-appending on retries by stable trigger key (task ID + implementation merge SHA + milestone). If the dependency graph is incomplete, retain provisional M1 2026-11-15, M2 2026-12-31, M3/final 2027-02-28 unless supported evidence requires movement; record unchanged with honest uncertainty rather than claim full critical-path calculation.

The T158 calendar edge T157 -> T158 is a **defect-evidence reference**, not an executable finish-to-start prerequisite. The current generic dependencies field cannot express that distinction without risk of logical circularity (T157's completion requires T158). Governance implementation must introduce an explicitly typed non-scheduling evidence relationship or a narrowly documented exception, preserving authorization history and removing that edge only from scheduling topology, not deleting provenance. T156 is the scheduling predecessor. Validators must distinguish scheduling edges from evidence edges and reject true scheduling cycles.

## Validation and compatibility requirements

For T157+ ordinary tasks, enforce: (a) Authorized + QA-approved + unmerged implementation PR permits null completion actuals, no Done marker and no completion history; (b) implementation merged + closeout pending likewise remains queue Authorized, with merge evidence externally verifiable and a mandatory pending-closeout operational alert/report; (c) Done marker requires QA evidence, protected implementation merge proof, nonnull complete actuals, consistent signed variance/classification, one idempotent history trigger, matching derived PROJECT_STATE ledger and a protected closeout PR; (d) reject fabricated merge dates, conflicting merge SHA, stale base/head, duplicate history, missing provenance, unsupported scheduling cycles and inconsistent snapshot. Validators must not require an unmerged PR to have future actuals. Preserve T1–T155 historical records and exempt T156 bootstrap; do not backfill dates or reinterpret old Done declarations. Existing schema v1 fields and tests remain valid until separately approved implementation explicitly evolves them.

Validator should mechanically check repository-local evidence and optionally verify remote GitHub merge provenance via a clearly distinguished CI/online verification step; offline validation must not falsely claim remote proof. If network unavailable, require a signed/auditable recorded merge evidence tuple and flag remote verification pending for Git/CI gate, not silently certify.

## T157 recovery

Keep PR #296 frozen at b6c4158b23744390dcc284010cff6aec8d59dd75; do not merge until T158 PR 2 architecture/QA protected merge and PR 3 protected closeout make this policy effective. Reconcile its pre-merge Documentation Manager changes with the new contract without modifying product code or repeating already valid Independent QA. Verify exact QA-covered implementation tree, any documentation-only descendant, CI and protections; re-review only if candidate code changes or QA authority requires it. Then Git/CI PR Manager protected-merges #296; independent Control Tower verifies merge and timestamp; Documentation Manager opens a new T157 completion-closeout PR, deriving actuals from real GitHub evidence and recalculating forecasts; independent QA and protected merge follow. Do not mark T157 Done or fill actuals before #296 actually merges.

## Failure, retry and reconciliation

Merge request fails: PR stays open; no completion mutation. Ambiguous response: fetch PR and protected main; only confirmed merged_at and merge SHA permit closeout. Main drift: refresh baseline and rerun affected gates; never force or bypass. Closeout PR fails CI/QA: leave task Authorized and technical merge intact, fix only closeout artifacts and rerun independent gates. Concurrent closeouts: serialize or rebase from fresh main, recompute derived ledger and history, retain one event per merge key. Partial calendar/queue/state edits: validator fails atomically; repair in same closeout PR, never assert Done with missing actuals. Historical discrepancy: preserve evidence, report to Control Tower, obtain scoped reconciliation authorization; no guessed dates.

## Alternatives considered

- Pre-merge Done/estimated actuals: rejected as fabricated and validator-incompatible.
- Post-merge direct main mutation: rejected by protected-branch rules.
- GitHub Actions bot direct commit: rejected unless a separately authorized protected-PR mechanism preserves independent review and role boundaries; greater complexity.
- New intermediate queue enum: unnecessary; phase is derivable from PR evidence and introduces migration/validator overhead.
- Keep all governance changes pre-merge and only annotate externally: cannot persist Done calendar actuals in protected repository.
- Dedicated post-merge closeout PR: selected; costs one extra protected review/CI cycle but is deterministic, auditable and least disruptive.

## Acceptance/test matrix for subsequent implementation

1. QA-approved unmerged ordinary candidate validates with null actuals and Authorized row.
2. Pre-merge Done or nonnull completion date fails.
3. Protected implementation merge plus pending closeout remains Authorized and is reported.
4. Done without merge evidence, QA, actual_start, completion, elapsed, variance, classification or matching ledger fails.
5. Date boundary UTC -> project-local conversion, leap day, inclusive duration, negative/zero/positive variance tested.
6. Forecast history includes unchanged milestones, correct trigger, no duplicate on retry; original planned finish immutable.
7. Incomplete graph retains provisional forecasts with uncertainty; evidence-only T157 reference does not form scheduling cycle.
8. Stale exact head, missing review, failed CI, merge conflict or unverified classic/ruleset protection STOP.
9. Concurrent closeout and partially synchronized state fail safely, recover by rebase/reconciliation.
10. §3.1 remains exactly three PRs; T1–T156 compatibility and T157 no-product-change recovery verified.

## Boundaries

No Required ADR #[12,15,16,17,20] is resolved; repository ADR-0020 is unrelated to Required ADR #20. ADR-0044 remains Proposed/Resolves None. No Alembic migration; frontier b155caa6d4e1. No T157 implementation or QA modifications, no T159+ authorization, no branch-protection relaxation.
