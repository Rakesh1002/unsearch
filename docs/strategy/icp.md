---
title: ICP
description: The three personas UnSearch sells to, ordered by sales sequence
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

UnSearch has three ideal-customer profiles, ordered by **when we sell to them**, not by revenue size. ICP-1 is the wedge into the regulated-AI ecosystem; ICP-2 is the revenue base; ICP-3 is the distribution / credibility channel. The order is non-negotiable — we have zero credibility selling to ICP-2 (a bank or BigLaw firm) until ~20 ICP-1 logos exist (legal-AI startups, medical-RAG cos, fintech research-agent startups).

## ICP-1 — "Priya, the regulated-AI startup eng lead"

**Months 1–6 · Wedge · MCP-first acquisition + founder-led close**

| Dimension | Detail |
|-----------|--------|
| Firmographic | Series Seed–B, 10–80 person AI startup, building vertical AI for legal / medical / finance / insurance / research / compliance |
| Role | Engineering lead, CTO, or "AI engineer" responsible for retrieval and evals |
| Stack | LangGraph, Vercel AI SDK, LlamaIndex, or OpenAI Agents SDK; Cloudflare Workers or Vercel for serving; Anthropic Claude or OpenAI GPT-5 in production |
| Vertical examples | Case-law RAG, contract-review agents, legal-research copilots, clinical-decision-support tools, drug-interaction agents, fintech investment-research bots, biotech literature agents, compliance-tracking copilots, GovTech regulatory-tracking tools, academic-integrity tools |
| Current state | Pays Tavily + Firecrawl + writes custom Playwright snapshot code + maintains a Postgres provenance table + runs a homemade NLI grader (BART-MNLI or a Workers AI prompt). 1–2 internal engineering FTE-equivalents lost to duct-tape glue. |
| Behavioral signal | Hit a Tavily cost cliff; first customer requested audit logs; saw the Q1 2026 sanctions news; received an EU AI Act compliance memo from their legal counsel; published a "how we evaluated retrieval vendors" blog post |
| Buying authority | Tech lead signs $500–$2K/mo without board approval; $2K+ usually needs cofounder buy-in |
| WTP | $500–$5K/mo (replaces 1–2 FTE-equivalents of snapshot + verification glue) |
| Where they live | LangGraph Discord, Anthropic Builders Discord, MCP server directory, regulated-AI Slack groups (Legal Tech Slack, Health AI Slack, FinTech AI Slack), YC AI cohort backchannels, the `r/LegalTechnology` / `r/MedicalAI` subreddits, the Webrecorder / Harvard LIL community |
| Estimated population | 3,000–8,000 companies globally (regulated-AI startup founded post-2023) |

