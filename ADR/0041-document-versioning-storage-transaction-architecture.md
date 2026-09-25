# ADR-0041: Document Versioning and Storage Transaction Architecture

**Status:** Proposed
**Date:** 2026-09-25
**Related task:** T140 — Document Versioning and Storage Transaction Architecture.

**Resolves:** Required ADR #11, “Document/version architecture.” Independent architecture QA approved the architecture and the §3.1 architecture PR merged; T140 governance closeout records the completed resolution.

**Does not resolve:** Required ADR #12 (Workflow vs Government Status), #15 (Core vs configurable vocabulary), #16 (UUID vs human-readable identifiers), #17 (Soft deletion/history), or #20 (Migration strategy from the current schema). It does not authorize implementation, deletion/retention policy, legacy Document→File resolution, compatibility retirement, or T141+.

**Composes with:** ADR-0020 session commit/rollback policy, ADR-0021 Organization tenant isolation, ADR-0022 authorization, ADR-0027 File numbering, ADR-0030 Matter/File identity, ADR-0037 operational-fresh provenance, ADR-0038 Self-Context projection authority, and ADR-0040 File/Document transition.

## Problem

T139 established the canonical application chain `authenticated Organization → Matter → genuine File → Document`. New Documents are File-canonical; retained `matter_id` is the ADR-0040 compatibility shadow; legacy `matter_id != NULL && file_id == NULL` Documents remain explicitly unfiled.

The repository already contains `DocumentVersion`, `FileStorageRecord`, a `FileStorage` port, and `LocalFileStorage`, but no application version/upload/download surface. The persistence shape fixes some facts while leaving the operational contract undecided. A version has UUID identity, `document_id`, integer `version_number`, mandatory `file_storage_record_id`, optional `change_summary`, creator and timestamp; `(document_id, version_number)` is unique. `Document` deliberately has no current-version pointer. `FileStorageRecord` stores provider, locator/path, original filename, MIME type, size, SHA-256, a generic optimistic-style `version` field, optional retention policy, uploader/timestamp and `deleted_at`. Neither `DocumentVersion` nor `FileStorageRecord` currently has `organization_id` or RLS. `LocalFileStorage` stores bytes beneath one configured root and rejects traversal, but accepts caller-selected relative paths.

A database commit and an external filesystem/object-store write cannot be one ordinary atomic transaction. Without architecture, implementation would have to invent version allocation, tenant ownership, storage namespace, failure compensation, retries and authorization while coding.

## Existing repository state

- `DocumentVersion` is immutable-shaped persistence: it has no update timestamp, soft-delete field or optimistic-lock mixin. Its unique key is `(document_id, version_number)`.
- Every persisted `DocumentVersion` currently requires exactly one `FileStorageRecord` by non-null FK.
- No uniqueness constraint currently prevents two versions from referencing the same storage record.
- Latest version is intentionally query-derived by highest `version_number`; there is no `documents.current_version_id`.
- `FileStorageRecord` is physical-object metadata, not the business File aggregate.
- The `FileStorage` port exposes `save(path, bytes)`, `read(path)`, `delete(path)`, and `exists(path)`; `StoredFile` returns path, size and content type.
- `LocalFileStorage` uses provider-relative paths under `settings.storage_root`.
- ADR-0020 makes the request-scoped SQLAlchemy session the database transaction owner: repositories flush and the request dependency commits on success or rolls back on exception.
- ADR-0021 requires mandatory application Organization scoping plus FORCE RLS/default-deny using the trusted Organization GUC and a non-owning, non-superuser, NOBYPASSRLS runtime role.
- T139 uses `documents:read` and `documents:write`; File/Matter permissions are explicitly not substitutes.
- Alembic/provenance frontier at T140 authorization is `be439c0d6fdb`.

## Options Considered

### 1. Database-only version records; add physical storage later

Allow DocumentVersion metadata without durable bytes and make storage optional. Rejected. It contradicts the existing mandatory `file_storage_record_id`, permits “versions” with no content, and creates a second lifecycle that later storage work would have to reconcile.

### 2. Store document bytes in PostgreSQL

