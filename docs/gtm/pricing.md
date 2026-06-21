---
title: Pricing
description: Tier rationale, annual-default checkout, overage policy, self-host pricing, and the 12-month price-commitment statement
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

## Tiers

The four self-serve hosted tiers plus self-host plus Enterprise. Tiers now price three resources, not one: **search volume**, **snapshot storage**, and **claim verifications**. The latter two are the new wedge dimensions and are what regulated buyers pay for.

| Tier | Monthly | Annual (2 months free) | Searches/mo | Snapshots stored | Claim verifications/mo | Audit log retention | Rate limit |
|------|---------|------------------------|-------------|------------------|------------------------|---------------------|------------|
| **Free** | $0 | — | 5,000 | 1,000 | 100 | 7 days | 10 rpm |
| **Pro** | $19 | $190 | 25,000 | 25,000 | 1,000 | 30 days | 60 rpm |
| **Growth** | $49 | $490 | 100,000 | 100,000 | 10,000 | 90 days | 200 rpm |
| **Scale** | $149 | $1,490 | 500,000 | 500,000 | 100,000 | 1 year | 1,000 rpm |
| **Self-host (managed contract)** | — | $24,000/yr v1 → $99,000/yr v2 | Unlimited | Customer R2 | Unlimited | 10 years (EU AI Act) | Customer-controlled |
| **Enterprise (hosted)** | — | Contact us | Custom | Custom | Custom | 10 years | Custom |

## Why these tiers, in this order

The new wedge is verifiability, not price — but price is still the floor that removes objections. Hosted tier pricing inherits the 10×-cheaper claim from the previous pricing doc because nothing about SearXNG + Cloudflare Containers + R2 makes UnSearch more expensive than Tavily / Exa. The headline shifts from "$49 for 100K searches" to **"$49 for 100K signed, verified, replayable searches"** — same number, different proposition.

- **Free at 5,000 searches + 1,000 snapshots + 100 verifications.** ICP-3 (citation-integrity research/journalism) lives here indefinitely; ICP-1 and ICP-2 evaluate here for free. Free includes signing and verification, not a stripped version — otherwise the wedge does not demo.
- **Pro at $19.** "I'm trying it on a real project" tier. Below the credit-card-without-thinking threshold. Must not become the natural ceiling.
- **Growth at $49** is the headline ICP-1 tier — the one that goes in MCP descriptions, HN comments, and `awesome-mcp-servers` listings. At 100K verifications/mo for $49 it is the floor for a serious regulated-AI startup.
- **Scale at $149** sits below the "I need a procurement call" psychological barrier (~$500/mo for SMB SaaS), preserving the PLG funnel. Adds 1-year audit-log retention which is the first compliance milestone.
- **Self-host (managed contract).** ICP-2's primary tier. **$24K/yr v1** for self-host + deployment support + monthly updates. **$99K/yr v2** adds SOC 2 + BAA + dedicated support + signed PKI key issuance + Cloudflare-account co-management. Flat-fee, not usage-based — predictable for compliance budgets.
- **Enterprise (hosted).** Hand-touched, annual contracts only, no listed price. See [Sales playbook](./sales-playbook.md).

## Annual is the default at checkout

Budget tiers (<$50/mo) retain only ~23% of gross revenue at 12 months on monthly billing; annual pulls that closer to 70%+. Annual is structural, not optimization.

Implementation: `price_yearly` columns already exist in the schema. The `/billing` page defaults the toggle to annual, with monthly as a secondary option. Existing monthly customers get a "switch to annual and save 2 months" banner on their dashboard.

## Overage policy

Soft cap at 100% of plan. Hard cap at 120%. Above the soft cap, customers pay overage at rates that **preserve the cost-per-verified-result claim** at each tier:

| Tier | Search overage | Snapshot overage | Verification overage |
|------|----------------|------------------|----------------------|
| Pro | $0.005/search | $0.0005/snapshot | $0.005/verification |
| Growth | $0.002/search | $0.0002/snapshot | $0.002/verification |
| Scale | $0.001/search | $0.0001/snapshot | $0.001/verification |
| Free | hard cutoff, no overage | hard cutoff | hard cutoff |

Hard cap at 120% prevents bill-shock-driven churn. Above 120%, requests return 429 with a "talk to us" upgrade link.

> **Implementation note:** Overage billing requires Stripe metered billing on top of the existing fixed-plan model. Wiring is on the roadmap; not part of this strategy refresh.

## Bring-your-own-keys (BYOK) for premium engines

Available on Growth and above:

- Google Custom Search (user-supplied CSE ID + API key)
- Brave Search API (user-supplied key)
- Bing Web Search (user-supplied key)

UnSearch routes queries through the supplied key and bills the customer's vendor account directly. UnSearch charges no per-search markup; this is a sales-assist feature that converts cost-sensitive customers to Growth.

## Bring-your-own-storage (BYOS) for snapshots — self-host

ICP-2 buyers who cannot use Cloudflare R2 (data-residency-driven or hyperscaler-relationship-driven) can configure the snapshot store to write to S3, GCS, or Azure Blob via the `SNAPSHOT_BACKEND` env. Available on self-host only.

## Free-tier sustainability

Marginal cost per Free user: dominated by (a) SearXNG sidecar CPU time, (b) Workers AI grader tokens for `verify_claim`, (c) R2 storage for snapshots.

