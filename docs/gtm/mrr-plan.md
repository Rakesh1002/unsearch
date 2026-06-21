---
title: MRR Plan
description: Month-by-month path from $0 → $25K → $250K → $750K MRR with named first-10-customer hypothesis, leading indicators, tripwires
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

This is the **load-bearing** strategy doc. Every assumption is cited; every conversion rate is within 2× of a benchmark in [Market](./market.md) or the industry research. Where a number is an estimate, it's labeled. After the 2026-05-28 reposition to verifiable retrieval, the funnel shape changes meaningfully — fewer free signups (smaller TAM), higher conversion (sharper pain), higher ARPU (regulated buyers, not indie devs), and Enterprise / Self-host as the load-bearing pillar instead of an afterthought.

## Headline numbers

| Milestone | Target month | Composition |
|-----------|--------------|-------------|
| $25K MRR | Month 3 | ~120 self-serve (Pro/Growth) + 1–2 self-host design partners (free or paid pilot) |
| $250K MRR | Month 9 | ~250 self-serve + 8 self-host contracts at ~$24K/yr ($2K/mo avg) |
| $750K MRR | Month 12 | ~350 self-serve + 22 self-host contracts ($24K/yr avg) + 4 self-host v2 ($99K/yr) + 1 Enterprise (hosted) |

**Reality check.** Regulated-AI infra is a higher-ACV / lower-volume motion than the indie-dev funnel the previous MRR plan assumed. The "$100K MRR at Month 24" target from the prior framing has been replaced because the post-pivot motion is faster to revenue (compliance forcing function: EU AI Act Aug 2026), even if the raw signup volume is lower.

## Funnel inputs (cited)

| Input | Assumed value | Source / rationale |
|-------|---------------|---------------------|
| MCP install → first verified result | 80% | MCP-first means evaluation = use; the install IS activation |
| MCP install → paying (any tier) within 30d | 8% blended | Sharper pain + lower volume; 2× indie-dev band benchmark |
| Self-host pilot → paid contract | 40% | Mid-band for compliance-forced procurement once an executive sponsor exists |
| Monthly churn — Free + Pro | 5% net | Comparable to budget tier; annual billing pulls this lower over time |
| Monthly churn — Growth + Scale | 3% net | Annual billing default + higher ARPU |
| Monthly churn — Self-host annual contracts | 0.8% net | Annual contracts; switching costs high once compliance is in place |
| ARPU mix at $250K MRR | Pro 15% / Growth 25% / Scale 12% / Self-host 48% | Estimate based on ICP-1 + ICP-2 ratio |
| Self-host v1 ACV | $24K/yr ($2K/mo) | Pricing doc floor |
| Self-host v2 ACV | $99K/yr ($8.25K/mo) | Pricing doc v2 |
| Enterprise (hosted) ACV blended | $36K/yr ($3K/mo) | Floor $1.5K, ceiling $10K, weighted |
| Show HN baseline | 7K visitors → ~$3,500 MRR in 30d | Indie Hackers cohort data adjusted for sharper-wedge framing |

## Month-by-month plan

Numbers below are working estimates; actuals will replace them at each quarterly review. Bold rows are milestone months.

| Month | Major channel event | MCP installs | New paying | Churned | Total paying | Self-host | MRR |
|-------|----------------------|--------------|------------|---------|--------------|-----------|-----|
| **1** | HN launch + MCP registry submission | 1,200 | 80 | 0 | 80 | 0 | $5,200 |
| 2 | EU AI Act content piece + 40-prospect outbound | 900 | 65 | 4 | 141 | 1 (pilot, $0) | $9,200 |
| **3** | First self-host paid contract closes | 800 | 50 | 5 | 186 | 2 (1 paid v1) | **$25,000** |
| 4 | LegalGeek US conference talk | 700 | 45 | 6 | 225 | 3 | $35,200 |
| 5 | LangChain + Vercel AI SDK integrations land; "Hallucinated Citation Index" Q1 published | 1,000 | 60 | 7 | 278 | 5 | $54,500 |
| 6 | AI4 Health conference; ICP-2 outbound to 30 named banks/hospitals | 800 | 50 | 8 | 320 | 7 | $80,000 |
| 7 | Second HN post ("how we sign 1M citations on Cloudflare") + first Self-host v2 close | 1,100 | 70 | 10 | 380 | 9 (1 v2 at $99K) | $135,000 |
| 8 | First Big4 partnership kickoff | 900 | 55 | 12 | 423 | 12 | $170,000 |
| **9** | **$250K MRR within reach** — first US bank pilot starts | 900 | 55 | 13 | 465 | 15 | $215,000 |
| 10 | "EU AI Act Article 12 logging" technical guide; first BigLaw close | 800 | 50 | 14 | 501 | 18 | $250,000 |
| 11 | AI Engineer Summit talk | 1,000 | 60 | 14 | 547 | 22 | $315,000 |
| **12** | **$750K MRR runway visible** — second v2 close + first Enterprise (hosted) | 900 | 55 | 15 | 587 | 26 | $420,000 |

