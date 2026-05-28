"""
RAG (Retrieval-Augmented Generation) service for AI agent web search pipelines.

This module provides:
- Research query generation for comprehensive topic coverage
- Embedding generation for semantic search
- Vector storage and retrieval
- Content summarization and relevance scoring
- Integration with SearXNG search backend

Dependencies:
- numpy: For vector operations (pip install numpy)
- httpx: For async HTTP requests
- Optional: openai API key for embeddings, or use compatible API
"""
import asyncio
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import httpx
from httpx import AsyncClient
import structlog

# NumPy for vector operations (optional fallback if not installed)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

from app.config import get_settings
from app.services.core.searxng import SearXNGService, get_searxng_service
from app.services.scraping.scraping import ContentScrapingService, get_scraping_service
from app.services.ai.cloudflare_ai import get_cloudflare_ai_service
from app.models.responses import SearchResult, ScrapedContent
from app.utils.text_processing import sanitize_text, extract_keywords, calculate_text_quality

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class ResearchSource:
    """Represents a research source with content and metadata."""
    url: str
    title: str
    content: str
    summary: Optional[str] = None
    relevance_score: float = 0.0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    word_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content[:1000] if self.content else "",  # Truncate for storage
            "summary": self.summary,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
            "scraped_at": self.scraped_at.isoformat(),
            "word_count": self.word_count
        }


@dataclass  
class ResearchResult:
    """Result of a research operation."""
    query: str
    sources: List[ResearchSource]
    total_sources_found: int
    queries_executed: List[str]
    processing_time_ms: int
    corpus_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "sources": [s.to_dict() for s in self.sources],
            "total_sources_found": self.total_sources_found,
            "queries_executed": self.queries_executed,
            "processing_time_ms": self.processing_time_ms,
            "corpus_id": self.corpus_id
        }


