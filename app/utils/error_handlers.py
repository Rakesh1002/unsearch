"""
Global error handlers for the UnSearch API.
"""
import traceback
from typing import Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from httpx import HTTPError, TimeoutException
import structlog

from app.config import get_settings
from app.models.responses import ErrorResponse
from app.utils.exceptions import (
    UnSearchException, SearXNGException, ScrapingException,
    CacheException, DatabaseException, UnSearchHTTPException
)

logger = structlog.get_logger(__name__)
settings = get_settings()


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.warning(
        "validation_error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors(),
        client_ip=request.client.host if request.client else None
    )
    
    # Format validation errors
    formatted_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    error_response = ErrorResponse(
        error="ValidationError",
        message="Request validation failed",
        details={"validation_errors": formatted_errors},
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json")
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limiting errors."""
    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else None,
        rate_limit=str(exc)
    )
    
    error_response = ErrorResponse(
        error="RateLimitExceeded",
        message="Rate limit exceeded. Please try again later.",
        details={
            "limit": str(exc),
            "retry_after": getattr(exc, "retry_after", 60)
        },
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response.model_dump(mode="json"),
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))}
    )


async def searxng_exception_handler(request: Request, exc: SearXNGException) -> JSONResponse:
    """Handle SearXNG service errors."""
    logger.error(
        "searxng_error",
        path=request.url.path,
        error=str(exc),
        details=exc.details,
        client_ip=request.client.host if request.client else None
    )
    
    error_response = ErrorResponse(
        error="SearXNGError",
        message="Search service temporarily unavailable",
        details=exc.details if settings.debug else None,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(mode="json"),
        headers={"Retry-After": "60"}
    )


async def scraping_exception_handler(request: Request, exc: ScrapingException) -> JSONResponse:
    """Handle content scraping errors."""
    logger.error(
        "scraping_error",
        path=request.url.path,
        error=str(exc),
        details=exc.details,
        client_ip=request.client.host if request.client else None
    )
    
    error_response = ErrorResponse(
        error="ScrapingError",
        message="Content scraping failed",
        details=exc.details if settings.debug else None,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=error_response.model_dump(mode="json")
    )


async def cache_exception_handler(request: Request, exc: CacheException) -> JSONResponse:
    """Handle cache service errors."""
    logger.error(
        "cache_error",
        path=request.url.path,
        error=str(exc),
        details=exc.details,
        client_ip=request.client.host if request.client else None
    )
    
    # Cache errors are usually non-critical, continue without cache
    error_response = ErrorResponse(
        error="CacheError",
        message="Cache service temporarily unavailable",
        details={"note": "Request processed without caching"} if settings.debug else None,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,  # Continue processing
        content=error_response.model_dump(mode="json")
    )


async def database_exception_handler(request: Request, exc: DatabaseException) -> JSONResponse:
    """Handle database errors."""
    logger.error(
        "database_error",
        path=request.url.path,
        error=str(exc),
        details=exc.details,
        client_ip=request.client.host if request.client else None
    )
    
    error_response = ErrorResponse(
        error="DatabaseError",
        message="Database service temporarily unavailable",
        details=exc.details if settings.debug else None,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(mode="json"),
        headers={"Retry-After": "30"}
    )


async def http_error_handler(request: Request, exc: HTTPError) -> JSONResponse:
    """Handle HTTP client errors (httpx)."""
    logger.error(
        "http_client_error",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
        client_ip=request.client.host if request.client else None
    )
    
    if isinstance(exc, TimeoutException):
        error_code = "RequestTimeout"
        message = "Request timed out"
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    else:
        error_code = "HTTPError"
        message = "External service error"
        status_code = status.HTTP_502_BAD_GATEWAY
    
    error_response = ErrorResponse(
        error=error_code,
        message=message,
        details={"error": str(exc)} if settings.debug else None,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode="json")
    )


async def UnSearch_http_exception_handler(request: Request, exc: UnSearchHTTPException) -> JSONResponse:
    """Handle custom UnSearch HTTP exceptions."""
    logger.warning(
        "UnSearch_http_error",
        path=request.url.path,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        client_ip=request.client.host if request.client else None
    )
    
    error_response = ErrorResponse(
        error=exc.error_code,
        message=exc.message,
        details=exc.details,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
        headers=exc.headers
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        request_id=request_id,
        client_ip=request.client.host if request.client else None,
        stack_trace=traceback.format_exc() if settings.debug else None
    )
    
    # Log to database if possible
    try:
        from app.services.core.database import get_database_service
        db = await get_database_service()
        await db.log_error(
            error_type=type(exc).__name__,
            error_message=str(exc),
            request_id=request_id,
            stack_trace=traceback.format_exc(),
            endpoint=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else None
        )
    except:
        # Don't fail if database logging fails
        pass
    
    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        details={
            "error": str(exc),
            "type": type(exc).__name__
        } if settings.debug else None,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json")
    )


# Exception handler mapping
EXCEPTION_HANDLERS = {
    RequestValidationError: validation_exception_handler,
    RateLimitExceeded: rate_limit_exception_handler,
    SearXNGException: searxng_exception_handler,
    ScrapingException: scraping_exception_handler,
    CacheException: cache_exception_handler,
    DatabaseException: database_exception_handler,
    HTTPError: http_error_handler,
    TimeoutException: http_error_handler,
    UnSearchHTTPException: UnSearch_http_exception_handler,
    Exception: generic_exception_handler,
}


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    for exception_class, handler in EXCEPTION_HANDLERS.items():
        app.add_exception_handler(exception_class, handler)
