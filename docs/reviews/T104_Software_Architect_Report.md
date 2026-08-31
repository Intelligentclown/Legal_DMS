# T104 Software Architect Report

**Task:** T104 — Formalize a narrow, prospective governance-process exception ("Option A") allowing
qualifying Project-Owner-authorized, documentation-only synchronization actions to be tracked by
durable GitHub Issue/PR references without consuming a `T##` number. Full authorized-scope text:
`IMPLEMENTATION_QUEUE.md`'s own T104 row (authorization commit `0e06a2a`, merge `bdab49c`, PR #170).

**Role:** Software Architect / Governance Process Architect, per direct task assignment for the T104
Amendment + QA phase — the same specialist role `docs/prompts/SoftwareArchitect.md` and `T103`'s own
report describe, applied here to a governance-process document rather than an ADR, consistent with
how `T96`'s equivalent report notes process documents "are not architecture or planning documents"
in the ADR sense but still require the same evidence-grounded, self-scoped drafting discipline.

---

## 1. Verified Baseline and Authorization

- `git fetch origin` + `git rev-parse origin/main`: `bdab49c4f3157621a80300b64e58ba52dc0e4fd7` —
  independently confirmed as PR #170's actual merge commit (`gh pr view 170`, `baseRefName: main`),
  not taken on the governing prompt's word.
- Authorization commit ancestry confirmed: `git merge-base --is-ancestor
  0e06a2a47ea36cbfaf8a3bd8157fe6cd10c2cdc0 HEAD` → true (checked before branching; local `main` was
  fast-forwarded to `origin/main` first, since local `main` was two commits behind at session start).
- `IMPLEMENTATION_QUEUE.md`'s T104 row, read directly from `origin/main`, names: the exact ten
  conditions (1–10) and the A–I threshold test the amendment must preserve; the required minimum
  authorization-record fields; the explicit distinction between Option A and numbered
  governance/implementation work; the explicit exclusions (no `T105`, no retroactive renumbering of
  `Issue #167`/`PR #168`/`PR #169`, no application/schema/ADR/CI/ruleset change, no validator change
  without a separate report, no Organization/Tenant Core authorization); and — critically — a
  **pre-merge QA Decision requirement**, the same discipline `T103` restored after `T101`/`T102`'s
  disclosed post-merge sequencing gap.
- Branch `docs/t104-amendment-option-a-exception` created directly from `origin/main` at `bdab49c`.
- `PROJECT_STATE.json`'s `governanceLedger` already shows `latestTaskAuthorized: "T104"`,
  `latestTaskDone: "T103"` (set by PR #170) — unchanged by this pass, per T104's own row (ledger
  synchronization is explicitly deferred to a future Governance Closeout PR, not this one).

## 2. Required Reading Completed

`PROJECT_WORKFLOW.md` (in full, including §3.1); `AI_BOOTSTRAP.md` (in full); `IMPLEMENTATION_QUEUE.md`
T103 and T104 rows (T104 row read via targeted `grep`/`awk` — the file's own lines exceed normal
per-line read limits by design, not a defect); `PROJECT_STATE.json`'s `governanceLedger`; `docs/
prompts/ProjectManager.md` (in full — no direct contradiction with Option A found; its scope is
Pre-Merge Governance Gate mechanics for numbered implementation PRs, not a blanket "every
documentation change needs a `T##`" claim); `docs/reviews/T96_Implementation_Report.md` (precedent
for how a prior process-only amendment was scoped, drafted, and reported); `Issue #167` (the
worked-example authorization record); `PR #168` (the historical, non-task documentation
synchronization this section formalizes the rule for, without retroactively authorizing it); `PR
#169` (open, unmerged at the time of this report — the separate, non-numeric ledger reconciliation
for that history; not this task's concern and not touched here); `PR #170` (T104's own Authorization
PR, merged).

## 3. Decision Made

