"""
Enhanced backend services with crawl4ai-inspired capabilities.

This module provides a comprehensive suite of web scraping and content processing services:

Core Services:
- ContentScrapingService: Basic web content extraction
- EnhancedScrapingService: Advanced crawling with all features

Advanced Extraction:
- ExtractionStrategies: LLM, Cosine, JsonCSS, Regex extraction methods
- ContentFilters: BM25, Pruning, LLM content filtering
- ChunkingStrategies: Various text chunking approaches
- TableExtraction: Intelligent table detection and extraction

Content Processing:
- MarkdownGeneration: Enhanced HTML to markdown conversion
- LinkAnalysis: Intelligent link scoring and analysis

Crawling Intelligence:
- AdaptiveCrawling: Learning-based crawling optimization
- VirtualScrolling: Infinite scroll page handling  
- URLSeeder: Advanced URL discovery from multiple sources

Infrastructure:
- Dispatcher: Memory-aware concurrent operation management
- BrowserConfig: Comprehensive browser configuration
- RateLimiter: Advanced rate limiting with multiple strategies

All services are designed to work together seamlessly while maintaining
backward compatibility with existing systems.
"""

from .scraping import ContentScrapingService
from .enhanced_scraping import EnhancedScrapingService, get_enhanced_scraping_service

from .extraction_strategies import (
    ExtractionStrategy, NoExtractionStrategy, CosineStrategy, 
    JsonCssExtractionStrategy, RegexExtractionStrategy, LLMExtractionStrategy,
    create_extraction_strategy
)

from .content_filters import (
    RelevantContentFilter, NoContentFilter, PruningContentFilter,
    BM25ContentFilter, LLMContentFilter, create_content_filter
)

from .chunking_strategies import (
    ChunkingStrategy, IdentityChunking, RegexChunking, SentenceChunking,
    ParagraphChunking, FixedSizeChunking, TopicChunking, HybridChunking,
    create_chunking_strategy, chunk_text, smart_chunk_for_llm
)

from .table_extraction import (
    TableExtractionStrategy, NoTableExtraction, DefaultTableExtraction,
    LLMTableExtraction, SmartTableExtraction, create_table_extraction_strategy,
    extract_tables, tables_to_markdown
)

from .markdown_generation import (
    MarkdownGenerationStrategy, DefaultMarkdownGenerator,
    generate_markdown, generate_simple_markdown
)

from .link_analysis import (
    LinkInfo, LinkScorer, LinkAnalyzer, analyze_links, get_top_links
)

from .adaptive_crawling import (
    CrawlState, CrawlStrategy, StatisticalStrategy, AdaptiveCrawler,
    create_adaptive_crawler
)

from .virtual_scrolling import (
    VirtualScrollConfig, VirtualScrollHandler, PuppeteerVirtualScroller,
    create_virtual_scroll_config, scroll_infinite_page
)

from .url_seeder import (
    SeedingConfig, DiscoveredURL, URLSeeder, discover_urls, filter_urls_by_patterns
)

from .browser_config import (
    BrowserType, DeviceType, GeolocationConfig, ProxyConfig, UserAgentConfig,
    BrowserConfig, get_stealth_browser_config, get_mobile_browser_config,
    get_high_performance_browser_config, create_browser_config_from_env
)

from .dispatcher import (
    BaseDispatcher, SemaphoreDispatcher, MemoryAdaptiveDispatcher,
    RateLimiter, TaskResult, DispatchStats, create_dispatcher, create_rate_limiter
)

# NEW: Missing crawl4ai features implemented
from .deep_crawling import (
    DeepCrawlStrategy, BFSDeepCrawlStrategy, DFSDeepCrawlStrategy, BestFirstCrawlStrategy,
    URLFilter, DomainFilter, URLPatternFilter, ContentTypeFilter, SEOFilter, ContentRelevanceFilter,
    FilterChain, URLScorer, KeywordRelevanceScorer, PathDepthScorer, DomainAuthorityScorer,
    FreshnessScorer, CompositeScorer, create_deep_crawl_strategy, deep_crawl
)

