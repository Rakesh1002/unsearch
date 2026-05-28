# ADR-0001: Cloudflare-native edge architecture

- Status: Accepted
- Date: 2026-04-15
- Deciders: @Rakesh1002

## Context

UnSearch v1 ran the classic "managed VPS + Postgres + Redis + Celery" stack. Three problems were structural:

1. **Latency.** Search traffic is globally distributed; an origin-only deploy meant ~200–400ms p95 from outside the origin region.
2. **Cost at the high-traffic ICP.** Persona A — indie devs hitting 100K+ searches/mo — would burn through a $20/mo VPS in cold-start storms and trigger always-on Celery workers we paid for at idle.
3. **Vendor positioning.** Tavily / Exa / Brave all run their own infra. Our pitch ("10× cheaper, Apache 2.0, self-hostable") needs a unit-economics story that holds at the price point. Cloudflare's free-tier-then-cheap pricing curve maps onto our pricing curve.

## Decision

Adopt **Cloudflare-native edge** as the default deploy target:

- **Cloudflare Workers (Hono router)** front every request at `workers/src/index.ts`. Endpoints that don't need Python (KV cache hits, simple search proxying, auth checks, rate limiting) terminate at the edge.
- **Cloudflare Containers** host the FastAPI origin (`Dockerfile.cloudflare`, `workers/containers.toml`) with auto-scale 0–10. Workloads that need Python's ecosystem (heavy scraping, complex orchestration, alembic migrations against the long-tail of features) proxy from the worker via a service binding.
- **D1** is the primary edge database (`workers/schema.sql`). Postgres remains as the local-dev origin DB and as an escape hatch for ops that need it.
- **KV** for hot-path caches (auth, rate-limit counters, search cache hits).
- **R2** for object storage (scraped HTML snapshots, large extracted artifacts).
- **Vectorize** for the RAG corpus — `bge-m3` 1024-dim embeddings.
- **Queues** for async work (research-agent fan-out, monitor checks, batch crawls).
- **Durable Objects** for stateful coordination — `RateLimiter` (sliding window), `TopicMonitor` (alarms + webhook fan-out), `ResearchAgent` (multi-step LLM-driven research), `SessionManager` (chat/pagination cursors).
- **Workers AI** for LLM inference and embeddings — see [ADR-0004](./0004-workers-ai-tiered-model-selection.md).

The split between "lives at the edge" and "lives in the Container" is documented in [`docs/cloudflare-architecture.md`](../cloudflare-architecture.md).

## Consequences

- **Pro:** Single-vendor edge story. The deploy is `wrangler deploy` for the edge + `wrangler deploy --config workers/containers.toml` for the Container. No Kubernetes, no managed Postgres bill for v2.
- **Pro:** Global p95 latency drops to <100ms for KV-cache hits, <200ms for Worker AI calls.
- **Pro:** Free tier on the platform side maps neatly onto our 5,000-req/mo free tier on the product side.
- **Con:** Self-host story is more complex than "docker compose up" — we keep `docker-compose.yml` working as the no-Cloudflare path (see [ADR-0005](./0005-apache-2-license-self-hostable-from-day-one.md)), but it deliberately leaves the edge-resident features (Vectorize, Workers AI) as optional.
- **Con:** Cloudflare Containers is still maturing — direct bindings from inside Containers aren't available, so the FastAPI Container talks to D1 / KV / Queues over REST (see `app/services/core/d1_client.py`, `cache_kv.py`, `queue_producer.py`).
- **Con:** Locks us into Cloudflare's specific quirks (Vectorize index size limits, Durable Object eviction semantics, Workers' 50ms CPU-time budget).

## Alternatives considered

- **AWS Lambda + DynamoDB + Bedrock.** Rejected — multi-vendor cost story is worse, Bedrock model selection lags Workers AI, latency at the edge requires CloudFront in front of Lambda@Edge (extra hop).
- **Vercel + Vercel KV + OpenAI.** Rejected — pricing per-invocation is opaque, vendor lock to a single LLM (OpenAI) breaks the "model selection" pitch, no equivalent of Vectorize as a first-party offering.
- **Stay on VPS + Postgres.** Rejected — the latency and unit-economics problems were the explicit reason to move.
- **Hybrid: VPS origin + Cloudflare CDN-only.** Considered. Rejected because it leaves the latency problem unsolved for any endpoint that hits the origin (everything except static asset serving).
