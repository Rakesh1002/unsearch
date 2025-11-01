"""
Advanced API endpoints with Firecrawl-inspired functionality.

Provides cutting-edge features including:
- Multi-engine scraping with intelligent fallback
- Multi-provider search with automatic failover
- LLM-powered configuration generation
- Multi-entity extraction with relationship mapping
- Advanced batch processing operations
"""

import asyncio
import json
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, status, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
import structlog

from app.models.requests import ScrapingConfig
from app.models.responses import UnQuestResponse, AsyncTaskResponse, SearchResult
from app.api.dependencies import (
    ApiKeyDep, SettingsDep, DatabaseDep, 
    CacheDep, ClientInfoDep
)
from app.services.multi_search import get_multi_search_service, SearchOptions
from app.services.multi_engine_scraper import get_multi_engine_service, EngineType
from app.services.llm_configuration import get_llm_config_service, generate_config_from_prompt
from app.services.batch_operations import get_batch_service
from app.services.multi_entity_extraction import (
    get_multi_entity_service, 
    MultiEntityExtractionRequest,
    ExtractionStrategy
)
from app.services.actions_system import get_actions_service, execute_browser_actions
from app.services.website_mapping import get_website_mapper, MapOptions, MapStrategy
from app.services.change_tracking import get_change_tracking_service, ChangeTrackingConfig
from app.services.attributes_extraction import get_attributes_extractor, AttributeExtractionRule, AttributeProcessingType

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v2/advanced", tags=["advanced-features"])


# Request/Response Models

# Actions System Models
class ActionRequest(BaseModel):
    """Single browser action request."""
    type: str = Field(..., description="Action type (wait, click, scroll, write, press, screenshot, scrape, executeJavascript, pdf)")
    # Action-specific fields (will be validated by the actions system)
    milliseconds: Optional[int] = Field(None, description="Wait time in milliseconds (for wait actions)")
    selector: Optional[str] = Field(None, description="CSS selector (for click, scroll, wait actions)")
    text: Optional[str] = Field(None, description="Text to write (for write actions)")
    key: Optional[str] = Field(None, description="Key to press (for press actions)")
    script: Optional[str] = Field(None, description="JavaScript to execute")
    fullPage: Optional[bool] = Field(False, description="Full page screenshot")
    quality: Optional[int] = Field(None, ge=1, le=100, description="Screenshot quality")
    direction: Optional[str] = Field("down", description="Scroll direction")
    all: Optional[bool] = Field(False, description="Click all matching elements")

class BrowserActionsRequest(BaseModel):
    """Request for browser actions sequence."""
    url: str = Field(..., description="URL to navigate to")
    actions: List[ActionRequest] = Field(..., description="Sequence of actions to perform")
    browser_options: Optional[Dict[str, Any]] = Field(None, description="Browser configuration options")

# Website Mapping Models  
class WebsiteMapRequest(BaseModel):
    """Request for website mapping."""
    url: str = Field(..., description="Website URL to map")
    strategy: str = Field("combined", description="Mapping strategy (sitemap_only, search_engine, combined, crawl_based)")
    limit: int = Field(1000, ge=1, le=10000, description="Maximum URLs to return")
    include_subdomains: bool = Field(True, description="Include subdomains")
    allow_external_links: bool = Field(False, description="Allow external links")
    search_query: Optional[str] = Field(None, description="Search query for filtering")
    ignore_sitemap: bool = Field(False, description="Ignore sitemap")
    filter_by_path: bool = Field(True, description="Filter by URL path")
    timeout: int = Field(30, ge=5, le=120, description="Request timeout")
    max_depth: int = Field(3, ge=1, le=10, description="Maximum crawl depth")

# Change Tracking Models
class ChangeTrackingRequest(BaseModel):
    """Request for change tracking."""
    url: str = Field(..., description="URL to track changes for")
    tag: Optional[str] = Field(None, description="Tag for grouping tracked content")
    threshold: float = Field(0.05, ge=0.0, le=1.0, description="Minimum change percentage to trigger notification")
    compare_text: bool = Field(True, description="Compare text content")
    compare_html: bool = Field(True, description="Compare HTML content")
    compare_metadata: bool = Field(True, description="Compare metadata")
    notification_webhook: Optional[str] = Field(None, description="Webhook URL for notifications")
    store_history: bool = Field(True, description="Store change history")

# Attributes Extraction Models
class AttributeExtractionRuleRequest(BaseModel):
    """Single attribute extraction rule."""
    selector: str = Field(..., description="CSS selector")
    attribute: str = Field(..., description="HTML attribute to extract")
    processing: str = Field("cleaned", description="Processing type (raw, cleaned, urls_resolved, numeric, boolean, list)")
    filter_empty: bool = Field(True, description="Filter empty values")
    filter_duplicates: bool = Field(True, description="Filter duplicate values")
    limit: Optional[int] = Field(None, description="Maximum elements to process")
    transform: Optional[str] = Field(None, description="Transform function")
    validation_pattern: Optional[str] = Field(None, description="Validation regex pattern")

