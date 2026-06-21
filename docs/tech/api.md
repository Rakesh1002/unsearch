# UnSearch API Reference

Complete API documentation with request/response schemas, use cases, and implementation examples.

**Base URL:** `https://api.unsearch.dev/api/v1`

**Authentication:** All endpoints require an API key via header:
- `X-API-Key: uns_your_api_key` or
- `Authorization: Bearer uns_your_api_key`

---

## Table of Contents

1. [Search API](#search-api) - Core web search with optional scraping
2. [Agent API](#agent-api) - Tavily-compatible AI search
3. [Neural API](#neural-api) - Exa-compatible semantic search
4. [RAG API](#rag-api) - Deep research and retrieval
5. [Verify API](#verify-api) - Fact-checking and verification
6. [Monitor API](#monitor-api) - Real-time topic monitoring
7. [Error Handling](#error-handling)
8. [Rate Limits](#rate-limits)

---

## Search API

Core search and scraping endpoints for web search with optional content extraction.

### POST /search

Perform web search with optional content scraping from results.

#### Use Cases

- **RAG Applications**: Get search results with full page content for LLM context
- **Content Aggregation**: Gather information from multiple sources
- **Research Tools**: Build comprehensive search interfaces
- **Data Collection**: Extract structured data from web pages

#### Request Schema

```json
{
  "query": "string (required, 1-500 chars)",
  "engines": ["google", "bing", "duckduckgo"],
  "max_results": 10,
  "scrape_content": true,
  "scrape_selectors": {
    "title": "h1",
    "content": "article",
    "author": ".author-name"
  },
  "output_format": "json",
  "cache_ttl": 3600,
  "language": "en",
  "safe_search": "moderate",
  "include_images": true,
  "include_links": true,
  "timeout": 30,
  "async_mode": false,
  "js_mode": false,
  "screenshot": false,
  "pdf": false,
  "webhook_url": "https://your-server.com/webhook"
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query (1-500 characters) |
| `engines` | string[] | No | `["google", "bing", "duckduckgo"]` | Search engines to use. Options: `google`, `bing`, `duckduckgo`, `startpage`, `qwant`, `yahoo`, `searx`, `brave`, `ecosia` |
| `max_results` | integer | No | 10 | Maximum results (1-100) |
| `scrape_content` | boolean | No | true | Whether to scrape full page content |
| `scrape_selectors` | object | No | null | Custom CSS selectors for extraction |
| `output_format` | string | No | "json" | Response format: `json` or `markdown` |
| `cache_ttl` | integer | No | 3600 | Cache TTL in seconds (0-86400, 0 disables) |
| `language` | string | No | "en" | ISO 639-1 language code |
| `safe_search` | string | No | "moderate" | Safe search: `off`, `moderate`, `strict` |
| `include_images` | boolean | No | true | Extract images from scraped content |
| `include_links` | boolean | No | true | Extract links from scraped content |
| `timeout` | integer | No | 30 | Request timeout in seconds (5-120) |
| `async_mode` | boolean | No | false | Process asynchronously via webhook |
| `js_mode` | boolean | No | false | Use headless browser for JS rendering |
| `screenshot` | boolean | No | false | Capture screenshot (requires js_mode) |
| `pdf` | boolean | No | false | Capture PDF (requires js_mode) |
| `webhook_url` | string | No | null | Webhook URL for async results (required if async_mode=true) |

#### Response Schema

```json
{
  "search_metadata": {
    "query": "Python web scraping",
    "engines_used": ["google", "bing"],
    "engines_succeeded": ["google", "bing"],
    "engines_failed": [],
    "total_results_found": 250,
    "results_returned": 10,
    "search_time_ms": 1250,
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "results": [
    {
      "rank": 1,
      "title": "Python Web Scraping Tutorial",
      "url": "https://example.com/python-scraping",
      "snippet": "Learn how to scrape websites using Python...",
      "engine": "google",
      "score": 0.95,
      "cached": false,
      "scraped_content": {
        "url": "https://example.com/python-scraping",
        "title": "Complete Python Web Scraping Guide",
        "text": "Full extracted content...",
        "html": "<html>...</html>",
        "images": ["https://example.com/img1.png"],
        "links": ["https://example.com/related"],
        "metadata": {
          "title": "Complete Python Web Scraping Guide",
          "description": "Learn web scraping with Python",
          "author": "John Doe",
          "published_date": "2024-01-10T00:00:00Z",
          "keywords": ["python", "scraping", "tutorial"],
          "og_data": {},
          "twitter_data": {}
        },
        "extraction_success": true,
        "extraction_time_ms": 850,
        "word_count": 2500,
        "language_detected": "en",
        "content_quality_score": 0.92
      }
    }
  ],
  "processing_time_ms": 2500,
  "cached": false,
  "cache_key": "search:abc123",
  "total_results": 10,
  "request_id": "req_xyz789"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `search_metadata` | object | Search operation metadata |
| `search_metadata.query` | string | Original search query |
| `search_metadata.engines_used` | string[] | Engines that were queried |
| `search_metadata.engines_succeeded` | string[] | Engines that returned results |
| `search_metadata.engines_failed` | string[] | Engines that failed |
| `search_metadata.total_results_found` | integer | Total results across all engines |
| `search_metadata.results_returned` | integer | Results in this response |
| `search_metadata.search_time_ms` | integer | Search execution time |
| `search_metadata.timestamp` | string | ISO 8601 timestamp |
| `results` | array | Array of search results |
| `results[].rank` | integer | Result ranking position |
| `results[].title` | string | Page title |
| `results[].url` | string | Page URL |
| `results[].snippet` | string | Search result snippet |
| `results[].engine` | string | Source search engine |
| `results[].score` | float | Relevance score (0-1) |
| `results[].cached` | boolean | Whether result was cached |
| `results[].scraped_content` | object | Scraped content (if enabled) |
| `processing_time_ms` | integer | Total processing time |
| `cached` | boolean | Whether response was cached |
| `cache_key` | string | Cache key for this query |
| `total_results` | integer | Number of results returned |
| `request_id` | string | Unique request identifier |

#### ScrapedContent Object

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | Scraped URL |
| `title` | string | Page title |
| `text` | string | Extracted text content |
| `html` | string | Raw HTML (if requested) |
| `images` | string[] | Extracted image URLs |
| `links` | string[] | Extracted link URLs |
| `metadata` | object | Page metadata (OG, Twitter, etc.) |
| `extraction_success` | boolean | Whether extraction succeeded |
| `extraction_time_ms` | integer | Extraction time |
| `word_count` | integer | Content word count |
| `language_detected` | string | Detected language |
| `content_quality_score` | float | Quality score (0-1) |

#### Example: Basic Search

```bash
curl -X POST "https://api.unsearch.dev/api/v1/search" \
  -H "X-API-Key: uns_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning frameworks comparison",
    "engines": ["google", "bing"],
    "max_results": 5,
    "scrape_content": false
  }'
```

#### Example: Search with Scraping

```python
import httpx

async def search_and_scrape(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.unsearch.dev/api/v1/search",
            headers={"X-API-Key": "uns_your_api_key"},
            json={
                "query": query,
                "engines": ["google", "bing", "duckduckgo"],
                "max_results": 10,
                "scrape_content": True,
                "include_images": True,
                "include_links": True
            }
        )
        data = response.json()
        
        for result in data["results"]:
            if result.get("scraped_content"):
                print(f"Title: {result['scraped_content']['title']}")
                print(f"Words: {result['scraped_content']['word_count']}")
                print(f"Quality: {result['scraped_content']['content_quality_score']}")
        
        return data
```

#### Example: JavaScript Rendering

```javascript
const response = await fetch("https://api.unsearch.dev/api/v1/search", {
  method: "POST",
  headers: {
    "X-API-Key": "uns_your_api_key",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    query: "react spa example",
    engines: ["google"],
    max_results: 5,
    scrape_content: true,
    js_mode: true,  // Enable headless browser
    screenshot: true  // Capture screenshots
  })
});

const data = await response.json();
```

---

### POST /search/batch

Process multiple search queries in parallel.

#### Use Cases

- **Bulk Research**: Search multiple related topics at once
- **Competitor Analysis**: Search for multiple brands/products
- **Content Research**: Gather sources for multiple articles
- **SEO Analysis**: Check rankings for multiple keywords

#### Request Schema

```json
{
  "queries": [
    "Python asyncio tutorial",
    "FastAPI best practices",
    "Redis caching strategies"
  ],
  "engines": ["google", "bing"],
  "max_results_per_query": 5,
  "scrape_content": false,
  "parallel_requests": 5
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `queries` | string[] | Yes | - | List of queries (1-100) |
| `engines` | string[] | No | `["google", "bing"]` | Search engines |
| `max_results_per_query` | integer | No | 5 | Results per query (1-20) |
| `scrape_content` | boolean | No | false | Scrape content (disabled by default for performance) |
| `parallel_requests` | integer | No | 5 | Parallel request limit (1-20) |

#### Response Schema

```json
{
  "batch_id": "batch_abc123",
  "queries_processed": 3,
  "queries_failed": 0,
  "results": {
    "Python asyncio tutorial": [
      {
        "rank": 1,
        "title": "Asyncio Tutorial",
        "url": "https://example.com/asyncio",
        "snippet": "Learn Python asyncio...",
        "engine": "google"
      }
    ],
    "FastAPI best practices": [...],
    "Redis caching strategies": [...]
  },
  "processing_time_ms": 3500,
  "errors": {}
}
```

#### Example: Batch Search

```python
queries = [
    "machine learning libraries",
    "deep learning frameworks", 
    "natural language processing tools"
]

response = await client.post(
    "https://api.unsearch.dev/api/v1/search/batch",
    headers={"X-API-Key": "uns_your_api_key"},
    json={
        "queries": queries,
        "engines": ["google", "duckduckgo"],
        "max_results_per_query": 10,
        "parallel_requests": 5
    }
)

data = response.json()
print(f"Processed: {data['queries_processed']} queries")
print(f"Failed: {data['queries_failed']} queries")

for query, results in data["results"].items():
    print(f"\n{query}: {len(results)} results")
```

---

### GET /search/engines

List available search engines and their capabilities.

#### Response Schema

```json
{
  "engines": {
    "google": {
      "name": "google",
      "enabled": true,
      "categories": ["general", "images", "news"],
      "supported_languages": ["*"],
      "safe_search_support": true,
      "time_range_support": true,
      "paging_support": true
    },
    "bing": {...},
    "duckduckgo": {...}
  },
  "total_engines": 15,
  "enabled_engines": 12
}
```

---

### GET /search/health

Check health of search services.

#### Response Schema

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "services": {
    "searxng": {
      "status": "healthy",
      "latency_ms": 120,
      "last_check": "2024-01-15T10:30:00Z"
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 5,
      "last_check": "2024-01-15T10:30:00Z"
    },
    "database": {
      "status": "healthy",
      "latency_ms": 15,
      "last_check": "2024-01-15T10:30:00Z"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 86400
}
```

---

## Agent API

Tavily-compatible endpoints for AI agents. Drop-in replacement - just change your base URL.

### POST /agent/search

AI-optimized web search with optional answer generation.

#### Use Cases

- **LLM Tool Calling**: Give AI agents web search capability
- **RAG Pipelines**: Retrieve context for generation
- **Chatbots**: Answer questions with real-time web data
- **Research Assistants**: Automated information gathering

#### Request Schema

```json
{
  "query": "What is machine learning?",
  "search_depth": "basic",
  "max_results": 5,
  "topic": "general",
  "include_answer": true,
  "include_raw_content": false,
  "include_images": false,
  "include_image_descriptions": false,
  "include_domains": ["wikipedia.org", "arxiv.org"],
  "exclude_domains": ["pinterest.com"],
  "rerank": false,
  "model": "auto",
  "check_safety": false
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `search_depth` | string | No | "basic" | `basic`, `advanced`, `fast`, `ultra-fast` |
| `max_results` | integer | No | 5 | Results to return (1-20) |
| `topic` | string | No | "general" | `general`, `news`, `finance` |
| `include_answer` | bool/string | No | false | `true`, `false`, `"basic"`, `"advanced"`, `"production"` |
| `include_raw_content` | bool/string | No | false | `true`, `false`, `"markdown"`, `"text"` |
| `include_images` | boolean | No | false | Include image results |
| `include_domains` | string[] | No | null | Only include these domains |
| `exclude_domains` | string[] | No | null | Exclude these domains |
| `rerank` | boolean | No | false | AI reranking for relevance |
| `model` | string | No | "auto" | `auto`, `speed`, `quality`, `reasoning`, `production` |
| `check_safety` | boolean | No | false | Run content safety checks |

#### Model Options

| Model | ID | Best For |
|-------|-----|----------|
| `auto` | Auto-select | Default - picks best model for query |
| `speed` | llama-3.1-8b-instruct-fast | Simple queries, low latency |
| `quality` | llama-3.3-70b-instruct-fp8-fast | Balanced quality/speed |
| `reasoning` | qwq-32b | Complex analytical queries |
| `production` | gpt-oss-120b | Maximum quality, enterprise |

#### Response Schema

```json
{
  "query": "What is machine learning?",
  "answer": "Machine learning is a subset of artificial intelligence...",
  "images": [],
  "results": [
    {
      "title": "Machine Learning - Wikipedia",
      "url": "https://en.wikipedia.org/wiki/Machine_learning",
      "content": "Machine learning is a branch of AI...",
      "score": 0.95,
      "raw_content": null
    }
  ],
  "response_time": 1.25,
  "model_used": "llama-3.3-70b-instruct-fp8-fast",
  "query_complexity": "simple",
  "safety_check": null
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original query |
| `answer` | string | AI-generated answer (if requested) |
| `images` | array | Image results (if requested) |
| `results` | array | Search results |
| `results[].title` | string | Page title |
| `results[].url` | string | Page URL |
| `results[].content` | string | Snippet or content (up to 500 chars) |
| `results[].score` | float | Relevance score (0-1) |
| `results[].raw_content` | string | Full page content (if requested) |
| `response_time` | float | Response time in seconds |
| `model_used` | string | AI model used |
| `query_complexity` | string | Detected complexity |

#### Example: Basic Agent Search

```bash
curl -X POST "https://api.unsearch.dev/api/v1/agent/search" \
  -H "X-API-Key: uns_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the benefits of RAG in AI?",
    "include_answer": true,
    "max_results": 5
  }'
```

#### Example: Production Quality Answer

```python
response = await client.post(
    "https://api.unsearch.dev/api/v1/agent/search",
    json={
        "query": "Explain quantum computing applications",
        "include_answer": "production",
        "model": "production",
        "max_results": 10,
        "include_raw_content": True
    }
)
data = response.json()
print(f"Answer: {data['answer']}")
print(f"Model: {data['model_used']}")
```

---

### POST /agent/extract

Extract content from URLs (Tavily /extract compatible).

#### Request Schema

```json
{
  "urls": [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://docs.python.org/3/tutorial/"
  ],
  "include_images": false,
  "extract_depth": "basic"
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `urls` | string[] | Yes | - | URLs to extract (max 20) |
| `include_images` | boolean | No | false | Extract images |
| `extract_depth` | string | No | "basic" | `basic` or `advanced` (JS rendering) |

#### Response Schema

```json
{
  "results": [
    {
      "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "raw_content": "Artificial intelligence (AI) is intelligence...",
      "images": [],
      "failed": false,
      "error": null
    }
  ],
  "failed_urls": [],
  "response_time": 2.5
}
```

---

### POST /agent/research

Deep research with AI synthesis (UnSearch exclusive).

#### Use Cases

- **Comprehensive Reports**: Multi-source research synthesis
- **Due Diligence**: Thorough investigation of topics
- **Academic Research**: Gather and analyze sources
- **Market Analysis**: Deep dive into industry topics

#### Request Schema

```json
{
  "query": "Impact of AI on healthcare",
  "depth": "deep",
  "max_sources": 20,
  "include_analysis": true,
  "include_summary": true,
  "focus_areas": ["diagnostics", "drug discovery"]
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Research question/topic |
| `depth` | string | No | "standard" | `quick`, `standard`, `deep`, `comprehensive` |
| `max_sources` | integer | No | 10 | Target sources (3-30) |
| `include_analysis` | boolean | No | true | Include detailed analysis |
| `include_summary` | boolean | No | true | Include executive summary |
| `focus_areas` | string[] | No | null | Specific areas to emphasize |

#### Depth Levels

| Depth | Sources | Model | Use Case |
|-------|---------|-------|----------|
| `quick` | 3-5 | llama-3.1-8b-fast | Fast overview |
| `standard` | 5-10 | llama-3.3-70b-fast | Balanced research |
| `deep` | 10-20 | qwq-32b | Thorough analysis |
| `comprehensive` | 20-30 | gpt-oss-120b | Expert-level |

#### Response Schema

```json
{
  "query": "Impact of AI on healthcare",
  "executive_summary": "AI is transforming healthcare across...",
  "detailed_analysis": "## Current State\n\nAI in healthcare...",
  "key_findings": [
    "AI diagnostics show 95% accuracy in certain conditions",
    "Drug discovery time reduced by 40% with AI"
  ],
  "sources": [
    {
      "title": "AI in Healthcare Report 2024",
      "url": "https://example.com/ai-healthcare",
      "content": "Summary of the article...",
      "score": 0.92,
      "raw_content": "Full article content..."
    }
  ],
  "methodology": {
    "depth": "deep",
    "sources_analyzed": 18,
    "engines_used": ["google", "bing", "duckduckgo"],
    "content_scraped": true
  },
  "model_used": "qwq-32b",
  "response_time": 45.2
}
```

---

## Neural API

Exa-compatible semantic search using embeddings for conceptual matching.

### POST /neural/search

Semantic search with optional query expansion and highlights.

#### Use Cases

- **Conceptual Search**: Find results by meaning, not keywords
- **Research Discovery**: Find related content you didn't know to search for
- **Content Recommendations**: Discover similar articles
- **Knowledge Exploration**: Explore topics semantically

#### Request Schema

```json
{
  "query": "how do neural networks learn",
  "num_results": 10,
  "use_autoprompt": true,
  "include_highlights": true,
  "include_domains": ["arxiv.org", "nature.com"],
  "exclude_domains": ["pinterest.com"],
  "start_published_date": "2024-01-01",
  "end_published_date": "2024-12-31",
  "category": "academic"
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `num_results` | integer | No | 10 | Results (1-50) |
| `use_autoprompt` | boolean | No | false | AI query expansion |
| `include_highlights` | boolean | No | true | Include key passages |
| `include_domains` | string[] | No | null | Only these domains |
| `exclude_domains` | string[] | No | null | Exclude these domains |
| `start_published_date` | string | No | null | Filter by date (YYYY-MM-DD) |
| `end_published_date` | string | No | null | Filter by date (YYYY-MM-DD) |
| `category` | string | No | null | `general`, `news`, `academic`, `tech`, `finance` |

#### Response Schema

```json
{
  "query": "how do neural networks learn",
  "expanded_queries": [
    "neural network training process",
    "backpropagation algorithm explained",
    "deep learning optimization"
  ],
  "results": [
    {
      "title": "Understanding Neural Network Learning",
      "url": "https://example.com/nn-learning",
      "content": "Neural networks learn through...",
      "score": 0.92,
      "published_date": "2024-03-15",
      "author": "Dr. Smith",
      "highlights": [
        "The backpropagation algorithm adjusts weights...",
        "Gradient descent optimizes the loss function..."
      ]
    }
  ],
  "autoprompt_used": true,
  "search_type": "neural",
  "response_time_ms": 1850
}
```

---

### POST /neural/similar

Find content similar to a URL or text.

#### Request Schema

```json
{
  "url": "https://example.com/article-about-ai",
  "text": null,
  "num_results": 10,
  "exclude_source": true
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | No* | null | URL to find similar content for |
| `text` | string | No* | null | Text to find similar content for |
| `num_results` | integer | No | 10 | Results (1-50) |
| `exclude_source` | boolean | No | true | Exclude source URL from results |

*Either `url` or `text` is required.

#### Response Schema

```json
{
  "source": "https://example.com/article-about-ai",
  "similar": [
    {
      "title": "Related AI Article",
      "url": "https://other.com/ai-article",
      "content": "This article discusses...",
      "score": 0.88
    }
  ],
  "response_time_ms": 2100
}
```

---

### POST /neural/highlights

Extract key relevant passages from content.

#### Request Schema

```json
{
  "query": "benefits of machine learning",
  "content": "Machine learning is a subset of AI that enables...",
  "num_highlights": 3
}
```

#### Response Schema

```json
{
  "query": "benefits of machine learning",
  "highlights": [
    {
      "text": "Machine learning enables automated decision-making...",
      "relevance": 0.95,
      "start_index": 150
    }
  ]
}
```

---

### POST /neural/predictive

Predict what the user might search for next (UnSearch exclusive).

#### Request Schema

```json
{
  "context": "Current page content about Python programming...",
  "recent_searches": ["python tutorial", "flask api"],
  "num_predictions": 5
}
```

#### Response Schema

```json
{
  "predictions": [
    {
      "query": "python web frameworks comparison",
      "confidence": 0.85,
      "reason": "Based on Flask interest and Python context"
    }
  ],
  "context_used": true
}
```

---

## RAG API

Deep research and retrieval-augmented generation endpoints.

### POST /rag/research

Comprehensive multi-query research on a topic.

#### Use Cases

- **Knowledge Base Building**: Gather sources for AI training
- **Content Generation**: Research for article writing
- **Competitive Analysis**: Deep dive into market topics
- **Academic Research**: Systematic literature gathering

#### Request Schema

```json
{
  "topic": "How does vector database indexing work?",
  "depth": "standard",
  "num_queries": 10,
  "target_sources": 50,
  "categories": ["technical", "practical", "comparison"],
  "engines": ["google", "bing", "duckduckgo"],
  "scrape_content": true,
  "generate_embeddings": true,
  "language": "en"
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `topic` | string | Yes | - | Research topic (3-500 chars) |
| `depth` | string | No | "standard" | `quick`, `standard`, `deep` |
| `num_queries` | integer | No | null | Override query count (1-50) |
| `target_sources` | integer | No | null | Target source count (5-500) |
| `categories` | string[] | No | null | Query categories to include |
| `engines` | string[] | No | ["google","bing","duckduckgo"] | Search engines |
| `scrape_content` | boolean | No | true | Scrape full content |
| `generate_embeddings` | boolean | No | true | Create embeddings for semantic search |
| `language` | string | No | "en" | Language code |

#### Depth Configurations

| Depth | Queries | Target Sources |
|-------|---------|----------------|
| `quick` | 5 | 20 |
| `standard` | 10 | 50 |
| `deep` | 25 | 150 |

#### Query Categories

- `overview` - Definitions and introductions
- `history` - Historical context
- `current_state` - Recent developments
- `technical` - Implementation details
- `practical` - How-to guides
- `comparison` - Alternatives analysis
- `expert_opinion` - Industry insights
- `future_trends` - Predictions
- `case_studies` - Real examples
- `best_practices` - Recommendations

#### Response Schema

```json
{
  "topic": "Vector database indexing",
  "corpus_id": "abc123def456",
  "sources": [
    {
      "url": "https://example.com/vector-db",
      "title": "Understanding Vector Databases",
      "content": "Vector databases use specialized indexing...",
      "summary": "This article explains HNSW and IVF indexing...",
      "relevance_score": 0.92,
      "word_count": 2500,
      "engine": "google",
      "scraped_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total_sources_found": 85,
  "queries_executed": [
    "vector database indexing",
    "how vector search works",
    "HNSW algorithm explained"
  ],
  "processing_time_ms": 15000,
  "depth": "standard"
}
```

---

### POST /rag/search

Quick RAG-optimized single-query search.

#### Request Schema

```json
{
  "query": "How does RAG work?",
  "max_sources": 10,
  "scrape_content": true,
  "engines": ["google", "bing", "duckduckgo"],
  "include_context": true
}
```

#### Response Schema

```json
{
  "query": "How does RAG work?",
  "context": "[Source 1] RAG Overview\nURL: https://...\nContent: RAG combines retrieval...\n---\n[Source 2]...",
  "sources": [...],
  "source_count": 10,
  "processing_time_ms": 3500
}
```

---

### POST /rag/semantic-search

Search a research corpus using vector similarity.

#### Request Schema

```json
{
  "corpus_id": "abc123def456",
  "query": "HNSW indexing performance",
  "limit": 10,
  "min_relevance": 0.5
}
```

#### Response Schema

```json
{
  "corpus_id": "abc123def456",
  "query": "HNSW indexing performance",
  "results": [
    {
      "id": "vec_123",
      "score": 0.89,
      "url": "https://example.com/hnsw",
      "title": "HNSW Performance Analysis",
      "summary": "HNSW achieves logarithmic search complexity...",
      "relevance_score": 0.92
    }
  ],
  "total_results": 8,
  "processing_time_ms": 120
}
```

---

### POST /rag/images

Search for images.

#### Request Schema

```json
{
  "query": "machine learning architecture diagram",
  "max_results": 20,
  "safe_search": "moderate",
  "engines": ["google images", "bing images"]
}
```

#### Response Schema

```json
{
  "query": "machine learning architecture diagram",
  "images": [
    {
      "url": "https://example.com/ml-diagram.png",
      "thumbnail_url": "https://example.com/ml-diagram-thumb.png",
      "title": "Neural Network Architecture",
      "source_url": "https://example.com/article",
      "width": 1200,
      "height": 800,
      "engine": "google images"
    }
  ],
  "total_results": 20,
  "processing_time_ms": 850
}
```

---

## Verify API

Fact-checking and source credibility assessment (UnSearch exclusive).

### POST /verify/claim

Verify a claim using multi-source fact-checking.

#### Use Cases

- **Fact-Checking**: Verify news and claims
- **Content Moderation**: Assess accuracy of user content
- **Research Validation**: Verify research findings
- **Misinformation Detection**: Identify false claims

#### Request Schema

```json
{
  "claim": "GPT-4 was released in March 2023",
  "depth": "thorough",
  "include_sources": true
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `claim` | string | Yes | - | Claim to verify |
| `depth` | string | No | "quick" | `quick` or `thorough` |
| `include_sources` | boolean | No | true | Include source URLs |

#### Response Schema

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
      "stance": "supporting",
      "credibility_score": 0.98
    }
  ],
  "contradicting_evidence": [],
  "key_facts": [
    "GPT-4 announced March 14, 2023",
    "Released via ChatGPT Plus and API"
  ],
  "nuances": "Initial release was limited; broader access came later.",
  "sources_checked": 12,
  "verification_time_ms": 3500
}
```

#### Verdict Values

| Verdict | Description |
|---------|-------------|
| `true` | Claim is accurate |
| `false` | Claim is inaccurate |
| `partially_true` | Claim contains some truth but is misleading |
| `misleading` | Claim is technically true but deceptive |
| `unverifiable` | Not enough evidence to determine |

---

### POST /verify/source

Check credibility of a source or domain.

#### Request Schema

```json
{
  "url": "https://www.reuters.com"
}
```

#### Response Schema

```json
{
  "domain": "reuters.com",
  "credibility_score": 92,
  "category": "news",
  "bias_rating": "center",
  "factual_reporting": "very_high",
  "notes": "Major international news agency with strong editorial standards.",
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Category Values

`news`, `academic`, `government`, `commercial`, `personal`, `satire`, `unknown`

#### Bias Rating Values

`far_left`, `left`, `center_left`, `center`, `center_right`, `right`, `far_right`, `unknown`

#### Factual Reporting Values

`very_high`, `high`, `mostly_factual`, `mixed`, `low`, `very_low`, `unknown`

---

## Monitor API

Real-time topic monitoring with webhook alerts (UnSearch exclusive).

### POST /monitor/topics

Create a new topic monitor.

#### Use Cases

- **News Monitoring**: Track breaking news on topics
- **Brand Monitoring**: Watch for brand mentions
- **Competitor Tracking**: Monitor competitor activity
- **Research Updates**: Get alerts on new publications

#### Request Schema

```json
{
  "topic": "AI regulations",
  "keywords": ["GDPR", "AI Act", "OpenAI"],
  "sources": ["techcrunch.com", "wired.com"],
  "check_interval_minutes": 60,
  "webhook_url": "https://your-app.com/webhooks/monitor",
  "deep_analysis": true
}
```

#### Request Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `topic` | string | Yes | - | Topic to monitor |
| `keywords` | string[] | No | [] | Additional keywords |
| `sources` | string[] | No | null | Specific domains to monitor |
| `check_interval_minutes` | integer | No | 60 | Check interval (5-1440) |
| `webhook_url` | string | No | null | Webhook for alerts |
| `deep_analysis` | boolean | No | false | Include AI analysis |

#### Response Schema

```json
{
  "id": "mon_abc123",
  "topic": "AI regulations",
  "keywords": ["GDPR", "AI Act", "OpenAI"],
  "sources": ["techcrunch.com", "wired.com"],
  "check_interval_minutes": 60,
  "webhook_url": "https://your-app.com/webhooks/monitor",
  "deep_analysis": true,
  "status": "active",
  "last_checked": null,
  "alerts_sent": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET /monitor/topics

List all monitors.

### GET /monitor/topics/{monitor_id}

Get a specific monitor.

### POST /monitor/topics/{monitor_id}/pause

Pause a monitor.

### POST /monitor/topics/{monitor_id}/resume

Resume a paused monitor.

### DELETE /monitor/topics/{monitor_id}

Delete a monitor.

### GET /monitor/topics/{monitor_id}/results

Get recent results from a monitor.

---

## Error Handling

All errors follow a consistent format.

### Error Response Schema

```json
{
  "error": "ValidationError",
  "message": "Invalid search query",
  "details": {
    "field": "query",
    "reason": "Query exceeds maximum length of 500 characters"
  },
  "request_id": "req_xyz789",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing API key |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Request validation failed |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Error - Server error |

### Error Handling Example

```python
import httpx

async def safe_search(query: str):
    try:
        response = await client.post(
            "https://api.unsearch.dev/api/v1/search",
            json={"query": query}
        )
        response.raise_for_status()
        return response.json()
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise AuthError("Invalid API key")
        elif e.response.status_code == 429:
            retry_after = e.response.headers.get("Retry-After", 60)
            raise RateLimitError(f"Rate limited. Retry after {retry_after}s")
        elif e.response.status_code == 422:
            detail = e.response.json()
            raise ValidationError(detail["message"])
        else:
            raise APIError(f"API error: {e.response.status_code}")
```

---

## Rate Limits

Rate limits vary by plan.

### Limits by Plan

| Plan | Queries/Month | Rate Limit | Burst |
|------|---------------|------------|-------|
| Free | 5,000 | 10/min | 20 |
| Pro | 25,000 | 60/min | 100 |
| Growth | 100,000 | 200/min | 300 |
| Scale | 500,000 | 1,000/min | 1,500 |

### Rate Limit Headers

Response headers include rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705312200
```

### Handling Rate Limits

```python
async def search_with_retry(query: str, max_retries: int = 3):
    for attempt in range(max_retries):
        response = await client.post("/api/v1/search", json={"query": query})
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            await asyncio.sleep(retry_after)
            continue
        
        response.raise_for_status()
        return response.json()
    
    raise RateLimitError("Max retries exceeded")
```

---

## Privacy & Zero-Retention

Enable zero-retention mode to prevent query/result storage:

```bash
curl -X POST "https://api.unsearch.dev/api/v1/search" \
  -H "X-API-Key: uns_your_api_key" \
  -H "X-Zero-Retention: true" \
  -H "Content-Type: application/json" \
  -d '{"query": "sensitive search query"}'
```

When enabled:
- Queries are not logged
- Results are not cached
- No data retained after response

---

## SDK Examples

### Python

```python
from unsearch import UnSearchClient

client = UnSearchClient(api_key="uns_your_api_key")

# Search
results = client.search("machine learning", max_results=10)

# Agent search with answer
response = client.agent_search(
    query="What is RAG?",
    include_answer=True
)
print(response.answer)

# Deep research
research = client.research(
    topic="AI in healthcare",
    depth="deep"
)
print(research.executive_summary)
```

### JavaScript/TypeScript

```typescript
import { UnSearchClient } from 'unsearch';

const client = new UnSearchClient({ apiKey: 'uns_your_api_key' });

// Search
const results = await client.search({
  query: 'machine learning',
  maxResults: 10
});

// Agent search with answer
const response = await client.agentSearch({
  query: 'What is RAG?',
  includeAnswer: true
});
console.log(response.answer);

// Deep research
const research = await client.research({
  topic: 'AI in healthcare',
  depth: 'deep'
});
console.log(research.executiveSummary);
```

---

*For more examples, see [API_EXAMPLES.md](./API_EXAMPLES.md)*

*For migration from Tavily, see [Migration Guide](./migration/from-tavily.md)*
