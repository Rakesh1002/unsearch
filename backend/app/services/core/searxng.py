"""
SearXNG integration service for search operations.
"""
import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode, urljoin
import httpx
from httpx import AsyncClient, HTTPError, TimeoutException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.models.responses import SearchResult, EngineInfo, ServiceHealth
from app.utils.text_processing import sanitize_text, extract_snippet
from app.services.core.relevance import get_relevance_filter, RelevanceFilter, QueryAnalysis
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()


class SearXNGService:
    """Service for interacting with SearXNG instance."""
    
    def __init__(self):
        self.base_url = str(settings.searxng_url).rstrip('/')
        self.timeout = settings.searxng_timeout
        self.max_retries = settings.searxng_max_retries
        self._client: Optional[AsyncClient] = None
        self._session_cookies: Optional[Dict[str, str]] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self):
        """Initialize HTTP client with connection pooling."""
        if not self._client:
            self._client = AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30
                ),
                headers={
                    "User-Agent": settings.scraping_user_agent,
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )
            # Get initial session cookies
            await self._get_session()
            
    async def close(self):
        """Close HTTP client connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
            
    async def _get_session(self):
        """Get SearXNG session cookies for proper operation."""
        try:
            response = await self._client.get(self.base_url)
            self._session_cookies = dict(response.cookies)
            logger.info("searxng_session_initialized", cookies_count=len(self._session_cookies))
        except Exception as e:
            logger.warning("searxng_session_init_failed", error=str(e))
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((HTTPError, TimeoutException))
    )
    async def search(
        self, 
        query: str, 
        engines: List[str], 
        language: str = "en",
        safe_search: int = 1,
        time_range: Optional[str] = None,
        categories: Optional[List[str]] = None,
        pageno: int = 1,
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform search using SearXNG.
        
        Args:
            query: Search query
            engines: List of search engines to use
            language: Language code (e.g., 'en', 'de', 'fr')
            safe_search: Safe search level (0=off, 1=moderate, 2=strict)
            time_range: Time range filter (e.g., 'day', 'week', 'month', 'year')
            categories: Search categories (e.g., ['general', 'images', 'news'])
            pageno: Page number for pagination
            
        Returns:
            List of SearchResult objects
        """
        if not self._client:
            await self.initialize()
            
        # Build search parameters
        params = {
            "q": query,
            "format": "json",
            "language": language,
            "safesearch": safe_search,
            "pageno": pageno,
        }
        
        # Add engines
        if engines:
            params["engines"] = ",".join(engines)
            
        # Add time range
        if time_range and time_range in ["day", "week", "month", "year"]:
            params["time_range"] = time_range
            
        # Add categories
        if categories:
            params["categories"] = ",".join(categories)
            
        # Merge additional parameters
        params.update(kwargs)
        
        search_url = urljoin(self.base_url, "/search")
        
        try:
            logger.info(
                "searxng_search_start",
                query=query,
                engines=engines,
                language=language,
                params=params
            )
            
            response = await self._client.get(
                search_url,
                params=params,
                cookies=self._session_cookies
            )
            response.raise_for_status()
            
            data = response.json()
            results = await self._parse_results(data, query)
            
            logger.info(
                "searxng_search_completed",
                query=query,
                results_count=len(results),
                response_time_ms=int(response.elapsed.total_seconds() * 1000)
            )
            
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "searxng_search_http_error",
                query=query,
                status_code=e.response.status_code,
                error=str(e)
            )
            raise
            
        except Exception as e:
            logger.error(
                "searxng_search_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
            
    async def _parse_results(self, data: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse SearXNG response into SearchResult objects."""
        results = []
        seen_urls = set()
        
        for idx, item in enumerate(data.get("results", [])):
            url = item.get("url", "")
            
            # Skip duplicate URLs
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Extract and sanitize fields
            title = sanitize_text(item.get("title", ""))
            content = item.get("content", "")
            
            # Generate snippet if content is too long
            if len(content) > 300:
                snippet = extract_snippet(content, query, max_length=250)
            else:
                snippet = sanitize_text(content)
                
            # Determine which engine returned this result
            engine = item.get("engine", "unknown")
            if isinstance(engine, list):
                engine = engine[0] if engine else "unknown"
                
            result = SearchResult(
                rank=idx + 1,
                title=title or "Untitled",
                url=url,
                snippet=snippet,
                engine=engine,
                score=item.get("score"),
                cached=False
            )
            
            results.append(result)
            
        return results
    
    async def search_with_relevance(
        self,
        query: str,
        engines: List[str],
        max_results: int = 10,
        language: str = "en",
        safe_search: int = 1,
        time_range: Optional[str] = None,
        categories: Optional[List[str]] = None,
        pageno: int = 1,
        enable_filtering: bool = True,
        min_relevance_score: float = 0.15,
        **kwargs
    ) -> Tuple[List[SearchResult], Optional[QueryAnalysis]]:
        """
        Perform search with relevance filtering and ranking.
        
        This is the recommended search method for production use.
        It fetches extra results, filters irrelevant ones, and re-ranks by relevance.
        
        Args:
            query: Search query
            engines: List of search engines to use
            max_results: Maximum results to return (after filtering)
            language: Language code
            safe_search: Safe search level (0=off, 1=moderate, 2=strict)
            time_range: Time range filter
            categories: Search categories
            pageno: Page number
            enable_filtering: Whether to enable relevance filtering
            min_relevance_score: Minimum relevance score threshold
            
        Returns:
            Tuple of (filtered results, query analysis)
        """
        # Fetch more results than needed to account for filtering
        fetch_count = max_results * 2 if enable_filtering else max_results
        
        # Get raw results from SearXNG
        raw_results = await self.search(
            query=query,
            engines=engines,
            language=language,
            safe_search=safe_search,
            time_range=time_range,
            categories=categories,
            pageno=pageno,
            **kwargs
        )
        
        if not enable_filtering or not raw_results:
            return raw_results[:max_results], None
        
        # Apply relevance filtering
        relevance_filter = get_relevance_filter()
        relevance_filter.min_relevance_score = min_relevance_score
        
        # Analyze query once
        query_analysis = relevance_filter.analyze_query(query)
        
        # Convert SearchResult objects to dicts for filtering
        # Note: r.url may be HttpUrl object, convert to string
        results_dicts = [
            {
                'url': str(r.url),
                'title': r.title,
                'snippet': r.snippet,
                'engine': r.engine,
                'score': r.score,
                'rank': r.rank
            }
            for r in raw_results
        ]
        
        # Filter and rank
        filtered_dicts = relevance_filter.filter_and_rank(
            query=query,
            results=results_dicts,
            max_results=max_results,
            query_analysis=query_analysis
        )
        
        # Convert back to SearchResult objects with new ranks
        filtered_results = []
        for idx, rd in enumerate(filtered_dicts):
            result = SearchResult(
                rank=idx + 1,  # New rank based on relevance
                title=rd['title'],
                url=rd['url'],
                snippet=rd['snippet'],
                engine=rd.get('engine', 'unknown'),
                score=rd.get('_relevance_score'),  # Use relevance score
                cached=False
            )
            filtered_results.append(result)
        
        logger.info(
            "searxng_search_with_relevance",
            query=query,
            intent=query_analysis.intent.value,
            raw_count=len(raw_results),
            filtered_count=len(filtered_results)
        )
        
        return filtered_results, query_analysis
        
    async def get_available_engines(self) -> Dict[str, EngineInfo]:
        """Get list of available search engines with their capabilities."""
        if not self._client:
            await self.initialize()
            
        try:
            # Get engine stats from SearXNG
            config_url = urljoin(self.base_url, "/config")
            response = await self._client.get(config_url)
            response.raise_for_status()
            
            config_data = response.json()
            engines_data = config_data.get("engines", [])
            
            engines = {}
            for engine in engines_data:
                name = engine.get("name", "")
                if not name:
                    continue
                    
                engine_info = EngineInfo(
                    name=name,
                    enabled=not engine.get("disabled", False),
                    categories=engine.get("categories", ["general"]),
                    supported_languages=engine.get("supported_languages", ["*"]),
                    safe_search_support=engine.get("safesearch", False),
                    time_range_support=engine.get("time_range_support", False),
                    paging_support=engine.get("paging", False)
                )
                
                engines[name] = engine_info
                
            logger.info(
                "searxng_engines_fetched",
                total_engines=len(engines),
                enabled_engines=sum(1 for e in engines.values() if e.enabled)
            )
            
            return engines
            
        except Exception as e:
            logger.error("searxng_engines_fetch_error", error=str(e))
            # Return default engines if fetch fails
            return self._get_default_engines()
            
    def _get_default_engines(self) -> Dict[str, EngineInfo]:
        """Get default engine configuration."""
        default_engines = {
            "google": EngineInfo(
                name="google",
                enabled=True,
                categories=["general", "images", "news"],
                supported_languages=["*"],
                safe_search_support=True,
                time_range_support=True,
                paging_support=True
            ),
            "bing": EngineInfo(
                name="bing",
                enabled=True,
                categories=["general", "images", "news"],
                supported_languages=["*"],
                safe_search_support=True,
                time_range_support=True,
                paging_support=True
            ),
            "duckduckgo": EngineInfo(
                name="duckduckgo",
                enabled=True,
                categories=["general", "images"],
                supported_languages=["*"],
                safe_search_support=True,
                time_range_support=True,
                paging_support=True
            ),
            "startpage": EngineInfo(
                name="startpage",
                enabled=True,
                categories=["general"],
                supported_languages=["*"],
                safe_search_support=True,
                time_range_support=False,
                paging_support=True
            ),
            "qwant": EngineInfo(
                name="qwant",
                enabled=True,
                categories=["general", "images", "news"],
                supported_languages=["*"],
                safe_search_support=True,
                time_range_support=False,
                paging_support=True
            )
        }
        
        return default_engines
        
    async def health_check(self) -> ServiceHealth:
        """Perform comprehensive health check on SearXNG service."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self._client:
                await self.initialize()
                
            # Check basic connectivity
            response = await self._client.get(
                self.base_url,
                timeout=httpx.Timeout(5.0)
            )
            response.raise_for_status()
            
            # Check search functionality with minimal query
            test_results = await self.search(
                query="test",
                engines=["duckduckgo"],
                language="en"
            )
            
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return ServiceHealth(
                status="healthy",
                latency_ms=latency_ms,
                last_check=asyncio.get_event_loop().time(),
                details={
                    "version": response.headers.get("X-SearXNG-Version", "unknown"),
                    "test_results_count": len(test_results)
                }
            )
            
        except Exception as e:
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return ServiceHealth(
                status="unhealthy",
                latency_ms=latency_ms,
                last_check=asyncio.get_event_loop().time(),
                details={
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            
    def generate_cache_key(self, query: str, engines: List[str], **params) -> str:
        """Generate deterministic cache key for search query."""
        # Sort engines and params for consistency
        sorted_engines = sorted(engines)
        sorted_params = sorted(params.items())
        
        key_data = {
            "query": query.lower().strip(),
            "engines": sorted_engines,
            "params": sorted_params
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()


# Singleton instance
_searxng_service: Optional[SearXNGService] = None


async def get_searxng_service() -> SearXNGService:
    """Get or create SearXNG service instance."""
    global _searxng_service
    
    if _searxng_service is None:
        _searxng_service = SearXNGService()
        await _searxng_service.initialize()
        
    return _searxng_service
