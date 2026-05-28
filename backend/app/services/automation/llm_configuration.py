"""
LLM-powered configuration service for converting natural language to crawler options.

Inspired by Firecrawl's natural language configuration capabilities.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog
import openai

from app.config import get_settings
from app.models.requests import ScrapingConfig, ExtractionStrategyConfig, ContentFilterConfig

logger = structlog.get_logger(__name__)
settings = get_settings()


class ConfigurationPromptType(Enum):
    """Types of configuration prompts."""
    CRAWLER_OPTIONS = "crawler_options"
    EXTRACTION_SCHEMA = "extraction_schema" 
    CONTENT_FILTER = "content_filter"
    SEARCH_STRATEGY = "search_strategy"


@dataclass
class LLMConfigurationRequest:
    """Request for LLM-powered configuration generation."""
    prompt: str
    prompt_type: ConfigurationPromptType
    context: Optional[Dict[str, Any]] = None
    model: str = "gpt-4"
    temperature: float = 0.1
    max_retries: int = 3


@dataclass
class LLMConfigurationResponse:
    """Response from LLM configuration generation."""
    success: bool
    config: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    model_used: str = ""


class LLMConfigurationService:
    """
    Service for converting natural language descriptions into structured configurations.
    
    Provides intelligent configuration generation for:
    - Crawler options and settings
    - Data extraction schemas
    - Content filtering rules
    - Search strategies
    """
    
    def __init__(self):
        """Initialize LLM configuration service."""
        self.openai_client = openai.AsyncOpenAI(
            api_key=getattr(settings, 'openai_api_key', None)
        )
        self.model_configs = {
            "gpt-4": {"max_tokens": 4096, "fallback": "gpt-3.5-turbo"},
            "gpt-4-turbo": {"max_tokens": 4096, "fallback": "gpt-4"},
            "gpt-3.5-turbo": {"max_tokens": 4096, "fallback": None}
        }
        self.usage_stats = {"total_requests": 0, "successful_requests": 0, "tokens_used": 0}
    
    async def generate_config(self, request: LLMConfigurationRequest) -> LLMConfigurationResponse:
        """
        Generate configuration from natural language prompt.
        
        Args:
            request: Configuration request with prompt and type
            
        Returns:
            LLMConfigurationResponse with generated configuration
        """
        self.usage_stats["total_requests"] += 1
        
        logger.info("llm_config_generation_started",
                   prompt=request.prompt[:100] + "..." if len(request.prompt) > 100 else request.prompt,
                   type=request.prompt_type.value)
        
        # Get appropriate system prompt
        system_prompt = self._get_system_prompt(request.prompt_type)
        
        # Try with primary model, fallback if needed
        models_to_try = [request.model]
        if request.model in self.model_configs and self.model_configs[request.model]["fallback"]:
            models_to_try.append(self.model_configs[request.model]["fallback"])
        
        last_error = None
        
        for model in models_to_try:
            for attempt in range(request.max_retries):
                try:
                    response = await self._make_llm_request(
                        system_prompt=system_prompt,
                        user_prompt=request.prompt,
                        model=model,
                        temperature=request.temperature + (attempt * 0.1),  # Increase temp on retries
                        context=request.context
                    )
                    
                    if response.success:
                        self.usage_stats["successful_requests"] += 1
                        self.usage_stats["tokens_used"] += response.tokens_used
                        return response
                    else:
                        last_error = response.error
                        
                except Exception as e:
                    last_error = str(e)
                    logger.warning("llm_request_failed", 
                                 model=model, 
                                 attempt=attempt + 1, 
                                 error=str(e))
                    
                    # Add delay before retry
                    await asyncio.sleep(1 + attempt)
        
        return LLMConfigurationResponse(
            success=False,
            error=f"Failed to generate configuration: {last_error}"
        )
    
    async def _make_llm_request(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMConfigurationResponse:
        """Make request to LLM API."""
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add context if provided
        if context:
            context_prompt = f"Additional context: {json.dumps(context, indent=2)}\n\n"
            user_prompt = context_prompt + user_prompt
        
        messages.append({"role": "user", "content": user_prompt})
        
        # Make API request
        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Process response
        try:
            content = response.choices[0].message.content
            config_data = json.loads(content)
            
            return LLMConfigurationResponse(
                success=True,
                config=config_data.get("config", {}),
                reasoning=config_data.get("reasoning", ""),
                tokens_used=response.usage.total_tokens,
                model_used=model
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            return LLMConfigurationResponse(
                success=False,
                error=f"Failed to parse LLM response: {str(e)}"
            )
    
    def _get_system_prompt(self, prompt_type: ConfigurationPromptType) -> str:
        """Get appropriate system prompt for configuration type."""
        
        if prompt_type == ConfigurationPromptType.CRAWLER_OPTIONS:
            return self._get_crawler_options_prompt()
        elif prompt_type == ConfigurationPromptType.EXTRACTION_SCHEMA:
            return self._get_extraction_schema_prompt()
        elif prompt_type == ConfigurationPromptType.CONTENT_FILTER:
            return self._get_content_filter_prompt()
        elif prompt_type == ConfigurationPromptType.SEARCH_STRATEGY:
            return self._get_search_strategy_prompt()
        else:
            return "You are a helpful assistant that generates structured configurations from natural language."
    
    def _get_crawler_options_prompt(self) -> str:
        """System prompt for crawler options generation."""
        return """You are a web crawler configuration expert. Generate crawler options based on natural language instructions.

