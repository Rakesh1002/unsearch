---
title: Sales Playbook
description: Founder-led sales loop for Personas B and C, with templates, demo flow, and AE-hire transition
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

This playbook is for **founder-led sales-assist** (months 6–14) and the transition to a commission-only AE (months 14+). Persona A converts entirely self-serve through `apps/web/`; this doc is for everything above $149/mo.

See [ICP](./icp) for persona definitions and [GTM](./gtm) for where leads come from.

## Outreach motion — trigger-based, never spray-and-pray

The funnel above $149/mo is opened by one of four triggers:

| Trigger | Source | Action |
|---------|--------|--------|
| Free/Pro user >50% utilization in last 30 days | PostHog → Slack alert | Founder DM within 24 hours |
| User comments on Tavily/Exa pricing on X or HN | Manual X listening | Founder reply in thread + DM |
| Inbound from `/enterprise` page | Form submission → email | Founder reply within 4 business hours |
| YC W26/S26 cohort posting on Twitter about agent infra | Manual scan, weekly | Cold email referencing the post |

No mass cold-email. Solo founder cannot recover from a deliverability hit.

## Outreach templates

Three email templates, one X DM, one LinkedIn DM. Use as starting points; **always personalize the first sentence** to a specific public artifact (tweet, GitHub comment, blog post).

### Template 1 — Tavily migration

```
Subject: Saw your note on Tavily pricing — quick option

Hey [Name],

Saw your [tweet / GitHub issue / HN comment] about Tavily [pricing /
the Nebius acquisition / rate limits]. I'm building UnSearch — same
API surface as Tavily (drop-in compatible), Apache 2.0, runs on
Cloudflare. About 10× cheaper at your usage band.

If you've got 20 minutes I'll walk you through a migration on your
real queries. If not, here's the migration page:
https://unsearch.dev/migrate-from-tavily

— Rakesh
github.com/Rakesh1002/unsearch
```

### Template 2 — Exa cost pressure

```
Subject: Quick math on your Exa bill

Hey [Name],

I noticed [you / your team] is on Exa for [Project]. At your usage
they recently moved from $5 to $7/1K — that's [estimate]/mo at your
scale.

We're open source (Apache 2.0) and run on Cloudflare. Growth tier
is $49/mo for 100K searches. If the math works, I'll do the
migration with you on a 30-min call.

— Rakesh
```

### Template 3 — Raw inbound (filled out the contact form)

```
Subject: Re: UnSearch enterprise inquiry

Hey [Name],

Thanks for the note. Quick to grab a 30-min call this week —
[3 specific time slots in their TZ]. I'll come ready to talk
through:

1. Your current search volume and what you're paying
2. Self-host vs managed — which fits your team
3. SLA + DPA — what your security review needs

Or if it's easier, send me your top 5 queries and I'll have
benchmarks against your current vendor in 24 hours.

— Rakesh
```

### X DM template

```
Saw your post on [thing]. Building UnSearch — open-source
Tavily alternative on Cloudflare. If you're shopping for
search APIs, happy to do a 20-min walkthrough on your queries.
```

### LinkedIn DM template

```
Hi [Name] — saw [thing they posted / a public project]. I built
UnSearch (open-source search API for AI agents, Tavily-compatible).
If your team is evaluating retrieval options, happy to send the
migration page or hop on a 20-min call.
```

## Demo flow — 30 minutes, structured

| Minutes | Section | What happens |
|---------|---------|--------------|
| 0–5 | Context | Founder asks: stack, current vendor, search volume, biggest pain |
| 5–15 | Live playground walkthrough on **their** use case | Type their queries into `/playground`; show neural search, highlights, fact verification if relevant; copy-as-cURL into Postman to show no magic |
| 15–20 | Pricing | Anchor with median market ($500/100K); show our $49 Growth; let them name the tier they'd buy |
| 20–30 | Q&A + close | Address SLA / self-host / SOC 2 / data residency as raised |

**Always end with:** "Send me your top 5 queries — I'll benchmark UnSearch against [their current vendor] and email results tomorrow." This is the homework that converts "interesting" into "starting trial."

## Pricing conversation script

The founder never quotes a number first. The script is:

1. "What's your monthly volume?" → confirm with usage data if they're already on UnSearch Free/Pro.
2. "What's your bill on [current vendor]?" → let them say it.
3. "Median in the category right now is around $500/mo for 100K searches. Our Growth tier is $49 — same volume, 10× cheaper. Would Growth work, or do you need something custom?"
4. If they push past Scale ($149) volume or ask about SLA/SSO/MSA: "That's where we move into Enterprise. Annual contracts, custom volume, signed MSA + DPA. I'll send you our standard Enterprise terms — when can we get on a call to walk through?"

Operating floor: **do not negotiate Enterprise below $1,000/mo**. Below that, point them at Scale + overage.

