# ADR-0048: Workflow vs Government Status — Domain Boundary and Persistence Separation

**Status:** Proposed
**Date:** 2026-10-31

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item **#12** ("Workflow vs Government Status").

**Does not resolve:** Required ADR #15 (Core vs configurable vocabulary), #16 (UUID vs human-readable identifiers), #17 (Soft deletion/history), or #20 (Migration strategy) — all remain untouched. Required ADR #1–#11, #13, #14, #18, #19 (already resolved by `ADR/0021`–`ADR/0046`, not reopened here) remain as they stand.

**Dependencies:** `ADR/0030-matter-file-lifecycle-and-identity-boundary.md` (the Matter→File boundary this ADR's attachment-granularity question builds on, without deciding it). `ADR/0029-activity-vs-audit-architecture-boundary-and-coverage.md` (the Activity-vs-Audit boundary this ADR's history/event discussion composes with, without reopening). `ADR/0021-organization-tenant-boundary-enforcement.md` (tenant isolation — future Workflow/Government-Process tables are tenant-scoped entities, cited for composition). `ADR/0022-authorization-architecture.md` (future operations on workflow/government status are gated by the existing resource+action model, cited for composition). `ADR/0012-transaction-pipeline.md` and `ADR/0020-session-commit-rollback-policy.md` (future state-transition writes participate in the existing transaction/session boundaries, cited for composition).

## Context

### The decision Required ADR #12 is asking for

The governed specification freezes, as Confirmed Business Rules, a strict separation between three related but distinct concepts:

- **§4 rule 32:** "Internal workflow status is distinct from government status."
- **§4 rule 33:** "Government Process is its own domain concept."
- **§4 rule 34:** "Government events must retain historical information."

§24.10 and §24.11 restate these rules as the organizing constraint for the Workflow/Task and Government Process domains. The risk register calls rule 32 a "🔴 Critical" risk precisely because the two state machines are easy to collapse into a single status field or a single history table. Required ADR #12 is the architectural decision that prevents that collapse by deciding the boundary and mechanism up front.

### Repository baseline (direct inspection, this ADR's authoring baseline)

- **A framework-free workflow engine exists** — `backend/src/app/application/workflow/engine.py` provides `WorkflowDefinition`, `Transition`, and `WorkflowEngine` (`can_transition()` / `transition()`, raising `WorkflowError` on invalid moves). It is intentionally pure: it stores no workflow-instance state and imports no framework types. It decides whether a transition is valid; it does not decide what entity is in what state.
- **Database-side workflow definition/history tables exist** — `backend/src/app/infrastructure/persistence/models/workflow.py` defines `WorkflowDefinition`, `WorkflowState`, and `WorkflowHistory`. `WorkflowHistory` uses a polymorphic `entity_type` + `entity_id` reference (no FK constraint) so any entity can have workflow history tracked against it. These tables are unwired to any service, route, or feature today.
- **A starter workflow definition is seeded** — `backend/alembic/versions/9963e15f2752_seed_lookup_data.py` seeds one `matter_lifecycle` workflow definition with states `OPEN`, `IN_PROGRESS`, `PENDING_REVIEW`, `ON_HOLD`, `CLOSED`, and `CANCELLED`. This is configuration data, not a runtime wiring decision.
- **A separate `matter_statuses` lookup table exists** — `backend/src/app/infrastructure/persistence/models/matter.py` defines `MatterStatus` and `Matter.matter_status_id`. This is a lookup-driven status field on `matters`, not a workflow-state machine. It predates the workflow engine and is not itself the subject of this ADR; it is noted only because future work must not confuse it with either Workflow state or Government Process status.
- **No Government Process or Government Event tables exist** — confirmed by full-repository search: no `government_processes`, `government_events`, `authority_processes`, or similar table; no model, service, or route references government status. This is a genuinely new domain area, as §24.11 states.
- **No service or route currently wires the workflow engine to the workflow tables** — confirmed by direct inspection. The engine and the tables are "framework exists; domain wiring absent," exactly as §24.10 describes.

### What this ADR is not being asked to decide

The specification leaves several adjacent questions explicitly unresolved (marked `ED — engineering decision` in §24.10/§24.11):

