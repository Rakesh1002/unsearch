import os
# Set environment variables for testing before any app imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["RATE_LIMIT_STORAGE_URL"] = "memory://"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["SEARXNG_URL"] = "http://localhost:8888"
os.environ["API_KEYS"] = "test-key-1,test-key-2"
os.environ["CLOUDFLARE_AI_ENABLED"] = "false"
os.environ["PUPPETEER_ENABLED"] = "false"

import asyncio
import pytest
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fakeredis import FakeAsyncRedis

from app.main import app
from app.config import Settings, get_settings
from app.models.database import Base, APIKey
from app.services.core.database import DatabaseService
from app.services.core.cache import CacheService
from app.services.core.searxng import SearXNGService
from app.services.scraping.scraping import ContentScrapingService
from app.services.rag.rag import RAGService, VectorStore, EmbeddingService, ResearchSource
from app.models.users import User


# Test settings
@pytest.fixture
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        environment="testing",  # Testing environment
        database_url="postgresql://test:test@localhost:5432/test_db",  # Mock database
        redis_url="redis://localhost:6379/15",
        searxng_url="http://localhost:8888",
        api_keys="test-key-1,test-key-2",  # Use comma-separated string
        rate_limit_enabled=False,
        cache_default_ttl=60,
        _env_file=None  # Don't load .env file
    )


@pytest.fixture
def override_settings(test_settings: Settings, test_db, test_cache, mock_searxng, mock_scraper):
    """Override application settings and dependencies."""
    from app.api.dependencies import get_searxng, get_scraper, get_cache, get_db_service, get_settings_dependency
    app.dependency_overrides[get_settings_dependency] = lambda: test_settings
    app.dependency_overrides[get_db_service] = lambda: test_db
    app.dependency_overrides[get_cache] = lambda: test_cache
    app.dependency_overrides[get_searxng] = lambda: mock_searxng
    app.dependency_overrides[get_scraper] = lambda: mock_scraper
    yield
    app.dependency_overrides.clear()


# Database fixtures
@pytest.fixture
async def test_db(test_settings: Settings) -> AsyncGenerator[DatabaseService, None]:
    """Create test database."""
    from sqlalchemy.pool import NullPool
    from sqlalchemy import event
    # Create SQLite in-memory test engine with shared cache to support concurrency
    engine = create_async_engine(
        "sqlite+aiosqlite:///file:test_db?mode=memory&cache=shared&uri=true",
        poolclass=NullPool,
        connect_args={"timeout": 30},
        echo=False,
        future=True
    )
    

    
    # Keep one connection open to prevent the shared-cache in-memory DB from being destroyed
    keep_alive_conn = await engine.connect()
    
    # Create tables
    from app.models.users import Base as UserBase
    
    # Merge both metadata collections so foreign keys resolve properly
    for table_name, table in list(UserBase.metadata.tables.items()):
        if table_name not in Base.metadata.tables:
            table.to_metadata(Base.metadata)
            
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
    
    # Override singleton _database_service
    import app.services.core.database
    original_db_service = app.services.core.database._database_service
    app.services.core.database._database_service = db_service
    
    # Prepopulate the database with test user and test API keys
    async with db_service.get_session() as session:
        user1 = User(
            id=1,
            email="test@example.com",
            password_hash="fakehash",
            salt="fakesalt",
            is_active=True
        )
        session.add(user1)
        await session.commit()
        
        key1 = APIKey(
            id=1,
            key="test-key-1",
            name="Test Key 1",
            is_active=True,
            user_id=1
        )
        key2 = APIKey(
            id=2,
            key="test-key-2",
            name="Test Key 2",
            is_active=True,
            user_id=1
        )
        session.add(key1)
        session.add(key2)
        await session.commit()
    
    yield db_service
    
    # Restore singleton and cleanup
    app.services.core.database._database_service = original_db_service
    await keep_alive_conn.close()
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
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
    from app.models.responses import SearchResult
    mock = mocker.Mock(spec=SearXNGService)
    default_results = [
        SearchResult(
            rank=1,
            title="Test Result 1",
            url="https://example.com/tutorial",
            snippet="Learn how to scrape websites with Python...",
            engine="google"
        )
    ]
    mock.search.return_value = default_results
    mock.search_with_relevance = mocker.AsyncMock(return_value=(default_results, None))
    mock.get_available_engines.return_value = {"google": {}, "bing": {}, "duckduckgo": {}}
    mock.health_check.return_value = {
        "status": "healthy",
        "latency_ms": 100
    }
    return mock


