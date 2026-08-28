# Definition of Done

The bar a piece of work must clear before it's actually finished — not "Ready for QA" (that's the
Reviewer Checklist's job) and not "the QA Reviewer signed off" (that's the QA Decision's job), but
everything those two plus the surrounding process require, all together. Applies to a completed
implementation batch/phase, a pull request, or a release — whichever unit of work is being closed
out.

## How this relates to the Reviewer Checklist and QA Decision

Both live in [docs/ImplementationLog/README.md](ImplementationLog/README.md) and are **inputs** to
this checklist, not duplicated here:

- The **Reviewer Checklist** is the implementer's own self-assessment, ending in "Ready for QA."
- The **QA Decision** is the QA Reviewer's independent gate on top of that — `Approved` /
  `Approved with comments` / `Rework required`.
- **This document** is the outer gate: it assumes both of the above already happened, and adds the
  process/release mechanics (CI, merge, release notes) that sit outside any one phase log.

Don't check anything below until the Reviewer Checklist and QA Decision it depends on are actually
filled in — this checklist isn't a substitute for either.

## Checklist

- [ ] **Feature implemented.** The work described in the task/phase's Objective actually exists in
      the code, not just planned or partially built.
- [ ] **Acceptance criteria met.** Every acceptance criterion `IMPLEMENTATION_QUEUE.md` (or the
      equivalent planning document) defined for this work is satisfied — checked against the
      criteria themselves, not inferred from "the tests pass."
- [ ] **Unit tests added.** New behavior has new tests, not just reliance on existing coverage
      happening to exercise it.
- [ ] **Existing tests pass.** The full suite was actually re-run, not assumed — cite the pass
      count.
- [ ] **QA Decision is `Approved` or `Approved with comments`.** A `Rework required` decision means
      this checklist cannot be started yet — see
      [docs/ImplementationLog/README.md#qa-decision](ImplementationLog/README.md#qa-decision).
- [ ] **Documentation synchronized.** Every document this work affects reflects reality — at minimum
      whichever of `docs/ProjectStatus.md`, `docs/AI_HANDOVER.md`, `docs/SessionReport.md`,
      `PROJECT_STATE.json`, and the changelogs apply (see
      [Documentation Ownership](ImplementationLog/README.md#documentation-ownership) for who's
      responsible).
- [ ] **ADR created if required.** A significant architectural decision has a corresponding ADR in
      [`/ADR`](../ADR/); check this box as N/A (not failed) if this work made no such decision.
- [ ] **GitHub Actions pass.** All four CI workflows (`backend.yml`, `frontend.yml`,
      `release.yml`, `governance.yml`) are green on the commit/PR being closed out — see
      [ADR/0017](../ADR/0017-github-actions-ci.md) and
      [docs/GOVERNANCE_VALIDATION.md](GOVERNANCE_VALIDATION.md) (T95) for what `governance.yml`
      specifically checks. **A green `governance.yml` run is necessary, not sufficient** — it
      catches objectively-checkable text inconsistencies only; it is not a substitute for the
      independent QA Decision this checklist's other boxes still require.
- [ ] **Pull request merged.** If this project's branch-per-unit-of-work convention was used for
      this work, the PR is actually merged, not just approved and left open.
- [ ] **Release notes updated (if applicable).** If this work ships as (or as part of) a tagged
      version, `docs/releases/vX.Y.Z.md` and `docs/releases/LATEST.md` reflect it — see
      [docs/releases/README.md](releases/README.md). Not every completed batch ships a release
      immediately; check N/A if this one doesn't.

Leave a box unchecked rather than mark it done to move faster — an honest unchecked box with a
reason noted is more useful than a falsely checked one, the same discipline every other checklist
in this project's documentation set follows.
