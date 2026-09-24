# T136 Software Architect Report — File/Document Transition and Current-Schema Migration Architecture

**Task:** T136  
**Role:** Software Architect  
**Authorization baseline:** `09229cef3a4e31300edf31a904aa7a443fe80f4b`  
**Authorization PR:** #243  
**Architecture ADR:** `ADR/0040-file-document-transition-current-schema-migration.md`  
**QA Decision:** Approved by Independent QA Reviewer

## 1. Baseline and authorization

Fresh GitHub verification established `origin/main = 09229cef3a4e31300edf31a904aa7a443fe80f4b`, the merge of PR #243. PR #243 is merged; final authorization head is `ee9368cc79430ee4e05c5896033b2a58c4b6d093`; base is T135 merge `ff6dbe02daf887489dfdabc3e30248491813d429`; merged at 2026-09-24T10:39:08Z.

Governance is `latestTaskDone=T135`, `latestTaskAuthorized=T136`, transitions empty. T136 is Authorized/not Done; T137+ is unauthorized. At architecture start there were no open PRs and no competing T136 architecture branch. The merged authorization branch `docs/t136-authorization` remains as historical branch evidence only. Alembic frontier is `9e6a4b2c8d1f`. Unresolved Required ADRs are `[10,11,12,15,16,17,20]`. ADR-0036/0037/0038/0039 are Proposed.

## 2. Evidence inspected

