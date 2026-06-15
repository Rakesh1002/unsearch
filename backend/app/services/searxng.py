"""
SearXNG integration service.

This module re-exports the canonical implementation from app.services.core.searxng.
Tests and legacy imports continue to work while the production runtime uses the
same code path.
"""
from app.services.core.searxng import SearXNGService, get_searxng_service

__all__ = ["SearXNGService", "get_searxng_service"]
