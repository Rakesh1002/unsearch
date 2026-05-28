---
title: Jobs to Be Done
description: What each persona hires UnSearch to do, what they currently use, and what triggers a switch
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

JTBD framing forces us to separate *what we sell* from *what the buyer is actually trying to accomplish*. Every UnSearch feature must map to a Job; if a feature doesn't fit, it's the feature that's wrong, not the framing.

## Job format

> When [situation], I want to [motivation], so I can [expected outcome].

Functional, social, and emotional dimensions per Job. See [ICP](./icp.md) for persona definitions.

## Job 1 — Priya (ICP-1, regulated-AI startup eng lead)

> **When my legal-AI / medical-RAG / fintech-research agent answers a customer question, I want every cited source to be auditable to the exact bytes the agent saw, signed and replayable months later, so my customer's lawyer / regulator / compliance officer can defend the claim and I do not get fired when a citation is challenged.**

- **Current alternative:** Tavily / Exa + Firecrawl + custom Playwright snapshots to their own S3 + custom Postgres provenance table + BART-MNLI or Workers AI grader. ~1–2 FTEs of glue.
- **Switching trigger:** first customer asks "can you show me what your agent saw last month?" *or* internal hallucination caught by a customer *or* EU AI Act memo from legal counsel *or* a partner-firm AI lead points at the Q1 2026 sanctions cycle.
- **Functional dimension:** drop in via MCP (`claude mcp add unsearch`) in 60 seconds; signed envelope on every result; `verify_claim` endpoint with span-level evidence; audit-log API.
- **Social dimension:** "we ground our agent in customer-pinned, signed citations" is a credible answer in a YC AI Demo Day pitch, in a customer's procurement review, and in an EU AI Act readiness conversation.
- **Emotional dimension:** career-protection. "I will not be the engineer whose agent's $30K customer contract gets cancelled because a court citation was fabricated."
- **Outcome metric:** zero customer-facing hallucinations attributed to retrieval in any quarter; <5 minutes to first MCP-served verified result; replaceability of 1+ FTE-equivalent of snapshot/verification glue.

## Job 2 — David (ICP-2, regulated-company AI platform director)

> **When my AI committee, compliance officer, or external regulator asks for the retrieval audit trail behind any AI-assisted decision, I want a primitive that runs inside my own Cloudflare account, signs every retrieved source with my own keys, retains it for 10 years, and produces logs my regulator can replay, so I can ship LLM features without re-architecting our agent every time compliance moves.**

- **Current alternative:** Splunk + custom S3 snapshot pipeline + manual provenance spreadsheets + a closed-source vendor that fails security review every quarter. Or no LLM agent at all because compliance blocked it.
- **Switching trigger:** EU AI Act August 2026 enforcement deadline; CISO blocks Tavily / Exa for data-residency reasons; AI committee mandates "auditable retrieval"; regulator inquiry post-incident.
- **Functional dimension:** self-host inside their own Cloudflare account in <30 minutes; signed envelope with customer-controlled HMAC key (PKI v2 in roadmap); audit-log retention configurable up to 10 years; signed BAA / DPA / MSA available; SOC 2 Type II on roadmap (Month 9).
- **Social dimension:** "open source, runs in our account, customer-controlled signing keys, WACZ-aligned" is a stronger story in a procurement review than "trust this SaaS vendor."
- **Emotional dimension:** risk reduction; the buyer's career depends on the vendor not failing the audit and on the vendor not disappearing.
- **Outcome metric:** pass EU AI Act readiness review by Aug 2026; renewal lift on year two; <30-day onboarding to first production traffic with full signing + audit log live.

## Job 3 — Anika (ICP-3, citation-integrity research / journalism engineer)

> **When I publish a research paper / investigative piece / fact-check, I want to snapshot every URL I cite so I can prove the source said what I claimed at publish time and so my readers can replay it months later when the URL has rotted, so the integrity of my work survives bit rot and silent edits.**

