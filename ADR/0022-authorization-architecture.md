# ADR-0022: Authorization Architecture — Permission Granularity and Composition with Tenant Isolation

**Status:** Proposed
**Date:** 2026-08-27

**Resolves:** `docs/Legal_DMS — Domain Model & Functional Specification.md` §21 planning-list item
**#18** ("Authorization architecture") — see that document's §21 terminology note, restated here
because the numbering collision is a real and easy mistake to make: `ADR/0018-authentication-authorization-architecture.md`
is an **already-accepted, unrelated** repository ADR (D1–D6: JWT mechanism, Argon2id, `PyJWT`,
bootstrap CLI, no self-registration, Electron token storage) — filename `0018`. Planning-list item
**#18** ("Authorization architecture" — role/permission granularity, enforcement point, composition
with tenant isolation) is a *different thing*, resolved by *this* ADR, filed as `ADR/0022` because
`0022` is the next available repository ADR number, not because of any relationship to filename
`0018`.

**Does not resolve:** Required ADR #1 or #19 (already resolved by `ADR/0021`) or Required ADR
#2–#17/#20 (untouched; see "Explicitly Unresolved Items" below).

**Dependencies:** `ADR/0021-organization-tenant-boundary-enforcement.md` (tenant isolation
mechanism — frozen, not reopened by this ADR; see "Relationship to ADR-0021" below). `ADR-0019`
(D7, `AuthenticationProvider` signature — the authentication/authorization separation-of-concerns
precedent this ADR follows). `ADR-0020` (session commit/rollback policy — the request-scoped
transaction boundary authorization checks execute inside).

## Problem

The governed specification requires, as a Confirmed Business Rule, that "access must be
permission-aware" (§4 rule 44) and that "Matters, Files and Documents may require finer-grained
access" (§4 rule 45) — on top of the already-settled §4 rule 43 that Organization is the
tenant/security boundary, whose enforcement mechanism `ADR/0021` has now decided. What §25's
invariant #12 and §26 item 8 both independently name as the specification's other most
consequential open item is **how** permission-aware access is technically architected: what a
"permission" is, where it is evaluated, and — critically, per `ADR/0021`'s own "Relationship to
Required ADR #18" section — how that evaluation composes with the tenant-scope check `ADR/0021`
already mandates, without either check ever substituting for the other.

Direct inspection of `main` at this ADR's authoring baseline (commit `388e723`) shows this is not a
from-scratch design question the way tenant isolation was — a real, working, tested authorization
mechanism already exists:

- **`RbacAuthorizationService`** (`infrastructure/auth/rbac_authorization_service.py`) implements
  the `AuthorizationService` port (`application/interfaces/auth.py`) as
  `require_permission(user: CurrentUser, permission: str) -> None`: denies an unauthenticated
  caller outright, then checks the caller's `roles` (a `frozenset[str]` of role names) against a
  pre-loaded `role name → permission-code set` snapshot, raising `ForbiddenError` if no role grants
  the requested code. Permission codes follow a `"<resource>:<action>"` convention (e.g.
  `"matters:read"`), confirmed by the persistence model's own module docstring.
- **`RequirePermission(*permissions)`** (`presentation/api/deps.py`) is the FastAPI dependency
  factory routes use to gate access: one or more bare permission-code strings, OR semantics across
  them, a 401-before-403 split (unauthenticated callers never reach `AuthorizationService` at all),
  and an audit record (`AuditLogger`, T65) on the final denial only.
- **`Role`/`Permission`/`UserRole`/`RolePermission`** (`infrastructure/persistence/models/identity.py`)
  are four real tables: a many-to-many `user_roles` join and a many-to-many `role_permissions` join,
  neither carrying `organization_id` or any tenant column. Six seeded roles (`Administrator`,
  `Advocate`, `Paralegal`, `Clerk`, `Accountant`, `Read Only`), eighteen seeded permission codes
  across six categories, fifty-nine role→permission grants — all global, none Organization-scoped,
  confirmed exactly by `test_t66_role_permissions.py`'s regression assertion (`len(...) == 59`).
- This mechanism is exercised in production today by exactly one router
  (`presentation/api/v1/users.py`, gated on `"users:manage"`/`"roles:manage"`) and extensively
  tested (`test_rbac_authorization_service.py`, `test_auth.py`, `test_auth_dependency_wiring.py`,
  `test_users.py`'s `TestAuthorization`/`TestRoleAssignmentAuthorization`/
  `TestPermissionDeniedAuditing` classes) — this is not a stub or placeholder, unlike tenant
  isolation's total absence that `ADR/0021` found.

