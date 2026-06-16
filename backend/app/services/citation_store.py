"""
Content normalization and snapshot storage for verifiable citations.

This module:
1. Normalizes retrieved bytes (HTML, JSON, PDF, text/markdown) so that
   re-fetching the same URL produces a stable SHA-256.
2. Stores content-addressable snapshot bundles locally or in Cloudflare R2.
3. Creates signed CitationEnvelope objects for inline return.

Storage backend is selected via CITATION_SNAPSHOT_STORE_TYPE env var:
- "local" (default for development / self-host): filesystem under CITATION_SNAPSHOT_DIR
- "r2": Cloudflare R2 bucket via boto3 S3-compatible API
"""
import asyncio
import concurrent.futures
import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from urllib.parse import urlparse

from pydantic import HttpUrl
from bs4 import BeautifulSoup
import structlog

from app.config import get_settings
from app.models.citation import CitationEnvelope, SnapshotBundle
from app.models.responses import ScrapedContent
from app.services.citation_signer import get_citation_signer

logger = structlog.get_logger(__name__)

# Dedicated thread pool executor for CPU-bound citation content normalization.
_citation_cpu_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=16,
    thread_name_prefix="citation_cpu"
)


def _detect_content_type(content_bytes: bytes, headers: Optional[Dict[str, str]]) -> str:
    """Best-effort content-type detection."""
    if headers:
        ct = headers.get("content-type") or headers.get("Content-Type")
        if ct:
            return ct.split(";")[0].strip().lower()
    # Sniff PDF
    if content_bytes.startswith(b"%PDF"):
        return "application/pdf"
    # Sniff JSON
    try:
        content_bytes.decode("utf-8")
        text = content_bytes.lstrip()[:1]
        if text in (b"{", b"["):
            return "application/json"
    except Exception:
        pass
    return "text/html"


def _normalize_html(html_bytes: bytes) -> bytes:
    """Normalize HTML for stable hashing."""
    try:
        text = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = html_bytes.decode("utf-8", errors="replace")

    soup = BeautifulSoup(text, "lxml")

    # Remove scripts, styles, comments, and csrf tokens.
    for tag in soup(["script", "style"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, str) and t.strip().startswith("<!--")):
        comment.extract()
    for meta in soup.find_all("meta", {"name": "csrf-token"}):
        meta.decompose()

    # Canonicalize attribute order alphabetically on every element.
    for tag in soup.find_all(True):
        if tag.attrs:
            tag.attrs = dict(sorted(tag.attrs.items()))

    # Collapse whitespace.
    normalized = soup.get_text(" ")
    normalized = " ".join(normalized.split())
    return normalized.encode("utf-8")


def _normalize_json(json_bytes: bytes) -> bytes:
    """Normalize JSON for stable hashing."""
    try:
        obj = json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return json_bytes
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode("utf-8")


def _normalize_text(text_bytes: bytes) -> bytes:
    """Normalize text/markdown for stable hashing."""
    try:
        text = text_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = text_bytes.decode("utf-8", errors="replace")
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = "\n".join(lines).strip()
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned.encode("utf-8")


def _normalize_pdf(pdf_bytes: bytes) -> bytes:
    """PDFs are treated as byte-stable."""
    return pdf_bytes


def normalize_content(content_bytes: bytes, content_type: str) -> bytes:
    """Normalize content based on its MIME type."""
    ct = content_type.split(";")[0].strip().lower()
    if ct in ("text/html", "application/xhtml+xml"):
        return _normalize_html(content_bytes)
    if ct == "application/json":
        return _normalize_json(content_bytes)
    if ct in ("text/plain", "text/markdown", "text/x-markdown"):
        return _normalize_text(content_bytes)
    if ct == "application/pdf":
        return _normalize_pdf(content_bytes)
    # Default: treat as text.
    return _normalize_text(content_bytes)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot_key_prefix(content_sha256: str) -> str:
    return f"citations/{content_sha256[:2]}/{content_sha256[2:4]}/{content_sha256}"


def _build_bundle(
    url: str,
    raw_bytes: bytes,
    content_type: str,
    headers: Dict[str, str],
    engine: str,
    fetched_at: datetime,
    request_id: Optional[str] = None,
    redirects: Optional[list] = None,
) -> SnapshotBundle:
    normalized = normalize_content(raw_bytes, content_type)
    sha256 = compute_sha256(normalized)
    return SnapshotBundle(
        url=url,
        fetched_at=fetched_at,
        content_sha256=sha256,
        content_type=_detect_content_type(raw_bytes, headers) if not content_type else content_type,
        content_bytes=len(normalized),
        normalized_bytes=normalized,
        headers=dict(headers) if headers else {},
        redirects=redirects or [],
        engine=engine,
        request_id=request_id,
    )


