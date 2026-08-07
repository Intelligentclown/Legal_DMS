# Documentation Migration Note: T44/T45 Task-ID Reuse

**Purpose:** A single, canonical disambiguation reference for the "T44"/"T45" task-ID reuse
discovered during Stage 3. Every other document that mentions T44/T45 already explains this
locally (see Findings below) — this note exists so a reader who encounters a bare "T44" or "T45"
anywhere in this repository, in a document that *doesn't* already carry that local explanation (a
future QA report, a future ADR, a future session's quick reference), has one authoritative place to
resolve the ambiguity instead of having to already know which of several documents to check.

**Date:** 2026-08-06
**Status:** Informational — explains history, does not change it. No task was renumbered; no
completed log was rewritten.

## What happened

`IMPLEMENTATION_QUEUE.md`'s Stage 3 Phase 0 table originally defined:

- **T44** = "Complete `docs/templates/PreStageChecklist.md` for Stage 3, signed off, stored at
  `docs/reviews/PreStageChecklist_Stage3_<date>.md`."
- **T45** = "Write `ADR-0018` (Authentication & Authorization Architecture — D1–D6) and `ADR-0019`
  (`AuthenticationProvider` interface change — D7)."

On 2026-08-06, a direct project-owner instruction ("batch 2") described different work under those
same two IDs:

- **T44 (redefined)** = add the approved authentication dependencies (`argon2-cffi`, `PyJWT`) and
  `Settings` configuration (`jwt_secret_key`, `jwt_algorithm`, `access_token_ttl_minutes`,
  `refresh_token_ttl_days`).
- **T45 (redefined)** = finalize the `AuthenticationProvider` interface per decision D7
  (`get_current_user(token: str | None)`) and write `ADR-0019` for that specific decision — **not**
  `ADR-0018`.

The discrepancy was flagged to the project owner *before* implementing, per this project's
discrepancy-reporting rule. The direct instruction was treated as the more authoritative source
(explicit, detailed, and more recent than the static planning table), and the work proceeded under
the reused IDs rather than being blocked. `IMPLEMENTATION_QUEUE.md` and
`docs/ImplementationLog/Stage3/Phase0.md` were updated at the time to record both what was
originally planned and what actually happened — see Findings below for exactly where.

A batch-3 re-verification pass (also 2026-08-06) re-checked the redefined T44/T45 against a more
precise, exhaustive spec, confirmed batch 2's implementation already satisfied it exactly, and
closed two test-coverage gaps. **QA Decision: Approved.**

## Current meaning of each ID (as of this note)

| ID | Original meaning (pre-2026-08-06) | Current meaning (2026-08-06 onward) | Original meaning's status |
|---|---|---|---|
| **T44** | `docs/templates/PreStageChecklist.md` sign-off for Stage 3 | Auth dependencies (`argon2-cffi`, `PyJWT`) + `Settings` config | **Not done. No task ID currently tracks it.** |
| **T45** | Write `ADR-0018` (D1–D6) and `ADR-0019` (D7) | Finalize the `AuthenticationProvider` interface (D7) + write `ADR-0019` only | The `ADR-0018` (D1–D6) half is **not done. No task ID currently tracks it.** |

**Rule of thumb for reading any reference to "T44" or "T45" in this repository:** if the surrounding
text or the document's own date is from before 2026-08-06 (batch 2), it means the *original*
content. If it's from 2026-08-06 (batch 2) onward, it means the *redefined* content. When in doubt,
follow the reference to `docs/ImplementationLog/Stage3/Phase0.md`'s "⚠ Task-ID discrepancy" section
— that is the authoritative account of what actually happened under each ID, per this project's
Canonical Document Roles (`docs/ImplementationLog/README.md#canonical-document-roles`).

## Findings — where T44/T45 are referenced, and how each already handles the ambiguity

Audited by searching the full repository for every "T44"/"T45" occurrence.