Equally confirmed by direct inspection: **this mechanism has zero tenant/Organization awareness,
and nothing else in the request/data-access stack has any permission awareness at all.**
`CurrentUser` (`application/interfaces/auth.py`) carries `id`, `display_name`, `roles`,
`is_authenticated` — no `organization_id` field. `AbstractRepository`/`SqlAlchemyRepository`,
`JobQueue`/`Job`, `SearchIndex`, and `FileStorage`/`LocalFileStorage` contain no reference to
`CurrentUser`, `AuthorizationService`, roles, or permission codes anywhere — confirmed by a full
read of each file. So the problem this ADR must solve has two parts: (1) formalize the granularity
and semantics of the *existing, working* permission model as this repository's authorization
architecture, rather than silently assuming it without ever having decided it as one, and (2)
decide how that model's enforcement extends to the four surfaces that currently have none
(repositories, jobs, search, file storage) and composes — without collision — with `ADR/0021`'s
now-decided tenant-isolation mechanism across all five surfaces.

**What this ADR explicitly does not decide**, because the business model does not yet establish it
and inventing it would violate this task's own boundary against reopening frozen or undecided
business rules:

- **Resource-instance-level access** (§4 rule 45's "finer-grained access" for Matters/Files/
  Documents). §24.14 names three candidate mechanisms — a confidentiality-label vocabulary, explicit
  per-Matter/File/Document access-grant rows, or Team-based visibility inherited from Matter
  assignment, "or some combination" — and states the choice among them is **ED, genuinely open**.
  This ADR decides the *architecture* that any of those three mechanisms would plug into (see
  "Decision" → "Extension point for resource-instance authorization" below); it does not choose
  among them.
- **Whether the Role/Permission catalog itself becomes per-Organization** (each Organization gets
  its own Role set, requiring `organization_id` on `roles` and system-role templates cloned per
  Organization) **or stays a shared global catalogue with only Role *assignment* scoped per
  Organization**. §24.1 states this explicitly as unresolved, tracked under Required ADR #1/#18.
  This ADR's composition architecture (see "Relationship to ADR-0021" below) holds correctly under
  either shape — the decision below does not depend on resolving this question, and does not
  resolve it.
- **The exact shape of the `User` ↔ `Organization` relationship** — already flagged as unresolved
  by `ADR/0021` itself (§24.1) and not revisited here.

## Options Considered — Permission Granularity Model

1. **Role-only authorization** (check role name directly; no permission-code indirection). Simplest
   possible model, but coarser than what already exists and is already tested: it would require
   discarding the working `Permission`/`RolePermission` tables and the `"resource:action"` code
   convention, regressing against §4 rule 44's "permission-aware" requirement (a role name alone
   does not express "reads Matters" versus "reads Clients" without a parallel enumeration
   elsewhere). **Rejected** — no benefit over the existing model, real migration cost against
   fifty-nine already-seeded, already-tested grants.
2. **Permission-only authorization** (permissions assigned directly to users, no Role indirection).
   Most expressive per-user, but discards the ergonomic value of six named roles matching real
   legal-office job functions (Advocate, Paralegal, Clerk, Accountant, Read Only) that the seed data
   and `ADR-0018`'s D5 reasoning already establish as the operative mental model — every new user
   would need eighteen individual permission assignments instead of one role assignment.
   **Rejected** — higher per-user administrative burden with no expressiveness gain the business
   rules currently need; role indirection is exactly what makes "give this new Clerk hire the Clerk
   permissions" a one-step operation instead of six.
3. **Resource + action permission model, via role indirection (the existing implementation)**.
   Permission = `resource:action` (e.g. `matters:read`); Role = named, reusable bundle of
   permissions; User ↔ Role is the assignable unit. Matches §4 rule 44 directly, matches the
   specification's own §24.1 characterization of the existing mechanism as "a real, working
   implementation, not a stub," and matches §24.1's explicit repository-mapping guidance for
   Role/Permission: **"Modify"**, not "Create new" or "Replace" — i.e., the specification itself
   already anticipates extending this mechanism, not discarding it. **Selected** — see Decision.
