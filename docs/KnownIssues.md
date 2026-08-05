# Known Issues

## shadcn/ui CLI is broken on this Windows setup

`npx shadcn@latest init` and `npx shadcn@latest add <component>` fail on this machine
(shadcn CLI 4.16.1 and 4.15.0 both tested). `init` fails with "Could not load the workspace
config" after writing `components.json`. `add` runs but writes files to a **literal directory
named `@`** instead of resolving the `@/...` path alias — e.g. it created
`frontend/@/components/ui/button.tsx` instead of
`frontend/src/presentation/components/ui/button.tsx`.

**Workaround used in Stage 0:** installed the underlying dependencies directly
(`class-variance-authority`, `clsx`, `tailwind-merge`, `radix-ui`, `lucide-react`) and
hand-authored `frontend/src/presentation/components/ui/button.tsx` by adapting the CLI's
(misplaced) output. This is legitimate — shadcn/ui components are meant to be copied into your
repo and owned, not consumed as a locked npm package.

**Impact going forward:** don't rely on `shadcn add` to work automatically on Windows with this
CLI version. To add a new shadcn component: copy the source from ui.shadcn.com, place it under
`frontend/src/presentation/components/ui/`, and fix the import path to
`@/shared/utils/cn` (this project's `cn()` location, not the shadcn-default `@/lib/utils`).

## `react-router-dom` has one open high-severity advisory

`npm audit` flags [GHSA-qwww-vcr4-c8h2](https://github.com/advisories/GHSA-qwww-vcr4-c8h2) ("RSC
Mode CSRF Bypass") against `react-router` `7.12.0`–`8.2.0`, which covers every currently-published
`7.x` release (`7.18.2` at time of writing). **Accepted as not applicable**: this project uses
`react-router-dom` in plain client-side SPA mode (`createBrowserRouter`, no RSC/framework mode, no
server actions) — the vulnerable code path isn't reachable. Downgrading to the last unaffected
version (`7.11.0`) was tried and reintroduced several *other*, more severe, already-patched
advisories, so it was reverted. Re-check `npm audit` when upgrading `react-router-dom` and confirm
a patched `7.x`/`8.x` release exists before assuming this is still the only one.

## Backend can't be verified against Postgres without Docker

`alembic upgrade head` and any DB-touching code require a running Postgres. If Docker isn't
available in a given environment, only DB-independent checks are possible (app import, `TestClient`
requests to `/health`/`/version`, `alembic history` which loads `env.py` but doesn't connect). This
was hit once during Stage 0 development (Docker wasn't installed yet) and resolved once Docker
Desktop was installed — see [SessionReport.md](SessionReport.md).
