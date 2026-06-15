"""
Content scraping service.

This module re-exports the canonical implementation from app.services.scraping.scraping.
Tests and legacy imports continue to work while the production runtime uses the
same code path.
"""
from app.services.scraping.scraping import ContentScrapingService, get_scraping_service

__all__ = ["ContentScrapingService", "get_scraping_service"]
