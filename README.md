# UnSearch

> **Verifiable web retrieval for AI agents. Every result signed, hashed, snapshotted, and replayable months later.**

Apache 2.0. MCP-native. Self-hostable on Cloudflare Workers + Containers. WACZ-aligned signed citation envelopes so any retrieval can be replayed in court, in an FDA submission, or in an EU AI Act Article 12 audit log months after the fact.

[![Python SDK](https://img.shields.io/pypi/v/unsearch?label=pip%20install%20unsearch)](https://pypi.org/project/unsearch/)
[![TypeScript SDK](https://img.shields.io/npm/v/@unsearch/sdk?label=npm%20%40unsearch%2Fsdk)](https://www.npmjs.com/package/@unsearch/sdk)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

---

## The problem

AI agents confidently make claims tied to web sources that are wrong, dead, paraphrased, fabricated, or — worst — silently changed since the agent retrieved them. There is no widely-adopted infrastructure primitive that produces a **cryptographically verifiable record** of "what the agent saw, at what URL, at what time, and what hash" — so every team building agents for regulated workflows is rebuilding this primitive from scratch.

The numbers from 2026 so far:

- **$145K in U.S. court sanctions in Q1 2026 alone** for AI-hallucinated legal citations. Single largest: **$110K** on April 4 2026 (23 fabricated citations + 8 false quotations across three filings).
- **Harvey AI** ($8B valuation) still hallucinates **1 in 6** queries.
- **40–60% reference fabrication rate** on biomedical questions without retrieval; even with RAG, accuracy is only 69.5%.
- **EU AI Act Article 12** full enforcement begins **August 2026** — automatic event logging required over the system's lifetime, 6-month log retention minimum, 10-year documentation retention, **provenance documentation explicitly required**. Penalty: **€15M or 3% of worldwide turnover.**

Regulated buyers cannot use Anthropic's native `web_search` or OpenAI Codex CLI search because the citations aren't customer-pinnable, the snapshots aren't reproducible, and the data leaves their perimeter. So they hand-roll: Tavily + Firecrawl + Playwright snapshots + custom NLI grader + Postgres provenance table. Five vendors and 1–2 FTEs of glue per company.

**UnSearch is the missing primitive.**

---

## For whom

UnSearch is built for:

- **Engineering leads at regulated-AI startups** (Series Seed–B, 10–80 people) building vertical AI for legal / medical / finance / insurance / research / compliance verticals
- **AI platform directors at established regulated companies** (banks, hospital systems, insurance carriers, BigLaw firms, pharma) retrofitting LLM features ahead of EU AI Act enforcement
- **Citation-integrity research & journalism engineers** snapshotting cited sources so retraction-tracking and reproducibility survive bit rot

UnSearch is **not** for:

- Indie devs building non-regulated agents — Anthropic native `web_search` and Codex CLI search are free and good enough for them
- Anyone needing a consumer search UI (we're an API + MCP, not a browser)
- Anyone needing internal-document search across Slack/Drive/Confluence (that's [Glean's](https://www.glean.com) job)
- Anyone needing aggressive scraping of login-walled or anti-bot sites (we respect `robots.txt` and ToS)

See [`docs/strategy/icp.md`](./docs/strategy/icp.md) for the three personas in detail.

---

## How it works

Every search or extract call returns a **signed citation envelope** plus a **content-addressable snapshot** in your own R2 bucket (self-host) or ours (hosted). The `verify_claim` endpoint then takes any `{claim, source_url}` pair and returns span-level evidence with a confidence score.

```json
// citation_envelope returned with every result
{
  "v": 1,
  "url": "https://example.com/article",
  "fetched_at": "2026-05-28T18:32:11Z",
  "content_sha256": "a3f5...",
  "content_type": "text/html",
  "snapshot_r2_key": "citations/a3f5.../snapshot.wacz",
  "engine": "searxng:google",
  "agent_run_id": "run_01HQ...",
  "api_key_id": "key_01HK...",
  "signature_hmac_sha256": "9d2e..."
}
```

Envelope format is aligned with the [WACZ-Auth spec](https://github.com/webrecorder/wacz-auth-spec) so any consumer of the broader web-archival ecosystem can verify our snapshots with existing tooling. Full schema: [`docs/citation-envelope.md`](./docs/citation-envelope.md).

---

## Quick start — MCP-first

The fastest way to evaluate UnSearch — no signup, no API key, no credit card. Free tier 5,000 verified searches / month is built into the MCP server itself:

```bash
claude mcp add unsearch
# or, in any other MCP-compatible client:
npx @unsearch/mcp-server
```

Then ask Claude (or any MCP-compatible agent):

> Search for "Q1 2026 legal AI sanctions" and verify the claim that the single largest sanction was $110,000 against the URL you find.

You'll get back signed results and a `verify_claim` response with evidence spans.

### Or use the SDK

```bash
# Python
pip install unsearch
```

```python
from unsearch import UnSearch

client = UnSearch(api_key="uns_...")
hits = client.search({"query": "EU AI Act Article 12 logging requirements"})
for r in hits["results"]:
    print(r["rank"], r["title"], r["citation_envelope"]["content_sha256"])

# Verify a claim
verify = client.verify_claim({
    "claim": "EU AI Act full enforcement begins August 2026",
    "source_url": hits["results"][0]["url"],
})
print(verify["supported"], verify["confidence"], verify["evidence_spans"])
```

```bash
# TypeScript / Node / Bun / Deno / Workers / Edge
pnpm add @unsearch/sdk
```

```ts
import { UnSearch } from "@unsearch/sdk"

const client = new UnSearch({ apiKey: process.env.UNSEARCH_API_KEY! })
const hits = await client.search({ query: "EU AI Act Article 12 logging" })
const verify = await client.verifyClaim({
  claim: "EU AI Act full enforcement begins August 2026",
  source_url: hits.results[0].url,
})
```

### Self-host on your own Cloudflare account

For ICP-2 (regulated companies) — your data stays in your perimeter, you control the signing keys, audit logs retain up to 10 years.

```bash
git clone https://github.com/Rakesh1002/unsearch.git
cd unsearch
cp .env.example .env   # fill in CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN
wrangler login
wrangler containers deploy   # deploys FastAPI + SearXNG to CF Containers (GA April 2026)
wrangler deploy              # deploys Hono edge + MCP + dashboard
```

Full self-host guide at [`docs/quickstart.md`](./docs/quickstart.md) and [`docs/deployment/`](./docs/deployment/).

For a Docker-Compose stack instead (no Cloudflare account required):

```bash
docker compose up -d
# minimal stack (no Celery/Postgres if you only need search + verify):
docker compose -f docker-compose.quickstart.yml up -d
```

---

## What's in the repo

```
unsearch/
├── backend/                # FastAPI backend — search, extract, verify, audit (Python 3.11+)
│   ├── app/                #   Python module (`from app.X import Y`)
│   ├── alembic/            #   Postgres migrations
│   ├── tests/              #   pytest suite
│   ├── Dockerfile          #   Self-host image
│   └── Dockerfile.cloudflare #   CF Containers image
├── apps/                   # TypeScript / Python SDK packages (pnpm workspace)
│   ├── web/                #   Next.js dashboard on Cloudflare Workers (@opennextjs/cloudflare)
│   ├── sdk-ts/             #   @unsearch/sdk — TypeScript SDK
│   ├── sdk-py/             #   unsearch — Python SDK (sync + async)
│   ├── sdk-llamaindex/     #   @unsearch/llamaindex — LlamaIndex retriever
│   └── mcp-server/         #   @unsearch/mcp-server — MCP server (P0 Week 3)
├── workers/                # Cloudflare Workers edge — Hono router, MCP transport, Durable Objects, D1 schema, containers.toml
├── infra/                  # Operational config (self-host stack + CF Container sidecars)
│   ├── nginx/              #   Reverse-proxy for self-host TLS
│   ├── monitoring/         #   Prometheus + Grafana provisioning
│   └── searxng/            #   SearXNG meta-search engine config (production settings.yml)
├── docs/                   # Architecture, API reference, strategy, ADRs, runbooks
├── scripts/                # Setup + ops scripts (manage.sh, setup-stripe.sh, …)
└── docker-compose*.yml     # Self-host stacks (build context = root; mount paths from infra/)
```

The architecture (Workers fronting FastAPI on Cloudflare Containers GA, with D1 / KV / Vectorize / R2 / Queues / Durable Objects + SearXNG sidecar) is documented in [`docs/cloudflare-architecture.md`](./docs/cloudflare-architecture.md). The five new ADRs that drove the 2026-05-28 reposition are at [`docs/adr/`](./docs/adr/README.md) (#0009 through #0013). ADR-0006 has a 2026-05-28 amendment describing the directory restructure (`app/` → `backend/app/`, ops into `infra/`).

---

## Honest feature status

> See [`docs/feature-matrix.md`](./docs/feature-matrix.md) for the full table. TL;DR below.

### Shipped (production, end-to-end tested)
- Web search (`/api/v1/search`, `/api/v1/agent/search`) — Tavily-compatible drop-in compatibility surface
- Neural / semantic search + auto-prompt + highlights + similar — Exa-compatible
- Multi-engine aggregation via SearXNG (70+ engines, sidecar container)
- Scraping (static, JavaScript, PDF, multi-engine), extraction, deep crawl
- RAG with Cloudflare Vectorize + `bge-m3` embeddings + 4-tier Workers AI model selector
- Stripe billing — checkout + portal + subscriptions
- Cloudflare edge — Workers, Workers AI, Vectorize, Queues, Durable Objects, D1, KV, R2
- TypeScript SDK (`@unsearch/sdk`), Python SDK (`unsearch`), LlamaIndex retriever (`@unsearch/llamaindex`)

### Shipping in the 3-week rebuild (per the approved plan)
- ✏️ Cloudflare Containers deploy (FastAPI + SearXNG sidecar) — **Week 1**
- ✏️ Dashboard at `app.unsearch.dev`, edge at `api.unsearch.dev` — **Week 1**
- ✏️ Signed citation envelope on every result (HMAC v1, WACZ-aligned) — **Week 2**
- ✏️ R2 snapshot store (content-addressable, sha256-keyed) — **Week 2**
- ✏️ `/api/v1/verify/citation` + `/api/v1/verify/claim` GA — **Week 2**
- ✏️ `/api/v1/audit` per-API-key audit log — **Week 2**
- ✏️ MCP server (Streamable HTTP) at `api.unsearch.dev/mcp` — **Week 3**
- ✏️ `npx @unsearch/mcp-server` package — **Week 3**
- ✏️ MCP registry submission + HN launch — **Week 3**

### In beta (code paths exist, hardening in flight)
- Knowledge graph — entity extraction, relationship mapping (`/api/v1/knowledge/*`)
- Topic monitoring + webhook alerts (`/api/v1/monitor/topics`)
- Source credibility (`/api/v1/verify/source`)
- Deep research agent (`/api/v1/agent/research`)
- Predictive search (`/api/v1/neural/predictive`)

### On the roadmap
- Google OAuth wiring (keys in `.env.example`; flow not yet wired)
- LangChain + Vercel AI SDK adapters
- WACZ public-key signing (Month 7+, replacing HMAC v1)
- BYO storage (S3 / GCS / Azure Blob) for snapshot store on self-host
- SOC 2 Type II (Month 9), HIPAA BAA (Month 6), ISO 42001 (Month 9–12)
- BYOC beyond Cloudflare (AWS / GCP / Azure deploy templates) — Month 10+
- SAML / OIDC SSO + RBAC — Enterprise tier

---

## Path forward

The full ordered roadmap lives in [`docs/roadmap.md`](./docs/roadmap.md). The 3-week rebuild plan lives at `~/.claude/plans/app-unsearch-dev-is-not-deployed-luminous-wilkinson.md`. At a glance:

**Week 1 — Deploy what exists + reposition**
1. Container deploy of FastAPI + SearXNG sidecar on CF Containers GA
2. Frontend `pnpm cf:build && pnpm cf:deploy` to `app.unsearch.dev`
3. Hono edge to `api.unsearch.dev`
4. Strategy docs + landing copy rewrite (this PR)

**Week 2 — Verification wedge**
5. R2 citation snapshot store with sha256 content addressing
6. WACZ-aligned signed envelopes (HMAC v1)
7. `verify/citation` + `verify/claim` endpoints GA
8. Dashboard verify + audit views

**Week 3 — MCP-first distribution + launch**
9. Hono-hosted MCP server at `/mcp` exposing `search`, `extract`, `research`, `verify_claim`
10. `npx @unsearch/mcp-server` package
11. MCP registry + `awesome-mcp-servers` submission
12. HN launch + outreach to first 10 named ICP-1 customers

**Month 2–6**
- LangChain + Vercel AI SDK adapters
- Self-host quickstart + `wrangler deploy` UX polish
- WACZ export endpoint
- BYO storage on self-host
- SOC 2 Type I (Month 4) → Type II (Month 9)
- First self-host v2 customer with BAA + DPA + SSO

---

## SDKs

| Language | Package | Repo |
|----------|---------|------|
| Python (sync + async) | [`unsearch`](https://pypi.org/project/unsearch/) | [`apps/sdk-py`](./apps/sdk-py/) |
| TypeScript / Node / Edge | [`@unsearch/sdk`](https://www.npmjs.com/package/@unsearch/sdk) | [`apps/sdk-ts`](./apps/sdk-ts/) |
| LlamaIndex retriever | [`@unsearch/llamaindex`](https://www.npmjs.com/package/@unsearch/llamaindex) | [`apps/sdk-llamaindex`](./apps/sdk-llamaindex/) |
| MCP server | _coming Week 3_ | [`apps/mcp-server/`](./apps/mcp-server/) |
| LangChain | _community PR in flight_ | — |

All SDKs cover the same surface — search, extract, research, neural search, RAG (with streaming), ingest, verify, topic monitoring, plus a `tavily_search` / `tavilySearch` drop-in.

---

## API reference

93 endpoints across 14 routers. Live OpenAPI docs at:

- Local: `http://localhost:8000/docs`
- Production: [api.unsearch.dev/docs](https://api.unsearch.dev/docs)

### Headline endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/search` | Native UnSearch search — returns signed citation envelope per result |
| `POST /api/v1/agent/search` | Tavily-compatible drop-in (compatibility surface) |
| `POST /api/v1/agent/research` | Deep research agent (Durable Object, multi-step, audit-trailed) |
| `POST /api/v1/agent/extract` | Web extraction with envelope |
| `POST /api/v1/verify/citation` | Snapshot pin + live diff (**shipping Week 2**) |
| `POST /api/v1/verify/claim` | Span-level claim grading via Workers AI (**shipping Week 2**) |
| `POST /api/v1/verify/source` | 🔶 Source credibility |
| `GET  /api/v1/audit` | Per-API-key audit log (**shipping Week 2**) |
| `POST /api/v1/neural/search` | Exa-compatible neural search |
| `POST /api/v1/rag/query` | RAG over your Vectorize namespace (SSE streaming) |
| `GET  /mcp` | Streamable HTTP MCP server (**shipping Week 3**) |

Full reference: [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md). Worked examples: [`docs/API_EXAMPLES.md`](./docs/API_EXAMPLES.md). Envelope schema: [`docs/citation-envelope.md`](./docs/citation-envelope.md).

---

## AI pipeline

UnSearch routes generation, embeddings, reranking, and the `verify_claim` grader through Cloudflare Workers AI. Pick a tier per request.

| Tier | Model | Use case |
|------|-------|----------|
| `fast` | `llama-3.1-8b-instruct-fast` | Cheap, low-latency answers, simple queries |
| `balanced` | `llama-3.3-70b-instruct-fp8-fast` | Default — general answers + `verify_claim` grader |
| `reasoning` | `qwq-32b` | Multi-step reasoning, agent workflows |
| `production` | `gpt-oss-120b` | Highest-quality enterprise traffic |

Embeddings: `bge-m3` (1024 dims) into Cloudflare Vectorize.

Full pipeline: [`docs/ai-pipeline.md`](./docs/ai-pipeline.md).

---

## Configuration

See [.env.example](./.env.example) for the canonical list. The two required values for the hosted Cloudflare features:

```bash
CLOUDFLARE_ACCOUNT_ID="..."
CLOUDFLARE_API_TOKEN="..."
```

Optional infra defaults assume the Docker Compose stack:

```bash
SEARXNG_URL="http://searxng:8080"
REDIS_URL="redis://localhost:6379"
DATABASE_URL="postgresql://unsearch:${POSTGRES_PASSWORD:-changeme}@localhost:5432/unsearch"
```

Stripe billing, SMTP, OAuth, monitoring — all documented in [`docs/configuration/env-variables.md`](./docs/configuration/env-variables.md).

---

## Development

```bash
# Python backend (everything backend-related lives in backend/)
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (Next.js on Workers)
pnpm --filter @unsearch/web dev

# Edge worker (Hono on CF Workers)
cd workers && pnpm dev

# Python SDK
cd apps/sdk-py && pip install -e ".[test]" && pytest -q

# TypeScript SDK
pnpm --filter @unsearch/sdk build && pnpm --filter @unsearch/sdk test

# Backend tests (from backend/ where pytest.ini lives)
cd backend && pytest tests/unit/ -v --cov=app
cd backend && pytest tests/integration/ -v

# Or via the Makefile (handles the `cd backend` for you)
make dev       # uvicorn with --reload
make test      # full test suite
make migrate   # alembic upgrade head
```

Lint, type-check, and test commands are wired into CI ([.github/workflows/](./.github/workflows/)). Conventions live in [CLAUDE.md](./CLAUDE.md) and [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](./docs/architecture.md) | System architecture overview |
| [Cloudflare architecture](./docs/cloudflare-architecture.md) | Edge / Containers / D1 / Vectorize wiring |
| [Citation envelope](./docs/citation-envelope.md) | Signed envelope schema + signing |
| [AI pipeline](./docs/ai-pipeline.md) | Models, embeddings, reranking |
| [API reference](./docs/API_REFERENCE.md) | Full endpoint catalog |
| [API examples](./docs/API_EXAMPLES.md) | Worked examples per endpoint |
| [Feature matrix](./docs/feature-matrix.md) | Honest ✅ / 🔶 / 📋 status table |
| [Roadmap](./docs/roadmap.md) | ICP-ordered roadmap |
| [Quickstart](./docs/quickstart.md) | Self-host guide |
| [Migrate from Tavily](./docs/migration/from-tavily.md) | Compatibility surface |
| [Runbooks](./docs/operations/RUNBOOKS.md) | On-call playbooks |
| [Strategy](./docs/strategy/README.md) | Problem, ICP, GTM, pricing, positioning |
| [ADRs](./docs/adr/README.md) | Architecture decision records (0001–0013) |
| [Changelog](./CHANGELOG.md) | What shipped in each release |

---

## Contributing

We welcome contributions — see [CONTRIBUTING.md](./CONTRIBUTING.md). Good first issues:

- Add an example notebook to `docs/API_EXAMPLES.md` showing `verify_claim` against a real source
- Improve test coverage on `app/services/` (currently ~40%; target 80%)
- Build a community integration (LangGraph, Haystack, DSPy, Vercel AI SDK)
- File issues on any 🔶 in-beta endpoint that returns surprising results — we're hardening these next

## License

[Apache 2.0](./LICENSE).

## Support

- **Docs:** [docs.unsearch.dev](https://docs.unsearch.dev) (or browse [./docs/](./docs/) locally)
- **Issues:** [GitHub Issues](https://github.com/Rakesh1002/unsearch/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Rakesh1002/unsearch/discussions)
- **Email:** support@unsearch.dev
