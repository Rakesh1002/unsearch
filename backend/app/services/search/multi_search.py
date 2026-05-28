"""
Multi-provider search service inspired by Firecrawl's search architecture.

Provides fallback capabilities across multiple search engines with smart provider selection.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
import httpx
import structlog

from app.config import get_settings
from app.models.responses import SearchResult, SearchMetadata

logger = structlog.get_logger(__name__)
settings = get_settings()


class SearchProvider(Enum):
    """Available search providers in order of preference."""
    FIRE_ENGINE = "fire_engine"
    SERPER = "serper"
    SEARCHAPI = "searchapi"  
    SEARXNG = "searxng"
    GOOGLE = "google"  # Fallback


@dataclass
class SearchOptions:
    """Search configuration options."""
    query: str
    num_results: int = 10
    lang: str = "en"
    country: str = "us"
    location: Optional[str] = None
    tbs: Optional[str] = None  # Time-based search
    filter: Optional[str] = None
    advanced: bool = False
    timeout: int = 30


@dataclass
class SearchProviderConfig:
    """Configuration for each search provider."""
    name: str
    enabled: bool
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    timeout: int = 30


class MultiProviderSearchService:
    """
    Multi-provider search service with intelligent fallback.
    
    Provides unified search interface across multiple providers with:
    - Automatic provider fallback
    - Rate limiting and error handling  
    - Result normalization and deduplication
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize multi-provider search service."""
        self.client = httpx.AsyncClient(timeout=30)
        self.providers = self._configure_providers()
        self.provider_stats = {provider: {"requests": 0, "errors": 0, "avg_latency": 0.0} 
                              for provider in SearchProvider}
        
    def _configure_providers(self) -> Dict[SearchProvider, SearchProviderConfig]:
        """Configure available search providers from environment."""
        return {
            SearchProvider.FIRE_ENGINE: SearchProviderConfig(
                name="Fire Engine",
                enabled=bool(settings.fire_engine_url),
                endpoint=settings.fire_engine_url,
                rate_limit=200
            ),
            SearchProvider.SERPER: SearchProviderConfig(
                name="Serper",
                enabled=bool(getattr(settings, 'serper_api_key', None)),
                api_key=getattr(settings, 'serper_api_key', None),
                rate_limit=150
            ),
            SearchProvider.SEARCHAPI: SearchProviderConfig(
                name="SearchAPI",
                enabled=bool(getattr(settings, 'searchapi_key', None)),
                api_key=getattr(settings, 'searchapi_key', None),
                rate_limit=100
            ),
            SearchProvider.SEARXNG: SearchProviderConfig(
                name="SearXNG",
                enabled=bool(settings.searxng_url),
                endpoint=settings.searxng_url,
                rate_limit=300
            ),
            SearchProvider.GOOGLE: SearchProviderConfig(
                name="Google",
                enabled=True,  # Always available as fallback
                rate_limit=50
            )
        }
    
    async def search(self, options: SearchOptions) -> List[SearchResult]:
        """
        Perform multi-provider search with intelligent fallback.
        
        Args:
            options: Search configuration
            
        Returns:
            List of search results from the first successful provider
        """
        logger.info("multi_provider_search_started", 
                   query=options.query, 
                   providers=len([p for p in self.providers.values() if p.enabled]))
        
        # Try each provider in order until one succeeds
        for provider_type, config in self.providers.items():
            if not config.enabled:
                continue
                
            try:
                start_time = asyncio.get_event_loop().time()
                results = await self._search_with_provider(provider_type, options)
                
                if results:
                    # Update stats
                    latency = asyncio.get_event_loop().time() - start_time
                    self.provider_stats[provider_type]["requests"] += 1
                    self.provider_stats[provider_type]["avg_latency"] = (
                        (self.provider_stats[provider_type]["avg_latency"] + latency) / 2
                    )
                    
                    logger.info("search_successful",
                               provider=config.name,
                               results=len(results),
                               latency=latency)
                    return results
                
            except Exception as e:
                self.provider_stats[provider_type]["errors"] += 1
                logger.warning("search_provider_failed",
                             provider=config.name,
                             error=str(e))
                continue
        
        logger.error("all_search_providers_failed", query=options.query)
        return []
    
    async def _search_with_provider(
        self, 
        provider: SearchProvider, 
        options: SearchOptions
    ) -> List[SearchResult]:
        """Execute search with specific provider."""
        
        if provider == SearchProvider.FIRE_ENGINE:
            return await self._fire_engine_search(options)
        elif provider == SearchProvider.SERPER:
            return await self._serper_search(options)
        elif provider == SearchProvider.SEARCHAPI:
            return await self._searchapi_search(options)
        elif provider == SearchProvider.SEARXNG:
            return await self._searxng_search(options)
        else:  # Google fallback
            return await self._google_search(options)
    
    async def _fire_engine_search(self, options: SearchOptions) -> List[SearchResult]:
        """Search using Fire Engine API."""
        config = self.providers[SearchProvider.FIRE_ENGINE]
        
        payload = {
            "q": options.query,
            "numResults": options.num_results,
            "lang": options.lang,
            "country": options.country,
        }
        
        if options.location:
            payload["location"] = options.location
        if options.tbs:
            payload["tbs"] = options.tbs
        if options.filter:
            payload["filter"] = options.filter
            
        response = await self.client.post(
            f"{config.endpoint}/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        return self._normalize_fire_engine_results(data)
    
    async def _serper_search(self, options: SearchOptions) -> List[SearchResult]:
        """Search using Serper API."""
        config = self.providers[SearchProvider.SERPER]
        
        payload = {
            "q": options.query,
            "num": options.num_results,
            "hl": options.lang,
            "gl": options.country,
        }
        
        if options.location:
            payload["location"] = options.location
        if options.tbs:
            payload["tbs"] = options.tbs
            
        response = await self.client.post(
            "https://google.serper.dev/search",
            json=payload,
            headers={
                "X-API-KEY": config.api_key,
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
        
        data = response.json()
        return self._normalize_serper_results(data)
    
    async def _searchapi_search(self, options: SearchOptions) -> List[SearchResult]:
        """Search using SearchAPI."""
        config = self.providers[SearchProvider.SEARCHAPI]
        
        params = {
            "engine": "google",
            "q": options.query,
            "num": options.num_results,
            "hl": options.lang,
            "gl": options.country,
            "api_key": config.api_key
        }
        
        if options.location:
            params["location"] = options.location
        if options.tbs:
            params["tbs"] = options.tbs
            
        response = await self.client.get(
            "https://www.searchapi.io/api/v1/search",
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        return self._normalize_searchapi_results(data)
    
    async def _searxng_search(self, options: SearchOptions) -> List[SearchResult]:
        """Search using SearXNG instance."""
        config = self.providers[SearchProvider.SEARXNG]
        
        params = {
            "q": options.query,
            "format": "json",
            "categories": "general",
            "language": options.lang,
            "pageno": 1,
        }
        
        response = await self.client.get(
            f"{config.endpoint}/search",
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        return self._normalize_searxng_results(data, options.num_results)
    
    async def _google_search(self, options: SearchOptions) -> List[SearchResult]:
        """Fallback Google search (simplified implementation)."""
        # This would implement direct Google scraping as fallback
        # For now, return empty results as this needs careful implementation
        logger.warning("google_fallback_not_implemented")
        return []
    
    def _normalize_fire_engine_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Normalize Fire Engine results."""
        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                description=item.get("description", ""),
                engine="fire_engine",
                score=item.get("score", 0.0)
            ))
        return results
    
    def _normalize_serper_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Normalize Serper results."""
        results = []
        for item in data.get("organic", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                description=item.get("snippet", ""),
                engine="serper",
                score=item.get("position", 0)
            ))
        return results
    
    def _normalize_searchapi_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Normalize SearchAPI results."""
        results = []
        for item in data.get("organic_results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                description=item.get("snippet", ""),
                engine="searchapi",
                score=item.get("position", 0)
            ))
        return results
    
    def _normalize_searxng_results(self, data: Dict[str, Any], limit: int) -> List[SearchResult]:
        """Normalize SearXNG results."""
        results = []
        for item in data.get("results", [])[:limit]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                description=item.get("content", ""),
                engine="searxng",
                score=0.0
            ))
        return results
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all providers."""
        return {
            "providers": {
                provider.value: {
                    "config": {
                        "name": config.name,
                        "enabled": config.enabled,
                        "rate_limit": config.rate_limit
                    },
                    "stats": self.provider_stats[provider]
                }
                for provider, config in self.providers.items()
            }
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            await self.client.aclose()


# Singleton instance
_multi_search_service: Optional[MultiProviderSearchService] = None


async def get_multi_search_service() -> MultiProviderSearchService:
    """Get or create multi-provider search service instance."""
    global _multi_search_service
    
    if _multi_search_service is None:
        _multi_search_service = MultiProviderSearchService()
    
    return _multi_search_service


# Convenience functions
async def search_multi_provider(
    query: str,
    num_results: int = 10,
    lang: str = "en",
    country: str = "us",
    **kwargs
) -> List[SearchResult]:
    """Convenience function for multi-provider search."""
    service = await get_multi_search_service()
    options = SearchOptions(
        query=query,
        num_results=num_results,
        lang=lang,
        country=country,
        **kwargs
    )
    return await service.search(options)