Month 12 → $750K MRR requires the load-bearing assumption that Self-host v1 + v2 contracts can be paced at ~2/mo from Month 9 onward. This is the failure-mode-sensitive number.

**Reality check on Month 12.** $420K is the modeled landing; the headline $750K requires Months 13–18 to land another ~25–30 self-host contracts. Carry that into the Month-12 review and re-baseline if the slope is shallower than 2/mo.

## Composition at $250K MRR (Month 9)

| Segment | Customer count | ARPU | Subtotal MRR |
|---------|----------------|------|--------------|
| Pro ($19) | ~150 | $19 | $2,850 |
| Growth ($49) | ~190 | $49 | $9,310 |
| Scale ($149) | ~100 | $149 | $14,900 |
| Self-host v1 ($24K/yr = $2K/mo) | 14 | $2,000 | $28,000 |
| Self-host v2 ($99K/yr = $8.25K/mo) | 1 | $8,250 | $8,250 |
| Enterprise (hosted) | 0 | — | $0 |
| Overage (Stripe metered, once shipped) | n/a | n/a | $5,000 (est.) |
| **Total** | **~440 + 15 contracts** | — | **~$68K self-host + $32K self-serve + $5K overage = $105K hosted band + $145K self-host** |

(Adjust on quarterly review — these are projections.)

**Self-host (v1 + v2) is the load-bearing pillar of the $250K plan.** Without 15+ self-host contracts at ~$2K/mo blended, $250K is unreachable in 9 months. This means the founder-led ICP-2 motion is not optional from Month 3 onward.

## First 10 named customer hypothesis (illustrative — validate Week 1)

Targets defined as "AI startups < 80 people, building vertical AI for regulated industry, observable on YC / GitHub / LinkedIn / Crunchbase." Each closes within 4 weeks of HN launch.

| # | Vertical | How they hear about us |
|---|---|---|
| 1 | Legal-AI startup, case-law RAG | Show HN comment-threaders explicitly looking for citation-grade retrieval |
| 2 | Legal-AI startup, contract-review agent | Same |
| 3 | Legal-AI startup, legal-research copilot | MCP registry listing inbound |
| 4 | Medical-RAG, clinical-decision-support | EU AI Act content piece inbound |
| 5 | Medical-RAG, drug-interaction agent | Hand-picked outbound (founder DM) |
| 6 | Fintech research-agent | Hand-picked outbound |
| 7 | Fintech compliance-bot | Hand-picked outbound |
| 8 | Insurance underwriting AI | MCP registry inbound |
| 9 | GovTech / regulatory-tracking | Webrecorder community thread → ICP-3 → ICP-1 ladder |
| 10 | Academic-integrity / citation-checking newsroom tool (ICP-3 conversion to paid) | Sponsored SearXNG upstream relationship |

Math: 7K HN visitors × 8% MCP install × 8% paying within 30 days = ~45 paying customers from the launch alone. The named first 10 close within 4 weeks; numbers 11–80 trickle in over weeks 5–12 as the long tail of HN / MCP-registry / `awesome-mcp-servers` traffic continues.

## First 5 Self-host customers — channels named

| # | Channel | Expected close timing |
|---|---------|----------------------|
| 1 | ICP-1 customer scales past Scale tier; founder upsell offers self-host v1 | Month 3 |
| 2 | EU AI Act content inbound from a Series-B legal-AI company; founder-closed v1 | Month 5 |
| 3 | Inbound from a regional bank's AI platform director, sourced via LinkedIn outbound | Month 7 (v2, $99K) |
| 4 | AI4 Health talk leads to a hospital-system AI platform conversation | Month 8 |
| 5 | Big4 partnership co-introduces a BigLaw client; v1 with v2 upsell at Year 2 | Month 9 |

## Leading indicators per month

MRR is a lagging indicator. Instrument these weekly via Workers Observability + PostHog:

| Indicator | Month-3 target | Month-6 target | Month-12 target |
|-----------|----------------|----------------|------------------|
| GitHub stars | 1,000 | 2,500 | 5,500 |
| MCP registry installs (lifetime) | 600 | 2,500 | 7,500 |
| Free signups / week | 75 | 150 | 250 |
| Verified-results-per-week, all customers | 200K | 1M | 5M |
| Paying conversions / week (self-serve) | 12 | 25 | 50 |
| Self-host pipeline (open opportunities) | 1 | 5 | 18 |
| Self-host closes (cumulative) | 2 | 7 | 26 |
| Open-source contributors with merged PRs | 2 | 7 | 20 |