Added a single new subsection, `PROJECT_WORKFLOW.md` §3.2 "Non-Task Documentation/Governance Action
Exception (\"Option A\")", immediately after the existing §3.1 and before §4 — the same insertion
point/pattern `T96` used for §3.1 itself (decimal subsection, no renumbering of any existing
section). The new section states, self-containedly:

- What the exception is and why it exists (one paragraph).
- All 14 qualifying conditions, consolidated from the T104 row's ten numbered conditions and A–I
  threshold test into one non-duplicated list (the two source lists overlap substantially — e.g.
  "no ADR touched" and condition (D)/(6) are the same requirement stated twice in the authorization
  row's own text; this report and the merged section state each requirement exactly once).
- The minimum authorization-record content required.
- An explicit statement that a GitHub Issue is not equivalent to `IMPLEMENTATION_QUEUE.md`
  authorization for numbered work — only for this narrow class.
- The anti-loophole/scope-expansion rule, including the explicit statement that changing this
  governance process itself is never eligible for the exception it defines.
- A "History" paragraph stating plainly that this is prospective: `Issue #167`/`PR #168` remain
  non-task historical work under whatever rules were actually in force when they happened, `T104`
  does not retroactively authorize or renumber them, and `PR #169`'s own separate reconciliation is
  unaffected by this section.

**No STOP condition was triggered.** T104's authorized scope is a process-documentation decision
(where and how to state an already-owner-decided rule), not a business-policy or undetermined
technical decision — the Project Owner's decision (Option A, and its exact ten conditions/A–I test)
was already made and recorded in the T104 authorization row before this drafting pass began; this
report's only judgment calls were editorial (section placement, consolidating the row's own
enumerations into one list, wording for a document meant to be read standalone) — none of them
change the substance of what the Project Owner already authorized.

## 4. Alternatives Evaluated

- **Where to place the new text.** Considered a new top-level `## 4a` section, or folding the
  exception into existing §2 ("Repository Principles"). Rejected both: §2 is a list of one-line
  principles, not a place for a fourteen-condition policy; a new top-level section between §3 and
  §4 would require renumbering every subsequent top-level section (§4–§12), which the task's own
  minimal-diff instruction and `PROJECT_WORKFLOW.md`'s own §12 ("this document itself is meant to
  stay stable") both counsel against. A `§3.2` decimal subsection, directly following `§3.1`'s own
  identical precedent, requires no renumbering and reads naturally as "the two documented exceptions
  to the default single-PR lifecycle live together."
- **Whether to touch `AI_BOOTSTRAP.md` or `docs/prompts/ProjectManager.md`.** T104's own row
  permitted this "only where genuinely required for internal consistency." Read both in full,
  specifically hunting for language that would contradict or need updating for a non-task
  documentation action to exist without a `T##` row. Found none: `AI_BOOTSTRAP.md`'s "Task lifecycle"
  bullet describes the state machine *tasks* follow, not a claim that every documentation change is
  a task; `docs/prompts/ProjectManager.md`'s Pre-Merge Governance Gate (§9) governs merging
  *implementation* PRs reported `Approved`/`Approved with comments` and does not assume every merged
  PR corresponds to a `T##` row. Concluded neither file requires a change, and left both untouched,
  per the task's own "change only what is necessary" instruction and "do not perform a broad
  governance rewrite."
- **Whether to write conditions as one consolidated list or preserve the authorization row's two
  separate enumerations (1–10, A–I) verbatim.** The row's own text is dense, cross-referencing,
  legally-styled prose intended for the authorization commit, not for `PROJECT_WORKFLOW.md`'s stated
  purpose ("read this once to understand the entire development lifecycle... for any reader, human
  or AI"). Reproducing both enumerations verbatim would duplicate several conditions under different
  numbers and materially hurt readability. Chose one merged, deduplicated 14-item list instead,
  preserving every substantive requirement from both source enumerations with nothing weakened,
  narrowed, or dropped — checked item-by-item against the row's own text during drafting.
- **Whether a companion report was required at all.** `T96`'s report explains itself as following
  because that task, like this one, is a process/governance-hardening amendment tracked directly by
  its own `IMPLEMENTATION_QUEUE.md` row rather than an `ImplementationLog`-based flow — exactly
  T104's own class per §3.1's own applicability statement. Concluded the same pattern applies here;
  produced this report rather than skipping it.

## 5. Composition Check

- **`PROJECT_WORKFLOW.md` §3 (Standard Development Lifecycle).** Not modified. §3.2 states plainly
  that a failing Option-A action reverts to "the normal numbered-task lifecycle (§3 or §3.1,
  whichever actually fits its nature)" — composing with, not replacing, the existing default.
- **`PROJECT_WORKFLOW.md` §3.1 (Three-PR Required-ADR/Governance-Hardening Lifecycle, added by
  `T96`).** Not modified. §3.2 explicitly cites it twice: once as the fallback lifecycle for a
  disqualified Option-A action, and once to state that T104 itself — because it changes governance
  process — is a §3.1 task, not an Option-A action. No wording inside §3.1 itself was touched.
- **`PROJECT_WORKFLOW.md` §6 (Pull Request Workflow).** Not modified. §3.2 references its QA
  remote-publication gate and required-checks language directly (conditions 10–11) rather than
  restating or altering it — Option A actions are still bound by §6 in full, not exempted from it.
- **`AI_BOOTSTRAP.md`, `docs/prompts/ProjectManager.md`.** Not modified — see §4 above for the
  affirmative check that neither required a change.
- **`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`.** Not modified — per T104's own row, ledger
  synchronization is a Governance Closeout PR action, not this Amendment+QA PR's.
- **Any ADR.** Not touched, created, reopened, or referenced as being modified. This is a process
  document change, not an architectural decision.
- **`Issue #167` / `PR #168` / `PR #169`.** Not rewritten, not renumbered, not converted into a
  task. §3.2's "History" paragraph states their non-task status explicitly and leaves `PR #169`'s
  own separate, still-open reconciliation entirely alone.
- **`T103`.** Not modified, reopened, or reinterpreted anywhere in this diff.

## 6. Exact Files Changed

```
$ git status --short
 M PROJECT_WORKFLOW.md
?? docs/reviews/T104_Software_Architect_Report.md

$ git diff --stat origin/main
 PROJECT_WORKFLOW.md | 76 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 76 insertions(+)
```

Exactly one existing file modified (`PROJECT_WORKFLOW.md`, insertion-only — no existing line removed
or altered) and one new file added (this report). No `scripts/*`, `PROJECT_STATE.json`,
`IMPLEMENTATION_QUEUE.md`, `AI_BOOTSTRAP.md`, `docs/prompts/*`, `ADR/*`, or `backend/`/`frontend/`/
`electron/` file appears anywhere in this branch's diff against `origin/main`. No `T105` row, branch,
or PR exists anywhere in the repository.

## 7. Confirmation No Implementation Occurred

No database table, migration, backend model, service, repository, route, frontend code, CLI script,
CI workflow, or GitHub ruleset was created or modified. No test was added or changed — this task
authorizes no code, so none is required. `scripts/governance_validate.py` and its test suite are
untouched, as T104's row required (any needed validator change was to be **reported**, not
implemented, under this row — see §8 Validation below: none was needed).

