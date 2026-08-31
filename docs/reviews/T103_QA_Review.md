# T103 QA Review

**Record type:** This is a **genuine pre-merge QA Decision**, rendered and persisted on PR #165's
actual remote HEAD before that PR is merged — explicitly restoring the discipline `T101`/PR #158 and
`T102`/PR #162 both departed from, exactly as `T103`'s own authorization row requires. This record does
not treat the Software Architect's "Ready for QA" checklist item, nor `docs/reviews/
T103_Software_Architect_Report.md`'s own explicit disclaimer that it "does not record, anticipate, or
imply" a QA outcome, as evidence that QA has passed — every finding below was independently re-derived
from the actual repository and GitHub state.

**Task:** T103 — User/Organization Pre-Existing-Data Reconciliation (narrow slice of Required ADR #20).

**Authorization:** commit `7fa7c10` (`docs(governance): authorize T103...`), plus pre-merge ledger-sync
commit `e05ce31`, both merged via PR #164 as `e9550ae2a4322ee9da69e6fa4b24e2f76b9573ba`.

**PR under review:** #165 (`docs/t103-adr-0032-user-organization-reconciliation` → `main`).

**Reviewed commit — the current required review HEAD, exactly:**

```
367cace51701f5bd9ef3983ff8994ff320b41385
```

The superseded original draft (`4fb36c874a76941cad0d94e2704d56a84d085612`) was **not** reviewed or
approved by this record. If PR #165's branch changes after this review, this QA Decision must be
reconsidered against the new HEAD before merge.

**Date:** 2026-08-31.

---

## Governance findings

- `gh pr view 165`: `state: OPEN`, `mergedAt: null`, `closed: false` — **not merged**, independently
  observed via live GitHub API, not assumed.
- `baseRefOid: e9550ae2a4322ee9da69e6fa4b24e2f76b9573ba` — confirmed identical to live `origin/main`
  (`git rev-parse origin/main`), which is itself PR #164's own merge commit (T103's authorization).
- `headRefOid: 367cace51701f5bd9ef3983ff8994ff320b41385` — confirmed to match the mandated review
  target exactly (`git rev-parse HEAD` on the checked-out branch).
- `git merge-base --is-ancestor 7fa7c10 367cace...` → succeeds. **Authorization ancestry: confirmed.**
- Live CI on the exact reviewed SHA (`gh api repos/.../commits/367cace.../check-runs`): all four
  required checks — `Backend validation`, `Frontend validation`, `Release build verification`,
  `Governance consistency validation` (×2, push/PR triggers) — `completed`/`success`.
- `main-required-ci` ruleset (read-only): `enforcement: active`, `required_approving_review_count: 1`,
  `bypass_actors: []`, `current_user_can_bypass: "never"`, four required contexts matching the live
  check-run names exactly. Not modified by this review.
- `python scripts/governance_validate.py` (run fresh on the exact reviewed HEAD) →
  `OK (0 warning(s), 0 errors)`.
- `python scripts/tests/test_governance_validate.py -v` (run fresh) → **51/51 passing.**
- This QA Decision is being persisted **now, before merge** — PR #165 remains `OPEN`/`mergedAt: null`
  at the time this record is committed, independently reconfirmed immediately before writing it.

## Scope findings — exact changed-file verification

`git diff --name-only e9550ae..367cace` (PR #165's actual base to its actual current HEAD) — exactly
two files:

- `ADR/0032-user-organization-pre-existing-data-reconciliation.md`
- `docs/reviews/T103_Software_Architect_Report.md`

Independently confirmed absent from the diff: `IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, any
`ADR/0001`–`ADR/0031` file, `backend/pyproject.toml`, any `backend/`/`frontend/`/`electron/` file, any
migration, any workflow file, any deployment configuration. No `T104` row exists
(`grep -c "^| T104" IMPLEMENTATION_QUEUE.md` → `0`) and no `T104` branch exists anywhere. **Scope
matches the Software Architect's own report exactly — no discrepancy found.**

## Architecture findings

Independently read `ADR/0032` in full (not summarized) and cross-checked every specific claim against
the actual cited source, not the ADR's own narrative:

