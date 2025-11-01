"""
Plan-based rate limiting middleware.
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
import structlog
import redis.asyncio as redis

from app.config import get_settings
from app.services.auth_service import AuthService
from app.models.users import User, PlanType

logger = structlog.get_logger(__name__)
settings = get_settings()


class PlanBasedRateLimiter:
    """Rate limiter that considers user subscription plans."""
    
    def __init__(self):
        self.redis_client = None
        self.default_limits = {
            PlanType.FREE: "100/hour",
            PlanType.PRO: "1000/hour",
            PlanType.ENTERPRISE: "10000/hour"
        }
        
    async def initialize(self):
        """Initialize Redis connection."""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True
            )
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _parse_rate_limit(self, limit_str: str) -> Tuple[int, int]:
        """Parse rate limit string (e.g., '100/hour') to count and seconds."""
        parts = limit_str.split('/')
        if len(parts) != 2:
            return 100, 3600  # Default
        
        count = int(parts[0])
        
        period_map = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }
        
        period = parts[1].lower()
        seconds = period_map.get(period, 3600)
        
        return count, seconds
    
    async def check_rate_limit(
        self,
        request: Request,
        user: Optional[User] = None
    ) -> bool:
        """Check if request exceeds rate limit."""
        await self.initialize()
        
        # Determine rate limit based on user plan
        if user:
            # Get user's subscription
            subscription = user.current_subscription
            if subscription and subscription.rate_limit:
                limit_str = subscription.rate_limit
            else:
                limit_str = self.default_limits.get(user.current_plan, "100/hour")
            
            key = f"rate_limit:user:{user.id}"
        else:
            # Anonymous users get minimal rate limit
            limit_str = "10/hour"
            client_ip = get_remote_address(request)
            key = f"rate_limit:ip:{client_ip}"
        
        # Parse limit
        max_requests, period_seconds = self._parse_rate_limit(limit_str)
        
        # Check current count
        current = await self.redis_client.get(key)
        current_count = int(current) if current else 0
        
        if current_count >= max_requests:
            return False
        
        # Increment counter
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, period_seconds)
        await pipe.execute()
        
        # Set rate limit headers
        request.state.rate_limit_limit = max_requests
        request.state.rate_limit_remaining = max_requests - current_count - 1
        request.state.rate_limit_reset = datetime.utcnow() + timedelta(seconds=period_seconds)
        
        return True
    
    async def check_usage_limit(
        self,
        user: User,
        search: bool = False,
        scrape: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Check if user has exceeded monthly usage limits."""
        # Get current month usage
        now = datetime.utcnow()
        month_key = f"usage:{user.id}:{now.year}:{now.month}"
        
        search_key = f"{month_key}:search"
        scrape_key = f"{month_key}:scrape"
        
        # Get current counts
        search_count = await self.redis_client.get(search_key) or 0
        scrape_count = await self.redis_client.get(scrape_key) or 0
        
        search_count = int(search_count)
        scrape_count = int(scrape_count)
        
        # Get limits from subscription
        subscription = user.current_subscription
        
        if subscription:
            search_limit = subscription.search_limit
            scrape_limit = subscription.scrape_limit
        else:
            # Free plan defaults
            search_limit = 1000
            scrape_limit = 10000
        
        # Check limits
        if search:
            if search_limit and search_count >= search_limit:
                return False, f"Monthly search limit ({search_limit}) exceeded"
        
        if scrape:
            if scrape_limit and scrape_count >= scrape_limit:
                return False, f"Monthly scrape limit ({scrape_limit}) exceeded"
        
        return True, None
    
    async def increment_usage(
        self,
        user: User,
        search_count: int = 0,
        scrape_count: int = 0
    ):
        """Increment usage counters."""
        now = datetime.utcnow()
        month_key = f"usage:{user.id}:{now.year}:{now.month}"
        
        pipe = self.redis_client.pipeline()
        
        if search_count > 0:
            search_key = f"{month_key}:search"
            pipe.incrby(search_key, search_count)
            pipe.expire(search_key, 35 * 24 * 3600)  # Expire after 35 days
        
        if scrape_count > 0:
            scrape_key = f"{month_key}:scrape"
            pipe.incrby(scrape_key, scrape_count)
            pipe.expire(scrape_key, 35 * 24 * 3600)
        
        await pipe.execute()
    
    async def get_usage_stats(self, user: User) -> dict:
        """Get current usage statistics."""
        now = datetime.utcnow()
        month_key = f"usage:{user.id}:{now.year}:{now.month}"
        
        search_key = f"{month_key}:search"
        scrape_key = f"{month_key}:scrape"
        
        search_count = await self.redis_client.get(search_key) or 0
        scrape_count = await self.redis_client.get(scrape_key) or 0
        
        subscription = user.current_subscription
        
        if subscription:
            search_limit = subscription.search_limit
            scrape_limit = subscription.scrape_limit
        else:
            search_limit = 1000
            scrape_limit = 10000
        
        return {
            "searches": {
                "used": int(search_count),
                "limit": search_limit,
                "remaining": (search_limit - int(search_count)) if search_limit else None,
                "unlimited": search_limit is None
            },
            "scrapes": {
                "used": int(scrape_count),
                "limit": scrape_limit,
                "remaining": (scrape_limit - int(scrape_count)) if scrape_limit else None,
                "unlimited": scrape_limit is None
            }
        }


# Singleton instance
_rate_limiter: Optional[PlanBasedRateLimiter] = None


async def get_rate_limiter() -> PlanBasedRateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = PlanBasedRateLimiter()
        await _rate_limiter.initialize()
    
    return _rate_limiter


async def rate_limit_middleware(request: Request, call_next):
    """Middleware to enforce rate limits based on user plan."""
    # Skip rate limiting for certain paths
    skip_paths = ["/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"]
    if request.url.path in skip_paths:
        return await call_next(request)
    
    # Skip webhooks
    if "/webhook/" in request.url.path:
        return await call_next(request)
    
    # Get user from request if authenticated
    user = None
    if hasattr(request.state, "user"):
        user = request.state.user
    
    # Check rate limit
    rate_limiter = await get_rate_limiter()
    allowed = await rate_limiter.check_rate_limit(request, user)
    
    if not allowed:
        # Get limit info for error message
        if user:
            subscription = user.current_subscription
            limit_str = subscription.rate_limit if subscription else "100/hour"
        else:
            limit_str = "10/hour"
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limit_str}",
            headers={
                "X-RateLimit-Limit": str(request.state.rate_limit_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": request.state.rate_limit_reset.isoformat(),
                "Retry-After": str(int((request.state.rate_limit_reset - datetime.utcnow()).total_seconds()))
            }
        )
    
    # Add rate limit headers to response
    response = await call_next(request)
    
    if hasattr(request.state, "rate_limit_limit"):
        response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
        response.headers["X-RateLimit-Reset"] = request.state.rate_limit_reset.isoformat()
    
    return response
