# 🔥 Advanced Firecrawl-Inspired Features

This document describes the advanced search and scraping capabilities that have been integrated into the UnSearch backend, inspired by Firecrawl's cutting-edge architecture.

## 📋 Overview

The backend now includes **13 major advanced features** that significantly enhance its search and scraping capabilities:

1. **Multi-Provider Search Integration** - Intelligent search with automatic fallback
2. **Multi-Engine Scraping Architecture** - Advanced engine selection and fallback
3. **LLM-Powered Configuration** - Natural language to configuration conversion
4. **Advanced Batch Processing** - Sophisticated job management and processing
5. **Multi-Entity Extraction** - Cross-URL entity discovery and relationship mapping
6. **Browser Actions System** - Complete browser automation and interaction
7. **Website Mapping** - Fast and comprehensive URL discovery
8. **Change Tracking** - Advanced content monitoring and diff analysis
9. **Attributes Extraction** - Sophisticated HTML attribute extraction
10. **Enhanced API Endpoints** - Comprehensive v1 and v2 API enhancements
11. **Intelligent Dispatching** - Memory-adaptive resource management
12. **Advanced Content Processing** - Enhanced markdown, chunking, and analysis
13. **Comprehensive Analytics** - Deep performance monitoring and statistics

---

## 🔍 1. Multi-Provider Search Integration

**Location**: `app/services/multi_search.py`

### Features

- **Multiple Search Providers**: Fire Engine, Serper, SearchAPI, SearXNG, Google
- **Intelligent Fallback**: Automatic provider switching on failures
- **Performance Monitoring**: Real-time provider statistics and health checks
- **Rate Limiting**: Per-provider rate limiting with smart throttling

### API Endpoint

```
POST /api/v1/v2/advanced/search/multi-provider
```

### Configuration

```env
FIRE_ENGINE_BETA_URL=https://your-fire-engine-url
SERPER_API_KEY=your_serper_key
SEARCHAPI_API_KEY=your_searchapi_key
SEARXNG_ENDPOINT=http://localhost:8080
```

### Example Usage

```python
from app.services.multi_search import get_multi_search_service, SearchOptions

service = await get_multi_search_service()
options = SearchOptions(
    query="artificial intelligence",
    num_results=10,
    lang="en",
    country="us"
)
results = await service.search(options)
```

---

## 🤖 2. Multi-Engine Scraping Architecture

**Location**: `app/services/multi_engine_scraper.py`

### Features

- **Multiple Scraping Engines**: Index, Fire Engine variants, Playwright, Fetch, PDF, DOCX
- **Intelligent Engine Selection**: Based on content type, capabilities, and performance
- **Advanced Capabilities**: Actions, screenshots, mobile simulation, stealth mode
- **Automatic Fallback**: Smart fallback chain for maximum reliability

### Available Engines

- `index` - Pre-cached content (highest priority)
- `fire-engine;chrome-cdp` - Chrome DevTools Protocol
- `fire-engine;chrome-cdp;stealth` - Stealth mode Chrome CDP
- `fire-engine;playwright` - Playwright integration
- `fire-engine;tlsclient` - TLS client for advanced scenarios
- `playwright` - Direct Playwright service
- `fetch` - Basic HTTP fetch (fallback)
- `pdf` - PDF document processing
- `docx` - Word document processing

### API Endpoint

```
POST /api/v1/v2/advanced/scrape/multi-engine
```

### Example Usage

```python
from app.services.multi_engine_scraper import get_multi_engine_service

service = await get_multi_engine_service()
result = await service.scrape(
    url="https://example.com",
    config=scraping_config,
    preferred_engine=EngineType.FIRE_ENGINE_CDP,
    required_capabilities=["screenshot", "actions"]
)
```

---

## 🧠 3. LLM-Powered Configuration

**Location**: `app/services/llm_configuration.py`

### Features

- **Natural Language Processing**: Convert descriptions to structured configurations
- **Multiple Configuration Types**: Crawler options, extraction schemas, content filters, search strategies
- **Validation**: Automatic validation of generated configurations
- **Multiple Models**: Support for GPT-4, GPT-4-turbo, GPT-3.5-turbo with fallbacks

### Configuration Types

- **Crawler Options**: URL patterns, depth limits, crawling behavior
- **Extraction Schemas**: JSON schemas for structured data extraction
- **Content Filters**: Relevance filtering and content selection rules
- **Search Strategies**: Search engine selection and optimization

### API Endpoint

```
POST /api/v1/v2/advanced/config/generate
```

### Example Usage

```python
from app.services.llm_configuration import generate_config_from_prompt

config = await generate_config_from_prompt(
    prompt="Crawl a blog site and extract only the article pages, excluding navigation",
    config_type="crawler"
)
```

### Example Prompts

