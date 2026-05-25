"""
API request models using Pydantic v2.
"""
from typing import Dict, List, Literal, Optional, Union, Any
from pydantic import BaseModel, Field, HttpUrl, validator
import re


class UnSearchRequest(BaseModel):
    """Main search and scrape request model."""
    
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=500, 
        description="Search query",
        examples=["Python web scraping tutorial"]
    )
    
    engines: List[str] = Field(
        default=["google", "bing", "duckduckgo"], 
        description="Search engines to use",
        min_items=1,
        max_items=10
    )
    
    max_results: int = Field(
        default=10, 
        ge=1, 
        le=100, 
        description="Maximum results to return"
    )
    
    scrape_content: bool = Field(
        default=True, 
        description="Whether to scrape page content"
    )
    
    scrape_selectors: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Custom CSS selectors for content extraction",
        examples=[{"title": "h1", "content": "article", "author": ".author-name"}]
    )
    
    output_format: Literal["json", "markdown"] = Field(
        default="json",
        description="Response format (json or markdown)"
    )
    
    cache_ttl: int = Field(
        default=3600, 
        ge=0, 
        le=86400, 
        description="Cache TTL in seconds (0 to disable caching)"
    )
    
    language: str = Field(
        default="en", 
        pattern="^[a-z]{2}$", 
        description="Language code (ISO 639-1)"
    )
    
    safe_search: Literal["strict", "moderate", "off"] = Field(
        default="moderate", 
        description="Safe search level"
    )
    
    include_images: bool = Field(
        default=True, 
        description="Extract images from scraped content"
    )
    
    include_links: bool = Field(
        default=True, 
        description="Extract links from scraped content"
    )
    
    timeout: int = Field(
        default=30, 
        ge=5, 
        le=120, 
        description="Request timeout in seconds"
    )
    
    async_mode: bool = Field(
        default=False,
        description="Process request asynchronously"
    )

    # Advanced crawling options
    js_mode: bool = Field(
        default=False,
        description="Use headless browser (Puppeteer) for JavaScript rendering"
    )
    screenshot: bool = Field(
        default=False,
        description="Capture screenshot when js_mode is enabled"
    )
    pdf: bool = Field(
        default=False,
        description="Capture PDF when js_mode is enabled"
    )
    
    webhook_url: Optional[HttpUrl] = Field(
        default=None,
        description="Webhook URL for async results"
    )
    
    # Relevance filtering options
    relevance_filter: bool = Field(
        default=True,
        description="Enable relevance filtering to improve result quality"
    )
    
    min_relevance_score: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold (0-1). Lower values return more results."
    )
    
    @validator("query")
    def sanitize_query(cls, v):
        """Sanitize search query to prevent injection."""
        # Remove any potential script tags or SQL injection attempts
        v = re.sub(r'<[^>]*>', '', v)
        v = re.sub(r'[;\'"\\]', '', v)
        return v.strip()
    
    @validator("engines")
    def validate_engines(cls, v):
        """Validate search engines."""
        allowed_engines = {
            "google", "bing", "duckduckgo", "startpage", 
            "qwant", "yahoo", "searx", "brave", "ecosia"
        }
        invalid = set(v) - allowed_engines
        if invalid:
            raise ValueError(f"Invalid engines: {invalid}")
        return list(set(v))  # Remove duplicates
    
    @validator("webhook_url")
    def validate_webhook_url(cls, v, values):
        """Validate webhook URL is required for async mode."""
        if values.get("async_mode") and not v:
            raise ValueError("webhook_url is required when async_mode is True")
        return v


class BatchSearchRequest(BaseModel):
    """Batch search request for multiple queries."""
    
    queries: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=100,
        description="List of search queries"
    )
    
    engines: List[str] = Field(
        default=["google", "bing"], 
        description="Search engines to use for all queries"
    )
    
    max_results_per_query: int = Field(
        default=5, 
        ge=1, 
        le=20,
        description="Maximum results per query"
    )
    
    scrape_content: bool = Field(
        default=False,
        description="Whether to scrape content (disabled by default for batch)"
    )
    
    parallel_requests: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of parallel requests"
    )


