"""
Data models for the UnSearch API.
"""
from app.models.requests import UnSearchRequest, BatchSearchRequest, ScrapingConfig
from app.models.responses import (
    UnSearchResponse, 
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
    "UnSearchRequest",
    "BatchSearchRequest", 
    "ScrapingConfig",
    
    # Response models
    "UnSearchResponse",
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
