# ADR-0019: `AuthenticationProvider` Interface Change

**Status:** Accepted
**Date:** 2026-08-06

## Problem

Stage 1's `AuthenticationProvider` port (`application/interfaces/auth.py`) was defined as
`async def get_current_user(self) -> CurrentUser` — no arguments, because no login mechanism
existed and the one shipped implementation (`AnonymousAuthenticationProvider`) always returns the
same anonymous default regardless of any request context. Stage 3 replaces that stub with a real
JWT-based provider (`JwtAuthenticationProvider`, Phase 2/`T52`) that must decode a bearer token to
know who's calling — but the port as written gives it no way to receive one. This is decision D7
from Stage 3's approved architecture review: a genuine breaking change to an existing Stage 1 port,
made explicitly and documented here rather than silently, per this project's standing rule that
architecture changes never happen quietly.

## Options Considered

1. **Keep the no-argument signature; have the provider discover the token itself** (e.g. via a
   request-scoped global, a `contextvar` set by middleware, or constructor-injecting a
   request-bound object). Rejected: every variant hides a real dependency behind implicit state.
   A `contextvar` set by middleware means `get_current_user()`'s actual behavior depends on
   something that ran earlier and isn't visible at the call site; constructor injection of a
   request-bound object would make `AuthenticationProvider` request-scoped, contradicting how
   every other port in this codebase is registered (singleton, resolved once, reused across
   requests) and complicating `configure_container()` for no benefit this stage actually needs.
2. **Add `token` as an explicit parameter**: `async def get_current_user(self, token: str | None)
   -> CurrentUser`. The caller (a FastAPI dependency, ultimately) extracts the token from the
   request and passes it in directly — the only way a real implementation can know which
   request's token to validate without hidden state. `token=None` (no credential presented) must
   resolve the same as an invalid/expired token: the anonymous default, never a raised exception —
   keeping "is this caller allowed to be anonymous here" a decision for `AuthorizationService`/the
   route, not this method.

## Decision

Option 2. `AuthenticationProvider.get_current_user()` now takes an explicit `token: str | None`
parameter, with no default (a caller must pass something, even if that something is `None`) —
exactly the approved D7 signature. Both existing callers of the changed method were updated in the
same change, so nothing is left broken:

- `AnonymousAuthenticationProvider.get_current_user()` (`infrastructure/auth/`) now accepts
  `token` and deliberately ignores it — still always returns the anonymous default. It predates
  real login; D7 only changed the port's shape, not this stub's behavior.
- `presentation/api/deps.py`'s `get_current_user()` dependency wrapper now calls
  `auth_provider.get_current_user(token=None)`. This is a **Stage 3 Phase 0 placeholder** — real
  bearer-token extraction from the incoming request (`HTTPBearer`/`OAuth2PasswordBearer` or manual
  header parsing) is `T56` (Phase 2), not built yet. Since `AnonymousAuthenticationProvider` ignores
  the value regardless, passing `None` unconditionally is behaviorally identical to today until
  `T56` lands — this line will need updating then, deliberately, not silently.

No password hashing, JWT encoding/decoding, or route was implemented as part of this change —
those remain `T46`/`T47`/`T52`/Phase 3, explicitly out of scope for this batch.

## Reasoning

- Matches how this project's other request-scoped-but-singleton-resolved dependencies already
  work (`SettingsDep` resolves once, reused everywhere; `DBSessionDep` alone gets genuine
  per-request state, and that's handled by FastAPI's own generator `Depends()` pattern, not by
  this port). Adding a parameter keeps `AuthenticationProvider` itself simple and still
  singleton-registrable; the request-scoped part (extracting the token) stays where FastAPI's
  dependency system already handles request-scoped values well — the caller, not the port.
- `token=None` resolving to the anonymous default (never raising) keeps this port's contract
  simple: it answers "who is this," not "is this request allowed to proceed." A route that
  requires authentication enforces that via `RequirePermission(...)`/`AuthorizationService`
  (`T54`), checking the resulting `CurrentUser.is_authenticated`, not by `get_current_user()`
  raising on a missing token.
- Updating both existing callers in the same change (rather than leaving `AnonymousAuthenticationProvider`
  or `deps.py` broken until Phase 2) keeps the full test suite genuinely green throughout — a
  signature change that breaks its own only two callers until some later phase fixes them would
  leave the codebase in a knowingly-broken state, which this project's "small, reviewed sections"
  discipline doesn't allow.

## Trade-offs

- `deps.py`'s `get_current_user()` hardcoding `token=None` is a known, temporary placeholder — it
  makes every request resolve to anonymous today, identical to pre-Stage-3 behavior, but doesn't
  yet do what Stage 3 actually needs (extracting a real bearer token). Flagged explicitly here and
  in the function's own comment so `T56` isn't mistaken for optional — without it, D7's signature
  change has no real effect yet.
- `AuthenticationProvider.get_current_user()` still can't distinguish "no token presented" from "a
  token was presented but is garbage" at the type level — both are `str | None` values a
  conforming implementation must handle without raising. `JwtAuthenticationProvider` (`T52`) is
  where that distinction actually matters (logging/metrics might care which case occurred); this
  ADR doesn't require it to expose that distinction back through `CurrentUser`.

## Future Impact

- `T52` (`JwtAuthenticationProvider`) is the real implementation this signature exists for —
  decoding `token`, loading the `User` + roles, returning a populated `CurrentUser`, or the
  anonymous default for `None`/invalid/expired, per `docs/Stage3_Backend_Handoff.md`'s Phase 2
  file map.
- `T56` must replace `deps.py`'s hardcoded `token=None` with real extraction from the request
  (`Authorization: Bearer <token>` header) — tracked as a named, not-yet-done follow-up here and in
  `docs/ImplementationLog/Stage3/Phase0.md`, not something to silently forget once Phase 2 starts.
- `ADR-0018` (recording D1–D6: the broader token mechanism/password hashing/JWT library/bootstrap/
  self-registration/frontend-storage decisions) remains a separate, not-yet-written document —
  this ADR covers D7 only, since D7 is the one decision this specific code change actually applies.
