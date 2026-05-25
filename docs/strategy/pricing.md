---
title: Pricing
description: Tier rationale, annual-default checkout, overage policy, and our public price-commitment statement
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

## Tiers

The four self-serve tiers below are the canonical product plans. They match the seed data in `workers/schema.sql` and `app/services/stripe_service.py`. Enterprise is sales-led only; no published floor.

| Tier | Monthly | Annual (2 months free) | Search/mo | Scrape/mo | Rate limit | Burst |
|------|---------|------------------------|-----------|-----------|------------|-------|
| **Free** | $0 | — | 5,000 | 500 | 10 rpm | 2× for 10s |
| **Pro** | $19 | $190 | 25,000 | 5,000 | 60 rpm | 2× for 10s |
| **Growth** | $49 | $490 | 100,000 | 25,000 | 200 rpm | 2× for 10s |
| **Scale** | $149 | $1,490 | 500,000 | 100,000 | 1,000 rpm | 2× for 10s |
| **Enterprise** | Contact us | Annual contracts | Custom | Custom | Custom | Custom |

## Why these tiers, in this order

The market price for 100K searches/mo across closed-source vendors is **~$500/mo median** (see [Market](./market)). At $49 our Growth tier is **10× cheaper** at the headline usage band. That gap is the marketing wedge and we will defend it.

- **Free at 5,000 searches/mo** is 5× Tavily's 1,000 free quota. The cost to UnSearch is small at scale: at >40% cache hit rate on common queries, marginal cost per free user is ~$0.90/mo, fully absorbed at 2%+ conversion.
- **Pro at $19** is the "I'm trying it" tier. Below the credit-card-without-thinking threshold. Must not become the natural ceiling — the playground will surface "you've used 70% of Pro, Growth saves you $X" math early.
- **Growth at $49** is the headline 10×-cheaper tier — the one that goes in every comparison post and HN comment.
- **Scale at $149** sits comfortably below the "I need a procurement call" psychological barrier (~$500/mo for SMB SaaS), preserving the PLG funnel.
- **Enterprise** is hand-touched, annual contracts only, no listed price. See [Sales playbook](./sales-playbook).

## Annual is the default at checkout

Industry benchmark: **the budget tier (<$50/mo) retains only 23% of gross revenue at 12 months** on monthly billing. Annual billing pulls that closer to 70%+. Annual is therefore not an optimization — it's structural.

Implementation: `price_yearly` columns already exist in the schema. The `/billing` page defaults the toggle to annual, with monthly as a secondary option. Existing monthly customers get a "switch to annual and save 2 months" banner on their dashboard.

## Overage policy

Soft cap at 100% of plan. Hard cap at 120%. Above the soft cap, customers pay overage at rates that **preserve the 10×-cheaper claim at each tier**:

| Tier | Overage rate | Comparable closed-vendor price |
|------|--------------|-------------------------------|
| Pro | $0.005/search | ~10× cheaper than Exa $0.05/search |
| Growth | $0.002/search | ~10× cheaper than Brave $0.005/search |
| Scale | $0.001/search | ~10× cheaper than Tavily $0.008/credit |
| Free | hard cutoff, no overage | — |

Hard cap at 120% prevents bill-shock-driven churn. Above 120%, requests return 429 with a "talk to us" upgrade link.

> **Implementation note:** Overage billing requires Stripe metered billing on top of the existing fixed-plan model. Schema already supports `search_overage` in `usage_records`; wiring up the Stripe metered prices is a separate engineering task tracked in the [roadmap](../roadmap), not part of this strategy refresh.

## Bring-your-own-keys (BYOK) for premium engines

Available on Growth and above:

- Google Custom Search (user-supplied CSE ID + API key)
- Brave Search API (user-supplied key)
- Bing Web Search (user-supplied key)

UnSearch routes queries through the supplied key and bills the customer's vendor account directly. UnSearch charges no per-search markup; this is a sales-assist feature that converts cost-sensitive customers to Growth.

## Free-tier sustainability

