"""
HTML attributes extraction service inspired by Firecrawl.

Provides comprehensive attribute extraction capabilities:
- CSS selector-based attribute extraction
- Bulk attribute extraction
- Multi-element attribute collection
- Advanced filtering and processing
- Structured attribute analysis
"""

import asyncio
import time
import re
from typing import Dict, List, Optional, Any, Union, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urljoin, urlparse
import structlog

from app.config import get_settings
from app.services.scraping.enhanced_scraping import get_enhanced_scraping_service
from app.utils.text_processing import sanitize_text, clean_text

logger = structlog.get_logger(__name__)
settings = get_settings()


class AttributeProcessingType(Enum):
    """Types of attribute processing."""
    RAW = "raw"
    CLEANED = "cleaned"
    URLS_RESOLVED = "urls_resolved"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    LIST = "list"


@dataclass
class AttributeExtractionRule:
    """Rule for extracting attributes."""
    selector: str
    attribute: str
    processing: AttributeProcessingType = AttributeProcessingType.RAW
    filter_empty: bool = True
    filter_duplicates: bool = True
    limit: Optional[int] = None
    transform: Optional[str] = None  # CSS transform function or regex
    validation_pattern: Optional[str] = None  # Regex for validation


@dataclass
class AttributeResult:
    """Result of attribute extraction for a single element."""
    element_index: int
    selector_match: str
    attribute_name: str
    raw_value: str
    processed_value: Any
    element_text: Optional[str] = None
    element_tag: Optional[str] = None
    element_classes: List[str] = field(default_factory=list)
    element_id: Optional[str] = None


@dataclass
class SelectorAttributeResults:
    """Results for a specific selector and attribute combination."""
    selector: str
    attribute: str
    values: List[str]
    processed_values: List[Any]
    element_count: int
    results: List[AttributeResult] = field(default_factory=list)


@dataclass
class AttributesExtractionConfig:
    """Configuration for attributes extraction."""
    rules: List[AttributeExtractionRule] = field(default_factory=list)
    base_url: Optional[str] = None  # For URL resolution
    include_element_context: bool = True
    max_elements_per_selector: int = 1000
    timeout: int = 30
    resolve_relative_urls: bool = True
    normalize_whitespace: bool = True
    
    # Advanced options
    extract_computed_styles: bool = False
    include_xpath_location: bool = False
    extract_surrounding_context: bool = False
    context_window: int = 50  # Characters around element


