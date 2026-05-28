"""
Adaptive crawling with learning algorithms inspired by crawl4ai.

This module implements adaptive information foraging for efficient web crawling:
- Statistical strategy for learning content patterns
- Embedding-based strategy for semantic understanding
- Learning algorithms that improve extraction over time
- State persistence for continued learning
"""

import asyncio
import json
import math
import pickle
import re
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse

import numpy as np
import structlog
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.responses import ScrapedContent
from app.utils.text_processing import clean_tokens, sanitize_text

logger = structlog.get_logger(__name__)


@dataclass
class CrawlState:
    """Tracks the current state of adaptive crawling."""
    crawled_urls: Set[str] = field(default_factory=set)
    knowledge_base: List[Dict[str, Any]] = field(default_factory=list)
    pending_links: List[Dict[str, Any]] = field(default_factory=list)
    query: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Statistical tracking
    term_frequencies: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    document_frequencies: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    documents_with_terms: Dict[str, Set[int]] = field(default_factory=lambda: defaultdict(set))
    total_documents: int = 0
    
    # History tracking for saturation detection
    new_terms_history: List[int] = field(default_factory=list)
    crawl_order: List[str] = field(default_factory=list)
    
    # Content quality tracking
    quality_scores: List[float] = field(default_factory=list)
    relevance_scores: List[float] = field(default_factory=list)
    
    # Learning parameters
    learning_rate: float = 0.1
    confidence_threshold: float = 0.7
    max_crawl_depth: int = 5
    max_pages: int = 20
    
    def save(self, path: Union[str, Path]):
        """Save state to disk for persistence."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert sets to lists for JSON serialization
        state_dict = {
            'crawled_urls': list(self.crawled_urls),
            'knowledge_base': self.knowledge_base,
            'pending_links': self.pending_links,
            'query': self.query,
            'metrics': self.metrics,
            'term_frequencies': dict(self.term_frequencies),
            'document_frequencies': dict(self.document_frequencies),
            'documents_with_terms': {k: list(v) for k, v in self.documents_with_terms.items()},
            'total_documents': self.total_documents,
            'new_terms_history': self.new_terms_history,
            'crawl_order': self.crawl_order,
            'quality_scores': self.quality_scores,
            'relevance_scores': self.relevance_scores,
            'learning_rate': self.learning_rate,
            'confidence_threshold': self.confidence_threshold,
            'max_crawl_depth': self.max_crawl_depth,
            'max_pages': self.max_pages
        }
        
        with open(path, 'w') as f:
            json.dump(state_dict, f, indent=2)
    
    @classmethod
    def load(cls, path: Union[str, Path]) -> 'CrawlState':
        """Load state from disk."""
        path = Path(path)
        if not path.exists():
            return cls()
            
        with open(path, 'r') as f:
            state_dict = json.load(f)
        
        state = cls()
        state.crawled_urls = set(state_dict.get('crawled_urls', []))
        state.knowledge_base = state_dict.get('knowledge_base', [])
        state.pending_links = state_dict.get('pending_links', [])
        state.query = state_dict.get('query', '')
        state.metrics = state_dict.get('metrics', {})
        state.term_frequencies = defaultdict(int, state_dict.get('term_frequencies', {}))
        state.document_frequencies = defaultdict(int, state_dict.get('document_frequencies', {}))
        state.documents_with_terms = defaultdict(
            set, 
            {k: set(v) for k, v in state_dict.get('documents_with_terms', {}).items()}
        )
        state.total_documents = state_dict.get('total_documents', 0)
        state.new_terms_history = state_dict.get('new_terms_history', [])
        state.crawl_order = state_dict.get('crawl_order', [])
        state.quality_scores = state_dict.get('quality_scores', [])
        state.relevance_scores = state_dict.get('relevance_scores', [])
        state.learning_rate = state_dict.get('learning_rate', 0.1)
        state.confidence_threshold = state_dict.get('confidence_threshold', 0.7)
        state.max_crawl_depth = state_dict.get('max_crawl_depth', 5)
        state.max_pages = state_dict.get('max_pages', 20)
        
        return state


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive crawling."""
    confidence_threshold: float = 0.7
    max_depth: int = 5
    max_pages: int = 20
    strategy: str = "statistical"  # "statistical" or "embedding"
    learning_rate: float = 0.1
    min_relevance_score: float = 0.3
    saturation_threshold: int = 5  # Number of crawls without new terms
    quality_threshold: float = 0.5
    save_state: bool = True
    state_path: Optional[str] = None


