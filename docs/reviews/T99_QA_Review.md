# T99 QA Review

**Task:** T99 — Governance Lifecycle / Required-CI Compatibility Remediation (CI required-check
naming).

**Scope:** Rename the `name:` field of the single job in each of `.github/workflows/frontend.yml`,
`.github/workflows/backend.yml`, and `.github/workflows/release.yml` so each produces a check name
distinct from the others and free of the "Lint, format, and test" collision between frontend and
backend. `.github/workflows/governance.yml` is explicitly out of scope (its job name was already
correct). No workflow trigger, permission, step, action version, environment variable, secret,
runner, condition, matrix, artifact, concurrency, or path-filter change is authorized. No change to
the `main-required-ci` ruleset, `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`,
`scripts/governance_validate.py`, its test suite, application code, or any T98/T100+ material is
authorized as part of this PR.

**Authorization:** commit `1eef559d6f60988b46d899e61d36003c38e78cfa` (T99 authorization, itself
built on `90a5e1e` which authorized the task).

**Implementation:** commit `777a3fdb50e3ca1dd6b31ae27906829c3f3c49a3`, branch
`ci/t99-required-check-naming`, PR #150.

**Reviewed:** actual remote HEAD of PR #150 as returned live by `gh pr view 150` and
`git rev-parse origin/ci/t99-required-check-naming` — confirmed identical to the reported
implementation commit `777a3fd`. Base confirmed identical to live `origin/main`
(`10727d64f43c6f8992dbf608efb751d62f1ce9b5`). Diffs inspected: `git diff
10727d64..HEAD`, `git diff 1eef559d..HEAD`, and `git show 777a3fd` in isolation. Live GitHub state
inspected: `gh pr checks 150`, `gh pr view 150 --json statusCheckRollup`, `gh api
.../commits/777a3fd/check-runs`, `gh api repos/.../rulesets` and
`.../rulesets/21745493`. Local execution: `python scripts/governance_validate.py` and
`python scripts/tests/test_governance_validate.py -v` (pytest is not installed in this
environment; substituted the repository's own CI-invoked unittest entry point, which is the same
command `governance.yml`'s "Run governance validator unit tests" step runs — not an ad hoc
substitute).

**Date:** 2026-08-29

---

## Verification performed

- **PR state** — `gh pr view 150`: `state: OPEN`, `closed: false`, `mergedAt: null`,
  `mergeStateStatus: BLOCKED` (expected — required contexts on the ruleset still name the old
  short forms; see Ruleset section below). `baseRefOid` = live `origin/main` exactly. No merge was
  performed by this review.
- **Actual remote HEAD** — `headRefOid` from `gh pr view 150` and `git rev-parse
  origin/ci/t99-required-check-naming` both resolve to `777a3fdb50e3ca1dd6b31ae27906829c3f3c49a3`,
  matching the reported implementation commit. No commit has appeared after it; no rebase or
  history replacement occurred.
- **Ancestry** — `git merge-base --is-ancestor 1eef559d6f60988b46d899e61d36003c38e78cfa HEAD` and
  `git merge-base --is-ancestor 777a3fdb50e3ca1dd6b31ae27906829c3f3c49a3 HEAD` both succeed. `git
  log 10727d64..HEAD` shows exactly three commits ahead of main: `90a5e1e` (T99 authorization),
  `1eef559` (governance-ledger sync, itself part of authorization), `777a3fd` (implementation). No
  unexpected or unauthorized commit exists on the branch.
- **Diff scope** — `git diff --stat 10727d64..HEAD` touches five files: `frontend.yml`,
  `backend.yml`, `release.yml`, `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`. Isolating the
  implementation commit alone (`git show --stat 777a3fd`) shows it touches **only** the three
  workflow files, one line each (+1/-1). `IMPLEMENTATION_QUEUE.md`/`PROJECT_STATE.json` changes are
  entirely attributable to the pre-existing authorization commits (`90a5e1e`, `1eef559`), confirmed
  via `git log 10727d64..HEAD -- PROJECT_STATE.json IMPLEMENTATION_QUEUE.md`, which lists only
  those two commits — not the implementation commit. `governance.yml` does not appear in `git diff
  --name-only 10727d64..HEAD` at all — confirmed untouched.
