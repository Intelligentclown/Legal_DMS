# Folder Structure

```
Legal_DMS/
├── .editorconfig
├── .gitignore
├── .gitattributes
├── docker-compose.yml           # local Postgres for development
├── .env.example                 # docker-compose Postgres credentials
├── .vscode/                     # workspace settings + recommended extensions
├── README.md
├── CHANGELOG.md                 # pointer to docs/CHANGELOG.md
├── package.json                 # root: Electron build/dev orchestration
├── electron-builder.yml         # packaging config
│
├── docs/                        # project memory system — see docs/README.md
├── ADR/                         # architecture decision records
│
├── backend/
│   ├── pyproject.toml           # uv-managed, deps + tool config
│   ├── uv.lock
│   ├── ruff.toml
│   ├── pytest.ini
│   ├── alembic.ini
│   ├── .env.example
│   ├── alembic/                 # async template; env.py reads DATABASE_URL from Settings
│   │   └── versions/             # empty — no business migrations yet
│   ├── src/app/
│   │   ├── main.py               # FastAPI app factory
│   │   ├── domain/                common/entity.py — base Entity/ValueObject
│   │   ├── application/
│   │   │   ├── errors/            AppError hierarchy
│   │   │   └── interfaces/         future repository ports (empty)
│   │   ├── infrastructure/
│   │   │   ├── config/             Settings (pydantic-settings)
│   │   │   ├── logging/            structured JSON logging
│   │   │   ├── database/           SQLAlchemy Base, async engine/session
│   │   │   └── persistence/         future repository implementations (empty)
│   │   ├── presentation/
│   │   │   ├── api/v1/             health.py, version.py, router.py
│   │   │   ├── api/deps.py          SettingsDep, DBSessionDep
│   │   │   └── middleware/          RequestIDMiddleware, LoggingMiddleware, error_handler.py
│   │   └── workers/                 future background jobs (empty)
│   └── tests/
│       ├── conftest.py            client fixture (FastAPI TestClient)
│       ├── unit/                   test_example.py — AppError + Settings tests
│       └── integration/            test_health_endpoint.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts / vitest.config.ts
│   ├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
│   ├── eslint.config.js / .prettierrc
│   ├── components.json           # shadcn/ui config (aliases match this project's layout)
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── index.css              # Tailwind v4 import + shadcn CSS variable theme
│       ├── app/                    App.tsx, routes.tsx, providers/
│       ├── presentation/            layouts/, pages/, components/ (incl. components/ui/)
│       ├── application/services/     future use-case orchestration (empty)
│       ├── domain/types/              shared TS types (health.ts)
│       ├── infrastructure/            api/httpClient.ts, ipc/ipcBridge.ts
│       ├── shared/                    config/env.ts, utils/cn.ts, constants/
│       └── test/                      setup.ts (Vitest/jsdom)
│
└── electron/
    ├── main.ts
    ├── preload.ts
    ├── ipc/channels.ts
    └── tsconfig.json
```

## Notes

- `frontend/` and `backend/` are independent projects with their own lockfiles/toolchains
  (npm and uv respectively) — the root `package.json` only orchestrates Electron + dev scripts,
  it does not use npm workspaces.
- Every `infrastructure/persistence`, `application/interfaces`, and `workers/` folder is an
  intentionally empty seam for future feature modules — see
  [Architecture.md](Architecture.md) for what goes where.
- Full file-by-file annotation of what each backend/frontend file does lives inline as module
  docstrings/comments — this document tracks structure, not implementation detail.
