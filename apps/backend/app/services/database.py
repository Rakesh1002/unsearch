"""
Database service for persistent storage operations.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.exc import IntegrityError
import uuid

from app.config import get_settings
from app.models.database import (
    Base, APIKey, SearchRequest, SearchResult as DBSearchResult,
    ScrapingJob, CacheEntry, ErrorLog
)
from app.models.responses import UnQuestResponse
import structlog
import ssl
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

logger = structlog.get_logger(__name__)
settings = get_settings()


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        # Convert sync PostgreSQL URL to async and handle sslmode for asyncpg (Neon)
        original_url = str(settings.database_url)
        if original_url.startswith("postgresql://"):
            async_url = original_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif original_url.startswith("postgres://"):
            async_url = original_url.replace("postgres://", "postgresql+asyncpg://", 1)
        else:
            async_url = original_url

        # Strip unsupported sslmode from asyncpg URL and map to connect_args['ssl']
        connect_args: dict[str, object] = {}
        try:
            parts = urlsplit(async_url)
            query_items = parse_qsl(parts.query, keep_blank_values=True)
            sslmode_value = None
            filtered_items = []
            # Remove parameters not understood by asyncpg
            unsupported_params = {
                "sslmode",
                "sslrootcert",
                "sslcert",
                "sslkey",
                "options",
                "channel_binding",
            }
            for k, v in query_items:
                key_lower = k.lower()
                if key_lower == "sslmode":
                    sslmode_value = v.lower() if isinstance(v, str) else str(v)
                    # drop from URL
                    continue
                if key_lower in unsupported_params:
                    # drop from URL; handled via connect_args where applicable
                    continue
                else:
                    filtered_items.append((k, v))

            # asyncpg doesn't accept 'sslmode'; use 'ssl' connect arg instead
            if sslmode_value and sslmode_value != "disable":
                # For Neon, a default SSL context or True works; True lets asyncpg create a context
                connect_args["ssl"] = True

            cleaned_query = urlencode(filtered_items, doseq=True)
            async_url = urlunsplit((parts.scheme, parts.netloc, parts.path, cleaned_query, parts.fragment))
        except Exception:
            # If anything goes wrong, fall back to the async_url as-is
            pass

        self.engine = create_async_engine(
            async_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            echo=settings.database_echo,
            future=True,
            connect_args=connect_args,
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
    async def initialize(self):
        """Initialize database connection.

        Avoid creating schema at startup to prevent greenlet requirement and
        rely on Alembic migrations for schema management. Just validate the
        connection with a lightweight query.
        """
        from sqlalchemy import text
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_initialized")
        
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
        logger.info("database_closed")
        
    @asynccontextmanager
    async def get_session(self):
        """Get database session context manager."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
                
    # API Key Management
    
    async def get_api_key(self, key: str) -> Optional[APIKey]:
        """Get API key by value."""
        async with self.get_session() as session:
            result = await session.execute(
                select(APIKey).where(
                    and_(APIKey.key == key, APIKey.is_active == True)
                )
            )
            api_key = result.scalar_one_or_none()
            
            # Update last used timestamp
            if api_key:
                api_key.last_used_at = datetime.utcnow()
                await session.commit()
                
            return api_key
            
    async def create_api_key(self, name: str, description: str = "") -> APIKey:
        """Create new API key."""
        api_key = APIKey(
            key=str(uuid.uuid4()),
            name=name,
            description=description
        )
        
        async with self.get_session() as session:
            session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
            
        logger.info("api_key_created", key_id=api_key.id, name=name)
        return api_key
        
    async def deactivate_api_key(self, key: str) -> bool:
        """Deactivate an API key."""
        async with self.get_session() as session:
            result = await session.execute(
                select(APIKey).where(APIKey.key == key)
            )
            api_key = result.scalar_one_or_none()
            
            if api_key:
                api_key.is_active = False
                await session.commit()
                logger.info("api_key_deactivated", key_id=api_key.id)
                return True
                
        return False
        
    # Search Request Logging
    
    async def log_search_request(
        self,
        request_data: Dict[str, Any],
        response: Optional[UnQuestResponse] = None,
        api_key_id: Optional[int] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SearchRequest:
        """Log a search request for analytics."""
        search_request = SearchRequest(
            request_id=request_data.get("request_id", str(uuid.uuid4())),
            api_key_id=api_key_id,
            query=request_data["query"],
            engines=request_data["engines"],
            max_results=request_data["max_results"],
            language=request_data.get("language", "en"),
            safe_search=request_data.get("safe_search", "moderate"),
            client_ip=client_ip,
            user_agent=user_agent,
            request_headers=request_data.get("headers", {})
        )
        
        if response:
            search_request.search_time_ms = response.search_metadata.search_time_ms
            search_request.total_time_ms = response.processing_time_ms
            search_request.results_count = len(response.results)
            search_request.scraped_count = sum(
                1 for r in response.results if r.scraped_content
            )
            search_request.cache_hit = response.cached
            search_request.cache_key = response.cache_key
            search_request.completed_at = datetime.utcnow()
            
        async with self.get_session() as session:
            session.add(search_request)
            await session.commit()
            await session.refresh(search_request)
            
        return search_request
        
    async def get_search_analytics(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        api_key_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get search analytics for the specified period."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
            
        async with self.get_session() as session:
            # Base query
            base_query = select(SearchRequest).where(
                and_(
                    SearchRequest.created_at >= start_date,
                    SearchRequest.created_at <= end_date
                )
            )
            
            if api_key_id:
                base_query = base_query.where(SearchRequest.api_key_id == api_key_id)
                
            # Get total requests
            total_result = await session.execute(
                select(func.count(SearchRequest.id)).where(
                    and_(
                        SearchRequest.created_at >= start_date,
                        SearchRequest.created_at <= end_date
                    )
                )
            )
            total_requests = total_result.scalar() or 0
            
            # Get cache statistics
            cache_result = await session.execute(
                select(
                    func.count(SearchRequest.id).filter(SearchRequest.cache_hit == True)
                ).where(
                    and_(
                        SearchRequest.created_at >= start_date,
                        SearchRequest.created_at <= end_date
                    )
                )
            )
            cache_hits = cache_result.scalar() or 0
            
            # Get average response times
            timing_result = await session.execute(
                select(
                    func.avg(SearchRequest.search_time_ms),
                    func.avg(SearchRequest.total_time_ms)
                ).where(
                    and_(
                        SearchRequest.created_at >= start_date,
                        SearchRequest.created_at <= end_date,
                        SearchRequest.search_time_ms.isnot(None)
                    )
                )
            )
            avg_search_time, avg_total_time = timing_result.one()
            
            # Get top queries
            top_queries_result = await session.execute(
                select(
                    SearchRequest.query,
                    func.count(SearchRequest.id).label('count')
                ).where(
                    and_(
                        SearchRequest.created_at >= start_date,
                        SearchRequest.created_at <= end_date
                    )
                ).group_by(SearchRequest.query)
                .order_by(desc('count'))
                .limit(10)
            )
            top_queries = [
                {"query": row[0], "count": row[1]} 
                for row in top_queries_result
            ]
            
            # Get engine usage
            engine_stats = {}
            requests_with_engines = await session.execute(
                select(SearchRequest.engines).where(
                    and_(
                        SearchRequest.created_at >= start_date,
                        SearchRequest.created_at <= end_date
                    )
                )
            )
            
            for row in requests_with_engines:
                engines = row[0]
                if engines:
                    for engine in engines:
                        engine_stats[engine] = engine_stats.get(engine, 0) + 1
                        
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_requests": total_requests,
                "cache_hits": cache_hits,
                "cache_hit_rate": (cache_hits / total_requests * 100) if total_requests > 0 else 0,
                "avg_search_time_ms": float(avg_search_time) if avg_search_time else 0,
                "avg_total_time_ms": float(avg_total_time) if avg_total_time else 0,
                "top_queries": top_queries,
                "engine_usage": engine_stats
            }
            
    # Scraping Job Management
    
    async def create_scraping_job(
        self,
        urls: List[str],
        config: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> ScrapingJob:
        """Create a new scraping job."""
        job = ScrapingJob(
            urls=urls,
            config=config,
            webhook_url=webhook_url
        )
        
        async with self.get_session() as session:
            session.add(job)
            await session.commit()
            await session.refresh(job)
            
        logger.info("scraping_job_created", job_id=job.job_id)
        return job
        
    async def update_scraping_job(
        self,
        job_id: str,
        status: str,
        results: Optional[List[Dict]] = None,
        error_message: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Optional[ScrapingJob]:
        """Update scraping job status."""
        async with self.get_session() as session:
            result = await session.execute(
                select(ScrapingJob).where(ScrapingJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if job:
                job.status = status
                job.task_id = task_id
                
                if status == "processing":
                    job.started_at = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    job.completed_at = datetime.utcnow()
                    
                if results:
                    job.results = results
                if error_message:
                    job.error_message = error_message
                    
                await session.commit()
                logger.info("scraping_job_updated", job_id=job_id, status=status)
                
            return job
            
    async def get_scraping_job(self, job_id: str) -> Optional[ScrapingJob]:
        """Get scraping job by ID."""
        async with self.get_session() as session:
            result = await session.execute(
                select(ScrapingJob).where(ScrapingJob.job_id == job_id)
            )
            return result.scalar_one_or_none()
            
    # Error Logging
    
    async def log_error(
        self,
        error_type: str,
        error_message: str,
        request_id: Optional[str] = None,
        error_details: Optional[Dict] = None,
        stack_trace: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        client_ip: Optional[str] = None
    ):
        """Log an error for debugging."""
        error_log = ErrorLog(
            request_id=request_id,
            error_type=error_type,
            error_message=error_message,
            error_details=error_details or {},
            stack_trace=stack_trace,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            client_ip=client_ip
        )
        
        async with self.get_session() as session:
            session.add(error_log)
            await session.commit()
            
        logger.error(
            "error_logged",
            error_type=error_type,
            request_id=request_id,
            endpoint=endpoint
        )
        
    async def get_recent_errors(
        self, 
        limit: int = 100,
        error_type: Optional[str] = None
    ) -> List[ErrorLog]:
        """Get recent errors for monitoring."""
        async with self.get_session() as session:
            query = select(ErrorLog)
            
            if error_type:
                query = query.where(ErrorLog.error_type == error_type)
                
            query = query.order_by(desc(ErrorLog.created_at)).limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()


# Singleton instance
_database_service: Optional[DatabaseService] = None


async def get_database_service() -> DatabaseService:
    """Get or create database service instance."""
    global _database_service
    
    if _database_service is None:
        _database_service = DatabaseService()
        await _database_service.initialize()
        
    return _database_service