Architecture was derived from repository authority including T136 authorization, `PROJECT_WORKFLOW.md`, `PROJECT_STATE.json`, `IMPLEMENTATION_QUEUE.md`, the governed Domain Model & Functional Specification (Required ADR #10/#20, §11 and §24.8/24.9), ADR-0021, ADR-0027, ADR-0030, ADR-0039, current Matter/Document/DocumentVersion/FileStorageRecord models, FileStorage port and LocalFileStorage, document/storage migration `9a68ef4298ae`, document/storage tests, current migration frontier and current Matter application architecture.

Fresh ADR namespace inspection found ADR-0039 highest; ADR-0040 is the next valid identifier.

## 3. Current model and consumers

Matter is directly Organization-owned and still retains transitional `client_id` and `property_id`. Document has mandatory direct `matter_id`, type, title/status and audit/optimistic-lock metadata, but no direct Organization or File relationship. DocumentVersion belongs to Document, has immutable per-Document version numbering and points to FileStorageRecord. FileStorageRecord is blob metadata, not the business File.

No Document repository/service/API exists. Material consumers are the ORM/migration/schema tests and the DocumentVersion/storage chain. OCR depends on DocumentVersion, not Matter directly. The storage port is independent of business grouping.

## 4. Governing File architecture

ADR-0030 remains compatible: Matter 1→0..N File; File cannot exist without Matter; identity is distinct; lifecycle is existence-dependent but operationally separate.

ADR-0027 remains compatible: Matter-scoped transactional counter table, atomic upsert, counter and File insert in one transaction, committed numbers never reused, display format deferred.

No conflict requiring STOP was found.

## 5. Central decision

Selected strategy: **legacy Documents remain explicitly unfiled during compatibility; no automatic compatibility/default File is created.**

Current `Document→Matter` is retained as evidence. Future schema adds nullable `file_id` and mandatory direct `organization_id`. New Documents are File-canonical from first write. Existing Documents remain `matter_id set / file_id NULL` until an authorized operator explicitly assigns them to a genuine same-Matter File.

Automatic one-File-per-Matter was rejected because it fabricates a historical work-package assertion. Operator resolution before all new File use was rejected because it unnecessarily blocks clean/new business. Heuristic grouping is prohibited.

## 6. Target and authority

Target is `Organization→Matter→File→Document→DocumentVersion→FileStorageRecord`. File belongs to one Matter; Document belongs to one File in target state; no multi-File Document relationship. File may contain zero Documents.

During coexistence, `file_id` is canonical once present and `matter_id` is a derived compatibility shadow. For unresolved legacy rows, `matter_id` preserves Matter membership only. New Documents on all installation classes require File. MIGRATED does not imply File resolution.

## 7. Tenant/RLS/integrity

File and Document directly carry mandatory Organization. Direct Document ownership is necessary because legacy-unfiled Documents intentionally have no File. Both require application scoping plus forced Organization-GUC RLS. Same-Organization composite constraints bind File→Matter and Document→File/Matter. When both Document relationships exist, a composite database constraint must enforce File Matter equals Document compatibility Matter.

Missing/contradictory Organization evidence fails closed; no default tenant.

## 8. Numbering and migration

No synthetic File means migration consumes no File numbers. Every genuine File, including one explicitly created by an operator to resolve old Documents, consumes a normal ADR-0027 number. Failed creation rolls counter and File back together; committed numbers never return.

Migration phases are additive foundation; canonical new-write switch; explicit operator resolution; canonical-read/consumer migration; validation; separately authorized retirement. Each pre-retirement stage has an explicit compatibility state. Destructive `matter_id` retirement is separate.

## 9. Downgrade

Downgrade refuses once the previous schema cannot faithfully represent persisted File identity/grouping. It must never collapse multiple Files to Matter-only and call that reversible, erase explicit assignment, rewind counters, or fabricate File membership. Safe refusal/forward repair is preferred to lossy reversal.

## 10. Required ADR effects

ADR-0040 fully answers Required ADR #10's Document/File redirect mechanics and therefore proposes #10 resolution, **subject to independent QA and §3.1 governance closeout**. This architecture PR does not mutate the structured resolved-ADR ledger.

Required ADR #20 remains globally unresolved. T136 settles only its File/Document seam.

ADR-0039 remains Proposed and supplies compatible single-canonical-authority/compatibility-shadow discipline; it is not changed.

## 11. Boundaries

MatterProperty and classification/work-type are independent and not required for File/Document transition. No design for them was introduced. FileStorageRecord remains storage metadata. DocumentVersion remains structurally unchanged. GovernmentProcess/Workflow/Task attachment granularity and Document confidentiality/status vocabulary remain outside T136.

## 12. Future implementation decomposition

Unnumbered/unauthorized slices:
1. File + Document tenant/compatibility schema foundation and supported-revision advancement — Codex; migration/RLS/downgrade QA.
2. File application + concurrency-safe numbering — Codex; concurrency/rollback/tenant QA.
3. File-canonical Document/version application surface — Codex; storage/version/tenant QA.
4. Explicit legacy-unfiled resolution tooling — executor chosen after exact scope; Codex if admin/migration authority involved.
5. Compatibility consumer/read migration.
6. Separately authorized destructive `documents.matter_id` retirement — Codex with recovery evidence.

No successor/task number is selected.

## 13. Alpha effect

The architecture enables the minimum Alpha File/Document vertical slice without Enquiry/Quotation/MatterProperty/Gujarat-record/work-type redesign: genuine File under Matter with safe number, Document under File, immutable DocumentVersion backed by FileStorageRecord, Organization-scoped reads, and explicit preservation/resolution of legacy-unfiled Documents.

## 14. STOP-condition assessment

No STOP condition was triggered. Authorization is valid; ADR-0027/0030 do not conflict; safe non-fabricating legacy semantics exist; tenant/RLS can be defined; downgrade can safely refuse lossy reversal; File transition does not require MatterProperty or classification redesign; #20 need not resolve globally; no competing migration-frontier branch/PR was present at architecture start.

## 15. QA handoff

Independent QA must review the exact published architecture head, not this chat. Verify ADR-0040 against repository evidence and its own acceptance criteria, especially no synthetic File, direct Document tenant ownership, composite mismatch prevention, downgrade refusal, #10 resolution claim, #20 boundedness, and absence of implementation/schema/test changes.

**QA Decision:** Approved (see `docs/reviews/T136_QA_Review.md`)