Make the relational transaction fully atomic by storing binary content in the database. Rejected. The repository deliberately separates binary content from database metadata through FileStorage/FileStorageRecord, and this would discard the provider abstraction.

### 3. Blob-first write followed by one database commit, with deterministic technical storage keys and compensation

Write bytes to a deterministic, tenant-scoped provider key first; then, in the request's database transaction, allocate the version number and persist FileStorageRecord + DocumentVersion atomically. A database failure leaves at worst an unreferenced blob that is safely retryable/reconcilable. Selected.

### 4. Database-first metadata commit followed by blob write

Commit FileStorageRecord/DocumentVersion before writing bytes. Rejected. It can expose a committed “latest version” whose physical content does not exist and would require a staged/pending version state absent from the current domain.

### 5. Persisted per-Document counter table

Maintain a separate next-version counter row. Viable, but rejected as unnecessary state. The Document row itself already provides a natural per-Document serialization lock. A counter adds migration/state/recovery obligations without improving the required semantics.

### 6. `MAX(version_number)+1` without locking

Rejected. The unique constraint catches duplicates but does not provide deterministic concurrent behavior and forces collision/retry semantics into the API.

### 7. Current-version pointer on Document

Rejected for now. The existing model deliberately avoids the circular/denormalized pointer, and highest committed version number is sufficient once incomplete versions are never committed.

### 8. Transitive-only tenant ownership for versions/storage

Derive Organization only through Document. Rejected for application-visible DocumentVersion/FileStorageRecord. ADR-0021 requires tenant-scoped entities to be application-scoped and RLS-backed; direct independently queried rows need direct tenant identity for a simple default-deny RLS backstop and enforceable same-tenant references.

### 9. Content-addressed storage/deduplication

Use checksum as storage identity and share blobs across versions. Deferred. It introduces lifecycle/reference-counting and cross-tenant information-sharing questions not required for versioning.

## Decision

### 1. Identity and lifecycle

A **DocumentVersion** is one immutable, successfully committed content revision of one canonical File-resolved Document. UUID `DocumentVersion.id` is technical identity; `version_number` is an integer ordinal scoped only to `document_id`. It has no business-facing formatting semantics.

A version becomes durable and visible only when all of the following are true:

1. authorization and canonical Organization/Matter/File/Document validation succeeded;
2. the exact bytes have been durably saved through FileStorage under the selected technical key;
3. their SHA-256 and byte length are known;
4. one FileStorageRecord describing those exact bytes and one DocumentVersion referencing it have been inserted in the same database transaction; and
5. that database transaction committed.

There is no persisted incomplete/staged DocumentVersion in the normal path. A failed attempt is not a version.

Successfully committed DocumentVersion rows are immutable. `document_id`, `version_number`, `file_storage_record_id`, `change_summary`, `created_at`, `created_by`, and tenant identity introduced by implementation are not ordinary update fields. `change_summary` is optional creation-time metadata and is immutable after commit. Correction means creating another version, not replacing bytes or mutating the historical row.

Normal version replacement is prohibited. Global deletion, archival, legal hold, retention and purge semantics remain Required ADR #17. T140 defines no ordinary version delete.

A committed DocumentVersion requires exactly one committed FileStorageRecord. The normal DocumentVersion-owned FileStorageRecord is exclusive to that version. Future implementation must enforce one-to-one ownership for this use case (for example a uniqueness constraint on the DocumentVersion reference) rather than silently permitting sharing. Existing other FileStorageRecord consumers such as templates/QR are not redesigned.

A FileStorageRecord for a DocumentVersion is an immutable descriptor of the stored object after commit: provider, locator, original filename, MIME type, size, checksum and uploader/upload time are facts of that stored revision. Existing generic `version`, retention/deletion fields are not authority to mutate version content. Broader retention/deletion behavior remains #17.

The database is authoritative for **committed version existence**. A physical blob with no committed FileStorageRecord+DocumentVersion is an orphan candidate, not a DocumentVersion.

### 2. Version-number allocation and concurrency

Allocation scope is one Document.