class AttributesExtractionRequest(BaseModel):
    """Request for attributes extraction."""
    url: str = Field(..., description="URL to extract attributes from")
    rules: List[AttributeExtractionRuleRequest] = Field(..., description="Extraction rules")
    base_url: Optional[str] = Field(None, description="Base URL for URL resolution")
    include_element_context: bool = Field(True, description="Include element context")
    max_elements_per_selector: int = Field(1000, ge=1, le=10000, description="Max elements per selector")
    resolve_relative_urls: bool = Field(True, description="Resolve relative URLs")

# Combined Request Models
class AdvancedScrapeRequest(BaseModel):
    """Advanced scraping request with all features."""
    url: str = Field(..., description="URL to scrape")
    actions: Optional[List[ActionRequest]] = Field(None, description="Browser actions to perform before scraping")
    change_tracking: Optional[ChangeTrackingRequest] = Field(None, description="Change tracking configuration")
    attributes_extraction: Optional[AttributesExtractionRequest] = Field(None, description="Attributes extraction configuration")
    scraping_config: Optional[ScrapingConfig] = Field(None, description="Scraping configuration")
    engine: Optional[str] = Field(None, description="Preferred scraping engine")
class MultiProviderSearchRequest(BaseModel):
    """Request for multi-provider search."""
    query: str = Field(..., description="Search query")
    num_results: int = Field(10, ge=1, le=100, description="Number of results")
    lang: str = Field("en", description="Language code")
    country: str = Field("us", description="Country code")
    location: Optional[str] = Field(None, description="Location for search")
    tbs: Optional[str] = Field(None, description="Time-based search filter")
    filter: Optional[str] = Field(None, description="Search filter")
    advanced: bool = Field(False, description="Enable advanced search")
    scrape_results: bool = Field(False, description="Scrape search results")
    scrape_config: Optional[Dict[str, Any]] = Field(None, description="Scraping configuration")


class MultiEngineScrapingRequest(BaseModel):
    """Request for multi-engine scraping."""
    urls: List[str] = Field(..., description="URLs to scrape")
    preferred_engine: Optional[str] = Field(None, description="Preferred scraping engine")
    required_capabilities: List[str] = Field(default_factory=list, description="Required engine capabilities")
    config: Optional[ScrapingConfig] = Field(None, description="Scraping configuration")
    timeout: int = Field(30, ge=5, le=300, description="Timeout per URL in seconds")


class LLMConfigurationRequest(BaseModel):
    """Request for LLM-powered configuration generation."""
    prompt: str = Field(..., description="Natural language configuration prompt")
    config_type: str = Field(..., description="Type of configuration (crawler|extraction|filter|search)")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class BatchOperationRequest(BaseModel):
    """Request for batch operations."""
    operation_type: str = Field(..., description="Type of batch operation (scrape|search|extract)")
    urls: List[str] = Field(..., description="URLs or queries to process")
    config: Optional[Dict[str, Any]] = Field(None, description="Operation configuration")
    priority: int = Field(10, ge=1, le=100, description="Job priority (lower = higher priority)")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for status updates")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MultiEntityExtractionRequestModel(BaseModel):
    """Request for multi-entity extraction."""
    urls: List[str] = Field(..., description="URLs to extract entities from")
    schema: Dict[str, Any] = Field(..., description="JSON schema for extraction")
    extraction_strategy: str = Field("linked_entities", description="Extraction strategy")
    max_related_urls: int = Field(50, ge=1, le=200, description="Maximum related URLs to discover")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")
    cross_validate: bool = Field(True, description="Enable cross-validation")
    follow_links: bool = Field(True, description="Follow links to discover related URLs")
    max_depth: int = Field(2, ge=1, le=5, description="Maximum crawl depth")


# API Endpoints

