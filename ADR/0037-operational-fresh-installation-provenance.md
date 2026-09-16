# ADR-0037: Operational-Fresh Installation Provenance

**Status:** Proposed
**Date:** 2026-09-16

**Related task:** T125 — Fresh-Install Operational-State Continuation Architecture.

**Qualifies and extends:** ADR-0036 Decisions 1, 2, 3, and 7. ADR-0036 remains Proposed; this ADR
does not silently rewrite or accept it.

**Does not resolve:** Required ADR #20 (migration strategy), normal Party-write eligibility for
migrated installations, Client-master cutover, `matters.client_id` or `clients` retirement,
compatibility-bridge removal, final migration completion, legacy cleanup, Address CRUD, or
MatterParty role/cardinality.

## Problem

T124 implemented ADR-0036's initial fresh-install classification as a live zero-row predicate over
eleven governed business/migration tables. It excludes `parties`, correctly allowing Party rows
created through the new Party surface to remain writable. It includes `addresses`, however, so the
first legitimate Address makes that same genuinely fresh installation appear
`LEGACY_WITH_BUSINESS_DATA`, blocking later Party maintenance through the FRESH-only
`PartyWriteGate`.

Excluding Address next, then Matter, Property, File, and every later new-domain table would turn the
classifier into an ever-growing rollout list and progressively erase its ability to identify legacy
evidence. The underlying distinction is temporal: historical provenance is not the same property as
current contents. Current emptiness can prove bootstrap eligibility at one protected instant; it
cannot remain the definition of an operating installation, and it cannot prove whether an empty
database was born fresh or became empty by deleting legacy data.

The architecture must let a mechanically proven genuinely fresh database enter durable operation
and accumulate legitimate new-domain rows while ensuring legacy, migrated, reset, emptied, copied,
or operator-asserted databases cannot manufacture a new fresh lineage.

## Options Considered

### 1. Growing zero-row exclusions

Exclude every newly enabled domain table from the continuing predicate. This is locally simple but
weakens provenance with every feature, couples classification to rollout order, and cannot
distinguish birth from deletion. Rejected.

### 2. Mutable installation-state flag

Store `operational_fresh=true` or a mutable enum. It is simple to query but can be asserted,
updated, restored, or scripted without retaining proof of how it was reached. Rejected.

### 3. Schema revision plus current row counts

Require a supported Alembic revision and an empty database. These are necessary bootstrap
preconditions, but an upgraded and emptied legacy database can have the same revision and counts as
a new one. Rejected as durable provenance; retained as bootstrap validation.

### 4. Immutable singleton provenance record only

Create one immutable record saying the installation is fresh. This is stronger than a mutable flag,
but conflates birth identity with the later proof that all ADR-0036 prerequisites held at the
operational transition. It provides no transition history or clean retry/concurrency semantics.
Rejected as incomplete on its own.

### 5. Append-only event ledger without installer-established birth identity

Append an `OPERATIONAL_FRESH` event after checking current emptiness. This is auditable from that
point forward, but an old/emptied database could append the same first event because it lacks
pre-business-data evidence. Rejected.

### 6. Installer-established immutable birth identity plus append-only transition evidence

A dedicated new-install path creates a unique birth identity only while proving no prior Legal_DMS
schema, migration history, provenance, or business tables exist. A later serialized bootstrap
rechecks ADR-0036 prerequisites and appends exactly one operational-fresh transition. Normal runtime
may read the resulting state but cannot create, update, delete, or reset it. Selected.

### 7. Cryptographically signed evidence

A signature can detect some out-of-band edits and may be added later, but a signing key does not
prove birth if an operator can use it to sign a legacy database. Key custody and recovery also add
complexity. Rejected as the root of trust; optional defense-in-depth only.

### 8. External installation registry

An external registry can enforce globally unique active installation identities and detect clones,
but adds an unavailable service dependency. It is not required to prevent a legacy copy from
becoming fresh. Deferred as a possible future deployment-identity layer.