**Sourcing channels (named, for the GTM team):**
- Submit to the [official MCP registry](https://modelcontextprotocol.io/registry) — every install is an ICP-1 signup.
- Read recent funding announcements on TechCrunch / The Information / Sifted filtered for "AI" + ("legal" | "medical" | "fintech" | "compliance"). DM the technical cofounder.
- Watch X / LinkedIn for the Q1 2026 legal-AI sanctions cycle aftershocks; reply in thread to engineers asking "how do we ground this?".
- LegalGeek US, AI4 Health, FinRegTech, RSA AI Track — single-conference presence per quarter.
- Cross-link from LangChain + LlamaIndex + Vercel AI SDK integration directories.
- Sponsor SearXNG upstream (small grant) — relationship + credibility with the open-source meta-search community.

**Disqualifiers:** consumer / non-regulated AI startups (Anthropic native search is good enough — wrong ICP); pre-revenue agent demos with no users (Free tier indefinitely — serve them but do not optimize for them); anyone who only wants raw search with no envelope / no verification (they want Tavily — refer them away politely).

## ICP-2 — "David, the regulated-company AI platform director"

**Months 4–18 · Revenue base · Compliance-hook sales-led**

| Dimension | Detail |
|-----------|--------|
| Firmographic | 200–10,000-person regulated company retrofitting LLM features: regional or commercial bank, hospital system, insurance carrier, BigLaw firm, pharma, asset manager, accounting firm |
| Role | Director or VP of AI Platform, Head of Applied AI, or Head of AI Engineering. Sometimes accompanied by a compliance officer or CISO in the buying committee. |
| Stack | Multi-cloud or Cloudflare-heavy; has an internal AI platform team, an MSA template, a SIEM, and an established model-risk-management (MRM) process |
| Current state | Cannot use Anthropic / Codex native search — data leaves the perimeter; no audit log; no customer-pinned snapshots. Hand-rolling a citation store on Splunk + S3. Months behind their EU AI Act August 2026 timeline. |
| Behavioral signal | Compliance officer signs an RFP; AI committee asks for "auditable retrieval"; CISO blocks Tavily for data-residency reasons; legal counsel cites Q1 2026 sanctions case-law internally |
| Buying authority | VP-level + procurement; $50K–$500K annual contracts; signed MSA + DPA + BAA + SSO required |
| WTP | $5K–$50K/mo hosted; **$20K–$200K/yr self-hosted in their own CF account with support contract** |
| Where they live | EU AI Act readiness events; Big4 partner channels (Deloitte, EY, PwC, KPMG AI-risk practices); ISACA / IIA AI-audit working groups; CDISC / IHE for healthcare; XBRL / FIBO for finance |
| Estimated population | 800–2,500 companies globally (regulated companies with >$500K AI infra budget) |

**Sourcing channels (mix of inbound and partner-sourced):**
- Inbound from ICP-1 customers who scale or are acquired into ICP-2 buyers (the natural ladder).
- EU AI Act content + webinars (Phase 2 GTM); "Article 12 logging for agent retrieval" technical guide.
- Big4 / Tier-1 consultancy partnerships — co-branded readiness assessments with UnSearch as the technical answer.
- Cloudflare Workers Launchpad relationship for shared portfolio referrals (post-ICP-2 customers running on CF).
- Apply to NIST AI RMF examples directory once SOC 2 Type I lands.

**Disqualifiers:** any prospect requesting bespoke product work (custom connectors, custom models, dedicated engineering teams); any deal where the procurement cycle is projected past 120 days (disqualify and re-engage in 6 months); RFP-only buyers with no executive sponsor (these never close).

## ICP-3 — "Anika, the citation-integrity research / journalism engineer"

**Months 1–24 · Credibility + distribution · Free-tier ambassador**

| Dimension | Detail |
|-----------|--------|
| Firmographic | NIH-funded research lab, citation-integrity newsroom, academic-integrity tool startup, fact-check publisher, Webrecorder-community-adjacent civic-tech project |
| Role | Research engineer, data journalist, or "head of fact-checking infra" |
| Stack | Python + LlamaIndex / Haystack; sometimes a custom RAG over public records (PACER, SEC EDGAR, FDA orange book, PubMed) |
| Current state | Mixes Wayback Machine snapshots + Playwright + manual fact-check spreadsheets. NeurIPS 2025 hallucinated-citation scandal made this their professional problem. |
| Behavioral signal | Published a piece on retracted research, AI-generated citations, or platform misinformation; star on Webrecorder repos; member of the ICIJ / Bellingcat / Storyful / GIJN communities |
| Buying authority | Free tier indefinitely as OSS evangelist; will pay $19–49/mo when team scales |
| WTP | Low ($0–500/mo), but high credibility and reputation leverage |
| Where they live | Webrecorder community Slack; Society of Professional Journalists; GIJN forums; Reproducibility Project mailing lists; `r/AcademicIntegrity` |
| Estimated population | 200–800 organizations |

**Why we want them:** distribution and credibility. NeurIPS 2025's 100+ hallucinated citations made this a publicly named problem. ICP-3 customers produce the public artifacts (a retraction-tracking news piece, a research-integrity dashboard, a Bellingcat investigation) that get UnSearch in front of ICP-1 and ICP-2 buyers without sales effort.

**Sourcing channels:**
- Partner with Webrecorder / Harvard LIL on WACZ alignment; sponsor a workshop at the next IIPC (International Internet Preservation Consortium) meeting.
- Free grant of Growth tier to civic-tech / journalism orgs working on AI-misinformation provenance.
- Conference presence at the Online News Association annual.
- Open-source the verification grader's eval harness; let academic researchers publish on it.

**Disqualifiers:** general-purpose academic libraries (use Internet Archive directly); commercial publishers with closed agendas (their incentives are misaligned with provenance).

## Anti-personas — who we explicitly do not sell to

These are common false positives that look like ICPs but burn solo-founder hours with no payoff.

| Anti-persona | Why not |
|--------------|---------|
| Consumer search users | Wrong product (we don't have a UI, we have an API + MCP) |
| Indie devs building non-regulated agents | Anthropic native `web_search` and Codex CLI search are free and good enough for them — wrong ICP |
| Glean's enterprise procurement buyers | Wrong product (internal knowledge ≠ open web retrieval); cycle measured in quarters |
| Big Tech internal teams | Won't adopt an open-source competitor to Cloudflare AI Search hosted on Cloudflare |
| "I want to scrape Twitter / Instagram / LinkedIn" | Scraping legal landscape (Anthropic $1.5B settlement, Reddit v. Perplexity) — politely refuse |
| Marketers wanting SEO data at $10/mo | Wrong category; refer them to Serper |
| Cheaper-Tavily seekers with no compliance need | Right idea, wrong ICP — they will churn within 60 days when Anthropic native search becomes their default |
| Customers who want closed-source UnSearch | We will not white-label or close-source — refuse politely |

## Buying-trigger summary

| ICP | Trigger that creates the buy | Time-to-first-value target |
|-----|------------------------------|----------------------------|
| ICP-1 (Priya) | First customer asks for audit logs OR first internal hallucination caught OR EU AI Act compliance memo | 60 seconds to first MCP-served verified result |
| ICP-2 (David) | EU AI Act compliance deadline OR CISO blocks Tavily/Exa OR regulator asks "show me your retrieval logs" | 30 days from RFP to signed self-host pilot |
| ICP-3 (Anika) | Retraction tied to URL rot OR AI-misinformation story OR Webrecorder community thread | 5 minutes to first signed snapshot |

## Persona-name decision

The ICP names changed on 2026-05-28 from the old Maya / Priya / David (indie / Seed-CTO / Series-B) framing to the verifiable-retrieval framing above. **Priya is reused** (she went from "Seed/A CTO" to "regulated-AI startup eng lead") because the previous Priya cohort overlapped substantially with the new ICP-1. **David is reused** (he moved from "Series B+ AI infra buyer" to "regulated-company AI platform director") for the same reason. **Maya was retired** — Anthropic's free native `web_search` and Codex CLI search ate her wedge. **Anika is new** — ICP-3 did not exist before, because the previous positioning had nothing to offer the citation-integrity community.

Cross-references:
- See [JTBD](./jtbd.md) for the job each persona hires UnSearch to do.
- See [GTM](./gtm.md) for how we reach each persona by phase.
- See [Pricing](./pricing.md) for the tier each persona buys.
- See [Sales playbook](./sales-playbook.md) for the motion that closes ICP-1 and ICP-2.
