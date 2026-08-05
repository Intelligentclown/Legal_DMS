# Frontend

React + TypeScript + Vite + Tailwind CSS + shadcn/ui, following the Clean Architecture layering
described in [`/docs/Architecture.md`](../docs/Architecture.md).

See the [repo root README](../README.md) for full setup instructions (installing, running
alongside the backend and Electron, testing). Quick reference for this package alone:

```bash
npm install
cp .env.example .env
npm run dev            # start the Vite dev server
npm run lint            # ESLint
npm run format           # Prettier — write
npm run format:check      # Prettier — check only
npm run build            # type-check + production build
```
