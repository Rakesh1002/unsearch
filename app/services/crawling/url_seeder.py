"""
Advanced URL seeding and discovery system inspired by crawl4ai.

This module provides sophisticated URL discovery capabilities:
- Sitemap parsing and URL extraction  
- Common Crawl data integration
- Pattern-based URL filtering and scoring
- Concurrent URL validation and scoring
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Any, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from dataclasses import dataclass, field
import time

import httpx
import structlog
from bs4 import BeautifulSoup

from app.utils.text_processing import clean_tokens

logger = structlog.get_logger(__name__)


@dataclass
class SeedingConfig:
    """Configuration for URL discovery and seeding."""
    
    source: str = "sitemap"  # "sitemap", "cc", "sitemap+cc", "crawl"
    pattern: Optional[str] = None  # URL pattern to match
    query: Optional[str] = None  # Query for relevance scoring
    score_threshold: float = 0.0  # Minimum score threshold
    max_urls: int = 1000  # Maximum URLs to discover
    concurrent_requests: int = 10  # Concurrent validation requests
    timeout: float = 10.0  # Request timeout in seconds
    
    # Sitemap-specific settings
    sitemap_urls: List[str] = field(default_factory=list)
    follow_sitemap_index: bool = True
    
    # Common Crawl settings
    cc_index: Optional[str] = None  # Common Crawl index to use
    cc_limit: int = 100  # Limit for CC results
    
    # Crawl-based discovery settings
    crawl_depth: int = 2  # Maximum crawl depth
    crawl_max_pages: int = 50  # Maximum pages to crawl
    
    # Filtering settings
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)


@dataclass
class DiscoveredURL:
    """Represents a discovered URL with metadata."""
    
    url: str
    source: str  # "sitemap", "cc", "crawl"
    score: float = 0.0
    last_modified: Optional[str] = None
    change_freq: Optional[str] = None
    priority: Optional[float] = None
    
    # Additional metadata
    title: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[str] = None
    status_code: Optional[int] = None
    discovery_time: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "source": self.source, 
            "score": self.score,
            "last_modified": self.last_modified,
            "change_freq": self.change_freq,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "content_type": self.content_type,
            "status_code": self.status_code,
            "discovery_time": self.discovery_time
        }


class URLSeeder:
    """
    Advanced URL seeding system for discovering URLs from multiple sources.
    
    This class provides comprehensive URL discovery capabilities including
    sitemap parsing, Common Crawl integration, and pattern-based filtering.
    """
    
    def __init__(self, config: SeedingConfig):
        """Initialize URL seeder with configuration."""
        self.config = config
        self.discovered_urls: Set[str] = set()
        self.scored_urls: List[DiscoveredURL] = []
        
        # HTTP client for requests
        self.client: Optional[httpx.AsyncClient] = None
        
        # Compiled regex patterns for performance
        self.include_regexes = [re.compile(pattern) for pattern in config.include_patterns]
        self.exclude_regexes = [re.compile(pattern) for pattern in config.exclude_patterns]
        
        # Query tokens for relevance scoring
        self.query_tokens = set(clean_tokens(config.query.lower().split())) if config.query else set()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def initialize(self):
        """Initialize HTTP client."""
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; URLSeeder/1.0; +https://example.com/bot)"
                }
            )
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def discover(self, base_url: str) -> List[DiscoveredURL]:
        """
        Discover URLs from configured sources.
        
        Args:
            base_url: Base URL to start discovery from
            
        Returns:
            List of discovered and scored URLs
        """
        logger.info(f"Starting URL discovery for {base_url} with source: {self.config.source}")
        
        if not self.client:
            await self.initialize()
        
        discovered_urls = []
        
        # Source-based discovery
        if "sitemap" in self.config.source:
            sitemap_urls = await self._discover_from_sitemaps(base_url)
            discovered_urls.extend(sitemap_urls)
            logger.info(f"Discovered {len(sitemap_urls)} URLs from sitemaps")
        
        if "cc" in self.config.source:
            cc_urls = await self._discover_from_common_crawl(base_url)
            discovered_urls.extend(cc_urls)
            logger.info(f"Discovered {len(cc_urls)} URLs from Common Crawl")
        
        if self.config.source == "crawl":
            crawl_urls = await self._discover_from_crawling(base_url)
            discovered_urls.extend(crawl_urls)
            logger.info(f"Discovered {len(crawl_urls)} URLs from crawling")
        
        # Remove duplicates and apply filtering
        unique_urls = self._deduplicate_and_filter(discovered_urls)
        logger.info(f"After deduplication and filtering: {len(unique_urls)} URLs")
        
        # Score and rank URLs
        scored_urls = await self._score_and_rank_urls(unique_urls)
        
        # Apply score threshold
        final_urls = [
            url for url in scored_urls 
            if url.score >= self.config.score_threshold
        ]
        
        # Limit results
        final_urls = final_urls[:self.config.max_urls]
        
        logger.info(f"Final URL set: {len(final_urls)} URLs (threshold: {self.config.score_threshold})")
        
        return final_urls
    
    async def _discover_from_sitemaps(self, base_url: str) -> List[DiscoveredURL]:
        """Discover URLs from XML sitemaps."""
        discovered_urls = []
        
        # Determine sitemap URLs
        sitemap_urls = self.config.sitemap_urls.copy()
        if not sitemap_urls:
            # Try common sitemap locations
            common_locations = [
                "/sitemap.xml",
                "/sitemap_index.xml",
                "/sitemaps.xml",
                "/robots.txt"  # Parse sitemap references
            ]
            
            for location in common_locations:
                sitemap_url = urljoin(base_url, location)
                if location.endswith("robots.txt"):
                    # Extract sitemap URLs from robots.txt
                    robots_sitemaps = await self._extract_sitemaps_from_robots(sitemap_url)
                    sitemap_urls.extend(robots_sitemaps)
                else:
                    sitemap_urls.append(sitemap_url)
        
        # Process each sitemap URL
        for sitemap_url in sitemap_urls:
            try:
                urls_from_sitemap = await self._parse_sitemap(sitemap_url)
                discovered_urls.extend(urls_from_sitemap)
                
                if len(discovered_urls) >= self.config.max_urls:
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to parse sitemap {sitemap_url}: {str(e)}")
                continue
        
        return discovered_urls
    
    async def _parse_sitemap(self, sitemap_url: str) -> List[DiscoveredURL]:
        """Parse a single XML sitemap."""
        try:
            response = await self.client.get(sitemap_url)
            response.raise_for_status()
            
            content = response.text
            root = ET.fromstring(content)
            
            # Handle namespace
            namespace = ""
            if root.tag.startswith("{"):
                namespace = root.tag.split("}")[0] + "}"
            
            discovered_urls = []
            
            # Check if this is a sitemap index
            sitemap_elements = root.findall(f"{namespace}sitemap")
            if sitemap_elements and self.config.follow_sitemap_index:
                # This is a sitemap index - recursively parse child sitemaps
                for sitemap_elem in sitemap_elements:
                    loc_elem = sitemap_elem.find(f"{namespace}loc")
                    if loc_elem is not None:
                        child_sitemap_url = loc_elem.text.strip()
                        child_urls = await self._parse_sitemap(child_sitemap_url)
                        discovered_urls.extend(child_urls)
            else:
                # This is a regular sitemap - extract URLs
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
                            change_freq=changefreq_elem.text.strip() if changefreq_elem is not None else None,
                            priority=float(priority_elem.text.strip()) if priority_elem is not None else None
                        )
                        
                        discovered_urls.append(discovered_url)
            
            return discovered_urls
            
        except Exception as e:
            logger.error(f"Error parsing sitemap {sitemap_url}: {str(e)}")
            return []
    
    async def _extract_sitemaps_from_robots(self, robots_url: str) -> List[str]:
        """Extract sitemap URLs from robots.txt."""
        try:
            response = await self.client.get(robots_url)
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
            logger.warning(f"Error parsing robots.txt {robots_url}: {str(e)}")
            return []
    
    async def _discover_from_common_crawl(self, base_url: str) -> List[DiscoveredURL]:
        """Discover URLs from Common Crawl data."""
        # This is a simplified implementation
        # In production, you would integrate with Common Crawl's APIs
        logger.info("Common Crawl integration not fully implemented - using mock data")
        
        # Mock implementation
        await asyncio.sleep(0.1)  # Simulate API call
        
        domain = urlparse(base_url).netloc
        mock_urls = [
            DiscoveredURL(f"https://{domain}/page1", "cc", score=0.8),
            DiscoveredURL(f"https://{domain}/page2", "cc", score=0.6),
            DiscoveredURL(f"https://{domain}/blog/", "cc", score=0.7),
        ]
        
        return mock_urls
    
    async def _discover_from_crawling(self, base_url: str) -> List[DiscoveredURL]:
        """Discover URLs by crawling the website."""
        discovered_urls = []
        crawled_urls = set()
        urls_to_crawl = [base_url]
        current_depth = 0
        
        while urls_to_crawl and current_depth < self.config.crawl_depth:
            current_level_urls = urls_to_crawl.copy()
            urls_to_crawl.clear()
            
            # Process current level
            for url in current_level_urls:
                if url in crawled_urls or len(crawled_urls) >= self.config.crawl_max_pages:
                    continue
                
                try:
                    response = await self.client.get(url)
                    if response.status_code != 200:
                        continue
                    
                    crawled_urls.add(url)
                    
                    # Add current URL to discovered
                    discovered_urls.append(DiscoveredURL(
                        url=url,
                        source="crawl",
                        status_code=response.status_code,
                        content_type=response.headers.get("content-type", "")
                    ))
                    
                    # Extract links for next level
                    if current_depth < self.config.crawl_depth - 1:
                        soup = BeautifulSoup(response.text, 'lxml')
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            absolute_url = urljoin(url, href)
                            
                            # Only follow same-domain links
                            if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                                if absolute_url not in crawled_urls:
                                    urls_to_crawl.append(absolute_url)
                
                except Exception as e:
                    logger.warning(f"Error crawling {url}: {str(e)}")
                    continue
            
            current_depth += 1
        
        return discovered_urls
    
    def _deduplicate_and_filter(self, discovered_urls: List[DiscoveredURL]) -> List[DiscoveredURL]:
        """Remove duplicates and apply filtering rules."""
        unique_urls = {}
        
        for discovered_url in discovered_urls:
            url = discovered_url.url
            
            # Skip if already seen
            if url in unique_urls:
                continue
            
            # Apply pattern filtering
            if not self._passes_pattern_filters(url):
                continue
            
            # Apply domain filtering  
            if not self._passes_domain_filters(url):
                continue
            
            unique_urls[url] = discovered_url
        
        return list(unique_urls.values())
    
    def _passes_pattern_filters(self, url: str) -> bool:
        """Check if URL passes pattern-based filters."""
        # Check include patterns
        if self.include_regexes:
            if not any(regex.search(url) for regex in self.include_regexes):
                return False
        
        # Check exclude patterns
        if self.exclude_regexes:
            if any(regex.search(url) for regex in self.exclude_regexes):
                return False
        
        # Check explicit pattern from config
        if self.config.pattern:
            pattern_regex = re.compile(self.config.pattern)
            if not pattern_regex.search(url):
                return False
        
        return True
    
    def _passes_domain_filters(self, url: str) -> bool:
        """Check if URL passes domain-based filters."""
        domain = urlparse(url).netloc.lower()
        
        # Check allowed domains
        if self.config.allowed_domains:
            if not any(allowed in domain for allowed in self.config.allowed_domains):
                return False
        
        # Check blocked domains
        if self.config.blocked_domains:
            if any(blocked in domain for blocked in self.config.blocked_domains):
                return False
        
        return True
    
    async def _score_and_rank_urls(self, urls: List[DiscoveredURL]) -> List[DiscoveredURL]:
        """Score and rank URLs based on various factors."""
        if not urls:
            return []
        
        # Score URLs concurrently for performance
        semaphore = asyncio.Semaphore(self.config.concurrent_requests)
        
        async def score_url(discovered_url: DiscoveredURL) -> DiscoveredURL:
            async with semaphore:
                try:
                    score = await self._calculate_url_score(discovered_url)
                    discovered_url.score = score
                    return discovered_url
                except Exception as e:
                    logger.warning(f"Error scoring URL {discovered_url.url}: {str(e)}")
                    discovered_url.score = 0.0
                    return discovered_url
        
        # Score all URLs
        scored_urls = await asyncio.gather(*[score_url(url) for url in urls])
        
        # Sort by score (descending)
        scored_urls.sort(key=lambda x: x.score, reverse=True)
        
        return scored_urls
    
    async def _calculate_url_score(self, discovered_url: DiscoveredURL) -> float:
        """Calculate relevance score for a URL."""
        score = 0.0
        url = discovered_url.url
        
        # Base score from source
        source_scores = {
            "sitemap": 0.8,
            "cc": 0.6,
            "crawl": 0.5
        }
        score += source_scores.get(discovered_url.source, 0.5)
        
        # Sitemap-specific scoring
        if discovered_url.source == "sitemap":
            if discovered_url.priority:
                score += discovered_url.priority * 0.2
            
            if discovered_url.change_freq:
                freq_scores = {
                    "always": 0.1, "hourly": 0.09, "daily": 0.08,
                    "weekly": 0.06, "monthly": 0.04, "yearly": 0.02, "never": 0.0
                }
                score += freq_scores.get(discovered_url.change_freq.lower(), 0.0)
        
        # URL structure scoring
        score += self._score_url_structure(url)
        
        # Query relevance scoring
        if self.query_tokens:
            score += self._score_query_relevance(url)
        
        # Content preview scoring (if enabled)
        if self.config.source == "crawl":
            content_score = await self._score_content_preview(discovered_url)
            score += content_score
        
        return min(1.0, score)  # Cap at 1.0
    
    def _score_url_structure(self, url: str) -> float:
        """Score URL based on structure indicators."""
        score = 0.0
        path = urlparse(url).path.lower()
        
        # Content indicators
        content_indicators = [
            "blog", "article", "post", "news", "guide", "tutorial",
            "documentation", "docs", "help", "support", "about"
        ]
        
        for indicator in content_indicators:
            if indicator in path:
                score += 0.1
                break
        
        # Depth penalty (deeper URLs less likely to be important)
        depth = len([p for p in path.split('/') if p])
        if depth <= 2:
            score += 0.1
        elif depth > 4:
            score -= 0.1
        
        # File extension analysis
        if path.endswith(('.html', '.htm', '.php')):
            score += 0.05
        elif path.endswith(('.pdf', '.doc', '.docx')):
            score += 0.03
        
        return score
    
    def _score_query_relevance(self, url: str) -> float:
        """Score URL relevance to the query."""
        if not self.query_tokens:
            return 0.0
        
        # Extract words from URL
        url_words = set(re.findall(r'[a-zA-Z]+', url.lower()))
        
        # Calculate overlap with query
        overlap = len(self.query_tokens.intersection(url_words))
        max_overlap = len(self.query_tokens)
        
        if max_overlap > 0:
            return (overlap / max_overlap) * 0.3
        
        return 0.0
    
    async def _score_content_preview(self, discovered_url: DiscoveredURL) -> float:
        """Score URL based on content preview."""
        # This would make a HEAD request to get basic content info
        # For now, return a simple score based on status code
        if discovered_url.status_code == 200:
            return 0.1
        elif discovered_url.status_code in [301, 302, 307, 308]:
            return 0.05
        else:
            return 0.0


# Factory function
async def discover_urls(
    base_url: str,
    source: str = "sitemap",
    pattern: Optional[str] = None,
    query: Optional[str] = None,
    max_urls: int = 100
) -> List[DiscoveredURL]:
    """
    Convenience function to discover URLs.
    
    Args:
        base_url: Base URL to start discovery
        source: Discovery source ("sitemap", "cc", "crawl")
        pattern: URL pattern to match
        query: Query for relevance scoring
        max_urls: Maximum URLs to return
        
    Returns:
        List of discovered URLs
    """
    config = SeedingConfig(
        source=source,
        pattern=pattern,
        query=query,
        max_urls=max_urls
    )
    
    async with URLSeeder(config) as seeder:
        return await seeder.discover(base_url)


# Utility functions
def filter_urls_by_patterns(
    urls: List[str],
    include_patterns: List[str] = None,
    exclude_patterns: List[str] = None
) -> List[str]:
    """Filter URLs by regex patterns."""
    include_regexes = [re.compile(p) for p in (include_patterns or [])]
    exclude_regexes = [re.compile(p) for p in (exclude_patterns or [])]
    
    filtered = []
    for url in urls:
        # Check include patterns
        if include_regexes and not any(r.search(url) for r in include_regexes):
            continue
        
        # Check exclude patterns
        if exclude_regexes and any(r.search(url) for r in exclude_regexes):
            continue
        
        filtered.append(url)
    
    return filtered
