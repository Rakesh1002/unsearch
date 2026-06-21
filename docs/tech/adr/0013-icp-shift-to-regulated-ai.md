# ADR-0013: ICP shift to regulated AI

- Status: Accepted
- Date: 2026-05-28
- Deciders: @Rakesh1002

## Context

The prior ICP set (documented in `docs/strategy/icp.md` before 2026-05-28) was:

- **Persona A — Maya the AI-Native Indie**: pre-seed to Series A, 2–10 engineers, building generic AI agents, paying $30–200/mo on Tavily/Exa.
- **Persona B — Priya the Seed/A CTO**: 5–25 person AI startup, building generic vertical AI, $500–3K/mo on closed retrieval vendors.
- **Persona C — David the Series B+ Buyer**: 100–500 person AI infra or vertical AI company, $5K–30K/mo on Glean + Exa/Tavily.

That framing optimized for *volume of acquisition* (Maya as the wedge) and *generic agent infra spend* (Priya / David as the revenue base). It worked while the search-API-for-agents category was differentiated on price + open-source license.

After Anthropic shipped native `web_search` (free at Claude API tier) and OpenAI shipped Codex CLI's first-party search (default-on, free for Codex users), Maya stopped being a viable wedge: she could now use free LLM-vendor search. UnSearch's TAM for Maya effectively evaporated.

Meanwhile, the rest of the market evolved:

- Legal-AI startups (Harvey ($8B), Casetext-derivatives, contract-review agents) hit a hallucinated-citation crisis. Q1 2026: $145K in US court sanctions; the April 4 2026 Oregon sanction alone was $110K for 23 fabricated citations.
- Medical-RAG buildouts (clinical decision support, drug-interaction agents, FDA-submission AI) hit measurable hallucination floors — 40–60% fabricated references without retrieval, ~30% remaining error rate with naive RAG.
- The EU AI Act Aug 2026 enforcement deadline made provenance documentation a regulatory requirement, not a nice-to-have. Article 12: automatic event logging, 6-month log retention minimum, 10-year documentation retention, €15M / 3% turnover penalty.
- Regulated-AI startups (legal / medical / fintech / insurance / govtech) — a defined and addressable cohort of ~5,000 globally — could not use native LLM search because (a) citations weren't customer-pinnable, (b) snapshots weren't reproducible, (c) data left the perimeter, (d) audit retention wasn't customer-controlled.

The market split in two: indie / non-regulated agent builders went to free native LLM search; regulated-AI builders had no good infra option and were duct-taping the same five-vendor stack from scratch per company.

ADR-0009 made verifiable retrieval the product surface. This ADR formalizes the corresponding ICP shift.

## Decision

UnSearch's ICP is **regulated AI**, ordered:

- **ICP-1: Priya, regulated-AI startup eng lead** (replaces prior Persona B, narrowed to regulated verticals). Series Seed–B, 10–80 person AI startup building vertical AI for legal / medical / finance / insurance / research / compliance. WTP $500–5K/mo hosted. Buying trigger: first customer asks for audit logs, first hallucination caught by a customer, EU AI Act compliance memo.

- **ICP-2: David, regulated-company AI platform director** (replaces prior Persona C, refocused on regulated companies retrofitting AI). 200–10,000-person regulated company: bank, hospital system, insurance carrier, BigLaw firm, pharma, asset manager. WTP $5–50K/mo hosted, $20–200K/yr self-host with BAA / DPA / SSO. Buying trigger: EU AI Act August 2026 deadline; CISO blocks Tavily / Exa for data-residency; AI committee mandates "auditable retrieval"; regulator inquiry post-incident.

- **ICP-3: Anika, citation-integrity research / newsroom engineer** (new persona). NIH-funded research lab, citation-integrity newsroom, academic-integrity tool startup, fact-check publisher, Webrecorder-adjacent civic-tech project. Low ACV, high distribution + credibility leverage.

- **Maya is retired.** Anthropic native `web_search` and Codex CLI search occupy her wedge. UnSearch does not compete for her.

Practical implementation:

