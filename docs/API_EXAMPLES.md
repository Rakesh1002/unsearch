# SearchScrape API Examples

This document provides comprehensive examples of using the SearchScrape API.

## Table of Contents

1. [Authentication](#authentication)
2. [Basic Search](#basic-search)
3. [Search with Content Scraping](#search-with-content-scraping)
4. [Batch Search](#batch-search)
5. [Async Search](#async-search)
6. [Custom Scraping Selectors](#custom-scraping-selectors)
7. [Error Handling](#error-handling)
8. [Advanced Usage](#advanced-usage)

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

class SearchScrapeClient:
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
    client = SearchScrapeClient("your-api-key")

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
