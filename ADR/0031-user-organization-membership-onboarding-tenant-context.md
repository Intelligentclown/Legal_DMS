# ADR-0031: User–Organization Membership, Onboarding & Tenant-Context Semantics

**Status:** Proposed
**Date:** 2026-08-31

**Resolves:** the architectural gap identified by the Software Architect architecture-gate assessment
of 2026-08-30 (authorized as `T102`) — User↔Organization membership cardinality, first-Organization
creation semantics, first-Administrator semantics, membership↔RBAC composition, and active
tenant-context resolution. This gap is **not** one of the governed specification's own 20 enumerated
Required-ADR planning-list items (§21); see "Does not resolve" below for exactly where it sits relative
to that list, and "Evidence Inventory" for the sourcing. This is the first ADR in this series resolving
a gap outside the original 20-item list.

**Does not resolve:** Required ADR #10, #11, #12, #15, #16, #17, or #20 (untouched). Required ADR #1
("Organization as tenant boundary") and #18 ("Authorization architecture") were already resolved by
`ADR/0021` and `ADR/0022` respectively, are not reopened or re-resolved here, and this ADR's own gap
sits in the seam those two decisions deliberately left between them — both explicitly and repeatedly
decline, in their own text, to decide the question this ADR answers (see "Evidence Inventory"). Does
not reopen `ADR/0007`, `ADR/0009`, `ADR/0018`, `ADR/0019`, `ADR/0020`, `ADR/0021`, `ADR/0022`, or
`ADR/0023`–`ADR/0030`. `T98` (`ADR/0029`, PR #148) is unrelated and untouched.

**Dependencies:** `ADR/0021` (tenant-isolation enforcement mechanism — this ADR supplies the missing
input that mechanism has always required: how a User resolves to an Organization). `ADR/0022`
(authorization architecture — this ADR states how Organization membership composes with, without
redesigning, the existing Role/Permission model). `ADR/0020` (session commit/rollback policy — governs
the transaction boundary this ADR's onboarding-atomicity decision relies on). `ADR/0018`/`ADR/0019`
(authentication architecture — this ADR extends, without modifying, the existing JWT/`CurrentUser`
live-rederivation mechanism). `ADR/0029` (Activity/Audit boundary — cited for the audit-significance
of Organization/membership creation, composed with, not reopened).

## 1. Evidence Inventory

| Source | GOVERNED / DERIVED / evidence it supplies |
|---|---|
| Spec §4 rule 43 | GOVERNED — "Organization is the tenant/security boundary." |
| Spec §24.1 "Organization" | GOVERNED — root of ownership, no sub-organization requirement (default single-level tenancy). DERIVED — name/legal-name "near-certainly required." Explicitly **not specified**: full field list, lifecycle states. |
| Spec §24.1 "User," quoted verbatim | *"Whether the same person can be a User of more than one Organization... is ED — unresolved; the frozen architecture doesn't address multi-Organization users explicitly."* — the central gap this ADR closes. |
| Spec §24.1 "Role/Permission" | GOVERNED — Role groups Permissions, User assigned one-or-more Roles (existing). Global-vs-per-Organization catalogue shape explicitly `ED`, tracked under #1/#18 — this ADR narrows only the membership-composition question, not that catalogue question. |
| `ADR/0021`, quoted verbatim | *"How exactly a `User` resolves to an Organization is itself part of the still-open `User` ↔ Organization relationship question flagged in §24.1... and is not decided by this ADR."* Also GOVERNED by `ADR/0021`: the resolved Organization identifier must be resolved **server-side from trusted identity data, never client-supplied**; missing tenant context must fail closed. |
| `ADR/0022`, quoted verbatim | *"The exact shape of the `User` ↔ `Organization` relationship — already flagged as unresolved."* / *"Organization membership: not a field on `CurrentUser` today, and this ADR does not add one... deliberate."* Also GOVERNED: the composed sequence is Authentication → Organization/Tenant-Scope resolution (`ADR/0021`) → permission check (`ADR/0022`); neither check substitutes for the other; an Organization-scoped permission is never itself proof of tenant membership. |
| `ADR/0020` | GOVERNED — `get_db()` commits once per request on success, rolls back on any exception; repositories remain `flush()`-only and composable — multiple writes in one request commit or roll back together. |
| `ADR/0018` D4/D5 | GOVERNED — first-admin bootstrap is a one-time, interactive-only CLI command (no argv/env/config credential exposure); **no self-registration exists anywhere** — every User is admin-created. |
| `backend/.../identity.py` | RC — `User`, `Role`, `Permission`, `UserRole`, `RolePermission`, `RefreshToken`. No `Organization` class; no `organization_id` anywhere (confirmed by full-repository grep). |
| `backend/.../auth.py` `CurrentUser` | RC — fields `id`, `display_name`, `roles`, `is_authenticated` only. No Organization field. |
| `backend/.../jwt_authentication_provider.py` | RC — `get_current_user()` decodes only a `sub` (user id) claim from the JWT, then re-reads `user.is_active` and `roles` **fresh from the database on every request** via `UserRepository`. Roles are never trusted from the JWT itself. |
| `backend/.../user_repository.py` (`UserRepository` interface) | RC — `get_by_email`, `get_role_names(user_id)`, `assign_role`, `remove_role`, inherited `AbstractRepository` CRUD. No Organization-related method. |
| `backend/.../cli/bootstrap.py` (T67) | RC — the repository's only first-actor-creation code path. `run_bootstrap()` creates exactly one `User` + one `UserRole` (Administrator), inside one caller-owned transaction (`flush()` only, `main()` commits). Zero reference to Organization anywhere. |
| `docs/BusinessRequirementsPlan.md` | Confirms this is a single-practice/internal-staff tool (no client-facing portal, no self-registration use case named anywhere) — cited as context for the cardinality decision below, not as a frozen rule. |

## 2. Problem Statement

`ADR/0021` fully specifies *how* tenant isolation is enforced once a resolved Organization context
exists, and `ADR/0022` fully specifies how authorization composes with that context — but neither
states, nor was authorized to state, how a `User` comes to have an Organization context in the first
place. No Organization concept exists anywhere in the repository today. Without this ADR, the
Organization/Tenant Core vertical slice cannot be implemented without an implementer silently inventing
cardinality, onboarding, and tenant-resolution semantics — precisely the "coding AI invents domain
semantics" failure mode the specification's own highest-risk list names first (§1.6 item 6).

## 3. Decision Scope

Exactly the seven items `T102`'s authorization approved: cardinality; first-Organization creation
semantics; first-Administrator semantics; membership↔RBAC composition; active tenant-context
resolution; minimum `CurrentUser`/authentication consequence; minimum existing-data consequences
(disclosure only). Nothing beyond this — see §15 "Explicit Non-Goals."

## 4. Governing Constraints (reused, not reopened)

- Organization is the tenant/security boundary (§4 rule 43) — not reinterpreted.
- `ADR/0021`'s enforcement mechanism (mandatory application-layer scoping + RLS backstop, fail-closed,
  server-side-only resolution) — this ADR supplies its missing input, does not alter the mechanism.
- `ADR/0022`'s composed sequence and "Organization membership is not itself proof of authorization"
  principle — not altered.
- `ADR/0020`'s one-request-one-commit-boundary policy — this ADR's onboarding atomicity decision
  (§6.2) relies on it directly, unchanged.
- `ADR/0018`/`ADR/0019`'s authentication mechanism (JWT + revocable refresh token, Argon2id, no
  self-registration, interactive-only bootstrap) — not redesigned; extended at exactly one point
  (§10).