@router.post("/search/multi-provider")
async def multi_provider_search(
    request_data: MultiProviderSearchRequest,
    request: Request,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    db: DatabaseDep,
    cache: CacheDep,
    client_info: ClientInfoDep
):
    """
    Advanced multi-provider search with intelligent fallback.
    
    Uses multiple search providers with automatic failover:
    - Fire Engine (if available)
    - Serper API (if configured)
    - SearchAPI (if configured) 
    - SearXNG (if configured)
    - Google (fallback)
    
    Optional result scraping with multi-engine support.
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info("multi_provider_search_started", 
                   request_id=request_id,
                   query=request_data.query,
                   scrape_results=request_data.scrape_results)
        
        # Perform multi-provider search
        search_service = await get_multi_search_service()
        search_options = SearchOptions(
            query=request_data.query,
            num_results=request_data.num_results,
            lang=request_data.lang,
            country=request_data.country,
            location=request_data.location,
            tbs=request_data.tbs,
            filter=request_data.filter,
            advanced=request_data.advanced
        )
        
        search_results = await search_service.search(search_options)
        
        # Optionally scrape search results
        scraped_results = []
        if request_data.scrape_results and search_results:
            urls_to_scrape = [result.url for result in search_results]
            
            # Use multi-engine scraping for results
            engine_service = await get_multi_engine_service()
            
            scrape_config = ScrapingConfig(**(request_data.scrape_config or {}))
            
            for url in urls_to_scrape:
                try:
                    scrape_result = await engine_service.scrape(url, scrape_config)
                    if scrape_result.success:
                        scraped_results.append({
                            "url": url,
                            "content": scrape_result.content.dict(),
                            "engine_used": scrape_result.engine_used.value,
                            "processing_time": scrape_result.processing_time
                        })
                except Exception as e:
                    logger.warning("scraping_search_result_failed", url=url, error=str(e))
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        # Prepare response
        response_data = {
            "request_id": request_id,
            "query": request_data.query,
            "search_results": [result.dict() for result in search_results],
            "scraped_results": scraped_results,
            "metadata": {
                "total_results": len(search_results),
                "scraped_count": len(scraped_results),
                "processing_time_ms": int(processing_time * 1000),
                "search_providers_available": await search_service.get_provider_stats()
            }
        }
        
        logger.info("multi_provider_search_completed",
                   request_id=request_id,
                   results_count=len(search_results),
                   scraped_count=len(scraped_results),
                   processing_time=processing_time)
        
        return response_data
        
    except Exception as e:
        logger.error("multi_provider_search_failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-provider search failed: {str(e)}"
        )


@router.post("/scrape/multi-engine")
async def multi_engine_scraping(
    request_data: MultiEngineScrapingRequest,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
):
    """
    Advanced multi-engine scraping with intelligent engine selection.
    
    Automatically selects the best scraping engine based on:
    - Content type detection
    - Required capabilities
    - Engine availability and performance
    - Fallback strategies
    
    Available engines:
    - Index (cached content)
    - Fire Engine variants (Chrome CDP, Playwright, TLS Client)
    - Playwright service
    - Basic fetch (fallback)
    - PDF/DOCX processors
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info("multi_engine_scraping_started",
                   request_id=request_id,
                   urls=len(request_data.urls),
                   preferred_engine=request_data.preferred_engine)
        
        engine_service = await get_multi_engine_service()
        
        # Convert preferred engine string to enum if provided
        preferred_engine = None
        if request_data.preferred_engine:
            try:
                preferred_engine = EngineType(request_data.preferred_engine)
            except ValueError:
                logger.warning("invalid_preferred_engine", engine=request_data.preferred_engine)
        
        # Process each URL
        results = []
        for url in request_data.urls:
            try:
                scrape_result = await engine_service.scrape(
                    url=url,
                    config=request_data.config or ScrapingConfig(urls=[]),
                    preferred_engine=preferred_engine,
                    required_capabilities=request_data.required_capabilities
                )
                
                results.append({
                    "url": url,
                    "success": scrape_result.success,
                    "content": scrape_result.content.dict() if scrape_result.success else None,
                    "engine_used": scrape_result.engine_used.value,
                    "processing_time": scrape_result.processing_time,
                    "attempts": scrape_result.attempts,
                    "error": scrape_result.error
                })
                
            except Exception as e:
                logger.error("url_scraping_failed", url=url, error=str(e))
                results.append({
                    "url": url,
                    "success": False,
                    "content": None,
                    "engine_used": "none",
                    "processing_time": 0,
                    "attempts": 0,
                    "error": str(e)
                })
        
        processing_time = asyncio.get_event_loop().time() - start_time
        successful_results = [r for r in results if r["success"]]
        
        # Get engine statistics
        engine_stats = await engine_service.get_engine_stats()
        
        response_data = {
            "request_id": request_id,
            "results": results,
            "metadata": {
                "total_urls": len(request_data.urls),
                "successful_scrapes": len(successful_results),
                "failed_scrapes": len(results) - len(successful_results),
                "processing_time_ms": int(processing_time * 1000),
                "engine_statistics": engine_stats
            }
        }
        
        logger.info("multi_engine_scraping_completed",
                   request_id=request_id,
                   successful=len(successful_results),
                   failed=len(results) - len(successful_results),
                   processing_time=processing_time)
        
        return response_data
        
    except Exception as e:
        logger.error("multi_engine_scraping_failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-engine scraping failed: {str(e)}"
        )


