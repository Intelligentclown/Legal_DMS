# ADR-0004: Security foundation placeholders (no auth yet)

**Status:** Accepted
**Date:** 2026-08-05

## Problem

The Stage 0 charter explicitly excludes implementing login/authentication, but also requires
"preparing the architecture for future authentication" — security middleware structure,
configuration placeholders, and a secret-management approach, without actually building auth
itself. This ADR records what was (and wasn't) prepared, and why, so a future stage implementing
real auth doesn't have to guess what already exists.

## Options Considered

1. **Do nothing security-related in Stage 0** — defer everything to the auth stage. Simpler now,
   but risks the auth stage having to retrofit request correlation, error handling, and CORS
   discipline that are much easier to establish before routes/business logic exist.
2. **Build a stub auth system now** (fake login, placeholder JWT middleware) — explicitly
   forbidden by the charter ("Do NOT implement login yet") and would create dead code that likely
   doesn't match the real auth stage's requirements anyway.
3. **Prepare the seams without building auth**: request correlation, consistent error responses,
   CORS configuration, and env-driven secret handling — all useful regardless of what the eventual
   auth mechanism is, none of it auth-specific.

## Decision

Option 3. Specifically, Stage 0 includes:

- `RequestIDMiddleware` — every request gets a correlated ID, useful for security auditing
  regardless of auth mechanism.
- `CORSMiddleware`, configured via `Settings.cors_origins` (env-driven, never hardcoded) — the
  first line of defense against unauthorized cross-origin requests, needed before any protected
  route exists.
- Consistent error response shape (`AppError` → `{"error": {"code", "message"}}`) including
  `UnauthorizedError` (401) and `ForbiddenError` (403) subclasses already defined and ready to
  raise once auth exists — no route currently raises them.
- All configuration (including anything that will eventually be a secret — API keys, JWT signing
  keys, etc.) flows through `pydantic-settings` reading from `.env` files, never hardcoded. The
  pattern is established; no actual secrets exist yet to manage.
- Electron's `contextIsolation`/`nodeIntegration: false`/`sandbox: true` baseline — not
  authentication, but the same "security by default, established before it's load-bearing"
  principle applied to the desktop shell.

Explicitly **not** built: no login endpoint, no session/token handling, no user model, no
password storage, no `Authorization` header parsing.

## Reasoning

Establishing the seams (error types, middleware ordering, config discipline) costs little now and
means the eventual auth stage plugs into existing patterns rather than reshaping the request
pipeline. Building fake auth would have been pure waste — actively forbidden by the charter, and a
liability if left in place accidentally.

## Trade-offs

`UnauthorizedError`/`ForbiddenError` currently have no caller — they're speculative until an auth
stage exists. Minor: if the eventual auth design doesn't fit an "exception raised mid-request"
model (e.g. needs a 401 before routing even happens), these may need adjusting.

## Future Impact

When an auth stage is scoped, it should: choose a specific mechanism (session vs. JWT vs.
something else — not decided here), add a `users`/auth-related table via Alembic, add auth
middleware/dependencies, and start actually raising `UnauthorizedError`/`ForbiddenError`. That
stage should write its own ADR for the mechanism choice — this ADR only covers what Stage 0
prepared in advance.
