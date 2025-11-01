"""
AI-powered data extraction service inspired by Firecrawl's Extract feature.

Provides comprehensive AI extraction capabilities:
- Natural language prompt-based extraction
- JSON schema-driven structured extraction
- Multi-URL and domain-wide extraction
- Web search augmentation
- Source mapping and citation
- Advanced agent configuration
"""

import asyncio
import time
import json
import uuid
from typing import Dict, List, Optional, Any, Union, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import structlog

from app.config import get_settings
from app.models.responses import ScrapedContent
from app.services.enhanced_scraping import get_enhanced_scraping_service
from app.services.multi_search import get_multi_search_service, SearchOptions
from app.services.website_mapping import get_website_mapper, MapOptions, MapStrategy
from app.services.llm_configuration import get_llm_config_service

logger = structlog.get_logger(__name__)
settings = get_settings()


class AgentModel(Enum):
    """Available LLM models for extraction."""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"


class ExtractionStatus(Enum):
    """Status of extraction operation."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for extraction agent."""
    model: AgentModel = AgentModel.GPT_4
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    session_id: Optional[str] = None
    custom_instructions: Optional[str] = None


@dataclass
class ExtractionSource:
    """Source information for extracted data."""
    url: str
    title: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 1.0
    extraction_method: str = "llm"


@dataclass
class ExtractedData:
    """Container for extracted structured data."""
    data: Any
    sources: List[ExtractionSource] = field(default_factory=list)
    confidence_score: float = 1.0
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionRequest:
    """Request for AI-powered extraction."""
    # Input URLs (optional if using web search)
    urls: Optional[List[str]] = None
    
    # Extraction configuration
    prompt: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    
    # Search and discovery options
    enable_web_search: bool = False
    search_query: Optional[str] = None
    allow_external_links: bool = False
    include_subdomains: bool = True
    
    # Processing options
    show_sources: bool = True
    ignore_invalid_urls: bool = True
    max_urls: int = 100
    
    # Agent configuration
    agent: Optional[AgentConfig] = None
    
    # Advanced options
    integration: Optional[str] = None
    webhook_url: Optional[str] = None
    timeout: int = 300  # 5 minutes default


@dataclass
class ExtractionJob:
    """Represents an extraction job."""
    id: str
    request: ExtractionRequest
    status: ExtractionStatus = ExtractionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    total_urls: int = 0
    processed_urls: int = 0
    error: Optional[str] = None
    result: Optional[ExtractedData] = None