At 5K searches + 1K snapshots + 100 verifications, blended marginal cost ≈ $0.40/user/mo at zero cache hit; ≈ $0.15/user/mo at 40% cache hit (instrument weekly via Workers Analytics). Fully absorbed at 2%+ conversion to Pro.

Defense against Free-tier abuse:

- IP-based rate limits at the edge (Durable-Object sliding window in `apps/workers/src/durable-objects/rate-limiter.ts`).
- Sandbox-key flow (`is_agent_placeholder` + `claim_code` already in schema) means agent-only signups are rate-limited at the sandbox key level and cannot burn quota indefinitely without claiming.
- Snapshots + verifications have hard caps (no overage on Free) — caps protect us from cost surprises.

If marginal cost ever exceeds $2/user/mo, the response is to **lower the Free tier from 5K/1K/100 to 2K/500/50** (a `plans` row update), not to push paid users harder.

## Price-commitment statement

This appears verbatim on `unsearch.dev/pricing`:

> **We will give existing paying customers 12 months written notice before any price increase. Your tier today is your tier next year.**

This is positioning, not legal copy. It is the direct counter to Exa's March 2026 $5→$7 price hike and Brave's February 2026 free-tier kill — both of which left customers with no time to budget or migrate. The 12-month policy is enforceable in our standard ToS (existing contracts honor the price at sign-up).

## Grandfathering policy

Any tier price is locked for any individual customer for **24 months from their first paid subscription**. If we raise list prices, existing customers see the new price only at the start of their 25th month (or at renewal of an annual contract, whichever is sooner). This is the operational implementation of the 12-month-notice commitment.

## Self-host pricing rationale

| Bundle | Annual | What's included |
|---|---|---|
| **Self-host v1** | $24,000/yr | Repo access (already Apache 2.0); deployment support (1 30-min session at kickoff + 2 follow-ups in 30 days); monthly minor release updates; private Slack channel; email support; office hours quarterly |
| **Self-host v2** | $99,000/yr | All v1 + SOC 2 Type II evidence package + signed BAA / DPA / MSA + dedicated co-managed Cloudflare-account deployment + PKI key issuance with hardware-backed signing + on-call rotation for production-blocking issues + roadmap influence (one quarterly call) |

**Why flat-fee, not usage-based for self-host:** ICP-2 compliance budgets are annual line items. Predictability beats lower-on-paper-cost. Usage-based self-host triggers procurement re-review every quarter — a no-go for regulated buyers.

**Why $24K v1 / $99K v2:** ICP-2 WTP for replacing 1 FTE-equivalent of internal AI-platform-engineering work is ~$150–250K loaded. $24K is well below that floor; $99K is the upper end with compliance-grade adds. Below $24K we waste calendar; above $99K we conflict with the "AI infra is a budget line, not a CapEx" assumption.

**Floor for sales motion: do not negotiate v1 self-host below $18K, do not negotiate v2 below $75K.** Below those, point at hosted Scale + overage.

## Enterprise (hosted) — "Contact us" with no listed floor

Enterprise (hosted) sits above Scale and is **deliberately unpriced** in public. Used for hosted-but-bigger-than-Scale customers who specifically do not want self-host.

What an Enterprise (hosted) contract includes:
- Custom search / snapshot / verification volume
- Signed MSA + DPA + BAA (template from Common Paper or LawTrades — see [Sales playbook](./sales-playbook.md))
- Dedicated Container replicas + dedicated Durable-Object pool for predictable latency
- SLA — 99.9% effective uptime, 4-hour P1 response
- SSO (SAML / OIDC) by Month 6 of contract, contracted as "delivered within 90 days"
- 10-year audit-log retention
- Custom signing-key issuance ceremony

Operating floor: **do not negotiate Enterprise (hosted) below $1,500/mo**. Below that, point them at Scale + overage.

## Price localization

USD only for v1. India-based founder; a regional INR tier is deferred until MRR > $25K. Revisit at the Month-12 review.

## What we will not do

These are pricing temptations that erode the model — explicit guardrails:

- **No per-user / per-seat pricing.** UnSearch is an API + MCP, not a SaaS dashboard.
- **No "open core" feature splits.** Every feature in the codebase works the same way self-hosted and managed. The wedge is Apache 2.0 — splitting features breaks it.
- **No "$1 first month" promotional pricing.** It attracts the wrong cohort.
- **No discounts off list price for self-serve tiers.** Discounts are an Enterprise / Self-host lever only; below those, the answer is "use the lower tier."
- **No surprise price increases.** The 12-month notice policy makes this enforceable.
- **No usage-based self-host.** Defeats the predictability that makes self-host buyable for ICP-2.
- **No "verification quota separate from search quota" obfuscation.** The whole point is that signing is the primitive, not a feature; tier limits surface as separate numbers but the user does not pay separately per signed result.

## Cross-references

- See [Market](./market.md) for the competitor-pricing benchmarks that anchor the tier math.
- See [User journey](./user-journey.md) for upgrade triggers tied to quota burn.
- See [Sales playbook](./sales-playbook.md) for the Enterprise and Self-host quoting motion.
- See [MRR plan](./mrr-plan.md) for how tier mix maps to revenue milestones.
