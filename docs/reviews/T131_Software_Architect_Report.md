# T131 Software Architect Report — Legacy Client-to-Party Cutover and Domain-Relationship Migration Architecture

**Task:** T131  
**Role:** Software Architect  
**Authorization baseline:** `0933dc765693a62499be78d68256e8ea70988f71`  
**Architecture ADR:** `ADR/0039-legacy-client-party-cutover-domain-relationship-migration.md`  
**QA Decision:** _Pending independent QA_

## 1. Baseline and authorization verification

Fresh GitHub verification established that `origin/main` is `0933dc765693a62499be78d68256e8ea70988f71`, the merge of authorization PR #232. PR #232 is merged; its final head is `9e9f05e53e59361ba4d063e1ddea8a2e96b27160`, its base is T130 merge `bc6b902bfe7522e737cfe9403b457d3c4713c45d`, and GitHub records `merged_at = 2026-09-22T08:04:42Z`.

The authorization merge changes only `IMPLEMENTATION_QUEUE.md` and `PROJECT_STATE.json`. Governance records T130 Done, T131 Authorized/not Done, latest Done T130, latest Authorized T131 and no in-progress transition. Fresh searches found no T132 PR/branch reservation.

## 2. Authority inspected

The architecture was derived from repository evidence, including:
- `AGENTS.md`, `AI_BOOTSTRAP.md`, `docs/AI_EXECUTION_ROUTING.md`, `PROJECT_WORKFLOW.md`;
- `PROJECT_STATE.json`, T131's `IMPLEMENTATION_QUEUE.md` authorization row;
- `docs/Legal_DMS — Domain Model & Functional Specification.md`, especially §21 Required ADR #20 and Matter/Party/Property sections;
- ADR-0021/0022/0023/0024/0028/0030 and ADR-0033 through ADR-0038;
- `docs/PartyClientReconciliationContract.md`;
- current Client, Party, Matter, Property, Scheduling, Finance and Document ORM models;
- T116/T117 compatibility migrations, Party/Address RLS migrations, T130 supported-revision migration;
- T108–T118 preflight/reconciliation/staleness/executor path;
- PartyWriteGate and SQLAlchemy installation classifier.

Required ADR #20 is verified as the planning-list item **“Migration strategy from the current schema.”**

## 3. Current Client dependency inventory

| Dependency | Current role | T131 classification |
|---|---|---|
| `clients` | real legacy master/source | transitional compatibility + migration source |
| Client→Party UUID mapping | T118 identity-preserving migration | canonical migration mapping |
| `client_party_migration_ledger.legacy_client_id` | immutable completion evidence | runtime/migration safety infrastructure |
| `Matter.client_id` mandatory | legacy one-client Matter | transitional; target is MatterParty client role |
| `MatterParty` | bounded target join already present | canonical target architecture |
| `PropertyOwner.client_id` mandatory | legacy owner identity | transitional |
| `PropertyOwner.party_id` nullable | compatibility bridge | target ownership identity |
| `ClientContact.client_id` mandatory | legacy contact anchor | transitional; later contact/Representative decision required |
| `ClientContact.party_id` nullable | compatibility bridge | migration linkage, not full contact redesign |
| `Appointment.client_id` nullable | legacy scheduling link | transitional |
| `Appointment.party_id` nullable | compatibility bridge | later scheduling target |
| `Invoice.client_id` mandatory | legacy finance identity | transitional |
| `Invoice.party_id` nullable | compatibility bridge | later finance target |
| `Payment.client_id` mandatory | legacy finance identity | transitional |
| `Payment.party_id` nullable | compatibility bridge | later finance target |
| Address links | shared concrete address | canonical retained aggregate; tenant-finalized |
| `organization_id` on legacy downstream tables | nullable staging | transitional tenant foundation |
| PartyWriteGate | ordinary Party-write eligibility | runtime safety; unchanged |
| operational-fresh provenance/classifier | installation identity/state | runtime safety; unchanged |

