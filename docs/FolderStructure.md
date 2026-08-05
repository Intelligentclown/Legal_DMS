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
│   │   └── versions/             # 12 migrations: 11 schema sections + 1 seed-data migration
│   ├── src/app/
│   │   ├── main.py               # FastAPI app factory
│   │   ├── domain/                common/entity.py — base Entity/ValueObject/AggregateRoot/Result,
│   │   │                          events/domain_event.py
│   │   ├── application/
│   │   │   ├── common/             BaseService, validation, pagination/query shapes
│   │   │   ├── errors/            AppError hierarchy
│   │   │   ├── interfaces/         framework-agnostic ports (repository, event_bus, job_queue,
│   │   │   │                       file_storage, notifier, auth, audit, search, feature_flags)
│   │   │   └── workflow/            WorkflowDefinition/WorkflowEngine (generic state machine)
│   │   ├── infrastructure/
│   │   │   ├── config/             Settings (pydantic-settings), feature_flags.py
│   │   │   ├── logging/            structured JSON logging
│   │   │   ├── database/           SQLAlchemy Base (naming_convention), async engine/session
│   │   │   ├── di/                 Container, configure_container()
│   │   │   ├── events/ jobs/ storage/ notifications/ auth/ audit/ search/ modules/
│   │   │   │                       one minimal default implementation per Stage 1 port
│   │   │   └── persistence/
│   │   │       ├── sqlalchemy_repository.py   SqlAlchemyRepository[ModelT] (generic, Stage 1)
│   │   │       └── models/                     Stage 2: the complete 49-table schema —
│   │   │           mixins.py                    AuditMixin, OptimisticLockMixin
│   │   │           identity.py                  users, roles, permissions, user_roles, role_permissions
│   │   │           geography.py                 countries, states, districts, talukas, villages
│   │   │           client.py                    addresses, clients, client_contacts
│   │   │           property.py                  properties, property_owners
│   │   │           matter.py                    matter_types, matter_statuses, matters
│   │   │           workflow.py                  workflow_definitions/states/history
│   │   │           document.py                  document_types/templates/variables, documents, document_versions
│   │   │           storage.py                   file_storage_records, ocr_jobs/results, qr_code_records, backups
│   │   │           financial.py                 payment_methods, invoices, payments, receipts
│   │   │           activity.py                  activity_logs, audit_logs, notifications
│   │   │           scheduling.py                tasks, appointments, tags, matter_tags
│   │   │           system.py                    application_settings, feature_flags, ai_requests/responses,
│   │   │                                         plugin_registry, background_jobs, system_events
│   │   ├── presentation/
│   │   │   ├── api/v1/             health.py, version.py, router.py
│   │   │   ├── api/deps.py          SettingsDep, DBSessionDep, CurrentUserDep
│   │   │   ├── common/               ApiResponse, build_crud_router() (test-only, never mounted)
│   │   │   └── middleware/          RequestIDMiddleware, LoggingMiddleware, error_handler.py
│   │   └── workers/                 JobRegistry, NoOpJob (no business jobs)
│   └── tests/
│       ├── conftest.py            client fixture (TestClient) + shared async db_session fixture
│       ├── unit/                   AppError + Settings tests
│       ├── support/                 in-memory test fakes (repository, etc.)
│       └── integration/            health/version endpoint tests, sqlalchemy_repository tests,
│                                    and one test_*_models.py per Stage 2 schema section +
│                                    test_seed_data.py
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
- `infrastructure/persistence/models/` is no longer an empty seam — Stage 2 filled it with the
  complete 49-table schema. It's still unwired, though: no repository, service, or route reads or
  writes through these models yet. `application/interfaces/` and `workers/` remain empty seams for
  future feature modules — see [Architecture.md](Architecture.md) for what goes where.
- Full file-by-file annotation of what each backend/frontend file does lives inline as module
  docstrings/comments — this document tracks structure, not implementation detail.
