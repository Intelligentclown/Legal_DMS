# ADR-0040: File/Document Transition and Current-Schema Migration Architecture

**Status:** Proposed  
**Date:** 2026-09-24  
**Related task:** T136 — File/Document Transition and Current-Schema Migration Architecture.

**Resolves, subject to independent QA and §3.1 governance closeout:** Required ADR #10, “Document/File relationship” — the exact `documents.matter_id` → `documents.file_id` relationship and migration mechanics.

**Advances but does not resolve:** Required ADR #20, “Migration strategy from the current schema.” T136 settles only the File/Document seam. Matter `property_id` / `matter_type_id`, MatterProperty/classification/work-type transitions, remaining Client consumers, ClientContact, Appointment, Invoice, Payment, final Client retirement, and other separately governed current-schema transitions remain unresolved.

**Composes with:** ADR-0020, ADR-0021, ADR-0022, ADR-0027, ADR-0030, ADR-0037 and ADR-0039. None is reopened.

## Context and current state

At authorization baseline `09229cef3a4e31300edf31a904aa7a443fe80f4b`, the repository has no business File/work-package entity. `Matter` is directly tenant-owned through mandatory `organization_id`. `Document` is an audited/optimistic-locked entity with mandatory `matter_id`, mandatory `document_type_id`, `title`, and `status` (default `draft`). It does not directly carry Organization ownership. `DocumentVersion` is immutable history with mandatory `document_id`, unique `(document_id, version_number)`, mandatory `file_storage_record_id`, optional change summary, created-at and created-by. The latest version is deliberately query-derived; no current-version pointer exists.

`FileStorageRecord` is physical/blob-storage metadata: provider, path, original filename, MIME type, size, SHA-256 checksum, retention policy, uploader/timestamps and soft deletion metadata. The `FileStorage` port and `LocalFileStorage` implementation store bytes outside Postgres. A FileStorageRecord is therefore **not** the business File aggregate. Business grouping belongs to File; legal-document identity belongs to Document; immutable content-version identity belongs to DocumentVersion; physical storage identity belongs to FileStorageRecord.

Current persisted relationship:

```text
Matter 1 ── 0..N Document 1 ── 0..N DocumentVersion ── 1 FileStorageRecord
```

Target relationship:

```text
Organization 1 ── 0..N Matter 1 ── 0..N File 1 ── 0..N Document
                                               Document 1 ── 0..N DocumentVersion
                                               DocumentVersion ── 1 FileStorageRecord
```

The governed specification requires `Matter → File → Document`. Existing `Document.matter_id` proves only Matter membership. It does **not** prove membership in a particular work package.

## Governing decisions preserved

### ADR-0030

Matter is the root; File is optional under Matter; File cannot exist without exactly one Matter; File has identity distinct from Matter; File is a work package; its lifecycle is existence-dependent on Matter but operationally distinct. Cardinality remains Matter `1 → 0..N File`.

### ADR-0027

File numbers remain Matter-scoped. `file_number_sequences` is a directly tenant-owned counter table. Allocation uses an atomic PostgreSQL `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` counter operation, and counter advancement plus File insertion occur in one transaction. Successfully persisted File numbers are never reused. Exact display formatting remains deferred.

### ADR-0021

Every tenant-scoped table carries mandatory direct `organization_id`; application scoping is primary and PostgreSQL `FORCE ROW LEVEL SECURITY`, Organization-GUC default-deny policy, and a non-owning/non-superuser/`NOBYPASSRLS` runtime role form the database backstop. Migration/admin authority is separate.

## Problem

The project must introduce the business File without fabricating File membership for retained Documents and without creating two undefined relationship authorities. A migration based on title, filename, chronology, document type, upload order, storage path, similarity or arbitrary grouping would create unsupported business meaning.

The transition must support clean operational-fresh business immediately while preserving retained `Document → Matter` evidence until an operator explicitly assigns each legacy Document to a real File.

## Alternatives considered

### A. One automatic compatibility File per Matter

Rejected. Although deterministic and operationally convenient, it asserts that all historical Documents in a Matter formed one business work package. Current data proves only Matter membership. Calling the synthetic row “compatibility” does not remove that fabricated business meaning. It also consumes a File identity/number for an entity no user actually created.

