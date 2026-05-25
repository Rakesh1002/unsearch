"""
Advanced deep crawling system with multiple strategies and sophisticated filtering.

This module provides comprehensive deep crawling capabilities:
- Multi-strategy crawling (BFS, DFS, Best-First)
- Advanced URL filtering chain
- Composite URL scoring system
- Content relevance filtering
- SEO-based filtering and prioritization
"""

import re
import asyncio
import time
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Optional, Any, Tuple, Pattern, Union
from urllib.parse import urljoin, urlparse
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum

import structlog
from bs4 import BeautifulSoup

from app.utils.text_processing import clean_tokens, calculate_text_quality

logger = structlog.get_logger(__name__)


class CrawlOrder(str, Enum):
    """Crawl order strategies."""
    BFS = "bfs"  # Breadth-first search
    DFS = "dfs"  # Depth-first search  
    BEST_FIRST = "best_first"  # Best-first based on scoring


@dataclass
class FilterStats:
    """Statistics for URL filtering operations."""
    total_urls: int = 0
    passed_urls: int = 0
    rejected_urls: int = 0
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        return self.passed_urls / self.total_urls if self.total_urls > 0 else 0.0


@dataclass 
class CrawlProgress:
    """Progress tracking for deep crawling operations."""
    urls_discovered: int = 0
    urls_processed: int = 0
    urls_successful: int = 0
    urls_failed: int = 0
    current_depth: int = 0
    start_time: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.urls_successful / self.urls_processed if self.urls_processed > 0 else 0.0
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time."""
        return time.time() - self.start_time


# URL Filtering System
class URLFilter(ABC):
    """Base class for URL filtering."""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.stats = FilterStats()
    
    @abstractmethod
    def apply(self, url: str, **kwargs) -> bool:
        """Apply filter to URL and return True if URL should be kept."""
        pass
    
    def _update_stats(self, passed: bool):
        """Update filter statistics."""
        self.stats.total_urls += 1
        if passed:
            self.stats.passed_urls += 1
        else:
            self.stats.rejected_urls += 1


class DomainFilter(URLFilter):
    """Filter URLs based on allowed/blocked domains."""
    
    def __init__(self, 
                 allowed_domains: List[str] = None,
                 blocked_domains: List[str] = None,
                 same_domain_only: bool = False,
                 base_domain: str = None):
        super().__init__()
        self.allowed_domains = set(allowed_domains or [])
        self.blocked_domains = set(blocked_domains or [])
        self.same_domain_only = same_domain_only
        self.base_domain = base_domain
    
    def apply(self, url: str, **kwargs) -> bool:
        """Apply domain filtering."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Same domain only check
            if self.same_domain_only and self.base_domain:
                if domain != self.base_domain.lower():
                    self._update_stats(False)
                    return False
            
            # Blocked domains check
            if self.blocked_domains:
                for blocked in self.blocked_domains:
                    if blocked.lower() in domain:
                        self._update_stats(False)
                        return False
            
            # Allowed domains check
            if self.allowed_domains:
                allowed = any(allowed.lower() in domain for allowed in self.allowed_domains)
                self._update_stats(allowed)
                return allowed
            
            self._update_stats(True)
            return True
            
        except Exception:
            self._update_stats(False)
            return False


class URLPatternFilter(URLFilter):
    """Filter URLs based on regex patterns."""
    
    def __init__(self, 
                 include_patterns: List[str] = None,
                 exclude_patterns: List[str] = None):
        super().__init__()
        self.include_patterns = [re.compile(p) for p in (include_patterns or [])]
        self.exclude_patterns = [re.compile(p) for p in (exclude_patterns or [])]
    
    def apply(self, url: str, **kwargs) -> bool:
        """Apply pattern filtering."""
        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if pattern.search(url):
                self._update_stats(False)
                return False
        
        # Check include patterns
        if self.include_patterns:
            for pattern in self.include_patterns:
                if pattern.search(url):
                    self._update_stats(True)
                    return True
            self._update_stats(False)
            return False
        
        self._update_stats(True)
        return True


