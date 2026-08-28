# T96 Implementation Report

**Task:** T96 — Codify Required-ADR Governance Lifecycle and Authorization-Ancestry Verification.
Full authorized-scope text: `IMPLEMENTATION_QUEUE.md`'s own T96 row (PR #141, merge `031de180`).

**Role:** No fixed role prompt applied — per T96's own authorization row, `PROJECT_WORKFLOW.md` and
`docs/prompts/` are process documents, not architecture or planning documents, and the implementing
role was left for whichever session picks up implementation, consistent with how `T95`'s row left
its own implementing role unfixed. This report follows `docs/prompts/QAReviewer.md` §6's Required
Output structure, mirroring `docs/reviews/T95_Implementation_Report.md`.

---

## 1. Verified Baseline

- Authorization: `IMPLEMENTATION_QUEUE.md` T96 row, merged via PR #141 (`docs/t96-authorization`,
  merge `031de1807fa5c5fae4b9c615203e8fd6bf70dec8`).
- Baseline `main` at implementation start: `031de1807fa5c5fae4b9c615203e8fd6bf70dec8` —
  `main == origin/main`, working tree clean, confirmed before branching.
- No `T97` row/branch/PR existed at any point during implementation.

## 2. Authorized Scope

Document two already-proven governance practices: (1) the three-PR lifecycle in
`PROJECT_WORKFLOW.md`, alongside — not replacing — the existing single-PR lifecycle; (2) the
authorization-commit-ancestry requirement in `docs/prompts/ProjectManager.md` §9, preserving the
existing QA-commit-ancestry check, grounded in `T94`'s incident history. Full text in the T96 row.
Explicitly excluded: `scripts/governance_validate.py`, any tests, `PROJECT_STATE.json`,
`IMPLEMENTATION_QUEUE.md`, `AI_BOOTSTRAP.md`, the three status docs, any ADR, a new ADR file,
resolving/reopening any Required ADR, application/database/schema code, branch-protection settings,
`T97`, and broadening the three-PR lifecycle into universal policy.

## 3. Implementation Summary

Single commit `d3980dde07406e6dc52766fc2b3ab2589737f6dd` on branch
`docs/t96-governance-lifecycle-and-ancestry`:

- **`PROJECT_WORKFLOW.md`** — new §3.1 "Required-ADR / Governance-Hardening Lifecycle (Three-PR)",
  inserted after §3's table and before §4, with no renumbering of any existing section. Describes
  the authorization PR → architecture/implementation+QA PR → governance closeout PR pattern.
  Grounded in verified history, not invention: `T87`'s own merged PRs were checked directly via
  `gh pr view` (#113 `docs(governance): authorize T87`, #114 `docs(adr): ADR-0021 -- ...`, #115
  `docs(governance): close out T87 as Done after PR #114 merge`), confirming the pattern was in use
  from the very first task in the series, not only the more recent ones. States explicitly when it
  applies, that it does not replace §3, and that it is not, by this addition alone, a universal
  policy for future work.
- **`docs/prompts/ProjectManager.md`** §9 — added a new required bullet to the Pre-Merge Governance
  Gate: the task's authorization commit must be a genuine `git merge-base --is-ancestor` ancestor of
  the PR's actual remote HEAD, preserving the existing QA-commit-ancestry bullet unchanged. Added an
  explanatory subsection naming both real `T94` defects this check closes (conversational-only
  authorization; authorization not actually incorporated into the branch), citing `T94`'s
  `IMPLEMENTATION_QUEUE.md` row and `docs/reviews/T94_Software_Architect_Report.md` directly.

## 4. Testing Performed

- `python scripts/governance_validate.py` — 0 errors (validator itself untouched).
- `python scripts/tests/test_governance_validate.py -v` — 35/35 passing (suite itself untouched).
- `git diff --stat main` reviewed — exactly `PROJECT_WORKFLOW.md` (+44) and
  `docs/prompts/ProjectManager.md` (+39/-4), 79 insertions, 4 deletions.
- Branch confirmed built directly on the authorized `main`
  (`git merge-base HEAD main` = `031de1807fa5c5fae4b9c615203e8fd6bf70dec8`).

## 5. Discovered

Nothing requiring architectural judgment. Verifying the "already in use since `T87`" claim (rather
than asserting it) surfaced that `T87` used all three PRs from the start of the series (#113/#114/
#115) — this strengthened the documentation's factual grounding but required no scope change.

## 6. Deferred

Nothing beyond what T96's own row already deferred: branch-protection configuration, broadening the
three-PR lifecycle to other task categories, and any change to `scripts/governance_validate.py`
itself remain explicitly out of this task's scope.

## 7. Exact Files Changed

```
PROJECT_WORKFLOW.md            (modified -- new SS3.1 only, no existing section renumbered)
docs/prompts/ProjectManager.md (modified -- SS9 extended only)
```

No `scripts/*`, `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, `AI_BOOTSTRAP.md`,
`docs/ProjectStatus.md`/`AI_HANDOVER.md`/`SessionReport.md`, `ADR/*`, or
`backend/`/`frontend/`/`electron/` file appears anywhere in this diff. No `T97` row, branch, or PR
exists anywhere in the repository.

## Reviewer Checklist

```
Reviewer Checklist

[x] Architecture preserved -- no ADR touched; SS3's existing lifecycle and SS9's existing QA-commit
    ancestry check both left intact, only extended.
[x] Existing design patterns followed -- new PROJECT_WORKFLOW.md content added as a decimal
    subsection (SS3.1) rather than renumbering; T87's own PR history cited as evidence rather than
    asserted from memory.
[ ] Tests added -- not applicable; documentation-only task, no code changed.
[x] Existing tests pass -- 35/35, unmodified suite, unmodified validator.
[x] Documentation updated -- this report and the two authorized files are the documentation this
    task produces.
[ ] ADR updated (if required) -- not applicable; T96 does not resolve or touch any ADR.
[x] PROJECT_STATE updated (if required) -- N/A, explicitly excluded from this task's scope.
[x] No unrelated refactoring -- every change traces directly to one of T96's two authorized items.
[x] No scope creep -- no excluded file touched, no Required ADR resolved/reopened, no T97
    authorized or created, three-PR lifecycle explicitly scoped as non-universal.
[x] Ready for QA -- implementation complete, PR #142 open, this report complete.
```

## QA Decision

☐ Approved
☒ Approved with comments
☐ Rework required

**Recorded by the independent QA Reviewer role (2026-08-28), against PR #142's actual remote HEAD
at review time (`d3980dde07406e6dc52766fc2b3ab2589737f6dd`).**

**Blocking findings: none.**

Confirmed:

- Implementation is within the authorized T96 scope.
- Exactly the two authorized files changed.
- Authorization-ancestry requirement is correctly documented.
- Three-PR lifecycle is correctly documented alongside the existing lifecycle.
- T94 incident rationale is appropriately recorded.
- Governance validator passes.
- 35/35 governance tests pass.
- CI is green.
- No excluded files or T97 work were introduced.

Non-blocking comment (does not require T96 rework or expansion):

1. The documented three-PR lifecycle must remain understood as applying only to the task class
   explicitly described by `PROJECT_WORKFLOW.md` §3.1 (Required-ADR / governance-hardening tasks
   tracked directly in `IMPLEMENTATION_QUEUE.md`), not as automatic authorization or a universal
   policy for future tasks. This is already stated explicitly in the merged text ("This is not, by
   this addition alone, a universal policy for all future work... a separate project-owner
   decision, not implied here") — confirmed present, not newly required.

**QA Decision: Approved with comments.**
