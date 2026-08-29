# Governance Validation (T95)

What `scripts/governance_validate.py` mechanically checks, what it deliberately does not, and how it
relates to the human/AI governance process this repository already follows. This document exists so
that reading it — not trusting a PR description or a chat summary — is enough to know exactly what
the automated gate does and does not guarantee.

## Authoritative sources (unchanged by T95)

This tool validates the repository's existing sources of truth; it does not become a new one and
does not replace any of them:

| Artifact | Still the authority for |
|---|---|
| `IMPLEMENTATION_QUEUE.md` | Task backlog, authorization, and completion narrative — owned by the Project Manager role (`PROJECT_WORKFLOW.md`). |
| `ADR/*.md` | Accepted architecture decisions and exactly what each one resolves/defers. |
| `docs/Legal_DMS — Domain Model & Functional Specification.md` | The frozen business/domain baseline, including the §21 Required-ADR planning list. |
| `docs/reviews/*.md` | Per-task Software Architect self-review and QA Decision history. |
| `PROJECT_STATE.json` | Point-in-time snapshot. Its narrative `note` fields remain the authoritative historical record. This task adds one new, optional, structured field (`governanceLedger`) — see below. |

If `governance_validate.py`'s output ever disagrees with what a human/AI reader concludes from
reading these files directly, **trust the files and treat the validator's disagreement as a bug
report against the validator**, not the other way around. The validator computes a *derived* view
(e.g., which Required ADRs are resolved) from the ADR files' own text; it does not decide anything
architectural itself, and per its own design must not (see "What this deliberately does not
validate" below).

## What this validates

Run `python scripts/governance_validate.py` from anywhere inside the repository (it walks upward to
find `IMPLEMENTATION_QUEUE.md`). Exit code `0` means no errors; non-zero means at least one check
below failed, with every violation printed, not just the first.

1. **Duplicate task IDs.** No two rows in `IMPLEMENTATION_QUEUE.md` may claim the same `TNN` — task
   IDs are immutable per `AI_BOOTSTRAP.md`.
2. **Done requires authorization evidence in the same row.** If a row contains
   `"TNN is now Done"`, that same row must also contain the phrase `"Authorized by the project
   owner"`. This is a heuristic tied to this repository's own established convention — verified
   present on every Done row from `T4` through `T94` when this check was written — not an assumption
   about how governance *should* be written elsewhere. It exists specifically because T94 was once
   authorized only conversationally, with no corresponding row at all; this check catches the
   textual shape of that defect (a Done claim with no authorization phrase anywhere in its own row),
   though see the limitation below — it cannot catch every variant of that defect.
3. **Done requires a QA Decision mention in the same row.** Same shape as check 2, requiring the
   phrase `"QA Decision"` (case-insensitive) instead — verified present on the same `T4`–`T94` rows.
   `docs/DefinitionOfDone.md` already requires a QA Decision before closeout; this makes that
   requirement mechanically checkable, not just documented.
4. **ADR filename/header integrity.** Each `ADR/NNNN-slug.md` file's leading `# ADR-NNNN: ...`
   header number must match its filename number, and no two files may share a filename number.
   Non-numbered files (e.g. `ADR/template.md`) are silently skipped, not flagged.
5. **No duplicate Required-ADR resolution.** Each ADR file's own `**Resolves:**` field is parsed for
   `#N` references (only inside that field, not the whole file, so `**Does not resolve:**` and
   `**Dependencies:**` prose mentioning other Required ADR numbers is never misread as a resolution
   claim — and an ADR whose *body* extensively discusses a Required ADR's subject matter without
   naming it in `**Resolves:**` is never inferred to resolve it; see
   `test_topic_similarity_does_not_imply_resolution`). No two different ADR files may claim to
   resolve the same Required ADR number.
6. **No dangling `ADR/NNNN` references.** Every `` `ADR/NNNN...` `` reference inside
   `IMPLEMENTATION_QUEUE.md` must name a file that actually exists in `ADR/`.
7. **`PROJECT_STATE.json` governance-ledger drift.** `PROJECT_STATE.json`'s optional
   `governanceLedger` object has four independently-optional sub-fields, each cross-checked only if
   present (declaring one does not require declaring the others):
   - `resolvedRequiredADRs` / `unresolvedRequiredADRs` — checked against what is dynamically computed
     from the ADR files' own `**Resolves:**` fields.
   - `latestTaskDone` / `latestTaskAuthorized` — checked against the highest-numbered
     `IMPLEMENTATION_QUEUE.md` row whose own text actually contains `"TNN is now Done"` /
     `"Authorized by the project owner"`, respectively — not a hand-maintained guess.
   The whole `governanceLedger` object is optional; its absence is not an error, but any sub-field
   present must stay accurate. See "In-progress transition declarations" below for the one narrow,
   mechanically-verified exception to "must stay accurate at all times."

Run `python scripts/governance_validate.py --report` for a plain-language "which Required ADRs are
resolved, by which file" summary — the fast, mechanically-verified answer to a question this
repository's own governance history (see `T93`/`T94`) has shown is easy to get wrong by hand.

## In-progress transition declarations (T99)

**The problem this solves.** `PROJECT_WORKFLOW.md` §3.1's three-PR Required-ADR lifecycle
deliberately synchronizes `governanceLedger` only in the third PR (Governance Closeout), *after* the
second PR (Architecture+QA) has already merged the new ADR file. Between those two merges, check 7
above correctly detects a real, mechanical mismatch — the ADR files now resolve one more Required ADR
than the ledger records — and reports it as an `ERROR`. That mismatch is completely expected and
intentional under the lifecycle's own design, yet `.github/workflows/governance.yml`'s "Governance
consistency validation" job is a required status check on protected `main`, so an Architecture+QA PR
for *any* Required-ADR task fails a required check it can never itself fix (fixing it is explicitly
the *next* PR's job) — a structural incompatibility between two already-correct mechanisms, first
named as its own remediation task by `T99`.

**The mechanism.** An Architecture+QA PR may add exactly one object to
`governanceLedger.inProgressTransitions` (a list, so its cardinality is itself checkable) declaring
the ADR-resolution gap *that specific PR* introduces:

```json
"inProgressTransitions": [
  { "task": "T41", "requiredAdrs": [7] }
]
```

`scripts/governance_validate.py`'s `validate_in_progress_transition()` grants no leniency at all
unless **every** one of the following holds, checked purely against text already parsed from
`IMPLEMENTATION_QUEUE.md` and the ADR files themselves — never git history, never a literal task/ADR/
PR number:

- The list has **exactly one** entry — zero means no declaration (ordinary behavior); more than one
  is `governance-transition-ambiguous` and grants no exemption to either.
- The entry is well-formed — `task` matches `T\d+`, `requiredAdrs` is a non-empty list of integers
  inside the valid planning-list range — otherwise `governance-transition-malformed` /
  `governance-transition-invalid-adr-state`.
- `task` names a row in `IMPLEMENTATION_QUEUE.md` that actually contains `"Authorized by the project
  owner"` — otherwise `governance-transition-unauthorized`.
- `task` **is** the current frontier — equal to what `latestTaskAuthorized` independently computes —
  not an older or unrelated authorized task; otherwise `governance-transition-wrong-task`.
- `task`'s own row does **not** already contain `"TNN is now Done"` — a completed task has no
  in-progress transition left to explain, that window closed at its own Closeout; otherwise
  `governance-transition-already-settled`.
- `requiredAdrs` is **exactly** the real gap (`resolved` computed from ADR files, minus the ledger's
  current `resolvedRequiredADRs`) — not a superset (which would excuse unrelated drift) and not a
  subset (which would leave a real, unexplained mismatch); otherwise
  `governance-transition-scope-mismatch`.

Only when all of these hold does check 7 treat the declared `requiredAdrs` as expected, temporary
drift: `resolvedRequiredADRs`/`unresolvedRequiredADRs` are compared with that gap folded in, and a
`latestTaskAuthorized` mismatch is excused *only* when it is explained by that same validated
transition. **`latestTaskDone` is never exempted, under any declaration** — Closeout's own
zero-tolerance settled-state requirement is unaffected by this mechanism entirely.

**Who adds and removes it.** The Software Architect's Architecture+QA PR adds the single entry
alongside the ADR file it justifies (this is *not* the "ledger synchronization" `PROJECT_WORKFLOW.md`
§3.1 reserves for Governance Closeout — it is a distinct, additive, self-justifying declaration of
*why* synchronization hasn't happened yet, independently checked, not merely asserted). QA
independently re-verifies the declaration is accurate, the same as any other content in that PR. The
Governance Closeout PR removes the `inProgressTransitions` entry entirely as part of performing the
real synchronization — leaving it in place after Closeout is itself now a detected violation
(`governance-transition-already-settled`).

**What this deliberately does not do.** It does not know about, name, or special-case any specific
task, ADR, or PR number — `scripts/tests/test_governance_validate.py`'s
`TestInProgressTransition.test_mechanism_is_generalized_not_hard_coded_to_any_specific_task_or_adr`
inspects the function's own source to confirm no such literal exists, not merely that a few examples
happen to pass. It does not weaken `check_governance_ledger` for any state other than the one, single,
currently-declared, evidence-backed transition. It does not touch git ancestry verification, which
remains exactly as out of scope as described below.

## What this deliberately does not validate

This is a **text-consistency** checker over the repository's content at a single commit. It does
**not**:

- **Check git ancestry.** Whether a PR branch actually contains its authorization commit — the
  exact class of defect a Project Manager pre-merge gate caught twice during `T94` (once when
  authorization existed only in conversation, and again when the architecture branch had not
  actually merged the recorded authorization) — is not something a static text check at a single
  commit can see. That remains a Project Manager pre-merge-verification responsibility, done against
  the live repository/GitHub state with `git merge-base --is-ancestor` and equivalent commands. Do
  not treat a clean `governance_validate.py` run as ancestry-clean.
- **Render or substitute for a QA Decision.** Passing this validator is necessary but not
  sufficient for any task's closeout — `docs/DefinitionOfDone.md` and the established `T80`–`T95`
  pattern still require an independent, human/AI QA Reviewer decision on the actual content, not
  merely on whether the text is internally consistent.
- **Decide unresolved architecture.** If a Required ADR is unresolved, the validator reports it as
  unresolved — it never infers, guesses, or fills in what an unresolved decision "probably" is. Per
  T95's own authorization boundary, this tool must not invent architectural conclusions.
- **Detect every phrasing of a missing-authorization defect** — only the specific, observed textual
  shape described in check 2 above. A row that is Done, contains some other authorization-sounding
  text, but not this exact phrase, would not be flagged; a human/AI reviewer's judgment is still the
  backstop, not a replacement target.
- **Distinguish an assertion from a narrative mention.** Checks 2 and 3 are pure substring matching
  — if the authorization phrase or "QA Decision" appears *anywhere* in a Done row's text, even while
  narrating or quoting a different task's history (the way `T94`'s own row quotes its prior defect),
  the check passes. It cannot tell "this task IS authorized" apart from "this task discusses what
  authorization means." See
  `test_known_limitation_narrative_mention_is_not_distinguished_from_assertion` for the exact
  accepted behavior — documented as a known limitation, not silently assumed away.
- **Check implementation-before-authorization ordering**, task-sequencing "depends on" correctness
  beyond what's stated in a row's own text, or any application/business logic. Out of `T95`'s
  authorized scope entirely.

## Where this runs

`.github/workflows/governance.yml` runs the validator's own test suite
(`scripts/tests/test_governance_validate.py`) and then the validator itself, on every push and pull
request against `main` — deliberately stdlib-only and independent of `backend/`'s or `frontend/`'s
dependency graph, so a documentation-only or governance-only change gets fast, real content
validation instead of only a trivially-passing, unrelated CI run.

## Extending this

Each check is a small, independently-testable function in `scripts/governance_validate.py` — new
checks should follow the same shape: a pure function taking parsed data in and returning
`Violation` objects out, with both a positive and a negative test in
`scripts/tests/test_governance_validate.py`. Prefer checks that hold structurally (e.g., "field X
must equal a value computed from field Y") over checks that depend on one exact sentence surviving
verbatim in future prose, per this task's own governing instruction.
