# ADR-0036: Fresh-Installation Party Enablement Boundary

**Status:** Proposed
**Date:** 2026-09-10

**Resolves:** the precise boundary under which an installation may treat the `ADR/0035`
Party-migration-window prohibition as vacuous and enable ordinary, application-visible Party
creation, for the fresh-installation party-enablement slice authorized by task `T121`. This ADR
decides the objective fresh/empty-installation classification, the failure-closed condition under
which `ADR/0035`'s migration-window Party prohibition is vacuous, the install-agnostic
prerequisites (Address tenant finalization per `ADR/0035` section 6, `ADR/0021` tenant-security,
`ADR/0022` authorization) that must still be satisfied on every path, an objective hold-until gate
for ordinary Party writes, coexistence with the T108-T120 legacy migration process, the exact
`ADR/0035` clauses this decision qualifies or supersedes versus those that remain fully applicable,
and the dependency sequence it creates for future tasks.

**Does not resolve:** Required ADR #20 (migration strategy). This ADR deliberately resolves only a
fresh-installation boundary and does not narrow, sequence, or reopen the global cutover/removal
choreography, legacy staged-column final `NOT NULL` enforcement already delegated by `ADR/0035`, the
legacy backfill completion gate inside the governed reconciliation process (T108-T118), the
legacy-path final nullability of `party_id` bridge columns, `client_id`/`clients` retirement, bridge
removal, application cutover, or any other remaining planning-list item. It does not reopen
`ADR/0021`, `ADR/0022`, `ADR/0033`, `ADR/0034`, or `ADR/0035` in any legacy-path clause. No
`IMPLEMENTATION_QUEUE.md` governing `T121` transition is declared here; Required ADR #20 remains
globally unresolved after this ADR.

**Dependencies:** `ADR/0020-session-commit-rollback-policy.md`,
`ADR/0021-organization-tenant-boundary-enforcement.md`,
`ADR/0022-authorization-architecture.md`, `ADR/0033-party-client-migration-organization-boundary.md`,
`ADR/0034-party-client-migration-persistence-and-execution-ledger.md`,
`ADR/0035-party-persistence-schema-contract-and-tenant-safe-migration-bridges.md`,
`docs/PartyClientReconciliationContract.md`, and the T108-T120 governed evidence chain. Current
repository schema facts used by this ADR were re-verified directly on the authoring baseline:
`parties`, `matter_parties`, `client_party_migration_ledger`, and the five direct `party_id` bridge
columns exist; `clients.organization_id`, `addresses.organization_id`, and every staged downstream
`organization_id` column remain nullable; Row-Level Security is enabled and forced on exactly
`organizations` and `users`; the runtime role `legal_dms_app` is the non-owning application role; and
no `parties` permission codes, `parties` routes, or ordinary Party write path exist.

## Problem

`ADR/0035` made ordinary Party creation unavailable during the governed migration window and made
migration-time writes the only allowed Party writes until governed backfill completes. Those rules
presuppose an installation that starts with legacy `clients` data needing reconciliation. A brand
new installation created from the repository's migration head has no such data: there is nothing to
reconcile, nothing to backfill, and no unmigrated Client rows to coexist with Party rows. Yet the
repository today has no governed answer for (1) what "fresh/empty" objectively means, (2) when
`ADR/0035`'s migration-window prohibition is genuinely vacuous rather than merely asserted, (3)
which prerequisites ordinary Party creation on a fresh installation must still satisfy, and (4) how
that boundary coexists with the T108-T120 legacy process so nothing invented here weakens the
legacy path or the mandatory tenant-safety invariants.

Unresolved, the following specific failure modes are open:

- an operator labels a database "fresh" without any structural verification, hiding legacy data that
  should still be governed by the T108-T120 reconciliation process;
- a developer treats "we only have dummy/test data" as permission to enable ordinary Party writes,
  then loses the ability to distinguish disposable development data from retained legacy-shaped
  business data;
- `addresses.organization_id`, Address RLS, Party RLS, the non-owning runtime role, or Party
  permission codes are skipped "because this is a fresh install," silently waiving the very
  tenant-safety and authorization prerequisites that protect cross-Organization integrity;
