# T99 Governance Closeout — Post-QA Correction

**Task:** T99 — Governance Lifecycle / Required-CI Compatibility Remediation

**PR:** #152 (`docs/t99-governance-closeout` → `main`)

**Date:** 2026-08-29

## Purpose

This is a narrow correction to the T99 Governance Closeout record. It does **not** change
T99's substantive implementation, its closeout state, or the GitHub ruleset.

The original closeout QA record was accurate as of the state it independently verified, but its
wording that the `main-required-ci` ruleset was "unmodified" could be read as a continuing
assertion about later repository state. That wording is now explicitly time-scoped.

## Corrected ruleset statement

The `main-required-ci` ruleset was verified unchanged **at the time of the T99 closeout
verification**. That verification was a snapshot, not a claim that the ruleset could not or would
not subsequently change.

Subsequent ruleset changes are separate Project-Owner-authorized repository-configuration actions
and are outside the file changes made by T99's closeout PR:

- `required_approving_review_count`: `1` → `0`
- Required contexts: `Frontend` / `Backend` / `Release` →
  `Frontend validation` / `Backend validation` / `Release build verification`
  (with `Governance consistency validation` unchanged)

The current required contexts correspond to the current workflow job names. These later ruleset
changes therefore must not be described as T99 implementation, T99 closeout work, or an
unauthorized weakening performed by PR #152.

## Audit interpretation

The original closeout record remains a historical record of what was verified at its stated
verification point. This correction prevents that historical snapshot from being interpreted as a
perpetual guarantee about the ruleset's later state.

No restoration or rollback is authorized or performed by this correction. No ruleset API write is
part of this commit. PR #148/T98 remains outside T99 closeout scope, and no T100 is created.

## Scope

Only this correction document is added by this commit. No implementation file, ADR,
`PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, workflow, or GitHub ruleset is changed by this
correction itself.

## Timing clarification — 2026-08-30

**Authorized by the project owner, 2026-08-30, recorded here as its own narrow, append-only,
documentation-only addition — no implementation beyond this addition is authorized or performed by
it.**

This section clarifies the timing of the two ruleset changes described above, using the
independently-verified ruleset version history already recorded in
`docs/reviews/T99_Governance_Closeout_Correction_QA_Review.md` §5. It does not change, retract, or
supersede any statement above; it narrows the reading of one phrase ("Subsequent ruleset changes")
that could otherwise be misread as describing changes occurring after T99's closeout verification.

Ruleset version history (`main-required-ci`, ruleset `21745493`), as independently confirmed against
`gh api repos/.../rulesets/21745493/history`:

1. Version `47981544`, created 2026-08-28 21:38:36 — `required_approving_review_count: 1`; required
   contexts `Frontend`, `Backend`, `Release`, `Governance consistency validation`.
2. Version `48039365`, 2026-08-29 15:55:20 — `required_approving_review_count` changed `1` → `0`.
3. Version `48040166`, 2026-08-29 16:22:39 — three required contexts renamed to `Frontend
   validation`, `Backend validation`, `Release build verification` (`Governance consistency
   validation` unchanged).

Both changes (2) and (3) therefore occurred **before** every closeout-verification read documented
in this task's own QA trail — the earliest of those reads (during the original PR #150/T99 QA task)
already observed the post-change state. Neither change occurred after T99's closeout verification.

Consequently, "Subsequent ruleset changes" in the corrected ruleset statement above means subsequent
to the ruleset's original creation (version `47981544`, 2026-08-28 21:38:36) — not subsequent to
T99's closeout verification. No statement above is thereby shown to be inaccurate: neither claims a
specific ordering relative to the closeout verification beyond what the version history in fact
shows.

No repository PR under T99 or T100 caused, authorized, or performed either ruleset change; both
remain, as stated above, separate Project-Owner-authorized repository-configuration actions outside
T99's and T100's own file changes. A later ruleset remediation restored
`required_approving_review_count` to `1` (independently confirmed live, `gh api
repos/Intelligentclown/Legal_DMS/rulesets/21745493`, `updated_at: 2026-08-30T15:38:10`, alongside
unchanged `bypass_actors: []` and `current_user_can_bypass: never`); that remediation is itself
outside this correction's scope and is not described further here.

**Further historical disclosure — PR #154 merge-time ruleset state.**

Independent inspection of the same ruleset version history reveals one additional intermediate
version not previously described in this correction:

4. Version `48082147`, active 2026-08-30 09:16:38 +05:30 — `required_approving_review_count`
   restored to `1`; `bypass_actors` set to `[{"actor_id": 5, "actor_type": "RepositoryRole",
   "bypass_mode": "always"}]`; `current_user_can_bypass: "always"`. This version remained active
   until version `48093097`, 2026-08-30 15:38:10 +05:30.

PR #154 (`docs/t100-frontier-generalization`, merge commit
`3768348e9cecfb48b848c0bf67a35b17b77fb8f3`) merged at 2026-08-30 09:21:06 +05:30 (`03:51:06Z`) —
independently confirmed via `gh pr view 154`. This merge timestamp falls inside version
`48082147`'s active window (09:16:38–15:38:10), not the earlier `48040166` window this correction
and T100's own closeout entry otherwise describe. At the moment PR #154 merged:

- the ruleset required one approving review (`required_approving_review_count: 1`), not zero;
- `gh pr view 154 --json reviews` returns zero review submissions (`reviews: []`);
- a repository-role bypass actor with `bypass_mode: "always"` was configured, and
  `current_user_can_bypass` read `"always"` for that role.

This established bypass *authority* was directly available at the exact merge moment. It does not
by itself establish that the bypass mechanism was actually invoked to merge PR #154: no direct
audit-log record proving invocation is available from the repository or account evidence examined
for this correction. The observed facts — a required review that was not satisfied, combined with a
successful merge, combined with an available always-on bypass actor at that instant — are consistent
with, and are the strongest available inference from, bypass having been used; they are not
independent proof of it. No specific human or agent is identified as having performed any bypass
action; none is attributed here.

This also means T100's own closeout entry, which explains PR #154's zero review submissions as
"consistent with `required_approving_review_count` currently being `0`," describes the mechanism
correctly for the ruleset state at other points in this history but not for the ruleset state at PR
#154's own actual merge instant, which this correction now separately discloses. This is a factual
completion of the historical record, not a correction of T100's own diff, scope, or QA outcome, and
does not reopen T100.

Version `48093097` (2026-08-30 15:38:10 +05:30) removed the bypass actor entirely
(`bypass_actors: []`) and restored `current_user_can_bypass: "never"`, alongside the
already-disclosed restoration of `required_approving_review_count` to `1`. This is the current, live
ruleset state, independently re-confirmed via `gh api repos/Intelligentclown/Legal_DMS/rulesets/21745493`
as of this addition. No further ruleset remediation is authorized, recommended, or performed by this
correction.

This bypass-authority window and PR #154's merge-time state were both previously omitted from this
correction record. Neither T99's nor T100's own repository file changes caused, modified, or are
responsible for any version in this ruleset history, including version `48082147`. This addition is
a historical disclosure only; it does not reopen T99 or T100, does not modify either task's row
content, and does not authorize, recommend, or perform any change to the current ruleset, which
remains as independently confirmed above.

This clarification is itself a narrow, append-only addition. It does not modify, delete, or
reinterpret any sentence written above it; it adds explicit timing context that was previously
verified only in QA-record form, not in the correction document itself.
