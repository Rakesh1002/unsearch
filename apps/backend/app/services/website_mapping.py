"""
Website mapping service for fast URL discovery inspired by Firecrawl.

Provides comprehensive website mapping capabilities:
- Sitemap-based URL discovery
- Search engine-based URL mapping
- Subdomain and path filtering
- External link detection
- Fast URL enumeration
"""

import asyncio
import time
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Set, Union
from urllib.parse import urlparse, urljoin, quote
from dataclasses import dataclass, field
from enum import Enum
import structlog
import httpx

from app.config import get_settings
from app.services.multi_search import get_multi_search_service, SearchOptions
from app.utils.text_processing import sanitize_text

logger = structlog.get_logger(__name__)
settings = get_settings()


class MapStrategy(Enum):
    """Website mapping strategies."""
    SITEMAP_ONLY = "sitemap_only"
    SEARCH_ENGINE = "search_engine"
    COMBINED = "combined"
    CRAWL_BASED = "crawl_based"


@dataclass
class MapOptions:
    """Configuration for website mapping."""
    strategy: MapStrategy = MapStrategy.COMBINED
    limit: int = 1000
    include_subdomains: bool = True
    allow_external_links: bool = False
    ignore_sitemap: bool = False
    filter_by_path: bool = True
    search_query: Optional[str] = None
    timeout: int = 30
    max_depth: int = 3
    concurrent_requests: int = 10
    
    # Sitemap options
    follow_sitemap_index: bool = True
    sitemap_timeout: int = 15
    
    # Search engine options
    search_results_per_page: int = 100
    max_search_pages: int = 10
    
    # Filtering options
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class DiscoveredURL:
    """Represents a discovered URL with metadata."""
    url: str
    source: str  # "sitemap", "search", "crawl", "index"
    title: Optional[str] = None
    description: Optional[str] = None
    last_modified: Optional[str] = None
    change_frequency: Optional[str] = None
    priority: Optional[float] = None
    content_type: Optional[str] = None
    status_code: Optional[int] = None
    discovery_time: float = field(default_factory=time.time)
    parent_url: Optional[str] = None
    depth: int = 0