If Month-3 self-host pipeline is <1 open opportunity, the ICP-2 motion is broken — see tripwires.

## Tripwires — what invalidates the plan

These are pre-committed responses, not exception handling.

| Tripwire | Response |
|----------|----------|
| Month 3 MCP install → paying <4% | The MCP free-tier framing is wrong; tighten the funnel by surfacing `verify_claim` in the first tool description |
| Month 4 self-host pipeline empty (<1 open opp) | Phase-2 motion is broken. Founder pauses Phase-1 channels for 6 weeks and dedicates fully to ICP-2 outbound (~40-prospect list) |
| Month 6 no Self-host close | Re-baseline the self-host pricing ($24K v1 floor too high?); or the ICP-2 motion is wrong (need a Big4 / consultancy co-sell) |
| Anthropic ships native citation signing | Lean self-host + customer-controlled keys + 10-year retention harder; reposition page rewrite required within 30 days |
| Founder >55 hr/wk for 3 consecutive weeks | Pause acquisition (channels off, decline podcasts) for 1 week. Consolidate |
| <$15K MRR at Month 9 | Post-mortem. Either pivot (specific direction TBD), reduce scope (sunset to community-maintained), or commit to a 6-month "research project" mode at $0 acquisition spend |
| ICP-1 churn >7%/mo after Month 6 | Tighten Free-tier rate limits to filter abusers; review ICP fit on churned cohort; check whether `verify_claim` accuracy is below customer expectations |

## What breaks first — the founder solo cap

The plan above hits its mechanical limits around **Month 8**:

- 5+ active self-host opportunities + 25+ Pro/Growth onboarding touches/month + 12 hours/week of GTM content + product roadmap + verification-grader accuracy tuning = ~60+ hours/week founder workload.
- Founder cannot sustain this past Month 8 without help.

**Required hires/automation (in this order):**

1. **Month 5–6 — PQL automation.** A simple Workers cron that flags Pro/Growth accounts crossing 50% utilization and drafts a Slack-channel notification with email template. Founder still sends. Saves ~5 hrs/week. Uses existing infra; ~1 day of engineering.
2. **Month 6–7 — Customer support automation.** A docs-search-bot on `docs.unsearch.dev` (uses UnSearch's own API for retrieval — dogfood) answering tier-1 support questions. Saves ~4 hrs/week.
3. **Month 7–9 — First Enterprise / Self-host AE.** 25% commission on closed annual contract value, no base, plus a $1K/closed-deal sourcing bonus. See [Sales playbook](./sales-playbook.md) for the hire spec. Frees ~10 hrs/week of founder time.
4. **Month 9–11 — Founding engineer (full-time).** Not a marketer, not a CS rep. The bottleneck post-$250K MRR is product velocity (verification accuracy + WACZ v2 + BYOC), not GTM.
5. **Month 11–13 — Compliance / partner liaison (fractional).** Manages Big4 partnership cycles and SOC 2 Type II evidence collection.

## Probability bands — being honest

| Outcome at Month 12 | Probability (founder's estimate) | What it requires |
|---------------------|-----------------------------------|------------------|
| $0–$10K MRR | 15% | Verifiable-retrieval thesis is wrong OR regulated-AI startups don't pay infra vendors at this stage |
| $10K–$50K MRR | 25% | MCP wedge works for ICP-1 but self-host motion stalls |
| $50K–$250K MRR | 30% | MCP + 5–10 self-host contracts |
| $250K–$750K MRR | 22% | Plan execution close to spec |
| >$750K MRR | 8% | Step-function event (anchor logo, Big4 partnership lands early, EU AI Act enforcement intensifies) |

These bands are honest about risk. The "good plan execution" outcome lands in the $250K–$750K band — which **includes** the $750K target as a reachable midpoint, not a guaranteed endpoint.

## Cash-out / failure-mode commitment

If MRR is <$15K at Month 9, the founder commits to publishing a post-mortem within 30 days. The repo stays Apache 2.0 and community-maintained; any active customers are migrated to a self-host configuration or refunded if they prefer. This is in the plan up-front because pre-committing to a failure-mode response is the only way to make the rest of the plan honest.

Cross-references:
- See [Market](./market.md) for the citations behind the funnel inputs.
- See [ICP](./icp.md) for the personas the funnel acquires.
- See [Pricing](./pricing.md) for the tier ARPU mix this plan assumes.
- See [GTM](./gtm.md) and [Sales playbook](./sales-playbook.md) for the operational motion that drives the numbers.
