# ADR-0009: Verifiable Retrieval as the product surface

- Status: Accepted
- Date: 2026-05-28
- Deciders: @Rakesh1002

## Context

The original UnSearch positioning ("open-source Tavily alternative, 10× cheaper") was anchored on price + drop-in compatibility for indie developers building agents. Three structural shifts in early 2026 made that wedge unsellable to the indie cohort:

1. **Anthropic shipped native `web_search` as a server-side tool** (default in Sonnet 4.6 / Opus 4.7) with 2026 Dynamic Filtering. Free at usage tier for Claude API customers.
2. **OpenAI Codex CLI ships first-party web search default-on**, backed by OpenAI's indexed cache.
3. **The MCP registry crossed 800 official servers and 13K+ total**; Firecrawl, Exa, Tavily, Linkup all ship search MCPs. "MCP search" became table stakes.

Indie developers — the prior wedge — moved to native LLM search at zero cost. The "cheaper Tavily" wedge survives mechanically but no longer differentiates.

At the same time, three regulatory / litigation events opened a different, larger opening:

1. **Q1 2026 US court sanctions for AI-hallucinated legal citations crossed $145,000.** Largest single sanction: $110K, Oregon, April 4 2026.
2. **Harvey AI ($8B valuation) still hallucinates 1-in-6 queries**, demonstrating that even the leading legal-AI vendor hasn't solved citation grounding at the infra layer.
3. **EU AI Act Article 12 full enforcement begins August 2026.** Provenance documentation explicitly required; 6-month log retention minimum; 10-year documentation retention; penalty up to €15M or 3% of worldwide turnover.

Regulated buyers (legal-AI startups, medical RAG, fintech research bots, insurance underwriting AI, gov-tech, BigLaw, banks, pharma) **cannot use native LLM search** because (a) citations aren't customer-pinnable, (b) snapshots aren't reproducible, (c) data leaves the customer's perimeter, (d) there is no audit log retention guarantee. They are forced to hand-roll a citation infrastructure stack from Tavily / Exa + Firecrawl / Jina + Playwright + custom NLI grader + Postgres provenance table — 1–2 FTEs of glue per company.

No third-party infrastructure owns "verifiable retrieval for AI agents" as a primitive. Webrecorder owns the archivist workflow primitive (WACZ) but not the agent shape. Tavily/Exa/Brave own the agent shape but not the provenance primitive. Harvey/Hebbia/V7 Go own the application tier but cannot be embedded by ICP-1 builders. Braintrust/Patronus monitor outputs post-hoc but don't fix the input.

## Decision

UnSearch's product surface is **Verifiable Retrieval Infrastructure**, not "search API for agents." The four jobs the product owns:

1. **Source pinning** — content-addressable snapshot of the exact bytes at retrieval time.
2. **Signed citations** — a signed envelope per result with `{url, sha256, fetched_at, snapshot_key, signature}` that downstream pipelines and auditors can verify.
3. **Claim verification** — `{claim, source_url} → {supported, evidence_spans, confidence}` with the snapshot re-fetched and graded.
4. **Replay / audit** — per-API-key audit log of every retrieval, with WACZ-style replay months later.

These four jobs together — not "search" alone — are the product. Search is the substrate.

Practical implementation:

- Every result from `/api/v1/search`, `/api/v1/agent/search`, and the MCP `search` tool returns an inline `citation_envelope`.
- `/api/v1/verify/citation` returns pinned snapshot + live diff.
- `/api/v1/verify/claim` returns span-level grading via Workers AI llama-3.3-70b.
- `/api/v1/audit` exposes the per-API-key audit log.
- The MCP server exposes `verify_claim` as a first-class tool, not just `search`.

The Tavily-compatible drop-in `/api/v1/agent/search` (ADR-0003) stays as a compatibility surface but is no longer the lead onboarding path. Its ADR status is downgraded from "primary positioning" to "compatibility surface."

## Consequences

We commit to:

- Citation envelope schema as a permanent API contract. Breaking changes require an explicit ADR + v2 envelope co-existing with v1 for ≥12 months. Audit consumers depend on stability.
- `verify_claim` accuracy as a top-line product KPI tracked publicly via a quarterly "Hallucinated Citation Index" report.
- An R2 snapshot store on every tier — Free included. Free is not a crippled version of the wedge or the demo collapses.
- Workers AI llama-3.3-70b as the default grader (ADR-0004 tier "balanced") — changing this affects accuracy + cost simultaneously and requires a co-ADR.
- WACZ-Auth spec alignment for the envelope format (ADR-0011) so archivist + journalism + reproducibility ecosystems read our snapshots natively.

What we knowingly give up:

- The indie-dev TAM. Native LLM search ate it; trying to compete head-on wastes runway.
- The "Tavily-compatible" lead message. We keep the endpoint for SEO + customer-continuity, but it sits below the wedge in messaging hierarchy.
- The "10× cheaper" lead message. The claim is still true as a side-effect of SearXNG + active-CPU billing, but it stops being the hero on landing pages.
- A larger initial signup pool. Sharper wedge = smaller TAM, higher ACV, higher conversion. This is intentional.

## Alternatives considered

**1. Stay with "cheaper Tavily" positioning.** Rejected: Anthropic / OpenAI native search make this unwinnable for indie devs. Existing customers are not the lever; future cohorts are. The wedge no longer differentiates.

**2. Pivot to a separate verification-only product ("Signoff") layered on top of any search vendor.** Rejected: introducing a separate brand fragments the OSS flywheel and the MCP distribution surface. The verification primitive must live inside the retrieval primitive to demo end-to-end.

**3. Pivot to vertical applications (legal-AI / medical-RAG / fintech-research SaaS).** Rejected: Harvey, Hebbia, Casetext-derivatives, V7 Go already occupy the application tier. UnSearch is infra. Application-tier competition is a different motion, different ACV, different ICP — not adjacent.

**4. Pivot to hallucination monitoring (Braintrust / Patronus / Galileo overlap).** Rejected: monitoring is post-hoc; the wedge here is fixing the input primitive so there is less to monitor. Different category, different sales cycle.

**5. Add verification as a feature on top of the existing "search API" positioning.** Rejected: that framing buries the wedge below a commoditized lead message. The whole product surface must be verifiable retrieval; verification cannot be a checkbox at the bottom of the feature matrix.

## Cross-references

- [`docs/strategy/positioning.md`](../strategy/positioning.md) — new one-liner and pillars
- [`docs/strategy/market.md`](../strategy/market.md) — Q1 2026 incidents + EU AI Act forcing function
- [`docs/strategy/icp.md`](../strategy/icp.md) — Priya / David / Anika persona shifts driven by this ADR
- [ADR-0010](./0010-cloudflare-containers-as-origin-runtime.md) — runtime choice for the verifiable-retrieval implementation
- [ADR-0011](./0011-wacz-aligned-signed-envelope.md) — envelope format
- [ADR-0012](./0012-mcp-first-distribution.md) — distribution surface for the new positioning
- [ADR-0013](./0013-icp-shift-to-regulated-ai.md) — ICP implications
- [`docs/citation-envelope.md`](../citation-envelope.md) — schema spec
