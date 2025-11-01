"""
Main FastAPI application entry point.
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.config import get_settings
from app.api.v1 import search, auth, billing
from app.api.v1 import enhanced_search
from app.api.v2 import advanced_endpoints
from app.models.responses import ErrorResponse
from app.services.database import get_database_service
from app.services.searxng import get_searxng_service
from app.services.scraping import get_scraping_service
from app.services.cache import get_cache_service
from app.utils.error_handlers import register_exception_handlers
from app.utils.security import SecurityHeaders

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if get_settings().debug else structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(get_settings().log_level),
)

logger = structlog.get_logger()
settings = get_settings()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds', 
    'HTTP request duration',
    ['method', 'endpoint']
)
SEARCH_REQUESTS = Counter(
    'search_requests_total',
    'Total search requests',
    ['engine', 'cached']
)
SCRAPING_REQUESTS = Counter(
    'scraping_requests_total',
    'Total scraping requests',
    ['success']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("application_startup", version=settings.version, environment=settings.environment)
    
    # Initialize services
    db_service = await get_database_service()
    searxng_service = await get_searxng_service()
    scraping_service = await get_scraping_service()
    cache_service = await get_cache_service()
    
    # Store services in app state for cleanup
    app.state.db = db_service
    app.state.searxng = searxng_service
    app.state.scraper = scraping_service
    app.state.cache = cache_service
    
    # Store startup time for uptime calculation
    app.state.startup_time = time.time()
    
    logger.info("services_initialized")
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    
    # Cleanup services
    await app.state.searxng.close()
    await app.state.scraper.close()
    await app.state.cache.close()
    await app.state.db.close()
    
    logger.info("services_closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url=settings.docs_url,
    openapi_url=settings.openapi_url,
    lifespan=lifespan,
    description="Privacy-respecting web search and scraping API powered by SearXNG and BeautifulSoup4",
    contact={
        "name": "UnSearch API",
        "url": "https://github.com/UnSearch/api",
        "email": "support@UnSearch.io"
    },
    license_info={
        "name": "AGPL-3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html"
    }
)

# Configure rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    enabled=settings.rate_limit_enabled,
    storage_uri=settings.rate_limit_storage_url
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Register exception handlers
register_exception_handlers(app)

# Add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.UnSearch.io", "localhost"]
    )


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware for request logging and metrics.
    """
    # Generate request ID
    request_id = request.headers.get("X-Request-ID", str(time.time()))
    
    # Bind request context for structured logging
    bind_contextvars(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else None
    )
    
    # Track request duration
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Update metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        
        # Add security headers
        security_headers = SecurityHeaders.get_headers()
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Log request
        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_seconds=duration
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(
            "http_request_error",
            error=str(e),
            duration_seconds=duration
        )
        
        raise
        
    finally:
        clear_contextvars()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    """
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    
    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        request_id=request.headers.get("X-Request-ID"),
        details={"error": str(exc)} if settings.debug else None
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


# Include routers
app.include_router(
    search.router,
    prefix=settings.api_prefix
)

app.include_router(
    auth.router,
    prefix=settings.api_prefix
)

app.include_router(
    billing.router,
    prefix=settings.api_prefix
)

# Enhanced search endpoints (v1)
app.include_router(
    enhanced_search.router,
    prefix=settings.api_prefix
)

# Advanced endpoints (v2)
app.include_router(
    advanced_endpoints.router,
    prefix=settings.api_prefix
)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": settings.docs_url,
        "health": "/health"
    }


@app.get("/health", include_in_schema=False)
async def health():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.enable_metrics:
        return {"error": "Metrics disabled"}
        
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    )
