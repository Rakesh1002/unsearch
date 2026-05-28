---
title: User Journey
description: Awareness → activation → retention → expansion, mapped to actual MCP install + dashboard screens
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

This journey maps to the surfaces that actually exist in v1: the MCP install (lead), the dashboard (`apps/web/`), and the self-host deployment flow. Where a stage requires a screen we don't have yet, it's flagged as a friction point with a target ship date.

## Awareness → first surface mapping

The MCP-first reposition changes the lead surface from "homepage hero" to "MCP install command" for most traffic. The dashboard exists but is supporting, not lead.

| Traffic source | First surface they touch | Why this works |
|----------------|---------------------------|----------------|
| MCP registry listing | `claude mcp add unsearch` (no signup) | Zero-friction evaluation; lifetime free tier built-in |
| Show HN comment thread | `unsearch.dev` landing → 60-second `verify_claim` interactive demo → MCP install CTA | Confirms the wedge under load; demo is the proof |
| EU AI Act content piece | `unsearch.dev/eu-ai-act` → self-host architecture diagram | High-intent ICP-2 — already compliance-shopping |
| Legal-AI / medical-RAG outbound DM | Personalized 90-second Loom + `unsearch.dev` landing | High-intent ICP-1 — pre-qualified |
| `awesome-mcp-servers` listing | MCP install → first tool call | High-intent — already integrating MCPs |
| LangChain / Vercel AI SDK integration page | `apps/sdk-llamaindex` README + landing | Confirms it's "real" |
| GitHub trending / search | Repo README in browser | Apache 2.0 + signed-envelope screenshot is the proof |
| Webrecorder community thread | `unsearch.dev/for-research` → free-tier signup | Aligns with ICP-3 mental model |
| Anthropic MCP marketplace | Verified-retrieval listing → install | Highest-intent path |

## Activation funnel

Activation in the verifiable-retrieval frame is **"first signed verified result"** — not "first API call." That happens fastest via MCP.

### Path A — MCP install (the lead path)

```
MCP registry / awesome-mcp-servers / claude mcp add unsearch
   → npx @unsearch/mcp-server starts locally
   → Free tier API key auto-issued on first use (no signup)
   → First `search` call returns signed envelope
   → User asks Claude "verify this claim against this source"
   → First `verify_claim` returns evidence spans — ACTIVATION EVENT
```

**Activation metric:** first `verify_claim` call within 24 hours of first `search` call.
**Target rate:** 50% (MCP users self-select for agent-grounding intent).
**Instrumentation:** MCP server telemetry to PostHog with anonymized key ID.

### Path B — Dashboard signup (the supporting path)

```
unsearch.dev/
   → /signup (email + password, or Google OAuth)
   → email verification (non-blocking for /playground)
   → /dashboard (usage + plan summary)
   → /playground (first search query + signed envelope display)
   → /verify (paste claim + URL, see live verification)
   → /api-keys (copy a key)
   → install SDK + first external API call
```

**Activation metric:** first external `verify_claim` call within 24 hours of signup.
**Target rate:** 30% (lower than MCP path; signup adds friction).

### Stage-by-stage friction inventory

| Stage | Current state (as of 2026-05-28) | Friction | Mitigation + target ship |
|-------|-----------------------------------|----------|--------------------------|
| MCP install | `npx @unsearch/mcp-server` (will ship Week 3 per `~/.claude/plans/...`) | None target | Ship + submit to registry by Week 3 — **P0** |
| First MCP tool call | Returns signed envelope | None | n/a |
| First `verify_claim` MCP call | Live verification result | None target after Week 2 ship | Ship `verify/claim` endpoint Week 2 — **P0** |
| Dashboard signup | Email + password (localStorage JWT) | ~20% drop vs social-login baseline | Wire Google OAuth (env keys already in `.env.example`) — **Week 4** |
| Email verify | Required before dashboard access | Adds ~5–10% drop | Make verification non-blocking for `/playground` (verify before first paid action) — **Week 4** |
| `/dashboard` | Usage + plan summary | Empty state on day 0 is dispiriting | Show "Run your first verification →" CTA pointing at `/verify` — **Week 3** |
| `/playground` | Live search form | No signed-envelope display on results | Surface envelope `sha256`, snapshot link, "Verify a claim" inline button — **Week 3** |
| `/verify` | New page (will ship Week 2) | First-time UX needs to be obvious | Pre-fill with example claim + URL; show evidence-span highlight on first result — **Week 2** |
| `/audit` | New audit-log view (will ship Week 2) | First-time UX | Pre-fill with recent activity; "Download WACZ" link per entry — **Week 2** |
| `/api-keys` | Create/revoke per-key UI | No labels or environment tags | Add labels (dev / staging / prod) — **Month 2** |
| First external call | SDK install + paste key | Sentry breadcrumb measures the gap | Instrument the time-delta between key creation and first external 200 — **Week 3** |
| `/team` and `/settings` | Routes are placeholder | Blocks ICP-2 onboarding | Ship — **Month 2** |
| Self-host wizard | New surface (planned Month 2) | Customers want a guided `wrangler deploy` | `/deploy` page with copy-paste env block + `wrangler login` flow — **Month 2** |

### Agent-first signup path

`workers/schema.sql` includes `is_agent_placeholder`, `claim_code`, and `sandbox_expires_at` columns. This enables an agent-first journey:

