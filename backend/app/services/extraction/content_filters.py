"""
Advanced content filtering strategies inspired by crawl4ai.

This module implements sophisticated content filtering for relevance and quality:
- BM25ContentFilter: Information retrieval-based filtering using BM25 algorithm
- PruningContentFilter: Removes irrelevant content based on thresholds
- LLMContentFilter: AI-powered content relevance filtering
- NoContentFilter: Pass-through filter for no filtering
"""

import asyncio
import math
import re
import json
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional, Set, Any
from collections import deque, Counter, defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path

import numpy as np
from bs4 import BeautifulSoup, Tag, NavigableString, Comment
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import structlog

from app.utils.text_processing import sanitize_text, clean_tokens

logger = structlog.get_logger(__name__)


@dataclass 
class FilterResult:
    """Result of content filtering operation."""
    filtered_content: str
    original_length: int
    filtered_length: int
    relevance_score: float
    filter_metadata: Dict[str, Any]


class RelevantContentFilter(ABC):
    """Abstract base class for content filtering strategies."""

    def __init__(
        self,
        user_query: Optional[str] = None,
        verbose: bool = False,
        **kwargs
    ):
        """
        Initialize content filter.

        Args:
            user_query: User query for relevance filtering (optional)
            verbose: Enable verbose logging
            **kwargs: Additional filter-specific parameters
        """
        self.user_query = user_query
        self.verbose = verbose
        
        # Tags to include in content filtering
        self.included_tags = {
            # Primary structure
            "article", "main", "section", "div",
            # List structures  
            "ul", "ol", "li", "dl", "dt", "dd",
            # Text content
            "p", "span", "blockquote", "pre", "code",
            # Headers
            "h1", "h2", "h3", "h4", "h5", "h6",
            # Tables
            "table", "thead", "tbody", "tr", "td", "th",
            # Other semantic elements
            "figure", "figcaption", "details", "summary",
            # Text formatting
            "em", "strong", "b", "i", "mark", "small",
            # Rich content
            "time", "address", "cite", "q"
        }
        
        # Tags to exclude from content filtering
        self.excluded_tags = {
            "script", "style", "noscript", "nav", "footer", 
            "header", "aside", "form", "button", "input"
        }

    @abstractmethod
    async def filter(self, html_content: str, **kwargs) -> FilterResult:
        """
        Filter HTML content based on relevance.
        
        Args:
            html_content: Raw HTML content to filter
            **kwargs: Additional filtering parameters
            
        Returns:
            FilterResult with filtered content and metadata
        """
        pass

    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML and clean unwanted elements."""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove excluded tags
        for tag in self.excluded_tags:
            for element in soup.find_all(tag):
                element.decompose()
                
        return soup

    def _extract_text_blocks(self, soup: BeautifulSoup) -> List[Tuple[Tag, str, int]]:
        """Extract text blocks with their elements and scores."""
        text_blocks = []
        
        for element in soup.find_all(self.included_tags):
            if self._should_include_element(element):
                text = sanitize_text(element.get_text())
                if text and len(text.split()) >= 3:  # Minimum word threshold
                    score = self._calculate_element_score(element)
                    text_blocks.append((element, text, score))
        
        return text_blocks

    def _should_include_element(self, element: Tag) -> bool:
        """Determine if element should be included in filtering."""
        # Skip if element is too nested in unimportant containers
        parent_chain = []
        current = element.parent
        while current and len(parent_chain) < 5:
            if current.name:
                parent_chain.append(current.name)
            current = current.parent
            
        # Skip if too many div layers (likely layout)
        if parent_chain.count('div') > 3:
            return False
            
        # Include if has important semantic meaning
        if element.name in ['article', 'main', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return True
            
        # Include if has meaningful text content
        text = element.get_text().strip()
        return len(text) > 20 and len(text.split()) >= 5

    def _calculate_element_score(self, element: Tag) -> int:
        """Calculate relevance score for HTML element."""
        score = 0
        
        # Tag-based scoring
        tag_scores = {
            'h1': 10, 'h2': 8, 'h3': 6, 'h4': 4, 'h5': 2, 'h6': 1,
            'article': 8, 'main': 8, 'section': 6,
            'p': 3, 'div': 1, 'span': 1,
            'li': 2, 'td': 2, 'th': 3,
            'strong': 2, 'em': 1, 'b': 2, 'i': 1
        }
        score += tag_scores.get(element.name, 0)
        
        # Class and ID based scoring
        classes = element.get('class', [])
        element_id = element.get('id', '')
        
        content_indicators = [
            'content', 'article', 'main', 'body', 'text',
            'post', 'entry', 'story', 'news', 'blog'
        ]
        
        for indicator in content_indicators:
            if any(indicator in cls.lower() for cls in classes):
                score += 3
            if indicator in element_id.lower():
                score += 3
                
        return score


class NoContentFilter(RelevantContentFilter):
    """Pass-through filter that doesn't modify content."""

    async def filter(self, html_content: str, **kwargs) -> FilterResult:
        """Return content without filtering."""
        soup = self._parse_html(html_content)
        filtered_content = str(soup)
        
        return FilterResult(
            filtered_content=filtered_content,
            original_length=len(html_content),
            filtered_length=len(filtered_content),
            relevance_score=1.0,
            filter_metadata={"filter_type": "none"}
        )