The later implementation shall serialize allocation by acquiring a PostgreSQL row lock on the canonical Document (`SELECT ... FOR UPDATE`) inside the request database transaction after tenant/File/Document validation. While holding that lock it derives:

`next_version = COALESCE(MAX(committed version_number for document), 0) + 1`

and inserts the new version before commit. The existing unique `(document_id, version_number)` remains the final integrity backstop.

This is deliberately not ADR-0027's File-number counter architecture. Version numbers are internal immutable-history ordinals, not business File numbers, and the Document row is already a stable serialization point.

Same-Document writers serialize. Writers for different Documents do not block one another except for ordinary database/storage contention.

A failed database transaction does **not** consume a version number. Gaps are not intentionally allocated. The invariant is positive monotonically increasing committed ordinals; the architecture does not promise gap-free history after future #17 deletion/retention decisions.

Physical blob writing occurs before the Document row lock is held. This keeps potentially slow external I/O outside the database critical section. The blob key is independent of `version_number`, so storage does not require pre-reserving the ordinal.

Serialization/deadlock failures during the short database phase are retryable at the operation boundary. A uniqueness violation is a fail-closed integrity signal; implementation may retry the database allocation only after revalidation, never overwrite an existing version.

### 3. Latest/current version

“Latest version” means the highest `version_number` among committed DocumentVersion rows visible to the caller's Organization.

No Document pointer is introduced.

Because incomplete attempts never create committed DocumentVersion rows, failed uploads cannot become latest. Concurrent same-Document creation is serialized by the Document lock. Transaction isolation means another request sees only committed rows. Retry of the same logical upload must resolve to the already-created version when idempotency proves it committed, rather than create a new latest version.

Future #17 policy may define whether tombstoned/purged history affects read eligibility; T140 does not alter the definition for normal non-deleted committed history.

### 4. Tenant ownership, integrity and RLS

DocumentVersion and DocumentVersion-owned FileStorageRecord are tenant-scoped.

Later implementation requires direct mandatory `organization_id` on both tables for this application surface, populated only from the authenticated/canonical Document chain, never caller-controlled.

Database integrity must enforce:

- `document_versions.organization_id NOT NULL → organizations.id`;
- same-Organization DocumentVersion→Document, preferably composite `(organization_id, document_id) → documents(organization_id, id)`;
- `file_storage_records.organization_id NOT NULL → organizations.id` for records brought into this tenant-scoped architecture;
- same-Organization DocumentVersion→FileStorageRecord via composite FK/candidate key;
- exclusive DocumentVersion ownership of its FileStorageRecord.

Both tables must use ADR-0021's established tenant posture: RLS enabled and FORCE RLS; default deny without a valid Organization GUC; wrong Organization denied; correct Organization permitted subject to application authorization; runtime role non-owner, non-superuser, NOBYPASSRLS; migration/admin authority separate.

Existing FileStorageRecord consumers create a migration compatibility problem because the current table is shared by DocumentVersion, DocumentTemplate and QR metadata. The implementation migration must not fabricate tenant ownership. It may make direct Organization mandatory only where authoritative ownership is mechanically derivable. If retained pre-existing storage records cannot be assigned an Organization from authoritative relationships, implementation must STOP and use an additive nullable/staged tenant column plus guarded application eligibility until separately resolved; it must not guess. This is a bounded schema-transition consequence of T140, not resolution of global Required ADR #20.

No-GUC/wrong-GUC access to versions/storage metadata fails closed.

### 5. Storage namespace and locator

Physical object keys are technical, opaque, provider-relative identifiers. They never derive authority or business meaning from mutable title, DocumentType, original filename, File number, Matter number, client name, year, office, district, or other business labels.

For DocumentVersion content the canonical key shape is:

`organizations/{organization_uuid}/document-versions/{document_version_uuid}/content`

The DocumentVersion UUID is generated before physical write and is stable across retries. Organization UUID provides an explicit tenant namespace. Original filename is metadata only and is never part of the authoritative locator.

The key uses only server-generated UUID text and fixed separators, so callers cannot inject traversal components. LocalFileStorage must continue to enforce root containment as defense in depth. Object-storage providers treat the same value as an opaque provider-relative key.

