------------------------------------------------

# Stage 4 – Phase 1

Status: Done

Started: 2026-08-18

Completed: 2026-08-18

Related Tasks: T69

Related ADRs: None (closes Stage 2.5's finding F10 — a pre-existing gap flagged before Stage 3, not
a new architectural decision)

Git Commit: `5196fdf` (merge; parents `b544135` and `79af7ac`; feature commit `cca729f`;
documentation-metadata commit `d5ecdbc`; pre-merge `main`-sync merge `f09f3a5`; QA-approval commit
`6b90ede`; pre-merge documentation-synchronization commit `79af7ac`) — independently verified via
`git log`/`git show 5196fdf` this session, not taken on faith.

Pull Request: #54 (`feature/stage4-t69-http-client-methods` → `main`, merged `5196fdf`, 2026-08-18)

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

☑ Approved
□ Approved with comments
□ Rework required
```

Rendered by the QA Reviewer role, independently, against feature commit `cca729f`
(`feature/stage4-t69-http-client-methods`) — no PR opened yet; this decision is recorded pre-PR, per
this project's practice of committing the QA Decision to the branch before any PR is opened or
merged. Context rebuilt from the repository directly (`docs/prompts/QAReviewer.md`,
`PROJECT_WORKFLOW.md`, `IMPLEMENTATION_QUEUE.md`'s T69 row, this phase log) — not from prior chat
history.

**Post-merge correction (2026-08-18):** the "no PR opened yet"/"recorded pre-PR" framing above was
accurate at the time this QA Decision was rendered and is preserved verbatim, not rewritten. A
documentation-synchronization pass then committed to the same branch (`79af7ac`), a pull request was
opened (PR #54), and it merged as `5196fdf` with **no rework** — this QA Decision's `Approved` (plain)
disposition was carried into the merge exactly as rendered, with zero changes requested or made
between this decision and the merge. See the Post-Merge Verification section below for the
independent post-merge re-check.

**Files reviewed:** `frontend/src/infrastructure/api/httpClient.ts`,
`frontend/src/infrastructure/api/httpClient.test.ts`, and this phase log — the full diff against
`main` (`git diff main...feature/stage4-t69-http-client-methods`), read directly, not the
Developer's summary alone.

**Verification Results (checked directly against the repository and live test/lint runs, not taken
from the Developer's self-assessment):**

- **Authorization:** T69's authorization commit (`cf7a570`, `PROJECT_STATE.json` sync `0a9ad12`,
  PR #52, merged `5abceee`) precedes the implementation commit (`cca729f`) — confirmed by commit
  order via `git log`.
- **Scope:** `git diff main...feature/stage4-t69-http-client-methods --name-only` independently
  confirms exactly three files changed: `httpClient.ts`, `httpClient.test.ts`, and this phase log.
  Matches `IMPLEMENTATION_QUEUE.md`'s T69 row exactly — no forbidden file touched, no route/schema/
  backend file touched, `T70`–`T76` not implemented.
- **HTTP methods and body serialization — read directly, not assumed:** `requestWithBody()` passes
  `method` straight through to `fetch`'s `init.method`, so `post`/`put` issue `"POST"`/`"PUT"` and
  `delete` issues `"DELETE"`. The body is `JSON.stringify(body)` only when `body !== undefined`
  (otherwise `undefined`, not the string `"undefined"` fetch would otherwise send) — correct
  serialization, including the no-body `delete()` case.
- **Structured-error validation is a genuine structural check, not an assumption the backend sent
  what's expected:** `isStructuredErrorBody()` verifies the body itself is a non-null object, that
  its `error` property is also a non-null object (the explicit `=== null` check matters here —
  `typeof null` is `"object"` in JS, so a bare `typeof` check alone would have let `error: null`
  through), and that both `code` and `message` are actually strings before `buildHttpError()` trusts
  any of it. A body with the right keys but wrong types, or missing keys entirely, correctly falls
  through to the generic fallback rather than being trusted.
- **Fails safely, doesn't crash, on non-JSON or differently-shaped bodies:** `buildHttpError()`
  wraps `response.json()` in `try`/`catch`, so an unparseable body (confirmed via a test where
  `.json()` rejects) is caught and resolves to the generic-message `HttpError`, never an unhandled
  rejection. A body that parses as valid JSON but doesn't match the structured shape — wrong keys, a
  bare string, `error: null` — falls through the type guard to the same generic fallback. No path
  found where a malformed error body reaches an unhandled throw or a `TypeError` from blindly
  indexing into an unexpected shape.
- **Tests — independently re-run, not taken on the reported count:** `npm run test -- --run` on this
  branch: **17/17 passing, 4 test files** — matches the Developer's claim. The 4 new error-handling
  tests are non-vacuous: each asserts a specific `.status`/`.code`/`.message` combination, and the
  two fallback tests exercise genuinely different failure modes (a real-but-non-matching JSON shape,
  and a rejecting `.json()` call) rather than duplicating the same path twice. The verb tests assert
  the actual `RequestInit` passed to the mocked `fetch`, not just that the call didn't throw.
- **Lint/format — independently re-run:** `npm run lint`: 0 errors, 3 warnings, all three
  pre-existing (`react-refresh/only-export-components` in files this batch never touches) — matches
  the documented baseline. `npm run format:check`: clean.
- **Architecture:** no port/contract or layering change; `get()` and `request<T>()`'s success path
  are byte-for-byte unchanged; `httpClient`'s existing shape (a plain object of verb functions) is
  extended, not redesigned.

**Non-blocking observation, already disclosed by the Developer, re-confirmed here rather than raised
as a new finding:** `delete()`'s success path still calls `response.json()` unconditionally
(inherited unchanged from the pre-existing `request<T>()`), which would throw on a real `204 No
Content` response. Correctly out of this batch's scope — no caller of `delete()` exists yet (`T70`+
is unauthorized), and extending the success-path body handling was never part of T69's approved
scope. The phase log's own Deferred Work section already names this with `T70`+ as the trigger; no
QA action required.

**Required changes:** None.

No defects found. Scope matches authorization exactly. Tests are real and independently confirmed
passing. Error parsing validates response shape before trusting it and fails safely on both
non-JSON and differently-shaped bodies.

## Post-Merge Verification — T69 batch (2026-08-18)

**Verified directly on `main` at `5196fdf`, not assumed:**
- `git log --oneline -8 main` and `git rev-parse main origin/main` both confirm `main`/`origin/main`
  are synchronized at `5196fdf` — "Merge pull request #54 from
  Intelligentclown/feature/stage4-t69-http-client-methods."
- `git show --no-patch --format="%H%n%P"` on `5196fdf` confirms its parents are `b544135` (prior
  `main`, T68's own post-merge documentation closeout) and `79af7ac` (the feature branch tip, this
  batch's own pre-merge documentation-synchronization commit) — beneath which sit `6b90ede` (QA
  Decision — T69 batch: Approved), `d5ecdbc` (feature-commit metadata), and `cca729f`
  (implementation), plus `f09f3a5` (this branch's own merge of up-to-date `main`, performed before the
  documentation-synchronization pass since `main` had advanced past this branch's original base via
  `T68`'s own closeout).
- `gh pr view 54` independently confirms `state: MERGED`, `mergeCommit.oid: 5196fdf...`,
  `baseRefName: main`, `headRefName: feature/stage4-t69-http-client-methods`.
- `git show --stat 5196fdf` confirms the file set matches this batch plus its own documentation sync
  exactly: `frontend/src/infrastructure/api/httpClient.ts`,
  `frontend/src/infrastructure/api/httpClient.test.ts`, this phase log, and the five project-wide
  documentation files (`IMPLEMENTATION_QUEUE.md`, `PROJECT_STATE.json`, `docs/AI_HANDOVER.md`,
  `docs/Roadmap.md`, `docs/SessionReport.md`) — no backend file touched.
- `npm run test -- --run` on merged `main`: **17/17 passing, 4 test files** — personally re-run this
  session, not carried over from the pre-merge figure.
- `npm run lint`: 0 errors, 3 warnings, all three pre-existing (`react-refresh/only-export-components`
  in files this batch never touches). `npm run format:check`: clean.
- No rework occurred between this QA Decision and the merge — `Approved` (plain) is the batch's only
  QA Decision, carried into `main` unchanged.

**`T69` is now Done — merged.**
- Authorization commit: `cf7a570` (`PROJECT_STATE.json` sync `0a9ad12`, PR #52, merged `5abceee`)
- Implementation commit: `cca729f`
- QA-approval commit: `6b90ede`
- Documentation-synchronization commit: `79af7ac`
- Merge: PR #54, `5196fdf` (2026-08-18)

**Stage 4 Phase 5 (`T69`) is complete in full.** `T70`–`T76` remain explicitly out of scope and
unauthorized.