| Document | How it currently handles the discrepancy | Assessment |
|---|---|---|
| `IMPLEMENTATION_QUEUE.md` | Phase 0 table rows use strikethrough on the original task description, then an explicit "Superseded"/"Partially superseded" annotation stating what was actually done under each ID. A dedicated "Discrepancy note" paragraph follows the table, naming both orphaned original-content items. The Stage 3 status header also summarizes it. | **Already adequate.** Canonical planning backlog; correctly kept current rather than frozen. |
| `docs/ImplementationLog/Stage3/Phase0.md` | Carries a dedicated, prominent "⚠ Task-ID discrepancy (batch 2)" section immediately after the phase's Objective — the most thorough treatment in the repository. Every batch-2/3 task entry is explicitly labeled "(batch 2, redefined)." Deferred Work names both orphaned items. | **Already adequate — this is the authoritative record.** Not modified by this note. |
| `docs/SessionReport.md` | Each dated session entry reflects what was true *at the time it was written* — the batch-1 entry describes the original T44/T45 plan (accurate then), the batch-2 entry explicitly states "Discrepancy found and flagged before proceeding," the batch-3 entry references the re-verification. | **Already adequate and correctly historical.** Not modified by this note — rewriting a past entry to reflect later knowledge would violate this project's "corrections get a new dated entry, not a silent rewrite" rule. |
| `PROJECT_STATE.json` | `currentStage.note`, `stages[].note`, the relevant `backendSubsystems` entry, and a dedicated `openQuestions` entry all explain the reuse and name the orphaned items. | **Already adequate.** Machine-readable snapshot, correctly kept current. |
| `docs/AI_HANDOVER.md` | Summarizes the discrepancy briefly and points to `Phase0.md` for full detail, consistent with this project's no-duplication rule. | **Already adequate.** |
| `ADR/0019-authentication-provider-interface-change.md` | Does not reference "T44"/"T45" by ID at all. | **Correct as-is** — ADRs record decisions, not task-ID history, per Canonical Document Roles. Nothing to fix. |
| `ADR-0018` | Does not exist. | Its absence is already flagged in every document above. Not a gap in *this* audit — a gap in the backlog (see Recommendation). |
| `docs/Stage3_Backend_Handoff.md` | ⚠ **Stale, corrected by this session.** Its "Status" line said "Architecture approved (`ADR-0018`/`0019`/`0020`, once written per T45/T43)" — written before the batch-2 redefinition, it now falsely implies `ADR-0018` either exists or is still forthcoming via T45. Since this document is explicitly named as required reading (`AI_BOOTSTRAP.md`'s New Session Protocol, step 4), a fresh session could be misled into thinking D1–D6 are documented when they aren't. | **Fixed as part of this note** — see Files Modified below. |
| `AI_BOOTSTRAP.md`, `docs/ImplementationLog/README.md` | No T44/T45 references at all. | **Correct as-is** — these are general, ID-agnostic standard documents; they should never cite a specific instance ID. This is also where a future "task IDs are immutable" rule would live (see Recommendation). |
| `docs/reviews/` (QA reports) | No Stage 3 QA report exists yet — only `Stage_2_5_QA_Review.md` (pre-Stage-3). | **Not a current inconsistency — a live forward risk.** The first Stage 3 QA report will need to cite T44/T45 carefully. See Recommendation. |

## Recommendation

1. **Preserve history exactly as it is.** No task ID has been renumbered, no completed
   `ImplementationLog` entry or `SessionReport.md` session has been rewritten. The existing
   discrepancy notes in `IMPLEMENTATION_QUEUE.md` and `Phase0.md` already do the right thing —
   annotate in place, don't silently overwrite.
2. **This note is the least-disruptive way to add what was missing**: a single, dated, canonical
   cross-reference that a future document (a QA report, an ADR, a quick status check) can point to
   without re-deriving or re-explaining the discrepancy — additive only, nothing existing changed
   in meaning.
3. **When the first Stage 3 QA report or a future ADR needs to cite T44 or T45, cite the dated work,
   not the bare ID** — e.g. "T44 (2026-08-06, auth dependencies & config)" rather than just "T44."
   This is a per-document writing convention, not a rule requiring adoption elsewhere.
4. **The two orphaned original-content items need a tracking decision, separately from this note:**
   the `docs/templates/PreStageChecklist.md` sign-off and `ADR-0018` (D1–D6) currently have no task
   ID at all. The least-disruptive fix is almost certainly assigning each a **new** ID (continuing
   the existing sequence, or a clearly-marked variant) rather than reusing or reinstating T44/T45 —
   but that is itself a planning decision for `IMPLEMENTATION_QUEUE.md`'s owner (Project Manager,
   per Documentation Ownership) and is **not made by this note**. Flagging it here so it isn't lost;
   `IMPLEMENTATION_QUEUE.md`'s own "Discrepancy note" already flags it too.
5. **Consider a new project rule: "Task IDs are immutable."** Recommended, not adopted — see below.

### Proposed rule (not adopted — awaiting approval)

> Once a task ID is assigned in `IMPLEMENTATION_QUEUE.md`, its meaning does not change. If a
> project-owner instruction describes different work than a task ID's original definition, that
> work gets a **new** ID (e.g. the next sequential number) rather than reusing the old one — even
> under direct instruction — unless the instruction explicitly and knowingly overrides this rule.
> The original task keeps its original definition and is separately marked `Not Started`,
> `Deferred`, or `Superseded`, but never silently repurposed.

**Recommended home:** `AI_BOOTSTRAP.md`'s "Non-negotiable rules for this project" section — the
same placement and style as the existing "Process changes are versioned" rule, which this is a
close sibling of (both are about not silently changing an established meaning). Cross-reference
from:
- `docs/ImplementationLog/README.md`'s "Metadata block" section, where "Related Tasks" is filled
  in — the point where a task ID's identity actually gets consumed by a phase log.
