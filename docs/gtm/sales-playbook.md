---
title: Sales Playbook
description: Founder-led sales loop for ICP-1 and ICP-2 (self-host), with templates, demo flow, and AE-hire transition
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

This playbook is for **founder-led sales** (Months 1–7) and the transition to a commission-only AE (Months 7+). ICP-1 below Scale tier converts entirely self-serve through `apps/web/` and the MCP install; this doc is for everything above ($149/mo hosted + every self-host deal).

See [ICP](./icp.md) for persona definitions and [GTM](./gtm.md) for where leads come from.

## Outreach motion — trigger-based, never spray-and-pray

The funnel above $149/mo (and every self-host deal) is opened by one of five triggers:

| Trigger | Source | Action |
|---------|--------|--------|
| Pro/Growth user >50% utilization in last 30 days | PostHog → Slack alert | Founder DM within 24 hours |
| MCP install with >100 verified searches in first week | MCP server telemetry → Slack alert | Founder DM with "I noticed you ran 100 verifications — happy to do a 30-min architecture review" |
| ICP-1 prospect publicly asks about retrieval grounding | Manual X / LinkedIn / HN listening | Founder reply in thread + DM |
| Inbound from `/eu-ai-act` page | Form submission → email | Founder reply within 4 business hours |
| Inbound from a hand-picked ICP-2 outbound DM | LinkedIn + email response | Founder reply within 24 hours |

No mass cold-email. Solo founder cannot recover from a deliverability hit.

## Outreach templates

Four email templates, one X DM, one LinkedIn DM. Use as starting points; **always personalize the first sentence** to a specific public artifact (tweet, GitHub comment, blog post, conference talk, press release).

### Template 1 — ICP-1, regulated-AI startup (legal / medical / fintech)

```
Subject: Citation grounding for [their product]

Hey [Name],

Saw your [tweet / blog post / GitHub repo] about [their vertical
AI product]. Two questions you may already be solving — feel free
to ignore if so:

1) When a customer asks "what did the agent see?" weeks after the
   answer was generated, can you re-fetch the exact bytes?
2) When your legal counsel asks about EU AI Act Article 12
   provenance retention, what do you point them at?

I'm building UnSearch — Apache-2.0 verifiable retrieval for AI
agents. Every search returns a signed citation envelope, a
content-addressed snapshot, and a `verify_claim` endpoint. MCP
install in 60 seconds.

Happy to do a 20-min walkthrough on your real customer questions.
Or just kick the tires: `claude mcp add unsearch`.

— Rakesh
github.com/Rakesh1002/unsearch
```

### Template 2 — ICP-2, regulated-company AI platform director

```
Subject: Verifiable retrieval for [their team's] AI program

Hey [Name],

[Specific reference to their public artifact — conference talk,
quoted statement, AI policy, press release.]

If your team is shipping LLM features ahead of the EU AI Act
August 2026 deadline, here's a concrete data point: Article 12
requires automatic event logging over the system's lifetime, with
provenance documentation explicitly required and 10-year retention.

I built UnSearch — Apache-2.0 verifiable web retrieval. Runs on
your own Cloudflare account. Customer-controlled signing keys.
10-year audit-log retention available on self-host. WACZ-aligned
envelope so your auditor can replay any retrieval months later.

20-min call to walk through the architecture? Or, if it's easier,
I can send the deployment guide and a sample audit-log replay.

— Rakesh
unsearch.dev/eu-ai-act
```

### Template 3 — Inbound (filled out the `/eu-ai-act` form or contact form)

```
Subject: Re: UnSearch inquiry — [their company]

Hey [Name],

Thanks for the note. Quick to grab a 30-min call this week —
[3 specific time slots in their TZ]. I'll come ready to talk
through:

1. Your current retrieval / RAG architecture and what audit
   evidence your compliance team expects
2. Self-host on your own Cloudflare account vs hosted with
   signed BAA / DPA
3. EU AI Act Article 12 logging — what the regulator-replay
   path looks like in UnSearch

Or if it's easier, send me a real claim + source URL from your
production agent and I'll send a signed-envelope verification
demo by tomorrow.

— Rakesh
```

### Template 4 — ICP-3, citation-integrity research / newsroom

```
Subject: WACZ-aligned signed snapshots for [their project]

Hey [Name],

Saw your work on [retraction-tracking / fact-check infra / 
academic-integrity tool]. UnSearch ships a free tier of
verifiable retrieval — signed citation envelope + WACZ-exportable
snapshot per result. Aligned with the Webrecorder Auth spec.

Free tier covers individual researcher / small newsroom workflow.
Happy to set up a complimentary Growth-tier grant if your project
needs more headroom — we want what you're building to exist.

— Rakesh
github.com/Rakesh1002/unsearch
```

