# UnSearch Product Roadmap

> **How to read this doc:** This is the engineering roadmap. For the *commercial* story (ICP, pricing, GTM), see [strategy docs](./strategy/README.md). For the truthful per-feature status, see [feature matrix](./feature-matrix.md). The source of truth for what shipped in the last release is [CHANGELOG.md](../CHANGELOG.md) — anything in its `[Unreleased] — Deferred to follow-up` section is not yet live.

Roadmap is **ordered around ICP needs** (see [ICP](./strategy/icp.md)). Phase 1 (Persona A — indie devs) is the priority. Phase 2 (Persona B — Seed/A CTOs) follows. Phase 3 (Persona C — Series B+ buyers) lands once Personas A and B are converting.

## Current State Summary

**Version:** 2.0.0 (Cloudflare-native rewrite in flight — see [CHANGELOG `[Unreleased]`](../CHANGELOG.md))
**API Endpoints:** 75+
**AI Integration:** Cloudflare Workers AI
**Edge Infrastructure:** Cloudflare Workers, Vectorize, Queues, Durable Objects, D1, KV, R2

### Status legend
- ✅ Shipped (production, end-to-end tested)
- 🔶 In beta (code paths exist, hardening in flight)
- 📋 Planned (on this roadmap)

### Core capabilities — honest status

| Category | Features | Status |
|----------|----------|--------|
| **AI Search** | gpt-oss-120b, qwq-32b, llama-3.3-70b, model selection | ✅ |
| **Web Search** | SearXNG meta-search, multi-provider fallback | ✅ |
| **Neural Search** | Semantic search, auto-prompting, highlights (Exa-compatible neural endpoints) | ✅ |
| **Knowledge Graph** | Entity extraction, people search, relationship mapping | 🔶 (no Drive/Slack/Confluence/Notion/GitHub connectors yet) |
| **Topic Monitoring** | Durable Object + scheduled checks + webhook fan-out | 🔶 (webhook retry logic + at-scale testing remaining) |
| **Fact Verification** | Claim check, source credibility | 🔶 (pipeline functional, accuracy benchmarking ongoing) |
| **Scraping** | Static, JavaScript, PDF, multi-engine | ✅ |
| **Extraction** | Tables, entities, attributes | ✅ |
| **Crawling** | Deep crawl, mapping, change tracking | ✅ |
| **RAG** | Embeddings (bge-m3), Vectorize, research mode | ✅ |
| **Auth** | JWT, API keys | ✅ |
| **OAuth (Google + GitHub)** | Env keys in `.env.example`, no flow wired | 📋 (Week 1 ship — see strategy [user-journey](./strategy/user-journey.md)) |
| **Privacy** | Zero-retention mode, content safety | ✅ |
| **Edge Infrastructure** | Workers, Queues, Durable Objects, D1, KV, R2, Vectorize | ✅ |
| **Stripe billing** | Checkout + portal + subscription management | ✅ |
| **Stripe metered overage** | Schema fields present (`usage_records.search_overage`) | 📋 |
| **Dashboard `/team` and `/settings`** | Placeholder routes | 📋 (Month 2 ship) |
| **Deep Research Agent** | Durable Object skeleton + Workers AI | 🔶 (multi-step depth + citation polish remaining) |

---

## Competitive parity — honest status

We previously claimed "Glean parity ✅". That's not true — Glean searches inside-company corpora via connectors we haven't built. The corrected scope:

### Tavily compatibility — ✅ Shipped
The single most important parity claim. Drop-in replacement, same `client.search()` calls, one base-URL change. See [migration guide](./migration/from-tavily.md).

### Exa neural-endpoint compatibility — ✅ Shipped
| Feature | Status | Endpoint |
|---------|--------|----------|
| Neural/Semantic Search | ✅ | `POST /api/v1/neural/search` |
| Auto-Prompting | ✅ | `POST /api/v1/neural/search?use_autoprompt=true` |
| Highlights Extraction | ✅ | `POST /api/v1/neural/highlights` |
| Similar Content | ✅ | `POST /api/v1/neural/similar` |
| Category Filtering | ✅ | `GET /api/v1/neural/categories` |

