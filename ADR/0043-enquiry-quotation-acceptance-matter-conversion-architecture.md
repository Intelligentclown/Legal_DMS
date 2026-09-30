# ADR-0043: Enquiry, Quotation, Acceptance, and Matter Conversion Architecture

**Status:** Proposed  
**Date:** 2026-09-30  
**Related task:** T147 — Enquiry & Quotation Pre-Engagement and Matter Conversion Architecture.

**Resolves:** None.

**Does not resolve:** Required ADR #12 (Workflow vs Government Status), #15 (Core vs configurable vocabulary), #16 (UUID vs human-readable identifiers), #17 (Soft deletion/history), or #20 (Migration strategy from the current schema). It does not authorize implementation, schema/migration/seed work, Commercial Scope/Charge/Invoice/Payment implementation, Client retirement, Workflow/Government Process, Property/Scheme expansion, or T148+.

**Composes with:** ADR-0020 session commit/rollback policy; ADR-0021 Organization tenant isolation; ADR-0022 authorization; ADR-0023 Party vs Client; ADR-0028 financial boundary; ADR-0029 Activity vs Audit; ADR-0030 Matter/File lifecycle; ADR-0031 trusted User→Organization context; ADR-0037 operational-fresh provenance; ADR-0039 Party-canonical Matter cutover; and the current T134/T145 Party-canonical Matter application surface.

## Problem

The governed business baseline fixes the pre-engagement chain:

`Party → Enquiry → Quotation → Acceptance → Matter`.

The repository now has an operational authenticated downstream slice from Party through Matter, File, Document and DocumentVersion, but it has no Enquiry or Quotation persistence/application surface. New Matters are already Party-canonical: T134 creates `Matter(client_id=None)` and a `MatterParty(role="client")`; it does not manufacture a legacy Client. Matter creation also requires no File.

The specification intentionally leaves several engineering questions open: whether intake may precede Party creation, how Quotation revisions retain evidence, what exact event constitutes acceptance, how duplicate conversion is prevented, and how accepted commercial evidence relates to later Commercial Scope. Without a bounded architecture, implementation would have to answer those questions while coding and could silently cross Required ADR #15/#16/#17/#20.

## Decision drivers

1. Preserve the frozen distinction between Enquiry, Quotation, Acceptance and Matter.
2. Preserve Party as reusable canonical identity and Client only as a Matter relationship.
3. Permit real prospective intake before a reusable Party record is ready without creating a second identity master.
4. Make the exact commercial proposal relied upon for acceptance durable and historically stable.
5. Make conversion atomic, idempotent and concurrency-safe, producing one Matter and no synthetic File.
6. Reuse ADR-0020 transaction ownership and ADR-0021/0022 tenancy/security rather than redesigning them.
7. Keep lifecycle vocabulary policy, business-readable numbering, destructive retention and legacy retirement outside T147.
8. Keep Quotation distinct from Commercial Scope, Charges, Invoice and Payment.

## Options considered

### Intake requires Party before Enquiry

Rejected as the sole path. The specification explicitly leaves room for a not-yet-a-Party prospective contact. Forcing Party creation at first contact would turn incomplete intake into durable reusable identity and make Party cleanup/retention semantics a prerequisite.

### Separate Lead master before Enquiry

Rejected. No governed domain concept requires Lead, and T147 explicitly forbids inventing it.

### Enquiry owns prospective-contact evidence and may later link Party — selected

An Enquiry may begin without `party_id`, carrying bounded tenant-owned contact evidence sufficient to identify and contact the prospect. Linking a canonical Party is a later explicit operation. Acceptance requires Party resolution; conversion itself does not create or infer Party.

### One mutable Quotation row

Rejected. Editing the same row after it was sent or relied upon would destroy the exact proposal evidence and conflict with the specification's historical-integrity posture.

### Independent Quotation rows for every revision

