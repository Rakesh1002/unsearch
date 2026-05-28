# What is what

> Plain-language map of the repo so a new contributor can navigate in 5 minutes. For the *why*, see [`adr/`](./adr/README.md). For the runtime picture, see [`architecture.md`](./architecture.md).

## Top-level tour

```
unsearch/
├── README.md               ← Start here. Repo overview + quick start.
├── CHANGELOG.md            ← What shipped in each release. Source of truth for release notes.
├── CLAUDE.md               ← Per-repo conventions for Claude Code sessions (and human contributors).
├── CONTRIBUTING.md         ← How to propose changes. PR template, test expectations.
├── LICENSE                 ← Apache 2.0. See ADR-0005.
│
├── app/                    ← Python FastAPI backend (legacy single-package layout). uvicorn imports from here.
├── apps/                   ← Monorepo packages.
│   ├── backend/            ←   FastAPI backend, monorepo-shaped. Builds the Docker image.
│   ├── web/                ←   Next.js dashboard on Cloudflare Workers (@opennextjs/cloudflare).
│   ├── sdk-ts/             ←   @unsearch/sdk — TypeScript SDK.
│   ├── sdk-py/             ←   unsearch — Python SDK (sync + async). See ADR-0007.
│   └── sdk-llamaindex/     ←   @unsearch/llamaindex — LlamaIndex retriever.
│
├── workers/                ← Cloudflare Workers edge router (Hono) + Durable Objects + D1 schema.
│
├── docs/                   ← All long-form docs.
│   ├── README.md           ←   This directory's index.
│   ├── architecture.md     ←   Current architecture overview.
│   ├── what-is-what.md     ←   ← you are here.
│   ├── adr/                ←   Architecture Decision Records.
│   ├── feature-matrix.md   ←   Honest ✅ / 🔶 / 📋 status per feature. Source of truth for marketing claims.
│   ├── roadmap.md          ←   ICP-ordered priorities. P0 → P4.
│   ├── strategy/           ←   ICP, GTM, pricing, positioning, user journey.
│   ├── operations/         ←   Runbooks. Read before on-call.
│   ├── deployment/         ←   Per-target deploy guides (Cloudflare, Railway, DigitalOcean).
│   ├── configuration/      ←   Env vars + Stripe webhook setup.
│   ├── migration/          ←   Migration guide from Tavily (compatibility surface — see ADR-0003).
│   ├── citation-envelope.md ←   Signed envelope schema + signing. See ADR-0011.
│   ├── API_REFERENCE.md    ←   Full endpoint catalog. Live OpenAPI at /docs.
│   ├── API_EXAMPLES.md     ←   Worked examples per endpoint.
│   ├── ai-pipeline.md      ←   Models, embeddings, reranking. See ADR-0004.
│   ├── cloudflare-architecture.md ← Edge / Containers / D1 / Vectorize wiring detail. See ADR-0001.
│   ├── BILLING_SETUP.md    ←   Stripe products + prices + portal config.
│   ├── SECRETS_MANAGEMENT.md ← How we handle env secrets in self-host and prod.
│   ├── introduction.mdx    ←   Public docs site entry (Mintlify).
│   └── quickstart.md       ←   Self-host quickstart.
│
├── alembic/                ← Postgres migrations (origin DB).
├── searxng/                ← SearXNG meta-search engine config. See ADR-0002.
├── monitoring/             ← Prometheus + Grafana provisioning. Dashboards in grafana/dashboards/.
├── nginx/                  ← Reverse-proxy config for self-host TLS.
├── scripts/                ← Setup + ops scripts (manage.sh, setup-stripe.sh, smoke tests).
├── tests/                  ← Backend test suite (unit + integration + performance).
│
├── docker-compose.yml             ← Self-host: full stack (API + SearXNG + Postgres + Redis + Celery).
├── docker-compose.quickstart.yml  ← Self-host: minimal stack (API + SearXNG only).
├── docker-compose.prod.yml        ← Self-host: production overrides.
├── Dockerfile                     ← FastAPI Container image (self-host).
├── Dockerfile.cloudflare          ← FastAPI Container image (Cloudflare Containers).
│
├── .env.example            ← Copy to .env. Required: CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN.
└── requirements.txt        ← Backend Python deps. apps/sdk-py has its own pyproject.toml.
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
                       │   + Durable Objects (RateLimiter,│
                       │     TopicMonitor, ResearchAgent, │
                       │     SessionManager)              │
                       │   + Queues consumer              │
                       └──────────────────┬──────────────┘
                                          │ service binding
                                          ▼
                       ┌─────────────────────────────────┐
        Container      │   app/  +  apps/backend/        │  FastAPI on CF Containers
                       │   (Python 3.11, 93 endpoints)   │
                       └──────────────────┬──────────────┘
                                          │
                       ┌──────────────────┴───────────────────┐
                       ▼                                      ▼
                ┌──────────────┐                       ┌──────────────┐
        State   │  Cloudflare  │              Origin   │  Postgres    │
                │  D1 / KV /   │                       │  + Redis     │
                │  R2 / Vec    │                       │  + SearXNG   │
                └──────────────┘                       └──────────────┘
```

## Glossary

Terms that show up in code and docs without being defined.

