"""
Relevance filtering and ranking service for search results.

Provides:
- Query intent detection (commercial, definitional, navigational, etc.)
- Result type classification (dictionary, news, commercial, reference)
- BM25-style relevance scoring
- Intent-based filtering to remove irrelevant results
- Optional AI reranking integration
"""
import re
import math
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse
import structlog

logger = structlog.get_logger(__name__)


class QueryIntent(str, Enum):
    """Detected intent of the search query."""
    COMMERCIAL = "commercial"      # Looking to buy/hire services
    DEFINITIONAL = "definitional"  # "What is X" questions
    NAVIGATIONAL = "navigational"  # Looking for specific site
    INFORMATIONAL = "informational"  # General information seeking
    LOCAL = "local"                # Location-based queries
    TUTORIAL = "tutorial"          # How-to, guides
    COMPARISON = "comparison"      # Comparing options
    NEWS = "news"                  # Current events


class ResultType(str, Enum):
    """Classification of search result type."""
    DICTIONARY = "dictionary"      # Dictionary/definition sites
    WIKIPEDIA = "wikipedia"        # Wikipedia/encyclopedias
    NEWS = "news"                  # News articles
    COMMERCIAL = "commercial"      # Business/e-commerce sites
    FORUM = "forum"                # Forums, Q&A sites
    BLOG = "blog"                  # Blog posts
    DOCUMENTATION = "documentation"  # Technical docs
    SOCIAL = "social"              # Social media
    VIDEO = "video"                # Video platforms
    ACADEMIC = "academic"          # Academic papers
    GOVERNMENT = "government"      # Government sites
    UNKNOWN = "unknown"


@dataclass
class RelevanceScore:
    """Relevance score breakdown for a result."""
    total: float = 0.0
    title_score: float = 0.0
    snippet_score: float = 0.0
    url_score: float = 0.0
    domain_authority: float = 0.0
    intent_match: float = 0.0
    freshness: float = 0.0


@dataclass
class QueryAnalysis:
    """Analysis of the search query."""
    intent: QueryIntent
    confidence: float
    keywords: List[str]
    location: Optional[str] = None
    is_question: bool = False
    expected_result_types: List[ResultType] = field(default_factory=list)


# Domain classifications
DICTIONARY_DOMAINS = {
    'dictionary.com', 'merriam-webster.com', 'cambridge.org',
    'oxford.com', 'oxfordlearnersdictionaries.com', 'thefreedictionary.com',
    'yourdictionary.com', 'vocabulary.com', 'wordnik.com', 'wiktionary.org',
    'collinsdictionary.com', 'macmillandictionary.com'
}

WIKIPEDIA_DOMAINS = {
    'wikipedia.org', 'britannica.com', 'encyclopedia.com',
    'wikiwand.com', 'simple.wikipedia.org'
}

NEWS_DOMAINS = {
    'bbc.com', 'cnn.com', 'reuters.com', 'apnews.com', 'nytimes.com',
    'theguardian.com', 'washingtonpost.com', 'forbes.com', 'bloomberg.com',
    'techcrunch.com', 'theverge.com', 'wired.com', 'arstechnica.com',
    'news.google.com', 'news.yahoo.com', 'hindustantimes.com', 
    'timesofindia.com', 'ndtv.com', 'indianexpress.com'
}

FORUM_DOMAINS = {
    'reddit.com', 'quora.com', 'stackoverflow.com', 'stackexchange.com',
    'discourse.org', 'answers.com', 'askubuntu.com'
}

VIDEO_DOMAINS = {
    'youtube.com', 'vimeo.com', 'dailymotion.com', 'twitch.tv'
}

SOCIAL_DOMAINS = {
    'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 
    'linkedin.com', 'pinterest.com', 'tiktok.com'
}

ACADEMIC_DOMAINS = {
    'arxiv.org', 'scholar.google.com', 'researchgate.net', 'academia.edu',
    'pubmed.ncbi.nlm.nih.gov', 'ieee.org', 'acm.org', 'sciencedirect.com'
}

# High authority domains (boost score)
HIGH_AUTHORITY_DOMAINS = {
    'github.com', 'stackoverflow.com', 'wikipedia.org', 'mozilla.org',
    'w3.org', 'python.org', 'nodejs.org', 'docs.microsoft.com',
    'developer.apple.com', 'developers.google.com', 'aws.amazon.com'
}

