"""
Advanced content extraction strategies inspired by crawl4ai.

This module implements sophisticated extraction strategies for different use cases:
- LLMExtractionStrategy: AI-powered structured data extraction
- CosineStrategy: Semantic similarity clustering for content extraction
- JsonCssExtractionStrategy: Advanced CSS/XPath extraction with schema
- RegexExtractionStrategy: Pattern-based extraction
- NoExtractionStrategy: Simple pass-through strategy
"""

import asyncio
import json
import re
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Pattern, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
import numpy as np
from bs4 import BeautifulSoup
from lxml import html, etree
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
import structlog

from app.utils.text_processing import sanitize_text, clean_tokens
from app.models.responses import ExtractedContent, ExtractionMetadata

logger = structlog.get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage tracking for LLM operations."""
    completion_tokens: int = 0
    prompt_tokens: int = 0
    total_tokens: int = 0
    completion_tokens_details: Optional[dict] = None
    prompt_tokens_details: Optional[dict] = None


class ExtractionStrategy(ABC):
    """Abstract base class for all extraction strategies."""

    def __init__(self, input_format: str = "markdown", **kwargs):
        """
        Initialize the extraction strategy.

        Args:
            input_format: Content format to use for extraction.
                         Options: "markdown" (default), "html", "fit_markdown"
            **kwargs: Additional keyword arguments
        """
        self.input_format = input_format
        self.name = self.__class__.__name__
        self.verbose = kwargs.get("verbose", False)

    @abstractmethod
    async def extract(self, url: str, html: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract meaningful blocks or chunks from the given HTML.

        Args:
            url: The URL of the webpage.
            html: The HTML content of the webpage.
            **kwargs: Additional extraction parameters.
            
        Returns:
            A list of extracted blocks or chunks.
        """
        pass

    async def run(self, url: str, sections: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Process sections of text in parallel.

        Args:
            url: The URL of the webpage.
            sections: List of sections (strings) to process.
            **kwargs: Additional extraction parameters.
            
        Returns:
            A list of processed JSON blocks.
        """
        extracted_content = []
        
        # Use ThreadPoolExecutor for CPU-bound operations
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, self.extract_sync, url, section, **kwargs)
                for section in sections
            ]
            
            for future in asyncio.as_completed(futures):
                try:
                    result = await future
                    extracted_content.extend(result)
                except Exception as e:
                    logger.error("extraction_section_failed", error=str(e))
                    
        return extracted_content

    def extract_sync(self, url: str, html: str, **kwargs) -> List[Dict[str, Any]]:
        """Synchronous wrapper for extract method."""
        # This will be overridden by async strategies
        return []


class NoExtractionStrategy(ExtractionStrategy):
    """A strategy that returns the entire HTML as a single block."""

    async def extract(self, url: str, html: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract the entire HTML as a single block."""
        return [{"index": 0, "content": html}]

    async def run(self, url: str, sections: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Process sections without any extraction."""
        return [
            {"index": i, "tags": [], "content": section}
            for i, section in enumerate(sections)
        ]


class CosineStrategy(ExtractionStrategy):
    """
    Extract meaningful blocks using cosine similarity clustering.
    
    This strategy:
    1. Pre-filters documents using embeddings and semantic_filter
    2. Performs clustering using cosine similarity
    3. Organizes texts by their cluster labels, retaining order
    4. Filters clusters by word count
    5. Extracts meaningful blocks from filtered clusters
    """

    def __init__(
        self,
        semantic_filter: Optional[str] = None,
        word_count_threshold: int = 10,
        max_dist: float = 0.2,
        linkage_method: str = "ward",
        top_k: int = 3,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        sim_threshold: float = 0.3,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.semantic_filter = semantic_filter
        self.word_count_threshold = word_count_threshold
        self.max_dist = max_dist
        self.linkage_method = linkage_method
        self.top_k = top_k
        self.model_name = model_name
        self.sim_threshold = sim_threshold

    async def extract(self, url: str, html: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract content using cosine similarity clustering."""
        try:
            # Parse HTML and extract text blocks
            soup = BeautifulSoup(html, 'lxml')
            text_blocks = self._extract_text_blocks(soup)
            
            if not text_blocks:
                return []

            # Apply semantic filtering if specified
            if self.semantic_filter:
                text_blocks = self._apply_semantic_filter(text_blocks)

            # Perform TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            try:
                tfidf_matrix = vectorizer.fit_transform(text_blocks)
            except ValueError:
                # Handle case where all documents are empty
                return [{"index": i, "content": block} for i, block in enumerate(text_blocks)]

            # Perform clustering
            if len(text_blocks) > 1:
                clustering = AgglomerativeClustering(
                    n_clusters=None,
                    distance_threshold=self.max_dist,
                    linkage=self.linkage_method
                )
                cluster_labels = clustering.fit_predict(tfidf_matrix.toarray())
            else:
                cluster_labels = [0]

            # Group by clusters and filter by word count
            clusters = {}
            for idx, (text, label) in enumerate(zip(text_blocks, cluster_labels)):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append({
                    "index": idx,
                    "content": text,
                    "word_count": len(text.split())
                })

            # Filter clusters by word count and select top-k
            filtered_clusters = []
            for label, blocks in clusters.items():
                total_words = sum(block["word_count"] for block in blocks)
                if total_words >= self.word_count_threshold:
                    # Combine blocks in cluster
                    combined_content = "\n\n".join(block["content"] for block in blocks)
                    filtered_clusters.append({
                        "cluster": label,
                        "content": combined_content,
                        "word_count": total_words,
                        "blocks": blocks
                    })

            # Sort by word count and take top-k
            filtered_clusters.sort(key=lambda x: x["word_count"], reverse=True)
            top_clusters = filtered_clusters[:self.top_k]

            # Return extracted content
            results = []
            for i, cluster in enumerate(top_clusters):
                results.append({
                    "index": i,
                    "content": cluster["content"],
                    "cluster": cluster["cluster"],
                    "word_count": cluster["word_count"],
                    "blocks_count": len(cluster["blocks"])
                })

            return results

        except Exception as e:
            logger.error("cosine_strategy_extraction_failed", url=url, error=str(e))
            return []

    def _extract_text_blocks(self, soup: BeautifulSoup) -> List[str]:
        """Extract text blocks from HTML."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()

        # Extract text from meaningful elements
        text_blocks = []
        for element in soup.find_all(['p', 'div', 'article', 'section', 'li', 'td', 'th']):
            text = sanitize_text(element.get_text())
            if text and len(text.split()) >= 3:  # Minimum 3 words
                text_blocks.append(text)

        return text_blocks

    def _apply_semantic_filter(self, text_blocks: List[str]) -> List[str]:
        """Apply semantic filtering based on keyword similarity."""
        if not self.semantic_filter:
            return text_blocks

        filter_keywords = set(self.semantic_filter.lower().split())
        filtered_blocks = []

        for block in text_blocks:
            block_words = set(block.lower().split())
            # Calculate Jaccard similarity
            intersection = len(filter_keywords.intersection(block_words))
            union = len(filter_keywords.union(block_words))
            similarity = intersection / union if union > 0 else 0

            if similarity >= self.sim_threshold:
                filtered_blocks.append(block)

        return filtered_blocks if filtered_blocks else text_blocks


class JsonCssExtractionStrategy(ExtractionStrategy):
    """
    Advanced CSS/XPath extraction with schema-based data extraction.
    
    Supports extracting structured data using CSS selectors and XPath expressions
    with a defined schema for consistent output formatting.
    """

    def __init__(self, schema: Dict[str, Any], **kwargs):
        """
        Initialize with extraction schema.
        
        Args:
            schema: JSON schema defining extraction rules
            Example schema:
            {
                "name": "Product Extractor",
                "baseSelector": ".product",
                "fields": [
                    {"name": "title", "selector": "h2", "type": "text"},
                    {"name": "price", "selector": ".price", "type": "text"},
                    {"name": "image", "selector": "img", "type": "attribute", "attribute": "src"}
                ]
            }
        """
        super().__init__(**kwargs)
        self.schema = schema
        self.validate_schema()

    def validate_schema(self):
        """Validate the extraction schema."""
        required_fields = ["name", "baseSelector", "fields"]
        for field in required_fields:
            if field not in self.schema:
                raise ValueError(f"Schema missing required field: {field}")

        if not isinstance(self.schema["fields"], list):
            raise ValueError("Schema 'fields' must be a list")

        for field in self.schema["fields"]:
            if not isinstance(field, dict) or "name" not in field or "selector" not in field:
                raise ValueError("Each field must have 'name' and 'selector'")

    async def extract(self, url: str, html: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract structured data using the schema."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            base_elements = soup.select(self.schema["baseSelector"])
            
            if not base_elements:
                if self.verbose:
                    logger.warning("no_base_elements_found", 
                                 url=url, 
                                 selector=self.schema["baseSelector"])
                return []

            results = []
            for idx, base_element in enumerate(base_elements):
                extracted_item = {"_index": idx}
                
                for field in self.schema["fields"]:
                    field_name = field["name"]
                    selector = field["selector"]
                    field_type = field.get("type", "text")
                    attribute = field.get("attribute", None)
                    
                    # Find element within base element
                    target_element = base_element.select_one(selector)
                    
                    if target_element:
                        if field_type == "text":
                            extracted_item[field_name] = sanitize_text(target_element.get_text())
                        elif field_type == "attribute" and attribute:
                            attr_value = target_element.get(attribute, "")
                            # Make URLs absolute if needed
                            if attribute in ["href", "src"] and attr_value:
                                extracted_item[field_name] = urljoin(url, attr_value)
                            else:
                                extracted_item[field_name] = attr_value
                        elif field_type == "html":
                            extracted_item[field_name] = str(target_element)
                        else:
                            extracted_item[field_name] = sanitize_text(target_element.get_text())
                    else:
                        extracted_item[field_name] = ""
                
                results.append(extracted_item)

            return results

        except Exception as e:
            logger.error("json_css_extraction_failed", url=url, error=str(e))
            return []


class RegexExtractionStrategy(ExtractionStrategy):
    """
    Pattern-based extraction using regular expressions.
    
    Supports extracting data using multiple regex patterns with named groups
    for structured output.
    """

    def __init__(self, patterns: Dict[str, Union[str, Pattern]], **kwargs):
        """
        Initialize with regex patterns.
        
        Args:
            patterns: Dictionary of pattern names to regex patterns
            Example:
            {
                "emails": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "phones": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                "prices": r"\$[\d,]+\.?\d*"
            }
        """
        super().__init__(**kwargs)
        self.patterns = {}
        
        # Compile patterns
        for name, pattern in patterns.items():
            if isinstance(pattern, str):
                self.patterns[name] = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            else:
                self.patterns[name] = pattern

    async def extract(self, url: str, html: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract content using regex patterns."""
        try:
            # Parse HTML to get clean text
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()
            
            text_content = soup.get_text()
            results = []
            
            # Apply each pattern
            for pattern_name, pattern in self.patterns.items():
                matches = pattern.findall(text_content)
                
                if matches:
                    for i, match in enumerate(matches):
                        if isinstance(match, tuple):
                            # Named groups
                            match_dict = {
                                "pattern": pattern_name,
                                "index": i,
                                "match": match[0] if match else "",
                                "groups": list(match)
                            }
                        else:
                            # Simple match
                            match_dict = {
                                "pattern": pattern_name,
                                "index": i,
                                "match": match
                            }
                        
                        results.append(match_dict)

            # If no matches found, return the text in chunks
            if not results:
                text_chunks = text_content.split('\n\n')
                for i, chunk in enumerate(text_chunks):
                    chunk = chunk.strip()
                    if chunk and len(chunk.split()) >= 5:
                        results.append({
                            "pattern": "text_chunk",
                            "index": i,
                            "content": sanitize_text(chunk)
                        })

            return results

        except Exception as e:
            logger.error("regex_extraction_failed", url=url, error=str(e))
            return []


class LLMExtractionStrategy(ExtractionStrategy):
    """
    AI-powered structured data extraction using language models.
    
    This strategy uses LLMs to extract structured data based on:
    - Custom schemas
    - Natural language instructions
    - Contextual understanding
    """

    def __init__(
        self,
        llm_config: Optional[Dict[str, Any]] = None,
        schema: Optional[Dict[str, Any]] = None,
        extraction_type: str = "schema",
        instruction: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LLM extraction strategy.
        
        Args:
            llm_config: Configuration for LLM provider (API keys, model, etc.)
            schema: JSON schema for structured extraction
            extraction_type: Type of extraction ("schema", "instruction", "blocks")
            instruction: Natural language instruction for extraction
        """
        super().__init__(**kwargs)
        self.llm_config = llm_config or {}
        self.schema = schema
        self.extraction_type = extraction_type
        self.instruction = instruction
        self.token_usage = TokenUsage()

    async def extract(self, url: str, html: str, **kwargs) -> List[Dict[str, Any]]:
        """Extract content using LLM."""
        try:
            # Parse and clean HTML
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()

            # Get clean text content
            text_content = sanitize_text(soup.get_text())
            
            # Truncate if too long (to fit LLM context)
            max_chars = kwargs.get('max_chars', 10000)
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars] + "..."

            # Prepare prompt based on extraction type
            if self.extraction_type == "schema" and self.schema:
                prompt = self._build_schema_prompt(text_content, url)
            elif self.extraction_type == "instruction" and self.instruction:
                prompt = self._build_instruction_prompt(text_content, url)
            else:
                prompt = self._build_blocks_prompt(text_content, url)

            # Make LLM API call (mock implementation for now)
            # In production, this would call actual LLM APIs like OpenAI, etc.
            result = await self._call_llm_api(prompt, **kwargs)
            
            return result

        except Exception as e:
            logger.error("llm_extraction_failed", url=url, error=str(e))
            return []

    def _build_schema_prompt(self, content: str, url: str) -> str:
        """Build prompt for schema-based extraction."""
        schema_str = json.dumps(self.schema, indent=2)
        
        prompt = f"""
Extract structured data from the following content according to this JSON schema:

Schema:
{schema_str}

Content from {url}:
{content}

Please return the extracted data as a JSON array of objects matching the schema.
If no data matches the schema, return an empty array.
"""
        return prompt

    def _build_instruction_prompt(self, content: str, url: str) -> str:
        """Build prompt for instruction-based extraction."""
        prompt = f"""
{self.instruction}

Content from {url}:
{content}

Please extract the requested information and return it as structured JSON.
"""
        return prompt

    def _build_blocks_prompt(self, content: str, url: str) -> str:
        """Build prompt for general block extraction."""
        prompt = f"""
Analyze the following content and extract the most important and meaningful blocks of information.
Focus on the main content, key facts, and important details.

Content from {url}:
{content}

Please return the extracted blocks as a JSON array with each block containing:
- "index": sequential number
- "content": the extracted text block
- "importance": relevance score (1-10)
- "category": type of content (article, list, table, etc.)
"""
        return prompt

    async def _call_llm_api(self, prompt: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Call LLM API for extraction.
        
        Note: This is a mock implementation. In production, you would integrate
        with actual LLM providers like OpenAI, Anthropic, etc.
        """
        # Mock response - in production, replace with actual LLM API calls
        await asyncio.sleep(0.1)  # Simulate API call delay
        
        # For now, return a simple structured response
        # This would be replaced with actual LLM API integration
        mock_response = [
            {
                "index": 0,
                "content": "Mock extracted content - replace with actual LLM integration",
                "confidence": 0.8,
                "source": "llm_extraction"
            }
        ]
        
        # Update token usage (mock)
        self.token_usage.prompt_tokens += len(prompt.split())
        self.token_usage.completion_tokens += 50
        self.token_usage.total_tokens = self.token_usage.prompt_tokens + self.token_usage.completion_tokens
        
        return mock_response


# Factory function for creating extraction strategies
def create_extraction_strategy(
    strategy_type: str,
    config: Dict[str, Any]
) -> ExtractionStrategy:
    """
    Factory function to create extraction strategies.
    
    Args:
        strategy_type: Type of strategy ("cosine", "json_css", "regex", "llm", "none")
        config: Configuration dictionary for the strategy
        
    Returns:
        Configured extraction strategy instance
    """
    strategies = {
        "cosine": CosineStrategy,
        "json_css": JsonCssExtractionStrategy,
        "regex": RegexExtractionStrategy,
        "llm": LLMExtractionStrategy,
        "none": NoExtractionStrategy
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"Unknown strategy type: {strategy_type}. Available: {list(strategies.keys())}")
    
    strategy_class = strategies[strategy_type]
    return strategy_class(**config)


# Convenience functions for common extraction patterns
async def extract_with_schema(html: str, url: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract data using JSON CSS schema."""
    strategy = JsonCssExtractionStrategy(schema=schema)
    return await strategy.extract(url, html)


async def extract_with_patterns(html: str, url: str, patterns: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract data using regex patterns."""
    strategy = RegexExtractionStrategy(patterns=patterns)
    return await strategy.extract(url, html)


async def extract_with_clustering(
    html: str, 
    url: str, 
    semantic_filter: Optional[str] = None,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """Extract content using cosine similarity clustering."""
    strategy = CosineStrategy(
        semantic_filter=semantic_filter,
        top_k=top_k
    )
    return await strategy.extract(url, html)
