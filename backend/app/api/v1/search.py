"""
Search and scraping API endpoints.
"""
import asyncio
import uuid
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, status
import httpx
from fastapi.responses import JSONResponse, Response
import structlog

from app.models.requests import UnSearchRequest, BatchSearchRequest, ScrapingConfig
from app.models.responses import (
    UnSearchResponse, AsyncTaskResponse, BatchSearchResponse,
    SearchResult, SearchMetadata, EnginesListResponse, HealthResponse, ServiceHealth
)
from app.api.dependencies import (
    ApiKeyDep, AuthUserDep, SettingsDep, DatabaseDep, SearxngDep,
    ScraperDep, CacheDep, CitationStoreDep, ClientInfoDep, check_search_limit, increment_sandbox_usage
)
from app.workers.tasks import process_async_search_scrape
from app.services.auth_service import track_usage
from app.services.citation_store import envelope_for_result
from app.api.v1.audit import record_audit_event

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=UnSearchResponse)
async def search_and_scrape(
    request_data: UnSearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    auth_user: AuthUserDep,
    settings: SettingsDep,
    db: DatabaseDep,
    searxng: SearxngDep,
    scraper: ScraperDep,
    cache: CacheDep,
    citation_store: CitationStoreDep,
    client_info: ClientInfoDep
):
    """
    Main search and scrape endpoint.
    
    Performs web search using SearXNG and optionally scrapes content from results.
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    # Check usage limits before processing
    check_search_limit(auth_user)
    
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
                    int(auth_user.api_key_id) if auth_user and auth_user.api_key_id else None,
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
                
            # Create scraping job
            job = await db.create_scraping_job(
                urls=[],  # Will be populated after search
                config=request_data.dict(),
                webhook_url=str(request_data.webhook_url)
            )
            
            # Queue async task
            task = process_async_search_scrape.delay(
                job_id=job.job_id,
                request_data=request_data.dict()
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
                created_at=datetime.utcnow(),
                webhook_url=request_data.webhook_url,
                estimated_completion_seconds=30
            )
            
        # Perform search
        search_start = asyncio.get_event_loop().time()
        
        # Convert safe_search to numeric
        safe_search_map = {"off": 0, "moderate": 1, "strict": 2}
        safe_search_value = safe_search_map.get(request_data.safe_search, 1)
        
        # Use relevance-filtered search if enabled
        query_analysis = None
        if request_data.relevance_filter:
            search_results, query_analysis = await searxng.search_with_relevance(
                query=request_data.query,
                engines=request_data.engines,
                max_results=request_data.max_results,
                language=request_data.language,
                safe_search=safe_search_value,
                enable_filtering=True,
                min_relevance_score=request_data.min_relevance_score,
                pageno=1
            )
        else:
            # Legacy: no relevance filtering
            search_results = await searxng.search(
                query=request_data.query,
                engines=request_data.engines,
                language=request_data.language,
                safe_search=safe_search_value,
                pageno=1
            )
            search_results = search_results[:request_data.max_results]
        
        search_time_ms = int((asyncio.get_event_loop().time() - search_start) * 1000)
        
        # Scrape content if requested
        if request_data.scrape_content and search_results:
            scraping_start = asyncio.get_event_loop().time()
            
            # Extract URLs to scrape (convert HttpUrl to string)
            urls_to_scrape = [str(result.url) for result in search_results]
            
            # Create scraping config
            scraping_config = ScrapingConfig(
                urls=urls_to_scrape,
                selectors=request_data.scrape_selectors,
                extract_images=request_data.include_images,
                extract_links=request_data.include_links,
                javascript_rendering=request_data.js_mode,
                js_mode=request_data.js_mode,
                response_format=request_data.output_format,
                screenshot=request_data.screenshot,
                pdf=request_data.pdf,
            )
            
            # Scrape URLs
            scraped_contents = await scraper.scrape_urls(
                urls_to_scrape[:10],  # Limit concurrent scraping
                scraping_config
            )
            
            # Map scraped content to results (filter out None and unsuccessful scrapes)
            # Normalize URLs by removing trailing slashes for matching
            def normalize_url(url) -> str:
                return str(url).rstrip('/')
            
            scraped_map = {normalize_url(sc.url): sc for sc in scraped_contents if sc and sc.extraction_success}
            
            for result in search_results:
                normalized_result_url = normalize_url(result.url)
                if normalized_result_url in scraped_map:
                    result.scraped_content = scraped_map[normalized_result_url]

            scraping_time_ms = int((asyncio.get_event_loop().time() - scraping_start) * 1000)

        # Attach signed citation envelopes to every result.
        api_key_id_str = str(auth_user.api_key_id) if auth_user and auth_user.api_key_id else None
        for result in search_results:
            envelope = await envelope_for_result(
                store=citation_store,
                url=str(result.url),
                snippet=result.snippet or "",
                engine=result.engine,
                scraped_content=result.scraped_content,
                api_key_id=api_key_id_str,
                request_id=request_id,
            )
            if envelope:
                result.citation_envelope = envelope
                if result.scraped_content:
                    result.scraped_content.citation_envelope = envelope
        else:
            scraping_time_ms = 0
            
        # Build response
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        response = UnSearchResponse(
            search_metadata=SearchMetadata(
                query=request_data.query,
                engines_used=request_data.engines,
                engines_succeeded=request_data.engines,  # TODO: Track actual successes
                engines_failed=[],
                total_results_found=len(search_results),
                results_returned=len(search_results),
                search_time_ms=search_time_ms,
                query_intent=query_analysis.intent.value if query_analysis else None,
                relevance_filtered=request_data.relevance_filter
            ),
            results=search_results,
            processing_time_ms=processing_time_ms,
            cached=False,
            cache_key=cache_key,
            total_results=len(search_results),
            request_id=request_id
        )
        
        # Cache response if enabled
        if request_data.cache_ttl > 0:
            background_tasks.add_task(
                cache.set_search_results,
                cache_key,
                response,
                request_data.cache_ttl
            )
            
        # Log request
        # Note: api_key_id is set to None because search_requests.api_key_id references
        # the legacy api_keys table, not user_api_keys. User tracking is done via track_usage.
        background_tasks.add_task(
            db.log_search_request,
            request_data.dict(),
            response,
            None,  # api_key_id - legacy field, usage tracked separately
            client_info["client_ip"],
            client_info["user_agent"]
        )
        
        # Track usage
        if auth_user:
            # For sandbox agents, increment daily counter
            if auth_user.is_agent_placeholder:
                background_tasks.add_task(
                    increment_sandbox_usage,
                    auth_user,
                    db
                )
            else:
                # Regular users - track monthly usage
                scrape_count = len([r for r in search_results if r.scraped_content]) if request_data.scrape_content else 0
                background_tasks.add_task(
                    track_usage,
                    user_id=auth_user.user_id,
                    search_count=1,
                    scrape_count=scrape_count,
                    engine=request_data.engines[0] if request_data.engines else "searxng"
                )

        # Log audit event for citation envelopes
        background_tasks.add_task(
            record_audit_event,
            citation_store,
            api_key_id_str,
            request_id,
            "POST /api/v1/search",
            search_results,
        )

        # If markdown format requested, return text/markdown response with concatenated markdown from scraped contents
        if request_data.output_format == "markdown" and request_data.scrape_content:
            parts = []
            for r in search_results:
                if r.scraped_content and r.scraped_content.text:
                    header = f"# {r.title}\n{r.url}\n\n" if r.title else f"{r.url}\n\n"
                    parts.append(header + r.scraped_content.text)
            markdown_body = "\n\n---\n\n".join(parts) if parts else ""
            return Response(content=markdown_body, media_type="text/markdown")

        return response
        
    except Exception as e:
        logger.error(
            "search_scrape_error",
            request_id=request_id,
            query=request_data.query,
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Log error to database
        background_tasks.add_task(
            db.log_error,
            error_type=type(e).__name__,
            error_message=str(e),
            request_id=request_id,
            endpoint="/search",
            method="POST",
            client_ip=client_info["client_ip"]
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchSearchResponse)
async def batch_search(
    request_data: BatchSearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    auth_user: AuthUserDep,
    settings: SettingsDep,
    db: DatabaseDep,
    searxng: SearxngDep,
    scraper: ScraperDep,
    citation_store: CitationStoreDep,
    client_info: ClientInfoDep
):
    """
    Batch search endpoint for multiple queries.
    
    Processes multiple search queries in parallel with optional content scraping.
    """
    start_time = asyncio.get_event_loop().time()
    batch_id = str(uuid.uuid4())
    
    # Check usage limits before processing
    check_search_limit(auth_user)
    
    try:
        results = {}
        errors = {}
        
        # Create semaphore for parallel request limiting
        semaphore = asyncio.Semaphore(request_data.parallel_requests)
        
        async def search_single_query(query: str) -> List[SearchResult]:
            """Search a single query with rate limiting."""
            async with semaphore:
                try:
                    # Use relevance-filtered search for better quality
                    search_results, _ = await searxng.search_with_relevance(
                        query=query,
                        engines=request_data.engines,
                        max_results=request_data.max_results_per_query,
                        language="en",
                        safe_search=1,
                        enable_filtering=True
                    )
                    
                    limited_results = search_results
                    
                    # Optional content scraping for batch
                    if request_data.scrape_content and limited_results:
                        urls = [r.url for r in limited_results[:3]]  # Limit scraping in batch
                        
                        scraping_config = ScrapingConfig(
                            urls=urls,
                            extract_images=False,
                            extract_links=False
                        )
                        
                        scraped_contents = await scraper.scrape_urls(urls, scraping_config)
                        scraped_map = {str(sc.url): sc for sc in scraped_contents if sc and sc.extraction_success}
                        
                        for result in limited_results:
                            if str(result.url) in scraped_map:
                                result.scraped_content = scraped_map[str(result.url)]
                                
                    return limited_results
                    
                except Exception as e:
                    logger.error("batch_search_query_error", query=query, error=str(e))
                    errors[query] = str(e)
                    return []
                    
        # Execute searches in parallel
        tasks = [search_single_query(query) for query in request_data.queries]
        search_results = await asyncio.gather(*tasks)

        # Map results to queries and attach citation envelopes
        api_key_id_str = str(auth_user.api_key_id) if auth_user and auth_user.api_key_id else None
        for query, query_results in zip(request_data.queries, search_results):
            if query not in errors:
                for result in query_results:
                    envelope = await envelope_for_result(
                        store=citation_store,
                        url=str(result.url),
                        snippet=result.snippet or "",
                        engine=result.engine,
                        scraped_content=result.scraped_content,
                        api_key_id=api_key_id_str,
                        request_id=batch_id,
                    )
                    if envelope:
                        result.citation_envelope = envelope
                        if result.scraped_content:
                            result.scraped_content.citation_envelope = envelope
                results[query] = query_results
                
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Log batch request
        background_tasks.add_task(
            db.log_search_request,
            {
                "query": f"BATCH:{len(request_data.queries)} queries",
                "engines": request_data.engines,
                "max_results": request_data.max_results_per_query,
                "request_id": batch_id
            },
            None,
            auth_user.api_key_id if auth_user else None,
            client_info["client_ip"],
            client_info["user_agent"]
        )
        
        # Track usage for batch (count each query)
        if auth_user:
            # For sandbox agents, increment daily counter for each query
            if auth_user.is_agent_placeholder:
                # Each query counts as one search for sandbox
                for _ in range(len(results)):
                    background_tasks.add_task(
                        increment_sandbox_usage,
                        auth_user,
                        db
                    )
            else:
                # Regular users - track monthly usage
                background_tasks.add_task(
                    track_usage,
                    user_id=auth_user.user_id,
                    search_count=len(results),
                    engine=request_data.engines[0] if request_data.engines else "searxng"
                )
        
        return BatchSearchResponse(
            batch_id=batch_id,
            queries_processed=len(results),
            queries_failed=len(errors),
            results=results,
            processing_time_ms=processing_time_ms,
            errors=errors
        )
        
    except Exception as e:
        logger.error("batch_search_error", batch_id=batch_id, error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch search failed: {str(e)}"
        )


@router.get("/engines", response_model=EnginesListResponse)
async def list_engines(
    searxng: SearxngDep,
    api_key_id: ApiKeyDep
):
    """
    List available search engines.
    
    Returns information about all configured search engines including their
    capabilities and current status.
    """
    try:
        engines = await searxng.get_available_engines()
        
        return EnginesListResponse(
            engines=engines,
            total_engines=len(engines),
            enabled_engines=sum(1 for e in engines.values() if e.enabled)
        )
        
    except Exception as e:
        logger.error("list_engines_error", error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list engines: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: SettingsDep,
    searxng: SearxngDep,
    cache: CacheDep,
    db: DatabaseDep
):
    """
    Health check endpoint.
    
    Checks the health of all service dependencies.
    """
    start_time = datetime.utcnow()
    
    # Check SearXNG
    searxng_health = await searxng.health_check()
    
    # Check Redis
    cache_start = asyncio.get_event_loop().time()
    try:
        await cache._client.ping()
        cache_health = ServiceHealth(
            status="healthy",
            latency_ms=int((asyncio.get_event_loop().time() - cache_start) * 1000),
            last_check=datetime.utcnow()
        )
    except Exception as e:
        cache_health = ServiceHealth(
            status="unhealthy",
            latency_ms=int((asyncio.get_event_loop().time() - cache_start) * 1000),
            last_check=datetime.utcnow(),
            details={"error": str(e)}
        )
        
    # Check Database
    db_start = asyncio.get_event_loop().time()
    try:
        async with db.get_session() as session:
            await session.execute("SELECT 1")
        db_health = ServiceHealth(
            status="healthy",
            latency_ms=int((asyncio.get_event_loop().time() - db_start) * 1000),
            last_check=datetime.utcnow()
        )
    except Exception as e:
        db_health = ServiceHealth(
            status="unhealthy",
            latency_ms=int((asyncio.get_event_loop().time() - db_start) * 1000),
            last_check=datetime.utcnow(),
            details={"error": str(e)}
        )

    # Check Puppeteer (if enabled)
    puppeteer_health = ServiceHealth(
        status="degraded",
        latency_ms=0,
        last_check=datetime.utcnow(),
        details={"enabled": False}
    )
    if getattr(settings, 'puppeteer_enabled', False) and settings.puppeteer_service_url:
        pupp_start = asyncio.get_event_loop().time()
        try:
            base = str(settings.puppeteer_service_url).rstrip('/')
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                # Try /health then fallback to /
                tried = False
                for path in ("/health", "/"):
                    try:
                        resp = await client.get(base + path)
                        resp.raise_for_status()
                        tried = True
                        break
                    except Exception:
                        continue
                status_ok = tried
            puppeteer_health = ServiceHealth(
                status="healthy" if status_ok else "unhealthy",
                latency_ms=int((asyncio.get_event_loop().time() - pupp_start) * 1000),
                last_check=datetime.utcnow(),
                details={"url": base}
            )
        except Exception as e:
            puppeteer_health = ServiceHealth(
                status="unhealthy",
                latency_ms=int((asyncio.get_event_loop().time() - pupp_start) * 1000),
                last_check=datetime.utcnow(),
                details={"error": str(e), "url": str(settings.puppeteer_service_url)}
            )
        
    # Determine overall status
    services = {
        "searxng": searxng_health,
        "redis": cache_health,
        "database": db_health,
        "puppeteer": puppeteer_health
    }
    
    unhealthy_count = sum(1 for s in services.values() if s.status == "unhealthy")
    
    if unhealthy_count == 0:
        overall_status = "healthy"
    elif unhealthy_count < len(services):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
        
    uptime_seconds = int((datetime.utcnow() - start_time).total_seconds())
    
    return HealthResponse(
        status=overall_status,
        version=settings.version,
        environment=settings.environment,
        services=services,
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime_seconds
    )