The marginal cost of a free-tier search is dominated by search-engine API calls + Workers AI tokens for reranking + Workers/D1 compute. At measured cache hit rates >40% on common queries (instrument weekly via Workers Analytics), the marginal cost per free user is small relative to the conversion value of the cohort. If marginal cost ever exceeds $2/user/mo, the response is to **lower the free-tier quota from 5K to 2K** (a `plans.search_limit` row update), not to push paid users harder.

Defense against free-tier abuse:

- The `is_agent_placeholder` + `claim_code` flow already in the schema means agent-only signups are rate-limited at the sandbox key level and can't burn quota indefinitely without claiming.
- IP-based rate limits prevent obvious abuse at the edge (Durable-Object sliding window in `workers/src/durable-objects/rate-limiter.ts`).

## Price-commitment statement

This appears verbatim on `unsearch.dev/pricing`:

> **We will give existing paying customers 12 months written notice before any price increase. Your tier today is your tier next year.**

This is positioning, not legal copy. It is the direct counter to Exa's March 2026 $5→$7 price hike and Brave's February 2026 free-tier kill — both of which left customers with no time to budget or migrate. The 12-month policy is enforceable in our standard ToS (existing contracts honor the price at sign-up).

## Grandfathering policy

Any tier price is locked for any individual customer for **24 months from their first paid subscription**. If we raise list prices, existing customers see the new price only at the start of their 25th month (or at renewal of an annual contract, whichever is sooner). This is the operational implementation of the 12-month-notice commitment.

## Price localization

USD only for v1.

- Per the [market data](./market), no incumbent (Tavily, Exa, Brave, Linkup, Perplexity) offers regional pricing on their search APIs.
- Founder is India-based; a regional INR tier is an obvious lever but **deferred until MRR > $25K**. The operational overhead of a second currency, second Stripe account, and India GST registration is not justified at sub-$25K MRR. Revisit at the month-12 review.

## Enterprise — "Contact us" with no listed floor

Enterprise sits above Scale and is **deliberately unpriced** in public.

What an Enterprise contract includes:
- Custom search/scrape volume
- Self-host deployment guide + 30-day deployment-support engagement
- Signed MSA + DPA (template from Common Paper or LawTrades — see [Sales playbook](./sales-playbook))
- Dedicated Durable-Object pool / dedicated Container replicas for predictable latency
- SLA — 99.9% effective uptime, 4-hour P1 response (commitments calibrated to operational maturity at deal time; see [observability docs](../../workers/OBSERVABILITY.md))
- SSO (planned; not shipped — explicitly contracted as "delivered within 90 days")
- Audit logs (D1 query log replay)

Why "no listed price":
- Founder-led sales motion can't run with a published floor that anchors negotiations.
- Enterprise deals are calibrated to volume + service level; no two are identical.
- The lack of a number on the page is a deliberate qualification gate — buyers who require a public price are not Persona C.

Operating floor for the founder: **do not negotiate Enterprise contracts below $1,000/mo**. Below that, point them at Scale + overage.

## What we will not do

These are pricing temptations that erode the model — explicit guardrails:

- **No per-user / per-seat pricing.** UnSearch is an API, not a SaaS dashboard. Per-call billing is the model.
- **No "open core" feature splits.** Every feature in the codebase works the same way self-hosted and managed. The wedge is Apache 2.0 — splitting features breaks it.
- **No "$1 first month" promotional pricing.** It attracts the wrong cohort.
- **No discounts off list price for self-serve tiers.** Discounts are an Enterprise lever only; below Enterprise, the answer is "use the lower tier."
- **No surprise price increases.** The 12-month notice policy makes this enforceable.

## Cross-references

- See [Market](./market) for the competitor-pricing benchmarks that anchor the tier math.
- See [User journey](./user-journey) for upgrade triggers tied to quota burn.
- See [Sales playbook](./sales-playbook) for the Enterprise quoting motion.
- See [MRR plan](./mrr-plan) for how tier mix maps to revenue milestones.
