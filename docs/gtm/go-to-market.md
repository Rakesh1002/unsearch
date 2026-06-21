---
title: Go-to-Market
description: Three-phase motion, channel prioritization, T-14d → T+90d launch runbook
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

The motion is **sequenced**: MCP wedge + OSS flywheel (acquisition) → compliance hook + self-host wins (revenue) → compliance partner motion (ceiling). Channels are prioritized per phase, not run in parallel. Solo founder at 4 hours/day cannot run all channels at once.

See [ICP](./icp.md) for the personas each phase targets and [MRR plan](./mrr-plan.md) for the revenue targets each phase must hit.

## Phase 1 — MCP wedge + OSS flywheel (Months 1–3 · Target $25K MRR)

Primary ICP: **ICP-1 — Priya, regulated-AI startup eng lead.** Distribution surface that beats Anthropic native search at the moment of evaluation: one-command MCP install, free tier, signed envelope on the first response.

### Channels, ranked

1. **MCP registry + Anthropic / OpenAI MCP marketplaces.** The single highest-leverage acquisition surface of 2026. Listed as a **verified retrieval** MCP with `verify_claim` as the headline tool. Free tier 5,000/mo built into the MCP server.
2. **Show HN — end of Month 1.** Single shot. Title: *"Show HN: UnSearch — verifiable web retrieval for AI agents (signed snapshots, MCP-native, Apache-2.0)"*. 9am ET, Tue/Wed, 12-hour founder response window.
3. **Hand-picked outbound to 40 regulated-AI startups.** Loom demo per prospect referencing their specific public artifact (their funding announcement, their HN post about retrieval, their open GitHub repo).
4. **GitHub OSS flywheel.** Prominent README with verifiability hook + 60-second self-host quickstart. Public roadmap (`docs/roadmap.md`). Monthly release notes. Submit to `awesome-mcp-servers`, `awesome-llm-tools`, `awesome-rag` indices.
5. **Webrecorder / Harvard LIL alignment.** Align with WACZ + `wacz-signing` to inherit credibility from the archival community. Sponsor SearXNG upstream (small grant).
6. **Founder X / LinkedIn content.** 1 technical post per weekday on verifiable-retrieval primitives, citation incidents, Article 12 compliance. Specific, technical, no marketing copy.

### Explicitly de-prioritized in Phase 1

- Cold email at scale (founder fit poor; better channels exist).
- Paid ads (low intent for this category).
- Programmatic SEO (slow to compound at this stage).
- Conferences before Month 4 (founder is India-based; travel cost not justified pre-$25K MRR).
- ProductHunt (not the right audience for regulated-AI buyers).
- "Tavily migration" content as the lead message — keep the migration page for SEO continuity but secondary to verifiable-retrieval messaging.

## Phase 2 — Compliance hook + self-host wins (Months 4–9 · Target $250K MRR)

Primary ICP: **ICP-2 — David, regulated-company AI platform director.** Continues ICP-1 acquisition channels. The wedge is the EU AI Act August 2026 enforcement deadline.

### Channels added in Phase 2

1. **EU AI Act content + webinars.** "Article 12 logging for agent retrieval" technical guide. Quarterly webinar with a partner legal-tech consultancy.
2. **Quarterly "Hallucinated Citation Index" report.** Public methodology, open-source eval harness. Drives PR + inbound.
3. **Regulated-AI conference circuit (one per quarter):**
   - LegalGeek US (Month 4)
   - AI4 Health (Month 6)
   - FinRegTech (Month 8)
4. **Outbound to 30 named regulated-AI buyers** — banks, hospital systems, insurance carriers, BigLaw firms — via LinkedIn + Cloudflare-portfolio referrals.
5. **Cloudflare Workers Launchpad relationship.** Get listed as a recommended integration; partner with Cloudflare AEs for portfolio company referrals (now CF Containers GA, this is a real co-sell).
6. **First commission-only AE hire (Month 7–9).** 25% commission on closed self-host ACV, no base, $1K/closed-deal sourcing bonus. Sourced via RepVue or founder network.
7. **Founder podcast tour.** One per month — Latent Space, AI Engineer, MLOps Community Podcast, Software Engineering Daily. Topic: verifiable retrieval, not generic agent infra.
8. **3 customer case studies by Month 9.** One per persona-vertical (legal / medical / fintech).

