"""
Validation utilities for the UnSearch API.
"""
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
import ipaddress
from pydantic import validator


def validate_query(query: str) -> str:
    """
    Validate and sanitize search query.
    
    Args:
        query: Search query to validate
        
    Returns:
        Validated query
        
    Raises:
        ValueError: If query is invalid
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    query = query.strip()
    
    if len(query) > 500:
        raise ValueError("Query too long (max 500 characters)")
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',               # JavaScript URLs
        r'vbscript:',                # VBScript URLs
        r'onload\s*=',               # Event handlers
        r'onerror\s*=',
        r'onclick\s*=',
        r'data:text/html',           # Data URLs
        r'expression\s*\(',          # CSS expressions
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError("Query contains potentially harmful content")
    
    return query


def validate_url(url: str, allow_private: bool = False) -> str:
    """
    Validate URL for scraping.
    
    Args:
        url: URL to validate
        allow_private: Whether to allow private/local IPs
        
    Returns:
        Validated URL
        
    Raises:
        ValueError: If URL is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")
    
    if not parsed.scheme:
        raise ValueError("URL must include scheme (http/https)")
    
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS URLs are allowed")
    
    if not parsed.netloc:
        raise ValueError("URL must include hostname")
    
    # Check for dangerous characters
    if any(char in url for char in ['<', '>', '"', "'", '`']):
        raise ValueError("URL contains invalid characters")
    
    # Validate hostname
    hostname = parsed.hostname
    if hostname:
        # Check if it's an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if not allow_private and (ip.is_private or ip.is_loopback or ip.is_reserved):
                raise ValueError("Private/local IP addresses are not allowed")
        except ValueError:
            # Not an IP, validate hostname
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', hostname):
                raise ValueError("Invalid hostname format")
    
    return url


def validate_engines(engines: List[str]) -> List[str]:
    """
    Validate search engines list.
    
    Args:
        engines: List of engine names
        
    Returns:
        Validated engines list
        
    Raises:
        ValueError: If engines list is invalid
    """
    if not engines:
        raise ValueError("At least one search engine must be specified")
    
    allowed_engines = {
        'google', 'bing', 'duckduckgo', 'startpage', 'qwant',
        'yahoo', 'searx', 'brave', 'ecosia', 'yandex'
    }
    
    # Validate each engine
    validated = []
    for engine in engines:
        if not isinstance(engine, str):
            raise ValueError("Engine names must be strings")
        
        engine = engine.lower().strip()
        if not engine:
            continue
            
        if engine not in allowed_engines:
            raise ValueError(f"Unsupported search engine: {engine}")
        
        if engine not in validated:
            validated.append(engine)
    
    if not validated:
        raise ValueError("No valid search engines provided")
    
    return validated


def validate_language_code(language: str) -> str:
    """
    Validate ISO 639-1 language code.
    
    Args:
        language: Language code to validate
        
    Returns:
        Validated language code
        
    Raises:
        ValueError: If language code is invalid
    """
    if not isinstance(language, str):
        raise ValueError("Language code must be a string")
    
    language = language.lower().strip()
    
    if not re.match(r'^[a-z]{2}$', language):
        raise ValueError("Language code must be a 2-letter ISO 639-1 code")
    
    # Common language codes (not exhaustive, but covers main ones)
    valid_codes = {
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko',
        'ar', 'hi', 'tr', 'pl', 'nl', 'sv', 'da', 'no', 'fi', 'he',
        'th', 'vi', 'id', 'ms', 'tl', 'sw', 'am', 'bn', 'ta', 'te',
        'ml', 'kn', 'gu', 'or', 'pa', 'as', 'ne', 'si', 'my', 'km'
    }
    
    if language not in valid_codes:
        # Allow it but log a warning
        pass
    
    return language