class PruningContentFilter(RelevantContentFilter):
    """
    Remove irrelevant content based on configurable thresholds.
    
    This filter removes elements that don't meet minimum thresholds for:
    - Word count
    - Relevance score
    - Content density
    """

    def __init__(
        self,
        threshold: float = 0.48,
        threshold_type: str = "fixed",
        min_word_threshold: int = 0,
        **kwargs
    ):
        """
        Initialize pruning filter.
        
        Args:
            threshold: Minimum relevance threshold (0.0 to 1.0)
            threshold_type: Type of threshold ("fixed", "adaptive")
            min_word_threshold: Minimum word count per element
        """
        super().__init__(**kwargs)
        self.threshold = threshold
        self.threshold_type = threshold_type
        self.min_word_threshold = min_word_threshold

    async def filter(self, html_content: str, **kwargs) -> FilterResult:
        """Filter content by removing low-relevance elements."""
        soup = self._parse_html(html_content)
        text_blocks = self._extract_text_blocks(soup)
        
        if not text_blocks:
            return FilterResult(
                filtered_content=html_content,
                original_length=len(html_content),
                filtered_length=len(html_content),
                relevance_score=0.0,
                filter_metadata={"filter_type": "pruning", "blocks_found": 0}
            )

        # Calculate adaptive threshold if needed
        if self.threshold_type == "adaptive":
            scores = [score for _, _, score in text_blocks]
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            adaptive_threshold = max(self.threshold, mean_score - 0.5 * std_score)
        else:
            adaptive_threshold = self.threshold

        # Filter elements based on thresholds
        filtered_elements = []
        total_score = 0
        
        for element, text, score in text_blocks:
            word_count = len(text.split())
            
            # Apply thresholds
            normalized_score = score / 10.0  # Normalize to 0-1 range
            
            if (normalized_score >= adaptive_threshold and 
                word_count >= self.min_word_threshold):
                filtered_elements.append(element)
                total_score += score

        # Rebuild HTML with filtered elements
        if filtered_elements:
            # Create new soup with filtered content
            new_soup = BeautifulSoup('<div class="filtered-content"></div>', 'lxml')
            container = new_soup.find('div', class_='filtered-content')
            
            for element in filtered_elements:
                # Clone element to avoid modifying original
                cloned = BeautifulSoup(str(element), 'lxml').body.contents[0]
                container.append(cloned)
                
            filtered_content = str(new_soup)
        else:
            # If nothing passes threshold, return original
            filtered_content = html_content

        # Calculate relevance score
        relevance_score = min(1.0, total_score / (len(text_blocks) * 10.0)) if text_blocks else 0.0

        return FilterResult(
            filtered_content=filtered_content,
            original_length=len(html_content),
            filtered_length=len(filtered_content),
            relevance_score=relevance_score,
            filter_metadata={
                "filter_type": "pruning",
                "threshold": adaptive_threshold,
                "blocks_original": len(text_blocks),
                "blocks_filtered": len(filtered_elements),
                "total_score": total_score
            }
        )


