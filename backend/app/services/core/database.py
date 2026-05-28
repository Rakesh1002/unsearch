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
    ScrapingJob, ScrapeRequest, CacheEntry, ErrorLog
)
from app.models.responses import UnSearchResponse
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
            pool_recycle=settings.database_pool_recycle,  # Recycle connections to handle cloud DB idle timeouts
            pool_pre_ping=settings.database_pool_pre_ping,  # Check connection validity before use
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
    
    async def get_user_by_api_key(self, key: str):
        """Get user associated with an API key."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(APIKey).where(
                    and_(APIKey.key == key, APIKey.is_active == True)
                )
            )
            api_key = result.scalar_one_or_none()
            
            if not api_key or not api_key.user_id:
                return None
            
            # Get user with subscription
            user_result = await session.execute(
                select(User).where(User.id == api_key.user_id)
            )
            return user_result.scalar_one_or_none()
            
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
        response: Optional[UnSearchResponse] = None,
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
    
    async def log_scraping_request(
        self,
        request_data: Dict[str, Any],
        response: Optional[Dict[str, Any]] = None,
        api_key_id: Optional[int] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None
    ) -> ScrapeRequest:
        """Log a scraping request for analytics."""
        urls = request_data.get("urls", [])
        # Convert HttpUrl objects to strings if needed
        url_list = [str(url) for url in urls] if urls else []
        
        # Serialize config to make it JSON-safe (convert HttpUrl objects, etc.)
        def serialize_value(v):
            # Check for Pydantic URL types (HttpUrl, AnyUrl, etc.)
            type_name = type(v).__name__
            if type_name in ('HttpUrl', 'AnyUrl', 'Url') or 'Url' in type_name:
                return str(v)
            if hasattr(v, 'model_dump'):  # Pydantic model
                return v.model_dump(mode='json')
            if isinstance(v, dict):
                return {k: serialize_value(val) for k, val in v.items()}
            if isinstance(v, list):
                return [serialize_value(item) for item in v]
            return v
        
        serialized_config = serialize_value(request_data)
        
        scrape_request = ScrapeRequest(
            request_id=request_data.get("request_id", str(uuid.uuid4())),
            api_key_id=api_key_id,
            urls=url_list,
            url_count=len(url_list),
            config=serialized_config,
            extraction_strategy=request_data.get("extraction_strategy", "none"),
            client_ip=client_ip,
            user_agent=user_agent,
            error_message=error
        )
        
        if response:
            metadata = response.get("metadata", {})
            scrape_request.successful_scrapes = metadata.get("successful_scrapes", 0)
            scrape_request.failed_scrapes = metadata.get("total_urls", 0) - metadata.get("successful_scrapes", 0)
            scrape_request.processing_time_ms = metadata.get("processing_time_ms")
            scrape_request.completed_at = datetime.utcnow()
            
            # Calculate total content length
            scraped_content = response.get("scraped_content", [])
            total_length = sum(
                len(c.get("text", "") or "") 
                for c in scraped_content 
                if isinstance(c, dict)
            )
            scrape_request.total_content_length = total_length
            
        async with self.get_session() as session:
            session.add(scrape_request)
            await session.commit()
            await session.refresh(scrape_request)
            
        return scrape_request
        
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

    # ==================== User Management ====================
    
    async def get_user_by_email(self, email: str):
        """Get user by email address."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.subscriptions))
                .options(selectinload(User.api_keys))
                .options(selectinload(User.usage_records))
                .where(User.email == email)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int):
        """Get user by ID."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.subscriptions))
                .options(selectinload(User.api_keys))
                .options(selectinload(User.usage_records))
                .where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    # Alias for get_user_by_id for compatibility
    async def get_user(self, user_id: int):
        """Get user by ID (alias for get_user_by_id)."""
        return await self.get_user_by_id(user_id)
    
    async def get_user_by_stripe_customer(self, customer_id: str):
        """Get user by Stripe customer ID."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.subscriptions))
                .options(selectinload(User.api_keys))
                .options(selectinload(User.usage_records))
                .where(User.stripe_customer_id == customer_id)
            )
            return result.scalar_one_or_none()
    
    async def create_user(self, user):
        """Create a new user."""
        async with self.get_session() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user
    
    async def update_user(self, user):
        """Update user record."""
        from app.models.users import User
        async with self.get_session() as session:
            # Merge the detached object into the session
            merged = await session.merge(user)
            await session.commit()
            await session.refresh(merged)
        return merged

    async def delete_user(self, user_id: int) -> bool:
        """Permanently delete a user and all associated data."""
        from app.models.users import User, UserAPIKey, Subscription, Invoice, UsageRecord
        async with self.get_session() as session:
            # Get the user first
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False
            
            # Delete associated data in order (respecting foreign keys)
            # 1. Delete usage records
            await session.execute(
                UsageRecord.__table__.delete().where(UsageRecord.user_id == user_id)
            )
            
            # 2. Delete invoices
            await session.execute(
                Invoice.__table__.delete().where(Invoice.user_id == user_id)
            )
            
            # 3. Delete subscriptions
            await session.execute(
                Subscription.__table__.delete().where(Subscription.user_id == user_id)
            )
            
            # 4. Delete API keys
            await session.execute(
                UserAPIKey.__table__.delete().where(UserAPIKey.user_id == user_id)
            )
            
            # 5. Finally delete the user
            await session.delete(user)
            await session.commit()
            
            logger.info("user_deleted", user_id=user_id)
            return True

    # ==================== User API Keys ====================
    
    async def get_user_api_keys(self, user_id: int):
        """Get all API keys for a user."""
        from app.models.users import UserAPIKey
        async with self.get_session() as session:
            result = await session.execute(
                select(UserAPIKey).where(
                    and_(UserAPIKey.user_id == user_id, UserAPIKey.is_active == True)
                ).order_by(desc(UserAPIKey.created_at))
            )
            return result.scalars().all()
    
    async def get_user_api_key_by_key(self, key: str):
        """Get API key by key value."""
        from app.models.users import UserAPIKey
        async with self.get_session() as session:
            result = await session.execute(
                select(UserAPIKey).where(
                    and_(UserAPIKey.key == key, UserAPIKey.is_active == True)
                )
            )
            api_key = result.scalar_one_or_none()
            if api_key:
                api_key.last_used_at = datetime.utcnow()
                api_key.request_count = (api_key.request_count or 0) + 1
                await session.commit()
            return api_key
    
    async def create_user_api_key(self, api_key):
        """Create a new user API key."""
        async with self.get_session() as session:
            session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
        return api_key
    
    async def delete_api_key(self, key_id: int, user_id: int) -> bool:
        """Soft delete (deactivate) an API key."""
        from app.models.users import UserAPIKey
        async with self.get_session() as session:
            result = await session.execute(
                select(UserAPIKey).where(
                    and_(UserAPIKey.id == key_id, UserAPIKey.user_id == user_id)
                )
            )
            api_key = result.scalar_one_or_none()
            if api_key:
                api_key.is_active = False
                await session.commit()
                return True
        return False
    
    async def get_api_key_by_value(self, key: str):
        """Get user API key by key value (alias for get_user_api_key_by_key)."""
        return await self.get_user_api_key_by_key(key)
    
    async def update_api_key(self, api_key):
        """Update a user API key."""
        from app.models.users import UserAPIKey
        async with self.get_session() as session:
            # Merge the detached object
            merged = await session.merge(api_key)
            await session.commit()
            await session.refresh(merged)
        return merged

    # ==================== Plans ====================
    
    async def get_active_plans(self):
        """Get all active subscription plans."""
        from app.models.users import Plan
        async with self.get_session() as session:
            result = await session.execute(
                select(Plan).where(
                    and_(Plan.is_active == True, Plan.is_visible == True)
                ).order_by(Plan.price)
            )
            return result.scalars().all()
    
    async def get_plan_by_name(self, name: str):
        """Get plan by name."""
        from app.models.users import Plan
        async with self.get_session() as session:
            result = await session.execute(
                select(Plan).where(Plan.name == name)
            )
            return result.scalar_one_or_none()
    
    async def get_plan_by_price_id(self, price_id: str):
        """Get plan by Stripe price ID."""
        from app.models.users import Plan
        async with self.get_session() as session:
            result = await session.execute(
                select(Plan).where(Plan.stripe_price_id == price_id)
            )
            return result.scalar_one_or_none()
    
    async def create_plan(self, plan):
        """Create a new plan."""
        async with self.get_session() as session:
            session.add(plan)
            await session.commit()
            await session.refresh(plan)
        return plan

    # ==================== Subscriptions ====================
    
    async def create_subscription(self, subscription):
        """Create a new subscription."""
        async with self.get_session() as session:
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
        return subscription
    
    async def update_subscription(self, subscription):
        """Update subscription record."""
        async with self.get_session() as session:
            merged = await session.merge(subscription)
            await session.commit()
            await session.refresh(merged)
        return merged
    
    async def get_subscription_by_stripe_id(self, stripe_subscription_id: str):
        """Get subscription by Stripe subscription ID."""
        from app.models.users import Subscription
        async with self.get_session() as session:
            result = await session.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_subscription_id
                )
            )
            return result.scalar_one_or_none()
    
    async def get_subscription_by_stripe_customer(self, customer_id: str):
        """Get active subscription by Stripe customer ID."""
        from app.models.users import Subscription, User, SubscriptionStatus
        async with self.get_session() as session:
            result = await session.execute(
                select(Subscription).join(User).where(
                    and_(
                        User.stripe_customer_id == customer_id,
                        Subscription.status == SubscriptionStatus.ACTIVE
                    )
                )
            )
            return result.scalar_one_or_none()

    # ==================== Usage Records ====================
    
    async def get_user_usage(self, user_id: int, period_start: datetime):
        """Get usage record for a user and period."""
        from app.models.users import UsageRecord
        async with self.get_session() as session:
            result = await session.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.user_id == user_id,
                        UsageRecord.period_start == period_start
                    )
                )
            )
            return result.scalar_one_or_none()
    
    async def create_usage_record(self, usage_record):
        """Create a new usage record."""
        async with self.get_session() as session:
            session.add(usage_record)
            await session.commit()
            await session.refresh(usage_record)
        return usage_record
    
    async def update_usage_record(self, usage_record):
        """Update usage record."""
        async with self.get_session() as session:
            merged = await session.merge(usage_record)
            await session.commit()
            await session.refresh(merged)
        return merged
    
    async def reset_user_usage(self, user_id: int):
        """Reset usage for a new billing period (called on invoice.paid)."""
        # This creates a new usage record for the new period
        pass  # The existing period record is kept for history

    # ==================== Invoices ====================
    
    async def get_user_invoices(self, user_id: int, limit: int = 10):
        """Get invoices for a user."""
        from app.models.users import Invoice
        async with self.get_session() as session:
            result = await session.execute(
                select(Invoice).where(Invoice.user_id == user_id)
                .order_by(desc(Invoice.created_at))
                .limit(limit)
            )
            return result.scalars().all()
    
    async def get_invoice_by_stripe_id(self, stripe_invoice_id: str):
        """Get invoice by Stripe invoice ID."""
        from app.models.users import Invoice
        async with self.get_session() as session:
            result = await session.execute(
                select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
            )
            return result.scalar_one_or_none()
    
    async def create_invoice(self, invoice):
        """Create a new invoice."""
        async with self.get_session() as session:
            session.add(invoice)
            await session.commit()
            await session.refresh(invoice)
        return invoice
    
    async def update_invoice(self, invoice):
        """Update invoice record."""
        async with self.get_session() as session:
            merged = await session.merge(invoice)
            await session.commit()
            await session.refresh(merged)
        return merged

    # ==================== Webhook Events ====================
    
    async def get_webhook_event(self, stripe_event_id: str):
        """Get webhook event by Stripe event ID."""
        from app.models.users import WebhookEvent
        async with self.get_session() as session:
            result = await session.execute(
                select(WebhookEvent).where(
                    WebhookEvent.stripe_event_id == stripe_event_id
                )
            )
            return result.scalar_one_or_none()
    
    async def create_webhook_event(self, stripe_event_id: str, event_type: str, data: dict):
        """Create a new webhook event record."""
        from app.models.users import WebhookEvent
        event = WebhookEvent(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            data=data
        )
        async with self.get_session() as session:
            session.add(event)
            await session.commit()
            await session.refresh(event)
        return event
    
    async def update_webhook_event(self, event):
        """Update webhook event record."""
        async with self.get_session() as session:
            merged = await session.merge(event)
            await session.commit()
            await session.refresh(merged)
        return merged

    # ==================== Agent Self-Registration ====================
    
    async def get_user_by_claim_code(self, claim_code: str):
        """Get user (agent placeholder) by claim code."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.subscriptions))
                .options(selectinload(User.api_keys))
                .where(User.claim_code == claim_code)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_agent_name(self, agent_name: str):
        """Get user (agent placeholder) by agent name."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.subscriptions))
                .options(selectinload(User.api_keys))
                .where(User.agent_name == agent_name)
            )
            return result.scalar_one_or_none()
    
    async def increment_agent_daily_searches(self, user_id: int) -> int:
        """Increment daily search count for agent. Returns new count."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                # Check if we need to reset daily counter
                now = datetime.utcnow()
                if user.daily_reset_at is None or now >= user.daily_reset_at:
                    # Reset at midnight UTC
                    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    user.daily_searches_used = 1
                    user.daily_reset_at = tomorrow
                else:
                    user.daily_searches_used = (user.daily_searches_used or 0) + 1
                await session.commit()
                return user.daily_searches_used
            return 0
    
    async def get_agent_daily_searches(self, user_id: int) -> tuple[int, datetime]:
        """Get current daily search count and reset time for agent."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                now = datetime.utcnow()
                # Check if counter should be reset
                if user.daily_reset_at is None or now >= user.daily_reset_at:
                    return 0, (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                return user.daily_searches_used or 0, user.daily_reset_at
            return 0, datetime.utcnow()
    
    async def mark_agent_sandbox_expired(self, user_id: int):
        """Mark an agent's sandbox as expired."""
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.is_sandbox_expired = True
                await session.commit()
    
    async def get_unclaimed_agent_by_ip(self, ip_address: str):
        """Get an unclaimed agent placeholder by IP address.
        
        Returns the first unclaimed agent registered from this IP, or None.
        Used to enforce one-unclaimed-agent-per-IP rule.
        """
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.api_keys))
                .where(
                    and_(
                        User.is_agent_placeholder == True,
                        User.registration_ip == ip_address
                    )
                )
                .order_by(User.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
    
    async def get_ip_daily_sandbox_usage(self, ip_address: str) -> int:
        """Get total daily sandbox searches used by all agents from an IP.
        
        This enforces a shared daily limit across all sandbox agents from the same IP,
        preventing abuse by registering multiple agents.
        """
        from app.models.users import User
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with self.get_session() as session:
            # Sum daily_searches_used for all sandbox agents from this IP
            # that have been reset today (daily_reset_at > today_start)
            result = await session.execute(
                select(func.coalesce(func.sum(User.daily_searches_used), 0)).where(
                    and_(
                        User.is_agent_placeholder == True,
                        User.registration_ip == ip_address,
                        or_(
                            User.daily_reset_at == None,
                            User.daily_reset_at > today_start
                        )
                    )
                )
            )
            return result.scalar() or 0
    
    async def increment_ip_sandbox_usage(self, user_id: int, ip_address: str) -> int:
        """Increment daily search count for a sandbox agent.
        
        Returns the new IP-wide daily usage count.
        """
        from app.models.users import User
        async with self.get_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                # Check if we need to reset daily counter
                now = datetime.utcnow()
                if user.daily_reset_at is None or now >= user.daily_reset_at:
                    # Reset at midnight UTC
                    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    user.daily_searches_used = 1
                    user.daily_reset_at = tomorrow
                else:
                    user.daily_searches_used = (user.daily_searches_used or 0) + 1
                await session.commit()
            
            # Return IP-wide usage
            return await self.get_ip_daily_sandbox_usage(ip_address)


# Singleton instance
_database_service: Optional[DatabaseService] = None


async def get_database_service() -> DatabaseService:
    """Get or create database service instance."""
    global _database_service
    
    if _database_service is None:
        _database_service = DatabaseService()
        await _database_service.initialize()
        
    return _database_service
