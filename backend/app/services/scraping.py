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
from app.utils.text_processing import (
    sanitize_text, 
    detect_language, 
    calculate_text_quality,
    extract_keywords
)
import structlog

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
            
        # Create tasks for concurrent scraping
        tasks = []
        for url in urls:
            task = self._scrape_single_url(url, config)
            tasks.append(task)
            
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
            
            # Scrape the URL
            return await self._scrape_url(url, config)
            
    async def _scrape_url(
        self, 
        url: str, 
        config: Optional[ScrapingConfig] = None
    ) -> ScrapedContent:
        """Scrape and extract content from a single URL."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Build request headers
            headers = dict(self._client.headers)
            if config and config.headers:
                headers.update(config.headers)
                
            # Make request
            response = await self._client.get(
                url,
                headers=headers,
                cookies=config.cookies if config else None
            )
            response.raise_for_status()
            
            # Detect encoding
            encoding = self._detect_encoding(response)
            html_content = response.content.decode(encoding, errors='ignore')
            
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
                
            # Detect language
            language = detect_language(extracted['text'])
            
            # Calculate quality score
            quality_score = calculate_text_quality(extracted['text'])
            
            # Calculate processing time
            extraction_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return ScrapedContent(
                url=url,
                title=extracted.get('title', metadata.title),
                text=extracted['text'],
                html=html_content if config and hasattr(config, 'include_html') and config.include_html else None,
                images=images,
                links=links,
                metadata=metadata,
                extraction_success=True,
                extraction_time_ms=extraction_time_ms,
                word_count=len(extracted['text'].split()),
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
                text_blocks.append((len(text), text, elem))
                
        if text_blocks:
            text_blocks.sort(reverse=True)
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