`FileStorageRecord.storage_provider` identifies the configured provider implementation; `file_path` is the provider-relative opaque locator, not an externally exposed filesystem path or URL.

### 6. Upload/version-creation transaction and compensation

The authoritative normal sequence is:

1. authenticate caller and resolve trusted Organization;
2. require Document write authority;
3. validate Organization → Matter → genuine File → Document using the canonical T139/ADR-0040 chain; legacy-unfiled Documents are not eligible;
4. validate upload limits/metadata required by implementation policy before persistence;
5. generate `document_version_id` and `file_storage_record_id` UUIDs and derive the deterministic storage key;
6. compute SHA-256 over the exact bytes that will be stored and byte length;
7. call FileStorage.save using that key; successful return means the provider accepted the exact bytes;
8. enter/continue the request SQL transaction, lock the Document row, allocate the next version number, and persist FileStorageRecord plus DocumentVersion with the same Organization and actor;
9. flush constraints;
10. allow ADR-0020's request boundary to commit;
11. only after commit is the version visible/committed.

The architecture does **not** claim distributed atomicity.

Failure behavior:

- before blob save succeeds: database contains no version/storage record; return failure;
- blob save fails: database contains no version/storage record;
- blob succeeds, then validation/allocation/flush/commit fails: database transaction rolls back; the blob is an orphan candidate;
- the request path must make a best-effort compensating `FileStorage.delete(key)` after a known database failure where safe to do so; compensation failure is recorded/observable and does not turn the blob into a version;
- uncertain client outcome after database commit is handled by idempotency lookup, never by blindly creating another version;
- reconciliation tooling may later detect deterministic-key blobs without committed DB ownership and remove/quarantine them under separately authorized operational work.

Implementation must structure commit/compensation so ADR-0020 remains the database transaction authority. If the current dependency shape cannot expose commit outcome to the orchestration layer without changing ADR-0020 semantics, implementation must STOP and seek a bounded transaction-orchestration decision rather than committing inside repositories or claiming compensation it cannot execute.

### 7. Retry and idempotency

Version creation requires a persisted idempotency key because a client can lose the response after both blob and database commit and cannot distinguish “failed” from “committed.”

The key is caller-supplied as an opaque request token but is scoped server-side to `(organization_id, document_id, idempotency_key)`. It is not a version number and carries no business meaning.

Later persistence must record, transactionally with the committed DocumentVersion, at minimum the scoped key, a SHA-256 payload/content fingerprint sufficient to detect conflicting reuse, and the resulting `document_version_id`. A dedicated upload/version-request table is preferred over overloading immutable DocumentVersion business fields.

Behavior:

- first key + payload performs the operation;
- retry with the same scoped key and same fingerprint returns the already-committed version;
- same scoped key with different fingerprint is a conflict and performs no write;
- key scope prevents one Organization/Document from observing another's request;
- an orphan blob from a pre-commit failure uses the same deterministic version UUID/key only when the persisted request state proves that identity; otherwise retry may create a fresh UUID and reconciliation handles the orphan;
- no idempotency record may claim success before the version transaction commits.

A later migration is therefore expected for idempotency persistence.

### 8. Checksum and integrity

SHA-256 is mandatory integrity metadata for DocumentVersion content.

It is computed by the trusted application/storage orchestration over the exact bytes passed to FileStorage.save before database commit. `FileStorageRecord.checksum_sha256` stores the lowercase 64-hex digest; `size_bytes` stores exact byte length. Save result size must agree before commit; mismatch fails the operation and triggers compensation.

Checksum is **not content identity** and does not imply deduplication.

On download/read, the application validates the bytes returned by FileStorage against stored byte length and SHA-256 before releasing them as successful content. Mismatch is an integrity failure: do not return corrupted bytes as a successful download; record/raise an operational integrity error for diagnosis. This is intentionally stronger than trusting local disk/object storage and is provider-independent.

### 9. Authorization

Existing Document permissions are semantically sufficient for the first version/storage surface:

