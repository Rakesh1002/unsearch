"""
HMAC-SHA256 signing and verification for citation envelopes.

This implements the v1 signing scheme documented in docs/citation-envelope.md:
1. Build a canonical JSON serialization of all envelope fields except `signature`.
2. Compute HMAC-SHA256(signing_key, canonical_serialization).
3. Emit the hex-encoded MAC.

Key management is intentionally simple for v1: a single signing secret per
environment. Future versions will support per-customer keys and PKI signing.
"""
import hmac
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.config import get_settings
import structlog

logger = structlog.get_logger(__name__)


def _canonicalize(envelope_dict: Dict[str, Any]) -> str:
    """
    Create a canonical JSON serialization for signing.

    - Excludes the `signature` field.
    - Sorts keys lexicographically.
    - Uses compact separators.
    - Converts datetime objects to ISO 8601 UTC strings.
    """
    payload = {
        k: v.isoformat() if isinstance(v, datetime) else v
        for k, v in envelope_dict.items()
        if k != "signature"
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str)


class CitationSigner:
    """Signs and verifies citation envelopes using HMAC-SHA256."""

    def __init__(self, signing_key: Optional[str] = None, signing_key_id: Optional[str] = None):
        settings = get_settings()
        # Prefer explicit key, then environment secret, then fallback development key.
        # The fallback is only safe for local development and tests.
        self._key = (signing_key or os.environ.get("CITATION_SIGNING_KEY") or "dev-only-unsearch-citation-signing-key").encode("utf-8")
        self._key_id = signing_key_id or os.environ.get("CITATION_SIGNING_KEY_ID") or "sk_dev_unsearch_v1"

    def sign(self, envelope_dict: Dict[str, Any]) -> str:
        """Return hex-encoded HMAC-SHA256 signature for an envelope dict."""
        canonical = _canonicalize(envelope_dict)
        mac = hmac.new(self._key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        logger.debug("citation_signed", key_id=self._key_id, sha256_prefix=envelope_dict.get("content_sha256", "")[:16])
        return mac

    def verify(self, envelope_dict: Dict[str, Any]) -> bool:
        """Constant-time verify an envelope signature."""
        expected = envelope_dict.get("signature")
        if not expected:
            return False
        computed = self.sign(envelope_dict)
        return hmac.compare_digest(computed.encode("utf-8"), expected.encode("utf-8"))

    @property
    def signing_key_id(self) -> str:
        return self._key_id


_signer: Optional[CitationSigner] = None


def get_citation_signer() -> CitationSigner:
    """Get or create the singleton citation signer."""
    global _signer
    if _signer is None:
        _signer = CitationSigner()
    return _signer
