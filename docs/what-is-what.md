# What is what

> Plain-language map of the repo so a new contributor can navigate in 5 minutes. For the *why*, see [`adr/`](./adr/README.md). For the runtime picture, see [`architecture.md`](./architecture.md).

## Top-level tour

```
unsearch/
├── README.md                ← Start here. Repo overview + quick start.
├── CHANGELOG.md             ← What shipped in each release.
├── CLAUDE.md                ← Per-repo conventions for Claude Code sessions.
├── CONTRIBUTING.md          ← How to propose changes. PR template, test expectations.
├── LICENSE                  ← Apache 2.0. See ADR-0005.
├── Makefile                 ← `make dev`, `make test`, etc. Wraps backend operations.
├── pnpm-workspace.yaml      ← Declares apps/* + workers as a pnpm workspace.
│
├── backend/                 ← Python FastAPI backend. Single source of truth post-2026-05-28.
│   ├── app/                 ←   Python module (`from app.X import Y`). 93 endpoints across 14 routers.
│   ├── alembic/             ←   Postgres migrations (origin DB).
│   ├── alembic.ini          ←   Alembic config.
│   ├── pytest.ini           ←   Backend pytest config.
│   ├── requirements.txt     ←   Backend Python deps.
│   ├── tests/               ←   Backend test suite (unit + integration + performance + smoke + e2e).
│   ├── Dockerfile           ←   FastAPI Container image (self-host).
│   └── Dockerfile.cloudflare ←   FastAPI Container image for Cloudflare Containers GA.
│
├── apps/                    ← TypeScript / Python SDK packages (pnpm workspace).
│   ├── web/                 ←   Next.js dashboard on Cloudflare Workers (@opennextjs/cloudflare).
│   ├── sdk-ts/              ←   @unsearch/sdk — TypeScript SDK.
│   ├── sdk-py/              ←   unsearch — Python SDK (sync + async). See ADR-0007.
│   ├── sdk-llamaindex/      ←   @unsearch/llamaindex — LlamaIndex retriever.
│   └── mcp-server/          ←   @unsearch/mcp-server — MCP server (P0 Week 3, npx-runnable).
│
├── workers/                 ← Cloudflare Workers edge — Hono router, MCP transport, Durable Objects, D1 schema, containers.toml.
│
├── infra/                   ← Operational config (self-host stack + CF Container sidecars).
│   ├── nginx/               ←   Reverse-proxy config for self-host TLS termination.
│   ├── monitoring/          ←   Prometheus + Grafana provisioning. Dashboards in grafana/dashboards/.
│   └── searxng/             ←   SearXNG meta-search engine config (2,841-line production settings.yml). See ADR-0002.
│
├── docs/                    ← All long-form docs.
│   ├── README.md            ←   Doc-directory index. Read this first if you're confused.
│   ├── architecture.md      ←   Current architecture overview.
│   ├── what-is-what.md      ←   ← you are here.
│   ├── adr/                 ←   Architecture Decision Records (0001–0013).
│   ├── citation-envelope.md ←   Signed envelope schema + signing. See ADR-0011.
│   ├── feature-matrix.md    ←   Honest ✅ / 🔶 / 📋 status per feature.
│   ├── roadmap.md           ←   ICP-ordered priorities. P0 → P5.
│   ├── strategy/            ←   Problem, ICP, GTM, pricing, positioning, user journey.
│   ├── operations/          ←   Runbooks. Read before on-call.
│   ├── deployment/          ←   Per-target deploy guides (Cloudflare, Railway, DigitalOcean).
│   ├── configuration/       ←   Env vars + Stripe webhook setup.
│   ├── migration/           ←   Migration guide from Tavily (compatibility surface — see ADR-0003).
│   ├── API_REFERENCE.md     ←   Full endpoint catalog. Live OpenAPI at /docs.
│   ├── API_EXAMPLES.md      ←   Worked examples per endpoint.
│   ├── ai-pipeline.md       ←   Models, embeddings, reranking. See ADR-0004.
│   ├── cloudflare-architecture.md ← Edge / Containers / D1 / Vectorize wiring detail. See ADR-0001 + ADR-0010.
│   ├── BILLING_SETUP.md     ←   Stripe products + prices + portal config.
│   ├── SECRETS_MANAGEMENT.md ←  How we handle env secrets in self-host and prod.
│   ├── introduction.mdx     ←   Public docs site entry (Mintlify).
│   ├── mint.json            ←   Mintlify navigation config.
│   └── quickstart.md        ←   Self-host quickstart.
│
├── scripts/                 ← Setup + ops scripts (manage.sh, setup-stripe.sh, setup_stripe.py, deploy.sh, …).
│
├── docker-compose.yml             ← Self-host: full stack (API + SearXNG + Postgres + Redis + Celery + nginx).
├── docker-compose.quickstart.yml  ← Self-host: minimal stack (API + SearXNG + Postgres + Redis).
├── docker-compose.prod.yml        ← Self-host: production overrides.
├── ecosystem.config.js            ← PM2 config for bare-metal self-host (cwd=./backend, env_file=../.env).
├── quickstart.sh                  ← `curl … | bash` quickstart for self-host.
├── manage.sh                      ← Symlink → scripts/manage.sh.
│
├── .env.example             ← Copy to .env. Required: CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN.
└── .gitignore               ← Including .turbo/, .venv, node_modules/, __pycache__/, etc.
```

