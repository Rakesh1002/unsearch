---
title: Go-to-Market
description: Three-phase motion, channel prioritization, T-14d → T+90d launch runbook
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

The motion is **sequenced**: PLG (acquisition) → founder-led sales-assist (revenue) → enterprise expansion (ceiling). Channels are prioritized per phase, not run in parallel. Solo founder at 4 hours/day cannot run all channels at once.

See [ICP](./icp) for the personas each phase targets and [MRR plan](./mrr-plan) for the revenue targets each phase must hit.

## Phase 1 — PLG (Months 1–6 · Target $5K MRR)

Primary ICP: **Persona A — Maya the AI-Native Indie.**

### Channels, ranked

1. **Official MCP server in the Anthropic MCP registry.** The highest-leverage single artifact of the year. 97M monthly SDK downloads + 10K+ public servers = a distribution surface larger than npm for our category.
2. **`/migrate-from-tavily` SEO + content.** Existing page at `docs/migration/from-tavily.md` — polish it, add a "Migrate in 5 minutes" headline, copy-paste config diff, CTA to playground.
3. **LangChain + Vercel AI SDK retriever PRs.** Table stakes — every competitor has these. We need them merged before HN launch.
4. **Founder X/Twitter content.** 1 technical post per weekday. Specific, technical, no marketing copy.
5. **`/r/LocalLLaMA` weekly value posts.** Technical depth, no marketing. Reddit smells AI marketing copy immediately.
6. **Show HN — month 2.** Single shot, once 50 paying users exist for credible "X startups already on UnSearch" copy. 9am ET, Tue/Wed/Thu, 12-hour founder response window.
7. **GitHub releases — weekly.** Compounding star count is a channel. Release notes are public.

### Explicitly de-prioritized in Phase 1

- Cold email at scale (founder fit poor; better channels exist)
- Paid X/Twitter ads (low intent for this category)
- Programmatic SEO content farms (slow to compound, low quality)
- Conferences (founder is India-based, travel cost not justified pre-$25K MRR)
- Cold LinkedIn (wrong persona)
- Product Hunt (save for month 8, only if metrics warrant)

## Phase 2 — Sales-assist (Months 6–18 · Target $50K MRR)

Primary ICP: **Persona B — Priya the AI-Native CTO.** Continues Persona A acquisition channels.

### Channels added in Phase 2

1. **Founder DMs to PQL-flagged users.** Any Pro/Growth user crossing >50% utilization gets a personal DM offering a free 30-minute architecture session. PostHog event → Slack channel → founder DM the same day.
2. **Outbound to identifiable Tavily customers.** ~300 names from public case studies, conference talks, GitHub repos that use Tavily APIs.
3. **Anthropic Startup Program partner application.** Once accepted, our listing in the directory becomes a passive inbound source for Persona B.
4. **OpenAI startup directory submission.**
5. **Book of YC outreach.** Identify ~50 W26 + S26 AI-cohort companies; cold email with the YC affiliation as the opener.
6. **Cloudflare Workers Launchpad relationship.** Get listed as a recommended integration; partner with Cloudflare AEs for portfolio company referrals.
7. **Founder podcast tour.** One per month — Latent Space, AI Engineer, MLOps Community Podcast, Software Engineering Daily.
8. **Case studies — three by month 9.** One per persona-vertical (legal/sales/dev tools).

### Sales motion specifics

See [Sales playbook](./sales-playbook) for the detailed motion. Summary:

- Founder closes every deal personally through month 14.
- Cycle time: Persona B 7–21 days; Persona C 45–90 days.
- Disqualification rule: any feature request beyond the published roadmap = disqualified for current quarter.
- Demo flow: 30 minutes, ends with "send me your top 5 queries, I'll benchmark them by tomorrow."

## Phase 3 — Enterprise expansion (Months 18–24 · Target $100K MRR)

Primary ICP: **Persona C — David the Series B+ Buyer.**

### Channels in Phase 3

1. **First commission-only AE hire (months 14–16).** 30% commission on closed annual contract value, no base. Founder remains on first 3 demos to transfer script. Sourced via RepVue or founder network.
2. **Customer-referral program.** $1K credit per closed Enterprise deal sourced from an existing Persona B customer.
3. **Cloudflare partner co-sell motion.** Formal partner agreement; Cloudflare AEs earn spiff for referring customers running on Workers.
4. **Single annual conference — AI Engineer Summit.** Founder talk + table booth, not a booth-only sponsorship.
5. **Pause new content marketing.** Refocus founder time on enterprise close-out work.

### Channels we will not run in Phase 3

