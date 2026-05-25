---
title: Market
description: Market sizing, headwinds, tailwinds, and competitive landscape for UnSearch
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

UnSearch competes in **Agent Search Infrastructure** — the layer that gives AI agents real-time web grounding. The category is not "search engine" (Google/Brave own that), not "vector database" (Pinecone/Vectorize own that), and not "enterprise knowledge search" (Glean owns that). It's the API call an agent makes when it needs the open web.

## Why this category now

Three market events in the first quarter of 2026 created simultaneous in-market intent:

1. **Tavily was acquired by Nebius for $275M** in February 2026, leaving every Tavily customer with vendor-roadmap uncertainty ([TechCrunch, accessed 2026-05-23](https://techcrunch.com/2025/08/06/tavily-raises-25m-to-connect-ai-agents-to-the-web/)).
2. **Brave Search API killed its free tier** in February 2026, moving all developers to metered billing ([Implicator, accessed 2026-05-23](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/)).
3. **Exa raised list prices from $5 to $7 per 1K queries** in March 2026, with backlash on HackerNews ([Exa Pricing, accessed 2026-05-23](https://exa.ai/pricing); [HN discussion](https://news.ycombinator.com/item?id=43910228)).

These three displacements together create a six-month window where developers are actively evaluating alternatives.

## Sizing

Use developer counts as the sizing primitive rather than top-down TAM reports, which over-count adjacent vectors and crawlers.

- **OpenAI:** 4M developers had built on the platform by DevDay 2025 ([OpenAI Statistics, accessed 2026-05-23](https://www.getpanto.ai/blog/openai-statistics)).
- **Anthropic:** 300K+ business customers, 500+ spending over $1M annually ([Anthropic Statistics, accessed 2026-05-23](https://www.getpanto.ai/blog/anthropic-ai-statistics)).
- **Agentic AI market:** $9.14B in 2026, projected $139.19B by 2034 at 40.5% CAGR ([Fortune Business Insights, accessed 2026-05-23](https://www.fortunebusinessinsights.com/agentic-ai-market-114233)).
- **Worldwide AI spending:** $2.022T in 2026, +37% year-over-year ([Gartner, accessed 2026-05-23](https://www.gartner.com/en/newsroom/press-releases/2026-1-15-gartner-says-worldwide-ai-spending-will-total-2-point-5-trillion-dollars-in-2026)).

A reasonable working SAM is **English-speaking AI developers building agent or RAG products who add a web-search tool**. Working estimate: 4M OpenAI devs × ~8% search-tool attach × $25/mo blended = ~$96M/yr indie/pro band; add Anthropic's 300K business customers × ~20% search attach × $40/mo = ~$29M/yr — **~$125M/yr addressable today**, growing with the underlying market.

UnSearch at $100K MRR = **~1% of this addressable band**, a tractable but non-trivial target.

## Tailwinds

- **Model Context Protocol (MCP)** has 97M monthly SDK downloads and 10,000+ public servers as of March 2026 ([WorkOS MCP 2026 Guide, accessed 2026-05-23](https://workos.com/blog/everything-your-team-needs-to-know-about-mcp-in-2026)). MCP is the single highest-leverage distribution surface of 2026; shipping a first-class MCP server is table stakes.
- **Agent frameworks are at scale:** LangGraph 34.5M monthly downloads; Vercel AI SDK 20M+; OpenAI Agents SDK 10.3M ([Speakeasy Framework Comparison, accessed 2026-05-23](https://www.speakeasy.com/blog/ai-agent-framework-comparison)). Each is a retriever-integration surface.
- **Enterprise AI budgets are accelerating:** a16z's CIO survey shows ~75% expected YoY growth in LLM budgets ([CIO.com, accessed 2026-05-23](https://www.cio.com/article/4092928/how-cios-can-get-a-better-handle-on-budgets-as-ai-spend-soars.html)).
- **Open-source AI infra is mainstream:** vLLM joined the PyTorch Foundation in 2025; 72% of organizations have adopted AI in at least one business function (McKinsey 2025 Global AI Survey).
- **India developer market:** 890+ generative-AI startups, 3.7× year-over-year growth ([NASSCOM, accessed 2026-05-23](https://www.ciol.com/news/nasscom-genai-foundry-fourth-cohort-india-ai-startups-2026-11749733)).

## Headwinds

- **Cloudflare AI Search** launched in open beta in April 2026 — a managed RAG primitive on the same edge UnSearch runs on, with hybrid semantic + BM25 search ([Cloudflare Blog, accessed 2026-05-23](https://blog.cloudflare.com/ai-search-agent-primitive/)). This is the single largest existential threat. Defense framing: UnSearch is the open-source, vendor-agnostic alternative — you run UnSearch on *your* Cloudflare account (or any container host) and own the code path.
- **Foundation models ship native web search:** ChatGPT, Claude, Gemini, and Copilot all now offer real-time web retrieval in their consumer and enterprise products. Implication: standalone "search" commoditizes; the wedge moves to retrieval quality + agent integration + cost predictability.
- **Hyperscaler bundles:** AWS Bedrock Knowledge Bases, Azure AI Search, and Google Vertex AI Search ship RAG-as-a-service tied to their model platforms.
- **Scraping legal landscape:** Anthropic settled a U.S. copyright class action for $1.5B in September 2025 ([Techdirt, accessed 2026-05-23](https://www.techdirt.com/2025/12/24/google-built-its-empire-scraping-the-web-now-its-suing-to-stop-others-from-scraping-google/)); NYT v. OpenAI proceeding on copyright claims; Reddit v. Perplexity filed October 2025. robots.txt + ToS + technical barriers together form a legal bulwark — UnSearch must default to respecting them.

## Competitive landscape

| Vendor | Price for 100K searches/mo | Open source? | MCP server? | 2026 signal |
|--------|-----------------------------|--------------|-------------|-------------|
| Tavily | ~$700 ($30/$100 plans + $0.008/credit) | No | Yes | **Acquired by Nebius $275M, Feb 2026** — migration target |
| Exa | ~$700 ($7/1K) | No | No | **Raised prices $5→$7/1K, Mar 2026** — backlash |
| Brave Search API | ~$500 ($5/1K) | No | Yes | **Killed free tier, Feb 2026** — dev hostility |
| Serper | ~$50 ($0.30–1/1K) | No | No | Cheapest, but pure SERP — no agent features |
| Linkup | ~$500 ($0.005/req) | No | No | $13.2M raised, ~$990K revenue 2025; agent-native |
| Perplexity Sonar | token-priced | No | No | $200M ARR; consumer-first, not dev-first |
| You.com | ~$500 ($5/1K) | No | Yes (capped) | No major positioning move |
| Glean | ~$5K+/mo (enterprise only) | No | No | $200M ARR; orthogonal — internal knowledge, not open web |
| Cloudflare AI Search | Free beta | No | No | **Direct threat; same edge** |
| **UnSearch** | **$49 (Growth tier)** | **Apache 2.0** | **Yes (M1)** | **Drop-in Tavily replacement, 10× cheaper** |

Sources: [Tavily Pricing](https://www.tavily.com/pricing), [Exa Pricing](https://exa.ai/pricing), [Brave Search API Pricing](https://api-dashboard.search.brave.com/documentation/pricing), [Serper](https://serper.dev/), [Linkup Pricing](https://www.linkup.so/pricing), [Perplexity API Pricing](https://docs.perplexity.ai/docs/getting-started/pricing), [You.com Pricing](https://you.com/pricing), [Glean Pricing Breakdown](https://www.gosearch.ai/blog/glean-pricing-explained/) — all accessed 2026-05-23.

**Median price (excluding Glean's enterprise-only and Cloudflare's beta): ~$500/mo for 100K searches.** UnSearch Growth at $49 is 10× cheaper at the headline usage band — this is the marketing wedge.

## Adjacent benchmarks

- **Bright Data** (web data, not the same category): $300M ARR in late 2025, targeting $400M by mid-2026 ([Bright Data, accessed 2026-05-23](https://brightdata.com/blog/web-data/best-web-scraping-apis)).
- **Glean** (enterprise knowledge, orthogonal): doubled ARR from $100M to $200M in nine months ending mid-2026 at a $7.2B valuation ([Glean Press, accessed 2026-05-23](https://www.glean.com/press/glean-surpasses-200m-in-arr-for-enterprise-ai-doubling-revenue-in-nine-months)).

Adjacent revenue at this scale demonstrates that customers will pay for retrieval — the question is whether they pay closed-source vendors with retention or open-source vendors with portability.

## 24-month market thesis

Search is being unbundled from foundation models. The winning agent-search vendor is the one developers `npm install` or `pip install`, not the one VPs of AI sign procurement docs for. UnSearch's wedge is the combination of (a) Apache 2.0 license, (b) Tavily-compatible API surface (zero-rewrite migration), and (c) the same Cloudflare-edge cost structure as Cloudflare AI Search, but vendor-agnostic and open.

Cross-references:
- See [ICP](./icp) for who buys.
- See [Positioning](./positioning) for how we describe ourselves.
- See [MRR plan](./mrr-plan) for the realistic revenue path that this market enables.
