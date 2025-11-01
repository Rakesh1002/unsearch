"""
Enhanced search and scraping API endpoints with crawl4ai-inspired capabilities.

This module provides advanced search and scraping functionality including:
- Advanced extraction strategies
- Content filtering
- Enhanced markdown generation
- Adaptive crawling
- Virtual scrolling
- Link analysis
"""

import asyncio
import uuid
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse, Response
import structlog

from app.models.requests import (
    UnQuestRequest, BatchSearchRequest, ScrapingConfig,
    ExtractionStrategyConfig, ContentFilterConfig, MarkdownConfig,
    AdaptiveCrawlConfig, VirtualScrollConfig, LinkAnalysisConfig
)
from app.models.responses import (
    UnQuestResponse, AsyncTaskResponse, BatchSearchResponse,
    SearchResult, SearchMetadata, EnginesListResponse, HealthResponse, ServiceHealth
)
from app.api.dependencies import (
    ApiKeyDep, SettingsDep, DatabaseDep, SearxngDep,
    ScraperDep, CacheDep, ClientInfoDep
)
from app.workers.tasks import process_async_search_scrape
from app.services.enhanced_scraping import get_enhanced_scraping_service
from app.services.multi_search import get_multi_search_service, SearchOptions
from app.services.multi_engine_scraper import get_multi_engine_service
from app.services.llm_configuration import get_llm_config_service, generate_config_from_prompt
from app.services.batch_operations import get_batch_service
from app.services.multi_entity_extraction import get_multi_entity_service, MultiEntityExtractionRequest

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/enhanced", tags=["enhanced-search"])