- Exact attachment granularity (Matter vs. File vs. both) for Workflow and Government Process.
- Concrete workflow-definition vocabulary beyond the seeded starter.
- Government-process type vocabulary, authority/office reference shape, or reference-number validation.
- Exact field list for `government_processes` / `government_events`.
- Soft-deletion / history-retention mechanics.
- Migration strategy for the pre-existing `matter_statuses` / `Matter.matter_status_id` column.

This ADR decides only the boundary and mechanism necessary to satisfy Required ADR #12: **Workflow and Government Process remain separate domain concepts with separate persistence, ownership models, and lifecycle semantics**, and the existing workflow engine is reused only for internal workflow, never for government status.

## Decision

**Workflow and Government Process are permanently distinct domains.**

They are not two views of one state machine, not two vocabulary sets loaded into one table, and not two event streams written to one history table. The existing workflow engine and workflow tables are reserved for **internal workflow** only. Government Process requires its own future entity (`government_processes`) and its own append-only event history (`government_events`).

### Boundary decisions

1. **Ownership / control.**
   - **Workflow state** is controlled by the firm. A user (or an automated firm-internal action) initiates a workflow transition, and the system validates it against the active `WorkflowDefinition`.
   - **Government Process status** is observed from, or reported by, an external authority. The firm records it; the firm does not authoritatively set it. The system must not enforce a fixed transition graph over government status because the authority's actual process is outside the system's control.

2. **State vs. event semantics.**
   - **Workflow** is a state machine: a `Matter`/`File` has a current workflow state, and `workflow_history` records each valid transition (`from_state_id` → `to_state_id`) with actor and timestamp.
   - **Government Process** is an event-sourced observation: the authority reports events ("submitted," "query raised," "approved," "rejected"). `government_events` records each observation append-only. A current "government status" may be derived as the latest event, but the authoritative record is the event stream, not a mutable status field.

3. **Persistence separation.**
   - `workflow_definitions` / `workflow_states` / `workflow_history` are for internal workflow only.
   - `government_processes` / `government_events` are for external authority processing only.
   - Neither table set may be repurposed to store the other domain's data. A future migration that conflates them would reopen this ADR.

4. **Attachment granularity (deferred).**
   - Both Workflow and Government Process can attach to either `Matter` or `File` (or both), independently, once `File` exists as a persisted entity. The exact default and optional attachment points are not decided here; they remain a business/configuration decision for future implementation tasks, respecting `ADR/0030`'s Matter→File boundary.

5. **Relationship between the two domains.**
   - They are **correlated but not coupled**. A workflow transition may be triggered *in response to* a government event (e.g., "approval received" → move workflow to "approved"), but the workflow transition is a firm decision recorded in `workflow_history`; the government event is an external observation recorded in `government_events`. Neither record is derived from or contingent on the other.

## Decision Drivers

Ranked in the order this ADR actually weighs them, matching `ADR/0021`–`ADR/0047`'s established evidentiary discipline:

1. **§4 rules 32–34 (frozen CBRs)** — any candidate that collapses Workflow and Government Process into one table, one state machine, or one status field is disqualified outright.
2. **External-authority unpredictability** — government processes do not follow a firm-controlled transition graph. A state-machine engine that enforces valid transitions is the wrong model for authority-reported status.
3. **Repository consistency** — reuse the existing, framework-free workflow engine for exactly what it was built for (internal state machines), and introduce a new, separate domain model for government processing rather than stretching the existing machinery into a semantically different area.
4. **Non-invention** — decide only the boundary and mechanism Required ADR #12 asks for; do not design field lists, vocabularies, or attachment defaults the specification leaves open.
5. **Audit/activity composition** — both workflow transitions and government-event recordings are materially significant status changes that fall under `ADR/0029`'s coverage expectations; keeping the two domains separate at the data layer makes independent instrumentation straightforward.

## Alternatives Considered

### A. Represent both Workflow and Government Process with the same state-machine engine

