# Legal\_DMS — Final Feature & Implementation Report

**Status:** Final engineering planning baseline

**Business baseline:** **Legal\_DMS — Consolidated Functional & Domain Architecture**

**Repository inspected:** `Intelligentclown/Legal_DMS`, `main`

**Repository inspection conclusion:** The repository is a strong architectural/database foundation, but the finalized business domain is **not yet implemented as an operational business application**.

The repository README describes the product as an Electron + React + FastAPI + PostgreSQL application and explicitly states that no business features existed at the documented baseline.  The current project-status documentation subsequently records authentication/authorization and frontend/Electron foundations as completed, while still stating that no Matter/Client/Property/Document Management business feature has been built.

---

# 1. Executive Summary

## 1.1 Current state

Legal\_DMS has reached the point where the **technical platform is mature enough to begin domain-feature implementation**, but the existing schema should **not** be treated as the final domain model.

The repository already provides:

-  Electron desktop shell; 
-  React + TypeScript + Vite frontend; 
-  FastAPI backend; 
-  PostgreSQL; 
-  SQLAlchemy 2.x; 
-  Alembic; 
-  testing infrastructure; 
-  authentication/authorization foundations; 
-  repository/service/framework infrastructure; 
-  audit infrastructure; 
-  workflow framework; 
-  file-storage abstraction; 
-  search foundation; 
-  background-job framework; 
-  a substantial database schema. 

Stage 2 created a 49-table production-oriented schema, later extended with `refresh_tokens`, but explicitly did **not** wire those tables into repositories, services or API routes.

The current repository therefore represents:

> **Platform + framework + preliminary database architecture + authentication/frontend foundation**

rather than:

> **Completed Legal\_DMS business application**.

---

## 1.2 Business discovery is complete

The business/domain discovery phase is now considered **complete**.

The finalized **Consolidated Functional & Domain Architecture** is the authoritative business baseline.

Future development must not casually reinterpret:

-  Matter; 
-  File; 
-  Party; 
-  Client; 
-  Property; 
-  Land; 
-  Revenue records; 
-  City Survey records; 
-  Scheme; 
-  Work Type; 
-  Classification; 
-  Government Process; 
-  Workflow; 
-  Activity; 
-  Audit; 
-  Financial concepts. 

Any change to those definitions requires an explicit architectural/business decision.

---

## 1.3 Primary architectural direction

Legal\_DMS should follow:

> **Standardized architecture + configurable business vocabulary/workflows.**

The system owns the core concepts and invariants.

Organizations configure operational vocabulary such as:

-  classifications; 
-  work types; 
-  document types; 
-  workflows; 
-  task types; 
-  government-process types; 
-  numbering rules; 
-  teams; 
-  confidentiality labels. 

---

## 1.4 Most important architectural change

The existing database model is **not fully aligned** with the finalized domain.

For example, the current `Matter` table contains a single `client_id` and a single optional `property_id`.

That conflicts with the finalized requirement that:

-  one Matter can have multiple parties/clients; 
-  one Matter can involve multiple properties; 
-  Party is reusable; 
-  Client is a Matter relationship; 
-  the same property can participate in unrelated Matters. 

Similarly, the existing `clients` model currently represents individual/organization client records directly.

Therefore the next stage must include a **domain-aware schema reconciliation**, not simply build APIs around the existing tables.

---

## 1.5 Recommended implementation strategy

The recommended sequence is:

```
```

```
Frozen Business Architecture
        ↓
Domain Model & Functional Specification
        ↓
Repository Gap Analysis
        ↓
Technical ADRs
        ↓
Database/API Contracts
        ↓
Vertical Slice 1
        ↓
Vertical Slice 2
        ↓
Vertical Slice 3
        ↓
Finance
        ↓
Advanced Security / Reporting / Integrations
```

Do **not** start by implementing every table independently.

---

## 1.6 Highest risks

The highest risks are:

1.  Treating the existing Stage-2 schema as already correct. 
2.  Treating `Client` as the equivalent of `Party`. 
3.  Retaining one-client/one-property Matter relationships. 
4.  Conflating Revenue Survey and City Survey. 
5.  Adding File functionality without introducing the finalized Matter/File distinction. 
6.  Allowing coding AIs to invent domain semantics. 
7.  Large cross-domain migrations without a staged compatibility strategy. 
8.  Excessive use of polymorphic relationships without carefully defining integrity boundaries. 
9.  Building financial functionality before commercial-domain semantics are specified. 
10.  Implementing Gujarat property records as UI fields instead of domain entities. 

---

# 2. Final Product Scope

| CapabilityPurposePriority |                                                   |          |
| ------------------------- | ------------------------------------------------- | -------- |
| Organization & tenancy    | Customer boundary and data isolation              | Critical |
| Identity/users            | System users and actors                           | Critical |
| Teams                     | Organizational work grouping                      | High     |
| Roles/permissions         | Authorization                                     | Critical |
| Party management          | Reusable people/legal entities                    | Critical |
| Party relationships       | Ownership, representation and other relationships | Critical |
| Representatives           | Persons authorized to act for Parties             | Critical |
| Property                  | Independent property identity                     | Critical |
| Land                      | Revenue-oriented land identity                    | Critical |
| Revenue records           | Gujarat Revenue property references               | Critical |
| City Survey records       | City Survey property references                   | Critical |
| TP/FP records             | Town Planning references                          | High     |
| Scheme                    | Development/project structure                     | High     |
| Enquiry                   | Prospective engagement                            | Critical |
| Quotation                 | Commercial proposal                               | Critical |
| Matter                    | Accepted engagement                               | Critical |
| Matter classifications    | Multi-dimensional Matter classification           | Critical |
| Work Types                | Actual professional work                          | Critical |
| File                      | Work package within Matter                        | Critical |
| File numbering            | Human-readable File identity                      | Critical |
| Documents                 | Legal records/evidence                            | Critical |
| Document versions         | Historical document integrity                     | Critical |
| Workflows                 | Internal process management                       | High     |
| Tasks                     | Action management                                 | High     |
| Government Processes      | External authority processing                     | High     |
| Communications            | Client/party interactions                         | High     |
| Activities                | Business history                                  | High     |
| Timeline                  | Unified historical view                           | High     |
| Commercial Scope          | Accepted commercial baseline                      | High     |
| Charges                   | Amounts owed/incurred                             | High     |
| Expenses                  | Costs incurred                                    | High     |
| Invoices                  | Billing                                           | High     |
| Payments                  | Money received                                    | High     |
| Payment allocation        | Allocation of payments                            | High     |
| Refunds                   | Money returned                                    | Medium   |
| Confidentiality           | Information sensitivity                           | High     |
| Audit                     | Immutable accountability                          | Critical |
| Reporting                 | Operational/business reporting                    | Medium   |
| Integrations              | External services                                 | Later    |

---

# 3. Final Domain Architecture

## 3.1 Core model

```
```

```
Organization
│
├── Users / Teams / Roles / Permissions
│
├── Parties
│
├── Properties / Lands / Schemes
│
├── Enquiries
│     └── Quotations
│
└── Matters
      ├── Parties / Clients / Representatives
      ├── Properties / Schemes
      ├── Classifications
      ├── Work Types
      ├── Files
      │    └── Documents
      ├── Workflows
      │    └── Tasks
      ├── Government Processes
      ├── Communications
      ├── Activities
      └── Financial Records
```

---

## 3.2 Layer A — Business Identity

```
```

```
Organization
Party
Property
Land
Scheme
```

These answer:

> Who and what exists?

---

## 3.3 Layer B — Engagement & Work

```
```

```
Enquiry
Matter
Work Type
File
Workflow
Task
Government Process
```

These answer:

> What work is being performed?

---

## 3.4 Layer C — Records & Evidence

```
```

```
Document
Document Version
Communication
Activity
Government Event
Financial Record
```

These answer:

> What happened and what evidence exists?

---

## 3.5 Layer D — Control

```
```

```
User
Team
Role
Permission
Audit
Security Policy
Organization Configuration
```

These answer:

> Who is allowed to do what, and who did what?

---

# 4. Authoritative Business Rules

These are **invariants**, not recommendations.

## Matter/File

1.  Matter is the accepted engagement. 
2.  Matter is created when the overall engagement is accepted. 
3.  Matter does not require a File to exist. 
4.  File is a work package within a Matter. 
5.  File cannot exist without a Matter. 
6.  File Number is assigned when the File/work package is created. 
7.  File Number must not be silently reused. 

## Party/Client

8.  Party is the reusable master record. 
9.  Client is a Matter relationship/status, not a master entity. 
10.  A Matter may have multiple parties/clients. 
11.  A Party may participate in many Matters. 
12.  A Party may appear in different roles in different Matters. 
13.  A Party may have multiple representatives. 
14.  Multiple representatives may participate in appointing/authorizing work. 

## Property

15.  Property is independent of Matter. 
16.  A Property may participate in multiple unrelated Matters. 
17.  Same Property does not imply same Matter. 
18.  Land and Property Unit must not be conflated. 

## Gujarat property records

19.  Revenue and City Survey are distinct record systems. 
20.  Revenue Block/Survey Number belongs to the Revenue/Land model. 
21.  City Survey Number may identify property units. 
22.  City Survey Number is not merely another Revenue Survey Number. 
23.  TP/FP is independently represented. 
24.  Other property-record systems must remain extensible. 

## Scheme

25.  Scheme is independent of Matter. 
26.  One Organization may own/control multiple Schemes. 
27.  Scheme structure is flexible. 
28.  Building/Block/Section are standard concepts, not mandatory hierarchy requirements. 

## Classification/work

29.  Matter may have multiple classifications. 
30.  Matter may have multiple Work Types. 
31.  Classification and Work Type are distinct concepts. 

## Workflow/government

32.  Internal workflow status is distinct from government status. 
33.  Government Process is its own domain concept. 
34.  Government events must retain historical information. 

## Finance

35.  Quotation, Commercial Scope, Charges, Invoice and Payment are separate concepts. 
36.  Professional fees must remain distinguishable from government/third-party money. 
37.  Payment allocation must be separately represented where required. 
38.  Historical financial information must not be silently overwritten. 

## History

39.  Communication, Task, Follow-up and Activity are distinct. 
40.  Timeline is a unified view, not a replacement for underlying records. 
41.  Audit is distinct from Activity. 
42.  Historical actions remain attributable to the original actor. 

## Security

43.  Organization is the tenant/security boundary. 
44.  Access must be permission-aware. 
45.  Matters, Files and Documents may require finer-grained access. 
46.  Historical security/audit information must not be silently altered. 

These rules should become automated tests and, where practical, database constraints.

---

# 5. Final Feature Catalogue

**Status terminology:**

- **Existing** — implemented and usable. 
- **Modify** — existing implementation requires domain-alignment changes. 
- **New** — not implemented as the finalized feature. 
- **Unknown** — repository inspection did not establish sufficient evidence. 

| FeatureDomainPurposeDependenciesPriorityConfigAuditRepository impactStatus |                  |                              |                       |          |              |         |                                           |                |
| -------------------------------------------------------------------------- | ---------------- | ---------------------------- | --------------------- | -------- | ------------ | ------- | ----------------------------------------- | -------------- |
| Organization                                                               | Identity         | Tenant boundary              | Platform              | Critical | Core         | Yes     | Tenant model/services                     | **Modify**     |
| Users                                                                      | Identity         | System actors                | Organization          | Critical | Core         | Yes     | Existing auth                             | **Modify**     |
| Teams                                                                      | Identity         | Work grouping                | Users                 | High     | Configurable | Yes     | New domain/UI                             | **New**        |
| Roles                                                                      | Security         | Access roles                 | Organization          | Critical | Configurable | Yes     | Existing RBAC                             | **Modify**     |
| Permissions                                                                | Security         | Authorization                | Roles                 | Critical | Core/config  | Yes     | Existing RBAC                             | **Modify**     |
| Party                                                                      | Party            | Reusable identity            | Organization          | Critical | Core         | Yes     | Replace/extend Client model               | **New/Modify** |
| PartyRelationship                                                          | Party            | Relationship graph           | Party                 | Critical | Core         | Yes     | New                                       | **New**        |
| Representative                                                             | Party            | Authorized persons           | Party                 | Critical | Core         | Yes     | New                                       | **New**        |
| Property                                                                   | Property         | Independent subject          | Organization          | Critical | Core         | Yes     | Existing property model                   | **Modify**     |
| Land                                                                       | Property         | Revenue land identity        | Geography             | Critical | Core         | Yes     | New abstraction                           | **New**        |
| RevenueRecord                                                              | Property records | Revenue identifiers          | Land                  | Critical | Core         | Yes     | New                                       | **New**        |
| CitySurveyRecord                                                           | Property records | City Survey identifiers      | Property              | Critical | Core         | Yes     | New                                       | **New**        |
| TP/FP Record                                                               | Property records | Planning references          | Property              | High     | Core         | Yes     | New                                       | **New**        |
| Scheme                                                                     | Property/project | Development structure        | Organization/Property | High     | Core         | Yes     | New                                       | **New**        |
| Enquiry                                                                    | Intake           | Potential engagement         | Party                 | Critical | Core         | Yes     | New                                       | **New**        |
| Quotation                                                                  | Intake/Finance   | Commercial proposal          | Enquiry               | Critical | Config       | Yes     | New                                       | **New**        |
| Matter                                                                     | Engagement       | Accepted engagement          | Enquiry/Party         | Critical | Core         | Yes     | Existing schema requires major change     | **Modify**     |
| MatterParty                                                                | Engagement       | Multi-party Matter           | Matter/Party          | Critical | Core         | Yes     | New relationship                          | **New**        |
| MatterProperty                                                             | Engagement       | Multi-property Matter        | Matter/Property       | Critical | Core         | Yes     | New relationship                          | **New**        |
| Classification                                                             | Matter           | Matter categorization        | Matter                | Critical | Config       | Yes     | Existing type concept insufficient        | **Modify/New** |
| Work Type                                                                  | Matter           | Work being performed         | Matter                | Critical | Config       | Yes     | New                                       | **New**        |
| File                                                                       | Work             | Work package                 | Matter                | Critical | Core         | Yes     | No finalized File entity evident          | **New**        |
| File Numbering                                                             | Work             | Human-readable File ID       | File/Organization     | Critical | Config       | Yes     | New                                       | **New**        |
| Document                                                                   | Records          | Legal evidence               | Matter/File           | Critical | Core         | Yes     | Existing documents need File relationship | **Modify**     |
| Document Version                                                           | Records          | Version history              | Document              | Critical | Core         | Yes     | Existing schema                           | **Modify**     |
| Workflow                                                                   | Work             | Internal process             | Matter/File           | High     | Config       | Yes     | Framework exists; domain wiring absent    | **Modify**     |
| Task                                                                       | Work             | Action tracking              | Matter/File           | High     | Config       | Yes     | Existing table, needs domain alignment    | **Modify**     |
| Government Process                                                         | Government       | External processing          | Property/Matter       | High     | Config       | Yes     | New                                       | **New**        |
| Communication                                                              | History          | Interaction history          | Matter/Party          | High     | Config       | Yes     | New                                       | **New**        |
| Activity                                                                   | History          | Business events              | Any domain            | High     | Core         | Yes     | Existing log foundation                   | **Modify**     |
| Timeline                                                                   | History          | Unified view                 | Activities etc.       | High     | Core         | Derived | New API/UI                                | **New**        |
| Commercial Scope                                                           | Finance          | Accepted commercial baseline | Quotation/Matter      | High     | Core         | Yes     | New                                       | **New**        |
| Charge                                                                     | Finance          | Amount owed/incurred         | Matter                | High     | Config       | Yes     | New                                       | **New**        |
| Expense                                                                    | Finance          | Cost tracking                | Matter/File           | High     | Config       | Yes     | New                                       | **New**        |
| Invoice                                                                    | Finance          | Billing                      | Matter/Scope          | High     | Core         | Yes     | Existing schema                           | **Modify**     |
| Payment                                                                    | Finance          | Money received               | Invoice               | High     | Core         | Yes     | Existing schema                           | **Modify**     |
| Payment Allocation                                                         | Finance          | Payment distribution         | Payment/Invoice       | High     | Core         | Yes     | New                                       | **New**        |
| Refund                                                                     | Finance          | Money returned               | Payment               | Medium   | Core         | Yes     | New                                       | **New**        |
| Confidentiality                                                            | Security         | Sensitivity                  | Matter/File/Document  | High     | Config       | Yes     | New                                       | **New**        |
| Audit                                                                      | Control          | Accountability               | All domains           | Critical | Core         | Yes     | Existing foundation/table                 | **Modify**     |
| Reporting                                                                  | Platform         | Business intelligence        | All domains           | Medium   | Config       | Yes     | New                                       | **New**        |
| Integrations                                                               | Platform         | External systems             | Relevant domains      | Later    | Config       | Yes     | Future                                    | **Later**      |

The existing schema confirms that Matter, Property, Client, Document, Financial and Task tables already exist, but they are currently schema-level foundations rather than completed business features.

---

# 6. Core vs Configurable

## 6.1 System/Core

These must remain architectural concepts:

-  Organization 
-  Party 
-  Property 
-  Land 
-  Matter 
-  File 
-  Document 
-  Document Version 
-  Workflow 
-  Task 
-  Communication 
-  Activity 
-  Government Process 
-  Quotation 
-  Commercial Scope 
-  Invoice 
-  Payment 
-  Audit 

Organizations may configure their attributes and workflows, but cannot redefine what these concepts fundamentally mean.

---

## 6.2 Configurable

Organizations should configure:

-  Matter Classifications; 
-  Work Types; 
-  Document Types; 
-  Task Types; 
-  Activity Types; 
-  Expense Categories; 
-  Government Process Types; 
-  Workflow Templates; 
-  Numbering rules; 
-  Teams; 
-  Confidentiality labels; 
-  operational statuses where not architectural. 

The repository already uses lookup tables rather than native PostgreSQL enums, which is compatible with this direction.

---

# 7. Implementation Roadmap

## Phase 1 — Platform Foundation

### Objective

Make the existing platform a reliable multi-tenant business foundation.

### Features

-  Organization; 
-  tenant isolation; 
-  users; 
-  teams; 
-  roles; 
-  permissions; 
-  audit foundation. 

### Repository changes

The repository already has authentication/authorization foundations and role/permission schema. The required work is primarily **domain completion and tenant-aware authorization**, not rebuilding authentication.

### Testing

-  tenant isolation; 
-  role permissions; 
-  unauthorized access; 
-  audit actor attribution. 

### Exit criteria

A user can securely operate within one Organization and cannot access another Organization's data.

### PR strategy

**2–3 PRs**, not one large PR.

---

# Phase 2 — Master Data

## Objective

Create the reusable business identity graph.

### Features

```
```

```
Party
PartyRelationship
Representative
Property
Land
Scheme
RevenueRecord
CitySurveyRecord
TP/FP
PropertyRecordReference
```

### Important repository change

The current `Client` model must not simply be renamed to `Party`.

The current model is explicitly limited to:

```
```

```
individual
organization
```

and contains client-specific fields.

The finalized architecture requires a reusable Party abstraction capable of representing participants independent of Matter role.

### Exit criteria

The system can represent:

-  individual; 
-  company; 
-  multiple representatives; 
-  multiple owners; 
-  land; 
-  property unit; 
-  Revenue record; 
-  City Survey record; 
-  TP/FP references; 
-  flexible Scheme structure. 

### PR strategy

**4–5 PRs**.

---

# Phase 3 — Intake & Engagement

## Objective

Implement the business lifecycle from prospective work to accepted engagement.

```
```

```
Enquiry
 ↓
Quotation
 ↓
Acceptance
 ↓
Matter
```

### Critical requirement

Matter must be created at acceptance even when:

```
```

```
File count = 0
```

### Matter changes

The current Matter schema contains:

```
```

```
client_id
property_id
matter_type_id
```

as direct relationships.

These must be replaced/supplemented by relationship entities supporting:

```
```

```
MatterParty
MatterProperty
MatterClassification
MatterWorkType
```

### Exit criteria

An accepted engagement creates a Matter without requiring a File.

---

# Phase 4 — Work Management

## Objective

Introduce the actual work-package model.

### Features

-  File; 
-  File Number; 
-  numbering sequence; 
-  Workflow; 
-  Tasks; 
-  Government Processes. 

### Core invariant

```
```

```
Matter
├── File A
├── File B
└── File C
```

A Matter may have:

```
```

```
0 Files
```

### Exit criteria

File creation is independently controlled and assigns a unique File Number at creation.

### PR strategy

**3–4 PRs.**

---

# Phase 5 — Document Management

## Objective

Make Documents operational.

### Features

-  Document; 
-  Document Type; 
-  Document Version; 
-  File relationship; 
-  document security; 
-  storage; 
-  document lifecycle. 

The repository already has document/version/storage schema and a file-storage abstraction, and the database deliberately stores metadata rather than document content.

### Required change

The finalized domain requires:

```
```

```
Matter
  ↓
File
  ↓
Document
  ↓
DocumentVersion
```

rather than simply:

```
```

```
Matter
  ↓
Document
```

The current schema directly links Documents to Matter.

### PR strategy

**3 PRs.**

---

# Phase 6 — Communication & History

## Objective

Provide a complete Matter history.

### Features

-  Communication; 
-  participants; 
-  Activity; 
-  Follow-up; 
-  Timeline. 

### Exit criteria

The Matter timeline can show:

```
```

```
Task
Document
Communication
Government Event
Payment
Status Change
Activity
```

without collapsing those into one underlying entity.

### PR strategy

**2–3 PRs.**

---

# Phase 7 — Finance

## Objective

Implement commercial and financial integrity.

```
```

```
Quotation
 ↓
Commercial Scope
 ↓
Charges
 ↓
Invoice
 ↓
Payment
 ↓
Payment Allocation
 ↓
Refund
```

### Exit criteria

The system can distinguish:

```
```

```
Professional Fee
Government Fee
Third-party money
Expense
Payment
Refund
```

### PR strategy

**3–4 PRs.**

Finance should not be implemented as a generic "amount" field attached to Matter.

---

# Phase 8 — Advanced Security & Platform

### Features

-  Matter-level access; 
-  File-level access; 
-  Document sensitivity; 
-  external sharing; 
-  advanced audit; 
-  reporting; 
-  integrations. 

### Strategy

Do not implement until the core domain is stable.

---

# 8. Vertical Slice Strategy

## Vertical Slice 1 — Engagement-to-Document

```
```

```
Organization
    ↓
Party
    ↓
Property
    ↓
Enquiry
    ↓
Quotation
    ↓
Matter
    ↓
File
    ↓
Document
```

plus:

```
```

```
User
Role
Permission
Audit
```

### Purpose

This validates the most important business lifecycle.

---

## Vertical Slice 2 — Complex Matter

```
```

```
Matter
├── Multiple Parties
├── Multiple Clients
├── Multiple Representatives
├── Multiple Properties
├── Classifications
├── Work Types
└── Multiple Files
```

This slice is particularly important because it exposes the limitations of the existing single-client/single-property schema.

---

## Vertical Slice 3 — Operational Work

```
```

```
Workflow
Task
Government Process
Communication
Activity
Timeline
```

---

## Vertical Slice 4 — Commercial

```
```

```
Commercial Scope
Charges
Expenses
Invoice
Payment
Allocation
Refund
```

---

## Vertical Slice 5 — Advanced Platform

```
```

```
Advanced Security
Confidentiality
External Sharing
Advanced Audit
Reporting
Integrations
```

### Why vertical slices?

Because each slice proves a complete business path.

Building 15 isolated database entities first creates a false sense of progress: tables exist, but no real business workflow has been validated.

---

# 9. Existing Repository Impact

## 9.1 Repository architecture

Confirmed:

```
```

```
Electron
React + TypeScript + Vite
FastAPI
PostgreSQL
SQLAlchemy 2.x
Alembic
Pytest
Vitest / RTL
```

This is explicitly documented by the repository.

---

## 9.2 Existing framework

The repository already contains:

-  Repository abstraction; 
-  Service foundation; 
-  validation; 
-  pagination/filtering/search; 
-  command bus; 
-  query bus; 
-  transaction pipeline; 
-  event system; 
-  background-job framework; 
-  file storage; 
-  notification framework; 
-  authentication; 
-  authorization; 
-  audit logging; 
-  search; 
-  workflow engine; 
-  plugin architecture. 

These should be **used**, not independently recreated by every business module.

---

## 9.3 Existing database

The repository has 49 original business-oriented schema tables plus `refresh_tokens`.

The database currently includes:

-  users; 
-  roles; 
-  permissions; 
-  geography; 
-  clients; 
-  properties; 
-  matters; 
-  workflows; 
-  documents; 
-  financial tables; 
-  tasks; 
-  activity/audit; 
-  system/config; 
-  OCR; 
-  QR; 
-  backups; 
-  AI/plugin placeholders. 

However:

> **Existing table presence does not equal finalized feature implementation.**

---

## 9.4 Existing vs final architecture mapping

| Final conceptCurrent repositoryAction |                                               |                                    |
| ------------------------------------- | --------------------------------------------- | ---------------------------------- |
| Organization                          | No clearly established business tenant entity | **New**                            |
| User                                  | Existing                                      | Modify for Organization context    |
| Team                                  | Not established                               | New                                |
| Role                                  | Existing                                      | Keep/modify                        |
| Permission                            | Existing                                      | Keep/modify                        |
| Party                                 | `clients`                                     | **Major refactor/new abstraction** |
| Client                                | `clients`                                     | Replace as master concept          |
| Representative                        | `client_contacts` partially related           | Replace/extend                     |
| Party Relationship                    | Not present                                   | New                                |
| Property                              | Existing                                      | Major modification                 |
| Land                                  | Not distinct                                  | New                                |
| Revenue Record                        | Generic `survey_number` in Property           | Major redesign                     |
| City Survey                           | Not distinct                                  | New                                |
| TP/FP                                 | Not identified                                | New                                |
| Scheme                                | Not identified                                | New                                |
| Enquiry                               | Not identified                                | New                                |
| Quotation                             | Not identified                                | New                                |
| Matter                                | Existing                                      | Major modification                 |
| MatterParty                           | Not present                                   | New                                |
| MatterProperty                        | Not present                                   | New                                |
| Classification                        | `matter_types`                                | Redesign                           |
| Work Type                             | Not present                                   | New                                |
| File                                  | No finalized File entity identified           | New                                |
| File Number                           | No finalized File numbering identified        | New                                |
| Document                              | Existing                                      | Modify                             |
| Document Version                      | Existing                                      | Modify                             |
| Workflow                              | Framework + schema                            | Modify/wire                        |
| Task                                  | Existing                                      | Modify                             |
| Government Process                    | Not identified                                | New                                |
| Communication                         | Not identified as finalized entity            | New                                |
| Activity                              | Existing activity log                         | Modify                             |
| Timeline                              | Not finalized as operational feature          | New                                |
| Commercial Scope                      | Not identified                                | New                                |
| Charges                               | Not identified as finalized entity            | New                                |
| Expense                               | Not identified                                | New                                |
| Invoice                               | Existing                                      | Modify                             |
| Payment                               | Existing                                      | Modify                             |
| Payment Allocation                    | Not identified                                | New                                |
| Refund                                | Not identified                                | New                                |
| Confidentiality                       | Not identified                                | New                                |
| Audit                                 | Existing foundation/table                     | Modify                             |

The most important conclusion is:

> **The current schema is a useful starting point, not the final schema.**

---

# 10. Repository Change Assessment

## A. Database

Required changes include:

### New entities

At minimum:

```
```

```
organizations
teams
parties
party_relationships
representatives / party-authorizations
lands
schemes
scheme_nodes/structure
property_record_references
revenue_records
city_survey_records
tp_records
fp_records
enquiries
quotations
matter_parties
matter_properties
matter_classifications
matter_work_types
files
file_number_sequences
government_processes
government_events
communications
commercial_scopes
charges
expenses
payment_allocations
refunds
confidentiality/access records
```

Exact table design must wait for the formal specification.

### Existing entities requiring review

```
```

```
clients
properties
matters
documents
document_versions
workflow_*
tasks
invoices
payments
activity_logs
audit_logs
```

---

## B. Backend

Required:

-  domain services; 
-  repositories; 
-  application commands; 
-  application queries; 
-  API contracts; 
-  validation; 
-  authorization; 
-  audit; 
-  event publishing; 
-  workflow integration; 
-  numbering service; 
-  financial integrity services. 

The existing generic repository infrastructure should be reused.

---

## C. Frontend

Required application surfaces:

```
```

```
Organization
Party
Property
Scheme
Enquiry
Quotation
Matter
File
Document
Workflow
Government Process
Communication
Timeline
Finance
Security
```

The UI should be generated from the domain model, not used to define the domain.

---

## D. Infrastructure

Required later:

-  document storage; 
-  search indexing; 
-  background jobs; 
-  notification delivery; 
-  backups; 
-  observability; 
-  integrations. 

The existing file-storage abstraction is reusable. The database currently stores metadata rather than document content.

---

## E. Testing

Required:

-  unit; 
-  integration; 
-  API; 
-  authorization; 
-  tenant isolation; 
-  migration; 
-  property records; 
-  workflow; 
-  finance; 
-  audit; 
-  document versioning. 

---

# 11. Migration & Backward Compatibility

## 11.1 Migration is required

The finalized architecture materially differs from the current schema.

The biggest migration areas are:

### Client → Party

Current:

```
```

```
clients
```

Final:

```
```

```
parties
```

A direct rename is insufficient.

---

### Matter relationships

Current:

```
```

```
Matter
├── client_id
└── property_id
```

Final:

```
```

```
Matter
├── MatterParty[]
├── MatterProperty[]
├── MatterClassification[]
└── MatterWorkType[]
```

The current direct relationships are confirmed in the ORM model.

---

### Property identifiers

Current Property includes a generic:

```
```

```
survey_number
sub_division_number
```

and property type.

That is insufficient for:

```
```

```
Revenue
City Survey
TP
FP
other property records
```

---

### Documents

Current:

```
```

```
Matter → Document
```

Final:

```
```

```
Matter → File → Document
```

The existing ERD explicitly shows `matters ||--o{ documents`.

---

## 11.2 Migration approach

Recommended:

```
```

```
Existing schema
      ↓
Compatibility migration
      ↓
New domain structures
      ↓
Data backfill
      ↓
Validation/reconciliation
      ↓
Application cutover
      ↓
Retire obsolete fields
```

Do **not** immediately delete:

```
```

```
client_id
property_id
survey_number
```

until migration and reconciliation are proven.

---

## 11.3 Important limitation

Because Stage 2 explicitly created schema without business data/services, the current repository may contain little or no production business data.

Therefore migration complexity should be assessed against the actual target database before implementation.

---

# 12. Remaining Engineering Decisions

These are **not business ambiguities**. They are implementation decisions.

| DecisionClassification             |                                                          |
| ---------------------------------- | -------------------------------------------------------- |
| Exact Party subtype strategy       | Must decide before implementation                        |
| Organization/tenant representation | Must decide before implementation                        |
| Property vs Property Unit          | Must decide before implementation                        |
| Land representation                | Must decide before implementation                        |
| Scheme hierarchy storage           | Must decide before implementation                        |
| Property Record Reference strategy | Must decide before implementation                        |
| Revenue record structure           | Must decide before implementation                        |
| City Survey record structure       | Must decide before implementation                        |
| File numbering algorithm           | Must decide before implementation                        |
| Numbering concurrency strategy     | Must decide before implementation                        |
| UUID strategy                      | Already directionally established; confirm               |
| Document storage provider strategy | Can decide during implementation                         |
| Document version storage           | Must decide before Document implementation               |
| Timeline implementation            | Can decide during implementation                         |
| Workflow implementation            | Can decide during implementation                         |
| Authorization granularity          | Must decide before security implementation               |
| Audit storage                      | Existing direction; confirm before domain implementation |
| Financial ledger boundary          | Must decide before Finance                               |
| Configuration versioning           | Can decide during implementation                         |
| Reporting architecture             | Can be deferred                                          |
| Integration architecture           | Can be deferred                                          |

The repository already uses UUID primary keys consistently, and its documented schema conventions specify UUIDs and timezone-aware timestamps.

---

# 13. Risk Register

| RiskProbabilityImpactSeverityMitigationDetection |        |          |    |                                   |                     |
| ------------------------------------------------ | ------ | -------- | -- | --------------------------------- | ------------------- |
| Client/Party conflation                          | High   | Critical | 🔴 | Formal Party model                | Domain tests        |
| Organization/Party conflation                    | Medium | Critical | 🔴 | Explicit tenant model             | Architecture review |
| Property tied directly to Matter                 | High   | High     | 🔴 | MatterProperty relation           | Schema tests        |
| One-client Matter assumption                     | High   | Critical | 🔴 | MatterParty                       | Integration tests   |
| One-property Matter assumption                   | High   | High     | 🔴 | MatterProperty                    | Integration tests   |
| Revenue/City Survey conflation                   | High   | Critical | 🔴 | Separate bounded records          | Domain tests        |
| Land/unit conflation                             | High   | High     | 🔴 | Separate concepts                 | Property tests      |
| Scheme over-specialization                       | Medium | High     | 🟠 | Flexible hierarchy                | Architecture review |
| Hardcoded classifications                        | High   | Medium   | 🟠 | Configurable vocabulary           | Configuration tests |
| File/Matter confusion                            | High   | Critical | 🔴 | Explicit lifecycle rules          | Invariant tests     |
| File-number collisions                           | Medium | High     | 🟠 | DB sequence/locking strategy      | Concurrency tests   |
| Migration loss                                   | Medium | Critical | 🔴 | Staged migration + reconciliation | Migration tests     |
| Tenant leakage                                   | Medium | Critical | 🔴 | Organization scoping everywhere   | Security tests      |
| Authorization leakage                            | Medium | Critical | 🔴 | Policy tests                      | Negative tests      |
| Document history loss                            | Medium | Critical | 🔴 | Immutable versions                | Version tests       |
| Audit gaps                                       | Medium | High     | 🟠 | Mandatory audit service           | Audit tests         |
| Generic polymorphism overuse                     | Medium | High     | 🟠 | Use only where justified          | Architecture review |
| Excessive configurability                        | Medium | Medium   | 🟡 | Core/config boundary              | Product review      |
| Finance model drift                              | Medium | Critical | 🔴 | Separate commercial entities      | Financial tests     |
| Giant PRs                                        | High   | High     | 🔴 | Domain-bounded PRs                | PR review           |
| Coding AI invents semantics                      | High   | Critical | 🔴 | Frozen spec + role prompts        | QA/domain review    |
| Architecture drift                               | Medium | High     | 🟠 | ADR + architecture checks         | Periodic review     |
| UI-driven domain design                          | Medium | High     | 🟠 | Domain-first workflow             | Architecture review |

