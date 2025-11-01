"""
Advanced link preview system for extracting head content and metadata from links.

This module provides sophisticated link processing capabilities:
- Parallel link head extraction
- Link filtering and scoring
- Metadata extraction (title, description, images)
- BM25 relevance scoring
- Link quality assessment
- Performance optimization with caching
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from datetime import datetime

import httpx
import structlog
from bs4 import BeautifulSoup

from app.utils.text_processing import clean_tokens, calculate_text_quality

logger = structlog.get_logger(__name__)


@dataclass
class LinkMetadata:
    """Metadata extracted from link head content."""
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    site_name: Optional[str] = None
    type: Optional[str] = None
    
    # OpenGraph metadata
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    og_url: Optional[str] = None
    og_site_name: Optional[str] = None
    og_type: Optional[str] = None
    
    # Twitter Card metadata
    twitter_card: Optional[str] = None
    twitter_title: Optional[str] = None
    twitter_description: Optional[str] = None
    twitter_image: Optional[str] = None
    twitter_site: Optional[str] = None
    twitter_creator: Optional[str] = None
    
    # Technical metadata
    canonical_url: Optional[str] = None
    language: Optional[str] = None
    charset: Optional[str] = None
    viewport: Optional[str] = None
    
    # Content analysis
    content_preview: Optional[str] = None
    content_length: int = 0
    keywords: List[str] = field(default_factory=list)
    
    # Performance metrics
    response_time: float = 0.0
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    
    def get_best_title(self) -> Optional[str]:
        """Get the best available title."""
        return self.og_title or self.twitter_title or self.title
    
    def get_best_description(self) -> Optional[str]:
        """Get the best available description."""
        return self.og_description or self.twitter_description or self.description
    
    def get_best_image(self) -> Optional[str]:
        """Get the best available image."""
        return self.og_image or self.twitter_image or self.image


@dataclass
class LinkPreviewResult:
    """Result of link preview extraction."""
    url: str
    success: bool
    metadata: Optional[LinkMetadata] = None
    error: Optional[str] = None
    relevance_score: float = 0.0
    quality_score: float = 0.0
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'url': self.url,
            'success': self.success,
            'relevance_score': self.relevance_score,
            'quality_score': self.quality_score,
            'processing_time': self.processing_time
        }
        
        if self.metadata:
            result['metadata'] = {
                'title': self.metadata.get_best_title(),
                'description': self.metadata.get_best_description(),
                'image': self.metadata.get_best_image(),
                'site_name': self.metadata.og_site_name or self.metadata.site_name,
                'canonical_url': self.metadata.canonical_url,
                'language': self.metadata.language,
                'content_preview': self.metadata.content_preview,
                'keywords': self.metadata.keywords,
                'status_code': self.metadata.status_code,
                'content_type': self.metadata.content_type
            }
        
        if self.error:
            result['error'] = self.error
        
        return result


@dataclass
class LinkPreviewConfig:
    """Configuration for link preview extraction."""
    
    # Filtering options
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    
    # Processing options
    concurrent_requests: int = 10
    timeout: float = 10.0
    max_content_length: int = 1024 * 1024  # 1MB
    follow_redirects: bool = True
    max_redirects: int = 5
    
    # Content options
    extract_content_preview: bool = True
    preview_length: int = 500
    extract_keywords: bool = True
    max_keywords: int = 20
    
    # Quality scoring
    enable_quality_scoring: bool = True
    enable_relevance_scoring: bool = True
    query: Optional[str] = None
    
    # Performance options
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour


class LinkPreview:
    """
    Advanced link preview system for extracting metadata and content from links.
    
    Provides intelligent link processing with filtering, scoring, and optimization.
    """
    
    def __init__(self, config: LinkPreviewConfig = None):
        """
        Initialize link preview system.
        
        Args:
            config: Configuration for link preview processing
        """
        self.config = config or LinkPreviewConfig()
        self.client: Optional[httpx.AsyncClient] = None
        
        # Compile regex patterns for performance
        self.include_patterns = [re.compile(p) for p in self.config.include_patterns]
        self.exclude_patterns = [re.compile(p) for p in self.config.exclude_patterns]
        
        # Query tokens for relevance scoring
        self.query_tokens = set(clean_tokens(self.config.query.lower().split())) if self.config.query else set()
        
        # Cache for results
        self._cache: Dict[str, LinkPreviewResult] = {}
    
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
                limits=httpx.Limits(
                    max_connections=self.config.concurrent_requests * 2,
                    max_keepalive_connections=self.config.concurrent_requests
                ),
                follow_redirects=self.config.follow_redirects,
                max_redirects=self.config.max_redirects,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; LinkPreview/1.0; +https://example.com/bot)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive'
                }
            )
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    def _should_process_link(self, url: str) -> bool:
        """Check if link should be processed based on filters."""
        # Check include patterns
        if self.include_patterns:
            if not any(pattern.search(url) for pattern in self.include_patterns):
                return False
        
        # Check exclude patterns
        if self.exclude_patterns:
            if any(pattern.search(url) for pattern in self.exclude_patterns):
                return False
        
        # Check domain filters
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check blocked domains
        if self.config.blocked_domains:
            if any(blocked in domain for blocked in self.config.blocked_domains):
                return False
        
        # Check allowed domains
        if self.config.allowed_domains:
            if not any(allowed in domain for allowed in self.config.allowed_domains):
                return False
        
        return True
    
    async def extract_link_previews(self, links: List[str]) -> List[LinkPreviewResult]:
        """
        Extract previews for multiple links.
        
        Args:
            links: List of URLs to process
            
        Returns:
            List of LinkPreviewResult objects
        """
        if not self.client:
            await self.initialize()
        
        # Filter links
        filtered_links = [link for link in links if self._should_process_link(link)]
        
        logger.info(f"Processing {len(filtered_links)} links (filtered from {len(links)})")
        
        if not filtered_links:
            return []
        
        # Process links with concurrency control
        semaphore = asyncio.Semaphore(self.config.concurrent_requests)
        
        async def process_link(url: str) -> LinkPreviewResult:
            async with semaphore:
                return await self._extract_single_preview(url)
        
        # Execute all requests
        results = await asyncio.gather(
            *[process_link(url) for url in filtered_links],
            return_exceptions=True
        )
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = LinkPreviewResult(
                    url=filtered_links[i],
                    success=False,
                    error=str(result)
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        # Sort by quality and relevance scores
        processed_results.sort(
            key=lambda x: (x.relevance_score, x.quality_score), 
            reverse=True
        )
        
        logger.info(f"Completed link preview extraction: {len(processed_results)} results")
        
        return processed_results
    
    async def _extract_single_preview(self, url: str) -> LinkPreviewResult:
        """Extract preview for a single link."""
        import time
        start_time = time.time()
        
        # Check cache
        if self.config.enable_caching and url in self._cache:
            cached_result = self._cache[url]
            cached_result.processing_time = time.time() - start_time
            return cached_result
        
        try:
            # Make HEAD request first to check content type and size
            head_response = await self.client.head(url)
            content_type = head_response.headers.get('content-type', '').lower()
            content_length = int(head_response.headers.get('content-length', 0))
            
            # Skip if not HTML-like content
            if not ('text/html' in content_type or 'application/xhtml' in content_type):
                result = LinkPreviewResult(
                    url=url,
                    success=False,
                    error=f"Unsupported content type: {content_type}",
                    processing_time=time.time() - start_time
                )
                return result
            
            # Skip if content too large
            if content_length > self.config.max_content_length:
                result = LinkPreviewResult(
                    url=url,
                    success=False,
                    error=f"Content too large: {content_length} bytes",
                    processing_time=time.time() - start_time
                )
                return result
            
            # Make GET request for content
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Extract metadata from HTML
            metadata = self._extract_metadata_from_html(response.text, url)
            metadata.status_code = response.status_code
            metadata.content_type = content_type
            metadata.response_time = time.time() - start_time
            
            # Calculate scores
            relevance_score = self._calculate_relevance_score(metadata) if self.config.enable_relevance_scoring else 0.0
            quality_score = self._calculate_quality_score(metadata) if self.config.enable_quality_scoring else 0.0
            
            result = LinkPreviewResult(
                url=url,
                success=True,
                metadata=metadata,
                relevance_score=relevance_score,
                quality_score=quality_score,
                processing_time=time.time() - start_time
            )
            
            # Cache result
            if self.config.enable_caching:
                self._cache[url] = result
            
            return result
            
        except httpx.HTTPError as e:
            result = LinkPreviewResult(
                url=url,
                success=False,
                error=f"HTTP error: {str(e)}",
                processing_time=time.time() - start_time
            )
            return result
        
        except Exception as e:
            result = LinkPreviewResult(
                url=url,
                success=False,
                error=f"Processing error: {str(e)}",
                processing_time=time.time() - start_time
            )
            return result
    
    def _extract_metadata_from_html(self, html: str, base_url: str) -> LinkMetadata:
        """Extract metadata from HTML content."""
        soup = BeautifulSoup(html, 'lxml')
        metadata = LinkMetadata()
        
        # Basic metadata
        title_tag = soup.find('title')
        if title_tag:
            metadata.title = title_tag.get_text().strip()
        
        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '').strip()
            
            if not content:
                continue
            
            # Standard meta tags
            if name == 'description':
                metadata.description = content
            elif name == 'keywords':
                metadata.keywords = [kw.strip() for kw in content.split(',')]
            elif name == 'author':
                pass  # Could add author field
            
            # OpenGraph tags
            elif property_attr.startswith('og:'):
                og_type = property_attr[3:]  # Remove 'og:' prefix
                if og_type == 'title':
                    metadata.og_title = content
                elif og_type == 'description':
                    metadata.og_description = content
                elif og_type == 'image':
                    metadata.og_image = urljoin(base_url, content)
                elif og_type == 'url':
                    metadata.og_url = content
                elif og_type == 'site_name':
                    metadata.og_site_name = content
                elif og_type == 'type':
                    metadata.og_type = content
            
            # Twitter Card tags
            elif name.startswith('twitter:'):
                twitter_type = name[8:]  # Remove 'twitter:' prefix
                if twitter_type == 'card':
                    metadata.twitter_card = content
                elif twitter_type == 'title':
                    metadata.twitter_title = content
                elif twitter_type == 'description':
                    metadata.twitter_description = content
                elif twitter_type == 'image':
                    metadata.twitter_image = urljoin(base_url, content)
                elif twitter_type == 'site':
                    metadata.twitter_site = content
                elif twitter_type == 'creator':
                    metadata.twitter_creator = content
            
            # Technical metadata
            elif name == 'viewport':
                metadata.viewport = content
            elif property_attr == 'charset' or name == 'charset':
                metadata.charset = content
        
        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            metadata.canonical_url = urljoin(base_url, canonical['href'])
        
        # Language
        html_tag = soup.find('html')
        if html_tag:
            metadata.language = html_tag.get('lang')
        
        # Extract content preview
        if self.config.extract_content_preview:
            content_preview = self._extract_content_preview(soup)
            metadata.content_preview = content_preview[:self.config.preview_length] if content_preview else None
        
        # Extract keywords if not found in meta tags
        if self.config.extract_keywords and not metadata.keywords:
            metadata.keywords = self._extract_keywords_from_content(soup)
        
        # Content length
        body = soup.find('body')
        if body:
            metadata.content_length = len(body.get_text())
        
        return metadata
    
    def _extract_content_preview(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract preview text from page content."""
        # Try to find main content areas
        main_selectors = [
            'main', 'article', '.content', '.main-content', 
            '.post-content', '.entry-content', '#content'
        ]
        
        content_text = ""
        
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    text = element.get_text().strip()
                    if len(text) > len(content_text):
                        content_text = text
                break
        
        # Fallback to body text
        if not content_text:
            body = soup.find('body')
            if body:
                content_text = body.get_text()
        
        if content_text:
            # Clean up text
            content_text = re.sub(r'\s+', ' ', content_text).strip()
            return content_text
        
        return None
    
    def _extract_keywords_from_content(self, soup: BeautifulSoup) -> List[str]:
        """Extract keywords from page content."""
        # Get text from important elements
        text_elements = []
        
        # Headers
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text_elements.append(header.get_text())
        
        # Bold and italic text
        for emphasis in soup.find_all(['b', 'strong', 'i', 'em']):
            text_elements.append(emphasis.get_text())
        
        # First paragraph
        first_p = soup.find('p')
        if first_p:
            text_elements.append(first_p.get_text())
        
        # Extract meaningful words
        all_text = ' '.join(text_elements).lower()
        words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text)
        
        # Filter common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 
            'with', 'by', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'have', 'has',
            'had', 'do', 'does', 'did', 'get', 'got', 'make', 'made', 'take', 'took'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        # Count frequency and return top keywords
        from collections import Counter
        word_counts = Counter(filtered_words)
        
        return [word for word, count in word_counts.most_common(self.config.max_keywords)]
    
    def _calculate_relevance_score(self, metadata: LinkMetadata) -> float:
        """Calculate relevance score based on query."""
        if not self.query_tokens:
            return 0.5
        
        # Combine all textual content
        text_content = ' '.join(filter(None, [
            metadata.get_best_title(),
            metadata.get_best_description(),
            metadata.content_preview,
            ' '.join(metadata.keywords)
        ])).lower()
        
        if not text_content:
            return 0.0
        
        # Extract words from content
        content_words = set(re.findall(r'\b[a-zA-Z]+\b', text_content))
        
        # Calculate overlap with query
        overlap = len(self.query_tokens.intersection(content_words))
        max_possible = len(self.query_tokens)
        
        return overlap / max_possible if max_possible > 0 else 0.0
    
    def _calculate_quality_score(self, metadata: LinkMetadata) -> float:
        """Calculate quality score based on metadata completeness and content."""
        score = 0.0
        
        # Metadata completeness (0.4 weight)
        metadata_score = 0.0
        if metadata.get_best_title():
            metadata_score += 0.25
        if metadata.get_best_description():
            metadata_score += 0.25
        if metadata.get_best_image():
            metadata_score += 0.15
        if metadata.canonical_url:
            metadata_score += 0.1
        if metadata.language:
            metadata_score += 0.05
        if metadata.keywords:
            metadata_score += 0.2
        
        score += metadata_score * 0.4
        
        # Content quality (0.3 weight)
        content_score = 0.0
        if metadata.content_preview:
            preview_length = len(metadata.content_preview)
            # Optimal preview length around 200-300 chars
            if 100 <= preview_length <= 500:
                content_score += 0.3
            elif preview_length > 50:
                content_score += 0.2
            else:
                content_score += 0.1
        
        if metadata.content_length > 0:
            # Content length scoring (sweet spot around 1000-5000 chars)
            if 1000 <= metadata.content_length <= 10000:
                content_score += 0.2
            elif metadata.content_length > 500:
                content_score += 0.1
        
        score += content_score * 0.3
        
        # Technical quality (0.3 weight)
        technical_score = 0.0
        if metadata.status_code == 200:
            technical_score += 0.4
        elif metadata.status_code and 200 <= metadata.status_code < 300:
            technical_score += 0.3
        
        if metadata.response_time and metadata.response_time < 2.0:
            technical_score += 0.3
        elif metadata.response_time and metadata.response_time < 5.0:
            technical_score += 0.1
        
        if metadata.content_type and 'html' in metadata.content_type:
            technical_score += 0.3
        
        score += technical_score * 0.3
        
        return min(1.0, score)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cache_size': len(self._cache),
            'cache_enabled': self.config.enable_caching,
            'cache_ttl': self.config.cache_ttl
        }
    
    def clear_cache(self):
        """Clear the preview cache."""
        self._cache.clear()
        logger.info("Link preview cache cleared")


# Convenience functions
async def extract_link_previews(
    links: List[str],
    config: LinkPreviewConfig = None
) -> List[LinkPreviewResult]:
    """Extract link previews with default configuration."""
    async with LinkPreview(config) as previewer:
        return await previewer.extract_link_previews(links)


def filter_links_by_quality(
    results: List[LinkPreviewResult],
    min_quality_score: float = 0.3,
    min_relevance_score: float = 0.2
) -> List[LinkPreviewResult]:
    """Filter links by quality and relevance scores."""
    return [
        result for result in results
        if result.success and 
           result.quality_score >= min_quality_score and 
           result.relevance_score >= min_relevance_score
    ]
