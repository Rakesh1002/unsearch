"""
Utility functions for the UnSearch API.
"""
from app.utils.text_processing import (
    sanitize_text,
    extract_snippet,
    detect_language,
    calculate_text_quality,
    extract_keywords,
    truncate_text,
    normalize_url
)
from app.utils.validators import (
    validate_query,
    validate_url,
    validate_engines,
    validate_language_code,
    validate_css_selector,
    validate_custom_selectors,
    validate_webhook_url,
    validate_timeout,
    validate_cache_ttl,
    validate_max_results
)
from app.utils.security import (
    generate_api_key,
    hash_password,
    verify_password,
    sanitize_input,
    is_safe_url,
    generate_csrf_token,
    verify_csrf_token,
    SecurityHeaders
)
from app.utils.exceptions import (
    UnSearchException,
    SearXNGException,
    ScrapingException,
    CacheException,
    DatabaseException,
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    TooManyRequestsException,
    InternalServerErrorException,
    ServiceUnavailableException
)

__all__ = [
    # Text processing
    "sanitize_text",
    "extract_snippet",
    "detect_language",
    "calculate_text_quality",
    "extract_keywords",
    "truncate_text",
    "normalize_url",
    # Validators
    "validate_query",
    "validate_url",
    "validate_engines",
    "validate_language_code",
    "validate_css_selector",
    "validate_custom_selectors",
    "validate_webhook_url",
    "validate_timeout",
    "validate_cache_ttl",
    "validate_max_results",
    # Security
    "generate_api_key",
    "hash_password",
    "verify_password",
    "sanitize_input",
    "is_safe_url",
    "generate_csrf_token",
    "verify_csrf_token",
    "SecurityHeaders",
    # Exceptions
    "UnSearchException",
    "SearXNGException",
    "ScrapingException",
    "CacheException",
    "DatabaseException",
    "BadRequestException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "TooManyRequestsException",
    "InternalServerErrorException",
    "ServiceUnavailableException",
]
