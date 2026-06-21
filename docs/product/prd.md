# UnSearch — PRD

> **Scope:** The UnSearch product as a whole — the verifiable-retrieval API + MCP server and the supporting dashboard/self-host. Feature-level status lives in [feature-matrix.md](./feature-matrix.md); ordered delivery in [roadmap.md](./roadmap.md).

## Goal
Let a developer building a regulated-AI agent retrieve from the web and get back, per result, a signed citation envelope + content-addressable snapshot they can replay and prove months later — so that the team can pass their own customer's audit (EU AI Act Article 12, FDA, court) without hand-rolling a 5-vendor provenance stack. Outcome target: a regulated-AI team adopts UnSearch as the single retrieval+provenance layer and retires their custom snapshot/grader/provenance glue.

## Users & jobs
- **ICP-1 — engineering lead at a regulated-AI startup (wedge).** Job: ship pinnable, reproducible citations into a vertical AI product fast, so their buyer's compliance team signs off.
- **ICP-2 — AI platform director at a regulated incumbent (revenue base).** Job: get in-perimeter, key-controlled, long-retention verifiable retrieval before EU AI Act enforcement.
- **ICP-3 — citation-integrity research/journalism engineer (distribution/credibility).** Job: snapshot cited sources so reproducibility survives bit rot.

Detail in [jtbd.md](./jtbd.md), [../strategy/icp.md](../strategy/icp.md), [user-journey.md](./user-journey.md).

## Requirements
### Must have
- [x] Web search returning a signed citation envelope per result (`/api/v1/search`)
- [x] Content-addressable snapshot store (R2 self/hosted, sha256-addressed, WACZ-aligned)
- [x] Signed citation envelope, HMAC v1, WACZ-Auth-aligned schema
- [x] Claim verification with span-level evidence + confidence (`/api/v1/verify/claim`)
- [x] Citation diff / snapshot pin (`/api/v1/verify/citation`)
- [x] Per-API-key audit log (`/api/v1/audit`)
- [x] MCP server with built-in free tier, no signup (`npx @unsearch/mcp-server`, hosted `/mcp`)
- [x] SDKs: Python (sync+async), TypeScript/edge, LlamaIndex retriever
- [x] Apache 2.0, self-hostable on Cloudflare Workers + Containers
- [ ] Hosted edge + dashboard live on `api.unsearch.dev` / `app.unsearch.dev` (domain activation in flight)
- [ ] Cloudflare Containers deploy of FastAPI + SearXNG sidecar enabled in `wrangler.toml`

### Should have
- [x] Neural/semantic search, multi-engine SearXNG aggregation, scraping/extraction/deep crawl
- [x] RAG over Cloudflare Vectorize with `bge-m3` embeddings + tiered Workers AI model selection
- [x] Stripe billing (checkout, portal, subscriptions)
- [ ] WACZ public-key signing (replacing HMAC v1, Month 7+)
- [ ] LangChain + Vercel AI SDK adapters
- [ ] BYO storage (S3/GCS/Azure) for snapshots on self-host

### Non-goals
- Consumer search UI / browser (we are an API + MCP)
- Internal-document search across Slack/Drive/Confluence (that is Glean's job)
- Aggressive scraping of login-walled / anti-bot sites (we respect robots.txt + ToS)
- Serving indie devs on non-regulated agents (native `web_search` is good enough for them)

## Success metrics
- ICP-1 paid logos: 0 → ~20 (the credibility threshold to sell ICP-2 self-host)
- MRR path $0 → $25K → $250K → $750K — see [../gtm/mrr-plan.md](../gtm/mrr-plan.md)
- MCP free-tier installs → hosted-paid conversion rate (target benchmarked in mrr-plan)
- First self-host v2 deal with BAA + DPA + SSO

## Open questions
- Public-key signing rollout timing vs. HMAC v1 deprecation path → Decisions DB
- Which beta endpoints (knowledge graph, monitoring, source credibility, deep research, predictive) graduate to GA vs. get cut → Decisions DB
- Compliance certification sequence (SOC 2 Type II, HIPAA BAA, ISO 42001) vs. revenue gating → Decisions DB

---
**Owner:** Rakesh Roushan · **Last reviewed:** 2026-06-21 · **Review by:** 2026-09-21
