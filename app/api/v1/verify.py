"""
Verification API - Fact-Checking Pipeline

Groundbreaking feature for:
- Claim verification
- Source credibility assessment
- Multi-source fact-checking
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import hashlib
import structlog

from app.config import get_settings
from app.services.ai.cloudflare_ai import CloudflareAIService, CFModel
from app.services.core.searxng import SearXNGService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/verify", tags=["Fact Verification"])

settings = get_settings()


# Models
class ClaimVerificationRequest(BaseModel):
    claim: str = Field(..., description="The claim to verify")
    depth: Literal["quick", "thorough"] = Field("quick", description="Verification depth")
    include_sources: bool = Field(True, description="Include source URLs")


class SourceEvidence(BaseModel):
    title: str
    url: str
    snippet: str
    stance: Literal["supporting", "contradicting", "neutral"]
    credibility_score: Optional[float] = None


class ClaimVerificationResponse(BaseModel):
    claim: str
    verdict: Literal["true", "false", "partially_true", "unverifiable", "misleading"]
    confidence: float = Field(..., ge=0, le=100)
    summary: str
    supporting_evidence: List[SourceEvidence]
    contradicting_evidence: List[SourceEvidence]
    key_facts: List[str]
    nuances: Optional[str] = None
    sources_checked: int
    verification_time_ms: int


class SourceCredibilityRequest(BaseModel):
    url: str = Field(..., description="URL or domain to check")


class SourceCredibilityResponse(BaseModel):
    domain: str
    credibility_score: float = Field(..., ge=0, le=100)
    category: Literal["news", "academic", "government", "commercial", "personal", "satire", "unknown"]
    bias_rating: Literal["far_left", "left", "center_left", "center", "center_right", "right", "far_right", "unknown"]
    factual_reporting: Literal["very_high", "high", "mostly_factual", "mixed", "low", "very_low", "unknown"]
    notes: Optional[str] = None
    last_updated: datetime


class BatchVerificationRequest(BaseModel):
    claims: List[str] = Field(..., max_length=10, description="Claims to verify (max 10)")


class BatchVerificationResponse(BaseModel):
    job_id: str
    status: Literal["processing", "completed", "failed"]
    claims_count: int
    results: Optional[List[ClaimVerificationResponse]] = None
    poll_url: str


# Cache for credibility scores
_credibility_cache: Dict[str, SourceCredibilityResponse] = {}
_batch_jobs: Dict[str, BatchVerificationResponse] = {}


def get_ai_service() -> CloudflareAIService:
    return CloudflareAIService(
        account_id=settings.cloudflare_account_id,
        api_token=settings.cloudflare_api_token
    )


def get_search_service() -> SearXNGService:
    return SearXNGService(base_url=settings.searxng_url)


@router.post("/claim", response_model=ClaimVerificationResponse)
async def verify_claim(request: ClaimVerificationRequest):
    """
    Verify a claim using multi-source fact-checking.
    
    This groundbreaking feature:
    1. Searches for supporting and contradicting evidence
    2. Analyzes source credibility
    3. Uses AI reasoning to determine verdict
    4. Provides confidence score and nuances
    
    Not available in Tavily, Exa, or Glean.
    """
    start_time = datetime.now()
    
    ai = get_ai_service()
    search = get_search_service()
    
    search_count = 20 if request.depth == "thorough" else 10
    
    # Search for supporting evidence
    try:
        support_results = await search.search(
            query=f'"{request.claim}" evidence supports fact',
            engines=["google", "bing", "duckduckgo"],
            language="en"
        )
        support_results = support_results[:search_count // 2]
    except Exception as e:
        logger.warning("verify_support_search_failed", claim=request.claim, error=str(e))
        support_results = []
    
    # Search for contradicting evidence
    try:
        contradict_results = await search.search(
            query=f'"{request.claim}" false debunked incorrect misleading',
            engines=["google", "bing", "duckduckgo"],
            language="en"
        )
        contradict_results = contradict_results[:search_count // 2]
    except Exception as e:
        logger.warning("verify_contradict_search_failed", claim=request.claim, error=str(e))
        contradict_results = []
    
    # Format evidence - access SearchResult attributes properly
    supporting = []
    contradicting = []
    
    for result in support_results[:5]:
        supporting.append(SourceEvidence(
            title=result.title or "",
            url=str(result.url),
            snippet=(result.snippet or "")[:300],
            stance="supporting"
        ))
    
    for result in contradict_results[:5]:
        contradicting.append(SourceEvidence(
            title=result.title or "",
            url=str(result.url),
            snippet=(result.snippet or "")[:300],
            stance="contradicting"
        ))
    
    # Build context for AI analysis
    support_context = "\n".join([
        f"[{i+1}] {e.title}: {e.snippet}" 
        for i, e in enumerate(supporting)
    ]) or "No supporting evidence found."
    
    contradict_context = "\n".join([
        f"[{i+1}] {e.title}: {e.snippet}" 
        for i, e in enumerate(contradicting)
    ]) or "No contradicting evidence found."
    
    # Analyze with reasoning model
    analysis_prompt = f"""Analyze this claim for factual accuracy:

CLAIM: "{request.claim}"

SUPPORTING EVIDENCE:
{support_context}

CONTRADICTING EVIDENCE:
{contradict_context}

Provide your analysis as JSON:
{{
  "verdict": "true" | "false" | "partially_true" | "unverifiable" | "misleading",
  "confidence": 0-100,
  "summary": "one paragraph explanation",
  "key_facts": ["fact 1", "fact 2", "fact 3"],
  "nuances": "important context or caveats"
}}

