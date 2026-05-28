"""
FastAPI dependencies for dependency injection.
"""
from typing import Optional, Annotated
from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.core.searxng import get_searxng_service, SearXNGService
from app.services.scraping.scraping import get_scraping_service, ContentScrapingService
from app.services.core.cache import get_cache_service, CacheService
from app.services.core.database import get_database_service, DatabaseService
from app.config import get_settings, Settings
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AuthenticatedUser:
    """User context for authenticated requests."""
    user_id: int
    api_key_id: str
    api_key_name: str
    plan_name: str
    search_limit: Optional[int]
    scrape_limit: Optional[int]
    search_used: int
    scrape_used: int
    # Agent sandbox fields
    is_agent_placeholder: bool = False
    is_sandbox_expired: bool = False
    daily_limit: Optional[int] = None
    daily_used: Optional[int] = None
    claim_url: Optional[str] = None
    registration_ip: Optional[str] = None  # For IP-based sandbox limits

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_settings_dependency() -> Settings:
    """Get application settings."""
    return get_settings()


async def get_db_service() -> DatabaseService:
    """Get database service instance."""
    return await get_database_service()


async def get_searxng() -> SearXNGService:
    """Get SearXNG service instance."""
    return await get_searxng_service()


async def get_scraper() -> ContentScrapingService:
    """Get scraping service instance."""
    return await get_scraping_service()


async def get_cache() -> CacheService:
    """Get cache service instance."""
    return await get_cache_service()


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings_dependency),
    db: DatabaseService = Depends(get_db_service)
) -> Optional[str]:
    """
    Verify API key from header or Bearer token.
    
    Returns:
        API key ID if valid, None if no auth required
    """
    # Try X-API-Key header first
    api_key = x_api_key
    
    # Try Bearer token if no X-API-Key
    if not api_key and authorization:
        api_key = authorization.credentials
        
    if not api_key:
        # Check if API keys are configured (legacy static keys)
        if not settings.api_keys:
            # No API keys configured and no key provided, allow access
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # First, try to validate as a user API key (sk_live_*, sk_test_*, sk_*)
    if api_key.startswith("sk_"):
        user_api_key = await db.get_user_api_key_by_key(api_key)
        if user_api_key and user_api_key.is_active:
            # Check expiration
            if user_api_key.expires_at and user_api_key.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Store API key info in request state for logging
            request.state.api_key_id = user_api_key.id
            request.state.api_key_name = user_api_key.name
            request.state.user_id = user_api_key.user_id
            return str(user_api_key.id)
        
    # Fall back to legacy API key validation
    api_key_obj = await db.get_api_key(api_key)
    
    if not api_key_obj:
        logger.warning(
            "invalid_api_key",
            api_key=api_key[:8] + "..." if len(api_key) > 8 else api_key,
            client_ip=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Store API key info in request state for logging
    request.state.api_key_id = api_key_obj.id
    request.state.api_key_name = api_key_obj.name
    
    return str(api_key_obj.id)


async def get_authenticated_user(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings_dependency),
    db: DatabaseService = Depends(get_db_service)
) -> Optional[AuthenticatedUser]:
    """
    Get authenticated user with usage info for tracking.
    
    Returns:
        AuthenticatedUser with plan and usage info, or None if no auth required
    """
    # Try X-API-Key header first
    api_key = x_api_key
    
    # Try Bearer token if no X-API-Key
    if not api_key and authorization:
        api_key = authorization.credentials
        
    if not api_key:
        # Check if API keys are configured (legacy static keys)
        if not settings.api_keys:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = None
    api_key_id = None
    api_key_name = None
    
    # First, try to validate as a user API key (sk_live_*, sk_test_*, sk_*)
    if api_key.startswith("sk_"):
        user_api_key = await db.get_user_api_key_by_key(api_key)
        if user_api_key and user_api_key.is_active:
            # Check expiration
            if user_api_key.expires_at and user_api_key.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Get the user
            user = await db.get_user(user_api_key.user_id)
            api_key_id = str(user_api_key.id)
            api_key_name = user_api_key.name
    
    # Fall back to legacy API key validation if not found
    if not user:
        api_key_obj = await db.get_api_key(api_key)
        
        if not api_key_obj:
            logger.warning(
                "invalid_api_key",
                api_key=api_key[:8] + "..." if len(api_key) > 8 else api_key,
                client_ip=request.client.host if request.client else None
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from legacy API key
        user = await db.get_user_by_api_key(api_key)
        api_key_id = str(api_key_obj.id)
        api_key_name = api_key_obj.name
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for API key"
        )
    
    # Store in request state
    request.state.api_key_id = api_key_id
    request.state.api_key_name = api_key_name
    request.state.user_id = user.id
    
    # Check if this is an agent placeholder (sandbox mode)
    if getattr(user, 'is_agent_placeholder', False):
        now = datetime.utcnow()
        
        # Check if sandbox expired
        is_expired = False
        if user.sandbox_expires_at and now >= user.sandbox_expires_at:
            is_expired = True
            # Mark as expired if not already
            if not getattr(user, 'is_sandbox_expired', False):
                await db.mark_agent_sandbox_expired(user.id)
        
        is_sandbox_expired = is_expired or getattr(user, 'is_sandbox_expired', False)
        
        # Get registration IP for IP-based daily limits
        registration_ip = getattr(user, 'registration_ip', None)
        
        # Get IP-based daily usage (shared across all sandbox agents from same IP)
        if registration_ip:
            daily_used = await db.get_ip_daily_sandbox_usage(registration_ip)
        else:
            # Fallback to per-agent usage if no IP
            daily_used, _ = await db.get_agent_daily_searches(user.id)
        
        # Build claim URL
        claim_code = getattr(user, 'claim_code', None)
        frontend_url = settings.frontend_url or "https://unsearch.dev"
        claim_url = f"{frontend_url}/claim/{claim_code}" if claim_code else None
        
        return AuthenticatedUser(
            user_id=user.id,
            api_key_id=api_key_id,
            api_key_name=api_key_name,
            plan_name="sandbox",
            search_limit=None,  # Sandbox uses daily limits
            scrape_limit=None,
            search_used=0,
            scrape_used=0,
            is_agent_placeholder=True,
            is_sandbox_expired=is_sandbox_expired,
            daily_limit=25,  # SANDBOX_DAILY_LIMIT
            daily_used=daily_used,
            claim_url=claim_url,
            registration_ip=registration_ip
        )
    
    # Regular user - get monthly usage
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage = await db.get_user_usage(user.id, period_start)
    
    # Get plan info from subscription
    plan_name = "free"
    search_limit = 5000  # Default free tier
    scrape_limit = 500
    
    if user.current_subscription:
        plan_name = user.current_subscription.plan_type.value if user.current_subscription.plan_type else "free"
        search_limit = user.current_subscription.search_limit
        scrape_limit = user.current_subscription.scrape_limit
    
    return AuthenticatedUser(
        user_id=user.id,
        api_key_id=api_key_id,
        api_key_name=api_key_name,
        plan_name=plan_name,
        search_limit=search_limit,
        scrape_limit=scrape_limit,
        search_used=usage.search_count if usage else 0,
        scrape_used=usage.scrape_count if usage else 0
    )


