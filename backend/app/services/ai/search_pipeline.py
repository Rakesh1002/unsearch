"""
Enterprise AI Search Pipeline for UnSearch.

End-to-end intelligent search pipeline leveraging Cloudflare Workers AI:
1. Query Analysis - Detect complexity and intent
2. Multi-Engine Search - SearXNG with 70+ engines
3. Content Extraction - Smart scraping with JS support
4. AI Reranking - BGE reranker for relevance
5. Answer Generation - gpt-oss-120b for production quality
6. Content Safety - Llama Guard for enterprise compliance

This is the core differentiator that makes UnSearch industry-leading.
"""
import asyncio
import time
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.services.ai.cloudflare_ai import (
    CloudflareAIService,
    CFModel,
    ModelTier,
    get_cloudflare_ai_service
)

logger = structlog.get_logger(__name__)


class QueryComplexity(str, Enum):
    """Query complexity levels for model selection."""
    SIMPLE = "simple"  # Factual lookups, definitions
    MODERATE = "moderate"  # Multi-faceted questions
    COMPLEX = "complex"  # Analytical, reasoning required
    EXPERT = "expert"  # Deep analysis, synthesis


class SearchIntent(str, Enum):
    """Detected search intent."""
    FACTUAL = "factual"  # Looking for facts
    ANALYTICAL = "analytical"  # Analysis/comparison
    NAVIGATIONAL = "navigational"  # Finding a specific site
    TRANSACTIONAL = "transactional"  # Action-oriented
    INFORMATIONAL = "informational"  # Learning about topic


@dataclass
class QueryAnalysis:
    """Result of query analysis."""
    complexity: QueryComplexity
    intent: SearchIntent
    suggested_model_tier: ModelTier
    keywords: List[str]
    is_question: bool
    requires_reasoning: bool
    estimated_tokens: int


@dataclass
class SearchSource:
    """A search result source."""
    title: str
    url: str
    snippet: str
    content: Optional[str] = None
    score: float = 0.0
    rank: int = 0


@dataclass
class PipelineResult:
    """Complete pipeline result."""
    query: str
    answer: Optional[str]
    sources: List[SearchSource]
    images: List[Dict[str, Any]]
    query_analysis: QueryAnalysis
    model_used: str
    safety_check: Optional[Dict[str, Any]]
    response_time: float
    credits_used: int


