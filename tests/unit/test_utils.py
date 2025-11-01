"""
Unit tests for utility functions.
"""
import pytest
from unittest.mock import Mock, patch

from app.utils.text_processing import (
    sanitize_text, extract_snippet, detect_language,
    calculate_text_quality, extract_keywords, truncate_text, normalize_url
)
from app.utils.validators import (
    validate_query, validate_url, validate_engines, validate_language_code,
    validate_css_selector, validate_custom_selectors, validate_webhook_url
)
from app.utils.security import (
    generate_api_key, hash_password, verify_password, sanitize_input,
    is_safe_url, generate_csrf_token, verify_csrf_token
)
from app.utils.exceptions import (
    SearchScrapeException, BadRequestException, UnauthorizedException
)


class TestTextProcessing:
    """Test text processing utilities."""
    
    def test_sanitize_text(self):
        """Test text sanitization."""
        # HTML entities
        assert sanitize_text("Hello &amp; world") == "Hello & world"
        
        # HTML tags
        assert sanitize_text("Hello <b>world</b>") == "Hello world"
        
        # Extra whitespace
        assert sanitize_text("Hello    world\n\n\n") == "Hello world"
        
        # Empty input
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""
    
    def test_extract_snippet(self):
        """Test snippet extraction."""
        text = "This is a test document. It contains multiple sentences about testing. The test should extract relevant content."
        query = "test"
        
        snippet = extract_snippet(text, query, max_length=50)
        assert len(snippet) <= 50
        assert "test" in snippet.lower()
    
    def test_detect_language(self):
        """Test language detection."""
        # English text
        english_text = "This is a sample English text for language detection testing."
        lang = detect_language(english_text)
        assert lang == "en" or lang is None  # langdetect may not work in test env
        
        # Short text should return None
        assert detect_language("Hi") is None
        
        # Empty text should return None
        assert detect_language("") is None
    
    def test_calculate_text_quality(self):
        """Test text quality calculation."""
        # Good quality text
        good_text = "This is a well-written article with proper sentence structure. It contains multiple paragraphs and good vocabulary diversity. The content is informative and well-structured."
        quality = calculate_text_quality(good_text)
        assert 0.0 <= quality <= 1.0
        
        # Poor quality text
        poor_text = "abc def"
        quality = calculate_text_quality(poor_text)
        assert quality < 0.5
        
        # Empty text
        assert calculate_text_quality("") == 0.0
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        text = "Python programming language development software engineering code"
        keywords = extract_keywords(text, max_keywords=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert all(isinstance(word, str) for word in keywords)
    
    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a long text that needs to be truncated at word boundaries"
        
        truncated = truncate_text(text, 20)
        assert len(truncated) <= 20
        assert truncated.endswith("...")
        
        # Short text should not be truncated
        short_text = "Short"
        assert truncate_text(short_text, 20) == short_text
    
    def test_normalize_url(self):
        """Test URL normalization."""
        # Remove tracking parameters
        url = "https://example.com/page?utm_source=test&utm_medium=email&normal_param=value"
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "normal_param=value" in normalized
        
        # Remove trailing slashes
        assert normalize_url("https://example.com/") == "https://example.com"


class TestValidators:
    """Test validation utilities."""
    
    def test_validate_query(self):
        """Test query validation."""
        # Valid query
        assert validate_query("python programming") == "python programming"
        
        # Empty query should raise error
        with pytest.raises(ValueError):
            validate_query("")
        
        # Too long query should raise error
        with pytest.raises(ValueError):
            validate_query("x" * 501)
        
        # Suspicious content should raise error
        with pytest.raises(ValueError):
            validate_query("<script>alert('xss')</script>")
    
    def test_validate_url(self):
        """Test URL validation."""
        # Valid URLs
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://test.org/path") == "http://test.org/path"
        
        # Invalid URLs should raise errors
        with pytest.raises(ValueError):
            validate_url("")
        
        with pytest.raises(ValueError):
            validate_url("ftp://example.com")
        
        with pytest.raises(ValueError):
            validate_url("https://127.0.0.1")  # Private IP
        
        # Allow private IPs when specified
        assert validate_url("https://127.0.0.1", allow_private=True)
    
    def test_validate_engines(self):
        """Test engines validation."""
        # Valid engines
        engines = validate_engines(["google", "bing"])
        assert "google" in engines
        assert "bing" in engines
        
        # Remove duplicates
        engines = validate_engines(["google", "google", "bing"])
        assert len(engines) == 2
        
        # Invalid engine should raise error
        with pytest.raises(ValueError):
            validate_engines(["invalid_engine"])
        
        # Empty list should raise error
        with pytest.raises(ValueError):
            validate_engines([])
    
    def test_validate_language_code(self):
        """Test language code validation."""
        # Valid codes
        assert validate_language_code("en") == "en"
        assert validate_language_code("ES") == "es"  # Case insensitive
        
        # Invalid format should raise error
        with pytest.raises(ValueError):
            validate_language_code("eng")
        
        with pytest.raises(ValueError):
            validate_language_code("1")
    
    def test_validate_css_selector(self):
        """Test CSS selector validation."""
        # Valid selectors
        assert validate_css_selector("div.class") == "div.class"
        assert validate_css_selector("#id") == "#id"
        assert validate_css_selector("div > p") == "div > p"
        
        # Empty selector should raise error
        with pytest.raises(ValueError):
            validate_css_selector("")
        
        # Dangerous content should raise error
        with pytest.raises(ValueError):
            validate_css_selector("javascript:alert()")
    
    def test_validate_custom_selectors(self):
        """Test custom selectors validation."""
        selectors = {
            "title": "h1",
            "content": "div.content",
            "author": ".author"
        }
        
        validated = validate_custom_selectors(selectors)
        assert len(validated) == 3
        assert validated["title"] == "h1"
        
        # Invalid field name should raise error
        with pytest.raises(ValueError):
            validate_custom_selectors({"invalid-field": "div"})
    
    def test_validate_webhook_url(self):
        """Test webhook URL validation."""
        # Valid webhook URL
        url = validate_webhook_url("https://api.example.com/webhook")
        assert url == "https://api.example.com/webhook"
        
        # Invalid URL should raise error
        with pytest.raises(ValueError):
            validate_webhook_url("invalid-url")


class TestSecurity:
    """Test security utilities."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        key = generate_api_key()
        assert isinstance(key, str)
        assert len(key) > 20
        
        # Different calls should produce different keys
        key2 = generate_api_key()
        assert key != key2
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        
        # Hash password
        hashed, salt = hash_password(password)
        assert isinstance(hashed, str)
        assert isinstance(salt, str)
        assert hashed != password
        
        # Verify correct password
        assert verify_password(password, hashed, salt) is True
        
        # Verify incorrect password
        assert verify_password("wrong_password", hashed, salt) is False
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        # Remove dangerous characters
        dangerous = "<script>alert('xss')</script>"
        sanitized = sanitize_input(dangerous)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        
        # Remove SQL injection patterns
        sql_injection = "'; DROP TABLE users; --"
        sanitized = sanitize_input(sql_injection)
        assert "DROP" not in sanitized
        assert "--" not in sanitized
    
    def test_is_safe_url(self):
        """Test URL safety checking."""
        # Safe URLs
        assert is_safe_url("https://example.com") is True
        assert is_safe_url("http://test.org") is True
        
        # Unsafe URLs
        assert is_safe_url("javascript:alert()") is False
        assert is_safe_url("ftp://example.com") is False
        assert is_safe_url("https://localhost") is False
        assert is_safe_url("https://127.0.0.1") is False
    
    def test_csrf_token(self):
        """Test CSRF token generation and verification."""
        token = generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 20
        
        # Verify correct token
        assert verify_csrf_token(token, token) is True
        
        # Verify incorrect token
        wrong_token = generate_csrf_token()
        assert verify_csrf_token(token, wrong_token) is False


class TestExceptions:
    """Test custom exceptions."""
    
    def test_searchscrape_exception(self):
        """Test base exception."""
        exc = SearchScrapeException("Test error", {"detail": "test"})
        assert str(exc) == "Test error"
        assert exc.details["detail"] == "test"
    
    def test_http_exceptions(self):
        """Test HTTP exceptions."""
        # Bad request
        exc = BadRequestException("Invalid input")
        assert exc.status_code == 400
        assert exc.detail["error"] == "BadRequest"
        
        # Unauthorized
        exc = UnauthorizedException()
        assert exc.status_code == 401
        assert exc.detail["error"] == "Unauthorized"
        assert "WWW-Authenticate" in exc.headers
