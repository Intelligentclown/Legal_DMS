# T106 Software Architect Report

**Task:** T106 — ADR-0033 Governance / Architecture Lifecycle: Party/Client Migration and
Organization-Boundary Reconciliation.

**Role:** Software Architect.

**Artifact under review:** `ADR/0033-party-client-migration-organization-boundary.md`.

**Status:** Architecture draft and self-assessment complete; independent QA is pending. This report
does not mark ADR-0033 accepted, authorize implementation, or perform governance closeout.

## 1. Authorization and Baseline

- T106 is authorized in `IMPLEMENTATION_QUEUE.md` with a narrow architecture/governance scope for
  ADR-0033 only. Its explicit exclusions include all Party, backend, frontend, schema, migration,
  Matter, Property, File, Finance, and Scheduling implementation; `create_user` Organization
  assignment; Organization onboarding/lifecycle; later tasks; and Governance Closeout.
- The authorization merged as `e6bcfef4f9a54c5328b5567460dbbdb280a5cfc2` (PR #176). Before
  drafting, `git merge-base --is-ancestor e6bcfef4f9a54c5328b5567460dbbdb280a5cfc2 HEAD` returned
  success on `docs/t106-adr-0033-party-client-migration`.
- `main` and `origin/main` were both verified at that merge before the branch was created.
- `PROJECT_STATE.json` records `latestTaskAuthorized: T106`, `latestTaskDone: T105`, unresolved
  Required ADRs `[10, 11, 12, 15, 16, 17, 20]`, and no in-progress transition. ADR-0033 does not
  claim to resolve Required ADR #20 in full, so this task makes no transition declaration and does
  not alter the ledger.

## 2. Repository and Governing Evidence Inspected

Read in full: `docs/prompts/SoftwareArchitect.md`, `AI_BOOTSTRAP.md`, `PROJECT_WORKFLOW.md`, the
T106 authorization row, `PROJECT_STATE.json`, `ADR/template.md`, ADRs `0021`, `0023`, `0024`,
`0028`, `0030`, `0031`, and `0032`, and the governed Domain Model & Functional Specification.

The live persistence model and migration history were rechecked in `client.py`, `matter.py`,
`property.py`, `financial.py`, `scheduling.py`, and the corresponding Alembic revisions. Repository-
wide searches rechecked Client models, direct `client_id` dependencies, permission seeds, tests,
current ERD/database documentation, and the absence of Client repositories, services, API routes,
schemas, production factories, and client-record seed data.

## 3. Current Client Dependency Graph

The canonical direct `clients.id` consumers are:

- `client_contacts.client_id`;
- mandatory `matters.client_id`;
- mandatory `property_owners.client_id`;
- nullable `appointments.client_id`;
- mandatory `invoices.client_id`; and
- mandatory `payments.client_id`.

The full inventory, including immutable historic migrations, `clients:*` permission grants and their
tests, model registration, transitive model-test setup, and ERD/schema/specification documentation,
is retained in ADR-0033 §2.4. The repository contains no `charges` or `expenses` model/table or
`client_id` dependency today; those future modules are constrained not to introduce one.

## 4. ADR-0033 Decision

ADR-0033 selects a staged, compatibility-first, backfill-before-cutover migration. Each legacy
Client becomes one Party, with the legacy UUID preserved only under an empty-Party preflight and a
durable mapping ledger. The UUID strategy is safe because both the current Client and governed Party
primary-key conventions are UUID/`uuid4`, not database sequences; unproven existing Party rows or
collisions abort rather than remap or overwrite data.

The ADR maps Client fields explicitly: ID, discriminator, universal name/contact/notes/address
fields, PAN, and Aadhaar are preserved; subtype semantics beyond the accepted Party discriminator
remain governed only to the degree ADR-0023 already establishes. `organization_id` is new and is
assigned through the reconciliation rule, not fabricated from a Client field.

## 5. Relationship and Migration Decisions

- `matters.client_id` is retired through `matter_parties`, with the legacy relationship backfilled as
  `role = 'client'`; it never becomes a long-lived `matters.party_id`.
- `property_owners`, `appointments`, `invoices`, and `payments` receive Party FK bridges, backfill,
  application cutover, and legacy-FK retirement. Required legacy links remain required; the existing
  nullable Appointment link remains nullable.
- `client_contacts` records ordinary contact facts and a free-text relationship label, not governed
  representative authority. Its records and fields are retained read-only through a Party-linked
  compatibility boundary; a separate Representative/contact decision is required before normalizing,
  replacing, or deleting them.
- Legacy `clients:*` authorization grants migrate to Party resource grants during the future
  implementation cutover; they are global authorization data, not Organization-scoped rows.

## 6. Organization Reconciliation and Tenant Boundary

The reconciliation anchor is `clients.id`. Deterministic evidence is limited to reconciled audit
users, directly linked already-resolved records with explicit FK paths, and a matching prior
reconciliation-ledger entry. One candidate Organization is deterministic; no candidate is
unmappable; multiple candidates or an inconsistent graph is ambiguous.

Ambiguous and unmappable sets require explicit, auditable operator mapping. They block Party/client
cutover. Creation date, name, contact details, geography, record order, and a single-Organization
assumption are expressly not evidence. The durable record must retain source fingerprint, evidence,
classification, selected Organization, migration-run identity, timestamp, and available operator or
process reference.

At final cutover, Parties, MatterParties, Matters, Properties, PropertyOwners, Appointments,
Invoices, Payments, and retained ClientContacts each carry `organization_id NOT NULL`, an FK to
`organizations`, ADR-0021 application-layer tenant scoping, and forced default-deny RLS. Tenant
ownership is never inferred solely through a join.

## 7. Composition Check

- **ADR-0021:** preserved. ADR-0033 applies its direct tenant-column, fail-closed, scoped-access and
  RLS requirements to every affected Party-side table.
- **ADR-0023:** preserved. Party remains the master record and Client remains a Matter role;
  `matter_parties` realizes that accepted direction without a Party subtype or a one-party shortcut.
- **ADR-0024:** preserved. Property remains independent of Matter, while the existing ownership
  history structure changes only its Client reference to Party.
- **ADR-0028:** preserved. Invoice and Payment remain real Finance entities; their Party redirect is
  performed without redesigning Finance or adding speculative Charge/Expense structures.
- **ADR-0030:** preserved. No File/Document relationship decision is changed; its later migration
  seam remains explicitly outside this ADR.
- **ADR-0031 and ADR-0032:** preserved. User-to-Organization cardinality is not reopened, and the
  explicit-reconciliation/fail-closed precedent is extended to legacy Client data without inventing
  onboarding, invitation, membership, or lifecycle policy.

## 8. Explicit Non-Scope and Owner Decisions

No Party implementation, data migration, backend/frontend work, model/table change, API route,
permission seeding, test implementation, or documentation synchronization was performed. No future
task was created or authorized. ADR-0033 remains `Proposed`.

No Project Owner policy decision is required to state this migration architecture. The actual
Organization mapping for an ambiguous deployment is an explicit operator-supplied migration input;
the architecture deliberately does not invent a business approver. Representative semantics remain a
separate future ADR, not an unresolved owner-policy question for this task.

## 9. Validation and QA Handoff

Before the PR is opened, this branch must pass the governance validator, its unit suite, and
`git diff --check`. The independent QA Reviewer must then inspect the actual remote PR head and
record one QA Decision before merge. This report contains no QA outcome and is not self-certifying.

## Reviewer Checklist

```text
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
□ Tests added
□ Existing tests pass
☑ Documentation updated
☑ ADR updated (if required)
□ AI_BOOTSTRAP updated (if required)
□ PROJECT_STATE updated (if required)
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

Tests were not added because this is an architecture-only task; existing application tests are not
re-run as a substitute for the required governance checks. `AI_BOOTSTRAP.md` and
`PROJECT_STATE.json` are correctly untouched: this task changes no standing process and has not
reached Governance Closeout.

## QA Decision

```text
□ Approved
□ Approved with comments
□ Rework required
```

The next required role is the independent QA Reviewer. This role must review the pushed PR head and
persist the QA Decision before the Project Manager may perform the pre-merge governance gate.