async def get_client_info(request: Request) -> dict:
    """Extract client information from request."""
    return {
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "referer": request.headers.get("Referer"),
        "origin": request.headers.get("Origin")
    }


def check_search_limit(auth_user: Optional["AuthenticatedUser"]) -> None:
    """Check if user has exceeded search limit. Raises HTTPException if exceeded."""
    if not auth_user:
        return
    
    # Check for agent sandbox users
    if auth_user.is_agent_placeholder:
        # Check if sandbox expired
        if auth_user.is_sandbox_expired:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "sandbox_expired",
                    "message": "Sandbox access expired after 7 days. Have your human verify to restore access.",
                    "claim_url": auth_user.claim_url,
                    "can_still_claim": True
                }
            )
        
        # Check daily limit (25 queries/day for sandbox)
        if auth_user.daily_limit and auth_user.daily_used is not None:
            if auth_user.daily_used >= auth_user.daily_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "daily_limit_exceeded",
                        "message": f"Daily sandbox limit ({auth_user.daily_limit}) reached. Resets at midnight UTC.",
                        "daily_used": auth_user.daily_used,
                        "daily_limit": auth_user.daily_limit,
                        "claim_url": auth_user.claim_url,
                        "upgrade_hint": "Have your human verify at claim_url to unlock 5,000 queries/month."
                    }
                )
        return
    
    # Regular user - check monthly limit
    if auth_user.search_limit:
        if auth_user.search_used >= auth_user.search_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly search limit ({auth_user.search_limit}) exceeded. "
                       f"Used: {auth_user.search_used}. Upgrade your plan for more queries.",
                headers={"X-Upgrade-URL": "/pricing"}
            )


def check_scrape_limit(auth_user: Optional["AuthenticatedUser"]) -> None:
    """Check if user has exceeded scrape limit. Raises HTTPException if exceeded."""
    if auth_user and auth_user.scrape_limit:
        if auth_user.scrape_used >= auth_user.scrape_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly scrape limit ({auth_user.scrape_limit}) exceeded. "
                       f"Used: {auth_user.scrape_used}. Upgrade your plan for more scrapes.",
                headers={"X-Upgrade-URL": "/pricing"}
            )


async def increment_sandbox_usage(auth_user: Optional[AuthenticatedUser], db: DatabaseService) -> None:
    """Increment daily search count for sandbox agents (IP-based)."""
    if auth_user and auth_user.is_agent_placeholder and not auth_user.is_sandbox_expired:
        if auth_user.registration_ip:
            # Use IP-based tracking
            await db.increment_ip_sandbox_usage(auth_user.user_id, auth_user.registration_ip)
        else:
            # Fallback to per-agent tracking
            await db.increment_agent_daily_searches(auth_user.user_id)


# Type aliases for cleaner dependency injection
ApiKeyDep = Annotated[Optional[str], Depends(verify_api_key)]
AuthUserDep = Annotated[Optional[AuthenticatedUser], Depends(get_authenticated_user)]
SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DatabaseDep = Annotated[DatabaseService, Depends(get_db_service)]
SearxngDep = Annotated[SearXNGService, Depends(get_searxng)]
ScraperDep = Annotated[ContentScrapingService, Depends(get_scraper)]
CacheDep = Annotated[CacheService, Depends(get_cache)]
ClientInfoDep = Annotated[dict, Depends(get_client_info)]
