"""
Multi-entity extraction service inspired by Firecrawl's advanced extraction capabilities.

Provides intelligent cross-URL data extraction and entity linking for complex data scenarios.
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
from urllib.parse import urlparse, urljoin
import re

from app.config import get_settings
from app.models.requests import ScrapingConfig
from app.models.responses import ScrapedContent, ContentMetadata
from app.services.enhanced_scraping import get_enhanced_scraping_service
from app.services.llm_configuration import get_llm_config_service
from app.utils.text_processing import sanitize_text, extract_entities, clean_tokens

logger = structlog.get_logger(__name__)
settings = get_settings()


class ExtractionStrategy(Enum):
    """Multi-entity extraction strategies."""
    LINKED_ENTITIES = "linked_entities"  # Extract entities and find related URLs
    HIERARCHICAL = "hierarchical"  # Follow hierarchical relationships
    SEMANTIC_SIMILARITY = "semantic_similarity"  # Group by semantic similarity
    TEMPORAL_SEQUENCE = "temporal_sequence"  # Time-based entity relationships
    CROSS_REFERENCE = "cross_reference"  # Cross-reference validation


@dataclass
class EntityRelation:
    """Represents relationship between entities."""
    source_url: str
    target_url: str
    relation_type: str
    confidence: float
    evidence: List[str]


@dataclass
class ExtractedEntity:
    """Represents an extracted entity with metadata."""
    id: str
    entity_type: str
    value: Any
    confidence: float
    source_url: str
    extraction_method: str
    context: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    related_entities: List[str] = field(default_factory=list)


@dataclass
class MultiEntityExtractionRequest:
    """Request for multi-entity extraction."""
    urls: List[str]
    schema: Dict[str, Any]
    extraction_strategy: ExtractionStrategy = ExtractionStrategy.LINKED_ENTITIES
    max_related_urls: int = 50
    similarity_threshold: float = 0.7
    cross_validate: bool = True
    follow_links: bool = True
    max_depth: int = 2
    include_metadata: bool = True
    timeout: int = 300  # 5 minutes


@dataclass
class MultiEntityExtractionResult:
    """Result of multi-entity extraction."""
    request_id: str
    entities: List[ExtractedEntity]
    relations: List[EntityRelation]
    discovered_urls: List[str]
    validation_results: Dict[str, Any]
    extraction_metadata: Dict[str, Any]
    processing_time: float
    success: bool
    errors: List[str] = field(default_factory=list)


class EntityLinker:
    """Links entities across multiple URLs and content sources."""
    
    def __init__(self):
        self.entity_cache: Dict[str, List[ExtractedEntity]] = {}
        self.url_graph: Dict[str, Set[str]] = {}
    
    async def discover_related_urls(
        self, 
        base_urls: List[str], 
        strategy: ExtractionStrategy,
        max_urls: int = 50
    ) -> List[str]:
        """Discover URLs related to base URLs using various strategies."""
        
        discovered = set(base_urls)
        
        if strategy == ExtractionStrategy.LINKED_ENTITIES:
            # Find URLs through link analysis
            for url in base_urls:
                linked_urls = await self._find_linked_urls(url)
                discovered.update(linked_urls[:max_urls // len(base_urls)])
        
        elif strategy == ExtractionStrategy.HIERARCHICAL:
            # Find URLs through hierarchical relationships
            for url in base_urls:
                hierarchical_urls = await self._find_hierarchical_urls(url)
                discovered.update(hierarchical_urls[:max_urls // len(base_urls)])
        
        elif strategy == ExtractionStrategy.SEMANTIC_SIMILARITY:
            # Find URLs through content similarity
            for url in base_urls:
                similar_urls = await self._find_similar_urls(url)
                discovered.update(similar_urls[:max_urls // len(base_urls)])
        
        return list(discovered)[:max_urls]
    
    async def _find_linked_urls(self, base_url: str) -> List[str]:
        """Find URLs through link analysis."""
        try:
            # Scrape base URL to extract links
            scraping_service = await get_enhanced_scraping_service()
            config = ScrapingConfig(
                urls=[base_url],
                extract_links=True,
                extract_text=True
            )
            
            results = await scraping_service.scrape_urls_enhanced([base_url], config)
            if not results or not results[0].extraction_success:
                return []
            
            links = results[0].links or []
            
            # Filter and score links based on relevance
            relevant_links = []
            base_domain = urlparse(base_url).netloc
            
            for link in links:
                # Prefer internal links but allow some external
                link_domain = urlparse(link.url).netloc
                if link_domain == base_domain:
                    relevant_links.append(link.url)
                elif len(relevant_links) < 10:  # Limited external links
                    relevant_links.append(link.url)
            
            return relevant_links[:20]
            
        except Exception as e:
            logger.warning("failed_to_find_linked_urls", url=base_url, error=str(e))
            return []
    
    async def _find_hierarchical_urls(self, base_url: str) -> List[str]:
        """Find URLs through hierarchical relationships."""
        hierarchical_urls = []
        parsed = urlparse(base_url)
        
        # Generate parent URLs
        path_parts = parsed.path.strip('/').split('/')
        for i in range(len(path_parts)):
            parent_path = '/'.join(path_parts[:i+1])
            if parent_path and parent_path != parsed.path.strip('/'):
                parent_url = f"{parsed.scheme}://{parsed.netloc}/{parent_path}"
                hierarchical_urls.append(parent_url)
        
        # Generate sibling URLs (same level)
        if len(path_parts) > 1:
            parent_path = '/'.join(path_parts[:-1])
            # This would typically query a sitemap or use discovery patterns
            # For now, we'll generate common patterns
            common_patterns = ['index.html', 'about.html', 'contact.html', 'services.html']
            for pattern in common_patterns:
                sibling_url = f"{parsed.scheme}://{parsed.netloc}/{parent_path}/{pattern}"
                hierarchical_urls.append(sibling_url)
        
        return hierarchical_urls
    
    async def _find_similar_urls(self, base_url: str) -> List[str]:
        """Find URLs through content similarity."""
        # This would typically use semantic search or content analysis
        # For now, return pattern-based URLs
        similar_urls = []
        parsed = urlparse(base_url)
        
        # Generate pattern-based similar URLs
        if 'blog' in base_url:
            # Find other blog posts
            base_blog_url = base_url.split('/blog/')[0] + '/blog/'
            for i in range(1, 6):
                similar_urls.append(f"{base_blog_url}post-{i}")
        
        if 'product' in base_url:
            # Find other products
            base_product_url = base_url.split('/product/')[0] + '/product/'
            for i in range(1, 6):
                similar_urls.append(f"{base_product_url}item-{i}")
        
        return similar_urls


class EntityExtractor:
    """Extracts structured entities from content using various methods."""
    
    def __init__(self):
        self.extraction_cache: Dict[str, List[ExtractedEntity]] = {}
    
    async def extract_entities(
        self,
        content: ScrapedContent,
        schema: Dict[str, Any],
        extraction_method: str = "llm"
    ) -> List[ExtractedEntity]:
        """Extract entities from scraped content based on schema."""
        
        # Check cache first
        cache_key = f"{content.url}:{hash(json.dumps(schema, sort_keys=True))}"
        if cache_key in self.extraction_cache:
            return self.extraction_cache[cache_key]
        
        entities = []
        
        try:
            if extraction_method == "llm":
                entities = await self._extract_with_llm(content, schema)
            elif extraction_method == "regex":
                entities = await self._extract_with_regex(content, schema)
            elif extraction_method == "css":
                entities = await self._extract_with_css(content, schema)
            else:
                entities = await self._extract_with_llm(content, schema)  # Default to LLM
            
            # Cache results
            self.extraction_cache[cache_key] = entities
            
        except Exception as e:
            logger.error("entity_extraction_failed", 
                        url=content.url, 
                        method=extraction_method, 
                        error=str(e))
        
        return entities
    
    async def _extract_with_llm(
        self, 
        content: ScrapedContent, 
        schema: Dict[str, Any]
    ) -> List[ExtractedEntity]:
        """Extract entities using LLM."""
        
        try:
            llm_service = await get_llm_config_service()
            
            # Prepare extraction prompt
            prompt = f"""
            Extract structured data from the following web content according to the schema.
            
            Schema: {json.dumps(schema, indent=2)}
            
            Content Title: {content.title}
            Content Text: {content.text[:5000]}...
            
            Extract all relevant entities that match the schema. For each entity, provide:
            1. The extracted value
            2. Confidence score (0.0-1.0)
            3. Context/evidence from the content
            
            Return as JSON array of entities.
            """
            
            from app.services.llm_configuration import LLMConfigurationRequest, ConfigurationPromptType
            
            request = LLMConfigurationRequest(
                prompt=prompt,
                prompt_type=ConfigurationPromptType.EXTRACTION_SCHEMA
            )
            
            response = await llm_service.generate_config(request)
            
            if response.success and response.config:
                entities = []
                extracted_data = response.config.get("extracted_entities", [])
                
                for i, data in enumerate(extracted_data):
                    entity = ExtractedEntity(
                        id=f"{content.url}:llm:{i}",
                        entity_type=data.get("type", "unknown"),
                        value=data.get("value"),
                        confidence=data.get("confidence", 0.5),
                        source_url=content.url,
                        extraction_method="llm",
                        context=data.get("context"),
                        attributes=data.get("attributes", {})
                    )
                    entities.append(entity)
                
                return entities
            
        except Exception as e:
            logger.error("llm_extraction_failed", url=content.url, error=str(e))
        
        return []
    
    async def _extract_with_regex(
        self, 
        content: ScrapedContent, 
        schema: Dict[str, Any]
    ) -> List[ExtractedEntity]:
        """Extract entities using regex patterns."""
        entities = []
        
        # Extract common patterns
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "url": r'https?://[^\s<>"{}|\\^`\[\]]+',
            "price": r'\$\d+(?:\.\d{2})?',
            "date": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b'
        }
        
        text = content.text or ""
        
        for entity_type, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for i, match in enumerate(matches):
                entity = ExtractedEntity(
                    id=f"{content.url}:regex:{entity_type}:{i}",
                    entity_type=entity_type,
                    value=match.group(),
                    confidence=0.8,  # Regex typically high confidence
                    source_url=content.url,
                    extraction_method="regex",
                    context=text[max(0, match.start()-50):match.end()+50]
                )
                entities.append(entity)
        
        return entities
    
    async def _extract_with_css(
        self, 
        content: ScrapedContent, 
        schema: Dict[str, Any]
    ) -> List[ExtractedEntity]:
        """Extract entities using CSS selectors."""
        entities = []
        
        if not content.html:
            return entities
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content.html, 'lxml')
            
            # Common CSS patterns for structured data
            selectors = {
                "title": ["h1", "h2", ".title", "#title"],
                "price": [".price", ".cost", "[data-price]"],
                "description": [".description", ".summary", ".excerpt"],
                "author": [".author", ".by", "[rel='author']"],
                "date": [".date", ".published", "time"],
            }
            
            for entity_type, css_selectors in selectors.items():
                for selector in css_selectors:
                    elements = soup.select(selector)
                    for i, element in enumerate(elements[:5]):  # Limit per type
                        entity = ExtractedEntity(
                            id=f"{content.url}:css:{entity_type}:{i}",
                            entity_type=entity_type,
                            value=sanitize_text(element.get_text()),
                            confidence=0.7,
                            source_url=content.url,
                            extraction_method="css",
                            attributes={"selector": selector}
                        )
                        entities.append(entity)
            
        except Exception as e:
            logger.error("css_extraction_failed", url=content.url, error=str(e))
        
        return entities


class EntityValidator:
    """Validates extracted entities through cross-referencing and consistency checks."""
    
    async def validate_entities(
        self, 
        entities: List[ExtractedEntity],
        validation_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate extracted entities."""
        
        validation_result = {
            "total_entities": len(entities),
            "valid_entities": 0,
            "invalid_entities": 0,
            "validation_errors": [],
            "consistency_score": 0.0,
            "cross_reference_matches": 0
        }
        
        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)
        
        # Validate each entity type
        for entity_type, type_entities in entities_by_type.items():
            type_validation = await self._validate_entity_type(entity_type, type_entities)
            validation_result["valid_entities"] += type_validation["valid_count"]
            validation_result["invalid_entities"] += type_validation["invalid_count"]
            validation_result["validation_errors"].extend(type_validation["errors"])
        
        # Cross-reference validation
        cross_ref_score = await self._cross_reference_validation(entities_by_type)
        validation_result["cross_reference_matches"] = cross_ref_score
        
        # Calculate overall consistency score
        if len(entities) > 0:
            validation_result["consistency_score"] = (
                validation_result["valid_entities"] / len(entities)
            ) * 0.7 + (cross_ref_score / 100) * 0.3
        
        return validation_result
    
    async def _validate_entity_type(
        self, 
        entity_type: str, 
        entities: List[ExtractedEntity]
    ) -> Dict[str, Any]:
        """Validate entities of a specific type."""
        
        validation = {"valid_count": 0, "invalid_count": 0, "errors": []}
        
        for entity in entities:
            is_valid = True
            
            # Basic validation rules by type
            if entity_type == "email":
                if not re.match(r'^[^@]+@[^@]+\.[^@]+$', str(entity.value)):
                    is_valid = False
                    validation["errors"].append(f"Invalid email format: {entity.value}")
            
            elif entity_type == "phone":
                # Remove non-digits and check length
                digits = re.sub(r'\D', '', str(entity.value))
                if len(digits) not in [10, 11]:
                    is_valid = False
                    validation["errors"].append(f"Invalid phone format: {entity.value}")
            
            elif entity_type == "url":
                try:
                    parsed = urlparse(str(entity.value))
                    if not parsed.scheme or not parsed.netloc:
                        is_valid = False
                        validation["errors"].append(f"Invalid URL format: {entity.value}")
                except:
                    is_valid = False
                    validation["errors"].append(f"Invalid URL format: {entity.value}")
            
            # Check confidence threshold
            if entity.confidence < 0.5:
                is_valid = False
                validation["errors"].append(f"Low confidence entity: {entity.value} ({entity.confidence})")
            
            if is_valid:
                validation["valid_count"] += 1
            else:
                validation["invalid_count"] += 1
        
        return validation
    
    async def _cross_reference_validation(
        self, 
        entities_by_type: Dict[str, List[ExtractedEntity]]
    ) -> int:
        """Validate entities through cross-referencing."""
        
        matches = 0
        
        # Compare entities across different URLs for consistency
        for entity_type, entities in entities_by_type.items():
            if len(entities) < 2:
                continue
            
            # Group by URL
            entities_by_url = {}
            for entity in entities:
                if entity.source_url not in entities_by_url:
                    entities_by_url[entity.source_url] = []
                entities_by_url[entity.source_url].append(entity)
            
            # Compare entities across URLs
            urls = list(entities_by_url.keys())
            for i in range(len(urls)):
                for j in range(i + 1, len(urls)):
                    url1_entities = entities_by_url[urls[i]]
                    url2_entities = entities_by_url[urls[j]]
                    
                    # Find matching values
                    for e1 in url1_entities:
                        for e2 in url2_entities:
                            if self._entities_match(e1, e2):
                                matches += 1
        
        return matches
    
    def _entities_match(self, e1: ExtractedEntity, e2: ExtractedEntity) -> bool:
        """Check if two entities match."""
        if e1.entity_type != e2.entity_type:
            return False
        
        # Exact match
        if str(e1.value).lower().strip() == str(e2.value).lower().strip():
            return True
        
        # Fuzzy match for text entities
        if isinstance(e1.value, str) and isinstance(e2.value, str):
            tokens1 = set(clean_tokens(e1.value.lower().split()))
            tokens2 = set(clean_tokens(e2.value.lower().split()))
            
            if tokens1 and tokens2:
                overlap = len(tokens1.intersection(tokens2))
                union = len(tokens1.union(tokens2))
                similarity = overlap / union if union > 0 else 0
                return similarity > 0.8
        
        return False