## Decision

### 1. Durable provenance mechanism

Adopt Option 6. Provenance is installation-wide, never Organization- or tenant-scoped. It consists
conceptually of:

1. one immutable installation-birth identity established before any Legal_DMS business write can
   exist; and
2. an append-only transition record proving that this birth lineage passed the protected
   operational bootstrap.

The minimum durable fields are:

- a random, stable `installation_id`;
- event/record identity and monotonic sequence;
- event kind, at minimum `FRESH_BIRTH` and `OPERATIONAL_FRESH_ENTERED`;
- database-generated timestamp;
- provenance-contract version;
- supported schema/Alembic revision observed at the event;
- the bootstrap predicate version for the operational event; and
- an optional previous-event digest/event digest for tamper evidence.

Exact table, column, routine, and digest choices belong to implementation. The enforceable
architecture does not: exactly one birth, at most one operational transition for that birth,
append-only events, immutable identity/sequence/kind/time/version/revision fields, no runtime DML,
and database-enforced uniqueness and transition validity.

### 2. Minimum state model

| State | Required evidence | Ordinary fresh-path writes |
|---|---|---:|
| `UNPROVEN` | No valid fresh birth/transition, or provenance not available at this contract version | Denied |
| `VERIFIED_FRESH_EMPTY` | Valid birth plus compatible schema and full ADR-0036 empty predicate proven inside bootstrap transaction | Denied; bootstrap only |
| `OPERATIONAL_FRESH` | Valid birth followed by one valid operational transition, compatible schema, no contradiction | Eligible, subject to all independent security gates |
| `LEGACY_WITH_BUSINESS_DATA` | Legacy/business evidence without valid operational-fresh lineage | Denied |
| `MIGRATED` | Valid T118 migration-ledger completion evidence | Denied pending Required ADR #20 |

Malformed, missing-after-expected, forked, unsupported, revision-incompatible, or contradictory
evidence is `INVALID`/`AMBIGUOUS` behavior, not another writable business state. It fails closed and
requires governed diagnosis.

`VERIFIED_FRESH_EMPTY` is a transient bootstrap observation. It must not be persisted or exposed as
a continuing runtime entitlement.

### 3. Transition matrix

| From | To | Allowed | Mechanical condition |
|---|---|---:|---|
| No Legal_DMS installation | Birth-established `UNPROVEN` | Yes | Dedicated installer proves absence of prior schema/history/evidence and records birth before business exposure |
| Birth-established `UNPROVEN` | `VERIFIED_FRESH_EMPTY` | Yes, transient | Locked transaction proves valid birth, compatible revision, full empty predicate, and no migration contradiction |
| `VERIFIED_FRESH_EMPTY` | `OPERATIONAL_FRESH` | Yes, once | Same transaction appends the unique operational transition and commits |
| `OPERATIONAL_FRESH` | `OPERATIONAL_FRESH` | Idempotent observation | Retry sees the existing valid transition and appends nothing |
| `UNPROVEN` | `LEGACY_WITH_BUSINESS_DATA` | Classification only | Legacy/business evidence exists or fresh lineage cannot be proven |
| Any non-invalid state | `MIGRATED` | Classification only | Governed migration ledger proves completion; Required ADR #20 still controls writes |
| `LEGACY_WITH_BUSINESS_DATA` | `OPERATIONAL_FRESH` | **No** | Deletion, reset, assertion, or current emptiness cannot create birth evidence |
| `MIGRATED` | `OPERATIONAL_FRESH` | **No** | Migration completion is not fresh birth and cannot bypass ADR #20 |
| Any | Invalid/ambiguous behavior | Yes on contradiction | Deny writes and require governed investigation |

Destroying a database and creating a genuinely new one creates a new installation identity; it is
not a legacy-to-fresh transition. ADR-0036's allowance for a controlled full reset to restore fresh
classification is superseded: reset/deletion is insufficient.

