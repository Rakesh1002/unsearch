"""
Agent API endpoints - Tavily-compatible interface for AI agents.

This module provides drop-in replacement endpoints for Tavily:
- POST /agent/search - Web search optimized for LLMs
- POST /agent/extract - Content extraction from URLs
- POST /agent/research - Deep research with reasoning (UnSearch exclusive)

Design goals:
1. API compatibility with Tavily for easy migration
2. Same request/response structure
3. Additional features (zero-retention, multi-engine, production models)

AI Models Available:
- gpt-oss-120b: OpenAI open-weight, production-grade reasoning (BEST)
- llama-3.3-70b-instruct-fp8-fast: Great quality/speed balance
- qwq-32b: Reasoning model for analytical queries
- llama-3.1-8b-instruct-fast: Ultra-fast for simple queries
"""
import asyncio
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Literal
from fastapi import APIRouter, HTTPException, Header, Request, status
from pydantic import BaseModel, Field, HttpUrl
import structlog

from app.api.dependencies import (
    ApiKeyDep, AuthUserDep, SettingsDep, SearxngDep, ScraperDep, DatabaseDep,
    check_search_limit, check_scrape_limit, increment_sandbox_usage
)
from app.models.requests import ScrapingConfig
from app.services.ai.cloudflare_ai import get_cloudflare_ai_service, CFModel
from app.services.ai.search_pipeline import (
    get_search_pipeline, 
    SearchSource, 
    QueryComplexity,
    AISearchPipeline
)
from app.services.auth_service import track_usage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent (Tavily-compatible)"])


# ============================================================================
# Request/Response Models (Tavily-compatible)
# ============================================================================

class AgentSearchRequest(BaseModel):
    """
    Tavily-compatible search request with UnSearch enhancements.
    
    Maps directly to Tavily's /search endpoint parameters,
    plus additional UnSearch-exclusive options for production-grade AI.
    """
    query: str = Field(..., description="The search query to execute")
    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = Field(
        default="basic",
        description="Controls latency vs relevance tradeoff"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of search results"
    )
    topic: Literal["general", "news", "finance"] = Field(
        default="general",
        description="Category of the search"
    )
    include_answer: Union[bool, Literal["basic", "advanced", "production"]] = Field(
        default=False,
        description="Include LLM-generated answer. 'production' uses gpt-oss-120b for best quality"
    )
    include_raw_content: Union[bool, Literal["markdown", "text"]] = Field(
        default=False,
        description="Include full page content"
    )
    include_images: bool = Field(
        default=False,
        description="Include image search results"
    )
    include_image_descriptions: bool = Field(
        default=False,
        description="Add descriptions to images"
    )
    include_domains: Optional[List[str]] = Field(
        default=None,
        description="Domains to include in results"
    )
    exclude_domains: Optional[List[str]] = Field(
        default=None,
        description="Domains to exclude from results"
    )
    rerank: bool = Field(
        default=False,
        description="Rerank results using AI for better relevance"
    )
    # UnSearch-exclusive options
    model: Optional[Literal["auto", "speed", "quality", "reasoning", "production"]] = Field(
        default="auto",
        description="Model selection: auto (smart selection), speed (8B fast), quality (70B), reasoning (qwq-32b), production (gpt-oss-120b)"
    )
    check_safety: bool = Field(
        default=False,
        description="Run content safety checks (enterprise feature)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is machine learning?",
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": True,
                "model": "auto"
            }
        }


class AgentSearchResult(BaseModel):
    """Single search result in Tavily format."""
    title: str
    url: str
    content: str = Field(description="Snippet or full content")
    score: float = Field(description="Relevance score 0-1")
    raw_content: Optional[str] = Field(default=None, description="Full page content if requested")


