# UnSearch Feature Matrix

> **Honesty policy:** "Shipped" means it's running in production with end-to-end tests. "In beta" means the code paths exist and respond, but coverage, edge cases, or polish are still being closed out. "Planned" means roadmap, not code. If you spot a discrepancy between this page and the actual repo, file an issue — we update this page on every release.

## Legend
- ✅ Shipped (production-ready)
- 🔶 In beta (functional, needs hardening — see [CHANGELOG](../CHANGELOG.md))
- 📋 Planned (on roadmap, not shipped)
- ❌ Not available
- 🚀 UnSearch differentiator

---

## Search Features

| Feature | UnSearch | Tavily | Exa | Brave |
|---------|----------|--------|-----|-------|
| **Basic Search** | ✅ | ✅ | ✅ | ✅ |
| **AI Answer Generation** | ✅ | ✅ | 🔶 | ✅ |
| **Neural/Semantic Search** | ✅ | ❌ | ✅ | 🔶 |
| **Auto-Prompting (Query Expansion)** | ✅ | ❌ | ✅ | 🔶 |
| **Highlights Extraction** | ✅ | ❌ | ✅ | ✅ |
| **Similar Content Discovery** | ✅ | ❌ | ✅ | ✅ |
| **Category Filtering** | ✅ | 🔶 | ✅ | ✅ |
| **Date Filtering** | ✅ | ✅ | ✅ | ✅ |
| **Domain Filtering** | ✅ | ✅ | ✅ | ✅ |
| **Multi-Engine Aggregation** | 🚀 (via SearXNG) | ❌ | ❌ | ❌ |
| **Predictive Search** | 🔶 | ❌ | ❌ | ❌ |

---

## AI / RAG Features

| Feature | UnSearch | Tavily | Exa | Brave |
|---------|----------|--------|-----|-------|
| **Basic Answer Generation** | ✅ | ✅ | 🔶 | ✅ |
| **Model Selection** | ✅ (Workers AI models) | ❌ | ❌ | 🔶 |
| **Cloudflare Workers AI (gpt-oss-120b, qwq-32b, llama-3.3-70b)** | 🚀 | ❌ | ❌ | ❌ |
| **AI Reranking** | ✅ | ❌ | ✅ | 🔶 |
| **Custom Embeddings (bge-m3)** | ✅ | ❌ | 🔶 | ❌ |
| **Multilingual** | ✅ | 🔶 | 🔶 | ✅ |
| **Content Safety Filtering** | ✅ | ❌ | ❌ | ✅ |

---

## Advanced Capabilities (In Beta)

These are functional in the codebase but still being hardened. Use in production with eyes open and please file issues.

| Feature | Status | Endpoint |
|---------|--------|----------|
| **Knowledge Graph — Entity Extraction** | 🔶 | `POST /api/v1/knowledge/extract` |
| **Knowledge Graph — Relationship Mapping** | 🔶 | `GET /api/v1/knowledge/graph` |
| **Topic Monitoring + Webhook Alerts** | 🔶 | `POST /api/v1/monitor/topics` |
| **Fact Verification — Claim Check** | 🔶 | `POST /api/v1/verify/claim` |
| **Fact Verification — Source Credibility** | 🔶 | `POST /api/v1/verify/source` |
| **Deep Research Agent** | 🔶 | `POST /api/v1/agent/research` |
| **Predictive Search** | 🔶 | `POST /api/v1/neural/predictive` |

These features differentiate UnSearch from Tavily/Exa/Brave (none of whom ship them), but they are not yet at the same maturity bar as our core search. See [CHANGELOG `[Unreleased]`](../CHANGELOG.md) for what's being closed out next.

---

## Enterprise / Glean-Adjacent Features

UnSearch is **not** a Glean competitor — Glean searches inside your company, UnSearch searches the open web. The features below are scoped narrowly:

| Feature | UnSearch | Glean |
|---------|----------|-------|
| **Internal Document Connectors (Drive/Slack/Confluence/Notion/GitHub)** | 📋 (planned) | ✅ |
| **Knowledge Graph over the public web** | 🔶 | ❌ (not their scope) |
| **Enterprise SSO** | 📋 (planned, Enterprise tier) | ✅ |
| **Team Permissions** | 📋 (planned, Enterprise tier) | ✅ |
| **Audit Logging** | 📋 (planned, Enterprise tier) | ✅ |