- `ADR/0029`'s Activity/Audit boundary — composed with for the audit-significance of Organization/
  membership creation (§4 rule 46), not redesigned.

## 5. Current-State Findings (RC, direct repository inspection)

No `Organization` table, class, or column exists anywhere in `backend/src/app` (confirmed by
full-repository grep, outside tests). `CurrentUser` carries no Organization field. `bootstrap.py`
creates a `User` + `Administrator`-role `UserRole` and nothing else. `JwtAuthenticationProvider`
already re-derives roles live from the database on every request rather than trusting JWT claims —
this is the one existing mechanism this ADR's tenant-context decision (§10) directly extends rather
than replaces.

## 6. Proposed Decision

### 6.1 User↔Organization cardinality — **DECIDED BY ADR-0031**

**A `User` belongs to at most one Organization (optional one-to-one), not many-to-many.**

No repository evidence — the governed specification, `ADR/0021`, `ADR/0022`, or
`BusinessRequirementsPlan.md` — names any driving requirement for a single person to act within more
than one Organization. Every seeded Role is internal staff (`ADR/0018` D5: no self-registration, no
client-facing portal); the product is evidenced throughout as a single-practice internal tool, not a
multi-firm platform. Choosing one-to-one is a deliberate architectural decision, not an oversight: it
is the smallest structure consistent with every piece of evidence gathered, and it eliminates the
active-tenant-context-selection problem by construction rather than by solving a harder version of it
that nothing in evidence actually requires (see Alternatives, §7.1).

