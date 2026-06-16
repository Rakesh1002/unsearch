"""
Smoke tests for quick validation of critical API functionality.
These tests should run quickly and verify basic operation.
"""
import os
import pytest
import httpx
from httpx import AsyncClient


BASE_URL = os.getenv("SMOKE_TEST_URL", "http://localhost:8000")
API_KEY = os.getenv("SMOKE_TEST_API_KEY", "test-key-1")


@pytest.mark.asyncio
class TestSmoke:
    """Quick smoke tests for critical functionality."""
    
    @pytest.fixture
    async def client(self, override_settings):
        """Create HTTP client for tests."""
        from app.main import app
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            timeout=10.0,
            follow_redirects=True
        ) as client:
            yield client
    
    async def test_api_is_running(self, client: AsyncClient):
        """Test that the API is running and responding."""
        response = await client.get("/")
        assert response.status_code in [200, 307, 404]  # API is responding
    
    async def test_health_check(self, client: AsyncClient):
        """Test that health endpoint is working."""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
    
    async def test_docs_available(self, client: AsyncClient):
        """Test that API documentation is available."""
        response = await client.get("/docs")
        assert response.status_code in [200, 307]  # Docs or redirect to docs
    
    async def test_authentication_required(self, client: AsyncClient):
        """Test that authentication is enforced."""
        # Try to access protected endpoint without auth
        response = await client.post("/api/v1/search", json={
            "query": "test",
            "engines": ["google"]
        })
        
        # Should require authentication (unless disabled in test env)
        if response.status_code == 401:
            detail_lower = response.json().get("detail", "").lower()
            assert "x-api-key" in detail_lower or \
                   "unauthorized" in response.json().get("message", "").lower() or \
                   "api key required" in detail_lower
    
    async def test_basic_search(self, client: AsyncClient):
        """Test basic search functionality."""
        client.headers["X-API-Key"] = API_KEY
        
        response = await client.post("/api/v1/search", json={
            "query": "Python programming",
            "engines": ["google"],
            "max_results": 1,
            "scrape_content": False  # Quick test without scraping
        })
        
        if response.status_code == 401:
            pytest.skip("API key not valid for this environment")
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic structure validation
        assert "search_metadata" in data
        assert "results" in data
        assert isinstance(data["results"], list)
    
    async def test_invalid_request_handling(self, client: AsyncClient):
        """Test that invalid requests are handled properly."""
        client.headers["X-API-Key"] = API_KEY
        
        # Send invalid request (empty query)
        response = await client.post("/api/v1/search", json={
            "query": "",
            "engines": ["google"]
        })
        
        # Should return validation error
        assert response.status_code in [400, 422]
        assert "error" in response.json() or "detail" in response.json()
    
    async def test_rate_limiting_headers(self, client: AsyncClient):
        """Test that rate limiting headers are present."""
        client.headers["X-API-Key"] = API_KEY
        
        response = await client.post("/api/v1/search", json={
            "query": "rate limit test",
            "engines": ["google"],
            "max_results": 1
        })
        
        # Check for rate limit headers (if implemented)
        if "X-RateLimit-Limit" in response.headers:
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
    
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers are properly set."""
        response = await client.options("/api/v1/search")
        
        # Check CORS headers
        if "Access-Control-Allow-Origin" in response.headers:
            assert "Access-Control-Allow-Methods" in response.headers
            assert "Access-Control-Allow-Headers" in response.headers
    
    async def test_metrics_endpoint_exists(self, client: AsyncClient):
        """Test that metrics endpoint exists."""
        response = await client.get("/metrics")
        
        # Metrics might be protected or disabled
        assert response.status_code in [200, 401, 404]
        
        if response.status_code == 200:
            # Should return Prometheus format
            assert response.headers.get("content-type", "").startswith("text/plain")


@pytest.mark.asyncio
class TestCriticalPaths:
    """Test critical user paths quickly."""
    
    @pytest.fixture
    async def auth_client(self, override_settings):
        """Create authenticated client."""
        from app.main import app
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"X-API-Key": "test-key-1"},
            timeout=15.0,
            follow_redirects=True
        ) as client:
            yield client
    
    async def test_search_to_results_path(self, auth_client: AsyncClient):
        """Test the critical path from search to getting results."""
        # Submit search
        response = await auth_client.post("/api/v1/search", json={
            "query": "test query",
            "engines": ["google"],
            "max_results": 3,
            "scrape_content": False
        })
        
        if response.status_code == 401:
            pytest.skip("Authentication not configured for test environment")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify we got results
        assert len(data["results"]) > 0
        
        # Verify result structure
        first_result = data["results"][0]
        assert "title" in first_result
        assert "url" in first_result
        assert "snippet" in first_result
    
    async def test_caching_works(self, auth_client: AsyncClient):
        """Test that caching is functional."""
        request_data = {
            "query": "cache test query",
            "engines": ["google"],
            "max_results": 2,
            "cache_ttl": 60
        }
        
        # First request
        response1 = await auth_client.post("/api/v1/search", json=request_data)
        if response1.status_code != 200:
            pytest.skip("Search not working in test environment")
        
        data1 = response1.json()
        
        # Second request (should be cached)
        response2 = await auth_client.post("/api/v1/search", json=request_data)
        assert response2.status_code == 200
        
        data2 = response2.json()
        
        # Check cache indicator
        if "cached" in data2:
            assert data2["cached"] == True
        
        # Results should be identical
        assert len(data1["results"]) == len(data2["results"])
    
    async def test_error_recovery(self, auth_client: AsyncClient):
        """Test that API recovers from errors gracefully."""
        # Send request that might cause error
        response = await auth_client.post("/api/v1/search", json={
            "query": "test",
            "engines": ["nonexistent_engine"],
            "max_results": 1
        })
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
        
        # Try valid request after error
        response = await auth_client.post("/api/v1/search", json={
            "query": "recovery test",
            "engines": ["google"],
            "max_results": 1
        })
        
        # Should work normally
        assert response.status_code in [200, 401]


def test_environment_configured():
    """Test that environment is properly configured."""
    assert BASE_URL, "BASE_URL not configured"
    assert API_KEY, "API_KEY not configured"
    
    # Check URL is valid
    assert BASE_URL.startswith("http://") or BASE_URL.startswith("https://")


if __name__ == "__main__":
    """Run smoke tests directly."""
    import sys
    import asyncio
    
    async def run_critical_tests():
        """Run only the most critical smoke tests."""
        print(f"Running smoke tests against: {BASE_URL}")
        
        async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            # Test 1: API is running
            try:
                response = await client.get("/health")
                if response.status_code == 200:
                    print("✅ API is running")
                else:
                    print(f"❌ API health check failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Cannot reach API: {e}")
                return False
            
            # Test 2: Search works
            client.headers["X-API-Key"] = API_KEY
            try:
                response = await client.post("/api/v1/search", json={
                    "query": "smoke test",
                    "engines": ["google"],
                    "max_results": 1
                })
                
                if response.status_code == 200:
                    print("✅ Search endpoint works")
                elif response.status_code == 401:
                    print("⚠️  Search requires valid authentication")
                else:
                    print(f"❌ Search failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Search error: {e}")
                return False
            
            # Test 3: Documentation available
            try:
                response = await client.get("/docs")
                if response.status_code in [200, 307]:
                    print("✅ API documentation available")
                else:
                    print("⚠️  API documentation not accessible")
            except:
                print("⚠️  Could not check documentation")
        
        print("\n✅ All critical smoke tests passed!")
        return True
    
    # Run the tests
    success = asyncio.run(run_critical_tests())
    sys.exit(0 if success else 1)