### B. Legacy Documents remain temporarily unfiled while new Documents are File-canonical

**Selected.** Introduce File and nullable `documents.file_id` while retaining `documents.matter_id` as compatibility evidence. Existing Documents remain unfiled until explicitly assigned by an authorized operator. No compatibility/default File is synthesized.

### C. Require all legacy Documents to be resolved before File capability is usable

Rejected. Safe but unnecessarily blocks operational-fresh and new canonical business. Ambiguous legacy rows can coexist as explicit compatibility state without weakening the canonical new-write contract.

### D. Infer File membership heuristically

Rejected. Unsupported inference is not evidence.

## Decision

### 1. Target aggregate/cardinality

- Organization owns zero or more Matters.
- Matter belongs to exactly one Organization and owns zero or more Files.
- File belongs to exactly one Organization and exactly one Matter.
- File may exist with zero Documents.
- In target state, every Document belongs to exactly one Organization and exactly one File.
- A File owns zero or more Documents.
- A Document belongs to **one File only**; many-to-many Document/File membership is prohibited.
- Document owns zero or more immutable DocumentVersions.
- Each DocumentVersion references exactly one FileStorageRecord.
- FileStorageRecord remains storage metadata, not a business File.
- DocumentVersion and FileStorageRecord do not acquire business-File semantics.

### 2. Minimum File persistence boundary

Migration-foundation File fields are:

- `id: UUID`;
- `organization_id: UUID NOT NULL`;
- `matter_id: UUID NOT NULL`;
- a File-number component/value produced exclusively by ADR-0027's counter;
- `title: string NOT NULL`;
- standard repository creation/update audit timestamps/actors only where the existing aggregate convention requires them.

A concrete File status vocabulary is **not required for safe migration and is deferred**. A future implementation must not invent terminal states merely to create the table. Description, classification/work-type inheritance/override, government-process attachment and richer lifecycle fields are deferred unless a separately governed task decides them.

File number display format remains deferred by ADR-0027. The persisted representation must preserve the counter value and enforce uniqueness at least within Matter.

Hard deletion/cascade semantics are not decided here beyond ADR-0030's invariant that an extant File cannot be orphaned from Matter. Initial implementation should prefer restrictive/no destructive delete until lifecycle semantics are separately governed.

### 3. No compatibility/default Files

Migration must **not** create a synthetic/default/“Legacy Documents” File. Consequently there is no migration-only File kind, magic title, provenance flag, special rename rule or special number allocation.

Every File row is a genuine business File. It is created explicitly through normal application behavior or explicit operator resolution and therefore consumes an ordinary File number under ADR-0027.

Operator-created Files used to resolve legacy Documents are genuine business Files: they receive normal identity/numbering, may receive Documents explicitly assigned to them, and participate in normal future File behavior. Assignment is an explicit business assertion, not inferred migration metadata.

### 4. Numbering

- New operational Files consume ordinary ADR-0027 numbers.
- Operator-created Files for legacy resolution consume ordinary ADR-0027 numbers.
- No number is consumed merely because a legacy Document exists.
- No migration/default File exists, so automatic migration consumes no File number.
- Allocation and File insertion are atomic in one transaction.
- Retried failed creation cannot leave a consumed counter value because counter and File insert roll back together.
- A committed File number is never reused after archive/removal.
- Downgrade/re-upgrade never rewinds counters or attempts to recover a previously committed number.

### 5. Compatibility schema and direct Organization ownership

The compatibility stage carries **both**:

- `documents.matter_id`;
- `documents.file_id`.

It also introduces mandatory direct `documents.organization_id`.

Direct Document Organization ownership is selected rather than RLS-through-File because legacy Documents intentionally have `file_id = NULL` during coexistence. A File-join-only policy would either fail to represent those rows or require a second policy path through Matter, increasing policy complexity and leaving Document without the direct tenant dimension ADR-0021 requires.

Organization backfill for retained Documents is deterministic from their existing mandatory `matter_id → Matter.organization_id`. Missing Matter evidence or contradictory Organization evidence fails migration; no default Organization is permitted.