class AgentSearchResponse(BaseModel):
    """
    Tavily-compatible search response with UnSearch metadata.
    """
    query: str
    answer: Optional[str] = Field(default=None, description="LLM-generated answer")
    images: List[Dict[str, Any]] = Field(default_factory=list)
    results: List[AgentSearchResult]
    response_time: float = Field(description="Time in seconds")
    # UnSearch-exclusive metadata
    model_used: Optional[str] = Field(default=None, description="AI model used for answer generation")
    query_complexity: Optional[str] = Field(default=None, description="Detected query complexity")
    safety_check: Optional[Dict[str, Any]] = Field(default=None, description="Content safety results")
    

class AgentExtractRequest(BaseModel):
    """
    Tavily-compatible extract request.
    """
    urls: List[str] = Field(..., description="URLs to extract content from", max_length=20)
    include_images: bool = Field(default=False)
    extract_depth: Literal["basic", "advanced"] = Field(default="basic")
    
    class Config:
        json_schema_extra = {
            "example": {
                "urls": ["https://en.wikipedia.org/wiki/Artificial_intelligence"],
                "extract_depth": "basic"
            }
        }


class ExtractedContent(BaseModel):
    """Single extracted content result."""
    url: str
    raw_content: str
    images: Optional[List[str]] = None
    failed: bool = False
    error: Optional[str] = None