## Contract essentials by ACV band

| ACV band | Contract type | Cycle time | Notes |
|----------|---------------|------------|-------|
| Growth / Scale ($49–$149/mo) | Click-through ToS only | <1 hour | Self-serve via Stripe |
| Founder-negotiated $200–$1,000/mo (rare; usually a Scale customer with one custom term) | Click-through ToS + email confirmation of the custom term | 1–3 days | Avoid where possible |
| Enterprise ($1,000+/mo) | MSA + Order Form + DPA | 45–90 days | Use Common Paper or LawTrades templates — do not bespoke-draft |

**MSA template source:** use [Common Paper](https://commonpaper.com/) cloud-services standard agreement, or LawTrades's startup MSA template, with light edits. The first three Enterprise contracts use the same template verbatim to build precedent.

**DPA template source:** Common Paper DPA template (GDPR + CCPA aligned). UnSearch is a Data Processor for customer search queries; data residency to be negotiated per-deal initially, then standardized after the first 5 Enterprise deals.

## Disqualification rules

The founder cannot run a full sales cycle for every prospect. Disqualify aggressively:

- Any prospect requesting a **product feature beyond the published roadmap** → disqualified for the current quarter. Re-engage when the feature ships (or when the founder decides not to ship it).
- Any prospect projecting **>90-day procurement cycle** → disqualify and re-engage in 6 months.
- Any prospect insisting on **bespoke product work** (custom connectors, custom models, dedicated engineering) → disqualify; refer to Glean if internal-knowledge, refer to Bright Data if scraping-led.
- Any prospect **negotiating Enterprise below $1,000/mo** → point at Scale + overage; do not engage.
- Any prospect with a **single-vertical 6-month security review** (legal AI, health AI in regulated verticals) → defer until SOC 2 attestation lands; not month-1–18 work.

## Cycle-time expectations

| Persona | First-touch to signed contract | What kills the cycle |
|---------|-------------------------------|----------------------|
| Persona B (Priya — Seed/A CTO) | 7–21 days | Procurement-shaped review on a $500/mo deal; disqualify |
| Persona C (David — Series B+ buyer) | 45–90 days | Security-review schedule slips; founder follows up weekly |

If a Persona C cycle drags past 90 days with no clear close-out signal, **disqualify and re-engage at month 6**. Sunk-cost discipline is the founder's hardest sales skill.

## CRM and tooling

Lightweight by design:

- **CRM:** Attio free tier or HubSpot free tier. Manual entry. No SDR. No marketing automation.
- **Calendar:** Cal.com — calendly link on `/enterprise` and in DM templates. 30-min slots only.
- **Email:** Founder's primary email; no shared inbox until month 14.
- **Notes:** plain-text notes per deal in Attio/HubSpot. No long-form notion docs.

When the AE comes on board (month 14), the founder migrates 5–10 active deals to the AE; everything before stays with the founder for continuity.

## AE-hire transition (months 14–16)

**Who:** US- or LATAM-based commission-only AE. Sourced from RepVue, the founder's network, or `peoplesourced` Slack groups. SaaS or dev-tool experience preferred; Cloudflare-stack familiarity bonus.

**Comp structure:**
- 30% commission on closed annual contract value, paid on cash receipt.
- No base salary.
- No SDR; AE handles their own outbound from a founder-handed list.
- Equity: small grant (0.1–0.25%) at a one-year cliff after $250K closed ARR.

**Onboarding:**
- Week 1: shadow 3 founder demos.
- Week 2: AE leads demos with founder silent on the call.
- Week 3: AE runs solo demos; founder reviews recordings at the end of the week.
- Month 1: AE owns the top of the Enterprise funnel; founder still closes the first deal solo to set the bar.

**What the AE cannot do unsupervised:**
- Negotiate below the $1K/mo floor.
- Sign an MSA with bespoke terms (DPA terms are negotiable; MSA structure is not).
- Promise feature delivery beyond the published roadmap.

**When to hire a second AE:** when the first AE is **closing >5 deals/quarter and has 10+ active opportunities**. Anything less, the founder is leaving demand on the table that one AE can absorb.

## Quarterly sales review checklist

Run this every 90 days, starting month 6.

- Win rate by source (DM / inbound / partner referral) — kill the worst-performing source.
- Average cycle time per persona — flag any creeping past target.
- Disqualified-prospect count — if it's <20% of the funnel, we're being too soft on disqualification.
- Per-customer touch count from first contact to close — > 8 touches signals a process problem, not a customer problem.
- Lost-deal reasons — look for product gaps that recur 3+ times.

Cross-references:
- See [ICP](./icp) for the personas this playbook sells to.
- See [Pricing](./pricing) for the floor / tier math the script anchors against.
- See [GTM](./gtm) for the channels that feed the funnel.
- See [MRR plan](./mrr-plan) for the deal count this motion must produce per month.