@pytest.fixture
def mock_scraper(mocker):
    """Mock scraping service."""
    from app.models.responses import ScrapedContent
    mock = mocker.Mock(spec=ContentScrapingService)
    default_scrape = [ScrapedContent(
        url="https://example.com/tutorial",
        title="Python Web Scraping Tutorial",
        text="This is a comprehensive guide to web scraping with Python...",
        images=["https://example.com/img1.jpg"],
        links=["https://example.com/related"],
        extraction_success=True,
        extraction_time_ms=250,
        word_count=1500,
        language_detected="en",
        content_quality_score=0.85,
        metadata={
            "title": "Python Web Scraping Tutorial",
            "description": "Learn web scraping with Python",
            "author": "John Doe",
            "keywords": ["python", "web scraping", "tutorial"]
        }
    )]
    mock.scrape_urls.return_value = default_scrape
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


# RAG Service fixtures
@pytest.fixture
def mock_rag_service(mocker):
    """Mock RAG service."""
    mock = mocker.Mock(spec=RAGService)
    mock.vector_store = VectorStore()
    mock.embedding_service = mocker.Mock(spec=EmbeddingService)
    mock.searxng = mocker.Mock(spec=SearXNGService)
    mock.scraper = mocker.Mock(spec=ContentScrapingService)
    mock._initialized = True
    
    # Default mock returns
    mock.generate_research_queries.return_value = [
        "test query 1",
        "test query 2",
        "test query 3"
    ]
    mock.deep_research.return_value = mocker.AsyncMock()
    mock.search_and_answer.return_value = mocker.AsyncMock()
    mock.semantic_search.return_value = mocker.AsyncMock()
    
    return mock


@pytest.fixture
def mock_embedding_service(mocker):
    """Mock embedding service."""
    mock = mocker.Mock(spec=EmbeddingService)
    mock.generate_embeddings.return_value = [[0.1] * 1536]
    mock.generate_single_embedding.return_value = [0.1] * 1536
    return mock


@pytest.fixture
def test_vector_store():
    """Create a test vector store with sample data."""
    store = VectorStore()
    
    # Add sample vectors
    vectors = [
        ("doc_1", [1.0, 0.0, 0.0] + [0.0] * 1533, {
            "url": "https://example.com/doc1",
            "title": "Document 1",
            "summary": "This is the first document about machine learning."
        }),
        ("doc_2", [0.0, 1.0, 0.0] + [0.0] * 1533, {
            "url": "https://example.com/doc2",
            "title": "Document 2",
            "summary": "This is the second document about data science."
        }),
        ("doc_3", [0.0, 0.0, 1.0] + [0.0] * 1533, {
            "url": "https://example.com/doc3",
            "title": "Document 3",
            "summary": "This is the third document about AI ethics."
        }),
    ]
    
    store.add_vectors("test_corpus", vectors)
    return store


@pytest.fixture
def sample_research_source():
    """Sample research source data."""
    from datetime import datetime
    return ResearchSource(
        url="https://example.com/article",
        title="Sample Article",
        content="This is sample content for testing purposes. It contains information about various topics.",
        summary="A sample article for testing",
        relevance_score=0.85,
        word_count=15,
        metadata={
            "engine": "google",
            "rank": 1
        },
        scraped_at=datetime.utcnow()
    )


@pytest.fixture
def sample_research_request():
    """Sample research request data."""
    return {
        "topic": "machine learning fundamentals",
        "depth": "standard",
        "engines": ["google", "bing"],
        "scrape_content": True,
        "generate_embeddings": True,
        "language": "en"
    }


@pytest.fixture
def sample_quick_search_request():
    """Sample quick search request data."""
    return {
        "query": "what is machine learning",
        "max_sources": 5,
        "scrape_content": True,
        "engines": ["google", "bing"],
        "include_context": True
    }


@pytest.fixture
def sample_semantic_search_request():
    """Sample semantic search request data."""
    return {
        "corpus_id": "test_corpus",
        "query": "neural networks",
        "limit": 10,
        "min_relevance": 0.5
    }


# Fallback benchmark fixture if pytest-benchmark is not installed
try:
    import pytest_benchmark
except ImportError:
    @pytest.fixture(name="benchmark")
    def benchmark_fallback():
        """Fallback benchmark fixture that runs the function synchronously once."""
        def _benchmark(func, *args, **kwargs):
            return func(*args, **kwargs)
        def pedantic(func, args=None, kwargs=None, **setup_kwargs):
            func_args = args or ()
            func_kwargs = kwargs or {}
            setup_func = setup_kwargs.get("setup")
            if setup_func:
                setup_args = setup_func()
                if setup_args:
                    if isinstance(setup_args, tuple):
                        func_args = setup_args + func_args
                    elif isinstance(setup_args, dict):
                        func_kwargs.update(setup_args)
            return func(*func_args, **func_kwargs)
        _benchmark.pedantic = pedantic
        return _benchmark