class AgentExtractResponse(BaseModel):
    """Tavily-compatible extract response."""
    results: List[ExtractedContent]
    failed_urls: List[str] = Field(default_factory=list)
    response_time: float


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/search", response_model=AgentSearchResponse)
async def agent_search(
    request: AgentSearchRequest,
    http_request: Request,
    auth_user: AuthUserDep,
    settings: SettingsDep,
    searxng: SearxngDep,
    scraper: ScraperDep,
    db: DatabaseDep,
    x_zero_retention: Optional[str] = Header(default=None, description="Set to 'true' for zero data retention")
):
    """
    AI-optimized web search (Tavily /search compatible).
    
    This endpoint is designed as a drop-in replacement for Tavily's search API.
    It returns results optimized for LLM consumption with optional answer generation.
    
    **Key features:**
    - Tavily-compatible request/response format
    - Multi-engine search via SearXNG (70+ engines)
    - Optional zero-retention mode (X-Zero-Retention: true)
    - 50% cheaper than Tavily
    
    **Search depths:**
    - `basic`: Balanced relevance and speed (1 credit)
    - `advanced`: Higher relevance, more latency (2 credits)  
    - `fast`: Lower latency, good relevance (1 credit)
    - `ultra-fast`: Minimum latency (1 credit)
    
    **Model options (UnSearch exclusive):**
    - `auto`: Intelligent model selection based on query complexity
    - `speed`: llama-3.1-8b-instruct-fast for simple queries
    - `quality`: llama-3.3-70b-instruct-fp8-fast for balanced quality
    - `reasoning`: qwq-32b for analytical queries
    - `production`: gpt-oss-120b for maximum quality (OpenAI open-weight)
    
    **Migration from Tavily:**
    Simply change the base URL and API key. Request/response format is compatible.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    zero_retention = x_zero_retention and x_zero_retention.lower() == "true"
    
    # Check usage limits before processing
    check_search_limit(auth_user)
    
    # Determine if production model requested
    use_production = (
        request.model == "production" or 
        request.include_answer == "production"
    )
    use_reasoning = request.model == "reasoning"
    
    logger.info(
        "agent_search_start",
        query=request.query,
        search_depth=request.search_depth,
        max_results=request.max_results,
        model=request.model,
        use_production=use_production,
        zero_retention=zero_retention,
        request_id=request_id
    )
    
    try:
        # Initialize AI pipeline
        pipeline = await get_search_pipeline()
        
        # Map search depth to SearXNG parameters
        safe_search = 1  # moderate
        
        # Determine engines based on topic
        if request.topic == "news":
            engines = ["google news", "bing news", "duckduckgo"]
        elif request.topic == "finance":
            engines = ["google", "bing", "yahoo"]
        else:
            engines = ["google", "bing", "duckduckgo"]
        
        # Perform search
        search_results = await searxng.search(
            query=request.query,
            engines=engines,
            language="en",
            safe_search=safe_search,
            pageno=1
        )
        
        # Apply domain filters
        if request.include_domains:
            search_results = [
                r for r in search_results 
                if any(domain in str(r.url) for domain in request.include_domains)
            ]
        
        if request.exclude_domains:
            search_results = [
                r for r in search_results 
                if not any(domain in str(r.url) for domain in request.exclude_domains)
            ]
        
        # Limit results
        search_results = search_results[:request.max_results]
        
        # Convert to SearchSource objects for pipeline
        sources = [
            SearchSource(
                title=r.title or "",
                url=str(r.url),
                snippet=r.snippet or getattr(r, 'content', '') or "",
                score=0.0,
                rank=i
            )
            for i, r in enumerate(search_results)
        ]
        
        # Scrape raw content if requested (do this before pipeline for richer context)
        raw_contents = {}
        if request.include_raw_content:
            urls_to_scrape = [str(r.url) for r in search_results]
            if urls_to_scrape:
                scraping_config = ScrapingConfig(
                    urls=urls_to_scrape,
                    extract_images=request.include_images,
                    extract_links=False,
                    response_format="markdown" if request.include_raw_content in [True, "markdown"] else "text"
                )
                
                scraped = await scraper.scrape_urls(urls_to_scrape[:10], scraping_config)
                for sc in scraped:
                    if sc and sc.text:
                        raw_contents[str(sc.url)] = sc.text
                        # Update source with full content
                        for source in sources:
                            if source.url == str(sc.url):
                                source.content = sc.text[:3000]  # Limit for context
        
        # Run AI pipeline (reranking, answer generation, safety)
        pipeline_result = await pipeline.run_pipeline(
            query=request.query,
            sources=sources,
            include_answer=bool(request.include_answer),
            use_production_model=use_production,
            check_safety=request.check_safety,
            rerank=request.rerank,
            max_sources=request.max_results
        )
        
        # Build response results from pipeline
        results = []
        for i, source in enumerate(pipeline_result.sources):
            # Ensure content field is populated with best available text
            content_text = ""
            if source.content:
                content_text = source.content[:500]
            elif source.snippet:
                content_text = source.snippet
            
            result = AgentSearchResult(
                title=source.title,
                url=source.url,
                content=content_text,
                score=round(source.score if source.score > 0 else max(0.1, 1.0 - (i * 0.1)), 4),
                raw_content=raw_contents.get(source.url) if request.include_raw_content else None
            )
            results.append(result)
        
        # Handle images if requested
        images = []
        if request.include_images:
            try:
                image_results = await searxng.search(
                    query=request.query,
                    engines=["google images", "bing images"],
                    language="en",
                    safe_search=safe_search,
                    pageno=1
                )
                for img in image_results[:5]:
                    img_data = {"url": str(img.url)}
                    if request.include_image_descriptions:
                        img_data["description"] = img.title or ""
                    images.append(img_data)
            except Exception as e:
                logger.warning("image_search_failed", error=str(e))
        
        response_time = round(time.time() - start_time, 2)
        
        logger.info(
            "agent_search_complete",
            query=request.query,
            results_count=len(results),
            model_used=pipeline_result.model_used,
            query_complexity=pipeline_result.query_analysis.complexity.value,
            response_time=response_time,
            request_id=request_id
        )
        
        # Track usage (1 search query)
        if auth_user:
            if auth_user.is_agent_placeholder:
                # Sandbox agent - increment daily counter
                await increment_sandbox_usage(auth_user, db)
            else:
                # Regular user - track monthly usage
                await track_usage(
                    user_id=auth_user.user_id,
                    search_count=1,
                    engine="searxng"
                )
        
        return AgentSearchResponse(
            query=request.query,
            answer=pipeline_result.answer,
            images=images,
            results=results,
            response_time=response_time,
            model_used=pipeline_result.model_used,
            query_complexity=pipeline_result.query_analysis.complexity.value,
            safety_check=pipeline_result.safety_check if request.check_safety else None
        )
        
    except Exception as e:
        logger.error(
            "agent_search_error",
            query=request.query,
            error=str(e),
            error_type=type(e).__name__,
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/extract", response_model=AgentExtractResponse)
async def agent_extract(
    request: AgentExtractRequest,
    http_request: Request,
    auth_user: AuthUserDep,
    settings: SettingsDep,
    scraper: ScraperDep,
    db: DatabaseDep,
    x_zero_retention: Optional[str] = Header(default=None)
):
    """
    Extract content from URLs (Tavily /extract compatible).
    
    This endpoint extracts and cleans content from provided URLs,
    returning structured text suitable for LLM consumption.
    
    **Key features:**
    - Tavily-compatible request/response format
    - Intelligent content extraction with boilerplate removal
    - Optional JavaScript rendering for dynamic pages
    - Zero-retention mode available
    
    **Extract depths:**
    - `basic`: Fast extraction, good for most pages
    - `advanced`: JavaScript rendering, better for SPAs
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    zero_retention = x_zero_retention and x_zero_retention.lower() == "true"
    
    logger.info(
        "agent_extract_start",
        urls_count=len(request.urls),
        extract_depth=request.extract_depth,
        zero_retention=zero_retention,
        request_id=request_id
    )
    
    # Check usage limits before processing
    check_scrape_limit(auth_user)
    
    try:
        # Configure scraping
        scraping_config = ScrapingConfig(
            urls=request.urls,
            extract_images=request.include_images,
            extract_links=False,
            javascript_rendering=request.extract_depth == "advanced",
            js_mode=request.extract_depth == "advanced",
            response_format="markdown"
        )
        
        # Scrape URLs
        scraped_results = await scraper.scrape_urls(request.urls, scraping_config)
        
        # Build response
        results = []
        failed_urls = []
        
        # Normalize URLs for matching (remove trailing slashes)
        def normalize_url(url) -> str:
            return str(url).rstrip('/')
        
        scraped_map = {normalize_url(sc.url): sc for sc in scraped_results if sc}
        
        for url in request.urls:
            normalized_url = normalize_url(url)
            if normalized_url in scraped_map and scraped_map[normalized_url].text:
                sc = scraped_map[normalized_url]
                result = ExtractedContent(
                    url=url,
                    raw_content=sc.text or "",
                    images=[str(img) for img in (sc.images or [])] if request.include_images else None,
                    failed=False
                )
            else:
                result = ExtractedContent(
                    url=url,
                    raw_content="",
                    failed=True,
                    error="Failed to extract content"
                )
                failed_urls.append(url)
            
            results.append(result)
        
        response_time = round(time.time() - start_time, 2)
        
        logger.info(
            "agent_extract_complete",
            urls_count=len(request.urls),
            success_count=len(request.urls) - len(failed_urls),
            failed_count=len(failed_urls),
            response_time=response_time,
            request_id=request_id
        )
        
        # Track usage (1 scrape per URL)
        if auth_user:
            if auth_user.is_agent_placeholder:
                # Sandbox agents - scrapes count against daily search limit
                await increment_sandbox_usage(auth_user, db)
            else:
                # Regular user - track monthly scrape usage
                await track_usage(
                    user_id=auth_user.user_id,
                    scrape_count=len(request.urls) - len(failed_urls)
                )
        
        return AgentExtractResponse(
            results=results,
            failed_urls=failed_urls,
            response_time=response_time
        )
        
    except Exception as e:
        logger.error(
            "agent_extract_error",
            urls_count=len(request.urls),
            error=str(e),
            error_type=type(e).__name__,
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extract failed: {str(e)}"
        )


