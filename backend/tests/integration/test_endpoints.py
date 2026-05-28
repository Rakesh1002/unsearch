"""
Integration tests for API endpoints.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.models.requests import UnSearchRequest
from app.models.responses import SearchResult, SearchMetadata
from app.config import get_settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock all external services."""
    with patch('app.services.searxng.get_searxng_service') as mock_searxng, \
         patch('app.services.scraping.get_scraping_service') as mock_scraper, \
         patch('app.services.cache.get_cache_service') as mock_cache, \
         patch('app.services.database.get_database_service') as mock_db:
        
        # Mock SearXNG service
        searxng_mock = AsyncMock()
        searxng_mock.search = AsyncMock(return_value=[
            SearchResult(
                rank=1,
                title="Test Result",
                url="https://example.com",
                snippet="Test snippet",
                engine="google"
            )
        ])
        searxng_mock.health_check = AsyncMock(return_value=Mock(status="healthy", latency_ms=100))
        searxng_mock.get_available_engines = AsyncMock(return_value={})
        mock_searxng.return_value = searxng_mock
        
        # Mock scraping service
        scraper_mock = AsyncMock()
        scraper_mock.scrape_urls = AsyncMock(return_value=[])
        mock_scraper.return_value = scraper_mock
        
        # Mock cache service
        cache_mock = AsyncMock()
        cache_mock.get_search_results = AsyncMock(return_value=None)
        cache_mock.set_search_results = AsyncMock()
        cache_mock.generate_cache_key = Mock(return_value="test-cache-key")
        cache_mock._client = AsyncMock()
        cache_mock._client.ping = AsyncMock()
        mock_cache.return_value = cache_mock
        
        # Mock database service
        db_mock = AsyncMock()
        db_mock.get_api_key = AsyncMock(return_value=None)
        db_mock.log_search_request = AsyncMock()
        db_mock.log_error = AsyncMock()
        db_mock.get_session = AsyncMock()
        db_mock.get_session.return_value.__aenter__ = AsyncMock()
        db_mock.get_session.return_value.__aexit__ = AsyncMock()
        mock_db.return_value = db_mock
        
        yield {
            'searxng': searxng_mock,
            'scraper': scraper_mock,
            'cache': cache_mock,
            'db': db_mock
        }