@router.post("/config/generate")
async def generate_configuration(
    request_data: LLMConfigurationRequest,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
):
    """
    Generate configuration from natural language using LLM.
    
    Converts natural language descriptions into structured configurations:
    - Crawler options and settings
    - Data extraction schemas
    - Content filtering rules
    - Search strategies
    
    Example prompts:
    - "Crawl a blog site and extract only the article pages"
    - "Extract product information including name, price, and reviews"
    - "Filter content to only include technical articles about AI"
    - "Search for recent news articles from reliable sources"
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info("llm_configuration_started",
                   request_id=request_id,
                   config_type=request_data.config_type,
                   prompt_length=len(request_data.prompt))
        
        # Generate configuration using LLM
        config = await generate_config_from_prompt(
            prompt=request_data.prompt,
            config_type=request_data.config_type,
            context=request_data.context
        )
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        # Get LLM service stats
        llm_service = await get_llm_config_service()
        usage_stats = await llm_service.get_usage_stats()
        
        response_data = {
            "request_id": request_id,
            "config_type": request_data.config_type,
            "generated_config": config,
            "metadata": {
                "processing_time_ms": int(processing_time * 1000),
                "prompt_length": len(request_data.prompt),
                "config_fields_generated": len(config) if isinstance(config, dict) else 0,
                "llm_usage_stats": usage_stats
            }
        }
        
        logger.info("llm_configuration_completed",
                   request_id=request_id,
                   config_fields=len(config) if isinstance(config, dict) else 0,
                   processing_time=processing_time)
        
        return response_data
        
    except Exception as e:
        logger.error("llm_configuration_failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM configuration generation failed: {str(e)}"
        )


@router.post("/batch/submit")
async def submit_batch_operation(
    request_data: BatchOperationRequest,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
):
    """
    Submit advanced batch operation.
    
    Supports various batch operations:
    - Batch scraping with intelligent resource management
    - Batch search across multiple providers
    - Batch extraction with entity linking
    
    Features:
    - Intelligent job scheduling and prioritization
    - Progress tracking and status updates
    - Error handling and retry logic
    - Webhook notifications
    - Job pause/resume/cancel capabilities
    """
    try:
        logger.info("batch_operation_submitted",
                   operation_type=request_data.operation_type,
                   urls=len(request_data.urls),
                   priority=request_data.priority)
        
        batch_service = await get_batch_service()
        
        # Submit appropriate batch operation
        if request_data.operation_type == "scrape":
            # Convert config to ScrapingConfig if provided
            scrape_config = None
            if request_data.config:
                scrape_config = ScrapingConfig(**request_data.config)
            
            job_id = await batch_service.submit_batch_scrape(
                urls=request_data.urls,
                config=scrape_config,
                priority=request_data.priority,
                webhook_url=request_data.webhook_url,
                metadata=request_data.metadata
            )
            
        elif request_data.operation_type == "search":
            job_id = await batch_service.submit_batch_search(
                queries=request_data.urls,  # Using URLs field for queries
                search_config=request_data.config,
                priority=request_data.priority,
                webhook_url=request_data.webhook_url,
                metadata=request_data.metadata
            )
            
        else:
            raise ValueError(f"Unsupported operation type: {request_data.operation_type}")
        
        # Get initial job status
        job_status = await batch_service.get_job_status(job_id)
        
        response_data = {
            "job_id": job_id,
            "operation_type": request_data.operation_type,
            "status": job_status.status.value if job_status else "unknown",
            "urls_count": len(request_data.urls),
            "priority": request_data.priority,
            "webhook_url": request_data.webhook_url,
            "estimated_completion": None,  # Will be updated as job progresses
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info("batch_operation_accepted",
                   job_id=job_id,
                   operation_type=request_data.operation_type)
        
        return response_data
        
    except Exception as e:
        logger.error("batch_operation_submission_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch operation submission failed: {str(e)}"
        )


@router.get("/batch/{job_id}/status")
async def get_batch_status(
    job_id: str,
    api_key_id: ApiKeyDep,
    settings: SettingsDep
):
    """Get status of batch operation."""
    try:
        batch_service = await get_batch_service()
        job_status = await batch_service.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        response_data = {
            "job_id": job_status.job_id,
            "status": job_status.status.value,
            "progress": {
                "total_urls": job_status.progress.total_urls if job_status.progress else 0,
                "completed_urls": job_status.progress.completed_urls if job_status.progress else 0,
                "failed_urls": job_status.progress.failed_urls if job_status.progress else 0,
                "skipped_urls": job_status.progress.skipped_urls if job_status.progress else 0,
                "completion_percentage": job_status.progress.completion_percentage if job_status.progress else 0,
                "estimated_completion": job_status.progress.estimated_completion.isoformat() if job_status.progress and job_status.progress.estimated_completion else None,
                "current_url": job_status.progress.current_url if job_status.progress else None
            },
            "results_count": len(job_status.results),
            "errors_count": len(job_status.errors),
            "metadata": job_status.metadata,
            "created_at": job_status.created_at.isoformat() if job_status.created_at else None,
            "updated_at": job_status.updated_at.isoformat() if job_status.updated_at else None
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("batch_status_failed", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get batch status: {str(e)}"
        )


@router.post("/batch/{job_id}/control")
async def control_batch_operation(
    job_id: str,
    action: str = Query(..., description="Action to perform (pause|resume|cancel)"),
    api_key_id: ApiKeyDep,
    settings: SettingsDep
):
    """Control batch operation (pause, resume, cancel)."""
    try:
        batch_service = await get_batch_service()
        
        result = False
        if action == "pause":
            result = await batch_service.pause_job(job_id)
        elif action == "resume":
            result = await batch_service.resume_job(job_id)
        elif action == "cancel":
            result = await batch_service.cancel_job(job_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}. Use pause, resume, or cancel."
            )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found or action not allowed"
            )
        
        return {
            "job_id": job_id,
            "action": action,
            "success": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("batch_control_failed", job_id=job_id, action=action, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control batch operation: {str(e)}"
        )


@router.post("/extract/multi-entity")
async def multi_entity_extraction(
    request_data: MultiEntityExtractionRequestModel,
    api_key_id: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
):
    """
    Advanced multi-entity extraction with relationship mapping.
    
    Performs sophisticated cross-URL data extraction:
    - Discovers related URLs through various strategies
    - Extracts entities using multiple methods (LLM, regex, CSS)
    - Maps relationships between entities
    - Validates data through cross-referencing
    - Provides comprehensive entity analytics
    
    Extraction strategies:
    - linked_entities: Extract entities and find related URLs
    - hierarchical: Follow hierarchical relationships
    - semantic_similarity: Group by semantic similarity
    - temporal_sequence: Time-based entity relationships
    - cross_reference: Cross-reference validation
    """
    start_time = asyncio.get_event_loop().time()
    request_id = str(uuid.uuid4())
    
    try:
        logger.info("multi_entity_extraction_started",
                   request_id=request_id,
                   urls=len(request_data.urls),
                   strategy=request_data.extraction_strategy)
        
        # Convert string strategy to enum
        try:
            strategy = ExtractionStrategy(request_data.extraction_strategy)
        except ValueError:
            strategy = ExtractionStrategy.LINKED_ENTITIES
        
        # Create extraction request
        extraction_request = MultiEntityExtractionRequest(
            urls=request_data.urls,
            schema=request_data.schema,
            extraction_strategy=strategy,
            max_related_urls=request_data.max_related_urls,
            similarity_threshold=request_data.similarity_threshold,
            cross_validate=request_data.cross_validate,
            follow_links=request_data.follow_links,
            max_depth=request_data.max_depth
        )
        
        # Perform extraction
        extraction_service = await get_multi_entity_service()
        result = await extraction_service.extract_multi_entity(extraction_request)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        # Prepare response
        response_data = {
            "request_id": result.request_id,
            "success": result.success,
            "entities": [
                {
                    "id": entity.id,
                    "type": entity.entity_type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "source_url": entity.source_url,
                    "extraction_method": entity.extraction_method,
                    "context": entity.context,
                    "attributes": entity.attributes,
                    "related_entities": entity.related_entities
                }
                for entity in result.entities
            ],
            "relationships": [
                {
                    "source_url": rel.source_url,
                    "target_url": rel.target_url,
                    "relation_type": rel.relation_type,
                    "confidence": rel.confidence,
                    "evidence": rel.evidence
                }
                for rel in result.relations
            ],
            "discovered_urls": result.discovered_urls,
            "validation_results": result.validation_results,
            "extraction_metadata": result.extraction_metadata,
            "processing_time": result.processing_time,
            "errors": result.errors
        }
        
        logger.info("multi_entity_extraction_completed",
                   request_id=request_id,
                   entities_extracted=len(result.entities),
                   relationships_found=len(result.relations),
                   urls_discovered=len(result.discovered_urls),
                   processing_time=processing_time)
        
        return response_data
        
    except Exception as e:
        logger.error("multi_entity_extraction_failed", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-entity extraction failed: {str(e)}"
        )


@router.get("/stats/comprehensive")
async def get_comprehensive_stats(
    api_key_id: ApiKeyDep,
    settings: SettingsDep
):
    """Get comprehensive statistics for all advanced services."""
    try:
        stats = {}
        
        # Multi-search service stats
        try:
            search_service = await get_multi_search_service()
            stats["multi_search"] = await search_service.get_provider_stats()
        except Exception as e:
            stats["multi_search"] = {"error": str(e)}
        
        # Multi-engine scraping stats
        try:
            engine_service = await get_multi_engine_service()
            stats["multi_engine_scraping"] = await engine_service.get_engine_stats()
        except Exception as e:
            stats["multi_engine_scraping"] = {"error": str(e)}
        
        # LLM configuration stats
        try:
            llm_service = await get_llm_config_service()
            stats["llm_configuration"] = await llm_service.get_usage_stats()
        except Exception as e:
            stats["llm_configuration"] = {"error": str(e)}
        
        # Batch operations stats
        try:
            batch_service = await get_batch_service()
            stats["batch_operations"] = await batch_service.get_service_stats()
        except Exception as e:
            stats["batch_operations"] = {"error": str(e)}
        
        # Multi-entity extraction stats
        try:
            extraction_service = await get_multi_entity_service()
            stats["multi_entity_extraction"] = await extraction_service.get_extraction_stats()
        except Exception as e:
            stats["multi_entity_extraction"] = {"error": str(e)}
        
        # Actions system stats
        try:
            actions_service = await get_actions_service()
            stats["actions_system"] = await actions_service.get_actions_stats()
        except Exception as e:
            stats["actions_system"] = {"error": str(e)}
        
        # Website mapping stats
        try:
            mapping_service = await get_website_mapper()
            stats["website_mapping"] = await mapping_service.get_mapping_stats()
        except Exception as e:
            stats["website_mapping"] = {"error": str(e)}
        
        # Change tracking stats
        try:
            tracking_service = await get_change_tracking_service()
            stats["change_tracking"] = await tracking_service.get_tracking_stats()
        except Exception as e:
            stats["change_tracking"] = {"error": str(e)}
        
        # Attributes extraction stats
        try:
            attributes_service = await get_attributes_extractor()
            stats["attributes_extraction"] = await attributes_service.get_extraction_stats()
        except Exception as e:
            stats["attributes_extraction"] = {"error": str(e)}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": stats
        }
        
    except Exception as e:
        logger.error("comprehensive_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comprehensive stats: {str(e)}"
        )


@router.get("/health/advanced")
async def advanced_health_check():
    """Health check for advanced services."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Check each service
        services_to_check = [
            ("multi_search", get_multi_search_service),
            ("multi_engine_scraping", get_multi_engine_service),
            ("llm_configuration", get_llm_config_service),
            ("batch_operations", get_batch_service),
            ("multi_entity_extraction", get_multi_entity_service),
            ("actions_system", get_actions_service),
            ("website_mapping", get_website_mapper),
            ("change_tracking", get_change_tracking_service),
            ("attributes_extraction", get_attributes_extractor)
        ]
        
        for service_name, service_getter in services_to_check:
            try:
                service = await service_getter()
                health_status["services"][service_name] = {
                    "status": "healthy",
                    "initialized": service is not None
                }
            except Exception as e:
                health_status["services"][service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        # Return appropriate status code
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return JSONResponse(
            content=health_status,
            status_code=status_code
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@router.post("/actions/execute", summary="Execute Browser Actions", status_code=status.HTTP_200_OK)
async def execute_browser_actions_endpoint(
    request: BrowserActionsRequest,
    api_key: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
) -> UnQuestResponse:
    """
    Execute a sequence of browser actions on a webpage.
    
    Supports all Firecrawl action types:
    - wait: Wait for time or element
    - click: Click elements
    - scroll: Scroll page
    - write: Type text
    - press: Press keys
    - screenshot: Capture screenshots
    - scrape: Extract page content
    - executeJavascript: Run JavaScript
    - pdf: Generate PDF
    """
    try:
        logger.info("browser_actions_execution_started", 
                   url=request.url, 
                   actions_count=len(request.actions),
                   client_info=client_info)
        
        # Convert request actions to dict format
        actions_dicts = [action.dict(exclude_none=True) for action in request.actions]
        
        # Execute actions
        result = await execute_browser_actions(
            url=request.url,
            actions=actions_dicts,
            browser_options=request.browser_options
        )
        
        if result.success:
            return UnQuestResponse(
                success=True,
                data={
                    "actions_results": [
                        {
                            "action_type": ar.action_type,
                            "success": ar.success,
                            "data": ar.data,
                            "execution_time_ms": ar.execution_time_ms,
                            "error": ar.error
                        }
                        for ar in result.actions_results
                    ],
                    "screenshots": result.screenshots,
                    "scrapes": result.scrapes,
                    "javascript_returns": result.javascript_returns,
                    "pdfs": result.pdfs,
                    "total_execution_time_ms": result.total_execution_time_ms
                },
                message=f"Executed {len(request.actions)} actions successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Actions execution failed: {result.error}"
            )
    
    except Exception as e:
        logger.error("browser_actions_execution_failed", 
                    url=request.url, 
                    error=str(e),
                    client_info=client_info)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Actions execution failed: {str(e)}"
        )


@router.post("/map/website", summary="Map Website URLs", status_code=status.HTTP_200_OK)
async def map_website_endpoint(
    request: WebsiteMapRequest,
    api_key: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
) -> UnQuestResponse:
    """
    Discover all URLs from a website using multiple strategies.
    
    Strategies:
    - sitemap_only: Use XML sitemaps only
    - search_engine: Use search engine queries
    - combined: Use both sitemaps and search engines
    - crawl_based: Use web crawling
    """
    try:
        logger.info("website_mapping_started", 
                   url=request.url, 
                   strategy=request.strategy,
                   limit=request.limit,
                   client_info=client_info)
        
        mapper = await get_website_mapper()
        
        # Create mapping options
        map_options = MapOptions(
            strategy=MapStrategy(request.strategy),
            limit=request.limit,
            include_subdomains=request.include_subdomains,
            allow_external_links=request.allow_external_links,
            search_query=request.search_query,
            ignore_sitemap=request.ignore_sitemap,
            filter_by_path=request.filter_by_path,
            timeout=request.timeout,
            max_depth=request.max_depth
        )
        
        # Execute mapping
        result = await mapper.map_website(request.url, map_options)
        
        if result.success:
            return UnQuestResponse(
                success=True,
                data={
                    "base_url": result.base_url,
                    "discovered_urls": [
                        {
                            "url": du.url,
                            "source": du.source,
                            "title": du.title,
                            "description": du.description,
                            "last_modified": du.last_modified,
                            "priority": du.priority,
                            "depth": du.depth
                        }
                        for du in result.discovered_urls
                    ],
                    "total_urls": result.total_urls,
                    "sources_breakdown": result.sources_breakdown,
                    "processing_time_ms": result.processing_time_ms,
                    "metadata": result.metadata
                },
                message=f"Discovered {result.total_urls} URLs from {request.url}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Website mapping failed: {result.error}"
            )
    
    except Exception as e:
        logger.error("website_mapping_failed", 
                    url=request.url, 
                    error=str(e),
                    client_info=client_info)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Website mapping failed: {str(e)}"
        )


