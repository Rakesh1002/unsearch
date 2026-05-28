"""
Text chunking strategies for breaking down content into manageable pieces.

This module provides various strategies for chunking text content:
- RegexChunking: Split text using regular expressions
- SentenceChunking: Split by sentences using NLP
- TopicChunking: Segment by topics using statistical methods
- FixedSizeChunking: Split into fixed-size chunks
"""

import re
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from collections import Counter

import structlog

logger = structlog.get_logger(__name__)


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""
    
    @abstractmethod
    def chunk(self, text: str, **kwargs) -> List[str]:
        """
        Chunk the given text into smaller pieces.
        
        Args:
            text: The text to chunk
            **kwargs: Additional parameters for chunking
            
        Returns:
            List of text chunks
        """
        pass


class IdentityChunking(ChunkingStrategy):
    """Chunking strategy that returns the input text as a single chunk."""
    
    def chunk(self, text: str, **kwargs) -> List[str]:
        """Return text as single chunk."""
        return [text] if text.strip() else []


class RegexChunking(ChunkingStrategy):
    """
    Chunking strategy that splits text based on regular expression patterns.
    
    Supports multiple patterns that are applied sequentially to split text
    into increasingly smaller chunks.
    """
    
    def __init__(self, patterns: Optional[List[str]] = None, **kwargs):
        """
        Initialize regex chunking strategy.
        
        Args:
            patterns: List of regex patterns to split text
                     Default: [r"\n\n", r"\n", r"\. "]
        """
        self.patterns = patterns or [r"\n\n", r"\n", r"\. "]
        self.min_chunk_length = kwargs.get('min_chunk_length', 10)
        self.max_chunk_length = kwargs.get('max_chunk_length', 5000)
    
    def chunk(self, text: str, **kwargs) -> List[str]:
        """Split text using regex patterns."""
        if not text.strip():
            return []
        
        chunks = [text]
        
        # Apply each pattern sequentially
        for pattern in self.patterns:
            new_chunks = []
            for chunk in chunks:
                if len(chunk) > self.max_chunk_length:
                    # Split this chunk further
                    split_chunks = re.split(pattern, chunk)
                    new_chunks.extend([c.strip() for c in split_chunks if c.strip()])
                else:
                    new_chunks.append(chunk)
            chunks = new_chunks
        
        # Filter by minimum length
        filtered_chunks = [
            chunk for chunk in chunks 
            if len(chunk.strip()) >= self.min_chunk_length
        ]
        
        return filtered_chunks


class SentenceChunking(ChunkingStrategy):
    """
    Chunking strategy that splits text into sentences.
    
    Uses regex patterns to identify sentence boundaries, with support
    for common abbreviations and edge cases.
    """
    
    def __init__(self, **kwargs):
        """Initialize sentence chunking strategy."""
        self.min_sentence_length = kwargs.get('min_sentence_length', 10)
        self.merge_short_sentences = kwargs.get('merge_short_sentences', True)
        
        # Regex pattern for sentence splitting
        self.sentence_pattern = re.compile(
            r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<![A-Z][A-Z]\.)(?<=[.!?])\s+',
            re.MULTILINE
        )
    
    def chunk(self, text: str, **kwargs) -> List[str]:
        """Split text into sentences."""
        if not text.strip():
            return []
        
        # Split by sentence boundaries
        sentences = self.sentence_pattern.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Optionally merge short sentences
        if self.merge_short_sentences:
            sentences = self._merge_short_sentences(sentences)
        
        # Filter by minimum length
        return [s for s in sentences if len(s) >= self.min_sentence_length]
    
    def _merge_short_sentences(self, sentences: List[str]) -> List[str]:
        """Merge sentences that are too short with adjacent ones."""
        if not sentences:
            return []
        
        merged = []
        current = sentences[0]
        
        for i in range(1, len(sentences)):
            if len(current) < self.min_sentence_length * 2:
                # Merge with next sentence
                current += " " + sentences[i]
            else:
                merged.append(current)
                current = sentences[i]
        
        # Add the last sentence
        if current:
            merged.append(current)
        
        return merged


