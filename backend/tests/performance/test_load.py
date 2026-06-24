"""
Performance and load tests for the UnSearch API.
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, AsyncMock, patch
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.models.responses import SearchResult


@pytest.fixture(autouse=True)
def override_api_keys():
    """Bypass API key check for load tests by clearing configured keys."""
    from app.config import get_settings
    from app.api.dependencies import get_settings_dependency
    settings = get_settings()
    original_api_keys = settings.api_keys
    settings.api_keys = []
    
    # Also override via dependency overrides mapping
    app.dependency_overrides[get_settings_dependency] = lambda: settings
    
    yield
    
    settings.api_keys = original_api_keys
    if get_settings_dependency in app.dependency_overrides:
        del app.dependency_overrides[get_settings_dependency]


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_fast_services():
    """Mock services with fast responses for load testing."""
    with patch('app.api.dependencies.get_searxng_service') as mock_searxng, \
         patch('app.services.searxng.get_searxng_service') as mock_searxng_legacy, \
         patch('app.services.core.searxng.get_searxng_service') as mock_searxng_core, \
         patch('app.api.dependencies.get_scraping_service') as mock_scraper, \
         patch('app.api.dependencies.get_cache_service') as mock_cache, \
         patch('app.api.dependencies.get_database_service') as mock_db:
        
        # Mock SearXNG with fast response
        searxng_mock = AsyncMock()
        searxng_mock.search = AsyncMock(return_value=[
            SearchResult(
                rank=i,
                title=f"Test Result {i}",
                url=f"https://example{i}.com",
                snippet=f"Test snippet {i}",
                engine="google"
            ) for i in range(1, 11)
        ])
        searxng_mock.search_with_relevance = AsyncMock(return_value=(searxng_mock.search.return_value, None))
        mock_searxng.return_value = searxng_mock
        mock_searxng_legacy.return_value = searxng_mock
        mock_searxng_core.return_value = searxng_mock
        
        # Mock other services
        scraper_mock = AsyncMock()
        scraper_mock.scrape_urls = AsyncMock(return_value=[])
        mock_scraper.return_value = scraper_mock
        
        cache_mock = AsyncMock()
        cache_mock.get_search_results = AsyncMock(return_value=None)
        cache_mock.set_search_results = AsyncMock()
        cache_mock.generate_cache_key = Mock(return_value="test-cache-key")
        mock_cache.return_value = cache_mock
        
        db_mock = AsyncMock()
        db_mock.get_api_key = AsyncMock(return_value=None)
        db_mock.log_search_request = AsyncMock()
        db_mock.log_error = AsyncMock()
        mock_db.return_value = db_mock
        
        yield {
            'searxng': searxng_mock,
            'scraper': scraper_mock,
            'cache': cache_mock,
            'db': db_mock
        }


class TestPerformance:
    """Test API performance."""
    
    def test_single_request_latency(self, client, mock_fast_services):
        """Test single request latency."""
        with patch('app.config.get_settings') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            start_time = time.time()
            
            response = client.post("/api/v1/search/", json={
                "query": "performance test",
                "engines": ["google"],
                "max_results": 10,
                "scrape_content": False
            })
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to ms
            
            assert response.status_code == 200
            assert latency < 1000  # Should respond within 1 second
            
            # Check response time header
            response_time = float(response.headers.get("X-Response-Time", "0"))
            assert response_time > 0
    
    def test_concurrent_requests(self, client, mock_fast_services):
        """Test concurrent request handling."""
        with patch('app.config.get_settings') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            def make_request(query_num):
                """Make a single request."""
                return client.post("/api/v1/search/", json={
                    "query": f"concurrent test {query_num}",
                    "engines": ["google"],
                    "max_results": 5,
                    "scrape_content": False
                })
            
            # Test with 10 concurrent requests
            concurrent_requests = 10
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
                futures = [executor.submit(make_request, i) for i in range(concurrent_requests)]
                responses = [future.result() for future in futures]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All requests should succeed
            assert all(response.status_code == 200 for response in responses)
            
            # Should handle concurrent requests efficiently
            assert total_time < 5.0  # All requests should complete within 5 seconds
            
            # Calculate requests per second
            rps = concurrent_requests / total_time
            assert rps > 2  # Should handle at least 2 requests per second
    
    def test_memory_usage(self, client, mock_fast_services):
        """Test memory usage during requests."""
        import psutil
        import os
        
        with patch('app.config.get_settings') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Make multiple requests
            for i in range(50):
                response = client.post("/api/v1/search/", json={
                    "query": f"memory test {i}",
                    "engines": ["google"],
                    "max_results": 10,
                    "scrape_content": False
                })
                assert response.status_code == 200
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024
    
    def test_large_response_handling(self, client, mock_fast_services):
        """Test handling of large responses."""
        # Mock a large number of results
        large_results = [
            SearchResult(
                rank=i,
                title=f"Large Test Result {i}" * 10,  # Longer titles
                url=f"https://example{i}.com/very/long/path/to/test/performance",
                snippet=f"This is a very long snippet for result {i} " * 20,
                engine="google"
            ) for i in range(1, 101)  # 100 results
        ]
        
        mock_fast_services['searxng'].search.return_value = large_results
        mock_fast_services['searxng'].search_with_relevance.return_value = (large_results, None)
        
        with patch('app.api.dependencies.get_settings_dependency') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = lambda: settings
            
            start_time = time.time()
            
            response = client.post("/api/v1/search/", json={
                "query": "large response test",
                "engines": ["google"],
                "max_results": 100,
                "scrape_content": False
            })
            
            end_time = time.time()
            
            assert response.status_code == 200
            assert end_time - start_time < 2.0  # Should handle large responses quickly
            
            data = response.json()
            assert len(data["results"]) == 100
    
    @pytest.mark.asyncio
    async def test_async_performance(self, mock_fast_services):
        """Test async operation performance."""
        from app.services.searxng import get_searxng_service
        
        searxng = await get_searxng_service()
        
        # Test multiple concurrent searches
        async def single_search(query_num):
            return await searxng.search(
                query=f"async test {query_num}",
                engines=["google"],
                language="en"
            )
        
        start_time = time.time()
        
        # Run 20 concurrent searches
        tasks = [single_search(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        assert len(results) == 20
        assert all(isinstance(result, list) for result in results)
        assert end_time - start_time < 3.0  # Should complete within 3 seconds


class TestStressTest:
    """Stress tests for the API."""
    
    @pytest.mark.slow
    def test_sustained_load(self, client, mock_fast_services):
        """Test sustained load over time."""
        with patch('app.config.get_settings') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            success_count = 0
            error_count = 0
            total_requests = 100
            
            start_time = time.time()
            
            for i in range(total_requests):
                try:
                    response = client.post("/api/v1/search/", json={
                        "query": f"stress test {i}",
                        "engines": ["google"],
                        "max_results": 5,
                        "scrape_content": False
                    })
                    
                    if response.status_code == 200:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception:
                    error_count += 1
                
                # Small delay to avoid overwhelming
                time.sleep(0.01)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            success_rate = success_count / total_requests
            rps = total_requests / total_time
            
            assert success_rate > 0.95  # 95% success rate
            assert rps > 5  # At least 5 requests per second
    
    @pytest.mark.slow
    def test_error_recovery(self, client, mock_fast_services):
        """Test error recovery under load."""
        with patch('app.config.get_settings') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            # Simulate intermittent failures
            call_count = 0
            original_search = mock_fast_services['searxng'].search
            
            async def failing_search(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count % 5 == 0:  # Fail every 5th request
                    raise Exception("Simulated failure")
                return await original_search(*args, **kwargs)
            
            mock_fast_services['searxng'].search = failing_search
            
            success_count = 0
            for i in range(20):
                try:
                    response = client.post("/api/v1/search/", json={
                        "query": f"error recovery test {i}",
                        "engines": ["google"],
                        "max_results": 5,
                        "scrape_content": False
                    })
                    
                    if response.status_code == 200:
                        success_count += 1
                        
                except Exception:
                    pass
            
            # Should recover from errors and continue processing
            assert success_count > 10  # More than half should succeed


class TestCachingPerformance:
    """Test caching performance."""
    
    def test_cache_hit_performance(self, client, mock_fast_services):
        """Test performance of cache hits."""
        from app.models.responses import UnSearchResponse, SearchMetadata
        
        # Mock cached response
        cached_response = UnSearchResponse(
            search_metadata=SearchMetadata(
                query="cached query",
                engines_used=["google"],
                engines_succeeded=["google"],
                engines_failed=[],
                total_results_found=10,
                results_returned=10,
                search_time_ms=100
            ),
            results=[],
            processing_time_ms=50,
            cached=True,
            total_results=10,
            request_id="cached-123"
        )
        
        mock_fast_services['cache'].get_search_results.return_value = cached_response
        
        with patch('app.config.get_settings') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            # Measure cache hit performance
            start_time = time.time()
            
            response = client.post("/api/v1/search/", json={
                "query": "cached query",
                "engines": ["google"],
                "cache_ttl": 3600
            })
            
            end_time = time.time()
            cache_hit_time = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            assert response.json()["cached"] is True
            assert cache_hit_time < 100  # Cache hits should be very fast
    
    def test_cache_performance_comparison(self, client, mock_fast_services):
        """Compare performance with and without cache."""
        with patch('app.config.get_settings') as mock_settings:
            from app.config import get_settings
            settings = get_settings()
            settings.api_keys = []
            mock_settings.return_value = settings
            
            # Test without cache
            start_time = time.time()
            response1 = client.post("/api/v1/search/", json={
                "query": "performance comparison",
                "engines": ["google"],
                "cache_ttl": 0  # No caching
            })
            no_cache_time = time.time() - start_time
            
            # Test with cache miss (first request)
            start_time = time.time()
            response2 = client.post("/api/v1/search/", json={
                "query": "performance comparison cached",
                "engines": ["google"],
                "cache_ttl": 3600
            })
            cache_miss_time = time.time() - start_time
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Cache miss should be similar to no cache (slightly slower due to caching overhead)
            assert cache_miss_time < no_cache_time * 2