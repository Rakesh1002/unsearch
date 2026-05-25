---
title: ICP
description: The three personas UnSearch sells to, ordered by sales sequence
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

UnSearch has three ideal-customer profiles, ordered by **when we sell to them**, not by revenue size. Persona A is the volume acquisition channel; Persona B is the revenue base; Persona C is the expansion ceiling. The order is non-negotiable — we have zero credibility selling to Persona C until ~30 Persona B logos exist.

## Persona A — "Maya the AI-Native Indie"

**Months 1–6 · Acquisition · Self-serve PLG**

| Dimension | Detail |
|-----------|--------|
| Firmographic | Pre-seed to Series A, AI-native product, 2–10 engineers, US/EU/Israel/India |
| Role | Solo founder, lead engineer, or "AI lead" at a 2–5 person startup |
| Stack | LangChain, LlamaIndex, Vercel AI SDK, or OpenAI Agents SDK; deploys on Vercel or Cloudflare |
| Current spend | $30–$200/mo on Tavily/Exa/Brave; or self-hosting SearXNG with regret |
| Behavioral signal | Has hit the Tavily $30 plan ceiling; tweets about search-API pricing; comments on the Tavily Nebius acquisition |
| Buying authority | Their own credit card, $19–$149/mo without asking a cofounder |
| Where they live | LangChain Discord #integrations, MCP server directory, `/r/LocalLLaMA`, Tavily GitHub issues, Y Combinator W26/S26 AI cohorts, Anthropic Builders Discord |
| Estimated population | 2,000–5,000 companies globally |

**Sourcing channels (named, for the GTM team):**
- Read [Tavily's GitHub issues](https://github.com/tavily-ai) and DM authors of pricing/limit complaints.
- Watch X/Twitter for "Tavily pricing", "Exa expensive", "open source search API" mentions; reply in thread.
- Submit to the official Anthropic MCP server registry — every install is a Persona A signup.
- Post weekly in `/r/LocalLLaMA` with technical depth (no marketing copy).
- Cross-link from the LangChain + LlamaIndex integration directories.

**Disqualifiers:** pre-revenue agent demos with no users (Free tier forever — serve them but do not optimize for them); solo developers building consumer search products (wrong volume curve); anyone using >1M searches/month already (belongs in Persona B or C).

## Persona B — "Priya the AI-Native Seed/Series A CTO"

**Months 6–18 · Revenue · Founder-led sales-assist**

| Dimension | Detail |
|-----------|--------|
| Firmographic | 5–25 person AI startup, $2–15M raised, has paying customers |
| Vertical | Vertical AI agents (legal research, sales intelligence, due diligence, content, dev tools, customer support) |
| Role | CTO or technical co-founder |
| Stack | Production agent on Anthropic or OpenAI; LangGraph or custom; Cloudflare Workers or Vercel for serving |
| Current spend | $500–$3,000/mo on Exa/Tavily; search is 30–60% of variable cost |
| Behavioral signal | CFO is asking about predictable pricing; legal review is asking about vendor lock-in; engineering is hitting rate-limit pain |
| Buying authority | CTO signs $500–$2,000/mo without board approval; $2K+ usually needs co-founder buy-in |
| Where they live | YC alumni Slack, Anthropic Startup Program directory, Cloudflare Workers Launchpad, On Deck Founders, AI Engineer Foundation events, founder X with `#buildinpublic` |
| Estimated population | 5,000–15,000 companies globally |

**Sourcing channels:**
- Inbound from Persona A who scale up (the natural ladder).
- Outbound to the ~300 Tavily customers identifiable from public case studies, conference talks, and GitHub repos.
- Partner channel: Anthropic Startup Program once accepted, OpenAI startup directory.
- Cloudflare Workers Launchpad relationship for shared portfolio companies.

**Disqualifiers:** pre-revenue (no buying authority); single-vertical compliance-led (legal/health AI with 6-month security review — too slow); any prospect asking for a feature beyond the published roadmap (disqualified for current quarter).

## Persona C — "David the Series B+ AI Infra Buyer"

**Months 18–24 · Expansion · Inbound only, sales-led**

| Dimension | Detail |
|-----------|--------|
| Firmographic | 100–500 person AI infra or vertical-AI company, $20–100M ARR |
| Role | VP Engineering + Procurement; sometimes a dedicated AI Platform Lead |
| Stack | Multi-cloud or Cloudflare-heavy; has a security team and an MSA template |
| Current spend | $5K–$30K/mo on Glean (internal) + Exa/Tavily (external); evaluating consolidation |
| Behavioral signal | Compliance team has asked about SOC 2 / data residency; procurement has rejected a quote from Exa or Glean |
| Buying authority | VP Eng + Procurement; $12K–$60K annual contracts |
| Where they live | Cloudflare partner ecosystem; inbound referrals from Persona B who got acquired or scaled into them |
| Estimated population | 500–1,500 companies globally |

**Sourcing channels (all inbound or partner-sourced):**
- Referrals from Persona B customers — $1K credit per closed Enterprise deal.
- Cloudflare AE co-sell motion: Cloudflare reps refer customers running on Workers to UnSearch self-hosted on Workers.
- Single annual conference presence (AI Engineer Summit) — talk + booth, not booth-only.

**Disqualifiers:** any prospect requesting bespoke product work (custom connectors, custom models, dedicated engineering); any deal where the procurement cycle is projected past 90 days (disqualify and re-engage in 6 months).

## Anti-personas — who we explicitly do not sell to

These are common false positives that look like ICPs but burn solo-founder hours with no payoff:

| Anti-persona | Why not |
|--------------|---------|
| Consumer search users | Wrong product (we don't have a UI, we have an API) |
| Glean's enterprise procurement buyers | Wrong product (internal knowledge ≠ open web search); cycle measured in quarters |
| Big Tech internal teams | Won't adopt an open-source competitor to Cloudflare AI Search hosted on Cloudflare |
| Legal-AI or health-AI compliance buyers | Multi-quarter security reviews; founder has no capacity to manage |
| "I want to scrape Twitter/Instagram/LinkedIn" | Scraping legal landscape (Anthropic $1.5B settlement, Reddit v. Perplexity) — politely refuse |
| Marketers wanting SEO data at $10/mo | Wrong category; refer them to Serper |

## Buying-trigger summary

| Persona | Trigger that creates the buy | Time-to-first-value target |
|---------|------------------------------|----------------------------|
| Maya (A) | Tavily/Exa free-tier cap hit OR Nebius email arrives | 5 minutes |
| Priya (B) | Exa bill crosses $1K/mo OR legal review flags vendor lock-in | 24 hours from intro to demo |
| David (C) | Procurement rejects Glean/Exa quote OR Persona B referral | 14 days from intro to POC start |

Cross-references:
- See [JTBD](./jtbd) for the job each persona hires UnSearch to do.
- See [GTM](./gtm) for how we reach each persona by phase.
- See [Pricing](./pricing) for the tier each persona buys.
- See [Sales playbook](./sales-playbook) for the motion that closes Personas B and C.
