"""
Enhanced content scraping service with crawl4ai-inspired capabilities.

This service integrates all the sophisticated features:
- Advanced extraction strategies
- Content filtering
- Enhanced markdown generation  
- Adaptive crawling
- Virtual scrolling
- Link analysis
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup

from app.config import get_settings
from app.models.responses import ScrapedContent, ContentMetadata
from app.models.requests import (
    ScrapingConfig, ExtractionStrategyConfig, ContentFilterConfig,
    MarkdownConfig, AdaptiveCrawlConfig, VirtualScrollConfig, LinkAnalysisConfig
)
from app.services.scraping import ContentScrapingService
from app.services.extraction.extraction_strategies import create_extraction_strategy
from app.services.extraction.content_filters import create_content_filter
from app.services.scraping.markdown_generation import DefaultMarkdownGenerator
from app.services.crawling.adaptive_crawling import create_adaptive_crawler
from app.services.crawling.virtual_scrolling import PuppeteerVirtualScroller
from app.services.extraction.link_analysis import LinkAnalyzer, LinkPreviewConfig
from app.services.extraction.chunking_strategies import create_chunking_strategy
from app.services.extraction.table_extraction import create_table_extraction_strategy
from app.services.automation.browser_config import BrowserConfig, create_browser_config_from_env
from app.services.infrastructure.dispatcher import create_dispatcher
from app.services.crawling.url_seeder import URLSeeder, SeedingConfig
from app.utils.text_processing import sanitize_text, detect_language, calculate_text_quality

logger = structlog.get_logger(__name__)
settings = get_settings()


class EnhancedScrapingService(ContentScrapingService):
    """Enhanced scraping service with crawl4ai-inspired features."""
    
    def __init__(self):
        """Initialize enhanced scraping service."""
        super().__init__()
        
        # Initialize advanced components
        self.markdown_generator = None
        self.adaptive_crawler = None
        self.virtual_scroller = None
        self.link_analyzer = None
        self.url_seeder = None
        self.dispatcher = None
        self.browser_config = None
        
        # Initialize dispatcher for concurrent operations
        self.dispatcher = create_dispatcher(
            dispatcher_type="memory_adaptive",
            max_concurrent=settings.scraping_max_concurrent
        )
    
    async def scrape_urls_enhanced(
        self,
        urls: List[str],
        config: Optional[ScrapingConfig] = None
    ) -> List[ScrapedContent]:
        """
        Enhanced URL scraping with all advanced features.
        
        Args:
            urls: List of URLs to scrape
            config: Enhanced scraping configuration
            
        Returns:
            List of enhanced ScrapedContent objects
        """
        if not config:
            # Use basic scraping if no advanced config provided
            return await super().scrape_urls(urls, config)
        
        logger.info(
            "enhanced_scraping_started",
            urls=len(urls),
            extraction_strategy=getattr(config, 'extraction_strategy', 'none'),
            content_filter=getattr(config, 'content_filter', 'none')
        )
        
        # Check if adaptive crawling is enabled
        if getattr(config, 'adaptive_crawling', False) and len(urls) == 1:
            return await self._adaptive_crawl_single_url(urls[0], config)
        
        # Process URLs with standard enhanced processing
        scraped_contents = []
        
        for url in urls:
            try:
                scraped_content = await self._scrape_single_url_enhanced(url, config)
                scraped_contents.append(scraped_content)
            except Exception as e:
                logger.error("enhanced_scraping_failed", url=url, error=str(e))
                # Create error result
                scraped_contents.append(
                    ScrapedContent(
                        url=url,
                        title=None,
                        text="",
                        extraction_success=False,
                        extraction_time_ms=0,
                        word_count=0,
                        metadata=ContentMetadata(),
                        error_message=str(e),
                        content_quality_score=0.0
                    )
                )
        
        return scraped_contents
    
    async def _scrape_single_url_enhanced(
        self,
        url: str,
        config: ScrapingConfig
    ) -> ScrapedContent:
        """Scrape single URL with all enhancements applied."""
        start_time = time.time()
        
        # Step 1: Basic content extraction
        if getattr(config, 'virtual_scrolling', False):
            # Use virtual scrolling for infinite pages
            basic_result = await self._scrape_with_virtual_scrolling(url, config)
        else:
            # Standard scraping
            basic_result = await super()._scrape_single_url(url, config)
        
        if not basic_result.extraction_success:
            return basic_result
        
        # Step 2: Apply extraction strategy
        extracted_content = await self._apply_extraction_strategy(
            url, basic_result.html or basic_result.text, config
        )
        
        # Step 3: Apply content filtering
        filtered_content = await self._apply_content_filtering(
            basic_result.html or basic_result.text, config
        )
        
        # Step 4: Generate enhanced markdown
        markdown_result = await self._generate_enhanced_markdown(
            filtered_content or basic_result.html or basic_result.text, url, config
        )
        
        # Step 5: Perform link analysis
        link_analysis_result = await self._analyze_links(
            basic_result.html or basic_result.text, url, config
        )
        
        # Step 6: Combine all results into enhanced ScrapedContent
        enhanced_result = await self._combine_enhanced_results(
            basic_result, extracted_content, filtered_content,
            markdown_result, link_analysis_result, config
        )
        
        processing_time = time.time() - start_time
        enhanced_result.extraction_time_ms = int(processing_time * 1000)
        
        logger.info(
            "enhanced_scraping_completed",
            url=url,
            processing_time=processing_time,
            extraction_strategy=getattr(config, 'extraction_strategy', 'none'),
            content_filter=getattr(config, 'content_filter', 'none')
        )
        
        return enhanced_result
    
    async def _scrape_with_virtual_scrolling(
        self,
        url: str,
        config: ScrapingConfig
    ) -> ScrapedContent:
        """Scrape URL with virtual scrolling for infinite pages."""
        try:
            # Parse virtual scroll configuration
            virtual_config = getattr(config, 'virtual_scroll_config', {})
            from app.services.crawling.virtual_scrolling import VirtualScrollConfig
            
            scroll_config = VirtualScrollConfig(**virtual_config)
            
            # Initialize virtual scroller
            if not self.virtual_scroller:
                self.virtual_scroller = PuppeteerVirtualScroller(
                    str(settings.puppeteer_service_url)
                )
            
            # Perform virtual scrolling
            scroll_result = await self.virtual_scroller.scroll_and_extract(
                url=url,
                config=scroll_config,
                headers=getattr(config, 'headers', None)
            )
            
            if scroll_result.success:
                # Convert virtual scroll result to ScrapedContent
                soup = BeautifulSoup(scroll_result.final_content, 'lxml')
                
                # Extract metadata
                metadata = await super().extract_metadata(soup, url)
                
                # Extract images and links
                images = super()._extract_images(soup, url) if getattr(config, 'extract_images', True) else []
                links = super()._extract_links(soup, url) if getattr(config, 'extract_links', True) else []
                
                # Get clean text
                for element in soup(['script', 'style', 'noscript']):
                    element.decompose()
                text = sanitize_text(soup.get_text())
                
                return ScrapedContent(
                    url=url,
                    title=soup.find('title').get_text() if soup.find('title') else metadata.title,
                    text=text,
                    html=scroll_result.final_content,
                    images=images,
                    links=links,
                    metadata=metadata,
                    extraction_success=True,
                    extraction_time_ms=int(scroll_result.performance_metrics.get('total_time', 0) * 1000),
                    word_count=len(text.split()) if text else 0,
                    language_detected=detect_language(text),
                    content_quality_score=calculate_text_quality(text),
                    # Add virtual scrolling metadata
                    **{
                        'virtual_scrolling_metadata': scroll_result.scroll_metadata,
                        'performance_metrics': scroll_result.performance_metrics
                    }
                )
            else:
                # Fallback to regular scraping
                return await super()._scrape_single_url(url, config)
                
        except Exception as e:
            logger.error("virtual_scrolling_failed", url=url, error=str(e))
            # Fallback to regular scraping
            return await super()._scrape_single_url(url, config)
    
    async def _apply_extraction_strategy(
        self,
        url: str,
        content: str,
        config: ScrapingConfig
    ) -> Optional[List[Dict[str, Any]]]:
        """Apply selected extraction strategy to content."""
        strategy_type = getattr(config, 'extraction_strategy', 'none')
        
        if strategy_type == 'none':
            return None
        
        try:
            # Parse extraction configuration
            extraction_config = getattr(config, 'extraction_config', {})
            
            # Create extraction strategy
            strategy = create_extraction_strategy(strategy_type, extraction_config)
            
            # Apply extraction
            extracted_blocks = await strategy.extract(url, content)
            
            logger.debug(
                "extraction_strategy_applied",
                strategy=strategy_type,
                blocks_extracted=len(extracted_blocks)
            )
            
            return extracted_blocks
            
        except Exception as e:
            logger.error(
                "extraction_strategy_failed",
                strategy=strategy_type,
                error=str(e)
            )
            return None
    
    async def _apply_content_filtering(
        self,
        content: str,
        config: ScrapingConfig
    ) -> Optional[str]:
        """Apply content filtering to HTML content."""
        filter_type = getattr(config, 'content_filter', 'none')
        
        if filter_type == 'none':
            return None
        
        try:
            # Parse filter configuration
            filter_config = getattr(config, 'content_filter_config', {})
            
            # Create content filter
            content_filter = create_content_filter(filter_type, filter_config)
            
            # Apply filtering
            filter_result = await content_filter.filter(content)
            
            logger.debug(
                "content_filter_applied",
                filter_type=filter_type,
                original_length=filter_result.original_length,
                filtered_length=filter_result.filtered_length,
                relevance_score=filter_result.relevance_score
            )
            
            return filter_result.filtered_content
            
        except Exception as e:
            logger.error(
                "content_filter_failed",
                filter_type=filter_type,
                error=str(e)
            )
            return None
    
    async def _generate_enhanced_markdown(
        self,
        content: str,
        url: str,
        config: ScrapingConfig
    ) -> Optional[Any]:
        """Generate enhanced markdown with citations."""
        if not getattr(config, 'markdown_generation', False):
            return None
        
        try:
            # Parse markdown configuration
            markdown_config = getattr(config, 'markdown_config', {})
            
            # Create content filter for fit markdown if specified
            content_filter = None
            if 'content_filter' in markdown_config:
                filter_config = markdown_config['content_filter']
                content_filter = create_content_filter(
                    filter_config.get('filter_type', 'none'),
                    filter_config
                )
            
            # Initialize markdown generator
            if not self.markdown_generator:
                self.markdown_generator = DefaultMarkdownGenerator(
                    content_filter=content_filter,
                    options=markdown_config
                )
            
            # Generate markdown
            markdown_result = await self.markdown_generator.generate_markdown(
                input_html=content,
                base_url=url,
                citations=markdown_config.get('citations', True)
            )
            
            logger.debug(
                "enhanced_markdown_generated",
                raw_length=len(markdown_result.raw_markdown),
                fit_length=len(markdown_result.fit_markdown) if markdown_result.fit_markdown else 0,
                citations_count=len(markdown_result.citation_map) if markdown_result.citation_map else 0
            )
            
            return markdown_result
            
        except Exception as e:
            logger.error("enhanced_markdown_failed", error=str(e))
            return None
    
    async def _analyze_links(
        self,
        content: str,
        url: str,
        config: ScrapingConfig
    ) -> Optional[Any]:
        """Perform intelligent link analysis."""
        if not getattr(config, 'link_analysis', False):
            return None
        
        try:
            # Parse link analysis configuration
            link_config = getattr(config, 'link_analysis_config', {})
            
            # Create link analysis configuration
            from app.services.extraction.link_analysis import LinkPreviewConfig
            preview_config = LinkPreviewConfig(**link_config)
            
            # Initialize link analyzer
            if not self.link_analyzer:
                from app.services.extraction.link_analysis import LinkAnalyzer
                self.link_analyzer = LinkAnalyzer(preview_config)
            
            # Perform link analysis
            analysis_result = await self.link_analyzer.analyze_page_links(
                html_content=content,
                base_url=url
            )
            
            logger.debug(
                "link_analysis_completed",
                total_links=analysis_result.analysis_metadata.get('total_links_found', 0),
                above_threshold=analysis_result.analysis_metadata.get('links_above_threshold', 0)
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error("link_analysis_failed", error=str(e))
            return None
    
    async def _adaptive_crawl_single_url(
        self,
        start_url: str,
        config: ScrapingConfig
    ) -> List[ScrapedContent]:
        """Perform adaptive crawling starting from a single URL."""
        try:
            # Parse adaptive crawling configuration
            adaptive_config = getattr(config, 'adaptive_config', {})
            from app.services.crawling.adaptive_crawling import AdaptiveConfig
            
            crawl_config = AdaptiveConfig(**adaptive_config)
            
            # Create adaptive crawler
            if not self.adaptive_crawler:
                from app.services.crawling.adaptive_crawling import AdaptiveCrawler
                self.adaptive_crawler = AdaptiveCrawler(
                    scraping_service=self,
                    config=crawl_config
                )
            
            # Perform adaptive crawling
            crawl_result = await self.adaptive_crawler.adaptive_crawl(
                start_url=start_url,
                query=getattr(config, 'link_score_query', '') or '',
                max_links_to_follow=crawl_config.max_pages
            )
            
            logger.info(
                "adaptive_crawling_completed",
                urls_crawled=crawl_result['crawl_state']['urls_crawled'],
                confidence=crawl_result['crawl_state']['confidence']
            )
            
            return crawl_result['results']
            
        except Exception as e:
            logger.error("adaptive_crawling_failed", error=str(e))
            # Fallback to single URL scraping
            basic_result = await super()._scrape_single_url(start_url, config)
            return [basic_result]
    
    async def _combine_enhanced_results(
        self,
        basic_result: ScrapedContent,
        extracted_content: Optional[List[Dict[str, Any]]],
        filtered_content: Optional[str],
        markdown_result: Optional[Any],
        link_analysis_result: Optional[Any],
        config: ScrapingConfig
    ) -> ScrapedContent:
        """Combine all enhancement results into final ScrapedContent."""
        
        # Start with basic result
        enhanced_data = {
            'url': basic_result.url,
            'title': basic_result.title,
            'text': basic_result.text,
            'html': basic_result.html,
            'images': basic_result.images,
            'links': basic_result.links,
            'metadata': basic_result.metadata,
            'extraction_success': basic_result.extraction_success,
            'extraction_time_ms': basic_result.extraction_time_ms,
            'word_count': basic_result.word_count,
            'language_detected': basic_result.language_detected,
            'content_quality_score': basic_result.content_quality_score,
            'error_message': basic_result.error_message
        }
        
        # Add extraction results
        if extracted_content:
            enhanced_data['extracted_content'] = extracted_content
            enhanced_data['extraction_strategy'] = getattr(config, 'extraction_strategy', 'none')
        
        # Add filtered content
        if filtered_content:
            enhanced_data['filtered_html'] = filtered_content
            enhanced_data['content_filter'] = getattr(config, 'content_filter', 'none')
            
            # Update text with filtered content if using markdown output
            if getattr(config, 'response_format', 'json') == 'markdown':
                soup = BeautifulSoup(filtered_content, 'lxml')
                enhanced_data['text'] = sanitize_text(soup.get_text())
        
        # Add markdown results
        if markdown_result:
            enhanced_data['markdown'] = {
                'raw_markdown': markdown_result.raw_markdown,
                'fit_markdown': markdown_result.fit_markdown,
                'references_markdown': markdown_result.references_markdown,
                'citation_map': markdown_result.citation_map,
                'link_analysis': markdown_result.link_analysis,
                'generation_metadata': markdown_result.generation_metadata
            }
            
            # Update text with markdown if requested
            if getattr(config, 'response_format', 'json') == 'markdown':
                enhanced_data['text'] = markdown_result.fit_markdown or markdown_result.raw_markdown
        
        # Add link analysis results
        if link_analysis_result:
            enhanced_data['link_analysis'] = {
                'top_links': [
                    {
                        'url': link.url,
                        'text': link.text,
                        'title': link.title,
                        'domain': link.domain,
                        'overall_score': link.overall_score,
                        'relevance_score': link.relevance_score,
                        'authority_score': link.authority_score,
                        'quality_score': link.quality_score,
                        'priority_rank': link.priority_rank
                    }
                    for link in link_analysis_result.top_links[:20]  # Top 20 links
                ],
                'domain_statistics': link_analysis_result.domain_statistics,
                'quality_distribution': link_analysis_result.quality_distribution,
                'analysis_metadata': link_analysis_result.analysis_metadata
            }
        
        return ScrapedContent(**enhanced_data)
    
    async def extract_tables(
        self,
        html_content: str,
        base_url: str = "",
        strategy: str = "default",
        config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract tables from HTML content."""
        try:
            extractor = create_table_extraction_strategy(strategy, config or {})
            return extractor.extract_tables(html_content, base_url)
        except Exception as e:
            logger.error("table_extraction_failed", error=str(e))
            return []
    
    async def chunk_content(
        self,
        text: str,
        strategy: str = "paragraph",
        config: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Chunk text content using specified strategy."""
        try:
            chunker = create_chunking_strategy(strategy, config or {})
            return chunker.chunk(text)
        except Exception as e:
            logger.error("content_chunking_failed", error=str(e))
            return [text]  # Fallback to original text
    
    async def discover_urls(
        self,
        base_url: str,
        config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Discover URLs using URL seeder."""
        try:
            seeding_config = SeedingConfig(**config) if config else SeedingConfig()
            
            if not self.url_seeder:
                self.url_seeder = URLSeeder(seeding_config)
                await self.url_seeder.initialize()
            
            discovered_urls = await self.url_seeder.discover(base_url)
            return [url.to_dict() for url in discovered_urls]
        except Exception as e:
            logger.error("url_discovery_failed", error=str(e))
            return []
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        report = {
            "enhanced_scraping": {
                "components_initialized": {
                    "markdown_generator": self.markdown_generator is not None,
                    "adaptive_crawler": self.adaptive_crawler is not None,
                    "virtual_scroller": self.virtual_scroller is not None,
                    "link_analyzer": self.link_analyzer is not None,
                    "url_seeder": self.url_seeder is not None,
                    "dispatcher": self.dispatcher is not None
                }
            }
        }
        
        # Add dispatcher performance report
        if self.dispatcher and hasattr(self.dispatcher, 'get_performance_report'):
            report["dispatcher"] = self.dispatcher.get_performance_report()
        
        return report
    
    async def cleanup(self):
        """Cleanup all resources."""
        try:
            # Cleanup dispatcher
            if self.dispatcher:
                await self.dispatcher.cleanup()
            
            # Cleanup URL seeder
            if self.url_seeder:
                await self.url_seeder.close()
            
            # Call parent cleanup
            await super().close()
            
        except Exception as e:
            logger.error("cleanup_failed", error=str(e))


# Singleton instance
_enhanced_scraping_service: Optional[EnhancedScrapingService] = None


async def get_enhanced_scraping_service() -> EnhancedScrapingService:
    """Get or create enhanced scraping service instance."""
    global _enhanced_scraping_service
    
    if _enhanced_scraping_service is None:
        _enhanced_scraping_service = EnhancedScrapingService()
        await _enhanced_scraping_service.initialize()
    
    return _enhanced_scraping_service
