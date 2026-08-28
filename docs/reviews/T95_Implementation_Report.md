# T95 Implementation Report

**Task:** T95 — Context & Governance Hardening. Unlike `T87`–`T94`, this task does not resolve a
Required ADR from the specification's §21 planning list — it hardens the repository's own
self-explaining context and governance automation. Full authorized-scope text:
`IMPLEMENTATION_QUEUE.md`'s own T95 row (PR #138, merge `9c29d081`).

**Role:** No fixed role prompt applied — the T95 authorization row itself states this task's
implementation "does not map cleanly onto the Software Architect role `T87`–`T94` used," leaving the
implementing role to whichever session picks up implementation. This report follows
`docs/prompts/QAReviewer.md` §6's Required Output structure (Files reviewed, Findings, Required
changes, Reviewer Checklist, QA Decision) adapted for a self-review of implementation work, since no
stage/phase `ImplementationLog` entry applies (T95 is governance tooling, outside the Stage 3/4
business roadmap `docs/ImplementationLog/` tracks).

---

## 1. Verified Baseline

- Authorization: `IMPLEMENTATION_QUEUE.md` T95 row, merged via PR #138
  (`docs/t95-authorization`, merge `a65999349d28bb73dfc8686775d64605c20527c3`).
- Baseline `main` at authorization: `a65999349d28bb73dfc8686775d64605c20527c3` —
  `main == origin/main`, working tree clean, confirmed at implementation start.
- No `ADR/0029`, no `T96` row/branch/PR existed at any point during implementation — re-confirmed
  throughout.

## 2. Authorized Scope

Six areas: (1) context architecture, (2) `PROJECT_STATE.json` structuring, (3) governance
consistency validation, (4) ADR/reference integrity validation, (5) governance CI gate,
(6) fresh-agent usability — full text in the T95 row. Explicitly excluded: resolving/reopening any
unresolved Required ADR, modifying `ADR/0021`–`ADR/0028`, creating `ADR/0029`, any
schema/application/business-feature implementation, and authorizing `T96` or any subsequent task.

## 3. Implementation Summary

**Initial pass (commits `c515964`, `f670abe`, `1269c42`, `ae8cd52`):**

- `scripts/governance_validate.py` — stdlib-only validator: duplicate task IDs; a `"TNN is now
  Done"` row missing the repository's established `"Authorized by the project owner"` phrase; ADR
  filename/header integrity; two ADR files claiming to resolve the same Required ADR; dangling
  `ADR/NNNN` references; `PROJECT_STATE.json` `governanceLedger` drift against what the ADR files
  themselves declare resolved. `--report` mode prints a live resolved/unresolved Required-ADR
  summary.
- `.github/workflows/governance.yml` — runs the validator's own tests then the validator itself, on
  every push/PR, independent of `backend`'s/`frontend`'s dependency graphs.
- `scripts/tests/test_governance_validate.py` — initial 22 tests (positive/negative per check, plus
  a live pass against the real repository).
- `PROJECT_STATE.json` — additive `governanceLedger` field (`resolvedRequiredADRs`,
  `unresolvedRequiredADRs`, `latestTaskDone`, `latestTaskAuthorized`, `asOfCommit`, `validator`),
  inserted via minimal text splice, no existing key touched.
- `AI_BOOTSTRAP.md` — new "Governance & Task Authorization Model" section; `docs/DefinitionOfDone.md`
  — CI checklist item now names `governance.yml` explicitly; `docs/GOVERNANCE_VALIDATION.md` —
  new file documenting what the validator does and deliberately does not check.

**Hardening pass, requested before QA (commits `b6d0f3d`, `d1a322e`, `15e2808`):**

- Reviewed the implementation against actual repository conventions rather than assuming the
  original tests proved correctness. Found and fixed a real bug: `check_governance_ledger` used
  `dict.get(key, [])`, so a ledger declaring only one of `resolvedRequiredADRs`/
  `unresolvedRequiredADRs` (or neither) was incorrectly treated as declaring the other as empty.
  Each of the four `governanceLedger` sub-fields is now independently optional.
- Added two new checks: `done-without-qa-evidence` (a Done row must also mention `"QA Decision"`,
  verified present on every Done row `T4`–`T94`) and `governanceLedger.latestTaskDone`/
  `.latestTaskAuthorized` drift detection (cross-checked against `IMPLEMENTATION_QUEUE.md`'s own
  rows, not trusted as hand-maintained).
- Discovered and corrected a genuine stale-context defect: the section header governing `T81` and
  `T86`–`T95` in `IMPLEMENTATION_QUEUE.md` read "flagged, not scheduled — unrelated to any single
  stage" — actively wrong for all twelve rows underneath it. Corrected the header text only; no row
  content changed.
- Added 13 new regression tests (35 total): the QA-evidence check, the ledger latest-task drift
  check, an explicit regression test for the optional-field bug, a test proving topic similarity in
  an ADR's body cannot cause false Required-ADR resolution inference, a test confirming
  `ADR/template.md`-style non-numbered files are skipped rather than flagged, and an explicit,
  documented test of the known narrative-vs-assertion limitation (see Discovered, below).

## 4. Testing Performed

- `python scripts/tests/test_governance_validate.py -v` — 35/35 passing, including a live assertion
  that the real repository currently passes with zero errors.
- `python scripts/governance_validate.py` — clean, 0 errors, against the actual repository.
- End-to-end CLI smoke tests against deliberately broken fixtures (duplicate task ID, Done without
  authorization, Done without QA evidence, dangling ADR reference, stale
  `governanceLedger.latestTaskDone`) — every case caught, correct message, exit code `1`.
