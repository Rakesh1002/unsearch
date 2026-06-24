"""
Integration tests for RAG API endpoints.
"""
import pytest
from datetime import datetime
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from app.models.responses import SearchResult
from app.services.rag import RAGService, ResearchSource, ResearchResult, VectorStore


@pytest.fixture
def mock_rag_service():
    """Create a mock RAG service."""
    service = MagicMock(spec=RAGService)
    service.vector_store = VectorStore()
    return service


@pytest.fixture
def sample_research_request():
    """Sample research request data."""
    return {
        "topic": "machine learning fundamentals",
        "depth": "quick",
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
        "corpus_id": "test_corpus_123",
        "query": "neural networks",
        "limit": 10,
        "min_relevance": 0.5
    }


@pytest.fixture
def sample_image_search_request():
    """Sample image search request data."""
    return {
        "query": "machine learning diagrams",
        "max_results": 10,
        "safe_search": "moderate",
        "engines": ["google images", "bing images"]
    }


@pytest.mark.asyncio
class TestRAGResearchEndpoint:
    """Test RAG research API endpoint."""
    
    async def test_research_endpoint_success(
        self,
        authenticated_client: AsyncClient,
        sample_research_request,
        mock_rag_service
    ):
        """Test successful research operation."""
        # Mock research result
        mock_sources = [
            ResearchSource(
                url="https://example.com/ml-intro",
                title="Machine Learning Introduction",
                content="Machine learning is a subset of artificial intelligence...",
                relevance_score=0.85,
                word_count=500,
                metadata={"engine": "google"}
            )
        ]
        mock_result = ResearchResult(
            query="machine learning fundamentals",
            sources=mock_sources,
            total_sources_found=10,
            queries_executed=["machine learning fundamentals", "what is machine learning"],
            processing_time_ms=5000,
            corpus_id="abc123"
        )
        
        mock_rag_service.deep_research = AsyncMock(return_value=mock_result)
        mock_rag_service.generate_research_queries = MagicMock(return_value=["query1", "query2"])
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/research",
                json=sample_research_request
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "topic" in data
        assert "sources" in data
        assert "corpus_id" in data
        assert "queries_executed" in data
        assert data["topic"] == "machine learning fundamentals"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["url"] == "https://example.com/ml-intro"
    
    async def test_research_endpoint_unauthorized(
        self,
        client: AsyncClient,
        sample_research_request
    ):
        """Test research without authentication."""
        response = await client.post(
            "/api/v1/rag/research",
            json=sample_research_request
        )
        
        assert response.status_code == 401
    
    async def test_research_endpoint_invalid_depth(
        self,
        authenticated_client: AsyncClient
    ):
        """Test research with invalid depth value."""
        response = await authenticated_client.post(
            "/api/v1/rag/research",
            json={
                "topic": "test",
                "depth": "invalid_depth"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_research_endpoint_different_depths(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test research with different depth settings."""
        mock_result = ResearchResult(
            query="test topic",
            sources=[],
            total_sources_found=0,
            queries_executed=["test topic"],
            processing_time_ms=1000
        )
        mock_rag_service.deep_research = AsyncMock(return_value=mock_result)
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            for depth in ["quick", "standard", "deep"]:
                response = await authenticated_client.post(
                    "/api/v1/rag/research",
                    json={
                        "topic": "test topic",
                        "depth": depth
                    }
                )
                
                assert response.status_code == 200
                assert response.json()["depth"] == depth


@pytest.mark.asyncio
class TestRAGSearchEndpoint:
    """Test RAG quick search API endpoint."""
    
    async def test_quick_search_success(
        self,
        authenticated_client: AsyncClient,
        sample_quick_search_request,
        mock_rag_service
    ):
        """Test successful quick search."""
        mock_rag_service.search_and_answer = AsyncMock(return_value={
            "query": "what is machine learning",
            "context": "[Source 1] Machine learning is...",
            "sources": [
                {
                    "url": "https://example.com/ml",
                    "title": "ML Guide",
                    "content": "Machine learning content...",
                    "relevance_score": 0.9,
                    "word_count": 100,
                    "metadata": {"engine": "google"},
                    "scraped_at": datetime.utcnow().isoformat()
                }
            ],
            "source_count": 1,
            "processing_time_ms": 2000
        })
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/search",
                json=sample_quick_search_request
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "what is machine learning"
        assert "context" in data
        assert "sources" in data
        assert len(data["sources"]) == 1
    
    async def test_quick_search_without_context(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test quick search without context included."""
        mock_rag_service.search_and_answer = AsyncMock(return_value={
            "query": "test query",
            "context": "Some context",
            "sources": [],
            "source_count": 0,
            "processing_time_ms": 500
        })
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/search",
                json={
                    "query": "test query",
                    "include_context": False
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["context"] is None
    
    async def test_quick_search_unauthorized(
        self,
        client: AsyncClient,
        sample_quick_search_request
    ):
        """Test quick search without authentication."""
        response = await client.post(
            "/api/v1/rag/search",
            json=sample_quick_search_request
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
class TestRAGSemanticSearchEndpoint:
    """Test RAG semantic search API endpoint."""
    
    async def test_semantic_search_success(
        self,
        authenticated_client: AsyncClient,
        sample_semantic_search_request,
        mock_rag_service
    ):
        """Test successful semantic search."""
        mock_rag_service.semantic_search = AsyncMock(return_value=[
            {
                "id": "doc_123",
                "score": 0.92,
                "url": "https://example.com/article",
                "title": "Neural Networks Explained",
                "summary": "A comprehensive guide to neural networks...",
                "relevance_score": 0.88
            }
        ])
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/semantic-search",
                json=sample_semantic_search_request
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["corpus_id"] == "test_corpus_123"
        assert data["query"] == "neural networks"
        assert len(data["results"]) == 1
        assert data["results"][0]["score"] == 0.92
    
    async def test_semantic_search_empty_results(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test semantic search with no matching results."""
        mock_rag_service.semantic_search = AsyncMock(return_value=[])
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/semantic-search",
                json={
                    "corpus_id": "empty_corpus",
                    "query": "nonexistent topic"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_results"] == 0
        assert len(data["results"]) == 0


@pytest.mark.asyncio
class TestRAGImageSearchEndpoint:
    """Test RAG image search API endpoint."""
    
    async def test_image_search_success(
        self,
        authenticated_client: AsyncClient,
        sample_image_search_request
    ):
        """Test successful image search."""
        mock_searxng = MagicMock()
        mock_searxng.search = AsyncMock(return_value=[
            SearchResult(
                rank=1,
                title="ML Diagram",
                url="https://example.com/image.png",
                snippet="Machine learning diagram",
                engine="google images",
                cached=False
            )
        ])
        
        with patch('app.api.v1.rag.get_searxng_service', return_value=mock_searxng):
            response = await authenticated_client.post(
                "/api/v1/rag/images",
                json=sample_image_search_request
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "machine learning diagrams"
        assert "images" in data
        assert "processing_time_ms" in data


@pytest.mark.asyncio
class TestRAGQueryGenerationEndpoint:
    """Test RAG query generation API endpoint."""
    
    async def test_generate_queries_success(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test successful query generation."""
        mock_rag_service.generate_research_queries = MagicMock(return_value=[
            "what is machine learning",
            "machine learning history",
            "machine learning applications"
        ])
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/generate-queries",
                params={"topic": "machine learning", "num_queries": 3}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["topic"] == "machine learning"
        assert "queries" in data
        assert len(data["queries"]) == 3
    
    async def test_generate_queries_default_count(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test query generation with default count."""
        mock_rag_service.generate_research_queries = MagicMock(
            return_value=["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10"]
        )
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/generate-queries",
                params={"topic": "AI"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["queries"]) == 10  # Default count


@pytest.mark.asyncio
class TestRAGCorpusEndpoints:
    """Test RAG corpus management API endpoints."""
    
    async def test_list_corpora(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test listing corpora."""
        # Add some vectors to simulate corpora
        mock_rag_service.vector_store._vectors = {
            "corpus_1": {"v1": {}, "v2": {}},
            "corpus_2": {"v1": {}}
        }
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.get("/api/v1/rag/corpus")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "corpora" in data
        assert data["total_count"] == 2
    
    async def test_get_corpus_info_success(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test getting corpus info."""
        mock_rag_service.vector_store.get_corpus_size = MagicMock(return_value=100)
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.get("/api/v1/rag/corpus/test_corpus/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["corpus_id"] == "test_corpus"
        assert data["vector_count"] == 100
        assert data["status"] == "active"
    
    async def test_get_corpus_info_not_found(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test getting info for non-existent corpus."""
        mock_rag_service.vector_store.get_corpus_size = MagicMock(return_value=0)
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.get("/api/v1/rag/corpus/nonexistent/info")
        
        assert response.status_code == 404
    
    async def test_delete_corpus_success(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test successful corpus deletion."""
        mock_rag_service.vector_store.get_corpus_size = MagicMock(return_value=50)
        mock_rag_service.vector_store.delete_corpus = AsyncMock()
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.delete("/api/v1/rag/corpus/test_corpus")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "deleted successfully" in data["message"]
        assert data["vectors_removed"] == 50
    
    async def test_delete_corpus_not_found(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test deleting non-existent corpus."""
        mock_rag_service.vector_store.get_corpus_size = MagicMock(return_value=0)
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.delete("/api/v1/rag/corpus/nonexistent")
        
        assert response.status_code == 404


@pytest.mark.asyncio
class TestRAGErrorHandling:
    """Test RAG API error handling."""
    
    async def test_research_service_error(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test research endpoint when service throws error."""
        mock_rag_service.deep_research = AsyncMock(
            side_effect=Exception("Service unavailable")
        )
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/research",
                json={"topic": "test"}
            )
        
        assert response.status_code == 500
        assert "Research failed" in response.json()["detail"]
    
    async def test_search_service_error(
        self,
        authenticated_client: AsyncClient,
        mock_rag_service
    ):
        """Test search endpoint when service throws error."""
        mock_rag_service.search_and_answer = AsyncMock(
            side_effect=Exception("Search failed")
        )
        
        with patch('app.api.v1.rag.get_rag_service', return_value=mock_rag_service):
            response = await authenticated_client.post(
                "/api/v1/rag/search",
                json={"query": "test"}
            )
        
        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]
    
    async def test_validation_error_missing_required_field(
        self,
        authenticated_client: AsyncClient
    ):
        """Test validation error when required field is missing."""
        response = await authenticated_client.post(
            "/api/v1/rag/research",
            json={}  # Missing required 'topic' field
        )
        
        assert response.status_code == 422
