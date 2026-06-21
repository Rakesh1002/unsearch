---
title: Value Proposition
description: Pains/gains × pain-relievers/gain-creators for the three ICPs
---

> Last reviewed: 2026-05-28 · Next review: 2026-08-28

This is the value-proposition canvas for UnSearch's three personas after the 2026-05-28 reposition to verifiable retrieval. See [ICP](./icp.md) and [JTBD](./jtbd.md) first if persona names look unfamiliar.

## ICP-1 — Priya the regulated-AI startup eng lead

### Customer profile

| Jobs | Pains | Gains |
|------|-------|-------|
| Ship a legal-AI / medical-RAG / fintech-research agent that defends every cited source | Tavily / Exa / Firecrawl return text, no signed envelope; first customer asks for "what did the agent see?" and you have nothing | Working MCP install in 60 seconds with signed envelope on every result |
| Keep eng team focused on product, not provenance plumbing | 1–2 FTE equivalents lost to Playwright + S3 + Postgres provenance + NLI grader glue | Replace the entire duct-tape stack with one primitive |
| Pass an EU AI Act / SOC 2 / partner-firm review without re-architecting | Closed vendors fail the review; native Anthropic search isn't auditable | Self-host inside their own CF account when the review demands it |
| Look defensible in a YC AI Demo Day, investor pitch, or partner conversation | "We use Tavily" sounds commodity; "we use Anthropic native search" is not enterprise-defensible | "We ground every claim in customer-pinned, signed citations" is a credible AI-engineering story |
| Not get fired when a citation is challenged | Mata v. Avianca-style risk; Q1 2026 $145K sanctions; Harvey AI 1-in-6 still hallucinate | Audit-log every retrieval; produce a signed envelope on demand |

### Value map

| Products & services | Pain relievers | Gain creators |
|---------------------|----------------|---------------|
| MCP server at `api.unsearch.dev/mcp` + `npx @unsearch/mcp-server` | One-command onboarding; no signup form between intent and proof | Evaluate UnSearch with a real agent task in 30 seconds |
| Signed citation envelope per result (WACZ-aligned) | First customer's "show me what you saw" request becomes a 30-second API call | Defensible audit trail without building one in-house |
| `verify_claim` endpoint with span-level evidence | NLI / SelfCheckGPT graders deprecated; one API call replaces them | Customer-facing "claim → evidence span → confidence" UI |
| R2 snapshot store, content-addressable by sha256 | URL rot stops breaking customer-facing demos | Replay any historical retrieval |
| Free tier 5,000 verified searches/mo | Demo is not blocked by quota; PoC traffic is free | First successful verified result <5 minutes |
| Pro at $19/mo, Growth at $49/mo | Below the credit-card-without-thinking threshold | Smooth ramp $19 → $49 → $149 → enterprise |
| Apache 2.0 + 12-month price-notice commitment | Vendor-lock-in objection eliminated in customer's security review | "We use Apache-2.0 retrieval infra" is a credible sales answer |
| LlamaIndex retriever + LangChain / Vercel AI SDK adapters | No glue code | Production agent code in <1 hour |
| Self-host on Cloudflare Containers GA | First ICP-2-style customer asks for "runs in our perimeter"; you can say yes | Expansion lever — same code paths hosted vs self-hosted |

**Switching cost analysis for Priya:**

- From Tavily + Firecrawl + custom snapshot stack to UnSearch via MCP: < 2 hours for first proof; ~1–2 days to fully migrate a production agent and decommission the duct-tape stack.
- From Anthropic native `web_search` (compliance-blocked): no migration; UnSearch is the answer they go to *because* they cannot use the native tool.
- From rolling-their-own WACZ snapshots + Webrecorder: < 1 day; UnSearch envelope is WACZ-aligned, so existing tooling reads it natively.

## ICP-2 — David the regulated-company AI platform director

### Customer profile

| Jobs | Pains | Gains |
|------|-------|-------|
| Pass the next AI committee / EU AI Act / SOC 2 / regulator review | "Closed-source SaaS retrieval, data leaves perimeter" is a non-starter; native Anthropic search same | Apache 2.0 self-host on customer's own CF account; customer-controlled signing keys |
| Stand up internal LLM agents without re-architecting every six months | Each new compliance requirement reshapes the stack | Single primitive that survives audit + DPI + BAA + DPA + SSO conversations |
| Defend an AI-assisted decision to a regulator months later | Manual S3 snapshots + spreadsheet provenance break under audit pressure | Retain audit log up to 10 years; WACZ export for forensic review |
| Preserve internal velocity for LLM features | Compliance blocks every external API call | UnSearch deployment is configurable to never call third-party endpoints (BYO storage, BYO grader) |
| Hire and retain AI platform engineers | Engineers leave when their work is "glue maintenance" | Engineers ship features, not provenance plumbing |

### Value map