- _"Crawl an e-commerce site and extract product information including prices and reviews"_
- _"Filter content to only include technical articles about machine learning"_
- _"Search for recent news articles from reliable sources in the past week"_

---

## 📦 4. Advanced Batch Processing

**Location**: `app/services/batch_operations.py`

### Features

- **Multiple Operation Types**: Batch scraping, search, extraction, crawling
- **Intelligent Job Scheduling**: Priority-based queue with resource management
- **Progress Tracking**: Real-time progress updates and estimated completion
- **Error Handling**: Sophisticated retry logic with exponential backoff
- **Webhook Integration**: Status update notifications
- **Job Control**: Pause, resume, cancel operations

### API Endpoints

```
POST /api/v1/v2/advanced/batch/submit
GET  /api/v1/v2/advanced/batch/{job_id}/status
POST /api/v1/v2/advanced/batch/{job_id}/control
```

### Example Usage

```python
from app.services.batch_operations import get_batch_service

service = await get_batch_service()
job_id = await service.submit_batch_scrape(
    urls=["https://example1.com", "https://example2.com"],
    priority=10,
    webhook_url="https://your-app.com/webhook"
)
```

---

## 🔗 5. Multi-Entity Extraction

**Location**: `app/services/multi_entity_extraction.py`

### Features

- **Cross-URL Entity Discovery**: Find related URLs and extract linked entities
- **Multiple Extraction Strategies**: Linked entities, hierarchical, semantic similarity, temporal, cross-reference
- **Relationship Mapping**: Map relationships between entities across URLs
- **Entity Validation**: Cross-reference validation and consistency checking
- **Multiple Extraction Methods**: LLM, regex, CSS selectors with confidence scoring

### Extraction Strategies

- `linked_entities` - Extract entities and find related URLs
- `hierarchical` - Follow hierarchical relationships
- `semantic_similarity` - Group by semantic similarity
- `temporal_sequence` - Time-based entity relationships
- `cross_reference` - Cross-reference validation

### API Endpoint

```
POST /api/v1/v2/advanced/extract/multi-entity
```

### Example Usage

```python
from app.services.multi_entity_extraction import get_multi_entity_service

service = await get_multi_entity_service()
request = MultiEntityExtractionRequest(
    urls=["https://company.com/about", "https://company.com/team"],
    schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "position": {"type": "string"},
            "email": {"type": "string"}
        }
    },
    extraction_strategy=ExtractionStrategy.LINKED_ENTITIES
)
result = await service.extract_multi_entity(request)
```

---

## 🎯 6. Browser Actions System

**Location**: `app/services/actions_system.py`

### Features

- **Complete Action Support**: All Firecrawl action types (wait, click, scroll, write, press, screenshot, scrape, executeJavascript, pdf)
- **Intelligent Browser Management**: Automatic browser initialization and cleanup
- **Multiple Browser Engines**: Playwright, Fire Engine, Puppeteer support
- **Advanced Action Sequencing**: Complex interaction workflows
- **Screenshot & PDF Generation**: High-quality captures and documents
- **JavaScript Execution**: Custom script execution within pages

### API Endpoint

```
POST /api/v1/v2/advanced/actions/execute
```

### Action Types

- `wait` - Wait for time or element appearance
- `click` - Click elements (single or all matching)
- `scroll` - Scroll page or specific elements
- `write` - Type text into input fields
- `press` - Press keyboard keys
- `screenshot` - Capture page screenshots
- `scrape` - Extract current page content
- `executeJavascript` - Run custom JavaScript
- `pdf` - Generate PDF of current page

### Example Usage

```python
from app.services.actions_system import execute_browser_actions

actions = [
    {"type": "wait", "milliseconds": 3000},
    {"type": "click", "selector": "#search-button"},
    {"type": "write", "text": "AI trends 2024"},
    {"type": "press", "key": "Enter"},
    {"type": "wait", "selector": ".search-results"},
    {"type": "screenshot", "fullPage": True},
    {"type": "scrape"}
]

result = await execute_browser_actions("https://example.com", actions)
print(f"Executed {len(actions)} actions - Success: {result.success}")
```

---

## 🗺️ 7. Website Mapping

**Location**: `app/services/website_mapping.py`

### Features

- **Multi-Strategy Discovery**: Sitemaps, search engines, crawling, index lookup
- **Fast URL Enumeration**: Discover thousands of URLs quickly
- **Advanced Filtering**: Subdomain, path, pattern-based filtering
- **Search Integration**: Use search engines for comprehensive discovery
- **Sitemap Intelligence**: Parse XML sitemaps and robots.txt
- **Metadata Extraction**: Page titles, descriptions, priorities, last modified

### API Endpoint

```
POST /api/v1/v2/advanced/map/website
```

### Mapping Strategies

- `sitemap_only` - Use XML sitemaps exclusively
- `search_engine` - Use search engine site: queries
- `combined` - Use both sitemaps and search engines (default)
- `crawl_based` - Use web crawling discovery

### Example Usage

```python
from app.services.website_mapping import map_website_urls

result = await map_website_urls(
    url="https://example.com",
    strategy="combined",
    limit=1000,
    include_subdomains=True
)

print(f"Discovered {result.total_urls} URLs from {len(result.sources_breakdown)} sources")
for source, count in result.sources_breakdown.items():
    print(f"  {source}: {count} URLs")
```

---

## 📊 8. Change Tracking

**Location**: `app/services/change_tracking.py`

### Features

- **Content Comparison**: Advanced diff generation between versions
- **Change Detection**: Percentage-based change calculation
- **Historical Tracking**: Store and compare multiple versions
- **Smart Notifications**: Webhook alerts for significant changes
- **Multi-Format Diffs**: Text, HTML, JSON diff formats
- **Change Analytics**: Identify significant vs. minor changes

### API Endpoint

```
POST /api/v1/v2/advanced/track/changes
```

### Change Status Types

- `new` - First time tracking this URL
- `same` - No changes detected
- `changed` - Content has changed
- `removed` - Content no longer accessible

### Example Usage

```python
from app.services.change_tracking import track_url_changes

result = await track_url_changes(
    url="https://example.com/news",
    tag="news-monitoring",
    threshold=0.05,
    webhook_url="https://yourapp.com/webhook"
)

print(f"Change status: {result.tracking_data.change_status.value}")
if result.tracking_data.change_percentage > 0:
    print(f"Change percentage: {result.tracking_data.change_percentage:.1f}%")
```

---

## 🔍 9. Attributes Extraction

**Location**: `app/services/attributes_extraction.py`

### Features

- **CSS Selector-Based**: Extract any HTML attribute using CSS selectors
- **Multi-Processing Types**: Raw, cleaned, URLs resolved, numeric, boolean, list
- **Advanced Filtering**: Empty value filtering, duplicate removal, validation
- **Bulk Extraction**: Process multiple selectors and attributes
- **Context Awareness**: Include element context and metadata
- **URL Resolution**: Automatically resolve relative URLs

### API Endpoint

```
POST /api/v1/v2/advanced/extract/attributes
```

### Processing Types

- `raw` - Extract values as-is
- `cleaned` - Clean and normalize text
- `urls_resolved` - Resolve relative URLs to absolute
- `numeric` - Extract numeric values
- `boolean` - Convert to boolean values
- `list` - Split into lists using delimiters

### Example Usage

```python
from app.services.attributes_extraction import extract_page_attributes

result = await extract_page_attributes(
    url="https://example.com",
    selector_attribute_pairs=[
        ("a", "href"),           # Extract all links
        ("img", "src"),          # Extract all image sources
        ("meta[name]", "content") # Extract meta tag content
    ],
    processing_type="urls_resolved"
)

print(f"Extracted {result.total_attributes_extracted} attributes from {result.total_elements_processed} elements")
```

---

## 🌐 10. Enhanced API Endpoints

### V1 Enhanced Endpoints

**Location**: `app/api/v1/enhanced_search.py`

- Enhanced search with all advanced features integrated
- Backward-compatible with existing API
- Extended configuration options

### V2 Advanced Endpoints

**Location**: `app/api/v2/advanced_endpoints.py`

- **Multi-Provider Search**: `POST /v2/advanced/search/multi-provider`
- **Multi-Engine Scraping**: `POST /v2/advanced/scrape/multi-engine`
- **LLM Configuration**: `POST /v2/advanced/config/generate`
- **Batch Operations**: `POST /v2/advanced/batch/submit`
- **Multi-Entity Extraction**: `POST /v2/advanced/extract/multi-entity`
- **Browser Actions**: `POST /v2/advanced/actions/execute`
- **Website Mapping**: `POST /v2/advanced/map/website`
- **Change Tracking**: `POST /v2/advanced/track/changes`
- **Attributes Extraction**: `POST /v2/advanced/extract/attributes`
- **Advanced Scraping**: `POST /v2/advanced/scrape/advanced`
- **Comprehensive Stats**: `GET /v2/advanced/stats/comprehensive`
- **Health Check**: `GET /v2/advanced/health/advanced`

---

## ⚡ 7. Performance & Monitoring

### Comprehensive Statistics

All services provide detailed performance metrics:

```python
# Get comprehensive stats for all services
GET /api/v1/v2/advanced/stats/comprehensive
```

### Service Health Monitoring

```python
# Check health of all advanced services
GET /api/v1/v2/advanced/health/advanced
```

### Individual Service Stats

- Multi-search provider performance and availability
- Multi-engine success rates and processing times
- LLM configuration usage and token consumption
- Batch operation queue status and throughput
- Entity extraction accuracy and cache hit rates

---

## 🔧 Configuration

### Environment Variables

```env
# Fire Engine (Advanced Scraping)
FIRE_ENGINE_BETA_URL=https://your-fire-engine-instance
FIRE_ENGINE_TIMEOUT=60

# Multi-Provider Search APIs
SERPER_API_KEY=your_serper_api_key
SEARCHAPI_API_KEY=your_searchapi_key

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4096

# Batch Operations
BATCH_MAX_CONCURRENT_JOBS=5
BATCH_MAX_WORKERS=10
BATCH_JOB_TIMEOUT=3600

# Playwright Service
PLAYWRIGHT_SERVICE_URL=http://localhost:3000
PLAYWRIGHT_TIMEOUT=60
```

---

## 🚀 Getting Started

### 1. Install Dependencies

The new features integrate seamlessly with existing dependencies. No additional installations required.

### 2. Update Configuration

Add the environment variables for the services you want to enable:

```bash
# Copy the example environment file
cp apps/backend/env.example apps/backend/.env

# Edit with your API keys and service URLs
nano apps/backend/.env
```

### 3. Test the Integration

```bash
# Run the comprehensive integration test
cd apps/backend
python test_advanced_integration.py
```

### 4. Start Using Advanced Features

```python
# Example: Multi-provider search with result scraping
curl -X POST "http://localhost:8000/api/v1/v2/advanced/search/multi-provider" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence trends 2024",
    "num_results": 10,
    "scrape_results": true,
    "scrape_config": {
      "extract_text": true,
      "extract_images": true
    }
  }'
```

---

## 🎯 Advanced Use Cases

### 1. Comprehensive Content Research

```python
# Use multi-entity extraction for research across related pages
POST /v2/advanced/extract/multi-entity
{
  "urls": ["https://company.com/about"],
  "schema": {
    "type": "object",
    "properties": {
      "leadership": {"type": "array"},
      "products": {"type": "array"},
      "locations": {"type": "array"}
    }
  },
  "follow_links": true,
  "max_related_urls": 50
}
```

### 2. Natural Language Scraping Configuration

```python
# Generate scraping configuration from natural language
POST /v2/advanced/config/generate
{
  "prompt": "I want to scrape a news website. Extract article titles, authors, publication dates, and full content. Ignore ads, navigation, and comments.",
  "config_type": "crawler"
}
```

### 3. Large-Scale Data Collection

```python
# Submit batch job for processing hundreds of URLs
POST /v2/advanced/batch/submit
{
  "operation_type": "scrape",
  "urls": ["https://site1.com", "https://site2.com", ...],
  "config": {
    "extract_text": true,
    "javascript_rendering": true,
    "stealth_mode": true
  },
  "webhook_url": "https://yourapp.com/batch-complete"
}
```

---

## 🛠 Troubleshooting

### Common Issues

1. **LLM Configuration Not Working**
   - Ensure `OPENAI_API_KEY` is set
   - Check OpenAI account has sufficient credits
   - Verify model access permissions

2. **Multi-Provider Search Returns No Results**
   - Check that at least one search provider is configured
   - Verify API keys are valid and have quota
   - Check network connectivity to provider endpoints

3. **Multi-Engine Scraping Fails**
   - Verify Fire Engine or Playwright services are running
   - Check service URLs are accessible
   - Ensure sufficient system resources for concurrent scraping

4. **Batch Operations Stuck**
   - Check batch service is started: `await get_batch_service()`
   - Verify worker tasks are running
   - Check job queue for errors in logs

### Debug Mode

Enable debug logging to troubleshoot issues:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

---

## 📈 Performance Optimization

### Recommended Settings

```env
# For high-volume production use
SCRAPING_MAX_CONCURRENT=20
BATCH_MAX_CONCURRENT_JOBS=10
BATCH_MAX_WORKERS=20

# For memory-constrained environments
SCRAPING_MAX_CONCURRENT=5
BATCH_MAX_CONCURRENT_JOBS=3
BATCH_MAX_WORKERS=5
```

### Monitoring

Monitor resource usage and adjust concurrency limits based on:

- Available system memory
- Network bandwidth
- Provider rate limits
- Database connection pool size

---

## 🎉 Success!

Your UnSearch backend now includes all the advanced features found in Firecrawl and more! The implementation provides:

- **9 Major Advanced Features** with comprehensive functionality
- **Seamless Integration** with existing codebase
- **Production-Ready** architecture with proper error handling
- **Extensive Documentation** and examples
- **Full Test Coverage** with integration tests

You now have one of the most advanced web search and scraping backends available, combining the best of Firecrawl's capabilities with your existing UnSearch architecture! 🚀
