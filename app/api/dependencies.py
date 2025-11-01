"""
FastAPI dependencies for dependency injection.
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.searxng import get_searxng_service, SearXNGService
from app.services.scraping import get_scraping_service, ContentScrapingService
from app.services.cache import get_cache_service, CacheService
from app.services.database import get_database_service, DatabaseService
from app.config import get_settings, Settings
import structlog

logger = structlog.get_logger(__name__)

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
    # Check if API keys are configured
    if not settings.api_keys:
        # No API keys configured, allow access
        return None
        
    # Try X-API-Key header first
    api_key = x_api_key
    
    # Try Bearer token if no X-API-Key
    if not api_key and authorization:
        api_key = authorization.credentials
        
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Validate API key
    api_key_obj = await db.get_api_key(api_key)
    
    if not api_key_obj:
        logger.warning(
            "invalid_api_key",
            api_key=api_key[:8] + "...",  # Log partial key
            client_ip=request.client.host
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Store API key info in request state for logging
    request.state.api_key_id = api_key_obj.id
    request.state.api_key_name = api_key_obj.name
    
    return api_key_obj.id


async def get_client_info(request: Request) -> dict:
    """Extract client information from request."""
    return {
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "referer": request.headers.get("Referer"),
        "origin": request.headers.get("Origin")
    }


# Type aliases for cleaner dependency injection
ApiKeyDep = Annotated[Optional[str], Depends(verify_api_key)]
SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DatabaseDep = Annotated[DatabaseService, Depends(get_db_service)]
SearxngDep = Annotated[SearXNGService, Depends(get_searxng)]
ScraperDep = Annotated[ContentScrapingService, Depends(get_scraper)]
CacheDep = Annotated[CacheService, Depends(get_cache)]
ClientInfoDep = Annotated[dict, Depends(get_client_info)]
