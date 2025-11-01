"""
API response models using Pydantic v2.
"""
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class ServiceHealth(BaseModel):
    """Service health status."""
    status: Literal["healthy", "degraded", "unhealthy"]
    latency_ms: int
    last_check: datetime
    details: Optional[Dict[str, Any]] = None


class ContentMetadata(BaseModel):
    """Extracted content metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    keywords: List[str] = Field(default_factory=list)
    og_data: Dict[str, str] = Field(default_factory=dict, description="Open Graph data")
    twitter_data: Dict[str, str] = Field(default_factory=dict, description="Twitter Card data")
    json_ld: Optional[Dict[str, Any]] = Field(default=None, description="JSON-LD structured data")


class ScrapedContent(BaseModel):
    """Scraped content from a webpage."""
    url: HttpUrl
    title: Optional[str] = None
    text: str
    html: Optional[str] = None
    images: List[HttpUrl] = Field(default_factory=list)
    links: List[HttpUrl] = Field(default_factory=list)
    metadata: ContentMetadata
    extraction_success: bool
    extraction_time_ms: int
    word_count: int
    language_detected: Optional[str] = None
    content_quality_score: float = Field(ge=0.0, le=1.0, description="Content quality score")
    error_message: Optional[str] = None


class SearchResult(BaseModel):
    """Individual search result."""
    rank: int
    title: str
    url: HttpUrl
    snippet: str
    engine: str
    score: Optional[float] = Field(default=None, description="Relevance score if available")
    scraped_content: Optional[ScrapedContent] = None
    cached: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "title": "Python Web Scraping Tutorial",
                "url": "https://example.com/python-scraping",
                "snippet": "Learn how to scrape websites using Python...",
                "engine": "google",
                "cached": False
            }
        }


class SearchMetadata(BaseModel):
    """Search operation metadata."""
    query: str
    engines_used: List[str]
    engines_succeeded: List[str]
    engines_failed: List[str] = Field(default_factory=list)
    total_results_found: int
    results_returned: int
    search_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SearchScrapeResponse(BaseModel):
    """Main search and scrape response."""
    search_metadata: SearchMetadata
    results: List[SearchResult]
    processing_time_ms: int
    cached: bool
    cache_key: Optional[str] = None
    total_results: int
    request_id: str = Field(description="Unique request identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "search_metadata": {
                    "query": "Python web scraping",
                    "engines_used": ["google", "bing"],
                    "engines_succeeded": ["google", "bing"],
                    "engines_failed": [],
                    "total_results_found": 250,
                    "results_returned": 10,
                    "search_time_ms": 1250,
                    "timestamp": "2024-01-01T00:00:00Z"
                },
                "results": [],
                "processing_time_ms": 2500,
                "cached": False,
                "total_results": 10,
                "request_id": "req_123456"
            }
        }


class AsyncTaskResponse(BaseModel):
    """Response for async task creation."""
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    created_at: datetime
    webhook_url: Optional[HttpUrl] = None
    estimated_completion_seconds: int = Field(default=60)
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_abc123",
                "status": "pending",
                "created_at": "2024-01-01T00:00:00Z",
                "webhook_url": "https://example.com/webhook",
                "estimated_completion_seconds": 30
            }
        }


class BatchSearchResponse(BaseModel):
    """Response for batch search operations."""
    batch_id: str
    queries_processed: int
    queries_failed: int
    results: Dict[str, List[SearchResult]]
    processing_time_ms: int
    errors: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid search query",
                "details": {"field": "query", "reason": "Query too long"},
                "request_id": "req_123456",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Application health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    environment: str
    services: Dict[str, ServiceHealth]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": "production",
                "services": {
                    "searxng": {
                        "status": "healthy",
                        "latency_ms": 120,
                        "last_check": "2024-01-01T00:00:00Z"
                    },
                    "redis": {
                        "status": "healthy",
                        "latency_ms": 5,
                        "last_check": "2024-01-01T00:00:00Z"
                    }
                },
                "timestamp": "2024-01-01T00:00:00Z",
                "uptime_seconds": 3600
            }
        }


class EngineInfo(BaseModel):
    """Search engine information."""
    name: str
    enabled: bool
    categories: List[str]
    supported_languages: List[str]
    safe_search_support: bool
    time_range_support: bool
    paging_support: bool
    
    
class EnginesListResponse(BaseModel):
    """List of available search engines."""
    engines: Dict[str, EngineInfo]
    total_engines: int
    enabled_engines: int