### 4. Birth contract

Only the dedicated installation path may create `FRESH_BIRTH`. Before doing so it must mechanically
prove that the target has no Legal_DMS schema objects, Alembic history, provenance structures, or
known business tables. Birth creation must be transactionally bound to initial schema installation,
or use an equivalently guarded database-owned routine, so a failed installation cannot leave valid
birth evidence attached to a pre-existing or partially created system.

An upgrade that first introduces provenance structures into an existing database must not create
birth evidence, even if the database is currently empty. No environment name, test mode, config
flag, operator declaration, or cleanup script may stand in for birth proof.

### 5. Operational bootstrap contract

Bootstrap is initiated by a dedicated deployment/install command using a narrowly privileged
bootstrap role. It is not a Party/Address API operation and the non-owning normal runtime role
`legal_dms_app` cannot invoke it.

One serializable transaction, or an equivalent transaction holding an installation-scoped advisory
lock, must:

1. acquire the unique bootstrap lock;
2. validate the complete provenance shape and unique fresh-birth identity;
3. verify the exact supported schema/Alembic revision and provenance-contract version;
4. verify no T118 migration ledger or other legacy/migrated contradiction exists;
5. evaluate ADR-0036's full bootstrap predicate, including `parties` and every governed
   business/migration table, in the protected transaction snapshot;
6. verify ADR-0036's Address finalization, Party/Address tenant security, non-owning runtime-role,
   and Party permission prerequisites;
7. append exactly one `OPERATIONAL_FRESH_ENTERED` event bound to the birth, revision, and predicate
   version; and
8. commit atomically.

Business writes are unavailable before the event. Locking/isolation must nevertheless prevent an
admin or concurrent process from committing relevant business data between the proof and event.
Concurrent business appearance causes serialization failure or failed revalidation and rolls back.

Two bootstrap attempts serialize. The first valid attempt commits one event; the second observes it
and succeeds idempotently without inserting another. A crash before commit leaves no operational
status. If the client loses confirmation after commit, retry observes the existing event. Partial,
duplicate, or conflicting evidence fails closed.

### 6. Classifier precedence

The future conceptual classifier evaluates in this order:

1. unreadable, malformed, forked, unsupported, schema-incompatible, or internally contradictory
   provenance => invalid/ambiguous, deny;
2. fresh provenance contradicting legacy/migration evidence => invalid/ambiguous, deny;
3. valid migration-complete T118 evidence => `MIGRATED`, deny ordinary Party writes pending ADR #20;
4. valid compatible birth plus operational transition => `OPERATIONAL_FRESH`;
5. valid birth without operational transition plus a full zero-row proof => transient
   `VERIFIED_FRESH_EMPTY`, visible only to bootstrap;
6. legacy/business evidence without valid operational-fresh provenance =>
   `LEGACY_WITH_BUSINESS_DATA`;
7. otherwise => `UNPROVEN`, deny.

Zero-row inspection therefore becomes bootstrap detection only. It is not continuing runtime
provenance. Once validly operational, legitimate new-domain rows do not revoke status merely by
existing.

### 7. PartyWriteGate

| Classifier result | Ordinary Party create/update/delete |
|---|---:|
| `OPERATIONAL_FRESH` | Eligible |
| `VERIFIED_FRESH_EMPTY` | Denied until bootstrap commits |
| `UNPROVEN` | Denied |
| `LEGACY_WITH_BUSINESS_DATA` | Denied |
| `MIGRATED` | Denied pending Required ADR #20 |
| Invalid, ambiguous, contradiction, or classifier error | Denied |

Eligibility is only the installation-provenance gate. Authentication, trusted Organization
resolution, ADR-0022 permission checks, application-layer Organization scoping, same-Organization
integrity, forced Party/Address RLS, and non-owning runtime execution remain separate mandatory
layers.

### 8. Address and future-domain composition