- the fresh path is implemented in a way that contradicts, duplicates, or obsoletes T108-T118
  tooling, the `party_id` compatibility bridges, or `client_party_migration_ledger`, forcing a
  second, divergent schema truth.

## Options Considered

1. **No boundary change: keep ordinary Party creation disabled everywhere until the entire legacy
   migration closes.** Pros: simplest; nothing new to verify; no fresh-installation privilege.
   Cons: a genuinely empty installation can never enable ordinary Party creation without first
   standing up legacy-shaped data and running the full T108-T120 process against it — meaningless
   work on a database that has nothing to migrate, and the reason task `T121` exists at all. The
   repository would permanently block a normal business path on a process whose entire premise is
   absent.

2. **Trust the operator's stated classification ("we promise this is an empty install").** Pros:
   low verification cost; convenient for legitimate fresh deployments. Cons: assertion is not
   proof. An operator with legacy data, or with accumulated "harmless" test rows, can mislabel the
   installation and enable ordinary Party writes against data that the T108-T120 boundary was
   designed to protect. This is exactly the failure class `ADR/0021` rejected application-layer-only
   enforcement for: a rule that exists only in someone's statement, not in anything the database can
   verify, fails open at the worst possible moment.

3. **Mechanically classified, install-agnostic prerequisites, with the fresh path as a
   formally-enabled subset of the same database (selected).** A fresh/empty installation is a
   mechanically verifiable property: zero rows in every migration-relevant and business table, plus
   never containing real customer data. On such an installation `ADR/0035`'s migration-window
   prohibition is vacuous (nothing to reconcile, nothing to backfill, no unmigrated Client rows),
   and ordinary Party creation becomes available behind an objective, failure-closed gate. The gate
   re-uses exactly the install-agnostic prerequisites `ADR/0035`, `ADR/0021`, and `ADR/0022` already
   require for any Party visibility, so nothing is waived on the fresh path; the legacy path is
   untouched in every non-vacuous case. Pros: failure-closed classification (any ambiguity resolves
   to legacy, keeping the T108-T120 process supreme); no tenant-safety or authorization waiver;
   legacy coexistence preserved because the fresh path exercises the exact same schema, ledger, and
   tooling surface rather than a second one. Cons: it requires a defined disposal/reset discipline
   for genuinely disposable development/test databases (a real but bounded operational cost), and it
   requires later implementation, not this ADR, to build the mechanical zero-row verification.

Option 3 is adopted.

## Decision

### 1. Objective installation classification

An installation is classified by its **other** `ADR/0035`-relevant state, not its origin story.

**Genuinely fresh / empty installation.** An installation is genuinely fresh/empty only when all of
the following hold, verified mechanically (row presence and shape, never operator assertion):

- the database was migrated from the repository's own, currently-authoritative migration head rather
  than seeded from any migrated or duplicated database;
- every migration-relevant and business table carries **zero rows**, covering at minimum `clients`,
  `client_contacts`, `addresses`, `properties`, `property_owners`, `matters`, `appointments`,
  `invoices`, `payments`, `parties`, `matter_parties`, and `client_party_migration_ledger` — and the
  same zero-row condition extends to any other table whose rows would be subject to the legacy
  migration; and
- the installation has never contained real customer/production business data.

**Disposable development/test-only data.** A database whose rows are purely development, test,
rehearsal, or demo data, in a database created specifically for that purpose and that can be
destroyed and recreated, is disposable. An installation that contains disposable data is classified
fresh **only after** a governed disposal/reset action: destroy and recreate the database (preferred),
or a controlled, documented reset deleting every business row and confirming the zero-row condition.
Disposable origin alone never classifies an installation fresh; the data must actually be removed or
the database discarded, and the zero-row condition re-verified.

**Legacy-with-business-data.** Any installation that contains rows representing or derived from real,
retained, production, or customer business data — or any legacy-shaped rows the operator intends to
keep — is classified **legacy** and remains fully governed by the ADR-0033/0034/0035 chain and the
T108-T120 process. This is the **default classification**: any ambiguity, any doubt about a row's
origin, or any verification failure resolves to legacy, never to fresh. "Not customer data" alone is
never a sufficient basis for the fresh classification, because the structural risk the migration
boundary exists to protect (legacy-shaped rows that would need reconciliation) does not depend on
whether those rows were once real.

