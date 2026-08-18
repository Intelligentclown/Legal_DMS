# Business Requirements & Original Vision Plan

*Authored by the project owner before implementation began. Preserved here verbatim in
structure and content (reformatted from the original `.docx` for readability only — no
substantive wording changed) as the canonical reference for Stage 4+ business-feature
planning.*

> **Status note (added when this document was committed):** This is a **pre-implementation
> vision document**, not a current-state description. Stages 0–3 built the technical
> foundation (architecture, database schema, authentication) with **zero business features**
> by deliberate charter — see [`AI_BOOTSTRAP.md`](../AI_BOOTSTRAP.md) and
> [`Roadmap.md`](Roadmap.md). This document is what Stage 4 planning (Matter Management,
> Client Management, Document Automation, etc.) should start from, **once explicitly
> authorized by the project owner** — not before. Where this plan's assumptions have already
> been overtaken by decisions made during Stages 1–3 (see the review notes at the end of this
> document), those later decisions govern; this document is not silently authoritative over
> the actual repository.
>
> **Editorial note (added at the project owner's request):** The original text below named
> a specific advocate/practice as the initial reference client. That reference has been
> generalized here, since the system is not scoped to a single practitioner and is intended
> for use by multiple users/practices once complete. This is the one departure from this
> document's "preserved verbatim" framing above — flagged here rather than silently edited,
> consistent with this repository's documentation conventions.

For a legal documentation practice.

## 1. Executive Summary

This document outlines a complete software architecture and operational plan for building a
centralized Legal Document & Matter Management System for a legal documentation business.

The system is designed specifically for high-volume legal drafting and property documentation
work including:

- Sale Deeds
- Affidavits
- Agreements
- GPA / POA
- Aadhaar Correction Work
- Mutation Work
- Property Documentation
- TDS Documentation
- Demat Transmission Cases
- Legal Notices
- Land Record Work

The main goal of the system is to create a:

- Centralized office management platform
- Unique matter identification system
- Fast searchable document archive
- Automated drafting workflow
- Scalable digital office structure

The entire office workflow will revolve around one permanent and unique File Identification
Number.

## 2. Project Objectives

### 2.1 Current Problems

- Files difficult to locate
- Duplicate work
- Random file naming
- No centralized search
- Physical and digital files disconnected
- No automated numbering
- Difficult follow-up tracking
- Manual drafting repetition
- Risk of losing documents
- No analytics or tracking

### 2.2 Target Outcomes

The system should:

- Generate automatic file numbers
- Create organized matter folders
- Store all documents digitally
- Maintain client database
- Track registration workflow
- Auto-generate drafts from templates
- Search instantly by client/property/file number
- Track payments and fees
- Maintain scan archives
- Support future office expansion

## 3. Core System Philosophy

Every legal matter should have:

1. One Unique File Number
2. One Master Database Entry
3. One Digital Folder
4. One Physical File Reference
5. One Searchable Identity

This file number becomes the permanent identity of the matter.

Example: `DMK/2026/SD/00459`

| Component | Meaning |
|---|---|
| DMK | Office Code |
| 2026 | Year |
| SD | Matter Type |
| 00459 | Serial Number |

## 4. Recommended Technology Stack

### 4.1 Frontend — Electron + React

Purpose: desktop application, modern user interface, Windows compatible, offline capable,
multi-window support.

### 4.2 Backend — FastAPI (Python)

Purpose: business logic, document automation, API handling, file management, search
operations.

### 4.3 Database — PostgreSQL

Purpose: store all matter data, search operations, relationship management, reporting.

### 4.4 Document Generation Engine — Python + docxtpl

Purpose: dynamic Word generation, legal template automation, Gujarati document generation.

### 4.5 PDF Conversion Engine — LibreOffice Headless

Purpose: DOCX to PDF conversion, bulk document conversion.

### 4.6 OCR Engine — Tesseract OCR

Purpose: scan text extraction, search scanned documents, survey number extraction, legacy
deed indexing.

### 4.7 QR Engine — Python QRCode Library

Purpose: matter QR labels, physical file linking, fast access system.

## 5. High-Level Software Architecture

System flow: Desktop Application → FastAPI Backend → Database + File Storage → Document
Automation Engine → Search / OCR / QR Systems.

## 6. Core Modules

### 6.1 Dashboard Module

Purpose: office overview, pending work tracking, daily operations summary.

Features: today's registrations, pending drafts, pending signatures, revenue summary, matter
status overview, recent activity.

### 6.2 Matter Management Module

Purpose: central matter handling system.

Features: matter creation, file number generation, matter tracking, status management,
timeline history, document linkage.

### 6.3 Client Management Module

Purpose: central client database.

Features: client profiles, mobile numbers, address records, identity references, matter
history.

### 6.4 Property Management Module

Purpose: property data storage.

Features: survey numbers, village details, taluka/district, area details, ownership records,
tenure information.

### 6.5 Drafting Module

Purpose: automated document creation.

Features: Word templates, auto variable replacement, PDF conversion, version management.

### 6.6 Scan & OCR Module

Purpose: scan storage, searchable PDFs, OCR indexing.

Features: scan upload, text extraction, auto tagging, search scanned content.

### 6.7 Payment Module

Purpose: fee tracking, payment records.

Features: payment history, balance tracking, pending dues, receipt tracking.

### 6.8 Search Module

Purpose: instant information retrieval.

Search filters: file number, client name, mobile number, survey number, village, document
type, registration number, Aadhaar last 4 digits.

### 6.9 Reports Module

Purpose: business analytics.

Reports: monthly revenue, matter count, pending work, document type statistics, client
analytics.

### 6.10 User Management Module

Purpose: staff access control.

Roles (as originally envisioned): Admin, Advocate, Draft operator, Accountant, Scanner
operator.

## 7. File Numbering System

### 7.1 Recommended Number Format

`DMK/2026/SD/00459`

### 7.2 Matter Type Codes

| Code | Matter Type |
|---|---|
| SD | Sale Deed |
| AFF | Affidavit |
| GPA | Power of Attorney |
| AG | Agreement |
| MUT | Mutation |
| NOC | NOC |
| DEM | Demat Transmission |
| TDS | TDS Work |
| AAD | Aadhaar Work |
| LEG | Legal Notice |
| REL | Release Deed |
| WIL | Will |

### 7.3 Number Generation Logic

Each matter type maintains a separate serial sequence.

Example current serials: SD = 459, AFF = 991, GPA = 112.

When a new matter is created:

1. System identifies matter type
2. Fetches latest serial
3. Increments serial
4. Generates new file number
5. Creates database entry
6. Creates digital folder

## 8. Folder Structure Architecture

### 8.1 Root Storage Structure

`LEGAL_DATA`

### 8.2 Year-Wise Structure

```
LEGAL_DATA
└── 2026
    ├── SD
    ├── AFF
    ├── GPA
    └── AAD
```

### 8.3 Matter Folder Structure

`DMK-2026-SD-00459`, containing:

`01_CLIENT_DOCS`, `02_DRAFTS`, `03_FINAL`, `04_REGISTERED`, `05_SCANS`, `06_TDS`,
`07_PAYMENT`, `08_PHOTOS`, `09_MISC`

## 9. Database Architecture (as originally envisioned)

> See the review note at the end of this document — the actual Stage 2 schema (49 tables,
> `docs/Database.md`/`docs/ERD.md`) is substantially more elaborate than the six tables
> below, which were this plan's minimum starting point, not a ceiling.

### 9.1 TABLE: matters

| Field | Type |
|---|---|
| id | UUID |
| file_no | VARCHAR |
| matter_type | VARCHAR |
| client_id | FK |
| property_id | FK |
| status | VARCHAR |
| registration_date | DATE |
| fees | DECIMAL |
| remarks | TEXT |
| created_at | DATETIME |

### 9.2 TABLE: clients

| Field | Type |
|---|---|
| id | UUID |
| name | VARCHAR |
| mobile | VARCHAR |
| address | TEXT |
| aadhaar_last4 | VARCHAR |
| pan_last4 | VARCHAR |
| created_at | DATETIME |

### 9.3 TABLE: properties

| Field | Type |
|---|---|
| id | UUID |
| survey_no | VARCHAR |
| village | VARCHAR |
| taluka | VARCHAR |
| district | VARCHAR |
| area | VARCHAR |
| tenure_type | VARCHAR |

### 9.4 TABLE: documents

| Field | Type |
|---|---|
| id | UUID |
| matter_id | FK |
| document_type | VARCHAR |
| file_path | TEXT |
| version | INTEGER |
| uploaded_at | DATETIME |

### 9.5 TABLE: payments

| Field | Type |
|---|---|
| id | UUID |
| matter_id | FK |
| amount | DECIMAL |
| payment_mode | VARCHAR |
| payment_date | DATE |
| remarks | TEXT |

### 9.6 TABLE: activity_logs

Purpose: track all edits and actions, for accountability and legal auditing.

Fields: `user_id`, `action`, `timestamp`, `entity_type`, `entity_id`.

## 10. Matter Workflow

### 10.1 New Matter Creation

1. Open software
2. Select matter type
3. Enter client details
4. Enter property details
5. Generate file number
6. Create digital folder
7. Create database entry
8. Open draft template

### 10.2 Drafting Workflow

1. Select template
2. Pull database data
3. Auto-fill variables
4. Generate DOCX
5. Convert PDF
6. Save version

### 10.3 Registration Workflow

Draft Created → Client Approval → Print Documents → Registration Completed → Scan
Registered Copy → Upload Final PDF → Mark Matter Complete

## 11. Document Automation System

### 11.1 Supported Templates

Sale deed, Affidavit, Agreement, GPA, NOC, Release deed, Legal notice, Undertaking,
Application formats.

### 11.2 Variable System

Example template variables: `{{client_name}}`, `{{survey_no}}`, `{{village}}`, `{{file_no}}`,
`{{registration_date}}`. The system automatically replaces these values.

### 11.3 Version Management

Example: `DMK-2026-SD-00459-DRAFT-v1.docx`, `DMK-2026-SD-00459-DRAFT-v2.docx`,
`DMK-2026-SD-00459-FINAL.docx`, `DMK-2026-SD-00459-REGISTERED.pdf`.

## 12. Search Architecture

### 12.1 Global Search

The search bar should support partial matching, multiple keyword search, and smart indexing.

Example: searching `"patel bavla 125"` should search client name, village, survey number, and
file references together.

### 12.2 Advanced Filters

Matter type, registration date, village, status, pending matters, client name, fees pending.

## 13. Dashboard Design

### 13.1 Daily Dashboard

Today's registrations, pending drafts, pending scans, fee collections, upcoming appointments.

### 13.2 Monthly Dashboard

Total matters, matter type breakdown, monthly revenue, completed matters, pending work.

## 14. QR Code Integration

Each matter should generate a QR code containing the file number, matter URL/path, and client
reference. Usage: physical file stickers, cover page, scan-based retrieval.

## 15. Security Architecture

### 15.1 Authentication

Username/password login, session timeout, role-based permissions.

### 15.2 Data Security

Encrypted backups, database protection, controlled access, audit logs.

### 15.3 Sensitive Data Protection

Sensitive data includes Aadhaar, PAN, financial documents, property papers.

Recommendations: store only last 4 digits where possible, restrict export permissions,
maintain access logs.

## 16. Backup Strategy

- **Local backup:** every 6 hours
- **External HDD backup:** daily
- **Cloud backup** (OneDrive / Google Drive): real-time sync

## 17. Deployment Architecture

### 17.1 Phase 1 — Single PC

Suitable for initial implementation, single operator office.

### 17.2 Phase 2 — Local Office Server

Main Office Server → Multiple Office Computers → Shared Database + Storage. Advantages:
centralized data, multi-user support, better management.

### 17.3 Phase 3 — Hybrid Cloud

Advantages: remote access, mobile access, automatic backups, multi-office support.

## 18. User Interface Plan

### 18.1 Sidebar Navigation

Dashboard, Matters, Clients, Properties, Documents, Payments, Reports, Settings.

### 18.2 Matter Detail Screen

Should display:

- **File Information:** file number, status, matter type
- **Client Information:** client details, contact info
- **Property Information:** survey number, village, area details
- **Documents:** drafts, final copies, registered copies, scans
- **Financial Section:** fees, payments, balance
- **Activity Timeline:** edit history, upload logs, status changes

## 19. Future AI Features

### 19.1 AI Draft Assistant

Input: matter details. Output: draft document skeleton.

### 19.2 OCR Intelligence

Upload old deed / 7-12 / mutation order → AI extracts survey number, owner name, village,
dates.

### 19.3 Voice Input System

Example: "Rajesh Patel Bavla sale deed" → system creates matter draft.

## 20. Development Roadmap (as originally envisioned)

- **Phase 1 — MVP (1 month):** matter creation, auto numbering, folder generation, client
  management, Word templates, basic search.
- **Phase 2 — Operations (2 months):** payment tracking, dashboard, registration tracking,
  scan uploads, PDF automation.
- **Phase 3 — Advanced Features (3–4 months):** OCR system, QR integration, smart search,
  analytics, backup automation.
- **Phase 4 — AI Systems:** AI drafting, OCR intelligence, Gujarati extraction, voice
  commands.

## 21. Recommended Immediate Implementation Strategy (as originally envisioned)

1. **Start with:** structured folders, Excel master register, standard naming system.
2. **Develop:** desktop application, PostgreSQL backend, template automation.
3. **Add:** OCR, QR system, analytics, AI drafting.

## 22. Expected Final Workflow

New Client → Create Matter → Auto File Number → Auto Folder Creation → Template Draft
Generation → Registration Tracking → Scan Upload → Permanent Searchable Archive.

Everything remains linked through **one unique file number**.

## 23. Final Recommendations

Most important principles:

1. Never save random filenames
2. Maintain one file number per matter
3. Keep physical and digital files linked
4. Use structured folders only
5. Maintain daily backups
6. Standardize all templates
7. Keep searchable records

## 24. Conclusion

This system is designed to transform a traditional legal documentation office into a
structured digital legal operations platform. The recommended implementation path is:
structured workflow → automation foundation → full desktop application → OCR and AI
integration.

The central principle of the entire system remains: **one unique file number for every legal
matter.**

---

## Review notes (added when this document was committed to the repository)

*Not part of the original plan — added for the Stage 4 planning session to start from,
flagging where the actual implementation (Stages 0–3) has already diverged from or gone
beyond what this plan assumed. None of this authorizes any Stage 4 work by itself.*

- **The database schema already went further than this plan's §9.** Stage 2 built a 49-table
  schema (`docs/Database.md`, `docs/ERD.md`) covering geography (country → state → district →
  taluka → village, richer than this plan's flat `village`/`taluka`/`district` strings),
  scheduling, tags, OCR/QR/backups, and system/config/plugin tables — this plan's six tables
  were a reasonable MVP floor, not a ceiling, and the floor has already been exceeded. Stage 4
  planning should start by reviewing what already exists in the schema before designing new
  tables.
- **The seeded roles (T66) don't exactly match §6.10's role list.** Currently seeded:
  Administrator, Advocate, Paralegal, Clerk, Accountant, Read Only. This plan named: Admin,
  Advocate, Draft operator, Accountant, Scanner operator. "Draft operator"/"Scanner operator"
  roughly map to Paralegal/Clerk but aren't identical, and there's no dedicated "scanner
  operator" permission set. Worth an explicit decision at Stage 4 planning time — the current
  roles are already live data with assigned permissions (T66), so changing them is a real
  migration, not a free edit.
- **§7's file-numbering system needs a concurrency design decision before implementation.**
  "Fetches latest serial, increments serial" as written is a classic race condition if two
  staff members create a matter of the same type at the same moment — needs an explicit
  choice (a database sequence per matter type, a `SELECT ... FOR UPDATE`, or an
  application-level lock) before this becomes a real feature, not left implicit.
- **§21 Step 1 ("Excel master register") is likely already obsolete** — the database schema
  and, once Stage 3's remaining frontend tasks (T69–T80) land, real authentication already
  exist. Worth confirming at planning time whether that interim step is still wanted or can be
  skipped entirely in favor of going straight to the digital system.
- **§4.4/§4.6's Python libraries (`docxtpl`, Tesseract OCR) are not yet dependencies of this
  project** — noted here so Stage 4 planning doesn't assume they're already wired in; they
  aren't.
- **This plan predates Stage 3's authentication design (`ADR-0018`).** §15.1's "username/password
  login, session timeout, role-based permissions" is already implemented, more rigorously than
  this section originally specified (JWT + revocable refresh tokens, Argon2id hashing, audit
  logging on login/permission events) — no gap here, just noting the plan is already satisfied
  on this point.
