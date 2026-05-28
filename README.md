# UnSearch

> **The open-source search API for AI agents. Tavily-compatible. 10× cheaper.**

Apache 2.0. Self-hostable on Cloudflare Workers + Containers. Drop-in replacement for Tavily — change one base URL, keep your existing `client.search()` calls. $49/mo on the Growth tier vs. a ~$500/mo median across closed-source competitors.

[![Python SDK](https://img.shields.io/pypi/v/unsearch?label=pip%20install%20unsearch)](https://pypi.org/project/unsearch/)
[![TypeScript SDK](https://img.shields.io/npm/v/@unsearch/sdk?label=npm%20%40unsearch%2Fsdk)](https://www.npmjs.com/package/@unsearch/sdk)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

---

## For whom

UnSearch is built for:

- **AI app builders shipping production agents** who hit Tavily's $30/$100 pricing cliff or are nervous about the [Nebius acquisition](https://techcrunch.com/2025/08/06/tavily-raises-25m-to-connect-ai-agents-to-the-web/)
- **AI-native startups** whose search bill became 30–60% of COGS on Exa or other closed vendors
- **Cloudflare-stack teams** who want retrieval that runs on the same edge as the rest of their app
- **Teams that need Apache 2.0** for legal/compliance review or to defuse vendor-lock-in objections

UnSearch is **not** for:

- Anyone who wants a consumer search UI (we're an API, not a browser)
- Anyone needing internal-document search across Slack/Drive/Confluence (that's [Glean's](https://www.glean.com) job)
- Anyone needing aggressive scraping of login-walled or anti-bot sites (we respect `robots.txt` and ToS)
- Procurement-led enterprises that require a 6-month security review before evaluating (we'll get there — see [strategy/mrr-plan.md](./docs/strategy/mrr-plan.md))

## Why UnSearch

| Feature | Tavily | Exa | Brave | UnSearch |
|---------|--------|-----|-------|----------|
| Open source license | — | — | — | **Apache 2.0** |
| Self-hostable | — | — | — | **Docker one-liner + CF Containers** |
| Drop-in Tavily API | N/A | — | — | **Yes** |
| Free tier | 1,000/mo | 1,000/mo | None (since Feb 2026) | **5,000/mo** |
| Price for 100K searches/mo | ~$700 | ~$700 | ~$500 | **$49 (Growth)** |
| Public 12-month price-notice commitment | — | — | — | **Yes** |
| Cloudflare-native (Workers / D1 / Vectorize) | — | — | — | **Yes** |
| Zero-retention mode | — | — | — | **Yes (Pro+)** |

For the full feature comparison with honest ✅ / 🔶 status, see [docs/feature-matrix.md](./docs/feature-matrix.md). For the strategy + GTM story, see [docs/strategy/](./docs/strategy/README.md).

---

## Quick start

### Use the hosted API

Grab a key at [app.unsearch.dev](https://app.unsearch.dev), then:

```bash
# Python
pip install unsearch
```

```python
from unsearch import UnSearch

client = UnSearch(api_key="uns_...")
hits = client.search({"query": "Cloudflare Workers in 2026", "max_results": 10})
for r in hits["results"]:
    print(r["rank"], r["title"], r["url"])
```

```bash
# TypeScript / Node / Bun / Deno / Workers / Edge
pnpm add @unsearch/sdk
```

```ts
import { UnSearch } from "@unsearch/sdk"

const client = new UnSearch({ apiKey: process.env.UNSEARCH_API_KEY! })
const hits = await client.search({ query: "Cloudflare Workers in 2026", max_results: 10 })
```

### Self-host

```bash
git clone https://github.com/Rakesh1002/unsearch.git
cd unsearch
cp .env.example .env   # fill in CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN
docker compose up -d
```

Local API + interactive OpenAPI docs at `http://localhost:8000/docs`. For the minimal stack (no Celery/Postgres if you only need search):

```bash
docker compose -f docker-compose.quickstart.yml up -d
```

For the full guide — including Cloudflare Workers / Containers deployment — see [docs/quickstart.md](./docs/quickstart.md) and [docs/deployment/](./docs/deployment/).

### Migrate from Tavily

```python
# Before
from tavily import TavilyClient
client = TavilyClient(api_key="tvly-...")
hits = client.search("AI news")

# After — same response shape, just change the import + key
from unsearch import UnSearch
client = UnSearch(api_key="uns_...")
hits = client.tavily_search({"query": "AI news"})
```

Full migration guide: [docs/migration/from-tavily.md](./docs/migration/from-tavily.md).

---

## What's in the repo

```
unsearch/
├── app/                    # FastAPI backend (legacy single-package layout, still authoritative)
├── apps/
│   ├── backend/            # FastAPI backend (monorepo layout — same code, packaged for Docker)
│   ├── web/                # Next.js dashboard on Cloudflare Workers (via @opennextjs/cloudflare)
│   ├── sdk-ts/             # @unsearch/sdk — TypeScript SDK
│   ├── sdk-py/             # unsearch — Python SDK (sync + async)
│   └── sdk-llamaindex/     # @unsearch/llamaindex — LlamaIndex retriever
├── workers/                # Cloudflare Workers edge router (Hono) + Durable Objects + D1 schema
├── docs/                   # Architecture, API reference, strategy, roadmap, runbooks
├── alembic/                # Postgres migrations (origin DB)
├── searxng/                # SearXNG meta-search engine config
├── monitoring/             # Prometheus + Grafana provisioning
└── docker-compose*.yml     # Self-host stacks
```

The Cloudflare-native architecture (Workers fronting a FastAPI Container, with D1 / KV / Vectorize / R2 / Queues / Durable Objects bindings) is described in [docs/cloudflare-architecture.md](./docs/cloudflare-architecture.md) and [workers/README.md](./workers/README.md).

---

## Honest feature status

> See [docs/feature-matrix.md](./docs/feature-matrix.md) for the full table. Tldr below.

### Shipped (production, end-to-end tested)
- AI / web search (`/api/v1/search`, `/api/v1/agent/search`) — Tavily-compatible
- Neural / semantic search + auto-prompt + highlights + similar — Exa-compatible
- Multi-engine aggregation via SearXNG (70+ engines)
- Scraping (static, JavaScript, PDF, multi-engine), extraction, deep crawl
- RAG with Cloudflare Vectorize + `bge-m3` embeddings + 4-tier Workers AI model selector
- Stripe billing — checkout + portal + subscriptions
- Cloudflare edge — Workers, Workers AI, Vectorize, Queues, Durable Objects, D1, KV, R2
- TypeScript SDK (`@unsearch/sdk`), Python SDK (`unsearch`), LlamaIndex retriever (`@unsearch/llamaindex`)

### In beta (code paths exist, hardening in flight)
- Knowledge graph — entity extraction, relationship mapping (`/api/v1/knowledge/*`)
- Topic monitoring + webhook alerts (`/api/v1/monitor/topics`)
- Fact verification — claim check + source credibility (`/api/v1/verify/*`)
- Deep research agent (`/api/v1/agent/research`)
- Predictive search (`/api/v1/neural/predictive`)

### On the roadmap (not yet shipped)
- MCP server published to npm + Anthropic directory (**next P0**)
- Google OAuth wiring (keys in `.env.example`; flow not yet wired)
- LangChain `langchain-community` integration PR
- `/team` and `/settings` dashboard routes
- Stripe metered overage billing
- Internal-document connectors (Drive/Slack/Confluence/Notion/GitHub) — Enterprise tier only
- SAML / OIDC SSO + audit logging — Enterprise tier
- SOC 2 attestation

---

## Path forward

The full ordered roadmap lives in [docs/roadmap.md](./docs/roadmap.md). At a glance:

**Now → Week 1 (P0, unblocks indie devs and the Show HN launch):**

1. **MCP server** (TypeScript) published to npm + Anthropic MCP directory
2. ~~Python SDK on PyPI~~ ✅ Shipped — `pip install unsearch`
3. Polish [docs/migration/from-tavily.md](./docs/migration/from-tavily.md) — 5-minute headline, 3-line diff, playground CTA
4. Wire Google OAuth (keys already in `.env.example`)
5. Homepage hero rewrite to the one-liner in [strategy/positioning.md](./docs/strategy/positioning.md)
6. Pricing-comparison table on `/pricing` with citations + access dates

**Weeks 2–4 (P1, deepens indie-dev activation):**

- LangChain `langchain-community` integration PR
- Playground "copy as cURL / TS / Python" buttons
- Activation-funnel instrumentation (Sentry breadcrumbs, PostHog events)
- "What would this cost on Tavily/Exa?" callout in the dashboard

**Month 2+ (P2, unlocks Seed/A CTOs):**

- `/team` + `/settings` dashboard routes
- Annual billing default at checkout
- Self-host quickstart with `docker compose up` → parity in <30 minutes
- Vercel AI SDK adapter
- Stripe metered overage (schema fields exist; need Stripe metered prices wired)

**Months 6–12+ (P3/P4, Enterprise):**

- SAML / OIDC SSO
- Audit logging (D1 query log replay)
- SOC 2 attestation (Drata / Vanta / vCISO engagement)
- Dedicated DO pool + Container replicas for Enterprise SLA tier

---

## SDKs

| Language | Package | Repo |
|----------|---------|------|
| Python (sync + async) | [`unsearch`](https://pypi.org/project/unsearch/) | [`apps/sdk-py`](./apps/sdk-py/) |
| TypeScript / Node / Edge | [`@unsearch/sdk`](https://www.npmjs.com/package/@unsearch/sdk) | [`apps/sdk-ts`](./apps/sdk-ts/) |
| LlamaIndex retriever | [`@unsearch/llamaindex`](https://www.npmjs.com/package/@unsearch/llamaindex) | [`apps/sdk-llamaindex`](./apps/sdk-llamaindex/) |
| MCP server | _coming soon (next P0)_ | — |
| LangChain | _community PR in flight_ | — |

All SDKs cover the same surface — search, neural search, similar, highlights, RAG (with streaming), ingest, research agent (with polling), verify, topic monitoring, plus a `tavily_search` / `tavilySearch` drop-in.

---

## API reference

93 endpoints across 14 routers. Live OpenAPI docs at:

- Local: `http://localhost:8000/docs`
- Production: [api.unsearch.dev/docs](https://api.unsearch.dev/docs)

### Headline endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/search` | Native UnSearch search (rich filters, scraping, caching) |
| `POST /api/v1/agent/search` | Tavily-compatible drop-in |
| `POST /api/v1/agent/research` | Deep research agent (Durable Object, multi-step) |
| `POST /api/v1/neural/search` | Exa-compatible neural search |
| `POST /api/v1/neural/similar` | Find similar content |
| `POST /api/v1/neural/highlights` | Extract key passages |
| `POST /api/v1/rag/query` | RAG over your Vectorize namespace (supports SSE streaming) |
| `POST /api/v1/rag/ingest` | Ingest documents into Vectorize |
| `POST /api/v1/knowledge/extract` | 🔶 Entity extraction |
| `POST /api/v1/monitor/topics` | 🔶 Topic monitoring with webhook fan-out |
| `POST /api/v1/verify/claim` | 🔶 Fact verification |

Full reference: [docs/API_REFERENCE.md](./docs/API_REFERENCE.md). Worked examples: [docs/API_EXAMPLES.md](./docs/API_EXAMPLES.md).

---

## AI pipeline

UnSearch routes generation, embeddings, and reranking through Cloudflare Workers AI. Pick a tier per request via the `model_tier` (RAG) or `model` (search) parameter.

| Tier | Model | Use case |
|------|-------|----------|
| `fast` | `llama-3.1-8b-instruct-fast` | Cheap, low-latency answers, simple queries |
| `balanced` | `llama-3.3-70b-instruct-fp8-fast` | Default — general-purpose answers |
| `reasoning` | `qwq-32b` | Multi-step reasoning, agent workflows |
| `production` | `gpt-oss-120b` | Highest-quality enterprise traffic |

Embeddings: `bge-m3` (1024 dims) into Cloudflare Vectorize.

Full pipeline: [docs/ai-pipeline.md](./docs/ai-pipeline.md).

---

## Configuration

See [.env.example](./.env.example) for the canonical list. The two required values for the hosted Cloudflare features:

```bash
CLOUDFLARE_ACCOUNT_ID="..."
CLOUDFLARE_API_TOKEN="..."
```

Optional infra defaults assume the `docker compose up -d` stack:

```bash
SEARXNG_URL="http://searxng:8080"
REDIS_URL="redis://localhost:6379"
DATABASE_URL="postgresql://unsearch:${POSTGRES_PASSWORD:-changeme}@localhost:5432/unsearch"
```

Stripe billing, SMTP, OAuth, monitoring — all documented in [docs/configuration/env-variables.md](./docs/configuration/env-variables.md).

---

## Development

```bash
# Python backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Next.js on Workers)
pnpm --filter @unsearch/web dev

# Edge worker (Hono on CF Workers)
cd workers && pnpm dev

# Python SDK
cd apps/sdk-py && pip install -e ".[test]" && pytest -q

# TypeScript SDK
pnpm --filter @unsearch/sdk build && pnpm --filter @unsearch/sdk test

# Backend tests
pytest tests/unit/ -v --cov=app
pytest tests/integration/ -v
```

Lint, type-check, and test commands are wired into CI ([.github/workflows/](./.github/workflows/)). Conventions live in [CLAUDE.md](./CLAUDE.md) and [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](./docs/architecture.md) | System architecture overview |
| [Cloudflare architecture](./docs/cloudflare-architecture.md) | Edge / Containers / D1 / Vectorize wiring |
| [AI pipeline](./docs/ai-pipeline.md) | Models, embeddings, reranking |
| [API reference](./docs/API_REFERENCE.md) | Full endpoint catalog |
| [API examples](./docs/API_EXAMPLES.md) | Worked examples per endpoint |
| [Feature matrix](./docs/feature-matrix.md) | Honest ✅ / 🔶 / 📋 status table |
| [Roadmap](./docs/roadmap.md) | ICP-ordered roadmap |
| [Quickstart](./docs/quickstart.md) | Self-host guide |
| [Migrate from Tavily](./docs/migration/from-tavily.md) | 5-minute migration guide |
| [Runbooks](./docs/operations/RUNBOOKS.md) | On-call playbooks |
| [Strategy](./docs/strategy/README.md) | ICP, GTM, pricing, positioning |
| [Changelog](./CHANGELOG.md) | What shipped in each release |

---

## Contributing

We welcome contributions — see [CONTRIBUTING.md](./CONTRIBUTING.md). Good first issues:

- Add an example notebook to `docs/API_EXAMPLES.md`
- Improve test coverage on `app/services/` (currently ~40%; target 80%)
- Build a community integration (LangChain, Haystack, DSPy, Vercel AI SDK)
- File issues on any 🔶 in-beta endpoint that returns surprising results — we're hardening these next

## License

[Apache 2.0](./LICENSE).

## Support

- **Docs:** [docs.unsearch.dev](https://docs.unsearch.dev) (or browse [./docs/](./docs/) locally)
- **Issues:** [GitHub Issues](https://github.com/Rakesh1002/unsearch/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Rakesh1002/unsearch/discussions)
- **Email:** support@unsearch.dev
