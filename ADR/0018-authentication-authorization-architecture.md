# ADR-0018: Authentication & Authorization Architecture (D1–D6)

**Status:** Accepted
**Date:** 2026-08-07 (records a project-owner approval given 2026-08-06)

## Problem

Stage 3 (Authentication & Authorization) is the first real business-adjacent feature this project
builds — real login, real password storage, real session/token handling. Per this project's
charter ("every stage's architecture proposal presented and approved before code"), six concrete
design questions had to be answered before any Stage 3 implementation could proceed: how sessions
are represented (D1), how passwords are hashed (D2), which JWT library to use (D3), how the first
administrator account comes to exist (D4), whether self-registration is offered (D5), and where the
frontend keeps its tokens (D6). A seventh decision, D7 (the `AuthenticationProvider` port's
signature), was recorded separately in `ADR-0019` because it required an immediate breaking code
change in Stage 3 Phase 0 batch 2, while D1–D6 did not yet manifest in any code at that point.

This ADR is a documentation-only record. **All six decisions below were already reviewed and
approved by the project owner on 2026-08-06** (see `IMPLEMENTATION_QUEUE.md`'s Stage 3 "Architecture
decisions — APPROVED" table). Nothing here is a new decision — this ADR exists because it was never
written down as an ADR at the time, which `IMPLEMENTATION_QUEUE.md`'s own Phase 0 table flagged as
outstanding (the original T45 content, orphaned by T44/T45's ID reuse — see
`docs/reviews/Documentation_Migration_Note_T44_T45_2026-08-06.md`, which remains the canonical
account of that reconciliation and is not revisited here).

## Decision

| # | Decision | Approved choice |
|---|---|---|
| D1 | Token mechanism | JWT access token (short-lived, ~15–30 min) + a DB-backed, revocable refresh token. One new table, `refresh_tokens` (Phase 1, `T49`). |
| D2 | Password hashing | Argon2id via `argon2-cffi`. |
| D3 | JWT library | `PyJWT`. |
| D4 | First-admin bootstrap | A one-time CLI command with an *interactive* password prompt (`getpass`-style) — the password must never pass through a command-line argument, an environment variable, or anything that would land in shell history or a process list. |
| D5 | Self-registration | None. Only admin-created users, via a `users:manage`-protected endpoint. |
| D6 | Frontend token storage (Electron) | Refresh token in OS-level encrypted storage via Electron's `safeStorage` API (main process only, a new IPC channel); access token held in-memory only (React state, never persisted — lost on app restart, forcing a silent refresh or re-login). |

## Reasoning

- **D1 (JWT + revocable refresh token):** A legal-document system carries real confidentiality
  obligations. A "logout" that cannot actually revoke a token is a meaningful gap if a device is
  lost or stolen. Short-lived access tokens limit the exposure window if one leaks; the DB-backed
  refresh token is the part that is actually revocable on demand.
- **D2 (Argon2id via `argon2-cffi`):** OWASP's current default recommendation for new applications'
  password hashing.
- **D3 (`PyJWT`):** More actively maintained at decision time than the main alternative
  (`python-jose`); fully encapsulated behind a single token utility (`T47`) so it stays swappable
  later at low cost if that changes.
- **D4 (interactive CLI bootstrap):** Refines the original recommendation with the detail that
  matters most for a first-admin credential: a plaintext password must never pass through `argv`,
  an environment variable, or a config file — an interactive prompt is the only one of those options
  that leaves no such trace.
- **D5 (no self-registration):** Every seeded role (`Administrator`, `Advocate`, `Paralegal`,
  `Clerk`, `Accountant`, `Read Only`) is internal staff. No client-facing portal exists or is
  planned, so self-registration would be an unused attack surface with no corresponding user need.
- **D6 (`safeStorage` refresh token, in-memory access token):** Matches this project's existing
  Electron security posture (`contextIsolation: true`, `nodeIntegration: false`, no generic IPC
  passthrough — see `docs/Architecture.md`'s Electron section and `ADR-0004`). Persisting the
  long-lived, revocable refresh token in OS-level encrypted storage keeps it off disk in plaintext;
  keeping the short-lived access token in-memory-only means a compromised on-disk artifact is never
  enough on its own to impersonate a session past its next natural refresh.

## Trade-offs

- **D1** adds one new table (`refresh_tokens`) and revocation-check logic to every refresh — a
  small, deliberate cost for the confidentiality property described above, versus a simpler
  stateless-JWT-only design that could never truly revoke a session before natural expiry.
- **D4** means bootstrapping a new environment always requires an interactive terminal session —
  no scripted/unattended first-admin creation. Accepted deliberately: the alternative (any
  non-interactive input path) is exactly what D4 exists to rule out.
- **D5** means every user account requires an administrator's action to create. Acceptable given
  D5's own premise (no client-facing portal), but this is a real operational constraint worth
  remembering if the product's audience ever expands beyond internal staff.
- **D6** requires a new Electron IPC surface (Phase 5, `T71`) specifically for `safeStorage` access
  — main-process-only, following the existing "no generic passthrough" preload discipline, rather
  than reusing any existing channel.

## Future Impact

- **D1** is implemented by Phase 1 (`T47` token utility, `T49` `refresh_tokens` migration, `T50`
  `AuthService.issue_tokens()`/`refresh()`/`revoke()`) and exercised by Phase 3's `/auth/refresh`
  and `/auth/logout` routes (`T59`, `T60`).
- **D2** is implemented by `T46` (`hash_password()`/`verify_password()` utility) and consumed by
  `T50`/`T62` (user creation).
- **D3** is implemented by `T47` and is the mechanism `T52`'s `JwtAuthenticationProvider` decodes
  against.
- **D4** is implemented by `T67` (the bootstrap CLI command), gated on `T46`/`T62` existing first.
- **D5** constrains `T62` (user-management routes) to admin-created users only — no public
  registration endpoint should ever be added without a new decision superseding this one.
- **D6** is implemented by `T71` (Electron secure storage IPC) and consumed by Phase 5's
  `T70`/`T74` (auth state, request header attachment).
- This ADR does not change, and is not changed by, `ADR-0019` (D7, the `AuthenticationProvider`
  port signature) or `ADR-0020` (the `get_db()` commit/rollback policy) — all three are independent
  records covering non-overlapping decisions from the same architecture review.
- If any of D1–D6 needs to change once Phase 1+ implementation surfaces a real constraint these
  decisions didn't anticipate, that is a new decision requiring its own approval and either an
  amendment here or a superseding ADR — not a silent implementation deviation.