### Sales motion specifics

See [Sales playbook](./sales-playbook.md) for the detailed motion. Summary:

- Founder closes every self-host deal personally through Month 7.
- ICP-1 cycle: 7–21 days. ICP-2 cycle: 30–90 days (self-host v1) or 60–120 days (self-host v2 with BAA / DPA / SSO).
- Disqualification rule: any feature request beyond the published roadmap = disqualified for current quarter.
- Demo flow: 30 minutes; ends with "send me a real claim + URL, I'll show you the signed envelope and verify result by tomorrow."

## Phase 3 — Compliance partner motion (Months 10–12 · Target $750K MRR)

Primary ICP: ICP-2 expansion via partner channels. ICP-1 acquisition continues passively via MCP + GitHub.

### Channels in Phase 3

1. **Big4 / Tier-1 consultancy partnerships.** Deloitte AI Risk, EY Trusted AI, PwC AI Governance, KPMG AI Risk practices. Co-branded EU AI Act readiness assessments with verifiable retrieval as the technical answer.
2. **NIST AI RMF examples directory submission.** Requires SOC 2 Type I evidence (Month 4); aim for listing by Month 10.
3. **ISO 42001 + SOC 2 Type II + HIPAA BAA readiness.** All three in market-ready state by Month 12; SOC 2 Type II audit underway.
4. **Customer-referral program.** $5K credit per closed self-host deal sourced from existing ICP-1 customer.
5. **AI Engineer Summit talk** (or equivalent flagship conference) — single talk, single table booth, not booth-only.
6. **Pause new top-of-funnel content.** Refocus founder time on enterprise / Big4 close-out work.

### Channels we will not run in Phase 3