- list versions / read version metadata: `documents:read`;
- download content: `documents:read`;
- create/upload a new version: `documents:write`.

No File or Matter permission substitutes for these permissions. No new permission family is required by T140.

Tenant/RLS checks remain independent and mandatory. Authorization is evaluated against the canonical File-resolved Document before storage access. A storage key or FileStorageRecord UUID is never itself authorization.

Future confidentiality/external-sharing requirements may introduce narrower permissions, but they are not required to establish normal versioning and are outside T140.

### 10. Read/download boundary

Application routes/services remain nested under the canonical Matter/File/Document context rather than exposing a raw storage-record endpoint.

The read path:

1. authenticate and require `documents:read`;
2. resolve Organization from trusted identity;
3. validate Matter → File → Document under that Organization;
4. load the requested DocumentVersion in the same Organization and Document;
5. resolve its exclusive FileStorageRecord;
6. select FileStorage provider from trusted persisted/configured provider identity;
7. call FileStorage.read with the provider-relative locator;
8. verify size and SHA-256;
9. return/stream bytes with response metadata derived from stored original filename and MIME type.

Physical local paths, storage-root paths, provider credentials and object-store internal URLs are never returned as authority to clients.

The current `read() -> bytes` port is sufficient for correctness but not ideal for large files. A later implementation may extend the port with streaming read/write methods while retaining the same opaque-key/provider contract. Such extension must be provider-neutral; application services must not depend on `pathlib` or cloud SDK types.

Missing blob, provider error or checksum mismatch fails closed as a storage/integrity error; it is not converted to “version not found” when database metadata proves the version exists.

### 11. Provider portability

`FileStorage` remains the application boundary. Provider selection is infrastructure/configuration, while `FileStorageRecord.storage_provider` records which provider owns the object.

Required semantics are provider-relative opaque key, save exact bytes, read exact bytes, existence check, and compensating delete. Provider-specific bucket/container/root details remain configuration and are not persisted as business identity.

The existing local implementation is valid as one provider. T140 does not authorize cloud storage, signed URLs, multipart uploads or provider-specific metadata. If future object storage requires richer streaming/conditional-put semantics, extend the port without changing DocumentVersion identity.

### 12. Legacy Document boundary

Legacy-unfiled Documents (`matter_id != NULL && file_id == NULL`) are **not eligible for new DocumentVersion upload/create/read/download through the canonical application surface**.

This does not erase any existing historical DocumentVersion rows that may already reference such Documents; they remain preserved database evidence. T140 does not expose them through a new canonical route, assign a File, manufacture a File, infer membership or retire `matter_id`.

Operator File resolution remains the ADR-0040 prerequisite before ordinary canonical version/storage operations on such a Document. This applies existing ADR-0040 semantics rather than inventing a new relationship.

### 13. Required ADR #17 boundary

T140 decides only normal immutable create/list/read/download semantics and failure cleanup for **uncommitted orphan blobs**.

It does not decide deletion, archival, retention periods, legal hold, purge, historical-record destruction, or the meaning/use of existing `deleted_at`/`retention_policy` fields. No committed DocumentVersion or its owned blob is deleted by normal T140 behavior.

Compensating deletion of an uncommitted orphan blob is not historical-record deletion because no committed DocumentVersion exists for it.

Any future committed-version removal or storage reclamation must compose with Required ADR #17.

### 14. Migration and integrity requirements for later implementation

A later implementation is expected to require an Alembic migration. Minimum required persistence work:

1. tenant ownership for DocumentVersion and the DocumentVersion-owned FileStorageRecord path;
2. candidate/composite keys and same-Organization FKs supporting tenant integrity;
3. FORCE RLS/default-deny policies on application-visible version/storage metadata;
4. exclusive DocumentVersion→FileStorageRecord ownership constraint for this use case;
5. persisted idempotency request/result state with tenant/document scope and fingerprint;
6. indexes for `(organization_id, document_id, version_number)`, idempotency lookup and storage ownership as required;
7. operational-fresh supported-revision advancement to the exact new Alembic head using ADR-0037's established mechanism.

No separate version counter table is required.

