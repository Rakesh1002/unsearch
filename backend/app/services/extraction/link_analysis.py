"""
Intelligent link prioritization and scoring inspired by crawl4ai.

This module implements sophisticated link analysis capabilities:
- 3-layer scoring system for smart link prioritization
- Domain authority and credibility assessment
- Content relevance scoring
- Link quality metrics and filtering
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from urllib.parse import urlparse, urljoin
from collections import Counter, defaultdict

import httpx
import numpy as np
from bs4 import BeautifulSoup
import structlog

from app.utils.text_processing import clean_tokens, sanitize_text

logger = structlog.get_logger(__name__)


@dataclass
class LinkInfo:
    """Comprehensive information about a link."""
    url: str
    text: str
    title: Optional[str] = None
    domain: str = ""
    path: str = ""
    is_external: bool = True
    
    # Scoring components
    relevance_score: float = 0.0
    authority_score: float = 0.0
    quality_score: float = 0.0
    freshness_score: float = 0.0
    
    # Combined scores
    overall_score: float = 0.0
    priority_rank: int = 0
    
    # Metadata
    depth_from_root: int = 0
    discovered_at: float = 0.0
    extraction_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.domain and self.url:
            parsed = urlparse(self.url)
            self.domain = parsed.netloc
            self.path = parsed.path
        
        if not self.discovered_at:
            self.discovered_at = time.time()


@dataclass
class LinkPreviewConfig:
    """Configuration for link analysis and scoring."""
    query: Optional[str] = None
    score_threshold: float = 0.3
    concurrent_requests: int = 10
    max_preview_length: int = 500
    enable_domain_authority: bool = True
    enable_content_preview: bool = True
    enable_freshness_scoring: bool = True
    preview_timeout: float = 5.0
    
    # Authority domain lists
    high_authority_domains: List[str] = field(default_factory=lambda: [
        'wikipedia.org', 'github.com', 'stackoverflow.com',
        'mozilla.org', 'w3.org', 'ietf.org', 'arxiv.org',
        'nature.com', 'sciencedirect.com', 'ieee.org'
    ])
    
    medium_authority_domains: List[str] = field(default_factory=lambda: [
        'medium.com', 'dev.to', 'reddit.com', 'news.ycombinator.com',
        'techcrunch.com', 'arstechnica.com', 'wired.com'
    ])
    
    low_quality_indicators: List[str] = field(default_factory=lambda: [
        'ads', 'advertisement', 'popup', 'spam', 'click',
        'buy-now', 'discount', 'offer', 'deal'
    ])


@dataclass
class LinkAnalysisResult:
    """Result of comprehensive link analysis."""
    analyzed_links: List[LinkInfo]
    top_links: List[LinkInfo]
    analysis_metadata: Dict[str, Any]
    domain_statistics: Dict[str, Any]
    quality_distribution: Dict[str, int]


class LinkScorer:
    """
    Sophisticated link scoring system with multiple scoring layers.
    
    Implements a 3-layer scoring approach:
    1. Relevance scoring - content relevance to query
    2. Authority scoring - domain credibility and authority
    3. Quality scoring - link and content quality indicators
    """
    
    def __init__(self, config: LinkPreviewConfig):
        """Initialize link scorer with configuration."""
        self.config = config
        
        # Compile regex patterns for performance
        self.quality_patterns = {
            'article_indicators': re.compile(r'(article|post|blog|news|story|guide|tutorial)', re.I),
            'date_patterns': re.compile(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})'),
            'low_quality': re.compile('|'.join(self.config.low_quality_indicators), re.I),
            'file_extensions': re.compile(r'\.(pdf|doc|docx|ppt|pptx|xls|xlsx)$', re.I)
        }
    
    async def score_links(
        self,
        links: List[str],
        base_url: str = "",
        link_texts: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> List[LinkInfo]:
        """
        Score a list of links using the 3-layer scoring system.
        
        Args:
            links: List of URLs to score
            base_url: Base URL for context
            link_texts: Optional mapping of URLs to their link text
            **kwargs: Additional scoring parameters
            
        Returns:
            List of LinkInfo objects with computed scores
        """
        start_time = time.time()
        link_texts = link_texts or {}
        
        # Create LinkInfo objects
        link_infos = []
        for url in links:
            absolute_url = urljoin(base_url, url) if base_url else url
            text = link_texts.get(url, url)
            
            link_info = LinkInfo(
                url=absolute_url,
                text=text,
                is_external=self._is_external_link(absolute_url, base_url)
            )
            link_infos.append(link_info)
        
        logger.info("link_scoring_started", total_links=len(link_infos))
        
        # Layer 1: Relevance Scoring
        await self._score_relevance(link_infos)
        
        # Layer 2: Authority Scoring
        await self._score_authority(link_infos)
        
        # Layer 3: Quality Scoring
        await self._score_quality(link_infos)
        
        # Layer 4: Freshness Scoring (if enabled)
        if self.config.enable_freshness_scoring:
            await self._score_freshness(link_infos)
        
        # Compute overall scores and rankings
        await self._compute_overall_scores(link_infos)
        
        # Sort by overall score
        link_infos.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Assign priority ranks
        for i, link_info in enumerate(link_infos):
            link_info.priority_rank = i + 1
        
        processing_time = time.time() - start_time
        logger.info(
            "link_scoring_completed",
            total_links=len(link_infos),
            processing_time=processing_time,
            top_score=link_infos[0].overall_score if link_infos else 0
        )
        
        return link_infos
    
    async def _score_relevance(self, link_infos: List[LinkInfo]):
        """Layer 1: Score links based on relevance to query."""
        if not self.config.query:
            # No query provided, assign neutral relevance
            for link_info in link_infos:
                link_info.relevance_score = 0.5
            return
        
        query_tokens = set(clean_tokens(self.config.query.lower().split()))
        
        for link_info in link_infos:
            score = 0.0
            
            # Score based on URL path
            url_tokens = set(clean_tokens(re.findall(r'[a-zA-Z]+', link_info.path.lower())))
            if url_tokens:
                url_overlap = len(query_tokens.intersection(url_tokens))
                score += (url_overlap / len(query_tokens)) * 0.4
            
            # Score based on link text
            if link_info.text and link_info.text != link_info.url:
                text_tokens = set(clean_tokens(link_info.text.lower().split()))
                if text_tokens:
                    text_overlap = len(query_tokens.intersection(text_tokens))
                    score += (text_overlap / len(query_tokens)) * 0.6
            
            # Bonus for exact query matches
            if self.config.query.lower() in link_info.url.lower():
                score += 0.3
            if self.config.query.lower() in link_info.text.lower():
                score += 0.4
            
            link_info.relevance_score = min(1.0, score)
    
    async def _score_authority(self, link_infos: List[LinkInfo]):
        """Layer 2: Score links based on domain authority."""
        for link_info in link_infos:
            score = 0.5  # Base authority score
            domain = link_info.domain.lower()
            
            # High authority domains
            if any(auth_domain in domain for auth_domain in self.config.high_authority_domains):
                score = 0.9
            
            # Medium authority domains
            elif any(med_domain in domain for med_domain in self.config.medium_authority_domains):
                score = 0.7
            
            # Educational and government domains
            elif domain.endswith(('.edu', '.gov', '.org')):
                score = 0.8
            
            # Well-known top-level domains
            elif domain.endswith(('.com', '.net')):
                score = 0.6
            
            # Country code TLDs
            elif len(domain.split('.')[-1]) == 2:
                score = 0.5
            
            # Subdomains penalty
            if len(domain.split('.')) > 2:
                score *= 0.9
            
            # Very short or very long domain names (potential spam indicators)
            base_domain = domain.split('.')[0]
            if len(base_domain) < 3 or len(base_domain) > 20:
                score *= 0.8
            
            link_info.authority_score = score
    
    async def _score_quality(self, link_infos: List[LinkInfo]):
        """Layer 3: Score links based on quality indicators."""
        for link_info in link_infos:
            score = 0.5  # Base quality score
            url = link_info.url.lower()
            path = link_info.path.lower()
            text = link_info.text.lower()
            
            # Positive quality indicators
            if self.quality_patterns['article_indicators'].search(path):
                score += 0.2
            
            # File format bonuses
            if self.quality_patterns['file_extensions'].search(url):
                score += 0.15  # PDFs and documents often contain quality content
            
            # Link text quality
            if link_info.text and link_info.text != link_info.url:
                if len(link_info.text) > 10:  # Descriptive link text
                    score += 0.15
                
                # Avoid generic link texts
                generic_texts = ['click here', 'read more', 'more info', 'link', 'here']
                if not any(generic in text for generic in generic_texts):
                    score += 0.1
            
            # URL structure quality
            if '?' not in url:  # Clean URLs without query parameters
                score += 0.05
            
            if path.count('/') <= 4:  # Not too deep in site hierarchy
                score += 0.05
            
            # Negative quality indicators
            if self.quality_patterns['low_quality'].search(url) or self.quality_patterns['low_quality'].search(text):
                score -= 0.3
            
            # Penalize very long URLs (potential spam)
            if len(link_info.url) > 100:
                score -= 0.1
            
            # Penalize URLs with many parameters
            if url.count('&') > 5:
                score -= 0.2
            
            link_info.quality_score = max(0.0, min(1.0, score))
    
    async def _score_freshness(self, link_infos: List[LinkInfo]):
        """Layer 4: Score links based on freshness indicators."""
        current_year = time.gmtime().tm_year
        
        for link_info in link_infos:
            score = 0.5  # Base freshness score
            
            # Look for dates in URL
            date_matches = self.quality_patterns['date_patterns'].findall(link_info.url)
            if date_matches:
                # Extract year from the most recent date found
                years = []
                for date_str in date_matches:
                    # Simple year extraction
                    year_match = re.search(r'(\d{4})', date_str)
                    if year_match:
                        year = int(year_match.group(1))
                        if 2000 <= year <= current_year:  # Valid year range
                            years.append(year)
                
                if years:
                    latest_year = max(years)
                    age = current_year - latest_year
                    
                    # Score based on age
                    if age == 0:  # Current year
                        score = 1.0
                    elif age == 1:  # Last year
                        score = 0.9
                    elif age <= 3:  # Within 3 years
                        score = 0.7
                    elif age <= 5:  # Within 5 years
                        score = 0.5
                    else:  # Older content
                        score = max(0.1, 0.5 - (age - 5) * 0.05)
            
            # Look for freshness indicators in path
            fresh_indicators = ['2024', '2023', 'latest', 'new', 'recent', 'current']
            path_lower = link_info.path.lower()
            if any(indicator in path_lower for indicator in fresh_indicators):
                score += 0.2
            
            link_info.freshness_score = min(1.0, score)
    
    async def _compute_overall_scores(self, link_infos: List[LinkInfo]):
        """Compute overall scores by combining all scoring layers."""
        # Weights for different score components
        weights = {
            'relevance': 0.35,
            'authority': 0.25,
            'quality': 0.25,
            'freshness': 0.15
        }
        
        for link_info in link_infos:
            overall_score = (
                link_info.relevance_score * weights['relevance'] +
                link_info.authority_score * weights['authority'] +
                link_info.quality_score * weights['quality'] +
                link_info.freshness_score * weights['freshness']
            )
            
            link_info.overall_score = overall_score
            
            # Store scoring breakdown for debugging
            link_info.extraction_context = {
                'relevance': link_info.relevance_score,
                'authority': link_info.authority_score,
                'quality': link_info.quality_score,
                'freshness': link_info.freshness_score,
                'weights': weights
            }
    
    def _is_external_link(self, url: str, base_url: str) -> bool:
        """Determine if a link is external to the base URL."""
        if not base_url:
            return True
        
        try:
            url_domain = urlparse(url).netloc
            base_domain = urlparse(base_url).netloc
            return url_domain != base_domain
        except:
            return True


class LinkAnalyzer:
    """
    Comprehensive link analysis system.
    
    This class orchestrates the complete link analysis process including
    extraction, scoring, filtering, and preview generation.
    """
    
    def __init__(self, config: LinkPreviewConfig):
        """Initialize link analyzer."""
        self.config = config
        self.scorer = LinkScorer(config)
    
    async def analyze_page_links(
        self,
        html_content: str,
        base_url: str = "",
        **kwargs
    ) -> LinkAnalysisResult:
        """
        Analyze all links found in HTML content.
        
        Args:
            html_content: HTML content to analyze
            base_url: Base URL for link resolution
            **kwargs: Additional analysis parameters
            
        Returns:
            LinkAnalysisResult with comprehensive link analysis
        """
        start_time = time.time()
        
        # Extract links from HTML
        links, link_texts = self._extract_links_from_html(html_content, base_url)
        
        if not links:
            return LinkAnalysisResult(
                analyzed_links=[],
                top_links=[],
                analysis_metadata={'total_links': 0, 'error': 'No links found'},
                domain_statistics={},
                quality_distribution={}
            )
        
        logger.info("link_analysis_started", total_links=len(links), base_url=base_url)
        
        # Score links
        scored_links = await self.scorer.score_links(
            links=links,
            base_url=base_url,
            link_texts=link_texts,
            **kwargs
        )
        
        # Filter links by score threshold
        filtered_links = [
            link for link in scored_links 
            if link.overall_score >= self.config.score_threshold
        ]
        
        # Generate previews for top links if enabled
        if self.config.enable_content_preview:
            top_links_for_preview = filtered_links[:self.config.concurrent_requests]
            await self._generate_link_previews(top_links_for_preview)
        
        # Generate statistics
        domain_stats = self._generate_domain_statistics(scored_links)
        quality_dist = self._generate_quality_distribution(scored_links)
        
        processing_time = time.time() - start_time
        
        # Prepare metadata
        analysis_metadata = {
            'total_links_found': len(links),
            'total_links_scored': len(scored_links),
            'links_above_threshold': len(filtered_links),
            'score_threshold': self.config.score_threshold,
            'processing_time': processing_time,
            'base_url': base_url,
            'query': self.config.query,
            'config': self.config.__dict__
        }
        
        logger.info(
            "link_analysis_completed",
            total_analyzed=len(scored_links),
            above_threshold=len(filtered_links),
            processing_time=processing_time
        )
        
        return LinkAnalysisResult(
            analyzed_links=scored_links,
            top_links=filtered_links,
            analysis_metadata=analysis_metadata,
            domain_statistics=domain_stats,
            quality_distribution=quality_dist
        )
    
    def _extract_links_from_html(
        self, 
        html_content: str, 
        base_url: str
    ) -> Tuple[List[str], Dict[str, str]]:
        """Extract links and their text from HTML content."""
        soup = BeautifulSoup(html_content, 'lxml')
        links = []
        link_texts = {}
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip anchor links, javascript, and email links
            if href.startswith(('#', 'javascript:', 'mailto:')):
                continue
            
            # Make URL absolute
            absolute_url = urljoin(base_url, href)
            
            # Extract link text
            link_text = sanitize_text(a_tag.get_text())
            if not link_text:
                link_text = a_tag.get('title', href)
            
            links.append(absolute_url)
            link_texts[absolute_url] = link_text
        
        # Remove duplicates while preserving order
        unique_links = []
        seen = set()
        for link in links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)
        
        return unique_links, link_texts
    
    async def _generate_link_previews(self, links: List[LinkInfo]):
        """Generate content previews for top links."""
        if not links:
            return
        
        logger.info("generating_link_previews", count=len(links))
        
        async def fetch_preview(link_info: LinkInfo):
            try:
                async with httpx.AsyncClient(timeout=self.config.preview_timeout) as client:
                    response = await client.get(
                        link_info.url,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                    )
                    
                    if response.status_code == 200:
                        # Extract preview content
                        soup = BeautifulSoup(response.text, 'lxml')
                        
                        # Try to get meta description
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc and meta_desc.get('content'):
                            preview = sanitize_text(meta_desc['content'])
                        else:
                            # Get first paragraph
                            first_p = soup.find('p')
                            preview = sanitize_text(first_p.get_text()) if first_p else ""
                        
                        # Truncate to max length
                        if len(preview) > self.config.max_preview_length:
                            preview = preview[:self.config.max_preview_length] + "..."
                        
                        link_info.extraction_context['preview'] = preview
                        link_info.extraction_context['preview_status'] = 'success'
                    
            except Exception as e:
                link_info.extraction_context['preview_error'] = str(e)
                link_info.extraction_context['preview_status'] = 'failed'
        
        # Generate previews concurrently
        tasks = [fetch_preview(link) for link in links]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _generate_domain_statistics(self, links: List[LinkInfo]) -> Dict[str, Any]:
        """Generate statistics about domains in the link set."""
        domain_counts = Counter(link.domain for link in links)
        external_count = sum(1 for link in links if link.is_external)
        internal_count = len(links) - external_count
        
        # Authority distribution
        high_authority = sum(1 for link in links if link.authority_score >= 0.8)
        medium_authority = sum(1 for link in links if 0.5 <= link.authority_score < 0.8)
        low_authority = sum(1 for link in links if link.authority_score < 0.5)
        
        return {
            'total_domains': len(domain_counts),
            'most_common_domains': domain_counts.most_common(10),
            'external_links': external_count,
            'internal_links': internal_count,
            'authority_distribution': {
                'high': high_authority,
                'medium': medium_authority,
                'low': low_authority
            }
        }
    
    def _generate_quality_distribution(self, links: List[LinkInfo]) -> Dict[str, int]:
        """Generate distribution of link quality scores."""
        score_ranges = {
            'excellent': 0,    # 0.8 - 1.0
            'good': 0,         # 0.6 - 0.8
            'average': 0,      # 0.4 - 0.6
            'poor': 0,         # 0.2 - 0.4
            'very_poor': 0     # 0.0 - 0.2
        }
        
        for link in links:
            score = link.overall_score
            if score >= 0.8:
                score_ranges['excellent'] += 1
            elif score >= 0.6:
                score_ranges['good'] += 1
            elif score >= 0.4:
                score_ranges['average'] += 1
            elif score >= 0.2:
                score_ranges['poor'] += 1
            else:
                score_ranges['very_poor'] += 1
        
        return score_ranges


# Convenience functions
async def analyze_links(
    html_content: str,
    base_url: str = "",
    query: Optional[str] = None,
    score_threshold: float = 0.3,
    concurrent_requests: int = 10
) -> LinkAnalysisResult:
    """
    Analyze links in HTML content with intelligent scoring.
    
    Args:
        html_content: HTML content to analyze
        base_url: Base URL for link resolution
        query: Optional query for relevance scoring
        score_threshold: Minimum score threshold for filtering
        concurrent_requests: Number of concurrent preview requests
        
    Returns:
        LinkAnalysisResult with comprehensive analysis
    """
    config = LinkPreviewConfig(
        query=query,
        score_threshold=score_threshold,
        concurrent_requests=concurrent_requests
    )
    
    analyzer = LinkAnalyzer(config)
    return await analyzer.analyze_page_links(html_content, base_url)


async def get_top_links(
    html_content: str,
    base_url: str = "",
    query: Optional[str] = None,
    top_k: int = 10
) -> List[LinkInfo]:
    """
    Get top-scored links from HTML content.
    
    Args:
        html_content: HTML content to analyze
        base_url: Base URL for link resolution  
        query: Optional query for relevance scoring
        top_k: Number of top links to return
        
    Returns:
        List of top-scored LinkInfo objects
    """
    result = await analyze_links(
        html_content=html_content,
        base_url=base_url,
        query=query,
        score_threshold=0.0  # No filtering, get all links
    )
    
    return result.analyzed_links[:top_k]