class ScrapingConfig(BaseModel):
    """Configuration for content scraping."""
    
    urls: List[HttpUrl] = Field(
        ..., 
        min_items=1, 
        max_items=50,
        description="URLs to scrape"
    )
    
    selectors: Optional[Dict[str, str]] = Field(
        default=None,
        description="CSS selectors for extraction"
    )
    
    extract_text: bool = Field(default=True)
    extract_images: bool = Field(default=True)
    extract_links: bool = Field(default=True)
    extract_metadata: bool = Field(default=True)
    
    javascript_rendering: bool = Field(
        default=False,
        description="Enable JavaScript rendering (slower)"
    )
    js_mode: bool = Field(
        default=False,
        description="Alias for javascript_rendering"
    )
    
    wait_time: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Wait time in seconds after page load"
    )
    
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom HTTP headers"
    )
    
    cookies: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom cookies"
    )

    # Output formatting
    response_format: Literal["json", "markdown"] = Field(
        default="json",
        description="Return JSON or Markdown content"
    )

    # Browser / identity / media options (used in js_mode)
    screenshot: bool = Field(default=False, description="Capture screenshot in js_mode")
    pdf: bool = Field(default=False, description="Capture PDF in js_mode")
    include_html: bool = Field(default=False, description="Include raw HTML in response")
    user_agent: Optional[str] = Field(default=None, description="Override User-Agent")
    proxy: Optional[str] = Field(default=None, description="HTTP proxy in host:port or scheme://host:port")
    wait_until: Optional[Literal["load", "domcontentloaded", "networkidle0", "networkidle2"]] = Field(
        default=None,
        description="Puppeteer navigation waitUntil option"
    )

    # Caching
    cache_mode: Literal["enabled", "read_only", "write_only", "bypass", "disabled"] = Field(
        default="enabled",
        description="Crawl cache behavior"
    )
    cache_ttl: int = Field(
        default=86400,
        ge=0,
        le=7 * 24 * 3600,
        description="TTL for cached HTML (seconds)"
    )

    # Dispatch/rate limiting
    per_host_concurrency: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Max parallel requests per host"
    )
    hits_per_sec: float = Field(
        default=0.0,
        ge=0.0,
        le=20.0,
        description="Per-host request rate (0 disables rate limiting)"
    )

    # Link head extraction / scoring
    link_head: bool = Field(
        default=False,
        description="Fetch link head/title and basic metadata"
    )
    link_enrichment_concurrency: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Max parallel link enrichment requests"
    )
    link_timeout: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Timeout (s) per link enrichment request"
    )
    link_max: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Max links to process for enrichment"
    )
    link_score_query: Optional[str] = Field(
        default=None,
        description="Query to score links against (simple relevance)"
    )
    link_score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Keep links with score >= threshold"
    )
    
    # Advanced crawl4ai-inspired features
    extraction_strategy: Literal["none", "cosine", "json_css", "regex", "llm"] = Field(
        default="none",
        description="Content extraction strategy"
    )
    
    extraction_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for the selected extraction strategy"
    )
    
    content_filter: Literal["none", "pruning", "bm25", "llm"] = Field(
        default="none",
        description="Content filtering strategy"
    )
    
    content_filter_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for the content filter"
    )
    
    markdown_generation: bool = Field(
        default=False,
        description="Enable enhanced markdown generation with citations"
    )
    
    markdown_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for markdown generation"
    )
    
    adaptive_crawling: bool = Field(
        default=False,
        description="Enable adaptive crawling with learning"
    )
    
    adaptive_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for adaptive crawling"
    )
    
    virtual_scrolling: bool = Field(
        default=False,
        description="Enable virtual scrolling for infinite pages"
    )
    
    virtual_scroll_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for virtual scrolling"
    )
    
    link_analysis: bool = Field(
        default=False,
        description="Enable intelligent link analysis and scoring"
    )
    
    link_analysis_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for link analysis"
    )


