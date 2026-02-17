"""
Neural Search API - Exa-compatible Semantic Search

Endpoints for:
- Neural/semantic search
- Similar content discovery
- Auto-prompting (query expansion)
- Highlights extraction
- Predictive search
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import hashlib
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
from app.services.ai.cloudflare_ai import CloudflareAIService, CFModel
from app.services.core.searxng import SearXNGService

router = APIRouter(prefix="/neural", tags=["Neural Search"])

settings = get_settings()


# Models
class NeuralSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    num_results: int = Field(10, ge=1, le=50)
    use_autoprompt: bool = Field(False, description="Expand query with AI")
    include_highlights: bool = Field(True, description="Include key passages")
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    start_published_date: Optional[str] = None
    end_published_date: Optional[str] = None
    category: Optional[Literal["general", "news", "academic", "tech", "finance"]] = None


class NeuralSearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None
    author: Optional[str] = None
    highlights: Optional[List[str]] = None


class NeuralSearchResponse(BaseModel):
    query: str
    expanded_queries: Optional[List[str]] = None
    results: List[NeuralSearchResult]
    autoprompt_used: bool
    search_type: str = "neural"
    response_time_ms: int


class SimilarContentRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL to find similar content for")
    text: Optional[str] = Field(None, description="Text to find similar content for")
    num_results: int = Field(10, ge=1, le=50)
    exclude_source: bool = Field(True, description="Exclude the source URL from results")


class SimilarContentResponse(BaseModel):
    source: str  # URL or "text"
    similar: List[NeuralSearchResult]
    response_time_ms: int


class HighlightsRequest(BaseModel):
    query: str
    content: str
    num_highlights: int = Field(3, ge=1, le=10)


class Highlight(BaseModel):
    text: str
    relevance: float
    start_index: Optional[int] = None


class HighlightsResponse(BaseModel):
    query: str
    highlights: List[Highlight]


class PredictiveSearchRequest(BaseModel):
    context: Optional[str] = Field(None, description="Current context/page content")
    recent_searches: Optional[List[str]] = Field(None, description="Recent search history")
    num_predictions: int = Field(5, ge=1, le=10)


class SearchPrediction(BaseModel):
    query: str
    confidence: float
    reason: str


class PredictiveSearchResponse(BaseModel):
    predictions: List[SearchPrediction]
    context_used: bool


# In-memory embedding cache
_embedding_cache: Dict[str, List[float]] = {}


def get_ai_service() -> CloudflareAIService:
    return CloudflareAIService(
        account_id=settings.cloudflare_account_id,
        api_token=settings.cloudflare_api_token
    )


def get_search_service() -> SearXNGService:
    return SearXNGService()


@router.post("/search", response_model=NeuralSearchResponse)
async def neural_search(request: NeuralSearchRequest):
    """
    Perform neural/semantic search.
    
    This is an Exa-compatible endpoint that uses embeddings
    for semantic similarity rather than keyword matching.
    
    Features:
    - Auto-prompting: AI expands your query for better recall
    - Semantic matching: Finds conceptually related results
    - Highlights: Key relevant passages from each result
    """
    start_time = datetime.now()
    
    ai = get_ai_service()
    search = get_search_service()
    
    # Query expansion if enabled
    expanded_queries = None
    search_query = request.query
    
    if request.use_autoprompt:
        try:
            expansion = await ai.generate_text(
                prompt=f"""Expand this search query with 3 alternative phrasings to improve search recall.