from .pdf_processing import (
    PDFProcessorStrategy, MockPDFProcessor, NaivePDFProcessor, PDFMetadata, PDFPage,
    PDFProcessResult, PDFImage, create_pdf_processor, process_pdf_file, process_pdf_bytes,
    extract_pdf_text, pdf_to_markdown
)

from .browser_profiler import (
    BrowserProfiler, BrowserProfile, get_browser_profiler, create_browser_profile,
    get_profile_browser_config, list_browser_profiles
)

from .link_preview import (
    LinkPreview, LinkPreviewConfig, LinkPreviewResult, LinkMetadata,
    extract_link_previews, filter_links_by_quality
)

from .crawler_monitor import (
    CrawlerMonitor, CrawlStatus, TaskMetrics, SystemMetrics, CrawlerStats,
    create_crawler_monitor, get_global_monitor, start_global_monitoring, stop_global_monitoring
)

from .proxy_rotation import (
    ProxyRotationStrategy, RoundRobinProxyStrategy, RandomProxyStrategy, 
    WeightedProxyStrategy, GeographicProxyStrategy, ProxyStatus, ProxyInfo, ProxyMetrics,
    create_proxy_strategy, create_proxy_list_from_strings, test_proxy_rotation
)

# NEW: Additional missing crawl4ai components  
from .database_manager import (
    DatabaseManager, CrawlRecord, DatabaseStats, get_database_manager,
    store_crawl_data, get_cached_content, search_content
)

from .cache_context import (
    CacheContext, CacheContextManager, CacheMode, URLType, CacheRule, CacheStats,
    get_cache_manager, create_cache_context, should_cache_url
)

from .user_agent_generator import (
    UAGenerator, ValidUAGenerator, OnlineUAGenerator, CustomUAGenerator,
    UserAgentManager, UserAgentProfile, get_user_agent_manager,
    generate_user_agent, get_random_user_agent, get_user_agent_with_hints
)

from .html_converter import (
    HTMLToTextConverter, HTMLToMarkdownConverter, ConversionConfig,
    create_html_converter, html_to_text, html_to_markdown, extract_clean_text
)

# Legacy imports for backward compatibility
from .auth_service import AuthService
from .cache import CacheService, get_cache_service
from .database import DatabaseService
from .searxng import SearxngService
from .puppeteer_client import PuppeteerClient