Files and Documents each receive their own forced Organization-GUC RLS policy.

### 6. Database integrity

Future implementation must provide:

- `files.organization_id NOT NULL → organizations.id`;
- unique `files(organization_id, id)` to support composite same-tenant FKs;
- same-Organization composite File→Matter FK `(organization_id, matter_id) → matters(organization_id, id)`;
- File-number uniqueness at Matter scope;
- `documents.organization_id NOT NULL → organizations.id`;
- unique `documents(organization_id, id)` where needed by tenant-safe downstream references;
- compatibility same-Organization Document→Matter FK `(organization_id, matter_id) → matters(organization_id, id)`;
- nullable same-Organization Document→File FK `(organization_id, file_id) → files(organization_id, id)`;
- an invariant that when `file_id IS NOT NULL`, the referenced File's `matter_id` equals `documents.matter_id`.

PostgreSQL cannot express the final three-column cross-table equality as a simple CHECK. The preferred database-enforceable shape is a composite FK from Document `(organization_id, matter_id, file_id)` to a candidate key on File `(organization_id, matter_id, id)`, while retaining ordinary indexing for File lookup. If implementation inspection shows this exact constraint shape conflicts with PostgreSQL/Alembic mechanics, STOP rather than weakening equality to application-only validation.

Both `matter_id=NULL,file_id=NULL` and `matter_id=NULL,file_id!=NULL` are invalid during compatibility. `matter_id!=NULL,file_id=NULL` is the explicit unresolved legacy state. `matter_id!=NULL,file_id!=NULL` is canonical/resolved only when the composite equality constraint succeeds.

### 7. Canonical write authority

**Operational-fresh/new business:** File is canonical from first write. A new Document must specify/resolve exactly one File. Application obtains Matter and Organization through the File. During compatibility the implementation also writes `documents.matter_id = files.matter_id` as a **derived compatibility shadow**, never as an independent caller-controlled relationship. Caller-supplied matter disagreement is rejected.

**Legacy/MIGRATED installations, new Documents:** same rule. Installation classification does not justify creating new matter-only Documents.

**Legacy untouched Documents:** no ordinary business update may silently invent `file_id`. They remain `matter_id != NULL, file_id = NULL` until explicit operator resolution.

**Operator resolution:** authorized operator selects/creates a genuine File under the Document's existing Matter; assignment is allowed only when Organization and Matter agree. The operation writes `file_id`; it does not change historical Matter membership.

**Migration/admin:** may populate `organization_id` mechanically from Matter and may validate relationships. It may not synthesize File membership.

There is never normal dual authority: `file_id` is canonical once present; `matter_id` is a derived compatibility shadow.

### 8. Canonical read authority

- If `file_id IS NOT NULL`, File is canonical for business grouping and its Matter is canonical for the target chain. `documents.matter_id` must match and is compatibility-only.
- If `file_id IS NULL`, the row is explicitly **legacy-unfiled**. `matter_id` remains authoritative only for preserved historical Matter membership; the application must not pretend the Document belongs to a File.
- Queries may expose legacy-unfiled status during coexistence.
- A mismatch between File and Document Matter/Organization is invalid and fails closed; no precedence rule “chooses” one side.

### 9. Operational-fresh behavior

At the future File-capable supported revision:

- Files are created explicitly and normally.
- New Documents require File.
- Compatibility/default Files do not exist.
- New application behavior never creates a matter-only Document.
- `documents.matter_id`, while retained, is populated only as a derived shadow from File.
- No Client identity is manufactured.
- File and Document are directly Organization-owned and RLS-protected.

The implementation task that introduces the schema/provenance revision owns advancing ADR-0037/T126's supported operational-fresh schema revision to its exact Alembic head using the established mechanism. T136 itself changes no classifier.

### 10. Legacy and MIGRATED behavior

Installation classification does not alter evidence semantics:

- retained valid `Document.matter_id` permits deterministic Document Organization derivation;
- it does not permit File inference;
- MIGRATED does not mean legacy Documents are File-resolved;
- operator resolution remains required for each unfiled retained Document unless future authoritative evidence, separately governed, proves a mapping;
- contradictory/missing tenant or Matter evidence fails closed.