class ContentTypeFilter(URLFilter):
    """Filter URLs based on expected content type."""
    
    def __init__(self, 
                 allowed_types: List[str] = None,
                 blocked_types: List[str] = None):
        super().__init__()
        self.allowed_types = set(allowed_types or ['text/html', 'application/xhtml+xml'])
        self.blocked_types = set(blocked_types or [])
        
        # Common file extensions to block for web content
        self.blocked_extensions = {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.mp4', '.avi', '.mov', '.wmv', '.flv',
            '.mp3', '.wav', '.flac', '.aac',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'
        }
    
    def apply(self, url: str, **kwargs) -> bool:
        """Apply content type filtering."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check file extensions
        for ext in self.blocked_extensions:
            if path.endswith(ext):
                self._update_stats(False)
                return False
        
        # If content type is provided in kwargs, check it
        content_type = kwargs.get('content_type', '').lower()
        if content_type:
            if self.blocked_types and any(blocked in content_type for blocked in self.blocked_types):
                self._update_stats(False)
                return False
            
            if self.allowed_types and not any(allowed in content_type for allowed in self.allowed_types):
                self._update_stats(False)
                return False
        
        self._update_stats(True)
        return True


class SEOFilter(URLFilter):
    """Filter URLs based on SEO and quality indicators."""
    
    def __init__(self, max_depth: int = 5, max_params: int = 10):
        super().__init__()
        self.max_depth = max_depth
        self.max_params = max_params
        
        # SEO-unfriendly patterns
        self.bad_patterns = [
            r'/cgi-bin/', r'/admin/', r'/private/', r'/tmp/',
            r'\?.*sessionid', r'\?.*sid=', r'\?.*PHPSESSID',
            r'\.php\?.*&.*&.*&', r'javascript:', r'mailto:',
        ]
        self.bad_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.bad_patterns]
    
    def apply(self, url: str, **kwargs) -> bool:
        """Apply SEO filtering."""
        parsed = urlparse(url)
        
        # Check URL depth
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) > self.max_depth:
            self._update_stats(False)
            return False
        
        # Check number of parameters
        if parsed.query:
            params = parsed.query.split('&')
            if len(params) > self.max_params:
                self._update_stats(False)
                return False
        
        # Check for bad patterns
        for regex in self.bad_regexes:
            if regex.search(url):
                self._update_stats(False)
                return False
        
        self._update_stats(True)
        return True


class ContentRelevanceFilter(URLFilter):
    """Filter URLs based on content relevance to a query."""
    
    def __init__(self, query: str = None, min_score: float = 0.3):
        super().__init__()
        self.query_tokens = set(clean_tokens(query.lower().split())) if query else set()
        self.min_score = min_score
    
    def apply(self, url: str, **kwargs) -> bool:
        """Apply content relevance filtering."""
        if not self.query_tokens:
            self._update_stats(True)
            return True
        
        # Score URL based on query relevance
        url_lower = url.lower()
        url_tokens = set(re.findall(r'[a-zA-Z]+', url_lower))
        
        if not url_tokens:
            self._update_stats(False)
            return False
        
        # Calculate overlap score
        overlap = len(self.query_tokens.intersection(url_tokens))
        score = overlap / len(self.query_tokens) if self.query_tokens else 0.0
        
        passed = score >= self.min_score
        self._update_stats(passed)
        return passed


class FilterChain:
    """Chain multiple URL filters together."""
    
    def __init__(self, filters: List[URLFilter] = None):
        self.filters = filters or []
        self.stats = FilterStats()
    
    def add_filter(self, filter_obj: URLFilter):
        """Add a filter to the chain."""
        self.filters.append(filter_obj)
    
    def apply(self, url: str, **kwargs) -> bool:
        """Apply all filters in sequence."""
        self.stats.total_urls += 1
        
        for filter_obj in self.filters:
            if not filter_obj.apply(url, **kwargs):
                self.stats.rejected_urls += 1
                return False
        
        self.stats.passed_urls += 1
        return True


# URL Scoring System
class URLScorer(ABC):
    """Base class for URL scoring."""
    
    def __init__(self, weight: float = 1.0):
        self.weight = weight
    
    @abstractmethod
    def calculate_score(self, url: str, **kwargs) -> float:
        """Calculate score for URL (0.0 to 1.0)."""
        pass
    
    def score(self, url: str, **kwargs) -> float:
        """Calculate weighted score."""
        return self.calculate_score(url, **kwargs) * self.weight


class KeywordRelevanceScorer(URLScorer):
    """Score URLs based on keyword relevance."""
    
    def __init__(self, keywords: List[str], weight: float = 1.0):
        super().__init__(weight)
        self.keywords = [kw.lower() for kw in keywords]
    
    def calculate_score(self, url: str, **kwargs) -> float:
        """Calculate keyword relevance score."""
        if not self.keywords:
            return 0.5
        
        url_lower = url.lower()
        matches = sum(1 for keyword in self.keywords if keyword in url_lower)
        return min(1.0, matches / len(self.keywords))


class PathDepthScorer(URLScorer):
    """Score URLs based on path depth (shorter paths = higher score)."""
    
    def __init__(self, max_depth: int = 5, weight: float = 1.0):
        super().__init__(weight)
        self.max_depth = max_depth
    
    def calculate_score(self, url: str, **kwargs) -> float:
        """Calculate depth score."""
        parsed = urlparse(url)
        depth = len([p for p in parsed.path.split('/') if p])
        return max(0.0, 1.0 - (depth / self.max_depth))


class DomainAuthorityScorer(URLScorer):
    """Score URLs based on domain authority."""
    
    def __init__(self, weight: float = 1.0):
        super().__init__(weight)
        # Predefined domain authority scores
        self.domain_scores = {
            # High authority domains
            'wikipedia.org': 1.0,
            'github.com': 0.9,
            'stackoverflow.com': 0.9,
            'mozilla.org': 0.8,
            'w3.org': 0.8,
            # Medium authority domains
            'medium.com': 0.7,
            'dev.to': 0.6,
            'reddit.com': 0.6,
        }
    
    def calculate_score(self, url: str, **kwargs) -> float:
        """Calculate domain authority score."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check for exact matches
        if domain in self.domain_scores:
            return self.domain_scores[domain]
        
        # Check for subdomain matches
        for scored_domain, score in self.domain_scores.items():
            if domain.endswith('.' + scored_domain):
                return score * 0.8  # Subdomains get 80% of parent score
        
        return 0.5  # Default score for unknown domains