@dataclass
class AttributesExtractionResult:
    """Complete result of attributes extraction."""
    url: str
    extractions: List[SelectorAttributeResults]
    total_attributes_extracted: int
    total_elements_processed: int
    processing_time_ms: int
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AttributeProcessor:
    """Handles processing of extracted attribute values."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url
    
    def process_value(
        self, 
        value: str, 
        processing_type: AttributeProcessingType,
        transform: Optional[str] = None
    ) -> Any:
        """Process attribute value according to type."""
        if not value and processing_type != AttributeProcessingType.BOOLEAN:
            return value
        
        try:
            if processing_type == AttributeProcessingType.RAW:
                return value
            
            elif processing_type == AttributeProcessingType.CLEANED:
                cleaned = clean_text(value) if value else ""
                return cleaned.strip()
            
            elif processing_type == AttributeProcessingType.URLS_RESOLVED:
                if self.base_url and value:
                    return urljoin(self.base_url, value)
                return value
            
            elif processing_type == AttributeProcessingType.NUMERIC:
                if not value:
                    return None
                # Extract first number from string
                number_match = re.search(r'-?\d+(?:\.\d+)?', value)
                if number_match:
                    num_str = number_match.group()
                    return float(num_str) if '.' in num_str else int(num_str)
                return None
            
            elif processing_type == AttributeProcessingType.BOOLEAN:
                if not value:
                    return False
                return value.lower() in ['true', '1', 'yes', 'on', 'checked', 'selected']
            
            elif processing_type == AttributeProcessingType.LIST:
                if not value:
                    return []
                # Split by common delimiters
                delimiters = [',', ';', '|', '\n']
                items = [value]
                for delimiter in delimiters:
                    new_items = []
                    for item in items:
                        new_items.extend([x.strip() for x in item.split(delimiter)])
                    items = new_items
                return [item for item in items if item]
            
            # Apply custom transform if provided
            if transform:
                return self._apply_transform(value, transform)
            
            return value
            
        except Exception as e:
            logger.warning("attribute_processing_failed", 
                          value=value, 
                          processing_type=processing_type.value, 
                          error=str(e))
            return value
    
    def _apply_transform(self, value: str, transform: str) -> Any:
        """Apply custom transform to value."""
        try:
            # Handle regex transforms
            if transform.startswith('regex:'):
                pattern = transform[6:]  # Remove 'regex:' prefix
                match = re.search(pattern, value)
                return match.group(1) if match and match.groups() else match.group(0) if match else None
            
            # Handle JavaScript-like transforms
            elif transform.startswith('js:'):
                # Simplified JS-like transforms
                js_code = transform[3:]
                if 'toLowerCase()' in js_code:
                    return value.lower()
                elif 'toUpperCase()' in js_code:
                    return value.upper()
                elif 'trim()' in js_code:
                    return value.strip()
            
            # Handle CSS-like transforms  
            elif transform == 'uppercase':
                return value.upper()
            elif transform == 'lowercase':
                return value.lower()
            elif transform == 'capitalize':
                return value.capitalize()
            
            return value
            
        except Exception as e:
            logger.warning("transform_failed", value=value, transform=transform, error=str(e))
            return value
    
    def validate_value(self, value: Any, pattern: Optional[str]) -> bool:
        """Validate processed value against pattern."""
        if not pattern:
            return True
        
        try:
            str_value = str(value) if value is not None else ""
            return bool(re.search(pattern, str_value))
        except Exception:
            return False


class AttributesExtractor:
    """
    HTML attributes extraction service.
    
    Provides comprehensive attribute extraction including:
    - CSS selector-based extraction
    - Multiple processing types
    - Bulk extraction operations
    - Advanced filtering and validation
    """
    
    def __init__(self):
        """Initialize attributes extractor."""
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "attributes_extracted": 0,
            "elements_processed": 0
        }
    
    async def extract_attributes(
        self, 
        url: str, 
        config: AttributesExtractionConfig
    ) -> AttributesExtractionResult:
        """
        Extract attributes from a web page.
        
        Args:
            url: URL to extract attributes from
            config: Extraction configuration
            
        Returns:
            AttributesExtractionResult with extracted attributes
        """
        start_time = time.time()
        
        self.extraction_stats["total_extractions"] += 1
        
        logger.info("attributes_extraction_started", 
                   url=url, 
                   rules_count=len(config.rules))
        
        try:
            # Scrape the page
            scraping_service = await get_enhanced_scraping_service()
            scrape_results = await scraping_service.scrape_urls_enhanced([url])
            
            if not scrape_results or not scrape_results[0].extraction_success:
                raise ValueError("Failed to scrape page content")
            
            scraped_content = scrape_results[0]
            html_content = scraped_content.html
            
            if not html_content:
                raise ValueError("No HTML content available")
            
            # Parse HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Set base URL for URL resolution
            base_url = config.base_url or url
            processor = AttributeProcessor(base_url)
            
            # Extract attributes for each rule
            extractions = []
            total_attributes = 0
            total_elements = 0
            
            for rule in config.rules:
                try:
                    logger.debug("processing_extraction_rule", 
                               selector=rule.selector, 
                               attribute=rule.attribute)
                    
                    extraction_result = await self._extract_for_rule(
                        soup, rule, processor, config
                    )
                    
                    extractions.append(extraction_result)
                    total_attributes += len(extraction_result.values)
                    total_elements += extraction_result.element_count
                    
                except Exception as e:
                    logger.error("rule_extraction_failed", 
                               selector=rule.selector, 
                               attribute=rule.attribute, 
                               error=str(e))
                    
                    # Add empty result for failed rule
                    extractions.append(SelectorAttributeResults(
                        selector=rule.selector,
                        attribute=rule.attribute,
                        values=[],
                        processed_values=[],
                        element_count=0
                    ))
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update stats
            self.extraction_stats["successful_extractions"] += 1
            self.extraction_stats["attributes_extracted"] += total_attributes
            self.extraction_stats["elements_processed"] += total_elements
            
            result = AttributesExtractionResult(
                url=url,
                extractions=extractions,
                total_attributes_extracted=total_attributes,
                total_elements_processed=total_elements,
                processing_time_ms=processing_time_ms,
                success=True,
                metadata={
                    "page_title": scraped_content.title,
                    "rules_processed": len(config.rules),
                    "html_size": len(html_content)
                }
            )
            
            logger.info("attributes_extraction_completed",
                       url=url,
                       total_attributes=total_attributes,
                       total_elements=total_elements,
                       processing_time_ms=processing_time_ms)
            
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            logger.error("attributes_extraction_failed", 
                        url=url, 
                        error=error_msg,
                        processing_time_ms=processing_time_ms)
            
            return AttributesExtractionResult(
                url=url,
                extractions=[],
                total_attributes_extracted=0,
                total_elements_processed=0,
                processing_time_ms=processing_time_ms,
                success=False,
                error=error_msg
            )
    
    async def _extract_for_rule(
        self, 
        soup: Any, 
        rule: AttributeExtractionRule,
        processor: AttributeProcessor,
        config: AttributesExtractionConfig
    ) -> SelectorAttributeResults:
        """Extract attributes for a specific rule."""
        try:
            # Find elements matching selector
            elements = soup.select(rule.selector)
            
            if rule.limit:
                elements = elements[:rule.limit]
            elif len(elements) > config.max_elements_per_selector:
                elements = elements[:config.max_elements_per_selector]
            
            results = []
            values = []
            processed_values = []
            
            for i, element in enumerate(elements):
                try:
                    # Get attribute value
                    raw_value = element.get(rule.attribute, "")
                    
                    if not raw_value and rule.filter_empty:
                        continue
                    
                    # Process value
                    processed_value = processor.process_value(
                        raw_value, rule.processing, rule.transform
                    )
                    
                    # Validate if pattern provided
                    if rule.validation_pattern and not processor.validate_value(
                        processed_value, rule.validation_pattern
                    ):
                        continue
                    
                    # Handle URL normalization
                    if config.normalize_whitespace and isinstance(processed_value, str):
                        processed_value = re.sub(r'\s+', ' ', processed_value).strip()
                    
                    # Create result
                    attribute_result = AttributeResult(
                        element_index=i,
                        selector_match=rule.selector,
                        attribute_name=rule.attribute,
                        raw_value=raw_value,
                        processed_value=processed_value
                    )
                    
                    # Add element context if requested
                    if config.include_element_context:
                        attribute_result.element_text = element.get_text(strip=True)[:200]  # Limit text
                        attribute_result.element_tag = element.name
                        attribute_result.element_classes = element.get('class', [])
                        attribute_result.element_id = element.get('id')
                    
                    results.append(attribute_result)
                    values.append(raw_value)
                    processed_values.append(processed_value)
                    
                except Exception as e:
                    logger.warning("element_processing_failed", 
                                 selector=rule.selector,
                                 element_index=i,
                                 error=str(e))
                    continue
            
            # Remove duplicates if requested
            if rule.filter_duplicates:
                unique_results = []
                seen_values = set()
                filtered_values = []
                filtered_processed = []
                
                for result, value, processed in zip(results, values, processed_values):
                    value_key = str(processed) if processed is not None else str(value)
                    
                    if value_key not in seen_values:
                        seen_values.add(value_key)
                        unique_results.append(result)
                        filtered_values.append(value)
                        filtered_processed.append(processed)
                
                results = unique_results
                values = filtered_values
                processed_values = filtered_processed
            
            return SelectorAttributeResults(
                selector=rule.selector,
                attribute=rule.attribute,
                values=values,
                processed_values=processed_values,
                element_count=len(results),
                results=results
            )
            
        except Exception as e:
            logger.error("rule_extraction_failed", 
                        selector=rule.selector, 
                        attribute=rule.attribute, 
                        error=str(e))
            
            return SelectorAttributeResults(
                selector=rule.selector,
                attribute=rule.attribute,
                values=[],
                processed_values=[],
                element_count=0
            )
    
    async def extract_bulk_attributes(
        self, 
        urls: List[str], 
        config: AttributesExtractionConfig,
        max_concurrent: int = 5
    ) -> List[AttributesExtractionResult]:
        """Extract attributes from multiple URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_single(url: str) -> AttributesExtractionResult:
            async with semaphore:
                return await self.extract_attributes(url, config)
        
        logger.info("bulk_attributes_extraction_started", urls_count=len(urls))
        
        results = await asyncio.gather(
            *[extract_single(url) for url in urls],
            return_exceptions=True
        )
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("bulk_extraction_failed", url=urls[i], error=str(result))
                final_results.append(AttributesExtractionResult(
                    url=urls[i],
                    extractions=[],
                    total_attributes_extracted=0,
                    total_elements_processed=0,
                    processing_time_ms=0,
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)
        
        successful_results = [r for r in final_results if r.success]
        
        logger.info("bulk_attributes_extraction_completed",
                   urls_count=len(urls),
                   successful_extractions=len(successful_results),
                   total_attributes=sum(r.total_attributes_extracted for r in successful_results))
        
        return final_results
    
    async def extract_common_attributes(
        self, 
        url: str, 
        base_url: Optional[str] = None
    ) -> AttributesExtractionResult:
        """Extract commonly useful attributes from a page."""
        common_rules = [
            # Links
            AttributeExtractionRule("a", "href", AttributeProcessingType.URLS_RESOLVED),
            AttributeExtractionRule("a", "title", AttributeProcessingType.CLEANED),
            
            # Images
            AttributeExtractionRule("img", "src", AttributeProcessingType.URLS_RESOLVED),
            AttributeExtractionRule("img", "alt", AttributeProcessingType.CLEANED),
            AttributeExtractionRule("img", "title", AttributeProcessingType.CLEANED),
            
            # Forms
            AttributeExtractionRule("form", "action", AttributeProcessingType.URLS_RESOLVED),
            AttributeExtractionRule("form", "method", AttributeProcessingType.RAW),
            AttributeExtractionRule("input", "type", AttributeProcessingType.RAW),
            AttributeExtractionRule("input", "name", AttributeProcessingType.RAW),
            
            # Meta tags
            AttributeExtractionRule("meta[name]", "name", AttributeProcessingType.RAW),
            AttributeExtractionRule("meta[name]", "content", AttributeProcessingType.CLEANED),
            AttributeExtractionRule("meta[property]", "property", AttributeProcessingType.RAW),
            AttributeExtractionRule("meta[property]", "content", AttributeProcessingType.CLEANED),
            
            # Scripts and styles
            AttributeExtractionRule("script", "src", AttributeProcessingType.URLS_RESOLVED),
            AttributeExtractionRule("link", "href", AttributeProcessingType.URLS_RESOLVED),
            AttributeExtractionRule("link", "rel", AttributeProcessingType.RAW),
            
            # Structured data
            AttributeExtractionRule("[itemtype]", "itemtype", AttributeProcessingType.RAW),
            AttributeExtractionRule("[itemprop]", "itemprop", AttributeProcessingType.RAW),
            
            # IDs and classes
            AttributeExtractionRule("[id]", "id", AttributeProcessingType.RAW),
            AttributeExtractionRule("[class]", "class", AttributeProcessingType.LIST),
        ]
        
        config = AttributesExtractionConfig(
            rules=common_rules,
            base_url=base_url,
            include_element_context=True
        )
        
        return await self.extract_attributes(url, config)
    
    async def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction service statistics."""
        return {
            "extraction_stats": self.extraction_stats,
            "success_rate": (
                self.extraction_stats["successful_extractions"] / 
                max(1, self.extraction_stats["total_extractions"])
            ) if self.extraction_stats["total_extractions"] > 0 else 0,
            "avg_attributes_per_extraction": (
                self.extraction_stats["attributes_extracted"] /
                max(1, self.extraction_stats["successful_extractions"])
            ) if self.extraction_stats["successful_extractions"] > 0 else 0,
            "avg_elements_per_extraction": (
                self.extraction_stats["elements_processed"] /
                max(1, self.extraction_stats["successful_extractions"])
            ) if self.extraction_stats["successful_extractions"] > 0 else 0
        }


# Singleton service
_attributes_extractor: Optional[AttributesExtractor] = None


async def get_attributes_extractor() -> AttributesExtractor:
    """Get or create attributes extractor service instance."""
    global _attributes_extractor
    
    if _attributes_extractor is None:
        _attributes_extractor = AttributesExtractor()
    
    return _attributes_extractor


# Convenience functions
async def extract_page_attributes(
    url: str,
    selector_attribute_pairs: List[tuple],  # [(selector, attribute), ...]
    processing_type: str = "cleaned",
    base_url: Optional[str] = None
) -> AttributesExtractionResult:
    """
    Convenience function for extracting specific attributes.
    
    Args:
        url: URL to extract from
        selector_attribute_pairs: List of (selector, attribute) tuples
        processing_type: How to process values
        base_url: Base URL for URL resolution
        
    Returns:
        AttributesExtractionResult with extracted attributes
    """
    extractor = await get_attributes_extractor()
    
    rules = []
    processing = AttributeProcessingType(processing_type)
    
    for selector, attribute in selector_attribute_pairs:
        rules.append(AttributeExtractionRule(
            selector=selector,
            attribute=attribute,
            processing=processing
        ))
    
    config = AttributesExtractionConfig(
        rules=rules,
        base_url=base_url
    )
    
    return await extractor.extract_attributes(url, config)


async def extract_all_links(url: str) -> List[str]:
    """Extract all links from a page."""
    extractor = await get_attributes_extractor()
    
    config = AttributesExtractionConfig(
        rules=[AttributeExtractionRule(
            "a", "href", AttributeProcessingType.URLS_RESOLVED
        )],
        base_url=url
    )
    
    result = await extractor.extract_attributes(url, config)
    
    if result.success and result.extractions:
        return result.extractions[0].processed_values
    
    return []


async def extract_all_images(url: str) -> List[Dict[str, str]]:
    """Extract all images with src and alt attributes."""
    extractor = await get_attributes_extractor()
    
    config = AttributesExtractionConfig(
        rules=[
            AttributeExtractionRule("img", "src", AttributeProcessingType.URLS_RESOLVED),
            AttributeExtractionRule("img", "alt", AttributeProcessingType.CLEANED),
        ],
        base_url=url,
        include_element_context=True
    )
    
    result = await extractor.extract_attributes(url, config)
    
    if result.success and len(result.extractions) >= 2:
        src_results = result.extractions[0]
        alt_results = result.extractions[1]
        
        images = []
        for i in range(min(len(src_results.results), len(alt_results.results))):
            images.append({
                "src": src_results.results[i].processed_value,
                "alt": alt_results.results[i].processed_value or ""
            })
        
        return images
    
    return []
