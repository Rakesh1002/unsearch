---
title: Strategy Docs
description: Why UnSearch exists, who it's for, how we sell it, and the path to $750K MRR
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

These are UnSearch's public strategy docs. They live in the open for three reasons: (1) it forces honesty (no internal-only weasel words), (2) it's a recruiting and partnership signal, (3) prospective customers can audit our thinking the same way they audit our code.

**Major reposition shipped 2026-05-28:** UnSearch is now "verifiable web retrieval for AI agents," not "the open-source Tavily alternative." See [positioning](./positioning.md) for the new one-liner, [market](./market.md) for the structural shifts that drove the reposition, and the approved plan at `~/.claude/plans/app-unsearch-dev-is-not-deployed-luminous-wilkinson.md` for the full context.

If you're new here, read in the order below.

## Reading order

| # | Doc | Read time | What's in it |
|---|-----|-----------|--------------|
| 1 | [Market](./market.md) | 6 min | The verifiable-retrieval problem, real Q1 2026 incidents driving pain, EU AI Act forcing function, sizing, competitive landscape |
| 2 | [ICP](./icp.md) | 5 min | The three personas — Priya, David, Anika — ordered by sales sequence |
| 3 | [JTBD](./jtbd.md) | 4 min | The jobs each persona hires UnSearch to do |
| 4 | [Positioning](./positioning.md) | 5 min | The one-liner, category claim, messaging house, vocabulary discipline |
| 5 | [Value Proposition](./value-prop.md) | 5 min | Pains/gains × relievers/creators per persona |
| 6 | [User Journey](./user-journey.md) | 4 min | MCP-install-first path + dashboard path + self-host path |
| 7 | [Pricing](./pricing.md) | 4 min | Tiers (now priced on searches + snapshots + verifications + retention), self-host pricing, 12-month price commitment |
| 8 | [GTM](./gtm.md) | 5 min | Three-phase motion (MCP wedge → compliance hook → partner) + T-14d → T+90d launch runbook |
| 9 | [Sales Playbook](./sales-playbook.md) | 5 min | Founder-led sales for ICP-1 and ICP-2, plus AE-hire transition |
| 10 | [MRR Plan](./mrr-plan.md) | 7 min | Month-by-month path from $0 → $25K → $250K → $750K MRR with cited assumptions |

Total read time: ~50 minutes for the full pack.

## Audience map

| If you are... | Read |
|---------------|------|
| A prospective customer evaluating UnSearch | [Market](./market.md), [Positioning](./positioning.md), [Pricing](./pricing.md) |
| A prospective hire or partner | [Market](./market.md), [GTM](./gtm.md), [MRR Plan](./mrr-plan.md) |
| A prospective investor | All ten in order |
| An open-source contributor | [JTBD](./jtbd.md), [Value Proposition](./value-prop.md), [User Journey](./user-journey.md) |
| The founder ([@Rakesh1002](https://github.com/Rakesh1002)) reviewing quarterly | All ten — update the "Last reviewed" date at the top |

## Source of truth — what's actually shipped

The strategy docs above describe what UnSearch sells and to whom. For what's actually in the codebase right now versus what's in flight, the source of truth is:

- **What ships in each release:** [CHANGELOG.md](../../CHANGELOG.md). The `[Unreleased] — Deferred to follow-up commits` section is the canonical list of work that's in flight but not live.
- **Feature parity claims:** [feature matrix](../feature-matrix.md). Anything marked "in beta" there is honestly in beta — don't lead with it in customer conversations.
- **Tech architecture:** [Cloudflare architecture](../cloudflare-architecture.md), [AI pipeline](../ai-pipeline.md), and ADRs 0001–0013 at [`docs/adr/`](../adr/README.md).
- **Citation envelope schema:** [`docs/citation-envelope.md`](../citation-envelope.md).
- **API surface:** [API reference](../API_REFERENCE.md).

## Doc maintenance rules

- Every quantitative claim is inline-cited with a URL and access date.
- Every persona reference uses the canonical names — Priya (ICP-1), David (ICP-2), Anika (ICP-3). Defined in [ICP](./icp.md).
- If a persona only appears in one doc, it's noise — delete or expand.
- If a feature claim doesn't grep to a shipped file path in the repo, label it "in beta" or don't claim it.
- Quarterly: founder updates each doc's "Last reviewed" date and reconciles the MRR plan against actuals.

## License

These docs ship under the same Apache 2.0 license as the codebase. Fork, remix, adapt — if you build something similar, we'd love to read it.