class FreshnessScorer(URLScorer):
    """Score URLs based on estimated freshness."""
    
    def __init__(self, weight: float = 1.0):
        super().__init__(weight)
        self.current_year = time.gmtime().tm_year
    
    def calculate_score(self, url: str, **kwargs) -> float:
        """Calculate freshness score based on URL indicators."""
        # Look for year patterns in URL
        years = re.findall(r'\b(20[0-9]{2})\b', url)
        if years:
            latest_year = max(int(year) for year in years)
            years_old = self.current_year - latest_year
            return max(0.0, 1.0 - (years_old / 10.0))  # Decay over 10 years
        
        return 0.5  # Default score if no year found


class CompositeScorer(URLScorer):
    """Combine multiple scorers with weighted average."""
    
    def __init__(self, scorers: List[URLScorer], normalize: bool = True):
        # Calculate total weight
        total_weight = sum(scorer.weight for scorer in scorers)
        super().__init__(total_weight if not normalize else 1.0)
        self.scorers = scorers
        self.normalize = normalize
    
    def calculate_score(self, url: str, **kwargs) -> float:
        """Calculate composite score."""
        if not self.scorers:
            return 0.5
        
        total_score = sum(scorer.score(url, **kwargs) for scorer in self.scorers)
        
        if self.normalize:
            total_weight = sum(scorer.weight for scorer in self.scorers)
            return total_score / total_weight if total_weight > 0 else 0.0
        else:
            return total_score


# Deep Crawling Strategies
class DeepCrawlStrategy(ABC):
    """Base class for deep crawling strategies."""
    
    def __init__(self, 
                 max_depth: int = 3,
                 max_pages: int = 100,
                 filter_chain: FilterChain = None,
                 url_scorer: URLScorer = None):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.filter_chain = filter_chain or FilterChain()
        self.url_scorer = url_scorer
        self.progress = CrawlProgress()
        
        # Crawling state
        self.discovered_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.url_to_depth: Dict[str, int] = {}
    
    @abstractmethod
    async def crawl(self, 
                   start_urls: List[str],
                   fetch_callback,
                   extract_links_callback) -> List[Dict[str, Any]]:
        """Execute the crawling strategy."""
        pass
    
    def _extract_links_from_html(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML content."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            links = []
            
            for anchor in soup.find_all('a', href=True):
                href = anchor['href'].strip()
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, href)
                    links.append(absolute_url)
            
            return links
            
        except Exception as e:
            logger.warning(f"Error extracting links from {base_url}: {str(e)}")
            return []