---

# 14. Explicitly Deferred Scope

The following remain deliberately postponed:

1.  Complex accounting. 
2.  Full ERP. 
3.  Elaborate CRM. 
4.  Automated legal advice. 
5.  Complicated joint-development ownership. 
6.  Universal government API integrations. 
7.  Excessively specialized property rules. 
8.  AI document interpretation as a core dependency. 

The architecture should remain extensible for these features.

They must **not** become dependencies of the core Matter/File/Property architecture.

---

# 15. Domain Model & Functional Specification Requirements

This is the **next major deliverable**.

Before substantial business coding begins, create:

> **Legal\_DMS Domain Model & Functional Specification**

Every entity must specify:

### Identity

-  purpose; 
-  identifier; 
-  ownership/tenant; 
-  lifecycle. 

### Fields

-  field name; 
-  data type; 
-  required/optional; 
-  validation; 
-  default; 
-  mutability. 

### Relationships

-  target; 
-  cardinality; 
-  ownership; 
-  cascade; 
-  lifecycle dependency. 

### States

-  valid states; 
-  transitions; 
-  terminal states. 

### Security

-  who can view; 
-  who can create; 
-  who can edit; 
-  who can archive; 
-  who can restore. 

### Audit

-  creation; 
-  modification; 
-  status changes; 
-  relationship changes; 
-  financial changes; 
-  access-sensitive events. 

### Configuration

-  system-controlled; 
-  organization-controlled; 
-  configurable; 
-  immutable. 

### Search

-  searchable fields; 
-  filters; 
-  indexes; 
-  full-text requirements. 

### Reporting

-  required reporting dimensions. 

### API

-  commands; 
-  queries; 
-  mutations; 
-  responses; 
-  validation errors. 

---

# 16. API & Database Planning

The correct derivation chain is:

```
```

```
Business Architecture
        ↓
Domain Model & Functional Specification
        ↓
Domain Relationships
        ↓
Database Model
        ↓
API Contracts
        ↓
Application Services
        ↓
UI
```

Do **not** derive database tables directly from the conceptual entity list.

For example:

```
```

```
Party
```

does not automatically mean:

```
```

```
CREATE TABLE parties (...)
```

until we have resolved:

-  subtype strategy; 
-  relationships; 
-  organization ownership; 
-  identity uniqueness; 
-  representative model; 
-  historical identity; 
-  archival behavior. 

Likewise:

```
```

```
Property
```

must be specified before deciding whether:

```
```

```
Property
Land
PropertyUnit
RevenueRecord
CitySurveyRecord
```

are separate tables, joined structures, or another arrangement.

---

# 17. Testing Strategy

## 17.1 Domain tests

Every invariant should have automated coverage.

---

## 17.2 Tenant tests

Test:

```
```

```
Organization A cannot access Organization B
```

through:

-  API; 
-  repositories; 
-  background jobs; 
-  documents; 
-  searches; 
-  reporting. 

---

## 17.3 Relationship tests

Must cover:

```
```

```
1 Matter → many Parties
1 Matter → many Properties
1 Party → many Matters
1 Party → many Representatives
1 Matter → many Work Types
1 Matter → many Classifications
1 Matter → many Files
```

---

## 17.4 Property-record tests

Test independently:

```
```

```
Revenue
City Survey
TP
FP
```

and combinations.

---

## 17.5 File tests

Mandatory:

```
```

```
File without Matter → reject
Matter without File → allow
File creation → assigns File Number
Concurrent File creation → no duplicate
Deleted/archived File → number not silently reused
```

---

## 17.6 Document tests

Test:

-  multiple versions; 
-  immutable historical versions; 
-  version ordering; 
-  status transitions; 
-  storage integrity; 
-  security; 
-  audit. 

---

## 17.7 Workflow tests

Prove:

```
```

```
Internal workflow state
```

does not accidentally overwrite:

```
```

```
Government status.
```

---

## 17.8 Financial tests

Test the entire lifecycle:

```
```

```
Quotation
Commercial Scope
Charge
Invoice
Payment
Allocation
Refund
```

including partial payments and historical integrity.

---

## 17.9 Audit tests

Every sensitive change must preserve:

```
```

```
actor
timestamp
entity
action
before/after or equivalent change information
```

---

# 18. Development Task Decomposition

Recommended implementation units:

## Task A — Organization & Identity Foundation

### Objective

Complete tenant-aware identity/security foundation.

### Scope

-  Organization; 
-  user membership; 
-  teams; 
-  roles; 
-  permissions; 
-  tenant enforcement. 

### Acceptance

No cross-organization access.

### PR

2–3 PRs.

---

## Task B — Party Domain

### Scope

-  Party; 
-  Party relationship; 
-  representative; 
-  Party roles. 

### Acceptance

Same Party can participate in many Matters with different roles.

### PR

2–3 PRs.

---

## Task C — Property & Land Domain

### Scope

-  Property; 
-  Land; 
-  Property Unit if approved; 
-  ownership. 

### Acceptance

Land/property distinctions work correctly.

### PR

2–3 PRs.

---

## Task D — Gujarat Property Records

### Scope

-  Revenue; 
-  City Survey; 
-  TP/FP; 
-  property record references. 

### Acceptance

Revenue Survey and City Survey cannot be accidentally conflated.

### PR

2–3 PRs.

---

## Task E — Scheme Domain

### Scope

-  Scheme; 
-  organization relationship; 
-  flexible structure; 
-  Building/Block/Section/Unit concepts. 

### PR

1–2 PRs.

---

## Task F — Enquiry & Quotation

### Scope

-  Enquiry; 
-  quotation; 
-  acceptance; 
-  rejection; 
-  commercial proposal. 

### PR

2 PRs.

---

## Task G — Matter Domain

### Scope

-  Matter; 
-  MatterParty; 
-  MatterProperty; 
-  classification; 
-  Work Type; 
-  Matter lifecycle. 

### Critical acceptance

Accepted engagement creates Matter before File.

### PR

2–3 PRs.

---

## Task H — File & Numbering

### Scope

-  File; 
-  Matter/File relation; 
-  File Number; 
-  concurrency-safe numbering. 

### PR

2 PRs.

---

## Task I — Document Management

### Scope

-  Document; 
-  Document Type; 
-  versions; 
-  storage; 
-  security. 

### PR

2–3 PRs.

---

## Task J — Workflow & Tasks

### Scope

-  workflow definitions; 
-  workflow instances; 
-  stages; 
-  tasks; 
-  assignment. 

### PR

2 PRs.

---

## Task K — Government Processes

### Scope

-  government process; 
-  authority; 
-  office; 
-  reference; 
-  events; 
-  status. 

### PR

2 PRs.

---

## Task L — Communications & Timeline

### Scope

-  communication; 
-  participants; 
-  activity; 
-  follow-up; 
-  timeline. 

### PR

2 PRs.

---

## Task M — Commercial & Finance

### Scope

-  Commercial Scope; 
-  Charge; 
-  Expense; 
-  Invoice; 
-  Payment; 
-  Allocation; 
-  Refund. 

### PR

3–4 PRs.

---

## Task N — Advanced Security

### Scope

-  Matter access; 
-  File access; 
-  document sensitivity; 
-  external sharing; 
-  advanced audit. 

### PR

2–3 PRs.

---

## Task O — Reporting & Integrations

### Scope

-  reports; 
-  dashboards; 
-  integrations. 

### PR

several independently scoped PRs.

---

# 19. PR Strategy

Each PR should represent:

> **One coherent architectural purpose.**

### Good

```
```

```
Implement MatterParty relationship
```

### Bad

```
```

```
Implement Matter + Property + Documents + Finance + UI
```

Each PR should contain:

-  implementation; 
-  migrations; 
-  tests; 
-  documentation; 
-  relevant ADR; 
-  acceptance evidence. 

Avoid large "everything for Matter" PRs.

---

## Recommended PR grouping

| AreaRecommended PR count |                          |
| ------------------------ | ------------------------ |
| Organization/identity    | 2–3                      |
| Party                    | 2–3                      |
| Property                 | 2–3                      |
| Gujarat records          | 2–3                      |
| Scheme                   | 1–2                      |
| Enquiry/Quotation        | 2                        |
| Matter                   | 2–3                      |
| File                     | 2                        |
| Documents                | 2–3                      |
| Workflow                 | 2                        |
| Government               | 2                        |
| Communication            | 2                        |
| Finance                  | 3–4                      |
| Security                 | 2–3                      |
| Reporting                | Multiple                 |
| Integrations             | Separate per integration |

This keeps reviews manageable and makes rollback safer.

---

# 20. Definition of Done

A feature is **not complete** merely because the UI works.

A feature is complete only when:

-  business rules implemented; 
-  domain validation implemented; 
-  database constraints implemented where appropriate; 
-  API validation implemented; 
-  authorization implemented; 
-  tenant isolation verified; 
-  audit implemented; 
-  tests added; 
-  migration tested; 
-  existing regression tests pass; 
-  documentation updated; 
-  relevant ADR updated; 
-  no unresolved critical security issue; 
-  no silent historical mutation; 
-  QA independently verifies the acceptance criteria. 

---

# 21. Required ADRs

**Terminology note (added during this correction pass):** the numbers 1–20 below are **planning-
list positions in this document only** — they identify an item's place in *this list*, nothing
more. They are **not** repository ADR filename numbers. The repository's actual ADRs already run
`ADR/0001-...` through `ADR/0020-...` (twenty already-written, already-decided files, covering
unrelated earlier topics — e.g. the existing `ADR/0018-authentication-authorization-architecture.md`
is about JWT/password-hashing/CLI-bootstrap and has no relationship to this list's item 18,
"Authorization architecture," despite the coincidentally matching number). When any item below is
actually written up as a real ADR, it will receive whatever the **next available** repository ADR
number is at that time (most likely `ADR/0021-...` onward, in whatever order the items are
actually tackled) — not necessarily this list's position number. Wherever this specification says
"Required ADR #N," read it strictly as "planning-list item N below," never as a repository ADR
file reference.

The following should become formal ADRs:

1.  Organization as tenant boundary. 
2.  Party vs Client. 
3.  Property vs Matter independence. 
4.  Land vs Property Unit. 
5.  Revenue vs City Survey. 
6.  Property Record Reference architecture. 
7.  Flexible Scheme hierarchy (**must also resolve the TP/FP-Record ↔ Scheme conceptual
    boundary** — whether a Town Planning Scheme is this specification's Scheme, a TP/FP-Record-only
    concept, or both; see Part II §24.4's TP/FP Record entry — assigned here, not to item 6, since
    it is a question of what "Scheme" itself means, not of the Property-record-linking mechanism
    item 6 governs). 
8.  Matter vs File lifecycle. 
9.  File numbering strategy. 
10.  Document/File relationship. 
11.  Document/version architecture. 
12.  Workflow vs Government Status. 
13.  Financial boundary. 
14.  Activity vs Audit. 
15.  Core vs configurable vocabulary. 
16.  UUID vs human-readable identifiers. 
17.  Soft deletion/history. 
18.  Authorization architecture. 
19.  Tenant isolation enforcement. 
20.  Migration strategy from the current schema. 

The repository already has an established ADR-driven governance culture, so these decisions should follow the existing project process rather than being left only in prompts or chat history. The repository documentation explicitly maintains architecture decisions under `ADR/`.

---

# 22. Recommended Next Steps

The recommended sequence is now definitive:

```
```

```
1. Freeze business baseline
        ↓
2. Inspect current repository
        ↓
3. Produce Domain Model & Functional Specification
        ↓
4. Identify repository/domain gaps
        ↓
5. Create ADRs for major technical decisions
        ↓
6. Define database/API contracts
        ↓
7. Implement dependency-ordered vertical slices
        ↓
8. Validate each slice
        ↓
9. Perform integration/regression testing
        ↓
10. Continue roadmap phases
```

## Immediate next deliverable

The next document should be:

> **Legal\_DMS — Domain Model & Functional Specification**

It should be written against **both**:

1.  the frozen business architecture; and 
2.  the inspected current repository. 

That document should explicitly mark every field/relationship as:

```
```

```
Confirmed Business Rule
Engineering Decision
Repository Constraint
Implementation Choice
Deferred
```

This will prevent a development AI from accidentally treating an old database design as a business requirement.

---

# 23. Final Executive Decision

## What is now finalized?

The **business/domain architecture is finalized**.

In particular, the following are frozen:

```
```

```
Organization
Party
Client-as-relationship
Representative
Property
Land
Revenue Records
City Survey Records
TP/FP
Scheme
Enquiry
Quotation
Matter
Classification
Work Type
File
Document
Workflow
Government Process
Communication
Activity
Timeline
Commercial Scope
Charges
Expenses
Invoice
Payment
Audit
```

along with the business invariants listed above (§4 numbers **46** rules in total, 1–46 —
independently recounted directly against §4 during this correction pass; the "20" this line
previously stated was a stale/inaccurate summary count from an earlier draft, corrected here as a
terminology fix only. No narrower "core 20" subset is designated anywhere in this document, and
none is invented here — all 46 numbered rules in §4 carry equal authority as Confirmed Business
Rules; none is demoted or promoted by this correction).

---

## What remains to be specified?

The remaining work is primarily **engineering specification**, especially:

-  exact Party model; 
-  exact Property/Land/Unit model; 
-  exact Scheme hierarchy; 
-  exact Gujarat record structures; 
-  Property Record Reference strategy; 
-  File numbering implementation; 
-  document storage/version architecture; 
-  authorization granularity; 
-  financial model boundary; 
-  API contracts; 
-  database derivation; 
-  migration strategy. 

These decisions must be made **without reopening the business semantics**.

---

## What must change in the current repository?

The current repository must evolve significantly in:

-  Client → Party architecture; 
-  Matter relationships; 
-  Property model; 
-  Gujarat property records; 
-  Scheme; 
-  Enquiry/Quotation; 
-  Matter classifications; 
-  Work Types; 
-  File; 
-  File numbering; 
-  Document/File relationship; 
-  Government Process; 
-  Communications; 
-  Commercial Scope; 
-  Charges; 
-  Expenses; 
-  Payment Allocation; 
-  Refunds; 
-  tenant-aware Organization model; 
-  fine-grained security. 

The existing Stage-2 schema is a useful foundation but is **not the final business schema**. The repository documentation itself describes those tables as schema without business services/API wiring.

---

## What should be built first?

**Not Finance. Not Reporting. Not AI. Not Integrations.**

First:

```
```

```
Organization
 ↓
Party
 ↓
Property / Land
 ↓
Gujarat Property Records
 ↓
Enquiry
 ↓
Quotation
 ↓
Matter
 ↓
Matter relationships
 ↓
File
 ↓
Document
```

This is the core Legal\_DMS business spine.

---

## What should not be built yet?

Keep the following deferred:

```
```

```
Complex accounting
Full ERP
Elaborate CRM
Automated legal advice
Complex joint-development ownership
Universal government APIs
Excessively specialized property rules
AI document interpretation as a core dependency
```

---

## Highest-risk areas

The highest-risk areas are:

1. **Current** **`Client`** **model vs finalized Party architecture.** 
2. **Current one-client/one-property Matter structure.** 
3. **Revenue vs City Survey modelling.** 
4. **Land vs Property Unit distinction.** 
5. **Introducing File correctly without damaging Document relationships.** 
6. **Migration of the current schema.** 
7. **Tenant isolation.** 
8. **Audit/history integrity.** 
9. **File-number concurrency.** 
10. **Preventing development AIs from inventing domain semantics.** 

---

# Final conclusion

> **Business discovery is complete.**

> **The Consolidated Functional & Domain Architecture is now the authoritative business baseline for Legal\_DMS.**

> **The existing repository has a strong technical foundation, but its current schema is only a preliminary implementation foundation and must not be mistaken for the finalized business model.**

> **The next deliverable is not coding.**

> **The next deliverable is the formal Legal\_DMS Domain Model & Functional Specification, derived from the frozen business architecture and reconciled against the actual repository.**

> **Only after that specification and the associated ADRs are approved should database/API implementation begin.**

The repository inspection confirms why this ordering is important: the current database already contains entities named `clients`, `properties`, `matters`, `documents`, etc., but their relationships reflect an earlier architectural model—for example, `Matter` currently has direct `client_id` and `property_id` fields, while the finalized architecture requires reusable Parties and many-to-many Matter relationships.