class EmbeddingService:
    """
    Service for generating text embeddings.
    
    Supports multiple backends (in priority order):
    1. Cloudflare Workers AI (BGE models) - 50K free credits
    2. OpenAI API (text-embedding-3-small)
    3. Local models via compatible API
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key if hasattr(settings, 'openai_api_key') else None
        self.base_url = base_url or getattr(settings, 'embedding_api_url', 'https://api.openai.com/v1')
        self.model = getattr(settings, 'embedding_model', 'text-embedding-3-small')
        self._client: Optional[AsyncClient] = None
        self._cf_ai = None
        self._use_cloudflare = getattr(settings, 'cloudflare_ai_enabled', True)
        
    async def initialize(self):
        """Initialize HTTP client and Cloudflare AI."""
        if not self._client:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = AsyncClient(
                timeout=httpx.Timeout(60.0),
                headers=headers
            )
        
        # Try to initialize Cloudflare AI
        if self._use_cloudflare and self._cf_ai is None:
            try:
                from app.services.ai.cloudflare_ai import get_cloudflare_ai_service
                self._cf_ai = await get_cloudflare_ai_service()
            except Exception as e:
                logger.warning("cloudflare_ai_init_failed", error=str(e))
                self._cf_ai = None
            
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._cf_ai:
            await self._cf_ai.close()
            self._cf_ai = None
            
    async def generate_embeddings(
        self, 
        texts: List[str],
        batch_size: int = 20
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Priority:
        1. Cloudflare Workers AI (free/cheap edge inference)
        2. OpenAI API (fallback)
        3. Zero vectors (emergency fallback)
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per batch
            
        Returns:
            List of embedding vectors
        """
        if not self._client:
            await self.initialize()
        
        # Try Cloudflare AI first (50K credits available)
        if self._cf_ai and self._cf_ai.is_configured:
            try:
                result = await self._cf_ai.generate_embeddings(texts)
                logger.info("embeddings_via_cloudflare", count=len(texts), dims=result.dimensions)
                return result.embeddings
            except Exception as e:
                logger.warning("cloudflare_embeddings_fallback", error=str(e))
            
        if not self.api_key:
            logger.warning("embedding_api_key_not_configured")
            # Return zero vectors as fallback (768 dims for BGE compatibility)
            return [[0.0] * 768 for _ in texts]
            
        all_embeddings = []
        
        # Process in batches via OpenAI
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = await self._client.post(
                    f"{self.base_url}/embeddings",
                    json={
                        "model": self.model,
                        "input": batch
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(
                    "embeddings_generated",
                    batch_size=len(batch),
                    total_processed=len(all_embeddings)
                )
                
            except Exception as e:
                logger.error("embedding_generation_failed", error=str(e), batch_index=i)
                # Return zero vectors for failed batch
                all_embeddings.extend([[0.0] * 1536 for _ in batch])
                
        return all_embeddings
        
    async def generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else [0.0] * 1536


class VectorStore:
    """
    Simple in-memory vector store for RAG retrieval.
    
    For production, integrate with:
    - Cloudflare Vectorize
    - Pinecone
    - Qdrant
    - ChromaDB
    """
    
    def __init__(self):
        self._vectors: Dict[str, Dict[str, Any]] = {}  # corpus_id -> {id: {embedding, metadata}}
        
    def add_vectors(
        self, 
        corpus_id: str,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]]
    ):
        """
        Add vectors to the store.
        
        Args:
            corpus_id: Identifier for the corpus/collection
            vectors: List of (id, embedding, metadata) tuples
        """
        if corpus_id not in self._vectors:
            self._vectors[corpus_id] = {}
            
        for vec_id, embedding, metadata in vectors:
            self._vectors[corpus_id][vec_id] = {
                "embedding": embedding,
                "metadata": metadata
            }
            
        logger.info(
            "vectors_added",
            corpus_id=corpus_id,
            count=len(vectors),
            total=len(self._vectors[corpus_id])
        )
        
    def search(
        self, 
        corpus_id: str,
        query_embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar vectors using cosine similarity.
        
        Args:
            corpus_id: Corpus to search in
            query_embedding: Query vector
            limit: Maximum results to return
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of (id, score, metadata) tuples sorted by score descending
        """
        if corpus_id not in self._vectors:
            return []
            
        results = []
        
        if NUMPY_AVAILABLE:
            query_norm = np.linalg.norm(query_embedding)
            
            if query_norm == 0:
                return []
                
            for vec_id, data in self._vectors[corpus_id].items():
                embedding = data["embedding"]
                vec_norm = np.linalg.norm(embedding)
                
                if vec_norm == 0:
                    continue
                    
                # Cosine similarity
                similarity = np.dot(query_embedding, embedding) / (query_norm * vec_norm)
                
                # Convert to 0-1 range (cosine similarity is -1 to 1)
                score = (similarity + 1) / 2
                
                if score >= min_score:
                    results.append((vec_id, score, data["metadata"]))
        else:
            # Fallback: Pure Python implementation (slower but works without numpy)
            query_norm = sum(x**2 for x in query_embedding) ** 0.5
            
            if query_norm == 0:
                return []
                
            for vec_id, data in self._vectors[corpus_id].items():
                embedding = data["embedding"]
                vec_norm = sum(x**2 for x in embedding) ** 0.5
                
                if vec_norm == 0:
                    continue
                    
                # Dot product
                dot_product = sum(a * b for a, b in zip(query_embedding, embedding))
                
                # Cosine similarity
                similarity = dot_product / (query_norm * vec_norm)
                
                # Convert to 0-1 range
                score = (similarity + 1) / 2
                
                if score >= min_score:
                    results.append((vec_id, score, data["metadata"]))
                
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
        
    def delete_corpus(self, corpus_id: str):
        """Delete all vectors for a corpus."""
        if corpus_id in self._vectors:
            del self._vectors[corpus_id]
            logger.info("corpus_deleted", corpus_id=corpus_id)
            
    def get_corpus_size(self, corpus_id: str) -> int:
        """Get number of vectors in a corpus."""
        return len(self._vectors.get(corpus_id, {}))


class RAGService:
    """
    Main RAG service for AI agent web search pipelines.
    
    Provides:
    - Multi-query research with parallel execution
    - Content extraction and summarization
    - Embedding generation and vector storage
    - Semantic search across research corpus
    - Relevance scoring
    """
    
    def __init__(self):
        self.searxng: Optional[SearXNGService] = None
        self.scraper: Optional[ContentScrapingService] = None
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self._initialized = False
        
    async def initialize(self):
        """Initialize all dependent services."""
        if self._initialized:
            return
            
        self.searxng = await get_searxng_service()
        self.scraper = await get_scraping_service()
        await self.embedding_service.initialize()
        self._initialized = True
        
        logger.info("rag_service_initialized")
        
    async def close(self):
        """Close all service connections."""
        await self.embedding_service.close()
        self._initialized = False
        
    def generate_research_queries(
        self,
        topic: str,
        num_queries: int = 10,
        include_categories: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate diverse research queries for comprehensive topic coverage.
        
        Based on the Agency implementation's query generation approach.
        
        Args:
            topic: Main research topic
            num_queries: Number of queries to generate
            include_categories: Specific categories to include
            
        Returns:
            List of diverse search queries
        """
        categories = include_categories or [
            "overview",
            "history",
            "current_state", 
            "technical",
            "practical",
            "comparison",
            "expert_opinion",
            "future_trends",
            "case_studies",
            "best_practices"
        ]
        
        query_templates = {
            "overview": [
                f"what is {topic}",
                f"{topic} explained",
                f"{topic} introduction guide",
            ],
            "history": [
                f"history of {topic}",
                f"{topic} evolution over time",
                f"origin and development of {topic}",
            ],
            "current_state": [
                f"{topic} 2024 latest",
                f"current state of {topic}",
                f"{topic} recent developments",
            ],
            "technical": [
                f"{topic} how it works",
                f"{topic} technical details",
                f"{topic} architecture implementation",
            ],
            "practical": [
                f"{topic} practical examples",
                f"how to use {topic}",
                f"{topic} tutorial guide",
            ],
            "comparison": [
                f"{topic} vs alternatives",
                f"{topic} comparison analysis",
                f"best {topic} options compared",
            ],
            "expert_opinion": [
                f"{topic} expert analysis",
                f"{topic} industry insights",
                f"what experts say about {topic}",
            ],
            "future_trends": [
                f"future of {topic}",
                f"{topic} predictions forecast",
                f"{topic} emerging trends",
            ],
            "case_studies": [
                f"{topic} case studies",
                f"{topic} real world examples",
                f"{topic} success stories",
            ],
            "best_practices": [
                f"{topic} best practices",
                f"{topic} tips and recommendations",
                f"common {topic} mistakes to avoid",
            ]
        }
        
        queries = []
        
        # Add base query
        queries.append(topic)
        
        # Generate queries from each category
        for category in categories:
            if category in query_templates:
                templates = query_templates[category]
                # Take first template from each category for diversity
                if templates and len(queries) < num_queries:
                    queries.append(templates[0])
                    
        # Ensure we have the requested number of queries
        while len(queries) < num_queries:
            # Add more specific queries
            queries.append(f"{topic} detailed analysis")
            
        return queries[:num_queries]
        
    async def deep_research(
        self,
        topic: str,
        num_queries: int = 10,
        max_sources_per_query: int = 10,
        target_total_sources: int = 50,
        scrape_content: bool = True,
        generate_embeddings: bool = True,
        engines: Optional[List[str]] = None
    ) -> ResearchResult:
        """
        Perform deep research on a topic using multiple queries.
        
        This implements a two-phase research approach:
        1. Generate diverse queries for comprehensive coverage
        2. Execute parallel searches and aggregate results
        
        Args:
            topic: Research topic
            num_queries: Number of search queries to execute
            max_sources_per_query: Maximum sources per query
            target_total_sources: Target total unique sources
            scrape_content: Whether to scrape full page content
            generate_embeddings: Whether to generate embeddings for vector search
            engines: Search engines to use
            
        Returns:
            ResearchResult with all gathered sources
        """
        if not self._initialized:
            await self.initialize()
            
        start_time = asyncio.get_event_loop().time()
        
        # Generate research queries
        queries = self.generate_research_queries(topic, num_queries)
        
        logger.info(
            "deep_research_started",
            topic=topic,
            num_queries=len(queries),
            target_sources=target_total_sources
        )
        
        # Execute searches in parallel batches
        all_sources: List[ResearchSource] = []
        seen_urls = set()
        search_engines = engines or settings.searxng_enabled_engines[:3]
        
        # Process queries in batches of 5 for rate limiting
        batch_size = 5
        for i in range(0, len(queries), batch_size):
            batch_queries = queries[i:i + batch_size]
            
            # Execute batch searches in parallel
            search_tasks = [
                self._search_and_extract(
                    query=q,
                    max_results=max_sources_per_query,
                    engines=search_engines,
                    scrape_content=scrape_content
                )
                for q in batch_queries
            ]
            
            batch_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results
            for query, result in zip(batch_queries, batch_results):
                if isinstance(result, Exception):
                    logger.error("research_query_failed", query=query, error=str(result))
                    continue
                    
                for source in result:
                    if source.url not in seen_urls:
                        seen_urls.add(source.url)
                        all_sources.append(source)
                        
            # Check if we've reached target
            if len(all_sources) >= target_total_sources:
                break
                
            # Small delay between batches
            await asyncio.sleep(0.5)
            
        # Score relevance
        for source in all_sources:
            source.relevance_score = self._calculate_relevance(source, topic)
            
        # Sort by relevance
        all_sources.sort(key=lambda s: s.relevance_score, reverse=True)
        
        # Limit to target
        all_sources = all_sources[:target_total_sources]
        
        # Generate embeddings if requested
        corpus_id = None
        if generate_embeddings and all_sources:
            corpus_id = hashlib.md5(topic.encode()).hexdigest()[:16]
            await self._generate_and_store_embeddings(corpus_id, all_sources)
            
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        result = ResearchResult(
            query=topic,
            sources=all_sources,
            total_sources_found=len(seen_urls),
            queries_executed=queries,
            processing_time_ms=processing_time_ms,
            corpus_id=corpus_id
        )
        
        logger.info(
            "deep_research_completed",
            topic=topic,
            sources_found=len(all_sources),
            processing_time_ms=processing_time_ms,
            corpus_id=corpus_id
        )
        
        return result
        
    async def _search_and_extract(
        self,
        query: str,
        max_results: int,
        engines: List[str],
        scrape_content: bool
    ) -> List[ResearchSource]:
        """Search and optionally scrape content."""
        sources = []
        
        try:
            # Perform search
            search_results = await self.searxng.search(
                query=query,
                engines=engines,
                language="en"
            )
            
            search_results = search_results[:max_results]
            
            if scrape_content and search_results:
                # Scrape content for search results
                urls = [r.url for r in search_results]
                scraped = await self.scraper.scrape_urls(urls[:10])  # Limit concurrent scraping
                
                scraped_map = {str(s.url): s for s in scraped if s.extraction_success}
                
                for result in search_results:
                    content = ""
                    word_count = 0
                    
                    if str(result.url) in scraped_map:
                        scraped_content = scraped_map[str(result.url)]
                        content = scraped_content.text
                        word_count = scraped_content.word_count
                    else:
                        content = result.snippet
                        word_count = len(result.snippet.split())
                        
                    source = ResearchSource(
                        url=str(result.url),
                        title=result.title,
                        content=content,
                        word_count=word_count,
                        metadata={
                            "engine": result.engine,
                            "snippet": result.snippet,
                            "rank": result.rank
                        }
                    )
                    
                    # Generate summary for content > 200 chars
                    if content and len(content) > 200:
                        try:
                            cf_ai = await get_cloudflare_ai_service()
                            if cf_ai and cf_ai.is_configured:
                                summary_result = await cf_ai.summarize(content[:3000])
                                source.summary = summary_result.summary
                        except Exception as e:
                            logger.warning("summary_generation_failed", url=source.url, error=str(e))
                    
                    sources.append(source)
            else:
                # Use search snippets only
                for result in search_results:
                    source = ResearchSource(
                        url=str(result.url),
                        title=result.title,
                        content=result.snippet,
                        word_count=len(result.snippet.split()),
                        metadata={
                            "engine": result.engine,
                            "rank": result.rank
                        }
                    )
                    sources.append(source)
                    
        except Exception as e:
            logger.error("search_extract_failed", query=query, error=str(e))
            
        return sources
        
    def _calculate_relevance(self, source: ResearchSource, query: str) -> float:
        """
        Calculate relevance score for a source.
        
        Based on Agency implementation's scoring approach.
        """
        score = 0.0
        query_terms = set(query.lower().split())
        
        # Title match (0-0.3)
        title_terms = set(source.title.lower().split())
        title_overlap = len(query_terms & title_terms) / max(len(query_terms), 1)
        score += title_overlap * 0.3
        
        # Content match (0-0.4)
        content_lower = source.content.lower()
        content_matches = sum(1 for term in query_terms if term in content_lower)
        content_score = content_matches / max(len(query_terms), 1)
        score += content_score * 0.4
        
        # Content quality (0-0.2)
        quality = calculate_text_quality(source.content)
        score += quality * 0.2
        
        # Length bonus (0-0.1)
        if source.word_count >= 500:
            score += 0.1
        elif source.word_count >= 200:
            score += 0.05
            
        return min(score, 1.0)
        
    async def _generate_and_store_embeddings(
        self,
        corpus_id: str,
        sources: List[ResearchSource]
    ):
        """Generate embeddings and store in vector store."""
        # Prepare texts for embedding
        texts = []
        for source in sources:
            # Combine title and content for better semantic representation
            text = f"{source.title}\n\n{source.content[:2000]}"  # Limit content length
            texts.append(text)
            
        # Generate embeddings
        embeddings = await self.embedding_service.generate_embeddings(texts)
        
        # Prepare vectors for storage
        vectors = []
        for i, (source, embedding) in enumerate(zip(sources, embeddings)):
            source.embedding = embedding
            vec_id = hashlib.md5(source.url.encode()).hexdigest()
            
            vectors.append((
                vec_id,
                embedding,
                {
                    "url": source.url,
                    "title": source.title,
                    "summary": source.content[:500],
                    "relevance_score": source.relevance_score
                }
            ))
            
        # Store vectors
        self.vector_store.add_vectors(corpus_id, vectors)
        
        logger.info(
            "embeddings_stored",
            corpus_id=corpus_id,
            count=len(vectors)
        )
        
    async def semantic_search(
        self,
        corpus_id: str,
        query: str,
        limit: int = 10,
        min_relevance: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search over a research corpus.
        
        Args:
            corpus_id: Corpus to search in
            query: Search query
            limit: Maximum results
            min_relevance: Minimum relevance score
            
        Returns:
            List of matching sources with scores
        """
        if not self._initialized:
            await self.initialize()
            
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_single_embedding(query)
        
        # Search vector store
        results = self.vector_store.search(
            corpus_id=corpus_id,
            query_embedding=query_embedding,
            limit=limit,
            min_score=min_relevance
        )
        
        # Format results
        formatted = []
        for vec_id, score, metadata in results:
            formatted.append({
                "id": vec_id,
                "score": score,
                **metadata
            })
            
        logger.info(
            "semantic_search_completed",
            corpus_id=corpus_id,
            query=query[:50],
            results=len(formatted)
        )
        
        return formatted
        
    async def search_and_answer(
        self,
        query: str,
        max_sources: int = 10,
        scrape_content: bool = True,
        engines: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Single-query search optimized for RAG answer generation.
        
        Args:
            query: Search query
            max_sources: Maximum sources to retrieve
            scrape_content: Whether to scrape full content
            engines: Search engines to use
            
        Returns:
            Dictionary with sources and context for answer generation
        """
        if not self._initialized:
            await self.initialize()
            
        start_time = asyncio.get_event_loop().time()
        
        sources = await self._search_and_extract(
            query=query,
            max_results=max_sources,
            engines=engines or settings.searxng_enabled_engines[:3],
            scrape_content=scrape_content
        )
        
        # Score and sort
        for source in sources:
            source.relevance_score = self._calculate_relevance(source, query)
        sources.sort(key=lambda s: s.relevance_score, reverse=True)
        
        # Build context for RAG
        context_parts = []
        for i, source in enumerate(sources[:5]):  # Top 5 for context
            context_parts.append(
                f"[Source {i+1}] {source.title}\n"
                f"URL: {source.url}\n"
                f"Content: {source.content[:1000]}\n"
            )
            
        processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        return {
            "query": query,
            "context": "\n---\n".join(context_parts),
            "sources": [s.to_dict() for s in sources],
            "source_count": len(sources),
            "processing_time_ms": processing_time_ms
        }


# Singleton instance
_rag_service: Optional[RAGService] = None


async def get_rag_service() -> RAGService:
    """Get or create RAG service instance."""
    global _rag_service
    
    if _rag_service is None:
        _rag_service = RAGService()
        await _rag_service.initialize()
        
    return _rag_service