def validate_css_selector(selector: str) -> str:
    """
    Validate CSS selector for safety.
    
    Args:
        selector: CSS selector to validate
        
    Returns:
        Validated selector
        
    Raises:
        ValueError: If selector is invalid or dangerous
    """
    if not selector or not selector.strip():
        raise ValueError("CSS selector cannot be empty")
    
    selector = selector.strip()
    
    if len(selector) > 200:
        raise ValueError("CSS selector too long (max 200 characters)")
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'javascript:',
        r'expression\s*\(',
        r'behavior\s*:',
        r'@import',
        r'url\s*\(',
        r'<.*?>',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, selector, re.IGNORECASE):
            raise ValueError("CSS selector contains potentially harmful content")
    
    # Basic CSS selector validation
    if not re.match(r'^[a-zA-Z0-9\s\.\#\[\]\(\)\:\-\*\>\+\~\,\"\'=\|\_]+$', selector):
        raise ValueError("CSS selector contains invalid characters")
    
    return selector


def validate_custom_selectors(selectors: Dict[str, str]) -> Dict[str, str]:
    """
    Validate custom CSS selectors dictionary.
    
    Args:
        selectors: Dictionary of custom selectors
        
    Returns:
        Validated selectors
        
    Raises:
        ValueError: If selectors are invalid
    """
    if not isinstance(selectors, dict):
        raise ValueError("Custom selectors must be a dictionary")
    
    if len(selectors) > 20:
        raise ValueError("Too many custom selectors (max 20)")
    
    validated = {}
    
    for field, selector in selectors.items():
        # Validate field name
        if not isinstance(field, str) or not field.strip():
            raise ValueError("Selector field names must be non-empty strings")
        
        field = field.strip()
        if len(field) > 50:
            raise ValueError(f"Selector field name too long: {field}")
        
        if not re.match(r'^[a-zA-Z0-9_]+$', field):
            raise ValueError(f"Invalid field name: {field}")
        
        # Validate selector
        validated[field] = validate_css_selector(selector)
    
    return validated


def validate_webhook_url(url: str) -> str:
    """
    Validate webhook URL.
    
    Args:
        url: Webhook URL to validate
        
    Returns:
        Validated URL
        
    Raises:
        ValueError: If URL is invalid for webhooks
    """
    validated_url = validate_url(url, allow_private=False)
    
    # Additional webhook-specific validations
    parsed = urlparse(validated_url)
    
    # Must be HTTPS in production
    if parsed.scheme != 'https':
        # Allow HTTP for development/testing
        pass
    
    # Check path doesn't contain suspicious elements
    if parsed.path:
        if any(suspicious in parsed.path.lower() for suspicious in ['admin', 'config', 'internal']):
            raise ValueError("Webhook URL path appears to target internal endpoints")
    
    return validated_url


def validate_timeout(timeout: int, min_timeout: int = 5, max_timeout: int = 120) -> int:
    """
    Validate timeout value.
    
    Args:
        timeout: Timeout in seconds
        min_timeout: Minimum allowed timeout
        max_timeout: Maximum allowed timeout
        
    Returns:
        Validated timeout
        
    Raises:
        ValueError: If timeout is invalid
    """
    if not isinstance(timeout, int):
        raise ValueError("Timeout must be an integer")
    
    if timeout < min_timeout:
        raise ValueError(f"Timeout too low (minimum {min_timeout} seconds)")
    
    if timeout > max_timeout:
        raise ValueError(f"Timeout too high (maximum {max_timeout} seconds)")
    
    return timeout


def validate_cache_ttl(ttl: int) -> int:
    """
    Validate cache TTL value.
    
    Args:
        ttl: TTL in seconds
        
    Returns:
        Validated TTL
        
    Raises:
        ValueError: If TTL is invalid
    """
    if not isinstance(ttl, int):
        raise ValueError("Cache TTL must be an integer")
    
    if ttl < 0:
        raise ValueError("Cache TTL cannot be negative")
    
    if ttl > 86400:  # 24 hours
        raise ValueError("Cache TTL too high (maximum 24 hours)")
    
    return ttl


def validate_max_results(max_results: int) -> int:
    """
    Validate max results parameter.
    
    Args:
        max_results: Maximum number of results
        
    Returns:
        Validated max results
        
    Raises:
        ValueError: If max results is invalid
    """
    if not isinstance(max_results, int):
        raise ValueError("Max results must be an integer")
    
    if max_results < 1:
        raise ValueError("Max results must be at least 1")
    
    if max_results > 100:
        raise ValueError("Max results too high (maximum 100)")
    
    return max_results