No direct Client FK was found in Document. Documents depend transitively through Matter. Task/MatterTag likewise do not create a direct Client identity seam.

## 4. Problem statement

The project already knows what the final identity model is and already knows how to migrate one Client anchor into Party plus compatibility bridges. The remaining problem is the **canonical switch**: how new/future domain behavior stops requiring Client while legacy data remains safely migratable and verifiable.

The key architecture risk is accidentally creating two masters. The second risk is destructive retirement before every consumer and tenant/RLS boundary is ready.

## 5. Options and selected architecture

Three options were evaluated:

1. immediate destructive cutover — rejected because it combines too many irreversible/security-sensitive changes;
2. indefinite dual-master/dual-write — rejected because it contradicts Party-as-master and creates divergence;
3. staged canonical switch with compatibility shadows — selected.

The selected model has one canonical write representation per concept. Client is never a co-equal master after Party migration. Legacy columns may coexist temporarily as frozen verification/read shadows.

## 6. Installation-state contract

**OPERATIONAL_FRESH:** Party is canonical immediately. No new Client rows are manufactured for new business. Matter/ownership application surfaces remain unavailable until their schema can represent Party relationships without Client.

**LEGACY_WITH_BUSINESS_DATA / UNPROVEN:** no automatic promotion. Existing governed migration tools are required; ambiguous evidence fails closed.

**MIGRATED:** means all Client anchors are ledger-covered under classifier rules. It does not automatically mean all downstream application consumers have cut over and does not automatically enable PartyWriteGate.

**Partial/stale/contradictory:** fail closed.

**Compatibility:** canonical target writes only; legacy shadows may be read for verification until retirement. No normal dual-write back to Client.

## 7. Client→Party mapping contract

The T118 contract remains authoritative for migration execution:
- one Client → one Party;
- UUID preserved;
- one resolved Organization;
- deterministic or operator-reconciled only;
- immutable ledger completion;
- exact-basis rerun is no-op;
- stale/collision/Party-without-ledger/cross-tenant conditions fail closed.

The Client row survives migration as source/compatibility evidence until downstream retirement gates pass.

## 8. Matter transition

MatterParty becomes canonical client participation. A future schema foundation must first finalize Matter tenancy and permit a Matter to exist without mandatory Client. Migrated legacy Matters require a ledger-backed Party and matching same-Organization MatterParty(`role='client'`).

Multiple client-role Parties are valid; role cannot be globally unique per Matter. `Matter.client_id` becomes a compatibility shadow and retires only after all consumers use MatterParty.

MatterProperty, MatterClassification and MatterWorkType are not implemented or fully designed here.

## 9. PropertyOwner transition

Ownership target is Party. Property and PropertyOwner must first receive finalized mandatory Organization ownership, same-Organization constraints and RLS. Operational-fresh ownership then uses Party directly. Legacy ownership is backfilled only from ledger-backed mappings.

`PropertyOwner.client_id` is a compatibility shadow after cutover and eventually retires. Revenue/City Survey/TP-FP remains outside T131.

## 10. ClientContact and other dependencies

ClientContact cannot be silently dropped because no governed Representative/contact replacement yet owns all of its information. It remains transitional; its Party bridge prevents Client retirement from being hidden.

Appointments, Invoices and Payments also carry Client dependencies. T131 records their cutover boundary but deliberately does not redesign Scheduling or Finance.

## 11. PartyWriteGate

No runtime change is made. Current behavior remains OPERATIONAL_FRESH-only for ordinary Party writes.

A future migrated-write task must prove governed migration completion plus whatever application-cutover invariants are necessary. MIGRATED alone is explicitly insufficient.

## 12. Tenant/RLS/security contract

Before normal target-domain writes, each tenant-scoped aggregate must have:
- reconciled direct Organization ownership;
- NOT NULL ownership;
- same-Organization composite constraints;
- application Organization scoping;
- permissions;
- forced default-deny RLS;
- non-owning/non-superuser/NOBYPASSRLS runtime posture.