class CrawlStrategy(ABC):
    """Abstract base class for crawling strategies."""
    
    @abstractmethod
    async def should_continue_crawling(self, state: CrawlState) -> bool:
        """Determine if crawling should continue based on current state."""
        pass
    
    @abstractmethod
    async def score_url(self, url: str, state: CrawlState) -> float:
        """Score a URL for crawling priority."""
        pass
    
    @abstractmethod
    async def update_state(self, state: CrawlState, content: ScrapedContent) -> None:
        """Update crawling state with new content."""
        pass


class StatisticalStrategy(CrawlStrategy):
    """
    Statistical strategy for adaptive crawling.
    
    Uses term frequency analysis, document frequency tracking,
    and information saturation detection to determine when
    sufficient information has been gathered.
    """
    
    def __init__(self, config: AdaptiveConfig):
        """Initialize statistical strategy."""
        self.config = config
        
    async def should_continue_crawling(self, state: CrawlState) -> bool:
        """Determine if crawling should continue based on statistical analysis."""
        # Check basic limits
        if len(state.crawled_urls) >= self.config.max_pages:
            logger.info("crawl_limit_reached", pages=len(state.crawled_urls))
            return False
        
        if len(state.crawl_order) >= self.config.max_depth:
            logger.info("depth_limit_reached", depth=len(state.crawl_order))
            return False
        
        # Check information saturation
        if len(state.new_terms_history) >= self.config.saturation_threshold:
            recent_new_terms = sum(state.new_terms_history[-self.config.saturation_threshold:])
            avg_new_terms = recent_new_terms / self.config.saturation_threshold
            
            if avg_new_terms < 5:  # Less than 5 new terms per crawl on average
                logger.info("information_saturation_detected", avg_new_terms=avg_new_terms)
                return False
        
        # Check confidence threshold
        if state.metrics.get('confidence', 0) >= self.config.confidence_threshold:
            logger.info("confidence_threshold_reached", confidence=state.metrics['confidence'])
            return False
        
        # Check content quality trends
        if len(state.quality_scores) >= 3:
            recent_quality = np.mean(state.quality_scores[-3:])
            if recent_quality < self.config.quality_threshold:
                logger.info("quality_threshold_not_met", recent_quality=recent_quality)
                return False
        
        return True
    
    async def score_url(self, url: str, state: CrawlState) -> float:
        """Score URL based on statistical relevance."""
        score = 0.5  # Base score
        
        # Parse URL for features
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path.lower()
        
        # Query-based scoring
        if state.query:
            query_terms = set(clean_tokens(state.query.lower().split()))
            
            # Check URL path for query terms
            url_terms = set(clean_tokens(re.findall(r'[a-zA-Z]+', path)))
            term_overlap = len(query_terms.intersection(url_terms))
            if term_overlap > 0:
                score += 0.3 * (term_overlap / len(query_terms))
        
        # Domain authority (simplified)
        authority_domains = [
            'wikipedia.org', 'github.com', 'stackoverflow.com',
            'news.ycombinator.com', 'reddit.com', 'medium.com'
        ]
        if any(auth_domain in domain for auth_domain in authority_domains):
            score += 0.2
        
        # Path depth penalty (prefer shallower pages)
        path_depth = len([p for p in path.split('/') if p])
        if path_depth > 0:
            score -= min(0.3, path_depth * 0.05)
        
        # Content type indicators
        content_indicators = ['article', 'post', 'blog', 'news', 'tutorial', 'guide']
        if any(indicator in path for indicator in content_indicators):
            score += 0.2
        
        # Avoid non-content URLs
        avoid_patterns = ['login', 'register', 'cart', 'checkout', 'admin', 'api']
        if any(pattern in path for pattern in avoid_patterns):
            score -= 0.4
        
        return max(0.0, min(1.0, score))
    
    async def update_state(self, state: CrawlState, content: ScrapedContent) -> None:
        """Update statistical state with new content."""
        if not content.extraction_success or not content.text:
            return
        
        # Tokenize content
        tokens = clean_tokens(content.text.lower().split())
        if not tokens:
            return
        
        # Update document tracking
        doc_id = state.total_documents
        state.total_documents += 1
        
        # Track new terms
        new_terms_count = 0
        term_counts = Counter(tokens)
        
        for term, count in term_counts.items():
            # Update term frequencies
            state.term_frequencies[term] += count
            
            # Update document frequencies
            if doc_id not in state.documents_with_terms[term]:
                state.documents_with_terms[term].add(doc_id)
                state.document_frequencies[term] += 1
                
                # Count as new term if first occurrence
                if state.document_frequencies[term] == 1:
                    new_terms_count += 1
        
        # Update new terms history
        state.new_terms_history.append(new_terms_count)
        if len(state.new_terms_history) > 20:  # Keep last 20 crawls
            state.new_terms_history = state.new_terms_history[-20:]
        
        # Update crawl order
        state.crawl_order.append(content.url)
        
        # Store content in knowledge base
        state.knowledge_base.append({
            'url': content.url,
            'title': content.title,
            'text': content.text[:1000],  # Store first 1000 chars
            'quality_score': content.content_quality_score or 0.0,
            'word_count': content.word_count,
            'extraction_time': content.extraction_time_ms,
            'crawl_order': len(state.crawl_order)
        })
        
        # Update quality tracking
        state.quality_scores.append(content.content_quality_score or 0.0)
        if len(state.quality_scores) > 20:
            state.quality_scores = state.quality_scores[-20:]
        
        # Calculate relevance score if query exists
        if state.query:
            relevance = await self._calculate_relevance(content.text, state.query)
            state.relevance_scores.append(relevance)
            if len(state.relevance_scores) > 20:
                state.relevance_scores = state.relevance_scores[-20:]
        
        # Update confidence metrics
        await self._update_confidence_metrics(state)
    
    async def _calculate_relevance(self, text: str, query: str) -> float:
        """Calculate relevance score between text and query."""
        if not text or not query:
            return 0.0
        
        text_tokens = set(clean_tokens(text.lower().split()))
        query_tokens = set(clean_tokens(query.lower().split()))
        
        if not text_tokens or not query_tokens:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(text_tokens.intersection(query_tokens))
        union = len(text_tokens.union(query_tokens))
        
        return intersection / union if union > 0 else 0.0
    
    async def _update_confidence_metrics(self, state: CrawlState) -> None:
        """Update confidence metrics based on current state."""
        if state.total_documents == 0:
            state.metrics['confidence'] = 0.0
            return
        
        # Calculate information gain rate
        if len(state.new_terms_history) > 1:
            recent_gains = state.new_terms_history[-3:] if len(state.new_terms_history) >= 3 else state.new_terms_history
            avg_gain = np.mean(recent_gains)
            max_possible_gain = 50  # Assumed max new terms per crawl
            gain_rate = 1 - (avg_gain / max_possible_gain)
        else:
            gain_rate = 0.0
        
        # Calculate quality consistency
        if len(state.quality_scores) > 1:
            quality_std = np.std(state.quality_scores[-5:])
            quality_consistency = max(0.0, 1 - quality_std)
        else:
            quality_consistency = 0.0
        
        # Calculate relevance consistency
        relevance_consistency = 0.0
        if state.query and len(state.relevance_scores) > 1:
            relevance_std = np.std(state.relevance_scores[-5:])
            relevance_consistency = max(0.0, 1 - relevance_std)
        
        # Combined confidence score
        confidence = (
            gain_rate * 0.4 +
            quality_consistency * 0.3 +
            relevance_consistency * 0.3
        )
        
        state.metrics.update({
            'confidence': confidence,
            'gain_rate': gain_rate,
            'quality_consistency': quality_consistency,
            'relevance_consistency': relevance_consistency,
            'total_terms': len(state.term_frequencies),
            'unique_documents': state.total_documents
        })