- **T83 evidence** — independently located in `IMPLEMENTATION_QUEUE.md`'s T83 row: *"`uv run
  bootstrap-admin` command exactly once against the local dev database (`legal_dms_dev`): 0 `User` rows
  before, exactly 1 after, with exactly one Administrator-role assignment"* — an already-independently-
  QA'd fact (T83's own row records QA independently re-verifying this read-only), not a fresh assertion.
  This confirms the reconciliation *problem* is real and non-theoretical, exactly as §3a's own careful
  framing states ("evidence the problem is real, not evidence for a universal migration rule").
- **`BusinessRequirementsPlan.md` quote** — independently located verbatim: *"the system is not scoped
  to a single practitioner and is intended for use by multiple users/practices once complete."*
  Confirmed accurate, not selectively edited.
- **`ADR/0021`'s "single legal-documentation office" language** — independently read in full context
  (§3 "Schema-per-tenant," "Deployment-model fit" subsection): the phrase is explicitly framed as an
  assumption about *deployment scale* (justifying shared-schema over schema-per-tenant/database-per-
  tenant on *operational-cost* grounds), not a claim that only one Organization/tenant exists. `ADR/0032`
  §3a's reading of this passage is accurate, not a strained reinterpretation — independently confirmed
  by reading the surrounding paragraphs, not the isolated phrase alone.
- **`ADR/0021`'s hybrid enforcement mechanism** — independently confirmed the file actually describes
  mandatory non-nullable `organization_id`, `FORCE`d default-deny RLS, and an explicit multi-tenant
  isolation design. `ADR/0032`'s argument that this entire mechanism would be unnecessary for a
  genuinely single-tenant product is architecturally sound, not asserted without support.
- **`bootstrap.py` precedent** — independently read in full: `run_bootstrap()`'s idempotency check
  (`_any_user_exists()`), `flush()`-only repository writes, caller-owned commit in `main()`/
  `_async_main()` — the mechanism §3b/§13 describes as the pattern this reconciliation command mirrors
  matches the actual current file exactly.
- **`ADR/0020`'s transaction policy** — independently re-read: `get_db()` commits on success, rolls
  back on exception; repositories remain `flush()`-only — matches `ADR/0032` §8's atomicity claim.
- **`ADR/0018` D4** — independently confirmed (interactive-only, no argv/env/config credential
  exposure) — used only as a cited precedent for interactive input, not altered.

**Architecture verdict: technically sound and internally consistent.** The mechanism (dedicated
interactive CLI, mirroring `bootstrap-admin`'s established shape; explicit operator-supplied mapping
of every `NULL`-organization `User` row to one or more Organizations; atomic; idempotent; separate from
Alembic) follows directly from the evidence cited, and every citation independently checks out against
the actual repository state, not merely the ADR's own account of it.

## Tenant/Security findings — mandatory multi-tenancy review

Each specific question independently assessed against `ADR/0032`'s actual text:

- **Can two legacy practices be silently merged?** No — §3b/§7/§14 state explicitly and repeatedly that
  every `NULL`-organization `User` row must be explicitly mapped by the operator; §7 states "none may be
  silently defaulted, silently skipped, or silently grouped by an inferred heuristic." No code path in
  the described mechanism produces an assignment without operator confirmation.
- **Can a User be assigned to an Organization without explicit operator confirmation?** No — this is the
  central safety property §3b states as an explicit constraint ("it must never produce an
  Organization-to-User assignment without the operator having explicitly confirmed which Users belong to
  which Organization").
- **Is there any inferred grouping rule?** None — independently verified the actual current `users`
  table schema (`backend/src/app/infrastructure/persistence/models/identity.py`, read in a prior
  session-turn's direct inspection and re-confirmed here has no tenant-adjacent column today beyond the
  reconciliation column itself under discussion) — §3b/§4's claim that "no automatic grouping heuristic
  is even technically possible without inventing unevidenced data" is accurate, not merely asserted.
- **Does the architecture accidentally reintroduce the withdrawn single-Organization assumption
  elsewhere?** Independently re-read the full document (§1 through References) — no remaining section
  asserts or presumes a single-Organization outcome; §5's "Consequences," §6's "Migration/Reconciliation
  Semantics," and §14's "Acceptance Criteria" all explicitly state the Organization count is
  operator-determined, not architecturally fixed. The withdrawn assumption does not resurface anywhere
  outside the explicitly-marked historical §3 REWORK NOTICE block.
- **Is "one User → at most one Organization" from `ADR/0031` preserved?** Yes — §10 states this
  directly and §3a's own argument (cardinality is orthogonal to total-Organization-count) is
  independently sound: fixing that each User has at most one Organization says nothing about how many
  Organizations exist in total, and the reconciliation mechanism never assigns more than one
  Organization to any single User row.
- **Does the decision remain compatible with multiple Organizations in one database?** Yes — this is
  the entire point of the correction; §3b/§4/§6/§14 all explicitly design for and test against a
  multi-Organization outcome, not merely tolerate it.

**Tenant/Security verdict: the corrected mechanism genuinely protects against cross-practice tenant
collapse.** This is not a superficial reading of the ADR's own safety claims — the specific mechanism
by which no inference is possible (no tenant-adjacent column exists on the pre-reconciliation schema)
was independently verified against the actual current schema, not accepted as asserted.

## Business-decision boundary

The ADR decides the **mechanism** (require explicit, per-row operator confirmation before any
Organization assignment) — an architectural decision about how the system behaves under uncertainty.
It does **not** decide **which real-world practice any specific legacy User belongs to** — that fact is
explicitly and permanently deferred to operator input at run time, in every scenario, including the
common single-practice case. §3b's own text states this distinction explicitly and correctly: an
operator "entering that mapping is fundamentally different from the architecture deciding, as a rule,
that all Users necessarily belong to one Organization." **Independently confirmed: no unsupported
business assumption is embedded in the corrected mechanism.** (The withdrawn original version did embed
such an assumption — correctly identified and corrected by the rework, as intended.)

## Alternatives review

Six alternatives (five plus the selected mechanism) independently checked against `ADR/0032` §4's
table, not merely counted:

- **Automatic single-Organization backfill** (the withdrawn original decision) — correctly rejected on
  rework, for the reason independently confirmed above (tenant-isolation failure mode).
- **Explicit operator mapping** (selected) — correctly identified as superior specifically because it
  is the only alternative in the table that satisfies the tenant-isolation criterion without
  sacrificing any other named criterion (data integrity, bootstrap continuity, idempotency,
  auditability all unchanged from the withdrawn version).
- **Embedded interactive Alembic migration** — reasonably rejected; this repository's migrations are
  independently confirmed non-interactive by convention (every existing migration file inspected in
  prior review passes this session contains no interactive prompt).
- **Heuristic grouping from existing data** — correctly rejected; independently confirmed no
  tenant-adjacent column exists on the pre-reconciliation schema for any heuristic to key off.
- **Indefinite `NULL` state** — correctly rejected; directly contradicts `ADR/0021`'s independently
  re-confirmed fail-closed principle.
- **Placeholder/synthetic Organization** — correctly rejected; would both invent an unapproved identity
  and (now, post-rework) risk merging distinct practices into it.

**No alternative in the table is a strawman added merely for length** — each is a genuinely distinct
mechanism with its own named failure mode, and the rejected alternatives were rejected for reasons
independently verifiable against actual repository facts (migration-file convention, schema content,
`ADR/0021`'s actual text), not merely asserted.

## Migration/data-integrity review

- **All legacy `NULL` Users accounted for** — §7 states this as a hard requirement ("must be explicitly
  accounted for by the operator's mapping before the transaction commits").
- **No partial assignment survives a failed operation** — §8 states the atomicity guarantee explicitly
  and correctly identifies that a partial multi-Organization mapping would be a *worse* failure mode
  than the withdrawn single-Organization version's partial state (some Users correctly isolated, others
  not) — a genuine, non-trivial safety observation, not boilerplate.
- **Coherent transaction boundary** — composes directly with the independently-re-verified `ADR/0020`
  commit/rollback policy; Organization creation and User assignment occur in one transaction.
- **Rerunning after success is safe** — §3b/§14 both state the idempotency check correctly: a database
  with zero `NULL`-organization rows is a no-op. **"Idempotent" is used correctly** here — the property
  claimed (repeated invocation with no unwanted additional effect once the target state is reached) is
  exactly what the described mechanism provides; it is not confused with the different-and-narrower
  property of "does nothing on a second matching run" in some looser sense.
- **Fresh `ADR/0031`-era bootstrap never needs this reconciliation** — §5/§14 state this explicitly, and
  it follows directly from `ADR/0031`'s own already-accepted decision that fresh bootstrap always
  creates the Organization/User/membership together — independently confirmed no gap exists between the
  two mechanisms' stated preconditions.
- **No destructive transformation hidden anywhere** — the mechanism is purely additive (create
  Organization rows, set a nullable FK); independently confirmed no `DELETE`, no data loss, no
  irreversible transformation is described anywhere in §3b, §6, §8, or §13.

## Historical rework review

- **Withdrawn decision clearly marked** — `ADR/0032` §3 opens with an explicit, bolded **"REWORK
  NOTICE (2026-08-31)"** paragraph stating the original decision "has been withdrawn," before any
  withdrawn reasoning is presented. The withdrawn text itself is not reproduced verbatim inline in the
  current file (unlike some other ADRs' correction style in this repository) — instead §3's notice
  summarizes what was withdrawn and points to `docs/reviews/T103_Software_Architect_Report.md`'s Rework
  section for the full original account, which itself is clearly headed and dated.
- **Corrected decision unambiguous** — §3b is headed "Corrected Decision" and is the only section in
  `ADR/0032` describing an operative, current mechanism; §§4–14 are all consistent with §3b, not with
  the withdrawn reasoning.
- **Could historical text be mistaken for the active decision?** Within `ADR/0032` itself: no — the
  REWORK NOTICE is the first thing a reader of §3 encounters, and the file contains no other section
  restating the withdrawn single-Organization mechanism as if current. **One non-blocking finding, in
  the companion report, not the ADR:** `docs/reviews/T103_Software_Architect_Report.md`'s own §3
  ("Decision Made," lines 87–106) reproduces the *original, withdrawn* single-Organization decision at
  length, marked as superseded only by the global preamble at the top of the report, not by an inline
  marker at §3 itself. A reader who jumps directly to that report's §3 without first reading its
  "Rework (2026-08-31) — read this first" preamble could be misled about what was actually decided.
  This does not affect `ADR/0032`'s own clarity (which is the governing document) and is not a defect in
  the ADR under review — recorded here as a documentation-hygiene comment for a future editorial pass,
  not a blocking issue.
- **Does governance tooling misinterpret the historical reference as an additional resolution?**
  Independently re-run: `python scripts/governance_validate.py` → `0 errors`; `--report` mode confirms
  `#20  unresolved`. The Architect's own drafting note (independently corroborated, not merely trusted)
  describes catching and removing a bare `#20` digit reference from the `**Resolves:**` field
  specifically because the validator's `RESOLVES_BLOCK_RE` regex reads that field literally — the
  current `**Resolves:**` field was independently re-read (§0 above) and contains no bare `#N` digit
  reference; all such references live in `**Does not resolve:**`, which the validator does not scan.
  **Confirmed: no false-positive resolution is registered.**