Available crawler options:
- includePaths: string[] - URL pathname regex patterns that include matching URLs in the crawl. Only the paths that match the specified patterns will be included in the response. For example, if you set "includePaths": ["blog/.*"] for the base URL firecrawl.dev, only results matching that pattern will be included, such as https://www.firecrawl.dev/blog/firecrawl-launch-week-1-recap.
- excludePaths: string[] - URL pathname regex patterns that exclude matching URLs from the crawl. For example, if you set "excludePaths": ["blog/.*"] for the base URL firecrawl.dev, any results matching that pattern will be excluded, such as https://www.firecrawl.dev/blog/firecrawl-launch-week-1-recap.
- maxDepth: number - Maximum absolute depth to crawl from the base of the entered URL. Basically, the max number of slashes the pathname of a scraped URL may contain. Default: 10
- maxDiscoveryDepth: number - Maximum depth to crawl based on discovery order. The root site and sitemapped pages has a discovery depth of 0. For example, if you set it to 1, and you set ignoreSitemap, you will only crawl the entered URL and all URLs that are linked on that page.
- crawlEntireDomain: boolean - Allows the crawler to follow internal links to sibling or parent URLs, not just child paths. false: Only crawls deeper (child) URLs. → e.g. /features/feature-1 → /features/feature-1/tips ✅ → Won't follow /pricing or / ❌. true: Crawls any internal links, including siblings and parents. → e.g. /features/feature-1 → /pricing, /, etc. ✅. Use true for broader internal coverage beyond nested paths. Default: false
- allowExternalLinks: boolean - Allows the crawler to follow links to external websites. Default: false
- allowSubdomains: boolean - Allows the crawler to follow links to subdomains of the main domain. Default: false
- sitemap: "skip" | "include" - Whether to ignore sitemap. Default: "include"
- ignoreQueryParameters: boolean - Do not re-scrape the same path with different (or none) query parameters. Default: false
- deduplicateSimilarURLs: boolean - Whether to deduplicate similar URLs
- delay: number - Delay in seconds between scrapes. This helps respect website rate limits.
- limit: number - Maximum number of pages to crawl. Default limit is 10000.
- javascript_rendering: boolean - Whether to enable JavaScript rendering for dynamic content
- screenshot: boolean - Whether to take screenshots of pages
- extract_images: boolean - Whether to extract images from pages
- extract_links: boolean - Whether to extract links from pages
- stealth_mode: boolean - Whether to use stealth mode to avoid detection
- mobile_mode: boolean - Whether to simulate mobile browser
- wait_time: number - Time to wait after page load (in seconds)

Return a JSON object with only the relevant options for the user's request. Don't include options that aren't relevant to the instruction. Focus on the most important options that directly address the user's intent.