- Booth at any conference besides AI Engineer Summit.
- Paid acquisition of any kind (the funnel is referral-led at this stage).
- Outbound SDR motion (cycle time and cost don't match Persona C economics for a single AE).

## T-14d → T+90d launch runbook

The "launch" is the Show HN post, scheduled for the **end of Month 1** (not Day 0 of the project). The 14 days before are prep; the 90 days after are the Phase-1 PLG ramp.

### T-14d → T-1d prep checklist

| # | Item | Owner | Hours |
|---|------|-------|-------|
| 1 | `/migrate-from-tavily` polished (headline + 3-line diff + CTA) | Founder | 4 |
| 2 | Python SDK published to PyPI as `unsearch` | Founder | 6 |
| 3 | MCP server published to npm + submitted to Anthropic MCP directory | Founder | 4 |
| 4 | LangChain integration PR open against `langchain-community` | Founder | 3 |
| 5 | Demo video <90s, hosted on the homepage | Founder | 2 |
| 6 | 3 blog posts queued (`Why we built UnSearch`, `Migrating from Tavily in 5 min`, `Cost math at 100K searches`) | Founder | 6 |
| 7 | HN account warmed (real comments on other posts, no shilling) | Founder | 1 |
| 8 | Homepage hero rewritten around the one-liner from [positioning](./positioning) | Founder | 2 |
| 9 | Pricing-comparison table on `/pricing` (sourced + dated) | Founder | 2 |
| 10 | 20-named-account DM list compiled from Tavily GitHub issues + Twitter | Founder | 2 |

Total: ~32 hours over 14 days = 2.3 hours/day average, within the 4-hour daily budget with buffer.

### T+0 launch day — Show HN

- **Post time:** 9:00 AM ET, Tuesday or Wednesday (not Monday, not Friday).
- **Title:** `Show HN: UnSearch – open-source Tavily alternative on Cloudflare ($49 vs $500/mo)`
- **First comment (founder, immediately after post):** technical context — what's shipped, what's in beta, what's planned. No marketing.
- **Response window:** 12 hours, every comment gets a reply.
- **Day-end action:** write the "we got X signups, here's what broke" follow-up draft.

### T+1 → T+30

- Week 1: respond to Show HN trail; ship Google OAuth (env keys are in `.env.example`); publish the "what broke" follow-up post on dev.to.
- Week 2: MCP directory launch announcement + `/r/LocalLLaMA` post + AMA on the LangChain Discord.
- Week 3: LangChain integration PR merged + announcement on the LangChain Discord + dev.to crosspost.
- Week 4: first Tavily-migration case study (single named customer, real numbers, before/after billing).

### T+30 → T+90

- Month 2: Python SDK launch + "I rewrote it in Python" technical post; one paying-customer interview content piece; first sponsored issue on a popular agent OSS repo; second blog post on cost math.
- Month 3: LlamaIndex retriever + Vercel AI SDK adapter ship; second HN post (different angle — e.g., "Scaling X to Y RPS on Cloudflare"); first Persona B founder-DM closes.

## Content calendar shape

| Cadence | What | Where |
|---------|------|-------|
| Weekly (Tue) | 1 deep blog post | unsearch.dev/blog + dev.to crosspost |
| 2× / week | X/Twitter thread | Founder X account |
| Daily (Mon/Wed/Fri) | 1 reply-with-link in an agent Discord | LangChain, MCP, Anthropic Builders, LlamaIndex |
| Weekly | GitHub release notes | github.com/Rakesh1002/unsearch |
| Monthly | AMA or community office hour | Discord or X Spaces |

Time budget: ~12 hours/week. Fits 4 hours/day × 4 days, leaving 1 day for product + 2 days slack.

## Named-account DM list — seed

The first 20 names for week-1 founder outbound. Pulled from Tavily GitHub issues, X mentions of "Tavily pricing", and LinkedIn employees of Tavily-using startups. Maintained as a private Notion or Airtable list outside the docs.

Sourcing methodology (for the founder to extend the list over time):

1. Read [github.com/tavily-ai](https://github.com/tavily-ai) issue authors of any pricing/limit complaint in the last 6 months.
2. X/Twitter search for "Tavily pricing", "Tavily expensive", "Exa pricing" — capture handles with "AI" or "agent" in bio.
3. LinkedIn search for "uses Tavily" or "Tavily customer" — capture mid-level engineers at AI startups.
4. Y Combinator W26/S26 AI companies on the YC company directory — capture CTOs.

Outreach cadence: 5 DMs/day, week 1; 3 DMs/day, weeks 2–4. Personalized (referencing the public complaint), no template-spray.

## When to pause acquisition

Hard rule: if founder logs >55 hours/week for 3 consecutive weeks, **pause all acquisition channels** (turn off X content, decline podcasts, no new outbound) for 1 week and consolidate. The plan stalls if the founder burns out.

Other tripwires that trigger a GTM re-plan (not just a pause) — see [MRR plan](./mrr-plan):

- Month 4 free→paid <2% → ICP targeting is wrong; rerun [ICP](./icp).
- Month 6 Enterprise pipeline empty → Phase-2 motion is broken; founder pauses Phase-1 channels for 6 weeks and dedicates fully to outbound.
- Cloudflare AI Search GA → lean [positioning](./positioning) harder into self-host; explore CF partner co-positioning.
- <$3K MRR at month 9 → write post-mortem; either pivot or sunset to community-maintained.

Cross-references:
- See [ICP](./icp) for who each channel reaches.
- See [Sales playbook](./sales-playbook) for the motion that converts Persona B and C.
- See [MRR plan](./mrr-plan) for the revenue targets each phase must hit.