4. **Service-layer-only authorization** (remove the `RequirePermission` route dependency; check
   permissions purely inside service/use-case methods, with no request-boundary short-circuit).
   Would lose the existing, tested 401-before-403 fail-fast behavior (a request is rejected before
   any handler code executes, avoiding partial side effects), for no compensating gain — the actual
   gap this option seems to address (a non-HTTP caller bypassing the FastAPI dependency graph) is
   addressed below in "Decision" by pushing enforcement *responsibility* to the service/use-case
   layer while *keeping* the route-level dependency as its currently-sufficient HTTP-facing
   implementation, not by removing the route-level check. **Rejected** as a wholesale replacement;
   its underlying concern is absorbed into the Decision and Bypass Analysis below.
5. **Authorization duplicated across every layer** (repository, service, route, job, search, and
   storage each independently re-implement full role→permission evaluation). Superficially the
   most bypass-resistant, but the authorizing task explicitly warns against automatic duplication
   without architectural justification, and `ADR/0021`'s own rejection of "application-layer-only"
   tenant isolation was about a *different* failure mode (ad hoc scripts bypassing the *only* layer
   that existed) — permission evaluation is a single, coherent business-logic decision
   ("may this principal perform this action"), and five independent implementations of it are five
   independent places for that decision to silently drift out of sync, not five independent
   safety nets. **Rejected** — see "Decision" for which layers get enforcement responsibility and
   why repositories specifically do not become a second permission engine.