Existing rows must be backfilled only from authoritative relationships. DocumentVersion Organization can derive from its Document when that Document has authoritative Organization. A FileStorageRecord used by a DocumentVersion can derive from that version's Document. Shared/other-consumer storage records require explicit migration analysis; contradictory multi-tenant ownership fails closed. No filename/path/provider heuristic may assign Organization.

If safe NOT NULL/direct RLS finalization cannot be achieved for the shared FileStorageRecord table without resolving unrelated existing consumers, implementation must use an additive staged design and STOP before claiming final tenant-safe application visibility for unresolved records.

### 15. Downgrade and recovery

Future migration downgrade is allowed only where the preceding schema can faithfully represent persisted state.

If a migration adds direct tenant/idempotency/integrity structures and populated rows cannot be represented without losing ownership, retry evidence or security invariants, downgrade must refuse rather than silently discard them. Operational-fresh supported-revision history must not be falsified.

Recovery classes:

- **orphan blob, no committed DB record:** safe candidate for reconciliation/compensating removal after proving no committed reference;
- **orphan FileStorageRecord without DocumentVersion:** invalid for the normal version path; quarantine/reconcile, never surface as a version;
- **committed DocumentVersion/FileStorageRecord but missing blob:** integrity incident; fail reads, do not manufacture content;
- **checksum/size mismatch:** integrity incident; fail reads, preserve evidence;
- **duplicate/conflicting idempotency evidence:** fail closed;
- **provider unavailable:** transient storage failure; committed metadata remains authoritative that a version exists, but content is unavailable until provider recovery.

Repair/reconciliation tooling is not implemented or authorized by T140.

### 16. Composition with governing ADRs

- **ADR-0020:** preserved. Database metadata is one request-scoped transaction; repositories remain flush-only. External storage is explicitly compensated rather than falsely included in the DB transaction.
- **ADR-0021:** strengthened for the new independently queried entities through direct tenant identity, application scoping and FORCE RLS. Storage keys also carry a technical Organization namespace, but namespace is defense in depth, not a replacement for DB/RBAC checks.
- **ADR-0022:** existing Document read/write permissions govern normal version/content operations; no File/Matter permission broadening or RBAC redesign.
- **ADR-0027:** unaffected. Version ordinals are not File numbers and use Document-row serialization rather than the File counter.
- **ADR-0030:** unaffected. Business File remains the work package; physical FileStorageRecord is not a business File.
- **ADR-0037:** a future migration must advance supported operational-fresh revision by the established mechanism; provenance architecture is unchanged.
- **ADR-0038:** unaffected. T140 adds durable architecture evidence but no Self-Context Layer B/C behavior.
- **ADR-0040:** preserved. Canonical version operations require a genuine File-resolved Document; legacy-unfiled records remain preserved and unresolved.

### 17. Consequences and trade-offs

Selected architecture favors correctness and recoverability over pretending DB/blob atomicity exists.

Benefits:

- committed versions never intentionally point to content that was never saved;
- latest-version semantics stay simple and pointer-free;
- same-Document version allocation is deterministic under concurrency;
- slow blob I/O does not hold the Document DB lock;
- retries cannot silently create duplicate versions after uncertain responses;
- tenant identity is explicit at independently queried persistence/storage layers;
- provider-specific filesystem/cloud details remain outside application logic;
- checksum is a real end-to-end integrity check rather than decorative metadata.

Costs:

- blob-first ordering can create orphan physical objects after DB failure;
- persisted idempotency adds schema and operational complexity;
- direct FileStorageRecord tenant ownership is complicated by existing non-DocumentVersion consumers;
- download checksum verification consumes I/O/CPU proportional to file size;
- Document row locking serializes concurrent version creation for one Document by design.

These are preferable to exposed incomplete versions, cross-tenant ambiguity or silent duplicate history.

### 18. Rejected alternatives summary

Rejected: DB-only versions, PostgreSQL blob storage, DB-first committed metadata, unlocked MAX+1, separate counter table, current-version pointer, transitive-only tenant enforcement, checksum/content-addressed deduplication, business-label-based storage paths, and broad new RBAC permissions.

