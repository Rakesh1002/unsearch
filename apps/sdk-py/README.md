# unsearch

Official Python SDK for [UnSearch](https://unsearch.dev) — open-source search API for AI agents.

Ships sync and async clients with the same surface. Works with any web search, neural search, RAG, monitoring, fact-verification, and Tavily-compatible endpoint exposed by the UnSearch API.

## Install

```bash
pip install unsearch
```

Requires Python 3.9+.

## Quick start

```python
from unsearch import UnSearch

client = UnSearch(api_key="uns_...")

# Web search
results = client.search({"query": "Cloudflare Workers in 2026", "max_results": 10})
for hit in results["results"]:
    print(hit["rank"], hit["title"], hit["url"])

# Neural / semantic search
neural = client.neural_search({"query": "vector databases for AI agents", "top_k": 5})

# RAG grounded in your namespace
answer = client.rag_query({"query": "How does D1 differ from Postgres?", "model_tier": "reasoning"})
print(answer["answer"])

# Stream tokens
for chunk in client.stream_rag({"query": "Explain Durable Objects"}):
    if chunk["event"] == "token":
        print(chunk["data"], end="", flush=True)

# Multi-step research agent
session = client.start_research("AI agent landscape 2026", depth=4)
final = client.poll_research(session["session_id"])
print(final.get("finalAnswer"))

# Tavily-compatible drop-in: same request shape as `tavily-python`'s search()
tavily_shape = client.tavily_search({"query": "AI news", "include_answer": True})
```

## Async

```python
import asyncio
from unsearch import AsyncUnSearch

async def main():
    async with AsyncUnSearch(api_key="uns_...") as client:
        results = await client.search({"query": "edge compute"})
        async for chunk in client.stream_rag({"query": "Explain Vectorize"}):
            if chunk["event"] == "token":
                print(chunk["data"], end="", flush=True)

asyncio.run(main())
```

## Migrating from Tavily

```python
# Before
from tavily import TavilyClient
client = TavilyClient(api_key="tvly-...")
hits = client.search("AI news")

# After
from unsearch import UnSearch
client = UnSearch(api_key="uns_...")
hits = client.tavily_search({"query": "AI news"})
```

The `tavily_search` method posts to `/api/v1/agent/search`, which mirrors Tavily's request and response schema.

## Errors

Every non-2xx response raises `UnSearchError`:

```python
from unsearch import UnSearch, UnSearchError

try:
    client.search({"query": ""})
except UnSearchError as exc:
    print(exc.status, exc.body)
```

## License

Apache-2.0