# Commercial intent signals
COMMERCIAL_KEYWORDS = {
    'buy', 'price', 'cost', 'shop', 'order', 'purchase', 'deal', 'discount',
    'cheap', 'affordable', 'best', 'top', 'review', 'compare', 'vs',
    'service', 'services', 'company', 'companies', 'provider', 'vendor',
    'hire', 'hiring', 'near me', 'in india', 'in delhi', 'in mumbai',
    'custom', 'printing', 'manufacturer', 'supplier', 'wholesale'
}

# Definitional intent signals
DEFINITIONAL_KEYWORDS = {
    'what is', 'what are', 'define', 'definition', 'meaning', 'means',
    'explain', 'description', 'overview', 'introduction', 'basics'
}

# Tutorial intent signals
TUTORIAL_KEYWORDS = {
    'how to', 'tutorial', 'guide', 'step by step', 'learn', 'example',
    'getting started', 'beginner', 'introduction to', 'walkthrough'
}

# Location indicators
LOCATION_PATTERNS = [
    r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',  # "in Delhi", "in New York"
    r'\bnear\s+(?:me|([A-Z][a-z]+))\b',  # "near me", "near Mumbai"
    r'\b([A-Z][a-z]+)\s+(?:based|located)\b',  # "Delhi based"
]