@router.post("/track/changes", summary="Track Content Changes", status_code=status.HTTP_200_OK)
async def track_content_changes_endpoint(
    request: ChangeTrackingRequest,
    api_key: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
) -> UnQuestResponse:
    """
    Track changes in website content over time.
    
    Features:
    - Content comparison and diff generation
    - Change percentage calculation
    - Historical tracking
    - Webhook notifications
    """
    try:
        logger.info("change_tracking_started", 
                   url=request.url, 
                   tag=request.tag,
                   threshold=request.threshold,
                   client_info=client_info)
        
        tracking_service = await get_change_tracking_service()
        
        # Create tracking configuration
        config = ChangeTrackingConfig(
            tag=request.tag,
            threshold=request.threshold,
            compare_text=request.compare_text,
            compare_html=request.compare_html,
            compare_metadata=request.compare_metadata,
            notification_webhook=request.notification_webhook,
            store_history=request.store_history
        )
        
        # Execute change tracking
        result = await tracking_service.track_content_changes(request.url, config)
        
        if result.success:
            # Convert scraped content to dict
            scraped_content_dict = result.scraped_content.dict()
            
            return UnQuestResponse(
                success=True,
                data={
                    "url": result.url,
                    "change_tracking": {
                        "previous_scrape_at": result.tracking_data.previous_scrape_at.isoformat() if result.tracking_data.previous_scrape_at else None,
                        "change_status": result.tracking_data.change_status.value,
                        "visibility": result.tracking_data.visibility.value,
                        "change_percentage": result.tracking_data.change_percentage,
                        "significant_changes": result.tracking_data.significant_changes,
                        "diff": {
                            "text": result.tracking_data.diff.text_diff if result.tracking_data.diff else "",
                            "json": result.tracking_data.diff.json_diff if result.tracking_data.diff else {}
                        } if result.tracking_data.diff else None
                    },
                    "scraped_content": scraped_content_dict,
                    "processing_time_ms": result.processing_time_ms
                },
                message=f"Change tracking completed for {request.url} - Status: {result.tracking_data.change_status.value}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Change tracking failed: {result.error}"
            )
    
    except Exception as e:
        logger.error("change_tracking_failed", 
                    url=request.url, 
                    error=str(e),
                    client_info=client_info)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Change tracking failed: {str(e)}"
        )