### 6.2 First-Organization creation semantics — **DECIDED BY ADR-0031**

**Organization creation is folded into the existing first-admin bootstrap flow (`T67`/`ADR-0018` D4),
not a separate onboarding flow.** The existing `bootstrap-admin` CLI command is extended so that, in
the same idempotency check and the same caller-owned transaction (`ADR-0020`) that today creates the
first `User` + `Administrator` `UserRole`, it also creates exactly one `Organization` row and links the
new `User` to it (§6.4). No HTTP endpoint, no self-service "create your firm" flow, and no
unauthenticated code path creates an Organization — consistent with `ADR/0018` D5's "no
self-registration" decision, extended by direct analogy to Organization creation, since nothing in
evidence distinguishes "creating the first User" from "creating the first Organization" as separate
authorization events for a single-Organization-per-deployment product.

- **Authorized actor:** whoever can run the interactive CLI against the deployment's own database —
  identical trust boundary to today's `bootstrap-admin`, not widened or narrowed.
- **Security context:** none beyond what `ADR/0018` D4 already requires (interactive-only, no
  credential in argv/env/config) — this ADR adds no new security surface.
- **Timing relative to bootstrap:** simultaneous, not sequential — Organization creation, User
  creation, and membership linkage occur in the same idempotency check and the same transaction, so
  a deployment can never reach a state with a User but no Organization, or an Organization but no
  Administrator.

### 6.3 First-Administrator semantics — **DECIDED BY ADR-0031**

**The bootstrapped Administrator's relationship to the Organization it creates is membership, carrying
the existing `Administrator` Role — no separate "ownership" flag or concept is introduced.** The
existing seeded `Administrator` Role already represents the highest-privilege role in the RBAC catalogue
(`ADR/0022`'s own evidence: fifty-nine role→permission grants, `is_system_role`); inventing a distinct
"owner" relationship on top of it would duplicate authority the Role system already expresses, for a
distinction (owner vs. administrator) no evidence anywhere requires. Minimum role linkage: the existing
`UserRole` row (Administrator), unchanged in shape, plus the new membership link established in §6.4.

### 6.4 Membership↔RBAC composition — **DECIDED BY ADR-0031**

**Organization membership is represented as a direct, nullable `organization_id` foreign key on
`users`** — not a separate join table. Because cardinality is fixed at one-to-one (§6.1), a join table
would model a many-to-many relationship this ADR explicitly does not adopt; a direct FK is the simplest
structure consistent with the decided cardinality, and mirrors this repository's own existing
direct-FK precedent for single-valued relationships (e.g. `matters.matter_number`, `documents.
matter_id`). Nullable, not `NOT NULL`, because it must remain possible to represent a `User` row that
has not yet completed onboarding (or, in principle, a future system/service account with no tenant) —
any tenant-scoped operation attempted with a `None` value fails closed, per `ADR/0021`'s own principle,
not silently proceeds unscoped.

**Membership is structurally distinct from `UserRole`, and the two remain orthogonal, not merged:**
`organization_id` answers *which Organization's data this User may be scoped into* (an `ADR/0021`
tenant-boundary question); `UserRole` continues to answer *what this User may do*, unchanged (an
`ADR/0022` authorization question). **Roles and Permissions remain global, exactly as they are today
— not made Organization-scoped by this decision.** The global-vs-per-Organization Role/Permission
catalogue question §24.1 flags remains open, tracked under #1/#18, not resolved or narrowed here; this
ADR decides only that Organization membership does not, by itself, require that catalogue question to
be resolved — a `User`'s roles apply within whichever single Organization their `organization_id`
places them, without the catalogue itself needing to know about Organizations.