Response format:
{
  "config": {
    "includePaths": ["pattern1", "pattern2"],
    "maxDepth": 5,
    "javascript_rendering": true,
    // ... other relevant options
  },
  "reasoning": "Explanation of why these options were chosen for the user's request."
}"""
    
    def _get_extraction_schema_prompt(self) -> str:
        """System prompt for extraction schema generation."""
        return """You are a data extraction expert. Generate JSON schemas for extracting structured data from web pages based on natural language descriptions.

You can create schemas for extracting:
- Articles and blog posts (title, content, author, date, tags)
- Product information (name, price, description, specifications, reviews)
- Contact information (name, email, phone, address)
- Job listings (title, company, location, salary, requirements)
- Event information (name, date, location, description)
- Research papers (title, authors, abstract, publication date)
- News articles (headline, summary, author, publication date)
- Business listings (name, address, phone, website, reviews)
- Social media posts (content, author, timestamp, engagement)
- And any other structured data

The schema should follow JSON Schema format with appropriate types, descriptions, and validation rules.

Response format:
{
  "config": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "The title or headline"
      },
      "content": {
        "type": "string", 
        "description": "The main content or body text"
      }
      // ... other fields
    },
    "required": ["title", "content"]
  },
  "reasoning": "Explanation of the schema design and why these fields are important."
}"""
    
    def _get_content_filter_prompt(self) -> str:
        """System prompt for content filter generation."""
        return """You are a content filtering expert. Generate content filter configurations based on natural language requirements.

Available filter types:
- pruning: Remove irrelevant content based on configurable thresholds
  - Options: relevance_threshold (0.0-1.0), content_length_min, content_length_max
- bm25: Information retrieval-based filtering using BM25 algorithm
  - Options: query_terms, score_threshold, max_results
- llm: AI-powered content relevance filtering
  - Options: relevance_query, confidence_threshold, model

Filter configurations:
{
  "filter_type": "pruning|bm25|llm",
  "config": {
    // Type-specific options
  }
}

Response format:
{
  "config": {
    "filter_type": "bm25",
    "config": {
      "query_terms": ["technology", "AI"],
      "score_threshold": 0.5,
      "max_results": 50
    }
  },
  "reasoning": "Explanation of why this filter configuration matches the user's requirements."
}"""
    
    def _get_search_strategy_prompt(self) -> str:
        """System prompt for search strategy generation."""
        return """You are a search strategy expert. Generate search configurations based on natural language requirements.

Available search options:
- engines: ["google", "bing", "searxng", "duckduckgo"] - Search engines to use
- max_results: number - Maximum number of results to return
- language: string - Language code (en, es, fr, etc.)
- country: string - Country code (us, uk, de, etc.)
- safe_search: "strict" | "moderate" | "off" - Safe search setting
- time_filter: "day" | "week" | "month" | "year" - Time-based filtering
- result_type: "web" | "images" | "news" | "videos" - Type of results
- advanced_operators: string[] - Advanced search operators to include

