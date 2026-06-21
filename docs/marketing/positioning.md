---
title: Positioning
description: One-liner, category claim, messaging house, and vocabulary discipline for UnSearch
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

## One-liner

> **Verifiable web retrieval for AI agents. Every result signed, hashed, snapshotted, and replayable months later.**

Sixteen words. Used verbatim on the homepage hero, GitHub README, and HN launch title. The four verbs (signed / hashed / snapshotted / replayable) are the proof. Do not shorten by dropping them.

## Category claim

UnSearch is in the **Verifiable Retrieval Infrastructure** category. Not "search engine" (Google/Brave own that), not "search API for agents" (Tavily/Exa/Brave/Linkup occupy that — and Anthropic + Codex now ship native server tools at zero cost there), not "vector database" (Pinecone/Vectorize own that), not "enterprise knowledge search" (Glean owns that), not "hallucination monitoring" (Braintrust/Patronus/Galileo own that — they watch outputs, we fix the input). Category matters because it determines which mental bucket buyers compare us against. We want the reference set to be **Webrecorder + Hebbia + WACZ + audit-trail infra**, not Bing.

## Messaging house

```
                          Roof
   "Verifiable web retrieval for AI agents.
    Every result signed, hashed, snapshotted, replayable."

  ┌───────────┬───────────┬───────────┬────────────┐
  │ Pillar 1  │ Pillar 2  │ Pillar 3  │ Pillar 4   │
  │ Signed    │ MCP-first │ Self-host │ Apache 2.0 │
  │ citation  │ distrib.  │ on your   │ +Cloudflare│
  │ envelope  │           │ CF account│ -native    │
  └───────────┴───────────┴───────────┴────────────┘
```

### Pillar 1 — "Signed citation envelope on every result"