| Alternative | Assessment |
|---|---|
| **Use `WorkflowEngine`/`WorkflowDefinition` for both internal workflow and government-process status** | Rejected outright — it directly violates rule 32 by collapsing two distinct state machines into one mechanism. It also misapplies a firm-controlled transition model to an authority-controlled observation domain. |
| **Use `WorkflowEngine` for workflow; define a second, parallel `GovernmentProcessEngine`/`GovernmentProcessDefinition` with the same state-machine semantics** | Rejected — government status is not a state machine the firm controls. Defining transitions like "PENDING → APPROVED" in code would create a false impression of control and would break whenever an authority introduces an unmodeled intermediate state. |
| **Use `WorkflowEngine` for workflow only; represent Government Process as an append-only event stream with no enforced transition graph (selected)** | Matches rule 33/rule 34, respects external-authority control, and reuses the right tool for each domain. |

### B. Persistence: one shared history table vs. two separate tables

| Alternative | Assessment |
|---|---|
| **Extend `workflow_history` to also store government events, distinguished by a `source` flag** | Rejected — it re-collapses the distinction rule 32 protects. The table name itself (`workflow_history`) would become semantically wrong for authority events, and a shared flag is a trivial future conflation risk. |
| **Create a generic `events` table that stores both workflow transitions and government events, typed by a discriminator** | Rejected — a generic event store would force both domains into a least-common-denominator shape, lose the `from_state_id`/`to_state_id` semantics specific to workflow transitions, and obscure the business meaning the specification explicitly wants preserved. |
| **Keep `workflow_history` for workflow transitions only; create a separate `government_events` table for authority events (selected)** | Preserves the semantic boundary at the schema level, allows each table to model its own domain accurately, and is the only option consistent with rule 33. |

### C. Government Process status: mutable field vs. derived view

| Alternative | Assessment |
|---|---|
| **`government_processes` carries a mutable `status` column that is updated in place when each new event arrives** | Rejected — it loses history by mutation, contradicting rule 34's "Government events must retain historical information." A mutable column is also prone to silent overwrites. |
| **`government_processes` carries only identifying/reference fields; current status is derived as the latest row in `government_events` (selected)** | Preserves the append-only event history as the authoritative record. A derived "current status" view is allowed as a read-side convenience, but the event stream remains the source of truth. |

## Consequences

- No schema, migration, service, route, or code is created or modified by this ADR — it is a documentation-only architectural decision, per its own "Implementation Boundary" below.
- Future workflow implementation will wire the existing `WorkflowEngine` to the existing `workflow_definitions`/`workflow_states`/`workflow_history` tables. It will not create new government-process behavior.
- Future government-process implementation will create new `government_processes` and `government_events` tables. It will not reuse `workflow_history` or the `WorkflowEngine`.
- The pre-existing `matter_statuses` lookup table and `Matter.matter_status_id` column remain untouched. Whether and how they relate to workflow state or government status is explicitly deferred to Required ADR #20 and future implementation tasks.
- `ADR/0029`'s coverage expectations apply independently to workflow transitions and government-event recordings: both are "status changes" under §17.9's six audit-test categories, so future instrumentation must call `AuditLogger.record()` (and optionally `ActivityLog`) for both, as separate operations.
- The existence of two similar-looking history tables (`workflow_history` and `government_events`) is an accepted trade-off. The structural similarity is incidental; the semantic distinction is the point.

## Invariants

1. `WorkflowEngine`, `workflow_definitions`, `workflow_states`, and `workflow_history` are for internal firm workflow only — never for government-process status or events.
2. Government Process is a separate domain entity with its own persistence (`government_processes` / `government_events`) — never stored in workflow tables.
3. Government-event history is append-only. The authoritative record is the event stream; any "current status" is a derived read-side view.
4. Workflow transitions are firm-controlled and validated against a `WorkflowDefinition`. Government-event recordings are authority-observed and not validated against a firm-defined transition graph.
5. Workflow and Government Process may both attach to `Matter` or `File` (once `File` exists), independently. This ADR does not decide the default or required attachment points.
6. No future migration may conflate `workflow_history` and `government_events` into one table, or use one table to store both domains' data, without reopening this ADR.

## Relationship to `ADR/0030`

`ADR/0030` decided the Matter→File lifecycle boundary: File is existence-dependent on Matter but has its own identity and lifecycle. Required ADR #12 needs that boundary as context — Workflow and Government Process can attach to Matter, to File, or to both — but this ADR deliberately does not decide the attachment granularity. `ADR/0030` is composed with, not reopened.