Viable, but rejected as the canonical model because it loses explicit proposal/revision identity and makes it harder to distinguish “another proposal for this Enquiry” from “a revision of the same proposal.”

### Quotation aggregate plus immutable QuotationRevision rows — selected

One Enquiry may have multiple Quotation aggregates. Each Quotation has one or more immutable revisions. Acceptance targets one exact revision.

### Acceptance represented only by a status value

Rejected. A mutable status cannot by itself provide durable conversion provenance, idempotency, actor/time evidence and a one-to-one resulting Matter link.

### Explicit Acceptance conversion record — selected

Acceptance is a durable event/record linking Enquiry, exact QuotationRevision and resulting Matter, with actor/time and idempotency provenance.

## Decision

### 1. Enquiry identity and lifecycle boundary

Enquiry is the tenant-owned prospective-engagement aggregate.

Its internal technical identity is a server-generated UUID. T147 defines no human/business-readable Enquiry number; Required ADR #16 remains open.

Future persistence requires direct mandatory `organization_id`. Organization is derived from authenticated trusted tenant context, never accepted as caller-selected authority.

An Enquiry may be created in either of two identity states:

- **Party-linked:** `party_id` references an existing Party in the same Organization.
- **Prospect-only:** `party_id` is null and the Enquiry stores a bounded prospective-contact snapshot.

The prospective-contact snapshot is intake evidence, not a reusable identity master. Its minimum purpose is to preserve the name/display label and contact channel(s) supplied for the prospective engagement. Exact optional contact fields beyond the repository's already-understood name/phone/email-shaped contact data are implementation-contract details, not new domain concepts.

A prospect-only Enquiry may later be explicitly linked to an existing or newly created Party through the ordinary Party capability. Linking must validate same-Organization ownership. T147 does not authorize automatic duplicate matching, fuzzy identity inference, Client creation, or Party manufacture inside conversion.

**Acceptance precondition:** the Enquiry must have a canonical same-Organization `party_id`. If it does not, conversion fails closed. The caller must first create/select/link Party through the canonical Party surface.

The Enquiry may carry prospective-work description and source/channel data as intake facts. T147 does not define a global status vocabulary. Structural lifecycle facts are sufficient for architecture: pre-quotation, quoted, converted, and closed/non-converted are lifecycle roles; whether labels are global/core/configurable is Required ADR #15 and remains undecided.

T147 defines no destructive delete, purge, archive duration or legal-hold policy. Non-converted Enquiries remain preservable records until Required ADR #17 governs destructive/history policy.

### 2. Enquiry → Quotation cardinality

One Enquiry may own zero or more Quotation aggregates. Every Quotation belongs to exactly one Enquiry and the same Organization.

A Quotation represents one commercial-proposal thread for that Enquiry. It has a server-generated UUID technical identity only; no project-wide business-readable quotation number is decided.

A Quotation may have one or more QuotationRevision rows. Revisions are ordered within one Quotation by an internal positive integer ordinal. That ordinal is technical history, not a business-readable identifier under Required ADR #16.

### 3. QuotationRevision as historical commercial evidence

QuotationRevision is immutable after it becomes an issued/reliance-capable revision.

Each revision preserves the exact proposal facts relied upon at that point, including the proposal scope representation, proposed fee representation, validity information when supplied, creation/issue actor and timestamps, and its parent Quotation.

T147 deliberately does **not** define the future financial ledger or require structured Charge rows. Quotation proposal data may be represented in the future implementation by a bounded proposal snapshot suitable for preserving what was offered. It must not be implemented as Invoice, Payment or Charge.

A later revision never overwrites an earlier issued revision. It coexists with and supersedes it for forward proposal use while prior evidence remains readable.

The architecture recognizes structural quotation roles such as draft, issued, superseded, accepted, rejected/declined and expired only to express invariants. T147 does not decide whether those labels are columns, derived state, lookup rows, global values or Organization-configurable vocabulary. That policy remains Required ADR #15.

