# ADR-0002: SearXNG as the meta-search aggregator

- Status: Accepted
- Date: 2026-04-15
- Deciders: @Rakesh1002

## Context

UnSearch needs a web-search backbone. The realistic options for "give me ranked results from the public web" all have trade-offs:

- **Direct provider APIs (Google CSE, Bing Web Search, Brave Search API).** Per-query costs ($3–$5 per 1k), opaque rate limits, and single-engine results. Vendor lock-in directly contradicts our positioning.
- **Build a crawler.** Multi-month project. Not differentiating. Politically and legally fraught (robots.txt, anti-bot signals, geo-blocking).
- **Buy from Tavily / Exa / Brave.** Defeats the whole product premise.
- **SearXNG** — open-source, self-hostable, aggregates 70+ engines, normalizes results, respects robots.txt.

## Decision

Use **SearXNG as the meta-search aggregation layer** that sits behind the search API.

- Self-hosted SearXNG container (`searxng/settings.yml`, `docker-compose.yml`)
- The FastAPI backend posts queries to `SEARXNG_URL` (env-driven)
- We aggregate, dedupe, and re-rank the SearXNG response before returning it to the caller
- Engine selection is exposed via the `engines` parameter on `/api/v1/search`

This decision is what enables the "Multi-Engine Aggregation 🚀" row in [`docs/feature-matrix.md`](../feature-matrix.md). It's our most defensible technical wedge against single-provider competitors.

## Consequences

- **Pro:** Zero per-query cost for the search itself — we pay only for the SearXNG host (and for the AI inference layer on top).
- **Pro:** Engine plurality is a feature: callers can ask for `["google", "duckduckgo", "brave"]` and get a deduped union.
- **Pro:** Self-host story is honest — the same SearXNG that powers `api.unsearch.dev` runs in the user's `docker compose up`.
- **Con:** SearXNG is community-maintained. Engines break when upstream providers change their HTML. We mitigate with multi-engine fallback in `app/services/search/`, but the failure mode is real.
- **Con:** No SLA on SearXNG itself. We accept this and design for graceful degradation (route around dead engines, expose engine health via `/api/v1/agent/health`).
- **Con:** Some providers (notably Google) actively rate-limit SearXNG IPs. We work around with proxy rotation in production; the open-source self-host docs note this honestly.

## Alternatives considered

- **Direct Bing Web Search API.** Cheapest per-query of the closed APIs, but $3 per 1k still murders our $49/100k pricing. Locks us into one engine.
- **Brave Search API.** Decent but expensive at our volume tier, and Brave is itself a competitor at the SDK layer.
- **Apache Solr / Elasticsearch + open crawl dataset (CommonCrawl).** Considered. Rejected — index freshness is 30–60 days behind reality, which is fatal for news/AI-research queries.
- **Build a thin Google CSE wrapper.** Rejected — CSE is artificially restricted (10 results, no recency control, expensive at scale).