Migration executor/admin paths remain separate. Compatibility never weakens tenant isolation.

## 13. Migration/provenance and rollback

ADR-0037 remains sufficient. Later post-`5d8a3f2e9c6b` migrations use T130's explicit supported-revision advancement pattern.

Additive bridge/tenant/canonical-read steps can be rollback-capable only while authoritative ledger evidence is preserved. Destructive legacy-column/table retirement is the irreversible boundary and must be separately authorized with recovery evidence. A downgrade must never synthesize Client identity from Party.

## 14. Required scenario proofs

All 24 required scenarios are specified in ADR-0039. Key outcomes are:
- clean installs create no fake Client;
- Party/Address growth preserves operational-fresh;
- future Matter/ownership are Party-based;
- legacy deterministic/operator migration remains T108–T118 governed;
- partial/stale/conflicting states fail closed;
- Matter and PropertyOwner retain shadows until canonical target rows exist;
- multi-party Matter semantics remain valid;
- cross-tenant mappings fail;
- compatibility writes are single-write to the canonical target;
- exact migration reruns are idempotent;
- later migration heads explicitly advance provenance support;
- rollback is bounded before destructive retirement and forward-repair/restore after it;
- dev/test Client rows are not treated as proof of real production migration needs.

## 15. Required ADR #20 analysis

T131 **cannot honestly mark Required ADR #20 fully resolved**.

ADR-0033 and the canonical specification explicitly assign broader current-schema migration concerns to #20. T131's authorization excludes File/Document architecture and does not authorize Matter `property_id`/`matter_type_id` retirement. Document/File migration also intersects unresolved Required ADR #10.

ADR-0039 therefore **advances but does not resolve** #20 and deliberately contains no `Resolves: Required ADR #20` metadata. Governance closeout must leave unresolved Required ADRs unchanged.

## 16. New ADR decision

A new ADR was required because ADR-0033–0035 define migration mechanics/foundations but intentionally leave final cutover/removal choreography unresolved. Fresh namespace inspection showed ADR-0038 as the highest existing ADR, so the next valid number is **ADR-0039**.

Created:
`ADR/0039-legacy-client-party-cutover-domain-relationship-migration.md`

Status: **Proposed**.

ADR-0036, ADR-0037 and ADR-0038 remain Proposed and unchanged.

## 17. Successor decomposition

Unnumbered and unauthorized:
1. Matter/Property tenant-and-canonical-relationship schema foundation.
2. MatterParty / PropertyOwner application canonicalization.
3. Migrated Party-write eligibility.
4. Scheduling/Finance/ClientContact consumer cutovers.
5. Destructive Client/direct-column retirement.

The first dependency-safe implementation slice is **Matter/Property tenant-and-canonical-relationship schema foundation**, bounded to schema/security/provenance compatibility and explicitly excluding CRUD. It should make operational-fresh MatterParty and Party-based PropertyOwner composition representable without Client.

Because it crosses Alembic, tenancy, RLS, compatibility FKs and operational-fresh revision support, the expected executor is **Codex**, with Antigravity as independent QA.

## 18. Architecture boundary and reviewer checklist

This branch must contain documentation/ADR architecture only.

Independent QA should verify:
- authorization ancestry from `0933dc765693a62499be78d68256e8ea70988f71`;
- no production code/schema/migration/database changes;
- complete Client dependency inventory, including Appointment/Invoice/Payment;
- consistency with ADR-0021/0023/0033/0034/0035/0036/0037;
- no dual-master semantics;
- clean operational-fresh path creates no Client;
- MIGRATED is not overinterpreted;
- tenant/RLS sequencing remains fail closed;
- rollback/retirement boundaries are coherent;
- ADR-0039 correctly does not resolve Required ADR #20;
- Required ADRs #10/#11/#12/#15/#16/#17 remain unresolved;
- T132+ remains unauthorized.

**QA Decision:** _Pending independent QA. Software Architect must not fill this section._
