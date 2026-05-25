# UnSearch Edge Worker

Cloudflare Workers edge router for UnSearch. Built with Hono.

## Quick start

```bash
pnpm install
pnpm wrangler login

# One-time: provision CF resources (D1, KV, R2, Vectorize, Queues, Pages)
bash ../scripts/cf-provision.sh

# Update wrangler.toml with the IDs printed by the provision script.

# Apply D1 schema to remote
pnpm db:migrate:remote

# Set secrets (see SECRETS.md for the full list)
pnpm wrangler secret put SECRET_KEY --env production
pnpm wrangler secret put STRIPE_SECRET_KEY --env production
# ... etc

# Local dev
pnpm dev

# Deploy
pnpm deploy:production
```

## Architecture

```
src/
├── index.ts              # Hono app, route mounting, error middleware
├── env.ts                # Env type with all CF bindings + secrets
├── middleware/
│   ├── auth.ts           # JWT verify + API key lookup (KV → D1 fallback)
│   ├── rate-limit.ts     # Sliding window via RateLimiter Durable Object
│   ├── cors.ts
│   └── logging.ts        # Workers Analytics Engine + structured logs
├── routes/
│   ├── auth.ts           # /api/v1/auth/*    signup, login, OAuth
│   ├── search.ts         # /api/v1/search/*  + SSE streaming
│   ├── neural.ts         # /api/v1/neural/*  Workers AI direct
│   ├── knowledge.ts      # /api/v1/knowledge/*
│   ├── rag.ts            # /api/v1/rag/*     Vectorize direct
│   ├── monitor.ts        # /api/v1/monitor/* Topic Monitor DO
│   ├── verify.ts         # /api/v1/verify/*  fact check
│   ├── agent.ts          # /api/v1/agent/*   Tavily-compat + research DO
│   ├── billing.ts        # /api/v1/billing/* Stripe webhook + portal
│   └── proxy.ts          # Forward to Container for heavy ops
├── durable-objects/
│   ├── research-agent.ts
│   ├── topic-monitor.ts
│   ├── session-manager.ts
│   └── rate-limiter.ts
└── lib/
    ├── d1.ts             # Typed query helpers
    ├── kv-cache.ts       # get/set with TTL + stale-while-revalidate
    ├── vectorize.ts      # search + upsert helpers
    ├── workers-ai.ts     # Model routing (gpt-oss-120b / qwq-32b / llama-3.3)
    └── stripe.ts         # Webhook signature verify
```

## Routing pattern

Endpoints that can run entirely on the edge (neural search, knowledge graph,
simple verify, cached search) execute in the Worker directly using Workers AI
+ Vectorize + D1 + KV bindings.

Endpoints requiring the Python FastAPI codebase (deep crawling, Playwright
scraping, complex RAG indexing, SearXNG aggregation) forward to the Container
via the `CONTAINER` service binding:

```ts
const resp = await c.env.CONTAINER.fetch(c.req.raw)
return resp
```

## Domains

| Env | Worker | Frontend | Docs |
|---|---|---|---|
| production | `api.unsearch.dev` | `unsearch.dev` | `docs.unsearch.dev` |
| staging | `unsearch-api-staging.workers.dev` | `staging.unsearch.dev` | — |

See `SECRETS.md` for the full secret inventory.