- **Line-level diff** — `git show 777a3fd -- frontend.yml backend.yml release.yml` confirms each
  file's diff is exactly one `name:` line under `jobs.<id>:`, with the surrounding
  `runs-on`/`defaults`/`steps` context lines unchanged:
  - `frontend.yml`: `Lint, format, and test` → `Frontend validation`
  - `backend.yml`: `Lint, format, and test` → `Backend validation`
  - `release.yml`: `Build verification` → `Release build verification`

  No trigger, permission, step, action version, env var, secret, runner, condition, matrix,
  artifact, concurrency, or path-filter line appears in any of the three diffs.
- **Job-name/collision check** — `grep -n '^\s*name:' .github/workflows/{frontend,backend,release,governance}.yml`
  at HEAD confirms four distinct job names (`Frontend validation`, `Backend validation`, `Release
  build verification`, `Governance consistency validation`) and four distinct workflow-level
  `name:` values (`Frontend`, `Backend`, `Release`, `Governance`, unchanged). No duplicate job name
  exists; the original frontend/backend collision is resolved.
- **Live CI on the actual HEAD** — `gh pr checks 150` and `gh api
  repos/.../commits/777a3fd/check-runs` (queried directly against the commit SHA, not just the PR
  view) both return exactly four check runs, all `completed`/`success`:
  `Frontend validation`, `Backend validation`, `Release build verification`, `Governance
  consistency validation`. No stale check run under either old name (`Lint, format, and test`,
  `Build verification`) is present on this commit — no naming ambiguity or collision exists on the
  actual HEAD.
- **Governance validator** — `python scripts/governance_validate.py` →
  `governance_validate: OK (0 warning(s), 0 errors)`.
- **Governance test suite** — pytest is not installed in this environment; ran the same command
  `governance.yml` itself runs in CI, `python scripts/tests/test_governance_validate.py -v` → `Ran
  35 tests in 0.051s — OK`, no failures.
- **Ruleset (read-only)** — `gh api repos/.../rulesets` lists one active ruleset,
  `main-required-ci` (id `21745493`). Fetched in full: `enforcement: active`, `bypass_actors: []`,
  `current_user_can_bypass: never`, `deletion` and `non_fast_forward` rules present, four required
  status-check contexts (`Frontend`, `Backend`, `Release`, `Governance consistency validation`).
  Not modified by this review or by PR #150. The mismatch between these four required *contexts*
  and the four *check names* the workflows now actually produce (`Frontend validation`, `Backend
  validation`, `Release build verification` differ from the first three required contexts;
  `Governance consistency validation` already matched and still does) is exactly the state the task
  description anticipates: PR #150 is scoped to the workflow side only, and ruleset-context
  synchronization is an explicit separate, later governance action outside this PR's authorized
  scope. This mismatch is why `mergeStateStatus` currently reads `BLOCKED` — expected, not a defect.

## Findings

None blocking. The implementation is minimal and exactly scoped: the isolated implementation
commit changes only the three authorized workflow files, one job-name line each, with no
behavioral, trigger, permission, or step change; `governance.yml` is untouched; no unauthorized
file, ruleset, or governance-state change exists on the branch; live CI on the actual remote HEAD
produces exactly the four intended, non-colliding check names, all passing; the governance
validator and its full test suite both pass clean.

One non-blocking observation: `mergeStateStatus` is `BLOCKED` because the `main-required-ci`
ruleset's required contexts (`Frontend`/`Backend`/`Release`) still name the pre-rename short forms
and do not yet match the workflows' new job names. This is expected and out of scope for PR #150 per
the task's own authorization — recorded here only so the Governance Control Tower does not attempt
to merge before a separate ruleset-synchronization action lands, and does not mistake the current
`BLOCKED` status for a defect in this implementation.

## QA Decision

```
☑ Approved with comments
□ Approved
□ Rework required
```

Approved with comments — the implementation correctly and minimally resolves the authorized
check-name collision with no scope creep or behavioral change, independently re-verified against
live repository and GitHub state (not accepted from the implementation's own report). The one
comment (ruleset-context mismatch causing `BLOCKED` merge status) is expected, pre-disclosed by the
task's own scope boundary, and requires a separate governance action — not rework of this PR.
