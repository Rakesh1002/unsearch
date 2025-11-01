"""
Pytest configuration and fixtures.
"""
import asyncio
import pytest
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fakeredis import FakeAsyncRedis

from app.main import app
from app.config import Settings, get_settings
from app.models.database import Base
from app.services.database import DatabaseService
from app.services.cache import CacheService
from app.services.searxng import SearXNGService
from app.services.scraping import ContentScrapingService


# Test settings
@pytest.fixture
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        environment="testing",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        searxng_url="http://localhost:8888",
        api_keys=["test-key-1", "test-key-2"],
        rate_limit_enabled=False,
        cache_default_ttl=60
    )


@pytest.fixture
def override_settings(test_settings: Settings):
    """Override application settings."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


# Database fixtures
@pytest.fixture
async def test_db(test_settings: Settings) -> AsyncGenerator[DatabaseService, None]:
    """Create test database."""
    # Create test engine
    engine = create_async_engine(
        str(test_settings.database_url),
        echo=False,
        future=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create service
    db_service = DatabaseService()
    db_service.engine = engine
    db_service.async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    yield db_service
    
    # Cleanup
    await engine.dispose()


# Cache fixtures
@pytest.fixture
async def test_cache() -> AsyncGenerator[CacheService, None]:
    """Create test cache service with fake Redis."""
    cache_service = CacheService()
    cache_service._client = FakeAsyncRedis()
    
    yield cache_service
    
    await cache_service.close()


# HTTP client fixtures
@pytest.fixture
async def client(override_settings) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def authenticated_client(client: AsyncClient) -> AsyncClient:
    """Create authenticated test client."""
    client.headers["X-API-Key"] = "test-key-1"
    return client


# Mock service fixtures
@pytest.fixture
def mock_searxng(mocker):
    """Mock SearXNG service."""
    mock = mocker.Mock(spec=SearXNGService)
    mock.search.return_value = []
    mock.get_available_engines.return_value = {}
    mock.health_check.return_value = {
        "status": "healthy",
        "latency_ms": 100
    }
    return mock


@pytest.fixture
def mock_scraper(mocker):
    """Mock scraping service."""
    mock = mocker.Mock(spec=ContentScrapingService)
    mock.scrape_urls.return_value = []
    return mock


# Event loop configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test data fixtures
@pytest.fixture
def sample_search_request():
    """Sample search request data."""
    return {
        "query": "Python web scraping",
        "engines": ["google", "bing"],
        "max_results": 10,
        "scrape_content": True,
        "language": "en",
        "safe_search": "moderate"
    }


@pytest.fixture
def sample_search_result():
    """Sample search result data."""
    return {
        "rank": 1,
        "title": "Python Web Scraping Tutorial",
        "url": "https://example.com/tutorial",
        "snippet": "Learn how to scrape websites with Python...",
        "engine": "google"
    }


@pytest.fixture
def sample_scraped_content():
    """Sample scraped content data."""
    return {
        "url": "https://example.com/tutorial",
        "title": "Python Web Scraping Tutorial",
        "text": "This is a comprehensive guide to web scraping with Python...",
        "images": ["https://example.com/img1.jpg"],
        "links": ["https://example.com/related"],
        "extraction_success": True,
        "extraction_time_ms": 250,
        "word_count": 1500,
        "language_detected": "en",
        "content_quality_score": 0.85,
        "metadata": {
            "title": "Python Web Scraping Tutorial",
            "description": "Learn web scraping with Python",
            "author": "John Doe",
            "keywords": ["python", "web scraping", "tutorial"]
        }
    }
