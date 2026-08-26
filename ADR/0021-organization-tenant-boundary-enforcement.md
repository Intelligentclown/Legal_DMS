# ADR-0021: Organization Tenant-Boundary Enforcement Mechanism

**Status:** Proposed
**Date:** 2026-08-26

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list items
**#1** ("Organization as tenant boundary") and **#19** ("Tenant isolation enforcement") — see that
document's §21 terminology note: these are planning-list positions in that document only, not
repository ADR numbers.

**Does not resolve:** Required ADR #18 ("Authorization architecture" — role/permission granularity
and its enforcement point). Tenant isolation and authorization are related but distinct layers; see
"Relationship to Required ADR #18" below.

## Problem

The governed specification freezes, as a Confirmed Business Rule, that **Organization is the
tenant/security boundary** (§4 rule 43) and that every tenant-scoped entity belongs to exactly one
Organization (§24.1). That business decision is not reopened by this ADR — it is settled. What is
*not* settled, and what §25's invariant #11 and #12 name as the specification's two most
consequential open items, is **how** that boundary is technically enforced across the repository's
actual access surface.

Direct inspection of `main` at this ADR's authoring baseline (commit `b3e8ffb`) confirms the gap is
total, not partial:

- **No `organization_id` column, or `Organization` table/class, exists anywhere** in
  `backend/src/app/infrastructure/persistence/models/*.py`. Confirmed by a full-repository search;
  zero matches.
- **`AbstractRepository[T]`** (`application/interfaces/repository.py`) and its only implementation,
  **`SqlAlchemyRepository[ModelT]`** (`infrastructure/persistence/sqlalchemy_repository.py`), are
  generic CRUD over a single SQLAlchemy model with no tenant dimension at all:
  `get_by_id(id_)` is a bare `session.get(model, id_)`; `list()` applies only the caller-supplied
  `SearchQuery` filters; `update()`/`delete()` operate on whatever entity/id was already fetched.
  Nothing here can distinguish one Organization's row from another's.
- **`RbacAuthorizationService.require_permission()`** (`infrastructure/auth/rbac_authorization_service.py`)
  checks role → permission membership only; it has no concept of *which* Organization's resource is
  being checked.
- **`SearchIndex`** (`application/interfaces/search.py`) indexes/searches by a bare `document_id` +
  free-form `metadata` dict — no structural tenant field.
- **`JobQueue`** (`application/interfaces/job_queue.py`) accepts an arbitrary `payload:
  dict[str, Any]` — nothing requires or validates an Organization identifier in that payload, and a
  `Job.run()` executes with no ambient request/user/tenant context at all.
- **`FileStorage`** (`application/interfaces/file_storage.py`, implemented today by
  `LocalFileStorage`) resolves a caller-supplied `path` string under a single storage root, with a
  path-traversal guard (rejecting `../`) but no tenant-namespace concept — any caller that can
  construct a path string can read/write it.
