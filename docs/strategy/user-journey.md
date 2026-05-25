---
title: User Journey
description: Awareness → activation → retention → expansion, mapped to actual dashboard screens
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

This journey maps to the screens that actually exist in `apps/web/` today, not aspirational ones. Where a stage requires a screen we don't have yet, it's flagged as a friction point with a target ship date.

## Awareness → first screen mapping

| Traffic source | First screen they land on | Why this works |
|----------------|---------------------------|----------------|
| Show HN comment | Homepage hero | Confirms the one-liner under load |
| Tavily-pricing X thread | `/migrate-from-tavily` | High-intent — already shopping |
| MCP directory listing | `/playground` (skip signup until call works) | High-intent — already installing |
| LangChain integration page | `/docs/integrations/langchain` | Confirms it's "real" |
| Tavily GitHub issue DM | Personalized email with migration steps | High-intent — already complained |
| Anthropic Startup directory | Homepage hero | Confirms partner credibility |
| Cloudflare Workers Launchpad | `/for-startups` | Co-positioning with CF |
| GitHub trending | README in repo | Apache 2.0 license is the proof |
| `/r/LocalLLaMA` post | Specific blog post (technical depth) | They want to learn, not buy |

## Activation funnel (the existing dashboard paths)

The actual `apps/web/` routes today (per `apps/web/README.md`):

```
unsearch.dev/
   → /signup (email + password)
   → email verification
   → /dashboard (usage + plan summary)
   → /playground (first search query)
   → /api-keys (copy a key)
   → install SDK + first external API call
```

**Activation metric** — "first external API call (not from `/playground`) within 24 hours of signup."

**Target rate:** 35% (industry top-quartile for dev APIs with a working playground; instrumentation is in PostHog via `NEXT_PUBLIC_POSTHOG_KEY`).

### Stage-by-stage friction inventory

| Stage | Current state | Friction | Mitigation + target ship |
|-------|---------------|----------|--------------------------|
| Signup | Email + password (token in localStorage) | ~20% drop vs. social login baseline | Wire Google OAuth (env keys already in `.env.example`) — **Week 1** |
| Email verify | Required before dashboard access | Adds ~5–10% drop | Make verification non-blocking for `/playground` (verify before first paid action) — **Week 2** |
| `/dashboard` | Usage + plan summary | Empty state on day 0 is dispiriting | Show "Try a search →" CTA pointing at `/playground` — **Week 1** |
| `/playground` | Live search form | No "copy as cURL / TS / Python" buttons | Add language-specific copy buttons → reduces playground→external call drop — **Week 2** |
| `/api-keys` | Create/revoke per-key UI | No labels or environment tags | Add labels (dev/staging/prod) — **Week 4** |
| First external call | SDK install + paste key | Sentry breadcrumb measures the gap | Instrument the time-delta between key creation and first external 200 — **Week 1** (data only, no UX change) |
| Team / Settings | Routes are placeholder | Blocks Persona B onboarding | Ship `/team` and `/settings` — **Month 2** |

### Agent-first signup path (unique to UnSearch — already in schema)

`workers/schema.sql` includes `is_agent_placeholder`, `claim_code`, and `sandbox_expires_at` columns. This enables a journey no competitor has:

1. Agent calls `POST /api/v1/agents/register` with a build-time hint.
2. UnSearch returns a 7-day sandbox key + a `claim_code`.
3. Agent uses the sandbox key for development.
4. Agent prints/emails its human developer with a claim link.
5. Human developer signs up and inherits the usage history.

This is a marketing surface, not a buried feature. It's a one-paragraph PR-grade differentiator on the homepage and in the [Tavily migration page](../migration/from-tavily). Ship the marketing of it in Week 2; it's already in the data model.

## Retention — day-by-day email triggers

Email automation tied to PostHog events. All emails go from `noreply@unsearch.dev` (already configured); reply-to is `support@unsearch.dev`.

| Day | Trigger | Content | Goal |
|-----|---------|---------|------|
| 0 | Email verified | Welcome + MCP server install link + Discord invite | Set "this is alive" tone |
| 1 | No API call yet | "Need help with your first call? Reply to this email." (founder reply) | Founder-led DM intercept |
| 3 | <100 calls | LangChain quickstart link + sample code | Reduce time-to-value |
| 7 | Weekly summary | Usage stats + nearest competitor cost ("you'd have paid $X on Tavily") | Anchor the value |
| 14 | >60% of free quota | Pro upgrade with annual-billing default | Convert the active cohort |
| 30 | Zero calls in 14 days | "Still figuring out search? Free 15-min office hours with the founder." (calendly link) | Save the lapsed cohort |
| 60 | Paying, but utilization >80% | Growth/Scale upgrade nudge with usage math | Tier-ladder |

**Week-1 retention target:** 50% for paying customers, 25% for free.

## Expansion — automatic + sales-led

| From | To | Trigger | Path |
|------|----|----|------|
| Free | Pro | 80% of monthly quota burned | In-product banner + email |
| Pro | Growth | 2 consecutive months >20K searches | Email + banner |
| Growth | Scale | 2 consecutive months >80K searches | Email + banner |
| Scale | Enterprise | Founder DM (no self-serve) | See [Sales playbook](./sales-playbook) |

The Scale → Enterprise transition is **deliberately not self-serve**. Above $149/mo, every customer gets a 30-minute founder call before they pay. This protects the PLG funnel from procurement-led customers who would consume 40 hours of sales cycle for $200 deals, and it sources case-study content.

## Advocacy

Persona A and B advocates become the acquisition engine for the next cohort.

| Trigger | Ask | Reward |
|---------|-----|--------|
| Paying for 60 days, >80% utilization | Public testimonial + GitHub star | Listed as customer logo (with permission) |
| First case-study interview | 30-min recorded conversation | $50 credit + co-marketing |
| Refers a paying Pro/Growth customer | Mention in onboarding | $50 credit each (capped at 5/year) |
| Refers a closed Enterprise customer | Direct intro | $1K credit (see [Sales playbook](./sales-playbook)) |

## Persona-specific journey overlays

The funnel above is Persona A's path. Personas B and C take a hybrid path that splits off at the activation stage.

**Persona B:** the founder sees PostHog activity (utilization >50% on Free or Pro tier) → DMs the user offering a free 30-min architecture session → that call is the activation event, not the dashboard.

**Persona C:** all entry is inbound or partner-sourced (Cloudflare AE intro, Persona B referral). The journey is: intro email → discovery call (30 min) → POC kickoff (signed POC agreement, 14-day timeline) → security review (variable, 14–60 days) → annual contract close. The dashboard plays a supporting role but is not the activation surface.

## Instrumentation checklist

What we measure to know the journey is working — all derived from PostHog (frontend) + Workers Analytics (API) + Sentry (errors):

- Signup → email-verified conversion (target: 80%)
- Email-verified → `/playground` first query (target: 75%)
- `/playground` first query → first external API call (target: 60%)
- External call within 24h of signup (composite activation metric, target: 35%)
- 7-day retention on paying cohort (target: 50%)
- 30-day retention on paying cohort (target: 75% — annual billing is the lever)
- Free → paid conversion at month 1 (target: 4%; 2–5% is the cited industry band — see [Market](./market))

Cross-references:
- See [ICP](./icp) for who is on this journey.
- See [Pricing](./pricing) for the expansion mechanics.
- See [GTM](./gtm) for what brings them to the awareness stage.
- See [MRR plan](./mrr-plan) for the conversion-rate assumptions this journey must hit.
