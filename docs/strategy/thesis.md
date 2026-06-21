# UnSearch — Thesis

> **The bet in one sentence:** As AI agents move into regulated workflows, "what the agent saw on the web, provably" becomes a required infrastructure primitive — and the team that ships it as an open, MCP-native, self-hostable signed-citation layer owns the category before the hyperscalers bolt it on.

## Problem
AI agents confidently cite web sources that are wrong, dead, paraphrased, fabricated, or silently changed since retrieval, and there is no widely-adopted primitive that records, cryptographically, what the agent saw at what URL, at what time, at what hash. The pain is acute and now-quantified:
- $145K in U.S. court sanctions in Q1 2026 alone for AI-hallucinated legal citations (single largest: $110K on 2026-04-04 for 23 fabricated citations + 8 false quotations).
- Harvey AI ($8B valuation) still hallucinates ~1 in 6 queries; biomedical reference-fabrication runs 40-60% without retrieval, ~69.5% accuracy even with RAG.
- Regulated buyers cannot use Anthropic native `web_search` or Codex CLI search because citations aren't customer-pinnable, snapshots aren't reproducible, and data leaves their perimeter — so they hand-roll a 5-vendor stack plus 1-2 FTEs of glue per company.

See [market.md](./market.md) for sourced incident detail and competitive landscape.

## Why now
- **Regulation is a hard forcing function.** EU AI Act Article 12 full enforcement begins August 2026 — automatic event logging over the system lifetime, 6-month minimum log retention, 10-year documentation retention, provenance documentation explicitly required. Penalty: EUR 15M or 3% of worldwide turnover. This converts "nice-to-have provenance" into a procurement checkbox on a deadline.
- **Cloudflare Containers reached GA (April 2026)**, making it viable to run FastAPI + a SearXNG meta-search sidecar at the edge alongside Workers/D1/Vectorize/R2/Queues — the substrate that makes a self-hostable, in-perimeter signed-retrieval layer cheap to ship.
- **MCP became the default agent-tool interface**, opening a no-signup distribution wedge: the verified-search tool can be installed directly into Claude and other clients.

## Wedge
MCP-first, free tier (5,000 verified searches/month) built into the server itself — `claude mcp add unsearch` / `npx @unsearch/mcp-server`, no signup, no key, no card. The smallest paid thing is the signed citation envelope + snapshot on hosted search; the first buyer is an engineering lead at a legal/medical/finance AI startup (ICP-1) who needs pinnable citations to pass their own customer's audit. ICP-1 logos then earn the credibility to sell self-host into regulated incumbents (ICP-2), who are the revenue base. See [icp.md](./icp.md) and [gtm/go-to-market.md](../gtm/go-to-market.md).

## Insight
The category is not "search engine," "search API for agents," "vector DB," or "hallucination monitoring" — it is **Verifiable Retrieval Infrastructure**, the missing primitive between *what the agent saw* and *what the agent's auditor can replay months later*. Two non-obvious bets competitors don't share: (1) aligning the envelope with the WACZ-Auth web-archival spec so the broader archival ecosystem can verify our snapshots with existing tooling (standards gravity, not a proprietary format); (2) shipping Apache 2.0 + self-hostable from day one, because the regulated buyers with the most acute pain are exactly the ones who refuse to let retrieval data leave their perimeter — closed SaaS is structurally disqualified from the highest-value accounts.

## What would make us kill this
- ICP-1 engineering leads, when shown signed envelopes, treat verifiable provenance as a "later" problem rather than a procurement blocker — i.e., the EU AI Act / sanction pressure does not translate into willingness to pay within ~2 sales cycles.
- A hyperscaler (Anthropic/OpenAI/Cloudflare) ships customer-pinnable, in-perimeter, reproducible signed citations natively before we reach ~20 ICP-1 logos, collapsing the wedge.
- Self-host conversion fails: regulated incumbents adopt the open layer but the in-perimeter deployment + signing-key model never converts to paid v2 (BAA/DPA/SSO) contracts, leaving no revenue base under the OSS funnel.

> {prompt: pressure-test the "why now" timing against the realistic enforcement ramp of EU AI Act Article 12 — does August 2026 actually pull budget forward, or do buyers wait for the first enforcement action? Source procurement-timeline evidence.}
> {prompt: quantify the build-vs-buy threshold — at what query volume / team size does the 5-vendor hand-rolled stack stay cheaper than UnSearch, and does that threshold sit inside or outside the ICP-1 band?}

---
**Owner:** Rakesh Roushan · **Last reviewed:** 2026-06-21 · **Review by:** 2026-09-21
