"""
Service layer for the SearchScrape API.
"""
from app.services.searxng import SearXNGService, get_searxng_service
from app.services.scraping import ContentScrapingService, get_scraping_service
from app.services.cache import CacheService, get_cache_service
from app.services.database import DatabaseService, get_database_service

__all__ = [
    # Service classes
    "SearXNGService",
    "ContentScrapingService",
    "CacheService",
    "DatabaseService",
    
    # Service getters
    "get_searxng_service",
    "get_scraping_service",
    "get_cache_service",
    "get_database_service"
]
