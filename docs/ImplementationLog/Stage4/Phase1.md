------------------------------------------------

# Stage 4 – Phase 1

Status: In Progress

Started: 2026-08-18

Completed:

Related Tasks: T69

Related ADRs: None (closes Stage 2.5's finding F10 — a pre-existing gap flagged before Stage 3, not
a new architectural decision)

Git Commit: pending (feature branch `feature/stage4-t69-http-client-methods` pushed; no PR opened —
Frontend Developer role stops here per this batch's stop condition, QA review happens in a separate
session)

Pull Request: not yet opened

Release:

------------------------------------------------

**Naming note:** `IMPLEMENTATION_QUEUE.md`'s own headings still nest T69 under "Stage 3 — Phase 5 —
Frontend." This file is named `Stage4/Phase1.md`, not `Stage3/Phase5.md`, following the precedent
`docs/AI_HANDOVER.md` records for `Stage4/Phase0.md` (T66–T68): "a new migration under
`docs/ImplementationLog/Stage4/Phase0.md` (Stage 4, not Stage 3 — the first task past the routes
phase)." `Phase0.md` covers the queue's "Phase 4 — Data: seed & bootstrap" (T66–T68); this file
continues that same renumbered sequence for the queue's next phase, "Phase 5 — Frontend" (T69–T76),
as `Phase1.md`. This is a judgment call, not a decision recorded anywhere explicitly for Phase 5
specifically — disclosed here rather than silently assumed, per this project's discipline of
surfacing interpretive choices instead of hiding them.

## T69 Batch: httpClient post/put/delete + Structured Error Parsing