@router.post("/search", response_model=UnQuestResponse)
async def enhanced_search_and_scrape(
    request_data: UnQuestRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    db: DatabaseDep,
    searxng: SearxngDep,
    scraper: ScraperDep,
    cache: CacheDep,
    client_info: ClientInfoDep
):
    """
    Enhanced search and scrape endpoint with crawl4ai-inspired capabilities.
    
    This endpoint provides advanced features including:
    - Multiple extraction strategies (Cosine, JSON CSS, Regex, LLM)
    - Content filtering (BM25, Pruning, LLM)
    - Enhanced markdown generation with citations
    - Adaptive crawling with learning algorithms
    - Virtual scrolling for infinite pages
    - Intelligent link analysis and scoring
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        # Generate cache key
        cache_key = cache.generate_cache_key(request_data)
        
        # Check cache if enabled
        if request_data.cache_ttl > 0:
            cached_response = await cache.get_search_results(cache_key)
            if cached_response:
                cached_response.request_id = request_id
                
                # Log request with cached response
                await db.log_search_request(
                    request_data.dict(),
                    cached_response,
                    api_key_id,
                    client_info["client_ip"],
                    client_info["user_agent"]
                )
                
                return cached_response
        
        # Handle async mode
        if request_data.async_mode:
            if not request_data.webhook_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="webhook_url is required for async mode"
                )
            
            # Create enhanced scraping job
            job = await db.create_scraping_job(
                urls=[],  # Will be populated after search
                config=request_data.dict(),
                webhook_url=str(request_data.webhook_url)
            )
            
            # Queue async task with enhanced processing
            task = process_async_search_scrape.delay(
                job_id=job.job_id,
                request_data=request_data.dict(),
                enhanced_processing=True
            )
            
            # Update job with task ID
            await db.update_scraping_job(
                job.job_id,
                status="processing",
                task_id=task.id
            )
            
            return AsyncTaskResponse(
                task_id=job.job_id,
                status="processing",
                message="Enhanced search and scraping job queued",
                estimated_completion_time=datetime.utcnow().timestamp() + 60
            )
        
        # Perform search
        logger.info("enhanced_search_started", query=request_data.query, engines=request_data.engines)
        
        search_results = await searxng.search(
            query=request_data.query,
            engines=request_data.engines,
            num_results=request_data.max_results,
            language=request_data.language,
            safe_search=request_data.safe_search,
            timeout=request_data.timeout
        )
        
        if not search_results:
            return UnQuestResponse(
                request_id=request_id,
                query=request_data.query,
                results=[],
                metadata=SearchMetadata(
                    total_results=0,
                    engines_used=request_data.engines,
                    search_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                    language=request_data.language
                )
            )
        
        # Prepare enhanced scraping configuration
        enhanced_scraping_config = await _prepare_enhanced_scraping_config(request_data)
        
        # Enhanced content scraping
        scraped_contents = []
        if request_data.scrape_content:
            logger.info("enhanced_content_scraping_started", urls=len(search_results))
            
            # Get enhanced scraping service
            enhanced_scraper = await get_enhanced_scraping_service()
            
            # Extract URLs from search results
            urls_to_scrape = [result.url for result in search_results]
            
            # Perform enhanced scraping
            scraped_contents = await enhanced_scraper.scrape_urls_enhanced(
                urls=urls_to_scrape,
                config=enhanced_scraping_config
            )
        
        # Process and combine results
        results = await _combine_search_and_scraping_results(
            search_results, scraped_contents, request_data
        )
        
        # Calculate processing time
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Create response
        response = UnQuestResponse(
            request_id=request_id,
            query=request_data.query,
            results=results,
            metadata=SearchMetadata(
                total_results=len(results),
                engines_used=request_data.engines,
                search_time_ms=processing_time_ms,
                language=request_data.language,
                scraped_count=len(scraped_contents),
                enhanced_features_used=_get_enhanced_features_summary(request_data)
            )
        )
        
        # Cache response if enabled
        if request_data.cache_ttl > 0:
            await cache.set_search_results(cache_key, response, request_data.cache_ttl)
        
        # Log successful request
        await db.log_search_request(
            request_data.dict(),
            response,
            api_key_id,
            client_info["client_ip"],
            client_info["user_agent"]
        )
        
        logger.info(
            "enhanced_search_completed",
            request_id=request_id,
            results_count=len(results),
            processing_time_ms=processing_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error("enhanced_search_failed", request_id=request_id, error=str(e))
        
        # Log failed request
        await db.log_search_request(
            request_data.dict(),
            None,
            api_key_id,
            client_info["client_ip"],
            client_info["user_agent"],
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced search failed: {str(e)}"
        )


@router.post("/scrape", response_model=Dict[str, Any])
async def enhanced_scraping_only(
    config: ScrapingConfig,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    db: DatabaseDep,
    client_info: ClientInfoDep
):
    """
    Enhanced content scraping endpoint without search.
    
    Directly scrapes provided URLs with all advanced features.
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(
            "enhanced_scraping_only_started",
            urls=len(config.urls),
            extraction_strategy=getattr(config, 'extraction_strategy', 'none')
        )
        
        # Get enhanced scraping service
        enhanced_scraper = await get_enhanced_scraping_service()
        
        # Convert URLs to strings
        urls = [str(url) for url in config.urls]
        
        # Perform enhanced scraping
        scraped_contents = await enhanced_scraper.scrape_urls_enhanced(
            urls=urls,
            config=config
        )
        
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Prepare response
        response = {
            "request_id": request_id,
            "scraped_content": [
                {
                    "url": content.url,
                    "title": content.title,
                    "text": content.text,
                    "extraction_success": content.extraction_success,
                    "word_count": content.word_count,
                    "content_quality_score": content.content_quality_score,
                    **({
                        "extracted_content": getattr(content, 'extracted_content', None)
                    } if hasattr(content, 'extracted_content') else {}),
                    **({
                        "markdown": getattr(content, 'markdown', None)
                    } if hasattr(content, 'markdown') else {}),
                    **({
                        "link_analysis": getattr(content, 'link_analysis', None)
                    } if hasattr(content, 'link_analysis') else {})
                }
                for content in scraped_contents
            ],
            "metadata": {
                "total_urls": len(urls),
                "successful_scrapes": sum(1 for c in scraped_contents if c.extraction_success),
                "processing_time_ms": processing_time_ms,
                "enhanced_features": _get_enhanced_features_summary_from_config(config)
            }
        }
        
        # Log scraping request
        await db.log_scraping_request(
            config.dict(),
            response,
            api_key_id,
            client_info["client_ip"],
            client_info["user_agent"]
        )
        
        logger.info(
            "enhanced_scraping_only_completed",
            request_id=request_id,
            successful_scrapes=response["metadata"]["successful_scrapes"],
            processing_time_ms=processing_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error("enhanced_scraping_only_failed", request_id=request_id, error=str(e))
        
        # Log failed request
        await db.log_scraping_request(
            config.dict(),
            None,
            api_key_id,
            client_info["client_ip"],
            client_info["user_agent"],
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced scraping failed: {str(e)}"
        )


@router.get("/features", response_model=Dict[str, Any])
async def get_enhanced_features():
    """Get information about available enhanced features."""
    return {
        "extraction_strategies": {
            "none": "No extraction - return raw content",
            "cosine": "Semantic similarity clustering for content extraction",
            "json_css": "Structured data extraction using CSS selectors and schemas",
            "regex": "Pattern-based extraction using regular expressions",
            "llm": "AI-powered structured data extraction using language models"
        },
        "content_filters": {
            "none": "No filtering - return all content",
            "pruning": "Remove irrelevant content based on configurable thresholds",
            "bm25": "Information retrieval-based filtering using BM25 algorithm",
            "llm": "AI-powered content relevance filtering"
        },
        "markdown_generation": {
            "features": [
                "Enhanced HTML to markdown conversion",
                "Citation management and link analysis",
                "Multiple output formats (raw, fit, with references)",
                "Link prioritization and scoring"
            ]
        },
        "adaptive_crawling": {
            "features": [
                "Learning algorithms that improve extraction over time",
                "Statistical and embedding-based strategies",
                "Information saturation detection",
                "State persistence for continued learning"
            ]
        },
        "virtual_scrolling": {
            "features": [
                "Automatic infinite scroll detection and handling",
                "Smart waiting strategies for dynamic content",
                "Content extraction during scrolling",
                "Progress tracking and optimization"
            ]
        },
        "link_analysis": {
            "features": [
                "3-layer scoring system for smart link prioritization",
                "Domain authority and credibility assessment",
                "Content relevance scoring",
                "Link quality metrics and filtering"
            ]
        }
    }


async def _prepare_enhanced_scraping_config(request_data: UnQuestRequest) -> ScrapingConfig:
    """Prepare enhanced scraping configuration from request data."""
    config_dict = {
        "urls": [],  # Will be populated with search results
        "selectors": request_data.scrape_selectors,
        "extract_text": True,
        "extract_images": request_data.include_images,
        "extract_links": request_data.include_links,
        "extract_metadata": True,
        "javascript_rendering": request_data.js_mode,
        "js_mode": request_data.js_mode,
        "wait_time": 3 if request_data.js_mode else 0,
        "response_format": request_data.output_format,
        "screenshot": getattr(request_data, 'screenshot', False),
        "pdf": getattr(request_data, 'pdf', False),
        "include_html": False,
        "cache_mode": "enabled",
        "cache_ttl": request_data.cache_ttl,
        "per_host_concurrency": 2,
        "hits_per_sec": 1.0,
    }
    
    # Add enhanced features if specified in request
    enhanced_features = [
        'extraction_strategy', 'extraction_config',
        'content_filter', 'content_filter_config',
        'markdown_generation', 'markdown_config',
        'adaptive_crawling', 'adaptive_config',
        'virtual_scrolling', 'virtual_scroll_config',
        'link_analysis', 'link_analysis_config'
    ]
    
    for feature in enhanced_features:
        if hasattr(request_data, feature):
            config_dict[feature] = getattr(request_data, feature)
    
    return ScrapingConfig(**config_dict)


async def _combine_search_and_scraping_results(
    search_results: List[Any],
    scraped_contents: List[Any],
    request_data: UnQuestRequest
) -> List[SearchResult]:
    """Combine search results with scraped content."""
    combined_results = []
    
    # Create lookup for scraped content
    scraped_lookup = {content.url: content for content in scraped_contents}
    
    for search_result in search_results:
        # Get corresponding scraped content
        scraped_content = scraped_lookup.get(search_result.url)
        
        # Create enhanced search result
        result_dict = {
            "title": search_result.title,
            "url": search_result.url,
            "description": search_result.description,
            "engine": search_result.engine,
            "score": getattr(search_result, 'score', 0.0)
        }
        
        # Add scraped content if available
        if scraped_content and scraped_content.extraction_success:
            result_dict.update({
                "content": scraped_content.text,
                "word_count": scraped_content.word_count,
                "language": scraped_content.language_detected,
                "quality_score": scraped_content.content_quality_score,
                "images": scraped_content.images if request_data.include_images else [],
                "links": scraped_content.links if request_data.include_links else [],
                "metadata": {
                    "author": scraped_content.metadata.author,
                    "published_date": scraped_content.metadata.published_date,
                    "keywords": scraped_content.metadata.keywords
                }
            })
            
            # Add enhanced features if present
            if hasattr(scraped_content, 'extracted_content'):
                result_dict["extracted_content"] = scraped_content.extracted_content
                
            if hasattr(scraped_content, 'markdown'):
                result_dict["markdown"] = scraped_content.markdown
                
            if hasattr(scraped_content, 'link_analysis'):
                result_dict["link_analysis"] = scraped_content.link_analysis
        
        combined_results.append(SearchResult(**result_dict))
    
    return combined_results


def _get_enhanced_features_summary(request_data: UnQuestRequest) -> Dict[str, Any]:
    """Get summary of enhanced features used in request."""
    features = {}
    
    if hasattr(request_data, 'extraction_strategy') and request_data.extraction_strategy != 'none':
        features['extraction_strategy'] = request_data.extraction_strategy
        
    if hasattr(request_data, 'content_filter') and request_data.content_filter != 'none':
        features['content_filter'] = request_data.content_filter
        
    if hasattr(request_data, 'markdown_generation') and request_data.markdown_generation:
        features['markdown_generation'] = True
        
    if hasattr(request_data, 'adaptive_crawling') and request_data.adaptive_crawling:
        features['adaptive_crawling'] = True
        
    if hasattr(request_data, 'virtual_scrolling') and request_data.virtual_scrolling:
        features['virtual_scrolling'] = True
        
    if hasattr(request_data, 'link_analysis') and request_data.link_analysis:
        features['link_analysis'] = True
    
    return features


def _get_enhanced_features_summary_from_config(config: ScrapingConfig) -> Dict[str, Any]:
    """Get summary of enhanced features from scraping config."""
    features = {}
    
    if hasattr(config, 'extraction_strategy') and config.extraction_strategy != 'none':
        features['extraction_strategy'] = config.extraction_strategy
        
    if hasattr(config, 'content_filter') and config.content_filter != 'none':
        features['content_filter'] = config.content_filter
        
    if hasattr(config, 'markdown_generation') and config.markdown_generation:
        features['markdown_generation'] = True
        
    if hasattr(config, 'adaptive_crawling') and config.adaptive_crawling:
        features['adaptive_crawling'] = True
        
    if hasattr(config, 'virtual_scrolling') and config.virtual_scrolling:
        features['virtual_scrolling'] = True
        
    if hasattr(config, 'link_analysis') and config.link_analysis:
        features['link_analysis'] = True
    
    return features


@router.post("/extract-tables", response_model=Dict[str, Any])
async def extract_tables_from_html(
    request: Dict[str, Any],
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
):
    """
    Extract tables from HTML content using advanced table extraction strategies.
    
    Request body:
    {
        "html_content": "HTML content",
        "base_url": "https://example.com",  # optional
        "strategy": "default|llm|smart",   # optional, default: "default"
        "config": {}                       # optional strategy config
    }
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        html_content = request.get("html_content", "")
        if not html_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="html_content is required"
            )
        
        base_url = request.get("base_url", "")
        strategy = request.get("strategy", "default")
        config = request.get("config", {})
        
        # Get enhanced scraping service
        enhanced_scraper = await get_enhanced_scraping_service()
        
        # Extract tables
        tables = await enhanced_scraper.extract_tables(
            html_content=html_content,
            base_url=base_url,
            strategy=strategy,
            config=config
        )
        
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        response = {
            "request_id": request_id,
            "tables": tables,
            "metadata": {
                "total_tables": len(tables),
                "processing_time_ms": processing_time_ms,
                "strategy_used": strategy
            }
        }
        
        logger.info(
            "table_extraction_completed",
            request_id=request_id,
            tables_found=len(tables),
            processing_time_ms=processing_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error("table_extraction_failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Table extraction failed: {str(e)}"
        )


@router.post("/chunk-content", response_model=Dict[str, Any])
async def chunk_text_content(
    request: Dict[str, Any],
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
):
    """
    Chunk text content using various chunking strategies.
    
    Request body:
    {
        "text": "Text content to chunk",
        "strategy": "paragraph|sentence|fixed|topic|hybrid",  # optional, default: "paragraph"
        "config": {}  # optional strategy config
    }
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="text is required"
            )
        
        strategy = request.get("strategy", "paragraph")
        config = request.get("config", {})
        
        # Get enhanced scraping service
        enhanced_scraper = await get_enhanced_scraping_service()
        
        # Chunk content
        chunks = await enhanced_scraper.chunk_content(
            text=text,
            strategy=strategy,
            config=config
        )
        
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        response = {
            "request_id": request_id,
            "chunks": chunks,
            "metadata": {
                "total_chunks": len(chunks),
                "original_length": len(text),
                "avg_chunk_length": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0,
                "processing_time_ms": processing_time_ms,
                "strategy_used": strategy
            }
        }
        
        logger.info(
            "content_chunking_completed",
            request_id=request_id,
            chunks_created=len(chunks),
            processing_time_ms=processing_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error("content_chunking_failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content chunking failed: {str(e)}"
        )


@router.post("/discover-urls", response_model=Dict[str, Any])
async def discover_urls_from_source(
    request: Dict[str, Any],
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
):
    """
    Discover URLs from various sources (sitemaps, crawling).
    
    Request body:
    {
        "base_url": "https://example.com",
        "source": "sitemap|cc|crawl",  # optional, default: "sitemap"
        "max_urls": 100,              # optional
        "pattern": "regex_pattern",   # optional
        "query": "search_query"       # optional for relevance scoring
    }
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        base_url = request.get("base_url", "")
        if not base_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="base_url is required"
            )
        
        config = {
            "source": request.get("source", "sitemap"),
            "max_urls": request.get("max_urls", 100),
            "pattern": request.get("pattern"),
            "query": request.get("query"),
            "score_threshold": request.get("score_threshold", 0.0)
        }
        
        # Get enhanced scraping service
        enhanced_scraper = await get_enhanced_scraping_service()
        
        # Discover URLs
        discovered_urls = await enhanced_scraper.discover_urls(
            base_url=base_url,
            config=config
        )
        
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        response = {
            "request_id": request_id,
            "discovered_urls": discovered_urls,
            "metadata": {
                "total_urls": len(discovered_urls),
                "base_url": base_url,
                "source": config["source"],
                "processing_time_ms": processing_time_ms
            }
        }
        
        logger.info(
            "url_discovery_completed",
            request_id=request_id,
            urls_discovered=len(discovered_urls),
            processing_time_ms=processing_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error("url_discovery_failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"URL discovery failed: {str(e)}"
        )


@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_metrics(
    api_key_id: ApiKeyDep,
    settings: SettingsDep
):
    """Get comprehensive performance metrics for the enhanced scraping system."""
    try:
        enhanced_scraper = await get_enhanced_scraping_service()
        performance_report = await enhanced_scraper.get_performance_report()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": performance_report
        }
        
    except Exception as e:
        logger.error("performance_metrics_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )
