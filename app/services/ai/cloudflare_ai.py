"""
Cloudflare Workers AI Integration Service.

Enterprise-grade edge AI for UnSearch RAG pipeline:
- Text embeddings: bge-m3 (multilingual), embeddinggemma (Google), qwen3-embedding
- Text generation: gpt-oss-120b (OpenAI), llama-4-scout, llama-3.3-70b, qwq-32b (reasoning)
- Reranking: bge-reranker-base
- Summarization: bart-large-cnn
- Content Safety: llama-guard-3-8b

50K credits available for inference at the edge.

Model Selection Strategy (consistent with workers/src/config/models.ts):
- SPEED: llama-3.2-3b-instruct (ultra-fast, <100ms, simple queries)
- BALANCED: llama-3.3-70b-instruct-fp8-fast (best quality/speed balance)
- QUALITY: gpt-oss-120b (highest quality, production use)
- REASONING: qwq-32b (complex analytical queries, competitive with o1-mini)
"""
import os
import asyncio
import httpx
from typing import List, Dict, Any, Optional, Literal, Union
from dataclasses import dataclass, field
from enum import Enum
import structlog
from functools import lru_cache

logger = structlog.get_logger(__name__)


class CFModel(str, Enum):
    """
    Available Cloudflare Workers AI models.
    
    Organized by task and quality tier for enterprise RAG applications.
    """
    # ===================
    # EMBEDDINGS
    # ===================
    # Multi-lingual (RECOMMENDED for enterprise)
    BGE_M3 = "@cf/baai/bge-m3"  # Multi-lingual, Multi-Functionality, Multi-Granularity
    EMBEDDING_GEMMA = "@cf/google/embeddinggemma-300m"  # Google's latest, 100+ languages
    QWEN3_EMBEDDING = "@cf/qwen/qwen3-embedding-0.6b"  # Qwen's latest embedding
    
    # English-optimized
    BGE_LARGE = "@cf/baai/bge-large-en-v1.5"  # 1024 dims, high quality
    BGE_BASE = "@cf/baai/bge-base-en-v1.5"  # 768 dims, balanced
    BGE_SMALL = "@cf/baai/bge-small-en-v1.5"  # 384 dims, fast
    
    # ===================
    # TEXT GENERATION (LLMs)
    # ===================
    # Enterprise/Production Tier (highest quality)
    GPT_OSS_120B = "@cf/openai/gpt-oss-120b"  # OpenAI open-weight, production reasoning
    GPT_OSS_20B = "@cf/openai/gpt-oss-20b"  # OpenAI open-weight, faster
    
    # Latest Generation (Llama 4 & 3.3)
    LLAMA_4_SCOUT = "@cf/meta/llama-4-scout-17b-16e-instruct"  # Llama 4, MoE, multimodal, function calling
    LLAMA_3_3_70B_FAST = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"  # 70B optimized, function calling
    
    # Reasoning Models (for complex analytical queries)
    QWQ_32B = "@cf/qwen/qwq-32b"  # Competitive with DeepSeek-R1, o1-mini
    DEEPSEEK_R1 = "@cf/deepseek/deepseek-r1-distill-qwen-32b"  # State-of-the-art reasoning
    
    # RAG-Optimized
    GRANITE_4_MICRO = "@cf/ibm/granite-4.0-h-micro"  # IBM, specifically for RAG & agentic tasks
    
    # Quality Tier
    QWEN3_30B = "@cf/qwen/qwen3-30b-a3b-fp8"  # Qwen3, function calling
    GEMMA_3_12B = "@cf/google/gemma-3-12b-it"  # Google Gemma 3, 128K context, multimodal
    MISTRAL_SMALL = "@cf/mistralai/mistral-small-3.1-24b-instruct"  # 128K context, vision, function calling
    QWEN_32B_CODER = "@cf/qwen/qwen2.5-coder-32b-instruct"  # Code-specialized
    
    # Fast Tier (low latency)
    LLAMA_3_1_8B_FAST = "@cf/meta/llama-3.1-8b-instruct-fast"  # Ultra-fast
    LLAMA_3_1_8B = "@cf/meta/llama-3.1-8b-instruct"  # Standard 8B
    LLAMA_3_2_3B = "@cf/meta/llama-3.2-3b-instruct"  # Tiny, very fast
    LLAMA_3_2_1B = "@cf/meta/llama-3.2-1b-instruct"  # Smallest, fastest
    LLAMA_3_1_70B = "@cf/meta/llama-3.1-70b-instruct"  # Legacy 70B
    
    # ===================
    # RERANKING
    # ===================
    BGE_RERANKER = "@cf/baai/bge-reranker-base"  # Only reranker available
    
    # ===================
    # SUMMARIZATION
    # ===================
    BART_SUMMARIZATION = "@cf/facebook/bart-large-cnn"
    
    # ===================
    # CONTENT SAFETY (Enterprise requirement)
    # ===================
    LLAMA_GUARD = "@cf/meta/llama-guard-3-8b"  # Content safety classification
    
    # ===================
    # SPEECH
    # ===================
    WHISPER = "@cf/openai/whisper"
    WHISPER_TURBO = "@cf/openai/whisper-large-v3-turbo"
    
    # ===================
    # VISION
    # ===================
    LLAMA_3_2_11B_VISION = "@cf/meta/llama-3.2-11b-vision-instruct"  # Image understanding


# Model tiers for automatic selection
class ModelTier(str, Enum):
    """
    Model tiers for automatic selection based on query complexity.
    
    Consistent with workers/src/config/models.ts TIER_MODELS mapping.
    """
    SPEED = "speed"  # Ultra-fast, simple queries (<100ms)
    BALANCED = "balanced"  # Best quality/speed balance (default)
    QUALITY = "quality"  # Highest quality, production use
    REASONING = "reasoning"  # Complex analytical queries


# Tier to model mapping
# Consistent with workers/src/config/models.ts TIER_MODELS
TIER_MODELS = {
    ModelTier.SPEED: CFModel.LLAMA_3_2_3B,  # Ultra-fast for simple tasks
    ModelTier.BALANCED: CFModel.LLAMA_3_3_70B_FAST,  # Best quality/speed balance
    ModelTier.QUALITY: CFModel.GPT_OSS_120B,  # Highest quality
    ModelTier.REASONING: CFModel.QWQ_32B,  # Complex analytical queries
}

# Embedding recommendations
EMBEDDING_RECOMMENDATIONS = {
    "multilingual": CFModel.BGE_M3,  # Best for enterprise, 100+ languages
    "english_quality": CFModel.BGE_LARGE,  # 1024 dims, English-focused
    "english_fast": CFModel.BGE_BASE,  # 768 dims, balanced
    "google": CFModel.EMBEDDING_GEMMA,  # Google's latest
}


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embeddings: List[List[float]]
    model: str
    dimensions: int
    tokens_used: int = 0


@dataclass
class GenerationResult:
    """Result from text generation."""
    text: str
    model: str
    tokens_used: int = 0
    finish_reason: str = "stop"


@dataclass
class RerankResult:
    """Result from reranking."""
    scores: List[float]
    rankings: List[int]
    model: str


@dataclass
class SummarizationResult:
    """Result from summarization."""
    summary: str
    model: str


class CloudflareAIService:
    """
    Enterprise-grade Cloudflare Workers AI service for edge inference.
    
    Designed for industry-leading RAG search with:
    - Multi-lingual embeddings (bge-m3, 100+ languages)
    - Production LLMs (OpenAI gpt-oss-120b, Llama 4, Qwen3)
    - Reasoning models (QwQ-32B, DeepSeek-R1)
    - Content safety (Llama Guard)
    - Automatic model tier selection
    
    50K credits available for cost-effective edge inference.
    """
    
    BASE_URL = "https://api.cloudflare.com/client/v4/accounts"
    
    def __init__(
        self,
        account_id: Optional[str] = None,
        api_token: Optional[str] = None,
        default_embedding_model: Optional[CFModel] = None,
        default_llm_model: Optional[CFModel] = None,
        default_reasoning_model: Optional[CFModel] = None,
        timeout: float = 60.0  # Increased for large models
    ):
        """
        Initialize Cloudflare AI service.
        
        Args:
            account_id: Cloudflare account ID
            api_token: Cloudflare API token with Workers AI access
            default_embedding_model: Default model for embeddings (default: bge-m3 for multilingual)
            default_llm_model: Default model for text generation (default: llama-3.3-70b-fp8-fast)
            default_reasoning_model: Model for complex reasoning (default: qwq-32b)
            timeout: Request timeout in seconds (increased for large models)
        """
        self.account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN")
        
        # Load model preferences from environment or use enterprise defaults
        self.default_embedding_model = default_embedding_model or self._get_env_model(
            "CLOUDFLARE_EMBEDDING_MODEL", CFModel.BGE_M3  # Multi-lingual for enterprise
        )
        self.default_llm_model = default_llm_model or self._get_env_model(
            "CLOUDFLARE_LLM_MODEL", CFModel.LLAMA_3_3_70B_FAST  # Best quality/speed balance
        )
        self.default_reasoning_model = default_reasoning_model or self._get_env_model(
            "CLOUDFLARE_REASONING_MODEL", CFModel.QWQ_32B  # For complex queries
        )
        self.timeout = timeout
        
        self._client: Optional[httpx.AsyncClient] = None
        self._usage_stats = {
            "embeddings": 0,
            "generations": 0,
            "reranks": 0,
            "summarizations": 0,
            "safety_checks": 0,
            "total_tokens": 0
        }
    
    def _get_env_model(self, env_var: str, default: CFModel) -> CFModel:
        """Get model from environment variable or use default."""
        env_value = os.environ.get(env_var)
        if env_value:
            # Try to match to CFModel enum
            for model in CFModel:
                if model.value == env_value:
                    return model
        return default
    
    def select_model_for_tier(self, tier: ModelTier) -> CFModel:
        """Select the appropriate model for a given tier."""
        return TIER_MODELS.get(tier, self.default_llm_model)
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
            )
        return self._client
    
    def _get_url(self, model: str) -> str:
        """Get API URL for a model."""
        return f"{self.BASE_URL}/{self.account_id}/ai/run/{model}"
    
    def _get_responses_url(self) -> str:
        """Get API URL for OpenAI Responses API (gpt-oss models)."""
        return f"{self.BASE_URL}/{self.account_id}/ai/v1/responses"
    
    def _is_openai_model(self, model: CFModel) -> bool:
        """Check if model uses OpenAI Responses API format."""
        return model in [CFModel.GPT_OSS_120B, CFModel.GPT_OSS_20B]
    
    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured."""
        return bool(self.account_id and self.api_token)
    
    async def generate_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[CFModel] = None
    ) -> EmbeddingResult:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text or list of texts to embed
            model: Embedding model to use (default: bge-base-en-v1.5)
            
        Returns:
            EmbeddingResult with embeddings and metadata
            
        Example:
            >>> result = await cf_ai.generate_embeddings("What is AI?")
            >>> print(len(result.embeddings[0]))  # 768 dimensions
        """
        if not self.is_configured:
            raise ValueError("Cloudflare AI not configured. Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN")
        
        model = model or self.default_embedding_model
        
        if isinstance(texts, str):
            texts = [texts]
        
        logger.info("cf_ai_embeddings_start", texts_count=len(texts), model=model.value)
        
        try:
            response = await self.client.post(
                self._get_url(model.value),
                json={"text": texts}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ValueError(f"API error: {data.get('errors', 'Unknown error')}")
            
            result_data = data.get("result", {})
            embeddings = result_data.get("data", [])
            
            # Track usage
            self._usage_stats["embeddings"] += len(texts)
            
            # Get dimensions from first embedding
            dimensions = len(embeddings[0]) if embeddings else 0
            
            logger.info("cf_ai_embeddings_complete", 
                       texts_count=len(texts), 
                       dimensions=dimensions,
                       model=model.value)
            
            return EmbeddingResult(
                embeddings=embeddings,
                model=model.value,
                dimensions=dimensions,
                tokens_used=len(texts)  # Approximate
            )
            
        except httpx.HTTPError as e:
            logger.error("cf_ai_embeddings_error", error=str(e), model=model.value)
            raise
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[CFModel] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        reasoning_effort: Optional[Literal["low", "medium", "high"]] = None
    ) -> GenerationResult:
        """
        Generate text using LLM.
        
        Supports both standard Cloudflare AI models and OpenAI Responses API models
        (gpt-oss-120b, gpt-oss-20b).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: LLM model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response
            reasoning_effort: For OpenAI models - "low", "medium", or "high"
            
        Returns:
            GenerationResult with generated text
            
        Example:
            >>> result = await cf_ai.generate_text(
            ...     "Summarize the key points about AI",
            ...     system_prompt="You are a helpful assistant."
            ... )
            >>> print(result.text)
        """
        if not self.is_configured:
            raise ValueError("Cloudflare AI not configured")
        
        model = model or self.default_llm_model
        
        logger.info("cf_ai_generation_start", 
                   prompt_length=len(prompt), 
                   model=model.value,
                   max_tokens=max_tokens,
                   is_openai=self._is_openai_model(model))
        
        try:
            # Use different API format for OpenAI models (gpt-oss-120b, gpt-oss-20b)
            if self._is_openai_model(model):
                return await self._generate_with_openai_api(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    reasoning_effort=reasoning_effort
                )
            
            # Standard Cloudflare AI format for other models
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.post(
                self._get_url(model.value),
                json={
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": stream
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ValueError(f"API error: {data.get('errors', 'Unknown error')}")
            
            result = data.get("result", {})
            generated_text = result.get("response", "")
            
            # Track usage
            self._usage_stats["generations"] += 1
            self._usage_stats["total_tokens"] += max_tokens  # Approximate
            
            logger.info("cf_ai_generation_complete",
                       output_length=len(generated_text),
                       model=model.value)
            
            return GenerationResult(
                text=generated_text,
                model=model.value,
                tokens_used=max_tokens,
                finish_reason="stop"
            )
            
        except httpx.HTTPError as e:
            logger.error("cf_ai_generation_error", error=str(e), model=model.value)
            raise
    
    async def _generate_with_openai_api(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: CFModel = None,
        reasoning_effort: Optional[Literal["low", "medium", "high"]] = "medium"
    ) -> GenerationResult:
        """
        Generate text using OpenAI Responses API format (for gpt-oss models).
        
        These models use a different API format:
        - Endpoint: /ai/v1/responses
        - Input: {"model": "...", "input": "...", "reasoning": {...}}
        """
        model = model or CFModel.GPT_OSS_120B
        
        # Build input with optional system prompt
        if system_prompt:
            full_input = f"{system_prompt}\n\n{prompt}"
        else:
            full_input = prompt
        
        # Build request payload
        payload = {
            "model": model.value,
            "input": full_input,
        }
        
        # Add reasoning parameters for production-grade responses
        if reasoning_effort:
            payload["reasoning"] = {
                "effort": reasoning_effort,
                "summary": "auto"
            }
        
        logger.info("cf_ai_openai_generation_start",
                   model=model.value,
                   input_length=len(full_input),
                   reasoning_effort=reasoning_effort)
        
        try:
            response = await self.client.post(
                self._get_responses_url(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # OpenAI Responses API format:
            # {
            #   "output": [
            #     {"type": "reasoning", "content": [{"text": "...", "type": "reasoning_text"}]},
            #     {"type": "message", "content": [{"text": "...", "type": "output_text"}]}
            #   ],
            #   "usage": {"input_tokens": N, "output_tokens": M, "total_tokens": T}
            # }
            generated_text = ""
            tokens_used = 0
            reasoning_text = ""
            
            # Extract from output array
            output = data.get("output", [])
            if isinstance(output, list):
                for item in output:
                    item_type = item.get("type", "")
                    content = item.get("content", [])
                    
                    if item_type == "message" and content:
                        # This is the actual response
                        for c in content:
                            if c.get("type") == "output_text":
                                generated_text = c.get("text", "")
                                break
                    elif item_type == "reasoning" and content:
                        # This is the reasoning (chain-of-thought)
                        for c in content:
                            if c.get("type") == "reasoning_text":
                                reasoning_text = c.get("text", "")
                                break
            
            # Get token usage
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            
            # Track usage
            self._usage_stats["generations"] += 1
            self._usage_stats["total_tokens"] += tokens_used
            
            logger.info("cf_ai_openai_generation_complete",
                       output_length=len(generated_text),
                       reasoning_length=len(reasoning_text),
                       tokens_used=tokens_used,
                       model=model.value)
            
            return GenerationResult(
                text=generated_text,
                model=model.value,
                tokens_used=tokens_used,
                finish_reason="stop"
            )
            
        except httpx.HTTPError as e:
            logger.error("cf_ai_openai_generation_error", 
                        error=str(e), 
                        model=model.value,
                        status=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None)
            raise
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        model: CFModel = CFModel.BGE_RERANKER,
        top_k: Optional[int] = None
    ) -> RerankResult:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: Search query
            documents: List of documents to rerank
            model: Reranker model
            top_k: Return only top K results
            
        Returns:
            RerankResult with scores and rankings
            
        Example:
            >>> result = await cf_ai.rerank(
            ...     "What is machine learning?",
            ...     ["ML is...", "Deep learning...", "Python is..."]
            ... )
            >>> print(result.rankings)  # [0, 1, 2] sorted by relevance
        """
        if not self.is_configured:
            raise ValueError("Cloudflare AI not configured")
        
        logger.info("cf_ai_rerank_start", 
                   query_length=len(query), 
                   docs_count=len(documents))
        
        try:
            # BGE reranker expects query-document pairs
            pairs = [[query, doc] for doc in documents]
            
            response = await self.client.post(
                self._get_url(model.value),
                json={"text": pairs}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ValueError(f"API error: {data.get('errors', 'Unknown error')}")
            
            result = data.get("result", {})
            scores = result.get("data", [])
            
            # Sort by score descending to get rankings
            indexed_scores = list(enumerate(scores))
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            rankings = [idx for idx, _ in indexed_scores]
            sorted_scores = [score for _, score in indexed_scores]
            
            if top_k:
                rankings = rankings[:top_k]
                sorted_scores = sorted_scores[:top_k]
            
            self._usage_stats["reranks"] += 1
            
            logger.info("cf_ai_rerank_complete", docs_count=len(documents))
            
            return RerankResult(
                scores=sorted_scores,
                rankings=rankings,
                model=model.value
            )
            
        except httpx.HTTPError as e:
            logger.error("cf_ai_rerank_error", error=str(e))
            raise
    
    async def summarize(
        self,
        text: str,
        max_length: int = 150,
        min_length: int = 30,
        model: CFModel = CFModel.BART_SUMMARIZATION
    ) -> SummarizationResult:
        """
        Summarize text.
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
            min_length: Minimum summary length
            model: Summarization model
            
        Returns:
            SummarizationResult with summary
            
        Example:
            >>> result = await cf_ai.summarize(long_article)
            >>> print(result.summary)
        """
        if not self.is_configured:
            raise ValueError("Cloudflare AI not configured")
        
        logger.info("cf_ai_summarize_start", text_length=len(text))
        
        try:
            response = await self.client.post(
                self._get_url(model.value),
                json={
                    "input_text": text,
                    "max_length": max_length,
                    "min_length": min_length
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ValueError(f"API error: {data.get('errors', 'Unknown error')}")
            
            result = data.get("result", {})
            summary = result.get("summary", "")
            
            self._usage_stats["summarizations"] += 1
            
            logger.info("cf_ai_summarize_complete", summary_length=len(summary))
            
            return SummarizationResult(
                summary=summary,
                model=model.value
            )
            
        except httpx.HTTPError as e:
            logger.error("cf_ai_summarize_error", error=str(e))
            raise
    
    async def generate_answer(
        self,
        question: str,
        context: List[str],
        model: Optional[CFModel] = None,
        max_tokens: int = 512,
        use_reasoning: bool = False
    ) -> str:
        """
        Generate answer to question using context (RAG).
        
        Args:
            question: User question
            context: List of context documents
            model: LLM model to use
            max_tokens: Maximum tokens for answer
            use_reasoning: Use reasoning model for complex analytical queries
            
        Returns:
            Generated answer string
        """
        # Select model based on query complexity
        if model is None:
            if use_reasoning:
                model = self.default_reasoning_model
            else:
                model = self.default_llm_model
        
        # Build context string
        context_str = "\n\n".join([f"Source {i+1}:\n{doc}" for i, doc in enumerate(context)])
        
        system_prompt = """You are a helpful search assistant. Answer the user's question based ONLY on the provided sources. 
If the sources don't contain relevant information, say so. Be concise and cite sources when possible."""
        
        prompt = f"""Sources:
{context_str}

Question: {question}

Answer based on the sources above:"""
        
        result = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=0.3  # Lower temperature for factual responses
        )
        
        return result.text
    
    async def check_content_safety(
        self,
        text: str,
        check_prompt: bool = True,
        check_response: bool = False
    ) -> Dict[str, Any]:
        """
        Check content safety using Llama Guard (enterprise requirement).
        
        Args:
            text: Text to check
            check_prompt: Whether this is a user prompt (vs response)
            check_response: Whether this is an LLM response
            
        Returns:
            Dict with 'safe' boolean and 'categories' list if unsafe
            
        Example:
            >>> result = await cf_ai.check_content_safety("Some text to check")
            >>> if not result['safe']:
            ...     print(f"Unsafe content: {result['categories']}")
        """
        if not self.is_configured:
            raise ValueError("Cloudflare AI not configured")
        
        logger.info("cf_ai_safety_check_start", text_length=len(text))
        
        try:
            # Llama Guard expects specific prompt format
            role = "User" if check_prompt else "Agent"
            prompt = f"""<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Task: Check if there is unsafe content in '{role}' messages in conversations according to our safety policy.

<BEGIN CONVERSATION>

{role}: {text}

<END CONVERSATION>

Provide your safety assessment for {role} in the above conversation:
- First line must read 'safe' or 'unsafe'.
- If unsafe, a second line must include a comma-separated list of violated categories.<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
            
            response = await self.client.post(
                self._get_url(CFModel.LLAMA_GUARD.value),
                json={
                    "prompt": prompt,
                    "max_tokens": 50
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise ValueError(f"API error: {data.get('errors', 'Unknown error')}")
            
            result = data.get("result", {})
            output = result.get("response", "").strip().lower()
            
            self._usage_stats["safety_checks"] += 1
            
            # Parse response
            lines = output.split('\n')
            is_safe = lines[0].strip() == 'safe' if lines else True
            categories = []
            
            if not is_safe and len(lines) > 1:
                categories = [c.strip() for c in lines[1].split(',')]
            
            logger.info("cf_ai_safety_check_complete", 
                       safe=is_safe, 
                       categories=categories)
            
            return {
                "safe": is_safe,
                "categories": categories,
                "raw_response": output
            }
            
        except httpx.HTTPError as e:
            logger.error("cf_ai_safety_check_error", error=str(e))
            # Fail open - return safe on error to not block
            return {"safe": True, "categories": [], "error": str(e)}
    
    async def generate_with_reasoning(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048
    ) -> GenerationResult:
        """
        Generate response using reasoning model for complex analytical queries.
        
        Uses QwQ-32B or DeepSeek-R1 which are competitive with o1-mini.
        
        Args:
            prompt: User prompt requiring reasoning
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens (higher for reasoning)
            
        Returns:
            GenerationResult with chain-of-thought reasoning
        """
        return await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.default_reasoning_model,
            max_tokens=max_tokens,
            temperature=0.7  # Reasoning models benefit from some creativity
        )
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics."""
        return self._usage_stats.copy()
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_cf_ai_service: Optional[CloudflareAIService] = None


async def get_cloudflare_ai_service() -> CloudflareAIService:
    """Get or create Cloudflare AI service instance."""
    global _cf_ai_service
    if _cf_ai_service is None:
        _cf_ai_service = CloudflareAIService()
    return _cf_ai_service