## 8. Confirmation Governance Boundaries Were Respected

`IMPLEMENTATION_QUEUE.md` and `PROJECT_STATE.json` were not modified — ledger synchronization is
explicitly deferred to a future, separate Governance Closeout PR, per T104's own row. No `T105` was
created, authorized, or implied. `T104` is not marked Done by this report or any file it changes —
that requires the Governance Closeout PR (step 3 of §3.1's lifecycle), not opened by this pass. No
accepted ADR is reopened, created, or modified — confirmed absent from this branch's diff. `Issue
#167`/`PR #168`/`PR #169` are not retroactively converted into a `T`-numbered task or rewritten —
confirmed by direct inspection of this diff (none of those references' own text is touched) and by
§3.2's own explicit "History" statement.

## Validation

1. **Branch ancestry**: `git merge-base --is-ancestor 0e06a2a47ea36cbfaf8a3bd8157fe6cd10c2cdc0 HEAD`
   → `true`.
2. **Base identity**: `git rev-parse origin/main` == `bdab49c4f3157621a80300b64e58ba52dc0e4fd7`,
   matching PR #170's reported merge commit exactly.
3. **`git diff --check`** — clean (no whitespace errors).
4. **Governance validator**:

```
$ python scripts/governance_validate.py
governance_validate: OK (0 warning(s), 0 errors)
```

5. **Governance test suite**:

```
$ python scripts/tests/test_governance_validate.py -v
Ran 51 tests ... OK
```

6. **No excluded content**: confirmed via `git diff --stat origin/main` — one modified file
   (`PROJECT_WORKFLOW.md`), one new file (this report).
7. **`T103` untouched**: confirmed — `T103`'s row in `IMPLEMENTATION_QUEUE.md`, `ADR/0032`, and
   `docs/reviews/T103_*` do not appear in this diff.
8. **Validation failures**: none found or concealed.

## Reviewer Checklist

```
Reviewer Checklist

[x] Architecture preserved -- no ADR touched; SS3's existing default lifecycle and SS3.1's existing
    three-PR lifecycle both left intact, only extended with a new, narrower SS3.2 exception.
[x] Existing design patterns followed -- new content added as a decimal subsection (SS3.2) rather
    than a renumbered top-level section, mirroring exactly how T96 added SS3.1 itself.
[ ] Tests added -- not applicable; documentation-only process amendment, no code changed.
[x] Existing tests pass -- 51/51, unmodified suite, unmodified validator.
[x] Documentation updated -- PROJECT_WORKFLOW.md SS3.2 and this report are the documentation this
    task produces.
[ ] ADR updated (if required) -- not applicable; T104 does not resolve, touch, or require an ADR.
[x] PROJECT_STATE updated (if required) -- N/A this PR; explicitly deferred to a future Governance
    Closeout PR, per T104's own authorization row.
[x] No unrelated refactoring -- every sentence in SS3.2 traces directly to one of T104's ten
    authorized conditions or its A-I threshold test; no other section of PROJECT_WORKFLOW.md edited.
[x] No scope creep -- no excluded file touched (AI_BOOTSTRAP.md and docs/prompts/ProjectManager.md
    read in full and affirmatively found not to require a change); no T105 authorized or created; no
    ADR reopened; no Organization/Tenant Core authorization; Issue #167/PR #168/PR #169 not
    renumbered or rewritten.
[x] Ready for QA -- PROJECT_WORKFLOW.md SS3.2 and this report are complete and handed off below.
```

## QA Handoff — critical, pre-merge requirement

**This is the operative instruction for this PR, per `T104`'s own authorization row:** a formal,
independent QA Decision must be **rendered and persisted on this PR's actual remote HEAD before this
PR is merged** — the same pre-merge discipline `T103` restored and this task's row explicitly
requires ("no exemption exists in `PROJECT_WORKFLOW.md`/`docs/DefinitionOfDone.md` for
documentation-only work"). This report does **not** say "QA passed" and does not substitute for that
independent review. The QA Reviewer is specifically asked to independently verify, against the PR's
actual remote HEAD (not this local report):

- That `PROJECT_WORKFLOW.md` §3.2's 14 conditions genuinely preserve, without weakening or
  narrowing, every one of the T104 authorization row's ten numbered conditions and its A–I threshold
  test — condition-by-condition, not by trusting this report's own "consolidated, nothing dropped"
  claim in §4.
- That §3.2 does not state or imply "a GitHub Issue is equivalent to `IMPLEMENTATION_QUEUE.md`
  authorization" for numbered work — only for the narrow documentation-only class it defines.
- That §3.2's anti-loophole rule genuinely closes the "split substantive work into apparently
  documentation-only steps" risk, and genuinely states that changing governance process itself is
  never Option-A-eligible.
- That §3.2's History paragraph does not retroactively authorize, renumber, or reinterpret `Issue
  #167`, `PR #168`, or `PR #169` — and does not claim `PR #169` has merged (it was open, unmerged,
  at the time of this report; QA should re-check its actual current state at review time).
- That the diff is exactly `PROJECT_WORKFLOW.md` (insertion-only) plus this report — no other file.
- That `T103`'s status, `PROJECT_STATE.json`, and `IMPLEMENTATION_QUEUE.md` are genuinely untouched.
- That the governance validator and full test suite pass on the PR's actual remote HEAD, not merely
  as reported here.

**This PR must not be merged until that QA Decision exists on its actual remote HEAD.**

## QA Decision

☐ Approved
☐ Approved with comments
☐ Rework required

This Software Architect pass does not record, anticipate, or imply any of the three outcomes above.
`PROJECT_WORKFLOW.md` §3.2 and this report are not self-certifying.

---

**This report ends T104's Amendment phase at the drafting handoff.** T104 stops here, awaiting
independent, pre-merge QA. No further action (opening/merging this PR without a persisted QA
Decision, creating `T105`, marking `T104` Done, Governance Closeout, or authorizing Organization/
Tenant Core or any other implementation) is taken by this pass.