- **The application connects to Postgres as a single role** (`legal_dms`, per
  `backend/.env.example` / `settings.py`'s default `DATABASE_URL`), which is also the role Alembic
  uses to create every table — i.e. today's runtime role **owns** every table it queries. This is
  directly relevant to Row-Level Security feasibility (see "Alternatives Considered" and
  "Operational Implications" below): Postgres does not apply RLS policies to a table's owner by
  default.

In short: every one of the five access paths §21 item #19 requires this ADR to address — request/
service, repository/data-access, background jobs, search, and file storage — is, today, **equally
and completely unenforced**. There is no partial mechanism to extend; this is a from-scratch design
decision.

## Options Considered

### 1. Application-layer filtering only (no database-level backstop)

Add `organization_id` to every tenant-scoped table; require every repository method to take an
explicit tenant-scope parameter; rely on code review and tests to guarantee every call site passes
it correctly. No RLS, no database-level check.

- **Isolation strength:** weak on its own — correctness depends entirely on every current and
  future call site remembering to pass and apply the filter.
- **Bypass risk:** high. This repository's own history already contains a concrete precedent for
  the failure mode this option is exposed to: `T79`'s verification pass found three disposable,
  never-reviewed ad hoc scripts (`insert_admin.py`, `insert_admin2.py`, `insert_admin3.py`) written
  directly against the database outside the normal repository/service layers. A tenant boundary
  that exists only in application code is one such script, one raw `session.execute(text(...))`
  debugging query, or one future reporting job written against the ORM models directly away from a
  silent cross-tenant leak.
- **Ergonomics:** best of all options — a developer reads one thing (the repository signature) to
  understand the rule.
- **Coverage:** does not naturally reach file storage or the search index, since neither is a
  Postgres table; each would need its own bespoke enforcement, duplicating the same discipline
  problem across three different subsystems instead of one.
- **Rejected as the sole mechanism** — acceptable ergonomics, unacceptable bypass risk for a
  system ADR-0018 itself already describes as carrying "real confidentiality obligations."

### 2. PostgreSQL Row-Level Security (RLS) only, no mandatory application-layer parameter

Add `organization_id` to every tenant-scoped table; set a session-level GUC (e.g.
`app.current_organization_id`) at the start of each request/job; let Postgres RLS policies filter
every query transparently, with no change to repository method signatures.

- **Isolation strength:** strong *if* correctly configured (`FORCE ROW LEVEL SECURITY`, a
  non-owner runtime role, a default-deny policy) — but genuinely fragile in this repository's
  current state, precisely because the runtime role currently *is* the table owner (see Problem
  above). RLS policies are silently skipped for a table's owner unless `FORCE ROW LEVEL SECURITY`
  is set, and are always skipped for any role with the `BYPASSRLS` attribute — neither exception is
  currently absent from this repository's setup; establishing them is new operational work.
- **Bypass risk:** low, once correctly configured — but the correctness of "once correctly
  configured" is doing a lot of work; a missed `SET` on one raw connection (e.g. a pooled
  connection reused by `asyncpg`/SQLAlchemy's async pool without resetting session-level GUCs, a
  detail this repository does not yet have infrastructure to guarantee) fails **open**, not closed,
  unless every table is also `FORCE`d and default-deny.
- **Coverage:** identical gap to Option 1 — RLS protects Postgres tables only; file storage and the
  search index are untouched by it.
- **Ergonomics:** weaker than Option 1 — the enforcing rule lives in database migration DDL, not in
  the code path a developer is reading, making it easy to forget the invariant exists at all when
  writing a new repository method.
- **Rejected as the sole mechanism** — for a defense-in-depth argument, not because RLS is
  unsound; RLS's actual role in this decision is below.

### 3. Schema-per-tenant

One Postgres schema per Organization, with the application selecting the active schema
(`search_path`) per request/job.

- **Isolation strength:** very strong — a query literally cannot reference another tenant's table
  without an explicit cross-schema reference.
- **Operational complexity:** high, and unsupported by anything currently in this repository. Every
  Alembic migration would need to run once per tenant schema (no per-schema migration fan-out
  tooling exists today — `backend/alembic.ini` targets one schema); every new Organization requires
  schema provisioning; connection-pool/session `search_path` management becomes a new,
  tenant-aware concern the current DI/session-lifecycle code (`infrastructure/database/`) does not
  have.
- **Deployment-model fit (assumption, labeled as such):** `docker-compose.yml` shows a single
  `postgres:16-alpine` service with one `POSTGRES_DB`; nothing in the repository indicates
  large per-tenant compliance/data-residency requirements that would justify this cost. This is an
  assumption about the product's likely scale (a single legal-documentation office's internal
  tool, per `docs/BusinessRequirementsPlan.md`), not a fact established anywhere in the frozen
  specification — flagged explicitly as an assumption, not asserted as CBR.
- **Rejected** — the isolation-strength gain does not justify the operational cost this repository
  is not currently built to absorb, given the deployment-model assumption above. Revisit if a
  future decision establishes materially different scale/compliance requirements (see Future
  Impact).

