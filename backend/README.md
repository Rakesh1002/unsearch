# backend

Python FastAPI backend for UnSearch — search, extract, verify, audit. 93 endpoints across 14 routers. Runs on Cloudflare Containers (GA April 2026) in production via `backend/Dockerfile.cloudflare`, and on a self-host Docker stack via `backend/Dockerfile`.

Python module: **`app`** (`from app.X import Y`). The folder is named `backend/` to disambiguate from the `apps/` (TypeScript packages) directory — see [ADR-0006](../docs/adr/0006-monorepo-with-apps-and-workers.md).

## Layout

```
backend/
├── app/                    Python module
│   ├── main.py             FastAPI entry — uvicorn target is `app.main:app`
│   ├── config.py           Settings (Pydantic), env-driven
│   ├── api/v1/             Route handlers (93 endpoints, 14 routers)
│   ├── services/           Business logic
│   │   ├── core/           D1 / KV / Queues REST clients, DB session
│   │   ├── search/         SearXNG orchestration + dedup + rerank
│   │   ├── scraping/       Static / JS / PDF / multi-engine
│   │   ├── extraction/     Entities, tables, attributes
│   │   ├── crawling/       Deep crawl, mapping, change tracking
│   │   ├── rag/            Embeddings, Vectorize, research mode
│   │   ├── ai/             Workers AI tiered-model selector + verify_claim grader
│   │   └── …
│   ├── models/             Pydantic + SQLAlchemy models
│   ├── middleware/         Auth, rate-limit, request-ID, error handling
│   └── workers/            Celery tasks (named to avoid confusion with Cloudflare Workers)
├── alembic/                Postgres migrations
├── alembic.ini             Alembic config
├── pytest.ini              Pytest config (rootdir = backend/)
├── requirements.txt        Python deps
├── tests/                  Unit + integration + performance + smoke + e2e tests
├── Dockerfile              Self-host image (multi-worker uvicorn, NLTK download in build)
└── Dockerfile.cloudflare   CF Containers image (single uvicorn worker, no NLTK in build)
```

## Quickstart

From the **repo root**:

```bash
# Local dev (uses backend/.env)
make dev                     # uvicorn --reload on :8000
make test                    # pytest backend/tests/
make migrate                 # alembic upgrade head
make typecheck               # mypy backend/app
make lint                    # black + isort + flake8

# Or invoke uvicorn directly
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

Docker (self-host):

```bash
docker compose up -d                                    # full stack (API + Postgres + Redis + SearXNG + Celery + nginx)
docker compose -f docker-compose.quickstart.yml up -d   # minimal (API + Postgres + Redis + SearXNG)
```

Cloudflare Containers (production):

```bash
wrangler containers deploy --config apps/workers/containers.toml
```

## Env

Backend env lives at `backend/.env` (gitignored). Required values are documented in `.env.example` at the repo root and in [`docs/configuration/env-variables.md`](../docs/configuration/env-variables.md).

The two values required for any Cloudflare-bound feature:

```bash
CLOUDFLARE_ACCOUNT_ID="..."
CLOUDFLARE_API_TOKEN="..."
```

## How requests reach the backend

The Cloudflare Workers edge router at [`apps/workers/`](../apps/workers/README.md) fronts every public request. The Worker either answers from the edge (KV cache hit, auth, rate-limit, MCP transport, simple Tavily-shape search) or forwards to this Container via a service binding (catch-all → Container for anything that needs the Python ecosystem).

The Container does **not** face the public internet directly in production.

## Citation envelope

Every result returned from `/api/v1/search`, `/api/v1/agent/search`, `/api/v1/agent/extract`, and the MCP `search`/`extract` tools carries a signed `citation_envelope`. Schema + signing process: [`docs/citation-envelope.md`](../docs/citation-envelope.md). See [ADR-0011](../docs/adr/0011-wacz-aligned-signed-envelope.md) for the design rationale.

## See also

- [`docs/architecture.md`](../docs/architecture.md) — system architecture
- [`docs/cloudflare-architecture.md`](../docs/cloudflare-architecture.md) — edge / Container wiring detail
- [`docs/API_REFERENCE.md`](../docs/API_REFERENCE.md) — full endpoint catalog
- [`docs/ai-pipeline.md`](../docs/ai-pipeline.md) — Workers AI tiers, embeddings, reranker, grader
- [`docs/operations/RUNBOOKS.md`](../docs/operations/RUNBOOKS.md) — on-call playbooks