**Migrated.** A legacy installation on which the governed backfill (T118 executor) has completed per
`client_party_migration_ledger` is migrated; its Party behavior remains governed by the legacy-path
finalization obligations (staged-column `NOT NULL` enforcement, cutover, removal) that this ADR does
not decide and Required ADR #20 still blocks.

An installation never changes its classification by operator declaration alone. A legacy or migrated
installation may become fresh only through destruction/recreation or a governed full reset that
removes all business data — and doing so is itself a separately authorized operation, never an
incidental privilege of this ADR.

### 2. Vacuous migration-window condition (fail closed)

`ADR/0035` section 5's rule — "ordinary Party creation must remain unavailable during the governed
migration window" — and section 4's coexistence safety conditions ("before legacy Party backfill
begins, `parties` must be empty of ordinary Party business rows"; "new Party rows may not coexist
with unmigrated Client rows"; "Party creation remains unavailable during the migration window") are
**vacuous on, and only on, a genuinely fresh/empty installation** as classified in Decision 1.

The vacuous determination is made exclusively by the mechanical zero-row verification of Decision 1.
It is never made by operator assertion, by the presence of a fresh-installation feature flag, by the
absence of visible customer rows, or by a belief that some data is "only" disposable. If any
migration-relevant or business row exists anywhere on the installation, the migration window and the
T108-T120 process apply in full and ordinary Party creation remains unavailable. In particular, an
installation that carries unresolved legacy Client/business relationships is never a vacuous case,
regardless of how it was labeled or created.

Because a genuinely fresh/empty installation has no legacy rows, the vacuous condition also implies
the `ADR/0035` section 5 precondition "migration-time writes are the only allowed Party writes until
the entire governed backfill and bridge population is complete" has nothing for it to govern: the
same zero-row verification that proves the migration window vacuous proves there is no backfill to
complete. This ADR does not re-state that rule; it defines the one mechanical condition under which
the rule has no object.

### 3. Fresh and legacy paths

**Fresh path.** On a genuinely fresh/empty installation, ordinary, application-visible Party creation
becomes available once the install-agnostic prerequisites of Decisions 4 through 7 are all met. The
fresh path uses the same `parties`, `matter_parties`, `client_party_migration_ledger`, `party_id`
bridge, and staged-column schema the legacy path uses; it does not create a second schema, second
ledger, or second Party write path. `ADR/0035` section 4's coexistence invariant ("new Party rows
may not coexist with unmigrated Client rows") continues to hold on the fresh path by construction:
the classification requires zero Client rows, and the fresh path must not create legacy `clients`
rows to place alongside Party rows. If a future feature cannot satisfy that invariant (for example,
it needs ordinary Client-row creation to coexist with Party rows), that is a migration-strategy
question for Required ADR #20, not a silent change to this boundary.

**Legacy path.** Any non-fresh installation keeps the full `ADR/0033`/`ADR/0034`/`ADR/0035` wiring
exactly as it stands: refused ordinary Party writes; backfill only through T108-T118 governed
preflight/reconciliation/executor/ledger; staging and bridge columns populated only by governed
migration. Nothing in this ADR changes the legacy path, the T118 executor's behavior, the preflight/
staleness gates, or the `client_party_migration_ledger` contract.

**Path switching.** A fresh installation that later acquires legacy-shaped data (for example, a
decision to import legacy Clients) switches to the legacy path at that moment — the migration window
applies thereafter, fail closed — and can only return to fresh by a governed destruction/reset, per
Decision 1. A legacy/migrated installation never switches to fresh by declaration.

### 4. Address tenant finalization (install-agnostic; no waiver)

`ADR/0035` section 6 remains fully applicable on the fresh path. Before any normal Party write,
every address involved must satisfy:

- `addresses.organization_id` is final `NOT NULL`, not the currently-staged nullable reconciliation
  column;
- Address rows are Organization-scoped at creation (on a fresh path they are created tenant-owned;
  there is no reconciliation/backfill stage to backfill into);
- same-Organization integrity is enforced by the composite support and reference rules `ADR/0035`
  section 6 fixes: `(organization_id, id)` support keys, and the Party/Property <-> Address
  same-Organization composite references;
