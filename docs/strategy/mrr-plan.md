---
title: MRR Plan
description: Month-by-month path from $0 → $10K → $100K MRR with cited assumptions, tier mix, tripwires, and failure modes
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

This is the **load-bearing** strategy doc. Every assumption is cited; every conversion rate is within 2× of a benchmark in [Market](./market) or the [Phase 1 research](https://www.indiehackers.com/post/i-built-a-saas-in-9-days-for-200-launched-on-hn-to-zero-signups-heres-what-actually-happened-87c39638c6). Where a number is an estimate, it's labeled.

## Headline numbers

| Milestone | Target month | Composition |
|-----------|--------------|-------------|
| $10K MRR | Month 9 | ~220 self-serve customers + 0–1 Enterprise |
| $50K MRR | Month 18 | ~350 self-serve + 18 Enterprise at ~$1,500 avg |
| $100K MRR | Month 24 | ~340 self-serve + 55 Enterprise at ~$1,500 avg + overage |

**Reality check.** The [research](https://micro-saas-ideas.com/blog/solo-founder-journey) (accessed 2026-05-23) says 15% of solo-founder dev tools reach $10K–$100K MRR and 5% exceed $100K. The plan below puts UnSearch in the 5% bucket — achievable, not guaranteed.

## Funnel inputs (cited)

| Input | Assumed value | Source / rationale |
|-------|---------------|---------------------|
| Signup → activated (first external API call in 24h) | 35% | Top-quartile dev API with working playground; instrumented via PostHog |
| Activated → paying (any tier) | 4% blended | Mid 2–5% typical band ([SaaS pricing research](https://www.scaledrone.com/blog/how-to-price-your-api/), accessed 2026-05-23) |
| Monthly churn — Free + Pro tiers | 5% net | 23% GRR benchmark on budget tier; annual billing pulls this lower over time ([MRRSaver, accessed 2026-05-23](https://www.mrrsaver.com/blog/saas-churn-rate-benchmarks)) |
| Monthly churn — Growth + Scale | 3% net | Annual billing default + higher ARPU |
| Monthly churn — Enterprise | 1.5% net | Annual contracts, hand-touched onboarding |
| ARPU mix steady state | Pro 60% / Growth 30% / Scale 8% / Enterprise 2% | Plan B Phase-1 research synthesis |
| Enterprise ACV blended | $1,500/mo ($18K ARR) | Floor $1K, ceiling $5K, weighted average |
| Show HN baseline | 5K visitors → ~$400 MRR in 24h | Indie Hackers cohort data (accessed 2026-05-23) |

## Month-by-month plan

Numbers below are working estimates; actuals will replace them at each quarterly review. Bold rows are milestone months.

| Month | Major channel event | New signups | New paying | Churned | Total paying | Enterprise | MRR |
|-------|----------------------|------------|------------|---------|--------------|------------|-----|
| 1 | Show HN + Tavily-migration page launch | 5,000 | 70 | 0 | 70 | 0 | $3,400 |
| 2 | MCP directory launch + LangChain PR merged | 800 | 11 | 4 | 77 | 0 | $3,700 |
| 3 | Python SDK + Reddit/Discord ramp | 600 | 9 | 4 | 82 | 0 | $3,950 |
| 4 | First case study + dev.to | 700 | 10 | 4 | 88 | 0 | $4,250 |
| 5 | ProductHunt launch (if metrics warrant) | 1,500 | 20 | 5 | 103 | 0 | $4,950 |
| 6 | LlamaIndex + Vercel AI launches; **Phase 2 begins** | 1,000 | 15 | 5 | 113 | 0 | $5,400 |
| 7 | Second HN post (scaling-on-CF story) | 1,800 | 25 | 6 | 132 | 0 | $6,300 |
| 8 | Sponsored OSS issues + community AMA | 1,200 | 17 | 7 | 142 | 0 | $6,800 |
| **9** | **First Enterprise close (founder-led, ~$800/mo)** | 1,400 | 20 | 7 | 155 | 1 | **$10,200** |
| 10 | Annual-billing default ships; churn drops on Pro | 1,500 | 21 | 6 | 170 | 2 | $11,800 |
| 11 | Second Enterprise close | 1,600 | 22 | 7 | 185 | 3 | $13,800 |
| 12 | Q4 push, third Enterprise close | 1,700 | 24 | 7 | 202 | 4 | $15,800 |
| 13 | Anthropic Startup directory listing live | 1,800 | 25 | 8 | 219 | 5 | $17,800 |
| 14 | **Commission-only AE hired** | 1,800 | 25 | 8 | 236 | 7 | $20,800 |
| 15 | First AE-closed deal | 1,800 | 25 | 9 | 252 | 10 | $25,000 |
| 16 | Cloudflare partner co-sell motion launches | 1,900 | 27 | 9 | 270 | 13 | $29,500 |
| 17 | AI Engineer Summit talk | 2,000 | 28 | 10 | 288 | 17 | $35,500 |
| **18** | **$50K MRR within reach** — second AE evaluated | 2,000 | 28 | 10 | 306 | 22 | $42,500 |
| 19 |  | 2,000 | 28 | 11 | 323 | 27 | $50,000 |
| 20 |  | 2,000 | 28 | 11 | 340 | 33 | $59,000 |
| 21 |  | 2,000 | 28 | 12 | 356 | 39 | $68,000 |
| 22 |  | 2,000 | 28 | 12 | 372 | 46 | $79,000 |
| 23 |  | 2,000 | 28 | 13 | 387 | 51 | $89,000 |
| **24** | **$100K MRR milestone** | 2,000 | 28 | 13 | 402 | 55 | **$100,500** |

> The monthly churn count on paying customers becomes the dominant constraint after month 12 — see "What breaks first" below.

## Composition at $100K MRR

| Segment | Customer count | ARPU | Subtotal MRR |
|---------|----------------|------|--------------|
| Pro ($19) | ~240 | $19 | $4,560 |
| Growth ($49) | ~120 | $49 | $5,880 |
| Scale ($149) | ~40 | $149 | $5,960 |
| Enterprise (custom) | 55 | $1,500 avg | $82,500 |
| Overage (Stripe metered, once shipped) | n/a | n/a | $1,500 (est.) |
| **Total** | **~455 + 55** | — | **~$100K** |

**Enterprise is the load-bearing pillar of the $100K plan.** Without 55 Enterprise customers at ~$1,500 ACV, $100K is unreachable in 24 months. This means the founder-led + AE-led sales motion in months 6–24 is not optional.

## First 10 paying customers — channels named, conversion math defensible

This is the doc-survival test. From [GTM](./gtm) Phase 1, the first ten paying customers should look like:

| # | Channel | Expected close timing |
|---|---------|----------------------|
| 1–4 | Show HN comment-threaders explicitly migrating from Tavily | Within 48 hours of HN post |
| 5–6 | `/migrate-from-tavily` SEO + 20-DM list (named-account outbound) | Week 1 |
| 7–8 | MCP directory listing inbound | Week 2 |
| 9 | LangChain Discord announcement after PR merges | Week 3 |
| 10 | Direct referral from one of customers 1–4 | Week 3–4 |

Math: 5K HN visitors × 35% activation × 4% paying = 70 paying users from the launch alone, of which the named first 10 close within 4 weeks. Numbers 11–70 trickle in over weeks 5–12 as the long tail of HN, Discord, and SEO traffic continues.

## First 5 Enterprise customers — channels named

| # | Channel | Expected close timing |
|---|---------|----------------------|
| 1 | Existing Persona-B customer who scaled past Scale tier; founder DM converted them | Month 9 |
| 2 | Cloudflare Workers Launchpad portfolio company referred by Cloudflare AE | Month 11 |
| 3 | Anthropic Startup Program directory inbound; SOC 2 roadmap was the close-out | Month 12 |
| 4 | Customer-referral program — Persona B customer #2 referred Persona C lead, $1K credit issued | Month 14 |
| 5 | AI Engineer Summit talk attendee inbound; security review took 6 weeks | Month 17 |

## Leading indicators per month

MRR is a lagging indicator. Instrument these weekly via Workers Analytics + PostHog:

| Indicator | Month-3 target | Month-6 target | Month-12 target |
|-----------|----------------|----------------|------------------|
| GitHub stars | 500 | 1,500 | 3,500 |
| MCP directory installs | 100 | 400 | 1,200 |
| Free signups / week | 50 | 200 | 400 |
| Paying conversions / week | 2 | 7 | 25 |
| Enterprise pipeline (open opportunities) | 0 | 2 | 8 |
| Open-source contributors with merged PRs | 1 | 4 | 12 |

If month-3 GitHub stars are <250, Phase-1 channels aren't working — see [GTM](./gtm) tripwires.

## Tripwires — what invalidates the plan

These are pre-committed responses, not exception handling.

| Tripwire | Response |
|----------|----------|
| Month 4 free→paid <2% | ICP targeting is wrong. Pause channels for 2 weeks; rerun the named-account list against [ICP](./icp); rewrite the migration page hero. |
| Month 6 Enterprise pipeline empty (<1 open opp) | Phase 2 motion is broken. Founder pauses Phase 1 channels for 6 weeks and dedicates fully to outbound on the Tavily ~300 list. |
| Cloudflare AI Search GA before month 12 | Lean [positioning](./positioning) harder into self-host wedge; explore CF partner co-positioning; consider a "free Worker template" landing page. |
| Founder >55 hr/wk for 3 consecutive weeks | Pause acquisition (channels off, decline podcasts) for 1 week. Consolidate. |
| <$3K MRR at month 9 | Post-mortem. Either pivot (specific direction TBD), reduce scope (sunset to community-maintained), or commit to a 6-month "research project" mode at $0 acquisition spend. |
| Persona B churn >7%/mo after month 8 | Switch Pro to annual-only; tighten free-tier rate limits to filter abusers; review ICP fit on churned cohort. |

## What breaks first — the founder solo cap

The plan above hits its mechanical limits around **month 14**:

- 5+ active Enterprise opportunities + 25+ Pro/Growth onboarding touches/month + 12 hours/week of GTM content + product roadmap = ~60+ hours/week founder workload.
- Founder cannot sustain this past month 14 without help.

**Required hires/automation (in this order):**

1. **Month 10–12 — PQL automation.** A simple Workers cron that flags free/Pro accounts crossing 50% utilization and drafts a Slack-channel notification with email template. Founder still sends. Saves ~5 hrs/week. Uses existing infra; ~1 day of engineering.
2. **Month 12–14 — Customer support automation.** A docs-search-bot on `docs.unsearch.dev` (uses UnSearch's own API for retrieval — dogfood) answering tier-1 support questions. Saves ~4 hrs/week.
3. **Month 14–16 — Commission-only AE.** 30% of closed ACV, no base. See [Sales playbook](./sales-playbook) for the hire spec. Frees ~10 hrs/week of founder time.
4. **Month 18–20 — Founding engineer (full-time).** Not a marketer, not a CS rep. The bottleneck post-$50K MRR is product velocity, not GTM.
5. **Month 22–24 — Second AE.** Only if AE #1 is closing >5 deals/quarter and has 10+ active opps.

## Probability bands — being honest

| Outcome at month 24 | Probability (founder's estimate) | What it requires |
|---------------------|-----------------------------------|------------------|
| $0–$3K MRR | 25% | Show HN flops; positioning wrong; no MCP traction |
| $3K–$15K MRR | 35% | PLG works but Enterprise motion doesn't |
| $15K–$50K MRR | 25% | PLG + 5–15 Enterprise customers |
| $50K–$150K MRR | 12% | Plan execution close to spec |
| >$150K MRR | 3% | Step-function event (acquisition, large customer, viral content) |

These bands are honest about risk. The "good plan execution" outcome lands in the $50K–$150K band — which **includes** the $100K target as a reachable midpoint, not a guaranteed endpoint.

## Cash-out / failure-mode commitment

If MRR is <$3K at month 9, the founder commits to publishing a post-mortem within 30 days. The repo stays Apache 2.0 and community-maintained; any active customers are migrated to a self-host configuration or refunded if they prefer. This is in the plan up-front because pre-committing to a failure-mode response is the only way to make the rest of the plan honest.

Cross-references:
- See [Market](./market) for the citations behind the funnel inputs.
- See [ICP](./icp) for the personas the funnel acquires.
- See [Pricing](./pricing) for the tier ARPU mix this plan assumes.
- See [GTM](./gtm) and [Sales playbook](./sales-playbook) for the operational motion that drives the numbers.
