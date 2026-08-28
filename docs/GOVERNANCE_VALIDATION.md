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
3. **ADR filename/header integrity.** Each `ADR/NNNN-slug.md` file's leading `# ADR-NNNN: ...`
   header number must match its filename number, and no two files may share a filename number.
4. **No duplicate Required-ADR resolution.** Each ADR file's own `**Resolves:**` field is parsed for
   `#N` references (only inside that field, not the whole file, so `**Does not resolve:**` and
   `**Dependencies:**` prose mentioning other Required ADR numbers is never misread as a resolution
   claim). No two different ADR files may claim to resolve the same Required ADR number.
5. **No dangling `ADR/NNNN` references.** Every `` `ADR/NNNN...` `` reference inside
   `IMPLEMENTATION_QUEUE.md` must name a file that actually exists in `ADR/`.
6. **`PROJECT_STATE.json` governance-ledger drift.** If `PROJECT_STATE.json` has a
   `governanceLedger.resolvedRequiredADRs` / `.unresolvedRequiredADRs` pair, both are cross-checked
   against what is dynamically computed from the ADR files themselves at validation time. The field
   is optional — its absence is not an error — but if present, it must stay accurate.

Run `python scripts/governance_validate.py --report` for a plain-language "which Required ADRs are
resolved, by which file" summary — the fast, mechanically-verified answer to a question this
repository's own governance history (see `T93`/`T94`) has shown is easy to get wrong by hand.

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
