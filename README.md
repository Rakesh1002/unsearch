# UnSearch

> **The open-source search API for AI agents. Tavily-compatible. 10× cheaper.**

Apache 2.0. Self-hostable on Cloudflare Workers + Containers. Drop-in replacement for Tavily — change one base URL, keep your existing `client.search()` calls. $49/mo on the Growth tier vs. a ~$500/mo median across closed-source competitors.

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

For the full feature comparison, see [docs/feature-matrix.md](./docs/feature-matrix.md). For the strategy + GTM story, see [docs/strategy/](./docs/strategy/README.md).

## Quick Start

```bash
# Clone and start
git clone https://github.com/Rakesh1002/unsearch.git
cd unsearch
cp .env.example .env
# Edit .env with your credentials (see .env.example for details)
docker compose up -d
```

API available at `http://localhost:8000/docs`

### Minimal Setup (Quickstart)

```bash
docker compose -f docker-compose.quickstart.yml up -d
```

## Features

### Tavily-Compatible API (Drop-in Replacement)

```python
# Before (Tavily)
from tavily import TavilyClient
client = TavilyClient(api_key="tvly-...")
hits = client.search("query")

# After (UnSearch) — install with `pip install unsearch`
from unsearch import UnSearch
client = UnSearch(api_key="uns_...")
hits = client.tavily_search({"query": "query"})
```

### Search API

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI news", "max_results": 10}'
```

### Neural Search (Exa-Compatible)

```bash
curl -X POST http://localhost:8000/api/v1/neural/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "renewable energy innovations",
    "use_autoprompt": true,
    "num_results": 10
  }'
```

### Knowledge Graph

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/extract \
  -d '{"text": "Elon Musk founded SpaceX in 2002..."}'
```

### Topic Monitoring

```bash
curl -X POST http://localhost:8000/api/v1/monitor/topics \
  -d '{
    "topic": "AI regulation",
    "keywords": ["EU AI Act", "FTC"],
    "check_interval_minutes": 60,
    "webhook_url": "https://your-webhook.com/alerts"
  }'
```

### Fact Verification

```bash
curl -X POST http://localhost:8000/api/v1/verify/claim \
  -d '{"claim": "OpenAI was founded in 2015", "depth": "thorough"}'
```

### Deep Research Agent

```bash
curl -X POST http://localhost:8000/api/v1/agent/research \
  -d '{
    "topic": "Impact of AI on healthcare",
    "depth": "comprehensive",
    "focus_areas": ["diagnostics", "drug discovery"]
  }'
```

## AI Pipeline (Cloudflare Workers AI)

UnSearch uses Cloudflare Workers AI for answer generation, embeddings, and reasoning.

| Tier | Model | Use Case |
|------|-------|----------|
| Speed | llama-3.1-8b-instruct-fast | Simple queries |
| Quality | llama-3.3-70b-instruct-fp8-fast | General answers |
| Reasoning | qwq-32b | Complex analysis |
| Production | gpt-oss-120b | Enterprise quality |

## API Endpoints

### Tavily-Compatible
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/agent/search` | AI-powered search |
| `POST /api/v1/agent/extract` | Content extraction |
| `POST /api/v1/agent/research` | Deep research |
| `GET /api/v1/agent/models` | Available AI models |
| `GET /api/v1/agent/health` | Health check |

### Exa-Compatible (Neural Search)
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/neural/search` | Semantic search |
| `POST /api/v1/neural/similar` | Find similar content |
| `POST /api/v1/neural/highlights` | Extract key passages |

### Knowledge & Monitoring
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/knowledge/extract` | Entity extraction |
| `POST /api/v1/knowledge/search` | Knowledge search |
| `POST /api/v1/monitor/topics` | Topic monitoring |
| `POST /api/v1/verify/claim` | Fact verification |
| `POST /api/v1/verify/source` | Source credibility |

## Configuration

See [.env.example](.env.example) for all configuration options.

### Required

```bash
# Cloudflare Workers AI (for AI features)
CLOUDFLARE_ACCOUNT_ID="your_account_id"
CLOUDFLARE_API_TOKEN="your_api_token"
```

### Optional

```bash
SEARXNG_URL="http://searxng:8080"
REDIS_URL="redis://localhost:6379"
DATABASE_URL="postgresql://unsearch:unsearch@localhost:5432/unsearch"
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture |
| [AI Pipeline](docs/ai-pipeline.md) | AI features & models |
| [API Reference](docs/API_REFERENCE.md) | Full API documentation |
| [API Examples](docs/API_EXAMPLES.md) | Usage examples |
| [Feature Matrix](docs/feature-matrix.md) | Feature comparison |
| [Quickstart](docs/quickstart.md) | Getting started guide |
| [Migrate from Tavily](docs/migration/from-tavily.md) | Migration guide |

## Self-Hosting

### Docker Compose (Recommended)

```bash
docker compose up -d
```

This starts the API, SearXNG, Redis, PostgreSQL, and Celery workers.

### Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

See [docs/deployment/](docs/deployment/) for deployment guides.

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/unit/ -v --cov=app
pytest tests/integration/ -v
```

## Roadmap

### Completed
- [x] Tavily API compatibility
- [x] Exa neural search features
- [x] Knowledge graph features
- [x] Topic monitoring
- [x] Fact verification
- [x] Cloudflare Workers AI integration
- [x] 15+ AI model support
- [x] TypeScript SDK (`@unsearch/sdk`)
- [x] Python SDK (`pip install unsearch`)

### In Progress
- [ ] Full test coverage
- [ ] Production deployment guides
- [ ] MCP server (TypeScript)

### Planned
- [ ] Enterprise SSO
- [ ] Multi-region deployment

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 — See [LICENSE](LICENSE) for details.

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/Rakesh1002/unsearch/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Rakesh1002/unsearch/discussions)
