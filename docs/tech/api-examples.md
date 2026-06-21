# UnSearch API Examples

This document provides comprehensive examples of using the UnSearch API.

## Table of Contents

1. [Authentication](#authentication)
2. [Basic Search](#basic-search)
3. [Search with Content Scraping](#search-with-content-scraping)
4. [Batch Search](#batch-search)
5. [Async Search](#async-search)
6. [Custom Scraping Selectors](#custom-scraping-selectors)
7. [Error Handling](#error-handling)
8. [Advanced Usage](#advanced-usage)
9. [Agent API (Tavily-Compatible)](#agent-api-tavily-compatible)
10. [Neural Search (Exa-Compatible)](#neural-search-exa-compatible)
11. [Deep Research API](#deep-research-api)
12. [Topic Monitoring](#topic-monitoring)
13. [Fact Verification](#fact-verification)
14. [Available AI Models](#available-ai-models)

## Authentication

All API requests require authentication using an API key.

### Using Header Authentication

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "example search"}'
```

### Using Bearer Token

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "example search"}'
```

## Basic Search

### Simple Search Query

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python programming tutorials",
    "engines": ["google", "bing"],
    "max_results": 10
  }'
```

### Python Example

```python
import httpx
import json

async def search(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/search",
            headers={"X-API-Key": "your-api-key"},
            json={
                "query": query,
                "engines": ["google", "bing", "duckduckgo"],
                "max_results": 20
            }
        )
        return response.json()

# Usage
results = await search("machine learning frameworks")
print(f"Found {len(results['results'])} results")
```

## Search with Content Scraping

### Full Content Extraction

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "FastAPI tutorial",
    "engines": ["google"],
    "max_results": 5,
    "scrape_content": true,
    "include_images": true,
    "include_links": true,
    "timeout": 60
  }'
```

### JavaScript/Node.js Example

```javascript
const axios = require("axios");

async function searchAndScrape(query) {
  try {
    const response = await axios.post(
      "http://localhost:8000/api/v1/search",
      {
        query: query,
        engines: ["google", "bing"],
        max_results: 10,
        scrape_content: true,
        include_images: true,
        include_links: true,
        language: "en",
        safe_search: "moderate",
      },
      {
        headers: {
          "X-API-Key": "your-api-key",
          "Content-Type": "application/json",
        },
      }
    );

    // Process scraped content
    response.data.results.forEach((result) => {
      if (result.scraped_content && result.scraped_content.extraction_success) {
        console.log(`Title: ${result.scraped_content.title}`);
        console.log(`Word Count: ${result.scraped_content.word_count}`);
        console.log(
          `Quality Score: ${result.scraped_content.content_quality_score}`
        );
      }
    });

    return response.data;
  } catch (error) {
    console.error("Search failed:", error.response?.data || error.message);
  }
}
```

## Batch Search

### Multiple Queries at Once

```bash
curl -X POST "http://localhost:8000/api/v1/search/batch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "Python asyncio tutorial",
      "FastAPI best practices",
      "Redis caching strategies",
      "PostgreSQL optimization"
    ],
    "engines": ["google", "bing"],
    "max_results_per_query": 5,
    "parallel_requests": 4
  }'
```

### Python Batch Example

```python
import asyncio
import httpx

async def batch_search(queries: list):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/search/batch",
            headers={"X-API-Key": "your-api-key"},
            json={
                "queries": queries,
                "engines": ["google", "duckduckgo"],
                "max_results_per_query": 10,
                "scrape_content": False,  # Disabled for performance
                "parallel_requests": 5
            },
            timeout=120.0  # Longer timeout for batch
        )

        data = response.json()
        print(f"Processed: {data['queries_processed']} queries")
        print(f"Failed: {data['queries_failed']} queries")

        return data

# Usage
queries = [
    "machine learning libraries",
    "deep learning frameworks",
    "natural language processing",
    "computer vision tools"
]

results = await batch_search(queries)
```

## Async Search

### Webhook-based Async Processing

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "large dataset processing",
    "engines": ["google", "bing", "duckduckgo"],
    "max_results": 50,
    "scrape_content": true,
    "async_mode": true,
    "webhook_url": "https://your-server.com/webhook/search-results"
  }'
```

### Webhook Handler Example (Flask)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook/search-results', methods=['POST'])
def handle_search_results():
    data = request.json

    job_id = data.get('job_id')
    status = data.get('status')
    results = data.get('results', [])

    if status == 'completed':
        print(f"Job {job_id} completed with {len(results)} results")
        # Process results
        for result in results:
            # Store in database, send notifications, etc.
            pass
    else:
        print(f"Job {job_id} failed")

    return jsonify({"received": True}), 200
```

## Custom Scraping Selectors

### Target Specific Content

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python documentation",
    "engines": ["google"],
    "max_results": 5,
    "scrape_content": true,
    "scrape_selectors": {
      "title": "h1.main-title",
      "content": "div.documentation-content",
      "code_examples": "pre.code-block",
      "sidebar": "nav.sidebar",
      "author": "span.author-name",
      "date": "time.publish-date"
    }
  }'
```

### Advanced Selector Example

```python
# Extract specific content from Stack Overflow
response = await client.post(
    "http://localhost:8000/api/v1/search",
    headers={"X-API-Key": "your-api-key"},
    json={
        "query": "site:stackoverflow.com python asyncio",
        "engines": ["google"],
        "max_results": 10,
        "scrape_content": True,
        "scrape_selectors": {
            "question": "div.question-header h1",
            "accepted_answer": "div.accepted-answer div.answercell",
            "votes": "div.js-vote-count",
            "tags": "div.post-taglist a.post-tag",
            "code_snippets": "pre code"
        }
    }
)
```

## Error Handling

### Comprehensive Error Handling

```python
import httpx
from typing import Optional, Dict, Any

class UnSearchClient:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"X-API-Key": api_key},
            timeout=30.0
        )

    async def search(self, query: str, **kwargs) -> Optional[Dict[str, Any]]:
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/search",
                json={"query": query, **kwargs}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("Authentication failed: Invalid API key")
            elif e.response.status_code == 429:
                print("Rate limit exceeded. Please wait before retrying.")
            elif e.response.status_code == 422:
                print(f"Validation error: {e.response.json()}")
            else:
                print(f"HTTP error {e.response.status_code}: {e.response.text}")
            return None

        except httpx.TimeoutException:
            print("Request timed out. Try reducing max_results or disabling scraping.")
            return None

        except httpx.RequestError as e:
            print(f"Network error: {e}")
            return None

    async def close(self):
        await self.client.aclose()

# Usage with proper error handling
async def main():
    client = UnSearchClient("your-api-key")

    try:
        results = await client.search(
            "Python web scraping",
            engines=["google", "bing"],
            max_results=10,
            scrape_content=True
        )

        if results:
            print(f"Search completed in {results['processing_time_ms']}ms")
            print(f"Found {len(results['results'])} results")
    finally:
        await client.close()
```

## Advanced Usage

### Caching Strategy

```python
# Search with custom cache TTL
response = await client.post(
    "http://localhost:8000/api/v1/search",
    json={
        "query": "Python tutorials",
        "cache_ttl": 7200,  # Cache for 2 hours
        # ... other parameters
    }
)

# Disable caching for real-time results
response = await client.post(
    "http://localhost:8000/api/v1/search",
    json={
        "query": "breaking news today",
        "cache_ttl": 0,  # No caching
        # ... other parameters
    }
)
```

### Language-Specific Search

```python
# Search in different languages
languages = ["en", "es", "fr", "de", "ja"]

for lang in languages:
    response = await client.post(
        "http://localhost:8000/api/v1/search",
        json={
            "query": "machine learning",
            "language": lang,
            "engines": ["google", "bing"],
            "max_results": 5
        }
    )
    print(f"Results for {lang}: {len(response.json()['results'])}")
```

### Safe Search Levels

```python
# Different safe search levels
safe_search_levels = ["off", "moderate", "strict"]

for level in safe_search_levels:
    response = await client.post(
        "http://localhost:8000/api/v1/search",
        json={
            "query": "art photography",
            "safe_search": level,
            "engines": ["google"],
            "max_results": 10
        }
    )
```

### Performance Optimization

```python
# Optimize for speed - disable scraping
fast_search = {
    "query": "quick search",
    "engines": ["duckduckgo"],  # Fastest engine
    "max_results": 10,
    "scrape_content": False,
    "cache_ttl": 3600
}

# Optimize for completeness - enable everything
thorough_search = {
    "query": "comprehensive research",
    "engines": ["google", "bing", "duckduckgo", "startpage", "qwant"],
    "max_results": 50,
    "scrape_content": True,
    "include_images": True,
    "include_links": True,
    "timeout": 120
}
```

### Monitoring and Analytics

```python
# Get search engines status
engines_response = await client.get(
    "http://localhost:8000/api/v1/search/engines",
    headers={"X-API-Key": "your-api-key"}
)

engines = engines_response.json()
print(f"Total engines: {engines['total_engines']}")
print(f"Enabled engines: {engines['enabled_engines']}")

for name, info in engines['engines'].items():
    if info['enabled']:
        print(f"- {name}: {', '.join(info['categories'])}")
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- Default: 1000 requests per hour
- Burst: 100 requests
- Rate limit info is returned in response headers:
  - `X-RateLimit-Limit`: Your rate limit
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets

```python
# Check rate limit headers
response = await client.post("/api/v1/search", json={...})
print(f"Remaining requests: {response.headers.get('X-RateLimit-Remaining')}")
print(f"Limit resets at: {response.headers.get('X-RateLimit-Reset')}")
```

---

## Agent API (Tavily-Compatible)

The Agent API provides Tavily-compatible endpoints for easy migration. Simply change your base URL.

### Agent Search

```bash
curl -X POST "http://localhost:8000/api/v1/agent/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "search_depth": "basic",
    "max_results": 5,
    "include_answer": true
  }'
```

### Agent Search with AI Answer

```python
response = await client.post(
    "http://localhost:8000/api/v1/agent/search",
    headers={"X-API-Key": "your-api-key"},
    json={
        "query": "How does photosynthesis work?",
        "search_depth": "advanced",
        "max_results": 10,
        "include_answer": "production",  # Use gpt-oss-120b
        "include_raw_content": True
    }
)

data = response.json()
print(f"Answer: {data['answer']}")
print(f"Model used: {data['model_used']}")
```

### Agent Extract (Content Extraction)

```bash
curl -X POST "http://localhost:8000/api/v1/agent/extract" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "https://docs.python.org/3/tutorial/"
    ],
    "extract_depth": "advanced"
  }'
```

---

## Neural Search (Exa-Compatible)

Semantic search using embeddings for conceptual matching.

### Basic Neural Search

```bash
curl -X POST "http://localhost:8000/api/v1/neural/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how do neural networks learn",
    "num_results": 10,
    "use_autoprompt": true,
    "include_highlights": true
  }'
```

### Find Similar Content

```python
response = await client.post(
    "http://localhost:8000/api/v1/neural/similar",
    headers={"X-API-Key": "your-api-key"},
    json={
        "url": "https://example.com/article-about-ai",
        "num_results": 10,
        "exclude_source": True
    }
)

for result in response.json()['similar']:
    print(f"{result['title']} - Score: {result['score']}")
```

### Extract Highlights

```bash
curl -X POST "http://localhost:8000/api/v1/neural/highlights" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "benefits of machine learning",
    "content": "Machine learning is a subset of AI...",
    "num_highlights": 3
  }'
```

---

## Deep Research API

Multi-source research with AI synthesis for comprehensive topic coverage.

### Quick Research

```bash
curl -X POST "http://localhost:8000/api/v1/rag/research" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "quantum computing applications",
    "depth": "quick",
    "scrape_content": true
  }'
```

### Deep Research with Analysis

```python
response = await client.post(
    "http://localhost:8000/api/v1/agent/research",
    headers={"X-API-Key": "your-api-key"},
    json={
        "query": "Impact of AI on healthcare",
        "depth": "deep",
        "max_sources": 20,
        "include_analysis": True,
        "include_summary": True,
        "focus_areas": ["diagnostics", "drug discovery"]
    }
)

data = response.json()
print(f"Executive Summary: {data['executive_summary']}")
print(f"Key Findings: {data['key_findings']}")
print(f"Sources analyzed: {len(data['sources'])}")
```

---

## Topic Monitoring

Real-time web monitoring with webhook alerts.

### Create a Topic Monitor

```bash
curl -X POST "http://localhost:8000/api/v1/monitor/topics" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI regulations",
    "keywords": ["GDPR", "AI Act", "OpenAI"],
    "check_interval_minutes": 60,
    "webhook_url": "https://your-app.com/webhooks/monitor",
    "deep_analysis": true
  }'
```

### List Active Monitors

```bash
curl -X GET "http://localhost:8000/api/v1/monitor/topics" \
  -H "X-API-Key: your-api-key"
```

### Get Monitor Results

```python
response = await client.get(
    f"http://localhost:8000/api/v1/monitor/topics/{monitor_id}/results",
    headers={"X-API-Key": "your-api-key"}
)

for result in response.json()['results']:
    print(f"New content found at {result['timestamp']}")
    for item in result['new_results']:
        print(f"  - {item['title']}: {item['url']}")
```

---

## Fact Verification

Verify claims against multiple sources with credibility scoring.

### Verify a Claim

```bash
curl -X POST "http://localhost:8000/api/v1/verify/claim" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "GPT-4 was released in March 2023",
    "depth": "thorough",
    "include_sources": true
  }'
```

### Response Example

```json
{
  "claim": "GPT-4 was released in March 2023",
  "verdict": "true",
  "confidence": 95,
  "summary": "GPT-4 was officially released by OpenAI on March 14, 2023.",
  "supporting_evidence": [
    {
      "title": "OpenAI GPT-4 Announcement",
      "url": "https://openai.com/research/gpt-4",
      "snippet": "We've created GPT-4, released on March 14, 2023...",
      "stance": "supporting"
    }
  ],
  "contradicting_evidence": [],
  "sources_checked": 12
}
```

### Check Source Credibility

```python
response = await client.post(
    "http://localhost:8000/api/v1/verify/source",
    headers={"X-API-Key": "your-api-key"},
    json={
        "url": "https://www.reuters.com"
    }
)

data = response.json()
print(f"Domain: {data['domain']}")
print(f"Credibility Score: {data['credibility_score']}/100")
print(f"Category: {data['category']}")
print(f"Bias Rating: {data['bias_rating']}")
```

---

## Available AI Models

UnSearch supports multiple AI models for different use cases.

### List Available Models

```bash
curl -X GET "http://localhost:8000/api/v1/agent/models" \
  -H "X-API-Key: your-api-key"
```

### Model Tiers

| Tier | Model | Use Case |
|------|-------|----------|
| **speed** | llama-3.1-8b-instruct-fast | Simple queries, low latency |
| **quality** | llama-3.3-70b-instruct-fp8-fast | Balanced quality/speed |
| **reasoning** | qwq-32b | Complex analytical queries |
| **production** | gpt-oss-120b | Maximum quality, enterprise |

### Using Specific Model Tiers

```python
# Use reasoning model for complex analysis
response = await client.post(
    "http://localhost:8000/api/v1/agent/search",
    json={
        "query": "Compare the pros and cons of microservices vs monoliths",
        "include_answer": True,
        "model": "reasoning"  # Uses qwq-32b
    }
)

# Use production model for maximum quality
response = await client.post(
    "http://localhost:8000/api/v1/agent/search",
    json={
        "query": "Explain quantum entanglement",
        "include_answer": "production"  # Uses gpt-oss-120b
    }
)
```