### 11. RLS/security

File and Document are tenant-scoped entities. Future implementation must:

- carry mandatory direct `organization_id` on both;
- use application Organization scoping on every repository/service operation;
- enable and FORCE RLS on both tables;
- use Organization-GUC default-deny policies;
- prove no-GUC and wrong-Organization denial;
- use the established non-owner/non-superuser/`NOBYPASSRLS` runtime role;
- keep Alembic/migration/admin authority separate;
- ensure `file_number_sequences.organization_id` and referenced Matter Organization agree.

DocumentVersion remains transitively owned through Document for this T136 decision and is not structurally redesigned. Before a future DocumentVersion application surface becomes tenant-queryable independently, its tenant/RLS treatment must be checked against ADR-0021; T136 does not authorize adding a direct Organization field there.

### 12. Migration phases and pause points

**Phase A — additive tenant/File foundation.** Add File, `file_number_sequences`, direct Document Organization ownership, nullable `file_id`, same-tenant constraints and RLS. Backfill Document Organization solely through existing Matter. Existing Documents remain matter-only. No File backfill. New File creation may become available only after numbering/RLS tests pass. Safe pause: yes. Canonical reads for old Documents remain Matter compatibility reads.

**Phase B — canonical new-write switch.** File application creation exists; new Document creation, once implemented, requires File and derives compatibility `matter_id`. Legacy Documents remain explicitly unfiled. Safe pause: yes.

**Phase C — operator legacy resolution.** Provide bounded tooling/application behavior to list legacy-unfiled Documents and assign each to a genuine File under the same Matter. No heuristic auto-assignment. Safe pause: yes; unresolved rows remain visible as compatibility state.

**Phase D — canonical-read switch and consumer migration.** All consumers capable of File-aware behavior use File where present and explicitly handle unresolved legacy rows. Once every retained Document has File, business reads stop relying on direct Matter relationship. Safe pause: yes after validation.

**Phase E — validation/retirement preparation.** Prove zero unfiled retained Documents, zero mismatches, all consumers migrated, API/contracts/tests no longer depend on direct Matter authority, and recovery/downgrade policy accepted. No column removal yet.

**Phase F — separately authorized destructive retirement.** Drop direct `documents.matter_id` only under a future task after the retirement gate below. This is the irreversible semantic boundary and is not authorized by T136.

### 13. Downgrade

- Phase A can downgrade only if no persisted File-dependent business state would be lost. A downgrade may remove purely additive empty File structures after proving they are unused.
- Once any genuine File exists, a downgrade to a schema with no File representation must **refuse** unless an explicit separately governed recovery procedure preserves File identity and grouping. Multiple Files under one Matter cannot be collapsed into `Document.matter_id` without information loss.
- Once a Document has been explicitly assigned to File, downgrade must not erase that assignment and pretend Matter-only state is equivalent.
- Counter state must not be rewound to reuse committed numbers.
- Operator-resolution evidence must survive any supported rollback/re-upgrade path.
- After Phase F retirement, rollback is forward-repair or restore/recovery, not fabrication of direct relationships.

Safe refusal is the required behavior whenever the previous revision cannot faithfully represent persisted File distinctions.

### 14. Retirement gate for `documents.matter_id`

Direct Matter linkage may be removed only by a separately authorized task after all are proven:

1. every retained non-deleted Document has non-null valid File;
2. every Document Organization equals File Organization;
3. every retained compatibility Matter equals File Matter;
4. no unresolved legacy-unfiled row exists;
5. no runtime repository/service/API/background/search/audit/storage consumer reads or independently writes `Document.matter_id`;
6. all new writes have been File-canonical for an evidenced compatibility period;
7. migration/backfill/operator-resolution tooling reports no unresolved/contradictory cases;
8. QA covers tenant isolation, compatibility, canonical reads/writes and failure paths;
9. downgrade/recovery semantics for retirement are documented and tested;
10. documentation and Self-Context references no longer describe Matter→Document as canonical;
11. protected CI/governance gates are green on the exact retirement head.

### 15. Required ADR #10

