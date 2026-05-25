---
title: Positioning
description: One-liner, category claim, messaging house, and vocabulary discipline for UnSearch
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

## One-liner

> **The open-source search API for AI agents. Tavily-compatible. 10× cheaper.**

Twelve words. Used verbatim on the homepage hero, GitHub README, and HN launch title. Resist the urge to make it cleverer.

## Category claim

UnSearch is in the **Agent Search Infrastructure** category. Not "search engine" (Google/Brave own that), not "vector database" (Pinecone/Vectorize own that), not "enterprise knowledge search" (Glean owns that). Category matters because it determines which mental bucket buyers compare us against — we want Pinecone/Vectorize as the reference set, not Bing.

## Messaging house

```
                        Roof
   "Open-source search API for AI agents.
    Tavily-compatible. 10× cheaper."

  ┌─────────┬───────────┬───────────┬────────────┐
  │Pillar 1 │ Pillar 2  │ Pillar 3  │ Pillar 4   │
  │Open you │ Drop-in   │ 10×       │ Cloudflare │
  │can trust│ Tavily    │ cheaper   │ -native    │
  └─────────┴───────────┴───────────┴────────────┘
```

### Pillar 1 — "Open source you can trust"
- **Proof point:** [Apache 2.0 LICENSE](https://github.com/Rakesh1002/unsearch/blob/main/LICENSE) on the repo.
- **Receipt:** Public **price-commitment statement** (see [Pricing](./pricing)) — "12 months notice on any price increase to existing paying customers." This is the direct counter to Exa's 2026-03 price hike and Brave's 2026-02 free-tier kill.
- **Anti-vector:** "Tavily was acquired by Nebius in Feb 2026; you can't fork Tavily. You can fork UnSearch."

### Pillar 2 — "Drop-in Tavily replacement"
- **Proof point:** [Migration guide](../migration/from-tavily) — change one base URL, keep your existing `client.search()` calls.
- **Receipt:** Working code diff (3 lines changed) on the migration landing page.

### Pillar 3 — "10× cheaper at the median usage band"
- **Proof point:** Growth tier at $49/mo for 100K searches vs the **competitor median ~$500/mo** (see [Market](./market)).
- **Receipt:** Pricing comparison table on the marketing site, sourced and dated.

### Pillar 4 — "Cloudflare-native"
- **Proof point:** Edge worker fronts every request (`workers/src/index.ts`); D1 for state, KV for cache, Vectorize for embeddings, Durable Objects for sessions.
- **Receipt:** p50 latency number from production (instrumented via Workers Analytics — see [observability docs](../../workers/OBSERVABILITY.md)).
- **Jujitsu against the Cloudflare AI Search threat:** "We run *on* Cloudflare, but you own the code. Cloudflare AI Search is managed; UnSearch is buildable. Use both — we don't compete with the platform, we extend it."

## Anti-positioning

What we are explicitly *not* — naming this is more important than naming what we are.

- **We are not Google.** No consumer search UI, no SERP page, no ad model.
- **We are not Perplexity.** No human-facing answer engine. We're the layer Perplexity's developer customers would call.
- **We are not a vector database.** We use vectors; we don't sell them.
- **We are not a managed scraper.** We surface what's findable on the open web; we don't run targeted scraping campaigns. (See [JTBD](./jtbd) anti-jobs.)
- **We are not Glean.** Glean = inside your company. UnSearch = outside.
- **We are not enterprise-grade.** Anyone who needs that word in the hero has procurement. Procurement-led buyers are explicitly out of scope until month 18 (see [GTM](./gtm)).

## Persona-specific entry points (constant position, different proof leads)

The position above is **constant**. What changes between phases is *which proof point leads* on the landing page.

| Entry URL | For | Leads with |
|-----------|-----|------------|
| `unsearch.dev/migrate-from-tavily` | Persona A | Code diff + price comparison |
| `unsearch.dev/for-startups` | Persona B | Self-host story + zero-retention + founder support |
| `unsearch.dev/enterprise` | Persona C | SLA + SOC 2 roadmap + dedicated capacity + MSA template |

Constant position is non-negotiable because changing it destroys SEO compounding and confuses MCP-server-installers who will become future Persona B/C champions.

## Vocabulary discipline

Use these words. Never use the banned ones — they erode credibility with the buyers we want.

| Use | Instead of |
|-----|------------|
| search API | search engine |
| agent | bot, LLM, AI |
| self-hostable | on-prem, on-premise |
| Apache 2.0 | open source (alone — be specific) |
| Tavily-compatible | "drop-in" without naming Tavily |
| in beta | partial, basic, early |

**Banned phrases:**
- "enterprise-grade" (signals we're not)
- "AI-powered" (every product is)
- "next-generation" (zero information content)
- "revolutionary" (no)
- "best-in-class" (claim, not evidence)
- "leverage" as a verb in customer-facing copy

## Channel-specific taglines

Constant position, channel-tuned phrasing:

| Channel | Tagline |
|---------|---------|
| GitHub README | "Open-source search API for AI agents. Drop-in Tavily replacement." |
| Show HN title | "UnSearch — open-source Tavily alternative on Cloudflare ($49 vs $500/mo)" |
| MCP directory listing | "Search any web source from your MCP-compatible agent." |
| LangChain integration page | "Production retrieval for LangChain agents." |
| Pricing-comparison X thread | "We charge $49/mo for what Tavily charges $500/mo for. Same API. Apache 2.0." |
| Anthropic Startup directory | "Cloudflare-native, Tavily-compatible search API for Anthropic agents." |

## Price-commitment statement (must appear on `pricing.md` page)

> We will give existing paying customers **12 months written notice** before any price increase. Your tier today is your tier next year.

This is positioning, not legal copy. It is the direct anti-Exa, anti-Brave lever and the single most credible thing we can say about being a trustworthy vendor.

## Positioning under threat conditions

What changes if Cloudflare AI Search goes GA with free tier:

- Pillar 1 (open source) leans harder — Cloudflare AI Search will be closed managed. "Run UnSearch on your own Cloudflare account, no vendor lock-in."
- Pillar 4 (Cloudflare-native) shifts framing from "we use the same edge" to "we extend the same edge with open code you can audit."
- Open partner conversation with Cloudflare: "Cloudflare AI Search for managed; UnSearch for self-hosted on Workers." Don't fight, slot in.

What changes if Tavily/Nebius shuts down the API or pivots:

- Pillar 2 (Tavily-compatible) becomes "Tavily-compatible *because we are the surviving open implementation*."
- Ship a migration tool that ingests Tavily API keys and copies usage logs (read-only) into UnSearch for the first 30 days post-shutdown.

Cross-references:
- See [Market](./market) for the competitor data the pillars cite.
- See [Value prop](./value-prop) for the pain/gain mapping behind each pillar.
- See [Pricing](./pricing) for the price-commitment language verbatim.