@router.post("/extract/attributes", summary="Extract HTML Attributes", status_code=status.HTTP_200_OK)
async def extract_attributes_endpoint(
    request: AttributesExtractionRequest,
    api_key: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep
) -> UnQuestResponse:
    """
    Extract specific HTML attributes from webpage elements.
    
    Features:
    - CSS selector-based extraction
    - Multiple processing types (raw, cleaned, urls_resolved, numeric, boolean, list)
    - Advanced filtering and validation
    - Bulk extraction operations
    """
    try:
        logger.info("attributes_extraction_started", 
                   url=request.url, 
                   rules_count=len(request.rules),
                   client_info=client_info)
        
        extractor = await get_attributes_extractor()
        
        # Convert request rules to service format
        from app.services.attributes_extraction import AttributesExtractionConfig
        
        rules = []
        for rule_req in request.rules:
            rules.append(AttributeExtractionRule(
                selector=rule_req.selector,
                attribute=rule_req.attribute,
                processing=AttributeProcessingType(rule_req.processing),
                filter_empty=rule_req.filter_empty,
                filter_duplicates=rule_req.filter_duplicates,
                limit=rule_req.limit,
                transform=rule_req.transform,
                validation_pattern=rule_req.validation_pattern
            ))
        
        config = AttributesExtractionConfig(
            rules=rules,
            base_url=request.base_url,
            include_element_context=request.include_element_context,
            max_elements_per_selector=request.max_elements_per_selector,
            resolve_relative_urls=request.resolve_relative_urls
        )
        
        # Execute extraction
        result = await extractor.extract_attributes(request.url, config)
        
        if result.success:
            return UnQuestResponse(
                success=True,
                data={
                    "url": result.url,
                    "extractions": [
                        {
                            "selector": extraction.selector,
                            "attribute": extraction.attribute,
                            "values": extraction.values,
                            "processed_values": extraction.processed_values,
                            "element_count": extraction.element_count,
                            "results": [
                                {
                                    "element_index": res.element_index,
                                    "raw_value": res.raw_value,
                                    "processed_value": res.processed_value,
                                    "element_text": res.element_text,
                                    "element_tag": res.element_tag,
                                    "element_classes": res.element_classes,
                                    "element_id": res.element_id
                                }
                                for res in extraction.results
                            ] if request.include_element_context else []
                        }
                        for extraction in result.extractions
                    ],
                    "total_attributes_extracted": result.total_attributes_extracted,
                    "total_elements_processed": result.total_elements_processed,
                    "processing_time_ms": result.processing_time_ms,
                    "metadata": result.metadata
                },
                message=f"Extracted {result.total_attributes_extracted} attributes from {result.total_elements_processed} elements"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Attributes extraction failed: {result.error}"
            )
    
    except Exception as e:
        logger.error("attributes_extraction_failed", 
                    url=request.url, 
                    error=str(e),
                    client_info=client_info)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Attributes extraction failed: {str(e)}"
        )