Required ADR #10 asks for Document/File relationship migration mechanics — the `matter_id`→`file_id` redirect sequencing. This ADR answers the relationship, coexistence, authority, allowed states, migration, operator-resolution, tenant, downgrade and retirement mechanics completely enough for implementation.

Therefore ADR-0040 **proposes resolution of Required ADR #10**. The structured governance ledger must not mark #10 resolved on this architecture PR merely because this document says so. Independent QA must verify the claim, and §3.1 governance closeout after the architecture PR merges is the proper synchronization point.

### 16. Required ADR #20 boundary

T136 settles only:

- introduction/coexistence of `Document.file_id`;
- retention and eventual retirement gate for `Document.matter_id`;
- direct Document tenant ownership required by this migration;
- File/Document legacy-resolution sequencing;
- rollback/refusal boundary for this seam.

Required ADR #20 remains globally unresolved. It still includes Matter `property_id`, `matter_type_id`, MatterProperty, classification/work-type migration, remaining Client compatibility consumers, ClientContact, Appointment, Invoice, Payment, final Client retirement and any other separately governed current-schema transition.

### 17. ADR-0039 composition

ADR-0039's discipline is reused, not extended into a second master:

- one canonical write representation;
- compatibility columns are evidence/shadows, not co-equal authorities;
- no fabricated identity/relationship;
- contradiction fails closed;
- destructive retirement has an explicit evidence gate.

For File-resolved Documents, `file_id` is canonical and `matter_id` is a derived compatibility shadow. For unresolved legacy Documents, `matter_id` preserves only the historical fact it actually proves.

### 18. Independent boundaries

MatterProperty is independent. File belongs to Matter regardless of how Matter eventually relates to one or many Properties. T136 does not design MatterProperty or retire `Matter.property_id`.

Classification/work-type is independent. File existence and Document membership do not require deciding `matter_type_id`, MatterClassification or MatterWorkType. T136 does not redesign them.

GovernmentProcess/Workflow/Task attachment granularity is outside T136.

Document confidentiality/status vocabulary and Required ADR #11 broader Document/version questions are not silently resolved here. Existing DocumentVersion structure is preserved.

## Existing-consumer impact inventory

| Component | T136 finding | Future adaptation |
|---|---|---|
| `Document` ORM | direct mandatory `matter_id`; no tenant/File field | **first schema slice** |
| `DocumentVersion` ORM | Document-owned immutable versions | unaffected structurally by first slice |
| `FileStorageRecord` ORM | physical metadata only | unaffected |
| `DocumentTemplate` / `DocumentVariable` | template framework, independent of business File | unaffected |
| `9a68ef4298ae_documents_and_file_storage.py` | created current direct relationship | historical evidence; no edit |
| document model integration tests | assert valid Matter FK/version uniqueness | **first schema slice tests must adapt/extend** |
| FileStorage port / LocalFileStorage | byte storage abstraction | unaffected |
| Matter application repository/service/API | no Document application behavior | later File navigation only if authorized |
| document repository/service/API | none exists at baseline | future canonical implementation starts File-first |
| OCR jobs/results | reference DocumentVersion, not Matter | later compatibility consumer only if tenant-access path is implemented |
| QR records | generic entity reference | unaffected by relationship migration itself |
| search | no current Document application query implementation | later File-aware indexing/query work |
| workflow/tasks/government process | no authoritative Document.matter_id consumer identified | unaffected by T136; attachment architecture deferred |
| audit/activity | no direct Document relationship consumer identified | later application/audit integration |
| permissions | no File/Document application permissions established for this surface | first application slice |
| bootstrap/seed | DocumentType lookup exists; no File business seed | File seed not required |
| Self-Context/docs | specification and ADRs mention current gap | documentation updated through architecture/closeout, implementation references later |

No current Document repository/service/API was found. The material current consumers are schema/migration/model tests and transitive storage/version infrastructure.

## Implementation decomposition

These slices are unnumbered and unauthorized.

