"""
Unit tests for RAG (Retrieval-Augmented Generation) service components.
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx

from app.services.rag import (
    RAGService, 
    EmbeddingService, 
    VectorStore,
    ResearchSource,
    ResearchResult,
    get_rag_service
)
from app.models.responses import SearchResult


class TestResearchSource:
    """Tests for ResearchSource dataclass."""
    
    def test_create_research_source(self):
        """Test creating a ResearchSource."""
        source = ResearchSource(
            url="https://example.com/article",
            title="Test Article",
            content="This is test content for the article.",
            word_count=7
        )
        
        assert source.url == "https://example.com/article"
        assert source.title == "Test Article"
        assert source.content == "This is test content for the article."
        assert source.word_count == 7
        assert source.relevance_score == 0.0
        assert source.summary is None
        assert source.embedding is None
        assert isinstance(source.scraped_at, datetime)
    
    def test_to_dict(self):
        """Test converting ResearchSource to dict."""
        source = ResearchSource(
            url="https://example.com/article",
            title="Test Article",
            content="Short content",
            word_count=2
        )
        
        result = source.to_dict()
        
        assert result["url"] == "https://example.com/article"
        assert result["title"] == "Test Article"
        assert result["content"] == "Short content"
        assert result["word_count"] == 2
        assert "scraped_at" in result
        # scraped_at should be ISO format string
        assert isinstance(result["scraped_at"], str)
    
    def test_to_dict_truncates_long_content(self):
        """Test that to_dict truncates content longer than 1000 chars."""
        long_content = "x" * 2000
        source = ResearchSource(
            url="https://example.com/article",
            title="Test Article",
            content=long_content,
            word_count=1
        )
        
        result = source.to_dict()
        
        assert len(result["content"]) == 1000


class TestResearchResult:
    """Tests for ResearchResult dataclass."""
    
    def test_create_research_result(self):
        """Test creating a ResearchResult."""
        sources = [
            ResearchSource(
                url="https://example.com/1",
                title="Article 1",
                content="Content 1"
            )
        ]
        
        result = ResearchResult(
            query="test query",
            sources=sources,
            total_sources_found=10,
            queries_executed=["test query", "test query expanded"],
            processing_time_ms=1500
        )
        
        assert result.query == "test query"
        assert len(result.sources) == 1
        assert result.total_sources_found == 10
        assert len(result.queries_executed) == 2
        assert result.processing_time_ms == 1500
        assert result.corpus_id is None
    
    def test_to_dict(self):
        """Test converting ResearchResult to dict."""
        sources = [
            ResearchSource(
                url="https://example.com/1",
                title="Article 1",
                content="Content 1"
            )
        ]
        
        result = ResearchResult(
            query="test query",
            sources=sources,
            total_sources_found=10,
            queries_executed=["test query"],
            processing_time_ms=1500,
            corpus_id="abc123"
        )
        
        data = result.to_dict()
        
        assert data["query"] == "test query"
        assert len(data["sources"]) == 1
        assert data["total_sources_found"] == 10
        assert data["corpus_id"] == "abc123"


class TestVectorStore:
    """Tests for VectorStore."""
    
    @pytest.fixture
    async def vector_store(self):
        """Create a VectorStore instance."""
        return VectorStore()
    
    @pytest.mark.asyncio
    async def test_add_vectors(self, vector_store):
        """Test adding vectors to the store."""
        vectors = [
            ("id1", [0.1, 0.2, 0.3], {"title": "Test 1"}),
            ("id2", [0.4, 0.5, 0.6], {"title": "Test 2"}),
        ]
        
        await vector_store.add_vectors("test_corpus", vectors)
        
        assert vector_store.get_corpus_size("test_corpus") == 2
    
    @pytest.mark.asyncio
    async def test_search_basic(self, vector_store):
        """Test basic vector search."""
        # Add vectors
        vectors = [
            ("id1", [1.0, 0.0, 0.0], {"title": "Test 1"}),
            ("id2", [0.0, 1.0, 0.0], {"title": "Test 2"}),
            ("id3", [0.0, 0.0, 1.0], {"title": "Test 3"}),
        ]
        await vector_store.add_vectors("test_corpus", vectors)
        
        # Search with query similar to id1
        results = await vector_store.search(
            corpus_id="test_corpus",
            query_embedding=[0.9, 0.1, 0.0],
            limit=2
        )
        
        assert len(results) == 2
        # First result should be closest to id1
        assert results[0][0] == "id1"
        assert results[0][1] > 0.5  # High similarity
    
    @pytest.mark.asyncio
    async def test_search_with_min_score(self, vector_store):
        """Test search with minimum score filter."""
        vectors = [
            ("id1", [1.0, 0.0, 0.0], {"title": "Test 1"}),
            ("id2", [0.0, 1.0, 0.0], {"title": "Test 2"}),
        ]
        await vector_store.add_vectors("test_corpus", vectors)
        
        # Search with high min_score
        results = await vector_store.search(
            corpus_id="test_corpus",
            query_embedding=[1.0, 0.0, 0.0],
            limit=10,
            min_score=0.9
        )
        
        # Only id1 should match
        assert len(results) == 1
        assert results[0][0] == "id1"
    
    @pytest.mark.asyncio
    async def test_search_empty_corpus(self, vector_store):
        """Test search on non-existent corpus."""
        results = await vector_store.search(
            corpus_id="nonexistent",
            query_embedding=[1.0, 0.0, 0.0],
            limit=10
        )
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_delete_corpus(self, vector_store):
        """Test deleting a corpus."""
        vectors = [
            ("id1", [1.0, 0.0, 0.0], {"title": "Test 1"}),
        ]
        await vector_store.add_vectors("test_corpus", vectors)
        
        assert vector_store.get_corpus_size("test_corpus") == 1
        
        await vector_store.delete_corpus("test_corpus")
        
        assert vector_store.get_corpus_size("test_corpus") == 0
    
    @pytest.mark.asyncio
    async def test_get_corpus_size(self, vector_store):
        """Test getting corpus size."""
        assert vector_store.get_corpus_size("nonexistent") == 0
        
        vectors = [
            ("id1", [1.0, 0.0, 0.0], {"title": "Test 1"}),
            ("id2", [0.0, 1.0, 0.0], {"title": "Test 2"}),
        ]
        await vector_store.add_vectors("test_corpus", vectors)
        
        assert vector_store.get_corpus_size("test_corpus") == 2


class TestEmbeddingService:
    """Tests for EmbeddingService."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create an EmbeddingService instance."""
        return EmbeddingService(api_key="test-api-key")
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self, embedding_service):
        """Test successful embedding generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3] * 512},
                {"embedding": [0.4, 0.5, 0.6] * 512}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(embedding_service, '_client') as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            
            embeddings = await embedding_service.generate_embeddings(
                ["text 1", "text 2"]
            )
            
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 1536
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_no_api_key(self):
        """Test embedding generation without API key returns zero vectors."""
        service = EmbeddingService(api_key=None)
        service._client = Mock()  # Fake initialized client
        
        embeddings = await service.generate_embeddings(["test"])
        
        assert len(embeddings) == 1
        assert embeddings[0] == [0.0] * 768
    
    @pytest.mark.asyncio
    async def test_generate_single_embedding(self, embedding_service):
        """Test generating a single embedding."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3] * 512}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(embedding_service, '_client') as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            
            embedding = await embedding_service.generate_single_embedding("test text")
            
            assert len(embedding) == 1536