class BM25ContentFilter(RelevantContentFilter):
    """
    Information retrieval-based filtering using BM25 algorithm.
    
    This filter ranks content blocks by relevance to a user query using
    the BM25 scoring algorithm, commonly used in search engines.
    """

    def __init__(
        self,
        user_query: str,
        bm25_threshold: float = 1.0,
        top_k: int = 10,
        **kwargs
    ):
        """
        Initialize BM25 filter.
        
        Args:
            user_query: Query to filter content against
            bm25_threshold: Minimum BM25 score threshold
            top_k: Maximum number of top-scoring blocks to include
        """
        super().__init__(user_query=user_query, **kwargs)
        self.bm25_threshold = bm25_threshold
        self.top_k = top_k
        
        if not user_query:
            raise ValueError("user_query is required for BM25ContentFilter")

    async def filter(self, html_content: str, **kwargs) -> FilterResult:
        """Filter content using BM25 relevance scoring."""
        soup = self._parse_html(html_content)
        text_blocks = self._extract_text_blocks(soup)
        
        if not text_blocks:
            return FilterResult(
                filtered_content=html_content,
                original_length=len(html_content),
                filtered_length=len(html_content),
                relevance_score=0.0,
                filter_metadata={"filter_type": "bm25", "blocks_found": 0}
            )

        # Prepare documents for BM25
        documents = []
        elements = []
        
        for element, text, _ in text_blocks:
            # Tokenize and clean text
            tokens = clean_tokens(text.lower().split())
            if tokens:
                documents.append(tokens)
                elements.append(element)

        if not documents:
            return FilterResult(
                filtered_content=html_content,
                original_length=len(html_content),
                filtered_length=len(html_content),
                relevance_score=0.0,
                filter_metadata={"filter_type": "bm25", "documents": 0}
            )

        # Initialize BM25
        bm25 = BM25Okapi(documents)
        
        # Query tokenization
        query_tokens = clean_tokens(self.user_query.lower().split())
        
        # Get BM25 scores
        bm25_scores = bm25.get_scores(query_tokens)
        
        # Combine elements with scores
        scored_elements = list(zip(elements, bm25_scores))
        
        # Filter by threshold and sort by score
        filtered_scored = [
            (element, score) for element, score in scored_elements 
            if score >= self.bm25_threshold
        ]
        filtered_scored.sort(key=lambda x: x[1], reverse=True)
        
        # Take top-k elements
        top_elements = filtered_scored[:self.top_k]
        
        if top_elements:
            # Rebuild HTML with top elements in order of appearance
            element_scores = {id(elem): score for elem, score in top_elements}
            top_element_set = {id(elem) for elem, _ in top_elements}
            
            # Create filtered soup maintaining document order
            new_soup = BeautifulSoup('<div class="bm25-filtered-content"></div>', 'lxml')
            container = new_soup.find('div', class_='bm25-filtered-content')
            
            for element, _, _ in text_blocks:
                if id(element) in top_element_set:
                    cloned = BeautifulSoup(str(element), 'lxml').body.contents[0]
                    container.append(cloned)
            
            filtered_content = str(new_soup)
            
            # Calculate average relevance score
            avg_score = np.mean([score for _, score in top_elements])
            relevance_score = min(1.0, avg_score / 10.0)  # Normalize BM25 score
        else:
            filtered_content = html_content
            relevance_score = 0.0

        return FilterResult(
            filtered_content=filtered_content,
            original_length=len(html_content),
            filtered_length=len(filtered_content),
            relevance_score=relevance_score,
            filter_metadata={
                "filter_type": "bm25",
                "query": self.user_query,
                "threshold": self.bm25_threshold,
                "blocks_original": len(text_blocks),
                "blocks_filtered": len(top_elements),
                "top_k": self.top_k,
                "scores": [score for _, score in top_elements[:5]]  # Top 5 scores
            }
        )