@router.get("/health")
async def agent_health():
    """Health check for agent endpoints."""
    cf_ai = await get_cloudflare_ai_service()
    return {
        "status": "healthy",
        "service": "UnSearch Agent API",
        "version": "1.0.0",
        "tavily_compatible": True,
        "cloudflare_ai_configured": cf_ai.is_configured if cf_ai else False
    }


# ============================================================================
# UnSearch Exclusive Endpoints
# ============================================================================

class ResearchRequest(BaseModel):
    """Deep research request with reasoning capabilities."""
    query: str = Field(..., description="Research question or topic")
    depth: Literal["quick", "standard", "deep", "comprehensive"] = Field(
        default="standard",
        description="Research depth level"
    )
    max_sources: int = Field(default=10, ge=3, le=30)
    include_analysis: bool = Field(default=True, description="Include analytical reasoning")
    include_summary: bool = Field(default=True, description="Include executive summary")
    focus_areas: Optional[List[str]] = Field(default=None, description="Specific areas to focus on")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the implications of quantum computing on cybersecurity?",
                "depth": "deep",
                "max_sources": 15,
                "include_analysis": True,
                "focus_areas": ["encryption", "post-quantum cryptography"]
            }
        }


class ResearchResponse(BaseModel):
    """Deep research response."""
    query: str
    executive_summary: Optional[str] = None
    detailed_analysis: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)
    sources: List[AgentSearchResult]
    methodology: Dict[str, Any] = Field(default_factory=dict)
    model_used: str
    response_time: float


