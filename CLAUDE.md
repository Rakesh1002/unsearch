# UnSearch — Developer Guide

> Guidelines for contributing to UnSearch

---

## Product Overview

**UnSearch** is an open-source search API designed for AI agents, RAG pipelines, and LLM applications. It provides real-time web search, content extraction, and deep research capabilities.

### Core APIs
1. **Search API** — Real-time web search across 70+ engines
2. **Extract API** — Scrape and structure content from any URL
3. **Research API** — Multi-step research with source citations
4. **Agent Endpoints** — Tavily-compatible drop-in replacements

### Tech Stack
- **Backend:** Python 3.11+ / FastAPI
- **Search Engine:** SearXNG (70+ engines)
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **Task Queue:** Celery
- **AI:** Cloudflare Workers AI
- **Auth:** Custom JWT + OAuth (Google, GitHub)

---

## Development Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Redis (or use Docker)
- PostgreSQL 15 (or use Docker)

### Quick Start
```bash
# Clone the repo
git clone https://github.com/Rakesh1002/unsearch.git
cd unsearch

# Copy environment config
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker compose up -d

# Or run locally
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### Running Tests
```bash
# All tests
pytest

# Unit tests with coverage
pytest tests/unit/ -v --cov=app

# Integration tests (requires running services)
pytest tests/integration/ -v

# Performance benchmarks
pytest tests/performance/ -v
```

---

## Code Style Guidelines

### Python
```python
# Use type hints
async def search(query: str, engines: list[str] | None = None) -> SearchResult:
    """
    Search the web using specified engines.

    Args:
        query: The search query
        engines: List of engine IDs (default: auto-select)

    Returns:
        SearchResult with results and metadata
    """
    pass

# Use Pydantic for data models
class SearchResult(BaseModel):
    query: str
    results: list[Result]
    response_time_ms: int
```

### Formatting
- **Black** for code formatting (line length: 120)
- **isort** for import sorting
- **Flake8** for linting
- **MyPy** for type checking

---

## API Documentation Style

### Endpoint Documentation Format
```markdown
## Search API

`POST /api/v1/search`

Search the web and optionally scrape content from results.

### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `engines` | string[] | No | Engine IDs to use |
| `max_results` | integer | No | Max results (default: 10) |
| `scrape_content` | boolean | No | Scrape page content |

### Response

\`\`\`json
{
  "query": "AI news",
  "results": [...],
  "response_time_ms": 287
}
\`\`\`
```

---

## File Structure

```
unsearch/
├── app/                    # FastAPI application
│   ├── api/v1/            # API route handlers
│   ├── models/            # Pydantic models & SQLAlchemy ORM
│   ├── services/          # Business logic
│   │   ├── core/          # Database, cache, search engine
│   │   ├── search/        # Search service
│   │   ├── scraping/      # Web scraping
│   │   ├── extraction/    # Content extraction
│   │   ├── rag/           # RAG pipeline
│   │   └── ai/            # AI integration
│   ├── middleware/        # Custom middleware
│   ├── utils/             # Utilities
│   └── workers/           # Celery tasks
├── alembic/               # Database migrations
├── tests/                 # Test suite
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── performance/
├── scripts/               # Utility scripts
├── monitoring/            # Prometheus/Grafana configs
├── docs/                  # Documentation
├── docker-compose.yml     # Full stack
├── Dockerfile
└── requirements.txt
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Run linting: `black --check app/ tests/ && isort --check-only app/ tests/`
6. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

Apache 2.0 — See [LICENSE](LICENSE) for details.