## Issues / Required Rework

None blocking. One non-blocking documentation-hygiene comment (above): `docs/reviews/
T103_Software_Architect_Report.md`'s §3 could benefit from an inline "(withdrawn — see rework above)"
marker for a reader who skips the preamble; does not require reworking `ADR/0032` itself.

---

## QA Decision

**ACCEPTED WITH COMMENTS**

`ADR/0032`'s corrected decision (`367cace51701f5bd9ef3983ff8994ff320b41385`) is technically sound,
internally consistent, and within `T103`'s authorization. The multi-tenancy correction is genuine and
independently verified against the actual cited evidence (`BusinessRequirementsPlan.md`, `ADR/0021`'s
actual architecture, the actual current schema) rather than accepted on the ADR's own word. The
business-decision boundary is correctly respected: the ADR decides the reconciliation *mechanism*, not
which real-world practice any User belongs to. Scope is exactly the two authorized documentation files.
Governance validator and full test suite both pass. Live CI is green on the exact reviewed SHA. The one
comment (documentation-hygiene, in the companion report, not the ADR) does not block acceptance.

## Reviewed Commit

```
367cace51701f5bd9ef3983ff8994ff320b41385
```

## Merge Recommendation

**PR #165 may proceed to merge**, subject to this QA Decision continuing to apply to whatever commit is
actually merged — if the branch changes after this record is persisted, this QA Decision must be
reconsidered against the new HEAD before merge, per this task's own governing instruction. This review
does not itself merge PR #165; that remains a separate action for the Governance Control Tower/Project
Manager role, per `PROJECT_WORKFLOW.md`'s own role table.
