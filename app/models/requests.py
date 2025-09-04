"""
API request models using Pydantic v2.
"""
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, validator
import re


class SearchScrapeRequest(BaseModel):
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
    
    output_format: Literal["json", "xml"] = Field(
        default="json", 
        description="Response format"
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
    
    webhook_url: Optional[HttpUrl] = Field(
        default=None,
        description="Webhook URL for async results"
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