6. **Policy-based/resource-based authorization** (an external policy engine — OPA-style ABAC/RBAC
   hybrid, attribute-based rules). Would meaningfully help with the still-open resource-instance
   granularity question (§24.14), but introduces new infrastructure and operational complexity this
   repository's evidenced single-office deployment scale (the same scale assumption `ADR/0021`
   already made explicitly, not newly asserted here) does not currently justify, and the business
   rule it would serve (§4 rule 45) is not yet decided regardless. **Rejected for now** — worth
   revisiting only once/if a resource-instance mechanism (§24.14's three candidates) is actually
   chosen and found to need it; not a decision this ADR can responsibly make in advance of that.

| Criterion | 1 Role-only | 2 Permission-only | 3 Resource+action (role indirection) | 4 Service-only | 5 Duplicate everywhere | 6 Policy engine |
|---|---|---|---|---|---|---|
| Security | Medium | High | High | High | High (nominally) | High |
| Expressiveness | Low | High | High | High | High | Highest |
| Consistency | High | Medium | High | High | Low (drift risk) | High |
| Bypass resistance | Medium | Medium | Medium (see Bypass Analysis) | Low (no fail-fast) | Nominally high, practically low (drift) | High |
| Maintainability | High | Low | High | High | Low | Medium |
| Operational complexity | Low | Low | Low (already built) | Low | High | High |
| Compatible with `ADR/0021` | Yes | Yes | Yes | Yes | Yes | Yes |
| Compatible with existing Stage 3 code | No (regresses) | No (regresses) | **Yes (formalizes)** | Partial | Partial (adds, doesn't replace) | No (new infra) |

## Decision

**Option 3 is adopted and formalized**: authorization is **resource + action, permission-based,
via role indirection** — `RbacAuthorizationService`, `RequirePermission`, and the
`Role`/`Permission`/`UserRole`/`RolePermission` schema are the adopted mechanism, not a
placeholder to be replaced. This ADR's job is to state the semantics precisely, fix the enforcement
point, and — the part that does not exist yet — decide how this mechanism composes with `ADR/0021`
across all five access surfaces.

### Permission semantics

- **Permission**: a `resource:action` code (e.g. `matters:read`, `users:manage`) — the atomic,
  checkable unit. Represents "may perform this class of action against this class of resource,"
  not any specific resource instance.
- **Role**: a named, reusable bundle of permissions (`RolePermission`), assigned to zero or more
  `User`s via `UserRole`. The unit an administrator actually assigns; permissions are never
  assigned to a `User` directly today.
- **Authenticated principal**: `CurrentUser` — `id`, `display_name`, `roles` (role *names*, not
  permission codes), `is_authenticated`. Resolved fresh per request by `JwtAuthenticationProvider`
  from the database, never trusted from JWT claims beyond "which user" — meaning a revoked role
  takes effect on the caller's very next request, a property this ADR relies on and does not
  change.
- **Organization membership**: not a field on `CurrentUser` today, and this ADR does not add one to
  the authorization port itself (see "Relationship to ADR-0021" below for why that boundary is
  deliberate). The resolved Organization context is `ADR/0021`'s concern to establish and propagate;
  this ADR's mechanism consumes it as an already-resolved value, never re-derives it.
- **Tenant scope**: `ADR/0021`'s `organization_id` — a wholly separate axis from permission,
  composed with it per "Relationship to ADR-0021" below.
- **Resource ownership**: not a concept this schema currently models (no `owner_id` on any
  tenant-scoped table, confirmed by the same model inspection `ADR/0021` performed). Not invented
  here — see "Explicitly Unresolved Items."

### Primary authorization decision point

The primary authorization decision — "may this principal perform this action" — is evaluated **at
the request/service (use-case) boundary**, before the business operation executes, exactly where
`RbacAuthorizationService.require_permission()` is invoked today. This is deliberately kept as
the *one* place a developer reads to understand the rule, mirroring `ADR/0021`'s own ergonomics
argument for why tenant scoping lives in application code rather than being invisible database
config, and mirroring `ADR-0019`'s existing precedent that authentication ("who") and authorization
("may they") are separate, narrow ports rather than logic smeared across layers.

Today this decision point is wired as a FastAPI route dependency (`RequirePermission`), which is
correct and sufficient **for every access path that currently exists**, since every current access
path is an HTTP route. This ADR fixes the *responsibility* one level more precisely than the
current code does: the permission check conceptually belongs to the **service/use-case boundary**,
not to "being an HTTP route" — a distinction with no effect today (nothing currently calls a
permission-gated service method except through an HTTP route) but that matters for the Bypass
Analysis below and for any future non-HTTP entry point (a CLI command, a command-bus handler, an
enqueue-time caller) invoking the same use case.

### Repository / data-access layer

**Repositories remain permission-agnostic.** `AbstractRepository`/`SqlAlchemyRepository` do not,
and per this decision should not, gain `CurrentUser`/permission-code parameters. This is a
deliberate rejection of Option 5 (duplicate-everywhere): a generic `get_by_id`/`list`/`add` method
has no way to know what business action it's being called on behalf of — that information belongs
to the service/use-case method that decided to call it, which is exactly where the permission check
above already runs. Turning repositories into a second permission engine would require passing
permission context through every CRUD call for no correctness gain, since the call never reaches
the repository unless the service-layer check already passed.

This is distinct from — and does not weaken — `ADR/0021`'s repository requirement that every
tenant-scoped operation take a mandatory Organization-scope argument. Tenant filtering is
structural (which rows exist for this caller at all) and belongs at the data-access layer per
`ADR/0021`; permission authorization is a business-action decision (may this caller take this
action at all) and belongs at the service/use-case layer per this ADR. Both remain mandatory,
enforced independently, at their own layer — see "Relationship to ADR-0021."

### Extension point for resource-instance authorization

§4 rule 45 and §24.14 require, eventually, filtering *which* Matters/Files/Documents a
permission-holding caller may see — a dimension `RbacAuthorizationService.require_permission()`
cannot answer today ("a user who holds `matters:read` can read *every* Matter," per §24.14's own
direct observation). Because the specification leaves the actual mechanism open (label vocabulary,
explicit grant rows, or Team-inherited visibility), this ADR does not implement one. It does,
however, fix where such a mechanism — whichever one is eventually chosen — must plug in: **as a
second, independent filter alongside `ADR/0021`'s tenant-scope filter, applied at the same
data-access layer**, not as an extension of `RbacAuthorizationService.require_permission()`'s
coarse-grained action check. This follows directly from resource-instance visibility being
structural (which rows) rather than action-level (which operation) — the same distinction that
places tenant scoping at the repository layer and action permission at the service layer above.
This paragraph names an architectural slot, not a decision about what fills it.

### Background jobs

No live request/session context exists once work is dequeued (`Job.run(self, payload: dict[str,
Any])` carries neither `CurrentUser` nor a permission code, confirmed by direct inspection — this
is unchanged by, and consistent with, `ADR/0021`'s identical finding for tenant context). Therefore:
**permission is evaluated once, at the point the job is enqueued, by the already-authorized caller
requesting it** — the same request/service-boundary check above must pass before `enqueue()` is
called, exactly as it must pass before any other business operation. At execution time, no
principal/permission re-check is possible (there is no principal to re-check against), so
`Job.run()` re-establishes only `ADR/0021`'s mandatory Organization scope, not a permission
decision.

This is an explicit, named trade-off, not an oversight: a role revoked between enqueue and
execution does not retroactively cancel an already-queued job. `ADR/0021` accepted an analogous
gap for its own reasons; this ADR accepts this one for the same category of reason — see
Trade-offs.

### Search

A search operation is itself a use-case and follows the same primary-enforcement rule: the caller
must hold the relevant read permission (e.g. `matters:read`) before any query executes, checked at
the same service/use-case boundary as any other operation — search is not a separate authorization
surface, it is one more use-case behind the same gate. Independently, and mandatorily, every search
query is scoped by `ADR/0021`'s tenant filter (a structural part of the index, not free-form
metadata, per that ADR). Resource-instance-level result filtering (which specific Matters a
`matters:read`-holding caller's search may surface) is the same open §24.14 extension point named
above, not decided here — a search index gains no bespoke permission mechanism beyond the two
already named.

### File storage

A file read/write is likewise a use-case behind the same primary permission gate. In addition,
`ADR/0021` already mandates an independent Organization-namespace verification at the storage layer
itself as a tenant-isolation backstop — this ADR does not weaken that. This ADR adds one
authorization-specific rule for this surface: **when a caller lacks authorization (fails either the
permission check or `ADR/0021`'s tenant-namespace check) for a requested file, and separately when
the requested object does not exist at all, the two cases must not be distinguishable from the
response** — both resolve to a not-found response, never a response that confirms an object exists
in another Organization's namespace or exists but is merely forbidden. This is an authorization
architecture decision (avoiding information leakage through response shape), not a business rule,
and is consistent with `ADR/0021`'s own file-storage requirement that path-naming/existence alone
must never function as a security signal.

### Fail-closed requirements

No authorization decision may default to "allow" when its inputs are missing or invalid, matching
and extending the existing implementation's own behavior (`RbacAuthorizationService`'s
`.get(role, frozenset())` already denies-by-default for a role absent from the permission mapping —
no `KeyError`, no implicit grant):

- **Missing/unauthenticated principal:** deny (401) before any permission evaluation — existing
  behavior, unchanged.
- **Authenticated principal, missing/insufficient permission:** deny (403) — existing behavior,
  unchanged.
- **Missing or unresolved role:** deny — a role name present on `CurrentUser` but absent from the
  permission-mapping snapshot grants nothing; a `CurrentUser` with no roles at all grants nothing.
- **Missing or invalid Organization/tenant context:** deny, per `ADR/0021`'s own identical
  fail-closed requirement — this ADR does not create a new failure path here, it relies on
  `ADR/0021`'s.
- **Missing or unresolved authorization policy** (e.g. a permission code checked against that does
  not exist in the seeded `permissions` table): deny — an unrecognized code can never be present in
  any role's grant set, so this already denies by construction; no change needed, stated explicitly
  so a future refactor does not accidentally introduce a "treat unknown permission code as
  pass-through" shortcut.
- **No implicit administrative bypass.** No code path exists, or may be added, that grants access
  merely because a caller is Administrator by name rather than because the `Administrator` role's
  explicit grant set (today, all eighteen codes) includes the requested permission. The current
  seed data already achieves "Administrator can do everything" through explicit grants, not a
  special-cased bypass — this ADR requires that property to be preserved, not newly introduced.

## Relationship to ADR-0021 — Tenant Isolation

**Tenant isolation and authorization remain two distinct, independently-enforced security
dimensions.** `ADR/0021` answers "which Organization may this request/data access operate within";
this ADR answers "what may this authenticated principal do within that Organization." Neither
answers the other's question, and this ADR does not weaken, reinterpret, or duplicate `ADR/0021`'s
mechanism.

**Composed sequence:** Authentication (establishes `CurrentUser` — who) → Organization/Tenant-Scope
resolution (`ADR/0021` — which Organization, resolved server-side from trusted identity data) →
Authorization (this ADR — does the principal's role grant the attempted action) → Business
operation, whose own data access independently and mandatorily re-applies `ADR/0021`'s tenant scope
(application-layer scoping plus the RLS backstop) regardless of the authorization outcome already
reached. This is not a novel sequence invented here — it is the direct, repository-evidenced
consequence of how `CurrentUser` is already established before `RequirePermission` runs today, and
of `ADR/0021`'s own stated principle that Organization context originates "from the same trust
boundary that already establishes `CurrentUser`."

The Critical Architectural Constraints this composition must hold, stated explicitly and without
exception:

- **Authorization does not replace tenant scoping.** `RbacAuthorizationService.require_permission()`
  does not check, and per this ADR must not be extended to check, `organization_id` — that
  remains entirely `ADR/0021`'s mechanism, evaluated independently at the data-access layer
  regardless of what this ADR's check decided.
- **Tenant scoping does not replace authorization.** `ADR/0021`'s repository/RLS scoping does not,
  and must not be treated as if it does, express "may this principal take this action" — a
  correctly-scoped, same-Organization caller with no `matters:read` grant must still be denied by
  this ADR's check.
- **A permission check is never an alternative tenant-isolation mechanism.** A caller who holds
  `matters:read` is authorized for the *action* "read a Matter" — never for reading a specific
  Matter merely because the permission check passed. Which Matters are visible at all is decided
  exclusively by `ADR/0021`'s scoping, applied independently, every time.
- **An Organization-scoped permission is never itself proof of tenant membership.** Because the
  Role/Permission catalog's own per-Organization-vs-global shape is explicitly unresolved (see
  "Problem" above), this ADR's decision does not depend on, and must not be read as asserting, that
  holding a permission implies anything about which Organization a caller belongs to — that
  inference is exactly the failure mode this constraint forbids, regardless of how the still-open
  catalog-shape question is eventually resolved.
- **Both controls compose fail-closed.** A request missing either a resolved Organization scope or
  a granted permission is denied — there is no code path where one control's success substitutes
  for the other's absence.

This composition holds identically whether the eventual Role/Permission catalog answer (§24.1,
unresolved) turns out to be global-with-per-Organization-assignment or fully per-Organization —
both this ADR's decision and `ADR/0021`'s decision were deliberately kept independent of that
still-open question, precisely so that resolving it later does not require reopening either ADR.

## Bypass Analysis

Considered against this repository's actual architecture and the `T79` precedent (`ADR/0021`'s own
finding of unreviewed ad hoc `insert_admin*.py` scripts written directly against the database,
bypassing every application-layer control that existed):

- **API/request bypass:** prevented by the mandatory `RequirePermission` route dependency, which
  this ADR requires be applied to every future permission-gated router the same way `users.py`
  already does — not merely a convention `users.py` happened to adopt. 401/403 fail closed before
  any handler code runs.
- **Direct service/use-case invocation** (bypassing the FastAPI dependency graph entirely — a
  future CLI command, command-bus handler, or any code path that calls a service method without
  going through an HTTP route): this is the one genuine gap this ADR identifies and does not
  fully close by architecture alone, because no such non-HTTP entry point exists in the repository
  today to design against concretely. The decision above — that the permission check's
  responsibility belongs conceptually to the service/use-case boundary, not to "being a route" — is
  this ADR's answer: any future non-HTTP caller of a permission-gated use case must invoke
  `AuthorizationService.require_permission()` (or an equivalent explicit check) itself, exactly as
  the FastAPI dependency does today, rather than relying on a dependency graph that does not run
  outside HTTP. This is a requirement on future implementation, not a currently-enforced structural
  guarantee — named explicitly, per the same discipline `ADR/0021` used for its own analogous
  gaps, rather than silently assumed closed.
- **Repository invocation directly** (bypassing the service layer): repositories carry no
  permission logic by design (see Decision above), so nothing at that layer itself prevents this —
  protection relies entirely on repositories being called only from within already-authorized
  service/use-case code, an architectural convention rather than a structural guarantee. `ADR/0021`
  already accepts an analogous reliance for its own application-layer tenant scoping; this ADR does
  not introduce a new failure mode, it inherits the same one for the same reason (a generic CRUD
  layer cannot itself know what business action authorized its own invocation).
- **Background-job execution:** cannot bypass authorization *because* no sensitive action should
  ever reach `enqueue()` without having already passed the request/service-boundary check — the gap
  is the same reliance named above (enqueue-time call sites must live inside already-authorized
  code), plus the explicitly-named staleness trade-off (a revoked role does not cancel an
  already-queued job).
- **Search queries:** a use-case like any other, behind the same gate; no separate bypass surface.
- **File-storage reads:** the same service-boundary gate applies before any storage call; `ADR/0021`'s
  independent tenant-namespace check is a partial backstop specifically against *cross-Organization*
  reads reaching storage directly, but — stated explicitly, not glossed over — it is **not** a
  backstop against a same-Organization, unauthorized caller who reaches `FileStorage.read()`
  directly, since tenant-namespace matching says nothing about permission. That residual gap is
  closed the same way the repository gap is: by the convention that only already-authorized
  service code may call `FileStorage` directly, not by a structural guarantee this ADR can create
  without adding permission logic to the storage port itself (rejected above as Option-5-style
  duplication with no repository-evidenced entry point to justify it yet).
- **Ad hoc scripts / privileged database access:** identical residual risk to the one `ADR/0021`
  already named and accepted for tenant isolation, inherited here rather than re-litigated. Unlike
  tenant isolation, this ADR has **no database-level backstop equivalent to RLS** — Postgres Row-
  Level Security enforces which *rows* a session may see (a tenant/ownership-shaped question); it
  has no native concept of "resource:action permission code," so there is no analogous
  database-enforced backstop for *this* ADR's decision to adopt. This is named explicitly as an
  accepted, asymmetric trade-off between the two ADRs' bypass resistance, not an omission.
- **Stale authorization context:** already substantially mitigated by existing, unchanged behavior
  — `JwtAuthenticationProvider` re-derives `CurrentUser.roles` from the database on every request,
  never from JWT claims, so a revoked role takes effect on the very next request. The one place
  this guarantee does not reach is the background-job case above, where no next request exists to
  re-derive against — named, not silently assumed solved.

## Reasoning

The existing `RbacAuthorizationService`/`RequirePermission`/`Role`/`Permission` mechanism was
evaluated on its own merits against five alternatives, not adopted merely because it already
exists: it is the only option that satisfies §4 rule 44's permission-aware requirement without
either coarsening the model (Options 1, 4) or discarding a real, tested fifty-nine-grant dataset
for no expressiveness gain (Option 2), and it matches §24.1's own explicit "Modify" repository-
mapping guidance rather than the specification silently implying a rebuild. Keeping the primary
enforcement point singular (service/use-case boundary) rather than duplicating it (Option 5)
follows the same reasoning `ADR/0021` used to distinguish its primary layer from its backstop layer:
a single, inspectable decision point is more maintainable and less prone to silent drift than the
same logic re-implemented five times, and the actual bypass risk this repository has *already
demonstrated* (`T79`) was ad hoc scripts against raw data access, not multiple layers of permission
logic disagreeing with each other — so the mitigation this ADR invests in (service-layer discipline,
named explicitly rather than assumed) targets the risk that is actually evidenced, the same
standard `ADR/0021` held itself to. Deferring the resource-instance-granularity question (§24.14)
rather than choosing among its three candidates follows directly from this task's own instruction
not to invent unresolved business rules — the architecture decided here (a second, independent,
structural filter alongside tenant scope) is compatible with any of the three candidates the
specification names, so nothing about deferring the choice blocks or narrows it later.

## Trade-offs

- **No database-level backstop for permission checks**, unlike `ADR/0021`'s RLS backstop for tenant
  isolation — accepted because Postgres RLS is structurally suited to row-visibility (tenant/
  ownership) questions, not to arbitrary business-action permission codes; building an equivalent
  would mean either encoding every permission as a row-visibility predicate (a poor fit for
  action-level concepts like `users:manage`) or introducing an entirely separate policy-engine
  layer (Option 6, rejected above as unjustified at current scale).
- **Direct service/repository/storage invocation relies on architectural convention, not a
  structural guarantee**, for every non-HTTP entry point — an accepted trade-off given no such
  entry point exists in the repository today to design a stronger guarantee against, named
  explicitly (Bypass Analysis) rather than left implicit, so it is not mistaken for a solved
  problem by a future reader.
- **Background-job permission staleness**: a role revoked after a job is enqueued but before it
  executes does not retroactively deny that job. Accepted because no live principal/session context
  survives to `Job.run()` to re-check against (confirmed, not assumed), and re-deriving one would
  require carrying a re-authenticatable credential into job payloads — a materially larger, riskier
  change than the exposure window it would close, for a repository with no evidenced job workload
  yet at all.
- **The resource-instance-granularity extension point is unfilled.** §4 rule 45 remains
  architecturally supported (a slot exists, at the correct layer) but not implemented — a real
  gap for whichever future task eventually resolves §24.14's three candidates, not a small addition
  once that choice is made, since it means new filtering logic at the same layer `ADR/0021`'s
  tenant scope already occupies.
- **The Role/Permission catalog's global-vs-per-Organization shape remains genuinely open** — this
  ADR's decision does not narrow that choice, which some readers might expect an authorization ADR
  to settle. Deliberately not settled here, per this task's explicit instruction against inventing
  unresolved business rules; flagged as a real limitation of this ADR's scope, not an oversight.

## Dependencies / Other Unresolved Related ADRs

Not resolved by this ADR, left open per the governing task's explicit boundary:

- **#1 Organization as tenant boundary** — already resolved by `ADR/0021`.
- **#19 Tenant isolation enforcement** — already resolved by `ADR/0021`.
- **#18 Authorization architecture** — resolved by this ADR (`ADR/0022`).
- **#2–#17, #20** — untouched; none of those entities' internal shape, or the migration-sequencing
  question (#20), is decided or implied by this ADR beyond the already-established requirement
  (§4 rule 44, unchanged by this ADR) that access be permission-aware.

## Testing / Verification Obligations

Named here as obligations for whichever future implementation task carries this decision out —
not performed by this ADR, mirroring `ADR/0021`'s identical convention:

- **Negative authorization tests** for every currently-untested surface this ADR newly assigns
  enforcement responsibility to (background-job enqueue-time permission checks, search-use-case
  permission checks, file-storage-use-case permission checks) — mirroring the existing pattern
  already proven for routes (`test_users.py`'s `TestAuthorization` class).
- **A same-Organization, wrong-permission test** and a **correct-permission, wrong-Organization
  test**, run together, proving neither `ADR/0021`'s tenant check nor this ADR's permission check
  alone is sufficient — the concrete regression test for this ADR's Critical Architectural
  Constraints.
- **A file-storage indistinguishability test** proving a forbidden-but-existing object and a
  genuinely nonexistent object produce the same response shape, per this ADR's file-storage
  decision.
- **A background-job enqueue-time rejection test** proving a tenant-scoped, permission-gated job
  cannot be enqueued by a caller lacking the relevant permission — extending, not duplicating,
  `ADR/0021`'s existing enqueue-time Organization-identifier obligation.

## Future Impact

- This ADR is the foundation the still-open resource-instance-granularity decision (§24.14, the
  extension point named above) will build on — whichever of the three named candidate mechanisms is
  eventually chosen plugs into the structural-filter slot this ADR defines, without needing to
  revisit this ADR's enforcement-point or composition decisions.
- The still-open Role/Permission catalog shape question (§24.1) can be resolved independently of
  this ADR, by a future ADR or amendment, without reopening this ADR's composition architecture —
  this ADR was deliberately written to hold under either answer.
- Any future non-HTTP entry point into a permission-gated use case (a CLI command, a command-bus
  handler, a scheduled job trigger) inherits this ADR's requirement that it invoke
  `AuthorizationService.require_permission()` explicitly — a requirement this ADR creates and future
  implementation work must satisfy, not an existing guarantee.
- If a future decision establishes that resource-instance-level authorization needs a policy-engine
  approach (Option 6, rejected above at current scale) after §24.14's mechanism choice is made, that
  is a new decision superseding the relevant part of this ADR — not a silent implementation
  deviation, per this repository's established convention (`ADR-0018`) for handling decisions that
  later need to change.

## Explicitly Unresolved Items

After this ADR, the Required ADR status is:

- **Required ADR #1** ("Organization as tenant boundary") — already resolved by `ADR/0021`. Not
  reopened, not revisited, not affected by this ADR.
- **Required ADR #19** ("Tenant isolation enforcement") — already resolved by `ADR/0021`. Not
  reopened, not revisited, not affected by this ADR.
- **Required ADR #18** ("Authorization architecture") — **resolved by this ADR (`ADR/0022`).**
  Permission granularity (resource+action via role indirection), the enforcement point
  (service/use-case boundary, with repositories deliberately kept permission-agnostic), and
  composition with `ADR/0021` (independent, both-mandatory, fail-closed) are decided. The
  resource-instance-granularity *mechanism* (§24.14's three candidates) and the Role/Permission
  catalog's global-vs-per-Organization shape (§24.1) are **explicitly not resolved by this ADR** —
  recorded as limitations of this ADR's scope, not silently decided by omission, per this task's
  own governing instruction.
- **Required ADR #2–#17 and #20** — remain fully unresolved. Nothing in this ADR decides, narrows,
  or implies a position on any of them beyond the already-frozen §4 rule 44 requirement that access
  be permission-aware, which predates this ADR and is not a new decision it introduces.

No Required ADR other than #18 is resolved, reinterpreted, or narrowed by this document. `ADR/0021`
is not modified, reopened, or reinterpreted by this document.