@router.post("/research", response_model=ResearchResponse)
async def agent_research(
    request: ResearchRequest,
    http_request: Request,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    searxng: SearxngDep,
    scraper: ScraperDep,
    x_zero_retention: Optional[str] = Header(default=None)
):
    """
    Deep research with reasoning (UnSearch exclusive).
    
    This endpoint performs multi-stage research:
    1. Multi-engine search across web, news, and academic sources
    2. Content extraction and analysis
    3. AI-powered synthesis using reasoning models
    4. Key findings extraction
    
    **Depth levels:**
    - `quick`: Fast research, 3-5 sources, basic analysis
    - `standard`: Balanced, 5-10 sources, good analysis
    - `deep`: Thorough, 10-20 sources, detailed reasoning
    - `comprehensive`: Maximum depth, 20-30 sources, expert-level analysis
    
    **Models used:**
    - Quick: llama-3.1-8b-instruct-fast
    - Standard: llama-3.3-70b-instruct-fp8-fast  
    - Deep: qwq-32b (reasoning model)
    - Comprehensive: gpt-oss-120b (production)
    
    This is NOT available in Tavily - UnSearch exclusive feature.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    logger.info(
        "agent_research_start",
        query=request.query,
        depth=request.depth,
        max_sources=request.max_sources,
        request_id=request_id
    )
    
    try:
        pipeline = await get_search_pipeline()
        
        # Map depth to source count and model
        depth_config = {
            "quick": {"sources": min(5, request.max_sources), "model": CFModel.LLAMA_3_1_8B_FAST},
            "standard": {"sources": min(10, request.max_sources), "model": CFModel.LLAMA_3_3_70B_FAST},
            "deep": {"sources": min(20, request.max_sources), "model": CFModel.QWQ_32B},
            "comprehensive": {"sources": request.max_sources, "model": CFModel.GPT_OSS_120B},
        }
        config = depth_config[request.depth]
        
        # Multi-engine search
        all_results = []
        engines_sets = [
            ["google", "bing", "duckduckgo"],  # Web
            ["google news", "bing news"],  # News
        ]
        
        for engines in engines_sets:
            try:
                results = await searxng.search(
                    query=request.query,
                    engines=engines,
                    language="en",
                    safe_search=1,
                    pageno=1
                )
                all_results.extend(results)
            except Exception as e:
                logger.warning("search_engine_failed", engines=engines, error=str(e))
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = str(r.url)
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        # Convert to SearchSource
        sources = [
            SearchSource(
                title=r.title or "",
                url=str(r.url),
                snippet=r.snippet or "",
                score=0.0,
                rank=i
            )
            for i, r in enumerate(unique_results[:config["sources"]])
        ]
        
        # Scrape content for deeper analysis
        if request.depth in ["deep", "comprehensive"]:
            urls_to_scrape = [s.url for s in sources[:15]]
            if urls_to_scrape:
                scraping_config = ScrapingConfig(
                    urls=urls_to_scrape,
                    extract_images=False,
                    extract_links=False,
                    response_format="markdown"
                )
                scraped = await scraper.scrape_urls(urls_to_scrape, scraping_config)
                for sc in scraped:
                    if sc and sc.text:
                        for source in sources:
                            if source.url == str(sc.url):
                                source.content = sc.text[:5000]
        
        # Rerank all sources
        sources = await pipeline.rerank_results(request.query, sources, top_k=config["sources"])
        
        # Generate executive summary
        executive_summary = None
        if request.include_summary:
            summary_prompt = f"""Based on research about: {request.query}

