# ADR-0011: WACZ-aligned signed envelope format

- Status: Accepted
- Date: 2026-05-28
- Deciders: @Rakesh1002

## Context

ADR-0009 commits UnSearch to verifiable retrieval as the product surface. The primitive at the heart of that surface is a **signed citation envelope** returned with every result — a structured record of what the agent saw, at what URL, at what time, with what bytes, that can be re-verified by any downstream consumer.

This raises a wire-format question: do we invent a new envelope format, adopt an existing standard, or align with one?

Two open standards exist for content provenance and web-archival signing:

1. **C2PA (Coalition for Content Provenance and Authenticity)** — broad media-provenance standard with cryptographically signed metadata embedded in digital files. v2.2 published May 2025; v2.3 in draft. Backed by Adobe, BBC, Microsoft, Sony, the New York Times. Optimized for embedded-in-file provenance (images, audio, video, PDFs).
2. **WACZ-Auth (Web Archive Collection Zipped, Authentication Spec)** — Webrecorder's signing and verification mechanics for WACZ web-archive packages. Standardized by the Webrecorder community; integrated into ReplayWeb.page; Harvard LIL maintains a `wacz-signing` library. Optimized for web-archive provenance (HTML pages, signed snapshots, replayability).

C2PA's strength is content-embedded signing for distributable media files. Our problem is not media file authenticity — it is "the bytes at this URL at this moment." Embedding C2PA manifests inside HTML snapshots is awkward and not how the C2PA ecosystem is wired.

WACZ-Auth's strength is signing + timestamping + replaying web archives in exactly the shape an agent retrieval produces. The downstream ecosystem (ReplayWeb.page, Webrecorder browser extensions, Harvard LIL's wacz-signing) already reads and verifies these envelopes. Aligning with WACZ-Auth means our snapshots are immediately interoperable with the archivist and journalism communities that ICP-3 (Anika) lives in, and that ICP-1 (Priya — legal-AI startup) can point a court forensics consultant at.

Neither C2PA nor WACZ-Auth gives us *exactly* what we need at the per-result wire level — both are package-level formats. Our retrieval envelope is per-result and must travel in JSON inline with API responses, not as a separate file download. The decision is therefore: which format do we *align with* for the envelope shape, and which underlying signing primitive do we use?

## Decision

UnSearch's per-result envelope is a JSON object that **mirrors the WACZ-Auth signed envelope shape** (compatible field names, compatible signing algorithm, compatible verifier semantics) but lives inline with API responses. WACZ packages are an export option, not the default transport.

The envelope schema lives at [`docs/citation-envelope.md`](../citation-envelope.md). Shape:

```json
{
  "v": 1,
  "url": "https://example.com/article",
  "fetched_at": "2026-05-28T18:32:11Z",
  "content_sha256": "a3f5...",
  "content_type": "text/html",
  "snapshot_r2_key": "citations/a3f5.../snapshot.wacz",
  "engine": "searxng:google",
  "agent_run_id": "run_01HQ...",
  "api_key_id": "key_01HK...",
  "signature_hmac_sha256": "9d2e..."
}
```

Signing primitive — phased:

- **v1 (Week 2):** HMAC-SHA256 with per-customer signing key issued at API-key creation. Stored as `wrangler secret`. Cheap, fast, sufficient for "did UnSearch produce this envelope and has it been tampered with."
- **v2 (Month 7+):** WACZ-Auth-compatible PKI signing — per-customer keypair, signed certificate chain, public verification by anyone via the `wacz-verify` tooling. Self-host customers control their own private keys; hosted customers inherit a per-account UnSearch-signed key by default with option to BYOK.

Snapshot storage — the `snapshot_r2_key` points at a content-addressable object in R2 (or BYO storage on self-host). Content is the normalized HTML / PDF / extracted markdown plus an HTTP response header sidecar. On WACZ export (Month 3), the snapshot bundle is packaged as a valid `.wacz` file readable by ReplayWeb.page.

## Consequences

We commit to:

- Envelope schema stability — breaking changes require a new ADR, a v2 envelope co-existing with v1 for ≥12 months, and a documented migration tool. Audit consumers (regulators, court forensics, internal compliance) depend on this stability over years, not quarters.
- An HMAC v1 → PKI v2 migration path with no envelope-shape break.
- WACZ export endpoint as a Month-3 deliverable so signed envelopes can be archived in the broader web-archival ecosystem.
- Documentation that explicitly maps our envelope fields to the WACZ-Auth spec, so a Webrecorder community member or court forensics consultant can read both side-by-side.
- Per-API-key signing keys (not per-call), with key rotation supported (rotation must allow re-verifying historical envelopes against the prior key).

What we knowingly give up:

- C2PA compatibility. Re-evaluating if a customer in media authentication requires it. Not in scope for ICP-1 / ICP-2 / ICP-3.
- An ECDSA / Ed25519 signing primitive from day one. HMAC v1 is simpler to operate, easier for customers to verify in a Worker without key management, and ships in Week 2. PKI v2 unlocks third-party verification but is a Month-7+ effort.
- A custom-named, marketing-friendly envelope format. The wire format is intentionally boring and aligned with an existing standard so the broader provenance community recognizes it.

## Alternatives considered

**1. Roll our own signed envelope format optimized for agent retrieval, no standards alignment.** Rejected: doesn't inherit the credibility of the WACZ / Webrecorder ecosystem and forces downstream consumers (auditors, archivists, journalists) to learn a new format. Active risk of "yet another standard."

**2. Adopt C2PA as the primary envelope.** Rejected: C2PA is optimized for file-embedded provenance in distributable media; our object is "an HTTP retrieval at time T" which sits awkwardly in C2PA's manifest model. The C2PA ecosystem isn't where ICP-1 / ICP-3 buyers verify retrievals.

**3. Use JWT with a custom claim set for the envelope.** Rejected: JWT is fine cryptographically but couples the envelope to OAuth-style token semantics that confuse the use case. Anyone reading the envelope expects "did the bytes match the hash and was this signed by UnSearch?" — that doesn't need JWT's audience / issuer / expiry semantics, and adding them dilutes the signal.

**4. PKI signing from day one (skip HMAC).** Rejected: per-customer keypair issuance, certificate-chain operations, and BYOK self-host all need to be solved before Week 3 ship — pushes the launch back 4+ weeks. HMAC v1 → PKI v2 with no envelope-shape break is the lower-risk path.

**5. Stop at hashing without signing.** Rejected: a hash alone proves bytes match; a signed envelope additionally proves *UnSearch produced this envelope*. The latter is the actual evidentiary property regulators and courts need.

## Cross-references

- [ADR-0009](./0009-verifiable-retrieval-as-product-surface.md) — product surface that requires this primitive
- [`docs/citation-envelope.md`](../citation-envelope.md) — full schema, signing process, verification process
- [WACZ-Auth spec](https://github.com/webrecorder/wacz-auth-spec)
- [WACZ Signing and Verification](https://specs.webrecorder.net/wacz-auth/0.1.0/)
- [Harvard LIL wacz-signing library](https://github.com/harvard-lil/wacz-signing)
- [C2PA FAQ](https://c2pa.org/faqs/) — for the rejected alternative