class TestRAGService:
    """Tests for RAGService."""
    
    @pytest.fixture
    async def rag_service(self):
        """Create a RAGService instance with mocked dependencies."""
        service = RAGService()
        
        # Mock dependent services
        service.searxng = Mock()
        service.scraper = Mock()
        
        # Create async mock for embedding service
        mock_embedding = AsyncMock()
        mock_embedding.close = AsyncMock()
        service.embedding_service = mock_embedding
        
        service.vector_store = VectorStore()
        service._initialized = True
        
        yield service
        
        await service.close()
    
    def test_generate_research_queries_default(self, rag_service):
        """Test generating research queries with default settings."""
        queries = rag_service.generate_research_queries(
            topic="machine learning",
            num_queries=5
        )
        
        assert len(queries) == 5
        assert "machine learning" in queries[0].lower()
    
    def test_generate_research_queries_all_categories(self, rag_service):
        """Test generating queries covers multiple categories."""
        queries = rag_service.generate_research_queries(
            topic="python programming",
            num_queries=10
        )
        
        assert len(queries) == 10
        
        # Check that different query types are generated
        queries_lower = [q.lower() for q in queries]
        has_overview = any("what is" in q or "explained" in q for q in queries_lower)
        has_history = any("history" in q or "evolution" in q for q in queries_lower)
        
        assert has_overview or has_history  # At least some variety
    
    def test_generate_research_queries_custom_categories(self, rag_service):
        """Test generating queries with specific categories."""
        queries = rag_service.generate_research_queries(
            topic="AI ethics",
            num_queries=3,
            include_categories=["overview", "practical"]
        )
        
        assert len(queries) == 3
    
    def test_calculate_relevance(self, rag_service):
        """Test relevance score calculation."""
        source = ResearchSource(
            url="https://example.com/ml-article",
            title="Machine Learning Guide",
            content="This comprehensive machine learning guide covers neural networks and deep learning fundamentals with practical examples.",
            word_count=15
        )
        
        score = rag_service._calculate_relevance(source, "machine learning")
        
        # Should have reasonable score since title and content contain query terms
        assert 0.0 <= score <= 1.0
        assert score > 0.3  # Should have some relevance
    
    def test_calculate_relevance_no_match(self, rag_service):
        """Test relevance score for non-matching content."""
        source = ResearchSource(
            url="https://example.com/cooking",
            title="Cooking Recipes",
            content="Learn to cook delicious meals with these easy recipes.",
            word_count=10
        )
        
        score = rag_service._calculate_relevance(source, "machine learning")
        
        # Should have low score since no query terms match
        assert score < 0.3
    
    @pytest.mark.asyncio
    async def test_search_and_answer(self, rag_service):
        """Test search_and_answer returns properly formatted results."""
        # Mock search results
        mock_search_results = [
            SearchResult(
                rank=1,
                title="Test Result",
                url="https://example.com/test",
                snippet="Test content snippet",
                engine="google",
                cached=False
            )
        ]
        
        # Mock scraping results
        mock_scraped = Mock()
        mock_scraped.url = "https://example.com/test"
        mock_scraped.text = "Full article content here"
        mock_scraped.word_count = 5
        mock_scraped.extraction_success = True
        
        rag_service.searxng.search = AsyncMock(return_value=mock_search_results)
        rag_service.scraper.scrape_urls = AsyncMock(return_value=[mock_scraped])
        
        result = await rag_service.search_and_answer(
            query="test query",
            max_sources=5,
            scrape_content=True
        )
        
        assert "query" in result
        assert "sources" in result
        assert "context" in result
        assert result["query"] == "test query"
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, rag_service):
        """Test semantic search over corpus."""
        # Add some vectors to the store
        vectors = [
            ("id1", [1.0, 0.0, 0.0] * 512, {"url": "https://example.com/1", "title": "Article 1", "summary": "Summary 1"}),
            ("id2", [0.0, 1.0, 0.0] * 512, {"url": "https://example.com/2", "title": "Article 2", "summary": "Summary 2"}),
        ]
        await rag_service.vector_store.add_vectors("test_corpus", vectors)
        
        # Mock embedding generation
        rag_service.embedding_service.generate_single_embedding = AsyncMock(
            return_value=[1.0, 0.0, 0.0] * 512
        )
        
        results = await rag_service.semantic_search(
            corpus_id="test_corpus",
            query="test query",
            limit=5,
            min_relevance=0.0
        )
        
        assert len(results) > 0
        assert "id" in results[0]
        assert "score" in results[0]


