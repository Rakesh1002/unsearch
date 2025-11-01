"""
Celery tasks for async processing.
"""
from celery import Celery, Task
from typing import Dict, Any
import httpx
import asyncio
from datetime import datetime

from app.config import get_settings
from app.services.searxng import SearXNGService
from app.services.scraping import ContentScrapingService
from app.services.database import DatabaseService
from app.models.requests import UnQuestRequest, ScrapingConfig
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()

# Initialize Celery
celery = Celery(
    'UnQuest',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_time_limit=settings.celery_task_time_limit,
    worker_concurrency=settings.celery_worker_concurrency,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True
)


class AsyncTask(Task):
    """Base task that properly handles async operations."""
    
    def run(self, *args, **kwargs):
        """Run the task in an async context."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_run(*args, **kwargs))
        finally:
            loop.close()
            
    async def async_run(self, *args, **kwargs):
        """Override this method in subclasses."""
        raise NotImplementedError


@celery.task(base=AsyncTask, bind=True, max_retries=3)
async def process_async_search_scrape(self, job_id: str, request_data: Dict[str, Any]):
    """
    Process search and scrape request asynchronously.
    
    Args:
        job_id: Scraping job ID
        request_data: UnQuestRequest data as dict
    """
    logger.info("async_search_scrape_started", job_id=job_id)
    
    try:
        # Initialize services
        searxng = SearXNGService()
        scraper = ContentScrapingService()
        db = DatabaseService()
        
        await searxng.initialize()
        await scraper.initialize()
        await db.initialize()
        
        # Update job status
        await db.update_scraping_job(
            job_id,
            status="processing",
            task_id=self.request.id
        )
        
        # Create request object
        request = UnQuestRequest(**request_data)
        
        # Perform search
        search_results = await searxng.search(
            query=request.query,
            engines=request.engines,
            language=request.language,
            safe_search=1 if request.safe_search == "moderate" else 0
        )
        
        # Limit results
        search_results = search_results[:request.max_results]
        
        # Scrape content if requested
        scraped_results = []
        if request.scrape_content and search_results:
            urls = [str(result.url) for result in search_results]
            
            scraping_config = ScrapingConfig(
                urls=urls,
                selectors=request.scrape_selectors,
                extract_images=request.include_images,
                extract_links=request.include_links,
                javascript_rendering=request.js_mode,
                js_mode=request.js_mode,
                response_format=request.output_format,
                screenshot=request.screenshot,
                pdf=request.pdf,
            )
            
            scraped_contents = await scraper.scrape_urls(urls[:10], scraping_config)
            
            # Combine results
            scraped_map = {str(sc.url): sc for sc in scraped_contents}
            
            for result in search_results:
                result_dict = result.dict()
                if str(result.url) in scraped_map:
                    result_dict['scraped_content'] = scraped_map[str(result.url)].dict()
                scraped_results.append(result_dict)
        else:
            scraped_results = [r.dict() for r in search_results]
            
        # Update job with results
        await db.update_scraping_job(
            job_id,
            status="completed",
            results=scraped_results
        )
        
        # Send webhook if configured
        if request_data.get('webhook_url'):
            await send_webhook(
                job_id,
                request_data['webhook_url'],
                scraped_results,
                db
            )
            
        logger.info("async_search_scrape_completed", job_id=job_id, results_count=len(scraped_results))
        
        # Cleanup
        await searxng.close()
        await scraper.close()
        await db.close()
        
        return {"job_id": job_id, "status": "completed", "results_count": len(scraped_results)}
        
    except Exception as e:
        logger.error("async_search_scrape_error", job_id=job_id, error=str(e))
        
        # Update job status
        try:
            db = DatabaseService()
            await db.initialize()
            await db.update_scraping_job(
                job_id,
                status="failed",
                error_message=str(e)
            )
            await db.close()
        except:
            pass
            
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@celery.task(base=AsyncTask)
async def send_webhook(job_id: str, webhook_url: str, results: list, db: DatabaseService):
    """
    Send webhook notification with results.
    
    Args:
        job_id: Job ID
        webhook_url: URL to send results to
        results: Search/scrape results
        db: Database service instance
    """
    payload = {
        "job_id": job_id,
        "status": "completed",
        "results": results,
        "completed_at": datetime.utcnow().isoformat()
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
        await db.update_scraping_job(
            job_id,
            status="completed",
            webhook_success=True
        )
        
        logger.info("webhook_sent", job_id=job_id, webhook_url=webhook_url)
        
    except Exception as e:
        logger.error("webhook_error", job_id=job_id, webhook_url=webhook_url, error=str(e))
        
        await db.update_scraping_job(
            job_id,
            status="completed",
            webhook_success=False
        )


@celery.task
def cleanup_old_jobs():
    """Periodic task to cleanup old scraping jobs."""
    logger.info("cleanup_old_jobs_started")
    # Implementation would go here
    pass


# Configure periodic tasks
celery.conf.beat_schedule = {
    'cleanup-old-jobs': {
        'task': 'app.workers.tasks.cleanup_old_jobs',
        'schedule': 3600.0,  # Every hour
    },
}