- Strategy docs (`docs/strategy/icp.md`, `jtbd.md`, `value-prop.md`, `gtm.md`, `sales-playbook.md`, `user-journey.md`, `pricing.md`, `mrr-plan.md`) rewrite around these three personas.
- Persona-specific entry-URL pattern updated: `unsearch.dev` (default → ICP-1), `unsearch.dev/eu-ai-act` (→ ICP-2), `unsearch.dev/for-research` (→ ICP-3).
- The MRR plan's first-10-customer hypothesis shifts from "indie devs hitting Tavily ceiling" to "regulated-AI startup engineering leads."
- The sales playbook adds a Self-host motion (v1 $24K/yr, v2 $99K/yr) which becomes the load-bearing revenue pillar — see [pricing](../strategy/pricing.md) and [mrr-plan](../strategy/mrr-plan.md).

## Consequences

We commit to:

- A narrower top-of-funnel and a higher average ACV. The MRR plan's target shifts from "many small customers" to "fewer larger customers" — see [mrr-plan](../strategy/mrr-plan.md).
- A compliance-grade product story: SOC 2 Type I (Month 4) → Type II (Month 9); HIPAA BAA (Month 6); EU GDPR DPA in market immediately; ISO 42001 (Month 9–12).
- An ICP-2 sales motion that requires founder-led closing and (from Month 7) a commission-only AE — significantly more time per deal than the indie-dev funnel.
- A roadmap that prioritizes self-host UX, audit-log retention controls, customer-controlled signing keys, and BYO storage over generic indie-dev features (deeper LangGraph integrations, more SDK examples, prompt-engineering helpers).
- Disqualifying the prior Maya cohort. Indie devs evaluating UnSearch are welcome to use Free indefinitely (ICP-3-style), but the product is not optimized for them.

What we knowingly give up:

- The 2–5K-company global Maya TAM. Native LLM search ate it; we don't compete.
- A bottom-up viral motion driven by indie-dev word of mouth. We compensate with MCP-native distribution (ADR-0012) that reaches ICP-1 engineering leads where they already work, plus an ICP-3 ambassadorship that drives credibility for ICP-1 / ICP-2 adoption.
- A simpler "drop in for Tavily" sales pitch. The replacement pitch ("verifiable retrieval for AI agents") requires more education in the first conversation but anchors against a sharper pain.

## Alternatives considered

**1. Keep all three prior personas, add regulated-AI as a fourth.** Rejected: solo founder cannot serve four distinct ICPs. The Maya wedge is dead; pretending otherwise wastes runway. Disciplined disqualification is the lever.

**2. Reposition entirely to vertical legal-AI or medical-RAG (a single regulated vertical).** Rejected: deeper but narrower than necessary. Verifiable retrieval is a horizontal primitive that serves multiple regulated verticals — owning the primitive is more defensible than owning one vertical's application layer (where Harvey, Hebbia, Casetext already operate).

**3. Pivot to enterprise-only (skip ICP-1 startups).** Rejected: enterprise-only cycles are 6–12 months; runway-fatal at solo-founder velocity. ICP-1 startups close in 7–60 days and produce the customer-story credibility that ICP-2 needs to evaluate UnSearch in the first place.

**4. Keep "indie dev" as ICP-3 with EU AI Act / regulated-AI added as ICP-1/2.** Rejected: indie devs are a distraction, not an ambassador cohort. ICP-3 (citation-integrity research / journalism) is a genuinely different community whose public artifacts (a Bellingcat investigation, a Reproducibility Project dashboard) drive ICP-1 / ICP-2 inbound; indie devs do not produce the same kind of artifacts.

**5. Keep the prior ICP framing publicly and ship the verifiable-retrieval product to that audience.** Rejected: misalignment between positioning and ICP confuses everyone — the buyer who reads "for AI-native indies" but sees a SOC 2 / BAA / 10-year retention feature set; the SOC 2 / BAA buyer who reads "10× cheaper Tavily alternative" and stops reading. The ICP and the product surface have to move together.

## Cross-references

- [ADR-0009](./0009-verifiable-retrieval-as-product-surface.md) — product-surface pivot this ICP supports
- [ADR-0012](./0012-mcp-first-distribution.md) — distribution channel that reaches ICP-1 directly
- [`docs/strategy/icp.md`](../strategy/icp.md) — full ICP-1 / ICP-2 / ICP-3 personas
- [`docs/strategy/mrr-plan.md`](../strategy/mrr-plan.md) — revenue math with new ICP
- [`docs/strategy/gtm.md`](../strategy/gtm.md) — channels per ICP
- [`docs/strategy/sales-playbook.md`](../strategy/sales-playbook.md) — sales motion for ICP-1 + ICP-2
