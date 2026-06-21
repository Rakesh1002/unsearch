---
title: Market
description: The verifiable-retrieval problem, the market shifts that opened it, regulatory pressure, and competitive landscape
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

UnSearch competes in **Verifiable Retrieval Infrastructure** — the primitive that lets an AI agent ground a claim in a web source the agent's customer can re-verify months later. The category is not "search engine," not "search API for agents," not "vector database," and not "hallucination monitoring." It is the missing primitive between *what the agent saw* and *what the agent's auditor can replay*.

## Why this category now

Three structural shifts in early 2026 made the original "search API for AI agents" wedge unsellable to indie devs, and three regulatory / litigation events made the verifiable-retrieval wedge unavoidable for regulated buyers.

### What killed the old wedge

1. **Anthropic shipped native `web_search` as a server-side tool** in 2025 with 2026 "Dynamic Filtering" — Claude Sonnet 4.6 / Opus 4.7 default to it, free at usage tier, citations included, no third-party API required ([Anthropic web search docs, accessed 2026-05-28](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)).
2. **OpenAI Codex CLI ships first-party web search default-on** — `web_search = "cached"` by default, backed by OpenAI's own indexed cache; `--search` for live mode ([Codex CLI features, accessed 2026-05-28](https://developers.openai.com/codex/cli/features)).
3. **MCP registry crossed 800 official servers / 13K+ total**. Firecrawl, Exa, Tavily, Linkup all ship search MCPs ([MCP ecosystem 2026, accessed 2026-05-28](https://www.qcode.cc/mcp-servers-ecosystem-2026)). "MCP search" is now table stakes.

Plus: Tavily acquired by Nebius (Feb 2026), Brave killed free tier (Feb 2026), Exa raised prices (Mar 2026).

### What opened the new wedge

1. **Q1 2026 court sanctions for hallucinated legal citations crossed $145,000 in the US alone.** Largest single sanction: **$110,000, Oregon, April 4 2026** (Judge Mark D. Clarke; 23 fabricated citations + 8 false quotations across three filings). Sixth Circuit added $30K in March. **1,227 documented incidents globally; 550+ in the US** ([ComplianceHub 2026 reckoning, accessed 2026-05-28](https://compliancehub.wiki/legal-ai-hallucination-reckoning-2026/), [PlatinumIDS hallucination crisis report, accessed 2026-05-28](https://blog.platinumids.com/blog/ai-hallucination-crisis-courts-2026)).
2. **Medical RAG without retrieval fabricates references 40–60% of the time** on biomedical questions; even with RAG, accuracy is only 69.5%. Drug-interaction queries fabricate pharmacology references. NeurIPS 2025 had **100+ AI-hallucinated citations across 53 accepted papers** ([NCBI RAG drug side-effect study, accessed 2026-05-28](https://pmc.ncbi.nlm.nih.gov/articles/PMC13096530/), [Fortune NeurIPS scandal, accessed 2026-05-28](https://fortune.com/2026/01/21/neurips-ai-conferences-research-papers-hallucinations/)).
3. **EU AI Act full penalties begin August 2026 — three months from this document's review date.** Article 12 requires high-risk AI systems to implement automatic event logging; logs retained ≥ 6 months; documentation ≥ 10 years; provenance documentation explicitly required. Penalty: up to **€15M or 3% of worldwide turnover** ([Raconteur EU AI Act audit guide, accessed 2026-05-28](https://www.raconteur.net/global-business/eu-ai-act-compliance-a-technical-audit-guide-for-the-2026-deadline)).

These three events together create a six-month forcing-function window where regulated buyers are actively evaluating retrieval primitives that produce auditable evidence — not just clean markdown.

## The pain in numbers

| Vertical | Pain magnitude | Regulatory pressure | Source |
|---|---|---|---|
| Legal AI | $145K US sanctions Q1 2026 alone; Harvey AI ($8B valuation) still 1-in-6 queries hallucinate | Bar disciplinary actions; court sanctions; Mata v. Avianca precedent | [Harvey 1-in-6 analysis](https://tao-hpu.medium.com/harvey-ai-hit-8-billion-its-tools-still-hallucinate-in-one-of-every-six-queries-812d64182dc4) |
| Medical / Pharma RAG | 40–60% reference fabrication without RAG; clinical safety risk | FDA, HIPAA, ICH-E6(R3), EU AI Act high-risk | [NCBI biomedical RAG study](https://pmc.ncbi.nlm.nih.gov/articles/PMC13096530/) |
| Finance / Investment Research | Per-numeric-claim citations now de facto standard; Hebbia and V7 Go win on this | SEC disclosure rules, MiFID II, EU AI Act | [Hebbia financial analysis tooling](https://www.hebbia.com/resources/ai-tools-for-financial-analysis) |
| Insurance underwriting AI | Adverse-selection + bad-faith litigation risk | NAIC AI bulletin, state DOI rules | NAIC Model Bulletin 2023 |
| GovTech / Civic AI | FOIA, public records, regulatory submissions | OMB M-24-10, state procurement | OMB AI memos |
| Academic research | NeurIPS 2025 caught 100+ hallucinated citations | None hard yet — soft norms | [Fortune NeurIPS report](https://fortune.com/2026/01/21/neurips-ai-conferences-research-papers-hallucinations/) |

## Sizing

Use **regulated-AI engineering team count** as the sizing primitive rather than top-down TAM reports.

- **Regulated-AI startups (ICP-1):** ~5,000 globally (estimate based on Crunchbase + Dealroom filters: "AI" + ("legal" | "medical" | "financial" | "compliance" | "insurance") + founded 2022+). Conservative WTP $1,500/mo blended → ~$90M/yr SAM.
- **Regulated companies retrofitting AI (ICP-2):** ~1,500 globally with >$500K AI infra budget. Conservative WTP $30K/yr blended (self-host + support) → ~$45M/yr SAM.
- **Citation-integrity research / journalism (ICP-3):** ~500 organizations. WTP $200/mo blended → ~$1.2M/yr SAM.
- **Total addressable today: ~$135M/yr.** Growing with EU AI Act enforcement timeline + spread to US sectoral rules through 2027.

UnSearch at $100K MRR = **~0.9% of the addressable band** — tractable, not trivial.

## Tailwinds

- **EU AI Act Article 12 enforcement begins August 2026.** Three-month forcing function for ICP-2.
- **Tool-enabled grounding has become the architectural standard** for clinical safety and legal defensibility. The 2026 hallucination-detection / RAG research literature reads as "treat retrieval as the verifiable primitive, not the LLM" ([Braintrust 2026 detection tools roundup, accessed 2026-05-28](https://www.braintrust.dev/articles/best-hallucination-detection-tools-2026)).
- **WACZ ecosystem matured:** Webrecorder's signing spec is widely deployed in archivist and journalism workflows. C2PA v2.2 (May 2025) and v2.3 (draft) provide a parallel content-provenance standard. We borrow these formats; we don't reinvent them ([WACZ-Auth spec](https://github.com/webrecorder/wacz-auth-spec)).
- **Cloudflare Containers reached GA on April 13, 2026** with **active-CPU billing** — only billed when CPU actually burns cycles ([Cloudflare Containers pricing, accessed 2026-05-28](https://developers.cloudflare.com/containers/pricing/)). SearXNG (persistent process, cannot run on Workers) is now economical to run idle.
- **MCP Tool Search in Claude Code 4.x** — installing 10+ MCP servers no longer floods context, so MCP-first distribution is genuinely viable.
- **India / global regulated-AI buildout:** NASSCOM reports 890+ generative-AI startups in India alone (3.7× YoY growth); a meaningful subset target regulated verticals.

## Headwinds

- **Anthropic native `web_search` and Codex CLI search killed the indie-dev TAM.** Any positioning that targets indie devs will fail; this is why the ICP shifted.
- **Cloudflare AI Search exists** and offers managed RAG on the same edge. Defense framing: UnSearch is the auditable + self-hostable alternative; you own the code path and the signing keys.
- **Application-tier verticals already monetize provenance:** Hebbia ($300M+ ARR rumored), V7 Go, Harvey AI ($8B valuation). They sell apps, not infra — but they may decide to drop a public infra layer. Move faster on OSS flywheel + MCP-first to deepen distribution before they do.
- **Hyperscaler bundles:** AWS Bedrock Knowledge Bases, Azure AI Search, Google Vertex AI Search ship RAG-as-a-service tied to their model platforms. None of them sign citations or expose customer-controlled snapshots.
- **Scraping legal landscape:** Anthropic settled a US copyright class action for $1.5B in 2025; NYT v. OpenAI proceeding; Reddit v. Perplexity filed October 2025. UnSearch must default to respecting robots.txt + ToS — this is positioning, not just policy.

## Competitive landscape

Re-bucketed around the verifiable-retrieval frame:

| Category | Players | Their wedge | Why they don't solve our problem |
|---|---|---|---|
| Native LLM search | Anthropic `web_search`, Codex CLI, Gemini Grounding | Free + zero config | Closed; not customer-pinned; not replayable; data leaves perimeter; no audit log retention guarantees |
| Search APIs for agents | Tavily, Exa, Brave, Linkup, Serper, You.com, Firecrawl-search | LLM-shaped results | No signed envelopes; no snapshots; no claim verification; per-vendor format drift; Tavily now Nebius-owned |
| Web extraction | Firecrawl, Jina Reader, Crawl4AI | Clean markdown | Extraction-only; no provenance primitive |
| Web archival | Webrecorder (WACZ), ArchiveBox, Wayback Machine | Real provenance primitives | Built for archivists; no agent API; no LLM-shaped output; no MCP — we align with their formats and ship the missing agent surface |
| Application-tier vertical AI | Harvey (legal), Hebbia (finance), V7 Go (finance), Casetext-derivatives | Per-claim citations in a finished product | Closed apps; not infra; cannot be embedded by ICP-1 buyers |
| Hallucination eval / monitoring | Braintrust, Patronus, Galileo, FutureAGI, GPTZero | Post-hoc detection | Watch the output; don't fix the input |
| Content provenance standards | C2PA, WACZ, W3C PROV | Open signed-envelope formats | Standards, not products. We align with them. |
| Cloudflare AI Search | CF managed | Hybrid semantic + BM25 on CF edge | Closed managed; no self-host; no customer signing keys |
| **UnSearch** | — | **Signed citation envelope + claim verification + MCP-first + Apache 2.0** | — |

**Whitespace claim:** no third-party infra owns "verifiable retrieval for agents" as a category. Webrecorder owns the archival primitive but not the agent shape. Tavily/Exa own the agent shape but not the provenance primitive. Harvey/Hebbia own the application but not the infra. UnSearch sits in that gap.

## Pricing benchmark (where we still anchor)

Even though "cheaper Tavily" is no longer the lead, the 10× cheaper claim is still the right floor for the hosted tier — it removes "we cost too much" as an objection for ICP-1.

| Vendor | Price for 100K searches/mo | Verifiable envelope? | Claim verification? | Self-host? | MCP? |
|---|---|---|---|---|---|
| Tavily (Nebius) | ~$700 | No | No | No | Yes |
| Exa | ~$700 | No | No | No | No |
| Brave Search API | ~$500 | No | No | No | Yes |
| Linkup | ~$500 (€5/1K Standard) | No | No | No | No |
| Serper | ~$50 | No | No | No | No |
| Firecrawl Search | ~$83 (Standard $83/100K credits) | No | No | No | Yes |
| Perplexity Sonar | Token-priced | Partial (citations only) | No | No | No |
| Anthropic native `web_search` | Free at tier (Claude users) | No | No | No | N/A |
| OpenAI Codex CLI search | Free for Codex users | No | No | No | N/A |
| Cloudflare AI Search | Free beta | No | No | No | No |
| **UnSearch Growth** | **$49** | **Yes (signed)** | **Yes** | **Yes (Apache 2.0)** | **Yes (lead surface)** |

Sources accessed 2026-05-28: [Tavily Pricing](https://www.tavily.com/pricing), [Exa Pricing](https://exa.ai/pricing), [Brave Search API Pricing](https://api-dashboard.search.brave.com/documentation/pricing), [Linkup Pricing](https://www.linkup.so/pricing), [Firecrawl Pricing](https://www.firecrawl.dev/pricing), [Serper](https://serper.dev/), [Perplexity API Pricing](https://docs.perplexity.ai/docs/getting-started/pricing).

## 24-month market thesis

Retrieval is being unbundled into two layers. The application-and-evaluation layer (Harvey, Hebbia, Braintrust) commands the margin, but it is built on top of a primitive that nobody owns: customer-pinned, signed, replayable, agent-shaped retrieval. The winning vendor of the primitive layer is the one ICP-1 engineers `claude mcp add` first, and the one ICP-2 procurement officers can self-host in 30 minutes inside their own perimeter. That vendor needs to align with WACZ + C2PA so the broader archival and provenance ecosystem treats it as native, not as another fragment.

UnSearch's wedge is the combination of (a) signed citation envelopes aligned with WACZ-Auth, (b) MCP-first distribution that beats native LLM search at the moment of evaluation, (c) self-host on Cloudflare Containers GA with active-CPU billing so the cost story is defensible at low volume, and (d) Apache 2.0 + 12-month price commitment that defuses vendor-lock-in objections regulated buyers raise on day one.

Cross-references:
- See [ICP](./icp.md) for who buys.
- See [Positioning](./positioning.md) for how we describe ourselves.
- See [MRR plan](./mrr-plan.md) for the realistic revenue path this market enables.

---
**Owner:** Rakesh Roushan · **Last reviewed:** 2026-06-21 · **Review by:** 2026-09-21
