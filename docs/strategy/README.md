---
title: Strategy Docs
description: Why UnSearch exists, who it's for, how we sell it, and the path to $100K MRR
---

> Last reviewed: 2026-05-23 · Next review: 2026-08-23

These are UnSearch's public strategy docs. They live in the open for three reasons: (1) it forces honesty (no internal-only weasel words), (2) it's a recruiting and partnership signal, (3) prospective customers can audit our thinking the same way they audit our code.

If you're new here, read in the order below.

## Reading order

| # | Doc | Read time | What's in it |
|---|-----|-----------|--------------|
| 1 | [Market](./market) | 5 min | Why this category, why now; sizing; tailwinds; headwinds; competitor landscape |
| 2 | [ICP](./icp) | 4 min | The three personas — Maya, Priya, David — ordered by sales sequence |
| 3 | [JTBD](./jtbd) | 3 min | The jobs each persona hires UnSearch to do |
| 4 | [Positioning](./positioning) | 4 min | The one-liner, category claim, messaging house, and what we are not |
| 5 | [Value Proposition](./value-prop) | 4 min | Pains/gains × relievers/creators per persona |
| 6 | [User Journey](./user-journey) | 4 min | Awareness → activation → retention → expansion mapped to actual dashboard screens |
| 7 | [Pricing](./pricing) | 4 min | The four self-serve tiers, annual-default, overage policy, price-commitment statement |
| 8 | [GTM](./gtm) | 5 min | Three-phase motion + T-14d → T+90d launch runbook |
| 9 | [Sales Playbook](./sales-playbook) | 4 min | Founder-led sales for Personas B and C, plus the AE-hire transition |
| 10 | [MRR Plan](./mrr-plan) | 6 min | Month-by-month milestones from $0 → $10K → $100K MRR with cited assumptions |

Total read time: ~45 minutes for the full pack.

## Audience map

| If you are... | Read |
|---------------|------|
| A prospective customer evaluating UnSearch | [Market](./market), [Positioning](./positioning), [Pricing](./pricing) |
| A prospective hire or partner | [Market](./market), [GTM](./gtm), [MRR Plan](./mrr-plan) |
| A prospective investor | All ten in order |
| An open-source contributor | [JTBD](./jtbd), [Value Proposition](./value-prop), [User Journey](./user-journey) |
| The founder ([@Rakesh1002](https://github.com/Rakesh1002)) reviewing quarterly | All ten — update the "Last reviewed" date at the top |

## Source of truth — what's actually shipped

The strategy docs above describe what UnSearch sells and to whom. For what's actually in the codebase right now versus what's in flight, the source of truth is:

- **What ships in each release:** [CHANGELOG.md](https://github.com/Rakesh1002/unsearch/blob/main/CHANGELOG.md). The `[Unreleased] — Deferred to follow-up commits` section is the canonical list of work that's in flight but not live.
- **Feature parity claims vs. competitors:** [feature matrix](../feature-matrix). Anything marked "in beta" there is honestly in beta — don't lead with it in customer conversations.
- **Tech architecture:** [Cloudflare architecture](../cloudflare-architecture), [AI pipeline](../ai-pipeline).
- **API surface:** [API reference](../api-reference/introduction).

## Doc maintenance rules

- Every quantitative claim is inline-cited with a URL and access date.
- Every persona reference uses the canonical names — Maya (Persona A), Priya (Persona B), David (Persona C). Defined in [ICP](./icp).
- If a persona only appears in one doc, it's noise — delete or expand.
- If a feature claim doesn't grep to a shipped file path in the repo, label it "in beta" or don't claim it.
- Quarterly: founder updates each doc's "Last reviewed" date and reconciles the MRR plan against actuals.

## License

These docs ship under the same Apache 2.0 license as the codebase. Fork, remix, adapt — if you build something similar, we'd love to read it.