## Activity and Audit Composition (`ADR/0029`)

`ADR/0029` treats "status changes" as one of the six materially significant operation categories that require audit coverage. Workflow transitions and government-event recordings are both status changes in their respective domains. Future instrumentation must therefore call `AuditLogger.record()` for both, independently, and may also write `ActivityLog` entries if the event is business-visible. Neither recording is derived from the other.

## Tenant Isolation and Authorization Composition (`ADR/0021`, `ADR/0022`)

Once implemented, `workflow_definitions`/`workflow_states`/`workflow_history` and `government_processes`/`government_events` are tenant-scoped entities like every other new table this series introduces. They carry a mandatory, directly-carried `organization_id` per `ADR/0021`, and mutating operations are gated by the existing resource+action permission model per `ADR/0022`. Neither ADR is modified, reopened, or reinterpreted by this decision — cited here only for composition.

## Transaction and Session Composition (`ADR/0012`, `ADR/0020`)

Future workflow-state writes and government-event writes participate in the existing transaction/session boundaries: `ADR/0020`'s `get_db()` commit-on-success/rollback-on-exception policy, and `ADR/0012`'s `UnitOfWork`/`TransactionPipelineBehavior` when those abstractions are used by the implementing service. This ADR introduces no new transaction semantics.

## Unresolved / Deferred Questions

- Exact attachment granularity (Matter vs. File vs. both) for Workflow and Government Process.
- Concrete workflow-definition vocabulary and which Organization-scoped definitions are seeded by default.
- Government-process type vocabulary, authority/office reference shape, and reference-number validation rules.
- Exact field list for `government_processes` and `government_events`.
- Whether `government_processes` carries derived current-status materialization, and if so, how it is kept consistent with `government_events`.
- Soft-deletion / history-retention mechanics for both domains.
- Migration strategy for the pre-existing `matter_statuses` table and `Matter.matter_status_id` column.
- Whether Tasks (`scheduling.py`) should eventually participate in the Workflow engine; this ADR does not decide Task-status vs. Workflow-state relationship.

## Dependencies

`ADR/0030` (Matter→File boundary — composed with, not decided here). `ADR/0029` (Activity vs Audit coverage expectations — composed with). `ADR/0021` (tenant isolation — composition noted for future implementation). `ADR/0022` (authorization — composition noted). `ADR/0012`/`ADR/0020` (transaction/session boundaries — composition noted). The existing `WorkflowEngine` and `workflow_*` schema as framework infrastructure to be reused for workflow only.

## Explicit Out-of-Scope Boundaries

This ADR does **not** decide:

- Required ADR #15 (configurable vocabulary), #16 (UUID vs human-readable identifiers), #17 (soft deletion/history), or #20 (migration strategy).
- `ADR/0001` through `ADR/0047` — none is reopened, modified, or reinterpreted.
- File's own entity architecture beyond what `ADR/0030` already decided.
- Task-status vs. Workflow-state relationship.
- The exact field list, schema, migration, backend model, service, repository, route, frontend, or test for Workflow or Government Process.
- Any database schema change, migration, backend/frontend/Electron/API implementation, or test.

## Implementation Boundary

This ADR is a documentation-only architectural decision. No table, migration, backend model, service, repository, route, frontend, or test is created or modified by this ADR or its accompanying report. Future, separately authorized implementation tasks will build against the boundary this ADR states.

## References

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rules 32–34; §21 (Required ADR #12); §24.10 (Workflow & Tasks); §24.11 (Government Processes); §25 invariant #10.
- `ADR/0030-matter-file-lifecycle-and-identity-boundary.md`
- `ADR/0029-activity-vs-audit-architecture-boundary-and-coverage.md`
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `ADR/0012-transaction-pipeline.md`
- `ADR/0020-session-commit-rollback-policy.md`
- `backend/src/app/application/workflow/engine.py`
- `backend/src/app/infrastructure/persistence/models/workflow.py`
- `backend/src/app/infrastructure/persistence/models/matter.py`
- `backend/alembic/versions/9963e15f2752_seed_lookup_data.py`
- `docs/Database.md` (polymorphic `entity_type`+`entity_id` reference table)
