# ADR-0006: Monorepo layout with `apps/*` and `workers/`

- Status: Accepted
- Date: 2026-04-15
- Deciders: @Rakesh1002

## Context

UnSearch ships:

- A Python FastAPI backend
- A Next.js dashboard
- A Cloudflare Workers edge router (Hono)
- A TypeScript SDK
- A Python SDK
- A LlamaIndex retriever
- (Soon) an MCP server, a LangChain integration, more

These don't all share a language, but they *do* share types (request/response shapes), test fixtures, and release cadence. A multi-repo layout would mean N CI pipelines, N versions of the same TypeScript types, and a guaranteed drift between SDK packages and the API they call.

## Decision

Use a **single Git repository** with this layout:

```
unsearch/
├── app/                    # Legacy single-package FastAPI backend (kept as authoritative origin)
├── apps/                   # Monorepo packages
│   ├── backend/            # Same FastAPI code, packaged for Container deploy
│   ├── web/                # Next.js dashboard (on Workers via @opennextjs/cloudflare)
│   ├── sdk-ts/             # @unsearch/sdk — TypeScript SDK
│   ├── sdk-py/             # unsearch — Python SDK
│   └── sdk-llamaindex/     # @unsearch/llamaindex — LlamaIndex retriever
├── workers/                # Cloudflare Workers edge router + Durable Objects + D1 schema
├── docs/                   # All long-form docs (this directory)
├── alembic/                # Postgres migrations (origin DB)
├── searxng/                # SearXNG meta-search engine config
├── monitoring/             # Prometheus + Grafana provisioning
└── docker-compose*.yml     # Self-host stacks
```

- **JavaScript/TypeScript packages** use **pnpm workspaces** (`pnpm-workspace.yaml`) — one lockfile, one `node_modules`, fast install.
- **Python packages** are independent — backend uses `requirements.txt` (root) and a Poetry-managed `pyproject.toml` (`apps/backend/`); SDK uses Hatchling (`apps/sdk-py/pyproject.toml`). No shared Python lockfile.
- **CI scoping** — each `apps/*/` package has its own workflow under `.github/workflows/` (e.g., `sdk-py.yml`) triggered on `paths:` filters so unrelated changes don't run unrelated CI.

The `app/` directory at the repo root is the **historic** single-package backend layout from v1. We kept it because it's the directory production currently imports from (`uvicorn app.main:app`) and migrating that import path is a separate change with its own deploy risk. `apps/backend/` is the monorepo-shaped mirror that builds the Docker image — same code, different packaging boundary.

## Consequences

- **Pro:** A single PR can change the API endpoint shape and the SDK that consumes it. The diff is the proof of consistency. CI runs the matching tests for both.
- **Pro:** New SDK languages (Go, Ruby, MCP server) drop into `apps/sdk-*/` with a clear template (mirror the TS SDK surface — see [ADR-0007](./0007-python-sdk-sync-and-async.md)).
- **Pro:** Docs, ADRs, and code live next to each other. `git blame` on an architecture doc lands in the same history as the code it describes.
- **Con:** Repo size grows monotonically. We mitigate with `path:` filters in CI and per-app `.gitignore`s, but `git clone` time is non-trivial for new contributors.
- **Con:** Two backend layouts (`app/` and `apps/backend/`) is confusing for newcomers. The `docs/what-is-what.md` map documents this explicitly. A future PR will collapse them.
- **Con:** Tooling has to be polyglot — Python tests with pytest, TypeScript with vitest, the worker with `wrangler dev`. There's no single "run all tests" command; we accept this in exchange for keeping each ecosystem's conventions.

## Alternatives considered

- **Multi-repo (one per package).** Rejected — would have made the Tavily-compatibility cross-validation (see [ADR-0003](./0003-tavily-compatible-drop-in-surface.md)) impossible to keep in sync, and forced N versions of each TypeScript type.
- **Nx / Turborepo as the build orchestrator.** Considered. Turborepo is currently in use for the JS side (`.turbo/` exists). We deliberately stop short of using it to orchestrate the Python side; Python tooling is mature enough on its own.
- **Git submodules for SDKs.** Rejected outright — submodules guarantee broken `git clone --recurse-submodules` UX for at least 30% of contributors.
- **`packages/` instead of `apps/`.** Considered. `apps/` won because it reads as "deployable unit," and the SDK packages are *also* deployable (to PyPI / npm) — making `packages/` redundant.
