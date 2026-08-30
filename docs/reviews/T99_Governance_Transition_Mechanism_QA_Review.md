# T99 Governance Transition Mechanism QA Review

**Task:** T99 — Governance Lifecycle / Required-CI Compatibility Remediation. This record covers
this task's actual authorized deliverable per `IMPLEMENTATION_QUEUE.md`'s T99 row (the "Approved
scope" paragraph): a generalized `governanceLedger.inProgressTransitions` mechanism that lets a
genuinely authorized, currently-in-progress Required-ADR transition pass the required Governance CI
gate during the deliberate window between an Architecture+QA PR merging (which adds the ADR file)
and its own later Governance Closeout PR (which syncs the ledger), while ordinary stale or
unauthorized governance drift continues to fail it — the nine numbered minimum requirements stated
in that row. This is distinct from PR #150's earlier CI job-name collision fix, which this record
does not re-litigate or treat as this task's deliverable (see "Relationship to PR #150" below).

**Authorization:** commit `1eef559d6f60988b46d899e61d36003c38e78cfa` (T99 authorization, built on
`90a5e1e`).

**Implementation:** commit `e200b7d3661a084f5477f88161d997da4278d7c6`, branch
`docs/t99-governance-transition-mechanism`, PR #151.

**Reviewed:** actual remote HEAD of PR #151 as returned live by `gh pr view 151` and confirmed via
`git rev-parse` against the fetched remote ref — identical to the reported implementation commit
`e200b7d`. Base confirmed identical to live `origin/main` (`a79a07ab5d10ccddf9e80219fe309df76e85a55d`,
itself PR #150's own merge commit). Diffs inspected: `git diff a79a07a..e200b7d` (file list) and
`git show e200b7d` in full (every hunk in all five files, including the complete
`validate_in_progress_transition()` function body). Live GitHub state inspected: `gh pr view 151`,
`gh pr checks 151`, `gh api .../commits/e200b7d/check-runs`, `gh api .../rulesets` and
`.../rulesets/21745493`, `gh pr view 148` (read-only, T98's own Architecture+QA PR). Local execution,
in an isolated detached worktree at `e200b7d` (to avoid disturbing this session's own checked-out
branches): `python scripts/tests/test_governance_validate.py -v` and
`python scripts/governance_validate.py`; `python -m pytest --version` re-confirmed unavailable in
this environment.

**Date:** 2026-08-29

---

## Topology verification

Before reviewing content, independently confirmed PR #151 cannot reproduce the earlier
reachability/merge-attribution class of problem referenced in the task brief:

- `origin/main` (`a79a07a`) **is** PR #150's own merge commit (`git log --merges -1 origin/main` →
  `Merge pull request #150 from Intelligentclown/ci/t99-required-check-naming`).
- PR #151's `baseRefOid` (`a79a07a`) is identical to live `origin/main` — not a stale or
  independently-diverged base.
- `git log a79a07a..e200b7d` shows **exactly one** commit ahead of that base — the implementation
  commit itself. No merge commit, no accumulated history from an unrelated branch.
- `git branch -r --contains a79a07a` lists only `origin/main` and
  `origin/docs/t99-governance-transition-mechanism` — no other open PR branch (in particular, no
  leftover PR #149-shaped branch) reaches back through this commit in a way that could cause
  ambiguous merge-base/reachability attribution on merge.

Topology: **clean** — PR #151 branches directly from current `main` post-#150, single commit, no
unrelated ancestry.

## Authorization and implementation ancestry

- `git merge-base --is-ancestor 1eef559d6f60988b46d899e61d36003c38e78cfa e200b7d3661a08...` —
  **succeeds**. T99 authorization is an ancestor of the actual PR HEAD.
- Implementation commit `e200b7d` **is** the actual PR HEAD (`headRefOid` from `gh pr view 151`
  matches exactly).
- `IMPLEMENTATION_QUEUE.md`'s T99 row (`grep -n "T99" IMPLEMENTATION_QUEUE.md`) independently read in
  full: its "Approved scope" paragraph states the nine minimum requirements verified individually
  below, and its "Explicitly outside scope" clause names exactly what this implementation must not
  touch — `PROJECT_STATE.json`; `T98`'s branch/PR/ADR/`ADR/0007`/`ADR/0009`/`ADR/0021`-`ADR/0028`;
  any schema/backend/frontend/Electron/API/migration change; `T100` authorization or creation. All
  confirmed absent from the diff (see Scope below).

## Relationship to PR #150

PR #150 (already merged into `main` as `a79a07a`, independently QA'd and approved in
[docs/reviews/T99_QA_Review.md](T99_QA_Review.md)) renamed three GitHub Actions job names to resolve
a check-*identity* collision against the `main-required-ci` ruleset's required contexts. That fix is
real and was independently verified at the time, but it is **not** the mechanism T99's own
`IMPLEMENTATION_QUEUE.md` row describes in its "Approved scope" paragraph — that paragraph is
entirely about the `governanceLedger`/in-progress-transition problem this PR (#151) solves. Per this
review's own instructions, PR #150's CI-naming work is treated as related infrastructure, not as
this task's authorized deliverable; this record evaluates PR #151 against the row's actual nine
stated requirements, not against PR #150's separate scope. This distinction is recorded here as a
non-blocking observation for whoever performs T99's eventual Governance Closeout, not as a defect in
either PR.

## Scope verification

`git diff --name-only a79a07a..e200b7d` (and, equivalently, `git show --stat e200b7d`, since the PR
is a single commit) — **exactly five files**, matching the row's "potential files" list minus the
two that inspection evidently found unnecessary (`.github/workflows/governance.yml`, and no
in-repository ruleset record exists to touch):

- `scripts/governance_validate.py`
- `scripts/tests/test_governance_validate.py`
- `docs/GOVERNANCE_VALIDATION.md`
- `PROJECT_WORKFLOW.md`
- `AI_BOOTSTRAP.md`

Independently confirmed absent from the diff: `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, every
`ADR/*` file, every `.github/workflows/*` file, any backend/frontend/Electron source path, any T98
file (`ADR/0029` and `docs/reviews/T98_Software_Architect_Report.md` both untouched), and no
`T100` row was added to `IMPLEMENTATION_QUEUE.md` (the file itself is not even in the diff). Directly
inspected the PR #151 worktree's own `PROJECT_STATE.json.governanceLedger` — unchanged from `main`,
`latestTaskAuthorized: "T99"`, `latestTaskDone: "T97"`, no `inProgressTransitions` field present
(correct: T99 is a tooling task, not itself a Required-ADR resolution with an ADR gap to declare).

**Scope: PASS.**

## Mechanism correctness

Independently read the full body of `validate_in_progress_transition()` and its call site inside
`check_governance_ledger()` in `scripts/governance_validate.py` (not summarized from the commit
message). Verified, against the actual source, each property the task brief asked for:

1. **Optional `governanceLedger.inProgressTransitions` declaration** — `ledger.get("inProgressTransitions")`; `None` → `([], None)`, ordinary behavior unchanged. Confirmed.
2. **At most one declaration** — `len(raw) > 1` → `governance-transition-ambiguous`, no exemption. Confirmed.
3. **Well-formedness required** — not-a-list, missing `task`/`requiredAdrs` keys, or non-dict entry all → `governance-transition-malformed`. Confirmed.
4. **Task must match `T\d+`** — `TRANSITION_TASK_ID_RE = re.compile(r"^T\d+$")`, checked via `TRANSITION_TASK_ID_RE.match(task)`. A generic pattern, not a literal comparison. Confirmed.
5. **`requiredAdrs` must be a non-empty integer list** — `not declared_raw or not all(isinstance(n, int) and not isinstance(n, bool) for n in declared_raw)`; the explicit `not isinstance(n, bool)` guard is notable — Python's `bool` is a subclass of `int`, so without this guard a JSON `true`/`false` element would silently pass as `1`/`0`. Confirmed, and defensively correct.
6. **ADR numbers in valid range** — `declared_adrs - set(REQUIRED_ADR_RANGE)` non-empty → `governance-transition-invalid-adr-state`. Confirmed.
7. **Task must be genuinely authorized per repository evidence** — looks up the matching `TaskRow` in the already-parsed `rows` list and requires `AUTHORIZATION_PHRASE in task_row.text`; a nonexistent or unauthorized task ID → `governance-transition-unauthorized`. Confirmed — sourced from `IMPLEMENTATION_QUEUE.md`'s own parsed text, not asserted.
8. **Task must equal the computed frontier** — `computed_latest_authorized = latest_task_number(rows, lambda r: AUTHORIZATION_PHRASE in r.text)`; `task != computed_latest_authorized` → `governance-transition-wrong-task`. Reuses the pre-existing `latest_task_number()` helper already used elsewhere in this file for `latestTaskAuthorized`/`latestTaskDone` drift checks — not new, parallel logic. Confirmed.
9. **Already-Done task rejected** — `f"{task} is now Done" in task_row.text` → `governance-transition-already-settled`. This reuses the exact literal marker convention (`f"{row.task_id} is now Done"`) already established and tested elsewhere in this same file (`check_done_requires_authorization`/`check_done_requires_qa_evidence`, lines ~147/170) — not a new, independently-invented string. Confirmed.
10. **`requiredAdrs` must equal exactly the real gap** — `actual_gap = resolved - recorded_resolved_for_transition; declared_adrs != actual_gap` → `governance-transition-scope-mismatch`. Read the call site: `recorded_resolved_for_transition` is computed from the ledger's *current* `resolvedRequiredADRs` before any exemption is applied, and `resolved` is the ADR-file-derived ground truth already computed by the pre-existing `compute_resolved_required_adrs()`. This is a genuine equality check, not a subset/superset check — confirmed by direct code reading, not merely by the docstring's claim.
11. **No exemption unless every condition passes** — every failure branch returns `(violations, None)` immediately; the single `return [], TransitionExemption(...)` at the bottom is reached only after all prior checks fall through. Confirmed by reading the full control flow, not sampled.
12. **`latestTaskDone` never exempted** — in the `latestTaskAuthorized`/`latestTaskDone` drift loop, the exemption `continue` is gated on `field_name == "latestTaskAuthorized"` specifically; no equivalent branch exists for `latestTaskDone` anywhere in the function. Confirmed by reading the loop in full, not inferred from the docstring.
13. **Ordinary drift detection not weakened** — the `resolvedRequiredADRs` check becomes `(recorded_resolved | exempt_adrs) != resolved` (union, not replacement) and `unresolvedRequiredADRs` becomes `(recorded_unresolved - exempt_adrs) != unresolved` (subtraction, not replacement). Both forms mean any drift *outside* the exact declared gap still trips the check — verified by hand-tracing a case with an extra, unrelated stale entry in `resolvedRequiredADRs`: since `actual_gap` (used for the *equality* check granting the exemption in the first place) would then include that unrelated ADR too, `declared_adrs != actual_gap` fails at the transition-validation step itself, denying the exemption entirely rather than partially masking it. This is the load-bearing design property and it is real, not merely claimed in the docstring.
14. **No reliance on git history, hard-coded task/ADR/PR numbers** — confirmed by full-diff reading: no `subprocess`/`git` calls anywhere in the new code; `TRANSITION_TASK_ID_RE` and `REQUIRED_ADR_RANGE` are both generic; the only task/ADR-specific string anywhere is the (pre-existing, reused) `"TNN is now Done"`/`"Authorized by the project owner"` phrase templates, which are format strings built from the *declared* `task`, not literals for any specific task.

No hard-coded `T98`/`T99`/`ADR-0029`/PR-number literal exists anywhere in
`validate_in_progress_transition()` — confirmed independently by `grep -n "T98\|T99\|0029"
scripts/governance_validate.py` restricted to the new function's line range, in addition to the
implementation's own `inspect.getsource`-based test (see Test coverage below).

**Mechanism correctness: PASS.** No bypass path, no weakened failure condition, no broad
exception-swallowing (`validate_in_progress_transition` contains no `try`/`except` at all — malformed
input is handled by explicit `isinstance`/shape checks, not by catching and hiding exceptions), no
accidental exemption of `latestTaskDone`, no acceptance of a superset/subset ADR declaration, no
acceptance of multiple declarations, no acceptance of a non-frontier or already-Done task.

## Test coverage

Independently ran, inside a detached worktree at the actual PR HEAD (not merely accepted the
implementation's own report):

```
python scripts/tests/test_governance_validate.py -v
```

Result: **49 tests, all pass** (35 pre-existing + 14 new — count matches the PR's own claim exactly,
independently re-run rather than taken on faith).

Read every new test body in `TestInProgressTransition`, not just its name, and confirmed each
actually exercises the claimed behavior via a specific `violations`/`check`-code assertion (not a
bare "did not raise"):

- `test_valid_in_progress_transition_passes` — asserts `violations == []` for a well-formed,
  currently-frontier, evidence-backed declaration.
- `test_valid_settled_state_with_no_declaration_passes` — asserts `violations == []` post-Closeout
  with no declaration present.
- `test_ordinary_drift_without_any_declaration_still_fails` — asserts
  `"governance-ledger-drift" in checks` with no declaration at all.
- `test_unauthorized_transition_fails` — asserts both
  `"governance-transition-unauthorized"` *and* `"governance-ledger-drift"` are present — proving the
  real drift is not silently excused by a failed declaration attempt.
- `test_malformed_transition_declaration_fails` — six distinct malformed shapes
  (missing `task`, missing `requiredAdrs`, invalid task-ID string, empty list, string-typed ADR
  number, float-typed ADR number), each independently asserted to produce
  `"governance-transition-malformed"`.
- `test_out_of_range_required_adr_fails` — asserts `"governance-transition-invalid-adr-state"`.
- `test_missing_evidence_fails` — asserts `"governance-transition-scope-mismatch"` when the declared
  ADR isn't actually resolved by any ADR file.
- `test_multiple_simultaneous_transitions_fail_safely` — asserts both
  `"governance-transition-ambiguous"` *and* `"governance-ledger-drift"` — again proving no partial
  masking.
- `test_transition_for_non_latest_authorized_task_fails` — asserts
  `"governance-transition-wrong-task"` for a stale, superseded authorized task.
- `test_transition_for_already_done_task_fails` — asserts
  `"governance-transition-already-settled"`.
- `test_mechanism_is_generalized_not_hard_coded_to_any_specific_task_or_adr` — asserts
  `violations == []` for arbitrary task `T777`/ADR `19` (never used elsewhere in the module or its
  tests), *and* independently asserts, via `inspect.getsource(gv.validate_in_progress_transition)`,
  that none of `"T98"`, `"T99"`, `"0029"`, `"ADR-0029"` appear in the function's own source — a
  structural proof, not a behavioral inference.
- `test_settled_state_after_transition_completes_is_strict_again` — asserts a clean post-Closeout
  state passes, *and* that a stale `resolvedRequiredADRs` persisting after `Done` still produces
  `"governance-ledger-drift"` — the transition-completion strict re-validation case.
- Two additional direct unit tests on `validate_in_progress_transition()` itself (absent-declaration
  and non-list-declaration), bypassing `check_governance_ledger()` entirely to test the function in
  isolation.

**Test coverage: PASS** — every category the review brief asked for is genuinely exercised with a
specific assertion, not merely named.

## Validator result

```
python scripts/governance_validate.py
```

Result: `governance_validate: OK (0 warning(s), 0 errors)` — independently re-run against the actual
PR #151 worktree state, matching the implementation's own claim.

`pytest` is not installed in this environment (`python -m pytest --version` →
`No module named pytest`) — the same substitution disclosed in this task's own precedent
([T99_QA_Review.md](T99_QA_Review.md)) applies again: `python scripts/tests/test_governance_validate.py
-v` is the exact command `.github/workflows/governance.yml`'s own "Run governance validator unit
tests" CI step runs, not an ad hoc replacement.

## Documentation consistency

- **`docs/GOVERNANCE_VALIDATION.md`** — new "In-progress transition declarations (T99)" section
  independently re-read against the actual `validate_in_progress_transition()` source line-by-line:
  every condition it lists (exactly-one-entry, well-formed, authorized, frontier, not-Done,
  exact-gap) matches a real corresponding check in the code, in the same order, with matching
  `Violation` check-code names. No claim in this section overstates what the code does.
- **`PROJECT_WORKFLOW.md` §3.1** — the "Architecture/Implementation + QA PR" and "Governance Closeout
  PR" table rows were both amended (verified via `git show e200b7d -- PROJECT_WORKFLOW.md`): step 2
  may add the single declaration; step 3 must remove it, and leaving it past Closeout is stated to be
  "itself a detected governance violation" — accurately describing the
  `governance-transition-already-settled` check's actual behavior once a task reaches `Done`.
- **`AI_BOOTSTRAP.md`** — the mechanically-checkable-invariants bullet gained a one-line pointer to
  the new section with a correct anchor
  (`docs/GOVERNANCE_VALIDATION.md#in-progress-transition-declarations-t99`, matching GitHub's
  Markdown-heading-to-anchor convention for `## In-progress transition declarations (T99)`).
- **No premature "T99 Done" claim** — none of the three documentation files, nor the commit message,
  nor any code comment, asserts T99 is complete, Done, or closed out. The commit message's own final
  paragraph explicitly disclaims this: "Does not... mark T99 Done or perform closeout."

**Documentation consistency: PASS.**

## CI results (actual PR #151 HEAD, `e200b7d`)

Queried directly via `gh api repos/Intelligentclown/Legal_DMS/commits/e200b7d.../check-runs` (against
the commit SHA, not merely the PR view) as well as `gh pr checks 151`:

| Check | Result |
|---|---|
| Frontend validation | SUCCESS |
| Backend validation | SUCCESS |
| Release build verification | SUCCESS |
| Governance consistency validation (pull_request trigger) | SUCCESS |
| Governance consistency validation (push trigger, duplicate) | SUCCESS |

Two "Governance consistency validation" runs exist on this SHA because `governance.yml` triggers on
both `push` (this branch matches its `branches: [..., "docs/**"]` filter) and `pull_request` — by
its own documented design ("runs on every push/PR regardless of changed paths"), not a defect.
Independently distinguished the two runs via `gh api .../actions/runs/<id>` → `{event: "push", ...}`
vs. `{event: "pull_request", ...}`; both completed with `conclusion: "success"` on the identical
`head_sha`. `mergeStateStatus: CLEAN` / `mergeable: MERGEABLE` confirms GitHub itself is not treating
this as an ambiguous or blocking required-check state.

**CI: PASS**, all four intended check names green on the actual reviewed HEAD, no ambiguity from the
duplicate Governance run.

## Ruleset verification (read-only)

`gh api repos/Intelligentclown/Legal_DMS/rulesets/21745493`, re-read fresh for this review:

- `enforcement: "active"` — unchanged.
- `bypass_actors: []` — unchanged.
- `current_user_can_bypass: "never"` — unchanged.
- `deletion` and `non_fast_forward` rules present — unchanged.
- `required_approving_review_count: 0` — unchanged from the previously-observed state.
- `required_status_checks`: **`Frontend validation`, `Backend validation`, `Release build
  verification`, `Governance consistency validation`** — this now reads the *new* (post-#150) job
  names, not the pre-#150 short forms this same ruleset showed during PR #150's own review
  (`updated_at` moved from `2026-08-29T15:55:20` to `2026-08-29T16:22:38`). This synchronization was
  **not** performed by PR #151 (which touches no ruleset, and the ruleset is configured outside this
  repository's tracked files entirely) or by this review — it is read-only-observed, pre-existing
  state, presumably the separate governance-side ruleset-sync action that PR #150's own QA review
  flagged as still outstanding. Recorded here as a factual observation, not attributed to this PR.

**Ruleset: active and unmodified by this review or by PR #151.**

## T98 regression relevance

Independently inspected PR #148 (T98's own Architecture+QA PR, not modified by this review):

```
gh pr view 148 --json state,headRefOid,baseRefOid,mergeStateStatus,statusCheckRollup
```

PR #148 is still `OPEN`, `mergeStateStatus: BEHIND` (its base `10727d64` predates PR #150 by three
merges), and its `Governance consistency validation` check still reports `FAILURE` (two runs, both
`FAILURE`) — this is the exact class of failure T99 was authorized to solve. However, PR #148's own
branch has **not** been updated to declare an `inProgressTransitions` entry, and its base does not
even include the new validator code from PR #151 (not yet merged to `main` as of this review). The
mechanism implemented in PR #151 is therefore **not yet applied** to PR #148 — it has only been
proven correct in the abstract, via synthetic fixtures (`T41`, `T777`, etc.) and against this
repository's own real, currently-clean state (`test_real_repository_passes`).

This is expected, not a defect: `IMPLEMENTATION_QUEUE.md`'s T99 row explicitly places "touching `T98`
PR #148 in any way" outside this task's scope, and this review's own instructions forbid modifying PR
#148. Applying the mechanism to PR #148 (rebasing it onto a `main` that includes PR #151, then adding
the appropriate `inProgressTransitions` declaration to its branch) is necessarily separate, future,
T98-scoped work — not something PR #151 could or should have done itself. The mechanism *design*
genuinely addresses T98's originating problem class; its *application* to T98 specifically remains
outstanding and is correctly left outstanding by this PR.

## Findings

**Blocking:** none.

**Non-blocking:**

1. PR #150's CI job-renaming work and PR #151's governance-transition mechanism are both filed under
   the same T99 authorization identifier, but only the latter matches the "Approved scope" paragraph
   actually recorded in `IMPLEMENTATION_QUEUE.md`'s T99 row. Not a defect in either PR — recorded so
   T99's eventual Governance Closeout PR describes the task's actual delivered scope accurately
   (PR #151), rather than conflating it with PR #150's separate, already-closed contribution.
2. T98's own PR #148 has not yet had this mechanism applied to it (no `inProgressTransitions`
   declaration on that branch, and that branch is not yet rebased past PR #151). This is
   correctly out of scope for T99's own implementation PR, but is the necessary next step before
   PR #148 can pass its required Governance check — noted for whoever picks up that follow-on work,
   not as a defect here.

## QA Decision

```
□ APPROVED
☑ APPROVED WITH COMMENTS
□ CHANGES REQUIRED
□ REJECTED
```

**APPROVED WITH COMMENTS.** The implementation satisfies all nine of T99's stated minimum
requirements, verified individually against the actual source (not the commit message's claims about
it); scope is exactly the five authorized files with nothing else touched; the 49-test suite and the
validator both independently re-run clean; documentation accurately describes the mechanism's real
semantics without overstating completion; CI is green on the actual reviewed HEAD with the duplicate
Governance run correctly distinguished as non-blocking; the ruleset was independently confirmed
unmodified by this PR; and topology confirms PR #151 branches cleanly from post-#150 `main` with no
reachability ambiguity. The two non-blocking comments above do not require rework of this PR — they
are handoff notes for T99's Governance Closeout and for the separate, future application of this
mechanism to PR #148.

This record does not mark T99 Done, does not authorize or create T100, and does not merge PR #151.