class BFSDeepCrawlStrategy(DeepCrawlStrategy):
    """Breadth-first search deep crawling strategy."""
    
    async def crawl(self, 
                   start_urls: List[str],
                   fetch_callback,
                   extract_links_callback) -> List[Dict[str, Any]]:
        """Execute BFS crawling."""
        results = []
        queue = deque()
        
        # Initialize with start URLs
        for url in start_urls:
            queue.append((url, 0))  # (url, depth)
            self.discovered_urls.add(url)
            self.url_to_depth[url] = 0
        
        self.progress.urls_discovered = len(queue)
        
        while queue and len(self.processed_urls) < self.max_pages:
            current_url, depth = queue.popleft()
            
            if current_url in self.processed_urls or depth > self.max_depth:
                continue
            
            self.processed_urls.add(current_url)
            self.progress.urls_processed += 1
            self.progress.current_depth = depth
            
            try:
                # Fetch page content
                page_result = await fetch_callback(current_url)
                if page_result:
                    results.append({
                        'url': current_url,
                        'depth': depth,
                        'content': page_result,
                        'timestamp': time.time()
                    })
                    self.progress.urls_successful += 1
                    
                    # Extract links for next level
                    if depth < self.max_depth:
                        extracted_links = await extract_links_callback(
                            page_result.get('html', ''), current_url
                        )
                        
                        for link in extracted_links:
                            if (link not in self.discovered_urls and 
                                self.filter_chain.apply(link)):
                                
                                queue.append((link, depth + 1))
                                self.discovered_urls.add(link)
                                self.url_to_depth[link] = depth + 1
                                self.progress.urls_discovered += 1
                
            except Exception as e:
                logger.error(f"Error processing {current_url}: {str(e)}")
                self.progress.urls_failed += 1
        
        logger.info(
            f"BFS crawl completed: {len(results)} pages processed, "
            f"success rate: {self.progress.success_rate:.2%}"
        )
        
        return results


class DFSDeepCrawlStrategy(DeepCrawlStrategy):
    """Depth-first search deep crawling strategy."""
    
    async def crawl(self, 
                   start_urls: List[str],
                   fetch_callback,
                   extract_links_callback) -> List[Dict[str, Any]]:
        """Execute DFS crawling."""
        results = []
        
        for start_url in start_urls:
            if len(self.processed_urls) >= self.max_pages:
                break
                
            await self._dfs_recursive(
                start_url, 0, results, fetch_callback, extract_links_callback
            )
        
        logger.info(
            f"DFS crawl completed: {len(results)} pages processed, "
            f"success rate: {self.progress.success_rate:.2%}"
        )
        
        return results
    
    async def _dfs_recursive(self, 
                            url: str, 
                            depth: int,
                            results: List[Dict[str, Any]],
                            fetch_callback,
                            extract_links_callback):
        """Recursive DFS implementation."""
        if (url in self.processed_urls or 
            depth > self.max_depth or 
            len(self.processed_urls) >= self.max_pages):
            return
        
        self.processed_urls.add(url)
        self.progress.urls_processed += 1
        self.progress.current_depth = max(self.progress.current_depth, depth)
        
        try:
            # Fetch page content
            page_result = await fetch_callback(url)
            if page_result:
                results.append({
                    'url': url,
                    'depth': depth,
                    'content': page_result,
                    'timestamp': time.time()
                })
                self.progress.urls_successful += 1
                
                # Extract and recurse into links
                if depth < self.max_depth:
                    extracted_links = await extract_links_callback(
                        page_result.get('html', ''), url
                    )
                    
                    for link in extracted_links:
                        if (link not in self.discovered_urls and 
                            self.filter_chain.apply(link)):
                            
                            self.discovered_urls.add(link)
                            self.progress.urls_discovered += 1
                            
                            await self._dfs_recursive(
                                link, depth + 1, results, 
                                fetch_callback, extract_links_callback
                            )
            
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            self.progress.urls_failed += 1


