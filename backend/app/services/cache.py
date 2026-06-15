"""
Redis caching service.

This module re-exports the canonical implementation from app.services.core.cache.
Tests and legacy imports continue to work while the production runtime uses the
same code path.
"""
from app.services.core.cache import CacheService, get_cache_service

__all__ = ["CacheService", "get_cache_service"]
