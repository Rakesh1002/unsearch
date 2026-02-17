# UnSearch AI Pipeline Documentation

## Overview

UnSearch integrates Cloudflare Workers AI to provide enterprise-grade AI capabilities at the edge. This document covers all AI features, models, configuration, and usage.

## Table of Contents

1. [Architecture](#architecture)
2. [Available Models](#available-models)
3. [Configuration](#configuration)
4. [API Endpoints](#api-endpoints)
5. [Model Selection](#model-selection)
6. [Features](#features)
7. [Usage Examples](#usage-examples)
8. [Best Practices](#best-practices)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UnSearch AI Pipeline                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │  Query   │───▶│  Search  │───▶│  Scrape  │───▶│ Rerank   │───▶│Generate││
│  │ Analysis │    │ SearXNG  │    │ Content  │    │ BGE      │    │ Answer ││
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └────────┘│
│       │                                               │              │      │
│       │              Cloudflare Workers AI            │              │      │
│       ▼                                               ▼              ▼      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  bge-m3        │  bge-reranker  │  gpt-oss-120b / qwq-32b / llama   │  │
│  │  (embeddings)  │  (reranking)   │  (answer generation)              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│                          ┌──────────────┐                                   │
│                          │ Llama Guard  │ (Content Safety)                  │
│                          └──────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Purpose | Model |
|-----------|---------|-------|
| Query Analysis | Detect complexity & intent | Rule-based |
| Search | Multi-engine web search | SearXNG (70+ engines) |
| Scraping | Content extraction | BeautifulSoup/Playwright |
| Reranking | Relevance scoring | `bge-reranker-base` |
| Answer Generation | LLM response | `gpt-oss-120b`, `qwq-32b`, `llama-3.3-70b` |
| Embeddings | Vector generation | `bge-m3` (multilingual) |
| Safety | Content moderation | `llama-guard-3-8b` |

---

## Available Models

### Text Generation (LLMs)

#### Production Tier
| Model | ID | Best For | Response Time |
|-------|-----|----------|---------------|
| **gpt-oss-120b** | `@cf/openai/gpt-oss-120b` | Enterprise, maximum quality | ~5-6s |
| gpt-oss-20b | `@cf/openai/gpt-oss-20b` | Production, faster | ~3-4s |

**Features:**
- OpenAI open-weight model
- 128K context window
- Built-in reasoning with chain-of-thought
- Structured outputs with citations
- Pricing: $0.35/M input, $0.75/M output tokens

#### Quality Tier
| Model | ID | Best For | Response Time |
|-------|-----|----------|---------------|
| **llama-3.3-70b-fp8-fast** | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | Quality/speed balance | ~3-4s |
| llama-4-scout | `@cf/meta/llama-4-scout-17b-16e-instruct` | Multimodal, function calling | ~4-5s |
| gemma-3-12b | `@cf/google/gemma-3-12b-it` | 128K context, multimodal | ~3-4s |

#### Reasoning Tier
| Model | ID | Best For | Response Time |
|-------|-----|----------|---------------|
| **qwq-32b** | `@cf/qwen/qwq-32b` | Complex analysis, competitive with o1-mini | ~30-35s |
| deepseek-r1 | `@cf/deepseek/deepseek-r1-distill-qwen-32b` | State-of-the-art reasoning | ~30-35s |

**Features:**
- Chain-of-thought reasoning visible in output
- Best for analytical and comparative queries
- Shows reasoning process before final answer

#### Speed Tier
| Model | ID | Best For | Response Time |
|-------|-----|----------|---------------|
| **llama-3.1-8b-fast** | `@cf/meta/llama-3.1-8b-instruct-fast` | Simple queries, low latency | ~2-3s |
| llama-3.2-3b | `@cf/meta/llama-3.2-3b-instruct` | Ultra-fast, edge | ~1-2s |
| llama-3.2-1b | `@cf/meta/llama-3.2-1b-instruct` | Minimum latency | ~1s |

### Embeddings

| Model | ID | Dimensions | Languages | Best For |
|-------|-----|------------|-----------|----------|
| **bge-m3** | `@cf/baai/bge-m3` | 1024 | 100+ | Enterprise, multilingual |
| embeddinggemma | `@cf/google/embeddinggemma-300m` | 768 | 100+ | Google's latest |
| bge-large | `@cf/baai/bge-large-en-v1.5` | 1024 | English | High quality English |
| bge-base | `@cf/baai/bge-base-en-v1.5` | 768 | English | Balanced |
| bge-small | `@cf/baai/bge-small-en-v1.5` | 384 | English | Fast |

### Reranking

| Model | ID | Purpose |
|-------|-----|---------|
| **bge-reranker-base** | `@cf/baai/bge-reranker-base` | Search result reranking |

### Content Safety

| Model | ID | Purpose |
|-------|-----|---------|
| **llama-guard-3-8b** | `@cf/meta/llama-guard-3-8b` | Prompt/response safety classification |

---

## Configuration

### Environment Variables

```bash
# ====================
# Cloudflare Workers AI
# ====================
# Required - Get from https://dash.cloudflare.com/
CLOUDFLARE_ACCOUNT_ID="your-account-id"
CLOUDFLARE_API_TOKEN="your-api-token"
CLOUDFLARE_AI_ENABLED="true"

# Model Selection (optional - defaults shown)
CLOUDFLARE_EMBEDDING_MODEL="@cf/baai/bge-m3"
CLOUDFLARE_LLM_MODEL="@cf/meta/llama-3.3-70b-instruct-fp8-fast"
CLOUDFLARE_REASONING_MODEL="@cf/qwen/qwq-32b"
CLOUDFLARE_RERANKER_MODEL="@cf/baai/bge-reranker-base"
CLOUDFLARE_SAFETY_MODEL="@cf/meta/llama-guard-3-8b"
```

### Getting Cloudflare Credentials

1. **Account ID**: 
   - Go to https://dash.cloudflare.com/
   - Navigate to Workers & Pages > Overview
   - Find Account ID in the right sidebar

2. **API Token**:
   - Go to https://dash.cloudflare.com/profile/api-tokens
   - Create token with "Workers AI" template
   - Or custom token with "Workers AI - Run" permission

---

## API Endpoints

### Agent Search (Tavily-compatible)

```http
POST /api/v1/agent/search
```

**Request:**
```json
{
  "query": "What are the benefits of open-source AI?",
  "max_results": 5,
  "include_answer": true,
  "model": "auto",
  "rerank": true,
  "check_safety": false,
  "search_depth": "basic",
  "topic": "general",
  "include_domains": null,
  "exclude_domains": null
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query |
| `max_results` | int | 5 | Number of results (1-20) |
| `include_answer` | bool/string | false | Generate answer. Options: `true`, `"basic"`, `"advanced"`, `"production"` |
| `model` | string | "auto" | Model selection: `"auto"`, `"speed"`, `"quality"`, `"reasoning"`, `"production"` |
| `rerank` | bool | false | Use AI reranking |
| `check_safety` | bool | false | Run content safety checks |
| `search_depth` | string | "basic" | `"basic"`, `"advanced"`, `"fast"`, `"ultra-fast"` |
| `topic` | string | "general" | `"general"`, `"news"`, `"finance"` |

**Response:**
```json
{
  "query": "What are the benefits of open-source AI?",
  "answer": "Open-source AI models offer several key advantages...",
  "results": [
    {
      "title": "Benefits of Open Source AI",
      "url": "https://example.com/article",
      "content": "Snippet of content...",
      "score": 0.95
    }
  ],
  "images": [],
  "response_time": 3.57,
  "model_used": "@cf/openai/gpt-oss-120b",
  "query_complexity": "moderate",
  "safety_check": {
    "safe": true,
    "checked": true
  }
}
```

### Deep Research (UnSearch Exclusive)

```http
POST /api/v1/agent/research
```

**Request:**
```json
{
  "query": "Impact of AI on enterprise software development",
  "depth": "deep",
  "max_sources": 15,
  "include_analysis": true,
  "include_summary": true,
  "focus_areas": ["productivity", "code quality"]
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Research topic |
| `depth` | string | "standard" | `"quick"`, `"standard"`, `"deep"`, `"comprehensive"` |
| `max_sources` | int | 10 | Sources to analyze (3-30) |
| `include_analysis` | bool | true | Include detailed analysis |
| `include_summary` | bool | true | Include executive summary |
| `focus_areas` | array | null | Specific areas to focus on |

**Depth Levels:**

| Depth | Sources | Model | Use Case |
|-------|---------|-------|----------|
| quick | 3-5 | llama-3.1-8b-fast | Fast overview |
| standard | 5-10 | llama-3.3-70b-fast | Balanced research |
| deep | 10-20 | qwq-32b | Thorough analysis |
| comprehensive | 20-30 | gpt-oss-120b | Expert-level |

**Response:**
```json
{
  "query": "Impact of AI on enterprise software development",
  "executive_summary": "The research indicates...",
  "detailed_analysis": "A comprehensive analysis shows...",
  "key_findings": [
    "15%+ velocity gains in development",
    "Improved code quality metrics"
  ],
  "sources": [...],
  "methodology": {
    "depth": "deep",
    "sources_analyzed": 15,
    "content_scraped": true
  },
  "model_used": "@cf/qwen/qwq-32b",
  "response_time": 45.2
}
```

### Content Extraction

```http
POST /api/v1/agent/extract
```

**Request:**
```json
{
  "urls": ["https://example.com/article"],
  "include_images": false,
  "extract_depth": "basic"
}
```

### List Available Models

```http
GET /api/v1/agent/models
```

**Response:**
```json
{
  "configured": true,
  "models": {
    "embeddings": {...},
    "text_generation": {...},
    "reranking": {...},
    "safety": {...}
  },
  "default_selection": {
    "embeddings": "@cf/baai/bge-m3",
    "text_generation": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "reasoning": "@cf/qwen/qwq-32b",
    "production": "@cf/openai/gpt-oss-120b"
  }
}
```

### Health Check

```http
GET /api/v1/agent/health
```

---

## Model Selection

### Automatic Selection

When `model: "auto"`, the pipeline analyzes query complexity:

```
Query Analysis
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Simple?           → llama-3.1-8b-fast (speed)         │
│  "What is X?"                                           │
│  "Define Y"                                             │
├─────────────────────────────────────────────────────────┤
│  Moderate?         → llama-3.3-70b-fast (quality)      │
│  Multi-faceted                                          │
│  Informational                                          │
├─────────────────────────────────────────────────────────┤
│  Complex?          → qwq-32b (reasoning)               │
│  "Why does X..."                                        │
│  "Compare X and Y"                                      │
│  "What are the implications..."                         │
├─────────────────────────────────────────────────────────┤
│  Expert?           → gpt-oss-120b (production)         │
│  Deep analysis                                          │
│  Synthesis required                                     │
└─────────────────────────────────────────────────────────┘
```

### Complexity Detection Keywords

**Simple (Speed Tier):**
- "what is", "who is", "when was", "where is"
- "define", "meaning of", "definition of"

**Complex (Reasoning Tier):**
- "why", "how", "explain", "compare", "analyze"
- "what causes", "implications", "pros and cons"
- "difference between", "relationship between"
- "best way to", "should i", "trade-offs"

### Manual Selection

```json
// Force specific tier
{"model": "speed"}      // llama-3.1-8b-fast
{"model": "quality"}    // llama-3.3-70b-fast  
{"model": "reasoning"}  // qwq-32b
{"model": "production"} // gpt-oss-120b

// Or use include_answer for production
{"include_answer": "production"}
```

---

## Features

### 1. AI Reranking

Improves search result relevance using BGE reranker.

```json
{
  "query": "machine learning tutorials",
  "rerank": true
}
```

**How it works:**
1. Initial search returns results ranked by search engine
2. BGE reranker scores each result against query
3. Results reordered by relevance score
4. Top results returned with scores

### 2. Content Safety

Enterprise-grade content moderation using Llama Guard.

```json
{
  "query": "...",
  "check_safety": true
}
```

**Response includes:**
```json
{
  "safety_check": {
    "query_safe": true,
    "query_categories": [],
    "answer_safe": true,
    "answer_categories": [],
    "safe": true,
    "checked": true
  }
}
```

### 3. Chain-of-Thought Reasoning

Reasoning models (qwq-32b, deepseek-r1) show their thinking process:

```
Answer: "Okay, I need to analyze why transformer models 
outperform RNNs. Let me break this down...

First, transformers use self-attention which allows...
Second, the parallel processing capability means...

Therefore, the key reasons are:
1. Self-attention mechanisms
2. Parallel processing
3. Better long-range dependencies"
```

### 4. Multilingual Embeddings

BGE-M3 supports 100+ languages for:
- Semantic search across languages
- Cross-lingual document matching
- International enterprise use cases

### 5. Zero-Retention Mode

Privacy-first option for sensitive queries:

```bash
curl -X POST /api/v1/agent/search \
  -H "X-Zero-Retention: true" \
  -d '{"query": "..."}'
```

---

## Usage Examples

### Python SDK

```python
from unsearch import UnSearchClient

client = UnSearchClient(api_key="your-key")

# Simple search with auto model selection
result = client.search("What is quantum computing?")
print(result.answer)

# Production-quality search
result = client.search(
    "Enterprise AI deployment best practices",
    include_answer=True,
    model="production",
    rerank=True
)

# Deep research
research = client.research(
    "Impact of AI on healthcare",
    depth="deep",
    focus_areas=["diagnostics", "drug discovery"]
)
print(research.executive_summary)
print(research.key_findings)
```

### cURL Examples

```bash
# Auto model selection
curl -X POST http://localhost:8000/api/v1/agent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "include_answer": true,
    "model": "auto"
  }'

# Production model with safety checks
curl -X POST http://localhost:8000/api/v1/agent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI ethics considerations",
    "include_answer": "production",
    "model": "production",
    "rerank": true,
    "check_safety": true
  }'

# Deep research
curl -X POST http://localhost:8000/api/v1/agent/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Future of renewable energy",
    "depth": "comprehensive",
    "max_sources": 20
  }'
```

### LangChain Integration

```python
from unsearch.langchain import UnSearchResults

# As a LangChain tool
search_tool = UnSearchResults(
    api_key="your-key",
    max_results=5,
    include_answer=True
)

# Use in agent
from langchain.agents import initialize_agent
agent = initialize_agent(
    tools=[search_tool],
    llm=your_llm,
    agent="zero-shot-react-description"
)
```

---

## Best Practices

### 1. Model Selection

| Use Case | Recommended Model | Why |
|----------|-------------------|-----|
| FAQ/definitions | `speed` | Fast, cost-effective |
| General queries | `auto` | Intelligent selection |
| Technical docs | `quality` | Good accuracy |
| Analysis/reports | `reasoning` | Deep thinking |
| Enterprise/legal | `production` | Maximum quality |

### 2. Cost Optimization

```python
# Use auto selection to optimize costs
result = client.search(query, model="auto")

# Query complexity determines model:
# - Simple → 8B model (cheapest)
# - Complex → 32B+ model (when needed)
```

### 3. Latency vs Quality

| Priority | Configuration |
|----------|---------------|
| Speed | `model: "speed"`, `rerank: false` |
| Balanced | `model: "auto"`, `rerank: true` |
| Quality | `model: "production"`, `rerank: true`, `check_safety: true` |

### 4. Enterprise Deployment

```json
{
  "model": "production",
  "rerank": true,
  "check_safety": true,
  "include_answer": "production"
}
```

### 5. Handling Sensitive Data

```bash
# Use zero-retention header
curl -X POST /api/v1/agent/search \
  -H "X-Zero-Retention: true" \
  -H "Content-Type: application/json" \
  -d '{"query": "confidential topic", "check_safety": true}'
```

---

## Comparison with Competitors

| Feature | UnSearch | Tavily | Exa |
|---------|----------|--------|-----|
| OpenAI gpt-oss-120b | ✅ | ❌ | ❌ |
| Reasoning models (qwq-32b) | ✅ | ❌ | ❌ |
| Auto model selection | ✅ | ❌ | ❌ |
| Deep research endpoint | ✅ | ❌ | ❌ |
| Content safety | ✅ | ❌ | ❌ |
| Self-hostable | ✅ | ❌ | ❌ |
| Model choice | ✅ Full | ❌ Fixed | ❌ Fixed |
| Multilingual embeddings | ✅ 100+ | Limited | Limited |

---

## Troubleshooting

### Common Issues

**1. Empty responses from gpt-oss-120b**
- Ensure using correct API format (Responses API)
- Check `CLOUDFLARE_API_TOKEN` has Workers AI permissions

**2. Slow response times**
- Reasoning models (qwq-32b) take 30-35s by design
- Use `model: "speed"` for faster responses

**3. Safety check failures**
- Review query for policy violations
- Check `safety_check.categories` for specific issues

**4. Cloudflare AI not configured**
- Verify `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`
- Check `/api/v1/agent/health` endpoint

### Debug Mode

```bash
# Check configuration
curl http://localhost:8000/api/v1/agent/health

# List available models
curl http://localhost:8000/api/v1/agent/models

# Check server logs for errors
tail -f /tmp/server.log
```

---

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Initial AI pipeline with Cloudflare Workers AI |
| 1.1.0 | Added gpt-oss-120b support with Responses API |
| 1.2.0 | Added content safety checks, research endpoint |

---

## Support

- Documentation: `/docs/ai-pipeline.md`
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/agent/health`