### 6.5 Active tenant-context resolution — **DECIDED BY ADR-0031**

**Because cardinality is fixed at one-to-one, there is no "active Organization" selection to make** —
a `User` has exactly zero or one Organization, and the resolution mechanism is simply "read it." This
is a direct, deliberate consequence of §6.1, not a separate mechanism bolted on afterward.

**Resolution mechanism:** `JwtAuthenticationProvider.get_current_user()` is extended to read the
authenticated `User` row's `organization_id` **from the database, on every request, exactly the way it
already re-reads `roles`** — never from a JWT claim, never from client-supplied input of any kind. The
JWT continues to carry only `sub` (user id); it is not extended with an Organization claim. This
directly satisfies `ADR/0021`'s existing requirement (*"derived from the caller's verified identity,
not from any client-supplied header, query parameter, or request body field"*) using the exact
mechanism this repository already uses for the structurally identical roles problem — no new pattern
is introduced. **Server-side trust boundary:** identical to today's roles boundary — the database row
addressed by the JWT's verified `sub` claim, nothing else.

### 6.6 Minimum `CurrentUser`/authentication consequence — **DECIDED BY ADR-0031**

`CurrentUser` (`application/interfaces/auth.py`) gains exactly one new field:
`organization_id: str | None = None`, populated by `JwtAuthenticationProvider` per §6.5. No other field
changes. `AuthenticationProvider`'s abstract signature (`get_current_user(token) -> CurrentUser`) is
unchanged. `ADR/0018`/`ADR/0019`'s token issuance, refresh, and Electron-storage mechanisms are
untouched — this is a read-side extension to identity resolution, not an authentication-mechanism
change.

### 6.7 Minimum existing-data consequences — disclosure only, **not** Required ADR #20

Adding a nullable `organization_id` column to `users` is additive and requires no destructive change to
`UserRole`, `RolePermission`, or `RefreshToken`. What it does require, disclosed here and left entirely
to Required ADR #20: a decision for how this repository's existing `User` rows (created before any
Organization concept existed) are associated with an Organization — whether via a single backfilled
Organization created for existing data, a manual reconciliation step, or another mechanism. This ADR
states the requirement exists; it does not sequence, design, or resolve it.

## 7. Alternatives Considered

### 7.1 Cardinality

| Alternative | Assessment |
|---|---|
| **Many-to-many, with a join table** | Rejected — no repository evidence names a driving requirement for it; it would require designing and this ADR could not avoid designing an active-tenant-context-selection mechanism (API surface, session/JWT shape, switching UX) that nothing in evidence calls for, directly risking the "invent unrelated design surface" failure this task's own scope excludes. |
| **One-to-one, enforced structurally (selected)** | The smallest structure consistent with all evidence; eliminates tenant-context selection by construction. Revisitable later via a superseding ADR if a genuine multi-Organization requirement is ever evidenced (see Consequences, §14). |
| **Unresolved, deferred again** | Rejected — this is precisely what `T102` was authorized to stop happening; deferring again would leave the Organization/Tenant Core slice permanently ungated. |

### 7.2 First-Organization creation

| Alternative | Assessment |
|---|---|
| **A new, separate self-service "create your firm" onboarding flow/endpoint** | Rejected — directly contradicts `ADR/0018` D5's already-accepted "no self-registration" decision; no evidence names a multi-firm signup use case this product needs. |
| **Folded into the existing `bootstrap-admin` CLI, same transaction (selected)** | Reuses an already-accepted, already-implemented, already-tested pattern exactly; adds no new authorization surface. |

### 7.3 Membership representation

| Alternative | Assessment |
|---|---|
| **A dedicated `organization_memberships` join table** | Rejected for this cardinality — a join table exists to represent many-to-many or to carry per-relationship attributes (e.g. a join-specific role); §6.1's one-to-one decision and §6.3's "reuse the existing Role system, no new per-membership attribute" decision leave nothing for a join table to carry that a direct FK does not already express. |
| **A direct, nullable `organization_id` FK on `users` (selected)** | Matches the decided cardinality exactly; matches this repository's own existing direct-FK convention. |