class TestRAGServiceIntegration:
    """Integration tests for RAGService components working together."""
    
    @pytest.mark.asyncio
    async def test_vector_store_with_embedding_service(self):
        """Test vector store works with embedding service output."""
        vector_store = VectorStore()
        
        # Simulate embedding service output
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        
        vectors = [
            (f"id_{i}", emb, {"title": f"Test {i}"})
            for i, emb in enumerate(embeddings)
        ]
        
        await vector_store.add_vectors("test_corpus", vectors)
        
        # Search
        results = await vector_store.search(
            corpus_id="test_corpus",
            query_embedding=[0.15] * 1536,
            limit=2
        )
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self):
        """Test the full RAG pipeline with mocks."""
        service = RAGService()
        service._initialized = True
        
        # Mock all dependencies
        service.searxng = Mock()
        service.searxng.search = AsyncMock(return_value=[
            SearchResult(
                rank=1,
                title="Python Guide",
                url="https://example.com/python",
                snippet="Learn Python programming",
                engine="google",
                cached=False
            )
        ])
        
        service.scraper = Mock()
        mock_scraped = Mock()
        mock_scraped.url = "https://example.com/python"
        mock_scraped.text = "Python is a programming language used for web development, data science, and more."
        mock_scraped.word_count = 15
        mock_scraped.extraction_success = True
        service.scraper.scrape_urls = AsyncMock(return_value=[mock_scraped])
        
        mock_embedding = AsyncMock()
        mock_embedding.generate_embeddings = AsyncMock(return_value=[[0.1] * 1536])
        mock_embedding.initialize = AsyncMock()
        mock_embedding.close = AsyncMock()
        service.embedding_service = mock_embedding
        
        service.vector_store = VectorStore()
        
        # Execute search_and_answer
        result = await service.search_and_answer(
            query="python programming",
            max_sources=5,
            scrape_content=True,
            engines=["google"]
        )
        
        assert result["query"] == "python programming"
        assert len(result["sources"]) > 0
        assert result["source_count"] > 0
        
        await service.close()