@dataclass
class WebsiteMapResult:
    """Result of website mapping operation."""
    base_url: str
    discovered_urls: List[DiscoveredURL]
    total_urls: int
    sources_breakdown: Dict[str, int]
    processing_time_ms: int
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebsiteMapper:
    """
    Comprehensive website mapping service.
    
    Discovers URLs from websites using multiple strategies:
    - Sitemap parsing (XML sitemaps, robots.txt)
    - Search engine queries (site: operator)
    - Link crawling and discovery
    - Index-based lookups
    """
    
    def __init__(self):
        """Initialize website mapper."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            headers={
                "User-Agent": settings.scraping_user_agent
            }
        )
        self.discovered_cache: Dict[str, List[DiscoveredURL]] = {}
        self.mapping_stats = {"total_requests": 0, "successful_maps": 0, "urls_discovered": 0}
    
    async def map_website(
        self, 
        url: str, 
        options: Optional[MapOptions] = None
    ) -> WebsiteMapResult:
        """
        Map a website to discover all accessible URLs.
        
        Args:
            url: Base URL to map
            options: Mapping configuration options
            
        Returns:
            WebsiteMapResult with discovered URLs and metadata
        """
        start_time = time.time()
        options = options or MapOptions()
        
        self.mapping_stats["total_requests"] += 1
        
        logger.info("website_mapping_started", 
                   url=url, 
                   strategy=options.strategy.value,
                   limit=options.limit)
        
        try:
            discovered_urls: List[DiscoveredURL] = []
            sources_breakdown = {"sitemap": 0, "search": 0, "crawl": 0, "index": 0}
            
            # Execute mapping strategy
            if options.strategy == MapStrategy.SITEMAP_ONLY:
                sitemap_urls = await self._discover_from_sitemaps(url, options)
                discovered_urls.extend(sitemap_urls)
                sources_breakdown["sitemap"] = len(sitemap_urls)
                
            elif options.strategy == MapStrategy.SEARCH_ENGINE:
                search_urls = await self._discover_from_search_engines(url, options)
                discovered_urls.extend(search_urls)
                sources_breakdown["search"] = len(search_urls)
                
            elif options.strategy == MapStrategy.CRAWL_BASED:
                crawl_urls = await self._discover_from_crawling(url, options)
                discovered_urls.extend(crawl_urls)
                sources_breakdown["crawl"] = len(crawl_urls)
                
            else:  # COMBINED strategy
                # Run multiple discovery methods in parallel
                sitemap_task = self._discover_from_sitemaps(url, options)
                search_task = self._discover_from_search_engines(url, options)
                index_task = self._discover_from_index(url, options)
                
                sitemap_urls, search_urls, index_urls = await asyncio.gather(
                    sitemap_task, search_task, index_task, return_exceptions=True
                )
                
                # Handle results and exceptions
                if isinstance(sitemap_urls, list):
                    discovered_urls.extend(sitemap_urls)
                    sources_breakdown["sitemap"] = len(sitemap_urls)
                
                if isinstance(search_urls, list):
                    discovered_urls.extend(search_urls)
                    sources_breakdown["search"] = len(search_urls)
                
                if isinstance(index_urls, list):
                    discovered_urls.extend(index_urls)
                    sources_breakdown["index"] = len(index_urls)
            
            # Remove duplicates and apply filtering
            unique_urls = await self._deduplicate_and_filter(discovered_urls, url, options)
            
            # Apply limits
            final_urls = unique_urls[:options.limit]
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update stats
            self.mapping_stats["successful_maps"] += 1
            self.mapping_stats["urls_discovered"] += len(final_urls)
            
            # Cache results
            cache_key = f"{url}:{hash(str(options))}"
            self.discovered_cache[cache_key] = final_urls
            
            result = WebsiteMapResult(
                base_url=url,
                discovered_urls=final_urls,
                total_urls=len(final_urls),
                sources_breakdown=sources_breakdown,
                processing_time_ms=processing_time_ms,
                success=True,
                metadata={
                    "strategy_used": options.strategy.value,
                    "original_discovered": len(discovered_urls),
                    "after_deduplication": len(unique_urls),
                    "after_filtering": len(final_urls)
                }
            )
            
            logger.info("website_mapping_completed",
                       url=url,
                       total_urls=len(final_urls),
                       sources=sources_breakdown,
                       processing_time_ms=processing_time_ms)
            
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            logger.error("website_mapping_failed", 
                        url=url, 
                        error=error_msg,
                        processing_time_ms=processing_time_ms)
            
            return WebsiteMapResult(
                base_url=url,
                discovered_urls=[],
                total_urls=0,
                sources_breakdown={},
                processing_time_ms=processing_time_ms,
                success=False,
                error=error_msg
            )
    
    async def _discover_from_sitemaps(
        self, 
        base_url: str, 
        options: MapOptions
    ) -> List[DiscoveredURL]:
        """Discover URLs from XML sitemaps."""
        if options.ignore_sitemap:
            return []
        
        discovered_urls = []
        
        try:
            # Try common sitemap locations
            sitemap_urls = [
                urljoin(base_url, "/sitemap.xml"),
                urljoin(base_url, "/sitemap_index.xml"),
                urljoin(base_url, "/sitemaps.xml"),
                urljoin(base_url, "/sitemap/index.xml"),
                urljoin(base_url, "/wp-sitemap.xml"),  # WordPress
            ]
            
            # Also check robots.txt for sitemap declarations
            robots_sitemaps = await self._extract_sitemaps_from_robots(base_url)
            sitemap_urls.extend(robots_sitemaps)
            
            # Remove duplicates
            sitemap_urls = list(set(sitemap_urls))
            
            # Process sitemaps concurrently
            semaphore = asyncio.Semaphore(options.concurrent_requests)
            
            async def process_sitemap(sitemap_url: str):
                async with semaphore:
                    return await self._parse_single_sitemap(sitemap_url, options)
            
            # Process all sitemaps
            sitemap_results = await asyncio.gather(
                *[process_sitemap(url) for url in sitemap_urls],
                return_exceptions=True
            )
            
            # Collect URLs from successful sitemap parses
            for result in sitemap_results:
                if isinstance(result, list):
                    discovered_urls.extend(result)
                    if len(discovered_urls) >= options.limit * 2:  # Stop if we have enough
                        break
            
            logger.info("sitemap_discovery_completed",
                       base_url=base_url,
                       sitemaps_processed=len(sitemap_urls),
                       urls_discovered=len(discovered_urls))
            
            return discovered_urls[:options.limit]
            
        except Exception as e:
            logger.error("sitemap_discovery_failed", base_url=base_url, error=str(e))
            return []
    
    async def _parse_single_sitemap(
        self, 
        sitemap_url: str, 
        options: MapOptions
    ) -> List[DiscoveredURL]:
        """Parse a single XML sitemap."""
        try:
            response = await self.client.get(sitemap_url, timeout=options.sitemap_timeout)
            if response.status_code != 200:
                return []
            
            content = response.text
            root = ET.fromstring(content)
            
            # Handle namespaces
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0] + "}"
            
            discovered_urls = []
            
            # Check if this is a sitemap index
            sitemap_elements = root.findall(f"{namespace}sitemap")
            if sitemap_elements and options.follow_sitemap_index:
                # Recursively process child sitemaps
                for sitemap_elem in sitemap_elements:
                    loc_elem = sitemap_elem.find(f"{namespace}loc")
                    if loc_elem is not None:
                        child_sitemap_url = loc_elem.text.strip()
                        child_urls = await self._parse_single_sitemap(child_sitemap_url, options)
                        discovered_urls.extend(child_urls)
            
            else:
                # Parse regular sitemap URLs
                url_elements = root.findall(f"{namespace}url")
                for url_elem in url_elements:
                    loc_elem = url_elem.find(f"{namespace}loc")
                    if loc_elem is not None:
                        url = loc_elem.text.strip()
                        
                        # Extract additional metadata
                        lastmod_elem = url_elem.find(f"{namespace}lastmod")
                        changefreq_elem = url_elem.find(f"{namespace}changefreq")
                        priority_elem = url_elem.find(f"{namespace}priority")
                        
                        discovered_url = DiscoveredURL(
                            url=url,
                            source="sitemap",
                            last_modified=lastmod_elem.text.strip() if lastmod_elem is not None else None,
                            change_frequency=changefreq_elem.text.strip() if changefreq_elem is not None else None,
                            priority=float(priority_elem.text.strip()) if priority_elem is not None else None
                        )
                        
                        discovered_urls.append(discovered_url)
            
            return discovered_urls
            
        except Exception as e:
            logger.warning("sitemap_parsing_failed", sitemap_url=sitemap_url, error=str(e))
            return []
    
    async def _extract_sitemaps_from_robots(self, base_url: str) -> List[str]:
        """Extract sitemap URLs from robots.txt."""
        try:
            robots_url = urljoin(base_url, "/robots.txt")
            response = await self.client.get(robots_url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            sitemaps = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line[8:].strip()
                    sitemaps.append(sitemap_url)
            
            return sitemaps
            
        except Exception as e:
            logger.warning("robots_txt_parsing_failed", base_url=base_url, error=str(e))
            return []
    
    async def _discover_from_search_engines(
        self, 
        base_url: str, 
        options: MapOptions
    ) -> List[DiscoveredURL]:
        """Discover URLs using search engines."""
        try:
            # Prepare search query
            parsed_url = urlparse(base_url)
            domain = parsed_url.netloc
            
            if options.search_query and options.allow_external_links:
                search_query = f"{options.search_query} {domain}"
            elif options.search_query:
                search_query = f"{options.search_query} site:{domain}"
            else:
                search_query = f"site:{domain}"
            
            logger.info("search_engine_discovery_started", 
                       base_url=base_url, 
                       query=search_query)
            
            # Use multi-search service
            search_service = await get_multi_search_service()
            
            discovered_urls = []
            total_results_needed = min(options.limit, 1000)  # Cap at 1000
            
            # Calculate pages needed
            results_per_page = options.search_results_per_page
            pages_needed = min(
                options.max_search_pages,
                (total_results_needed + results_per_page - 1) // results_per_page
            )
            
            # Perform searches (for now, single search - can be extended for pagination)
            search_options = SearchOptions(
                query=search_query,
                num_results=total_results_needed,
                lang="en",
                country="us"
            )
            
            search_results = await search_service.search(search_options)
            
            # Convert search results to discovered URLs
            for result in search_results:
                discovered_url = DiscoveredURL(
                    url=result.url,
                    source="search",
                    title=result.title,
                    description=result.description
                )
                discovered_urls.append(discovered_url)
            
            logger.info("search_engine_discovery_completed",
                       base_url=base_url,
                       urls_discovered=len(discovered_urls))
            
            return discovered_urls
            
        except Exception as e:
            logger.error("search_engine_discovery_failed", base_url=base_url, error=str(e))
            return []
    
    async def _discover_from_index(
        self, 
        base_url: str, 
        options: MapOptions
    ) -> List[DiscoveredURL]:
        """Discover URLs from internal index/cache."""
        try:
            # Check if we have cached results
            cache_key = f"index:{base_url}"
            if cache_key in self.discovered_cache:
                cached_urls = self.discovered_cache[cache_key]
                logger.info("index_discovery_cache_hit", 
                           base_url=base_url, 
                           cached_urls=len(cached_urls))
                return cached_urls
            
            # In a real implementation, this would query an internal URL index
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error("index_discovery_failed", base_url=base_url, error=str(e))
            return []
    
    async def _discover_from_crawling(
        self, 
        base_url: str, 
        options: MapOptions
    ) -> List[DiscoveredURL]:
        """Discover URLs through crawling."""
        try:
            discovered_urls = []
            crawled_urls = set()
            urls_to_crawl = [(base_url, 0)]  # (url, depth)
            
            semaphore = asyncio.Semaphore(options.concurrent_requests)
            
            while urls_to_crawl and len(discovered_urls) < options.limit:
                current_batch = []
                
                # Prepare batch of URLs to crawl
                for _ in range(min(options.concurrent_requests, len(urls_to_crawl))):
                    if urls_to_crawl:
                        url, depth = urls_to_crawl.pop(0)
                        if url not in crawled_urls and depth <= options.max_depth:
                            current_batch.append((url, depth))
                            crawled_urls.add(url)
                
                if not current_batch:
                    break
                
                # Crawl batch
                async def crawl_url(url_depth_tuple):
                    async with semaphore:
                        return await self._crawl_single_url(url_depth_tuple, base_url, options)
                
                batch_results = await asyncio.gather(
                    *[crawl_url(item) for item in current_batch],
                    return_exceptions=True
                )
                
                # Process results
                for result in batch_results:
                    if isinstance(result, dict):
                        discovered_url = result["discovered_url"]
                        new_links = result["links"]
                        
                        discovered_urls.append(discovered_url)
                        
                        # Add new links to crawl queue
                        for link_url in new_links:
                            if link_url not in crawled_urls:
                                urls_to_crawl.append((link_url, discovered_url.depth + 1))
            
            logger.info("crawl_discovery_completed",
                       base_url=base_url,
                       urls_crawled=len(crawled_urls),
                       urls_discovered=len(discovered_urls))
            
            return discovered_urls[:options.limit]
            
        except Exception as e:
            logger.error("crawl_discovery_failed", base_url=base_url, error=str(e))
            return []
    
    async def _crawl_single_url(
        self, 
        url_depth_tuple: tuple, 
        base_url: str, 
        options: MapOptions
    ) -> Dict[str, Any]:
        """Crawl a single URL and extract links."""
        url, depth = url_depth_tuple
        
        try:
            response = await self.client.get(url, timeout=options.timeout)
            
            discovered_url = DiscoveredURL(
                url=url,
                source="crawl",
                status_code=response.status_code,
                content_type=response.headers.get("content-type", ""),
                depth=depth
            )
            
            links = []
            
            if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
                # Extract links from HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Extract title
                title_elem = soup.find('title')
                if title_elem:
                    discovered_url.title = title_elem.get_text().strip()
                
                # Extract meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    discovered_url.description = meta_desc.get('content', '').strip()
                
                # Extract links
                for link_elem in soup.find_all('a', href=True):
                    href = link_elem['href']
                    absolute_url = urljoin(url, href)
                    
                    # Filter links based on options
                    if self._should_include_url(absolute_url, base_url, options):
                        links.append(absolute_url)
            
            return {
                "discovered_url": discovered_url,
                "links": links
            }
            
        except Exception as e:
            logger.warning("url_crawling_failed", url=url, error=str(e))
            return {
                "discovered_url": DiscoveredURL(url=url, source="crawl", depth=depth),
                "links": []
            }
    
    def _should_include_url(self, url: str, base_url: str, options: MapOptions) -> bool:
        """Check if URL should be included based on options."""
        try:
            url_parsed = urlparse(url)
            base_parsed = urlparse(base_url)
            
            # Skip non-HTTP(S) URLs
            if url_parsed.scheme not in ['http', 'https']:
                return False
            
            # Check domain restrictions
            if not options.allow_external_links:
                if options.include_subdomains:
                    # Allow subdomains
                    if not url_parsed.netloc.endswith(base_parsed.netloc):
                        return False
                else:
                    # Exact domain match only
                    if url_parsed.netloc != base_parsed.netloc:
                        return False
            
            # Check path filtering
            if options.filter_by_path and base_parsed.path and base_parsed.path != "/":
                if not url_parsed.path.startswith(base_parsed.path):
                    return False
            
            # Check include patterns
            if options.include_patterns:
                if not any(re.search(pattern, url) for pattern in options.include_patterns):
                    return False
            
            # Check exclude patterns
            if options.exclude_patterns:
                if any(re.search(pattern, url) for pattern in options.exclude_patterns):
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def _deduplicate_and_filter(
        self, 
        discovered_urls: List[DiscoveredURL], 
        base_url: str, 
        options: MapOptions
    ) -> List[DiscoveredURL]:
        """Remove duplicates and apply final filtering."""
        # Deduplicate by URL
        unique_urls = {}
        for discovered_url in discovered_urls:
            url = discovered_url.url
            
            # Normalize URL for comparison
            normalized_url = self._normalize_url(url)
            
            if normalized_url not in unique_urls:
                # Apply final filtering
                if self._should_include_url(url, base_url, options):
                    unique_urls[normalized_url] = discovered_url
            else:
                # Merge metadata from multiple sources
                existing = unique_urls[normalized_url]
                if not existing.title and discovered_url.title:
                    existing.title = discovered_url.title
                if not existing.description and discovered_url.description:
                    existing.description = discovered_url.description
                if not existing.last_modified and discovered_url.last_modified:
                    existing.last_modified = discovered_url.last_modified
        
        # Sort by source priority and other factors
        sorted_urls = sorted(
            unique_urls.values(),
            key=lambda x: (
                self._get_source_priority(x.source),
                -(x.priority or 0),
                x.url
            )
        )
        
        return sorted_urls
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        try:
            parsed = urlparse(url)
            
            # Remove fragment
            normalized = parsed._replace(fragment="").geturl()
            
            # Remove trailing slash for non-root paths
            if normalized.endswith("/") and parsed.path != "/":
                normalized = normalized[:-1]
            
            # Remove www. for comparison
            normalized = normalized.replace("://www.", "://")
            
            return normalized.lower()
            
        except Exception:
            return url.lower()
    
    def _get_source_priority(self, source: str) -> int:
        """Get priority for source (lower number = higher priority)."""
        priorities = {
            "sitemap": 1,
            "index": 2,
            "search": 3,
            "crawl": 4
        }
        return priorities.get(source, 5)
    
    async def get_mapping_stats(self) -> Dict[str, Any]:
        """Get mapping service statistics."""
        return {
            "mapping_stats": self.mapping_stats,
            "cache_size": len(self.discovered_cache),
            "success_rate": (
                self.mapping_stats["successful_maps"] / 
                max(1, self.mapping_stats["total_requests"])
            ) if self.mapping_stats["total_requests"] > 0 else 0,
            "avg_urls_per_map": (
                self.mapping_stats["urls_discovered"] /
                max(1, self.mapping_stats["successful_maps"])
            ) if self.mapping_stats["successful_maps"] > 0 else 0
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            await self.client.aclose()


# Singleton service
_website_mapper: Optional[WebsiteMapper] = None


async def get_website_mapper() -> WebsiteMapper:
    """Get or create website mapper service instance."""
    global _website_mapper
    
    if _website_mapper is None:
        _website_mapper = WebsiteMapper()
    
    return _website_mapper


# Convenience function
async def map_website_urls(
    url: str,
    strategy: str = "combined",
    limit: int = 1000,
    include_subdomains: bool = True,
    search_query: Optional[str] = None
) -> WebsiteMapResult:
    """
    Convenience function for website mapping.
    
    Args:
        url: Base URL to map
        strategy: Mapping strategy (sitemap_only, search_engine, combined, crawl_based)
        limit: Maximum URLs to return
        include_subdomains: Whether to include subdomains
        search_query: Optional search query for filtering
        
    Returns:
        WebsiteMapResult with discovered URLs
    """
    mapper = await get_website_mapper()
    
    options = MapOptions(
        strategy=MapStrategy(strategy),
        limit=limit,
        include_subdomains=include_subdomains,
        search_query=search_query
    )
    
    return await mapper.map_website(url, options)