### 7.4 Tenant-context resolution mechanism

| Alternative | Assessment |
|---|---|
| **Carry `organization_id` as a JWT claim** | Rejected — would make a stale/reassigned Organization membership persist until the access token naturally expires, breaking the same "deactivated user takes effect immediately" property the specification explicitly praises the existing live-role-rederivation design for (§24.14); also a second, inconsistent pattern alongside roles' existing live-lookup approach. |
| **Live database lookup on every request, mirroring the existing roles mechanism (selected)** | Zero new pattern; immediate effect on reassignment/deactivation; directly satisfies `ADR/0021`'s server-side-resolution requirement using established precedent. |

## 8. Rationale / Trade-offs

The unifying rationale across §6 is **reuse over invention**: every decision extends an existing,
already-accepted mechanism (bootstrap CLI, live-rederivation, direct-FK convention, the existing Role
system) rather than introducing a structurally new one, and the cardinality decision (§6.1) is chosen
specifically because it is the option that requires inventing the *least* new surface while remaining
fully consistent with every piece of gathered evidence. The principal trade-off is optionality:
choosing one-to-one now means a genuine future multi-Organization requirement (a person working across
two client firms, for instance) would need a superseding ADR and a real migration, not a config toggle
— accepted deliberately, because no evidence today shows that requirement exists, and speculatively
building for it now would itself be the kind of invented complexity this task's evidence discipline
exists to prevent.

## 9. Security / Tenant-Isolation Implications

- Satisfies `ADR/0021`'s fail-closed, server-side-only resolution requirement directly (§6.5).
- A `None` `organization_id` must be treated by every tenant-scoped operation exactly as `ADR/0021`
  already requires missing tenant context to be treated: reject, never proceed unscoped.
- No new client-facing input, header, or claim is introduced that could be used to assert a tenant
  identity — the only server-side source of truth is the `users.organization_id` column, read live.
- `ADR/0022`'s principle that "an Organization-scoped permission is never itself proof of tenant
  membership" is unaffected — membership (this ADR) and permission (existing RBAC, unchanged) remain
  two independently-checked, non-substitutable gates.

## 10. Authentication / `CurrentUser` Implications

See §6.6. Summary: one new field on `CurrentUser`, populated by an extension to
`JwtAuthenticationProvider.get_current_user()` mirroring its own existing roles-lookup call; no change
to token issuance, refresh, revocation, hashing, or Electron storage (`ADR/0018`/`ADR/0019` untouched).

## 11. RBAC Implications

See §6.4. Summary: `UserRole`/`RolePermission`/`roles`/`permissions` are structurally unchanged; the
global-vs-per-Organization catalogue question remains exactly as open as it was before this ADR,
tracked under #1/#18, not narrowed or resolved here.

## 12. Data / Migration Consequences (disclosure only)

See §6.7. A nullable `users.organization_id` column is additive; backfilling/reconciling existing
pre-Organization `User` rows is Required ADR #20's territory, named as a requirement, not designed.

## 13. API / Client Consequences (architectural-contract level only)

Any future authenticated API response/contract that exposes `CurrentUser`-derived context may now
include the resolved Organization identity (name/id) alongside the caller's identity and roles, exactly
as it already exposes roles today — no new endpoint, no new client-supplied parameter, and no change to
existing route authorization sequencing (`ADR/0022`'s composed sequence is unaffected). Exact contract
shape is deferred to the API-contracts phase, per §16 of the governed specification — not decided here.

## 14. Activity / Audit Implications

Per `ADR/0029`'s existing coverage-classification test (creation, modification, status changes,
relationship changes — §17.9/§21), Organization creation and the first-Administrator membership
linkage are both audit-significant events (composing directly with spec rule 46 and `ADR/0029`'s own
"creation" category) and appropriate for Activity visibility as well. `ADR/0029` is not reopened,
modified, or reinterpreted by this statement — it already establishes that both mechanisms exist and
what triggers them; this ADR only confirms Organization/membership creation falls within that
already-decided coverage, exactly as `ADR/0029` itself anticipated for every future entity this
specification introduces.

## 15. Implementation Constraints and Explicit Non-Goals