After operational bootstrap, a future Address application surface may create legitimate
Organization-owned Address rows without changing installation provenance. T122 remains fully
binding: mandatory Organization ownership, Party/Property/Client same-Organization integrity,
forced default-deny Address RLS, and non-owning runtime security. This ADR neither designs nor
authorizes Address CRUD.

The same provenance supports later Party -> Address -> Matter -> MatterParty -> Property/File and
other new-domain growth. New tables do not join a continuing zero-row exclusion list. Their own
domain, permission, tenant, RLS, and migration requirements remain independently governed.
MatterParty roles/cardinality and Client coexistence are not decided here.

### 9. Attack and failure analysis

| Case | Result | Reason |
|---|---|---|
| Legacy DB with Clients | Deny | No fresh birth/transition; legacy rows corroborate legacy state |
| Legacy DB after deleting Clients | Deny | Deletion cannot create missing pre-business birth evidence |
| Fully emptied legacy DB | Deny | Current emptiness is bootstrap evidence only when valid birth already exists |
| Partially migrated DB | Deny | Migration evidence selects legacy/ambiguous handling |
| Migrated DB with complete T118 evidence | Deny | `MIGRATED` is distinct and ADR #20 still blocks ordinary writes |
| Restored backup predating provenance | Deny | Missing birth/transition => unproven |
| Restored backup with valid evidence | Same-lineage recovery only; otherwise fail closed | Restore does not create new provenance; revision and contradiction checks still apply |
| Copy/clone of legacy DB | Deny | Copy contains no valid fresh lineage |
| Copy/clone of operational-fresh DB | Not a new fresh installation | It duplicates the same `installation_id`; separate active use requires a later governed clone/restore activation policy or registry, not a new birth event |
| Manually fabricated row/event by runtime | Deny | Runtime lacks DML; uniqueness/transition/shape checks reject invalid evidence |
| Privileged-owner fabrication | Security incident; fail closed where detectable | DB owner/superuser is inside the administrative trust boundary; direct tampering is never legitimate bootstrap |
| Two concurrent bootstraps | One event, one idempotent observer | Lock plus uniqueness serializes attempts |
| Interrupted bootstrap | Deny until retry unless transaction committed | Proof and event are atomic |
| Missing evidence | Deny | Unproven |
| Malformed/forked evidence | Deny | Invalid/ambiguous precedence |
| Fresh evidence contradicting migration state | Deny | Contradiction outranks claimed freshness |
| Incompatible revision | Deny | Provenance contract is revision/version bound |
| Existing T124-era development/test DB | Deny unless recreated as a genuinely new installation | Labels, current contents, and historical assumptions cannot reconstruct birth |

A byte-for-byte copy of valid operational evidence preserves the source lineage; it does not
manufacture freshness for legacy data and must not be treated as a distinct installation. Robust
simultaneous-clone detection requires an external registry or activation lease and is explicitly
deferred rather than falsely claimed by database-local evidence.

### 10. Security and trust boundary

- `legal_dms_app` may read only the minimum classification projection; it cannot insert, update,
  delete, truncate, or invoke birth/bootstrap mutation routines.
- The installer alone creates birth evidence after proving schema absence.
- A narrowly privileged bootstrap role can append the operational transition only through the
  guarded routine; it receives no general evidence-table DML.
- Migration/admin execution remains separately named, credentialed, and audited. The T118 executor
  does not invoke fresh bootstrap.
- Database ownership, privileges, constraints, immutable/append-only enforcement, and guarded
  routines are required. Application code alone is insufficient.
- Installation provenance is not Organization-owned. Tenant RLS is therefore not its primary
  control; using RLS as an extra backstop cannot replace table privileges and ownership.
- A database owner/superuser can physically tamper with its database. That actor is an explicit
  administrative trust boundary; tampering is not a supported transition and requires separately
  governed recovery.

### 11. Upgrade and deployment behavior

- Future new installations use the dedicated installer, receive birth evidence before business
  exposure, reach the supported revision, and run bootstrap before normal writes.