Only one exact QuotationRevision is the subject of an Acceptance.

### 4. Acceptance

Acceptance is an explicit durable conversion event, not merely a mutable status flag.

Future persistence requires a tenant-owned Acceptance record with server-generated UUID technical identity and, at minimum, immutable references/provenance for:

- `organization_id`;
- `enquiry_id`;
- `quotation_id`;
- exact `quotation_revision_id`;
- resulting `matter_id`;
- accepting/recording actor;
- acceptance timestamp;
- a scoped idempotency key or equivalent durable request identity sufficient to make replay deterministic.

The Acceptance record is immutable evidence after commit. Correction of a mistaken acceptance is not defined by T147; destructive reversal/retention policy remains outside scope.

A QuotationRevision is eligible for acceptance only when it belongs to the supplied Quotation, that Quotation belongs to the Enquiry, all rows belong to the authenticated Organization, the revision is an issued/reliance-capable non-superseded proposal under the future concrete state representation, and the Enquiry has a canonical Party.

### 5. Exactly-one conversion outcome

One Enquiry may convert to **at most one Matter** through this architecture.

This is the duplicate-prevention boundary implied by one prospective engagement becoming the accepted engagement. Multiple quotation attempts/revisions may precede conversion, but concurrent or repeated acceptance cannot create multiple Matters for the same Enquiry.

Future database integrity must make that invariant mechanical, using a uniqueness boundary equivalent to one committed Acceptance per Enquiry and one Acceptance per resulting Matter. The exact accepted QuotationRevision must also be uniquely tied to that committed Acceptance.

A successfully converted Enquiry remains historical evidence; it is not deleted or transformed into the Matter.

### 6. Matter conversion

Conversion is one application operation executed inside the existing request-scoped database transaction owned by ADR-0020.

The authoritative sequence is:

1. authenticate and derive trusted Organization;
2. require acceptance/conversion authorization;
3. load the Enquiry inside the Organization;
4. validate its canonical Party;
5. load Quotation and exact QuotationRevision through the Enquiry hierarchy;
6. validate the revision is eligible for acceptance;
7. acquire a PostgreSQL row lock on the Enquiry (or an equivalently strong single-row serialization point);
8. re-check whether a committed Acceptance already exists;
9. if the same idempotency identity already committed, return the existing resulting Matter/Acceptance;
10. if a different acceptance already committed, fail with a deterministic conflict and never create another Matter;
11. create the Matter using the repository's existing Party-canonical semantics: `Matter.client_id = NULL` and `MatterParty(role="client", party_id=enquiry.party_id)`;
12. create the immutable Acceptance linking the exact revision and Matter;
13. flush constraints;
14. allow ADR-0020's request transaction owner to perform the single final commit.

The Matter's required existing creation inputs — including its existing Matter number, Matter Type, Matter Status, title/description/opened-at fields as applicable — remain governed by the current Matter contract. Conversion does not invent defaults for those fields and does not decide Required ADR #15/#16. The future conversion request must provide or derive them only from separately authoritative existing rules.

Conversion creates **no File**. Matter existence remains independent from File existence under ADR-0030.

Conversion creates no legacy Client and does not write `Matter.client_id`.

### 7. Idempotency and concurrency

Acceptance/conversion is retry-sensitive because a client can lose the response after commit.

The future operation therefore requires durable idempotency scoped at least to `(organization_id, enquiry_id, idempotency_key)`, with a request fingerprint sufficient to reject reuse of the same key for a different QuotationRevision or materially different Matter-creation payload.

Replay rules:

- same key + same fingerprint + committed conversion → return the existing Acceptance/Matter;
- same key + different fingerprint → conflict;
- new key after the Enquiry already converted → return deterministic already-converted conflict (or the existing result only where the API contract explicitly defines that safe readback);
- concurrent different acceptance requests serialize on the Enquiry and at most one commits.

