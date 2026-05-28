"""
RAG (Retrieval-Augmented Generation) request and response models.

These models support AI agent web search pipelines for RAG applications.
"""
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class ResearchDepth(str, Enum):
    """Research depth levels."""
    QUICK = "quick"  # 5 queries, 20 sources
    STANDARD = "standard"  # 10 queries, 50 sources
    DEEP = "deep"  # 25 queries, 150 sources
    

class QueryCategory(str, Enum):
    """Categories for research query generation."""
    OVERVIEW = "overview"
    HISTORY = "history"
    CURRENT_STATE = "current_state"
    TECHNICAL = "technical"
    PRACTICAL = "practical"
    COMPARISON = "comparison"
    EXPERT_OPINION = "expert_opinion"
    FUTURE_TRENDS = "future_trends"
    CASE_STUDIES = "case_studies"
    BEST_PRACTICES = "best_practices"


# ============== Request Models ==============

class ResearchRequest(BaseModel):
    """Request for deep research on a topic."""
    
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Research topic or question",
        examples=["How does vector database indexing work?"]
    )
    
    depth: ResearchDepth = Field(
        default=ResearchDepth.STANDARD,
        description="Research depth level"
    )
    
    num_queries: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Override number of search queries (otherwise based on depth)"
    )
    
    target_sources: Optional[int] = Field(
        default=None,
        ge=5,
        le=500,
        description="Target number of unique sources (otherwise based on depth)"
    )
    
    categories: Optional[List[QueryCategory]] = Field(
        default=None,
        description="Specific query categories to include"
    )
    
    engines: List[str] = Field(
        default=["google", "bing", "duckduckgo"],
        min_length=1,
        max_length=5,
        description="Search engines to use"
    )
    
    scrape_content: bool = Field(
        default=True,
        description="Whether to scrape full page content"
    )
    
    generate_embeddings: bool = Field(
        default=True,
        description="Whether to generate embeddings for semantic search"
    )
    
    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Language code for search"
    )


class SemanticSearchRequest(BaseModel):
    """Request for semantic search over a research corpus."""
    
    corpus_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="ID of the research corpus to search"
    )
    
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Search query"
    )
    
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return"
    )
    
    min_relevance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score (0-1)"
    )


class QuickSearchRequest(BaseModel):
    """Request for quick RAG-optimized search."""
    
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Search query"
    )
    
    max_sources: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum sources to retrieve"
    )
    
    scrape_content: bool = Field(
        default=True,
        description="Whether to scrape full page content"
    )
    
    engines: List[str] = Field(
        default=["google", "bing", "duckduckgo"],
        description="Search engines to use"
    )
    
    include_context: bool = Field(
        default=True,
        description="Include formatted context for LLM"
    )


class ImageSearchRequest(BaseModel):
    """Request for image search."""
    
    query: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Image search query"
    )
    
    max_results: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum images to return"
    )
    
    safe_search: Literal["strict", "moderate", "off"] = Field(
        default="moderate",
        description="Safe search level"
    )
    
    engines: List[str] = Field(
        default=["google images", "bing images"],
        description="Image search engines to use"
    )


# ============== Response Models ==============

class ResearchSourceResponse(BaseModel):
    """A single research source."""
    
    url: str
    title: str
    content: str = Field(description="Extracted content (truncated)")
    summary: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    word_count: int
    engine: Optional[str] = None
    scraped_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "title": "Understanding Vector Databases",
                "content": "Vector databases are specialized systems...",
                "relevance_score": 0.85,
                "word_count": 1500,
                "engine": "google",
                "scraped_at": "2024-01-01T00:00:00Z"
            }
        }


class ResearchResponse(BaseModel):
    """Response for deep research operation."""
    
    topic: str
    corpus_id: Optional[str] = Field(
        description="ID for semantic search (if embeddings generated)"
    )
    sources: List[ResearchSourceResponse]
    total_sources_found: int
    queries_executed: List[str]
    processing_time_ms: int
    depth: ResearchDepth
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Vector database indexing",
                "corpus_id": "abc123def456",
                "sources": [],
                "total_sources_found": 50,
                "queries_executed": ["vector database indexing", "how vector search works"],
                "processing_time_ms": 15000,
                "depth": "standard"
            }
        }


class SemanticSearchResult(BaseModel):
    """A single semantic search result."""
    
    id: str
    score: float = Field(ge=0.0, le=1.0, description="Similarity score")
    url: str
    title: str
    summary: str
    relevance_score: Optional[float] = None


class SemanticSearchResponse(BaseModel):
    """Response for semantic search."""
    
    corpus_id: str
    query: str
    results: List[SemanticSearchResult]
    total_results: int
    processing_time_ms: int


class QuickSearchResponse(BaseModel):
    """Response for quick RAG search."""
    
    query: str
    context: Optional[str] = Field(
        description="Formatted context for LLM consumption"
    )
    sources: List[ResearchSourceResponse]
    source_count: int
    processing_time_ms: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "How does RAG work?",
                "context": "[Source 1] RAG Overview...",
                "sources": [],
                "source_count": 10,
                "processing_time_ms": 3500
            }
        }


class ImageResult(BaseModel):
    """A single image search result."""
    
    url: str
    thumbnail_url: Optional[str] = None
    title: str
    source_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    engine: str


class ImageSearchResponse(BaseModel):
    """Response for image search."""
    
    query: str
    images: List[ImageResult]
    total_results: int
    processing_time_ms: int


class CorpusInfo(BaseModel):
    """Information about a research corpus."""
    
    corpus_id: str
    topic: str
    source_count: int
    created_at: datetime
    last_accessed: Optional[datetime] = None


class CorpusListResponse(BaseModel):
    """Response listing available research corpora."""
    
    corpora: List[CorpusInfo]
    total_count: int


# ============== Query Generation Models ==============

class GeneratedQueriesResponse(BaseModel):
    """Response with generated research queries."""
    
    topic: str
    queries: List[str]
    categories_used: List[str]
    total_queries: int
