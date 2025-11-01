"""
Data models for the SearchScrape API.
"""
from app.models.requests import SearchScrapeRequest, BatchSearchRequest, ScrapingConfig
from app.models.responses import (
    SearchScrapeResponse, 
    SearchResult, 
    ScrapedContent,
    SearchMetadata,
    ContentMetadata,
    AsyncTaskResponse,
    BatchSearchResponse,
    ErrorResponse,
    HealthResponse,
    ServiceHealth,
    EngineInfo,
    EnginesListResponse
)

__all__ = [
    # Request models
    "SearchScrapeRequest",
    "BatchSearchRequest", 
    "ScrapingConfig",
    
    # Response models
    "SearchScrapeResponse",
    "SearchResult",
    "ScrapedContent", 
    "SearchMetadata",
    "ContentMetadata",
    "AsyncTaskResponse",
    "BatchSearchResponse",
    "ErrorResponse",
    "HealthResponse",
    "ServiceHealth",
    "EngineInfo",
    "EnginesListResponse"
]