## Layer by layer — what runs what

```
                       ┌─────────────────────────────────┐
        Public         │   apps/web   (Next.js → Workers)│  app.unsearch.dev
                       └─────────────────────────────────┘
                                       │
                                       ▼
                       ┌─────────────────────────────────┐
        Edge           │   workers/   (Hono on Workers)  │  api.unsearch.dev
                       │   + MCP server at /mcp          │  api.unsearch.dev/mcp
                       │   + Durable Objects (RateLimiter,│
                       │     TopicMonitor, ResearchAgent, │
                       │     SessionManager)              │
                       │   + Queues consumer              │
                       └──────────────────┬──────────────┘
                                          │ service binding
                                          ▼
                       ┌─────────────────────────────────┐
        Container      │   backend/   (FastAPI)          │  Cloudflare Containers GA (active-CPU billing)
                       │   - app/services/* (Python 3.11)│
                       │   - SearXNG sidecar (port 8080) │
                       │   - 93 endpoints across 14 routers
                       │   - Signed citation envelope per result
                       └──────────────────┬──────────────┘
                                          │
                       ┌──────────────────┴───────────────────┐
                       ▼                                      ▼
                ┌──────────────┐                       ┌──────────────┐
        State   │  Cloudflare  │              Origin   │  Postgres    │
                │  D1 / KV /   │              (self-   │  + Redis     │
                │  R2 / Vec    │               host)   │  + SearXNG   │
                └──────────────┘                       └──────────────┘
```

## Glossary

Terms that show up in code and docs without being defined.

| Term | What it means here |
|------|--------------------|
| **Edge worker** | The Cloudflare Workers script in `workers/`. Fronts every request. |
| **Container** | The Cloudflare Containers FastAPI deployment. Source in `backend/app/`, packaged via `backend/Dockerfile.cloudflare`. See ADR-0010. |
| **DO** | Durable Object. Cloudflare's per-instance stateful actor. We have four — see `workers/src/durable-objects/`. |
| **KV** | Cloudflare's eventually-consistent key/value store. Used for hot caches (auth, ratelimit, search). |
| **D1** | Cloudflare's edge SQL database (SQLite dialect). Primary store for users, plans, API keys, audit log, citation envelopes. |
| **R2** | Cloudflare's object storage (S3-compatible). Stores content-addressable citation snapshots (sha256-keyed). |
| **Vectorize** | Cloudflare's vector database. Stores `bge-m3` embeddings, 1024 dims. |
| **Queues** | Cloudflare's managed message queue. Used for monitor-fire fan-out and async research steps. |
| **Service binding** | A Workers-to-Workers (or Worker-to-Container) call that skips the public internet. Worker → Container in our case. |
| **Tier (model_tier)** | The four Workers AI tiers: `fast`, `balanced`, `reasoning`, `production`. See ADR-0004. |
| **Citation envelope** | The signed `{url, sha256, fetched_at, snapshot_r2_key, signature, …}` record returned with every result. See ADR-0011 + [`citation-envelope.md`](./citation-envelope.md). |
| **Verify** | The `verify_claim` MCP tool / `POST /api/v1/verify/claim` endpoint — span-level evidence + confidence against a source URL. See ADR-0009. |
| **Drop-in (Tavily-compatible)** | Endpoints under `/api/v1/agent/*` that mirror Tavily's request/response shape. Compatibility surface, not lead positioning. See ADR-0003. |
| **Namespace (in `/api/v1/rag/*`)** | A logical partition inside Vectorize. Each customer's RAG corpus lives in their own namespace. |
| **`uns_` API key** | Customer-facing API key. Header: `X-API-Key: uns_...`. |
| **🔶 in beta** | Feature exists in code but is being hardened. See ADR-0008. |
| **🚀 differentiator** | Feature that no closed-source competitor has. Used in `docs/feature-matrix.md`. |
| **ICP-1 / ICP-2 / ICP-3** | The three personas: Priya (regulated-AI startup eng lead), David (regulated-company AI platform director), Anika (citation-integrity research / journalism). Defined in [`strategy/icp.md`](./strategy/icp.md). |