- Address Row-Level Security is active under `ADR/0021` before ordinary Party writes, exactly as the
  legacy path requires.

The only thing this ADR qualifies in `ADR/0035` section 6 is its reconciliation-stage framing: the
clause "nullable only during the reconciliation/backfill stage" has no matching stage on a fresh
path, so the nullable staging state is never occupied there — but the final `NOT NULL` and
same-Organization/Rls conditions are prerequisites on the fresh path exactly as on the legacy path.
There is no tenant-safety waiver on either path.

### 5. `ADR/0021` Party tenant-security prerequisites (install-agnostic)

Composing directly with `ADR/0021`, and required before any ordinary, application-visible Party write
on **both** the fresh and legacy paths:

- `parties.organization_id` is `NOT NULL` and Organization-scoped from first insert onward (already
  enforced by the T116 schema);
- every Party read/write path requires an Organization scope as a mandatory, non-optional input at
  the application layer (`ADR/0021`, "Repository / data-access layer"); missing scope fails closed.
- `parties` has forced default-deny Row-Level Security effective under the non-owning runtime role
  (`legal_dms_app`) before it becomes a normal application-visible table — `ADR/0021`'s RLS
  backstop, with `FORCE ROW LEVEL SECURITY` and a default-deny policy, effective for the role that
  actually serves runtime requests;
- runtime Party writes are performed under the non-owning runtime role, never the table-owning
  migration/admin role.

No Party permission, route, or normal write path exists today; these obligations are prerequisites
that whichever later implementation slice builds the fresh enablement must satisfy in this exact
order: RLS and runtime-role effectiveness and app-layer scoping before permission-before-API, before
ordinary Party creation is exposed.

### 6. `ADR/0022` authorization prerequisite (install-agnostic; no redesign)

Composing directly with `ADR/0022`, the existing resource-and-action RBAC mechanism
(`RbacAuthorizationService`, `RequirePermission`, and the `Role`/`Permission`/`UserRole`/
`RolePermission` schema) is the adopted authorization mechanism and is not redesigned. Before any
normal Party API exposure on either path:

- the permission catalog must contain explicit Party permission codes (the `parties` resource with
  read/write/delete actions, or the exact equivalent names a later permission task chooses), seeded
  like the existing eighteen codes;
- those codes must be granted to the seeded roles per governing policy, in the same role→permission
  grant structure already tested for `matters`/`clients`;
- every Party-facing route or use case must be gated by `RequirePermission` exactly as `users.py`
  gates `users:manage`/`roles:manage`, with the permission check at the service/use-case boundary
  per `ADR/0022`.

No full redesign of `ADR/0022` is required: `parties` is simply another resource in the existing
`resource:action` catalog. This prerequisite applies identically to fresh and legacy installations,
and the legacy migration executor (T118) remains the one governed Party write path that precedes
permission-code roll-out only in the sense that its writes are migration writes, not "normal Party
API exposure."

### 7. Objective failure-closed normal-write enablement gate

Ordinary Party creation and application visibility are enabled on the fresh path only when **every**
condition below is verifiably true. There is no "migration is probably complete enough" criterion
and no "this install doesn't really need X" exception. If any condition is unmet, or cannot be
verified, ordinary Party writes remain disabled.

1. Installation classification: genuinely fresh/empty per Decision 1, verified by the mechanical
   zero-row condition (Decision 2).
2. Address finalization per Decision 4: `addresses.organization_id NOT NULL`, Organization-scoped
   creation, same-Organization integrity, Address RLS active.
3. Party tenant security per Decision 5: Party RLS forced default-deny effective under the
   non-owning runtime role; runtime writes under that role; mandatory application-layer
   Organization scoping on every Party read/write path.
4. Authorization per Decision 6: Party permission codes exist, are granted, and every Party-facing
   route/use case is permission-gated.