### Knowledge / Verification / Monitoring — 🔶 In beta (NOT Glean parity)
| Feature | Status | Endpoint |
|---------|--------|----------|
| Entity Extraction | 🔶 | `POST /api/v1/knowledge/extract` |
| Knowledge Search | 🔶 | `POST /api/v1/knowledge/search` |
| People Search | 🔶 | `POST /api/v1/knowledge/people` |
| Knowledge Graph (public web) | 🔶 | `GET /api/v1/knowledge/graph` |
| Topic Monitoring | 🔶 | `POST /api/v1/monitor/topics` |
| Real-time Alerts (webhook) | 🔶 | Webhooks |
| Fact Verification | 🔶 | `POST /api/v1/verify/claim` |
| Source Credibility | 🔶 | `POST /api/v1/verify/source` |
| Batch Verification | 🔶 | `POST /api/v1/verify/batch` |
| Predictive Search | 🔶 | `POST /api/v1/neural/predictive` |
| Deep Research Agent | 🔶 | `POST /api/v1/agent/research` |
| Document Connectors (Drive/Slack/Confluence/Notion/GitHub) | 📋 Planned (Enterprise tier) | — |

---

## Cloudflare Edge Architecture

### Infrastructure Components ✅
| Component | Purpose | Status |
|-----------|---------|--------|
| **Workers** | Edge routing, API handling | ✅ Implemented |
| **Workers AI** | LLM, embeddings, reranking | ✅ Integrated |
| **Vectorize** | Vector database | ✅ Configured |
| **Queues** | Async task processing | ✅ Configured |
| **Durable Objects** | Stateful sessions | ✅ Implemented |
| **KV** | Edge caching | ✅ Configured |
| **R2** | Object storage | ✅ Configured |
| **D1** | Edge database | ✅ Schema ready |

### Edge Worker Structure
```
workers/
├── src/
│   ├── index.ts           # Main router
│   ├── types.ts           # Type definitions
│   ├── routes/
│   │   ├── search.ts      # Neural search routes
│   │   ├── research.ts    # Research agent routes
│   │   ├── monitor.ts     # Topic monitor routes
│   │   ├── connectors.ts  # Document connector routes
│   │   └── verify.ts      # Fact verification routes
│   ├── durable-objects/
│   │   ├── research-agent.ts    # Autonomous research
│   │   ├── topic-monitor.ts     # Real-time monitoring
│   │   └── session-manager.ts   # User sessions
│   └── utils/
│       ├── auth.ts        # Authentication
│       └── cors.ts        # CORS handling
├── wrangler.toml          # Cloudflare config
├── schema.sql             # D1 database schema
└── package.json           # Dependencies
```

---

## Immediate Action Items — ordered around ICP needs

Phase ordering matches [strategy/gtm.md](./strategy/gtm.md). Each item names the ICP it unblocks.

### P0 — Week 1 (unblocks Persona A — Maya)

These items are the prerequisites for the Show HN launch in [strategy/gtm.md](./strategy/gtm.md).

1. **MCP server (TypeScript)** published to npm + Anthropic MCP directory. Highest-leverage single artifact of 2026 (97M monthly SDK downloads — see [strategy/market.md](./strategy/market.md)).
2. ~~**Python SDK** published to PyPI as `unsearch`.~~ ✅ Shipped — sync + async client at [`apps/sdk-py`](../apps/sdk-py/README.md), ready for `pip install unsearch`.
3. **Polish `docs/migration/from-tavily.md`** — 5-minute migration headline, 3-line code diff, CTA to playground.
4. **Wire Google OAuth** (env keys are in `.env.example`; flow is not). Removes ~20% signup drop vs social-login baseline.
5. **Homepage hero rewrite** to the one-liner in [strategy/positioning.md](./strategy/positioning.md).
6. **Pricing-comparison table** on `/pricing` with citations + access dates.