# New enhanced configuration models for crawl4ai features

class ExtractionStrategyConfig(BaseModel):
    """Configuration for extraction strategies."""
    
    strategy_type: Literal["none", "cosine", "json_css", "regex", "llm"]
    
    # Cosine strategy options
    semantic_filter: Optional[str] = None
    word_count_threshold: int = 10
    max_dist: float = 0.2
    linkage_method: str = "ward"
    top_k: int = 3
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    sim_threshold: float = 0.3
    
    # JSON CSS strategy options
    schema: Optional[Dict[str, Any]] = None
    
    # Regex strategy options
    patterns: Optional[Dict[str, str]] = None
    
    # LLM strategy options
    llm_config: Optional[Dict[str, Any]] = None
    extraction_type: str = "schema"
    instruction: Optional[str] = None
    
    # Common options
    verbose: bool = False


class ContentFilterConfig(BaseModel):
    """Configuration for content filters."""
    
    filter_type: Literal["none", "pruning", "bm25", "llm"]
    user_query: Optional[str] = None
    verbose: bool = False
    
    # Pruning filter options
    threshold: float = 0.48
    threshold_type: str = "fixed"
    min_word_threshold: int = 0
    
    # BM25 filter options
    bm25_threshold: float = 1.0
    top_k: int = 10
    
    # LLM filter options
    llm_config: Optional[Dict[str, Any]] = None
    relevance_threshold: float = 0.7
    max_tokens: int = 4000


class MarkdownConfig(BaseModel):
    """Configuration for markdown generation."""
    
    include_images: bool = True
    include_links: bool = True
    include_tables: bool = True
    include_code: bool = True
    max_image_width: int = 800
    link_preview: bool = False
    citations: bool = True
    content_filter: Optional[ContentFilterConfig] = None


class AdaptiveCrawlConfig(BaseModel):
    """Configuration for adaptive crawling."""
    
    confidence_threshold: float = 0.7
    max_depth: int = 5
    max_pages: int = 20
    strategy: Literal["statistical", "embedding"] = "statistical"
    learning_rate: float = 0.1
    min_relevance_score: float = 0.3
    saturation_threshold: int = 5
    quality_threshold: float = 0.5
    save_state: bool = True
    state_path: Optional[str] = None


class VirtualScrollConfig(BaseModel):
    """Configuration for virtual scrolling."""
    
    container_selector: Optional[str] = None
    scroll_count: int = 10
    scroll_by: Literal["viewport_height", "container_height", "pixels"] = "viewport_height"
    scroll_pixels: int = 1000
    wait_after_scroll: float = 2.0
    wait_for_selector: Optional[str] = None
    scroll_timeout: float = 30.0
    check_content_changes: bool = True
    min_content_increase: int = 100
    max_scroll_attempts: int = 50
    auto_detect_infinite_scroll: bool = True
    scroll_pause_detection: bool = True
    content_stabilization_time: float = 3.0


class LinkAnalysisConfig(BaseModel):
    """Configuration for link analysis."""
    
    query: Optional[str] = None
    score_threshold: float = 0.3
    concurrent_requests: int = 10
    max_preview_length: int = 500
    enable_domain_authority: bool = True
    enable_content_preview: bool = True
    enable_freshness_scoring: bool = True
    preview_timeout: float = 5.0
    
    high_authority_domains: List[str] = Field(default_factory=lambda: [
        'wikipedia.org', 'github.com', 'stackoverflow.com',
        'mozilla.org', 'w3.org', 'ietf.org', 'arxiv.org'
    ])
    
    medium_authority_domains: List[str] = Field(default_factory=lambda: [
        'medium.com', 'dev.to', 'reddit.com', 'news.ycombinator.com'
    ])
    
    low_quality_indicators: List[str] = Field(default_factory=lambda: [
        'ads', 'advertisement', 'popup', 'spam', 'click'
    ])
