"""
Advanced Crawl Management service inspired by Firecrawl.

Provides comprehensive crawl job lifecycle management:
- Job status monitoring and control
- Crawl job cancellation and error handling
- Real-time progress tracking
- Resource management and throttling
- Job queuing and prioritization
- Comprehensive error reporting
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import structlog

from app.config import get_settings
from app.models.responses import ScrapedContent
from app.services.enhanced_scraping import get_enhanced_scraping_service
from app.services.website_mapping import get_website_mapper, MapOptions, MapStrategy
from app.services.dispatcher import get_memory_adaptive_dispatcher

logger = structlog.get_logger(__name__)
settings = get_settings()


class CrawlStatus(Enum):
    """Status of crawl operations."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    SCRAPING = "scraping"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class CrawlPriority(Enum):
    """Priority levels for crawl jobs."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20


@dataclass
class CrawlError:
    """Represents a crawl error."""
    url: str
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    fatal: bool = False


@dataclass
class CrawlProgress:
    """Progress tracking for crawl jobs."""
    total_urls: int = 0
    completed_urls: int = 0
    failed_urls: int = 0
    skipped_urls: int = 0
    current_url: Optional[str] = None
    percentage: float = 0.0
    estimated_completion: Optional[datetime] = None
    urls_per_minute: float = 0.0


@dataclass
class CrawlOptions:
    """Configuration options for crawl jobs."""
    # URL discovery
    max_urls: int = 1000
    max_depth: int = 3
    include_subdomains: bool = True
    allow_external_links: bool = False
    ignore_sitemap: bool = False
    include_paths: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)
    
    # Performance
    max_concurrent_requests: int = 10
    delay_between_requests: float = 0.5
    timeout: int = 30
    
    # Content filtering
    include_tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    only_main_content: bool = True
    
    # Retry logic
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Data retention
    zero_data_retention: bool = False
    webhook_url: Optional[str] = None


@dataclass
class CrawlJob:
    """Represents a crawl job."""
    id: str
    url: str
    options: CrawlOptions
    status: CrawlStatus = CrawlStatus.PENDING
    priority: CrawlPriority = CrawlPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: CrawlProgress = field(default_factory=CrawlProgress)
    errors: List[CrawlError] = field(default_factory=list)
    results: List[ScrapedContent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Resource tracking
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Job control
    cancellation_requested: bool = False
    pause_requested: bool = False


@dataclass
class CrawlJobSummary:
    """Summary information for a crawl job."""
    id: str
    url: str
    status: CrawlStatus
    priority: CrawlPriority
    created_at: datetime
    progress_percentage: float
    total_urls: int
    completed_urls: int
    error_count: int
    estimated_completion: Optional[datetime] = None


class CrawlManager:
    """
    Advanced crawl management service.
    
    Provides comprehensive crawl job lifecycle management including:
    - Job creation, monitoring, and control
    - Priority-based job queuing
    - Resource management and throttling
    - Error handling and retry logic
    - Real-time progress tracking
    """
    
    def __init__(self):
        """Initialize crawl manager."""
        self.jobs: Dict[str, CrawlJob] = {}
        self.job_queue: List[str] = []  # Job IDs in priority order
        self.active_jobs: Set[str] = set()
        self.max_concurrent_jobs = getattr(settings, 'crawl_max_concurrent_jobs', 5)
        
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "total_urls_crawled": 0,
            "total_errors": 0
        }
        
        # Start background worker
        self._worker_task = None
        asyncio.create_task(self._start_crawl_worker())
    
    async def start_crawl(
        self, 
        url: str, 
        options: Optional[CrawlOptions] = None,
        priority: CrawlPriority = CrawlPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new crawl job.
        
        Args:
            url: Starting URL for the crawl
            options: Crawl configuration options
            priority: Job priority level
            metadata: Additional metadata
            
        Returns:
            Job ID for monitoring
        """
        job_id = str(uuid.uuid4())
        options = options or CrawlOptions()
        metadata = metadata or {}
        
        job = CrawlJob(
            id=job_id,
            url=url,
            options=options,
            priority=priority,
            metadata=metadata
        )
        
        self.jobs[job_id] = job
        self.stats["total_jobs"] += 1
        
        # Add to priority queue
        self._add_to_queue(job_id, priority)
        
        logger.info("crawl_job_created",
                   job_id=job_id,
                   url=url,
                   priority=priority.name,
                   max_urls=options.max_urls)
        
        return job_id
    
    async def get_crawl_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a crawl job."""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        return {
            "id": job.id,
            "url": job.url,
            "status": job.status.value,
            "priority": job.priority.name,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "progress": {
                "total_urls": job.progress.total_urls,
                "completed_urls": job.progress.completed_urls,
                "failed_urls": job.progress.failed_urls,
                "skipped_urls": job.progress.skipped_urls,
                "percentage": job.progress.percentage,
                "current_url": job.progress.current_url,
                "estimated_completion": job.progress.estimated_completion.isoformat() if job.progress.estimated_completion else None,
                "urls_per_minute": job.progress.urls_per_minute
            },
            "resource_usage": {
                "memory_mb": job.memory_usage_mb,
                "cpu_percent": job.cpu_usage_percent
            },
            "errors": [
                {
                    "url": error.url,
                    "error_type": error.error_type,
                    "message": error.message,
                    "timestamp": error.timestamp.isoformat(),
                    "retry_count": error.retry_count,
                    "fatal": error.fatal
                }
                for error in job.errors[-10:]  # Last 10 errors
            ],
            "total_errors": len(job.errors),
            "results_count": len(job.results),
            "can_cancel": job.status in [CrawlStatus.PENDING, CrawlStatus.SCRAPING, CrawlStatus.PAUSED],
            "can_pause": job.status == CrawlStatus.SCRAPING,
            "can_resume": job.status == CrawlStatus.PAUSED
        }
    
    async def cancel_crawl(self, job_id: str) -> bool:
        """Cancel a crawl job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status in [CrawlStatus.COMPLETED, CrawlStatus.FAILED, CrawlStatus.CANCELLED]:
            return False
        
        job.cancellation_requested = True
        
        # If job is active, mark it for immediate cancellation
        if job_id in self.active_jobs:
            job.status = CrawlStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            self.active_jobs.remove(job_id)
            self.stats["cancelled_jobs"] += 1
        else:
            # Remove from queue if not started yet
            if job_id in self.job_queue:
                self.job_queue.remove(job_id)
            job.status = CrawlStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            self.stats["cancelled_jobs"] += 1
        
        logger.info("crawl_job_cancelled", job_id=job_id)
        
        # Send webhook notification
        if job.options.webhook_url:
            await self._send_webhook_notification(job, "cancelled")
        
        return True
    
    async def pause_crawl(self, job_id: str) -> bool:
        """Pause an active crawl job."""
        if job_id not in self.jobs or job_id not in self.active_jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status != CrawlStatus.SCRAPING:
            return False
        
        job.pause_requested = True
        job.status = CrawlStatus.PAUSED
        
        logger.info("crawl_job_paused", job_id=job_id)
        return True
    
    async def resume_crawl(self, job_id: str) -> bool:
        """Resume a paused crawl job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status != CrawlStatus.PAUSED:
            return False
        
        job.pause_requested = False
        job.status = CrawlStatus.SCRAPING
        
        logger.info("crawl_job_resumed", job_id=job_id)
        return True
    
    async def get_crawl_errors(self, job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get errors for a crawl job."""
        if job_id not in self.jobs:
            return []
        
        job = self.jobs[job_id]
        errors = job.errors[-limit:] if limit > 0 else job.errors
        
        return [
            {
                "url": error.url,
                "error_type": error.error_type,
                "message": error.message,
                "timestamp": error.timestamp.isoformat(),
                "retry_count": error.retry_count,
                "fatal": error.fatal
            }
            for error in errors
        ]
    
    async def get_active_crawls(self) -> List[CrawlJobSummary]:
        """Get summary of all active crawl jobs."""
        active_summaries = []
        
        for job_id in self.active_jobs:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                summary = CrawlJobSummary(
                    id=job.id,
                    url=job.url,
                    status=job.status,
                    priority=job.priority,
                    created_at=job.created_at,
                    progress_percentage=job.progress.percentage,
                    total_urls=job.progress.total_urls,
                    completed_urls=job.progress.completed_urls,
                    error_count=len(job.errors),
                    estimated_completion=job.progress.estimated_completion
                )
                active_summaries.append(summary)
        
        # Sort by priority and creation time
        active_summaries.sort(key=lambda x: (-x.priority.value, x.created_at))
        return active_summaries
    
    async def get_crawl_results(self, job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get results from a completed crawl job."""
        if job_id not in self.jobs:
            return []
        
        job = self.jobs[job_id]
        results = job.results[-limit:] if limit > 0 else job.results
        
        return [result.dict() for result in results]
    
    def _add_to_queue(self, job_id: str, priority: CrawlPriority):
        """Add job to priority queue."""
        # Find insertion point based on priority
        insert_pos = 0
        for i, existing_job_id in enumerate(self.job_queue):
            if existing_job_id in self.jobs:
                existing_priority = self.jobs[existing_job_id].priority
                if priority.value > existing_priority.value:
                    break
                insert_pos = i + 1
        
        self.job_queue.insert(insert_pos, job_id)
    
    async def _start_crawl_worker(self):
        """Start background worker for processing crawl jobs."""
        self._worker_task = asyncio.create_task(self._crawl_worker())
    
    async def _crawl_worker(self):
        """Background worker that processes crawl jobs."""
        while True:
            try:
                await self._process_job_queue()
                await asyncio.sleep(5)  # Check queue every 5 seconds
                
            except Exception as e:
                logger.error("crawl_worker_error", error=str(e))
                await asyncio.sleep(30)  # Wait 30 seconds before retrying
    
    async def _process_job_queue(self):
        """Process jobs from the queue."""
        # Check if we can start new jobs
        if len(self.active_jobs) >= self.max_concurrent_jobs:
            return
        
        # Clean up completed jobs from active set
        completed_jobs = []
        for job_id in list(self.active_jobs):
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status in [CrawlStatus.COMPLETED, CrawlStatus.FAILED, CrawlStatus.CANCELLED]:
                    completed_jobs.append(job_id)
        
        for job_id in completed_jobs:
            self.active_jobs.remove(job_id)
        
        # Start new jobs from queue
        while len(self.active_jobs) < self.max_concurrent_jobs and self.job_queue:
            job_id = self.job_queue.pop(0)
            
            if job_id in self.jobs:
                job = self.jobs[job_id]
                
                # Skip cancelled jobs
                if job.cancellation_requested:
                    job.status = CrawlStatus.CANCELLED
                    job.completed_at = datetime.utcnow()
                    continue
                
                # Start the job
                self.active_jobs.add(job_id)
                asyncio.create_task(self._execute_crawl_job(job))
    
    async def _execute_crawl_job(self, job: CrawlJob):
        """Execute a single crawl job."""
        try:
            job.status = CrawlStatus.INITIALIZING
            job.started_at = datetime.utcnow()
            
            logger.info("crawl_job_started",
                       job_id=job.id,
                       url=job.url)
            
            # Step 1: URL Discovery
            await self._discover_urls_for_job(job)
            
            if job.cancellation_requested:
                job.status = CrawlStatus.CANCELLED
                job.completed_at = datetime.utcnow()
                return
            
            # Step 2: Scraping
            job.status = CrawlStatus.SCRAPING
            await self._scrape_urls_for_job(job)
            
            if job.cancellation_requested:
                job.status = CrawlStatus.CANCELLED
                job.completed_at = datetime.utcnow()
                return
            
            # Step 3: Post-processing
            job.status = CrawlStatus.PROCESSING
            await self._post_process_job(job)
            
            # Complete job
            job.status = CrawlStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress.percentage = 100.0
            
            self.stats["completed_jobs"] += 1
            self.stats["total_urls_crawled"] += job.progress.completed_urls
            
            logger.info("crawl_job_completed",
                       job_id=job.id,
                       urls_crawled=job.progress.completed_urls,
                       processing_time_ms=int((job.completed_at - job.started_at).total_seconds() * 1000))
            
            # Send webhook notification
            if job.options.webhook_url:
                await self._send_webhook_notification(job, "completed")
        
        except Exception as e:
            job.status = CrawlStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.errors.append(CrawlError(
                url=job.url,
                error_type="job_execution_error",
                message=str(e),
                fatal=True
            ))
            
            self.stats["failed_jobs"] += 1
            self.stats["total_errors"] += 1
            
            logger.error("crawl_job_failed",
                        job_id=job.id,
                        error=str(e))
            
            # Send webhook notification
            if job.options.webhook_url:
                await self._send_webhook_notification(job, "failed")
    
    async def _discover_urls_for_job(self, job: CrawlJob):
        """Discover URLs for crawling."""
        try:
            mapper = await get_website_mapper()
            
            map_options = MapOptions(
                strategy=MapStrategy.COMBINED,
                limit=job.options.max_urls,
                include_subdomains=job.options.include_subdomains,
                allow_external_links=job.options.allow_external_links,
                ignore_sitemap=job.options.ignore_sitemap,
                max_depth=job.options.max_depth
            )
            
            mapping_result = await mapper.map_website(job.url, map_options)
            
            if mapping_result.success:
                discovered_urls = [du.url for du in mapping_result.discovered_urls]
                
                # Apply include/exclude path filters
                filtered_urls = self._apply_path_filters(discovered_urls, job.options)
                
                job.progress.total_urls = len(filtered_urls)
                job.metadata["discovered_urls"] = filtered_urls
                
                logger.info("urls_discovered_for_job",
                           job_id=job.id,
                           total_urls=len(filtered_urls))
            else:
                raise Exception(f"URL discovery failed: {mapping_result.error}")
        
        except Exception as e:
            job.errors.append(CrawlError(
                url=job.url,
                error_type="url_discovery_error",
                message=str(e)
            ))
            raise e
    
    def _apply_path_filters(self, urls: List[str], options: CrawlOptions) -> List[str]:
        """Apply include/exclude path filters."""
        filtered_urls = urls
        
        # Apply include patterns
        if options.include_paths:
            filtered_urls = [
                url for url in filtered_urls
                if any(pattern in url for pattern in options.include_paths)
            ]
        
        # Apply exclude patterns
        if options.exclude_paths:
            filtered_urls = [
                url for url in filtered_urls
                if not any(pattern in url for pattern in options.exclude_paths)
            ]
        
        return filtered_urls
    
    async def _scrape_urls_for_job(self, job: CrawlJob):
        """Scrape URLs for the job."""
        urls = job.metadata.get("discovered_urls", [])
        if not urls:
            return
        
        scraping_service = await get_enhanced_scraping_service()
        dispatcher = await get_memory_adaptive_dispatcher()
        
        # Process URLs in batches
        batch_size = min(job.options.max_concurrent_requests, 20)
        start_time = time.time()
        
        for i in range(0, len(urls), batch_size):
            # Check for cancellation/pause
            if job.cancellation_requested:
                break
            
            while job.pause_requested:
                await asyncio.sleep(1)
                if job.cancellation_requested:
                    break
            
            batch_urls = urls[i:i + batch_size]
            job.progress.current_url = batch_urls[0] if batch_urls else None
            
            try:
                # Use dispatcher for rate limiting
                batch_results = await dispatcher.dispatch_async_batch(
                    [scraping_service.scrape_urls_enhanced([url]) for url in batch_urls]
                )
                
                # Process results
                for j, result_list in enumerate(batch_results):
                    url = batch_urls[j]
                    
                    if result_list and result_list[0].extraction_success:
                        job.results.append(result_list[0])
                        job.progress.completed_urls += 1
                    else:
                        job.progress.failed_urls += 1
                        job.errors.append(CrawlError(
                            url=url,
                            error_type="scraping_failed",
                            message="Failed to scrape URL"
                        ))
                        self.stats["total_errors"] += 1
                
                # Update progress
                total_processed = job.progress.completed_urls + job.progress.failed_urls
                job.progress.percentage = min(90.0, (total_processed / job.progress.total_urls) * 90.0)
                
                # Calculate URLs per minute
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    job.progress.urls_per_minute = (total_processed / elapsed_time) * 60
                    
                    # Estimate completion time
                    if job.progress.urls_per_minute > 0:
                        remaining_urls = job.progress.total_urls - total_processed
                        remaining_minutes = remaining_urls / job.progress.urls_per_minute
                        job.progress.estimated_completion = datetime.utcnow() + timedelta(minutes=remaining_minutes)
                
                # Apply delay between batches
                if job.options.delay_between_requests > 0:
                    await asyncio.sleep(job.options.delay_between_requests)
            
            except Exception as e:
                logger.error("batch_scraping_failed",
                           job_id=job.id,
                           batch_urls=batch_urls,
                           error=str(e))
                
                # Mark all URLs in batch as failed
                for url in batch_urls:
                    job.progress.failed_urls += 1
                    job.errors.append(CrawlError(
                        url=url,
                        error_type="batch_scraping_error",
                        message=str(e)
                    ))
        
        logger.info("scraping_completed_for_job",
                   job_id=job.id,
                   completed_urls=job.progress.completed_urls,
                   failed_urls=job.progress.failed_urls)
    
    async def _post_process_job(self, job: CrawlJob):
        """Post-process job results."""
        # Register for zero data retention if enabled
        if job.options.zero_data_retention:
            from app.services.zero_retention import get_zero_retention_manager, DataType
            
            try:
                retention_manager = await get_zero_retention_manager()
                
                # Calculate total size
                total_size = sum(
                    len(result.text or "") + len(result.html or "")
                    for result in job.results
                )
                
                await retention_manager.register_data(
                    data_id=f"crawl_job_{job.id}",
                    data_type=DataType.CRAWL_DATA,
                    size_bytes=total_size,
                    tags=["zero_retention", "crawl_job"],
                    secure_delete=True
                )
                
                logger.info("job_registered_for_zero_retention",
                           job_id=job.id,
                           size_bytes=total_size)
            
            except Exception as e:
                logger.warning("zero_retention_registration_failed",
                             job_id=job.id,
                             error=str(e))
    
    async def _send_webhook_notification(self, job: CrawlJob, event: str):
        """Send webhook notification about job status."""
        try:
            import httpx
            
            webhook_data = {
                "job_id": job.id,
                "url": job.url,
                "event": event,
                "status": job.status.value,
                "progress": {
                    "total_urls": job.progress.total_urls,
                    "completed_urls": job.progress.completed_urls,
                    "failed_urls": job.progress.failed_urls,
                    "percentage": job.progress.percentage
                },
                "timestamp": datetime.utcnow().isoformat(),
                "results_count": len(job.results),
                "errors_count": len(job.errors)
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    job.options.webhook_url,
                    json=webhook_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info("webhook_notification_sent",
                               job_id=job.id,
                               event=event,
                               webhook_url=job.options.webhook_url)
                else:
                    logger.warning("webhook_notification_failed",
                                 job_id=job.id,
                                 event=event,
                                 status_code=response.status_code)
        
        except Exception as e:
            logger.error("webhook_notification_error",
                        job_id=job.id,
                        event=event,
                        error=str(e))
    
    async def get_crawl_stats(self) -> Dict[str, Any]:
        """Get crawl management statistics."""
        return {
            "crawl_stats": self.stats,
            "active_jobs": len(self.active_jobs),
            "queued_jobs": len(self.job_queue),
            "total_jobs_managed": len(self.jobs),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "success_rate": (
                self.stats["completed_jobs"] / 
                max(1, self.stats["total_jobs"])
            ) if self.stats["total_jobs"] > 0 else 0,
            "avg_urls_per_job": (
                self.stats["total_urls_crawled"] /
                max(1, self.stats["completed_jobs"])
            ) if self.stats["completed_jobs"] > 0 else 0,
            "worker_running": self._worker_task is not None and not self._worker_task.done()
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass


# Singleton service
_crawl_manager: Optional[CrawlManager] = None


async def get_crawl_manager() -> CrawlManager:
    """Get or create crawl manager service instance."""
    global _crawl_manager
    
    if _crawl_manager is None:
        _crawl_manager = CrawlManager()
    
    return _crawl_manager


# Convenience functions
async def start_website_crawl(
    url: str,
    max_urls: int = 100,
    max_depth: int = 2,
    webhook_url: Optional[str] = None,
    zero_data_retention: bool = False
) -> str:
    """
    Start a website crawl with common options.
    
    Args:
        url: Starting URL
        max_urls: Maximum URLs to crawl
        max_depth: Maximum crawl depth
        webhook_url: Webhook for notifications
        zero_data_retention: Enable 24-hour data deletion
        
    Returns:
        Job ID for monitoring
    """
    manager = await get_crawl_manager()
    
    options = CrawlOptions(
        max_urls=max_urls,
        max_depth=max_depth,
        webhook_url=webhook_url,
        zero_data_retention=zero_data_retention
    )
    
    return await manager.start_crawl(url, options)


async def get_crawl_progress(job_id: str) -> Optional[Dict[str, Any]]:
    """Get crawl job progress."""
    manager = await get_crawl_manager()
    return await manager.get_crawl_status(job_id)