### P1 — Weeks 2–4 (deepens Persona A activation)

7. **LangChain `langchain-community` integration PR** open (table stakes).
8. **`/playground` "copy as cURL / TS / Python" buttons** to reduce playground→external-call drop.
9. **Sentry breadcrumb** measuring time-delta between API key creation and first external 200.
10. **Free-tier "what would this cost on Tavily/Exa?" callout** in the dashboard usage view (anchor the value).
11. **PostHog events** wired for the activation funnel stages in [strategy/user-journey.md](./strategy/user-journey.md).

### P2 — Month 2 (unlocks Persona B — Priya)

12. **`/team` and `/settings` routes** (blocks Persona B onboarding — currently placeholder).
13. **Annual billing default at checkout** (structural fix for the 23% GRR budget-tier problem — see [strategy/pricing.md](./strategy/pricing.md)).
14. **Self-host quickstart guide** with a `docker compose up` path that hits parity with managed in <30 minutes.
15. **Vercel AI SDK adapter** ships.
16. **LlamaIndex retriever** — already shipped as `@unsearch/llamaindex`; publish a tutorial post.

### P3 — Month 3–6 (deepens Persona B revenue motion)

17. **Stripe metered overage billing** (schema fields exist; need Stripe metered prices wired). Smooths the upgrade cliff.
18. **PQL automation** — Workers cron that flags Free/Pro accounts crossing 50% utilization → Slack channel → founder DM template.
19. **First Cloudflare Workers Launchpad partner conversation.**
20. **Three published customer case studies** by month 9.

### P4 — Month 12+ (unlocks Persona C — David)

21. **SAML / OIDC SSO** (Enterprise tier prerequisite).
22. **Audit logging** (D1 query log replay).
23. **SOC 2 attestation work** — engage a vCISO / Drata / Vanta.
24. **Dedicated Durable-Object pool + dedicated Container replicas** for Enterprise SLA tier.

---

## Feature Roadmap (re-ordered around ICP needs)

### Phase 1 — PLG launch (Months 1–6) — Persona A
- [x] Core AI pipeline + Workers AI integration
- [x] Tavily-compatible `/api/v1/agent/search`
- [x] Exa-compatible neural endpoints
- [x] Stripe billing + dashboard + playground
- [x] TypeScript SDK + LlamaIndex retriever
- [x] Python SDK (sync + async, `pip install unsearch`)
- [x] CD pipeline + Sentry + smoke tests
- [ ] MCP server (P0, Week 1)
- [ ] LangChain integration PR (P1, Week 2)
- [ ] Google OAuth wiring (P0, Week 1)
- [ ] Annual billing default at checkout (P2, Month 2)
- [ ] Self-host quickstart with 30-min parity (P2, Month 2)
- [ ] Knowledge graph hardening → ship out of beta (rolling, Months 3–6)
- [ ] Topic monitoring hardening → ship out of beta (rolling, Months 3–6)
- [ ] Fact verification hardening → ship out of beta (rolling, Months 3–6)
- [ ] Deep research agent hardening → ship out of beta (rolling, Months 3–6)

### Phase 2 — Revenue motion (Months 6–18) — Persona B
- [ ] `/team` and `/settings` dashboard routes
- [ ] Stripe metered overage billing
- [ ] PQL automation (utilization >50% → Slack alert)
- [ ] Customer support automation (docs-search-bot dogfooding our own API)
- [ ] First Cloudflare Workers Launchpad partner integration
- [ ] Three published customer case studies

### Phase 3 — Enterprise (Months 18–24) — Persona C
- [ ] SAML / OIDC SSO
- [ ] Audit logging (D1 query log replay)
- [ ] SOC 2 attestation (engage vCISO / Drata / Vanta)
- [ ] Dedicated Durable-Object pool for SLA tier
- [ ] First Internal-Document connector (only if a paying Enterprise contract requires it)
- [ ] Multi-region active-active deployment