Return ONLY a JSON array of strings, no explanation.
Query: "{request.query}" """,
                model=CFModel.LLAMA_3_1_8B_FAST,
                max_tokens=200
            )
            
            import json
            import re
            json_match = re.search(r'\[[\s\S]*\]', expansion)
            if json_match:
                expanded_queries = json.loads(json_match.group())
                # Combine queries
                search_query = f"{request.query} {' '.join(expanded_queries[:2])}"
        except Exception as e:
            logger.warning("autoprompt_expansion_failed", query=request.query, error=str(e))
    
    # Build search filters
    filters = {}
    if request.include_domains:
        filters['include_domains'] = request.include_domains
    if request.exclude_domains:
        filters['exclude_domains'] = request.exclude_domains
    
    # Perform search
    try:
        raw_results = await search.search(
            query=search_query,
            engines=["google", "bing", "duckduckgo"],
            language="en"
        )
        # Limit results for reranking
        raw_results = raw_results[:request.num_results * 2]
    except Exception as e:
        logger.error("neural_search_failed", query=request.query, error=str(e))
        raw_results = []
    
    # Generate query embedding for reranking
    query_embedding = await ai.generate_embeddings([request.query])
    
    # Score and rerank results
    results = []
    for result in raw_results:
        # Access SearchResult attributes properly (not dict access)
        content = (result.snippet or "")[:1000]
        
        # Generate content embedding (cached)
        cache_key = hashlib.md5(content.encode()).hexdigest()
        if cache_key in _embedding_cache:
            content_embedding = _embedding_cache[cache_key]
        else:
            content_embeddings = await ai.generate_embeddings([content])
            content_embedding = content_embeddings[0] if content_embeddings else None
            if content_embedding:
                _embedding_cache[cache_key] = content_embedding
        
        # Calculate similarity
        if content_embedding and query_embedding:
            import numpy as np
            similarity = np.dot(query_embedding[0], content_embedding) / (
                np.linalg.norm(query_embedding[0]) * np.linalg.norm(content_embedding)
            )
        else:
            similarity = 0.5
        
        # Extract highlights if enabled
        highlights = None
        if request.include_highlights and content:
            highlights = await extract_highlights_internal(request.query, content, 3, ai)
        
        results.append(NeuralSearchResult(
            title=result.title or "",
            url=str(result.url),
            content=content,
            score=float(similarity),
            published_date=None,  # SearchResult doesn't have published_date
            author=None,  # SearchResult doesn't have author
            highlights=highlights
        ))
    
    # Sort by similarity score
    results.sort(key=lambda x: x.score, reverse=True)
    results = results[:request.num_results]
    
    response_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return NeuralSearchResponse(
        query=request.query,
        expanded_queries=expanded_queries,
        results=results,
        autoprompt_used=request.use_autoprompt and expanded_queries is not None,
        search_type="neural",
        response_time_ms=response_time
    )


@router.post("/similar", response_model=SimilarContentResponse)
async def find_similar(request: SimilarContentRequest):
    """
    Find content similar to a URL or text.
    
    Exa-compatible endpoint for content discovery.
    """
    start_time = datetime.now()
    
    if not request.url and not request.text:
        raise HTTPException(status_code=400, detail="Either url or text is required")
    
    ai = get_ai_service()
    search = get_search_service()
    
    # Get source content
    source_content = ""
    source_label = "text"
    
    if request.url:
        source_label = request.url
        # Fetch URL content
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(request.url, timeout=10.0)
                source_content = response.text[:5000]
        except:
            raise HTTPException(status_code=400, detail="Could not fetch URL content")
    else:
        source_content = request.text[:5000]
    
    # Generate embedding
    source_embedding = await ai.generate_embeddings([source_content])
    
    if not source_embedding:
        raise HTTPException(status_code=500, detail="Could not generate embedding")
    
    # Extract key concepts for search
    concepts = await ai.generate_text(
        prompt=f"Extract 5 key concepts/topics from this text as a comma-separated list:\n{source_content[:2000]}",
        model=CFModel.LLAMA_3_1_8B_FAST,
        max_tokens=100
    )
    
    # Search for similar content
    try:
        raw_results = await search.search(
            query=concepts,
            engines=["google", "bing", "duckduckgo"],
            language="en"
        )
        raw_results = raw_results[:request.num_results * 2]
    except Exception as e:
        logger.warning("similar_search_failed", error=str(e))
        raw_results = []
    
    # Filter and score
    similar = []
    for result in raw_results:
        # Skip source URL if requested
        if request.exclude_source and request.url and str(result.url) == request.url:
            continue
        
        content = (result.snippet or "")[:1000]
        
        # Generate embedding
        content_embeddings = await ai.generate_embeddings([content])
        
        if content_embeddings:
            import numpy as np
            similarity = np.dot(source_embedding[0], content_embeddings[0]) / (
                np.linalg.norm(source_embedding[0]) * np.linalg.norm(content_embeddings[0])
            )
        else:
            similarity = 0.5
        
        similar.append(NeuralSearchResult(
            title=result.title or "",
            url=str(result.url),
            content=content,
            score=float(similarity)
        ))
    
    similar.sort(key=lambda x: x.score, reverse=True)
    similar = similar[:request.num_results]
    
    response_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return SimilarContentResponse(
        source=source_label,
        similar=similar,
        response_time_ms=response_time
    )


@router.post("/highlights", response_model=HighlightsResponse)
async def extract_highlights(request: HighlightsRequest):
    """
    Extract key relevant passages from content.
    
    Exa-compatible highlight extraction.
    """
    ai = get_ai_service()
    
    highlights = await extract_highlights_internal(
        request.query, 
        request.content, 
        request.num_highlights,
        ai
    )
    
    return HighlightsResponse(
        query=request.query,
        highlights=[
            Highlight(text=h, relevance=1.0 - (i * 0.1))
            for i, h in enumerate(highlights or [])
        ]
    )


async def extract_highlights_internal(
    query: str, 
    content: str, 
    num_highlights: int,
    ai: CloudflareAIService
) -> List[str]:
    """Internal function to extract highlights."""
    try:
        result = await ai.generate_text(
            prompt=f"""Extract the {num_highlights} most relevant passages from this content for the query "{query}".