5. No legacy migration window applies (Decision 2's vacuous condition mechanically satisfied).

For a legacy or migrated installation, ordinary Party writes additionally remain blocked by the
legacy-path obligations this ADR does not decide (staged-column final `NOT NULL` enforcement,
cutover, retirement), which are already governed and remain under Required ADR #20. This ADR does
not create a legacy-path enablement gate; it goes no further than stating that Required ADR #20
still decides when the legacy path reaches its own equivalent point.

### 8. Required ADR #20 boundary (what remains blocked)

Required ADR #20 (migration strategy) is **not resolved** by this ADR and continues to block:

- final global cutover choreography: application cutover from Client-master to Party/MatterParty
  semantics, `matters.client_id` removal, downstream `client_id` removal, and `clients` retirement;
- removal of the `party_id` compatibility bridges and of now-unneeded legacy retention paths;
- legacy staged-column final `NOT NULL` enforcement over the reconciled legacy data set (`ADR/0035`
  section 10's final `party_id` nullability and the legacy staged `organization_id` columns), which
  presupposes reconciled data this ADR does not create;
- the decision of when a partially-used legacy installation is complete enough to move to the
  post-cutover surface.

This ADR opens a narrow, explicitly-bounded slice of that future (ordinary Party creation on a
genuinely fresh/empty installation) without deciding any of the cutover/removal choreography above.
Any reading that treats this ADR as resolving some or all of Required ADR #20 is rejected.

### 9. Coexistence and future compatibility

- The fresh path must never invalidate, fork, or shadow the T108-T120 pipeline: preflight,
  reconciliation artifacts, staleness checks, the T118 executor, and `client_party_migration_ledger`
  remain fully functional and authoritative on the legacy path; the fresh path simply has no
  migration work for them, because the same zero-row verification proves no migration is needed.
- The migration-era schema surface (`parties`, `matter_parties`, `ledger`, `party_id` bridges,
  staged `organization_id` columns) remains present and identical on a fresh installation. It is
  dormant for migration purposes because there is nothing to migrate; it is not retired, renamed, or
  replaced. Nothing from this ADR may be cited as authorization to remove bridges, drop staged
  columns, or retire `client_id`/`clients`, none of which this ADR authorizes.
- `matter_parties` on a fresh path is simply the Matter <-> Party join `ADR/0035` section 11 fixed;
  its ordinary business use follows the enabling of the entities it joins, not this ADR's
  boundary-specific decisions.
- A future task must be able to run the full T108-T120 flow on any database that contains
  legacy-shaped or business data. This ADR removes no capability, table, constraint, or ledger
  surface from the legacy path; it only defines when the migration window has no object.

## Reasoning

The core choice is between trusting a statement and verifying a state. Option 1 (never enable) keeps
the repository correct but makes ordinary Party creation literally impossible on a database with
nothing to migrate — an outcome the governing task exists to correct, on a product that will be
freshly installed. Option 2 (trust the operator) is the cheapest to state and the most dangerous to
grant, because the failure it enables — ordinary Party writes against uncategorized legacy-shaped
data — is the exact cross-contamination the T108-T120 boundary, and the entire `ADR/0033`/`ADR/0034`/
`ADR/0035` chain, exists to prevent, and because `ADR/0021` already documented this repository's
concrete precedent (`T79`'s ad hoc database-staged scripts) for why reliance on convention without
verification fails open. Option 3, adopted here, makes "fresh" a **property of the database that the
database can prove** (zero rows in every migration-relevant and business table, and no real customer
data ever) rather than a claim about its history. That property, not intent, is what makes
`ADR/0035`'s migration-window rule vacuous: a rule about reconciling data has no object when the
mechanical check proves there is no data to reconcile.

Equally decisive is that the fresh path grants **no** security or authorization waiver. Every
prerequisite this ADR restates — Address finalization, Party RLS, the non-owning runtime role,
application-layer scoping, Party permission codes — is one the legacy path already requires
(`ADR/0035` section 5/6, `ADR/0021`, `ADR/0022`). A fresh installation is not a simpler installation
for tenant-safety purposes; it is the same production database, merely empty. Keeping the
prerequisites identical is simultaneously the anti-weakening guarantee the task demands and the
reason the fresh path can coexist with the legacy process without contradiction: both paths share
one schema, one ledger, one RBAC surface, and one verification discipline, differing only in whether
the migration window has an object.

The failure-closed classification default (any ambiguity resolves to legacy) is deliberately
asymmetric. Treating a doubtful database as legacy only costs the operator a proper disposal/reset;
treating a legacy database as fresh costs the repository its migration boundary. The asymmetry is
the point, and it is consistent with `ADR/0021`'s and `ADR/0022`'s identical fail-closed stance on
tenant isolation and authorization.

## Trade-offs

- The fresh path requires a governed disposal/reset discipline for genuinely disposable
  development/test databases; without it, a database full of thrown-together test rows could never
  re-classify as fresh. This is operational surface, but the alternative (let disposable origin
  excuse the classification without removal) is precisely the loophole Decision 1 closes.
- The zero-row verification is broad by design (twelve named tables plus any other migration-relevant
  table). A narrow check (e.g., `clients` alone) would be cheaper but would leave classification
  vulnerable to a database whose legacy-shaped data lives elsewhere (a `matters` row with a
  `client_id`, a populated `addresses` table). The broad check is the cost of the broad guarantee.
- This ADR keeps ordinary Party creation blocked even on a fresh installation until every
  install-agnostic prerequisite is implemented (Address finalization, Party RLS + runtime-role
  effectiveness, app-layer scoping, permission codes). A fresh installation therefore does not gain
  ordinary Party writes as a side effect of being empty; it still must satisfy a real, later
  implementation slice. This is the intended meaning of "no waiver," accepted here over the
  alternative of a reduced, fresh-only prerequisite set.
- The fresh path resolves a slice of what Required ADR #20 would otherwise own, which could be read
  as creeping into the unresolved migration-strategy item. This ADR bounds that by construction:
  nothing about cutover, removal, retirement, or legacy completion is decided, and Decision 8 states
  the remaining boundary in full. The trade-off is accepted because T121's authorized scope demands
  precisely this slice and because the fresh case is definitionally separate from the legacy cases
  Required ADR #20 governs — they differ on an objective, mechanical predicate (zero rows versus
  retained data), not a judgment call that Required ADR #20 needs to arbitrate.

## Future Impact

### Required future dependency sequence (no task numbers assigned)

The following ordering is the minimal dependency scaffold a future task planner should assume,
each level gating the next:

1. **Install-agnostic prerequisites (both paths).** Address tenant finalization (`addresses`
   `NOT NULL`, same-Organization integrity, Address RLS); Party RLS (forced default-deny, effective
   under the non-owning runtime role) plus runtime-role effective verification and application-layer
   Organization scoping on Party read/write paths; Party permission codes seeded and granted, and
   Party-facing routes/use cases permission-gated. These are required before any ordinary Party
   write on either path.
2. **Fresh-installation enablement (fresh path only).** The mechanical zero-row classification and
   vacuity verification (Decision 1/2), wired as the gate-check that proves Decision 7's conditions;
   ordinary Party creation/application visibility enabled behind that gate. Cheap and safe only
   because level 1 is genuine.
3. **Legacy migration completion (legacy path only).** Staged-column final `NOT NULL` enforcement,
   remaining bridge finalization, and the reconciliation/backfill completion gate are governed by
   the existing T108-T120 chain and ADR-0033/0034/0035; this ADR changes none of it and Required
   ADR #20 still sequences the legacy finish.
4. **Cutover and retirement (Required ADR #20).** Application cutover, `matters.client_id` and
   downstream `client_id` removal, bridge removal, and `clients` retirement remain blocked by
   Required ADR #20 and are explicitly not sequenced by this ADR.

### Remaining Required ADR #20 boundary

Required ADR #20 remains unresolved globally after this ADR. Still outside the resolved slice:

- final cutover/removal choreography beyond the fresh/empty boundary;
- legacy staged-column final `NOT NULL` enforcement over reconciled data, and final `party_id`
  bridge nullability;
- `matters.client_id`, downstream `client_id`, and `clients` retirement;
- bridge removal and any removal of migration-era retention surfaces;
- the legacy-path completion gate and any legacy "migration complete enough" determination.

### What future work this constrains

- Any later task that implements ordinary Party creation must implement Decision 7's gate, not an
  operator-declared shortcut, and must keep the gate a property of the database, not a label.
- Any later task that touches Address finalization, Party RLS, or Party permission codes builds each
  prerequisite in the exact order Decision 5 fixes and must not skip one for a "fresh" deployment.
- Any later change to the Role/Permission catalog or the RLS/tenant layer remains governed by
  `ADR/0022` and `ADR/0021`; this ADR adds a consumer, not an override.