@dataclass
class ExtractionResponse:
    """Response from extraction operation."""
    success: bool
    job_id: str
    status: ExtractionStatus
    data: Optional[Any] = None
    sources: List[ExtractionSource] = field(default_factory=list)
    processing_time_ms: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIExtractor:
    """
    AI-powered data extraction service.
    
    Provides comprehensive extraction capabilities including:
    - Natural language prompt-based extraction
    - JSON schema-driven structured extraction
    - Multi-URL and domain-wide extraction
    - Web search augmentation
    - Source mapping and citation
    """
    
    def __init__(self):
        """Initialize AI extractor."""
        self.jobs: Dict[str, ExtractionJob] = {}
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "data_points_extracted": 0,
            "urls_processed": 0
        }
    
    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Start an extraction operation and wait for completion.
        
        Args:
            request: Extraction request configuration
            
        Returns:
            ExtractionResponse with extracted data
        """
        # Start async extraction
        job_id = await self.start_extraction(request)
        
        # Wait for completion
        return await self.wait_for_extraction(job_id, poll_interval=2, timeout=request.timeout)
    
    async def start_extraction(self, request: ExtractionRequest) -> str:
        """
        Start an asynchronous extraction operation.
        
        Args:
            request: Extraction request configuration
            
        Returns:
            Job ID for monitoring
        """
        job_id = str(uuid.uuid4())
        job = ExtractionJob(id=job_id, request=request)
        
        self.jobs[job_id] = job
        self.extraction_stats["total_extractions"] += 1
        
        logger.info("extraction_job_started", 
                   job_id=job_id, 
                   urls_count=len(request.urls or []),
                   has_prompt=bool(request.prompt),
                   has_schema=bool(request.schema))
        
        # Start background task
        asyncio.create_task(self._execute_extraction(job))
        
        return job_id
    
    async def get_extraction_status(self, job_id: str) -> ExtractionResponse:
        """Get status of extraction job."""
        if job_id not in self.jobs:
            return ExtractionResponse(
                success=False,
                job_id=job_id,
                status=ExtractionStatus.FAILED,
                error="Job not found"
            )
        
        job = self.jobs[job_id]
        
        return ExtractionResponse(
            success=job.status == ExtractionStatus.COMPLETED,
            job_id=job_id,
            status=job.status,
            data=job.result.data if job.result else None,
            sources=job.result.sources if job.result else [],
            processing_time_ms=int((datetime.utcnow() - job.created_at).total_seconds() * 1000),
            error=job.error,
            metadata={
                "progress": job.progress,
                "total_urls": job.total_urls,
                "processed_urls": job.processed_urls,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
        )
    
    async def wait_for_extraction(
        self, 
        job_id: str, 
        poll_interval: int = 2, 
        timeout: Optional[int] = None
    ) -> ExtractionResponse:
        """
        Wait for extraction to complete.
        
        Args:
            job_id: Job ID to monitor
            poll_interval: Seconds between status checks
            timeout: Maximum wait time in seconds
            
        Returns:
            Final extraction response
        """
        start_time = time.time()
        
        while True:
            response = await self.get_extraction_status(job_id)
            
            if response.status in [ExtractionStatus.COMPLETED, ExtractionStatus.FAILED, ExtractionStatus.CANCELLED]:
                return response
            
            if timeout and (time.time() - start_time) > timeout:
                return ExtractionResponse(
                    success=False,
                    job_id=job_id,
                    status=ExtractionStatus.FAILED,
                    error=f"Extraction timeout after {timeout} seconds"
                )
            
            await asyncio.sleep(poll_interval)
    
    async def cancel_extraction(self, job_id: str) -> bool:
        """Cancel an extraction job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status in [ExtractionStatus.COMPLETED, ExtractionStatus.FAILED]:
            return False
        
        job.status = ExtractionStatus.CANCELLED
        logger.info("extraction_job_cancelled", job_id=job_id)
        return True
    
    async def _execute_extraction(self, job: ExtractionJob):
        """Execute extraction job in background."""
        try:
            job.status = ExtractionStatus.PROCESSING
            job.started_at = datetime.utcnow()
            
            logger.info("extraction_job_processing", job_id=job.id)
            
            # Step 1: Discover URLs
            urls = await self._discover_urls(job)
            job.total_urls = len(urls)
            job.progress = 0.1
            
            if job.status == ExtractionStatus.CANCELLED:
                return
            
            # Step 2: Scrape URLs
            scraped_data = await self._scrape_urls(job, urls)
            job.progress = 0.6
            
            if job.status == ExtractionStatus.CANCELLED:
                return
            
            # Step 3: Extract structured data
            extracted_data = await self._extract_structured_data(job, scraped_data)
            job.progress = 0.9
            
            if job.status == ExtractionStatus.CANCELLED:
                return
            
            # Step 4: Post-process and finalize
            job.result = await self._finalize_extraction(job, extracted_data)
            job.status = ExtractionStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 1.0
            
            # Update stats
            self.extraction_stats["successful_extractions"] += 1
            self.extraction_stats["urls_processed"] += len(urls)
            if job.result:
                self.extraction_stats["data_points_extracted"] += self._count_data_points(job.result.data)
            
            logger.info("extraction_job_completed", 
                       job_id=job.id,
                       urls_processed=len(urls),
                       processing_time_ms=int((job.completed_at - job.started_at).total_seconds() * 1000))
            
            # Send webhook notification if configured
            if job.request.webhook_url:
                await self._send_webhook_notification(job)
        
        except Exception as e:
            job.status = ExtractionStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            
            logger.error("extraction_job_failed", 
                        job_id=job.id, 
                        error=str(e))
    
    async def _discover_urls(self, job: ExtractionJob) -> List[str]:
        """Discover URLs for extraction."""
        request = job.request
        urls = []
        
        # Use provided URLs
        if request.urls:
            urls.extend(request.urls)
        
        # Use web search if enabled
        if request.enable_web_search and request.search_query:
            try:
                search_service = await get_multi_search_service()
                search_options = SearchOptions(
                    query=request.search_query,
                    num_results=min(request.max_urls, 50),
                    lang="en",
                    country="us"
                )
                
                search_results = await search_service.search(search_options)
                search_urls = [result.url for result in search_results]
                urls.extend(search_urls)
                
                logger.info("web_search_urls_discovered", 
                           job_id=job.id, 
                           search_urls=len(search_urls))
                
            except Exception as e:
                logger.warning("web_search_failed", job_id=job.id, error=str(e))
        
        # Discover additional URLs from domains if wildcards used
        domain_urls = []
        for url in urls[:]:  # Copy to avoid modification during iteration
            if url.endswith('/*'):
                try:
                    base_url = url[:-2]  # Remove /*
                    mapper = await get_website_mapper()
                    
                    map_options = MapOptions(
                        strategy=MapStrategy.COMBINED,
                        limit=min(request.max_urls, 100),
                        include_subdomains=request.include_subdomains,
                        allow_external_links=request.allow_external_links
                    )
                    
                    mapping_result = await mapper.map_website(base_url, map_options)
                    if mapping_result.success:
                        discovered = [du.url for du in mapping_result.discovered_urls]
                        domain_urls.extend(discovered)
                        
                        logger.info("domain_urls_discovered", 
                                   job_id=job.id, 
                                   base_url=base_url,
                                   discovered_urls=len(discovered))
                
                except Exception as e:
                    logger.warning("domain_discovery_failed", 
                                 job_id=job.id, 
                                 url=url, 
                                 error=str(e))
        
        urls.extend(domain_urls)
        
        # Remove duplicates and filter invalid URLs
        unique_urls = list(set(urls))
        
        if request.ignore_invalid_urls:
            valid_urls = []
            for url in unique_urls:
                if self._is_valid_url(url):
                    valid_urls.append(url)
            unique_urls = valid_urls
        
        # Apply limit
        if len(unique_urls) > request.max_urls:
            unique_urls = unique_urls[:request.max_urls]
        
        logger.info("urls_discovered", 
                   job_id=job.id, 
                   total_urls=len(unique_urls))
        
        return unique_urls
    
    async def _scrape_urls(self, job: ExtractionJob, urls: List[str]) -> List[ScrapedContent]:
        """Scrape content from URLs."""
        try:
            scraping_service = await get_enhanced_scraping_service()
            
            # Scrape in batches to avoid overwhelming
            batch_size = 10
            all_scraped = []
            
            for i in range(0, len(urls), batch_size):
                if job.status == ExtractionStatus.CANCELLED:
                    break
                
                batch_urls = urls[i:i + batch_size]
                
                try:
                    batch_results = await scraping_service.scrape_urls_enhanced(batch_urls)
                    successful_results = [r for r in batch_results if r.extraction_success]
                    all_scraped.extend(successful_results)
                    
                    job.processed_urls += len(batch_results)
                    job.progress = 0.1 + (0.5 * job.processed_urls / job.total_urls)
                    
                    logger.debug("batch_scraped", 
                               job_id=job.id, 
                               batch_size=len(batch_urls),
                               successful=len(successful_results))
                
                except Exception as e:
                    logger.warning("batch_scraping_failed", 
                                 job_id=job.id, 
                                 batch_urls=batch_urls, 
                                 error=str(e))
                
                # Small delay between batches
                await asyncio.sleep(0.5)
            
            logger.info("scraping_completed", 
                       job_id=job.id, 
                       total_scraped=len(all_scraped),
                       total_attempted=len(urls))
            
            return all_scraped
        
        except Exception as e:
            logger.error("scraping_failed", job_id=job.id, error=str(e))
            raise e
    
    async def _extract_structured_data(
        self, 
        job: ExtractionJob, 
        scraped_data: List[ScrapedContent]
    ) -> ExtractedData:
        """Extract structured data using LLM."""
        request = job.request
        
        if not request.prompt and not request.schema:
            raise ValueError("Either prompt or schema is required for extraction")
        
        try:
            # Combine all scraped content
            combined_content = []
            sources = []
            
            for scraped in scraped_data:
                content_parts = []
                if scraped.title:
                    content_parts.append(f"Title: {scraped.title}")
                if scraped.text:
                    content_parts.append(f"Content: {scraped.text[:2000]}")  # Limit content length
                
                if content_parts:
                    combined_content.append(f"URL: {scraped.url}\n" + "\n".join(content_parts))
                    
                    sources.append(ExtractionSource(
                        url=scraped.url,
                        title=scraped.title,
                        confidence_score=scraped.content_quality_score or 1.0,
                        extraction_method="scraping"
                    ))
            
            # Prepare LLM prompt
            system_prompt = request.system_prompt or """You are an expert data extraction assistant. 
Extract structured information from web content according to the provided prompt or schema.
Return only valid JSON without any additional text or formatting."""
            
            if request.schema:
                if request.prompt:
                    user_prompt = f"""Extract data according to this prompt: {request.prompt}

Use this JSON schema as the structure:
{json.dumps(request.schema, indent=2)}

Content to extract from:
{chr(10).join(combined_content[:10])}"""  # Limit to first 10 sources
                else:
                    user_prompt = f"""Extract data according to this JSON schema:
{json.dumps(request.schema, indent=2)}

Content to extract from:
{chr(10).join(combined_content[:10])}"""
            else:
                user_prompt = f"""Extract data according to this prompt: {request.prompt}

Return the result as valid JSON.

Content to extract from:
{chr(10).join(combined_content[:10])}"""
            
            # Call LLM service
            llm_service = await get_llm_config_service()
            agent_config = request.agent or AgentConfig()
            
            extraction_result = await llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=agent_config.model.value,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens
            )
            
            # Parse LLM response as JSON
            try:
                extracted_json = json.loads(extraction_result)
            except json.JSONDecodeError:
                # Try to extract JSON from response if it's wrapped in text
                import re
                json_match = re.search(r'\{.*\}', extraction_result, re.DOTALL)
                if json_match:
                    extracted_json = json.loads(json_match.group())
                else:
                    extracted_json = {"extracted_text": extraction_result}
            
            return ExtractedData(
                data=extracted_json,
                sources=sources,
                confidence_score=0.9,  # High confidence for LLM extraction
                extraction_metadata={
                    "model_used": agent_config.model.value,
                    "sources_count": len(sources),
                    "extraction_method": "llm_structured"
                }
            )
        
        except Exception as e:
            logger.error("structured_extraction_failed", job_id=job.id, error=str(e))
            
            # Fallback to simple text extraction
            return ExtractedData(
                data={"error": str(e), "fallback_content": [s.text[:500] for s in scraped_data[:5]]},
                sources=sources,
                confidence_score=0.3,
                extraction_metadata={"extraction_method": "fallback"}
            )
    
    async def _finalize_extraction(self, job: ExtractionJob, extracted_data: ExtractedData) -> ExtractedData:
        """Finalize extraction with post-processing."""
        request = job.request
        
        # Add job metadata
        extracted_data.extraction_metadata.update({
            "job_id": job.id,
            "processing_time_ms": int((datetime.utcnow() - job.started_at).total_seconds() * 1000),
            "urls_processed": job.processed_urls,
            "integration": request.integration
        })
        
        # Filter sources if not requested
        if not request.show_sources:
            extracted_data.sources = []
        
        return extracted_data
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _count_data_points(self, data: Any) -> int:
        """Count data points in extracted data."""
        if isinstance(data, dict):
            return sum(self._count_data_points(v) for v in data.values())
        elif isinstance(data, list):
            return sum(self._count_data_points(item) for item in data)
        else:
            return 1
    
    async def _send_webhook_notification(self, job: ExtractionJob):
        """Send webhook notification about job completion."""
        try:
            import httpx
            
            webhook_data = {
                "job_id": job.id,
                "status": job.status.value,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "urls_processed": job.processed_urls,
                "success": job.status == ExtractionStatus.COMPLETED,
                "error": job.error
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    job.request.webhook_url,
                    json=webhook_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info("webhook_notification_sent", 
                               job_id=job.id, 
                               webhook_url=job.request.webhook_url)
                else:
                    logger.warning("webhook_notification_failed", 
                                 job_id=job.id, 
                                 status_code=response.status_code)
        
        except Exception as e:
            logger.error("webhook_notification_error", 
                        job_id=job.id, 
                        error=str(e))
    
    async def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction service statistics."""
        active_jobs = len([j for j in self.jobs.values() if j.status == ExtractionStatus.PROCESSING])
        completed_jobs = len([j for j in self.jobs.values() if j.status == ExtractionStatus.COMPLETED])
        
        return {
            "extraction_stats": self.extraction_stats,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "total_jobs": len(self.jobs),
            "success_rate": (
                self.extraction_stats["successful_extractions"] / 
                max(1, self.extraction_stats["total_extractions"])
            ) if self.extraction_stats["total_extractions"] > 0 else 0,
            "avg_urls_per_extraction": (
                self.extraction_stats["urls_processed"] /
                max(1, self.extraction_stats["successful_extractions"])
            ) if self.extraction_stats["successful_extractions"] > 0 else 0
        }


# Singleton service
_ai_extractor: Optional[AIExtractor] = None


async def get_ai_extractor() -> AIExtractor:
    """Get or create AI extractor service instance."""
    global _ai_extractor
    
    if _ai_extractor is None:
        _ai_extractor = AIExtractor()
    
    return _ai_extractor


# Convenience functions
async def extract_with_prompt(
    urls: List[str],
    prompt: str,
    enable_web_search: bool = False,
    show_sources: bool = True
) -> ExtractionResponse:
    """
    Extract data using natural language prompt.
    
    Args:
        urls: URLs to extract from
        prompt: Natural language extraction prompt
        enable_web_search: Enable web search augmentation
        show_sources: Include source information
        
    Returns:
        ExtractionResponse with extracted data
    """
    extractor = await get_ai_extractor()
    
    request = ExtractionRequest(
        urls=urls,
        prompt=prompt,
        enable_web_search=enable_web_search,
        show_sources=show_sources
    )
    
    return await extractor.extract(request)


async def extract_with_schema(
    urls: List[str],
    schema: Dict[str, Any],
    system_prompt: Optional[str] = None,
    show_sources: bool = True
) -> ExtractionResponse:
    """
    Extract data using JSON schema.
    
    Args:
        urls: URLs to extract from
        schema: JSON schema for structured extraction
        system_prompt: Optional system prompt
        show_sources: Include source information
        
    Returns:
        ExtractionResponse with extracted data
    """
    extractor = await get_ai_extractor()
    
    request = ExtractionRequest(
        urls=urls,
        schema=schema,
        system_prompt=system_prompt,
        show_sources=show_sources
    )
    
    return await extractor.extract(request)