**Implementation constraints for the future Organization/Tenant Core slice** (binding on that future,
separately-authorized task, not performed here): the `organizations` table and the `users.
organization_id` column must both carry `ADR/0021`'s mandatory `organization_id`-on-tenant-scoped-table
discipline appropriately (the `organizations` table itself is the tenant root and does not scope
itself; `users` gains the FK described in §6.4); `bootstrap.py`'s extension must remain inside the
existing `ADR/0020` transaction boundary (Organization + User + `UserRole` + membership FK, one
commit/rollback unit); `JwtAuthenticationProvider`'s extension must not introduce a JWT claim for
Organization (§7.4); RLS backstop policies for `organizations`/`users` must follow exactly the
`FORCE`d, default-deny shape `ADR/0021` already mandates.

**Explicit non-goals of this ADR** (per `T102`'s own authorization, restated for traceability):
Required ADR #10, #11, #12, #15, #16, #17, and #20 are not resolved. `ADR/0021`, `ADR/0022`, `ADR/0020`,
`ADR/0029`, `ADR/0018`, `ADR/0019` are not reopened or redesigned. No Party, Property, Matter, File,
Document, Workflow, Government Process, or Finance semantics are introduced. No Organization field
beyond name/legal-name (already `DERIVED` in §24.1, not newly invented here) is added. No application
code, schema migration, or frontend/backend implementation is performed by this ADR. This ADR does not,
and cannot, authorize implementation of the Organization/Tenant Core slice — per `T102`'s own governing
instruction, that slice must be re-gated against this ADR by a fresh Project Manager/Control Tower
assessment before any implementation task is authorized.

## 16. QA / Verification Strategy and Acceptance Criteria

A future implementation task, once separately authorized, should be verifiable against:

- **Cardinality invariant:** a `users.organization_id` FK cannot reference more than one Organization
  per User by construction (a single nullable column, not a join table) — no test can construct a
  counter-example.
- **Bootstrap atomicity:** a negative test proving that a failure partway through the extended
  `bootstrap-admin` flow (Organization created, User creation fails, or vice versa) leaves **no**
  partial state — mirrors `ADR/0020`'s own existing `test_get_db_transaction_policy.py` pattern.
- **Live tenant-context rederivation:** a test proving that changing a `User`'s `organization_id`
  takes effect on the *next* request without requiring token reissue — mirrors the existing
  roles-rederivation behavior and `ADR-0018`'s own praised "deactivated user takes effect immediately"
  property.
- **Fail-closed on missing context:** a negative test proving a tenant-scoped operation attempted with
  `CurrentUser.organization_id is None` is rejected, never silently unscoped — mirrors `ADR/0021`'s own
  Testing/Verification Obligations.
- **No client-supplied tenant assertion:** a negative test proving a client-supplied Organization
  identifier (header, query parameter, body field) has no effect on the resolved tenant context.
- **RBAC non-interference:** a test proving `UserRole`/`RolePermission` behavior is unchanged by this
  ADR — a `User`'s permissions before and after gaining `organization_id` are identical, confirming
  membership and authorization remain independently checked.

These are acceptance criteria for a future implementation task to satisfy, not tests this ADR itself
adds — no test file is created or modified by this ADR.

## References

- `docs/Legal_DMS — Domain Model & Functional Specification.md` §4 rule 43, rule 46; §1.6 item 6;
  §24.1 (Organization, User, Role/Permission); §16; §17.9; §21.
- `ADR/0018-authentication-authorization-architecture.md` (D4, D5)
- `ADR/0019-authentication-provider-interface-change.md`
- `ADR/0020-session-commit-rollback-policy.md`
- `ADR/0021-organization-tenant-boundary-enforcement.md`
- `ADR/0022-authorization-architecture.md`
- `ADR/0029-activity-vs-audit-architecture-boundary-and-coverage.md`
- `backend/src/app/infrastructure/persistence/models/identity.py`
- `backend/src/app/application/interfaces/auth.py` (`CurrentUser`, `AuthenticationProvider`)
- `backend/src/app/application/interfaces/user_repository.py`
- `backend/src/app/infrastructure/auth/jwt_authentication_provider.py`
- `backend/src/app/infrastructure/cli/bootstrap.py`
- `docs/BusinessRequirementsPlan.md`
