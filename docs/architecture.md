# Architecture

> **Scope:** This document describes the v2.0 Cloudflare-native architecture currently running in production. For the per-decision rationale behind each piece, see the [ADRs](./adr/README.md). For the directory-by-directory component map, see [what-is-what.md](./what-is-what.md). For the historic v1 (FastAPI-only) architecture, see git history before [`376f886`](https://github.com/Rakesh1002/unsearch/commit/376f886).

## One-paragraph summary

UnSearch is verifiable web retrieval for AI agents. Requests land on a **Cloudflare Workers** edge router (`workers/`), which either answers from the edge (KV cache hits, simple proxying, auth, rate-limit, MCP transport) or proxies to a **FastAPI Container** (`backend/`) for anything that needs Python's ecosystem (heavy scraping, RAG orchestration, alembic migrations, complex Stripe flows, claim verification). State lives in **D1** (relational), **KV** (hot caches), **R2** (citation snapshots + objects), and **Vectorize** (embeddings); async work runs on **Cloudflare Queues**; multi-step stateful workflows run inside **Durable Objects**. LLM inference, embeddings, and the `verify_claim` grader run on **Cloudflare Workers AI** (see [ADR-0004](./adr/0004-workers-ai-tiered-model-selection.md)). Web search aggregation is delegated to a self-hosted **SearXNG** instance (see [ADR-0002](./adr/0002-searxng-as-meta-search-aggregator.md)). A **Next.js dashboard** (`apps/web/`) deployed via `@opennextjs/cloudflare` lives on the same Workers platform.

---

## Request-flow diagram

```
                                Caller
                                  │
                                  ▼
                    ┌─────────────────────────────────┐
                    │  Cloudflare edge (300+ PoPs)    │
                    │  workers/src/index.ts (Hono)    │
                    └──────┬──────────────────────────┘
                           │
            ┌──────────────┼──────────────┬──────────────────┐
            ▼              ▼              ▼                  ▼
       ┌────────┐    ┌──────────┐   ┌──────────┐      ┌──────────────┐
       │  KV    │    │ Workers  │   │ Durable  │      │ Service      │
       │ cache  │    │ AI       │   │ Objects  │      │ binding →    │
       │ hit    │    │ (LLM)    │   │ (Rate-   │      │ FastAPI      │
       │  →     │    │   ↓      │   │ Limiter, │      │ Container    │
       │ return │    │ Vector-  │   │ Topic-   │      │ (backend/    │
       └────────┘    │ ize / D1 │   │ Monitor, │      │  app/*)      │
                     └──────────┘   │ Research-│      └──────┬───────┘
                                    │ Agent,   │             │
                                    │ Session) │             ▼
                                    └──────────┘    ┌─────────────────┐
                                                    │ SearXNG (70+    │
                                                    │ engines)        │
                                                    │ Postgres origin │
                                                    │ Redis (legacy)  │
                                                    │ Stripe webhooks │
                                                    └─────────────────┘
                                                              ▲
                                                              │
                                                    Async via Queues
                                                    (research fan-out,
                                                     monitor checks,
                                                     batch crawls)
```

ASCII diagrams elide a lot. The intended invariants:

1. **Edge handles what it can.** Auth checks, rate limiting, KV-cache lookups, simple search proxying, and any endpoint with a pure-TypeScript implementation terminate at the worker. No Python round-trip.
2. **Container handles what it must.** Heavy scraping, complex orchestrations (research pipelines, big crawls), Stripe webhook signing, alembic migrations against the long-tail of Postgres-backed features. Everything called from the worker via a [service binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/).
3. **Durable Objects do stateful coordination, never request handling.** A request handler may *create* a DO instance; the DO itself runs to completion in the background and emits events via Queues / webhooks.
4. **Queues are the boundary for "this might take seconds."** Anything that could blow the 50ms Worker CPU budget or the Container's request-timeout gets queued.

---

## Components

### Edge worker — `workers/`

- **Stack:** TypeScript, Hono router on Cloudflare Workers.
- **Files of interest:** `workers/src/index.ts` (router), `workers/src/routes/*.ts` (per-feature handlers), `workers/src/durable-objects/*.ts`, `workers/src/queue-consumer.ts`, `workers/src/scheduled.ts`, `workers/src/middleware/*.ts`, `workers/wrangler.toml` (bindings), `workers/schema.sql` (D1 schema), `workers/containers.toml` (Container config).
- **Bindings:** `DB` (D1), `CACHE` (KV — auth/ratelimit/search cache), `BUCKET` (R2), `VECTORS` (Vectorize), `AI` (Workers AI), `QUEUE` (Cloudflare Queues), plus DO namespaces `RATE_LIMITER`, `TOPIC_MONITOR`, `RESEARCH_AGENT`, `SESSION_MANAGER`, and a service binding `BACKEND` → FastAPI Container.
- **Per-route file map:** `agent.ts` (Tavily-compat), `auth.ts`, `billing.ts`, `knowledge.ts`, `monitor.ts`, `neural.ts`, `proxy.ts` (catch-all → Container), `rag.ts`, `search.ts`, `verify.ts`.

### Backend Container — `backend/`

- **Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy + Alembic (Postgres), Celery (Redis), httpx for outbound calls. 93 endpoints across 14 routers (counted via `backend/app/api/v1/*.py` and `backend/app/api/v2/*.py`).
- **Single source of truth.** `backend/` is the only backend layout — the prior duplicate `apps/backend/` was removed in PR #7, and the root-level scattering of `app/` + `alembic/` + `tests/` was consolidated into `backend/` in the 2026-05-28 reorg. Python module name stays `app/`; uvicorn invocation stays `uvicorn app.main:app` (now run from `backend/` cwd).
- **Service layout:** `backend/app/services/core/` (DB, KV, queues, D1 client), `backend/app/services/search/` (SearXNG orchestration + dedup + rerank), `backend/app/services/scraping/` (static + JS + PDF), `backend/app/services/extraction/` (entities, tables, attributes), `backend/app/services/crawling/`, `backend/app/services/rag/`, `backend/app/services/ai/` (Workers AI client + model-tier selector + `verify_claim` grader).
- **Container image:** `backend/Dockerfile.cloudflare` (CF Containers GA per ADR-0010) and `backend/Dockerfile` (self-host). Build context is the repo root; COPY paths are prefixed with `backend/`.
- **Inbound interface:** invoked by the edge worker via service binding for endpoints that aren't pure-TypeScript. The Container does *not* face the public internet directly in production.

### Web dashboard — `apps/web/`

- **Stack:** Next.js 15 (App Router) on Cloudflare Workers via `@opennextjs/cloudflare`. Tailwind for styling. Routes under `app/(auth)/` (login, signup), `app/(dashboard)/` (dashboard, api-keys, playground, billing).
- **Deploy:** Cloudflare Workers via `pnpm cf:build && pnpm cf:deploy` (config in `apps/web/wrangler.toml`). The migration from Cloudflare Pages to native Workers landed in commit [`376f886`](https://github.com/Rakesh1002/unsearch/commit/376f886) and is documented in `CHANGELOG.md`.
- **API client:** uses `@unsearch/sdk` directly — no separate fetch layer.

### SDKs — `apps/sdk-*/`

| Package | Languages | Purpose |
|---------|-----------|---------|
| [`@unsearch/sdk`](../apps/sdk-ts/) | TypeScript / Node / Bun / Deno / Workers / Edge | Primary public SDK, mirrors REST surface 1:1 |
| [`unsearch`](../apps/sdk-py/) | Python 3.9–3.13 (sync + async) | See [ADR-0007](./adr/0007-python-sdk-sync-and-async.md) |
| [`@unsearch/llamaindex`](../apps/sdk-llamaindex/) | TypeScript | LlamaIndex `BaseRetriever` implementation backed by UnSearch |

All three are kept structurally parallel (same method names, same request/response shapes, same SSE-streaming pattern) so cross-language onboarding is mechanical.

### SearXNG — `infra/searxng/`

The 70+-engine meta-search aggregator. Self-hosted as a Docker container (`docker-compose.yml`) in production and in self-host deployments. The FastAPI backend in `backend/app/services/search/` is the only client. Configuration in `infra/searxng/settings.yml`. See [ADR-0002](./adr/0002-searxng-as-meta-search-aggregator.md).

### Origin Postgres + Redis

Postgres is the Container's origin database for everything that hasn't moved to D1 yet — primarily the legacy Stripe/billing state and the Celery task results table. Redis backs Celery's broker and Celery's result backend. Both run as containers in self-host (`docker-compose.yml`) and as managed services (Neon Postgres, Upstash Redis) in production.

### Monitoring — `infra/monitoring/`

Prometheus + Grafana, provisioned via `infra/monitoring/docker-compose.monitoring.yml`. Dashboards in `infra/monitoring/grafana/dashboards/unsearch-overview.json`. The Container exports Prometheus metrics at `/metrics`; the worker emits the same via Workers Analytics Engine. Detailed observability runbook: [`workers/OBSERVABILITY.md`](../workers/OBSERVABILITY.md).

---

## Data model — what lives where

| State | Store | Why |
|-------|-------|-----|
| Users, accounts, plans | D1 (`workers/schema.sql`) — primary; Postgres mirror for the long-tail of Container-only features | Most reads happen at the edge; users + plans are the hot path |
| API keys | D1 | Auth check is on every request; must be edge-fast |
| Stripe subscriptions, invoices | Postgres (Container) — D1 stores only the `customer_id` / `subscription_id` projection | Stripe webhooks land at the Container; full state is too rich for D1 |
| Rate-limit counters | KV (TTL) + DO `RateLimiter` for sliding-window | KV for absolute-limit checks; DO for per-key sliding window |
| Search result cache | KV (60s default, configurable per-plan) | Reads are cache-hit-or-recompute; per-request size fits KV's value-size limit |
| Embeddings + metadata | Vectorize (`@cf/baai/bge-m3`, 1024d) | First-party vector store with edge-bindings |
| Scraped HTML + PDFs | R2 | Variable size, long retention, infrequent reads |
| Async job state | DO `ResearchAgent`, `TopicMonitor` (alarms), Queue messages | Each long-running operation owns its own DO; queue for dispatch |
| Chat / pagination cursors | DO `SessionManager` | Per-user state with TTL eviction |

The Container reaches D1 / KV / Vectorize / Queues over **REST**, not via direct bindings, because Cloudflare Containers do not yet expose direct bindings from inside the Container runtime. The REST clients live in `backend/app/services/core/d1_client.py`, `cache_kv.py`, and `queue_producer.py`. The worker uses direct bindings — no REST hop.

---

## Request lifecycle examples

### Cache hit on `POST /api/v1/search`

1. Worker `index.ts` matches the route, calls `routes/search.ts`.
2. KV lookup with key `search:sha256(query+engines+filters)`.
3. **Hit** → return the cached `SearchResponse` with `cache_hit: true`. ~5ms p95. Worker CPU budget unused.

### Cache miss on `POST /api/v1/search`

1. Worker → SearXNG via the Container service binding.
2. Container `backend/app/api/v1/search.py` orchestrates `backend/app/services/search/`: parallel engine queries, dedup, optional rerank via Workers AI (worker-resident — Container calls back to the worker for AI inference).
3. Optional scraping if `scrape_content: true` (`backend/app/services/scraping/`).
4. Container writes the response back to KV via REST (`cache_kv.py`).
5. Container returns response to the worker, worker returns to caller.

### `POST /api/v1/agent/research`

1. Worker `routes/agent.ts` validates auth + plan.
2. Worker spawns / fetches a `ResearchAgent` Durable Object instance keyed by `session_id`.
3. DO returns `{session_id, status: "running"}` immediately to the caller.
4. DO loops: query expansion → SearXNG search → scrape candidates → Workers AI synthesis → repeat until depth limit or convergence. Each step writes its results back to the DO's internal SQLite.
5. Caller polls `GET /api/v1/agent/research/{id}` → worker reads DO state → returns. When `status: "completed"`, the `finalAnswer` field is populated.

### Topic-monitor webhook fire

1. Caller creates monitor via `POST /api/v1/monitor/topics` → worker spawns a `TopicMonitor` DO with `interval_minutes` and `webhook_url`.
2. DO sets an alarm. On wake, runs the monitored search, computes a delta against the last result, and **enqueues** the webhook delivery via Cloudflare Queues.
3. The `queue-consumer.ts` worker reads the queue, POSTs to the webhook with retry + exponential backoff, and writes the delivery receipt back to the DO.

---

## Performance targets

| Metric | Target | Current |
|--------|--------|---------|
| API endpoints | 93 across 14 routers | ✅ |
| p95 search latency (KV cache hit) | <100ms | ~80ms |
| p95 search latency (miss) | <2s | 1–3s |
| AI answer generation | tier-dependent | `fast`: 1–3s, `balanced`: 3–8s, `reasoning`: 8–20s |
| Scraping throughput | 10 URLs/s per Container replica | ✅ |
| Container cold start | <2s | ~1.5s |
| Test coverage | >80% | ~40% (tech debt) |
| Uptime | 99.9% | tracked via [`workers/OBSERVABILITY.md`](../workers/OBSERVABILITY.md) |

---

## Tech-debt callouts

From [docs/roadmap.md § Technical Debt](./roadmap.md):

| Issue | Location | Impact | Plan |
|-------|----------|--------|------|
| In-memory vector store | `backend/app/services/rag/rag.py` | Doesn't scale beyond a small corpus | Migrate fully to Vectorize (most paths already use it; a few are still legacy) |
| Puppeteer stub | `backend/app/services/scraping/puppeteer_client.py` | No fallback when CF Browser Rendering unavailable | Either wire CF Browser Rendering or drop the stub |
| Sync DB operations | Multiple Container files | Blocks Uvicorn worker threads under load | Move to async SQLAlchemy where it matters |

---

## What this doc doesn't cover

- **Per-endpoint contracts.** See [`API_REFERENCE.md`](./API_REFERENCE.md) and the live OpenAPI at `/docs`.
- **Per-decision rationale.** See [`adr/`](./adr/README.md).
- **Honest feature status.** See [`feature-matrix.md`](./feature-matrix.md) and [ADR-0008](./adr/0008-honest-feature-status-policy.md).
- **Deploy step-by-step.** See [`deployment/`](./deployment/) and [`quickstart.md`](./quickstart.md).
- **On-call playbook.** See [`operations/RUNBOOKS.md`](./operations/RUNBOOKS.md).
- **Where does that file live?** See [`what-is-what.md`](./what-is-what.md).