### X DM template

```
Saw your post on [thing]. Built UnSearch — Apache-2.0 verifiable
web retrieval for AI agents. Signed citation envelope per result;
MCP-native; self-hostable on Cloudflare. If you're shopping for
retrieval that holds up under audit, happy to do a 20-min
walkthrough.
```

### LinkedIn DM template

```
Hi [Name] — saw [specific public artifact]. Building UnSearch
(Apache-2.0 verifiable retrieval for AI agents). If your team is
evaluating retrieval primitives ahead of the EU AI Act deadline,
happy to send the architecture overview or hop on a 20-min call.
```

## Demo flow — 30 minutes, structured

| Minutes | Section | What happens |
|---------|---------|--------------|
| 0–5 | Context | Founder asks: stack, current retrieval vendor, compliance posture, EU AI Act timeline, biggest pain |
| 5–15 | Live MCP + dashboard walkthrough on **their** use case | Run their real query through `claude mcp add unsearch` + `verify_claim` on a real claim from their product; show the signed envelope; show the audit log replay |
| 15–22 | Self-host vs hosted decision | Anchor with their security/data-residency constraints; show the `wrangler deploy` self-host flow |
| 22–30 | Pricing + close | For ICP-1: Growth tier $49 + Self-host v1 $24K/yr if they need it. For ICP-2: Self-host v1 $24K/yr or v2 $99K/yr. Let them name the tier. End with "send me a real claim + URL, I'll come back tomorrow with benchmarks against [their current vendor]." |

**Always end with:** a concrete homework that proves the wedge — "send me a real claim + URL, I'll send back a signed envelope, a verification result, and a WACZ snapshot tomorrow." This is the homework that converts "interesting" into "starting pilot."

## Pricing conversation script

The founder never quotes a number first. The script is:

1. "What's your monthly retrieval volume?" → confirm with usage data if they're already on UnSearch Free/Pro.
2. "What's your team paying today across search + extraction + snapshot infra?" → let them say it. Most ICP-1 buyers have a $1.5–4K/mo combined bill they've never added up.
3. "Median retrieval-API cost in the agent category is around $500/mo for 100K searches; that's *unsigned*. UnSearch Growth at $49/mo is 100K signed + verified + replayable. Would Growth work, or do you need self-host?"
4. If they push to self-host (ICP-2 signal): "Self-host runs on your own Cloudflare account in <30 minutes. v1 is $24K/yr, includes deployment support + monthly updates. v2 at $99K/yr adds SOC 2 evidence + BAA + dedicated co-management. When can we get on a call to walk through?"

Operating floors:
- **Do not negotiate Self-host v1 below $18K/yr.**
- **Do not negotiate Self-host v2 below $75K/yr.**
- **Do not negotiate Enterprise (hosted) below $1,500/mo.**

Below those, point at hosted Scale + overage and walk away politely.

## Contract essentials by ACV band

| ACV band | Contract type | Cycle time | Notes |
|----------|---------------|------------|-------|
| Growth / Scale ($49–$149/mo) | Click-through ToS only | <1 hour | Self-serve via Stripe |
| Self-host v1 ($24K/yr) | MSA + Order Form + DPA | 30–60 days | Use Common Paper or LawTrades templates |
| Self-host v2 ($99K/yr) | MSA + Order Form + DPA + BAA + custom SLA addendum | 60–120 days | Includes a security review questionnaire; respond from `docs/SECURITY.md` baseline |
| Enterprise (hosted) ($1,500+/mo) | MSA + Order Form + DPA + (BAA if healthcare) | 45–90 days | Same template family as Self-host v1 |