| Term | What it means here |
|------|--------------------|
| **Edge worker** | The Cloudflare Workers script in `workers/`. Fronts every request. |
| **Container** | The Cloudflare Containers FastAPI deployment. Same code as `app/`, packaged via `Dockerfile.cloudflare`. |
| **DO** | Durable Object. Cloudflare's per-instance stateful actor. We have four — see `workers/src/durable-objects/`. |
| **KV** | Cloudflare's eventually-consistent key/value store. Used for hot caches (auth, ratelimit, search). |
| **D1** | Cloudflare's edge SQL database (SQLite dialect). Primary store for users, plans, API keys. |
| **R2** | Cloudflare's object storage (S3-compatible). Stores scraped HTML and PDFs. |
| **Vectorize** | Cloudflare's vector database. Stores `bge-m3` embeddings, 1024 dims. |
| **Queues** | Cloudflare's managed message queue. Used for monitor-fire fan-out and async research steps. |
| **Service binding** | A Workers-to-Workers (or Worker-to-Container) call that skips the public internet. Worker → Container in our case. |
| **Tier (model_tier)** | The four Workers AI tiers: `fast`, `balanced`, `reasoning`, `production`. See ADR-0004. |
| **Drop-in (Tavily-compatible)** | Endpoints under `/api/v1/agent/*` that mirror Tavily's request/response shape 1:1. See ADR-0003. |
| **Namespace (in `/api/v1/rag/*`)** | A logical partition inside Vectorize. Each customer's RAG corpus lives in their own namespace. |
| **`uns_` API key** | Customer-facing API key. Header: `X-API-Key: uns_...`. |
| **🔶 in beta** | Feature exists in code but is being hardened. See ADR-0008. |
| **🚀 differentiator** | Feature that no closed-source competitor has. Used in `docs/feature-matrix.md`. |
| **Persona A / B / C** | The three ICPs. A = indie dev (Maya). B = Seed/A CTO (Priya). C = enterprise buyer (David). Defined in [`strategy/icp.md`](./strategy/icp.md). |

## "Where does that live?" cheat sheet

| You want to… | Open this |
|--------------|-----------|
| Read an endpoint's contract | [`API_REFERENCE.md`](./API_REFERENCE.md) or `http://localhost:8000/docs` |
| See an endpoint's worked example | [`API_EXAMPLES.md`](./API_EXAMPLES.md) |
| Change request validation | `app/models/requests.py` |
| Change a route handler at the edge | `workers/src/routes/*.ts` |
| Change a route handler in the Container | `app/api/v1/*.py` |
| Add a Durable Object | `workers/src/durable-objects/` + binding in `workers/wrangler.toml` |
| Add a new Cloudflare resource (KV, R2, etc.) | `workers/wrangler.toml` + a Python REST client in `app/services/core/` |
| Tweak Workers AI model selection | `app/services/ai/` (Container) + ADR-0004 |
| Touch the SearXNG engine config | `searxng/settings.yml` |
| Touch DB schema (edge) | `workers/schema.sql` (D1) |
| Touch DB schema (origin) | `alembic/versions/*.py` then `alembic upgrade head` |
| Update the dashboard | `apps/web/app/` |
| Update the public SDK contracts | All three of: `apps/sdk-ts/src/index.ts`, `apps/sdk-py/src/unsearch/client.py`, `apps/sdk-llamaindex/src/index.ts` |
| Add a Stripe product | `scripts/setup-stripe.sh` then run it |
| Add a Stripe webhook | [`configuration/stripe-webhook.md`](./configuration/stripe-webhook.md) |
| Wire a new env var | `.env.example` (root) + `docs/configuration/env-variables.md` + the consuming code |
| Trigger a deploy | [`deployment/quick-reference.md`](./deployment/quick-reference.md) |
| Investigate a prod incident | [`operations/RUNBOOKS.md`](./operations/RUNBOOKS.md) |
| Add a non-obvious architectural decision | [`adr/README.md`](./adr/README.md) |

## Two backend layouts — why?

`app/` and `apps/backend/` contain the same code. This isn't a bug; it's an in-flight migration. See [ADR-0006](./adr/0006-monorepo-with-apps-and-workers.md) for the explanation. Until they're collapsed:

- **`app/`** is what `uvicorn app.main:app` imports. Production currently runs from here.
- **`apps/backend/`** is what `Dockerfile.cloudflare` packages. Container deploys use this path.
- **Don't pick favorites.** If you change one, check both. A future PR will collapse them.

## Naming conventions

| Pattern | Where | Example |
|---------|-------|---------|
| `snake_case` | Python, JSON request/response fields | `model_tier`, `cache_hit` |
| `camelCase` | TypeScript SDK methods, internal | `neuralSearch`, `tavilySearch` |
| `kebab-case` | URL paths, npm packages, docker images | `/api/v1/agent/research`, `@unsearch/sdk` |
| `PascalCase` | TypeScript classes, Python classes | `UnSearch`, `AsyncUnSearch`, `RateLimiter` |
| `SCREAMING_SNAKE` | Env vars | `CLOUDFLARE_API_TOKEN` |

When the same field crosses a language boundary (e.g., a Python TypedDict that mirrors a TS interface), we always pick **snake_case for the wire format** and let each language convert as idiomatic.

## How to read a PR

When a PR lands, the order of relevant files is usually:

1. `app/api/v1/*.py` or `workers/src/routes/*.ts` — the route handler
2. `app/services/*` — supporting service code
3. `apps/sdk-*/` — if the wire format changed, the SDKs follow in lockstep
4. `docs/API_REFERENCE.md` + `docs/feature-matrix.md` — if the docs are out of date, request changes
5. `CHANGELOG.md` — `[Unreleased]` section should reflect the change
6. `docs/adr/` — only for cross-cutting decisions, not feature work

If a PR adds a new architectural decision and *doesn't* include an ADR, that's a review comment ("please write an ADR-NNNN for this").
