# UnSearch AI Quick Reference

## Model Selection Cheatsheet

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL SELECTION GUIDE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Query Type           Model                    Response Time    │
│  ───────────────────────────────────────────────────────────── │
│  "What is X?"         llama-3.1-8b-fast       ~2-3s            │
│  "How does X work?"   llama-3.3-70b-fast      ~3-4s            │
│  "Why does X..."      qwq-32b                 ~30-35s          │
│  "Analyze X vs Y"     qwq-32b                 ~30-35s          │
│  Enterprise/Legal     gpt-oss-120b            ~5-6s            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## API Quick Reference

### Search with Auto Model

```bash
curl -X POST http://localhost:8000/api/v1/agent/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your query", "include_answer": true, "model": "auto"}'
```

### Search with Specific Model

```bash
# Speed (fast, simple queries)
-d '{"query": "...", "model": "speed"}'

# Quality (balanced)
-d '{"query": "...", "model": "quality"}'

# Reasoning (complex analysis)
-d '{"query": "...", "model": "reasoning"}'

# Production (maximum quality)
-d '{"query": "...", "model": "production"}'
```

### Full-Featured Search

```bash
curl -X POST http://localhost:8000/api/v1/agent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Enterprise AI best practices",
    "include_answer": "production",
    "model": "production",
    "rerank": true,
    "check_safety": true,
    "max_results": 10
  }'
```

### Deep Research

```bash
curl -X POST http://localhost:8000/api/v1/agent/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Impact of AI on industry",
    "depth": "comprehensive",
    "max_sources": 20,
    "focus_areas": ["productivity", "employment"]
  }'
```

## Python Quick Reference

```python
from unsearch import UnSearchClient

client = UnSearchClient(api_key="your-key")

# Auto model selection
result = client.search("What is Python?")

# Force production model
result = client.search(
    "Enterprise AI deployment",
    model="production",
    include_answer=True,
    rerank=True
)

# Deep research
research = client.research(
    "Future of renewable energy",
    depth="deep",
    focus_areas=["solar", "wind"]
)
```

## Model IDs

| Tier | Model ID |
|------|----------|
| Production | `@cf/openai/gpt-oss-120b` |
| Quality | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` |
| Reasoning | `@cf/qwen/qwq-32b` |
| Speed | `@cf/meta/llama-3.1-8b-instruct-fast` |
| Embeddings | `@cf/baai/bge-m3` |
| Reranker | `@cf/baai/bge-reranker-base` |
| Safety | `@cf/meta/llama-guard-3-8b` |

## Environment Variables

```bash
# Required
CLOUDFLARE_ACCOUNT_ID="your-account-id"
CLOUDFLARE_API_TOKEN="your-api-token"

# Optional (defaults shown)
CLOUDFLARE_AI_ENABLED="true"
CLOUDFLARE_EMBEDDING_MODEL="@cf/baai/bge-m3"
CLOUDFLARE_LLM_MODEL="@cf/meta/llama-3.3-70b-instruct-fp8-fast"
CLOUDFLARE_REASONING_MODEL="@cf/qwen/qwq-32b"
```

## Response Fields

```json
{
  "query": "string",
  "answer": "string",
  "results": [{"title", "url", "content", "score"}],
  "model_used": "@cf/openai/gpt-oss-120b",
  "query_complexity": "simple|moderate|complex",
  "safety_check": {"safe": true, "checked": true},
  "response_time": 3.57
}
```

## Health Check

```bash
# Check if AI is configured
curl http://localhost:8000/api/v1/agent/health

# List available models
curl http://localhost:8000/api/v1/agent/models
```