class RelevanceFilter:
    """
    Fast relevance filtering for search results.
    
    Designed to improve result quality without adding significant latency.
    Uses lightweight heuristics for speed, with optional AI reranking.
    """
    
    def __init__(
        self,
        min_relevance_score: float = 0.15,
        boost_commercial_for_commercial: float = 1.5,
        penalize_dictionary_for_commercial: float = 0.3,
        enable_intent_filtering: bool = True
    ):
        """
        Initialize relevance filter.
        
        Args:
            min_relevance_score: Minimum score to keep a result (0-1)
            boost_commercial_for_commercial: Boost factor for commercial results on commercial queries
            penalize_dictionary_for_commercial: Penalty factor for dictionary results on commercial queries
            enable_intent_filtering: Whether to filter based on query intent
        """
        self.min_relevance_score = min_relevance_score
        self.boost_commercial = boost_commercial_for_commercial
        self.penalize_dictionary = penalize_dictionary_for_commercial
        self.enable_intent_filtering = enable_intent_filtering
        
        # Pre-compile patterns for speed
        self._location_patterns = [re.compile(p, re.IGNORECASE) for p in LOCATION_PATTERNS]
        self._question_pattern = re.compile(r'^(what|how|why|when|where|who|which|can|does|is|are)\s', re.IGNORECASE)
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze query to detect intent and extract signals.
        
        Fast heuristic-based analysis (~0.1ms).
        """
        query_lower = query.lower()
        keywords = self._extract_keywords(query)
        
        # Detect location
        location = None
        for pattern in self._location_patterns:
            match = pattern.search(query)
            if match:
                location = match.group(1) if match.lastindex else "local"
                break
        
        # Check if question
        is_question = bool(self._question_pattern.match(query))
        
        # Detect intent with confidence
        intent, confidence = self._detect_intent(query_lower, keywords, location, is_question)
        
        # Determine expected result types
        expected_types = self._get_expected_result_types(intent)
        
        return QueryAnalysis(
            intent=intent,
            confidence=confidence,
            keywords=keywords,
            location=location,
            is_question=is_question,
            expected_result_types=expected_types
        )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query."""
        # Remove common stopwords
        stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                    'through', 'during', 'before', 'after', 'above', 'below',
                    'between', 'under', 'again', 'further', 'then', 'once',
                    'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                    'neither', 'not', 'only', 'own', 'same', 'than', 'too',
                    'very', 'just', 'also', 'now', 'here', 'there', 'when',
                    'where', 'why', 'how', 'all', 'each', 'every', 'both',
                    'few', 'more', 'most', 'other', 'some', 'such', 'no',
                    'any', 'i', 'me', 'my', 'we', 'our', 'you', 'your', 'it'}
        
        words = re.findall(r'\b[a-zA-Z]{2,}\b', query.lower())
        return [w for w in words if w not in stopwords]
    
    def _detect_intent(
        self, 
        query_lower: str, 
        keywords: List[str],
        location: Optional[str],
        is_question: bool
    ) -> Tuple[QueryIntent, float]:
        """Detect query intent with confidence score."""
        
        # Check for definitional queries first
        for signal in DEFINITIONAL_KEYWORDS:
            if signal in query_lower:
                return QueryIntent.DEFINITIONAL, 0.9
        
        # Check for tutorial/how-to
        for signal in TUTORIAL_KEYWORDS:
            if signal in query_lower:
                return QueryIntent.TUTORIAL, 0.85
        
        # Check for commercial intent
        commercial_signals = sum(1 for kw in COMMERCIAL_KEYWORDS if kw in query_lower)
        if commercial_signals >= 2 or (commercial_signals >= 1 and location):
            return QueryIntent.COMMERCIAL, min(0.9, 0.5 + commercial_signals * 0.15)
        
        # Location-based queries are often commercial or local
        if location:
            return QueryIntent.LOCAL, 0.75
        
        # Check for comparison queries
        if any(w in query_lower for w in ['vs', 'versus', 'compare', 'comparison', 'better', 'best']):
            return QueryIntent.COMPARISON, 0.8
        
        # Check for news-related
        if any(w in query_lower for w in ['news', 'latest', 'recent', 'today', 'update']):
            return QueryIntent.NEWS, 0.75
        
        # Default to informational
        return QueryIntent.INFORMATIONAL, 0.5
    
    def _get_expected_result_types(self, intent: QueryIntent) -> List[ResultType]:
        """Get expected result types for an intent."""
        mapping = {
            QueryIntent.COMMERCIAL: [ResultType.COMMERCIAL, ResultType.FORUM, ResultType.NEWS],
            QueryIntent.DEFINITIONAL: [ResultType.WIKIPEDIA, ResultType.DICTIONARY, ResultType.DOCUMENTATION],
            QueryIntent.NAVIGATIONAL: [ResultType.COMMERCIAL, ResultType.DOCUMENTATION],
            QueryIntent.INFORMATIONAL: [ResultType.WIKIPEDIA, ResultType.BLOG, ResultType.DOCUMENTATION, ResultType.FORUM],
            QueryIntent.LOCAL: [ResultType.COMMERCIAL, ResultType.NEWS],
            QueryIntent.TUTORIAL: [ResultType.BLOG, ResultType.DOCUMENTATION, ResultType.VIDEO, ResultType.FORUM],
            QueryIntent.COMPARISON: [ResultType.BLOG, ResultType.FORUM, ResultType.NEWS],
            QueryIntent.NEWS: [ResultType.NEWS, ResultType.BLOG],
        }
        return mapping.get(intent, [ResultType.UNKNOWN])
    
    def classify_result(self, url: str, title: str, snippet: str) -> ResultType:
        """
        Classify a search result by type based on URL and content.
        
        Fast domain-based classification (~0.05ms).
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
        except Exception:
            return ResultType.UNKNOWN
        
        # Check against known domain sets
        for known_domain in DICTIONARY_DOMAINS:
            if known_domain in domain:
                return ResultType.DICTIONARY
        
        for known_domain in WIKIPEDIA_DOMAINS:
            if known_domain in domain:
                return ResultType.WIKIPEDIA
        
        for known_domain in NEWS_DOMAINS:
            if known_domain in domain:
                return ResultType.NEWS
        
        for known_domain in FORUM_DOMAINS:
            if known_domain in domain:
                return ResultType.FORUM
        
        for known_domain in VIDEO_DOMAINS:
            if known_domain in domain:
                return ResultType.VIDEO
        
        for known_domain in SOCIAL_DOMAINS:
            if known_domain in domain:
                return ResultType.SOCIAL
        
        for known_domain in ACADEMIC_DOMAINS:
            if known_domain in domain:
                return ResultType.ACADEMIC
        
        # Check for government domains
        if domain.endswith('.gov') or domain.endswith('.gov.in'):
            return ResultType.GOVERNMENT
        
        # Content-based classification for unknown domains
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        
        # Check for blog indicators
        if any(ind in domain for ind in ['blog', 'medium.com', 'dev.to', 'hashnode']):
            return ResultType.BLOG
        
        # Check for documentation
        if any(ind in domain for ind in ['docs.', 'documentation', 'readme', 'wiki.']):
            return ResultType.DOCUMENTATION
        
        # Check content for definition patterns
        if any(p in snippet_lower for p in ['definition:', 'meaning:', 'noun.', 'verb.', 'adjective.']):
            return ResultType.DICTIONARY
        
        # Default to commercial for business-looking domains
        if any(ext in domain for ext in ['.com', '.co.in', '.in', '.io', '.co']):
            # Check if it looks like a business
            if any(w in title_lower for w in ['services', 'products', 'shop', 'buy', 'order', 'pricing', 'custom', 'print', 'tshirt', 't-shirt']):
                return ResultType.COMMERCIAL
            # Check snippet for commercial indicators
            if any(w in snippet_lower for w in ['order', 'buy', 'price', 'delivery', 'shipping', 'free', 'discount', 'off', 'custom', 'design']):
                return ResultType.COMMERCIAL
        
        return ResultType.UNKNOWN
    
    def calculate_relevance(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        url: str,
        title: str,
        snippet: str,
        result_type: ResultType,
        position: int
    ) -> RelevanceScore:
        """
        Calculate relevance score for a single result.
        
        Fast BM25-inspired scoring (~0.2ms per result).
        """
        score = RelevanceScore()
        keywords = query_analysis.keywords
        
        if not keywords:
            keywords = self._extract_keywords(query)
        
        # Title score (0-0.35)
        title_lower = title.lower()
        title_matches = sum(1 for kw in keywords if kw in title_lower)
        score.title_score = min(0.35, (title_matches / max(len(keywords), 1)) * 0.35)
        
        # Snippet score (0-0.35)
        snippet_lower = snippet.lower()
        snippet_matches = sum(1 for kw in keywords if kw in snippet_lower)
        # Bonus for phrase match
        query_lower = query.lower()
        phrase_bonus = 0.1 if query_lower in snippet_lower else 0
        score.snippet_score = min(0.35, (snippet_matches / max(len(keywords), 1)) * 0.25 + phrase_bonus)
        
        # URL score (0-0.1)
        url_lower = url.lower()
        url_matches = sum(1 for kw in keywords if kw in url_lower)
        score.url_score = min(0.1, url_matches * 0.03)
        
        # Domain authority (0-0.1)
        try:
            domain = urlparse(url).netloc.lower()
            if any(d in domain for d in HIGH_AUTHORITY_DOMAINS):
                score.domain_authority = 0.1
            elif result_type in [ResultType.WIKIPEDIA, ResultType.DOCUMENTATION, ResultType.ACADEMIC]:
                score.domain_authority = 0.08
            elif result_type == ResultType.NEWS:
                score.domain_authority = 0.05
        except Exception:
            pass
        
        # Intent match score (0-0.15, can be negative for mismatches)
        score.intent_match = self._calculate_intent_match(
            query_analysis.intent, 
            result_type,
            query_analysis.expected_result_types
        )
        
        # Position decay (slight preference for original ranking)
        position_factor = 1.0 - (position * 0.01)  # 1% decay per position
        
        # Calculate total
        base_score = (
            score.title_score + 
            score.snippet_score + 
            score.url_score + 
            score.domain_authority + 
            score.intent_match
        )
        score.total = max(0, min(1.0, base_score * position_factor))
        
        return score
    
    def _calculate_intent_match(
        self,
        intent: QueryIntent,
        result_type: ResultType,
        expected_types: List[ResultType]
    ) -> float:
        """Calculate intent match score."""
        
        # Strong match with expected types
        if result_type in expected_types:
            return 0.15
        
        # Penalize dictionary results for commercial queries
        if intent == QueryIntent.COMMERCIAL and result_type == ResultType.DICTIONARY:
            return -0.2  # Strong penalty
        
        # Penalize dictionary for local queries
        if intent == QueryIntent.LOCAL and result_type == ResultType.DICTIONARY:
            return -0.2
        
        # Penalize dictionary for tutorial queries
        if intent == QueryIntent.TUTORIAL and result_type == ResultType.DICTIONARY:
            return -0.15
        
        # Slight penalty for Wikipedia on commercial queries
        if intent == QueryIntent.COMMERCIAL and result_type == ResultType.WIKIPEDIA:
            return -0.05
        
        # Neutral for unknown or unclassified
        return 0.0
    
    def filter_and_rank(
        self,
        query: str,
        results: List[Dict],
        max_results: int = 10,
        query_analysis: Optional[QueryAnalysis] = None
    ) -> List[Dict]:
        """
        Filter and rank search results by relevance.
        
        Main entry point for relevance filtering.
        Designed to be fast (<5ms for 20 results).
        
        Args:
            query: Original search query
            results: List of search results with 'url', 'title', 'snippet' keys
            max_results: Maximum results to return
            query_analysis: Pre-computed query analysis (optional)
            
        Returns:
            Filtered and re-ranked results with relevance scores
        """
        if not results:
            return []
        
        # Analyze query if not provided
        if query_analysis is None:
            query_analysis = self.analyze_query(query)
        
        logger.debug(
            "relevance_filter_start",
            query=query,
            intent=query_analysis.intent.value,
            intent_confidence=query_analysis.confidence,
            input_count=len(results)
        )
        
        scored_results = []
        
        for idx, result in enumerate(results):
            url = result.get('url', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Classify result type
            result_type = self.classify_result(url, title, snippet)
            
            # Calculate relevance score
            relevance = self.calculate_relevance(
                query=query,
                query_analysis=query_analysis,
                url=url,
                title=title,
                snippet=snippet,
                result_type=result_type,
                position=idx
            )
            
            # Apply intent-based filtering
            if self.enable_intent_filtering:
                # Skip results below minimum score
                if relevance.total < self.min_relevance_score:
                    logger.debug(
                        "relevance_filter_skip",
                        url=url,
                        score=relevance.total,
                        result_type=result_type.value,
                        reason="below_threshold"
                    )
                    continue
                
                # Skip dictionary results for commercial/local queries
                if (query_analysis.intent in [QueryIntent.COMMERCIAL, QueryIntent.LOCAL] and
                    result_type == ResultType.DICTIONARY):
                    logger.debug(
                        "relevance_filter_skip",
                        url=url,
                        score=relevance.total,
                        result_type=result_type.value,
                        reason="dictionary_for_commercial"
                    )
                    continue
            
            # Add metadata to result
            result_copy = result.copy()
            result_copy['_relevance_score'] = relevance.total
            result_copy['_result_type'] = result_type.value
            result_copy['_intent_match'] = relevance.intent_match
            result_copy['_score_breakdown'] = {
                'title': relevance.title_score,
                'snippet': relevance.snippet_score,
                'url': relevance.url_score,
                'authority': relevance.domain_authority,
                'intent': relevance.intent_match
            }
            
            scored_results.append(result_copy)
        
        # Sort by relevance score (descending)
        scored_results.sort(key=lambda x: x['_relevance_score'], reverse=True)
        
        # Limit to max_results
        final_results = scored_results[:max_results]
        
        logger.info(
            "relevance_filter_complete",
            query=query,
            intent=query_analysis.intent.value,
            input_count=len(results),
            output_count=len(final_results),
            filtered_count=len(results) - len(scored_results)
        )
        
        return final_results
    
    def quick_filter(
        self,
        query: str,
        results: List[Dict],
        max_results: int = 10
    ) -> List[Dict]:
        """
        Ultra-fast filtering without full scoring.
        
        Use for high-volume scenarios where speed is critical.
        Only removes obviously irrelevant results (<1ms).
        """
        if not results:
            return []
        
        query_analysis = self.analyze_query(query)
        
        # For definitional queries, keep as-is (dictionary results are expected)
        if query_analysis.intent == QueryIntent.DEFINITIONAL:
            return results[:max_results]
        
        filtered = []
        for result in results:
            url = result.get('url', '')
            result_type = self.classify_result(url, result.get('title', ''), result.get('snippet', ''))
            
            # Only filter out dictionary results for non-definitional queries
            if result_type == ResultType.DICTIONARY:
                if query_analysis.intent in [QueryIntent.COMMERCIAL, QueryIntent.LOCAL, QueryIntent.TUTORIAL]:
                    continue
            
            filtered.append(result)
            
            if len(filtered) >= max_results:
                break
        
        return filtered


# Singleton instance
_relevance_filter: Optional[RelevanceFilter] = None


def get_relevance_filter() -> RelevanceFilter:
    """Get or create relevance filter instance."""
    global _relevance_filter
    if _relevance_filter is None:
        _relevance_filter = RelevanceFilter()
    return _relevance_filter