class BestFirstCrawlStrategy(DeepCrawlStrategy):
    """Best-first search using URL scoring."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.url_scorer:
            # Default composite scorer
            self.url_scorer = CompositeScorer([
                KeywordRelevanceScorer(['content', 'article', 'blog'], weight=0.3),
                PathDepthScorer(weight=0.2),
                DomainAuthorityScorer(weight=0.3),
                FreshnessScorer(weight=0.2)
            ])
    
    async def crawl(self, 
                   start_urls: List[str],
                   fetch_callback,
                   extract_links_callback) -> List[Dict[str, Any]]:
        """Execute best-first crawling with priority queue."""
        import heapq
        
        results = []
        # Priority queue: (negative_score, url, depth)
        priority_queue = []
        
        # Initialize with start URLs
        for url in start_urls:
            score = self.url_scorer.score(url)
            heapq.heappush(priority_queue, (-score, url, 0))
            self.discovered_urls.add(url)
            self.url_to_depth[url] = 0
        
        self.progress.urls_discovered = len(priority_queue)
        
        while priority_queue and len(self.processed_urls) < self.max_pages:
            negative_score, current_url, depth = heapq.heappop(priority_queue)
            
            if current_url in self.processed_urls or depth > self.max_depth:
                continue
            
            self.processed_urls.add(current_url)
            self.progress.urls_processed += 1
            self.progress.current_depth = depth
            
            try:
                # Fetch page content
                page_result = await fetch_callback(current_url)
                if page_result:
                    results.append({
                        'url': current_url,
                        'depth': depth,
                        'score': -negative_score,
                        'content': page_result,
                        'timestamp': time.time()
                    })
                    self.progress.urls_successful += 1
                    
                    # Extract and score links
                    if depth < self.max_depth:
                        extracted_links = await extract_links_callback(
                            page_result.get('html', ''), current_url
                        )
                        
                        for link in extracted_links:
                            if (link not in self.discovered_urls and 
                                self.filter_chain.apply(link)):
                                
                                link_score = self.url_scorer.score(link)
                                heapq.heappush(priority_queue, (-link_score, link, depth + 1))
                                self.discovered_urls.add(link)
                                self.url_to_depth[link] = depth + 1
                                self.progress.urls_discovered += 1
                
            except Exception as e:
                logger.error(f"Error processing {current_url}: {str(e)}")
                self.progress.urls_failed += 1
        
        # Sort results by score for best-first
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(
            f"Best-first crawl completed: {len(results)} pages processed, "
            f"success rate: {self.progress.success_rate:.2%}"
        )
        
        return results


# Factory functions
def create_deep_crawl_strategy(
    strategy_type: str,
    config: Dict[str, Any] = None
) -> DeepCrawlStrategy:
    """Create a deep crawling strategy."""
    config = config or {}
    
    # Create filter chain
    filter_chain = FilterChain()
    
    if config.get('domain_filter'):
        filter_chain.add_filter(DomainFilter(**config['domain_filter']))
    
    if config.get('pattern_filter'):
        filter_chain.add_filter(URLPatternFilter(**config['pattern_filter']))
    
    if config.get('content_type_filter'):
        filter_chain.add_filter(ContentTypeFilter(**config['content_type_filter']))
    
    if config.get('seo_filter'):
        filter_chain.add_filter(SEOFilter(**config['seo_filter']))
    
    if config.get('relevance_filter'):
        filter_chain.add_filter(ContentRelevanceFilter(**config['relevance_filter']))
    
    # Create URL scorer for best-first
    url_scorer = None
    if strategy_type == 'best_first' and config.get('scoring'):
        scorers = []
        scoring_config = config['scoring']
        
        if scoring_config.get('keyword_relevance'):
            scorers.append(KeywordRelevanceScorer(**scoring_config['keyword_relevance']))
        
        if scoring_config.get('path_depth'):
            scorers.append(PathDepthScorer(**scoring_config['path_depth']))
        
        if scoring_config.get('domain_authority'):
            scorers.append(DomainAuthorityScorer(**scoring_config['domain_authority']))
        
        if scoring_config.get('freshness'):
            scorers.append(FreshnessScorer(**scoring_config['freshness']))
        
        if scorers:
            url_scorer = CompositeScorer(scorers)
    
    # Create strategy
    base_config = {
        'max_depth': config.get('max_depth', 3),
        'max_pages': config.get('max_pages', 100),
        'filter_chain': filter_chain,
        'url_scorer': url_scorer
    }
    
    strategies = {
        'bfs': BFSDeepCrawlStrategy,
        'dfs': DFSDeepCrawlStrategy,
        'best_first': BestFirstCrawlStrategy
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_type}. Available: {list(strategies.keys())}")
    
    strategy_class = strategies[strategy_type]
    return strategy_class(**base_config)


# Convenience functions
async def deep_crawl(
    start_urls: List[str],
    strategy: str = 'bfs',
    config: Dict[str, Any] = None,
    fetch_callback = None,
    extract_links_callback = None
) -> List[Dict[str, Any]]:
    """Convenience function for deep crawling."""
    if not fetch_callback or not extract_links_callback:
        raise ValueError("fetch_callback and extract_links_callback are required")
    
    crawler = create_deep_crawl_strategy(strategy, config)
    return await crawler.crawl(start_urls, fetch_callback, extract_links_callback)