---

## Technical Debt

### High Priority
| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| In-memory vectors | `services/rag/rag.py` | Not scalable | Migrate to Vectorize |
| Puppeteer stub | `scraping/puppeteer_client.py` | No fallback | Use CF Browser |
| Sync DB operations | Multiple files | Performance | Add async |

### Medium Priority
| Issue | Location | Impact |
|-------|----------|--------|
| Hardcoded limits | Config | Inflexible |
| Missing retries | API calls | Reliability |
| No request tracing | Middleware | Debugging |

### Low Priority
| Issue | Location | Impact |
|-------|----------|--------|
| Inconsistent naming | Services | Maintainability |
| Missing docstrings | Some files | Documentation |
| Unused imports | Various | Clean code |

---

## API Endpoint Summary

### Total Endpoints: 75+

| Category | Count | Path Prefix |
|----------|-------|-------------|
| Agent (Tavily-compatible) | 5 | `/api/v1/agent/` |
| Search | 6 | `/api/v1/search/` |
| Neural (Exa-compatible) | 6 | `/api/v1/neural/` |
| Knowledge (Glean-like) | 5 | `/api/v1/knowledge/` |
| Connectors | 6 | `/api/v1/connectors/` |
| Monitor | 6 | `/api/v1/monitor/` |
| Verify | 4 | `/api/v1/verify/` |
| RAG | 8 | `/api/v1/rag/` |
| Enhanced | 6 | `/api/v1/enhanced/` |
| Advanced v2 | 15 | `/api/v1/v2/advanced/` |
| Auth | 6 | `/api/v1/auth/` |
| Billing | 4 | `/api/v1/billing/` |

---

## Deployment Architecture

### Development
```
Local Machine
    └── Docker Compose
        ├── FastAPI (Python backend)
        ├── SearXNG (Search)
        ├── Redis (Cache)
        └── PostgreSQL (Database)
```

### Production
```
Cloudflare Edge (300+ PoPs)
    └── Workers (Router)
        ├── Workers AI (LLM/Embeddings)
        ├── Vectorize (Vectors)
        ├── Queues (Async tasks)
        ├── D1 (Edge database)
        ├── KV (Caching)
        └── R2 (Storage)
            │
            ▼
        FastAPI Origin (Complex operations)
            ├── SearXNG
            ├── Redis
            └── PostgreSQL
```

---

## Success Metrics

### Technical
| Metric | Target | Current |
|--------|--------|---------|
| API uptime | 99.9% | N/A |
| P95 latency | <200ms | ~300ms |
| Edge latency | <50ms | N/A |
| Test coverage | >80% | ~40% |
| Error rate | <0.1% | ~1% |

### Feature parity (corrected)
| Competitor | Scope | Parity |
|------------|-------|--------|
| Tavily | Drop-in API compat | ✅ Complete |
| Exa | Neural endpoints | ✅ Complete |
| Glean | Open-web search (not internal docs — that's not our scope) | N/A — different category, see [strategy/jtbd.md](./strategy/jtbd.md) anti-jobs |

### Business — see [strategy/mrr-plan.md](./strategy/mrr-plan.md) for the full month-by-month plan
| Milestone | Target month |
|-----------|--------------|
| $10K MRR | Month 9 |
| $50K MRR | Month 18 |
| $100K MRR | Month 24 |

---

## Contact & Resources

- **Feature Matrix:** `docs/feature-matrix.md`
- **Architecture:** `docs/architecture.md`
- **AI Pipeline:** `docs/ai-pipeline.md`
- **Cloudflare Architecture:** `docs/cloudflare-architecture.md`
- **API Reference:** `http://localhost:8000/docs`
- **Edge Worker Docs:** `workers/README.md`