### 4. Database-per-tenant

As Option 3, but a separate Postgres database (or instance) per Organization.

- **Rejected**, more strongly than Option 3, for the same reasons plus connection-pool and
  credential-provisioning multiplication per tenant. Nothing in the repository indicates this
  scale is needed; not pursued further.

### 5. Hybrid — mandatory application-layer scoping as the primary mechanism, PostgreSQL RLS as a mandatory defense-in-depth backstop

Shared single Postgres database and schema (today's actual deployment shape, unchanged). Every
tenant-scoped table gains a non-nullable `organization_id` column. Two independent, non-redundant
enforcement layers apply simultaneously:

- **Primary layer (application):** the repository/data-access contract is changed so that tenant
  scope is a **mandatory, non-optional input** to every operation that can read or write a
  tenant-scoped entity — not an optional filter a caller may forget to add. This is the layer a
  developer actually reads and the layer unit/integration tests exercise directly.
- **Backstop layer (database):** RLS policies (`FORCE ROW LEVEL SECURITY`, default-deny) on every
  tenant-scoped table, driven by a session-level GUC set once per request/job/session, so that even
  a bug in the application layer — a forgotten scope argument, a raw query, a future ad hoc script
  of exactly the kind `T79` already found once in this repository — cannot return or mutate another
  Organization's row.

This is the option selected below.

## Decision

**Option 5 is adopted.** Shared Postgres database and schema; a mandatory, non-optional
`organization_id` on every tenant-scoped table; mandatory application-layer scoping as the primary,
code-level enforcement mechanism; PostgreSQL RLS as a mandatory, independently-enforced backstop —
not a redundant restatement of the same check, but a genuinely separate failure-mode barrier.
Neither layer alone is sufficient per "Alternatives Considered" above; both are required.

The decision is stated below per access surface, per this ADR's authorized scope: it specifies
*what* must hold and *why*, not the literal code (no repository, service, migration, or
infrastructure change is made by this ADR — see "Implementation Boundary" in the governing task and
"Future Impact" below).

### Where tenant context originates

- **Authenticated HTTP requests:** the Organization the caller belongs to is established once,
  during authentication, from the same trust boundary that already establishes `CurrentUser`
  (`application/interfaces/auth.py`) — i.e. derived from the caller's verified identity, not from
  any client-supplied header, query parameter, or request body field. **How exactly a `User`
  resolves to an Organization is itself part of the still-open `User` ↔ Organization relationship
  question flagged in §24.1 ("Organization-membership relationship... exact shape unresolved") and
  is not decided by this ADR** — this ADR only establishes that, whatever that shape turns out to
  be, the resulting Organization identifier must be resolved server-side from trusted identity
  data, never accepted as untrusted client input.
- **Background jobs:** no HTTP request context exists once work is dequeued (confirmed directly —
  `Job.run(self, payload: dict[str, Any])` has no request/user parameter). Therefore **every job
  payload for a tenant-scoped job must carry its Organization identifier explicitly as a required
  payload field, validated at `enqueue()` time** — a job that operates on tenant-scoped data and is
  enqueued without one must fail to enqueue, not fail (or silently succeed unscoped) later at
  execution time.
- **Search indexing/reindexing/bulk operations:** these are background jobs for enforcement
  purposes and follow the background-job rule above — an indexing job's payload must carry the
  Organization identifier of the data it is indexing.
- **Administrative/system-level operations:** if any operation genuinely needs to act across
  Organizations (e.g. platform-level maintenance), it must use an **explicit, separately-named,
  audited system context** distinct from any per-Organization context — never an implicit "no
  filter applied" state reached by omission. This ADR does not enumerate which operations qualify;
  that is implementation-phase work, constrained by this principle.

### How tenant context propagates

Tenant context (an `organization_id`, however it is eventually represented in code) must be an
**explicit value threaded through the call chain from its origin point above to every repository,
search, and file-storage call it reaches** — not a global, not a thread-local/context-var read
implicitly deep inside a repository method with no caller-visible signal that scoping occurred.
Making it explicit at the call site is what keeps the primary (application) layer inspectable in
code review and testable directly, per the ergonomics criterion that ruled out RLS-only in
Alternatives Considered. The *specific* propagation shape (a parameter object, a scoped-repository
factory, a request-scoped dependency-injection value akin to the existing DI container patterns in
`infrastructure/di/container.py`) is an implementation choice, not decided here.

Simultaneously, for the RLS backstop, the resolved Organization identifier must be set as a
Postgres session-level GUC exactly once per database session/connection checkout (request, job
execution, or search/file operation that touches Postgres), before any tenant-scoped query runs on
that connection — analogous in spirit to how this repository already establishes per-request
transaction boundaries (ADR-0020's commit/rollback policy), a precedent this ADR extends rather
than duplicates.

### How missing tenant context fails

**Fail-closed, unconditionally, at both layers.** A repository operation invoked without a resolved
Organization scope must raise, not proceed with an implicit "all Organizations" or "no filter"
behavior. An RLS policy must be default-deny (a row is visible only if it matches the session GUC,
never visible when the GUC is unset) — this is what `FORCE ROW LEVEL SECURITY` plus a
default-deny policy body is for, and why "add RLS policies" alone (without `FORCE` and without a
non-owner runtime role) is explicitly insufficient and must not be treated as satisfying this
decision.

### How cross-tenant access is prevented

By the combination of both layers never returning or mutating a row whose `organization_id` does
not match the resolved context: the application layer because the operation cannot be constructed
without a scope value; the database layer because RLS denies the row regardless of what the
application layer did. Neither layer is permitted to be the *only* thing standing between a request
and another Organization's data.

### Repository / data-access layer

`AbstractRepository`/`SqlAlchemyRepository`'s current shape (`get_by_id`, `list`, `count`, `add`,
`update`, `delete` — verified directly, all six currently tenant-blind) must be extended so that
every one of those six operations, for every tenant-scoped entity, requires an Organization scope
as part of its contract — reads (`get_by_id`, `list`, `count`) and writes (`add`, `update`,
`delete`) alike; `add` specifically must reject constructing an entity without a resolved
Organization, not merely filter on read. The exact shape of that extension (a required constructor
parameter on a per-request repository instance, a wrapper/decorator layer, a new abstract method
signature) is implementation-phase work. Lookup tables that are not tenant-scoped (e.g.
`matter_types`, `document_types` — global vocabulary in today's schema) are out of this decision's
scope by definition; whether any of those become Organization-configurable (per §6.2) is a separate
question this ADR does not resolve.

### Background jobs

Every `Job` implementation that touches a tenant-scoped entity must (a) require and validate an
Organization identifier in its payload at `enqueue()` time, and (b) establish that Organization as
the active scope (both the application-layer propagated value and the RLS session GUC) before doing
any tenant-scoped work in `run()`. A job payload's Organization identifier must never be inferred
from data read *during* the job — it must be supplied at enqueue time by the (already-scoped)
caller that requested the job.

### Search

The search index (`SearchIndex.index()`/`search()`) must carry the Organization identifier as a
structural part of what's indexed — not merely as one more free-form `metadata` field a query might
or might not filter on — and every `search()` call must have its query scoped by the caller's
resolved Organization context before it reaches the index, the same fail-closed rule as the
repository layer. Reindexing/bulk operations are background jobs and follow that section's rule.

### File storage

`FileStorage`'s current shape (a caller-supplied `path` string, resolved under one storage root,
with only a path-traversal guard — verified directly in `LocalFileStorage`) must gain an
Organization-scoped storage key/path namespace: every stored file's path must be namespaced by its
owning Organization as a structural part of the path (not merely recorded separately in
`FileStorageRecord` metadata, which is a different table with its own read path), and every read
must verify the resolved caller Organization matches the file's namespace before returning bytes —
independent of, and not merely inferred from, whichever `FileStorageRecord` row happens to be
queried alongside it. This applies identically to background file-processing (OCR jobs, etc., per
the Background Jobs rule above) and to any future non-local/object-storage provider `FileStorage`
implementation — the port-level guarantee, not a `LocalFileStorage`-specific hack.

## Relationship to Required ADR #18

**Tenant isolation and authorization are two distinct layers and this ADR resolves only the
first.** A request must pass **both**: (1) the tenant-scope check this ADR establishes — is the
target resource even in an Organization the caller belongs to at all — and (2) the permission check
Required ADR #18 will establish — does the caller's role, within that Organization, actually grant
the specific action being attempted. Neither check is a substitute for the other; a user correctly
scoped to their own Organization can still lack `matters:read`, and a user with `matters:read` must
still never see another Organization's Matters.

This creates one explicit, disclosed dependency for ADR #18 to satisfy, not resolved here: **ADR
#18's eventual authorization mechanism must compose with the Organization-scope context this ADR
establishes** (run after or alongside it, never as a replacement, and never itself becoming the
only thing preventing cross-Organization access). §24.1's own Role/Permission entry already
anticipates this ("Required ADR #1/#18" cited together for exactly this reason) and §26 item 8
independently identifies authorization granularity as "the most consequential open item overall" —
this ADR narrows, but does not close, that item; #18 remains fully open.

## Dependencies / Other Unresolved Related ADRs

Not resolved by this ADR, left open per the governing task's explicit boundary:

- **#18 Authorization architecture** — see above; the more consequential dependency.
- **#20 Migration strategy** — adding `organization_id` to every existing table (`matters`,
  `documents`, `clients`, `properties`, `invoices`, `payments`, etc.) and backfilling it for
  whatever single-Organization default this repository's existing data represents is a migration
  question this ADR does not sequence.