class MultiEntityExtractionService:
    """
    Advanced multi-entity extraction service.
    
    Provides sophisticated extraction capabilities including:
    - Cross-URL entity discovery and linking
    - Multiple extraction strategies
    - Entity validation and consistency checking
    - Relationship mapping between entities
    - Temporal and semantic analysis
    """
    
    def __init__(self):
        """Initialize multi-entity extraction service."""
        self.entity_linker = EntityLinker()
        self.entity_extractor = EntityExtractor()
        self.entity_validator = EntityValidator()
        self.extraction_stats = {"total_requests": 0, "successful_extractions": 0}
    
    async def extract_multi_entity(
        self, 
        request: MultiEntityExtractionRequest
    ) -> MultiEntityExtractionResult:
        """
        Perform multi-entity extraction across multiple URLs.
        
        Args:
            request: Multi-entity extraction request
            
        Returns:
            Comprehensive extraction results with entities and relationships
        """
        
        start_time = time.time()
        request_id = f"multi-extract-{int(time.time())}"
        self.extraction_stats["total_requests"] += 1
        
        logger.info("multi_entity_extraction_started",
                   request_id=request_id,
                   urls=len(request.urls),
                   strategy=request.extraction_strategy.value)
        
        try:
            # Step 1: Discover related URLs
            all_urls = request.urls.copy()
            
            if request.follow_links and len(request.urls) > 0:
                logger.info("discovering_related_urls", request_id=request_id)
                related_urls = await self.entity_linker.discover_related_urls(
                    request.urls,
                    request.extraction_strategy,
                    request.max_related_urls
                )
                
                # Add new URLs (avoid duplicates)
                for url in related_urls:
                    if url not in all_urls:
                        all_urls.append(url)
                
                logger.info("related_urls_discovered", 
                           request_id=request_id, 
                           total_urls=len(all_urls))
            
            # Step 2: Scrape all URLs
            logger.info("scraping_urls", request_id=request_id, urls=len(all_urls))
            scraped_contents = await self._scrape_urls(all_urls)
            
            successful_scrapes = [c for c in scraped_contents if c.extraction_success]
            logger.info("scraping_completed",
                       request_id=request_id,
                       successful=len(successful_scrapes),
                       failed=len(scraped_contents) - len(successful_scrapes))
            
            # Step 3: Extract entities from each URL
            logger.info("extracting_entities", request_id=request_id)
            all_entities = []
            
            for content in successful_scrapes:
                entities = await self.entity_extractor.extract_entities(
                    content, 
                    request.schema
                )
                all_entities.extend(entities)
            
            logger.info("entity_extraction_completed",
                       request_id=request_id,
                       entities_extracted=len(all_entities))
            
            # Step 4: Find relationships between entities
            logger.info("analyzing_entity_relationships", request_id=request_id)
            relationships = await self._analyze_relationships(all_entities, request)
            
            # Step 5: Validate entities if requested
            validation_results = {}
            if request.cross_validate:
                logger.info("validating_entities", request_id=request_id)
                validation_results = await self.entity_validator.validate_entities(
                    all_entities
                )
            
            # Step 6: Prepare extraction metadata
            extraction_metadata = {
                "urls_processed": len(all_urls),
                "urls_successful": len(successful_scrapes),
                "extraction_strategy": request.extraction_strategy.value,
                "schema_fields": list(request.schema.get("properties", {}).keys()),
                "processing_time": time.time() - start_time
            }
            
            processing_time = time.time() - start_time
            self.extraction_stats["successful_extractions"] += 1
            
            result = MultiEntityExtractionResult(
                request_id=request_id,
                entities=all_entities,
                relations=relationships,
                discovered_urls=all_urls,
                validation_results=validation_results,
                extraction_metadata=extraction_metadata,
                processing_time=processing_time,
                success=True
            )
            
            logger.info("multi_entity_extraction_completed",
                       request_id=request_id,
                       entities=len(all_entities),
                       relationships=len(relationships),
                       processing_time=processing_time)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error("multi_entity_extraction_failed",
                        request_id=request_id,
                        error=error_msg,
                        processing_time=processing_time)
            
            return MultiEntityExtractionResult(
                request_id=request_id,
                entities=[],
                relations=[],
                discovered_urls=request.urls,
                validation_results={},
                extraction_metadata={},
                processing_time=processing_time,
                success=False,
                errors=[error_msg]
            )
    
    async def _scrape_urls(self, urls: List[str]) -> List[ScrapedContent]:
        """Scrape multiple URLs efficiently."""
        
        scraping_service = await get_enhanced_scraping_service()
        
        # Configure scraping for entity extraction
        config = ScrapingConfig(
            urls=urls,
            extract_text=True,
            extract_links=True,
            extract_metadata=True,
            javascript_rendering=True,  # For dynamic content
            wait_time=2
        )
        
        # Scrape URLs in batches to manage resources
        batch_size = 10
        all_results = []
        
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            config.urls = batch_urls
            
            try:
                batch_results = await scraping_service.scrape_urls_enhanced(
                    batch_urls, config
                )
                all_results.extend(batch_results)
                
            except Exception as e:
                logger.warning("batch_scraping_failed", 
                             batch=i//batch_size + 1, 
                             error=str(e))
                
                # Add failed results
                for url in batch_urls:
                    all_results.append(ScrapedContent(
                        url=url,
                        extraction_success=False,
                        text="",
                        metadata=ContentMetadata()
                    ))
        
        return all_results
    
    async def _analyze_relationships(
        self, 
        entities: List[ExtractedEntity],
        request: MultiEntityExtractionRequest
    ) -> List[EntityRelation]:
        """Analyze relationships between entities."""
        
        relationships = []
        
        # Group entities by URL
        entities_by_url = {}
        for entity in entities:
            if entity.source_url not in entities_by_url:
                entities_by_url[entity.source_url] = []
            entities_by_url[entity.source_url].append(entity)
        
        # Find relationships within same URL (co-occurrence)
        for url, url_entities in entities_by_url.items():
            for i in range(len(url_entities)):
                for j in range(i + 1, len(url_entities)):
                    e1, e2 = url_entities[i], url_entities[j]
                    
                    relation = EntityRelation(
                        source_url=url,
                        target_url=url,
                        relation_type="co_occurrence",
                        confidence=0.6,
                        evidence=[f"Found together on {url}"]
                    )
                    relationships.append(relation)
        
        # Find relationships across URLs
        urls = list(entities_by_url.keys())
        for i in range(len(urls)):
            for j in range(i + 1, len(urls)):
                url1_entities = entities_by_url[urls[i]]
                url2_entities = entities_by_url[urls[j]]
                
                # Look for matching or similar entities
                for e1 in url1_entities:
                    for e2 in url2_entities:
                        if self._entities_related(e1, e2):
                            relation = EntityRelation(
                                source_url=urls[i],
                                target_url=urls[j],
                                relation_type="cross_reference",
                                confidence=0.8,
                                evidence=[f"Similar entities: {e1.value} <-> {e2.value}"]
                            )
                            relationships.append(relation)
        
        return relationships
    
    def _entities_related(self, e1: ExtractedEntity, e2: ExtractedEntity) -> bool:
        """Check if entities are related."""
        # Same type and similar values
        if e1.entity_type == e2.entity_type:
            if isinstance(e1.value, str) and isinstance(e2.value, str):
                # Simple similarity check
                return e1.value.lower() in e2.value.lower() or e2.value.lower() in e1.value.lower()
        
        return False
    
    async def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction service statistics."""
        return {
            "extraction_stats": self.extraction_stats,
            "cache_sizes": {
                "entity_extractor": len(self.entity_extractor.extraction_cache),
                "entity_linker": len(self.entity_linker.entity_cache)
            },
            "success_rate": (
                self.extraction_stats["successful_extractions"] / 
                max(1, self.extraction_stats["total_requests"])
            )
        }


# Singleton instance
_multi_entity_service: Optional[MultiEntityExtractionService] = None


async def get_multi_entity_service() -> MultiEntityExtractionService:
    """Get or create multi-entity extraction service instance."""
    global _multi_entity_service
    
    if _multi_entity_service is None:
        _multi_entity_service = MultiEntityExtractionService()
    
    return _multi_entity_service