- **Proof point:** every search result returns a `citation_envelope` with `{url, fetched_at, content_sha256, snapshot_r2_key, signature_hmac_sha256, engine, agent_run_id}`. See [`docs/citation-envelope.md`](../citation-envelope.md) for the schema.
- **Receipt:** envelope format aligned with the [WACZ-Auth spec](https://github.com/webrecorder/wacz-auth-spec) so any consumer of the broader web-archival ecosystem can verify our snapshots with existing tooling.
- **Anti-vector:** "Anthropic's native `web_search` returns text. We return a signed, hashable, replayable record of what the agent saw — defensible in a court filing, an FDA submission, or an EU AI Act Article 12 audit log."

### Pillar 2 — "MCP-first distribution"

- **Proof point:** `claude mcp add unsearch` is the headline onboarding. No signup form between intent and proof of value.
- **Receipt:** UnSearch is listed in the [official MCP registry](https://modelcontextprotocol.io/registry) with `verify_claim` exposed as a tool, not just `search`. Free tier 5,000 verified searches/mo built into the MCP server itself.
- **Why this beats SDK-first:** Tool Search (Claude Code 4.x) means installing 10+ MCP servers does not flood context. One install wires Claude Code, Codex CLI (as external MCP), Cursor, Continue.dev, Zed simultaneously.

### Pillar 3 — "Self-host on your own Cloudflare account"

- **Proof point:** `wrangler deploy` from a forked repo brings up the full stack — Hono edge + FastAPI on Cloudflare Containers (GA April 13 2026) + SearXNG sidecar + R2 snapshots + D1 audit log. Customer's data never leaves their CF account.
- **Receipt:** Cloudflare Containers' active-CPU billing means idle cost is near zero ($0.01/hr scale) even with SearXNG running.
- **Why this matters:** regulated buyers (banks, hospital systems, BigLaw, pharma, insurance) physically cannot send retrieval data through a third-party API. Self-host is not a feature — it is a compliance prerequisite.

### Pillar 4 — "Apache 2.0 + Cloudflare-native"

- **Proof point:** [Apache 2.0 LICENSE](https://github.com/Rakesh1002/unsearch/blob/main/LICENSE); D1 + KV + Vectorize + R2 + Workers AI bindings already wired; no proprietary closed half.
- **Receipt:** [12-month price-commitment statement](./pricing.md#price-commitment-statement) — direct response to the Brave free-tier kill (Feb 2026), Exa price hike (Mar 2026), and Tavily-to-Nebius acquisition (Feb 2026).
- **Anti-vector:** "Tavily was acquired by Nebius — you can't fork Tavily. Anthropic ships native search but you can't audit it. You can fork UnSearch."

## Anti-positioning

What we are explicitly *not* — naming this is more important than naming what we are.

- **We are not Anthropic's `web_search` or Codex CLI search.** Those are server-side, free, and great for non-regulated workflows. We are the layer regulated buyers reach for when those fail their compliance review.
- **We are not a cheaper Tavily / Exa.** That wedge died when the LLM vendors shipped native search. The "10× cheaper" claim still holds as a side effect of SearXNG + active-CPU billing, but it is not the lead hook.
- **We are not Webrecorder.** Webrecorder owns the archivist workflow — `.wacz` packages for libraries and journalists. We borrow their signing format, then ship the agent-shaped retrieval API and MCP that Webrecorder explicitly does not.
- **We are not Hebbia or Harvey.** Those are closed application-tier products that wrap citations inside a finished legal/finance UI. We are the infra you would use to *build* a Harvey for your own vertical.
- **We are not Braintrust / Patronus / Galileo.** Those detect hallucinations after generation. We fix the retrieval primitive before generation.
- **We are not Glean.** Glean searches inside your company. UnSearch retrieves from the open web with provenance.
- **We are not "cheap." We are auditable.** Price is the second sentence, not the first. Buyers in regulated AI optimize for defensibility, not for $/1K.

## Persona-specific entry points (constant position, different proof leads)

The position above is **constant**. What changes between phases is *which proof point leads* on the landing page.

| Entry URL | For | Leads with |
|-----------|-----|------------|
| `unsearch.dev` (default) | ICP-1 (eng leads at regulated-AI startups) | MCP install + `verify_claim` live demo |
| `unsearch.dev/eu-ai-act` | ICP-2 (AI platform leads at regulated companies) | Article 12 logging + self-host + signed envelopes |
| `unsearch.dev/for-research` | ICP-3 (academic / journalism citation integrity) | Free tier + WACZ export |
| `unsearch.dev/migrate-from-tavily` | Legacy compat — still indexed for organic traffic | Tavily-shape endpoint + price comparison, secondary CTA "but here is what you actually came for: signed citations" |

Constant position is non-negotiable because changing it destroys SEO compounding and confuses MCP-server installers who become future ICP-2 champions.

## Vocabulary discipline

Use these words. Never use the banned ones — they erode credibility with the buyers we want.

| Use | Instead of |
|-----|------------|
| verifiable retrieval | search API |
| citation envelope | result metadata |
| snapshot | cached page |
| signed | timestamped |
| replayable | reproducible |
| audit log | usage stats |
| MCP-native | "supports MCP" |
| Apache 2.0 | "open source" alone |
| self-hostable on Cloudflare | "self-hostable" alone |
| regulated AI | enterprise |
| in beta | partial, basic, early |

**Banned phrases:**
- "enterprise-grade" (signals we are not)
- "AI-powered" (every product is)
- "next-generation" (zero information content)
- "revolutionary" (no)
- "best-in-class" (claim, not evidence)
- "leverage" as a verb in customer-facing copy
- "trust" without a primitive backing it (signed envelopes back it; the word alone does not)

## Channel-specific taglines

Constant position, channel-tuned phrasing:

| Channel | Tagline |
|---------|---------|
| GitHub README | "Verifiable web retrieval for AI agents. Signed citations. Self-hostable on Cloudflare. Apache 2.0." |
| Show HN title | "Show HN: UnSearch — verifiable web retrieval for AI agents (signed snapshots, MCP-native, Apache 2.0)" |
| MCP directory listing | "Web search that returns signed, replayable citations. Drop into any MCP-compatible agent." |
| Anthropic MCP marketplace | "Citation-grade retrieval for Claude agents. Every result signed and replayable." |
| OpenAI Codex external-MCP guide | "Verifiable web retrieval as an external MCP for Codex CLI." |
| EU AI Act content page | "Article 12 logging for agent retrieval. Every query, every snapshot, every claim, retained for 10 years." |
| Legal-AI vertical landing | "Defend every cited authority. Signed source-pinning so a judge can replay what your agent saw." |
| Medical-RAG vertical landing | "Verifiable retrieval for clinical decision support. Snapshot every drug-interaction source." |
| Hand-picked outbound | One-liner + a paragraph naming the specific incident the prospect is exposed to |

## Price-commitment statement (must appear on `pricing.md` page)

> We will give existing paying customers **12 months written notice** before any price increase. Your tier today is your tier next year.

This is positioning, not legal copy. The Brave free-tier kill (Feb 2026) and Exa price hike (Mar 2026) made this the single most credible thing we can say about being a trustworthy vendor.

## Positioning under threat conditions

What changes if **Anthropic ships native citation signing** as a server tool feature:

- Lead Pillar 1 with self-host: "Anthropic's signed citations live in Anthropic's infrastructure. UnSearch's signed citations live in your Cloudflare account, where your auditor can re-run them."
- Lean Pillar 3 (self-host) harder; emphasize 10-year retention which exceeds any LLM-vendor's audit retention.

What changes if **OpenAI ships citation signing for Codex CLI**:

- Same response — emphasize customer-controlled storage, customer-controlled signing keys, no data leaving the perimeter.

What changes if **Cloudflare AI Search adds verification**:

- Cloudflare AI Search is managed; UnSearch is buildable. Use both — we extend the same edge with code you can audit. Don't fight, slot in.

What changes if **Tavily / Nebius re-emerges with self-host**:

- Pillar 2 (MCP-first) becomes the wedge — Tavily was never MCP-shaped at the primitive level. Add Pillar 4 emphasis: Apache 2.0 vs Nebius closed-source.

What changes if **Harvey, Hebbia, or another application-tier vendor drops a public infra layer**:

- Move faster on OSS flywheel + MCP-first distribution. Their motion is application; ours is primitive. Different sales cycle, different ACV, different ICP — limited overlap.

Cross-references:
- See [Market](./market.md) for the competitor data the pillars cite.
- See [Value prop](./value-prop.md) for the pain/gain mapping behind each pillar.
- See [Pricing](./pricing.md) for the price-commitment language verbatim.
- See [`docs/citation-envelope.md`](../citation-envelope.md) for the envelope schema referenced in Pillar 1.