- **#2–#17** (Party/Client, Property/Land, Gujarat records, Scheme, Matter/File, numbering,
  Document/version, Workflow/Government, Financial boundary, Activity/Audit, core-vs-configurable,
  identifiers, soft deletion) — untouched; none of those entities' internal shape is decided or
  implied by this ADR beyond "whichever shape they take, they carry `organization_id`," which §24.1
  already establishes as CBR, not a new decision this ADR is introducing.

## Reasoning

Every alternative that relies on a single enforcement layer was rejected because this repository's
own governance history already demonstrates the specific failure mode a single layer is exposed to:
ad hoc, unreviewed scripts written directly against the database (`T79`'s `insert_admin*.py`
finding) bypass application-layer-only discipline entirely, while this repository's current
single-role database connection (owner = runtime role) means RLS-only would currently be silently
inert without an accompanying role split. Neither gap is hypothetical; both are directly observed in
this repository's actual current state. A hybrid, defense-in-depth design closes each layer's
specific weak point with the other layer, at a cost (two things to build and keep in sync, not one)
that is justified by ADR-0018's own already-accepted premise that this system "carries real
confidentiality obligations." Schema/database-per-tenant were rejected on cost grounds specific to
this repository's evidenced single-database deployment shape and the absence of any per-tenant
provisioning tooling — not on isolation-strength grounds, where they would in fact score higher;
this is recorded as a deliberate cost/benefit call, not a claim that hybrid shared-schema is
strictly superior in the abstract.

