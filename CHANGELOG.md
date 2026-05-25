# Changelog

## [Unreleased] — Cloudflare-native release

Big-bang rewrite from a self-hosted FastAPI/Postgres/Redis/Celery stack
to a fully Cloudflare-native architecture. See `docs/cloudflare-architecture.md`
and `workers/README.md` for the full picture.

### New

- **Edge Worker** (`workers/`) — Hono router on Cloudflare Workers
  fronts every request. Endpoints that don't need Python execute at
  the edge using Workers AI + Vectorize + D1 + KV bindings; everything
  else proxies to the FastAPI Container via a service binding.
- **Cloudflare Containers** (`Dockerfile.cloudflare`,
  `workers/containers.toml`) — FastAPI origin runs on CF Containers
  with auto-scaling 0–10, /health probes, single uvicorn worker per
  replica.
- **D1 schema** (`workers/schema.sql`) — consolidated from the 5
  alembic revisions, SQLite dialect, plans seed data, and partial
  unique indexes for nullable Stripe IDs.
- **D1 + KV + Queues clients for Python** — `app/services/core/d1_client.py`,
  `app/services/core/cache_kv.py`, `app/services/core/queue_producer.py`.
  The Container talks to CF resources via REST since direct bindings
  aren't available from inside Containers yet.
- **Durable Objects** — `RateLimiter` (sliding window per key),
  `TopicMonitor` (alarms for periodic queries + webhook fan-out),
  `ResearchAgent` (multi-step LLM-driven research), `SessionManager`
  (chat/pagination cursors).
- **CF Queues consumer** (`workers/src/queue-consumer.ts`) —
  replaces Celery for async tasks: scrape jobs, embed batches,
  monitor checks, retried webhook delivery.
- **Scheduled handler** — daily D1 backup to R2, daily usage rollover,
  6-hourly topic monitor refresh.
- **Next.js 15 dashboard** (`apps/web/`) — landing, signup/login, API
  keys, playground, billing, deployed via `@cloudflare/next-on-pages`.
- **TypeScript SDK** (`apps/sdk-ts/` → `@unsearch/sdk`) — typed
  client with SSE streaming helpers for search/RAG and a polling
  helper for the long-running research agent.
- **LlamaIndex retriever** (`apps/sdk-llamaindex/` →
  `@unsearch/llamaindex`) — drop-in `BaseRetriever` backed by UnSearch
  neural or full-text search.
- **Pre-flight provisioning** — `scripts/cf-provision.sh` idempotently
  creates D1, KV, R2, Vectorize, Queues, Pages projects, Container
  app. Writes IDs to `workers/.cf-resources.env`.
- **Postgres → D1 migration** — `scripts/migrate_pg_to_d1.py` walks
  every table in dependency order, coerces JSONB and booleans for
  SQLite, batches via D1 multi-statement endpoint.
- **Sentry middleware** for the Worker (`workers/src/middleware/sentry.ts`).
- **Production smoke test** (`tests/e2e/test_prod_smoke.py`) — runs
  end-to-end against `api.unsearch.dev` after every deploy via
  `.github/workflows/deploy-cf.yml`.

### Documentation

- `workers/README.md` — Worker package overview.
- `workers/SECRETS.md` — full secret inventory + provisioning sources.
- `workers/OBSERVABILITY.md` — Workers Analytics, Sentry, Logpush,
  PostHog, alert rules.
- `apps/web/README.md` and per-SDK READMEs.

### Deferred to follow-up commits (tracked in plan)

- Full SQLAlchemy → D1 rewrite of `app/services/core/database.py`
  (1065 LOC). Primitives are in place; per-route migration is
  incremental.
- Celery → CF Queues call-site swap in `app/workers/tasks.py` (236 LOC).
- `/team` and `/settings` dashboard routes.
- Better Auth integration for OAuth on the dashboard.
- LiveDocs site (Mintlify already configured at `docs/mint.json`).

## [2.0.0] — 2026-04 — Initial open-source release

Original FastAPI/SearXNG/Postgres/Redis/Celery stack.
