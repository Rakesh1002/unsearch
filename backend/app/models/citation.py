"""
Citation envelope models for verifiable web retrieval.

Every search result, extract result, and scraped page can carry a signed
citation envelope plus a content-addressable snapshot. The envelope proves
that UnSearch retrieved specific bytes at a specific time; the snapshot lets
any verifier replay the retrieval later.
"""
from datetime import datetime
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class CitationEnvelope(BaseModel):
    """
    Signed citation envelope returned inline with retrieval results.

    Schema version 1 uses HMAC-SHA256. See docs/citation-envelope.md for the
    full WACZ-aligned rationale.
    """
    v: int = Field(default=1, description="Envelope schema version")
    url: str = Field(description="Final URL retrieved")
    fetched_at: datetime = Field(description="Server-side fetch timestamp (UTC)")
    content_sha256: str = Field(description="SHA-256 of normalized content bytes")
    content_type: str = Field(default="text/html", description="HTTP Content-Type")
    content_bytes: int = Field(description="Size in bytes of normalized content")
    snapshot_key: str = Field(description="Object key for the stored snapshot bundle")
    engine: str = Field(description="Provenance of the retrieval, e.g. searxng:google")
    agent_run_id: Optional[str] = Field(default=None, description="Parent agent run ID, if any")
    api_key_id: Optional[str] = Field(default=None, description="API key under which the retrieval ran")
    signed_at: datetime = Field(default_factory=datetime.utcnow, description="Envelope signing timestamp (UTC)")
    signing_key_id: Optional[str] = Field(default=None, description="Signing key version")
    signing_alg: Literal["HMAC-SHA256"] = Field(default="HMAC-SHA256")
    signature: str = Field(description="Hex-encoded HMAC-SHA256 over canonical fields")

    class Config:
        json_schema_extra = {
            "example": {
                "v": 1,
                "url": "https://example.com/article",
                "fetched_at": "2026-05-28T18:32:11Z",
                "content_sha256": "a3f5...",
                "content_type": "text/html",
                "content_bytes": 184213,
                "snapshot_key": "citations/a3f5.../snapshot.json",
                "engine": "searxng:google",
                "api_key_id": "key_01HK...",
                "signed_at": "2026-05-28T18:32:11Z",
                "signing_key_id": "sk_01HJ...",
                "signing_alg": "HMAC-SHA256",
                "signature": "9d2e...",
            }
        }


class SnapshotBundle(BaseModel):
    """
    Content-addressable snapshot bundle persisted to object storage.

    The bundle includes normalized bytes plus a small header sidecar. In a
    future WACZ export endpoint this will be wrapped into a valid .wacz file.
    """
    url: str
    fetched_at: datetime
    content_sha256: str
    content_type: str
    content_bytes: int
    normalized_bytes: bytes
    headers: Dict[str, str] = Field(default_factory=dict)
    redirects: list[str] = Field(default_factory=list)
    engine: str
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SnapshotDiff(BaseModel):
    """Result of comparing a stored snapshot to a live re-fetch."""
    url: str
    snapshot_sha256: str
    live_sha256: Optional[str] = None
    status: Literal["unchanged", "changed", "missing_live", "missing_snapshot"]
    byte_diff: Optional[int] = None
    last_fetched_at: datetime
    live_fetched_at: Optional[datetime] = None
    changed_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    summary: str


class CitationVerificationRequest(BaseModel):
    """Request body for POST /verify/citation."""
    url: str
    snapshot_key: Optional[str] = None
    content_sha256: Optional[str] = None
    include_live_content: bool = False


class CitationVerificationResponse(BaseModel):
    """Response for POST /verify/citation."""
    url: str
    snapshot: Optional[SnapshotBundle] = None
    diff: SnapshotDiff
    envelope_valid: bool
    snapshot_matches_envelope: bool