1. **File + Document tenant/compatibility schema foundation.** Add File, counter, direct Document Organization, nullable File FK, same-tenant/equality constraints, forced RLS, deterministic Organization backfill, provenance supported-revision advancement. No File CRUD and no Document application CRUD. Migration/security impact high; downgrade must refuse if existing File state cannot be represented. **Codex-level implementation.** QA: migration upgrade/downgrade, tenant/RLS/runtime role, no synthetic File, legacy-unfiled preservation, composite mismatch rejection, classifier/provenance.

2. **File application + numbering surface.** Organization-scoped File list/get/create/update as safely governed; atomic ADR-0027 number allocation; no destructive delete unless separately governed. Depends on slice 1. No schema migration expected beyond missing implementation-proven invariant. **Codex preferred** because transactional numbering is concurrency-sensitive. QA: concurrent creation, rollback/no burned allocation, same-org Matter, RLS/permissions.

3. **Canonical Document application surface.** Document create/read/update and version operations require File for new business and derive compatibility Matter from File. Depends on slices 1–2. Security impact high; no heuristic legacy assignment. **Codex preferred.** QA: File-canonical writes, derived shadow, version immutability, storage boundary, cross-tenant denial.

4. **Legacy Document resolution tooling.** Explicitly list unresolved legacy-unfiled Documents and assign them to genuine same-Matter Files. Depends on File and Document application surfaces. No automatic grouping. Rollback must preserve explicit assignment evidence. **Codex/OpenCode only after exact scope inspection; Codex if migration/admin path is involved.** QA: idempotence, mismatch rejection, operator authorization, no inference.

5. **Compatibility consumer/read migration.** Move all File-resolved reads/navigation/search/audit integrations to File authority while retaining explicit handling for unresolved rows. Depends on sufficient resolution tooling. Migration impact low unless new indexes required. QA focuses on no fallback ambiguity.

6. **Direct Matter-link retirement.** Separately authorized destructive cleanup only after the retirement gate. Drops compatibility column/constraints and makes File mandatory in final schema. Required ADR #20 remains relevant to broader schema even after this seam closes. **Codex-level, independent QA and recovery evidence mandatory.**

No slice number or successor is selected by this ADR.

## Alpha consequence

After architecture closes, the minimum Alpha-useful File/Document vertical slice is: create a genuine File under Matter with concurrency-safe number; create a Document under that File; add/read immutable DocumentVersions backed by FileStorageRecord; list/read Files and Documents within Organization; preserve explicit legacy-unfiled Documents without fabricated grouping. Enquiry, Quotation, MatterProperty, Gujarat property records and final multi-work-type architecture are not prerequisites to this File/Document vertical slice.

## Risks and QA-verifiable acceptance criteria

Independent QA must verify:

1. authorization baseline and ancestry;
2. no business File existed at baseline;
3. current Document/DocumentVersion/FileStorageRecord shapes are accurately stated;
4. ADR-0027 and ADR-0030 are preserved;
5. no automatic compatibility File or heuristic File assignment exists in the decision;
6. target cardinality is unambiguous;
7. operational-fresh new Documents are File-canonical;
8. legacy-unfiled is explicit, not silently canonical;
9. dual-column authority/read precedence is defined;
10. mismatch fails closed and has a database-enforceable target;
11. direct Document Organization ownership/RLS is coherent with legacy-unfiled rows;
12. no Organization is guessed;
13. migration phases have safe pause points;
14. downgrade refuses lossy collapse;
15. retirement gate is evidence-based;
16. #10 can honestly resolve only after independent QA/closeout;
17. #20 remains globally unresolved;
18. ADR-0039 remains Proposed and is only composed with;
19. MatterProperty and classification remain outside scope;
20. no production/schema/migration/test implementation occurs on T136 architecture branch;
21. implementation decomposition is dependency-safe and does not authorize successors.

## Consequences

The selected strategy deliberately accepts a temporary explicit legacy-unfiled state. This is preferable to inventing work-package history. Clean/new business is immediately modeled correctly once implementation lands. Legacy resolution is visible and operator-driven. Direct Document Organization ownership adds schema work but produces simpler, stronger RLS and same-tenant constraints. The eventual removal of `documents.matter_id` is delayed until evidence proves it is merely a redundant shadow.

This ADR is architecture only. It creates no table, migration, model, service, route, permission, RLS policy, classifier change, test behavior, backfill or database mutation.