class AISearchPipeline:
    """
    Enterprise AI Search Pipeline.
    
    Integrates all AI capabilities for industry-leading search:
    - Intelligent model selection based on query complexity
    - Production-grade answer generation with gpt-oss-120b
    - Multi-stage reranking for relevance
    - Content safety for enterprise compliance
    """
    
    # Keywords that suggest complex/reasoning queries
    REASONING_KEYWORDS = {
        "why", "how", "explain", "compare", "analyze", "evaluate",
        "what causes", "what are the implications", "pros and cons",
        "difference between", "relationship between", "impact of",
        "best way to", "should i", "trade-offs"
    }
    
    # Keywords that suggest simple factual queries
    FACTUAL_KEYWORDS = {
        "what is", "who is", "when was", "where is", "define",
        "meaning of", "definition of"
    }
    
    def __init__(self):
        self._cf_ai: Optional[CloudflareAIService] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the pipeline with AI services."""
        if not self._initialized:
            self._cf_ai = await get_cloudflare_ai_service()
            self._initialized = True
            logger.info("ai_search_pipeline_initialized", 
                       configured=self._cf_ai.is_configured if self._cf_ai else False)
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze query to determine complexity and optimal model.
        
        This is a key differentiator - intelligent model selection
        maximizes quality while optimizing cost.
        """
        query_lower = query.lower().strip()
        words = query_lower.split()
        
        # Detect if it's a question
        is_question = query.endswith("?") or any(
            query_lower.startswith(w) for w in ["what", "who", "when", "where", "why", "how", "is", "are", "can", "should", "would"]
        )
        
        # Check for reasoning indicators
        requires_reasoning = any(kw in query_lower for kw in self.REASONING_KEYWORDS)
        is_factual = any(kw in query_lower for kw in self.FACTUAL_KEYWORDS)
        
        # Determine complexity
        if requires_reasoning or len(words) > 15:
            complexity = QueryComplexity.COMPLEX
            model_tier = ModelTier.REASONING
        elif is_factual or len(words) < 5:
            complexity = QueryComplexity.SIMPLE
            model_tier = ModelTier.SPEED
        else:
            complexity = QueryComplexity.MODERATE
            model_tier = ModelTier.QUALITY
        
        # Detect intent
        if is_factual:
            intent = SearchIntent.FACTUAL
        elif requires_reasoning:
            intent = SearchIntent.ANALYTICAL
        elif any(w in query_lower for w in ["buy", "download", "sign up", "subscribe"]):
            intent = SearchIntent.TRANSACTIONAL
        elif any(w in query_lower for w in ["login", "official", "website", "homepage"]):
            intent = SearchIntent.NAVIGATIONAL
        else:
            intent = SearchIntent.INFORMATIONAL
        
        # Extract keywords (simple approach - could use NLP)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "who", "when", "where", "why", "how", "in", "on", "at", "to", "for", "of", "with"}
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Estimate tokens
        estimated_tokens = len(query.split()) * 2  # Rough estimate
        
        return QueryAnalysis(
            complexity=complexity,
            intent=intent,
            suggested_model_tier=model_tier,
            keywords=keywords[:10],
            is_question=is_question,
            requires_reasoning=requires_reasoning,
            estimated_tokens=estimated_tokens
        )
    
    def select_model(
        self,
        analysis: QueryAnalysis,
        force_quality: bool = False,
        force_reasoning: bool = False
    ) -> CFModel:
        """
        Select optimal model based on query analysis.
        
        Model selection strategy:
        - SIMPLE queries -> llama-3.1-8b-instruct-fast (speed)
        - MODERATE queries -> llama-3.3-70b-instruct-fp8-fast (quality)
        - COMPLEX queries -> qwq-32b (reasoning)
        - EXPERT queries -> gpt-oss-120b (production)
        
        force_quality=True always uses gpt-oss-120b for maximum quality.
        """
        if force_quality:
            return CFModel.GPT_OSS_120B
        
        if force_reasoning or analysis.requires_reasoning:
            return CFModel.QWQ_32B
        
        if analysis.complexity == QueryComplexity.SIMPLE:
            return CFModel.LLAMA_3_1_8B_FAST
        elif analysis.complexity == QueryComplexity.MODERATE:
            return CFModel.LLAMA_3_3_70B_FAST
        elif analysis.complexity == QueryComplexity.COMPLEX:
            return CFModel.QWQ_32B
        else:  # EXPERT
            return CFModel.GPT_OSS_120B
    
    async def rerank_results(
        self,
        query: str,
        sources: List[SearchSource],
        top_k: int = 10
    ) -> List[SearchSource]:
        """
        Rerank search results using BGE reranker.
        
        This significantly improves result relevance, especially
        for complex queries where initial ranking may be poor.
        """
        if not self._cf_ai or not self._cf_ai.is_configured:
            return sources
        
        if len(sources) <= 1:
            return sources
        
        try:
            # Extract documents for reranking
            docs = [s.snippet or s.title for s in sources]
            
            result = await self._cf_ai.rerank(
                query=query,
                documents=docs,
                top_k=top_k
            )
            
            # Reorder sources by ranking
            reranked = []
            for i, idx in enumerate(result.rankings):
                if idx < len(sources):
                    source = sources[idx]
                    source.score = result.scores[i] if i < len(result.scores) else 0.0
                    source.rank = i + 1
                    reranked.append(source)
            
            logger.info("reranked_results", 
                       query=query[:50], 
                       original_count=len(sources),
                       reranked_count=len(reranked))
            
            return reranked
            
        except Exception as e:
            logger.warning("rerank_failed", error=str(e))
            return sources
    
    async def generate_answer(
        self,
        query: str,
        sources: List[SearchSource],
        analysis: QueryAnalysis,
        model: Optional[CFModel] = None,
        max_tokens: int = 1024,
        use_production_model: bool = False
    ) -> Optional[str]:
        """
        Generate high-quality answer using context from sources.
        
        Model selection:
        - use_production_model=True -> gpt-oss-120b (best quality)
        - Otherwise -> model based on query analysis
        """
        if not self._cf_ai or not self._cf_ai.is_configured:
            return self._fallback_answer(query, sources)
        
        if not sources:
            return None
        
        # Select model
        if model is None:
            model = CFModel.GPT_OSS_120B if use_production_model else self.select_model(analysis)
        
        try:
            # Build rich context
            context_parts = []
            for i, source in enumerate(sources[:7]):  # Top 7 sources
                context = f"[Source {i+1}] {source.title}\nURL: {source.url}\n"
                if source.content:
                    context += f"Full Content:\n{source.content[:2000]}\n"
                elif source.snippet:
                    context += f"Summary: {source.snippet}\n"
                context_parts.append(context)
            
            # Generate answer with appropriate model
            if analysis.requires_reasoning:
                # Use reasoning-specific generation
                answer = await self._cf_ai.generate_with_reasoning(
                    prompt=self._build_reasoning_prompt(query, context_parts),
                    max_tokens=max_tokens
                )
                return answer.text
            else:
                answer = await self._cf_ai.generate_answer(
                    question=query,
                    context=context_parts,
                    model=model,
                    max_tokens=max_tokens
                )
                return answer
                
        except Exception as e:
            logger.warning("answer_generation_failed", error=str(e), model=model.value if model else "unknown")
            return self._fallback_answer(query, sources)
    
    def _build_reasoning_prompt(self, query: str, context_parts: List[str]) -> str:
        """Build prompt optimized for reasoning models."""
        context_str = "\n\n".join(context_parts)
        return f"""I need you to analyze and reason through this question carefully.

**Question:** {query}

**Available Information:**
{context_str}

**Instructions:**
1. First, identify the key aspects of the question
2. Analyze the relevant information from each source
3. Consider different perspectives or interpretations
4. Synthesize a comprehensive answer with reasoning
5. Cite sources when making specific claims

**Your Analysis and Answer:**"""
    
    def _fallback_answer(self, query: str, sources: List[SearchSource]) -> Optional[str]:
        """Generate fallback answer when AI is unavailable."""
        if not sources:
            return None
        
        parts = [f"Based on {len(sources)} sources found for '{query}':"]
        for i, source in enumerate(sources[:3]):
            parts.append(f"\n{i+1}. {source.title}: {source.snippet[:200]}...")
        
        return " ".join(parts)
    
    async def check_safety(
        self,
        query: str,
        answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check content safety for enterprise compliance.
        
        Uses Llama Guard to classify prompts and responses.
        """
        if not self._cf_ai or not self._cf_ai.is_configured:
            return {"safe": True, "checked": False, "reason": "Safety check unavailable"}
        
        try:
            # Check query safety
            query_result = await self._cf_ai.check_content_safety(query, check_prompt=True)
            
            result = {
                "query_safe": query_result.get("safe", True),
                "query_categories": query_result.get("categories", []),
                "checked": True
            }
            
            # Check answer safety if provided
            if answer:
                answer_result = await self._cf_ai.check_content_safety(answer, check_response=True)
                result["answer_safe"] = answer_result.get("safe", True)
                result["answer_categories"] = answer_result.get("categories", [])
            
            result["safe"] = result["query_safe"] and result.get("answer_safe", True)
            
            return result
            
        except Exception as e:
            logger.warning("safety_check_failed", error=str(e))
            return {"safe": True, "checked": False, "error": str(e)}
    
    async def generate_embeddings(
        self,
        texts: List[str],
        use_multilingual: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for semantic search.
        
        Uses bge-m3 for multilingual support (100+ languages)
        or bge-large for English-optimized high-quality embeddings.
        """
        if not self._cf_ai or not self._cf_ai.is_configured:
            raise ValueError("Cloudflare AI not configured for embeddings")
        
        model = CFModel.BGE_M3 if use_multilingual else CFModel.BGE_LARGE
        
        result = await self._cf_ai.generate_embeddings(texts, model=model)
        return result.embeddings
    
    async def run_pipeline(
        self,
        query: str,
        sources: List[SearchSource],
        include_answer: bool = True,
        use_production_model: bool = False,
        check_safety: bool = True,
        rerank: bool = True,
        max_sources: int = 10
    ) -> PipelineResult:
        """
        Run the full AI search pipeline.
        
        This is the main entry point that orchestrates:
        1. Query analysis
        2. Result reranking
        3. Answer generation
        4. Safety checking
        
        Args:
            query: Search query
            sources: Raw search results
            include_answer: Generate LLM answer
            use_production_model: Use gpt-oss-120b for max quality
            check_safety: Run content safety checks
            rerank: Rerank results with AI
            max_sources: Maximum sources to process
        """
        start_time = time.time()
        await self.initialize()
        
        # 1. Analyze query
        analysis = self.analyze_query(query)
        logger.info("query_analyzed", 
                   query=query[:50],
                   complexity=analysis.complexity.value,
                   intent=analysis.intent.value,
                   requires_reasoning=analysis.requires_reasoning)
        
        # 2. Rerank results
        processed_sources = sources[:max_sources]
        if rerank and len(processed_sources) > 1:
            processed_sources = await self.rerank_results(query, processed_sources)
        
        # 3. Select model and generate answer
        answer = None
        model_used = "none"
        if include_answer:
            model = self.select_model(analysis, force_quality=use_production_model)
            model_used = model.value
            answer = await self.generate_answer(
                query=query,
                sources=processed_sources,
                analysis=analysis,
                model=model,
                use_production_model=use_production_model
            )
        
        # 4. Safety check
        safety_result = None
        if check_safety:
            safety_result = await self.check_safety(query, answer)
            if not safety_result.get("safe", True):
                logger.warning("content_safety_violation", 
                             query=query[:50],
                             categories=safety_result.get("query_categories", []))
        
        # Calculate credits used (approximate)
        credits = 1  # Base
        if rerank:
            credits += 1
        if include_answer:
            credits += 2 if use_production_model else 1
        if check_safety:
            credits += 1
        
        response_time = round(time.time() - start_time, 3)
        
        return PipelineResult(
            query=query,
            answer=answer,
            sources=processed_sources,
            images=[],  # Images handled separately
            query_analysis=analysis,
            model_used=model_used,
            safety_check=safety_result,
            response_time=response_time,
            credits_used=credits
        )


# Singleton instance
_pipeline: Optional[AISearchPipeline] = None


async def get_search_pipeline() -> AISearchPipeline:
    """Get or create the AI search pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = AISearchPipeline()
        await _pipeline.initialize()
    return _pipeline
