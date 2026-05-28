# Architecture Decision Records

This directory captures the **non-obvious, sticky decisions** that shaped UnSearch — the ones a new contributor would otherwise have to reverse-engineer from the code.

We use a lightweight [MADR](https://adr.github.io/madr/)-style template:

```
# ADR-NNNN: Short imperative title

- Status: Accepted | Superseded by ADR-XXXX | Deprecated
- Date: YYYY-MM-DD
- Deciders: GitHub handles

## Context
What is the problem we're solving? What constraints apply?

## Decision
What did we choose? Phrased so future-us can tell whether the current code still matches.

## Consequences
What does this commit us to? What did we knowingly give up?

## Alternatives considered
What did we reject and why?
```

## When to write an ADR

Write one when you're about to make a decision that is:

- **Hard to reverse** — picking a primary datastore, choosing a license, picking a wire format
- **Cross-cutting** — affects more than one app/package in the monorepo
- **Surprising in retrospect** — would make a new contributor ask "why on earth did they do it that way?"

Don't write one for routine implementation choices (loop vs. recursion, file naming, etc.).

## Status taxonomy

- **Accepted** — currently in force, code matches.
- **Superseded by ADR-XXXX** — the decision was reversed; the new ADR explains why.
- **Deprecated** — no longer in force but kept for history.

When you supersede an ADR, **don't delete the old one** — change its status line and link forward.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](./0001-cloudflare-native-edge-architecture.md) | Cloudflare-native edge architecture | Accepted |
| [0002](./0002-searxng-as-meta-search-aggregator.md) | SearXNG as the meta-search aggregator | Accepted |
| [0003](./0003-tavily-compatible-drop-in-surface.md) | Tavily-compatible drop-in API surface | Accepted (downgraded from primary positioning by ADR-0009) |
| [0004](./0004-workers-ai-tiered-model-selection.md) | Workers AI with tiered model selection | Accepted |
| [0005](./0005-apache-2-license-self-hostable-from-day-one.md) | Apache 2.0 + self-hostable from day one | Accepted |
| [0006](./0006-monorepo-with-apps-and-workers.md) | Monorepo layout with `apps/*` + `workers/` | Accepted |
| [0007](./0007-python-sdk-sync-and-async.md) | Python SDK ships sync + async clients | Accepted |
| [0008](./0008-honest-feature-status-policy.md) | Honest feature-status policy (✅ / 🔶 / 📋) | Accepted |
| [0009](./0009-verifiable-retrieval-as-product-surface.md) | Verifiable Retrieval as the product surface | Accepted |
| [0010](./0010-cloudflare-containers-as-origin-runtime.md) | Cloudflare Containers as origin runtime | Accepted |
| [0011](./0011-wacz-aligned-signed-envelope.md) | WACZ-aligned signed envelope format | Accepted |
| [0012](./0012-mcp-first-distribution.md) | MCP-first distribution | Accepted |
| [0013](./0013-icp-shift-to-regulated-ai.md) | ICP shift to regulated AI | Accepted |
