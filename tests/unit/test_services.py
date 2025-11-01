"""
Unit tests for services.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx
import redis.asyncio as redis

from app.services.searxng import SearXNGService
from app.services.scraping import ContentScrapingService
from app.services.cache import CacheService
from app.services.database import DatabaseService
from app.models.requests import SearchScrapeRequest, ScrapingConfig
from app.models.responses import SearchResult, ServiceHealth
from app.config import get_settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = get_settings()
    settings.searxng_url = "http://test-searxng:8080"
    settings.redis_url = "redis://test-redis:6379"
    settings.database_url = "postgresql://test:test@test-db:5432/test"
    return settings


class TestSearXNGService:
    """Test SearXNG service."""
    
    @pytest.fixture
    async def searxng_service(self):
        """Create SearXNG service for testing."""
        service = SearXNGService()
        yield service
        await service.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, searxng_service):
        """Test service initialization."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=Mock(cookies={}))
            await searxng_service.initialize()
            assert searxng_service._client is not None
    
    @pytest.mark.asyncio
    async def test_search_success(self, searxng_service):
        """Test successful search."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                    "engine": "google"
                }
            ]
        }
        mock_response.elapsed.total_seconds.return_value = 1.5
        
        with patch.object(searxng_service, '_client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            
            results = await searxng_service.search(
                query="test query",
                engines=["google"],
                language="en"
            )
            
            assert len(results) == 1
            assert results[0].title == "Test Result"
            assert results[0].url == "https://example.com"
            assert results[0].engine == "google"
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, searxng_service):
        """Test search error handling."""
        with patch.object(searxng_service, '_client') as mock_client:
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
            
            with pytest.raises(httpx.HTTPError):
                await searxng_service.search(
                    query="test query",
                    engines=["google"]
                )
    
    @pytest.mark.asyncio
    async def test_health_check(self, searxng_service):
        """Test health check."""
        mock_response = Mock()
        mock_response.headers = {"X-SearXNG-Version": "1.0.0"}
        
        with patch.object(searxng_service, '_client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            with patch.object(searxng_service, 'search', return_value=[]):
                
                health = await searxng_service.health_check()
                
                assert health.status == "healthy"
                assert health.latency_ms > 0
    
    def test_generate_cache_key(self, searxng_service):
        """Test cache key generation."""
        key1 = searxng_service.generate_cache_key("test query", ["google"])
        key2 = searxng_service.generate_cache_key("test query", ["google"])
        key3 = searxng_service.generate_cache_key("different query", ["google"])
        
        assert key1 == key2  # Same inputs should produce same key
        assert key1 != key3  # Different inputs should produce different keys


class TestContentScrapingService:
    """Test content scraping service."""
    
    @pytest.fixture
    async def scraping_service(self):
        """Create scraping service for testing."""
        service = ContentScrapingService()
        yield service
        await service.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, scraping_service):
        """Test service initialization."""
        await scraping_service.initialize()
        assert scraping_service._client is not None
    
    @pytest.mark.asyncio
    async def test_scrape_single_url_success(self, scraping_service):
        """Test successful URL scraping."""
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Test Heading</h1>
            <p>Test content paragraph.</p>
            <img src="/test.jpg" alt="Test image">
            <a href="/test-link">Test link</a>
        </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(scraping_service, '_client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await scraping_service._scrape_url("https://example.com")
            
            assert result.extraction_success is True
            assert result.title == "Test Page"
            assert "Test content paragraph" in result.text
            assert result.word_count > 0
            assert result.content_quality_score > 0
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_urls(self, scraping_service):
        """Test scraping multiple URLs."""
        urls = ["https://example1.com", "https://example2.com"]
        
        html_content = "<html><body><p>Test content</p></body></html>"
        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(scraping_service, '_client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            
            results = await scraping_service.scrape_urls(urls)
            
            assert len(results) == 2
            assert all(result.extraction_success for result in results)
    
    @pytest.mark.asyncio
    async def test_robots_txt_check(self, scraping_service):
        """Test robots.txt checking."""
        robots_content = """
        User-agent: *
        Disallow: /admin
        Allow: /
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = robots_content
        
        with patch.object(scraping_service, '_client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            
            # Should allow normal pages
            allowed = await scraping_service._check_robots_txt("https://example.com/page")
            assert allowed is True
            
            # Should disallow admin pages
            disallowed = await scraping_service._check_robots_txt("https://example.com/admin/secret")
            assert disallowed is False


class TestCacheService:
    """Test cache service."""
    
    @pytest.fixture
    async def cache_service(self):
        """Create cache service for testing."""
        service = CacheService()
        yield service
        await service.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, cache_service):
        """Test service initialization."""
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool:
            with patch('redis.asyncio.Redis') as mock_redis:
                mock_redis.return_value.ping = AsyncMock()
                await cache_service.initialize()
                assert cache_service._client is not None
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, cache_service):
        """Test cache set and get operations."""
        from app.models.responses import SearchScrapeResponse, SearchMetadata
        
        # Mock Redis client
        mock_redis = AsyncMock()
        cache_service._client = mock_redis
        
        # Test data
        response = SearchScrapeResponse(
            search_metadata=SearchMetadata(
                query="test",
                engines_used=["google"],
                engines_succeeded=["google"],
                engines_failed=[],
                total_results_found=1,
                results_returned=1,
                search_time_ms=100
            ),
            results=[],
            processing_time_ms=200,
            cached=False,
            total_results=1,
            request_id="test-123"
        )
        
        # Test cache set
        await cache_service.set_search_results("test-key", response, 3600)
        mock_redis.setex.assert_called_once()
        
        # Test cache get
        mock_redis.get = AsyncMock(return_value=b'{"test": "data"}')
        cached = await cache_service.get_search_results("test-key")
        # Result will be None due to serialization mocking, but operation should complete
        mock_redis.get.assert_called_once_with("test-key")
    
    def test_generate_cache_key(self, cache_service):
        """Test cache key generation."""
        request = SearchScrapeRequest(
            query="test query",
            engines=["google"],
            max_results=10
        )
        
        key1 = cache_service.generate_cache_key(request)
        key2 = cache_service.generate_cache_key(request)
        
        assert key1 == key2  # Same request should produce same key
        assert key1.startswith("search:")
        assert len(key1) > 20  # Should be reasonably long