1. Agent calls MCP server first (no human in the loop).
2. MCP server returns a 7-day sandbox key + a `claim_code`.
3. Agent uses the sandbox key for development.
4. Agent prints/emails its human developer with a claim link.
5. Human developer signs up and inherits the usage history + audit log.

This is a marketing surface, not a buried feature — it's the one-paragraph differentiator that says "UnSearch was designed agent-first, not retrofitted." Ship the marketing of it in Week 4.

## Retention — day-by-day email triggers

Email automation tied to PostHog events. All emails go from `noreply@unsearch.dev` (already configured); reply-to is `support@unsearch.dev`.

| Day | Trigger | Content | Goal |
|-----|---------|---------|------|
| 0 | MCP install OR email verified | Welcome + 60-second `verify_claim` demo link + Discord invite | Set "this is alive" tone |
| 1 | <5 `verify_claim` calls | "Here's how regulated-AI teams use `verify_claim` — reply with a real claim and I'll send back a signed verification by tomorrow." (founder reply) | Founder-led DM intercept |
| 3 | <100 calls total | LangGraph + LlamaIndex quickstart link + sample code | Reduce time-to-value |
| 7 | Weekly summary | Usage stats + "you signed X citations this week; if your customer asks for any of them, here's the audit-log link" | Anchor the value |
| 14 | >60% of free quota | Pro upgrade with annual-billing default | Convert the active cohort |
| 30 | Zero calls in 14 days | "Did the wedge land? Free 15-min office hours with the founder." (calendly link) | Save the lapsed cohort |
| 60 | Paying, but utilization >80% | Growth/Scale upgrade nudge with usage math | Tier-ladder |
| 60 | Paying, EU-domiciled, no self-host inquiry | "EU AI Act August 2026 — happy to walk through self-host posture for your perimeter." | Convert to Self-host |

**Week-1 retention target:** 60% for paying customers, 35% for free.

## Expansion — automatic + sales-led

| From | To | Trigger | Path |
|------|----|----|------|
| Free | Pro | 80% of monthly quota burned (any of: searches, snapshots, verifications) | In-product banner + email |
| Pro | Growth | 2 consecutive months >20K searches OR >500 verifications | Email + banner |
| Growth | Scale | 2 consecutive months >80K searches OR >5K verifications | Email + banner |
| Scale | Self-host v1 | Customer asks about data residency, compliance audit, or specific BAA / DPA needs | Founder DM (no self-serve above this point) |
| Self-host v1 | Self-host v2 | At renewal, customer has SOC 2 evidence needs OR a BAA requirement OR an SLA breach concern | Founder + AE upsell |
| Self-host v2 | Custom enterprise | Multi-region or multi-cloud requirements emerge | Custom contract via [Sales playbook](./sales-playbook.md) |

The Scale → Self-host transition is **deliberately not self-serve**. Above $149/mo hosted, every customer gets a 30-minute founder call before paying any larger contract. This protects the PLG funnel from procurement-led customers who would consume 40 hours of sales cycle for a $200 deal, and it sources case-study content.

## Advocacy

ICP-1 and ICP-3 advocates become the acquisition engine for the next cohort.

| Trigger | Ask | Reward |
|---------|-----|--------|
| Paying for 60 days, >80% utilization | Public testimonial + GitHub star | Listed as customer logo (with permission) |
| First case-study interview | 30-min recorded conversation about a defended customer claim | $100 credit + co-marketing |
| Refers a paying Pro/Growth customer | Mention in onboarding | $100 credit each (capped at 10/year) |
| Refers a closed Self-host customer | Direct intro | $5K credit per closed deal (see [Sales playbook](./sales-playbook.md)) |
| ICP-3 publishes a piece using UnSearch-signed snapshots | Public testimonial + link from `/for-research` | Continued Free or Growth-tier grant |

## Persona-specific journey overlays

The funnel above is ICP-1's path. ICP-2 and ICP-3 take hybrid paths.

**ICP-2:** all entry is inbound (EU AI Act content), partner-sourced (Cloudflare AE intro, Big4 referral), or hand-picked outbound. The journey is: intro email → discovery call (30 min) → POC kickoff (signed POC agreement, 14–21 day timeline) → security review (variable, 30–60 days) → annual self-host contract close. The dashboard plays a supporting role but is not the activation surface; the self-host `wrangler deploy` flow + the audit-log replay are.

**ICP-3:** journey is MCP install → first signed snapshot → integration into their publication workflow → WACZ export. Free tier indefinitely is the default; conversion to Pro at $19/mo happens when a small newsroom team grows past the Free quota.

## Instrumentation checklist

What we measure to know the journey is working — all derived from PostHog (frontend) + Workers Observability (API) + MCP server telemetry (anonymized) + Sentry (errors):

- MCP install → first `verify_claim` call (target: 50% within 24h).
- Signup → email-verified conversion (target: 80%).
- Email-verified → `/verify` first call (target: 65%).
- `/verify` first call → first external API call (target: 60%).
- External `verify_claim` call within 24h of signup or MCP install (composite activation metric, target: 35% blended).
- 7-day retention on paying cohort (target: 60%).
- 30-day retention on paying cohort (target: 80% — annual billing is the lever).
- Free → paid conversion at Month 1 (target: 8% blended; 6–10% is the realistic band given sharper pain).

Cross-references:
- See [ICP](./icp.md) for who is on this journey.
- See [Pricing](./pricing.md) for the expansion mechanics.
- See [GTM](./gtm.md) for what brings them to the awareness stage.
- See [MRR plan](./mrr-plan.md) for the conversion-rate assumptions this journey must hit.