@router.post("/scrape/advanced", summary="Advanced Scraping with All Features", status_code=status.HTTP_200_OK)
async def advanced_scrape_endpoint(
    request: AdvancedScrapeRequest,
    api_key: ApiKeyDep,
    settings: SettingsDep,
    client_info: ClientInfoDep,
    background_tasks: BackgroundTasks
) -> UnQuestResponse:
    """
    Perform advanced scraping with all features combined.
    
    Combines:
    - Browser actions (click, scroll, type, etc.)
    - Change tracking and monitoring
    - Attributes extraction
    - Multi-engine scraping
    """
    try:
        logger.info("advanced_scraping_started", 
                   url=request.url, 
                   features={
                       "actions": bool(request.actions),
                       "change_tracking": bool(request.change_tracking),
                       "attributes": bool(request.attributes_extraction)
                   },
                   client_info=client_info)
        
        results = {"url": request.url}
        
        # 1. Execute browser actions if provided
        if request.actions:
            actions_dicts = [action.dict(exclude_none=True) for action in request.actions]
            actions_result = await execute_browser_actions(
                url=request.url,
                actions=actions_dicts
            )
            results["actions"] = {
                "success": actions_result.success,
                "screenshots": actions_result.screenshots,
                "scrapes": actions_result.scrapes,
                "total_execution_time_ms": actions_result.total_execution_time_ms
            }
        
        # 2. Perform standard scraping
        from app.services.enhanced_scraping import get_enhanced_scraping_service
        scraping_service = await get_enhanced_scraping_service()
        
        scraping_config = request.scraping_config or ScrapingConfig()
        scrape_results = await scraping_service.scrape_urls_enhanced(
            [request.url], 
            config=scraping_config
        )
        
        if scrape_results:
            results["scraped_content"] = scrape_results[0].dict()
        
        # 3. Track changes if requested
        if request.change_tracking:
            tracking_service = await get_change_tracking_service()
            config = ChangeTrackingConfig(
                tag=request.change_tracking.tag,
                threshold=request.change_tracking.threshold,
                compare_text=request.change_tracking.compare_text,
                compare_html=request.change_tracking.compare_html,
                notification_webhook=request.change_tracking.notification_webhook
            )
            
            tracking_result = await tracking_service.track_content_changes(request.url, config)
            results["change_tracking"] = {
                "change_status": tracking_result.tracking_data.change_status.value,
                "change_percentage": tracking_result.tracking_data.change_percentage,
                "significant_changes": tracking_result.tracking_data.significant_changes
            }
        
        # 4. Extract attributes if requested
        if request.attributes_extraction:
            extractor = await get_attributes_extractor()
            
            from app.services.attributes_extraction import AttributesExtractionConfig
            
            rules = []
            for rule_req in request.attributes_extraction.rules:
                rules.append(AttributeExtractionRule(
                    selector=rule_req.selector,
                    attribute=rule_req.attribute,
                    processing=AttributeProcessingType(rule_req.processing)
                ))
            
            config = AttributesExtractionConfig(rules=rules)
            extraction_result = await extractor.extract_attributes(request.url, config)
            
            results["attributes"] = {
                "total_attributes_extracted": extraction_result.total_attributes_extracted,
                "extractions": [
                    {
                        "selector": ext.selector,
                        "attribute": ext.attribute,
                        "values": ext.values[:10]  # Limit to first 10 values
                    }
                    for ext in extraction_result.extractions
                ]
            }
        
        return UnQuestResponse(
            success=True,
            data=results,
            message="Advanced scraping completed successfully"
        )
    
    except Exception as e:
        logger.error("advanced_scraping_failed", 
                    url=request.url, 
                    error=str(e),
                    client_info=client_info)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Advanced scraping failed: {str(e)}"
        )