__all__ = [
    # Core services
    "ContentScrapingService",
    "EnhancedScrapingService", 
    "get_enhanced_scraping_service",
    
    # Extraction strategies
    "ExtractionStrategy",
    "NoExtractionStrategy",
    "CosineStrategy", 
    "JsonCssExtractionStrategy",
    "RegexExtractionStrategy",
    "LLMExtractionStrategy",
    "create_extraction_strategy",
    
    # Content filters
    "RelevantContentFilter",
    "NoContentFilter",
    "PruningContentFilter",
    "BM25ContentFilter",
    "LLMContentFilter",
    "create_content_filter",
    
    # Chunking strategies
    "ChunkingStrategy",
    "IdentityChunking",
    "RegexChunking", 
    "SentenceChunking",
    "ParagraphChunking",
    "FixedSizeChunking",
    "TopicChunking",
    "HybridChunking",
    "create_chunking_strategy",
    "chunk_text",
    "smart_chunk_for_llm",
    
    # Table extraction
    "TableExtractionStrategy",
    "NoTableExtraction",
    "DefaultTableExtraction",
    "LLMTableExtraction", 
    "SmartTableExtraction",
    "create_table_extraction_strategy",
    "extract_tables",
    "tables_to_markdown",
    
    # Markdown generation
    "MarkdownGenerationStrategy",
    "DefaultMarkdownGenerator",
    "generate_markdown",
    "generate_simple_markdown",
    
    # Link analysis
    "LinkInfo",
    "LinkScorer",
    "LinkAnalyzer",
    "analyze_links",
    "get_top_links",
    
    # Adaptive crawling
    "CrawlState",
    "CrawlStrategy", 
    "StatisticalStrategy",
    "AdaptiveCrawler",
    "create_adaptive_crawler",
    
    # Virtual scrolling
    "VirtualScrollConfig",
    "VirtualScrollHandler",
    "PuppeteerVirtualScroller",
    "create_virtual_scroll_config",
    "scroll_infinite_page",
    
    # URL seeding
    "SeedingConfig",
    "DiscoveredURL",
    "URLSeeder",
    "discover_urls",
    "filter_urls_by_patterns",
    
    # Browser configuration
    "BrowserType",
    "DeviceType", 
    "GeolocationConfig",
    "ProxyConfig",
    "UserAgentConfig",
    "BrowserConfig",
    "get_stealth_browser_config",
    "get_mobile_browser_config", 
    "get_high_performance_browser_config",
    "create_browser_config_from_env",
    
    # Dispatcher system
    "BaseDispatcher",
    "SemaphoreDispatcher",
    "MemoryAdaptiveDispatcher",
    "RateLimiter",
    "TaskResult",
    "DispatchStats",
    "create_dispatcher",
    "create_rate_limiter",
    
    # Deep crawling system
    "DeepCrawlStrategy",
    "BFSDeepCrawlStrategy", 
    "DFSDeepCrawlStrategy",
    "BestFirstCrawlStrategy",
    "URLFilter",
    "DomainFilter",
    "URLPatternFilter",
    "ContentTypeFilter",
    "SEOFilter",
    "ContentRelevanceFilter",
    "FilterChain",
    "URLScorer",
    "KeywordRelevanceScorer",
    "PathDepthScorer",
    "DomainAuthorityScorer",
    "FreshnessScorer",
    "CompositeScorer",
    "create_deep_crawl_strategy",
    "deep_crawl",
    
    # PDF processing
    "PDFProcessorStrategy",
    "MockPDFProcessor",
    "NaivePDFProcessor", 
    "PDFMetadata",
    "PDFPage",
    "PDFProcessResult",
    "PDFImage",
    "create_pdf_processor",
    "process_pdf_file",
    "process_pdf_bytes",
    "extract_pdf_text",
    "pdf_to_markdown",
    
    # Browser profiling
    "BrowserProfiler",
    "BrowserProfile",
    "get_browser_profiler",
    "create_browser_profile",
    "get_profile_browser_config",
    "list_browser_profiles",
    
    # Link preview system
    "LinkPreview",
    "LinkPreviewConfig",
    "LinkPreviewResult", 
    "LinkMetadata",
    "extract_link_previews",
    "filter_links_by_quality",
    
    # Crawler monitoring
    "CrawlerMonitor",
    "CrawlStatus",
    "TaskMetrics",
    "SystemMetrics",
    "CrawlerStats",
    "create_crawler_monitor",
    "get_global_monitor",
    "start_global_monitoring",
    "stop_global_monitoring",
    
    # Proxy rotation strategies
    "ProxyRotationStrategy",
    "RoundRobinProxyStrategy",
    "RandomProxyStrategy",
    "WeightedProxyStrategy", 
    "GeographicProxyStrategy",
    "ProxyStatus",
    "ProxyInfo",
    "ProxyMetrics",
    "create_proxy_strategy",
    "create_proxy_list_from_strings",
    "test_proxy_rotation",
    
    # Database management
    "DatabaseManager",
    "CrawlRecord",
    "DatabaseStats",
    "get_database_manager",
    "store_crawl_data",
    "get_cached_content", 
    "search_content",
    
    # Cache context management
    "CacheContext",
    "CacheContextManager", 
    "CacheMode",
    "URLType",
    "CacheRule",
    "CacheStats",
    "get_cache_manager",
    "create_cache_context",
    "should_cache_url",
    
    # User agent generation
    "UAGenerator",
    "ValidUAGenerator",
    "OnlineUAGenerator",
    "CustomUAGenerator",
    "UserAgentManager",
    "UserAgentProfile",
    "get_user_agent_manager",
    "generate_user_agent",
    "get_random_user_agent",
    "get_user_agent_with_hints",
    
    # HTML conversion
    "HTMLToTextConverter", 
    "HTMLToMarkdownConverter",
    "ConversionConfig",
    "create_html_converter",
    "html_to_text",
    "html_to_markdown",
    "extract_clean_text",
    
    # Legacy services  
    "AuthService",
    "CacheService",
    "get_cache_service",
    "DatabaseService", 
    "SearxngService",
    "PuppeteerClient"
]