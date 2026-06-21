# UnSearch Feature Matrix

> **Honesty policy:** "Shipped" means it's running in production with end-to-end tests. "In beta" means the code paths exist and respond, but coverage, edge cases, or polish are still being closed out. "Planned" means roadmap, not code. If you spot a discrepancy between this page and the actual repo, file an issue — we update this page on every release. See [ADR-0008](./adr/0008-honest-feature-status-policy.md).

> **Reposition note (2026-05-28):** UnSearch is "verifiable web retrieval for AI agents." The matrix below leads with verifiable-retrieval features (signed envelope, snapshot store, claim verification, audit log, MCP server) and treats raw search as the substrate. Tavily/Exa/Brave comparisons remain because the migration surface still exists, but the meaningful comparison columns are Anthropic native `web_search`, Codex CLI search, and Webrecorder/WACZ.

## Legend
- ✅ Shipped (production-ready)
- 🔶 In beta (functional, needs hardening — see [CHANGELOG](../CHANGELOG.md))
- 📋 Planned (on roadmap, not shipped)
- ❌ Not available
- 🚀 UnSearch differentiator

---

## Verifiable Retrieval (the wedge)

| Feature | UnSearch | Anthropic `web_search` | Codex CLI search | Tavily | Exa | Webrecorder |
|---------|----------|------------------------|------------------|--------|-----|-------------|
| **Signed citation envelope per result** | 🚀 (HMAC v1, WACZ-aligned) | ❌ | ❌ | ❌ | ❌ | ✅ (WACZ-Auth) |
| **Content-addressable snapshot store** | 🚀 (R2, sha256-keyed) | ❌ | ❌ (cache is OpenAI's) | ❌ | ❌ | ✅ (WACZ packages) |
| **Customer-controlled signing keys** | 🚀 (self-host) | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Claim verification with evidence spans** | 🚀 (`/verify/claim`) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Source-credibility scoring** | 🔶 (`/verify/source`) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Replayable audit log (per API key)** | 🚀 (`/audit`) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **10-year audit-log retention (EU AI Act Article 12)** | 🚀 (Enterprise / Self-host) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **WACZ export of any snapshot** | 📋 (Month 3) | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Differential snapshot diffs** | 📋 (Month 7+) | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Distribution surfaces

| Feature | UnSearch | Tavily | Exa | Brave | Linkup | Firecrawl |
|---------|----------|--------|-----|-------|--------|-----------|
| **MCP server (hosted at `api.unsearch.dev/mcp`)** | 🚀 (P0 — Week 3) | ✅ | ❌ | ✅ | ❌ | ✅ |
| **`npx @unsearch/mcp-server` (one-command install)** | 🚀 (P0) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **`verify_claim` as a first-class MCP tool** | 🚀 | ❌ | ❌ | ❌ | ❌ | ❌ |
| **TypeScript SDK** | ✅ (`@unsearch/sdk`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Python SDK (sync + async)** | ✅ (`unsearch` on PyPI) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **LlamaIndex retriever** | ✅ (`@unsearch/llamaindex`) | ✅ | 🔶 | ❌ | ❌ | ✅ |
| **LangChain integration** | 📋 (community PR in flight) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Vercel AI SDK adapter** | 📋 (Month 2) | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Search & Extraction (the substrate)

| Feature | UnSearch | Tavily | Exa | Brave |
|---------|----------|--------|-----|-------|
| **Basic Search** | ✅ | ✅ | ✅ | ✅ |
| **AI Answer Generation** | ✅ | ✅ | 🔶 | ✅ |
| **Neural / Semantic Search** | ✅ | ❌ | ✅ | 🔶 |
| **Auto-Prompting (Query Expansion)** | ✅ | ❌ | ✅ | 🔶 |
| **Highlights Extraction** | ✅ | ❌ | ✅ | ✅ |
| **Similar Content Discovery** | ✅ | ❌ | ✅ | ✅ |
| **Category / Date / Domain Filtering** | ✅ | 🔶 / ✅ / ✅ | ✅ / ✅ / ✅ | ✅ / ✅ / ✅ |
| **Multi-Engine Aggregation** | 🚀 (via SearXNG, 70+ engines) | ❌ | ❌ | ❌ |
| **JS-rendered / PDF / multi-engine scraping** | ✅ | ❌ | ❌ | ❌ |
| **Tavily-compatible drop-in** | ✅ (`/api/v1/agent/search`) | N/A | ❌ | ❌ |
| **Exa-compatible neural endpoints** | 🔶 | ❌ | N/A | ❌ |

---

## RAG / AI pipeline

| Feature | UnSearch | Tavily | Exa | Brave |
|---------|----------|--------|-----|-------|
| **Workers AI tiered models (gpt-oss-120b, qwq-32b, llama-3.3-70b, llama-3.1-8b)** | 🚀 | ❌ | ❌ | ❌ |
| **AI Reranking** | ✅ | ❌ | ✅ | 🔶 |
| **Custom Embeddings (bge-m3, 1024 dims)** | ✅ | ❌ | 🔶 | ❌ |
| **Multilingual** | ✅ | 🔶 | 🔶 | ✅ |
| **Content Safety Filtering** | ✅ | ❌ | ❌ | ✅ |
| **RAG over customer Vectorize namespace** | ✅ | ❌ | ❌ | ❌ |
| **SSE streaming for RAG** | ✅ | ❌ | ❌ | ❌ |

---

## Knowledge graph / Topic monitoring / Deep research (expansion bait, in beta)

These are 🔶 in beta — code paths exist, hardening in flight. Not lead-message material. See [JTBD](./strategy/jtbd.md) for how they fit ICP expansion.

| Feature | Status | Endpoint |
|---------|--------|----------|
| **Knowledge Graph — Entity Extraction** | 🔶 | `POST /api/v1/knowledge/extract` |
| **Knowledge Graph — Relationship Mapping** | 🔶 | `GET /api/v1/knowledge/graph` |
| **Topic Monitoring + Webhook Alerts** | 🔶 | `POST /api/v1/monitor/topics` |
| **Source Credibility** | 🔶 | `POST /api/v1/verify/source` |
| **Deep Research Agent** | 🔶 | `POST /api/v1/agent/research` |
| **Predictive Search** | 🔶 | `POST /api/v1/neural/predictive` |

UnSearch is **not** a Glean competitor — Glean searches inside your company, UnSearch retrieves from the open web with provenance. Internal-document connectors (Drive/Slack/Confluence/Notion/GitHub) are 📋 planned, but Enterprise-tier only, and only ship when a paying customer requires them.

---

## Infrastructure & Deployment

| Feature | UnSearch | Tavily | Exa | Brave | Anthropic `web_search` |
|---------|----------|--------|-----|-------|------------------------|
| **Open Source License** | 🚀 **Apache 2.0** | ❌ | ❌ | ❌ | ❌ |
| **Self-Hosted Option** | 🚀 (`wrangler deploy` from forked repo) | ❌ | ❌ | ❌ | ❌ |
| **Self-host on customer's own Cloudflare account** | 🚀 | ❌ | ❌ | ❌ | ❌ |
| **Cloudflare Containers (GA April 13 2026)** | 🚀 | ❌ | ❌ | ❌ | ❌ |
| **Workers / D1 / KV / R2 / Vectorize / Queues / DOs** | 🚀 (all wired) | ❌ | ❌ | ❌ | ❌ |
| **Docker Compose self-host** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **BYO storage (S3 / GCS) on self-host** | 📋 (Month 3) | ❌ | ❌ | ❌ | ❌ |
| **Global Distribution** | 🚀 (CF 300+ PoPs) | ✅ | ✅ | ✅ | ✅ |

---

## Privacy & Compliance

| Feature | UnSearch | Tavily | Exa | Brave | Anthropic `web_search` |
|---------|----------|--------|-----|-------|------------------------|
| **Zero-Retention Mode** | 🚀 (Pro+ tiers) | ❌ | ❌ | ❌ | N/A |
| **Customer-Controlled Signing Keys** | 🚀 (self-host) | ❌ | ❌ | ❌ | ❌ |
| **Data Sovereignty (self-host on customer perimeter)** | 🚀 | ❌ | ❌ | ❌ | ❌ |
| **GDPR DPA Available** | ✅ | ✅ | ✅ | ✅ | Via Anthropic ToS |
| **HIPAA BAA** | 📋 (Month 6) | ❌ | ❌ | ❌ | ❌ |
| **SOC 2 Type I** | 📋 (Month 4) | ✅ | ✅ | ❌ | ✅ |
| **SOC 2 Type II** | 📋 (Month 9) | ✅ | ✅ | ❌ | ✅ |
| **ISO 42001** | 📋 (Month 9) | ❌ | ❌ | ❌ | ❌ |
| **EU AI Act Article 12 logging-ready** | 🚀 (10-year retention on self-host / Enterprise) | ❌ | ❌ | ❌ | ❌ |

---

## Pricing & commercial

See [pricing](./strategy/pricing.md) for the full rationale.

| Aspect | UnSearch | Tavily | Exa | Brave | Anthropic `web_search` |
|--------|----------|--------|-----|-------|------------------------|
| **Free Tier (verified searches/mo)** | 🚀 5,000 + 1,000 snapshots + 100 verifications | 1,000 | 1,000 | None (paid since Feb 2026) | Free at Claude usage tier |
| **Self-Host annual contract** | 🚀 $24K v1 / $99K v2 | ❌ | ❌ | ❌ | ❌ |
| **Median 100K-search hosted cost** | $49 (Growth — signed + verified) | ~$700 (unsigned) | ~$700 (unsigned) | ~$500 (unsigned) | Free at tier |
| **Public 12-month price-commitment** | 🚀 | ❌ | ❌ (raised prices Mar 2026) | ❌ (killed free tier Feb 2026) | N/A (vendor model) |

---

## API endpoint summary

### Verifiable Retrieval (the wedge) — Shipped + in beta

```
POST /api/v1/search             # ✅ Native search with signed envelope per result
POST /api/v1/agent/search       # ✅ Tavily-compatible drop-in (compatibility surface)
POST /api/v1/agent/extract      # ✅ Extract with envelope
POST /api/v1/agent/research     # 🔶 Multi-step research with audit trail
POST /api/v1/verify/citation    # 📋 (Week 2) Snapshot pin + live diff
POST /api/v1/verify/claim       # 📋 (Week 2) Span-level claim grading
POST /api/v1/verify/source      # 🔶 Source credibility
GET  /api/v1/audit              # 📋 (Week 2) Per-API-key audit log
```

### MCP transport — P0 Week 3

```
GET  /mcp                       # 📋 (Week 3) Streamable HTTP MCP server
                                #   Tools: search, extract, research, verify_claim
```

### Neural / Exa-compatible — Shipped

```
POST /api/v1/neural/search      # ✅ Semantic search
POST /api/v1/neural/similar     # ✅ Similar content
POST /api/v1/neural/highlights  # ✅ Extract highlights
GET  /api/v1/neural/categories  # ✅ List categories
POST /api/v1/neural/predictive  # 🔶 In beta
```

### RAG — Shipped

```
POST /api/v1/rag/query          # ✅ RAG over Vectorize (SSE streaming)
POST /api/v1/rag/ingest         # ✅ Document ingest
```

### Knowledge / Monitoring — In beta

```
POST /api/v1/knowledge/extract  # 🔶 Entity extraction
POST /api/v1/knowledge/search   # 🔶 Knowledge search
POST /api/v1/knowledge/people   # 🔶 People search
GET  /api/v1/knowledge/graph    # 🔶 Knowledge graph
POST /api/v1/monitor/topics     # 🔶 Topic monitor + webhook fan-out
```

---

## Architecture

### Traditional search API (Tavily / Exa)
```
User → API Gateway → Single Region → Response (no envelope, no snapshot)
```

### UnSearch verifiable retrieval
```
User → Cloudflare Edge (300+ PoPs)
         ↓
    Hono Worker (auth / rate-limit / KV cache / MCP transport)
         ↓
    Service binding → Cloudflare Container (GA, active-CPU billing)
         ├── FastAPI (search / extract / verify / audit)
         └── SearXNG sidecar (70+ engines)
                  ↓
    R2: content-addressable snapshots (sha256-keyed, WACZ-aligned)
    D1: users, API keys, plans, audit log, citation envelopes
    KV: result cache (TTL per plan)
    Vectorize: RAG per customer namespace
    Workers AI: llama-3.3-70b grader for verify/claim
```

See [Cloudflare architecture](./cloudflare-architecture.md) for the full diagram and [`docs/citation-envelope.md`](./citation-envelope.md) for the envelope schema.

---

## Migration / compatibility

The Tavily-compatible drop-in stays as a compatibility surface (ADR-0003). New customers should lead with `verify_claim`; existing Tavily migrations are not blocked.

- [Migrate from Tavily](./migration/from-tavily.md)

For strategy context behind these features, see [strategy docs](./strategy/README.md).
