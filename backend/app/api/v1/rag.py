"""
RAG (Retrieval-Augmented Generation) API endpoints for AI agent integration.

This module provides endpoints for:
- Deep research with multi-query coverage
- Semantic search over research corpora
- Quick RAG-optimized search
- Image search
- Research query generation
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from prometheus_client import Counter
import structlog

from app.models.rag import (
    ResearchRequest, ResearchResponse, ResearchSourceResponse,
    SemanticSearchRequest, SemanticSearchResponse, SemanticSearchResult,
    QuickSearchRequest, QuickSearchResponse,
    ImageSearchRequest, ImageSearchResponse, ImageResult,
    GeneratedQueriesResponse, ResearchDepth, CorpusListResponse, CorpusInfo
)
from app.api.dependencies import ApiKeyDep, SettingsDep, DatabaseDep
from app.services.rag.rag import get_rag_service, RAGService
from app.services.core.searxng import get_searxng_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])

# Prometheus metrics
RAG_RESEARCH_REQUESTS = Counter(
    'rag_research_requests_total',
    'Total RAG research requests',
    ['depth']
)
RAG_SEARCH_REQUESTS = Counter(
    'rag_search_requests_total',
    'Total RAG quick search requests'
)
RAG_SEMANTIC_SEARCH_REQUESTS = Counter(
    'rag_semantic_search_total',
    'Total RAG semantic search requests'
)
RAG_IMAGE_SEARCH_REQUESTS = Counter(
    'rag_image_search_total',
    'Total RAG image search requests'
)


# Research depth configurations
DEPTH_CONFIG = {
    ResearchDepth.QUICK: {"num_queries": 5, "target_sources": 20},
    ResearchDepth.STANDARD: {"num_queries": 10, "target_sources": 50},
    ResearchDepth.DEEP: {"num_queries": 25, "target_sources": 150},
}


@router.post("/research", response_model=ResearchResponse)
async def deep_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    db: DatabaseDep
):
    """
    Perform deep research on a topic.
    
    This endpoint executes multiple search queries to gather comprehensive
    information on a topic. Results can be stored with embeddings for
    subsequent semantic search.
    
    **Use cases:**
    - Building knowledge bases for AI agents
    - Comprehensive research for content generation
    - Gathering training data for RAG systems
    
    **Research depths:**
    - `quick`: 5 queries, ~20 sources (fastest)
    - `standard`: 10 queries, ~50 sources (balanced)
    - `deep`: 25 queries, ~150 sources (most comprehensive)
    """
    request_id = str(uuid.uuid4())
    
    try:
        rag_service = await get_rag_service()
        
        # Get depth configuration
        depth_config = DEPTH_CONFIG[request.depth]
        num_queries = request.num_queries or depth_config["num_queries"]
        target_sources = request.target_sources or depth_config["target_sources"]
        
        # Convert categories to strings if provided
        categories = None
        if request.categories:
            categories = [cat.value for cat in request.categories]
        
        logger.info(
            "deep_research_started",
            request_id=request_id,
            topic=request.topic,
            depth=request.depth.value,
            num_queries=num_queries,
            target_sources=target_sources
        )
        
        # Execute research
        result = await rag_service.deep_research(
            topic=request.topic,
            num_queries=num_queries,
            max_sources_per_query=10,
            target_total_sources=target_sources,
            scrape_content=request.scrape_content,
            generate_embeddings=request.generate_embeddings,
            engines=request.engines
        )
        
        # Convert to response model
        sources = [
            ResearchSourceResponse(
                url=s.url,
                title=s.title,
                content=s.content[:2000] if s.content else "",  # Truncate for response
                summary=s.summary,
                relevance_score=s.relevance_score,
                word_count=s.word_count,
                engine=s.metadata.get("engine"),
                scraped_at=s.scraped_at
            )
            for s in result.sources
        ]
        
        response = ResearchResponse(
            topic=result.query,
            corpus_id=result.corpus_id,
            sources=sources,
            total_sources_found=result.total_sources_found,
            queries_executed=result.queries_executed,
            processing_time_ms=result.processing_time_ms,
            depth=request.depth
        )
        
        # Log usage in background
        background_tasks.add_task(
            db.log_search_request,
            {
                "query": f"RAG_RESEARCH:{request.topic}",
                "depth": request.depth.value,
                "sources_found": len(sources),
                "request_id": request_id
            },
            None,
            api_key_id,
            "",  # client_ip
            ""   # user_agent
        )
        
        # Track metrics
        RAG_RESEARCH_REQUESTS.labels(depth=request.depth.value).inc()
        
        logger.info(
            "deep_research_completed",
            request_id=request_id,
            topic=request.topic,
            sources_found=len(sources),
            corpus_id=result.corpus_id,
            processing_time_ms=result.processing_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "deep_research_error",
            request_id=request_id,
            topic=request.topic,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}"
        )


@router.post("/search", response_model=QuickSearchResponse)
async def quick_search(
    request: QuickSearchRequest,
    api_key_id: ApiKeyDep,
    settings: SettingsDep
):
    """
    Quick RAG-optimized search.
    
    This endpoint performs a single search query optimized for RAG applications.
    It returns sources with optional formatted context ready for LLM consumption.
    
    **Use cases:**
    - Real-time question answering
    - On-demand information retrieval
    - AI agent tool calls
    """
    request_id = str(uuid.uuid4())
    
    try:
        rag_service = await get_rag_service()
        
        result = await rag_service.search_and_answer(
            query=request.query,
            max_sources=request.max_sources,
            scrape_content=request.scrape_content,
            engines=request.engines
        )
        
        # Convert to response model - handle scraped_at which may be ISO string or datetime
        sources = []
        for s in result["sources"]:
            scraped_at_value = s.get("scraped_at")
            if scraped_at_value is None:
                scraped_at = datetime.utcnow()
            elif isinstance(scraped_at_value, str):
                try:
                    scraped_at = datetime.fromisoformat(scraped_at_value.replace('Z', '+00:00'))
                except ValueError:
                    scraped_at = datetime.utcnow()
            elif isinstance(scraped_at_value, datetime):
                scraped_at = scraped_at_value
            else:
                scraped_at = datetime.utcnow()
            
            sources.append(ResearchSourceResponse(
                url=s["url"],
                title=s["title"],
                content=s.get("content", "")[:2000],
                summary=s.get("summary"),
                relevance_score=s.get("relevance_score", 0.0),
                word_count=s.get("word_count", 0),
                engine=s.get("metadata", {}).get("engine"),
                scraped_at=scraped_at
            ))
        
        # Track metrics
        RAG_SEARCH_REQUESTS.inc()
        
        return QuickSearchResponse(
            query=result["query"],
            context=result["context"] if request.include_context else None,
            sources=sources,
            source_count=result["source_count"],
            processing_time_ms=result["processing_time_ms"]
        )
        
    except Exception as e:
        logger.error(
            "quick_search_error",
            request_id=request_id,
            query=request.query,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    api_key_id: ApiKeyDep
):
    """
    Perform semantic search over a research corpus.
    
    This endpoint searches a previously created research corpus using
    vector similarity. Use the `corpus_id` returned from the `/research`
    endpoint.
    
    **Use cases:**
    - Finding relevant information from prior research
    - Chapter-specific content retrieval
    - Context retrieval for generation tasks
    """
    request_id = str(uuid.uuid4())
    
    try:
        rag_service = await get_rag_service()
        
        results = await rag_service.semantic_search(
            corpus_id=request.corpus_id,
            query=request.query,
            limit=request.limit,
            min_relevance=request.min_relevance
        )
        
        # Convert to response model
        search_results = [
            SemanticSearchResult(
                id=r["id"],
                score=r["score"],
                url=r["url"],
                title=r["title"],
                summary=r.get("summary", ""),
                relevance_score=r.get("relevance_score")
            )
            for r in results
        ]
        
        # Track metrics
        RAG_SEMANTIC_SEARCH_REQUESTS.inc()
        
        return SemanticSearchResponse(
            corpus_id=request.corpus_id,
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            processing_time_ms=0  # Would need timing in service
        )
        
    except Exception as e:
        logger.error(
            "semantic_search_error",
            request_id=request_id,
            corpus_id=request.corpus_id,
            query=request.query,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.post("/images", response_model=ImageSearchResponse)
async def image_search(
    request: ImageSearchRequest,
    api_key_id: ApiKeyDep
):
    """
    Search for images using SearXNG image categories.
    
    **Use cases:**
    - Finding reference images for content
    - Visual research and inspiration
    - Image-based RAG applications
    """
    request_id = str(uuid.uuid4())
    start_time = asyncio.get_event_loop().time()
    
    try:
        searxng = await get_searxng_service()
        
        # Convert safe_search to numeric
        safe_search_map = {"off": 0, "moderate": 1, "strict": 2}
        safe_search_value = safe_search_map.get(request.safe_search, 1)
        
        # Search with image category
        results = await searxng.search(
            query=request.query,
            engines=request.engines,
            categories=["images"],
            safe_search=safe_search_value
        )
        
        # Extract image results
        images = []
        for result in results[:request.max_results]:
            images.append(ImageResult(
                url=str(result.url),
                thumbnail_url=None,  # Would need to extract from SearXNG response
                title=result.title,
                source_url=str(result.url),
                engine=result.engine
            ))
        
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Track metrics
        RAG_IMAGE_SEARCH_REQUESTS.inc()
        
        return ImageSearchResponse(
            query=request.query,
            images=images,
            total_results=len(images),
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        logger.error(
            "image_search_error",
            request_id=request_id,
            query=request.query,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image search failed: {str(e)}"
        )


@router.post("/generate-queries", response_model=GeneratedQueriesResponse)
async def generate_queries(
    topic: str,
    num_queries: int = 10,
    api_key_id: ApiKeyDep = None
):
    """
    Generate diverse research queries for a topic.
    
    This endpoint generates multiple search queries covering different
    aspects of a topic. Useful for understanding the search strategy
    before executing research.
    
    **Categories covered:**
    - Overview and definitions
    - Historical context
    - Current state and trends
    - Technical details
    - Practical applications
    - Comparisons and alternatives
    - Expert opinions
    - Future predictions
    - Case studies
    - Best practices
    """
    try:
        rag_service = await get_rag_service()
        
        queries = rag_service.generate_research_queries(
            topic=topic,
            num_queries=num_queries
        )
        
        return GeneratedQueriesResponse(
            topic=topic,
            queries=queries,
            categories_used=[
                "overview", "history", "current_state", "technical",
                "practical", "comparison", "expert_opinion", "future_trends"
            ][:num_queries],
            total_queries=len(queries)
        )
        
    except Exception as e:
        logger.error("generate_queries_error", topic=topic, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query generation failed: {str(e)}"
        )


@router.get("/corpus", response_model=CorpusListResponse)
async def list_corpora(
    api_key_id: ApiKeyDep
):
    """
    List all available research corpora.
    
    Returns a list of all corpora with their metadata including
    source counts and status.
    """
    try:
        rag_service = await get_rag_service()
        
        corpora = []
        for corpus_id, vectors in rag_service.vector_store._vectors.items():
            corpora.append(CorpusInfo(
                corpus_id=corpus_id,
                topic=corpus_id,  # We don't store the original topic, use corpus_id
                source_count=len(vectors),
                created_at=datetime.utcnow()  # We don't track creation time currently
            ))
        
        return CorpusListResponse(
            corpora=corpora,
            total_count=len(corpora)
        )
        
    except Exception as e:
        logger.error("list_corpora_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list corpora: {str(e)}"
        )


@router.get("/corpus/{corpus_id}/info")
async def get_corpus_info(
    corpus_id: str,
    api_key_id: ApiKeyDep
):
    """
    Get information about a research corpus.
    
    Returns metadata about the corpus including the number of stored
    vectors and creation time.
    """
    try:
        rag_service = await get_rag_service()
        
        size = rag_service.vector_store.get_corpus_size(corpus_id)
        
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus '{corpus_id}' not found"
            )
            
        return {
            "corpus_id": corpus_id,
            "vector_count": size,
            "status": "active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_corpus_info_error", corpus_id=corpus_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get corpus info: {str(e)}"
        )


@router.delete("/corpus/{corpus_id}")
async def delete_corpus(
    corpus_id: str,
    api_key_id: ApiKeyDep
):
    """
    Delete a research corpus.
    
    Removes all vectors and metadata associated with the corpus.
    This operation cannot be undone.
    """
    try:
        rag_service = await get_rag_service()
        
        size = rag_service.vector_store.get_corpus_size(corpus_id)
        
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Corpus '{corpus_id}' not found"
            )
            
        await rag_service.vector_store.delete_corpus(corpus_id)
        
        return {
            "message": f"Corpus '{corpus_id}' deleted successfully",
            "vectors_removed": size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_corpus_error", corpus_id=corpus_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete corpus: {str(e)}"
        )