**Authorization / Scope:** The project owner explicitly authorized T69 on 2026-08-18, recorded in
`IMPLEMENTATION_QUEUE.md` and `PROJECT_STATE.json` as its own documentation-only commit
(`cf7a570`/`0a9ad12`, PR #52, merged `5abceee`) before any implementation existed — independently
verified this session via `git log`/`git show`/`git branch --contains`, not taken on the task
prompt's word. Approved scope: `post`/`put`/`delete` methods added to
`frontend/src/infrastructure/api/httpClient.ts` alongside the existing `get()`; `HttpError` extended
to carry the backend's structured error code/message when the response body matches
`{"error":{"code": ..., "message": ...}}`, falling back to the existing generic
`Request to <path> failed with status <status>` message only when the body doesn't match that shape.
`T70`–`T76` explicitly out of scope and unauthorized.

### Objective

Close Stage 2.5's finding F10: give the frontend HTTP client the verbs a mutating request needs
(`post`/`put`/`delete`, alongside the existing `get()`), and let callers see the backend's actual
structured error code/message instead of always throwing a generic status-only string.

### Tasks Implemented

- `T69` — `post`/`put`/`delete` added to `httpClient.ts`; `HttpError` gained an optional `code`
  field, populated from the response body when it matches `{"error":{"code","message"}}`, with the
  original generic message preserved as the fallback for any other shape (including unparseable
  JSON).

### Files Modified

- `frontend/src/infrastructure/api/httpClient.ts` — added `isStructuredErrorBody()` (a type guard),
  extended `HttpError` with a `readonly code?: string`, added `buildHttpError()` (tries the
  structured shape first, falls back to the generic message on any mismatch or parse failure), added
  a shared `requestWithBody()` helper, and added `post`/`put`/`delete` to the exported `httpClient`
  object. `get()` and the existing `request<T>()` success path are unchanged.
- `frontend/src/infrastructure/api/httpClient.test.ts` (new) — 8 tests covering the verbs and the
  error-parsing behavior (see Tests Added below).
- `docs/ImplementationLog/Stage4/Phase1.md` (this file, new).

### Tests Added

All in `frontend/src/infrastructure/api/httpClient.test.ts`:

- `get() issues a GET request` — confirms no explicit method (or an explicit `"GET"`) is sent.
- `post() issues a POST request with a JSON-serialized body` — confirms method `"POST"` and
  `JSON.stringify(body)` as the request body.
- `put() issues a PUT request with a JSON-serialized body` — same, for `PUT`.
- `delete() issues a DELETE request` — confirms method `"DELETE"`.
- `populates HttpError's code and message from a structured error body` — a `409` response with
  `{"error":{"code":"CONFLICT","message":"Email already in use"}}` produces an `HttpError` whose
  `.status`/`.code`/`.message` match exactly.
- `falls back to the generic message when the body doesn't match the structured shape` — a `500`
  response with `{"detail":"boom"}` (a real but non-matching JSON shape) produces the generic
  `Request to /users failed with status 500` message and `code: undefined`.
- `falls back to the generic message when the response body isn't parseable JSON` — `response.json()`
  rejecting (simulating an unparseable body) is caught, doesn't crash, and produces the same generic
  fallback.
- `doesn't crash and still throws when the error body is a non-object JSON value` — a valid JSON
  response body that isn't an object (a bare string) is rejected by the type guard without throwing
  from inside the guard itself, and still falls back to the generic message.

### Test Results

`npm run test` (vitest run, from `frontend/`): **17/17 passing** (9 pre-existing + 8 new), 4 test
files. Full output: `Test Files 4 passed (4)`, `Tests 17 passed (17)`.

`npm run lint` (eslint): **0 errors**, 3 warnings — all three pre-existing
(`react-refresh/only-export-components` in `NotificationProvider.tsx`, `ThemeProvider.tsx`,
`button.tsx`), matching `PROJECT_STATE.json`'s already-documented baseline (`"3 pre-existing
react-refresh warnings are expected, 0 errors"`). None of the three touch this batch's files.

`npm run format:check` (prettier --check): initially flagged the new test file (wrapping choices
differed from Prettier's own formatting of the same source); re-run after `npx prettier --write` on
both touched files — **all matched files use Prettier code style**, re-verified clean on a second
`npm run format:check` pass.

Nothing in this batch required infrastructure this environment couldn't reach — no backend, no
database, no live network call; `fetch` is mocked directly in every test via `vi.stubGlobal`.

### Design Decisions

- **Structured-error detection is a strict type guard, not a loose duck-type.** `isStructuredErrorBody()`
  requires `error.code` and `error.message` to both be strings; anything else (missing `error` key,
  `error` not an object, `code`/`message` not strings, or a non-object body entirely) falls through
  to the generic message. This matches the approved scope's exact wording ("falling back ... only
  when the response body doesn't match that shape") rather than trying to be lenient about partial
  matches.
- **Error-body parsing is wrapped in `try`/`catch`.** `response.json()` throws on a non-JSON or empty
  body (e.g. an HTML error page from a proxy, or a body-less error response); that failure is caught
  inside `buildHttpError()` and always resolves to the generic-message `HttpError`, never an unhandled
  rejection.
- **`post`/`put`/`delete` share one `requestWithBody()` helper** rather than three near-duplicate
  functions, mirroring how `get()` already delegates to the shared `request<T>()`. `delete()` doesn't
  take a body parameter in this batch (no approved caller needs one), but `requestWithBody()` itself
  is generic enough that adding one later wouldn't need restructuring.
- **`code` is optional (`code?: string`), not defaulted to a placeholder string**, so callers can
  reliably branch on `error.code !== undefined` to know whether the backend actually sent a
  structured code, rather than a sentinel value that could collide with a real one.

### Problems Encountered

**A different, concurrent session shared this same working directory mid-batch.** After this batch's
own feature branch (`feature/stage4-t69-http-client-methods`) was created off an up-to-date `main`
and the implementation was already in progress, `git status` unexpectedly showed five unrelated files
(`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`, `docs/Roadmap.md`,
`docs/SessionReport.md`) as modified, none of which this batch had touched. `git reflog` showed the
cause directly: something switched the shared working directory's `HEAD` from
`feature/stage4-t69-http-client-methods` to a different local branch,
`docs/t68-post-merge-closeout`, and committed T68 post-merge documentation-closeout work there
(`b751fe2`) — a separate Documentation Manager session's legitimate work, not corruption. Resolved by
`git checkout feature/stage4-t69-http-client-methods` back onto this batch's own branch (leaving
`docs/t68-post-merge-closeout` and its commit untouched) and staging only this batch's two files
(`httpClient.ts`, `httpClient.test.ts`) rather than anything broader. No file belonging to the other
session's work was read, reverted, or committed by this batch. Flagged here as a process/governance
observation, not a T69 defect: this project's workflow doesn't currently document how concurrent
sessions sharing one working directory should coordinate branch checkouts.
- Pre-existing, unrelated uncommitted state was present in the working directory before this batch
  began and remains untouched by it: `docs/prompts/README.md` (modified), `docs/HANDOFF/` (untracked
  directory), `docs/prompts/GitCI_PR_Manager.md` (untracked file).

### Deferred Work

- **`delete()`'s success path still calls `response.json()`**, inherited unchanged from the existing
  `request<T>()` helper. A real `204 No Content` response (the shape this codebase's own backend
  logout route already returns, per `T60`) has no body, so `response.json()` would throw on a
  genuine no-content success response. No caller of `httpClient.delete()` exists yet (`T70`–`T76` are
  unauthorized), so this wasn't exercised or fixed here — flagged for whichever task (`T70`+) makes
  the first real `delete()` call, since fixing `request<T>()`'s success-path body handling generally
  is outside this batch's approved scope (extending `get()`/the success path was never part of T69's
  authorization).
