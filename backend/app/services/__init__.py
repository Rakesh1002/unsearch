"""
UnSearch Services Module

Organized into subdirectories:
- core/: Database, cache, search engine integration
- scraping/: Web scraping and content extraction
- search/: Multi-provider search services
- rag/: RAG pipeline for AI agents
- extraction/: Content extraction strategies
- crawling/: Deep crawling and website mapping
- automation/: Browser automation and actions
- infrastructure/: Batch ops, proxies, webhooks
"""

# Core services
from app.services.core.database import DatabaseService, get_database_service
from app.services.core.cache import CacheService, get_cache_service
from app.services.core.searxng import SearXNGService, get_searxng_service

# Scraping services
from app.services.scraping.scraping import ContentScrapingService, get_scraping_service

# Search services
from app.services.search.multi_search import MultiProviderSearchService, SearchOptions, get_multi_search_service

# RAG services
from app.services.rag.rag import RAGService, get_rag_service, VectorStore, EmbeddingService

# Auth and billing (root level)
from app.services.auth_service import AuthService
from app.services.stripe_service import StripeService

__all__ = [
    # Core
    "DatabaseService",
    "get_database_service",
    "CacheService", 
    "get_cache_service",
    "SearXNGService",
    "get_searxng_service",
    # Scraping
    "ContentScrapingService",
    "get_scraping_service",
    # Search
    "MultiProviderSearchService",
    "SearchOptions",
    "get_multi_search_service",
    # RAG
    "RAGService",
    "get_rag_service",
    "VectorStore",
    "EmbeddingService",
    # Auth/Billing
    "AuthService",
    "StripeService",
]
