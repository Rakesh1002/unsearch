# Citation envelope

> The signed envelope returned with every UnSearch retrieval. WACZ-aligned, content-addressable, replayable.

The citation envelope is the wire-level primitive that makes UnSearch verifiable retrieval rather than just search. Every result from `/api/v1/search`, `/api/v1/agent/search`, `/api/v1/agent/extract`, and the MCP `search` / `extract` tools carries an inline envelope. The `verify_claim` endpoint takes an envelope (or just its `url`) plus a claim and returns span-level evidence.

See [ADR-0011](./adr/0011-wacz-aligned-signed-envelope.md) for the rationale behind the format and the WACZ-Auth alignment.

---

## Schema (v1)

```json
{
  "v": 1,
  "url": "https://example.com/article",
  "fetched_at": "2026-05-28T18:32:11Z",
  "content_sha256": "a3f5be8c8e6a4d4b9c5e3f1a0d8b6c4e2f0a9d8b7c6e5f4a3b2c1d0e9f8a7b6c5",
  "content_type": "text/html",
  "content_bytes": 184213,
  "snapshot_r2_key": "citations/a3f5be8c.../snapshot.wacz",
  "engine": "searxng:google",
  "agent_run_id": "run_01HQX2Y5Z7K8M9N0P1Q2R3S4T5",
  "api_key_id": "key_01HK6V7B8C9D0E1F2G3H4J5K6L",
  "signed_at": "2026-05-28T18:32:11Z",
  "signing_key_id": "sk_01HJ7N8M9P0Q1R2S3T4U5V6W7X",
  "signing_alg": "HMAC-SHA256",
  "signature": "9d2e4f1a8b7c6e5d4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e"
}
```

### Field reference

| Field | Type | Required | Meaning |
|---|---|---|---|
| `v` | int | yes | Envelope schema version. `1` for now; `2` introduces PKI signing per ADR-0011 (Month 7+). |
| `url` | string (URL) | yes | The URL retrieved. After redirects this is the final URL. |
| `fetched_at` | string (RFC 3339) | yes | The server-side timestamp at which the bytes were retrieved. |
| `content_sha256` | string (hex) | yes | SHA-256 of the normalized content bytes (see normalization rules below). |
| `content_type` | string | yes | The HTTP `Content-Type` of the retrieved resource. |
| `content_bytes` | int | yes | Size in bytes of the normalized content. |
| `snapshot_r2_key` | string | yes | R2 object key for the WACZ-style snapshot package. On self-host this is in the customer's R2 bucket (or BYO storage). |
| `engine` | string | yes | Provenance of the retrieval — e.g. `searxng:google`, `searxng:bing`, `direct-fetch`, `puppeteer`. |
| `agent_run_id` | string (ULID) | optional | If the retrieval was triggered by an `/api/v1/agent/research` Durable Object run, the agent run ID. |
| `api_key_id` | string (ULID) | yes | The API key under which the retrieval ran. The audit log indexes by this field. |
| `signed_at` | string (RFC 3339) | yes | When the envelope was signed. Equals `fetched_at` for synchronous retrievals; later for async snapshots. |
| `signing_key_id` | string (ULID) | yes | The customer's signing key version. Key rotation supported; historical envelopes remain verifiable against the prior key (see [Key rotation](#key-rotation)). |
| `signing_alg` | string | yes | `HMAC-SHA256` for v1; `Ed25519` or `ECDSA-P256` for v2 PKI signing. |
| `signature` | string (hex / base64) | yes | The signature over the canonical serialization of all fields above. |

### Content normalization rules

Before hashing, content is normalized so re-fetching the same URL on the same day produces the same hash:

- **HTML:** parsed with `lxml`, all whitespace runs collapsed to single spaces, `<script>` / `<style>` / `<meta name="csrf-token">` / `<!--...-->` removed, attribute order canonicalized alphabetically, then re-serialized.
- **JSON:** parsed and re-serialized with sorted keys, ASCII-only escapes.
- **PDF:** binary bytes hashed as-is (PDFs are byte-stable per source).
- **Plaintext / Markdown:** trailing whitespace stripped from each line; final newline ensured.

The exact normalization implementation lives in `app/services/citation_store.py` (shipping Week 2). The normalized bytes are what the `snapshot_r2_key` object contains.

---

## Signing process (v1 — HMAC-SHA256)

1. Construct the canonical serialization: a JSON object with all envelope fields **except `signature`**, sorted lexicographically by key, with no whitespace (`json.dumps(..., separators=(",", ":"), sort_keys=True)`).
2. Compute `HMAC-SHA256(signing_key, canonical_serialization)`.
3. Emit the hex-encoded MAC as the `signature` field.

The `signing_key` is a 32-byte secret per `signing_key_id`, stored as a Cloudflare Worker secret. Each customer has at least one active signing key; key rotation generates a new `signing_key_id` and marks the prior as `rotated` (still valid for verification, no longer used to sign new envelopes).

---

## Verification process

Any party with the customer's signing key can verify an envelope:

1. Parse the envelope.
2. Reconstruct the canonical serialization (same algorithm as signing).
3. Compute `HMAC-SHA256(signing_key_for(signing_key_id), canonical_serialization)`.
4. Constant-time-compare to the `signature` field.
5. (Optional but recommended.) Fetch the snapshot from `snapshot_r2_key`, recompute SHA-256 over the normalized bytes, compare to `content_sha256`.