- Multiple conferences (one quarter; one flagship).
- Paid acquisition of any kind (the funnel is referral-led + content-led at this stage).
- Outbound SDR motion (cycle time and cost don't match self-host economics for a single AE).
- White-label / closed-source self-host (refuse politely).

## T-14d → T+90d launch runbook

The "launch" is the Show HN post, scheduled for the **end of Month 1** (not Day 0 of the project). The 14 days before are prep; the 90 days after are the Phase-1 ramp.

### T-14d → T-1d prep checklist

| # | Item | Owner | Hours |
|---|------|-------|-------|
| 1 | MCP server published to npm + Anthropic MCP directory; `npx @unsearch/mcp-server` works | Founder | 8 |
| 2 | Hosted API live at `api.unsearch.dev` with signed envelope on every result | Founder | 8 |
| 3 | Dashboard live at `app.unsearch.dev`; API-key issuance writes to D1 | Founder | 4 |
| 4 | Marketing landing at `unsearch.dev` with 60-second `verify_claim` interactive demo | Founder | 4 |
| 5 | "EU AI Act Article 12 compliance" technical guide page live | Founder | 3 |
| 6 | 3 blog posts queued: "Why we built UnSearch", "Signing citations on Cloudflare", "Active-CPU billing for SearXNG" | Founder | 6 |
| 7 | HN account warmed (real comments on other posts, no shilling) | Founder | 1 |
| 8 | Pricing page with comparison table (cited + dated) | Founder | 2 |
| 9 | 40-named-account list for hand-picked outbound | Founder | 3 |
| 10 | Submitted to `awesome-mcp-servers`, `awesome-llm-tools` PRs in flight | Founder | 1 |

Total: ~40 hours over 14 days = 2.9 hours/day, within the 4-hour daily budget with buffer.

### T+0 launch day — Show HN

- **Post time:** 9:00 AM ET, Tuesday or Wednesday (not Monday, not Friday).
- **Title:** `Show HN: UnSearch — verifiable web retrieval for AI agents (signed snapshots, MCP-native, Apache-2.0)`
- **First comment (founder, immediately after post):** technical context — what's shipped (search + extract + verify_claim + audit + MCP), what's in beta (knowledge / topic / research), what's planned (PKI v2 / WACZ v2 / BYOC). No marketing.
- **Response window:** 12 hours, every comment gets a reply.
- **Day-end action:** write the "we got X signups, here's what broke" follow-up draft.

### T+1 → T+30

- Week 1: respond to Show HN trail; ship Google OAuth; publish the "what broke" follow-up post on dev.to; submit to Hacker Newsletter, TLDR newsletter, etc.
- Week 2: MCP directory launch announcement + `r/MachineLearning` post + AMA on the LangChain Discord.
- Week 3: LangChain integration PR merged + announcement; Vercel AI SDK adapter; founder DM intercepts for first 5 paying users (architecture review).
- Week 4: first ICP-1 customer case study (legal-AI startup or medical-RAG, real numbers, signed-envelope screenshot of an actual customer-defended claim).

### T+30 → T+90

- Month 2: EU AI Act guide drives inbound from ICP-2 prospects. First Big4 partnership conversation. First self-host pilot signed (free).
- Month 3: First self-host paid contract close ($24K/yr). Second HN post ("how we sign 1M citations on Cloudflare"). LegalGeek US registration.
- T+90 review: re-baseline ICP-1 funnel vs MRR plan tripwires.

## Content calendar shape

| Cadence | What | Where |
|---------|------|-------|
| Weekly (Tue) | 1 deep blog post (engineering or compliance angle) | unsearch.dev/blog + dev.to crosspost |
| 2× / week | X/LinkedIn thread | Founder accounts |
| Daily (Mon/Wed/Fri) | 1 reply-with-link in regulated-AI Discord / Slack | LegalTech Slack, Health AI Slack, FinTech AI Slack, Anthropic Builders Discord |
| Weekly | GitHub release notes | github.com/Rakesh1002/unsearch |
| Monthly | AMA or community office hour | Discord or X Spaces |
| Quarterly | "Hallucinated Citation Index" report | Public blog + press release |

Time budget: ~12 hours/week. Fits 4 hours/day × 4 days, leaving 1 day for product + 2 days slack.

## Named-account list for ICP-2 outbound — seed

The first 30 ICP-2 names for Months 4–6 founder outbound. Maintained as a private Notion or Airtable list outside the docs. Sourcing methodology (for the founder to extend the list over time):

1. LinkedIn search: "Director" OR "VP" + "AI" + ("regulated" | "compliance") at banks, hospital systems, insurance carriers, BigLaw firms, pharma cos, asset managers.
2. AI4 / FinRegTech / LegalGeek attendee lists.
3. EU AI Act vendor-readiness consortia (e.g., responsible-ai.eu) member companies.
4. Cloudflare Workers Launchpad portfolio cos that have grown into ICP-2.
5. Big4 case studies on AI risk / governance — clients named.

Outreach cadence: 3 personalized DMs/day, Weeks 1–4; 2/day, Weeks 5–12. Personalized (referencing their specific public artifact — a conference talk, a regulator quote, a published AI policy), no template-spray.

## When to pause acquisition

Hard rule: if founder logs >55 hours/week for 3 consecutive weeks, **pause all acquisition channels** (turn off X content, decline podcasts, no new outbound) for 1 week and consolidate. The plan stalls if the founder burns out.

Other tripwires that trigger a GTM re-plan (not just a pause) — see [MRR plan](./mrr-plan.md):

- Month 3 MCP install→paying <4% → tighten free-tier framing; surface `verify_claim` earlier in tool description.
- Month 4 self-host pipeline empty → Phase-2 motion broken; founder pauses Phase-1 channels for 6 weeks and dedicates fully to outbound.
- Anthropic ships native citation signing → reposition page rewrite required within 30 days; lean self-host + customer-controlled keys harder.
- <$15K MRR at Month 9 → write post-mortem; either pivot or sunset to community-maintained.

Cross-references:
- See [ICP](./icp.md) for who each channel reaches.
- See [Sales playbook](./sales-playbook.md) for the motion that converts ICP-1 and ICP-2.
- See [MRR plan](./mrr-plan.md) for the revenue targets each phase must hit.
