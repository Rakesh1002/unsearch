"""
Unit tests for data models.
"""
import pytest
from pydantic import ValidationError

from app.models.requests import SearchScrapeRequest, BatchSearchRequest
from app.models.responses import SearchResult, ScrapedContent, SearchScrapeResponse


class TestSearchScrapeRequest:
    """Test SearchScrapeRequest model."""
    
    def test_valid_request(self):
        """Test creating valid request."""
        request = SearchScrapeRequest(
            query="Python tutorials",
            engines=["google", "bing"],
            max_results=10
        )
        
        assert request.query == "Python tutorials"
        assert request.engines == ["google", "bing"]
        assert request.max_results == 10
        assert request.scrape_content is True  # Default
        assert request.language == "en"  # Default
        
    def test_query_validation(self):
        """Test query validation."""
        # Empty query
        with pytest.raises(ValidationError):
            SearchScrapeRequest(query="", engines=["google"])
            
        # Query too long
        with pytest.raises(ValidationError):
            SearchScrapeRequest(query="x" * 501, engines=["google"])
            
    def test_engine_validation(self):
        """Test engine validation."""
        # Invalid engine
        with pytest.raises(ValidationError):
            SearchScrapeRequest(
                query="test",
                engines=["google", "invalid_engine"]
            )
            
        # Duplicate engines removed
        request = SearchScrapeRequest(
            query="test",
            engines=["google", "google", "bing"]
        )
        assert request.engines == ["google", "bing"]
        
    def test_language_validation(self):
        """Test language code validation."""
        # Valid language
        request = SearchScrapeRequest(
            query="test",
            engines=["google"],
            language="fr"
        )
        assert request.language == "fr"
        
        # Invalid language format
        with pytest.raises(ValidationError):
            SearchScrapeRequest(
                query="test",
                engines=["google"],
                language="eng"  # Should be 2 letters
            )
            
    def test_async_mode_validation(self):
        """Test async mode validation."""
        # Async mode without webhook
        with pytest.raises(ValidationError):
            SearchScrapeRequest(
                query="test",
                engines=["google"],
                async_mode=True,
                webhook_url=None
            )
            
        # Valid async mode
        request = SearchScrapeRequest(
            query="test",
            engines=["google"],
            async_mode=True,
            webhook_url="https://example.com/webhook"
        )
        assert request.async_mode is True
        assert str(request.webhook_url) == "https://example.com/webhook"


class TestBatchSearchRequest:
    """Test BatchSearchRequest model."""
    
    def test_valid_batch_request(self):
        """Test creating valid batch request."""
        request = BatchSearchRequest(
            queries=["Python", "FastAPI", "Web scraping"],
            engines=["google"],
            max_results_per_query=5
        )
        
        assert len(request.queries) == 3
        assert request.max_results_per_query == 5
        assert request.scrape_content is False  # Default for batch
        
    def test_batch_limits(self):
        """Test batch size limits."""
        # Too many queries
        with pytest.raises(ValidationError):
            BatchSearchRequest(
                queries=["query"] * 101,  # Max is 100
                engines=["google"]
            )
            
        # Empty queries
        with pytest.raises(ValidationError):
            BatchSearchRequest(
                queries=[],
                engines=["google"]
            )


class TestSearchResult:
    """Test SearchResult model."""
    
    def test_valid_result(self):
        """Test creating valid search result."""
        result = SearchResult(
            rank=1,
            title="Test Result",
            url="https://example.com",
            snippet="This is a test snippet",
            engine="google"
        )
        
        assert result.rank == 1
        assert result.title == "Test Result"
        assert str(result.url) == "https://example.com/"
        assert result.cached is False  # Default
        
    def test_with_scraped_content(self):
        """Test result with scraped content."""
        scraped = ScrapedContent(
            url="https://example.com",
            title="Page Title",
            text="Page content",
            extraction_success=True,
            extraction_time_ms=100,
            word_count=50,
            metadata={},
            content_quality_score=0.8
        )
        
        result = SearchResult(
            rank=1,
            title="Test",
            url="https://example.com",
            snippet="Test",
            engine="google",
            scraped_content=scraped
        )
        
        assert result.scraped_content is not None
        assert result.scraped_content.extraction_success is True


class TestSearchScrapeResponse:
    """Test SearchScrapeResponse model."""
    
    def test_response_serialization(self, sample_search_result):
        """Test response serialization."""
        from app.models.responses import SearchMetadata
        
        metadata = SearchMetadata(
            query="test",
            engines_used=["google"],
            engines_succeeded=["google"],
            engines_failed=[],
            total_results_found=10,
            results_returned=1,
            search_time_ms=500
        )
        
        response = SearchScrapeResponse(
            search_metadata=metadata,
            results=[SearchResult(**sample_search_result)],
            processing_time_ms=1000,
            cached=False,
            total_results=1,
            request_id="test-123"
        )
        
        # Test JSON serialization
        json_data = response.json()
        assert "search_metadata" in json_data
        assert "results" in json_data
        
        # Test dict conversion
        dict_data = response.dict()
        assert dict_data["request_id"] == "test-123"
        assert dict_data["processing_time_ms"] == 1000