- **Current alternative:** Wayback Machine + Webrecorder + manual Playwright + spreadsheets.
- **Switching trigger:** first retraction tied to URL rot; AI-misinformation story that requires provenance; NeurIPS 2025 citation-hallucination scandal awareness; Webrecorder community discussion.
- **Functional dimension:** Free tier with 1,000 snapshots/mo and 100 claim verifications/mo; WACZ export of every snapshot; signed envelope so peers can verify outside UnSearch.
- **Social dimension:** "I run an open-source primitive aligned with WACZ" is a credibility marker in journalism and reproducibility communities.
- **Emotional dimension:** professional integrity; reproducibility is the value, not a feature.
- **Outcome metric:** every cited URL is replayable from a signed snapshot; zero correction-driven retractions in a year.

## Anti-JTBDs — what we are explicitly *not* hired for

Naming what we're not hired to do prevents scope creep and keeps the product focused.

- **We are not hired to be Google.** No browser, no consumer UI, no SERP-page aesthetic.
- **We are not hired to be a vector database.** Pinecone, Vectorize, Qdrant own that job. We use vectors; we don't sell them.
- **We are not hired to be Anthropic's `web_search` or Codex CLI search.** Native LLM search is good enough for non-regulated workflows. We are the layer regulated buyers reach for when those fail their compliance review.
- **We are not hired to be Perplexity.** Perplexity owns "AI search for humans." We own "retrieval for agents that needs to defend its claims."
- **We are not hired to be a managed scraper.** Bright Data, Apify, Firecrawl own that. We surface what's findable on the open web with provenance; we don't run targeted scraping campaigns.
- **We are not hired to be Glean.** Glean owns "search the inside of your company." We own "verifiable retrieval from the open web."
- **We are not hired to be Braintrust / Patronus.** They monitor outputs. We fix the input primitive so there is less to monitor.
- **We are not hired to be Harvey or Hebbia.** They sell finished application-tier products. We sell the infra that ICP-1 startups build their version of Harvey on top of.

If a prospect's question is one of the above, refer them out and keep the conversation short. Saying no is a feature.

## Outcome-metric summary

Every Job has a measurable outcome the buyer judges us by. These drive product instrumentation in `apps/web/` and the agent observability layer.

| Persona | Outcome metric | Measurement source |
|---------|----------------|---------------------|
| Priya (ICP-1) | Time to first MCP-served verified result | MCP server install telemetry + first `verify_claim` call |
| David (ICP-2) | EU AI Act readiness audit pass + 30-day onboarding | Customer success log + audit attestation; SOC 2 evidence |
| Anika (ICP-3) | % of cited URLs with replayable signed snapshot | Self-reported in publication; WACZ export count |

## How JTBDs constrain product decisions

- **`verify_claim` is the single most load-bearing endpoint** for ICP-1 and ICP-2. Treat it as P0 reliability forever.
- **Citation envelope schema does not break backward-compatibility** without an explicit ADR and a v2 envelope co-existing with v1 for 12 months. Audit consumers depend on stability.
- **MCP server is the lead surface.** Any feature that does not appear as an MCP tool is hidden from the dominant evaluation path; either expose it as a tool or admit it is secondary.
- **Knowledge-graph, deep-research, topic-monitoring, predictive-search beta endpoints exist to deepen ICP-1 and ICP-2 jobs once verifiable-retrieval is solved.** They are not lead-message material. See [feature matrix](../feature-matrix.md).
- **Connectors (Slack / Drive / Confluence / Notion / GitHub) are Glean-job territory** — explicitly **not** an UnSearch Job. They are deferred indefinitely unless an ICP-2 contract requires them.
- **Tavily-compatible `/api/v1/agent/search` stays as a compatibility surface** (ADR-0003) so existing Tavily migrations still work, but it is no longer the lead onboarding path.

Cross-references:
- See [ICP](./icp.md) for persona definitions.
- See [Value prop](./value-prop.md) for the pain/gain mapping per Job.
- See [Positioning](./positioning.md) for how each Job becomes a messaging entry point.