## "Where does that live?" cheat sheet

| You want to… | Open this |
|--------------|-----------|
| Read an endpoint's contract | [`API_REFERENCE.md`](./API_REFERENCE.md) or `http://localhost:8000/docs` |
| See an endpoint's worked example | [`API_EXAMPLES.md`](./API_EXAMPLES.md) |
| Change request validation | `backend/app/models/requests.py` |
| Change a route handler at the edge | `workers/src/routes/*.ts` |
| Change a route handler in the Container | `backend/app/api/v1/*.py` |
| Add a Durable Object | `workers/src/durable-objects/` + binding in `workers/wrangler.toml` |
| Add a new Cloudflare resource (KV, R2, etc.) | `workers/wrangler.toml` + a Python REST client in `backend/app/services/core/` |
| Tweak Workers AI model selection | `backend/app/services/ai/` + ADR-0004 |
| Touch the SearXNG engine config | `infra/searxng/settings.yml` |
| Touch DB schema (edge) | `workers/schema.sql` (D1) |
| Touch DB schema (origin) | `backend/alembic/versions/*.py` then `make migrate` |
| Update the dashboard | `apps/web/app/` |
| Update the public SDK contracts | All three of: `apps/sdk-ts/src/index.ts`, `apps/sdk-py/src/unsearch/client.py`, `apps/sdk-llamaindex/src/index.ts` |
| Add a Stripe product | `scripts/setup-stripe.sh` then run it, or `python scripts/setup_stripe.py` |
| Add a Stripe webhook | [`configuration/stripe-webhook.md`](./configuration/stripe-webhook.md) |
| Wire a new env var | `.env.example` (root) + `docs/configuration/env-variables.md` + the consuming code |
| Trigger a deploy | [`deployment/quick-reference.md`](./deployment/quick-reference.md) |
| Investigate a prod incident | [`operations/RUNBOOKS.md`](./operations/RUNBOOKS.md) |
| Add a non-obvious architectural decision | [`adr/README.md`](./adr/README.md) |

## Naming conventions

| Pattern | Where | Example |
|---------|-------|---------|
| `snake_case` | Python, JSON request/response fields | `model_tier`, `cache_hit` |
| `camelCase` | TypeScript SDK methods, internal | `neuralSearch`, `verifyClaim` |
| `kebab-case` | URL paths, npm packages, docker images | `/api/v1/verify/claim`, `@unsearch/sdk` |
| `PascalCase` | TypeScript classes, Python classes | `UnSearch`, `AsyncUnSearch`, `RateLimiter` |
| `SCREAMING_SNAKE` | Env vars | `CLOUDFLARE_API_TOKEN` |

When the same field crosses a language boundary (e.g., a Python TypedDict that mirrors a TS interface), we always pick **snake_case for the wire format** and let each language convert as idiomatic.

## How to read a PR

When a PR lands, the order of relevant files is usually:

1. `backend/app/api/v1/*.py` or `workers/src/routes/*.ts` — the route handler
2. `backend/app/services/*` — supporting service code
3. `apps/sdk-*/` — if the wire format changed, the SDKs follow in lockstep
4. `docs/API_REFERENCE.md` + `docs/feature-matrix.md` — if the docs are out of date, request changes
5. `CHANGELOG.md` — `[Unreleased]` section should reflect the change
6. `docs/adr/` — only for cross-cutting decisions, not feature work

If a PR adds a new architectural decision and *doesn't* include an ADR, that's a review comment ("please write an ADR-NNNN for this").
