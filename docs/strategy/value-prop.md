---
title: Value Proposition
description: Pains/gains × pain-relievers/gain-creators for the top two ICPs
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

This is the value-proposition canvas applied to UnSearch's two highest-leverage personas (Maya/A and Priya/B). David/C inherits Priya's value map plus the procurement-defensibility layer; we'll document it after the first three Persona-C deals close.

See [ICP](./icp) and [JTBD](./jtbd) first if persona names look unfamiliar.

## Persona A — Maya the AI-Native Indie

### Customer profile

| Jobs | Pains | Gains |
|------|-------|-------|
| Ship the agent demo by Friday | Tavily 1K/mo free cap blocks the demo | Working end-to-end demo in <5 minutes |
| Keep monthly bill under $50 | $30→$100 cliff pricing at Tavily, $7/1K at Exa | Predictable bill at the price they expected |
| Use the agent framework they already know | Switching costs across vendors (different request shapes) | Drop-in code with one base-URL change |
| Not get acquired-out or price-hiked | Nebius email anxiety; Exa raised prices Mar 2026; Brave killed free tier Feb 2026 | Vendor that publishes a price-commitment policy |
| Look credible to YC/their investor | "AI-powered, closed-source, $500/mo" doesn't sound credible | "Apache 2.0, $49/mo, runs on Cloudflare" sounds credible |

### Value map

| Products & services | Pain relievers | Gain creators |
|---------------------|----------------|---------------|
| Free tier 5K searches/mo (5× Tavily's 1K) | Demo no longer blocked by quota | First successful API call in <5 minutes |
| Pro at $19/mo (entry tier) | No $30→$100 cliff; smooth $19→$49→$149 ramp | Credit card without thinking |
| Tavily-compatible `/api/v1/agent/search` | Zero rewrite — same `client.search()` calls | Migration from Tavily takes ~30 minutes |
| Apache 2.0 license | Fork-able if we ever disappoint; no acquisition risk | "We use open source" — credible in pitch decks |
| Cloudflare Workers + D1 + Vectorize | Sub-200ms global p50; no infra babysitting | Same edge as the rest of their stack |
| MCP server (M1 ship) | Native integration with Claude Desktop, Cursor, etc. | Distribution surface bigger than npm |
| TS SDK + LlamaIndex retriever (shipped) | No glue code to write | Production code in <1 hour |
| Public **12-month price-notice commitment** | Direct anti-Exa, anti-Brave guarantee | Sleep-at-night vendor trust |

**Switching cost analysis for Maya:**

- From Tavily: ~30 minutes. One base-URL change in their LangChain config. The `/api/v1/agent/search` endpoint shape matches.
- From Exa: ~4 hours. Different API shape (neural-search request payload), but the LlamaIndex retriever handles most of the translation.
- From Brave: ~2 hours. Different response shape, similar conceptually.

## Persona B — Priya the AI-Native Seed/Series A CTO

### Customer profile

| Jobs | Pains | Gains |
|------|-------|-------|
| Don't get fired for choosing the wrong vendor | Exa bill at $2K/mo is now visible to the CFO | Predictable monthly bill with variance <10% |
| Pass the next legal/compliance review | "Closed-source vendor with no SLA" is hard to defend | Self-host inside their VPC; signed DPA available |
| Preserve gross margin | Search is 30–60% of COGS in some verticals | $149 Scale tier → 10× cheaper per search than Exa |
| Stay portable across cloud vendors | Tavily/Exa lock-in if their account changes | Apache 2.0 means fork-and-run is always an option |
| Ship features, not infra | Babysitting SearXNG, managing scrapers, debugging rate limits | Managed option with self-host parity |

### Value map

| Products & services | Pain relievers | Gain creators |
|---------------------|----------------|---------------|
| Scale tier $149/mo for 500K searches | 10× cheaper per search vs $5–$7/1K market | Bill stays inside CFO comfort zone |
| Self-host on their own Cloudflare account in <30 minutes | Legal review passes — vendor lock-in eliminated | "We run our own infra" — defensible in due diligence |
| Same code paths self-hosted vs managed | No "open core surprise" — no proprietary closed half | Trust the docs; what's in the repo is what runs |
| Annual billing default (2 months free) | Predictable cash flow; no monthly surprise | CFO-friendly procurement |
| Zero-retention mode (Pro+ tiers) | GDPR/privacy review is faster | Customer-trust story in their own pitch |
| Topic monitoring + fact verification (in beta) | Future-proofs the retrieval layer for richer agent workflows | Expansion bait — converts Growth to Scale to Enterprise |
| Founder-led onboarding (under 25 paying customers per month) | Stuck? The founder is in your Slack | Velocity — onboarding in days not weeks |
| Apache 2.0 with 12-month price-notice commitment | Vendor uncertainty eliminated | Optionality — can fork if needed |

**Switching cost analysis for Priya:**

- From Tavily managed → UnSearch managed: ~30 minutes (same as Maya).
- From Exa managed → UnSearch managed: 4–8 hours (different request shape; benchmark on real queries).
- From any closed vendor → UnSearch self-hosted: 1–2 days for first-pass; the founder does the onboarding session.

**"Apache 2.0 = vendor-proof" — quantifying the gain:**

The standard procurement objection to a startup vendor is "what if you disappear or get acquired?" Open-source license is the answer that scales. A reasonable ceiling on the implicit lock-in cost of a closed vendor at Priya's scale (50K–500K searches/mo on annual contract) is **~$50K/year in negotiating power** — the rough difference between a closed-vendor renewal price and the price they could push to if they could credibly threaten to self-host. Cite the [Glean pricing breakdown](https://www.gosearch.ai/blog/glean-pricing-explained/) (accessed 2026-05-23) as the worked example of what happens when no portable alternative exists.

## How the "extra surfaces" fit

UnSearch ships more than core search — neural search, knowledge-graph (entity extraction), topic monitoring, fact verification, deep research agent. These are **expansion bait, not lead messages**.

- **For Persona A:** do not lead with them. Lead with Tavily compatibility + price.
- **For Persona B:** introduce them in the founder onboarding session as "things you can layer on as your agent matures." They become the reason Growth customers move to Scale.
- **For Persona C:** they are the procurement justification for Enterprise pricing — "one vendor for search + monitoring + verification."

Anything currently marked "in beta" in [feature-matrix](../feature-matrix) is described as "in beta" in customer conversations. We do not over-claim. (See the truthfulness rule in [README](./README).)

## What the value prop will *not* include

These are common temptations that erode credibility:

- Generic "saves you time" framing without a measured outcome.
- Generic "enterprise-grade reliability" before having an enterprise SLA.
- "AI-first" or "next-generation" — see [Positioning](./positioning) vocabulary discipline.
- Comparisons against Glean for connector features we don't ship (the [feature matrix](../feature-matrix) is being corrected to remove these claims).

Cross-references:
- See [ICP](./icp) for the personas this canvas applies to.
- See [JTBD](./jtbd) for the underlying jobs.
- See [User journey](./user-journey) for where each pain reliever shows up in the funnel.
- See [Pricing](./pricing) for the tier math behind the "10× cheaper" claim.