class ParagraphChunking(ChunkingStrategy):
    """
    Chunking strategy that splits text into paragraphs.
    
    Uses double newlines and other paragraph indicators to split text
    while preserving semantic boundaries.
    """
    
    def __init__(self, **kwargs):
        """Initialize paragraph chunking strategy."""
        self.min_paragraph_length = kwargs.get('min_paragraph_length', 50)
        self.max_paragraph_length = kwargs.get('max_paragraph_length', 2000)
    
    def chunk(self, text: str, **kwargs) -> List[str]:
        """Split text into paragraphs."""
        if not text.strip():
            return []
        
        # Split by paragraph indicators
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Handle overly long paragraphs
        processed_paragraphs = []
        for para in paragraphs:
            if len(para) > self.max_paragraph_length:
                # Split long paragraphs by sentences
                sentence_chunker = SentenceChunking(
                    min_sentence_length=self.min_paragraph_length // 2
                )
                sub_chunks = sentence_chunker.chunk(para)
                
                # Group sentences into paragraph-sized chunks
                current_chunk = ""
                for sentence in sub_chunks:
                    if len(current_chunk + sentence) <= self.max_paragraph_length:
                        current_chunk += " " + sentence if current_chunk else sentence
                    else:
                        if current_chunk:
                            processed_paragraphs.append(current_chunk)
                        current_chunk = sentence
                
                if current_chunk:
                    processed_paragraphs.append(current_chunk)
            else:
                processed_paragraphs.append(para)
        
        # Filter by minimum length
        return [p for p in processed_paragraphs if len(p) >= self.min_paragraph_length]


