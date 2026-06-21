# UnSearch — Overview

> **One-liner:** Verifiable web retrieval for AI agents — every search/extract result is signed, hashed, snapshotted, and replayable months later, delivered as an API + MCP server for teams building regulated-AI in legal, medical, finance, and compliance.

The single cold-start doc. Read this and you know what UnSearch is, how to run it, and where everything lives.

## What & why
- **Problem:** AI agents make claims tied to web sources that are wrong, dead, paraphrased, fabricated, or silently changed since retrieval. There is no widely-adopted infrastructure primitive that produces a cryptographically verifiable record of "what the agent saw, at what URL, at what time, and what hash." Regulated teams hand-roll this from 5 vendors (Tavily + Firecrawl + Playwright snapshots + a custom NLI grader + a Postgres provenance table) plus 1-2 FTEs of glue.
- **Who it's for:** Engineering leads at regulated-AI startups (Seed-B, legal/medical/finance/insurance/research/compliance verticals), AI platform directors at regulated incumbents (banks, hospital systems, insurers, BigLaw, pharma) retrofitting LLM features ahead of EU AI Act enforcement, and citation-integrity research/journalism engineers. Full personas in [strategy/icp.md](./strategy/icp.md).
- **What we're building:** A search/extract/research API and MCP server where every result returns a WACZ-aligned signed citation envelope plus a content-addressable snapshot in your R2 (self-host) or ours (hosted). A `verify_claim` endpoint grades any `{claim, source_url}` pair with span-level evidence. Apache 2.0, MCP-native, self-hostable on Cloudflare Workers + Containers.
- **Stage:** active (pre-deploy of the hosted edge/dashboard; SDKs published; MCP server shipped).
- **Status right now:** Search, neural/semantic search, multi-engine SearXNG aggregation, scraping/extraction, signed citation envelope (HMAC v1), claim verification, per-key audit log, RAG over Vectorize, Stripe billing, and three SDKs (Python, TypeScript, LlamaIndex) plus an npx MCP server are shipped and end-to-end tested. Cloudflare Containers deploy of FastAPI + SearXNG, domain activation for `app.unsearch.dev` / `api.unsearch.dev`, and MCP-registry + HN launch are in flight. Knowledge graph, topic monitoring, source credibility, deep research agent, and predictive search are in beta. See [product/feature-matrix.md](./product/feature-matrix.md) for the honest table.

## How to run it
```bash
# Clone + configure
git clone https://github.com/Rakesh1002/unsearch.git
cd unsearch
cp .env.example .env   # set CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (required for CF features)

# Full self-host stack (no Cloudflare account needed)
docker compose up -d
# Minimal stack (search + verify only):
docker compose -f docker-compose.quickstart.yml up -d

# Or run the Python backend locally
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000   # API docs at http://localhost:8000/docs

# Frontend dashboard (Next.js on Cloudflare Workers)
pnpm --filter @unsearch/web dev

# Edge worker (Hono on CF Workers)
cd apps/workers && pnpm dev

# Tests
cd backend && pytest tests/unit/ -v --cov=app   # backend
pnpm --filter @unsearch/sdk test                # TS SDK
make test                                        # full suite via Makefile

# Try it without signup — MCP free tier (5,000 verified searches/month)
claude mcp add unsearch   # or: npx @unsearch/mcp-server
```
- **Prod URLs:** API `https://api.unsearch.dev` (`/docs`, `/mcp`) · Dashboard `https://app.unsearch.dev` · Docs `https://docs.unsearch.dev` — domain activation in flight.
- **Repo:** https://github.com/Rakesh1002/unsearch
- **Deploy:** `wrangler containers deploy` (FastAPI + SearXNG on CF Containers) then `wrangler deploy` (Hono edge + MCP + dashboard). CI workflows in `.github/workflows/`. Railway / DigitalOcean alternatives in [ops/deployment/](./ops/deployment/).

## Where things are
| Area | Location |
|------|----------|
| Frontend / dashboard | `apps/web/` (Next.js on Cloudflare Workers) |
| Backend / API | `backend/` (FastAPI, Python 3.11+; `backend/app/`) |
| Edge worker / MCP transport | `apps/workers/` (Hono, Durable Objects, D1 schema, containers.toml) |
| SDKs | `apps/sdk-ts/` (`@unsearch/sdk`), `apps/sdk-py/` (`unsearch`), `apps/sdk-llamaindex/`, `apps/mcp-server/` |
| Infra / config | `infra/` (nginx, monitoring, searxng), `docker-compose*.yml` |
| DB migrations | `backend/alembic/` |
| Tests | `backend/tests/` (pytest), per-package tests under `apps/*` |
| Scripts | `scripts/`, `manage.sh`, `Makefile` |

## Top 5 decisions to know
1. Cloudflare-native edge architecture — Workers front FastAPI on CF Containers, with D1/KV/Vectorize/R2/Queues/Durable Objects → [[0001-cloudflare-native-edge-architecture]]
2. WACZ-aligned signed citation envelope as the wedge primitive (HMAC v1 now, public-key later) → [[0011-wacz-aligned-signed-envelope]]
3. Verifiable retrieval as the product surface (reposition from "open-source Tavily alternative") → [[0009-verifiable-retrieval-as-product-surface]]
4. MCP-first distribution — free tier built into the MCP server, no signup → [[0012-mcp-first-distribution]]
5. ICP shift to regulated AI (legal/medical/finance) as the buyer → [[0013-icp-shift-to-regulated-ai]]

## Key links
- **Repo:** https://github.com/Rakesh1002/unsearch · **Issues:** https://github.com/Rakesh1002/unsearch/issues
- **Strategy:** [[thesis]] · **Architecture:** [[architecture]] · **GTM:** [[positioning]]
- **Feature status:** [product/feature-matrix.md](./product/feature-matrix.md) · **API:** [tech/api.md](./tech/api.md) · **ADRs:** [tech/adr/](./tech/adr/README.md)

---
**Owner:** Rakesh Roushan · **Last reviewed:** 2026-06-21 · **Review by:** 2026-09-21
