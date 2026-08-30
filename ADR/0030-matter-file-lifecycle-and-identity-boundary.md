# ADR-0030: Matter–File Lifecycle and Identity Boundary

**Status:** Proposed
**Date:** 2026-08-30

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#8** ("Matter vs File").

**Does not resolve:** Required ADR #1–#7, #9, #13, #14, #18, #19 (already resolved by
`ADR/0021`–`ADR/0029`, not reopened here) or Required ADR #10, #11, #12, #15, #16, #17, #20 (untouched
— see "Explicit Out-of-Scope Boundaries" below). `T98` (Required ADR #14, Activity vs Audit, PR #148)
is a wholly separate, independently governed track, not touched, referenced as a dependency, or
depended upon by this ADR.

**Dependencies:** `ADR/0027-file-numbering-algorithm-and-concurrency-strategy.md` (already decided
Matter-scoped File-Number generation on top of the exact layered Matter→File model this ADR now
formally confirms — composed with, confirmed compatible, not reopened; see "Relationship to
`ADR/0027`" below). `ADR/0021` (tenant isolation — File, once implemented, is a tenant-scoped entity
like every other new table this series introduces; cited, not decided here). `ADR/0022`
(authorization — File-level access composes with the existing resource+action model; cited only).
`ADR/0028` (cited for evidentiary-discipline consistency only — no direct interaction).

## Context

### The conflict this ADR is authorized to reconcile

`docs/BusinessRequirementsPlan.md` (a pre-implementation vision document, explicitly marked by its own
status note as superseded wherever "later decisions" from Stages 1–3 disagree with it — see
"Precedence" below) and the governed
`docs/Legal_DMS — Domain Model & Functional Specification.md` describe two genuinely incompatible
models of what a File Number *is*.

**`BusinessRequirementsPlan.md` §3 ("Core System Philosophy"), quoted verbatim:**

> Every legal matter should have: 1. One Unique File Number... This file number becomes the permanent
> identity of the matter.

No File entity exists anywhere in that document — "file number," "matter," and "the matter's identity"
are treated as one and the same thing, one Number per Matter. §7.3 ("Number Generation Logic") states
generation as **matter-type-scoped**: "Each matter type maintains a separate serial sequence" (e.g.
independent `SD`/`AFF`/`GPA` counters) — a *fourth* numbering-scope candidate never named or evaluated
anywhere in the governed specification or in `ADR/0027` (which names only Organization-scoped,
Matter-scoped, or globally-sequential as the candidates `§24.8` left open).

**The governed specification, by contrast, freezes a layered model as Confirmed Business Rules —
quoted verbatim (§4, "Matter" and "File" groups):**

> 1. Matter is the accepted engagement.
> 2. Matter is created when the overall engagement is accepted.
> 3. Matter does not require a File to exist.
> 4. File is a work package within a Matter.
> 5. File cannot exist without a Matter.
> 6. File Number is assigned when the File/work package is created.
> 7. File Number must not be silently reused.

§7 Phase 4's core invariant diagrams a Matter with zero, one, or many Files (`Matter ├── File A ├──
File B └── File C`, or none), with its exit criterion: "File creation is independently controlled and
assigns a unique File Number **at creation**" (of the File, not the Matter). §11.1's required
migration example states the target relationship shape directly: `Matter → File → Document`, replacing
today's `Matter → Document`. §23's "Final Executive Decision" (the specification's own frozen-concept
list) names `Matter` and `File` as two separate frozen line items, not one.

These two documents cannot both be literally correct as written: one Number per Matter
(`BusinessRequirementsPlan.md`) is structurally incompatible with one Number per File, with a Matter
capable of holding several Files each carrying its own Number (the governed specification).

### Precedence (why the governed specification controls, stated explicitly per this task's own
authorization, not silently assumed)

- Every prior ADR in this series (`ADR/0021` onward) has treated the governed specification, not
  `BusinessRequirementsPlan.md` or any pre-specification discovery artifact, as this project's frozen
  business/domain baseline — without exception.
- `BusinessRequirementsPlan.md`'s own status note, added when it was committed to the repository,
  states this directly: *"Where this plan's assumptions have already been overtaken by decisions made
  during Stages 1–3..., those later decisions govern; this document is not silently authoritative over
  the actual repository."* Its own "Review notes" section (added at the same time) already flags §7's
  numbering *concurrency* gap as needing a decision before implementation, but does **not** flag the
  deeper identity conflict this ADR resolves — confirming this specific reconciliation was still
  genuinely open, not merely restated.
- §23's own text: *"The existing repository has a strong technical foundation, but its current schema
  is only a preliminary implementation foundation and must not be mistaken for the finalized business
  model."*
- `ADR/0027` (Required ADR #9, already resolved and accepted) **already made a concrete numbering-scope
  decision — "File Numbers are Matter-scoped," one Number per File — built directly on the governed
  specification's layered model**, without itself performing this reconciliation. Silently assuming
  the specification controls, rather than stating it, would leave `ADR/0027`'s own validity
  retroactively ambiguous to any future reader who first encounters `BusinessRequirementsPlan.md`'s
  conflicting language — precisely why this task's authorization requires the reconciliation to be
  explicit, in this ADR's own text.

### Repository baseline (direct inspection, this ADR's authoring baseline)

- **No File entity exists anywhere in `backend/src/app`** — confirmed by a full class-name grep
  returning zero matches for `File` as a domain entity (`FileStorageRecord` in `storage.py` is a
  document-blob storage record, an unrelated concept; not the File this ADR concerns). `documents.
  matter_id` (`document.py`) links directly to `Matter` with no intermediate File concept, matching
  §24.9's own "the gap" finding.
- **`matters.matter_number` (`matter.py:49`) exists today** — a plain `String(50)`, `unique=True`
  column, one per Matter row. This is a genuine, pre-existing repository fact directly relevant to
  this reconciliation: today's actual schema already behaviorally implements
  `BusinessRequirementsPlan.md`'s one-Number-per-Matter model, not the governed specification's
  one-Number-per-File model. This ADR does not migrate, rename, repurpose, or remove this column —
  that mechanics question is Required ADR #20's territory (see "Explicit Out-of-Scope Boundaries") —
  but the conflict this ADR reconciles is not merely theoretical or document-vs-document: it is
  already, concretely, present in the live schema.
- **`ADR/0027`'s own Decision, quoted verbatim:** *"File Numbers are Matter-scoped... The counter's
  increment and the new File row's own creation must occur in the same database transaction."* This
  is unambiguously a per-File mechanism — a Matter-scoped *counter* generating a *File's* Number, not
  a Matter's own Number — already built on exactly the boundary this ADR now formally confirms.

## Decision

**The governed specification's layered Matter→File model controls.**
`BusinessRequirementsPlan.md`'s File-Number-as-Matter-identity language (§3, §7.3) is superseded
pre-specification vision-document material, per the precedence already established throughout this
ADR series and stated explicitly in `BusinessRequirementsPlan.md`'s own status note. It is not
reinterpreted, edited, or treated as still-open; it is a historical document whose relevant portion has
already been overtaken, restated here explicitly rather than left as a silent assumption, specifically
because `ADR/0027`'s already-accepted decision depends on this reconciliation existing somewhere in the
repository's record.

**Matter–File boundary, decided as three separable questions:**

1. **Existence** (frozen CBR, restated as an architectural invariant, not re-litigated as a business
   rule): Matter is the root entity. A Matter does not require a File to exist (rule 3) — an
   engagement can be accepted and tracked with zero Files. A File cannot exist without a Matter (rule
   5) — File is strictly subordinate, never a peer or independent root. Cardinality is Matter
   `1 ── 0..N` File (§7 Phase 4's own diagram).

2. **Identity**: **File has its own independent identity, distinct from its owning Matter's identity.**
   A File's Number is assigned when *that File* is created (rule 6), not when its Matter is created
   (a temporally and operationally distinct event, per rule 2 vs. rule 6) — a Matter with three Files
   has one Matter identity and three separate File identities, each independently numbered, exactly
   the shape `ADR/0027`'s Matter-scoped generator already assumes and requires. File's identity is
   *scoped to*, but not *merged with*, its Matter's identity: the numbering mechanism may reference
   the owning Matter (as `ADR/0027`'s Matter-scoped counter does), but the resulting File Number
   identifies the File, not the Matter. Matter's own identity (today, `matters.matter_number`;
   whatever Required ADR #20 eventually decides for it) remains a wholly separate concern that this
   ADR does not merge into File's.

3. **Lifecycle**: File's lifecycle is **existence-dependent but operationally independent**. Bound by
   the existence invariant above (a File's lifecycle can never begin before, or persist after, its
   Matter's own existence — rule 5), but not otherwise slaved to Matter's own status: §7 Phase 4's exit
   criterion states File creation is "**independently controlled**," meaning a File is created, and
   presumably closed or archived, as its own operation — not merely an automatic side effect of a
   Matter status transition. This ADR does **not** invent File's own status vocabulary or terminal
   states (§24.8 itself marks this `ED — unresolved`); it decides only the boundary principle
   (existence-dependent, status-independent), leaving the concrete vocabulary to a future,
   separately-scoped decision.

## Decision Drivers

Ranked in the order this ADR actually weighs them, matching `ADR/0021`–`0029`'s established
evidentiary discipline:

1. **The frozen CBRs (§4 rules 1–7) cannot be reinterpreted** — any reconciliation candidate that
   contradicts them is disqualified outright, regardless of which document it favors.
2. **`ADR/0027`'s already-accepted decision must not be retroactively undermined** — a reconciliation
   that reopens or contradicts Matter-scoped, per-File numbering fails this driver immediately.
3. **Established documentation precedence (§23; `BusinessRequirementsPlan.md`'s own status note)** is
   applied directly, not reinvented — this project already has a settled answer to "which document
   wins," used here rather than re-litigated.
4. **Non-invention** — decide only the identity/lifecycle/existence boundary this task's authorization
   names; do not design File's field list, status vocabulary, attachment granularity, or migration
   mechanics.

## Alternatives Considered

### A. Which document's model controls

| Alternative | Assessment |
|---|---|
| **Treat `BusinessRequirementsPlan.md` as authoritative; redefine File as synonymous with Matter's own identity** | Rejected — directly contradicts §23's frozen entity list (File and Matter named as two separate concepts), reopens `ADR/0027`'s already-accepted Matter-scoped per-File numbering decision (which requires File and Matter to be distinct), and reverses this entire ADR series' own established precedent without any stated justification. |
| **Silently assume the governed specification controls, without stating the conflict anywhere** | Rejected — this task's own authorization specifically requires the reconciliation to be explicit, precisely because a silent assumption leaves `ADR/0027`'s validity retroactively questionable to a future reader who encounters `BusinessRequirementsPlan.md` first. |
| **The governed specification controls; the conflict and precedence are stated explicitly, in this ADR's own text (selected)** | Matches this project's established precedent, protects `ADR/0027`'s already-accepted decision with a documented rationale, and satisfies this task's own explicit "not silently assumed by omission" instruction. |

### B. Identity model

| Alternative | Assessment |
|---|---|
| **File shares Matter's identity — one Number, generated once, applies to both** | Rejected — directly contradicts rule 6 (a File Number is assigned when the *File* is created, a distinct event from Matter creation per rule 2) and `ADR/0027`'s per-File (not per-Matter) numbering decision. |
| **File has a fully independent identity, entirely unconnected to its Matter (e.g., a globally unique number with no Matter reference at all)** | Rejected as unsupported by the specification — rule 5 makes File's existence inherently dependent on its Matter, so treating File's identity as wholly unconnected ignores that dependency; `ADR/0027` specifically chose Matter-*scoped* generation because of it. |
| **File has its own independent identity, scoped to and dependent on its owning Matter's existence (selected)** | Matches `ADR/0027`'s already-accepted mechanism exactly — a Matter-scoped counter produces a File-identifying Number, not a Matter-identifying one. |

### C. Lifecycle coupling

| Alternative | Assessment |
|---|---|
| **File's lifecycle fully mirrors Matter's own status at all times** | Rejected — contradicts §7 Phase 4's "independently controlled" exit criterion, and is structurally incoherent with rule 3 (a Matter with zero Files has no File status to mirror). |
| **File's lifecycle is fully decoupled, including existence — a File could in principle predate or outlive its Matter** | Rejected outright — a direct violation of rule 5. |
| **File's lifecycle is existence-dependent (cannot exist without its Matter) but operationally independent (its own creation/status operations) (selected)** | The only option consistent with both rule 5 (existence) and the Phase 4 exit criterion (independent control) simultaneously; leaves the unresolved status vocabulary genuinely open rather than inventing one to force a false completeness. |

## Consequences

- **`ADR/0027` is confirmed compatible and unaffected** — this ADR is precisely the reconciliation
  `ADR/0027` itself did not perform when it made its own Matter-scoped numbering decision; nothing in
  `ADR/0027` requires modification.
- **Document's required relationship redesign (§24.9/§11.1)** now has an unambiguous target: a future
  Document/File-relationship task (Required ADR #10) redirects `documents.matter_id` toward File, not
  Matter directly, because this ADR confirms File is the intermediate entity Document actually attaches
  to (`Matter → File → Document`) — the *mechanics* of that redirect remain #10's and #20's territory,
  not decided here.
- **Workflow/Task/GovernmentProcess (§2's Feature Catalogue)** now has an unambiguous entity to
  eventually attach to at whichever granularity Required ADR #12 decides — this ADR confirms *what*
  File is (so #12 has a real boundary to attach to), not *where* (File-level vs. Matter-level) they
  attach, which remains #12's own open question.
- **`matters.matter_number` (the existing schema column) is now confirmed, explicitly, to encode a
  model this ADR does not adopt going forward** (one Number per Matter) — this is disclosed as a
  known, real migration-relevant fact for whichever future task addresses Required ADR #20, not
  resolved, renamed, or backfilled by this ADR.
- **File's own broader field architecture, status vocabulary, and Matter-deletion cascade mechanics**
  remain open, correctly deferred rather than invented to appear complete.

## Invariants

1. Matter is the root entity; File is optional (`0..N` per Matter) and strictly subordinate — restates
   rules 1, 3, 4, and 5 as an architectural invariant, not a re-litigated business rule.
2. A File Number is assigned per-File, at File creation — never at Matter creation, and never shared
   across multiple Files of the same Matter. A future implementation must not collapse File Number
   into Matter Number, consistent with and required by `ADR/0027`'s already-accepted mechanism.
3. A File row cannot exist, be created, or persist independent of a Matter row — enforced as a
   mandatory, non-nullable FK once File is implemented, mirroring rule 5 directly.
4. Matter's own identity (today, `matters.matter_number`; however Required ADR #20 eventually resolves
   it) and File's identity are two permanently distinct concerns — no future migration may unify them
   into one shared numbering mechanism or column without reopening this ADR.
5. This ADR's boundary decision does not itself decide Document/File relationship mechanics (#10),
   Workflow/Task/GovernmentProcess attachment granularity (#12), or migration/backfill strategy (#20)
   — future work in those areas builds on this boundary; it does not reopen it.

## Relationship to `ADR/0027`

`ADR/0027` resolved Required ADR #9 (the File-numbering *algorithm* and concurrency mechanism) by
deciding a Matter-scoped generator table producing one Number per File — a decision that assumed,
without itself deciding, exactly the layered Matter→File boundary this ADR now formally resolves. This
ADR does not modify, reopen, or reinterpret `ADR/0027` in any way; it retroactively confirms
`ADR/0027`'s own assumption was correct and consistent with the governed specification, closing the gap
that `BusinessRequirementsPlan.md`'s conflicting language could otherwise have left as an unresolved
question about `ADR/0027`'s own validity.

## Tenant-Isolation and Authorization Composition

Once File is implemented (a future, separately authorized task), it is a tenant-scoped entity like
every other new table this series introduces, carrying a mandatory, directly-carried `organization_id`
per `ADR/0021`'s established discipline, and its access is governed by the existing resource+action
permission model per `ADR/0022`. Neither ADR is modified, reopened, or reinterpreted by this decision
— cited here only for composition, matching `ADR/0024`'s, `ADR/0026`'s, `ADR/0027`'s, and `ADR/0029`'s
identical practice.

## Explicitly Unresolved / Deferred Questions

- Required ADR #10 (Document/File relationship mechanics — the exact FK redirect/migration mechanics
  from `documents.matter_id` to a File reference).
- Required ADR #12 (Workflow/Task/GovernmentProcess attachment granularity — File-level vs.
  Matter-level vs. either; this ADR confirms File's boundary, not where these mechanisms attach to it).
- Required ADR #20 (migration strategy — including any reconciliation or backfill of the existing
  `matters.matter_number` column against this ADR's per-File identity model).
- File's own lifecycle status vocabulary and terminal states (§24.8's own `ED`).
- File's own broader field list beyond what identity/lifecycle/existence require (title, status, owning
  Matter, File Number — the near-certain minimum §24.8 already names).
- Matter-deletion cascade/orphan behavior beyond the existence invariant itself (rule 5's "cannot exist
  without" implies a File cannot survive its Matter's deletion, but the exact cascade mechanism — hard
  delete, soft delete propagation, or a block — is not decided here; §4 rule 46's audit-integrity
  requirement makes outright deletion of either entity likely rare/soft-only in practice, but this is
  noted as context, not decided as architecture).

## Dependencies

`ADR/0027` (composed with, confirmed compatible, not reopened — see "Relationship to `ADR/0027`"
above). `ADR/0021` (tenant isolation — composition noted for File's future implementation, not decided
here). `ADR/0022` (authorization — composition noted, not decided here). `ADR/0028` (cited only for
evidentiary-discipline consistency; no direct interaction).

## Explicit Out-of-Scope Boundaries

This ADR does **not** decide:

- Required ADR #10 (Document/File relationship mechanics), #11 (Document/version architecture), #12
  (Workflow/Task/GovernmentProcess attachment granularity — only the boundary these mechanisms inform
  is confirmed, not #12's own resolution), #14 (`T98`'s own, separately governed track), #15, #16, #17,
  or #20 (migration strategy, including any `matters.matter_number` backfill/reconciliation).
- `ADR/0021` through `ADR/0029` — none is reopened, modified, or reinterpreted.
- File's own broader field list/entity architecture beyond what this lifecycle decision necessarily
  implies.
- Matter-deletion cascade behavior beyond what this boundary decision necessarily implies.
- The exact Workflow/Task/GovernmentProcess attachment mechanism itself — only the File-vs-Matter
  granularity *question* this task's boundary informs, not #12's own resolution.
- `docs/BusinessRequirementsPlan.md` or the governed specification's own text — neither document is
  modified by this ADR.
- Any §4 business rule — none is modified, reinterpreted, or narrowed; each cited rule is restated as
  an architectural consequence, not re-litigated.
- The frozen §23 entity model.
- Any database schema change, migration, backend/frontend/Electron/API implementation, or test.
- `T98`/PR #148/its in-flight ADR draft, in any way.

## Implementation Boundary

This ADR is a documentation-only architectural decision. No table, migration, backend model, service,
repository, route, frontend, or test is created or modified by this ADR or its accompanying report.
File's own eventual implementation, once separately authorized, builds against the boundary this ADR
states — the boundary itself, not File's full design, is this ADR's entire scope.

## References

- `docs/BusinessRequirementsPlan.md` §3 ("Core System Philosophy"), §7.1–7.3 ("File Numbering
  System"), status note, and "Review notes" section.
- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 1–7; §7 Phase 4; §11.1; §23;
  §24.8; §2 Feature Catalogue (File, File Numbering, Workflow, Task, Government Process rows).
- `ADR/0027-file-numbering-algorithm-and-concurrency-strategy.md`
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `backend/src/app/infrastructure/persistence/models/matter.py` (`matters.matter_number`, line 49)
- `backend/src/app/infrastructure/persistence/models/document.py` (`documents.matter_id`, today's gap)