**Therefore, the immediate engineering objective is:**

```
```

```
FROZEN BUSINESS ARCHITECTURE
            ↓
DOMAIN MODEL & FUNCTIONAL SPECIFICATION
            ↓
REPOSITORY GAP / MIGRATION SPECIFICATION
            ↓
TECHNICAL ADRs
            ↓
DATABASE + API CONTRACTS
            ↓
VERTICAL SLICE 1
```

That is the safest and most implementation-ready path forward for Legal\_DMS.

---

# Part II — Domain Model & Functional Specification (Entity Detail)

**Editorial note (Documentation Manager review pass):** Sections 1–23 above are the strategic
implementation report — business rules, feature catalogue, roadmap, risk register, and repository
mapping. That report's own §15/§16/§22 explicitly call for a further, entity-by-entity
specification as "the next major deliverable" before implementation begins. Sections 24 onward
below **are** that deliverable, developed against this repository's actual current state
(`main`, inspected directly — file paths cited throughout) and the business invariants already
frozen in §4 above. Nothing in §1–23 was reopened, reinterpreted, or renumbered; this part is a
pure addition.

**Classification key**, used throughout Part II:

- **CBR** — Confirmed Business Rule (already established by §4's authoritative business rules or
  the feature/priority catalogue in §2/§5; not open for reinterpretation here).
- **ED** — Engineering Decision (a technical/domain-implementation choice that still requires
  explicit resolution before database/API implementation).
- **RC** — Repository Constraint (a fact imposed by the current implementation that engineering
  must account for — not a requirement, a starting condition).
- **IC** — Implementation Choice (can reasonably be decided during implementation without changing
  business semantics).
- **DEF** — Deferred (intentionally postponed; not needed for the current implementation horizon).

Where a field, rule, or relationship is not yet knowable from either the frozen business
architecture or direct repository inspection, it is marked **ED — unresolved** rather than
invented. A short, honest "unresolved" list is more useful to a future Backend Developer than a
plausible-looking fabricated one.

**Reference-numbering note:** throughout §24, "Required ADR #N" refers to §21's planning-list
position N — a **document-internal planning identifier, not a repository ADR filename number**.
See §21's own terminology note for the full explanation before treating any "#N" below as a file
reference.

## 24. Entity Specifications

### 24.1 Organization & Identity

#### Organization

- **Purpose / business meaning (CBR):** the tenant boundary — the customer/firm whose data,
  users, and configuration are isolated from every other Organization's. §4 rule 43: "Organization
  is the tenant/security boundary."
- **Identity & tenant ownership (CBR/ED):** Organization is the root of ownership — it owns
  itself, nothing owns it. Whether an Organization can itself contain sub-organizations/branches is
  **ED — unresolved**; the frozen architecture does not require this, and none of §2's feature rows
  imply it. Default assumption unless decided otherwise: single-level tenancy (one flat
  Organization per customer).
- **Repository constraint (RC):** **no Organization table, column, or concept exists anywhere in
  the current schema.** Verified directly across every persistence model file
  (`backend/src/app/infrastructure/persistence/models/*.py`): `User`, `Client`, `Property`,
  `Matter`, `Document`, `Invoice`, `Payment`, `Task`, `ActivityLog`, `AuditLog` — none carry an
  `organization_id` or equivalent column. `RbacAuthorizationService.require_permission()`
  (`backend/src/app/infrastructure/auth/rbac_authorization_service.py`) checks only role → permission
  membership, with no tenant dimension at all. This is the single largest gap between the current
  repository and the frozen architecture, and the reason §1.4/§9.4/§13's top-severity risk rows
  exist.
- **Fields (ED — unresolved except where noted):** a name/legal-name pair is near-certainly
  required (CBR-adjacent — every tenant needs a display identity) but the exact field list
  (registration number, address, subscription/plan fields, locale/timezone defaults, branding) is
  not specified anywhere in the frozen architecture and must not be invented here.
- **Relationships (CBR):** every tenant-scoped entity in this specification (Party, Property,
  Matter, File, Document, Enquiry, Scheme, Team, Role assignment, etc.) belongs to exactly one
  Organization. Cross-Organization references must not exist for business data (only for
  platform-level concerns, if any — none identified).
- **Lifecycle (ED — unresolved):** active/suspended/archived states are plausible but not
  frozen; not specified.
- **Authorization (CBR + ED):** CBR — every authorization check must be Organization-scoped;
  §4 rule 43/44. ED — the exact mechanism (a column-level filter applied uniformly by the
  repository layer, a row-level-security Postgres feature, or a service-layer guard) is
  unresolved; see Required ADR #1 (§21) and #19.
- **Audit (CBR):** creation and any configuration change to an Organization is audit-significant
  (§4 rule 46).
- **Configuration (CBR):** Organization is the unit that *owns* configuration (§1.3/§6.2) —
  classifications, work types, document types, workflows, numbering rules, teams, confidentiality
  labels are all configured per-Organization, not global.
- **API implications (IC):** an Organization-scoped API is implied throughout; exact contract
  deferred to the API-contracts phase per §16.
- **Repository mapping:** **New** table required (§9.4, §10.A `organizations`). No existing table
  to migrate from.
- **Open engineering decisions:** exact field list; sub-organization support; lifecycle states;
  tenant-isolation enforcement mechanism (shared schema + `organization_id` filter vs. Postgres RLS
  vs. schema-per-tenant — the current single Postgres database with no tenant column at all makes
  shared-schema + mandatory `organization_id` filtering the practically-indicated default, but this
  is **ED**, not yet decided).

#### User

- **Purpose (CBR):** a system actor who can authenticate and act within one or more
  Organizations.
- **Repository constraint (RC):** `users` exists (`identity.py`) — `id`, `email` (globally unique),
  `full_name`, `phone`, `password_hash` (nullable — no login mechanism is wired yet per the file's
  own docstring), `is_active`, `last_login_at`, plus `AuditMixin`'s `created_at`/`updated_at`/
  `deleted_at`/`version`/`created_by`/`updated_by`. Authentication itself (JWT + DB-backed
  revocable refresh token, Argon2id hashing, `PyJWT`, interactive-only first-admin bootstrap, no
  self-registration, Electron `safeStorage` token persistence) is fully specified and implemented
  per ADR-0018 (D1–D6) and ADR-0019 — this is genuinely **Existing**, not a gap.
- **Gap vs. frozen architecture (RC → ED):** `email` is globally unique across the whole
  database, not scoped per-Organization. Whether the same person can be a User of more than one
  Organization (and if so, whether `email` uniqueness should become per-Organization) is
  **ED — unresolved**; the frozen architecture doesn't address multi-Organization users explicitly.
- **Relationships (RC, extending to ED):** `User` ⟷ `Role` is many-to-many via `user_roles`
  (existing). Adding an Organization-membership relationship (`user_organizations` or an
  `organization_id` column directly on `users`) is required by the Organization gap above — **ED**,
  exact shape unresolved.
- **Authorization (RC):** role-based only today (`RbacAuthorizationService`, string permission
  codes like `matters:read` checked against `role_permissions` via `roles`) — no tenant scoping,
  no resource-instance-level check. Extending this to be Organization-aware, and to support the
  finer-grained Matter/File/Document access §4 rule 45 requires, is **ED**, tracked under Required
  ADR #18.
- **Audit (RC):** `AuditMixin` already covers creation/modification; `last_login_at` covers login
  activity at a coarse grain.
- **Repository mapping:** **Modify** (§9.4) — add Organization membership; no other structural
  change indicated by the frozen architecture.

#### Team

- **Purpose (CBR):** an organizational work-grouping concept — §2 lists it "High" priority,
  §1.3/§6.2 lists Teams as an organization-configurable vocabulary item.
- **Repository constraint (RC):** **does not exist** — no team/group table anywhere in the schema.
- **Fields / relationships (ED — unresolved):** name, Organization ownership (CBR — Teams are
  necessarily Organization-scoped, since Organization owns configuration per §1.3), membership
  (User ⟷ Team, cardinality ED — unresolved whether a User can belong to more than one Team),
  and whether Teams participate in authorization (team-level Matter assignment/visibility) or are
  purely organizational/reporting metadata is **ED — unresolved**.
- **Repository mapping:** **New** (§9.4/§10.A `teams`).
- **Priority note (IC):** §2 marks this "High," not "Critical" — it can reasonably follow, rather
  than block, the Organization/Party/Matter spine (§23 "what should be built first").

#### Role / Permission

- **Purpose (CBR):** the authorization vocabulary — a Role groups Permissions; a User is assigned
  one or more Roles.
- **Repository constraint (RC — Existing, confirmed working):** `roles` (`id`, `name` unique,
  `description`, `is_system_role`), `permissions` (`id`, `code` unique — e.g. `matters:read`,
  `description`, `category`), `user_roles` and `role_permissions` join tables, all in
  `identity.py`. `RbacAuthorizationService.require_permission(user, permission)` denies an
  unauthenticated caller outright, then checks the caller's roles against a pre-loaded
  role-name → permission-codes snapshot (`RolePermissionRepository`), raising `ForbiddenError` on
  no match. This is a real, working implementation, not a stub — `PermissiveAuthorizationService`
  exists alongside it as an explicit allow-everyone stub for lower environments/tests, per its own
  file.
- **Gap vs. frozen architecture (RC → ED):** neither table nor the enforcement service is
  Organization-scoped. §6.2 lists Roles/Permissions as organization-*configurable* vocabulary
  (alongside classifications, work types, etc.) — today they are **global**, shared by every
  Organization in the database. Whether "configurable" means each Organization gets its own Role
  set (requiring `organization_id` on `roles`, and system-role templates cloned per Organization)
  or a shared global Role/Permission catalogue with per-Organization Role *assignment* only is
  **ED — unresolved**, tracked as part of Required ADR #1/#18.
- **Repository mapping:** **Modify** (§9.4) — the RBAC mechanism itself does not need
  reimplementation; it needs an Organization dimension added to it.