class LLMContentFilter(RelevantContentFilter):
    """
    AI-powered content relevance filtering using language models.
    
    This filter uses LLMs to determine content relevance based on:
    - Natural language understanding
    - Contextual relevance
    - Query matching
    """

    def __init__(
        self,
        user_query: str,
        llm_config: Optional[Dict[str, Any]] = None,
        relevance_threshold: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ):
        """
        Initialize LLM content filter.
        
        Args:
            user_query: Query to filter content against
            llm_config: Configuration for LLM provider
            relevance_threshold: Minimum relevance threshold (0.0 to 1.0)
            max_tokens: Maximum tokens to send to LLM
        """
        super().__init__(user_query=user_query, **kwargs)
        self.llm_config = llm_config or {}
        self.relevance_threshold = relevance_threshold
        self.max_tokens = max_tokens
        
        if not user_query:
            raise ValueError("user_query is required for LLMContentFilter")

    async def filter(self, html_content: str, **kwargs) -> FilterResult:
        """Filter content using LLM relevance assessment."""
        soup = self._parse_html(html_content)
        text_blocks = self._extract_text_blocks(soup)
        
        if not text_blocks:
            return FilterResult(
                filtered_content=html_content,
                original_length=len(html_content),
                filtered_length=len(html_content),
                relevance_score=0.0,
                filter_metadata={"filter_type": "llm", "blocks_found": 0}
            )

        # Prepare content for LLM assessment
        block_texts = [(element, text) for element, text, _ in text_blocks]
        
        # Truncate if too long for LLM context
        total_chars = sum(len(text) for _, text in block_texts)
        if total_chars > self.max_tokens * 4:  # Rough char to token ratio
            # Keep most important blocks first
            sorted_blocks = sorted(
                [(element, text, self._calculate_element_score(element)) 
                 for element, text, _ in text_blocks],
                key=lambda x: x[2], reverse=True
            )
            
            current_chars = 0
            truncated_blocks = []
            for element, text, score in sorted_blocks:
                if current_chars + len(text) <= self.max_tokens * 4:
                    truncated_blocks.append((element, text))
                    current_chars += len(text)
                else:
                    break
            block_texts = truncated_blocks

        # Assess relevance using LLM (mock implementation)
        relevance_scores = await self._assess_relevance_with_llm(block_texts)
        
        # Filter blocks by relevance threshold
        filtered_elements = []
        total_relevance = 0
        
        for (element, text), relevance in zip(block_texts, relevance_scores):
            if relevance >= self.relevance_threshold:
                filtered_elements.append(element)
                total_relevance += relevance

        # Rebuild HTML with relevant elements
        if filtered_elements:
            new_soup = BeautifulSoup('<div class="llm-filtered-content"></div>', 'lxml')
            container = new_soup.find('div', class_='llm-filtered-content')
            
            for element in filtered_elements:
                cloned = BeautifulSoup(str(element), 'lxml').body.contents[0]
                container.append(cloned)
                
            filtered_content = str(new_soup)
            avg_relevance = total_relevance / len(filtered_elements)
        else:
            filtered_content = html_content
            avg_relevance = 0.0

        return FilterResult(
            filtered_content=filtered_content,
            original_length=len(html_content),
            filtered_length=len(filtered_content),
            relevance_score=avg_relevance,
            filter_metadata={
                "filter_type": "llm",
                "query": self.user_query,
                "threshold": self.relevance_threshold,
                "blocks_original": len(text_blocks),
                "blocks_assessed": len(block_texts),
                "blocks_filtered": len(filtered_elements),
                "avg_relevance": avg_relevance
            }
        )

    async def _assess_relevance_with_llm(
        self, 
        block_texts: List[Tuple[Tag, str]]
    ) -> List[float]:
        """
        Assess content relevance using LLM.
        
        Note: This is a mock implementation. In production, integrate with
        actual LLM providers like OpenAI, Anthropic, etc.
        """
        # Mock implementation - simulate LLM assessment
        await asyncio.sleep(0.2)  # Simulate API call delay
        
        relevance_scores = []
        query_words = set(self.user_query.lower().split())
        
        for element, text in block_texts:
            # Simple keyword-based mock scoring
            text_words = set(text.lower().split())
            overlap = len(query_words.intersection(text_words))
            max_overlap = len(query_words)
            
            # Mock relevance score based on keyword overlap
            if max_overlap > 0:
                base_score = overlap / max_overlap
                # Add some randomness to simulate LLM assessment
                import random
                random.seed(hash(text[:50]))  # Deterministic randomness
                score = min(1.0, base_score + random.uniform(-0.2, 0.3))
            else:
                score = 0.1
                
            relevance_scores.append(max(0.0, score))
        
        return relevance_scores


# Factory function for creating content filters
def create_content_filter(
    filter_type: str,
    config: Dict[str, Any]
) -> RelevantContentFilter:
    """
    Factory function to create content filters.
    
    Args:
        filter_type: Type of filter ("pruning", "bm25", "llm", "none")
        config: Configuration dictionary for the filter
        
    Returns:
        Configured content filter instance
    """
    filters = {
        "pruning": PruningContentFilter,
        "bm25": BM25ContentFilter, 
        "llm": LLMContentFilter,
        "none": NoContentFilter
    }
    
    if filter_type not in filters:
        raise ValueError(f"Unknown filter type: {filter_type}. Available: {list(filters.keys())}")
    
    filter_class = filters[filter_type]
    return filter_class(**config)


# Convenience functions for common filtering patterns
async def filter_with_bm25(
    html_content: str,
    user_query: str,
    bm25_threshold: float = 1.0,
    top_k: int = 10
) -> FilterResult:
    """Filter content using BM25 algorithm."""
    filter_instance = BM25ContentFilter(
        user_query=user_query,
        bm25_threshold=bm25_threshold,
        top_k=top_k
    )
    return await filter_instance.filter(html_content)


async def filter_with_pruning(
    html_content: str,
    threshold: float = 0.48,
    min_word_threshold: int = 0
) -> FilterResult:
    """Filter content using pruning strategy."""
    filter_instance = PruningContentFilter(
        threshold=threshold,
        min_word_threshold=min_word_threshold
    )
    return await filter_instance.filter(html_content)


async def filter_with_llm(
    html_content: str,
    user_query: str,
    relevance_threshold: float = 0.7
) -> FilterResult:
    """Filter content using LLM assessment."""
    filter_instance = LLMContentFilter(
        user_query=user_query,
        relevance_threshold=relevance_threshold
    )
    return await filter_instance.filter(html_content)