- `IMPLEMENTATION_QUEUE.md`'s own header note (it already distinguishes itself from
  `docs/Roadmap.md` and `PROJECT_STATE.json`; one more sentence establishing ID immutability fits
  naturally there).

**Not implemented as part of this note or this session**, per explicit instruction — this is a
recommendation only, awaiting separate approval before any of the three files above are edited to
state it as a standing rule.

## Files Modified (by this note's own creation)

- `docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md` (this file, new).
- `IMPLEMENTATION_QUEUE.md` — one cross-reference line added to the existing "Discrepancy note"
  paragraph, pointing here. No other change.
- `docs/Stage3_Backend_Handoff.md` — corrected the one now-false sentence in its "Status" line (see
  Findings above). No other change; the Phase 1–4 file-by-file map and every other section is
  untouched.

## Future Risks

- **Future QA reports.** The first Stage 3 QA report (once Phase 1+ lands) will need to cite T44/T45
  somewhere in its evaluation of Phase 0. If it cites the bare ID without checking which meaning
  applies, it could misattribute a finding to the wrong scope of work. Mitigated by this note's
  "cite the dated work, not the bare ID" convention above, but that convention isn't enforced by
  anything — it relies on whoever writes that report reading this note first.
- **Future ADR references.** If a future ADR references "T44" or "T45" as context (e.g. "see T45"),
  a reader without this note's context could assume the *original* meaning (ADR-0018) rather than
  the *redefined* one. Same mitigation and same limitation as above.
- **The orphaned original-content items (`PreStageChecklist` sign-off, `ADR-0018`) have no task ID
  at all right now.** Until a tracking decision is made (see Recommendation #4), anyone searching
  `IMPLEMENTATION_QUEUE.md` by task ID for "the Stage 3 pre-stage checklist" or "the D1–D6 ADR" will
  find nothing — they're only discoverable by reading the discrepancy notes in prose, not by ID
  lookup. This is the most concrete, near-term risk: it's a genuine backlog gap, not just a
  documentation clarity issue.
- **If the "Task IDs are immutable" rule is never formally adopted, this exact situation can recur.**
  The rule is recommended, not enforced — nothing currently prevents a future direct instruction
  from reusing another already-assigned ID the same way T44/T45 were reused.

## Update (2026-08-07)

This note's body above is left exactly as originally written (2026-08-06) — a point-in-time
snapshot, not rewritten to match later developments, per this project's "freeze a moment in time,
append rather than rewrite" convention (the same pattern `docs/reviews/Stage_2_5_QA_Review.md` uses
for its `> RESOLVED` blockquotes). Two things above are now superseded:

- **The "Task IDs are immutable" rule (Recommendation #5 / "Proposed rule," above) was
  subsequently approved by the project owner and adopted** into `AI_BOOTSTRAP.md`'s "Non-negotiable
  rules," `IMPLEMENTATION_QUEUE.md`'s header, and `docs/ImplementationLog/README.md`'s metadata-block
  guidance. Where this note says "Recommended, not adopted" and "not yet adopted — awaiting
  approval," read those as accurate for 2026-08-06 only; the rule is now in effect.
- **`ADR-0018` (Authentication & Authorization Architecture, D1–D6) was subsequently written**
  (2026-08-07), closing that half of the originally-orphaned *original* T45 content. Where this
  note's Findings table and Future Risks say `ADR-0018` "does not exist," that was accurate as of
  2026-08-06 only. **The `docs/templates/PreStageChecklist.md` sign-off (the *original* T44
  content) remains the one still-open orphaned item** — drafted at
  [`docs/reviews/PreStageChecklist_Stage3_2026-08-07.md`](PreStageChecklist_Stage3_2026-08-07.md)
  but not yet formally approved (its own Sign-off section is intentionally left blank, pending
  project-owner review).

Neither update required renumbering any task ID or rewriting `docs/ImplementationLog/Stage3/Phase0.md`.

## Related Documents

- [`docs/ImplementationLog/Stage3/Phase0.md`](../ImplementationLog/Stage3/Phase0.md) — the
  authoritative implementation record, including the original "⚠ Task-ID discrepancy" section this
  note summarizes but does not replace.
- [`IMPLEMENTATION_QUEUE.md`](../../IMPLEMENTATION_QUEUE.md) — the canonical planning backlog,
  Phase 0 table and Discrepancy note.
- [`docs/Stage3_Backend_Handoff.md`](../Stage3_Backend_Handoff.md) — corrected by this session, see
  Files Modified above.
- [`PROJECT_STATE.json`](../../PROJECT_STATE.json) — `openQuestions` entry on the same topic.