## Trade-offs

- **Two enforcement layers to build and keep synchronized**, not one — every future tenant-scoped
  table needs both its application-layer scoping wired correctly *and* a `FORCE`d, default-deny RLS
  policy added in the same migration. A table that gets one but not the other is a real, specific
  regression risk this decision creates and that the Testing/Verification Obligations below exist
  to catch.
- **A currently-absent database role split becomes required, not optional.** Today's single
  `legal_dms` role both owns tables (via Alembic) and serves runtime queries. Making RLS a genuine
  backstop (not a no-op for the owning role) requires introducing a distinct, non-owning runtime
  role for the application/worker connections — new operational surface this ADR creates a
  requirement for but does not itself implement.
- **File storage and search gain a structural tenant dimension they don't have today**, which is
  net-new design surface for whichever future task implements it, not a small addition — `path`
  construction and `SearchIndex` metadata both change shape.
- **Background job payload validation becomes stricter** — jobs that don't yet carry an Organization
  identifier (none do today, since no tenant-scoped job exists yet) will need one from the moment
  they're introduced, not retrofitted later.
- **Schema-per-tenant's stronger isolation is deliberately given up** for lower operational cost,
  on the deployment-model assumption stated in Alternatives Considered — if that assumption is
  later shown wrong (materially more tenants, or a compliance requirement demanding physical/schema
  separation), this decision would need to be revisited, not silently reinterpreted.