Database uniqueness is the final integrity backstop. Application pre-checks are not sufficient by themselves.

There is no external side effect in the bounded conversion operation, so ADR-0042 compensation machinery is not required for normal T147 conversion. ADR-0020's ordinary single database transaction is sufficient.

### 8. Matter provenance

The immutable Acceptance record is the canonical provenance edge from the resulting Matter back to its Enquiry and accepted QuotationRevision.

The Matter itself need not gain mutable “source enquiry” or “accepted quotation” columns if the Acceptance relationship can enforce and query the provenance unambiguously. Future implementation may expose provenance through read models/API joins without duplicating authority.

Historical quotation facts are never recomputed from later Matter fields.

### 9. Commercial-history boundary

Quotation evidence answers **what was proposed and accepted**.

Commercial Scope answers **the accepted commercial baseline governing the Matter after acceptance**. Charges answer amounts owed/incurred; Invoice is billing; Payment is money received. ADR-0028 and specification rule 35 keep these concepts separate.

T147 conversion creates Matter-domain state plus Acceptance provenance only. It does **not** create Charge, Invoice, Payment or other ledger state.

T147 also does not require creation of CommercialScope because no authorized current application surface exists for it and doing so would widen this architecture into implementation of the financial domain. The accepted QuotationRevision remains durable source evidence from which a future separately authorized Commercial Scope operation may establish its own canonical baseline without mutating the quotation.

Later Matter/commercial changes cannot rewrite the accepted QuotationRevision.

### 10. Security, tenancy and hierarchy

Enquiry, Quotation, QuotationRevision and Acceptance are tenant-scoped entities.

Future persistence requires:

- direct mandatory `organization_id` on each;
- composite same-Organization foreign keys/candidate keys for Enquiry→Party, Quotation→Enquiry, QuotationRevision→Quotation, Acceptance→Enquiry/Quotation/Revision/Matter;
- ADR-0021 ENABLE + FORCE RLS/default deny on every new tenant table;
- trusted Organization GUC established by existing request infrastructure;
- non-owning, non-superuser, NOBYPASSRLS runtime role;
- no caller-controlled tenant identity.

Application hierarchy validation is mandatory even with RLS. A child identifier from another Enquiry/Quotation or Organization is treated as not found/non-enumerating rather than leaking existence.

RBAC is a separate application boundary from RLS. Future implementation should use narrow pre-engagement permissions rather than treating `matters:write` as blanket authority over prospective commercial records. At minimum, Enquiry read/write and Quotation read/write/accept capabilities must be distinguishable enough that accepting a quotation also requires authority to create the resulting Matter. Exact permission-code packaging and seed migration belong to implementation; T147 does not alter current grants.

Acceptance requires both authority over the quotation acceptance operation and the existing Matter-write capability because it mutates pre-engagement state and creates a Matter.

### 11. Audit and activity

Creation/modification of Enquiry, Party-link changes, quotation issue/revision events, acceptance and Matter conversion are audit-significant under ADR-0029's existing creation/modification/status/relationship categories.

Future implementation must preserve actor and timestamp provenance. Activity/timeline projection may later describe these events, but Activity is not a substitute for Audit.

### 12. Property and Scheme boundary

T147 adds no canonical Enquiry→Property, Quotation→Property or Enquiry/Quotation→Scheme relationship.

The governed dependency for Enquiry is Party, and current MatterProperty/Scheme work is not complete. Pulling those domains into T147 would create an unauthorized architecture dependency.

A prospective-work description may mention property in ordinary descriptive content, but that text is not a canonical Property relationship. A future separately authorized task may add explicit Property/Scheme linkage once its domain boundary is ready.

### 13. Required ADR boundary analysis

**#12 — Workflow vs Government Status:** not crossed. T147's lifecycle roles are local structural facts for Enquiry/Quotation/Acceptance, not a generalized Workflow or Government Status model.