**Cross-cutting repository constraint, verified across every model file:** the current schema
declares only columns and `ForeignKey` constraints — **no SQLAlchemy `relationship()` is declared
anywhere**, by deliberate original design ("deferred to the first feature that needs a specific
traversal," per the models' own docstrings). Every entity spec below therefore describes the
*logical* relationship the frozen architecture requires; the actual ORM `relationship()`
declarations (and their `cascade=`/`lazy=` behavior) remain **ED — implementation choice**, to be
added by whichever task first implements that entity, not retrofitted speculatively here.

---

### 24.2 Party

#### Party

- **Purpose / business meaning (CBR):** the reusable master record for any person or legal entity
  the firm deals with — §4 rule 8: "Party is the reusable master record." A Party's existence is
  independent of any specific Matter.
- **Identity & tenant ownership (CBR):** Organization-scoped (every Party belongs to exactly one
  Organization — §4 rule 43 applies transitively to every business entity). Identity is a durable
  UUID surrogate key (RC — matches this repository's established UUID-primary-key convention,
  confirmed on every existing table); no natural key (PAN/Aadhaar/registration number) is
  sufficiently universal or stable to serve as identity, though such identifiers are searchable
  attributes.
- **Business invariants (CBR):**
  - §4 rule 9: Client is a Matter *relationship/status*, not a master entity — "Client" is not a
    Party subtype or a separate table; it is what a Party *is* on a given Matter (see MatterParty
    below).
  - §4 rule 10/11: a Matter may have multiple Parties; a Party may participate in many Matters.
  - §4 rule 12: the same Party may hold different roles on different Matters (e.g. Party X is the
    Client on Matter A and a counter-party's Representative on Matter B).
  - §4 rule 13/14: a Party may have multiple Representatives, and multiple Representatives may
    jointly authorize/appoint work.
- **Subtype strategy (ED — must decide before implementation, §12):** the frozen architecture
  requires Party to represent both individuals and legal entities (companies, trusts, government
  bodies, etc. — broader than the current `Client.client_type`'s `individual|organization` pair).
  Whether this is modeled as (a) single-table with a discriminator column and nullable
  subtype-specific fields, (b) class-table inheritance (a `parties` base table + `individual_parties`/
  `organization_parties` extension tables), or (c) a JSONB "profile" blob keyed by subtype is
  **unresolved** — Required ADR #2 ("Party vs Client").
- **Fields (mixed):**
  - Universally applicable (**CBR-adjacent**, near-certain regardless of subtype strategy):
    display name, a subtype/kind discriminator, primary phone, primary email, notes, an address
    relationship (the existing `Address`/geography hierarchy — `client.py`'s `Address` model,
    already Gujarat-village-aware — is directly reusable, **RC/IC**: reuse rather than rebuild).
  - Individual-specific (**ED**, contingent on subtype strategy): PAN/Aadhaar (the current
    `Client.pan_number`/`aadhaar_number` regex-validated columns are directly reusable as a
    starting point — **RC**), date of birth, gender, occupation — none of these are frozen as
    requirements; do not assume all are needed.
  - Organization-specific (**ED**): registration/CIN number, GSTIN, incorporation date,
    authorized-signatory relationship (which is itself a Representative — see below).
  - **Explicitly not yet decided (ED):** exact required/optional split, validation rules beyond
    what's already proven for PAN/Aadhaar format, default values, mutability policy for identity
    fields (e.g. can `full_name` be edited after Matters reference the Party, and if so does that
    require an audit trail entry — almost certainly yes per §4 rule 42, but the mechanism is ED).
- **Relationships (CBR + ED):** Party ⟷ Matter is many-to-many through `MatterParty` (never
  direct — §4 rule 10/11 requires this). Party ⟷ Representative is one-to-many (a Party may have
  several Representatives). Party ⟷ Party via `PartyRelationship` (below). Party ⟷ Property
  ownership is **ED — likely** via a Property-side ownership relationship analogous to the
  existing `PropertyOwner` join table (`property.py`), but the frozen architecture's exact
  ownership-representation requirement is covered under Property below, not duplicated here.
- **Lifecycle (ED — unresolved):** active/inactive or archived states, and whether a Party can be
  "merged" with a duplicate (a realistic real-world need — the same person enquired twice under
  slightly different name spellings) are not specified. Flag for the Party ADR.
- **Authorization (CBR + ED):** Organization-scoped visibility (CBR, transitively). Whether Party
  records carry the same confidentiality/finer-grained access model as Matters (§4 rule 45) is
  **ED — unresolved**; the frozen architecture names Matters/Files/Documents explicitly for
  finer-grained access, not Party, so the default assumption is Organization-level visibility only
  unless a future decision extends it.
- **Audit (CBR):** creation, field changes, and relationship changes (new Representative, new
  PartyRelationship) are audit-significant per §4 rule 42's actor-attribution requirement.
- **Search requirements (IC, informed by RC):** name/phone/email/PAN/Aadhaar/registration-number
  search is clearly required by the business use case (finding an existing Party before creating a
  duplicate); the existing `SearchQuery`/`FilterSpec` framework (`application/common/query.py`,
  already wired through the generic repository via T4–T6) is directly reusable for this — no new
  search mechanism needs inventing.
- **Repository mapping / reconciliation:** **New/Modify** (§9.4/§5). The existing `clients` table
  (`client.py`) is the closest analogue but is explicitly **not** a direct rename target (§11.1
  "Client → Party... a direct rename is insufficient") — it is `individual|organization`-only,
  carries client-specific fields directly rather than through a subtype mechanism, and has no
  Representative or PartyRelationship concept at all. `client_contacts` is a partial precedent for
  Representative (see below) but conflates "any contact person" with "a person legally authorized
  to act for the Party."
- **Open engineering decisions:** subtype-modeling strategy (Required ADR #2); exact field list
  per subtype; Party-merge/deduplication; whether Party-level confidentiality exists.

#### PartyRelationship

- **Purpose (CBR):** represents relationships *between* Parties (e.g. director-of, partner-of,
  family-of, guardian-of) — distinct from a Party's role *on a Matter* (that's MatterParty) and
  distinct from Representative (a Representative acts *for* a Party on its behalf; a
  PartyRelationship just records that two Parties are related). §2 lists "Party relationships" as
  its own Critical-priority row, separate from Party and Representative.
- **Repository constraint (RC):** **does not exist** — confirmed, no relationship-graph table
  anywhere in the schema.
- **Fields / structure (ED — unresolved):** source Party, target Party, a relationship-type
  vocabulary (organization-configurable per §6.2's general pattern, though PartyRelationship is
  not explicitly named in §6.2's example list — **ED** whether it's core or configurable),
  directionality (is "X is director of Y" the same row read backwards as "Y is directed by X," or
  two distinct typed relationships?), and an effective-date range (mirroring `PropertyOwner`'s
  `from_date`/`to_date` pattern, which is a reasonable **IC** precedent, not a frozen requirement).
- **Relationships:** Party ⟷ Party (self-referential, many-to-many via this join entity).
- **Repository mapping:** **New** (§9.4/§10.A `party_relationships`).
- **Open engineering decisions:** relationship-type vocabulary and whether it is core or
  organization-configurable; directionality model; whether historical (ended) relationships are
  retained or archived.

#### Representative

- **Purpose (CBR):** a person authorized to act *for* a Party — §4 rule 13/14: a Party may have
  multiple Representatives, and multiple Representatives may jointly participate in
  appointing/authorizing work. Distinct from PartyRelationship (which relates two Parties to each
  other) and from MatterParty (which relates a Party to a Matter).
- **Repository constraint (RC):** `client_contacts` (`client.py`) is a **partial** precedent —
  `client_id`, `contact_name`, `relationship_type` (free string), `phone`, `email`, `is_primary` —
  but it models "a contact person for a Client," not "a person with legal authority to act for a
  Party," and it has no concept of authorization scope, effective dates, or document evidence of
  the authorization (e.g. a Power of Attorney).
- **Fields (ED — unresolved beyond what `client_contacts` already establishes):** name, contact
  details (RC-precedented, directly reusable shape), the Party being represented, an
  authorization-basis field (POA / director / natural guardian / court-appointed / other — **ED**,
  vocabulary not frozen), effective date range, and — the most consequential open question —
  whether a Representative record must reference supporting Document evidence (a scanned POA) is
  **ED — unresolved**, and matters for the Document-relationship design once Document is
  implemented.
- **Relationships (CBR):** Representative ⟷ Party is many-to-one (one Party, many
  Representatives — §4 rule 13). Whether a single natural person can be a Representative for more
  than one Party simultaneously (e.g. a professional POA-holder for several clients) is
  **ED — plausible, not frozen**.
- **Repository mapping:** **New/Modify** (§9.4: "`client_contacts` partially related").
- **Open engineering decisions:** authorization-basis vocabulary; whether Document evidence is
  mandatory; whether a Representative can represent multiple Parties.

---

### 24.3 Property & Land

#### Property

- **Purpose / business meaning (CBR):** an independently-identified subject of legal work — §4
  rule 15: "Property is independent of Matter." §4 rule 16/17: the same Property may participate
  in multiple, unrelated Matters; two Matters sharing a Property does not imply any relationship
  between those Matters.
- **Repository constraint (RC):** `properties` (`property.py`) exists —
  `property_type` (CHECK'd `agricultural|residential|commercial|industrial|other`),
  `survey_number`, `sub_division_number`, `area_value`/`area_unit`, `address_id`, `village_id`
  (denormalized for query performance — a deliberate, documented trade-off, `docs/Database.md`),
  `registration_number`. `PropertyOwner` already exists as a join table to `clients` with
  `ownership_share`/`ownership_type`/`from_date`/`to_date` — a genuinely useful precedent for the
  Party-ownership relationship the frozen architecture needs, once `client_id` is retargeted to
  Party.
- **Business invariants (CBR):** §4 rule 18: "Land and Property Unit must not be conflated" — the
  current `Property` table's single `survey_number` field is generic and does not distinguish a
  Revenue-system land identity from a City-Survey property-unit identity (see Land and the Gujarat
  Property Records group below).
- **Gap vs. frozen architecture (RC → ED):** `survey_number`/`sub_division_number` is a single,
  generic identifier pair. It cannot, as designed, hold both a Revenue Survey Number *and* a City
  Survey Number *and* a TP/FP reference for the same physical property — those are explicitly
  required to be distinct, extensible record systems (§4 rules 19–24). Whether `Property` becomes
  a genuinely generic "subject of legal work" record that *links to* separate Revenue/City-
  Survey/TP-FP record entities (this specification's working assumption, consistent with §9.4/
  §10.A's `property_record_references` row), or whether `Property` itself grows type-specific
  columns, is **ED — must decide before implementation** (§12 "Property Record Reference
  strategy").
- **Relationships (CBR + ED):** Property ⟷ Matter is many-to-many through `MatterProperty`
  (never direct — mirrors the Party/MatterParty pattern, same rationale, §4 rule 15–17). Property
  ⟷ Party ownership is **ED** in exact shape but has a strong existing precedent
  (`PropertyOwner`). Property ⟷ {RevenueRecord, CitySurveyRecord, TP/FP Record} is **ED**, per the
  Property Record Reference strategy decision above. Property ⟷ Scheme is plausible (a Property
  may be a unit within a Scheme) but not frozen as a required relationship — **ED**.
- **Search / reporting (IC):** village/survey-number/registration-number search is already
  supported by the existing indexes (`village_id`, `survey_number`, `registration_number` are all
  indexed today) and is directly reusable.
- **Repository mapping:** **Modify** (§9.4) — the table is a reasonable starting foundation
  (audited, optimistic-locked, geography-linked) but needs its identifier model split out per the
  decision above, and its `Matter`/`Party` relationships redirected through the new join entities.
- **Open engineering decisions:** Property Record Reference strategy (Required ADR #6); whether
  `Property` itself needs new columns or purely new linked-record tables; Property↔Scheme
  relationship.

#### Land

- **Purpose (CBR):** the Revenue-oriented land identity, explicitly distinct from a City-Survey
  property unit — §4 rule 18, and §2's "Land — Revenue-oriented land identity."
- **Repository constraint (RC):** **not distinct in the current schema** — `properties` does not
  separate land-level identity from unit-level identity at all.
- **Representation strategy (ED — must decide, §12 "Land representation"):** whether Land is (a)
  its own table that Property references, (b) a specialization/subtype of Property, or (c) folded
  into the RevenueRecord entity directly (i.e. "Land" and "RevenueRecord" turn out to be the same
  concept once the Gujarat records are specified) is genuinely unresolved and should not be
  guessed here — this decision and the Gujarat-records group below are tightly coupled and should
  be made together.
- **Repository mapping:** **New** (§9.4).
- **Open engineering decisions:** entire representation strategy, coupled to RevenueRecord below.

---

### 24.4 Gujarat Property Records

**Cross-cutting note (CBR):** §4 rules 19–24 are unusually explicit and must not be
reinterpreted: Revenue and City Survey are distinct record systems (rule 19); Revenue Block/Survey
Number belongs to the Revenue/Land model (rule 20); City Survey Number may identify property
*units* (rule 21) and is not merely another Revenue Survey Number (rule 22); TP/FP is
independently represented (rule 23); other property-record systems must remain extensible (rule
24 — i.e. the design must not hard-code "exactly these four systems" in a way that blocks adding a
fifth later).

#### RevenueRecord

- **Purpose (CBR):** the Gujarat Revenue-system property reference (Block/Survey Number lineage).
- **Repository constraint (RC):** does not exist distinctly; `properties.survey_number` is today's
  only (generic, insufficient) analogue.
- **Fields (ED — unresolved):** the exact Revenue-record field set (7/12 extract fields, Block
  Number, Survey Number, Sub-division, village/taluka/district linkage — the existing
  `geography.py` hierarchy is directly reusable, **RC/IC**) is not specified in the frozen
  architecture at the field level; only the *concept's* existence and independence from City
  Survey is frozen.
- **Repository mapping:** **New** (§9.4/§10.A `revenue_records`), coupled to the Land
  representation-strategy decision above.

#### CitySurveyRecord

- **Purpose (CBR):** the City Survey system's property-unit identifier — distinct from Revenue
  Survey Number (§4 rule 21/22).
- **Repository constraint (RC):** does not exist.
- **Fields (ED — unresolved):** City Survey Number, ward/zone linkage, and its relationship to a
  Property/Property-Unit are not specified at the field level.
- **Repository mapping:** **New** (§9.4/§10.A `city_survey_records`).

#### TP / FP Record

- **Purpose (CBR):** Town Planning / Final Plot references — §4 rule 23, "TP/FP is independently
  represented"; §2 lists this "High" (not "Critical") priority.
- **Repository constraint (RC):** does not exist.
- **Fields (ED — unresolved):** TP scheme number, FP number, and their relationship to Property/
  Scheme are not specified at the field level. Note the overlap risk with the Scheme entity
  (below) — a Town Planning Scheme is conceptually adjacent to but not necessarily the same thing
  as this specification's "Scheme" (development/project structure). **This boundary question is
  explicitly assigned to Required ADR #7 ("Flexible Scheme hierarchy," §21)**, not to Required ADR
  #6 ("Property Record Reference architecture") — #6 governs *how* a Property links to record
  entities like this one; #7 is where "Scheme" itself gets conceptually defined, which is the
  actual question here (does a Town Planning Scheme count as this specification's Scheme, a
  TP/FP-Record-only concept, or both). Recorded here so the question cannot be lost between the
  two adjacent list items.
- **Repository mapping:** **New** (§9.4/§10.A `tp_records`/`fp_records`).

#### PropertyRecordReference

- **Purpose (ED — architectural, not yet frozen at the mechanism level):** §4 rule 24 requires
  the property-record-system set to remain extensible (a fifth system must be addable without a
  schema rewrite). §9.4/§10.A lists `property_record_references` as a candidate table — i.e. one
  design option is a generic linking table (`property_id`, `record_type`, `record_id`) rather than
  N separate direct FKs from `Property` to each record type. This is genuinely **ED**, not CBR —
  the business rule only requires extensibility, not this specific mechanism; a well-designed set
  of direct FKs plus a documented "add a new table + FK when a new record system appears"
  convention could equally satisfy rule 24. Required ADR #6 must resolve this before any of the
  four record types above are implemented.
- **Open engineering decisions (whole group):** Land vs. RevenueRecord relationship; exact field
  sets for all four record types; the generic-reference-table vs. direct-FK mechanism question.

---

### 24.5 Scheme

#### Scheme

- **Purpose / business meaning (CBR):** a development/project structure — §4 rule 25: "Scheme is
  independent of Matter" (same independence pattern as Property). §4 rule 26: one Organization may
  own/control multiple Schemes.
- **Repository constraint (RC):** **does not exist** — no scheme/development/project table
  anywhere in the schema.
- **Structure (CBR + ED):** §4 rule 27/28 is explicit and must not be over-engineered: "Scheme
  structure is flexible. Building/Block/Section are standard concepts, not mandatory hierarchy
  requirements." This directly rules out a rigid, mandatory
  `Scheme → Building → Block → Section → Unit` fixed-depth hierarchy as a business requirement —
  any implementation must support *shallower* structures (a Scheme with units directly, no
  Building/Block layer) as a first-class case, not an edge case. The exact storage mechanism for a
  variable-depth hierarchy (adjacency list / materialized path / nested set / a fixed set of
  optional nullable levels) is **ED — must decide before implementation** (§12 "Scheme hierarchy
  storage").
- **Fields (ED — unresolved):** name, Organization ownership (CBR — transitively required),
  location, and the hierarchy-node fields depend entirely on the storage-mechanism decision above;
  not specified further here to avoid presupposing that decision.
- **Relationships (CBR + ED):** Scheme ⟷ Organization is many-to-one (CBR, rule 26). Scheme ⟷
  Property is plausible (a Property may be a unit within a Scheme) but its exact cardinality and
  whether it's mediated by a `scheme_nodes`/structure table (per §9.4/§10.A) is **ED**. Scheme ⟷
  Matter: **no direct relationship** is implied by the frozen architecture (Scheme is
  Matter-independent, same as Property; a Matter reaches a Scheme only by way of a Property it's
  related to, if at all).
- **Repository mapping:** **New** (§9.4/§10.A `schemes`, `scheme_nodes`/structure).
- **Open engineering decisions:** hierarchy storage mechanism (Required ADR #7); exact
  Scheme↔Property relationship; field list.

---

### 24.6 Enquiry & Quotation

#### Enquiry

- **Purpose / business meaning (CBR):** the prospective-engagement entry point, before any
  commercial commitment exists — §2: "Enquiry — Prospective engagement," §5's dependency column
  lists Enquiry depending only on Party, and §1.5/§7 Phase 3's lifecycle diagram is explicit:
  `Enquiry → Quotation → Acceptance → Matter`.
- **Repository constraint (RC):** **does not exist** — no intake/enquiry table anywhere in the
  schema; the current schema begins at `Matter`, with no pre-Matter stage represented at all.
- **Fields (ED — unresolved):** the enquiring Party (or a not-yet-a-Party prospective contact —
  **ED**, unresolved whether an Enquiry requires an existing Party record or can reference bare
  contact details that only become a Party on acceptance), a description of the prospective work,
  source/channel, and a status are all plausible but not frozen at the field level.
- **Lifecycle (CBR + ED):** CBR — an Enquiry precedes a Quotation, which precedes acceptance,
  which produces a Matter (the diagram above is itself part of the frozen roadmap, not an
  invented addition). ED — the exact status vocabulary (e.g. `open`/`quoted`/`converted`/
  `declined`/`lost`) and whether Enquiries that don't convert are archived or retained
  indefinitely for reporting/pipeline-analysis purposes are unresolved.
- **Relationships (CBR):** Enquiry ⟷ Party (many-to-one, at minimum). Enquiry ⟷ Quotation
  (one-to-many — an Enquiry may receive more than one Quotation iteration before acceptance,
  **ED** whether that's modeled as versions of one Quotation or multiple Quotation rows).
- **Repository mapping:** **New** (§9.4/§10.A `enquiries`).
- **Open engineering decisions:** whether an Enquiry requires an existing Party; status
  vocabulary; retention/archival policy for non-converted Enquiries.

#### Quotation

- **Purpose / business meaning (CBR):** the commercial proposal made in response to an Enquiry —
  §2: "Quotation — Commercial proposal." §4 rule 35: Quotation, Commercial Scope, Charges, Invoice
  and Payment are separate concepts — a Quotation must not be conflated with, or implemented as,
  an early Invoice.
- **Repository constraint (RC):** does not exist.
- **Fields (ED — unresolved):** scope-of-work description, proposed fee structure, validity
  period, and status (draft/sent/accepted/rejected/expired) are plausible but not frozen at the
  field level. Whether the proposed fee structure at Quotation stage is free-text/summary only, or
  already structured into line items that later become Commercial Scope/Charge records on
  acceptance, is **ED — unresolved** and matters for the Finance-chain design (§24.13).
- **Relationships (CBR):** Quotation ⟷ Enquiry (many-to-one). Quotation ⟷ Matter: on acceptance,
  produces exactly one Matter (§7 Phase 3's critical requirement: "Matter must be created at
  acceptance even when File count = 0"). Quotation ⟷ Commercial Scope: acceptance is the trigger
  that establishes the Matter's Commercial Scope (§4 rule 35's ordering) — **ED** on the exact
  hand-off mechanism (does accepting a Quotation *automatically* create a CommercialScope row, or
  is that a separate, explicit step?).
- **Lifecycle (CBR + ED):** CBR — accepted/rejected are real, business-meaningful terminal-ish
  outcomes (accepted specifically triggers Matter creation). ED — the full status vocabulary and
  whether a rejected/expired Quotation can be revised and re-sent as a new version vs. a wholly new
  row.
- **Repository mapping:** **New** (§9.4/§10.A `quotations`).
- **Open engineering decisions:** fee-structure granularity at Quotation stage; acceptance→
  CommercialScope hand-off mechanism; full status vocabulary; versioning vs. new-row-per-revision.

---

### 24.7 Matter

#### Matter

- **Purpose / business meaning (CBR):** the accepted engagement — §4 rule 1/2: "Matter is the
  accepted engagement... created when the overall engagement is accepted." §4 rule 3: Matter does
  not require a File to exist (a Matter may legitimately have zero Files — §7 Phase 4's core
  invariant diagram).
- **Repository constraint (RC — the most consequential single gap in the entire specification):**
  `matters` (`matter.py`) exists and is audited/optimistic-locked, but its relationship model is
  the frozen architecture's primary counter-example: `matter_type_id` (single classification),
  `client_id` (single, direct, non-nullable FK to `clients`), `property_id` (single, nullable,
  direct FK to `properties`), plus `matter_number` (unique), `assigned_to`, `title`,
  `description`, `opened_at`/`closed_at` (CHECK'd `closed_at >= opened_at`). This is explicitly
  the example the frozen architecture itself uses (§1.4, §11.1) to illustrate the required
  transition — a single `client_id`/`property_id` model cannot represent "a Matter may have
  multiple parties/clients" (§4 rule 10) or "a Matter can involve multiple properties" (§2's Matter
  row, §4 rule 16).
- **Business invariants (CBR):**
  - §4 rules 1–7 (Matter/File group in full): Matter is the accepted engagement; created at
    acceptance; does not require a File; File is a work package within a Matter; File cannot exist
    without a Matter; File Number is assigned at File creation; File Numbers must not be silently
    reused.
  - §4 rule 29/30/31: a Matter may have multiple Classifications and multiple Work Types;
    Classification and Work Type are distinct concepts (not to be conflated into one
    "matter type" field, which is exactly what `matter_type_id` currently is).
- **Relationship redesign required (CBR, mechanism ED):** `matter_type_id`/`client_id`/
  `property_id` as direct FKs must be replaced/supplemented (§11.1's own wording — "replaced/
  supplemented," i.e. whether the old columns are dropped immediately or retained during a
  compatibility-migration window is **ED**, tracked under Required ADR #20 "Migration strategy")
  by: `MatterParty[]` (multi-party), `MatterProperty[]` (multi-property), `MatterClassification[]`
  (multi-classification), `MatterWorkType[]` (multi-work-type) — all detailed as their own entities
  below.
- **Fields — what's confirmed vs. open:**
  - **CBR/RC (keep, directly reusable):** `matter_number` (unique human-readable identifier —
    already exists and already matches the general "human-readable identity" pattern the frozen
    architecture also wants for File Number), `title`, `description`, `assigned_to`,
    `opened_at`/`closed_at` with the existing chronological CHECK constraint, `matter_status_id`
    (a lookup-table-backed status, consistent with §6.2's "operational statuses where not
    architectural" configurability pattern).
  - **RC → CBR-mandated change:** `client_id`, `property_id`, `matter_type_id` must become
    relationship entities, not direct columns (see above).
  - **New, ED — unresolved:** Organization ownership column (mandatory per the Organization gap,
    §24.1) does not exist on `matters` today.
- **Lifecycle / states (RC + ED):** `matter_statuses` already exists as a lookup table with an
  `is_terminal` flag — a reasonable, reusable **IC** foundation for status modeling. The actual
  status vocabulary (open/on-hold/closed/etc.) is seed data, not schema, and is
  **ED — organization-configurable** per §6.2's general pattern (operational statuses are
  configurable; the *concept* of Matter status is core).
- **Authorization (CBR + ED):** §4 rule 45: "Matters, Files and Documents may require
  finer-grained access [beyond Organization-level]." The exact mechanism (per-Matter access grants,
  Team-based visibility, confidentiality labels — §6.2 lists "Confidentiality labels" as a
  configurable item) is **ED — must decide before security implementation**, tracked under §24.14
  Advanced Security and Required ADR #18.
- **Audit (CBR):** creation, status changes, and relationship changes (Party added/removed,
  Property added/removed, Classification/Work Type changed) are all audit-significant per §4 rule
  42.
- **Search / reporting (IC):** the existing `SearchQuery`/`FilterSpec`/`SortSpec` framework
  (already proven end-to-end through the generic repository/service/router chain via T4–T8) is
  directly reusable for Matter search/filtering once the relationship redesign lands; no new
  search mechanism needs inventing.
- **Repository mapping:** **Modify — major** (§9.4/§11.1's own explicit worked example).
- **Open engineering decisions:** exact migration sequencing for `client_id`/`property_id`/
  `matter_type_id` retirement (Required ADR #20); status vocabulary; Organization column addition;
  finer-grained authorization mechanism.

#### MatterParty

- **Purpose (CBR):** the multi-party relationship entity §4 rules 9–14 require — represents one
  Party's participation in one Matter, in a given role (e.g. Client, Opposing Party, Represented
  Third Party).
- **Repository constraint (RC):** **does not exist** — confirmed, `matters.client_id` is today's
  only (single, insufficient) analogue.
- **Fields (ED — unresolved, role vocabulary especially):** Matter reference, Party reference, a
  role field (§4 rule 9's "Client is a Matter relationship/status" is realized here — "Client" is
  a *value* this role field can take, not a separate table). The full role vocabulary beyond
  "Client" (Opposing Party, Co-Applicant, Objector, Represented Party, etc.) is **ED — unresolved**
  and organization-configurable per §6.2's general pattern, though not explicitly named in §6.2's
  example list.
- **Relationships (CBR):** many-to-many join between Matter and Party, carrying the role as an
  attribute of the join itself (a Party can hold *different* roles on *different* Matters per §4
  rule 12 — this is naturally satisfied by role living on `MatterParty`, not on `Party`).
- **Cardinality (CBR):** a Matter has zero-or-more MatterParty rows in principle, but realistically
  at least one (a Matter without any Party seems to contradict "accepted engagement," though the
  frozen architecture does not explicitly state a minimum — flagged as **ED — worth confirming**,
  not assumed here).
- **Repository mapping:** **New** (§9.4/§10.A `matter_parties`).
- **Open engineering decisions:** role vocabulary; minimum-cardinality question above.

#### MatterProperty

- **Purpose (CBR):** the multi-property relationship entity §4 rules 15–17 require.
- **Repository constraint (RC):** does not exist; `matters.property_id` (single, nullable) is
  today's only analogue.
- **Fields (ED — unresolved):** Matter reference, Property reference, and possibly a
  relationship-nature field (e.g. "subject property" vs. "comparable/reference property" if the
  business ever needs to distinguish — **not frozen**, do not assume this exists without
  confirmation).
- **Relationships (CBR):** many-to-many join between Matter and Property.
- **Repository mapping:** **New** (§9.4/§10.A `matter_properties`).
- **Open engineering decisions:** whether any relationship-nature qualifier is needed on the join.

#### Classification (MatterClassification)

- **Purpose (CBR):** multi-dimensional Matter categorization — §4 rule 29: a Matter may have
  multiple Classifications. §4 rule 31: Classification and Work Type are distinct concepts.
- **Repository constraint (RC):** `matter_types` exists as a lookup table but is wired as a
  single, non-nullable FK on `matters` — the opposite of "multiple Classifications." §9.4 marks
  this "Existing type concept insufficient."
- **Fields (ED — unresolved):** classification vocabulary/taxonomy is **organization-configurable**
  per §6.2 ("Matter Classifications" is explicitly named there), so the *values* are seed/config
  data, not schema; the join structure itself (Matter ⟷ Classification, many-to-many) is the
  schema-level requirement.
- **Repository mapping:** **Modify/New** (§9.4) — `matter_types` likely becomes the seed-vocabulary
  table underlying a new `matter_classifications` many-to-many join, rather than being discarded
  outright; exact reuse-vs-replace decision is **ED**.

#### Work Type (MatterWorkType)

- **Purpose (CBR):** the actual professional work being performed — §4 rule 30: a Matter may have
  multiple Work Types; distinct from Classification (rule 31).
- **Repository constraint (RC):** does not exist as its own concept anywhere in the current
  schema.
- **Fields (ED — unresolved):** Work Type vocabulary is **organization-configurable** per §6.2
  ("Work Types" explicitly named there) — values are seed/config data; the join structure (Matter
  ⟷ Work Type, many-to-many) is the schema-level requirement.
- **Repository mapping:** **New** (§9.4/§10.A `matter_work_types`, plus a Work Type vocabulary
  table).

---

### 24.8 File & Numbering

#### File

- **Purpose / business meaning (CBR):** a work package within a Matter — §4 rule 4: "File is a
  work package within a Matter." §4 rule 5: "File cannot exist without a Matter." §7 Phase 4's
  core invariant: a Matter may have zero, one, or many Files (`Matter ├── File A ├── File B └──
  File C`, or none).
- **Repository constraint (RC):** **no File entity exists anywhere in the current schema.**
  `documents.matter_id` links directly to Matter with no intermediate File concept at all — this
  is §9.4's "No finalized File entity identified" row and the specific gap §11.1's Documents
  reconciliation example calls out (`Matter → Document` today vs. required
  `Matter → File → Document`).
- **Fields (ED — unresolved):** a File Number (see below), a title/description, a status, and the
  owning Matter are the near-certain minimum; beyond that, whether a File carries its own
  classification/work-type dimension independent of its parent Matter's, or purely inherits the
  Matter's, is **ED — unresolved**.
- **Relationships (CBR):** File ⟷ Matter is many-to-one, mandatory (rule 5 — a File cannot exist
  without its Matter; cascade/orphan behavior on Matter deletion is **ED**, though "Matter
  deletion" itself is likely rare/soft-only given §4 rule 46's audit-integrity requirement). File ⟷
  Document is one-to-many (§11.1's required chain). File ⟷ Workflow/Task/GovernmentProcess: §2's
  Feature Catalogue lists these as depending on File (via Matter), consistent with File being the
  practical unit that internal workflow/tasks/government processes actually attach to — **ED**
  on the exact attachment point (File-level vs. Matter-level vs. either), not frozen at that
  granularity by §4's invariants alone.
- **Lifecycle (ED — unresolved):** status vocabulary and terminal states are not specified; only
  the structural invariants (no File without Matter, Number assigned at creation, Number never
  silently reused — §4 rule 6/7) are frozen.
- **Repository mapping:** **New** (§9.4/§10.A `files`) — this is one of the highest-priority gaps,
  since Document's required relationship redesign (§24.9) depends on File existing first.
- **Open engineering decisions:** File-level fields beyond Number/status; File's own
  classification/work-type independence from Matter; Matter-deletion cascade behavior;
  Workflow/Task/GovernmentProcess attachment granularity (File vs. Matter).

#### File Numbering

- **Purpose (CBR):** the human-readable File identity — §4 rule 6/7: assigned at File creation;
  must not be silently reused. §7 Phase 4's exit criterion: "File creation is independently
  controlled and assigns a unique File Number at creation," with a mandatory concurrency test
  (§17.5: "Concurrent File creation → no duplicate").
- **Repository constraint (RC):** **no numbering-sequence mechanism exists for Files.** The
  closest existing precedent is `matters.matter_number` (a plain unique string column with no
  visible generation-sequence table) and `invoices.invoice_number`/`receipts.receipt_number`
  (same pattern) — none of these demonstrate a concurrency-safe *generation* mechanism in the
  schema itself; uniqueness is enforced by a DB constraint, but the *algorithm* that produces the
  next number is application-layer and not evidenced in the models inspected.
- **Numbering algorithm & concurrency strategy (ED — must decide before implementation, §12,
  §17.5):** entirely unresolved. Candidate approaches (a Postgres `SEQUENCE` per Organization/
  scope, a dedicated `file_number_sequences` row locked via `SELECT ... FOR UPDATE` per
  generation, or an application-level distributed-lock scheme) are not chosen here — this is
  explicitly flagged as a concurrency-critical decision, not a cosmetic one, given the mandatory
  "no duplicate under concurrent creation" test requirement.
- **Format (ED — unresolved):** whether the File Number is Organization-scoped (resets or is
  namespaced per Organization), Matter-scoped (e.g. `MatterNumber-01`, `-02`), or globally
  sequential is not specified.
- **Repository mapping:** **New** (§9.4/§10.A `file_number_sequences`).
- **Open engineering decisions:** the entire numbering algorithm and concurrency mechanism
  (Required ADR #9); numbering scope/format.

---

### 24.9 Document Management

#### Document

- **Purpose / business meaning (CBR):** legal records/evidence — §2: "Documents — Legal records/
  evidence." §4 §History group implicitly, and §1.2's frozen-terms list, both name Document as a
  protected concept.
- **Repository constraint (RC — Existing foundation, genuinely reusable):** `documents`
  (`document.py`) exists — `matter_id` (direct FK, **the gap**), `document_type_id`, `title`,
  `status` (default `draft`) — plus `AuditMixin`/`OptimisticLockMixin`. `document_types` is
  already a proper lookup table, consistent with §6.2's "Document Types" configurability. The
  file-storage side is genuinely mature: `FileStorageRecord` (`storage.py`) holds provider/path/
  original filename/MIME type/size/SHA-256 checksum/retention policy, and the database
  deliberately never stores document content — only metadata (confirmed directly in the model's
  own docstring and by the `LocalFileStorage` implementation storing bytes on disk, not in
  Postgres). `DocumentTemplate`/`DocumentVariable` exist as a template-driven-generation
  *framework only* — no generation logic is implemented (RC, explicitly out of this
  specification's required scope unless separately prioritized).
- **Required change (CBR, mechanism largely RC-informed):** §11.1's explicit required chain:
  `Matter → File → Document`, not today's `Matter → Document`. Once File exists (§24.8),
  `documents.matter_id` should be redirected to (or supplemented by) a `file_id` FK — exact
  migration mechanics are **ED**, tracked under Required ADR #10 "Document/File relationship" and
  the general migration-strategy ADR (#20).
- **Fields — what's confirmed vs. open:** `title`, `document_type_id`, `status` are directly
  reusable (**RC/CBR-adjacent**). Confidentiality/sensitivity marking (§4 rule 45's "Documents...
  may require finer-grained access," §6.2's "Confidentiality labels") does not exist on the table
  today — **ED**, tracked under §24.14.
- **Relationships (CBR):** Document ⟷ File is many-to-one (post-redesign). Document ⟷
  DocumentVersion is one-to-many (existing, see below).
- **Lifecycle (RC + ED):** `status` defaults to `draft` today; the full vocabulary and whether
  archival/finalization states exist beyond that default is **ED — unresolved**.
- **Authorization (CBR + ED):** per §4 rule 45, Document-level access may need to be finer than
  Matter-level (e.g. a specific Document marked confidential within an otherwise normally-visible
  Matter) — mechanism is **ED**, same open item as Matter/File authorization.
- **Audit (CBR):** creation, version addition, status change, and access to confidentiality-marked
  Documents are all audit-significant (§4 rule 42/46).
- **Search / reporting (IC):** title/type/status filtering is directly supported by the existing
  generic `SearchQuery` framework; OCR-extracted full-text search is a **DEF** capability — the
  `OcrResult` table already has a GIN `to_tsvector` index prepared (per the storage model's own
  docstring) but no query code uses it yet; wiring that up is explicitly deferred until Document
  itself is implemented, not a prerequisite for it.
- **Repository mapping:** **Modify** (§9.4) — file-storage/versioning foundation is
  genuinely reusable; the `matter_id` → `file_id` relationship redirect is the required change.
- **Open engineering decisions:** `matter_id`→`file_id` migration mechanics (Required ADR #10);
  confidentiality field/mechanism; full status vocabulary.

#### Document Version

- **Purpose / business meaning (CBR):** historical document integrity — §2: "Document versions —
  Historical document integrity." §4 §History group's general principle (rule 42) and this
  specification's own cross-domain invariant ("Document history is immutable") apply directly.
- **Repository constraint (RC — Existing, already well-designed for this purpose):**
  `document_versions` (`document.py`) exists — `document_id`, `version_number` (unique per
  document via a composite `UniqueConstraint`), `file_storage_record_id`, `change_summary`,
  `created_at`/`created_by`. **Deliberately no `updated_at`/`updated_by`/`AuditMixin`** — the
  model's own docstring explains this: a version row, once created, is not meant to be mutated at
  all, which is *already* a correct implementation of the immutability invariant, not a gap.
  Similarly, `documents` deliberately has no `current_version_id` back-pointer (avoiding a
  circular FK for a denormalization with no proven query need) — "latest version" is derived by
  querying `document_versions` ordered by `version_number` descending. Both of these are sound,
  intentional design choices — **RC that should be preserved, not "fixed."**
- **Business invariant confirmation (CBR):** this table already satisfies "Document history is
  immutable" — the required work here is a `file_id` redirect at the `Document` level (above),
  not a `DocumentVersion` redesign.
- **Repository mapping:** **Modify** (§9.4) — no structural change to `DocumentVersion` itself is
  indicated by the frozen architecture; it is genuinely one of the closer-to-done entities in this
  specification.
- **Open engineering decisions:** none identified beyond those already listed under Document
  above (this entity's own design is sound as-is).

---

### 24.10 Workflow & Tasks

#### Workflow

- **Purpose / business meaning (CBR):** internal process management — §4 rule 32: "Internal
  workflow status is distinct from government status." This is one of this specification's most
  important cross-domain invariants: Workflow and Government Process (§24.11) must never be
  collapsed into one status field, however tempting that simplification might look.
- **Repository constraint (RC — a real, working, but entirely unwired framework):** two layers
  already exist. (1) A pure, framework-free state-machine engine —
  `application/workflow/engine.py`'s `WorkflowDefinition`/`Transition`/`WorkflowEngine`
  (`can_transition()`/`transition()`, raising `WorkflowError` on an invalid move) — with **no
  persistence of workflow instances**, by design. (2) The DB-side counterpart —
  `workflow_definitions`/`workflow_states`/`workflow_history` (`workflow.py`) — a definition
  owns a set of named states (`is_initial`/`is_final` flags) and `workflow_history` records each
  transition (polymorphic `entity_type`+`entity_id`, `from_state_id`→`to_state_id`, `event`,
  `transitioned_by`, `transitioned_at`, `notes`). **Confirmed by direct repository search: no
  route, service, or feature currently wires the engine to these tables, or to any Matter/File
  lifecycle** — this is genuinely "framework exists; domain wiring absent" (§5's Workflow row),
  not a misreading.
- **Required work (CBR + IC):** the framework itself should be **reused, not rebuilt** (§9.2's
  general instruction applies directly here) — the engineering work is wiring a real
  Matter/File-scoped workflow definition to this existing machinery, not designing a new state
  engine. The polymorphic `entity_type`+`entity_id` pattern on `workflow_history` (no FK
  constraint, by documented design — same trade-off as `activity_logs`/`qr_code_records`) already
  supports attaching workflow to either Matter or File without a schema change; which one (or
  both) actually gets used is the **ED** decision flagged in §24.8.
- **Configuration (CBR):** Workflow templates are organization-configurable per §6.2 ("Workflow
  Templates" explicitly named).
- **Repository mapping:** **Modify/wire** (§9.4) — this is a "connect existing infrastructure,"
  not "build from scratch," item; calibrate implementation effort accordingly.
- **Open engineering decisions:** Matter-vs-File attachment point (shared with File, §24.8); which
  concrete workflow definitions/states an Organization needs (business/config decision, not
  architectural).

#### Task

- **Purpose / business meaning (CBR):** action management — §2: "Tasks — Action management."
- **Repository constraint (RC):** `tasks` (`scheduling.py`) exists — `matter_id` (nullable),
  `title`, `description`, `assigned_to`, `due_at`, `status` (default `open`), `priority` (default
  `normal`), `completed_at`, plus `AuditMixin`. This is a genuine, working task-list model, not a
  stub — but it is Matter-scoped only (no File-level task attachment) and has no relationship to
  the Workflow engine above (a Task's `status` is independent free-text, not a
  `WorkflowState`-driven transition).
- **Gap vs. frozen architecture (RC → ED):** whether Tasks should become File-scoped (in addition
  to or instead of Matter-scoped, once File exists), and whether Task status should be
  reconciled with or kept independent from the Workflow engine's state model, are both
  **ED — unresolved**; not addressed by §4's invariants at this level of detail.
- **Repository mapping:** **Modify** (§9.4) — the existing table is a reasonable foundation;
  scope/relationship-to-Workflow questions are the open work, not a rebuild.
- **Open engineering decisions:** File-level Task attachment; Task-status vs. Workflow-state
  relationship.

---

### 24.11 Government Processes

#### Government Process

- **Purpose / business meaning (CBR):** external authority processing — §4 rule 33: "Government
  Process is its own domain concept." §4 rule 32 (repeated for emphasis, since it is the single
  most-flagged risk in §13's Risk Register at "🔴 Critical"): internal Workflow status must never
  be collapsed into, or confused with, Government Process status — they track fundamentally
  different things (the firm's own internal handling vs. an external authority's actual
  processing state, which the firm does not control and often cannot even directly observe).
- **Repository constraint (RC):** **does not exist** — confirmed, no authority/government-process/
  government-office table anywhere in the schema. This is a genuinely new domain area for the
  repository, not a redesign of an existing one.
- **Fields (ED — unresolved):** the owning Matter/File, an authority/office reference,
  a process-type vocabulary (organization-configurable per §6.2's "Government Process Types"),
  a reference/application number (the authority's own identifier for the submission — distinct
  from this system's File Number), and a status are all plausible but not frozen at the field
  level.
- **Relationships (CBR):** Government Process ⟷ Matter/File (dependency shown in §5 as
  "Property/Matter" — exact attachment granularity is the same open question as Workflow's,
  §24.10). Government Process ⟷ Government Event is one-to-many (below).
- **Repository mapping:** **New** (§9.4/§10.A `government_processes`).
- **Open engineering decisions:** attachment granularity (Matter vs. File); process-type
  vocabulary; whether/how the authority's own reference number is validated or free-text.

#### Government Event

- **Purpose (CBR):** §4 rule 34: "Government events must retain historical information" — the
  append-only record of what actually happened at the authority over time (a status change, a
  hearing date, a query raised, an approval, a rejection), analogous in spirit to
  `document_versions`' immutability but for external-process history rather than document content.
- **Repository constraint (RC):** does not exist. The existing `workflow_history` table's
  append-only, polymorphic-entity, `transitioned_by`/`transitioned_at`/`notes` shape is a
  reasonable **IC** precedent to draw on structurally, but Government Event must remain its own
  table per §4 rule 33 — it must not literally reuse `workflow_history`, which would re-collapse
  the exact distinction rule 32 protects.
- **Fields (ED — unresolved):** event type/description, date, and any authority-supplied
  reference are plausible but not frozen.
- **Repository mapping:** **New** (§9.4/§10.A `government_events`).
- **Open engineering decisions:** event-type vocabulary; exact field list.

---

### 24.12 Communication & Timeline

#### Communication

- **Purpose / business meaning (CBR):** client/party interaction history — §2: "Communications —
  Client/party interactions." §4 rule 39: Communication, Task, Follow-up and Activity are four
  distinct concepts — none is a substitute for another, and none should be silently merged for
  implementation convenience.
- **Repository constraint (RC):** **does not exist as a finalized entity** — no
  call-log/email-log/meeting-note table exists in the schema. (`Appointment` in `scheduling.py` is
  a scheduling record — a *planned future* meeting — not a Communication's historical record of
  *what was actually discussed*; the two are related but distinct, consistent with rule 39's "Task"
  vs. "Communication" separation.)
- **Fields (ED — unresolved):** the owning Matter, participants (which Parties/Representatives/
  Users were involved — plausibly a many-to-many join, not a single field, given multiple
  participants are realistic for a meeting or conference call), a channel (call/email/meeting/
  letter — organization-configurable, analogous to other type vocabularies), a summary/notes
  field, and occurrence timestamp are plausible but not frozen at the field level.
- **Relationships (CBR):** Communication ⟷ Matter (many-to-one, at minimum). Communication ⟷
  Party/Representative participants (**ED**, exact join structure unresolved).
- **Repository mapping:** **New** (§9.4/§10.A `communications`).
- **Open engineering decisions:** participant-join structure; channel vocabulary; exact field
  list.

#### Activity

- **Purpose / business meaning (CBR):** business history — §2: "Activities — Business history."
  §4 rule 41: Audit is distinct from Activity (two different concepts, not two names for the same
  mechanism).
- **Repository constraint (RC — Existing foundation, genuinely close to what's needed):**
  `activity_logs` (`activity.py`) exists — `entity_type`+`entity_id` (polymorphic, no FK, same
  documented trade-off as `workflow_history`/`qr_code_records`), `action`, `actor_id`,
  `occurred_at`, `details` (JSONB). This already coexists as a **structurally distinct** mechanism
  from `audit_logs` in the same module — i.e. §4 rule 41's Activity-vs-Audit separation is
  **already correctly implemented at the schema level today**, which is a genuinely positive
  finding worth stating plainly rather than only cataloguing gaps: the repository did not conflate
  these two concepts, even before this specification existed.
- **Gap vs. frozen architecture (RC → ED):** the polymorphic `entity_type`/`entity_id` pattern
  needs to cover the new entities this specification introduces (Matter/File/Document/
  GovernmentProcess/etc.) — a straightforward extension of an existing, working pattern, not a
  redesign (**IC**, not **ED**).
- **Repository mapping:** **Modify** (§9.4) — extend entity-type coverage; no structural change
  to the table itself is indicated.

#### Timeline

- **Purpose / business meaning (CBR):** a unified historical view — §2: "Timeline — Unified
  historical view." §4 rule 40: "Timeline is a unified view, not a replacement for underlying
  records" — Timeline must be a *read/query-time composition* of Task, Document, Communication,
  Government Event, Payment, Status Change, and Activity records (§7 Phase 6's exit criterion
  lists exactly this set, explicitly "without collapsing those into one underlying entity").
- **Repository constraint (RC):** does not exist as an operational feature (§9.4: "Not finalized
  as operational feature"). Given rule 40, this is **correctly** absent as its own table — Timeline
  is not supposed to be a new persisted entity at all; it is a query/API-composition concern over
  the entities that already do or will exist (Task, Document, DocumentVersion, Communication,
  GovernmentEvent, Payment, Matter status changes via `workflow_history`/`matter_statuses`,
  ActivityLog).
- **Classification (CBR, important to state explicitly):** Timeline should be specified and
  implemented as a **read-side query/API concern (derived), not a new database table** — this
  follows directly from rule 40 and should not be reopened as "should we have a `timeline_entries`
  table" without a specific, demonstrated query-performance need the composed-query approach
  cannot meet.
- **Repository mapping:** **New API/UI** (§9.4) — no new persistence table implied.
- **Open engineering decisions:** the exact composition/query mechanism (a `UNION`-style query
  across source tables, an application-layer aggregator, or an eventual materialized/denormalized
  read model if performance later demands it) is **IC — can decide during implementation** per
  §12's own classification of "Timeline implementation."

---

### 24.13 Commercial & Finance

**Cross-cutting note (CBR):** §4 rule 35 is the organizing principle for this entire group:
"Quotation, Commercial Scope, Charges, Invoice and Payment are separate concepts" — §7 Phase 7's
chain (`Quotation → Commercial Scope → Charges → Invoice → Payment → Payment Allocation →
Refund`) must not be compressed into fewer entities for implementation convenience, however
tempting a single "amount owed" field on Matter might look (§7 Phase 7 says this explicitly:
"Finance should not be implemented as a generic 'amount' field attached to Matter"). §4 rule 36:
professional fees must remain distinguishable from government/third-party money passing through
the firm. §4 rule 37: payment allocation must be separately represented where required. §4 rule
38: historical financial information must not be silently overwritten.

#### Commercial Scope

- **Purpose (CBR):** the accepted commercial baseline for a Matter — the fee/scope arrangement
  actually agreed to, distinct from the Quotation that proposed it (a Quotation can be revised
  before acceptance; once accepted, Commercial Scope is the settled baseline the Matter operates
  under).
- **Repository constraint (RC):** **does not exist** — confirmed, no commercial-scope/fee-
  agreement table anywhere in the schema; `invoices`/`payments` exist but represent billing
  execution, not the underlying agreed scope those bills should be checked against.
- **Fields (ED — unresolved):** fee structure (fixed/hourly/milestone-based — **not frozen**,
  do not assume a single billing model), currency, and the accepted-from Quotation reference are
  plausible but not specified at the field level.
- **Relationships (CBR):** Commercial Scope ⟷ Matter (one-to-one or one-to-few — **ED** whether a
  Matter can have its Commercial Scope revised/re-baselined over time as a new row or must be
  mutated in place, which interacts with rule 38's non-silent-overwrite requirement). Commercial
  Scope ⟷ Quotation (traces back to the accepted proposal).
- **Repository mapping:** **New** (§9.4/§10.A `commercial_scopes`).
- **Open engineering decisions:** fee-structure modeling; revision/re-baselining mechanism
  consistent with rule 38.

#### Charge

- **Purpose (CBR):** an amount owed/incurred — §2: "Charges — Amounts owed/incurred." Distinct
  from Invoice (a Charge is a line item of liability; an Invoice is the billing document that
  presents one or more Charges to the client for payment) and from Expense (a Charge is generally
  professional-fee-side; an Expense is a cost the firm incurred, e.g. a government filing fee paid
  on the client's behalf — §4 rule 36's professional-fee-vs-third-party-money distinction maps
  onto the Charge/Expense split).
- **Repository constraint (RC):** does not exist as its own entity; today's `invoices` table
  bundles `amount`/`tax_amount`/`total_amount` directly on the invoice itself, with no underlying
  line-item/charge breakdown.
- **Fields (ED — unresolved):** description, amount, a charge-type/category (organization-
  configurable, per §6.2's general vocabulary-configurability pattern extended here — not
  explicitly named in §6.2's example list but consistent with it), and the owning Matter (or File —
  **ED**, same granularity question as elsewhere).
- **Relationships (CBR):** Charge ⟷ Matter (many-to-one, at minimum). Charge ⟷ Invoice: **ED**
  whether a Charge must be invoiced before it "counts," or can exist as an un-invoiced liability
  record on its own.
- **Repository mapping:** **New** (§9.4/§10.A `charges`).
- **Open engineering decisions:** Charge-type vocabulary; Charge↔Invoice cardinality/timing;
  File-vs-Matter attachment.

#### Expense

- **Purpose (CBR):** cost tracking — §2: "Expenses — Costs incurred." Per rule 36, must remain
  distinguishable from professional fees (Charge) — an Expense is money the firm spent (often
  reimbursable by the client, e.g. government fees, courier costs, stamp duty paid on the client's
  behalf).
- **Repository constraint (RC):** does not exist.
- **Fields (ED — unresolved):** description, amount, category (organization-configurable per
  §6.2's "Expense Categories," explicitly named there), whether reimbursable, and the owning
  Matter/File are plausible but not specified at the field level.
- **Relationships (CBR):** Expense ⟷ Matter/File (**ED** on exact granularity, consistent with the
  pattern elsewhere). Expense ⟷ Invoice: **ED** whether reimbursable Expenses flow into an
  Invoice's line items or are tracked/settled separately.
- **Repository mapping:** **New** (§9.4/§10.A `expenses`).
- **Open engineering decisions:** category vocabulary; Expense↔Invoice relationship; Matter-vs-
  File attachment.

#### Invoice

- **Purpose (CBR):** billing — the document presented to the client requesting payment for
  Charges (and possibly reimbursable Expenses) incurred.
- **Repository constraint (RC — Existing, substantial foundation):** `invoices` (`financial.py`)
  exists — `invoice_number` (unique), `matter_id`, `client_id` (direct — will need to become a
  Party reference once Party exists, mirroring the Matter/`client_id` gap, though Invoice's own
  redesign is secondary to Matter's), `amount`/`tax_amount`/`total_amount` (all `Numeric(12,2)`,
  all CHECK'd non-negative), `status` (default `draft`), `issued_at`/`due_at`.
- **Gap vs. frozen architecture (RC → ED):** the amounts are direct columns on the Invoice itself,
  with no underlying Charge/Expense line-item breakdown — consistent with §4 rule 35's required
  separation, Invoice should ideally *derive* its totals from the Charges/Expenses it bills, not
  hold an independently-entered lump sum. Whether this is a required schema change (adding an
  Invoice-line-item join to Charge/Expense) or the existing direct-amount columns are retained
  alongside a *reporting* reconciliation against Charges/Expenses is **ED — unresolved**, tracked
  under Required ADR #13 "Financial boundary."
- **Repository mapping:** **Modify** (§9.4) — genuinely closer to done than most Finance entities;
  the `client_id`→Party redirect and the Charge/Expense line-item question are the open work.
- **Open engineering decisions:** Charge/Expense line-item linkage (Required ADR #13);
  `client_id`→Party redirect timing (tied to the Matter/Party migration overall, Required ADR
  #20).

#### Payment

- **Purpose (CBR):** money received — §2: "Payments — Money received."
- **Repository constraint (RC — Existing):** `payments` (`financial.py`) exists —
  `invoice_id` (nullable — already correctly allows a Payment not tied to a specific Invoice, a
  reasonable real-world case), `matter_id`, `client_id`, `payment_method_id` (lookup table,
  already exists), `amount` (CHECK'd positive), `paid_at`, `reference_number`, `status` (default
  `completed`). `Receipt` (also `financial.py`) already exists as the acknowledgment document for
  a Payment, with its own `receipt_number` and optional `file_storage_record_id` — genuinely
  reusable.
- **Gap vs. frozen architecture (RC → ED):** no `payment_allocations` concept exists — a single
  Payment today has at most one `invoice_id`, which cannot represent §4 rule 37's requirement that
  "payment allocation must be separately represented where required" (e.g. one Payment covering
  parts of multiple Invoices, or a Payment applied partially to Charges directly rather than a
  full Invoice).
- **Repository mapping:** **Modify** (§9.4) — the base Payment/Receipt model is sound; Payment
  Allocation is the required addition, not a Payment redesign.
- **Open engineering decisions:** none beyond Payment Allocation itself (below) and the
  `client_id`→Party redirect (shared with Invoice).

#### Payment Allocation

- **Purpose (CBR):** §4 rule 37's explicit requirement — the mechanism by which one Payment's
  amount is distributed across one or more Invoices/Charges when the simple "one Payment, one
  Invoice" case doesn't hold.
- **Repository constraint (RC):** **does not exist** — confirmed.
- **Fields (ED — unresolved):** Payment reference, target (Invoice or Charge — **ED**, unresolved
  which), allocated amount. A CHECK/invariant that the sum of a Payment's allocations never
  exceeds the Payment's own amount is a strong candidate for a database-level constraint (§4
  rule 38's non-silent-mutation spirit, plus §20's Definition of Done explicitly wanting database
  constraints "where appropriate") but is not itself frozen as a requirement here — flagged as a
  strong recommendation, not asserted as CBR.
- **Repository mapping:** **New** (§9.4/§10.A `payment_allocations`).
- **Open engineering decisions:** allocation target (Invoice vs. Charge vs. either); the
  sum-constraint mechanism.

#### Refund

- **Purpose (CBR):** money returned — §2: "Refunds — Money returned," priority "Medium" (the
  only Finance-group item not marked "High," per §2's table — a legitimate signal this can follow,
  not block, the rest of the Finance chain).
- **Repository constraint (RC):** does not exist.
- **Fields (ED — unresolved):** the originating Payment, amount, reason, and date are plausible
  but not specified at the field level.
- **Relationships (CBR):** Refund ⟷ Payment (many-to-one, at minimum — a Payment could
  theoretically be partially refunded more than once, **ED** whether that's supported).
- **Repository mapping:** **New** (§9.4/§10.A `refunds`).
- **Open engineering decisions:** partial/multiple-refund support; exact field list.

---

### 24.14 Advanced Security

**Scope note (CBR):** §7 Phase 8 explicitly defers this group ("Do not implement until the core
domain is stable") — the entries below specify the *concept*, per §5/§2's Feature Catalogue
priorities, without prescribing implementation before the Matter/File/Document/Finance spine
exists to secure.

#### Confidentiality

- **Purpose (CBR):** information sensitivity — §2: "Confidentiality — Information sensitivity,"
  priority "High." §4 rule 45 names Matters/Files/Documents specifically as needing finer-grained
  access beyond Organization-level.
- **Repository constraint (RC):** **does not exist** — no confidentiality-label or access-grant
  table anywhere in the schema; `RbacAuthorizationService` today checks only role→permission
  membership (`require_permission(user, permission)`, confirmed directly in
  `infrastructure/auth/rbac_authorization_service.py`), with no per-resource-instance dimension at
  all — a user who holds `matters:read` can read *every* Matter, not a permitted subset.
- **Mechanism (ED — must decide before security implementation, §12/Required ADR #18):** whether
  finer-grained access is implemented as (a) a confidentiality-label vocabulary
  (organization-configurable per §6.2) checked alongside role/permission, (b) explicit per-Matter/
  File/Document access-grant rows (a Team- or User-level allow-list), (c) Team-based visibility
  inherited from Matter assignment, or some combination, is genuinely open. This decision also
  determines how `JwtAuthenticationProvider`'s existing live-role-rederivation behavior (it
  re-reads the caller's roles from the DB on every request rather than trusting JWT claims — a
  detail worth preserving in whatever extension is built, since it's what makes a
  deactivated-user or role-change take effect immediately) should be extended to cover
  instance-level grants too.
- **Repository mapping:** **New** (§9.4/§10.A confidentiality/access records).
- **Open engineering decisions:** the entire access-control mechanism (Required ADR #18);
  interaction with the still-open Organization/tenant-scoping mechanism (§24.1), since both are
  layers of the same authorization stack and should likely be designed together, not sequentially
  bolted on.

#### Audit

- **Purpose (CBR):** immutable accountability — §2: "Audit — Immutable accountability," the only
  row marked "Critical" priority in the entire Security domain. §4 rule 42: historical actions
  remain attributable to the original actor. §4 rule 46: historical security/audit information
  must not be silently altered. §4 rule 41 (repeated from §24.12 for completeness here): Audit is
  distinct from Activity.
- **Repository constraint (RC — Existing, correctly designed, genuinely reusable):** two-layer
  mechanism, both already present and already *not* conflated with each other or with
  `ActivityLog`: (1) `AuditLogger` port (`application/interfaces/audit.py`,
  `record(actor, action, resource_type, resource_id, metadata)`) with `LoggingAuditLogger`
  (structured JSON to an `app.audit` log channel) as the current concrete implementation — this is
  Stage-1-era, deliberately deferring a DB table per ADR-0007. (2) `audit_logs` DB table
  (`activity.py`), added by ADR-0009 explicitly reversing ADR-0007 once Stage 2's schema charter
  asked for it — `actor_id`, `action`, `resource_type`, `resource_id`, `audit_metadata` (JSONB,
  mapped to a DB column literally named `metadata` to match the port's parameter name exactly),
  `created_at`. **No `SqlAlchemyAuditLogger` implementation exists yet** — `LoggingAuditLogger`
  (log-only) is still the only concrete `AuditLogger` wired in; the table exists and is shaped to
  receive exactly this port's calls the moment a SQL-backed implementation is written.
- **Gap vs. frozen architecture (RC → ED):** none identified at the mechanism level — this is
  §9.4's "Existing foundation/table" row, correctly assessed as **Modify**, not **New**. The
  required work is (a) writing the `SqlAlchemyAuditLogger` implementation so audit events actually
  persist to `audit_logs` rather than only structured logs, and (b) ensuring every sensitive
  action this specification's new entities introduce (Party/Matter/File/Document/Finance
  create/update/status-change/relationship-change, per §4 rule 42 and §17.9's mandatory test list)
  actually calls `AuditLogger.record()` — an *instrumentation coverage* task across the new
  domain, not a new audit *mechanism*.
- **Repository mapping:** **Modify** (§9.4) — genuinely one of the strongest existing foundations
  in the repository for this specification's purposes.
- **Open engineering decisions:** none at the mechanism level; only the coverage/instrumentation
  work across new entities, which is implementation-phase work, not a specification-level
  decision.

---

### 24.15 Reporting & Integrations

Both explicitly lower-priority (§2: Reporting "Medium," Integrations "Later") and explicitly
deferred by §7 Phase 8/§14. No entity-level specification is written here beyond what §2/§5/§14
already establish, consistent with "do not invent workflows/fields for scope that is intentionally
not yet being built." **DEF — Deferred**, both in full. When these are eventually prioritized,
they should be specified against whatever concrete Matter/File/Document/Finance schema actually
exists by then, not against speculation written now — writing detailed Reporting/Integration specs
today would itself violate this document's own "avoid speculative fields/invented workflows"
instruction.

---

## 25. Cross-Domain Invariant Verification

**Terminology note (added during this correction pass, to prevent confusion with §4):** the
**14** items below are a distinct, purpose-built cross-domain checklist — the specific set of
cross-cutting invariants this specification's own governing review brief named for verification —
not a renumbering, subset, or replacement of §4's **46** numbered business rules. The two lists
serve different purposes: §4 is the exhaustive, frozen business-rule set (the authoritative
source); this table is a narrower, cross-domain-focused verification lens applied *on top of* §4
for this review pass, most of whose rows draw on one or more specific §4 rule numbers (cited in
the "Preserved in §24?" column where a specific rule underlies the row) without being a complete
or exclusive accounting of §4. No mapping between "14" and "46" is asserted beyond what each row
explicitly cites — nothing here should be read as implying only 14 of the 46 rules matter, or that
these 14 are somehow a "core" tier above the other 32.

Each invariant below is checked against both the entity specifications in §24 and the current
repository, not merely restated.

| # | Invariant | Preserved in §24? | Repository status |
|---|---|---|---|
| 1 | One Party can participate in multiple Matters | Yes — §24.7 MatterParty, many-to-many, explicit | RC: currently impossible (`matters.client_id` is single-valued) |
| 2 | A Matter can have multiple Parties | Yes — §24.7 MatterParty | RC: currently impossible |
| 3 | A Matter can have multiple Properties | Yes — §24.7 MatterProperty | RC: currently impossible (`matters.property_id` is single, nullable) |
| 4 | Property is not owned by Matter | Yes — §24.3 Property, explicit independence (rule 15–17) | RC: `properties` has no `matter_id` today, so this one is not violated by the current schema — only the *reverse* direction (`matters.property_id`) needs correcting |
| 5 | Revenue and City Survey records remain distinct | Yes — §24.4, both specified as separate new entities, never merged | RC: neither exists yet; no conflation risk in the current schema because there is nothing to conflate |
| 6 | Land and Property Unit are not conflated | Partially — §24.3 Land is specified as distinct from Property, but the exact Land↔Property-Unit boundary is explicitly left **ED** (coupled to the Gujarat-records ADR) | RC: `properties` has no Land/Unit distinction today |
| 7 | Matter and File have distinct lifecycle semantics | Yes — §24.7 Matter and §24.8 File both specify independent lifecycle/status vocabularies; §4 rule 3/5 (Matter needs no File; File needs a Matter) preserved verbatim | RC: File does not exist yet, so no current-schema conflict |
| 8 | File numbering is concurrency-safe | Specified as a required, unresolved decision (§24.8, §12, §17.5's mandatory test) — **not yet designed**, correctly flagged rather than assumed solved | RC: no numbering mechanism exists to evaluate |
| 9 | Document history is immutable | Yes — §24.9 Document Version, and confirmed **already correctly implemented** in the current schema (no `updated_at`/`AuditMixin` on `document_versions`, by design) | RC: none — this one is already satisfied today |
| 10 | Workflow state is distinct from government-process status | Yes — §24.10/§24.11 repeatedly cross-reference rule 32 as the organizing constraint for both | RC: neither is wired to the other in the schema (`workflow_history` and the not-yet-built `government_events` are structurally separate), so no current conflation exists |
| 11 | Organization/tenant isolation is mandatory | Yes — asserted throughout §24.1 onward as a cross-cutting requirement | RC: **not enforced anywhere today** — this is the single largest gap in the entire specification, called out repeatedly (§24.1, §1.4, §13) rather than glossed over |
| 12 | Authorization cannot be bypassed via repositories, APIs, background jobs, search, or documents | Specified as a requirement at the mechanism-decision level (§24.1 Organization, §24.14 Confidentiality) but the **actual enforcement point is an unresolved ED** — today's `RbacAuthorizationService` is invoked at the service/route layer only; whether background jobs, the generic `SqlAlchemyRepository.list()`, and file-storage reads independently re-check authorization is not yet designed and must not be assumed solved by inspection alone | RC: `SqlAlchemyRepository` has no authorization awareness at all today — it is a generic CRUD layer, correctly so, meaning authorization must be enforced above it consistently, not assumed to happen "somewhere" |
| 13 | Sensitive changes are auditable | Yes — §24.14 Audit, and asserted per-entity throughout §24 (each entity's own Audit bullet) | RC: the mechanism exists and works (§24.14); coverage across the *new* entities this specification introduces is the open instrumentation task, not a missing mechanism |
| 14 | Financial history cannot be silently mutated | Yes — §24.13, rule 38 cited explicitly under Commercial Scope and Payment Allocation | RC: `invoices`/`payments` have no explicit protection against in-place mutation of historical amounts today beyond `OptimisticLockMixin`'s concurrency check (which prevents *concurrent* overwrites, not *authorized* silent edits) — flagged as a real gap the Finance ADR (#13) should address, not assumed handled |

**Summary:** no invariant in this list is contradicted by §24's specification content itself. Every
gap identified above is a **repository gap** (the current schema doesn't yet implement the
invariant) or a **genuinely unresolved engineering decision** (the mechanism isn't chosen yet) —
none is a case where this specification's own entity definitions conflict with the frozen business
architecture. Invariant #11 (tenant isolation) and #12 (authorization bypass surface) are the two
most consequential open items and should be prioritized accordingly, consistent with §1.4/§13/§23
naming Organization-as-tenant-boundary as the top risk.

---

## 26. Consolidated Unresolved Engineering Decisions

This consolidates every **ED** item raised across §24 into one list, organized by whether it must
be resolved before database/API implementation begins or can safely wait. This extends, rather
than duplicates, §12's earlier table — §12 was written before the entity-level detail existed;
this list is what that detail actually surfaced.

**Must resolve before implementation** (blocks correct schema/API design):

1. Party subtype-modeling strategy (§24.2; Required ADR #2).
2. Organization/tenant representation and enforcement mechanism (§24.1; Required ADR #1, #19).
3. Property vs. Land vs. Property-Unit boundary, and the Property Record Reference mechanism
   (generic linking table vs. direct FKs) (§24.3/§24.4; Required ADR #3, #4, #6).
4. Scheme hierarchy storage mechanism (§24.5; Required ADR #7).
5. Revenue/City-Survey/TP-FP exact field sets (§24.4; Required ADR #5).
6. File numbering algorithm and concurrency strategy (§24.8; Required ADR #9) — flagged as
   concurrency-*critical*, not cosmetic, given §17.5's mandatory concurrent-creation test.
7. Document/File relationship migration mechanics — the `matter_id`→`file_id` redirect sequencing
   (§24.9; Required ADR #10, #20).
8. Authorization granularity and enforcement-point mechanism, including how it composes with
   tenant isolation (§24.14; Required ADR #18) — this is the most consequential open item overall,
   per §25's invariant-verification table.
9. Financial ledger boundary — Charge/Expense line-item linkage to Invoice, and the
   non-silent-mutation mechanism for historical financial data (§24.13; Required ADR #13).
10. Matter's `client_id`/`property_id`/`matter_type_id` retirement sequencing (§24.7; Required ADR
    #20, the general migration-strategy ADR).

**Can be decided during implementation** (does not block correct upstream design):

11. Document storage provider strategy beyond what's already implemented (§24.9 — the current
    `LocalFileStorage`/`FileStorageRecord` foundation is sound and swappable later).
12. Timeline's exact composition/query mechanism (§24.12 — already classified IC in §12, confirmed
    here).
13. Workflow's concrete state/transition definitions per Organization (§24.10 — business/config
    content, not architecture).
14. Configuration versioning mechanism (carried forward from §12, unchanged by §24's findings).
15. Party-merge/deduplication tooling (§24.2 — a UX/operational concern layered on top of a
    correctly-designed Party table, not a prerequisite for one).
16. Whichever vocabulary values (Classification, Work Type, Charge/Expense categories, Government
    Process types, Communication channels, PartyRelationship types) an Organization actually needs
    — seed/config data, not schema.

**Deferred** (§14, §24.15, unchanged): complex accounting, full ERP, elaborate CRM, automated
legal advice, complex joint-development ownership, universal government API integrations,
excessively specialized property rules, AI document interpretation as a core dependency, and the
entire Reporting/Integrations domain group.

---

## 27. Specification Validation & Readiness Assessment

**Checked against the authoritative business architecture (§4's frozen rules):** every rule in §4
is either directly cited as the CBR basis for a §24 entity, or — where a §24 entity's scope simply
doesn't touch a given rule — left untouched. No rule was reinterpreted, weakened, or silently
narrowed. Verified by direct cross-reference while drafting each §24 subsection (each cites the
specific rule number(s) it implements), not asserted after the fact.

**Checked against the current repository (`main`, this inspection):** every §24 entity's
Repository Constraint / Repository Mapping subsection is grounded in a specific, named file read
directly during this pass (`backend/src/app/infrastructure/persistence/models/*.py`, the relevant
`application/interfaces/*.py` ports, `ADR/0001`–`0020`, `docs/ImplementationLog/`). No repository
fact in §24 is asserted without a citable source.

**Contradictions identified:** none found between §1–23 (the existing strategic report) and this
pass's direct repository inspection — the existing report's factual claims about the schema
(Matter's `client_id`/`property_id`, Document's direct `matter_id`, the absence of Organization/
Party/File/Scheme/Enquiry/Quotation/GovernmentProcess/Communication/CommercialScope/Charge/
PaymentAllocation/Refund tables) were all independently re-verified and confirmed accurate, not
taken on faith.

**Omissions found and corrected by this pass:** the existing report (§1–23) established *what*
needs to exist (feature catalogue, roadmap, risk register, mapping table) but did not yet specify
*how* each entity should be shaped at the field/relationship/lifecycle/authorization/audit level —
that was §15's own stated gap, and is what §24–26 now fill. No other material omission was found;
§1–23's roadmap/risk/testing/ADR sections remain accurate and are not duplicated here.

**Accidental business reinterpretations:** none introduced. Every place this pass could have been
tempted to "fill in" a plausible-sounding field or workflow (Party field lists, File status
vocabulary, Government Process fields, Confidentiality mechanism, etc.) is instead explicitly
marked **ED** rather than asserted as fact — checked specifically for this failure mode across all
30+ entities in §24, not just spot-checked.

**Places the existing schema incorrectly influenced the model:** none found *in this
specification* — §24 consistently treats the existing schema as **RC** (a constraint/starting
condition to reconcile against) rather than **CBR** (a source of business truth), per the task's
own governance instruction. The one place this distinction most needed active vigilance was
Matter (§24.7), where the temptation to treat `client_id`/`property_id`/`matter_type_id` as
"probably fine, minor tweak" is strongest — this pass instead treated §11.1's own worked example
(which explicitly calls out this exact temptation) as authoritative and specified the
MatterParty/MatterProperty/MatterClassification/MatterWorkType redesign as required, not optional.

**Unresolved engineering decisions:** consolidated in §26 above — 10 must-resolve-before-
implementation items, 6 can-decide-during-implementation items.

**Dependency ordering coherence:** §24's group ordering (Organization & Identity → Party →
Property & Land → Gujarat Records → Scheme → Enquiry & Quotation → Matter → File & Numbering →
Document Management → Workflow & Tasks → Government Processes → Communication & Timeline →
Commercial & Finance → Advanced Security → Reporting & Integrations) matches the dependency order
given for this task and is internally consistent: no group's specification depends on an entity
from a *later* group (verified by re-reading each group's Relationships bullets for forward
references — none found; where a later concept is mentioned, as with the Party/Property/Scheme
overlap notes, it is flagged as context, not depended upon).

**Tenant isolation, authorization, audit, history, and migration concerns across the model:** each
is represented per-entity throughout §24 (Identity & Tenant Ownership, Authorization, and Audit
bullets on every entity that has one) and consolidated in §25's invariant table and §26's
must-resolve list, rather than only addressed once at the top and assumed to propagate.

**No source code was modified during this review** — this pass was documentation/specification
only, consistent with the Documentation Manager role boundary this task specified.

### Readiness for Independent Technical Verification

This specification is **not** self-certifying — the following is a factual status report, not an
approval:

- Every CBR-classified statement traces to a specific §4 rule or §2/§5 catalogue entry.
- Every RC-classified statement traces to a specific file read during this inspection.
- Every ED-classified item is stated as unresolved, not resolved by assumption.
- §25's cross-domain invariant table gives an independent reviewer a direct checklist to verify
  this pass's own claims against, rather than having to reconstruct one from scratch.
- The 10 must-resolve-before-implementation items in §26 are exactly the set of decisions the
  Required ADRs (§21) need to close before database/API contract work (§16) can begin.

**This document does not itself constitute approval of the specification, and does not authorize
implementation.** It is submitted, per this task's governing instructions, for Independent
Technical Verification before any Required ADR is finalized or any database/API implementation
work is authorized.