"""
Multi-engine scraping architecture inspired by Firecrawl.

Provides sophisticated engine selection and fallback capabilities for various content types.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import httpx
import structlog

from app.config import get_settings
from app.models.responses import ScrapedContent, ContentMetadata
from app.models.requests import ScrapingConfig
from app.services.scraping import ContentScrapingService
from app.utils.text_processing import sanitize_text, detect_language, calculate_text_quality

logger = structlog.get_logger(__name__)
settings = get_settings()


class EngineType(Enum):
    """Available scraping engines."""
    INDEX = "index"  # Pre-indexed content
    INDEX_DOCUMENTS = "index;documents"  # Pre-indexed documents
    FIRE_ENGINE_CDP = "fire-engine;chrome-cdp"
    FIRE_ENGINE_CDP_STEALTH = "fire-engine;chrome-cdp;stealth"
    FIRE_ENGINE_CDP_RETRY = "fire-engine(retry);chrome-cdp"  
    FIRE_ENGINE_CDP_RETRY_STEALTH = "fire-engine(retry);chrome-cdp;stealth"
    FIRE_ENGINE_PLAYWRIGHT = "fire-engine;playwright"
    FIRE_ENGINE_PLAYWRIGHT_STEALTH = "fire-engine;playwright;stealth"
    FIRE_ENGINE_TLSCLIENT = "fire-engine;tlsclient"
    FIRE_ENGINE_TLSCLIENT_STEALTH = "fire-engine;tlsclient;stealth"
    PLAYWRIGHT = "playwright"
    FETCH = "fetch"
    PDF = "pdf"
    DOCX = "docx"


@dataclass
class EngineCapabilities:
    """Capabilities supported by each engine."""
    actions: bool = False
    wait_for: bool = False
    screenshot: bool = False
    screenshot_full: bool = False
    pdf: bool = False
    docx: bool = False
    atsv: bool = False  # Accessibility tree structured view
    mobile: bool = False
    location: bool = False
    skip_tls_verification: bool = False
    use_fast_mode: bool = False
    stealth_proxy: bool = False
    disable_adblock: bool = False


@dataclass  
class EngineConfig:
    """Configuration for scraping engine."""
    engine_type: EngineType
    capabilities: EngineCapabilities
    quality: int  # Higher = preferred, negative = specialty
    max_reasonable_time: int  # Maximum reasonable processing time (ms)
    enabled: bool = True


@dataclass
class ScrapeRequest:
    """Enhanced scrape request with engine selection."""
    url: str
    config: ScrapingConfig
    preferred_engine: Optional[EngineType] = None
    required_capabilities: List[str] = field(default_factory=list)
    timeout: int = 30
    retries: int = 2


@dataclass
class ScrapeResult:
    """Enhanced scrape result with engine metadata."""
    content: ScrapedContent
    engine_used: EngineType
    processing_time: float
    attempts: int
    success: bool
    error: Optional[str] = None


class BaseEngine(ABC):
    """Abstract base class for scraping engines."""
    
    def __init__(self, engine_type: EngineType, config: EngineConfig):
        self.engine_type = engine_type
        self.config = config
        self.stats = {"requests": 0, "successes": 0, "failures": 0, "avg_time": 0.0}
    
    @abstractmethod
    async def scrape(self, request: ScrapeRequest) -> ScrapedContent:
        """Scrape content using this engine."""
        pass
    
    def can_handle(self, request: ScrapeRequest) -> bool:
        """Check if engine can handle the request."""
        # Check required capabilities
        for capability in request.required_capabilities:
            if not getattr(self.config.capabilities, capability, False):
                return False
        return True
    
    def update_stats(self, success: bool, processing_time: float):
        """Update engine statistics."""
        self.stats["requests"] += 1
        if success:
            self.stats["successes"] += 1
        else:
            self.stats["failures"] += 1
        
        # Update average time
        if self.stats["requests"] > 0:
            self.stats["avg_time"] = (
                (self.stats["avg_time"] * (self.stats["requests"] - 1) + processing_time) 
                / self.stats["requests"]
            )


class IndexEngine(BaseEngine):
    """Index-based scraping for pre-cached content."""
    
    def __init__(self):
        super().__init__(
            EngineType.INDEX,
            EngineConfig(
                engine_type=EngineType.INDEX,
                capabilities=EngineCapabilities(
                    wait_for=True,
                    screenshot=True, 
                    screenshot_full=True,
                    mobile=True,
                    location=True,
                    skip_tls_verification=True,
                    use_fast_mode=True
                ),
                quality=1000,  # Highest priority
                max_reasonable_time=2000
            )
        )
        self.client = httpx.AsyncClient(timeout=30)
    
    async def scrape(self, request: ScrapeRequest) -> ScrapedContent:
        """Scrape using index/cache."""
        start_time = time.time()
        
        try:
            # Check if we have cached content
            cached_content = await self._get_cached_content(request.url)
            if cached_content:
                processing_time = time.time() - start_time
                self.update_stats(True, processing_time)
                return cached_content
            
            # If not cached, fall back to fast scraping
            return await self._fast_scrape(request)
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(False, processing_time)
            raise e
    
    async def _get_cached_content(self, url: str) -> Optional[ScrapedContent]:
        """Check for cached content."""
        # Implementation would check Redis/database cache
        # For now, return None to indicate no cache
        return None
    
    async def _fast_scrape(self, request: ScrapeRequest) -> ScrapedContent:
        """Perform fast scraping."""
        response = await self.client.get(request.url)
        response.raise_for_status()
        
        # Basic content extraction
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Clean content
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()
        
        text = sanitize_text(soup.get_text())
        title = soup.find('title').get_text() if soup.find('title') else ""
        
        return ScrapedContent(
            url=request.url,
            title=title,
            text=text,
            html=response.text,
            extraction_success=True,
            word_count=len(text.split()) if text else 0,
            language_detected=detect_language(text),
            content_quality_score=calculate_text_quality(text),
            metadata=ContentMetadata()
        )


class FireEngineEngine(BaseEngine):
    """Fire Engine based scraping with multiple protocols."""
    
    def __init__(self, engine_type: EngineType):
        # Configure capabilities based on engine variant
        if "stealth" in engine_type.value:
            capabilities = EngineCapabilities(
                actions=True,
                wait_for=True,
                screenshot=True,
                screenshot_full=True,
                location=True,
                mobile=True,
                skip_tls_verification=True,
                stealth_proxy=True
            )
            quality = -2 if "retry" in engine_type.value else -1
        else:
            capabilities = EngineCapabilities(
                actions=True,
                wait_for=True,
                screenshot=True,
                screenshot_full=True,
                location=True,
                mobile=True,
                skip_tls_verification=True
            )
            quality = 45 if "retry" in engine_type.value else 50
        
        super().__init__(
            engine_type,
            EngineConfig(
                engine_type=engine_type,
                capabilities=capabilities,
                quality=quality,
                max_reasonable_time=60000,
                enabled=bool(getattr(settings, 'fire_engine_url', None))
            )
        )
        self.client = httpx.AsyncClient(timeout=120)
    
    async def scrape(self, request: ScrapeRequest) -> ScrapedContent:
        """Scrape using Fire Engine."""
        start_time = time.time()
        
        try:
            # Prepare Fire Engine request
            payload = {
                "url": request.url,
                "options": {
                    "engine": self._get_engine_protocol(),
                    "timeout": request.timeout * 1000,  # Convert to ms
                    "waitFor": getattr(request.config, 'wait_time', 0) * 1000,
                }
            }
            
            # Add stealth options if needed
            if "stealth" in self.engine_type.value:
                payload["options"]["stealth"] = True
                payload["options"]["antiDetection"] = True
            
            # Add mobile options if requested
            if getattr(request.config, 'mobile_mode', False):
                payload["options"]["mobile"] = True
            
            # Add screenshot if needed
            if getattr(request.config, 'screenshot', False):
                payload["options"]["screenshot"] = True
            
            fire_engine_url = getattr(settings, 'fire_engine_url', '')
            response = await self.client.post(
                f"{fire_engine_url}/scrape",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            scraped_content = self._process_fire_engine_response(data, request.url)
            
            processing_time = time.time() - start_time
            self.update_stats(True, processing_time)
            return scraped_content
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(False, processing_time)
            raise e
    
    def _get_engine_protocol(self) -> str:
        """Get the engine protocol for Fire Engine."""
        if "chrome-cdp" in self.engine_type.value:
            return "chrome-cdp"
        elif "playwright" in self.engine_type.value:
            return "playwright"
        elif "tlsclient" in self.engine_type.value:
            return "tlsclient"
        return "chrome-cdp"  # default
    
    def _process_fire_engine_response(self, data: Dict[str, Any], url: str) -> ScrapedContent:
        """Process Fire Engine response."""
        content = data.get("content", {})
        html = content.get("html", "")
        text = content.get("text", "")
        title = content.get("title", "")
        
        # Extract metadata
        metadata_dict = content.get("metadata", {})
        metadata = ContentMetadata(
            title=metadata_dict.get("title", title),
            description=metadata_dict.get("description", ""),
            author=metadata_dict.get("author"),
            published_date=metadata_dict.get("publishedDate"),
            keywords=metadata_dict.get("keywords", [])
        )
        
        return ScrapedContent(
            url=url,
            title=title,
            text=text,
            html=html,
            extraction_success=True,
            word_count=len(text.split()) if text else 0,
            language_detected=detect_language(text),
            content_quality_score=calculate_text_quality(text),
            metadata=metadata,
            screenshots=content.get("screenshots", []) if content.get("screenshots") else None
        )


class PlaywrightEngine(BaseEngine):
    """Playwright-based scraping engine."""
    
    def __init__(self):
        super().__init__(
            EngineType.PLAYWRIGHT,
            EngineConfig(
                engine_type=EngineType.PLAYWRIGHT,
                capabilities=EngineCapabilities(
                    wait_for=True,
                    screenshot=True,
                    screenshot_full=True,
                    disable_adblock=True
                ),
                quality=35,
                max_reasonable_time=45000,
                enabled=bool(getattr(settings, 'playwright_service_url', None))
            )
        )
        self.client = httpx.AsyncClient(timeout=60)
    
    async def scrape(self, request: ScrapeRequest) -> ScrapedContent:
        """Scrape using Playwright service."""
        start_time = time.time()
        
        try:
            payload = {
                "url": request.url,
                "options": {
                    "waitTime": getattr(request.config, 'wait_time', 0) * 1000,
                    "timeout": request.timeout * 1000,
                }
            }
            
            if getattr(request.config, 'screenshot', False):
                payload["options"]["screenshot"] = True
            
            playwright_url = getattr(settings, 'playwright_service_url', '')
            response = await self.client.post(
                f"{playwright_url}/scrape",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            scraped_content = self._process_playwright_response(data, request.url)
            
            processing_time = time.time() - start_time
            self.update_stats(True, processing_time)
            return scraped_content
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(False, processing_time)
            raise e
    
    def _process_playwright_response(self, data: Dict[str, Any], url: str) -> ScrapedContent:
        """Process Playwright response."""
        html = data.get("html", "")
        text = data.get("text", "")
        title = data.get("title", "")
        
        return ScrapedContent(
            url=url,
            title=title,
            text=text,
            html=html,
            extraction_success=True,
            word_count=len(text.split()) if text else 0,
            language_detected=detect_language(text),
            content_quality_score=calculate_text_quality(text),
            metadata=ContentMetadata(),
            screenshots=data.get("screenshots", []) if data.get("screenshots") else None
        )


class FetchEngine(BaseEngine):
    """Simple HTTP fetch engine for basic scraping."""
    
    def __init__(self):
        super().__init__(
            EngineType.FETCH,
            EngineConfig(
                engine_type=EngineType.FETCH,
                capabilities=EngineCapabilities(use_fast_mode=True),
                quality=10,  # Low quality, fallback option
                max_reasonable_time=10000
            )
        )
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
    
    async def scrape(self, request: ScrapeRequest) -> ScrapedContent:
        """Scrape using basic HTTP fetch."""
        start_time = time.time()
        
        try:
            response = await self.client.get(request.url)
            response.raise_for_status()
            
            # Use existing scraping service for processing
            basic_service = ContentScrapingService()
            scraped_content = await basic_service._scrape_single_url(request.url, request.config)
            
            processing_time = time.time() - start_time
            self.update_stats(True, processing_time)
            return scraped_content
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(False, processing_time)
            raise e


class PDFEngine(BaseEngine):
    """PDF document processing engine."""
    
    def __init__(self):
        super().__init__(
            EngineType.PDF,
            EngineConfig(
                engine_type=EngineType.PDF,
                capabilities=EngineCapabilities(pdf=True),
                quality=-10,  # Specialty engine
                max_reasonable_time=30000
            )
        )
        self.client = httpx.AsyncClient(timeout=60)
    
    async def scrape(self, request: ScrapeRequest) -> ScrapedContent:
        """Scrape PDF content."""
        start_time = time.time()
        
        try:
            # Download PDF
            response = await self.client.get(request.url)
            response.raise_for_status()
            
            # Extract text from PDF (would need PyPDF2 or similar)
            # For now, simplified implementation
            text = f"PDF content from {request.url}"
            title = request.url.split('/')[-1]
            
            scraped_content = ScrapedContent(
                url=request.url,
                title=title,
                text=text,
                extraction_success=True,
                word_count=len(text.split()),
                language_detected=detect_language(text),
                content_quality_score=calculate_text_quality(text),
                metadata=ContentMetadata(content_type="application/pdf")
            )
            
            processing_time = time.time() - start_time
            self.update_stats(True, processing_time)
            return scraped_content
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.update_stats(False, processing_time)
            raise e


class MultiEngineScrapingService:
    """
    Multi-engine scraping service with intelligent engine selection.
    
    Provides automatic engine selection based on:
    - URL content type detection
    - Required capabilities
    - Engine availability and performance
    - Fallback strategies
    """
    
    def __init__(self):
        """Initialize multi-engine scraping service."""
        self.engines: Dict[EngineType, BaseEngine] = {}
        self._initialize_engines()
        self.usage_stats = {"total_requests": 0, "successful_requests": 0}
    
    def _initialize_engines(self):
        """Initialize all available engines."""
        # Index engines (highest priority)
        self.engines[EngineType.INDEX] = IndexEngine()
        
        # Fire Engine variants (if available)
        fire_engine_types = [
            EngineType.FIRE_ENGINE_CDP,
            EngineType.FIRE_ENGINE_CDP_STEALTH,
            EngineType.FIRE_ENGINE_CDP_RETRY,
            EngineType.FIRE_ENGINE_CDP_RETRY_STEALTH,
            EngineType.FIRE_ENGINE_PLAYWRIGHT,
            EngineType.FIRE_ENGINE_PLAYWRIGHT_STEALTH,
            EngineType.FIRE_ENGINE_TLSCLIENT,
            EngineType.FIRE_ENGINE_TLSCLIENT_STEALTH,
        ]
        
        for engine_type in fire_engine_types:
            engine = FireEngineEngine(engine_type)
            if engine.config.enabled:
                self.engines[engine_type] = engine
        
        # Playwright (if available)
        playwright_engine = PlaywrightEngine()
        if playwright_engine.config.enabled:
            self.engines[EngineType.PLAYWRIGHT] = playwright_engine
        
        # Specialty engines
        self.engines[EngineType.PDF] = PDFEngine()
        
        # Fetch engine (always available as fallback)
        self.engines[EngineType.FETCH] = FetchEngine()
        
        logger.info("multi_engine_initialized", 
                   engines=list(self.engines.keys()),
                   total_engines=len(self.engines))
    
    async def scrape(
        self,
        url: str,
        config: ScrapingConfig,
        preferred_engine: Optional[EngineType] = None,
        required_capabilities: List[str] = None
    ) -> ScrapeResult:
        """
        Scrape URL using the best available engine.
        
        Args:
            url: URL to scrape
            config: Scraping configuration
            preferred_engine: Preferred engine type
            required_capabilities: Required engine capabilities
            
        Returns:
            ScrapeResult with content and metadata
        """
        request = ScrapeRequest(
            url=url,
            config=config,
            preferred_engine=preferred_engine,
            required_capabilities=required_capabilities or []
        )
        
        self.usage_stats["total_requests"] += 1
        
        # Select appropriate engine
        selected_engines = await self._select_engines(request)
        
        if not selected_engines:
            logger.error("no_suitable_engine_found", url=url, capabilities=required_capabilities)
            return ScrapeResult(
                content=ScrapedContent(url=url, extraction_success=False, text=""),
                engine_used=EngineType.FETCH,
                processing_time=0,
                attempts=0,
                success=False,
                error="No suitable engine found"
            )
        
        # Try engines in order
        last_error = None
        attempts = 0
        
        for engine_type in selected_engines:
            engine = self.engines[engine_type]
            attempts += 1
            
            try:
                logger.info("attempting_scrape", url=url, engine=engine_type.value, attempt=attempts)
                start_time = time.time()
                
                content = await engine.scrape(request)
                processing_time = time.time() - start_time
                
                self.usage_stats["successful_requests"] += 1
                
                return ScrapeResult(
                    content=content,
                    engine_used=engine_type,
                    processing_time=processing_time,
                    attempts=attempts,
                    success=True
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning("engine_failed", 
                             url=url, 
                             engine=engine_type.value, 
                             error=str(e))
                continue
        
        # All engines failed
        return ScrapeResult(
            content=ScrapedContent(url=url, extraction_success=False, text=""),
            engine_used=selected_engines[0] if selected_engines else EngineType.FETCH,
            processing_time=0,
            attempts=attempts,
            success=False,
            error=last_error or "All engines failed"
        )
    
    async def _select_engines(self, request: ScrapeRequest) -> List[EngineType]:
        """Select appropriate engines based on request requirements."""
        suitable_engines = []
        
        # Check if user prefers a specific engine
        if request.preferred_engine and request.preferred_engine in self.engines:
            engine = self.engines[request.preferred_engine]
            if engine.can_handle(request):
                suitable_engines.append(request.preferred_engine)
        
        # Find all suitable engines
        for engine_type, engine in self.engines.items():
            if engine_type == request.preferred_engine:
                continue  # Already added
            
            if engine.can_handle(request):
                suitable_engines.append(engine_type)
        
        # Sort by quality (higher quality first)
        suitable_engines.sort(key=lambda e: self.engines[e].config.quality, reverse=True)
        
        # Special handling for specific content types
        url_lower = request.url.lower()
        if url_lower.endswith('.pdf'):
            # Prioritize PDF engine
            if EngineType.PDF in suitable_engines:
                suitable_engines.remove(EngineType.PDF)
                suitable_engines.insert(0, EngineType.PDF)
        
        return suitable_engines
    
    async def get_engine_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        engine_stats = {}
        for engine_type, engine in self.engines.items():
            engine_stats[engine_type.value] = {
                "config": {
                    "quality": engine.config.quality,
                    "max_reasonable_time": engine.config.max_reasonable_time,
                    "enabled": engine.config.enabled
                },
                "stats": engine.stats,
                "capabilities": {
                    field.name: getattr(engine.config.capabilities, field.name)
                    for field in engine.config.capabilities.__dataclass_fields__.values()
                }
            }
        
        return {
            "engines": engine_stats,
            "usage_stats": self.usage_stats,
            "total_engines": len(self.engines)
        }
    
    async def cleanup(self):
        """Cleanup all engine resources."""
        for engine in self.engines.values():
            if hasattr(engine, 'client') and engine.client:
                await engine.client.aclose()


# Singleton instance
_multi_engine_service: Optional[MultiEngineScrapingService] = None


async def get_multi_engine_service() -> MultiEngineScrapingService:
    """Get or create multi-engine scraping service instance."""
    global _multi_engine_service
    
    if _multi_engine_service is None:
        _multi_engine_service = MultiEngineScrapingService()
    
    return _multi_engine_service