class TestDatabaseService:
    """Test database service."""
    
    @pytest.fixture
    async def db_service(self):
        """Create database service for testing."""
        service = DatabaseService()
        yield service
        await service.close()
    
    @pytest.mark.asyncio
    async def test_initialize(self, db_service):
        """Test service initialization."""
        with patch.object(db_service.engine, 'begin') as mock_begin:
            mock_conn = AsyncMock()
            mock_begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_begin.return_value.__aexit__ = AsyncMock()
            mock_conn.run_sync = AsyncMock()
            
            await db_service.initialize()
            mock_begin.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_api_key_operations(self, db_service):
        """Test API key database operations."""
        from app.models.database import APIKey
        
        # Mock session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = APIKey(
            id=1,
            key="test-key",
            name="Test Key",
            is_active=True
        )
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch.object(db_service, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock()
            
            api_key = await db_service.get_api_key("test-key")
            assert api_key is not None
            assert api_key.key == "test-key"
    
    @pytest.mark.asyncio
    async def test_error_logging(self, db_service):
        """Test error logging."""
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch.object(db_service, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock()
            
            await db_service.log_error(
                error_type="TestError",
                error_message="Test error message",
                request_id="test-123"
            )
            
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_service_integration():
    """Test service integration."""
    # This would test how services work together
    # For now, just verify they can be imported and initialized
    from app.services.searxng import get_searxng_service
    from app.services.scraping import get_scraping_service
    from app.services.cache import get_cache_service
    from app.services.database import get_database_service
    
    # These should not raise exceptions
    assert get_searxng_service is not None
    assert get_scraping_service is not None
    assert get_cache_service is not None
    assert get_database_service is not None