A verifier helper ships with each SDK:

```python
from unsearch.verify import verify_envelope
verify_envelope(envelope, signing_key=...)  # raises if invalid
```

```ts
import { verifyEnvelope } from "@unsearch/sdk/verify"
verifyEnvelope(envelope, { signingKey: ... })
```

For self-host customers in v2 (PKI signing, Month 7+), verification uses the customer's public key — no shared secret required, anyone with the public key can verify.

---

## Snapshot storage

`snapshot_r2_key` points to a WACZ-style bundle in R2 (or BYO storage on self-host) containing:

- The normalized content bytes (HTML/JSON/PDF/markdown as appropriate).
- An HTTP response header sidecar (status, headers, redirects encountered).
- A small metadata JSON with `{ engine, fetched_at, request_id }`.

Snapshots are content-addressable: the object key is derived from `content_sha256`. Two identical retrievals deduplicate.

On WACZ export (Month 3 deliverable), the snapshot bundle is packaged as a valid `.wacz` file readable by ReplayWeb.page / Webrecorder browser extension / Harvard LIL's `wacz-verify`.

---

## Key rotation

Customers can rotate their signing key at any time via `POST /api/v1/auth/signing-keys/rotate`. Behavior:

1. A new `signing_key_id` is generated; the new key becomes the default for subsequent envelopes.
2. The prior key is marked `rotated` — still loaded by verifiers for historical envelopes, never used for new signing.
3. Audit-log envelopes signed under the prior key remain verifiable indefinitely (the prior key is retained per the customer's audit-log retention setting — up to 10 years on Enterprise / Self-host).

`signing_key_id` is included in every envelope so verifiers can look up the right key for the right historical retrieval.

---

## v1 → v2 migration (planned Month 7+)

v2 envelopes introduce PKI signing per [ADR-0011](./adr/0011-wacz-aligned-signed-envelope.md). Migration plan:

- Envelope schema remains stable (`v: 2` instead of `v: 1`, `signing_alg: "Ed25519"`).
- v1 envelopes remain verifiable indefinitely against the prior HMAC keys.
- v2 envelopes are co-signed with HMAC and PKI for a 90-day overlap window so downstream consumers can transition.
- Self-host customers retain control of their own private keys; hosted customers use UnSearch-issued keys with optional BYOK.

---

## Threat model — what the envelope proves and does not prove

The envelope proves:

- The bytes at `snapshot_r2_key` match `content_sha256` at the time of signing.
- UnSearch (or the customer in self-host) signed this envelope with `signing_key_id`.
- The retrieval happened at `fetched_at` from `engine`.

The envelope does **not** prove:

- That the URL still resolves to the same content live (use `/verify/citation` to compare snapshot vs live).
- That the source itself is true. Truth of the source is independent of provenance. We verify provenance and span-level claim-vs-source consistency; we do not vouch for the source itself.
- That a third party who lacks the signing key can verify the envelope without trusting UnSearch (this is a v1 limitation; v2 PKI signing fixes it).

---

## Implementation status

| Component | Status | Where |
|---|---|---|
| Envelope returned inline on `/api/v1/search` | ✏️ Shipping Week 2 | `app/api/v1/search.py:30` + `app/services/citation_store.py` (new) |
| Envelope returned inline on `/api/v1/agent/search` | ✏️ Shipping Week 2 | `app/api/v1/agent.py:45` |
| Envelope returned inline on MCP `search` tool | ✏️ Shipping Week 3 | `workers/src/mcp/server.ts` (new) |
| R2 snapshot store, content-addressable | ✏️ Shipping Week 2 | `app/services/citation_store.py` (new) |
| HMAC v1 signing | ✏️ Shipping Week 2 | `app/services/citation_signer.py` (new) |
| `POST /api/v1/verify/citation` (snapshot + live diff) | ✏️ Shipping Week 2 | `app/api/v1/verify.py` |
| `POST /api/v1/verify/claim` (span-level grading) | ✏️ Shipping Week 2 | `app/api/v1/verify.py` |
| `GET /api/v1/audit` per-API-key | ✏️ Shipping Week 2 | `app/api/v1/audit.py` (new) |
| Python + TypeScript SDK envelope verifiers | 📋 Week 4 | `apps/sdk-py`, `apps/sdk-ts` |
| WACZ export endpoint | 📋 Month 3 | `app/api/v1/audit.py` |
| BYO storage (S3 / GCS / Azure Blob) | 📋 Month 3 | `app/services/citation_store.py` |
| PKI v2 signing | 📋 Month 7+ | TBD |
| Differential snapshot diffs | 📋 Month 7+ | TBD |

---

## Cross-references

- [ADR-0009: Verifiable Retrieval as the product surface](./adr/0009-verifiable-retrieval-as-product-surface.md)
- [ADR-0011: WACZ-aligned signed envelope format](./adr/0011-wacz-aligned-signed-envelope.md)
- [WACZ-Auth spec](https://github.com/webrecorder/wacz-auth-spec)
- [Harvard LIL `wacz-signing`](https://github.com/harvard-lil/wacz-signing)
- [`docs/strategy/positioning.md`](./strategy/positioning.md) — how the envelope shows up in marketing