- Existing development/test databases are not classified by labels. Disposable ones may be
  destroyed and recreated; retained ones without provenance fail closed.
- Existing legacy and migrated databases may receive provenance schema structures on upgrade but
  receive no fresh birth/transition.
- T124-era Party-only and Party+Address databases are not automatically grandfathered. Safe
  reconstruction, if ever required, needs separately authorized architecture and evidence.
- Schema upgrade without provenance never manufactures it.
- The T124 shared-development-DB deviation is historical process debt, not provenance. T125 does
  not inspect, reset, mutate, classify, or repair that database.
- Backups restore the recorded lineage. A backup lacking evidence is unproven; a valid same-lineage
  restore must still pass revision and contradiction checks.

### 12. Required ADR #20 boundary

A legacy/upgraded database cannot obtain fresh birth through the normal upgrade/bootstrap path, and
valid T118 migration evidence has higher fail-closed precedence than operational-fresh eligibility.
Therefore T125 cannot be used to enable normal migrated Party writes, declare final migration
completion, cut over Client-master behavior, retire `matters.client_id`/`clients`, remove
compatibility bridges, or perform broader legacy cleanup. Only Required ADR #20 may decide those
outcomes.

### 13. Relationship to existing ADRs

- **ADR-0021:** unchanged; tenant context/application scoping and forced RLS remain independent.
- **ADR-0022:** unchanged; permissions remain independently mandatory.
- **ADR-0023:** unchanged; Party/Client meanings are not reopened.
- **ADR-0033:** unchanged; legacy Organization reconciliation remains authoritative.
- **ADR-0034:** unchanged; its migration ledger remains migration evidence and is not reused as
  fresh-install provenance.
- **ADR-0035:** unchanged on legacy coexistence, Party/Address schema integrity, and migration-only
  writes.
- **ADR-0036:** Decision 1's full zero-row test remains the bootstrap predicate, not continuing
  provenance; Decision 2 is limited to bootstrap; Decision 3 is qualified so legitimate new-domain
  rows do not switch a proven operational installation to legacy; Decision 7 uses valid
  operational-fresh provenance as its continuing installation condition. The full-reset path to
  fresh is superseded. All tenant, permission, RLS, Address, Party, migration, and ADR #20
  boundaries remain.

## Reasoning

Only evidence established before business data could exist can distinguish a genuinely new lineage
from a legacy database made empty later. A guarded birth identity supplies that historical fact;
the serialized empty bootstrap proves all ADR-0036 conditions at the transition instant; the
append-only operational event makes the result durable and auditable. This removes domain tables
from continuing provenance without weakening legacy detection.

The selected mechanism is smaller than an external registry or mandatory cryptography, but stronger
than a flag, singleton marker, or ledger created from present contents alone. It also makes honest
boundaries explicit: database-local evidence prevents runtime/operator-assertion bypass but cannot
detect every simultaneous physical clone without external coordination.

## Trade-offs

- New deployments require a dedicated installer/bootstrap path and database privilege design.
- Existing T124-era databases cannot be automatically grandfathered.
- Revision-bound evidence requires explicit compatibility handling during future upgrades.
- A physical operational-fresh clone carries the same identity; distinct activation requires later
  external or governed coordination.
- Reset-to-fresh convenience is deliberately removed; recreation is the automatic fresh path.

## Future Impact

Future implementation naturally decomposes, without authorization, into:

1. provenance schema, privilege model, guarded installer/birth path, bootstrap routine, and
   concurrency/crash/integrity validation;
2. classifier state/precedence and PartyWriteGate integration, without enabling migrated writes;
3. a separately authorized Address application surface preserving T122 security; and
4. later Matter/MatterParty and other domain composition, with separate domain/security decisions
   and Required ADR #20 still governing legacy cutover aspects.

Any clone activation/rekey registry, privileged recovery/reconstruction policy, or cryptographic
attestation is separate future architecture. This ADR authorizes none of these slices.