**#15 — Core vs configurable vocabulary:** not crossed. T147 names only the state roles needed to state invariants. It does not decide whether status labels are enums, lookup rows, global/core values or Organization-configurable values.

**#16 — UUID vs human-readable identifiers:** not crossed. UUIDs and revision ordinals are technical identities only. No Enquiry/Quotation business-number format or project-wide numbering policy is selected.

**#17 — Soft deletion/history:** not crossed. T147 requires preservation of issued quotation revisions and committed acceptance provenance and defines no ordinary destructive delete. It does not decide archive duration, purge, legal hold, soft-delete mechanism or organization-wide retention.

**#20 — Migration strategy:** not crossed. Enquiry/Quotation/Acceptance are new canonical entities. T147 does not retire Client, `matters.client_id`, `matters.property_id`, `matter_type_id`, legacy Documents or any compatibility bridge.

None of #12/#15/#16/#17/#20 is a prerequisite blocker for this bounded architecture.

## Future persistence shape

A later separately authorized implementation will likely require new tenant-scoped tables equivalent to:

- `enquiries`;
- `quotations`;
- `quotation_revisions`;
- `acceptances` (name may vary if repository naming conventions prefer a more explicit conversion name).

That implementation will require an Alembic migration, RLS policies, same-Organization integrity constraints, repositories/services/routes, RBAC seed/grants, audit instrumentation and tests. T147 itself is migration-free and leaves the current Alembic/operational-fresh frontier at `cdcfd7df5fde`.

## Invariants for implementation/QA

1. Enquiry is distinct from Party and Matter.
2. Prospect-only intake is not a second reusable identity master.
3. Acceptance requires a canonical same-Organization Party.
4. Quotation is distinct from Invoice/Payment/Charge.
5. One Enquiry may have multiple Quotations; one Quotation may have multiple immutable revisions.
6. Issued/reliance-capable revisions are not silently overwritten.
7. Acceptance targets one exact QuotationRevision.
8. One Enquiry converts to at most one Matter.
9. Conversion replay cannot create a duplicate Matter.
10. Concurrent acceptance cannot create duplicate Matters.
11. New Matter uses Party-canonical `MatterParty(role="client")` and `client_id=NULL`.
12. Conversion creates no synthetic/default File.
13. Accepted quotation evidence remains historical after later Matter changes.
14. Conversion creates no Charge/Invoice/Payment and no implicit financial ledger.
15. Every new table is Organization-scoped and FORCE-RLS/default-deny.
16. Cross-Organization/hierarchy mismatches are non-enumerating.
17. Business-readable Enquiry/Quotation numbering remains undecided.
18. Destructive retention/deletion remains undecided.
19. Legacy retirement/migration remains outside scope.
20. Alembic/provenance remains `cdcfd7df5fde` during T147 architecture.

## Consequences

The architecture closes the missing conceptual bridge between prospective intake and the already-operational Party-canonical Matter domain without reopening the downstream legal-work spine.

A future implementation has a clear decomposition: tenant-safe Enquiry persistence and Party linking; immutable Quotation/revision persistence; then atomic Acceptance→Matter conversion. It will require schema/RLS/RBAC work and therefore must be separately authorized after T147 completes its §3.1 lifecycle.

The cost is additional explicit history/provenance rows rather than one mutable “lead/quotation status” record. That cost is intentional: it makes acceptance evidence, retry behavior and duplicate prevention mechanically testable while preserving the repository's historical-integrity principles.

## Explicit exclusions

No production/frontend/backend implementation; no implementation tests; no schema/migration/seed; no database mutation; no Commercial Scope/Charge/Invoice/Payment implementation; no Work Type/Classification/configurable-vocabulary decision; no Workflow/Tasks/Government Process; no Scheme/Gujarat-property expansion; no Client retirement; no legacy Document→File migration; no deletion/retention implementation; no Self-Context Layer B/C; no Project Delivery Roadmap; no Required ADR resolution; no T148+ authorization.
