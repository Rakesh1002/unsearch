"""
Content scraping service using BeautifulSoup4.
"""
import asyncio
import re
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import httpx
from httpx import AsyncClient, HTTPError, TimeoutException
from bs4 import BeautifulSoup, Comment
import chardet
# from readability import Readability  # Optional: install readability-lxml for better extraction
import json
from datetime import datetime
import hashlib

from app.config import get_settings
from app.models.responses import ScrapedContent, ContentMetadata
from app.models.requests import ScrapingConfig
from app.utils.text_processing import sanitize_text
from app.utils.text_processing import (
    sanitize_text, 
    detect_language, 
    calculate_text_quality,
    extract_keywords
)
import structlog
from app.services.core.cache import get_cache_service

logger = structlog.get_logger(__name__)
settings = get_settings()


class ContentScrapingService:
    """Service for web content extraction using BeautifulSoup4."""
    
    def __init__(self):
        self.user_agent = settings.scraping_user_agent
        self.timeout = settings.scraping_timeout
        self.max_concurrent = settings.scraping_max_concurrent
        self.respect_robots = settings.scraping_respect_robots_txt
        self.min_delay = settings.scraping_min_delay_seconds
        self._client: Optional[AsyncClient] = None
        self._robots_cache: Dict[str, RobotFileParser] = {}
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self):
        """Initialize HTTP client with connection pooling."""
        if not self._client:
            self._client = AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=50,
                ),
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                },
                follow_redirects=True,
                max_redirects=5
            )
            
            # Check Puppeteer service availability if enabled
            await self._check_puppeteer_health()
    
    async def _check_puppeteer_health(self):
        """Check if Puppeteer service is available for JS rendering."""
        puppeteer_enabled = getattr(settings, 'puppeteer_enabled', False)
        puppeteer_url = getattr(settings, 'puppeteer_service_url', None)
        
        if puppeteer_enabled and puppeteer_url:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                    resp = await client.get(f"{str(puppeteer_url).rstrip('/')}/health")
                    resp.raise_for_status()
                    logger.info("puppeteer_service_available", url=puppeteer_url)
            except Exception as e:
                logger.warning(
                    "puppeteer_service_unavailable",
                    url=puppeteer_url,
                    error=str(e),
                    message="JavaScript rendering will fall back to basic scraping"
                )
            
    async def close(self):
        """Close HTTP client connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
            
    async def scrape_urls(
        self, 
        urls: List[str], 
        config: Optional[ScrapingConfig] = None
    ) -> List[ScrapedContent]:
        """
        Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            config: Scraping configuration
            
        Returns:
            List of ScrapedContent objects
        """
        if not self._client:
            await self.initialize()
            
        # Per-host concurrency and rate limiting
        host_semaphores: Dict[str, asyncio.Semaphore] = {}
        host_last_hit: Dict[str, float] = {}
        per_host_concurrency = getattr(config, 'per_host_concurrency', 2) if config else 2
        hits_per_sec = getattr(config, 'hits_per_sec', 0.0) if config else 0.0

        loop = asyncio.get_event_loop()

        def get_host(url: str) -> str:
            try:
                return urlparse(url).netloc.lower()
            except Exception:
                return ""

        async def run_with_limits(url: str) -> ScrapedContent:
            host = get_host(url)
            if host and host not in host_semaphores:
                host_semaphores[host] = asyncio.Semaphore(max(1, per_host_concurrency))

            # Rate limiting per host
            if hits_per_sec and hits_per_sec > 0:
                min_interval = 1.0 / hits_per_sec
                last = host_last_hit.get(host, 0.0)
                now = loop.time()
                wait_for = (last + min_interval) - now
                if wait_for and wait_for > 0:
                    await asyncio.sleep(wait_for)

            if host:
                async with host_semaphores[host]:
                    host_last_hit[host] = loop.time()
                    return await self._scrape_single_url(url, config)
            else:
                host_last_hit[host] = loop.time()
                return await self._scrape_single_url(url, config)

        # Create tasks for concurrent scraping with host-aware throttling
        tasks = [run_with_limits(url) for url in urls]
            
        # Wait for all tasks with proper error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        scraped_contents = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "scraping_task_failed",
                    url=urls[idx],
                    error=str(result),
                    error_type=type(result).__name__
                )
                # Create error result
                scraped_contents.append(
                    ScrapedContent(
                        url=urls[idx],
                        title=None,
                        text="",
                        extraction_success=False,
                        extraction_time_ms=0,
                        word_count=0,
                        metadata=ContentMetadata(),
                        error_message=str(result),
                        content_quality_score=0.0
                    )
                )
            else:
                scraped_contents.append(result)
                
        return scraped_contents
        
    async def _scrape_single_url(
        self, 
        url: str, 
        config: Optional[ScrapingConfig] = None
    ) -> ScrapedContent:
        """Scrape a single URL with rate limiting."""
        async with self._semaphore:
            # JS rendering path: attempt Puppeteer microservice fetch
            if config and (config.javascript_rendering or config.js_mode) and settings.puppeteer_enabled:
                try:
                    page = await self._fetch_with_puppeteer(url, config)
                    if page:
                        return await self._scrape_page_payload(url, page["html"], config, page)
                except Exception as e:
                    logger.warning("puppeteer_fetch_failed", url=url, error=str(e))
                    # Fallback to HTTPX+BS4
            # Check robots.txt if enabled
            if self.respect_robots and not await self._check_robots_txt(url):
                logger.warning("scraping_blocked_by_robots", url=url)
                return ScrapedContent(
                    url=url,
                    title=None,
                    text="",
                    extraction_success=False,
                    extraction_time_ms=0,
                    word_count=0,
                    metadata=ContentMetadata(),
                    error_message="Blocked by robots.txt",
                    content_quality_score=0.0
                )
                
            # Add delay between requests
            await asyncio.sleep(self.min_delay)
            
            # Scrape the URL (HTTPX fetch)
            return await self._scrape_url(url, config)
            
    async def _scrape_url(
        self, 
        url: str, 
        config: Optional[ScrapingConfig] = None
    ) -> ScrapedContent:
        """Scrape and extract content from a single URL."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            html_content: Optional[str] = None
            cache_mode = getattr(config, 'cache_mode', 'enabled') if config else 'enabled'
            # Cache read
            if cache_mode in ("enabled", "read_only"):
                try:
                    cache = await get_cache_service()
                    cached_html = await cache.get_cached_url_content(url)
                    if cached_html:
                        html_content = cached_html
                        logger.info("url_cache_hit", url=url)
                except Exception as e:
                    logger.warning("url_cache_read_failed", url=url, error=str(e))
            # Build request headers
            headers = dict(self._client.headers)
            if config and config.headers:
                headers.update(config.headers)
                
            # Make request
            if not html_content:
                response = await self._client.get(
                    url,
                    headers=headers,
                    cookies=config.cookies if config else None
                )
                response.raise_for_status()
                
                # Detect encoding
                encoding = self._detect_encoding(response)
                html_content = response.content.decode(encoding, errors='ignore')
                # Cache write
                if cache_mode in ("enabled", "write_only") and config and getattr(config, 'cache_ttl', 0) > 0:
                    try:
                        cache = await get_cache_service()
                        await cache.set_cached_url_content(url, html_content, ttl=config.cache_ttl)
                        logger.info("url_cache_write", url=url)
                    except Exception as e:
                        logger.warning("url_cache_write_failed", url=url, error=str(e))
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()
                
            # Extract content based on configuration
            if config and config.selectors:
                extracted = await self._extract_with_selectors(soup, config.selectors)
            else:
                extracted = await self._extract_main_content(soup, url)
                
            # Extract metadata
            metadata = await self.extract_metadata(soup, url)
            
            # Extract images if requested
            images = []
            if not config or config.extract_images:
                images = self._extract_images(soup, url)
                
            # Extract links if requested
            links = []
            if not config or config.extract_links:
                links = self._extract_links(soup, url)
                # Optional link head enrichment and scoring
                if config and getattr(config, 'link_head', False) and links:
                    try:
                        links = await self._enrich_and_score_links(links, config)
                    except Exception as e:
                        logger.warning("link_enrichment_failed", url=url, error=str(e))
                
            # Detect language
            language = detect_language(extracted['text'])
            
            # Calculate quality score
            quality_score = calculate_text_quality(extracted['text'])
            
            # Calculate processing time
            extraction_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Optionally return Markdown format when requested via config.response_format
            if config and getattr(config, 'response_format', 'json') == 'markdown':
                markdown_text = self._to_markdown(html_content, base_url=str(url))
                # Overwrite text with markdown output for markdown mode
                text_out = markdown_text
            else:
                text_out = extracted['text']

            return ScrapedContent(
                url=url,
                title=extracted.get('title', metadata.title),
                text=text_out,
                html=html_content if config and hasattr(config, 'include_html') and config.include_html else None,
                images=images,
                links=links,
                metadata=metadata,
                extraction_success=True,
                extraction_time_ms=extraction_time_ms,
                word_count=len(text_out.split()) if text_out else 0,
                language_detected=language,
                content_quality_score=quality_score
            )
            
        except Exception as e:
            extraction_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            logger.error("scraping_error", url=url, error=str(e))
            
            return ScrapedContent(
                url=url,
                title=None,
                text="",
                extraction_success=False,
                extraction_time_ms=extraction_time_ms,
                word_count=0,
                metadata=ContentMetadata(),
                error_message=str(e),
                content_quality_score=0.0
            )

    async def _fetch_with_puppeteer(self, url: str, config: ScrapingConfig) -> Optional[Dict[str, Any]]:
        """Fetch page via Puppeteer microservice. Returns dict with html, screenshot, pdf, final_url."""
        client_timeout = config.wait_time + settings.puppeteer_timeout
        params = {
            "url": url,
            "waitUntil": config.wait_until or settings.puppeteer_default_wait_until,
            "timeout": settings.puppeteer_timeout * 1000,
            "screenshot": bool(getattr(config, "screenshot", False)),
            "pdf": bool(getattr(config, "pdf", False)),
            "userAgent": config.user_agent or self.user_agent,
        }
        if config.headers:
            params["headers"] = config.headers
        if config.cookies:
            params["cookies"] = config.cookies
        if getattr(config, "proxy", None):
            params["proxy"] = config.proxy

        service_url = str(settings.puppeteer_service_url).rstrip('/') + "/render"

        async with AsyncClient(timeout=httpx.Timeout(client_timeout)) as client:
            resp = await client.post(service_url, json=params)
            resp.raise_for_status()
            data = resp.json()
            return data

    async def _scrape_page_payload(self, url: str, html: str, config: ScrapingConfig, page_meta: Optional[Dict[str, Any]] = None) -> ScrapedContent:
        """Scrape using provided HTML payload (from Puppeteer)."""
        start_time = asyncio.get_event_loop().time()
        soup = BeautifulSoup(html or "", 'lxml')
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()

        if config and config.selectors:
            extracted = await self._extract_with_selectors(soup, config.selectors)
        else:
            extracted = await self._extract_main_content(soup, url)

        metadata = await self.extract_metadata(soup, url)

        images = []
        if not config or config.extract_images:
            images = self._extract_images(soup, url)

        links = []
        if not config or config.extract_links:
            links = self._extract_links(soup, url)
            # Optional link head enrichment and scoring
            if getattr(config, 'link_head', False) and links:
                try:
                    links = await self._enrich_and_score_links(links, config)
                except Exception as e:
                    logger.warning("link_enrichment_failed", url=url, error=str(e))

        # Optionally return Markdown
        if getattr(config, 'response_format', 'json') == 'markdown':
            markdown_text = self._to_markdown(html, base_url=str(url))
            text_out = markdown_text
        else:
            text_out = extracted['text']

        language = detect_language(text_out)
        quality_score = calculate_text_quality(text_out)
        extraction_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        html_out = html if config and getattr(config, 'include_html', False) else None
        return ScrapedContent(
            url=url,
            title=extracted.get('title', metadata.title),
            text=text_out,
            html=html_out,
            images=images,
            links=links,
            metadata=metadata,
            extraction_success=True,
            extraction_time_ms=extraction_time_ms,
            word_count=len(text_out.split()) if text_out else 0,
            language_detected=language,
            content_quality_score=quality_score
        )

    def _to_markdown(self, input_html: str, base_url: str = "") -> str:
        """Convert HTML to Markdown (simple) with absolute links. Lightweight alternative to crawl4ai's generator."""
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin
            soup = BeautifulSoup(input_html or "", 'lxml')
            # Remove script/style
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()
            # Convert links to absolute and inline markdown-like refs
            for a in soup.find_all('a', href=True):
                href = a['href']
                if base_url and not href.startswith(('http://', 'https://', 'mailto:')):
                    a['href'] = urljoin(base_url, href)
            text = soup.get_text('\n')
            text = sanitize_text(text)
            return text
        except Exception as e:
            logger.warning("markdown_conversion_failed", error=str(e))
            return sanitize_text(BeautifulSoup(input_html or "", 'lxml').get_text('\n'))

    async def _enrich_and_score_links(self, links: List[str], config: ScrapingConfig) -> List[str]:
        """Fetch HEAD/title for links and apply simple relevance scoring/filtering."""
        max_links = max(1, int(getattr(config, 'link_max', 100)))
        concurrency = max(1, int(getattr(config, 'link_enrichment_concurrency', 8)))
        timeout_s = max(1, int(getattr(config, 'link_timeout', 5)))
        query = getattr(config, 'link_score_query', None)
        threshold = getattr(config, 'link_score_threshold', None)

        targets = links[:max_links]
        sem = asyncio.Semaphore(concurrency)

        async def fetch_title(u: str) -> Dict[str, Any]:
            async with sem:
                try:
                    async with AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
                        resp = await client.get(u, headers={"Accept": "text/html,application/xhtml+xml"})
                        ok = resp.status_code < 400
                        title_text = ""
                        if ok and resp.headers.get("content-type", "").startswith("text/html"):
                            try:
                                s = BeautifulSoup(resp.text, 'lxml')
                                t = s.find('title')
                                if t:
                                    title_text = sanitize_text(t.get_text())
                            except Exception:
                                title_text = ""
                        return {"url": u, "ok": ok, "title": title_text}
                except Exception:
                    return {"url": u, "ok": False, "title": ""}

        results = await asyncio.gather(*[fetch_title(u) for u in targets])

        def score(item: Dict[str, Any]) -> float:
            if not item.get("ok"):
                return 0.0
            if not query:
                return 1.0
            terms = [t.lower() for t in str(query).split() if len(t) > 2]
            if not terms:
                return 1.0
            text = f"{item.get('title','')} {item.get('url','')}".lower()
            hits = sum(1 for t in terms if t in text)
            return min(1.0, hits / max(1, len(terms)))

        scored = [(score(item), item["url"]) for item in results]
        if threshold is not None:
            try:
                thr = float(threshold)
                scored = [s for s in scored if s[0] >= thr]
            except Exception:
                pass

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [u for _, u in scored]
            
    async def _extract_main_content(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """
        Extract main content using multiple strategies.
        
        Returns dict with 'title' and 'text' keys.
        """
        # Strategy 1: Try Readability algorithm (if available)
        # Uncomment if readability-lxml is installed
        # try:
        #     doc = Readability(str(soup))
        #     summary = doc.summary()
        #     summary_soup = BeautifulSoup(summary, 'lxml')
        #     
        #     return {
        #         'title': doc.title() or self._extract_title(soup),
        #         'text': sanitize_text(summary_soup.get_text())
        #     }
        # except:
        #     pass
            
        # Strategy 2: Look for common content containers
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '#content',
            '.content',
            '#main',
            '.main',
            'div.post',
            'div.entry-content',
            'div.article-body',
            'div.story-body'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                text = sanitize_text(content.get_text())
                if len(text) > 100:  # Minimum content length
                    return {
                        'title': self._extract_title(soup),
                        'text': text
                    }
                    
        # Strategy 3: Find largest text block
        text_blocks = []
        for elem in soup.find_all(['div', 'section', 'article']):
            text = sanitize_text(elem.get_text())
            if len(text) > 50:
                text_blocks.append((len(text), text))
                
        if text_blocks:
            # Sort by length descending (only need length and text, not elem)
            text_blocks.sort(key=lambda x: x[0], reverse=True)
            return {
                'title': self._extract_title(soup),
                'text': text_blocks[0][1]
            }
            
        # Fallback: Get all text
        return {
            'title': self._extract_title(soup),
            'text': sanitize_text(soup.get_text())
        }
        
    async def _extract_with_selectors(
        self, 
        soup: BeautifulSoup, 
        selectors: Dict[str, str]
    ) -> Dict[str, str]:
        """Extract content using custom CSS selectors."""
        result = {
            'title': '',
            'text': ''
        }
        
        # Extract title
        if 'title' in selectors:
            title_elem = soup.select_one(selectors['title'])
            if title_elem:
                result['title'] = sanitize_text(title_elem.get_text())
        else:
            result['title'] = self._extract_title(soup)
            
        # Extract main content
        if 'content' in selectors:
            content_elem = soup.select_one(selectors['content'])
            if content_elem:
                result['text'] = sanitize_text(content_elem.get_text())
        
        # Extract additional fields
        text_parts = []
        for field, selector in selectors.items():
            if field not in ['title', 'content']:
                elems = soup.select(selector)
                for elem in elems:
                    text = sanitize_text(elem.get_text())
                    if text:
                        text_parts.append(text)
                        
        # Combine all text
        if text_parts:
            if result['text']:
                result['text'] += '\n\n' + '\n'.join(text_parts)
            else:
                result['text'] = '\n'.join(text_parts)
                
        return result
        
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title using multiple strategies."""
        # Try standard title tag
        title_tag = soup.find('title')
        if title_tag:
            return sanitize_text(title_tag.get_text())
            
        # Try meta property
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return sanitize_text(meta_title['content'])
            
        # Try h1 tag
        h1_tag = soup.find('h1')
        if h1_tag:
            return sanitize_text(h1_tag.get_text())
            
        return "Untitled"
        
    async def extract_metadata(self, soup: BeautifulSoup, url: str) -> ContentMetadata:
        """Extract structured metadata from the page."""
        metadata = ContentMetadata()
        
        # Extract title
        metadata.title = self._extract_title(soup)
        
        # Extract description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            metadata.description = sanitize_text(meta_desc['content'])
            
        # Extract author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            metadata.author = sanitize_text(author_meta['content'])
            
        # Extract dates
        date_published = soup.find('meta', property='article:published_time')
        if date_published and date_published.get('content'):
            try:
                metadata.published_date = datetime.fromisoformat(date_published['content'].replace('Z', '+00:00'))
            except:
                pass
                
        # Extract keywords
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta and keywords_meta.get('content'):
            metadata.keywords = [k.strip() for k in keywords_meta['content'].split(',')]
            
        # Extract Open Graph data
        for meta in soup.find_all('meta', property=re.compile('^og:')):
            prop = meta.get('property', '').replace('og:', '')
            content = meta.get('content', '')
            if prop and content:
                metadata.og_data[prop] = content
                
        # Extract Twitter Card data
        for meta in soup.find_all('meta', attrs={'name': re.compile('^twitter:')}):
            name = meta.get('name', '').replace('twitter:', '')
            content = meta.get('content', '')
            if name and content:
                metadata.twitter_data[name] = content
                
        # Extract JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    metadata.json_ld = data
                    break
            except:
                pass
                
        return metadata
        
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all images from the page."""
        images = []
        seen = set()
        
        for img in soup.find_all(['img', 'picture']):
            # Try different attributes
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            
            if not src:
                # Check source tags within picture elements
                if img.name == 'picture':
                    source = img.find('source')
                    if source:
                        src = source.get('srcset', '').split()[0]
                        
            if src:
                # Make URL absolute
                abs_url = urljoin(base_url, src)
                
                # Skip if already seen or too small (likely tracking pixels)
                if abs_url not in seen and not self._is_tracking_pixel(abs_url, img):
                    seen.add(abs_url)
                    images.append(abs_url)
                    
        return images[:100]  # Limit to 100 images
        
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from the page."""
        links = []
        seen = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Make URL absolute
            abs_url = urljoin(base_url, href)
            
            # Skip anchors, javascript, and mail links
            if (abs_url not in seen and 
                not href.startswith(('#', 'javascript:', 'mailto:'))):
                seen.add(abs_url)
                links.append(abs_url)
                
        return links[:200]  # Limit to 200 links
        
    def _is_tracking_pixel(self, url: str, img_tag) -> bool:
        """Check if an image is likely a tracking pixel."""
        # Check dimensions
        width = img_tag.get('width', '').replace('px', '')
        height = img_tag.get('height', '').replace('px', '')
        
        try:
            if width and height:
                w, h = int(width), int(height)
                if w <= 3 or h <= 3:
                    return True
        except:
            pass
            
        # Check common tracking domains
        tracking_domains = [
            'google-analytics.com',
            'googletagmanager.com',
            'facebook.com/tr',
            'doubleclick.net',
            'scorecardresearch.com',
            'quantserve.com',
            'amazon-adsystem.com'
        ]
        
        return any(domain in url for domain in tracking_domains)
        
    async def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # Check cache
        if robots_url in self._robots_cache:
            robot_parser = self._robots_cache[robots_url]
            return robot_parser.can_fetch(self.user_agent, url)
            
        # Fetch and parse robots.txt
        try:
            robot_parser = RobotFileParser()
            robot_parser.set_url(robots_url)
            
            # Fetch robots.txt content
            response = await self._client.get(robots_url, timeout=5)
            if response.status_code == 200:
                robot_parser.parse(response.text.splitlines())
            else:
                # No robots.txt, allow all
                robot_parser.allow_all = True
                
            # Cache parser
            self._robots_cache[robots_url] = robot_parser
            
            return robot_parser.can_fetch(self.user_agent, url)
            
        except Exception as e:
            logger.warning("robots_txt_check_failed", url=robots_url, error=str(e))
            # On error, allow scraping
            return True
            
    def _detect_encoding(self, response: httpx.Response) -> str:
        """Detect response encoding using multiple methods."""
        # Try charset from Content-Type header
        content_type = response.headers.get('content-type', '')
        match = re.search(r'charset=([^;]+)', content_type)
        if match:
            return match.group(1).strip()
            
        # Try to detect from content
        detected = chardet.detect(response.content)
        if detected['encoding'] and detected['confidence'] > 0.7:
            return detected['encoding']
            
        # Default to UTF-8
        return 'utf-8'


# Singleton instance
_scraping_service: Optional[ContentScrapingService] = None


async def get_scraping_service() -> ContentScrapingService:
    """Get or create scraping service instance."""
    global _scraping_service
    
    if _scraping_service is None:
        _scraping_service = ContentScrapingService()
        await _scraping_service.initialize()
        
    return _scraping_service