Response format:
{
  "config": {
    "engines": ["google", "searxng"],
    "max_results": 20,
    "language": "en",
    "country": "us",
    "safe_search": "moderate",
    "advanced_operators": ["site:example.com", "intitle:AI"]
  },
  "reasoning": "Explanation of the search strategy and why these settings were chosen."
}"""
    
    async def generate_crawler_options(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate crawler options from natural language prompt."""
        request = LLMConfigurationRequest(
            prompt=prompt,
            prompt_type=ConfigurationPromptType.CRAWLER_OPTIONS,
            context=context
        )
        
        response = await self.generate_config(request)
        return response.config if response.success else {}
    
    async def generate_extraction_schema(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate extraction schema from natural language prompt."""
        request = LLMConfigurationRequest(
            prompt=prompt,
            prompt_type=ConfigurationPromptType.EXTRACTION_SCHEMA,
            context=context
        )
        
        response = await self.generate_config(request)
        return response.config if response.success else {}
    
    async def generate_content_filter(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate content filter configuration from natural language prompt."""
        request = LLMConfigurationRequest(
            prompt=prompt,
            prompt_type=ConfigurationPromptType.CONTENT_FILTER,
            context=context
        )
        
        response = await self.generate_config(request)
        return response.config if response.success else {}
    
    async def generate_search_strategy(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate search strategy from natural language prompt."""
        request = LLMConfigurationRequest(
            prompt=prompt,
            prompt_type=ConfigurationPromptType.SEARCH_STRATEGY,
            context=context
        )
        
        response = await self.generate_config(request)
        return response.config if response.success else {}
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get service usage statistics."""
        return {
            "usage_stats": self.usage_stats,
            "success_rate": (
                self.usage_stats["successful_requests"] / max(1, self.usage_stats["total_requests"])
            ),
            "average_tokens_per_request": (
                self.usage_stats["tokens_used"] / max(1, self.usage_stats["successful_requests"])
            )
        }


class ConfigurationValidator:
    """Validates generated configurations for correctness and safety."""
    
    @staticmethod
    def validate_crawler_options(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate crawler options configuration."""
        errors = []
        
        # Validate numeric ranges
        if "maxDepth" in config and not (1 <= config["maxDepth"] <= 20):
            errors.append("maxDepth must be between 1 and 20")
        
        if "limit" in config and not (1 <= config["limit"] <= 50000):
            errors.append("limit must be between 1 and 50000")
        
        if "delay" in config and not (0 <= config["delay"] <= 60):
            errors.append("delay must be between 0 and 60 seconds")
        
        # Validate boolean options
        boolean_fields = ["crawlEntireDomain", "allowExternalLinks", "allowSubdomains", 
                         "javascript_rendering", "screenshot", "extract_images", 
                         "extract_links", "stealth_mode", "mobile_mode"]
        
        for field in boolean_fields:
            if field in config and not isinstance(config[field], bool):
                errors.append(f"{field} must be a boolean value")
        
        # Validate regex patterns
        if "includePaths" in config:
            if not isinstance(config["includePaths"], list):
                errors.append("includePaths must be an array")
            else:
                for i, pattern in enumerate(config["includePaths"]):
                    try:
                        import re
                        re.compile(pattern)
                    except re.error:
                        errors.append(f"includePaths[{i}] is not a valid regex pattern")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_extraction_schema(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate extraction schema configuration."""
        errors = []
        
        # Basic JSON Schema validation
        if "type" not in config:
            errors.append("Schema must have a 'type' field")
        elif config["type"] != "object":
            errors.append("Schema type must be 'object'")
        
        if "properties" not in config:
            errors.append("Schema must have a 'properties' field")
        elif not isinstance(config["properties"], dict):
            errors.append("Schema 'properties' must be an object")
        
        # Validate property definitions
        if "properties" in config:
            for prop_name, prop_def in config["properties"].items():
                if not isinstance(prop_def, dict):
                    errors.append(f"Property '{prop_name}' must be an object")
                elif "type" not in prop_def:
                    errors.append(f"Property '{prop_name}' must have a 'type' field")
        
        return len(errors) == 0, errors


# Singleton instance
_llm_config_service: Optional[LLMConfigurationService] = None


async def get_llm_config_service() -> LLMConfigurationService:
    """Get or create LLM configuration service instance."""
    global _llm_config_service
    
    if _llm_config_service is None:
        _llm_config_service = LLMConfigurationService()
    
    return _llm_config_service


# Convenience functions
async def generate_config_from_prompt(
    prompt: str,
    config_type: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate configuration from natural language prompt."""
    service = await get_llm_config_service()
    
    prompt_type_map = {
        "crawler": ConfigurationPromptType.CRAWLER_OPTIONS,
        "extraction": ConfigurationPromptType.EXTRACTION_SCHEMA,
        "filter": ConfigurationPromptType.CONTENT_FILTER,
        "search": ConfigurationPromptType.SEARCH_STRATEGY
    }
    
    if config_type not in prompt_type_map:
        raise ValueError(f"Unknown config type: {config_type}")
    
    request = LLMConfigurationRequest(
        prompt=prompt,
        prompt_type=prompt_type_map[config_type],
        context=context
    )
    
    response = await service.generate_config(request)
    
    if response.success:
        return response.config
    else:
        raise ValueError(f"Failed to generate configuration: {response.error}")
