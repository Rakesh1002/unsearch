"""Envelope verification helpers for UnSearch citations."""
from __future__ import annotations

import hmac
import json
from typing import Any

from .types import CitationEnvelope


def verify_envelope(envelope: CitationEnvelope, signing_key: str) -> bool:
    """
    Verify the HMAC-SHA256 signature on a citation envelope.

    Args:
        envelope: The citation envelope to verify.
        signing_key: The HMAC signing key used when the envelope was signed.

    Returns:
        True if the signature is valid, False otherwise.
    """
    expected = envelope.get("signature")
    if not expected:
        return False

    payload: dict[str, Any] = {
        "v": envelope["v"],
        "url": envelope["url"],
        "fetched_at": envelope["fetched_at"],
        "content_sha256": envelope["content_sha256"],
        "content_type": envelope["content_type"],
        "content_bytes": envelope["content_bytes"],
        "snapshot_key": envelope["snapshot_key"],
        "engine": envelope["engine"],
        "agent_run_id": envelope.get("agent_run_id"),
        "api_key_id": envelope.get("api_key_id"),
        "signed_at": envelope["signed_at"],
        "signing_key_id": envelope.get("signing_key_id"),
        "signing_alg": envelope["signing_alg"],
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)

    computed = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        "sha256",
    ).hexdigest()

    return hmac.compare_digest(computed.encode("utf-8"), expected.encode("utf-8"))
