---
title: Jobs to Be Done
description: What each persona hires UnSearch to do, what they currently use, and what triggers a switch
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

JTBD framing forces us to separate *what we sell* from *what the buyer is actually trying to accomplish*. Every UnSearch feature must map to a Job; if a feature doesn't fit, it's the feature that's wrong, not the framing.

## Job format

> When [situation], I want to [motivation], so I can [expected outcome].

Functional, social, and emotional dimensions per Job. See [ICP](./icp) for persona definitions.

## Job 1 — Maya (Persona A)

> **When my Tavily bill creeps over $100 and Nebius keeps emailing about "platform consolidation," I want to swap to a drop-in-compatible search API that I trust will still exist in 12 months, so I can stop worrying about my retrieval layer and ship features.**

- **Current alternative:** Tavily Researcher ($30/mo) or Hybrid ($100/mo).
- **Switching trigger:** Bill hits $100/mo for two consecutive months *or* a Nebius rebrand email arrives.
- **Functional dimension:** Drop-in compatibility — `client.search()` works with one base-URL change.
- **Social dimension:** "We use open source." Visible in our README, defensible in a YC AI Demo Day pitch.
- **Emotional dimension:** Sleep-at-night vendor trust. No "what happens if they get acquired again" thoughts.
- **Outcome metric:** Time to first successful API call <5 minutes; monthly bill <$50.

## Job 2 — Priya (Persona B)

> **When my Exa bill hits $2K/mo and search is now 40% of my COGS, I want to self-host the same-quality search on my own infrastructure, so I can preserve margin and not get fired for choosing the wrong vendor.**

- **Current alternative:** Exa Standard at $7/1K queries, or Tavily Startup at $100/mo capped.
- **Switching trigger:** Retrieval line crosses 25% of customer COGS *or* legal review flags closed-source vendor lock-in.
- **Functional dimension:** Self-host on own Cloudflare account in under 30 minutes, with same code paths as managed.
- **Social dimension:** "We run our own infra" — credible in a Series A pitch, in a security review, in customer trust convos.
- **Emotional dimension:** Control. Optionality. The Apache 2.0 license means we can fork if UnSearch ever disappoints us.
- **Outcome metric:** Predictable monthly bill (variance <10%); zero unplanned migrations; 99.9% effective uptime.

## Job 3 — David (Persona C)

> **When my compliance team audits us, I want a search vendor I can defend in a SOC 2 review with a clear data-flow diagram and a signed DPA, so I can pass the audit without re-architecting our agent.**

- **Current alternative:** Glean (internal knowledge only, doesn't cover open web) + Exa/Tavily (closed source, awkward in security review).
- **Switching trigger:** SOC 2 audit prep *or* procurement rejecting a Glean/Exa renewal quote.
- **Functional dimension:** Self-host inside our VPC/Cloudflare account; auditable code path; signed MSA + DPA; SLA-backed managed option.
- **Social dimension:** Vendor defensibility — "open source, runs in our account, we own the data" is a stronger story than "trust this SaaS vendor."
- **Emotional dimension:** Risk reduction. The buyer's career depends on the vendor not failing the audit.
- **Outcome metric:** Pass SOC 2 audit; renewal lift on year two; <30-day onboarding to first production traffic.

## Anti-JTBDs — what we are explicitly *not* hired for

Naming what we're not hired to do prevents scope creep and keeps the product focused.

- **We are not hired to be Google.** No browser, no consumer UI, no SERP-page aesthetic. If a user wants a search engine, we lose.
- **We are not hired to be a vector database.** Pinecone, Vectorize, Qdrant own that job. We use vectors, we don't sell them.
- **We are not hired to be a foundation model with web tools.** ChatGPT, Claude, Gemini already do that for end-users. We're the layer their *developer customers* call.
- **We are not hired to be Perplexity.** Perplexity owns "AI search for humans." We own "search for agents."
- **We are not hired to be a managed scraper.** Bright Data, Apify, Firecrawl own that. We surface what's findable on the open web; we don't run targeted scraping campaigns.
- **We are not hired to be Glean.** Glean owns "search the inside of your company." We own "search the outside."

If a prospect's question is one of the above, refer them out and keep the conversation short. Saying no is a feature.

## Outcome-metric summary

Every Job has a measurable outcome the buyer judges us by. These should drive product instrumentation in `apps/web/` and the agent observability layer.

| Persona | Outcome metric | Measurement source |
|---------|----------------|---------------------|
| Maya (A) | Time to first API call after signup | Sentry breadcrumb in `/playground` |
| Priya (B) | Monthly bill variance vs forecast | D1 `usage_records` rollup |
| David (C) | SOC 2 audit pass + 30-day prod onboarding | Customer success log + audit attestation |

## How JTBDs constrain product decisions

- Knowledge-graph, fact-verification, topic-monitoring, and deep-research features (currently in beta — see [feature matrix](../feature-matrix)) exist to **deepen** the Persona B job once core search is solved. They are not lead-message material for Persona A.
- Connectors (Slack/Drive/Confluence/Notion/GitHub) are Glean-job territory — explicitly **not** an UnSearch Job. They are deferred indefinitely unless a Persona C contract requires them.
- The Tavily-compatibility wedge (`POST /api/v1/agent/search`) is the single most load-bearing piece of code in the repo for Persona A's Job. Treat it as P0 reliability forever.

Cross-references:
- See [ICP](./icp) for persona definitions.
- See [Value prop](./value-prop) for the pain/gain mapping per Job.
- See [Positioning](./positioning) for how each Job becomes a messaging entry point.
