"""
Playwright-based web scraping service for JavaScript-rendered pages.

This module provides a fallback scraping mechanism for pages that require
JavaScript rendering, implementing anti-bot detection strategies.
"""
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urljoin
import structlog

from app.config import get_settings
from app.models.responses import ScrapedContent, ContentMetadata
from app.utils.text_processing import sanitize_text, detect_language, calculate_text_quality

logger = structlog.get_logger(__name__)
settings = get_settings()

# Check if playwright is available
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("playwright_not_installed", message="Install with: pip install playwright && playwright install chromium")


@dataclass
class PlaywrightConfig:
    """Configuration for Playwright scraping."""
    headless: bool = True
    timeout_ms: int = 30000
    wait_for_selector: Optional[str] = None
    wait_for_timeout_ms: int = 2000
    block_resources: List[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: Optional[str] = None
    
    def __post_init__(self):
        if self.block_resources is None:
            self.block_resources = ["image", "stylesheet", "font", "media"]


# Rotating user agents for anti-bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class PlaywrightScrapingService:
    """
    Service for scraping JavaScript-rendered pages using Playwright.
    
    Features:
    - Headless browser automation
    - Anti-bot detection measures
    - Resource blocking for performance
    - Automatic retry with different strategies
    - Content extraction from dynamic pages
    """
    
    def __init__(self, config: Optional[PlaywrightConfig] = None):
        self.config = config or PlaywrightConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._semaphore = asyncio.Semaphore(3)  # Limit concurrent browser contexts
        self._user_agent_index = 0
        
    async def initialize(self):
        """Initialize Playwright browser."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("playwright_not_available")
            return
            
        if self._browser is not None:
            return
            
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    '--disable-web-security',
                ]
            )
            logger.info("playwright_browser_initialized")
        except Exception as e:
            logger.error("playwright_init_failed", error=str(e))
            
    async def close(self):
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            
    def _get_user_agent(self) -> str:
        """Get rotating user agent."""
        ua = USER_AGENTS[self._user_agent_index % len(USER_AGENTS)]
        self._user_agent_index += 1
        return ua
        
    async def scrape_url(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        wait_timeout_ms: int = 2000,
        extract_images: bool = True,
        extract_links: bool = True
    ) -> ScrapedContent:
        """
        Scrape a single URL using Playwright.
        
        Args:
            url: URL to scrape
            wait_for_selector: CSS selector to wait for before extraction
            wait_timeout_ms: Timeout for waiting on selector
            extract_images: Whether to extract images
            extract_links: Whether to extract links
            
        Returns:
            ScrapedContent with extracted data
        """
        if not PLAYWRIGHT_AVAILABLE or not self._browser:
            return ScrapedContent(
                url=url,
                title=None,
                text="",
                extraction_success=False,
                extraction_time_ms=0,
                word_count=0,
                metadata=ContentMetadata(),
                error_message="Playwright not available",
                content_quality_score=0.0
            )
            
        start_time = asyncio.get_event_loop().time()
        
        async with self._semaphore:
            context = None
            page = None
            
            try:
                # Create browser context with anti-detection measures
                context = await self._browser.new_context(
                    viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height},
                    user_agent=self.config.user_agent or self._get_user_agent(),
                    java_script_enabled=True,
                    ignore_https_errors=True,
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                
                # Block unnecessary resources for performance
                await context.route("**/*", self._route_handler)
                
                page = await context.new_page()
                
                # Add stealth scripts to avoid detection
                await self._add_stealth_scripts(page)
                
                # Navigate to page
                response = await page.goto(
                    url,
                    timeout=self.config.timeout_ms,
                    wait_until='domcontentloaded'
                )
                
                if not response or response.status >= 400:
                    return ScrapedContent(
                        url=url,
                        title=None,
                        text="",
                        extraction_success=False,
                        extraction_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                        word_count=0,
                        metadata=ContentMetadata(),
                        error_message=f"HTTP {response.status if response else 'No response'}",
                        content_quality_score=0.0
                    )
                    
                # Wait for content to load
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=wait_timeout_ms)
                    except PlaywrightTimeout:
                        logger.warning("wait_for_selector_timeout", url=url, selector=wait_for_selector)
                else:
                    # Default wait for network idle
                    try:
                        await page.wait_for_load_state('networkidle', timeout=wait_timeout_ms)
                    except PlaywrightTimeout:
                        pass  # Continue with extraction
                        
                # Extract content
                content = await self._extract_content(page, url, extract_images, extract_links)
                
                extraction_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                
                return ScrapedContent(
                    url=url,
                    title=content.get('title'),
                    text=content.get('text', ''),
                    images=content.get('images', []),
                    links=content.get('links', []),
                    metadata=ContentMetadata(
                        title=content.get('title'),
                        description=content.get('description'),
                        og_data=content.get('og_data', {}),
                    ),
                    extraction_success=True,
                    extraction_time_ms=extraction_time_ms,
                    word_count=len(content.get('text', '').split()),
                    language_detected=detect_language(content.get('text', '')),
                    content_quality_score=calculate_text_quality(content.get('text', ''))
                )
                
            except PlaywrightTimeout as e:
                logger.error("playwright_timeout", url=url, error=str(e))
                return ScrapedContent(
                    url=url,
                    title=None,
                    text="",
                    extraction_success=False,
                    extraction_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                    word_count=0,
                    metadata=ContentMetadata(),
                    error_message=f"Timeout: {str(e)}",
                    content_quality_score=0.0
                )
                
            except Exception as e:
                logger.error("playwright_scrape_error", url=url, error=str(e))
                return ScrapedContent(
                    url=url,
                    title=None,
                    text="",
                    extraction_success=False,
                    extraction_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000),
                    word_count=0,
                    metadata=ContentMetadata(),
                    error_message=str(e),
                    content_quality_score=0.0
                )
                
            finally:
                if page:
                    await page.close()
                if context:
                    await context.close()
                    
    async def _route_handler(self, route):
        """Handle resource blocking for performance."""
        resource_type = route.request.resource_type
        
        if resource_type in self.config.block_resources:
            await route.abort()
        else:
            await route.continue_()
            
    async def _add_stealth_scripts(self, page: Page):
        """Add stealth scripts to avoid bot detection."""
        # Override webdriver property
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
    async def _extract_content(
        self,
        page: Page,
        base_url: str,
        extract_images: bool,
        extract_links: bool
    ) -> Dict[str, Any]:
        """Extract content from page."""
        content = {}
        
        # Extract title
        content['title'] = await page.title()
        
        # Extract meta description
        try:
            description = await page.eval_on_selector(
                'meta[name="description"]',
                'el => el.content'
            )
            content['description'] = description
        except:
            content['description'] = None
            
        # Extract Open Graph data
        og_data = {}
        try:
            og_elements = await page.query_selector_all('meta[property^="og:"]')
            for el in og_elements:
                prop = await el.get_attribute('property')
                value = await el.get_attribute('content')
                if prop and value:
                    og_data[prop.replace('og:', '')] = value
        except:
            pass
        content['og_data'] = og_data
        
        # Extract main content using multiple strategies
        content['text'] = await self._extract_main_text(page)
        
        # Extract images
        if extract_images:
            content['images'] = await self._extract_images(page, base_url)
            
        # Extract links
        if extract_links:
            content['links'] = await self._extract_links(page, base_url)
            
        return content
        
    async def _extract_main_text(self, page: Page) -> str:
        """Extract main text content from page."""
        # Remove unwanted elements
        await page.evaluate("""
            const selectors = [
                'script', 'style', 'noscript', 'iframe',
                'nav', 'header', 'footer', 'aside',
                '.nav', '.navbar', '.sidebar', '.footer', '.header',
                '.advertisement', '.ad', '.ads', '.cookie-banner',
                '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]'
            ];
            selectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => el.remove());
            });
        """)
        
        # Try to find main content container
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '#content',
            '.content',
            '#main',
            '.main',
            '.post-content',
            '.entry-content',
            '.article-body',
            '.story-body'
        ]
        
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    text = sanitize_text(text)
                    if len(text) > 100:
                        return text
            except:
                continue
                
        # Fallback to body text
        try:
            body = await page.query_selector('body')
            if body:
                text = await body.inner_text()
                return sanitize_text(text)
        except:
            pass
            
        return ""
        
    async def _extract_images(self, page: Page, base_url: str) -> List[str]:
        """Extract images from page."""
        images = []
        
        try:
            img_elements = await page.query_selector_all('img')
            
            for img in img_elements[:50]:  # Limit to 50 images
                src = await img.get_attribute('src') or await img.get_attribute('data-src')
                
                if src:
                    # Make absolute URL
                    if not src.startswith(('http://', 'https://', '//')):
                        src = urljoin(base_url, src)
                    elif src.startswith('//'):
                        src = 'https:' + src
                        
                    # Skip tracking pixels and icons
                    width = await img.get_attribute('width')
                    height = await img.get_attribute('height')
                    
                    try:
                        if width and height:
                            if int(width.replace('px', '')) <= 3 or int(height.replace('px', '')) <= 3:
                                continue
                    except:
                        pass
                        
                    images.append(src)
                    
        except Exception as e:
            logger.warning("image_extraction_error", error=str(e))
            
        return list(set(images))  # Remove duplicates
        
    async def _extract_links(self, page: Page, base_url: str) -> List[str]:
        """Extract links from page."""
        links = []
        
        try:
            link_elements = await page.query_selector_all('a[href]')
            
            for link in link_elements[:100]:  # Limit to 100 links
                href = await link.get_attribute('href')
                
                if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    # Make absolute URL
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(base_url, href)
                        
                    links.append(href)
                    
        except Exception as e:
            logger.warning("link_extraction_error", error=str(e))
            
        return list(set(links))  # Remove duplicates
        
    async def scrape_urls(
        self,
        urls: List[str],
        wait_for_selector: Optional[str] = None,
        extract_images: bool = False,
        extract_links: bool = False
    ) -> List[ScrapedContent]:
        """
        Scrape multiple URLs in parallel.
        
        Args:
            urls: URLs to scrape
            wait_for_selector: Optional selector to wait for
            extract_images: Whether to extract images
            extract_links: Whether to extract links
            
        Returns:
            List of ScrapedContent objects
        """
        if not self._browser:
            await self.initialize()
            
        tasks = [
            self.scrape_url(
                url=url,
                wait_for_selector=wait_for_selector,
                extract_images=extract_images,
                extract_links=extract_links
            )
            for url in urls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        scraped = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error("playwright_batch_error", url=url, error=str(result))
                scraped.append(ScrapedContent(
                    url=url,
                    title=None,
                    text="",
                    extraction_success=False,
                    extraction_time_ms=0,
                    word_count=0,
                    metadata=ContentMetadata(),
                    error_message=str(result),
                    content_quality_score=0.0
                ))
            else:
                scraped.append(result)
                
        return scraped


# Singleton instance
_playwright_service: Optional[PlaywrightScrapingService] = None


async def get_playwright_service() -> PlaywrightScrapingService:
    """Get or create Playwright scraping service instance."""
    global _playwright_service
    
    if _playwright_service is None:
        _playwright_service = PlaywrightScrapingService()
        await _playwright_service.initialize()
        
    return _playwright_service