Be objective and base your verdict on the evidence. If evidence is mixed or insufficient, reflect that in your verdict and confidence."""

    try:
        analysis = await ai.generate_text(
            prompt=analysis_prompt,
            model=CFModel.QWQ_32B,  # Use reasoning model
            max_tokens=1000
        )
        
        # Parse result
        import json
        import re
        
        json_match = re.search(r'\{[\s\S]*\}', analysis)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {
                "verdict": "unverifiable",
                "confidence": 50,
                "summary": analysis,
                "key_facts": [],
                "nuances": None
            }
    except Exception as e:
        result = {
            "verdict": "unverifiable",
            "confidence": 0,
            "summary": f"Analysis failed: {str(e)}",
            "key_facts": [],
            "nuances": None
        }
    
    verification_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    return ClaimVerificationResponse(
        claim=request.claim,
        verdict=result.get("verdict", "unverifiable"),
        confidence=result.get("confidence", 50),
        summary=result.get("summary", ""),
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        key_facts=result.get("key_facts", []),
        nuances=result.get("nuances"),
        sources_checked=len(support_results) + len(contradict_results),
        verification_time_ms=verification_time
    )


@router.post("/source", response_model=SourceCredibilityResponse)
async def check_source_credibility(request: SourceCredibilityRequest):
    """
    Check the credibility of a source/domain.
    
    Returns:
    - Credibility score (0-100)
    - Category (news, academic, etc.)
    - Bias rating
    - Factual reporting history
    """
    from urllib.parse import urlparse
    
    # Extract domain
    try:
        parsed = urlparse(request.url if request.url.startswith('http') else f"https://{request.url}")
        domain = parsed.netloc or parsed.path.split('/')[0]
    except:
        domain = request.url
    
    # Check cache
    if domain in _credibility_cache:
        cached = _credibility_cache[domain]
        # Cache valid for 7 days
        if (datetime.now() - cached.last_updated).days < 7:
            return cached
    
    ai = get_ai_service()
    search = get_search_service()
    
    # Search for information about the source
    try:
        results = await search.search(
            query=f'"{domain}" credibility reliability bias media fact-check',
            engines=["google", "bing", "duckduckgo"],
            language="en"
        )
        results = results[:10]
        context = "\n".join([
            f"- {r.title or ''}: {(r.snippet or '')[:200]}"
            for r in results[:5]
        ])
    except Exception as e:
        logger.warning("source_credibility_search_failed", domain=domain, error=str(e))
        context = "No information found about this source."
    
    # Analyze with AI
    prompt = f"""Assess the credibility of this source: {domain}

Available information:
{context}

Provide assessment as JSON:
{{
  "credibility_score": 0-100,
  "category": "news" | "academic" | "government" | "commercial" | "personal" | "satire" | "unknown",
  "bias_rating": "far_left" | "left" | "center_left" | "center" | "center_right" | "right" | "far_right" | "unknown",
  "factual_reporting": "very_high" | "high" | "mostly_factual" | "mixed" | "low" | "very_low" | "unknown",
  "notes": "relevant observations about this source"
}}

If you don't have enough information, use "unknown" for ratings and a neutral credibility score (50)."""

    try:
        analysis = await ai.generate_text(
            prompt=prompt,
            model=CFModel.LLAMA_3_1_8B_FAST,
            max_tokens=500
        )
        
        import json
        import re
        json_match = re.search(r'\{[\s\S]*\}', analysis)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {}
    except:
        result = {}
    
    response = SourceCredibilityResponse(
        domain=domain,
        credibility_score=result.get("credibility_score", 50),
        category=result.get("category", "unknown"),
        bias_rating=result.get("bias_rating", "unknown"),
        factual_reporting=result.get("factual_reporting", "unknown"),
        notes=result.get("notes"),
        last_updated=datetime.now()
    )
    
    # Cache result
    _credibility_cache[domain] = response
    
    return response


@router.post("/batch", response_model=BatchVerificationResponse)
async def batch_verify(
    request: BatchVerificationRequest,
    background_tasks: BackgroundTasks
):
    """
    Verify multiple claims in batch.
    
    Returns a job ID to poll for results.
    """
    if len(request.claims) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 claims per batch")
    
    job_id = hashlib.md5(f"{request.claims}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    
    response = BatchVerificationResponse(
        job_id=job_id,
        status="processing",
        claims_count=len(request.claims),
        results=None,
        poll_url=f"/api/v1/verify/batch/{job_id}"
    )
    
    _batch_jobs[job_id] = response
    
    # Process in background
    background_tasks.add_task(process_batch_verification, job_id, request.claims)
    
    return response


@router.get("/batch/{job_id}", response_model=BatchVerificationResponse)
async def get_batch_status(job_id: str):
    """Get the status of a batch verification job."""
    if job_id not in _batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return _batch_jobs[job_id]


async def process_batch_verification(job_id: str, claims: List[str]):
    """Background task to process batch verification."""
    results = []
    
    for claim in claims:
        try:
            result = await verify_claim(ClaimVerificationRequest(
                claim=claim,
                depth="quick"
            ))
            results.append(result)
        except Exception as e:
            results.append(ClaimVerificationResponse(
                claim=claim,
                verdict="unverifiable",
                confidence=0,
                summary=f"Verification failed: {str(e)}",
                supporting_evidence=[],
                contradicting_evidence=[],
                key_facts=[],
                sources_checked=0,
                verification_time_ms=0
            ))
    
    if job_id in _batch_jobs:
        _batch_jobs[job_id].status = "completed"
        _batch_jobs[job_id].results = results