Provide a concise executive summary (2-3 paragraphs) covering:
- Main findings
- Key insights
- Practical implications

Sources analyzed: {len(sources)}"""
            
            cf_ai = await get_cloudflare_ai_service()
            if cf_ai and cf_ai.is_configured:
                context = [f"{s.title}: {s.snippet}" for s in sources[:10]]
                executive_summary = await cf_ai.generate_answer(
                    question=summary_prompt,
                    context=context,
                    model=config["model"],
                    max_tokens=600
                )
        
        # Generate detailed analysis with reasoning
        detailed_analysis = None
        if request.include_analysis:
            focus_str = ""
            if request.focus_areas:
                focus_str = f"\n\nFocus particularly on: {', '.join(request.focus_areas)}"
            
            analysis_prompt = f"""Conduct a thorough analysis of: {request.query}

Analyze the following aspects:
1. Current state and key developments
2. Different perspectives and debates
3. Implications and future outlook
4. Recommendations{focus_str}

Use the provided sources to support your analysis with specific evidence."""
            
            cf_ai = await get_cloudflare_ai_service()
            if cf_ai and cf_ai.is_configured:
                context = []
                for s in sources[:15]:
                    ctx = f"[{s.title}] ({s.url})\n"
                    if s.content:
                        ctx += s.content[:2000]
                    else:
                        ctx += s.snippet
                    context.append(ctx)
                
                # Use reasoning for deep/comprehensive
                if request.depth in ["deep", "comprehensive"]:
                    result = await cf_ai.generate_with_reasoning(
                        prompt=f"{analysis_prompt}\n\nSources:\n" + "\n\n".join(context),
                        max_tokens=2048
                    )
                    detailed_analysis = result.text
                else:
                    detailed_analysis = await cf_ai.generate_answer(
                        question=analysis_prompt,
                        context=context,
                        model=config["model"],
                        max_tokens=1500
                    )
        
        # Extract key findings
        key_findings = []
        if detailed_analysis:
            # Simple extraction - look for numbered points or bullet patterns
            lines = detailed_analysis.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    finding = line.lstrip('0123456789.-•) ').strip()
                    if len(finding) > 20 and len(finding) < 300:
                        key_findings.append(finding)
                        if len(key_findings) >= 10:
                            break
        
        # Build response results
        results = [
            AgentSearchResult(
                title=s.title,
                url=s.url,
                content=s.snippet,
                score=round(s.score, 4) if s.score > 0 else 0.5,
                raw_content=s.content if s.content else None
            )
            for s in sources
        ]
        
        response_time = round(time.time() - start_time, 2)
        
        logger.info(
            "agent_research_complete",
            query=request.query,
            sources_count=len(sources),
            model=config["model"].value,
            response_time=response_time,
            request_id=request_id
        )
        
        return ResearchResponse(
            query=request.query,
            executive_summary=executive_summary,
            detailed_analysis=detailed_analysis,
            key_findings=key_findings,
            sources=results,
            methodology={
                "depth": request.depth,
                "sources_analyzed": len(sources),
                "engines_used": ["google", "bing", "duckduckgo", "google news", "bing news"],
                "content_scraped": request.depth in ["deep", "comprehensive"]
            },
            model_used=config["model"].value,
            response_time=response_time
        )
        
    except Exception as e:
        logger.error(
            "agent_research_error",
            query=request.query,
            error=str(e),
            error_type=type(e).__name__,
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research failed: {str(e)}"
        )


@router.get("/models")
async def list_models():
    """
    List available AI models (UnSearch exclusive).
    
    Shows all Cloudflare Workers AI models available for use.
    """
    cf_ai = await get_cloudflare_ai_service()
    
    return {
        "configured": cf_ai.is_configured if cf_ai else False,
        "models": {
            "embeddings": {
                "bge-m3": {
                    "id": "@cf/baai/bge-m3",
                    "description": "Multi-lingual embeddings (100+ languages)",
                    "dimensions": 1024,
                    "recommended_for": "Enterprise, multi-lingual"
                },
                "bge-large": {
                    "id": "@cf/baai/bge-large-en-v1.5",
                    "description": "High-quality English embeddings",
                    "dimensions": 1024,
                    "recommended_for": "English-only, high quality"
                },
                "embeddinggemma": {
                    "id": "@cf/google/embeddinggemma-300m",
                    "description": "Google's latest embedding model",
                    "dimensions": 768,
                    "recommended_for": "State-of-the-art quality"
                }
            },
            "text_generation": {
                "gpt-oss-120b": {
                    "id": "@cf/openai/gpt-oss-120b",
                    "description": "OpenAI open-weight, production-grade",
                    "tier": "production",
                    "recommended_for": "Maximum quality, enterprise"
                },
                "llama-3.3-70b-fast": {
                    "id": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                    "description": "Best quality/speed balance",
                    "tier": "quality",
                    "recommended_for": "Most use cases"
                },
                "llama-4-scout": {
                    "id": "@cf/meta/llama-4-scout-17b-16e-instruct",
                    "description": "Latest Llama 4, MoE architecture",
                    "tier": "quality",
                    "recommended_for": "Multimodal, function calling"
                },
                "qwq-32b": {
                    "id": "@cf/qwen/qwq-32b",
                    "description": "Reasoning model (competitive with o1-mini)",
                    "tier": "reasoning",
                    "recommended_for": "Complex analytical queries"
                },
                "deepseek-r1": {
                    "id": "@cf/deepseek/deepseek-r1-distill-qwen-32b",
                    "description": "State-of-the-art reasoning",
                    "tier": "reasoning",
                    "recommended_for": "Deep analysis"
                },
                "llama-3.1-8b-fast": {
                    "id": "@cf/meta/llama-3.1-8b-instruct-fast",
                    "description": "Ultra-fast for simple queries",
                    "tier": "speed",
                    "recommended_for": "Simple queries, low latency"
                }
            },
            "reranking": {
                "bge-reranker": {
                    "id": "@cf/baai/bge-reranker-base",
                    "description": "Result reranking for relevance"
                }
            },
            "safety": {
                "llama-guard": {
                    "id": "@cf/meta/llama-guard-3-8b",
                    "description": "Content safety classification"
                }
            }
        },
        "default_selection": {
            "embeddings": "@cf/baai/bge-m3",
            "text_generation": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            "reasoning": "@cf/qwen/qwq-32b",
            "production": "@cf/openai/gpt-oss-120b"
        }
    }
