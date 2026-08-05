# Coding Standards

## Backend (Python)

- Formatted with **Black** (line length 100), linted with **Ruff** (`E`, `W`, `F`, `I`, `UP`, `B`,
  `C4`, `SIM`, `RUF` rule sets — see `backend/ruff.toml`).
- Full type hints everywhere; `from __future__ import annotations` at the top of every module.
- No bare `except`. Deliberate errors raise a subclass of `AppError`
  (`application/errors/exceptions.py`), never a raw `Exception`.
- No business logic in `presentation/` (routers) — routers parse/validate input, call into
  `application`, and shape the response. No SQLAlchemy queries directly in a router.
- No comments explaining *what* code does (names should do that); a short comment is fine when it
  captures a non-obvious *why* — see e.g. the ordering comment on middleware registration in
  `main.py`, or the `NoDecode` annotation on `cors_origins` in `settings.py`.
- Constructor parameter-property shorthand (`def __init__(self, public readonly x: T)`-style) is
  **not** used — the project's `erasableSyntaxOnly`-equivalent discipline on the TS side and a
  general preference for explicit `self.x = x` assignments applies uniformly; see
  `HttpError` in `httpClient.ts` and the mirrored style in Python exception classes.
- Tests: Pytest, `tests/unit/` for pure logic (no I/O), `tests/integration/` for anything
  exercising the FastAPI app via `TestClient`. Fixtures in `conftest.py`.

## Frontend (TypeScript/React)

- Strict TypeScript (`strict: true` plus `noUnusedLocals`, `noUnusedParameters`,
  `erasableSyntaxOnly`, `noFallthroughCasesInSwitch` — see `tsconfig.app.json`). No `any` without
  a specific justification in a comment.
- Function components + hooks only — no class components, **except** `ErrorBoundary`, which must
  be class-based because React error boundaries require `getDerivedStateFromError` /
  `componentDidCatch`, which have no hook equivalent.
- Path aliases: `@/*` maps to `src/*` (configured in `tsconfig.app.json` `paths` and
  `vite.config.ts` `resolve.alias`). No `baseUrl` — deprecated as of the TypeScript version this
  project pins; `paths` alone resolves relative to the tsconfig file.
- ESLint (flat config, `eslint.config.js`) + Prettier (`.prettierrc`, 100-char print width, double
  quotes not enforced — Prettier defaults). Run `npm run lint` and `npm run format:check` before
  committing; `npm run format` to auto-fix.
- `react-hooks` ESLint rules are enforced at the "error" level for `set-state-in-effect`: don't
  call `setState` synchronously in the body of a `useEffect` — reset state in the event handler
  that triggers the effect instead (see `HealthCheckPage`'s retry button for the pattern).
- Components under `presentation/components/ui/` are shadcn/ui primitives — treat them as
  copied-in source you own and can edit, not a locked third-party dependency.
- Tests: Vitest + React Testing Library, colocated with the component (`Component.test.tsx` next
  to `Component.tsx`). Mock at the module boundary (e.g. `vi.mock("@/infrastructure/api/httpClient")`)
  rather than mocking `fetch` globally.

## Both

- No feature flags or backwards-compatibility shims for code that can simply be changed — this is
  a greenfield project with no external consumers yet.
- No dead code, no commented-out code blocks.
- Documentation (this file included) is part of the codebase — see
  [DevelopmentGuide.md](DevelopmentGuide.md) for when/how it must be updated.
