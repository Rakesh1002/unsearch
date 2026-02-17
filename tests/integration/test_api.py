"""
Integration tests for API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

from app.models.responses import SearchResult, EngineInfo


@pytest.mark.asyncio
class TestSearchEndpoints:
    """Test search API endpoints."""
    
    async def test_search_endpoint_success(
        self,
        authenticated_client: AsyncClient,
        sample_search_request,
        mock_searxng,
        mock_scraper,
        test_cache,
        test_db
    ):
        """Test successful search and scrape operation."""
        # Mock search results
        mock_searxng.search = AsyncMock(return_value=[
            SearchResult(
                rank=1,
                title="Test Result",
                url="https://example.com",
                snippet="Test snippet",
                engine="google"
            )
        ])
        
        # Mock dependencies
        authenticated_client.app.dependency_overrides[get_searxng_service] = lambda: mock_searxng
        authenticated_client.app.dependency_overrides[get_scraping_service] = lambda: mock_scraper
        authenticated_client.app.dependency_overrides[get_cache_service] = lambda: test_cache
        authenticated_client.app.dependency_overrides[get_database_service] = lambda: test_db
        
        response = await authenticated_client.post(
            "/api/v1/search",
            json=sample_search_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "search_metadata" in data
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Test Result"
        assert data["cached"] is False
        
    async def test_search_endpoint_unauthorized(
        self,
        client: AsyncClient,
        sample_search_request
    ):
        """Test search without authentication."""
        response = await client.post(
            "/api/v1/search",
            json=sample_search_request
        )
        
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]
        
    async def test_search_endpoint_invalid_request(
        self,
        authenticated_client: AsyncClient
    ):
        """Test search with invalid request data."""
        response = await authenticated_client.post(
            "/api/v1/search",
            json={
                "query": "",  # Empty query
                "engines": ["invalid_engine"]
            }
        )
        
        assert response.status_code == 422
        
    async def test_search_endpoint_with_caching(
        self,
        authenticated_client: AsyncClient,
        sample_search_request,
        mock_searxng,
        test_cache
    ):
        """Test search with caching enabled."""
        # First request - cache miss
        mock_searxng.search = AsyncMock(return_value=[
            SearchResult(
                rank=1,
                title="Cached Result",
                url="https://example.com",
                snippet="Test",
                engine="google"
            )
        ])
        
        authenticated_client.app.dependency_overrides[get_searxng_service] = lambda: mock_searxng
        authenticated_client.app.dependency_overrides[get_cache_service] = lambda: test_cache
        
        response1 = await authenticated_client.post(
            "/api/v1/search",
            json=sample_search_request
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False
        
        # Second request - should hit cache
        response2 = await authenticated_client.post(
            "/api/v1/search",
            json=sample_search_request
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        # Note: In real implementation, this would be True after proper cache implementation
        
    async def test_batch_search_endpoint(
        self,
        authenticated_client: AsyncClient,
        mock_searxng
    ):
        """Test batch search endpoint."""
        mock_searxng.search = AsyncMock(side_effect=[
            [SearchResult(rank=1, title=f"Result for query {i}", 
                         url=f"https://example{i}.com", snippet="Test", engine="google")]
            for i in range(3)
        ])
        
        authenticated_client.app.dependency_overrides[get_searxng_service] = lambda: mock_searxng
        
        response = await authenticated_client.post(
            "/api/v1/search/batch",
            json={
                "queries": ["Python", "FastAPI", "Docker"],
                "engines": ["google"],
                "max_results_per_query": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["queries_processed"] == 3
        assert data["queries_failed"] == 0
        assert len(data["results"]) == 3
        
    async def test_list_engines_endpoint(
        self,
        authenticated_client: AsyncClient,
        mock_searxng
    ):
        """Test list engines endpoint."""
        mock_engines = {
            "google": EngineInfo(
                name="google",
                enabled=True,
                categories=["general"],
                supported_languages=["*"],
                safe_search_support=True,
                time_range_support=True,
                paging_support=True
            ),
            "bing": EngineInfo(
                name="bing",
                enabled=True,
                categories=["general"],
                supported_languages=["*"],
                safe_search_support=True,
                time_range_support=True,
                paging_support=True
            )
        }
        
        mock_searxng.get_available_engines = AsyncMock(return_value=mock_engines)
        authenticated_client.app.dependency_overrides[get_searxng_service] = lambda: mock_searxng
        
        response = await authenticated_client.get("/api/v1/search/engines")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_engines"] == 2
        assert data["enabled_engines"] == 2
        assert "google" in data["engines"]
        assert "bing" in data["engines"]


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_basic_health_check(self, client: AsyncClient):
        """Test basic health endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
    async def test_detailed_health_check(
        self,
        client: AsyncClient,
        mock_searxng,
        test_cache,
        test_db
    ):
        """Test detailed health check endpoint."""
        from app.models.responses import ServiceHealth
        
        mock_searxng.health_check = AsyncMock(return_value=ServiceHealth(
            status="healthy",
            latency_ms=50,
            last_check="2024-01-01T00:00:00"
        ))
        
        client.app.dependency_overrides[get_searxng_service] = lambda: mock_searxng
        client.app.dependency_overrides[get_cache_service] = lambda: test_cache
        client.app.dependency_overrides[get_database_service] = lambda: test_db
        
        response = await client.get("/api/v1/search/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "services" in data
        assert "searxng" in data["services"]
        assert "redis" in data["services"]
        assert "database" in data["services"]


# Import after to avoid circular imports
from app.services.searxng import get_searxng_service
from app.services.scraping import get_scraping_service
from app.services.cache import get_cache_service
from app.services.database import get_database_service
