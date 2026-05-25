"""
AI Services for UnSearch.

Enterprise-grade edge AI for industry-leading RAG search:
- Cloudflare Workers AI (50K credits available)
  - Multi-lingual embeddings (bge-m3, embeddinggemma)
  - Production LLMs (gpt-oss-120b, llama-3.3-70b, llama-4-scout)
  - Reasoning models (qwq-32b, deepseek-r1)
  - Content safety (llama-guard-3-8b)
- AI Search Pipeline (end-to-end intelligent search)
"""
from app.services.ai.cloudflare_ai import (
    CloudflareAIService,
    CFModel,
    ModelTier,
    TIER_MODELS,
    EMBEDDING_RECOMMENDATIONS,
    EmbeddingResult,
    GenerationResult,
    RerankResult,
    SummarizationResult,
    get_cloudflare_ai_service
)

from app.services.ai.search_pipeline import (
    AISearchPipeline,
    QueryComplexity,
    SearchIntent,
    QueryAnalysis,
    SearchSource,
    PipelineResult,
    get_search_pipeline
)

__all__ = [
    # Main services
    "CloudflareAIService",
    "get_cloudflare_ai_service",
    "AISearchPipeline",
    "get_search_pipeline",
    # Models and tiers
    "CFModel",
    "ModelTier",
    "TIER_MODELS",
    "EMBEDDING_RECOMMENDATIONS",
    # Query analysis
    "QueryComplexity",
    "SearchIntent",
    "QueryAnalysis",
    "SearchSource",
    # Result types
    "EmbeddingResult",
    "GenerationResult",
    "RerankResult",
    "SummarizationResult",
    "PipelineResult",
]