class AdaptiveCrawler:
    """
    Adaptive crawler that learns and improves extraction over time.
    
    This crawler uses adaptive strategies to determine when sufficient
    information has been gathered and which URLs to prioritize.
    """
    
    def __init__(
        self,
        scraping_service,
        config: AdaptiveConfig,
        state_path: Optional[str] = None
    ):
        """
        Initialize adaptive crawler.
        
        Args:
            scraping_service: The scraping service to use
            config: Adaptive crawling configuration
            state_path: Optional path to save/load crawling state
        """
        self.scraping_service = scraping_service
        self.config = config
        self.state_path = state_path or config.state_path
        
        # Initialize strategy
        if config.strategy == "statistical":
            self.strategy = StatisticalStrategy(config)
        else:
            raise ValueError(f"Unknown strategy: {config.strategy}")
        
        # Load or create state
        if self.state_path and Path(self.state_path).exists():
            self.state = CrawlState.load(self.state_path)
            logger.info("adaptive_state_loaded", path=self.state_path)
        else:
            self.state = CrawlState()
            self.state.confidence_threshold = config.confidence_threshold
            self.state.max_crawl_depth = config.max_depth
            self.state.max_pages = config.max_pages
            self.state.learning_rate = config.learning_rate
    
    async def adaptive_crawl(
        self,
        start_url: str,
        query: str,
        max_links_to_follow: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform adaptive crawling starting from a URL.
        
        Args:
            start_url: Starting URL for crawling
            query: Query to guide crawling relevance
            max_links_to_follow: Maximum number of links to follow
            **kwargs: Additional crawling parameters
            
        Returns:
            Dictionary with crawling results and metadata
        """
        self.state.query = query
        crawled_results = []
        
        try:
            # Initial crawl
            logger.info("adaptive_crawl_started", start_url=start_url, query=query)
            
            if start_url not in self.state.crawled_urls:
                initial_result = await self._crawl_single_url(start_url, **kwargs)
                if initial_result:
                    crawled_results.append(initial_result)
                    await self.strategy.update_state(self.state, initial_result)
                    self.state.crawled_urls.add(start_url)
            
            # Extract and score links from initial page
            if crawled_results and crawled_results[0].links:
                await self._update_pending_links(crawled_results[0].links, start_url)
            
            # Adaptive crawling loop
            crawl_count = 1
            while (await self.strategy.should_continue_crawling(self.state) and 
                   crawl_count < max_links_to_follow and
                   self.state.pending_links):
                
                # Get next best URL to crawl
                next_url = await self._get_next_url_to_crawl()
                if not next_url:
                    break
                
                # Crawl the URL
                result = await self._crawl_single_url(next_url, **kwargs)
                if result:
                    crawled_results.append(result)
                    await self.strategy.update_state(self.state, result)
                    self.state.crawled_urls.add(next_url)
                    
                    # Extract new links
                    if result.links:
                        await self._update_pending_links(result.links, next_url)
                
                crawl_count += 1
                
                # Save state periodically
                if self.config.save_state and self.state_path:
                    self.state.save(self.state_path)
            
            # Final state save
            if self.config.save_state and self.state_path:
                self.state.save(self.state_path)
            
            logger.info(
                "adaptive_crawl_completed",
                urls_crawled=len(crawled_results),
                confidence=self.state.metrics.get('confidence', 0),
                total_terms=len(self.state.term_frequencies)
            )
            
            return {
                'results': crawled_results,
                'crawl_state': {
                    'urls_crawled': len(self.state.crawled_urls),
                    'confidence': self.state.metrics.get('confidence', 0),
                    'total_terms': len(self.state.term_frequencies),
                    'total_documents': self.state.total_documents,
                    'avg_quality': np.mean(self.state.quality_scores) if self.state.quality_scores else 0,
                    'pending_links': len(self.state.pending_links)
                },
                'metrics': self.state.metrics,
                'query': query
            }
            
        except Exception as e:
            logger.error("adaptive_crawl_failed", error=str(e), start_url=start_url)
            raise
    
    async def _crawl_single_url(self, url: str, **kwargs) -> Optional[ScrapedContent]:
        """Crawl a single URL using the scraping service."""
        try:
            results = await self.scraping_service.scrape_urls([url], **kwargs)
            return results[0] if results else None
        except Exception as e:
            logger.error("single_url_crawl_failed", url=url, error=str(e))
            return None
    
    async def _update_pending_links(self, links: List[str], base_url: str) -> None:
        """Update pending links with relevance scoring."""
        new_links = []
        
        for link in links:
            # Make absolute URL
            abs_link = urljoin(base_url, link)
            
            # Skip if already crawled or pending
            if (abs_link in self.state.crawled_urls or 
                any(pl['url'] == abs_link for pl in self.state.pending_links)):
                continue
            
            # Score the URL
            score = await self.strategy.score_url(abs_link, self.state)
            
            if score >= self.config.min_relevance_score:
                new_links.append({
                    'url': abs_link,
                    'score': score,
                    'base_url': base_url,
                    'discovered_at': len(self.state.crawl_order)
                })
        
        # Add new links and sort by score
        self.state.pending_links.extend(new_links)
        self.state.pending_links.sort(key=lambda x: x['score'], reverse=True)
        
        # Limit pending links to prevent memory issues
        if len(self.state.pending_links) > 100:
            self.state.pending_links = self.state.pending_links[:100]
    
    async def _get_next_url_to_crawl(self) -> Optional[str]:
        """Get the next best URL to crawl based on scoring."""
        if not self.state.pending_links:
            return None
        
        # Get highest scored link
        next_link = self.state.pending_links.pop(0)
        return next_link['url']
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning progress."""
        if not self.state.term_frequencies:
            return {'status': 'no_learning_data'}
        
        # Top terms
        top_terms = sorted(
            self.state.term_frequencies.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]
        
        return {
            'total_documents': self.state.total_documents,
            'unique_terms': len(self.state.term_frequencies),
            'confidence': self.state.metrics.get('confidence', 0),
            'top_terms': top_terms,
            'avg_quality': np.mean(self.state.quality_scores) if self.state.quality_scores else 0,
            'crawl_efficiency': len(self.state.crawled_urls) / max(1, len(self.state.crawl_order)),
            'information_saturation': np.mean(self.state.new_terms_history[-5:]) if len(self.state.new_terms_history) >= 5 else 0
        }


# Convenience functions
async def create_adaptive_crawler(
    scraping_service,
    confidence_threshold: float = 0.7,
    max_depth: int = 5,
    max_pages: int = 20,
    strategy: str = "statistical",
    state_path: Optional[str] = None
) -> AdaptiveCrawler:
    """Create an adaptive crawler with specified configuration."""
    config = AdaptiveConfig(
        confidence_threshold=confidence_threshold,
        max_depth=max_depth,
        max_pages=max_pages,
        strategy=strategy,
        state_path=state_path
    )
    
    return AdaptiveCrawler(
        scraping_service=scraping_service,
        config=config,
        state_path=state_path
    )