- `python -m py_compile` / `ast.parse` on both new Python files — no syntax errors. No repository
  lint config (ruff/black) reaches `scripts/` — `backend.yml`'s lint step is explicitly scoped to
  `working-directory: backend`, confirmed by reading the workflow file directly, so this is the
  applicable check, not a skipped one.
- `governance.yml` reviewed line-by-line for silent-skip mechanisms (`continue-on-error`, `if:`
  conditions) — none present; it cannot silently skip the validator.

## 5. Discovered (with disposition)

1. **Optional-field bug in `check_governance_ledger`** — found while writing new tests, not by
   inspection. **Fixed** (commit `b6d0f3d`).
2. **Stale `IMPLEMENTATION_QUEUE.md` section header** over `T81`, `T86`–`T95` — a genuine
   fresh-agent-usability defect (a naive reader could conclude the currently-authorized task, `T95`,
   is unscheduled background noise). **Fixed** (commit `d1a322e`), header text only.
3. **Narrative-vs-assertion limitation** — the authorization/QA-evidence checks are pure substring
   matching and cannot distinguish "this task IS authorized" from "this row discusses what
   authorization means" (e.g. quoting the phrase while narrating history, as `T94`'s own row does).
   **Documented, not fixed** — judged not safely addressable without brittle semantic parsing, which
   this task's own governing instructions warn against. Covered by an explicit regression test
   (`test_known_limitation_narrative_mention_is_not_distinguished_from_assertion`) and by
   `docs/GOVERNANCE_VALIDATION.md`'s "What this deliberately does not validate" section.
4. **Git-ancestry validation is out of reach for a static text checker** — confirmed structurally,
   not merely asserted: `governance_validate.py` operates on file content at a single commit; it has
   no access to git history/ancestry at all. Documented, not attempted.

No repository fact claimed in this report or in `docs/GOVERNANCE_VALIDATION.md` was asserted without
being directly re-verified during implementation.

## 6. Deferred

- Full historical backfill of a per-task structured governance ledger beyond the aggregate
  Required-ADR view (e.g. individual entries for `T1`–`T92`).
- Any further hardening of the narrative-vs-assertion limitation.
- Git-ancestry-aware validation as a possible future, separately-authorized task.

None of these require a decision this report is positioned to make; none was decided here.

## 7. Exact Files Changed

```
.github/workflows/governance.yml          (new)
AI_BOOTSTRAP.md                           (modified)
IMPLEMENTATION_QUEUE.md                   (modified -- header text only, no row content)
PROJECT_STATE.json                        (modified -- additive governanceLedger field only)
docs/DefinitionOfDone.md                  (modified)
docs/GOVERNANCE_VALIDATION.md             (new)
scripts/governance_validate.py            (new)
scripts/tests/test_governance_validate.py (new)
```

No `ADR/*`, `backend/`, `frontend/`, `electron/`, schema, or migration file appears anywhere in this
diff. No `ADR/0029` was created. No `T96` row, branch, or PR exists anywhere in the repository — the
only `T96` text anywhere in this diff is a Python string literal inside one test fixture, documenting
a hypothetical scenario, not a real task.

## Reviewer Checklist

Per `docs/ImplementationLog/README.md`'s standard eleven-item self-assessment:

```
Reviewer Checklist

[x] Architecture preserved -- ADR/0021-0028 not touched, referenced only as evidence sources.
[x] Existing design patterns followed -- stdlib-only tooling (no new dependency for backend/
    frontend to carry), minimal-text-splice discipline for PROJECT_STATE.json matching T93/T94's
    own established technique, existing entry points (AI_BOOTSTRAP.md) extended rather than
    duplicated.
[x] Tests added -- 35 tests, positive and negative fixtures per check, plus real-repository and
    CLI-level smoke tests.
[x] Existing tests pass -- no existing backend/frontend test or CI workflow was modified or
    touched by this change; governance.yml is additive.
[x] Documentation updated -- docs/GOVERNANCE_VALIDATION.md (new), AI_BOOTSTRAP.md, 
    docs/DefinitionOfDone.md.
[ ] ADR updated (if required) -- not applicable; T95 does not resolve or touch any ADR.
[ ] AI_BOOTSTRAP updated (if required) -- done where applicable (see above); N/A beyond that.
[x] PROJECT_STATE updated (if required) -- additive governanceLedger field, authorized explicitly
    by T95's own scope (unlike T87-T94's architecture-only phases, which excluded this file).
[x] No unrelated refactoring -- every change traces directly to one of T95's six authorized scope
    areas or a discovered defect within them.
[x] No scope creep -- no Required ADR resolved/reopened, no ADR/0021-0028 modified, no ADR/0029
    created, no application/schema/business-feature code, no T96 authorized or created.
[x] Ready for QA -- implementation and hardening complete, PR #139 open, this report complete.
```

## QA Decision

☐ Approved
☒ Approved with comments
☐ Rework required

**Recorded by the independent QA Reviewer role (2026-08-28), against PR #139's actual remote HEAD at
review time (`15e2808662e1b4c1605babfd295e0daee0307a4d`).**

**Blocking findings: none.**

Non-blocking comments (do not require T95 rework or expansion):

1. Authorization/QA-evidence checks are intentionally phrase-based and cannot distinguish assertion
   from narrative mention.
2. `governanceLedger.latestTaskAuthorized` has the same textual limitation.
3. Git ancestry validation remains deliberately outside T95 and remains a Project Manager
   pre-merge-verification responsibility.
4. `governanceLedger` must remain a derived convenience view, not a new source of truth.

All four comments describe limitations already disclosed in this report's §5 and in
`docs/GOVERNANCE_VALIDATION.md`'s "What this deliberately does not validate" section — confirmed,
not newly surfaced. Per this QA Decision's own governing instruction, T95 is not redesigned or
expanded to address them.

**QA Decision: Approved with comments.**
