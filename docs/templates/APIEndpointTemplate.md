# API Endpoint Template

**Purpose:** The skeleton for documenting a new endpoint in [docs/API.md](../API.md), matching the
shape its existing `GET /api/v1/health` and `GET /api/v1/version` entries already use. Every route
this project ever mounts into the real app — beyond the two health/version routes that have existed
since Stage 0 — should get an entry in this shape before (or as part of) being considered done.

**When to use:** Any time a new route is added to `presentation/api/v1/router.py` (or a future
`v2` package, per [docs/API.md](../API.md)'s stated versioning strategy) and actually mounted into
the real app — not for routes proven only against a test-only app (like the CRUD router factory's
own test suite), which don't belong in this project's live API documentation until they're real.

**Copy destination:** Append as a new `### METHOD /api/v1/...` section within
[docs/API.md](../API.md), and add a corresponding row to its "Implementation status" table at the
bottom of that file.

---

### `<METHOD> /api/v1/<path>`

\<One-line description of what this endpoint does.\>

\<Any behavioral notes worth calling out up front — e.g. "no database dependency" for `/health`,
or an idempotency/side-effect note for a mutating route.\>

**Auth required:** \<None | describes the permission/role required — see
[ADR/0004](../../ADR/0004-security-foundation-placeholders.md) for what's actually enforceable
today versus still a placeholder\>

**Request** (for `POST`/`PUT`/`PATCH`):
```json
{
  "...": "..."
}
```

Response `<status code>`:
```json
{
  "...": "..."
}
```

**Error responses:** List each distinct error case this route can return (validation failure, not
found, conflict, unauthorized, forbidden) with its status code — this project's error shape is
always `{ "error": { "code": "...", "message": "..." } }`, see
[docs/API.md](../API.md)'s "Cross-cutting behavior" section; don't repeat that shape here, just
name which `code` values this route can produce.

**Related feature:** Link to the [docs/FeatureRegistry.md](../FeatureRegistry.md) entry this route
belongs to (see [Feature_Template.md](Feature_Template.md)), if any — infrastructure routes like
`/health`/`/version` have none.

---

Add to [docs/API.md](../API.md)'s "Implementation status" table:

| Endpoint | Status | Auth | Tests |
|---|---|---|---|
| `<METHOD> /api/v1/<path>` | Implemented | \<None / permission name\> | `<test file path>` |