If you need internal-document search, [Glean](https://www.glean.com) is the right product. If you need open-web search for AI agents, that's us.

---

## Infrastructure & Deployment

| Feature | UnSearch | Tavily | Exa | Brave |
|---------|----------|--------|-----|-------|
| **Self-Hosted Option** | 🚀 (Apache 2.0) | ❌ | ❌ | ❌ |
| **Open Source License** | 🚀 **Apache 2.0** | ❌ | ❌ | ❌ |
| **Docker Deployment** | ✅ | ❌ | ❌ | ❌ |
| **Edge Computing (Cloudflare Workers)** | 🚀 | ❌ | ❌ | ❌ |
| **Global Distribution** | 🚀 (Cloudflare's 300+ PoPs) | ✅ | ✅ | ✅ |
| **Cloudflare Vectorize** | 🚀 | ❌ | ❌ | ❌ |
| **Cloudflare Queues** | 🚀 | ❌ | ❌ | ❌ |
| **Durable Objects (stateful sessions)** | 🚀 | ❌ | ❌ | ❌ |

---

## Privacy & Compliance

| Feature | UnSearch | Tavily | Exa | Brave |
|---------|----------|--------|-----|-------|
| **Zero-Retention Mode** | 🚀 (Pro+ tiers) | ❌ | ❌ | ❌ |
| **Data Sovereignty (self-host)** | 🚀 | ❌ | ❌ | ❌ |
| **GDPR-Compliant** | ✅ | ✅ | ✅ | ✅ |
| **SOC 2** | 📋 (Enterprise roadmap) | ✅ | ✅ | ❌ |
| **HIPAA Ready** | 📋 (Enterprise roadmap) | ❌ | ❌ | ❌ |

---

## Developer Experience

| Feature | UnSearch | Tavily | Exa | Brave |
|---------|----------|--------|-----|-------|
| **REST API** | ✅ | ✅ | ✅ | ✅ |
| **TypeScript SDK** | ✅ (`@unsearch/sdk`) | ✅ | ✅ | ✅ |
| **Python SDK** | ✅ (`unsearch` on PyPI) | ✅ | ✅ | ✅ |
| **LangChain Integration** | 📋 (PR in flight) | ✅ | ✅ | ✅ |
| **LlamaIndex Integration** | ✅ (`@unsearch/llamaindex`) | ✅ | 🔶 | ❌ |
| **MCP Server** | 📋 (next release) | ✅ | ❌ | ✅ |
| **Tavily API Compatibility** | 🚀 (drop-in) | N/A | ❌ | ❌ |
| **Exa API Compatibility** | 🔶 (neural endpoints) | ❌ | N/A | ❌ |
| **OpenAPI Docs** | ✅ | ✅ | ✅ | ✅ |
| **Webhook Support** | 🔶 (topic monitoring) | ❌ | ❌ | ❌ |

---

## Pricing

See [pricing](./strategy/pricing) for the full rationale.

| Aspect | UnSearch | Tavily | Exa | Brave |
|--------|----------|--------|-----|-------|
| **Free Tier (searches/mo)** | 🚀 5,000 | 1,000 | 1,000 | 2,000 (paid-only since Feb 2026) |
| **Self-Host (Unlimited)** | 🚀 $0 (Apache 2.0) | ❌ | ❌ | ❌ |
| **Median 100K-search cost (closed vendors)** | $49 (Growth) | ~$700 | ~$700 | ~$500 |
| **Enterprise** | Contact us | Custom | Custom | Custom |
| **Public Price-Commitment Statement** | 🚀 12-month notice on any increase | ❌ | ❌ (raised prices Mar 2026) | ❌ (killed free tier Feb 2026) |

Pricing data accessed 2026-05-23: [Tavily](https://www.tavily.com/pricing), [Exa](https://exa.ai/pricing), [Brave](https://api-dashboard.search.brave.com/documentation/pricing).

---

## API Endpoint Summary

### Tavily-Compatible (Drop-in Replacement) — ✅ Shipped

```
POST /api/v1/agent/search       # Tavily-shape search
POST /api/v1/agent/extract      # Content extraction
GET  /api/v1/agent/health       # Health check
```

### Exa-Compatible Neural Search — ✅ Shipped

```
POST /api/v1/neural/search      # Semantic search
POST /api/v1/neural/similar     # Similar content
POST /api/v1/neural/highlights  # Extract highlights
GET  /api/v1/neural/categories  # List categories
POST /api/v1/neural/predictive  # 🔶 In beta
```

### Knowledge Graph + Verification + Monitoring — 🔶 In Beta

```
POST /api/v1/knowledge/extract  # Entity extraction
POST /api/v1/knowledge/search   # Knowledge search
POST /api/v1/knowledge/people   # People search
GET  /api/v1/knowledge/graph    # Knowledge graph
POST /api/v1/monitor/topics     # Create topic monitor
POST /api/v1/verify/claim       # Fact verification
POST /api/v1/verify/source      # Source credibility
POST /api/v1/agent/research     # Deep research agent
```

### Internal-Document Connectors — 📋 Planned

```
POST /api/v1/connectors         # (Planned for Enterprise tier)
```

---

## Architecture Comparison

### Traditional (Tavily/Exa)
```
User → API Gateway → Single Region → Response
```

### UnSearch Edge Architecture
```
User → Cloudflare Edge (300+ PoPs)
         ↓
    Edge Worker (Router / Cache / Auth)
         ↓
    ┌────┴────┐
    │ Simple  │ → Workers AI → Response
    │ Query   │
    └─────────┘
    ┌────┴────┐
    │ Complex │ → Queue → Durable Object
    │ Research│              ↓
    └─────────┘      Background Processing
                            ↓
                     Webhook / Poll
```

See [Cloudflare architecture](./cloudflare-architecture.md) for the full diagram.

---

## Migration Guides

- [Migrate from Tavily](./migration/from-tavily.md)
- [Migrate from Exa](./migration/from-exa.md) (planned)
- [Migrate from Brave Search API](./migration/from-brave.md) (planned)

For strategy context behind these features, see [strategy docs](./strategy/README.md).