### 19. Implementation decomposition

No successor is authorized. After T140 completes its full §3.1 lifecycle, the smallest dependency-safe implementation is **two sequential slices**:

1. **Version/storage tenant + integrity schema foundation.** One migration establishes direct/staged tenant ownership, same-tenant constraints/RLS, exclusive version-storage ownership, idempotency persistence, indexes and operational-fresh revision advancement. It also performs only authoritative backfill/validation and must fail closed on ambiguous shared FileStorageRecord ownership. No upload/download API.
2. **Canonical DocumentVersion application + storage orchestration.** Repository/service/API for list/get/create-upload/download; Document-row allocation lock; FileStorage orchestration; checksum verification; idempotency behavior; compensation; existing Document RBAC; canonical File-resolved eligibility. Provider-port streaming extension may be included only if required by bounded implementation acceptance criteria.

Slice 2 depends on slice 1. Migration-frontier serialization therefore remains simple. Splitting the schema/security foundation from external-I/O orchestration gives independent QA a stable RLS/integrity base before transaction/failure-path behavior is added.

Legacy Document resolution remains a later independent task, not a third slice of this implementation.

### 20. Explicit exclusions

This ADR does not implement or authorize DocumentVersion repository/service/API, allocator code, FileStorageRecord CRUD, upload/download endpoints, FileStorage changes, migrations, database mutation, Document/File deletion, legacy Document→File resolution, synthetic/default Files, heuristic assignment, `documents.matter_id` retirement, OCR, template generation, MatterProperty, classification/work-type redesign, Client retirement/migrations, Enquiry/Lead, Quotation, Scheme, Gujarat record surfaces, Government Process, Self-Context B/C, Project Delivery Roadmap, frontend work, or T141+.

### 21. STOP conditions for implementation

A future implementation must stop/escalate rather than expand scope if:

- shared existing FileStorageRecord rows cannot be tenant-owned from authoritative evidence;
- safe application visibility would require global Required ADR #17 or #20 resolution;
- ADR-0020's request transaction cannot support observable commit/compensation semantics without a new transaction decision;
- tenant safety requires redesigning ADR-0021;
- storage namespace needs business-facing naming policy;
- authorization requires broad RBAC redesign;
- legacy File resolution becomes prerequisite;
- a destructive migration becomes prerequisite;
- existing production storage semantics contradict this ADR;
- another merged task changes the relevant migration/architecture frontier.

### 22. Required ADR #11 disposition

Required ADR #11 asks for Document/version architecture. This ADR defines version identity/lifecycle, immutable history, concurrency-safe allocation, latest-version semantics, storage ownership, tenant/RLS, namespace, DB/blob transaction and compensation, idempotency, checksums, authorization, read/download behavior, provider portability, migration/recovery requirements, legacy boundary and #17 boundary sufficiently for implementation.

Therefore ADR-0041 **resolves Required ADR #11**. Independent architecture QA approved the decision and the architecture PR merged; this §3.1 governance closeout performs the settled-state synchronization.

## Reviewer Checklist — Software Architect self-assessment

- [x] Scope matches the authorized T140 Required-ADR architecture task.
- [x] Repository/code/migration state was freshly inspected at authorization baseline.
- [x] Governing ADRs and ADR-0040 compatibility are composed rather than reopened.
- [x] Alternatives are genuine and the selected decisions are explicit.
- [x] Tenant isolation and authorization are treated as independent mandatory layers.
- [x] Concurrency, transaction, retry, integrity and failure semantics are concrete enough for implementation.
- [x] Required ADR #17/#20 and legacy boundaries are explicitly preserved.
- [x] Implementation decomposition is dependency-safe and does not authorize successors.
- [x] No production code, test or migration behavior is changed by this ADR.
- [x] Consequences, trade-offs, recovery and STOP conditions are documented.
- [x] Required ADR #11 resolution is proposed only through the §3.1 QA/closeout lifecycle.

## QA Decision

- [ ] Approved
- [ ] Approved with comments
- [ ] Rework required

Independent QA Reviewer only. The Software Architect does not render this decision.
