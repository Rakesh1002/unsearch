# ADR-0010: Cloudflare Containers as origin runtime

- Status: Accepted
- Date: 2026-05-28
- Deciders: @Rakesh1002

## Context

ADR-0001 committed to Cloudflare-native edge architecture: Workers + D1 + KV + Vectorize + R2 + Queues + Durable Objects. That stack runs the *edge* layer correctly.

The *origin* layer is where ADR-0001 hit a wall. UnSearch depends on SearXNG — a long-running Python process that aggregates 70+ search engines. Workers cannot host SearXNG: confirmed by the SearXNG maintainers ([discussion #4119](https://github.com/searxng/searxng/discussions/4119)) — SearXNG needs persistent compute and longer-lived process state than Workers' execution model provides. The same is largely true for parts of the FastAPI backend that depend on long-lived sessions or large native dependencies.

Until April 2026, the workable answers were:

1. Run SearXNG + FastAPI on a third-party container host (Railway, Fly, DigitalOcean) and have the Worker proxy to it. Adds an external dependency, hurts the "all-on-Cloudflare" story for ICP-2 buyers, and complicates self-host.
2. Rewrite the FastAPI backend in TypeScript/Hono running on Workers, replacing SearXNG with direct engine API calls. ~3 months of work, throws away a working 93-endpoint backend, and either reintroduces per-vendor lock-in or attempts to reimplement what SearXNG already does.
3. Keep the Container service binding in `workers/wrangler.toml` commented out (which is the current state — `wrangler.toml:84-90`) and ship nothing.

**Cloudflare Containers reached General Availability on April 13, 2026.** Per the [Cloudflare Containers docs](https://developers.cloudflare.com/containers/) and the [pricing page](https://developers.cloudflare.com/containers/pricing/), the GA brings three properties that change the trade-off:

- **Active-CPU billing** — only the CPU cycles actually consumed are billed; idle containers cost memory + storage only.
- **Service bindings address containers by hostname** — Workers can reach Containers as named services without explicit IP / DNS discovery.
- **Thousands of parallel containers per account** with autoscale.

Active-CPU billing is the critical property. SearXNG idle = ~$0. SearXNG handling a search burst = pennies. This eliminates the cost-driven reason for the rewrite-to-Workers path.

## Decision

UnSearch's origin runtime is **Cloudflare Containers**. The FastAPI backend (`app/`) and the SearXNG sidecar run together as a Container deployment, reachable from the Hono Worker edge (`workers/`) via service binding.

Practical implementation:

- `backend/Dockerfile.cloudflare` packages FastAPI + SearXNG together (supervisord-managed) or as adjacent containers wired via internal DNS. The two-container topology is preferred long-term for independent scaling.
- `wrangler.toml` (root) declares the Container with active-CPU billing.
- `workers/wrangler.toml:84-90` Container service binding is uncommented; Worker requests resolve to the Container by hostname.
- Hardcoded `localhost` URLs in `backend/app/config.py:31,37,47,79,140` are replaced with env-driven container-internal DNS.
- Hosted and self-host topologies use identical Docker images; self-host customers `wrangler containers deploy` from their forked repo.

## Consequences

We commit to:

- Cloudflare as the runtime substrate not just at the edge but at the origin. BYOC support (AWS / GCP / Azure deploy templates) is deferred to Month 10+, and is positioned as a customer accommodation, not as a strategic axis.
- Treating active-CPU billing as a P0 SLO concern — any code path that spins CPU unnecessarily (chatty polling, busy loops, unbatched engine fan-out) is a cost regression, not just a latency regression.
- A single set of deployment runbooks (`docs/deployment/`) anchored on `wrangler containers deploy`, with Railway / DigitalOcean kept as alternates for the open-source community but not as the default story.
- Workers reaching Containers via service binding only — no public Container hostnames, no direct ingress.

What we knowingly give up:

- A multi-cloud-from-day-one self-host story. ICP-2 buyers without Cloudflare strategy must wait until BYOC ships in Month 10+. We mitigate by selling self-host to CF-friendly accounts first.
- Theoretical edge-perfect latency on hot search paths. SearXNG must be reached, which crosses an internal hop. Mitigated by KV cache + the empirical observation that the 70+ engine fan-out is dominated by third-party engine latency, not by the internal hop.

## Alternatives considered

**1. Rewrite FastAPI to Hono on Workers and replace SearXNG with direct engine calls.** Rejected: ~3 months of work, abandons a production-ready 93-endpoint backend (audit confirms no critical stubs), reintroduces per-engine vendor relationships UnSearch wanted to abstract via SearXNG, and breaks ADR-0002.

**2. Run FastAPI + SearXNG on Railway / Fly / DigitalOcean as the primary topology, with Workers proxying.** Rejected: weakens the all-on-Cloudflare positioning for ICP-2 (self-host on customer's CF account); introduces a third-party billing relationship; complicates the self-host story; loses the active-CPU billing advantage; multi-vendor support contracts add overhead.

**3. Run SearXNG on Containers, FastAPI on Workers (Python via Pyodide / WebAssembly).** Rejected: FastAPI on Pyodide is experimental, has performance footguns, and would force a deeper rewrite of any sync DB code. Not worth the complexity given that Containers can host FastAPI directly.

**4. Wait for Pyodide Workers maturity instead of adopting Containers.** Rejected: that path's timeline is open; Containers GA shipped; we can deploy this month. ADR-0009 commits to a 3-week rebuild that requires a deploy path that exists today.

## Cross-references

- [ADR-0001](./0001-cloudflare-native-edge-architecture.md) — original CF-native commitment that this ADR extends
- [ADR-0002](./0002-searxng-as-meta-search-aggregator.md) — SearXNG dependency that requires persistent compute
- [ADR-0009](./0009-verifiable-retrieval-as-product-surface.md) — new product surface this runtime supports
- [Cloudflare Containers docs](https://developers.cloudflare.com/containers/)
- [Cloudflare Containers pricing](https://developers.cloudflare.com/containers/pricing/)
- [SearXNG Workers discussion](https://github.com/searxng/searxng/discussions/4119) — confirms SearXNG cannot run on Workers