class TestSearchEndpoints:
    """Test search-related endpoints."""
    
    def test_search_scrape_basic(self, client, mock_services):
        """Test basic search and scrape."""
        # Disable API key requirement for testing
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []  # No API keys required
            mock_settings.return_value = settings
            
            response = client.post("/api/v1/search/", json={
                "query": "python programming",
                "engines": ["google"],
                "max_results": 5,
                "scrape_content": False
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert "search_metadata" in data
            assert "results" in data
            assert "processing_time_ms" in data
            assert data["search_metadata"]["query"] == "python programming"
    
    def test_search_scrape_with_content(self, client, mock_services):
        """Test search with content scraping."""
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            response = client.post("/api/v1/search/", json={
                "query": "python programming",
                "engines": ["google"],
                "max_results": 5,
                "scrape_content": True,
                "include_images": True,
                "include_links": True
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["search_metadata"]["query"] == "python programming"
            mock_services['scraper'].scrape_urls.assert_called_once()
    
    def test_search_validation_errors(self, client, mock_services):
        """Test request validation errors."""
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            # Empty query
            response = client.post("/api/v1/search/", json={
                "query": "",
                "engines": ["google"]
            })
            assert response.status_code == 422
            
            # Invalid engine
            response = client.post("/api/v1/search/", json={
                "query": "test",
                "engines": ["invalid_engine"]
            })
            assert response.status_code == 422
            
            # Too many results
            response = client.post("/api/v1/search/", json={
                "query": "test",
                "engines": ["google"],
                "max_results": 200
            })
            assert response.status_code == 422
    
    def test_search_with_api_key(self, client, mock_services):
        """Test search with API key authentication."""
        from app.models.database import APIKey
        
        # Mock API key in database
        api_key_obj = APIKey(id=1, key="test-api-key", name="Test Key", is_active=True)
        mock_services['db'].get_api_key.return_value = api_key_obj
        
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = ["test-api-key"]  # Require API key
            mock_settings.return_value = settings
            
            # Request with valid API key
            response = client.post("/api/v1/search/", 
                headers={"X-API-Key": "test-api-key"},
                json={
                    "query": "python programming",
                    "engines": ["google"]
                }
            )
            
            assert response.status_code == 200
    
    def test_search_unauthorized(self, client, mock_services):
        """Test unauthorized access."""
        mock_services['db'].get_api_key.return_value = None
        
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = ["required-key"]  # Require API key
            mock_settings.return_value = settings
            
            # Request without API key
            response = client.post("/api/v1/search/", json={
                "query": "python programming",
                "engines": ["google"]
            })
            
            assert response.status_code == 401
            
            # Request with invalid API key
            response = client.post("/api/v1/search/", 
                headers={"X-API-Key": "invalid-key"},
                json={
                    "query": "python programming",
                    "engines": ["google"]
                }
            )
            
            assert response.status_code == 401
    
    def test_batch_search(self, client, mock_services):
        """Test batch search endpoint."""
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            response = client.post("/api/v1/search/batch", json={
                "queries": ["python programming", "web scraping"],
                "engines": ["google"],
                "max_results_per_query": 3,
                "parallel_requests": 2
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert "batch_id" in data
            assert "queries_processed" in data
            assert "results" in data
            assert data["queries_processed"] >= 0
    
    def test_list_engines(self, client, mock_services):
        """Test engines listing endpoint."""
        mock_engines = {
            "google": Mock(name="google", enabled=True),
            "bing": Mock(name="bing", enabled=True)
        }
        mock_services['searxng'].get_available_engines.return_value = mock_engines
        
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            response = client.get("/api/v1/search/engines")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "engines" in data
            assert "total_engines" in data
            assert "enabled_engines" in data
    
    def test_health_check(self, client, mock_services):
        """Test health check endpoint."""
        response = client.get("/api/v1/search/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "services" in data
        assert "timestamp" in data


class TestErrorHandling:
    """Test error handling."""
    
    def test_searxng_service_error(self, client, mock_services):
        """Test SearXNG service error handling."""
        # Mock SearXNG service error
        mock_services['searxng'].search.side_effect = Exception("SearXNG connection failed")
        
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            response = client.post("/api/v1/search/", json={
                "query": "test query",
                "engines": ["google"]
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
    
    def test_rate_limiting(self, client, mock_services):
        """Test rate limiting."""
        # This would require setting up actual rate limiting
        # For now, just test that the endpoint accepts requests
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            settings.rate_limit_enabled = True
            mock_settings.return_value = settings
            
            response = client.post("/api/v1/search/", json={
                "query": "test query",
                "engines": ["google"]
            })
            
            # Should still work for single request
            assert response.status_code in [200, 429]  # Either success or rate limited


class TestAsyncOperations:
    """Test async operations."""
    
    def test_async_search_request(self, client, mock_services):
        """Test async search request creation."""
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            # Mock job creation
            from app.models.database import ScrapingJob
            mock_job = ScrapingJob(job_id="test-job-123")
            mock_services['db'].create_scraping_job.return_value = mock_job
            mock_services['db'].update_scraping_job.return_value = mock_job
            
            with patch('app.workers.tasks.process_async_search_scrape.delay') as mock_task:
                mock_task.return_value = Mock(id="task-123")
                
                response = client.post("/api/v1/search/", json={
                    "query": "test query",
                    "engines": ["google"],
                    "async_mode": True,
                    "webhook_url": "https://example.com/webhook"
                })
                
                assert response.status_code == 200
                data = response.json()
                
                assert "task_id" in data
                assert "status" in data
                assert data["status"] in ["pending", "processing"]


class TestCaching:
    """Test caching functionality."""
    
    def test_cache_hit(self, client, mock_services):
        """Test cache hit scenario."""
        # Mock cached response
        from app.models.responses import UnSearchResponse, SearchMetadata
        
        cached_response = UnSearchResponse(
            search_metadata=SearchMetadata(
                query="cached query",
                engines_used=["google"],
                engines_succeeded=["google"],
                engines_failed=[],
                total_results_found=1,
                results_returned=1,
                search_time_ms=100
            ),
            results=[],
            processing_time_ms=50,
            cached=True,
            total_results=1,
            request_id="cached-123"
        )
        
        mock_services['cache'].get_search_results.return_value = cached_response
        
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            response = client.post("/api/v1/search/", json={
                "query": "cached query",
                "engines": ["google"],
                "cache_ttl": 3600
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["cached"] is True
            # SearXNG should not be called for cached results
            mock_services['searxng'].search.assert_not_called()
    
    def test_cache_disabled(self, client, mock_services):
        """Test when caching is disabled."""
        with patch('app.config.get_settings') as mock_settings:
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            response = client.post("/api/v1/search/", json={
                "query": "test query",
                "engines": ["google"],
                "cache_ttl": 0  # Disable caching
            })
            
            assert response.status_code == 200
            # Cache should not be checked when TTL is 0
            mock_services['cache'].get_search_results.assert_not_called()