**MSA template source:** [Common Paper](https://commonpaper.com/) cloud-services standard agreement, or LawTrades's startup MSA template, with light edits. The first three contracts use the same template verbatim to build precedent.

**DPA template source:** Common Paper DPA template (GDPR + CCPA aligned). UnSearch is a Data Processor for customer queries; for self-host customers, UnSearch is a Sub-processor only for support engagements, which makes the DPA conversation easier.

**BAA template:** Drafted on first healthcare deal; reused thereafter.

## Disqualification rules

The founder cannot run a full sales cycle for every prospect. Disqualify aggressively:

- Any prospect requesting a **product feature beyond the published roadmap** → disqualified for the current quarter. Re-engage when the feature ships (or when the founder decides not to ship it).
- Any prospect projecting **>120-day procurement cycle on Self-host v2** → disqualify and re-engage in 6 months.
- Any prospect insisting on **bespoke product work** (custom connectors, custom models, dedicated engineering) → disqualify; refer to Glean if internal-knowledge, refer to Bright Data if scraping-led.
- Any prospect **negotiating Self-host v1 below $18K/yr** → point at Scale + overage; do not engage.
- Any prospect **requesting white-label or closed-source self-host** → refuse politely; UnSearch is Apache 2.0.
- Any prospect with a **multi-stakeholder buying committee but no executive sponsor** → defer until they identify one.

## Cycle-time expectations

| Persona | First-touch to signed contract | What kills the cycle |
|---------|-------------------------------|----------------------|
| ICP-1 (Priya — hosted Pro/Growth) | 7 days (self-serve, but with founder onboarding intercept for Growth+) | Free-tier user with no real production need |
| ICP-1 (Priya — Self-host v1) | 30–60 days | Procurement-shaped review on a $1K/mo hosted deal — disqualify and offer Scale instead |
| ICP-2 (David — Self-host v1) | 30–90 days | Compliance officer not in initial conversation — re-engage when they are |
| ICP-2 (David — Self-host v2 with BAA) | 60–120 days | Security review schedule slips; founder follows up weekly |
| Enterprise (hosted) | 45–90 days | Buyer wants hosted but cannot justify data leaving perimeter — convert to Self-host or disqualify |

If an ICP-2 cycle drags past 120 days with no clear close-out signal, **disqualify and re-engage at Month 6**. Sunk-cost discipline is the founder's hardest sales skill.

## CRM and tooling

Lightweight by design:

- **CRM:** Attio free tier or HubSpot free tier. Manual entry. No SDR. No marketing automation.
- **Calendar:** Cal.com — calendly link on `/eu-ai-act` and in DM templates. 30-min slots only.
- **Email:** Founder's primary email; no shared inbox until Month 8.
- **Notes:** plain-text notes per deal in Attio/HubSpot. No long-form notion docs.
- **Doc-sharing:** Signed PDFs in customer's preferred storage; no third-party DocuSign markup beyond signature.

When the AE comes on board (Month 7–9), the founder migrates 5–10 active deals to the AE; everything before stays with the founder for continuity.

## AE-hire transition (Months 7–9)

**Who:** US- or LATAM-based commission-only AE. Sourced from RepVue, the founder's network, or `peoplesourced` Slack groups. Prefer experience selling regulated SaaS (legal tech, fintech compliance, health IT) over generic dev-tool experience; Cloudflare-stack familiarity bonus.

**Comp structure:**
- 25% commission on closed annual contract value (self-host or Enterprise), paid on cash receipt.
- $1K sourcing bonus per closed deal sourced solely by AE.
- No base salary in Year 1.
- No SDR; AE handles their own outbound from a founder-handed list.
- Equity: small grant (0.1–0.25%) at a one-year cliff after $250K closed ARR.

**Onboarding:**
- Week 1: shadow 3 founder demos.
- Week 2: AE leads demos with founder silent on the call.
- Week 3: AE runs solo demos; founder reviews recordings at the end of the week.
- Month 1: AE owns the top of the self-host funnel; founder still closes the first AE-sourced deal solo to set the bar.

**What the AE cannot do unsupervised:**
- Negotiate below the $18K (v1) / $75K (v2) floors.
- Sign an MSA with bespoke terms (DPA terms are negotiable; MSA structure is not).
- Promise feature delivery beyond the published roadmap.
- Sign a white-label or closed-source contract (refuse, escalate to founder).

**When to hire a second AE:** when the first AE is **closing >4 self-host deals/quarter and has 12+ active opportunities**. Anything less, the founder is leaving demand on the table that one AE can absorb.

## Quarterly sales review checklist

Run this every 90 days, starting Month 4.

- Win rate by source (DM / inbound / partner referral) — kill the worst-performing source.
- Average cycle time per persona — flag any creeping past target.
- Disqualified-prospect count — if it's <20% of the funnel, we're being too soft on disqualification.
- Per-customer touch count from first contact to close — > 10 touches on a self-host deal signals a process problem.
- Lost-deal reasons — look for product gaps that recur 3+ times. If "no SSO yet" is a 3+ reason, prioritize SSO.
- Big4 / consultancy partnership status — at least 1 active conversation by Month 8.

Cross-references:
- See [ICP](./icp.md) for the personas this playbook sells to.
- See [Pricing](./pricing.md) for the floor / tier math the script anchors against.
- See [GTM](./gtm.md) for the channels that feed the funnel.
- See [MRR plan](./mrr-plan.md) for the deal count this motion must produce per month.