## Operational Implications

- A distinct, non-table-owning Postgres role for the application/worker's runtime `DATABASE_URL`
  must be introduced (separate from whatever role runs Alembic migrations) before RLS can function
  as a genuine backstop rather than a bypassed no-op — flagged here as a required consequence of
  this decision, not performed by it.
- Every future Alembic migration that adds or alters a tenant-scoped table must pair the schema
  change with its RLS policy in the same migration — a paired-change discipline analogous to this
  repository's existing "constraint changes are documented, not silent" convention (§20 Definition
  of Done's database-constraints expectation).
- Connection-pool behavior (session GUC reset on connection reuse) becomes a correctness-relevant
  detail for the async session/engine setup in `infrastructure/database/`, not merely a performance
  one — must be verified as part of implementing the RLS backstop, not assumed safe by default.

## Testing / Verification Obligations

- **Negative tenant-isolation tests**, not merely positive-path tests: for every tenant-scoped
  repository, route, background job, search query, and file-storage read, an automated test must
  attempt cross-Organization access and assert it is denied/empty — mirroring this repository's
  existing pattern of dedicated negative-path integration tests (e.g. the auth-refresh
  invalid/expired/revoked-token tests already in `tests/integration/test_auth_refresh.py`).
- **A structural/architecture-level check** (in the spirit of ADR-0015's Architecture Health Check)
  that every tenant-scoped table has both a non-nullable `organization_id` column and a `FORCE`d
  RLS policy — catching the "table gets one layer but not the other" regression named in
  Trade-offs, at CI time rather than by incident.
- **A background-job payload-validation test** proving that enqueuing a tenant-scoped job without
  an Organization identifier fails at `enqueue()`, not silently at or after `run()`.
- **A file-storage namespace test** proving that a resolved path under one Organization's namespace
  is unreadable/undeletable through a differently-scoped caller, independent of what
  `FileStorageRecord` row is queried alongside it.
- These obligations extend, rather than duplicate, the mandatory tests already named in the
  governed specification's §17.2 ("Tenant tests").

## Future Impact

- This decision is the foundation every other Required ADR's entity design (#2–#17, #20) now builds
  on for tenant scoping — each of those ADRs' eventual schema must include `organization_id` per
  §24.1's already-frozen CBR, enforced per this ADR's mechanism, without re-deciding the mechanism
  itself.
- ADR #18 (Authorization architecture) is now unblocked to proceed independently, with this ADR's
  "Relationship to Required ADR #18" section as its explicit composition constraint.
- ADR #20 (Migration strategy) inherits a concrete new requirement from this ADR: every existing
  table gaining `organization_id` needs a backfill strategy for this repository's current
  (single-Organization, by construction, since no Organization concept exists yet) data — a
  sequencing question left to #20, not answered here.
- If a future decision establishes that this product's actual deployment scale or compliance
  requirements materially exceed the single-shared-database assumption this ADR made explicitly (see
  Alternatives Considered, Option 3), that would warrant revisiting this ADR — via a superseding
  ADR, not a silent implementation deviation, per this repository's existing ADR-0018 convention for
  handling decisions that later need to change.
