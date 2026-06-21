---
rros_project: unsearch
rros_doc_id: unsearch/docs/tech/adr/0006-monorepo-with-apps-and-workers.md
notion_page_id: 386e4a4b-2a11-819b-bcdd-e6699dc4ce60
rros_domain: adr
---

# ADR-0006: Monorepo layout — single `apps/*` workspace + `backend/` + `infra/`
- Status: Accepted (amended 2026-05-28: dual backends collapsed; backend moved into `backend/`, ops into `infra/`, workers moved into `apps/workers/`)
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
```javascript
unsearch/
├── backend/                # FastAPI Python backend (the only non-`apps/` deployable; reflects Python's single-tree convention)
│   ├── app/                #   Python module (`from app.X import Y`)
│   ├── alembic/            #   Postgres migrations
│   ├── tests/              #   pytest suite
│   ├── requirements.txt    #   Python deps
│   ├── pytest.ini          #   pytest config
│   ├── alembic.ini         #   Alembic config
│   ├── Dockerfile          #   Self-host image
│   └── Dockerfile.cloudflare #   CF Containers image
├── apps/                   # All TypeScript / SDK packages (pnpm workspace; `apps/*` glob in pnpm-workspace.yaml)
│   ├── workers/            #   Cloudflare Workers edge router (Hono) + Durable Objects + D1 schema + MCP transport
│   ├── web/                #   Next.js dashboard (on Workers via @opennextjs/cloudflare)
│   ├── sdk-ts/             #   @unsearch/sdk — TypeScript SDK
│   ├── sdk-py/             #   unsearch — Python SDK
│   ├── sdk-llamaindex/     #   @unsearch/llamaindex — LlamaIndex retriever
│   └── mcp-server/         #   @unsearch/mcp-server — npx-runnable MCP wrapper (P0 Week 3)
├── infra/                  # Operational config (self-host stack + CF Container sidecars)
│   ├── nginx/              #   Reverse-proxy for self-host TLS
│   ├── monitoring/         #   Prometheus + Grafana provisioning
│   └── searxng/            #   SearXNG meta-search engine config
├── docs/                   # All long-form docs (this directory)
├── scripts/                # Setup + ops scripts
└── docker-compose*.yml     # Self-host stacks (build context = root; mount paths from infra/)
```
- **JavaScript/TypeScript packages** use **pnpm workspaces** (`pnpm-workspace.yaml`) — one lockfile, one `node_modules`, fast install.
- **Python backend** lives under `backend/` (module name stays `app/` so `uvicorn app.main:app` still works when invoked from `backend/`). The Python SDK at `apps/sdk-py/` is independently packaged with Hatchling — no shared Python lockfile.
- **Operational config** lives under `infra/` — `nginx/`, `monitoring/`, `searxng/`. `docker-compose*.yml` stays at the root (compose convention) but mounts paths from `infra/`.
- **All TypeScript / SDK packages live under ****`apps/*`** — the Cloudflare edge worker, the Next.js dashboard, all SDKs, and the MCP server. `pnpm-workspace.yaml` is a single `apps/*` glob; nothing is registered outside it.
- **CI scoping** — each `apps/*/` package has its own workflow under `.github/workflows/` (e.g., `sdk-py.yml`) triggered on `paths:` filters so unrelated changes don't run unrelated CI.
The `backend/` directory is the single source of truth for the backend. (Prior to the 2026-05-28 reorg, the backend was at `app/` at the repo root, and prior to that, there was *also* a duplicate `apps/backend/` — see Amendment below.)
## Amendment — 2026-05-28 (part 1): `apps/backend/` consolidated into root `app/`
The original "two backend layouts" footnote in the Consequences section became real friction. Audit found that `apps/backend/` had diverged from `app/`:
- Different branding (`UnQuestRequest` vs `UnSearchRequest`)
- Different import paths (`app.services.searxng` vs `app.services.core.searxng`)
- Fewer Alembic migrations (2 vs 5)
- Different `pytest.ini` DB config (sqlite vs postgres)
- A 2,841-line production SearXNG `settings.yml` that was never mounted (the live mount path at `searxng/settings.yml` was a 40-line stub)
- A stale `.github/workflows/deploy.yml` targeting Railway via `cd apps/backend` (Railway deploy is sunset by [ADR-0010](./0010-cloudflare-containers-as-origin-runtime.md))
`apps/backend/` was removed in PR #7. The production SearXNG config was salvaged to `searxng/settings.yml` (later moved to `infra/searxng/settings.yml` — see Part 2). The Railway workflow was removed. The active `.github/workflows/ci-cd.yml` and `deploy-cf.yml` already targeted root `app/` and `workers/`. No production code path was affected.
## Amendment — 2026-05-28 (part 2): Backend moved into `backend/`; ops into `infra/`
The root layout had `app/` (Python backend) sitting one letter away from `apps/` (TypeScript monorepo) — two completely different things, easy to confuse. Backend-orbiting files (`alembic/`, `pytest.ini`, `requirements.txt`, `tests/`, `Dockerfile`, `Dockerfile.cloudflare`) were also scattered at root, making it unclear which belonged to the backend vs which were repo-wide. Operational config (`nginx/`, `monitoring/`, `searxng/`) was also at root with no clustering.
This reorg:
- Moves `app/` → `backend/app/` (Python module name unchanged — `from app.X import Y` still works because `backend/` is the cwd at runtime).
- Moves `alembic/`, `pytest.ini`, `requirements.txt`, `tests/`, `Dockerfile`, `Dockerfile.cloudflare` into `backend/`.
- Moves `nginx/`, `monitoring/`, `searxng/` into `infra/`.
- Updates Dockerfiles to prefix host paths with `backend/` (build context = repo root).
- Updates `docker-compose*.yml` build contexts and volume paths.
- Updates `.github/workflows/{ci-cd,deploy-cf}.yml` to prefix `backend/` on lint / test / coverage paths.
- Updates `Makefile`, `scripts/manage.sh`, `scripts/test.sh`, `scripts/setup.sh`, `scripts/run_rag_tests.sh`, `scripts/restore.sh`, `ecosystem.config.js` to `cd backend` before backend operations.
The Python module path stays `app/`. The on-disk path becomes `backend/app/`. uvicorn invocation stays `uvicorn app.main:app` (now invoked from `backend/`). No runtime imports or wire formats change.
## Amendment — 2026-05-28 (part 3): `workers/` moved into `apps/workers/`
The Part 2 layout still had `workers/` (Cloudflare edge router) as a sibling of `backend/` and `apps/` at the root. That was inconsistent: `apps/web` was already a Cloudflare Workers deployment but lived under `apps/`, while `apps/workers/` (the API edge router) sat at root. Two Workers deployments, two different shelves.
Decision: move `workers/` → `apps/workers/`. The single rule for `apps/*` becomes: **any deployable TypeScript / SDK package belongs in ****`apps/`** — including the Cloudflare edge worker.
`backend/` stays at the root, not under `apps/`, because (a) it's Python (different language, different runtime), (b) its `app/` Python module name would collide with the `apps/` directory if nested, and (c) the Python convention is one source tree per project, not a workspace of subpackages.
Mechanical changes in the part-3 PR:
- `git mv workers apps/workers`.
- `pnpm-workspace.yaml` collapses to just `- "apps/*"` (no separate `- "workers"` line).
- `apps/workers/containers.toml` build context: `..` → `../..`; dockerfile: `../backend/Dockerfile.cloudflare` → `../../backend/Dockerfile.cloudflare`.
- `.github/workflows/deploy-cf.yml`: every `working-directory: workers` and `workingDirectory: workers` → `apps/workers`; `cache-dependency-path: workers/pnpm-lock.yaml` → `apps/workers/pnpm-lock.yaml`.
- `scripts/cf-provision.sh`: `cd "$REPO_ROOT/workers"` → `cd "$REPO_ROOT/apps/workers"`.
- `backend/Dockerfile.cloudflare` comment header: `workers/containers.toml` → `apps/workers/containers.toml`.
- All docs (`docs/architecture.md`, `docs/what-is-what.md`, `docs/README.md`, `docs/citation-envelope.md`, `docs/roadmap.md`, `docs/strategy/{user-journey,pricing}.md`, ADRs 0001 / 0010, [README.md](http://README.md)): `workers/...` references → `apps/workers/...`. Historical CHANGELOG entries are left as-is (history is history).
The Worker's internal Hono routes, Durable Object bindings, D1 schema, MCP transport, wrangler.toml, and all source code are unchanged.
Concurrently in part 3, the now-empty `apps/backend/` directory was removed (the gitignored `.env` from before is left for the user to manually relocate to `backend/.env` on their local checkout — it can't ship through git).
## Consequences
- **Pro:** A single PR can change the API endpoint shape and the SDK that consumes it. The diff is the proof of consistency. CI runs the matching tests for both.
- **Pro:** New SDK languages (Go, Ruby, MCP server) drop into `apps/sdk-*/` with a clear template (mirror the TS SDK surface — see [ADR-0007](./0007-python-sdk-sync-and-async.md)).
- **Pro:** Docs, ADRs, and code live next to each other. `git blame` on an architecture doc lands in the same history as the code it describes.
- **Con:** Repo size grows monotonically. We mitigate with `path:` filters in CI and per-app `.gitignore`s, but `git clone` time is non-trivial for new contributors.
- **Resolved 2026-05-28:** ~~Two backend layouts (~~~~`app/`~~~~ and ~~~~`apps/backend/`~~~~) is confusing for newcomers.~~ See Amendment above — `apps/backend/` removed; root `app/` is now the single source of truth.
- **Con:** Tooling has to be polyglot — Python tests with pytest, TypeScript with vitest, the worker with `wrangler dev`. There's no single "run all tests" command; we accept this in exchange for keeping each ecosystem's conventions.
## Alternatives considered
- **Multi-repo (one per package).** Rejected — would have made the Tavily-compatibility cross-validation (see [ADR-0003](./0003-tavily-compatible-drop-in-surface.md)) impossible to keep in sync, and forced N versions of each TypeScript type.
- **Nx / Turborepo as the build orchestrator.** Considered. Turborepo is currently in use for the JS side (`.turbo/` exists). We deliberately stop short of using it to orchestrate the Python side; Python tooling is mature enough on its own.
- **Git submodules for SDKs.** Rejected outright — submodules guarantee broken `git clone --recurse-submodules` UX for at least 30% of contributors.
- **`packages/`**** instead of ****`apps/`****.** Considered. `apps/` won because it reads as "deployable unit," and the SDK packages are *also* deployable (to PyPI / npm) — making `packages/` redundant.
