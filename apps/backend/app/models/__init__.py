"""
Data models for the UnSearch API.
"""
from app.models.requests import UnQuestRequest, BatchSearchRequest, ScrapingConfig
from app.models.responses import (
    UnQuestResponse, 
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
    "UnQuestRequest",
    "BatchSearchRequest", 
    "ScrapingConfig",
    
    # Response models
    "UnQuestResponse",
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