class FixedSizeChunking(ChunkingStrategy):
    """
    Chunking strategy that splits text into fixed-size chunks.
    
    Useful for handling token limits in LLMs or creating uniform
    chunks for processing.
    """
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 100, **kwargs):
        """
        Initialize fixed-size chunking strategy.
        
        Args:
            chunk_size: Target size for each chunk in characters
            overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.preserve_words = kwargs.get('preserve_words', True)
    
    def chunk(self, text: str, **kwargs) -> List[str]:
        """Split text into fixed-size chunks."""
        if not text.strip():
            return []
        
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))
            
            # If preserving words, adjust boundaries
            if self.preserve_words and end < len(text):
                # Find the last space before the cut-off
                space_pos = text.rfind(' ', start, end)
                if space_pos > start:
                    end = space_pos
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.overlap if end - self.overlap > start else end
        
        return chunks


class TopicChunking(ChunkingStrategy):
    """
    Advanced chunking strategy that attempts to segment text by topics.
    
    Uses statistical methods to identify topic boundaries and create
    semantically coherent chunks.
    """
    
    def __init__(self, window_size: int = 3, k: int = 10, **kwargs):
        """
        Initialize topic chunking strategy.
        
        Args:
            window_size: Size of sliding window for coherence calculation
            k: Number of top sentences to consider per window
        """
        self.window_size = window_size
        self.k = k
        self.min_chunk_length = kwargs.get('min_chunk_length', 100)
        self.similarity_threshold = kwargs.get('similarity_threshold', 0.3)
    
    def chunk(self, text: str, **kwargs) -> List[str]:
        """Split text into topic-based chunks."""
        if not text.strip():
            return []
        
        # First split into sentences
        sentence_chunker = SentenceChunking(min_sentence_length=20)
        sentences = sentence_chunker.chunk(text)
        
        if len(sentences) <= self.window_size:
            return [text]  # Too few sentences for topic segmentation
        
        # Calculate coherence scores between adjacent windows
        boundaries = self._find_topic_boundaries(sentences)
        
        # Create chunks based on boundaries
        chunks = []
        start_idx = 0
        
        for boundary in boundaries:
            chunk_sentences = sentences[start_idx:boundary]
            chunk_text = ' '.join(chunk_sentences)
            
            if len(chunk_text) >= self.min_chunk_length:
                chunks.append(chunk_text)
            elif chunks:
                # Merge with previous chunk if too small
                chunks[-1] += ' ' + chunk_text
            else:
                # First chunk is small, keep it anyway
                chunks.append(chunk_text)
            
            start_idx = boundary
        
        # Handle remaining sentences
        if start_idx < len(sentences):
            remaining = ' '.join(sentences[start_idx:])
            if remaining and len(remaining) >= self.min_chunk_length:
                chunks.append(remaining)
            elif chunks:
                chunks[-1] += ' ' + remaining
        
        return [c for c in chunks if c.strip()]
    
    def _find_topic_boundaries(self, sentences: List[str]) -> List[int]:
        """Find topic boundaries using coherence analysis."""
        if len(sentences) <= self.window_size * 2:
            return [len(sentences)]  # Not enough sentences for analysis
        
        # Calculate vocabulary for each window
        window_vocabs = []
        for i in range(len(sentences) - self.window_size + 1):
            window_text = ' '.join(sentences[i:i + self.window_size])
            vocab = self._extract_vocabulary(window_text)
            window_vocabs.append(vocab)
        
        # Calculate similarity between adjacent windows
        similarities = []
        for i in range(len(window_vocabs) - 1):
            sim = self._calculate_similarity(window_vocabs[i], window_vocabs[i + 1])
            similarities.append(sim)
        
        # Find local minima as topic boundaries
        boundaries = []
        for i in range(1, len(similarities) - 1):
            if (similarities[i] < similarities[i-1] and 
                similarities[i] < similarities[i+1] and 
                similarities[i] < self.similarity_threshold):
                # Boundary is at the end of the current window
                boundary_idx = i + self.window_size
                boundaries.append(boundary_idx)
        
        # Always add the end as a boundary
        boundaries.append(len(sentences))
        
        return boundaries
    
    def _extract_vocabulary(self, text: str) -> Dict[str, int]:
        """Extract vocabulary from text with basic preprocessing."""
        # Simple word extraction and counting
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out very short words and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        return Counter(words)
    
    def _calculate_similarity(self, vocab1: Dict[str, int], vocab2: Dict[str, int]) -> float:
        """Calculate cosine similarity between two vocabulary distributions."""
        # Get all unique words
        all_words = set(vocab1.keys()) | set(vocab2.keys())
        
        if not all_words:
            return 0.0
        
        # Create vectors
        vec1 = [vocab1.get(word, 0) for word in all_words]
        vec2 = [vocab2.get(word, 0) for word in all_words]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class HybridChunking(ChunkingStrategy):
    """
    Hybrid chunking strategy that combines multiple approaches.
    
    Uses a cascade of chunking strategies to create optimal chunks
    that balance semantic coherence with size constraints.
    """
    
    def __init__(
        self,
        primary_strategy: str = 'paragraph',
        fallback_strategy: str = 'sentence',
        target_size: int = 1000,
        max_size: int = 2000,
        min_size: int = 100,
        **kwargs
    ):
        """
        Initialize hybrid chunking strategy.
        
        Args:
            primary_strategy: Primary strategy to use ('paragraph', 'topic', 'sentence')
            fallback_strategy: Fallback if primary produces unsuitable chunks
            target_size: Target size for chunks
            max_size: Maximum allowable chunk size
            min_size: Minimum allowable chunk size
        """
        self.primary_strategy = primary_strategy
        self.fallback_strategy = fallback_strategy
        self.target_size = target_size
        self.max_size = max_size
        self.min_size = min_size
        
        # Initialize strategies
        self.strategies = {
            'paragraph': ParagraphChunking(
                min_paragraph_length=min_size,
                max_paragraph_length=max_size
            ),
            'topic': TopicChunking(
                min_chunk_length=min_size
            ),
            'sentence': SentenceChunking(
                min_sentence_length=min_size // 4
            ),
            'fixed': FixedSizeChunking(
                chunk_size=target_size,
                overlap=target_size // 10
            )
        }
    
    def chunk(self, text: str, **kwargs) -> List[str]:
        """Apply hybrid chunking strategy."""
        if not text.strip():
            return []
        
        # Try primary strategy
        primary_chunks = self.strategies[self.primary_strategy].chunk(text)
        
        # Evaluate chunks and refine if needed
        refined_chunks = []
        
        for chunk in primary_chunks:
            if self.min_size <= len(chunk) <= self.max_size:
                # Chunk is good size
                refined_chunks.append(chunk)
            elif len(chunk) > self.max_size:
                # Chunk too large - split further
                sub_chunks = self.strategies[self.fallback_strategy].chunk(chunk)
                
                # If still too large, use fixed-size chunking
                final_sub_chunks = []
                for sub_chunk in sub_chunks:
                    if len(sub_chunk) > self.max_size:
                        final_sub_chunks.extend(
                            self.strategies['fixed'].chunk(sub_chunk)
                        )
                    else:
                        final_sub_chunks.append(sub_chunk)
                
                refined_chunks.extend(final_sub_chunks)
            else:
                # Chunk too small - might merge with next or keep as is
                refined_chunks.append(chunk)
        
        # Final size optimization - merge small adjacent chunks
        optimized_chunks = self._merge_small_chunks(refined_chunks)
        
        return optimized_chunks
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """Merge small adjacent chunks to optimize sizes."""
        if not chunks:
            return []
        
        merged = []
        current = chunks[0]
        
        for i in range(1, len(chunks)):
            next_chunk = chunks[i]
            
            # If both current and next are small, merge them
            if (len(current) < self.target_size and 
                len(next_chunk) < self.target_size and 
                len(current + ' ' + next_chunk) <= self.max_size):
                current = current + ' ' + next_chunk
            else:
                merged.append(current)
                current = next_chunk
        
        # Add the last chunk
        merged.append(current)
        
        return merged


# Factory function for creating chunking strategies
def create_chunking_strategy(
    strategy_type: str,
    config: Optional[Dict[str, Any]] = None
) -> ChunkingStrategy:
    """
    Factory function to create chunking strategies.
    
    Args:
        strategy_type: Type of strategy ('identity', 'regex', 'sentence', 'paragraph', 
                      'fixed', 'topic', 'hybrid')
        config: Configuration dictionary for the strategy
        
    Returns:
        Configured chunking strategy instance
    """
    config = config or {}
    
    strategies = {
        'identity': IdentityChunking,
        'regex': RegexChunking,
        'sentence': SentenceChunking,
        'paragraph': ParagraphChunking,
        'fixed': FixedSizeChunking,
        'topic': TopicChunking,
        'hybrid': HybridChunking
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown chunking strategy: {strategy_type}. Available: {list(strategies.keys())}")
    
    strategy_class = strategies[strategy_type]
    return strategy_class(**config)


# Convenience functions
def chunk_text(
    text: str,
    strategy: str = 'paragraph',
    config: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Convenience function to chunk text using specified strategy.
    
    Args:
        text: Text to chunk
        strategy: Chunking strategy to use
        config: Strategy configuration
        
    Returns:
        List of text chunks
    """
    chunker = create_chunking_strategy(strategy, config)
    return chunker.chunk(text)


def smart_chunk_for_llm(
    text: str,
    max_tokens: int = 4000,
    overlap_tokens: int = 200,
    strategy: str = 'hybrid'
) -> List[str]:
    """
    Smart chunking optimized for LLM processing.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (roughly 4 chars per token)
        overlap_tokens: Tokens to overlap between chunks
        strategy: Primary chunking strategy
        
    Returns:
        List of text chunks optimized for LLM processing
    """
    # Rough conversion: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4
    
    if strategy == 'hybrid':
        chunker = HybridChunking(
            target_size=max_chars // 2,
            max_size=max_chars,
            min_size=100
        )
    else:
        chunker = create_chunking_strategy(strategy, {
            'chunk_size': max_chars,
            'overlap': overlap_chars
        })
    
    return chunker.chunk(text)