- **No caller anywhere in the codebase uses `post`/`put`/`delete` yet** — by design, per the explicit
  out-of-scope instruction ("no new API calls added anywhere that uses httpClient"). Wiring them up
  is `T70`+'s job.

### Future Considerations

- `T70` (auth state management) and later tasks will be the first real callers of `post`; that's the
  point at which `HttpError.code` gets its first actual consumer, and where the `delete()`
  success-path gap above would first matter in practice.
- The concurrent-session working-directory issue under Problems Encountered is worth a explicit
  process note somewhere (`PROJECT_WORKFLOW.md` or `AI_BOOTSTRAP.md`) if it recurs — not something
  this batch is authorized to change unilaterally.

### Reviewer Checklist

```
Reviewer Checklist

☑ Architecture preserved
☑ Existing design patterns followed
☑ Tests added
☑ Existing tests pass
☑ Documentation updated
□ ADR updated (if required) — N/A, no architectural decision this batch (closes a pre-existing
  finding, F10, not a new decision)
□ AI_BOOTSTRAP updated (if required) — N/A, no standing convention changed
□ PROJECT_STATE updated (if required) — N/A; PROJECT_STATE.json synchronization is the Documentation
  Manager's role, after QA approval, per PROJECT_WORKFLOW.md §8
☑ No unrelated refactoring
☑ No scope creep
☑ Ready for QA
```

**Notes on the unchecked boxes:** "ADR updated" and "AI_BOOTSTRAP updated" are correctly N/A — this
batch closes an already-flagged finding using the codebase's existing patterns, it doesn't make a new
architectural decision or change a standing rule. "PROJECT_STATE updated" is correctly left to the
Documentation Manager, per this project's documentation-ownership rules
(`docs/prompts/BackendDeveloper.md` §5's "Documentation ownership rules," applied identically here for
the Frontend Developer role) — this role does not synchronize project-wide documents, and does so
only after a QA Decision exists.

## QA Decision — T69 batch

```
QA Decision (T69 batch)

□ Approved
□ Approved with comments
□ Rework required
```

Not yet rendered — this role (Frontend Developer) stops after implementation and self-assessment,
per its stop condition. QA review happens in a separate session.
