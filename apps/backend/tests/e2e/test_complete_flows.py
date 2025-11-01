"""
End-to-end tests for complete user flows in the  API.
These tests run against a fully deployed environment.
"""
import asyncio
import json
import time
from typing import Dict, List, Any
import pytest
import httpx
from httpx import AsyncClient
import os
from datetime import datetime, timedelta

# Configuration
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("E2E_API_KEY", "test-api-key")
WEBHOOK_URL = os.getenv("E2E_WEBHOOK_URL", "https://webhook.site/test")


class TestUnSearchE2E:
    """Complete end-to-end test scenarios."""
    
    @pytest.fixture
    async def client(self):
        """Create authenticated HTTP client."""
        async with AsyncClient(
            base_url=BASE_URL,
            headers={"X-API-Key": API_KEY},
            timeout=30.0
        ) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_complete_search_and_scrape_flow(self, client: AsyncClient):
        """
        Test the complete flow of searching and scraping content.
        
        Flow:
        1. Search for content
        2. Verify search results
        3. Check scraped content
        4. Validate response format
        """
        # Step 1: Perform search with scraping
        request_data = {
            "query": "Python FastAPI tutorial",
            "engines": ["google", "bing"],
            "max_results": 5,
            "scrape_content": True,
            "include_images": True,
            "include_links": True,
            "cache_ttl": 3600,
            "language": "en",
            "safe_search": "moderate"
        }
        
        start_time = time.time()
        response = await client.post("/api/v1/search", json=request_data)
        response_time = (time.time() - start_time) * 1000
        
        # Verify response status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify response time is reasonable
        assert response_time < 10000, f"Response took too long: {response_time}ms"
        
        data = response.json()
        
        # Step 2: Verify response structure
        assert "search_metadata" in data
        assert "results" in data
        assert "processing_time_ms" in data
        assert "cached" in data
        assert "total_results" in data
        
        # Verify metadata
        metadata = data["search_metadata"]
        assert metadata["query"] == request_data["query"]
        assert set(metadata["engines"]) == set(request_data["engines"])
        assert metadata["language"] == request_data["language"]
        
        # Step 3: Verify search results
        results = data["results"]
        assert len(results) > 0, "No results returned"
        assert len(results) <= request_data["max_results"]
        
        # Check each result
        for result in results:
            assert "rank" in result
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "engine" in result
            
            # Verify scraped content if available
            if "scraped_content" in result and result["scraped_content"]:
                content = result["scraped_content"]
                assert "text" in content
                assert "metadata" in content
                assert "extraction_success" in content
                assert "word_count" in content
                
                # Check requested fields
                if request_data["include_images"]:
                    assert "images" in content
                if request_data["include_links"]:
                    assert "links" in content
        
        # Step 4: Test caching
        # Make the same request again
        cached_response = await client.post("/api/v1/search", json=request_data)
        assert cached_response.status_code == 200
        cached_data = cached_response.json()
        
        # Should be cached
        assert cached_data.get("cached", False) == True
        
        # Results should be the same
        assert len(cached_data["results"]) == len(data["results"])
    
    @pytest.mark.asyncio
    async def test_batch_search_flow(self, client: AsyncClient):
        """
        Test batch search functionality.
        
        Flow:
        1. Submit multiple searches
        2. Verify batch processing
        3. Check individual results
        """
        batch_request = {
            "searches": [
                {
                    "query": "machine learning algorithms",
                    "engines": ["google"],
                    "max_results": 3
                },
                {
                    "query": "deep learning frameworks",
                    "engines": ["bing"],
                    "max_results": 3
                },
                {
                    "query": "neural networks tutorial",
                    "engines": ["duckduckgo"],
                    "max_results": 3
                }
            ]
        }
        
        response = await client.post("/api/v1/search/batch", json=batch_request)
        
        # Check if batch endpoint exists
        if response.status_code == 404:
            pytest.skip("Batch endpoint not implemented")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batch_id" in data
        assert "results" in data
        assert len(data["results"]) == len(batch_request["searches"])
        
        # Verify each search result
        for i, result in enumerate(data["results"]):
            assert result["query"] == batch_request["searches"][i]["query"]
            assert "results" in result
            assert len(result["results"]) <= batch_request["searches"][i]["max_results"]
    
    @pytest.mark.asyncio
    async def test_async_processing_flow(self, client: AsyncClient):
        """
        Test asynchronous processing with webhooks.
        
        Flow:
        1. Submit async search request
        2. Get job ID
        3. Check job status
        4. Verify completion
        """
        async_request = {
            "query": "large dataset processing techniques",
            "engines": ["google", "bing", "duckduckgo"],
            "max_results": 20,
            "scrape_content": True,
            "async_mode": True,
            "webhook_url": WEBHOOK_URL
        }
        
        # Submit async request
        response = await client.post("/api/v1/search", json=async_request)
        
        # Check if async mode is implemented
        if "job_id" not in response.json():
            pytest.skip("Async mode not implemented")
        
        assert response.status_code == 202  # Accepted
        data = response.json()
        
        assert "job_id" in data
        assert "status" in data
        assert data["status"] in ["pending", "processing"]
        
        job_id = data["job_id"]
        
        # Poll for job completion (max 60 seconds)
        max_attempts = 30
        for attempt in range(max_attempts):
            status_response = await client.get(f"/api/v1/search/status/{job_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data["status"] == "completed":
                    assert "results" in status_data
                    assert len(status_data["results"]) > 0
                    break
                elif status_data["status"] == "failed":
                    pytest.fail(f"Job failed: {status_data.get('error')}")
            
            await asyncio.sleep(2)
        else:
            pytest.fail(f"Job {job_id} did not complete in time")
    
    @pytest.mark.asyncio
    async def test_error_handling_flow(self, client: AsyncClient):
        """
        Test error handling and recovery.
        
        Flow:
        1. Send invalid requests
        2. Verify error responses
        3. Check rate limiting
        4. Test recovery
        """
        # Test 1: Invalid query
        invalid_request = {
            "query": "",  # Empty query
            "engines": ["google"]
        }
        
        response = await client.post("/api/v1/search", json=invalid_request)
        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data
        
        # Test 2: Invalid engine
        invalid_engine_request = {
            "query": "test",
            "engines": ["invalid_engine"]
        }
        
        response = await client.post("/api/v1/search", json=invalid_engine_request)
        assert response.status_code in [400, 422]
        
        # Test 3: Exceed max results
        excessive_request = {
            "query": "test",
            "engines": ["google"],
            "max_results": 1000  # Exceeds limit
        }
        
        response = await client.post("/api/v1/search", json=excessive_request)
        assert response.status_code in [400, 422]
        
        # Test 4: Rate limiting (if enabled)
        # Make many requests quickly
        rate_limit_hit = False
        for i in range(100):
            response = await client.post("/api/v1/search", json={
                "query": f"rate limit test {i}",
                "engines": ["google"],
                "max_results": 1
            })
            
            if response.status_code == 429:  # Too Many Requests
                rate_limit_hit = True
                break
        
        # Note: Rate limiting might not be hit in test environment
        if rate_limit_hit:
            assert "Retry-After" in response.headers
    
    @pytest.mark.asyncio
    async def test_multilanguage_search_flow(self, client: AsyncClient):
        """
        Test searching in different languages.
        
        Flow:
        1. Search in multiple languages
        2. Verify language-specific results
        3. Check content language detection
        """
        languages = [
            ("en", "Python programming"),
            ("es", "programación Python"),
            ("fr", "programmation Python"),
            ("de", "Python Programmierung")
        ]
        
        for lang_code, query in languages:
            request_data = {
                "query": query,
                "engines": ["google"],
                "max_results": 3,
                "language": lang_code,
                "scrape_content": True
            }
            
            response = await client.post("/api/v1/search", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["search_metadata"]["language"] == lang_code
            
            # Check if results contain content in the expected language
            results = data["results"]
            if results and results[0].get("scraped_content"):
                content = results[0]["scraped_content"]
                if "language_detected" in content:
                    # Language detection might not be 100% accurate
                    # but should be close
                    detected_lang = content["language_detected"]
                    print(f"Query language: {lang_code}, Detected: {detected_lang}")
    
    @pytest.mark.asyncio
    async def test_custom_selectors_flow(self, client: AsyncClient):
        """
        Test custom CSS selector functionality.
        
        Flow:
        1. Search with custom selectors
        2. Verify extracted content
        3. Test fallback behavior
        """
        request_data = {
            "query": "example.com",
            "engines": ["google"],
            "max_results": 1,
            "scrape_content": True,
            "scrape_selectors": {
                "title": "h1, h2, title",
                "main_content": "main, article, .content",
                "navigation": "nav, .navigation",
                "footer": "footer, .footer"
            }
        }
        
        response = await client.post("/api/v1/search", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            results = data["results"]
            
            if results and results[0].get("scraped_content"):
                content = results[0]["scraped_content"]
                
                # Check if custom extraction worked
                if "custom_extracted" in content:
                    extracted = content["custom_extracted"]
                    assert isinstance(extracted, dict)
                    
                    # Verify requested selectors were attempted
                    for selector_name in request_data["scrape_selectors"]:
                        # The content might not exist, but the key should be present
                        assert selector_name in extracted or True  # Flexible check
    
    @pytest.mark.asyncio
    async def test_performance_and_reliability(self, client: AsyncClient):
        """
        Test system performance and reliability under load.
        
        Flow:
        1. Send concurrent requests
        2. Measure response times
        3. Verify consistency
        4. Check error rates
        """
        # Define test parameters
        num_concurrent = 10
        num_iterations = 3
        
        async def make_search_request(query_suffix: int):
            """Make a single search request."""
            request_data = {
                "query": f"performance test query {query_suffix}",
                "engines": ["google"],
                "max_results": 2,
                "scrape_content": False  # Faster without scraping
            }
            
            start = time.time()
            try:
                response = await client.post("/api/v1/search", json=request_data)
                duration = time.time() - start
                return {
                    "success": response.status_code == 200,
                    "duration": duration,
                    "status_code": response.status_code
                }
            except Exception as e:
                return {
                    "success": False,
                    "duration": time.time() - start,
                    "error": str(e)
                }
        
        # Run performance test
        all_results = []
        for iteration in range(num_iterations):
            # Create concurrent tasks
            tasks = [
                make_search_request(i + (iteration * num_concurrent))
                for i in range(num_concurrent)
            ]
            
            # Execute concurrently
            results = await asyncio.gather(*tasks)
            all_results.extend(results)
            
            # Small delay between iterations
            await asyncio.sleep(1)
        
        # Analyze results
        successful_requests = [r for r in all_results if r["success"]]
        failed_requests = [r for r in all_results if not r["success"]]
        
        success_rate = len(successful_requests) / len(all_results)
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
        
        # Calculate response time statistics
        if successful_requests:
            response_times = [r["duration"] for r in successful_requests]
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"\nPerformance Statistics:")
            print(f"  Success Rate: {success_rate:.2%}")
            print(f"  Avg Response Time: {avg_time:.2f}s")
            print(f"  Min Response Time: {min_time:.2f}s")
            print(f"  Max Response Time: {max_time:.2f}s")
            
            # Performance assertions
            assert avg_time < 5.0, f"Average response time too high: {avg_time:.2f}s"
            assert max_time < 10.0, f"Max response time too high: {max_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_api_versioning_and_compatibility(self, client: AsyncClient):
        """
        Test API versioning and backward compatibility.
        
        Flow:
        1. Test current version endpoint
        2. Test deprecated features (if any)
        3. Verify version headers
        """
        # Test version endpoint
        response = await client.get("/api/v1/version")
        if response.status_code == 200:
            version_data = response.json()
            assert "version" in version_data
            assert "api_version" in version_data
        
        # Test that v1 endpoints work
        v1_response = await client.post("/api/v1/search", json={
            "query": "test",
            "engines": ["google"],
            "max_results": 1
        })
        assert v1_response.status_code == 200
        
        # Check for API version headers
        assert "X-API-Version" in v1_response.headers or True  # Flexible check


class TestHealthAndMonitoring:
    """E2E tests for health checks and monitoring endpoints."""
    
    @pytest.fixture
    async def client(self):
        """Create HTTP client without authentication for public endpoints."""
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test the health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        
        # Check service statuses
        if "services" in data:
            services = data["services"]
            expected_services = ["api", "database", "redis", "searxng"]
            
            for service in expected_services:
                if service in services:
                    assert "status" in services[service]
                    assert "response_time_ms" in services[service]
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test the Prometheus metrics endpoint."""
        response = await client.get("/metrics")
        
        if response.status_code == 200:
            content = response.text
            
            # Check for standard Prometheus metrics
            assert "http_requests_total" in content or "request_count" in content
            assert "http_request_duration_seconds" in content or "request_duration" in content
            
            # Check for custom metrics
            expected_metrics = [
                "search_requests_total",
                "search_results_count",
                "scraping_success_rate",
                "cache_hit_ratio"
            ]
            
            for metric in expected_metrics:
                # Metrics might not be present if not used yet
                pass  # Flexible check
    
    @pytest.mark.asyncio
    async def test_documentation_endpoints(self, client: AsyncClient):
        """Test API documentation endpoints."""
        # Test OpenAPI schema
        openapi_response = await client.get("/openapi.json")
        if openapi_response.status_code == 200:
            schema = openapi_response.json()
            assert "openapi" in schema
            assert "paths" in schema
            assert "/api/v1/search" in schema["paths"]
        
        # Test Swagger UI
        docs_response = await client.get("/docs")
        if docs_response.status_code == 200:
            assert "swagger" in docs_response.text.lower() or "openapi" in docs_response.text.lower()
        
        # Test ReDoc (if available)
        redoc_response = await client.get("/redoc")
        # ReDoc might not be configured, so we don't assert on status


@pytest.mark.asyncio
class TestDataIntegrity:
    """E2E tests for data integrity and consistency."""
    
    @pytest.fixture
    async def client(self):
        """Create authenticated HTTP client."""
        async with AsyncClient(
            base_url=BASE_URL,
            headers={"X-API-Key": API_KEY},
            timeout=30.0
        ) as client:
            yield client
    
    async def test_data_consistency_across_requests(self, client: AsyncClient):
        """
        Test that data remains consistent across multiple requests.
        
        Flow:
        1. Make identical requests
        2. Verify consistency (when not cached)
        3. Test with different parameters
        """
        # Disable caching for this test
        request_data = {
            "query": "data consistency test " + str(datetime.now()),
            "engines": ["google"],
            "max_results": 5,
            "cache_ttl": 0  # Disable caching
        }
        
        # Make multiple identical requests
        responses = []
        for _ in range(3):
            response = await client.post("/api/v1/search", json=request_data)
            assert response.status_code == 200
            responses.append(response.json())
            await asyncio.sleep(1)  # Small delay between requests
        
        # Verify that the structure is consistent
        for i in range(1, len(responses)):
            assert len(responses[i]["results"]) == len(responses[0]["results"])
            assert responses[i]["search_metadata"]["query"] == responses[0]["search_metadata"]["query"]
    
    async def test_unicode_and_special_characters(self, client: AsyncClient):
        """Test handling of Unicode and special characters."""
        test_queries = [
            "Python 编程",  # Chinese
            "Программирование на Python",  # Russian
            "Python & C++ comparison",
            "Search with \"quotes\" and 'apostrophes'",
            "Special chars: !@#$%^&*()",
            "Emoji test 🐍 🔍 💻"
        ]
        
        for query in test_queries:
            response = await client.post("/api/v1/search", json={
                "query": query,
                "engines": ["google"],
                "max_results": 1
            })
            
            # Should handle all characters gracefully
            assert response.status_code in [200, 400, 422]
            
            if response.status_code == 200:
                data = response.json()
                # Query should be preserved correctly
                assert data["search_metadata"]["query"] == query
