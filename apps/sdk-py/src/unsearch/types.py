from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    from typing import Literal, NotRequired, TypedDict
else:
    from typing_extensions import Literal, NotRequired, TypedDict


SafeSearch = Literal["off", "moderate", "strict"]
ModelTier = Literal["fast", "balanced", "reasoning"]
ResearchStatus = Literal["running", "completed", "failed"]


class SearchRequest(TypedDict, total=False):
    query: str
    engines: NotRequired[List[str]]
    max_results: NotRequired[int]
    language: NotRequired[str]
    safe_search: NotRequired[SafeSearch]
    scrape_content: NotRequired[bool]
    use_cache: NotRequired[bool]


class CitationEnvelope(TypedDict, total=False):
    v: int
    url: str
    fetched_at: str
    content_sha256: str
    content_type: str
    content_bytes: int
    snapshot_key: str
    engine: str
    agent_run_id: NotRequired[str]
    api_key_id: NotRequired[str]
    signed_at: str
    signing_key_id: NotRequired[str]
    signing_alg: str
    signature: str


class ScrapedContent(TypedDict, total=False):
    text: str
    html: NotRequired[str]
    citation_envelope: NotRequired[CitationEnvelope]


class SearchResult(TypedDict, total=False):
    rank: int
    title: str
    url: str
    snippet: str
    engine: str
    score: Optional[float]
    scraped_content: NotRequired[Optional[ScrapedContent]]
    citation_envelope: NotRequired[CitationEnvelope]


class SearchResponse(TypedDict, total=False):
    query: str
    results: List[SearchResult]
    response_time_ms: int
    cache_hit: bool
    request_id: NotRequired[str]


class ExtractRequest(TypedDict, total=False):
    urls: List[str]
    include_images: NotRequired[bool]
    extract_depth: NotRequired[Literal["basic", "advanced"]]


class ExtractedContentResult(TypedDict, total=False):
    url: str
    raw_content: str
    images: NotRequired[List[str]]
    failed: bool
    error: NotRequired[str]
    citation_envelope: NotRequired[CitationEnvelope]


class ExtractResponse(TypedDict, total=False):
    results: List[ExtractedContentResult]
    failed_urls: List[str]
    response_time: float


class NeuralSearchRequest(TypedDict, total=False):
    query: str
    top_k: NotRequired[int]
    use_autoprompt: NotRequired[bool]
    category: NotRequired[str]
    namespace: NotRequired[str]


class VectorMatch(TypedDict, total=False):
    id: str
    score: float
    metadata: NotRequired[Dict[str, Any]]


class NeuralSearchResponse(TypedDict, total=False):
    query: str
    expanded_from: NotRequired[str]
    matches: List[VectorMatch]


class SimilarRequest(TypedDict, total=False):
    url: NotRequired[str]
    text: NotRequired[str]
    top_k: NotRequired[int]


class SimilarResponse(TypedDict, total=False):
    matches: List[VectorMatch]


class HighlightsRequest(TypedDict, total=False):
    query: str
    document: str
    num_highlights: NotRequired[int]


class Highlight(TypedDict, total=False):
    text: str
    relevance: float


class HighlightsResponse(TypedDict, total=False):
    highlights: List[Highlight]


class RagQueryRequest(TypedDict, total=False):
    query: str
    namespace: NotRequired[str]
    top_k: NotRequired[int]
    model_tier: NotRequired[ModelTier]


class RagQueryResponse(TypedDict, total=False):
    query: str
    answer: str
    sources: List[VectorMatch]


class IngestDocument(TypedDict, total=False):
    id: NotRequired[str]
    text: str
    metadata: NotRequired[Dict[str, Any]]


class IngestRequest(TypedDict, total=False):
    namespace: NotRequired[str]
    documents: List[IngestDocument]


class IngestResponse(TypedDict, total=False):
    ingested: int
    mutation_id: str
    namespace: str


class ResearchStep(TypedDict, total=False):
    step: int
    query: str
    reasoning: str
    results: List[SearchResult]
    finishedAt: int


class ResearchSession(TypedDict, total=False):
    session_id: str
    status: ResearchStatus
    steps: List[ResearchStep]
    finalAnswer: NotRequired[str]


class MonitorRequest(TypedDict, total=False):
    topic: str
    query: str
    interval_minutes: NotRequired[int]
    webhook_url: NotRequired[str]


class StreamEvent(TypedDict):
    event: str
    data: str