| Products & services | Pain relievers | Gain creators |
|---------------------|----------------|---------------|
| Self-host on customer's own Cloudflare account in < 30 minutes | Legal review passes — vendor lock-in and data residency objections eliminated | "We run our own retrieval infra" — defensible in regulator conversation |
| Customer-controlled HMAC v1 signing key (PKI v2 in Month 7+ roadmap) | Cryptographic provenance owned by customer, not vendor | Forensic evidence stands up in court / regulator audit |
| 10-year audit-log retention on Enterprise tier | EU AI Act Article 12 / 10-year documentation requirement met | Auditor receives replayable WACZ exports in minutes, not weeks |
| BAA / DPA / MSA templates pre-prepped | Procurement closes a $50K–$200K self-host contract in 30–60 days instead of 6 months | Standardized terms reduce founder/AE legal cycle time |
| SOC 2 Type II on roadmap (Month 9); HIPAA BAA-ready (Month 6) | Compliance team has a roadmap they can plan around | Renewal lift on year two |
| Workers AI grader for `verify_claim` (no third-party LLM call) | "We do not send retrieval data to external LLM providers" — true for self-host | Defensible in a CISO review |
| BYO storage (S3 / GCS) for snapshot store on self-host | Customers who cannot use R2 still onboard | Removes infra-vendor objection |
| Dedicated Container replicas + dedicated Durable Object pool on Enterprise | Predictable latency in production | SLA-able 99.9% uptime |

**Switching cost analysis for David:**

- From homegrown Splunk + S3 + spreadsheets to UnSearch self-hosted: 1–4 weeks (deployment + integration + audit-log import + first end-to-end audit dry run).
- From closed-source agent retrieval vendor to UnSearch self-hosted: 4–8 weeks (compliance has to re-approve the new vendor, but UnSearch's self-host posture is the lever that gets approval).
- From "we cannot do AI retrieval at all" to UnSearch self-hosted: green-field deployment; UnSearch is the answer that unlocks the LLM agent in the first place.

## ICP-3 — Anika the citation-integrity research / journalism engineer

### Customer profile

| Jobs | Pains | Gains |
|------|-------|-------|
| Cite a source in a piece without it rotting | Wayback Machine + manual Playwright + spreadsheets; no signed integrity guarantee | One API call per cited URL produces a signed, WACZ-exportable snapshot |
| Reproducibility: peer can replay the exact bytes | "It worked when I checked it" is not reproducible | Content-addressed snapshot; SHA256 + signature published alongside the citation |
| Use Apache-2.0 infra (institutional preference) | Closed vendors not fundable / acceptable for many grants | UnSearch is Apache-2.0; fork-able if needed |
| Publish quickly without infra babysitting | Webrecorder requires manual workflow; archival tools are not API-first | API + MCP + free tier sized for individual-researcher workloads |

### Value map

| Products & services | Pain relievers | Gain creators |
|---------------------|----------------|---------------|
| Free tier 5K verified searches + 1K snapshots + 100 verifications | Individual researcher / small newsroom workflow fits Free indefinitely | Zero-friction adoption; ambassador effect for ICP-1 / ICP-2 |
| WACZ export of any signed snapshot | Drop into Webrecorder / ReplayWeb.page / IIPC workflows | Inherits the broader provenance ecosystem |
| MCP server | Use from any MCP-compatible tool (Claude Code, Cursor, custom CLIs) | Lower technical bar to entry |
| Apache 2.0 + Webrecorder-aligned signing | Fork-able; auditable; cite-able in academic paper | Reputation surface for the project |

**Why ICP-3 matters even at low ACV:** ICP-3 customers produce the public artifacts (a retraction-tracking news piece, a Bellingcat investigation that uses UnSearch, a Reproducibility Project dashboard) that get UnSearch in front of ICP-1 and ICP-2 buyers without sales effort.

## How the "extra surfaces" fit

UnSearch ships more than core verifiable retrieval — neural search, knowledge-graph, topic monitoring, deep research agent, predictive search. These are **expansion bait, not lead messages**.

- **For Priya (ICP-1):** introduce in the founder onboarding session as "things you can layer on as your agent matures." They become the reason Growth customers move to Scale.
- **For David (ICP-2):** they are the procurement justification for Enterprise pricing — "one vendor for verifiable retrieval + monitoring + verification + knowledge-graph."
- **For Anika (ICP-3):** mostly irrelevant; she uses `search` + `verify_claim` and not much else.

Anything currently marked "in beta" in [feature-matrix](../feature-matrix.md) is described as "in beta" in customer conversations. We do not over-claim. (See ADR-0008 truthfulness rule.)

## What the value prop will *not* include

These are common temptations that erode credibility:

- Generic "saves you time" framing without a measured outcome.
- Generic "enterprise-grade reliability" before having an enterprise SLA.
- "AI-first" or "next-generation" — see [Positioning](./positioning.md) vocabulary discipline.
- "Trust" without a primitive backing it — signed envelopes back it; the word alone does not.
- "Defensible" without a worked example — every "defensible" claim needs a worked customer story or a regulatory citation.

Cross-references:
- See [ICP](./icp.md) for the personas this canvas applies to.
- See [JTBD](./jtbd.md) for the underlying jobs.
- See [User journey](./user-journey.md) for where each pain reliever shows up in the funnel.
- See [Pricing](./pricing.md) for the tier math behind the cost story.