class LocalSnapshotBackend:
    """Filesystem-backed snapshot store (default for development/self-host)."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        # key is expected to look like citations/.../snapshot.json
        return os.path.join(self.base_dir, key)

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: open(path, "wb").write(data))
        return key

    async def get(self, key: str) -> Optional[bytes]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: open(path, "rb").read())

    async def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    async def delete(self, key: str) -> bool:
        path = self._path(key)
        if os.path.exists(path):
            await asyncio.get_event_loop().run_in_executor(None, os.remove, path)
            return True
        return False


class R2SnapshotBackend:
    """Cloudflare R2 snapshot store via boto3 S3-compatible API."""

    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region: str = "auto",
    ):
        import boto3
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        self._bucket = bucket_name

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            ),
        )
        return key

    async def get(self, key: str) -> Optional[bytes]:
        loop = asyncio.get_event_loop()
        try:
            obj = await loop.run_in_executor(None, lambda: self._client.get_object(Bucket=self._bucket, Key=key))
            return await loop.run_in_executor(None, obj["Body"].read)
        except Exception as e:
            logger.warning("r2_get_failed", key=key, error=str(e))
            return None

    async def exists(self, key: str) -> bool:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: self._client.head_object(Bucket=self._bucket, Key=key))
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, lambda: self._client.delete_object(Bucket=self._bucket, Key=key))
            return True
        except Exception:
            return False


class CitationStore:
    """High-level citation store: normalize, persist, and sign snapshots."""

    def __init__(self):
        settings = get_settings()
        self.store_type = os.environ.get("CITATION_SNAPSHOT_STORE_TYPE", "local").lower()

        if self.store_type == "r2":
            self._backend = R2SnapshotBackend(
                endpoint_url=os.environ["CITATION_R2_ENDPOINT_URL"],
                access_key_id=os.environ["CITATION_R2_ACCESS_KEY_ID"],
                secret_access_key=os.environ["CITATION_R2_SECRET_ACCESS_KEY"],
                bucket_name=os.environ["CITATION_R2_BUCKET"],
            )
        else:
            base_dir = os.environ.get("CITATION_SNAPSHOT_DIR", "/tmp/unsearch-snapshots")
            self._backend = LocalSnapshotBackend(base_dir)

        self._signer = get_citation_signer()

    @property
    def backend(self):
        return self._backend

    async def store_snapshot(
        self,
        url: str,
        raw_bytes: bytes,
        content_type: str,
        headers: Optional[Dict[str, str]] = None,
        engine: str = "direct-fetch",
        fetched_at: Optional[datetime] = None,
        request_id: Optional[str] = None,
        redirects: Optional[list] = None,
    ) -> SnapshotBundle:
        """Normalize content, persist bundle, return bundle metadata."""
        fetched_at = fetched_at or datetime.utcnow()
        loop = asyncio.get_running_loop()
        bundle = await loop.run_in_executor(
            _citation_cpu_executor,
            _build_bundle,
            url,
            raw_bytes,
            content_type,
            headers or {},
            engine,
            fetched_at,
            request_id,
            redirects,
        )
        return await self._persist_bundle(bundle)

    async def _persist_bundle(self, bundle: SnapshotBundle) -> SnapshotBundle:
        key = self._bundle_key(bundle.content_sha256)
        if not await self._backend.exists(key):
            payload = self._serialize_bundle(bundle)
            await self._backend.put(key, payload, content_type="application/json")
            logger.info("snapshot_stored", key=key, sha256=bundle.content_sha256, backend=self.store_type)
        else:
            logger.debug("snapshot_deduplicated", key=key, sha256=bundle.content_sha256)
        return bundle

    def _bundle_key(self, content_sha256: str) -> str:
        return f"{_snapshot_key_prefix(content_sha256)}/snapshot.json"

    def _serialize_bundle(self, bundle: SnapshotBundle) -> bytes:
        payload = {
            "url": bundle.url,
            "fetched_at": bundle.fetched_at.isoformat(),
            "content_sha256": bundle.content_sha256,
            "content_type": bundle.content_type,
            "content_bytes": bundle.content_bytes,
            "normalized_bytes": bundle.normalized_bytes.decode("utf-8", errors="replace"),
            "headers": bundle.headers,
            "redirects": bundle.redirects,
            "engine": bundle.engine,
            "request_id": bundle.request_id,
            "metadata": bundle.metadata,
        }
        return json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")

    def _deserialize_bundle(self, data: bytes) -> SnapshotBundle:
        payload = json.loads(data.decode("utf-8"))
        return SnapshotBundle(
            url=payload["url"],
            fetched_at=datetime.fromisoformat(payload["fetched_at"]),
            content_sha256=payload["content_sha256"],
            content_type=payload["content_type"],
            content_bytes=payload["content_bytes"],
            normalized_bytes=payload["normalized_bytes"].encode("utf-8"),
            headers=payload.get("headers", {}),
            redirects=payload.get("redirects", []),
            engine=payload.get("engine", "direct-fetch"),
            request_id=payload.get("request_id"),
            metadata=payload.get("metadata", {}),
        )

    async def get_bundle(self, content_sha256: str) -> Optional[SnapshotBundle]:
        key = self._bundle_key(content_sha256)
        data = await self._backend.get(key)
        if data is None:
            return None
        return self._deserialize_bundle(data)

    async def get_bundle_by_key(self, snapshot_key: str) -> Optional[SnapshotBundle]:
        data = await self._backend.get(snapshot_key)
        if data is None:
            return None
        return self._deserialize_bundle(data)

    async def create_envelope(
        self,
        bundle: SnapshotBundle,
        api_key_id: Optional[str] = None,
        agent_run_id: Optional[str] = None,
    ) -> CitationEnvelope:
        """Create a signed citation envelope for a stored snapshot bundle."""
        snapshot_key = self._bundle_key(bundle.content_sha256)
        envelope_data = {
            "v": 1,
            "url": bundle.url,
            "fetched_at": bundle.fetched_at,
            "content_sha256": bundle.content_sha256,
            "content_type": bundle.content_type,
            "content_bytes": bundle.content_bytes,
            "snapshot_key": snapshot_key,
            "engine": bundle.engine,
            "agent_run_id": agent_run_id,
            "api_key_id": api_key_id,
            "signed_at": datetime.utcnow(),
            "signing_key_id": self._signer.signing_key_id,
            "signing_alg": "HMAC-SHA256",
        }
        envelope_data["signature"] = self._signer.sign(envelope_data)
        return CitationEnvelope(**envelope_data)

    async def log_audit_event(
        self,
        api_key_id: str,
        request_id: str,
        endpoint: str,
        envelope_refs: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Persist a per-API-key audit event.

        Audit events are stored alongside snapshots so self-host deployments can
        retain them for as long as required (e.g. EU AI Act Article 12).
        """
        event_id = f"evt_{uuid.uuid4().hex}"
        event_at = datetime.utcnow()
        payload = {
            "event_id": event_id,
            "api_key_id": api_key_id,
            "request_id": request_id,
            "endpoint": endpoint,
            "envelope_refs": envelope_refs,
            "metadata": metadata or {},
            "created_at": event_at.isoformat(),
        }
        key = f"audit/{api_key_id}/{event_at.strftime('%Y/%m/%d')}/{event_id}.json"
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        await self._backend.put(key, data, content_type="application/json")
        logger.info("audit_event_logged", event_id=event_id, api_key_id=api_key_id, endpoint=endpoint)
        return event_id

    async def get_audit_events(
        self,
        api_key_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List audit events for a given API key, newest first."""
        if isinstance(self._backend, LocalSnapshotBackend):
            return await self._list_local_audit_events(api_key_id, start_date, end_date, limit, offset)
        # R2 listing would be implemented here with boto3 list_objects_v2.
        # For now, return an empty list on R2 until list support is added.
        logger.warning("r2_audit_list_not_implemented")
        return []

    async def _list_local_audit_events(
        self,
        api_key_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        base = os.path.join(self._backend.base_dir, "audit", api_key_id)
        events: List[Dict[str, Any]] = []
        if not os.path.exists(base):
            return events

        for root, _dirs, files in os.walk(base):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(root, fname)
                stat = os.stat(path)
                mtime = datetime.utcfromtimestamp(stat.st_mtime)
                if start_date and mtime < start_date:
                    continue
                if end_date and mtime > end_date:
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        events.append(json.load(f))
                except Exception:
                    continue

        events.sort(key=lambda e: e.get("created_at", ""), reverse=True)
        return events[offset:offset + limit]


async def envelope_for_result(
    store: CitationStore,
    url: str,
    snippet: str,
    engine: str,
    scraped_content: Optional[ScrapedContent] = None,
    api_key_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Optional[CitationEnvelope]:
    """
    Convenience helper: create a signed citation envelope for a search result.

    If scraped content is present, snapshot the raw HTML or text.
    Otherwise snapshot the search snippet as plain text so every result still
    has a replayable provenance record.
    """
    try:
        if scraped_content and scraped_content.html:
            raw_bytes = scraped_content.html.encode("utf-8")
            content_type = "text/html"
        elif scraped_content and scraped_content.text:
            raw_bytes = scraped_content.text.encode("utf-8")
            content_type = "text/plain"
        else:
            raw_bytes = snippet.encode("utf-8")
            content_type = "text/plain"

        bundle = await store.store_snapshot(
            url=url,
            raw_bytes=raw_bytes,
            content_type=content_type,
            headers={},
            engine=engine,
            request_id=request_id,
        )
        return await store.create_envelope(
            bundle=bundle,
            api_key_id=api_key_id,
        )
    except Exception as e:
        logger.warning("envelope_creation_failed", url=url, error=str(e))
        return None


_citation_store: Optional[CitationStore] = None


async def get_citation_store() -> CitationStore:
    """Get or create the singleton citation store."""
    global _citation_store
    if _citation_store is None:
        _citation_store = CitationStore()
    return _citation_store