Return ONLY a JSON array of strings, each string being a passage (50-150 words each).

Content:
{content[:4000]}""",
            model=CFModel.LLAMA_3_1_8B_FAST,
            max_tokens=800
        )
        
        import json
        import re
        json_match = re.search(r'\[[\s\S]*\]', result)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return None


@router.post("/predictive", response_model=PredictiveSearchResponse)
async def predictive_search(request: PredictiveSearchRequest):
    """
    Predict what the user might search for next.
    
    Groundbreaking feature that anticipates user needs based on:
    - Current page context
    - Recent search history
    - Time of day and patterns
    
    Not available in Tavily, Exa, or Glean.
    """
    ai = get_ai_service()
    
    context_info = ""
    if request.context:
        context_info = f"Current context: {request.context[:500]}\n"
    
    history_info = ""
    if request.recent_searches:
        history_info = f"Recent searches: {', '.join(request.recent_searches[-10:])}\n"
    
    if not context_info and not history_info:
        return PredictiveSearchResponse(
            predictions=[],
            context_used=False
        )
    
    prompt = f"""Based on this user context, predict {request.num_predictions} searches they might make next.

{context_info}{history_info}
Time: {datetime.now().strftime('%H:%M')}

Return as JSON array: [{{"query": "predicted search", "confidence": 0.0-1.0, "reason": "brief explanation"}}]"""

    try:
        result = await ai.generate_text(
            prompt=prompt,
            model=CFModel.LLAMA_3_1_8B_FAST,
            max_tokens=500
        )
        
        import json
        import re
        json_match = re.search(r'\[[\s\S]*\]', result)
        if json_match:
            predictions_data = json.loads(json_match.group())
            predictions = [
                SearchPrediction(
                    query=p.get('query', ''),
                    confidence=p.get('confidence', 0.5),
                    reason=p.get('reason', '')
                )
                for p in predictions_data
            ]
            return PredictiveSearchResponse(
                predictions=predictions,
                context_used=bool(request.context)
            )
    except:
        pass
    
    return PredictiveSearchResponse(
        predictions=[],
        context_used=bool(request.context)
    )


@router.get("/categories")
async def list_categories():
    """List available search categories."""
    return {
        "categories": [
            {"id": "general", "name": "General", "description": "All content types"},
            {"id": "news", "name": "News", "description": "News articles and journalism"},
            {"id": "academic", "name": "Academic", "description": "Research papers and scholarly content"},
            {"id": "tech", "name": "Technology", "description": "Tech blogs, documentation, tutorials"},
            {"id": "finance", "name": "Finance", "description": "Financial news and analysis"}
        ]
    }
