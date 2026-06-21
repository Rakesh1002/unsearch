# UnSearch Product Roadmap

> **How to read this doc:** Engineering roadmap. For the *commercial* story (ICP, pricing, GTM), see [strategy docs](./strategy/README.md). For per-feature truthful status, see [feature matrix](./feature-matrix.md). For what shipped in each release, see [CHANGELOG.md](../CHANGELOG.md) — anything in its `[Unreleased]` section is in flight but not live.

> **Reposition (2026-05-28).** UnSearch is "verifiable web retrieval for AI agents." The roadmap below is ordered around regulated-AI ICPs (legal-AI / medical-RAG / fintech research / govtech), not the prior indie-dev framing. ICP-1 (Priya — regulated-AI startup eng lead) is Phase 1; ICP-2 (David — regulated-company AI platform director) is Phase 2; ICP-3 (Anika — citation-integrity research / newsroom) is a continuous Free-tier ambassador track. See [strategy/icp.md](./strategy/icp.md).

## Current state summary

**Version:** 2.0.0 — Cloudflare-native rebuild deploying through the 3-week plan ending Week 3 (see `~/.claude/plans/app-unsearch-dev-is-not-deployed-luminous-wilkinson.md`).
**Status:** Backend production-ready in code (93 endpoints, real implementations), frontend built but never deployed, MCP server + verification wedge still to ship.

### Status legend
- ✅ Shipped (production, end-to-end tested)
- ✏️ Shipping in the 3-week rebuild (Week 1–3 work, per approved plan)
- 🔶 In beta (code paths exist, hardening in flight)
- 📋 Planned (on this roadmap, not shipped)

---

## Core capabilities — honest status

| Category | Features | Status |
|----------|----------|--------|
| **Verifiable retrieval (the wedge)** | Signed citation envelope per result, R2 snapshot store, `verify/citation`, `verify/claim`, audit log | ✏️ Shipping Week 2 |
| **MCP server** | Hono-hosted Streamable HTTP at `/mcp`; tools: `search`, `extract`, `research`, `verify_claim`; `npx @unsearch/mcp-server` | ✏️ Shipping Week 3 |
| **Web search** | SearXNG meta-search (70+ engines), multi-provider fallback | ✅ |
| **Neural / semantic search** | Exa-compatible neural endpoints (auto-prompt, highlights, similar) | ✅ |
| **Knowledge graph** | Entity extraction, people search, relationship mapping | 🔶 (no Drive/Slack/Confluence/Notion/GitHub connectors — not in scope) |
| **Topic monitoring** | Durable Object + scheduled checks + webhook fan-out | 🔶 (webhook retry + at-scale testing remaining) |
| **Source credibility** | `/api/v1/verify/source` heuristic | 🔶 |
| **Scraping** | Static, JavaScript, PDF, multi-engine | ✅ |
| **Extraction** | Tables, entities, attributes | ✅ |
| **Crawling** | Deep crawl, mapping, change tracking | ✅ |
| **RAG** | Embeddings (bge-m3), Vectorize, research mode | ✅ |
| **Workers AI tiered models** | gpt-oss-120b / qwq-32b / llama-3.3-70b / llama-3.1-8b | ✅ |
| **Auth** | JWT, API keys | ✅ |
| **OAuth (Google + GitHub)** | Env keys in `.env.example`, flow not wired | 📋 (Week 4) |
| **Privacy** | Zero-retention mode, content safety | ✅ |
| **Cloudflare edge — Workers / Vectorize / Queues / DOs / KV / R2 / D1** | All wired | ✅ |
| **Cloudflare Containers deploy** | FastAPI + SearXNG sidecar on CF Containers GA | ✏️ Shipping Week 1 |
| **Frontend on Cloudflare Workers** | Next.js 15 + @opennextjs/cloudflare, built but not deployed | ✏️ Shipping Week 1 |
| **Stripe billing** | Checkout + portal + subscription | ✅ |
| **Stripe metered overage** | Schema fields (`usage_records.search_overage`) present, Stripe metered prices not wired | 📋 (Month 3) |
| **Dashboard `/verify` + `/audit`** | New surfaces for the wedge | ✏️ Shipping Week 2 |
| **Dashboard `/team` + `/settings`** | Placeholder routes | 📋 (Month 2) |
| **Deep research agent** | Durable Object + Workers AI | 🔶 (multi-step depth + citation polish remaining) |

---

## 3-week rebuild plan — P0 (Weeks 1–3)

Mirrors the approved plan in `~/.claude/plans/app-unsearch-dev-is-not-deployed-luminous-wilkinson.md`. Each item names the ICP it unblocks.

### Week 1 — Deploy what exists + reposition

1. Rewrite [README](../README.md), [strategy docs](./strategy/README.md), [feature-matrix](./feature-matrix.md), and apps/web/app/page.tsx around verifiable retrieval. **(Day 1–2)** ✅ (this PR)
2. Build `backend/Dockerfile.cloudflare` image with FastAPI + SearXNG sidecar (supervisord-managed). **(Day 3)**
3. `wrangler containers deploy` on Cloudflare Containers GA (active-CPU billing). **(Day 3–4)**
4. Resolve all `localhost` refs in `backend/app/config.py:31,37,47,79,140` to container-internal DNS. **(Day 4)**
5. Uncomment container binding `apps/workers/wrangler.toml:84-90`; `wrangler deploy` Hono edge to `api.unsearch.dev`. **(Day 5)**
6. `cd apps/web && pnpm install && pnpm cf:build && pnpm cf:deploy` to `app.unsearch.dev`. **(Day 6)**
7. DNS: `unsearch.dev` → landing, `app.unsearch.dev` → dashboard, `api.unsearch.dev` → API/MCP. **(Day 7)**

### Week 2 — Verification wedge

8. Build `backend/app/services/citation_store.py` — R2 content-addressable snapshot store (sha256-keyed). **(Day 8–9)**
9. Update `backend/app/api/v1/search.py:30` + `backend/app/api/v1/agent.py:45` to compute hash + write snapshot for every result. **(Day 9–10)**
10. WACZ-aligned signed citation envelope (HMAC v1, key from `wrangler secret`); D1 schema for `citations` table. **(Day 10)**
11. `POST /api/v1/verify/citation` — return pinned snapshot + live diff. **(Day 11)**
12. `POST /api/v1/verify/claim` — re-fetch + Workers AI grader (llama-3.3-70b balanced) → `{supported, evidence_spans, confidence}`. **(Day 11–12)**
13. Promote `backend/app/api/v1/verify.py` from 🔶 beta to ✅ GA in feature matrix. **(Day 12)**
14. New dashboard page `apps/web/app/(dashboard)/verify/page.tsx`. **(Day 13)**
15. New dashboard page `apps/web/app/(dashboard)/audit/page.tsx`; D1 `verifications` table. **(Day 14)**

### Week 3 — MCP-first distribution + launch

16. Build `apps/workers/src/mcp/server.ts` — Hono MCP route at `/mcp` (Streamable HTTP transport). **(Day 15)**
17. Expose 4 tools: `search`, `extract`, `research`, `verify_claim`. **(Day 15–16)**
18. MCP auth: `X-API-Key` header → D1 lookup → plan-aware rate limit. **(Day 16)**
19. Build `apps/mcp-server/` npx package; `claude mcp add unsearch` works. **(Day 17)**
20. Submit to MCP registry, `awesome-mcp-servers`, `awesome-llm-tools`. **(Day 17)**
21. New landing copy: 60-second `verify_claim` interactive demo. **(Day 18)**
22. New page `docs/eu-ai-act-article-12.md` — compliance how-to. **(Day 18)**
23. Update `docs/quickstart.md` — three paths: MCP (lead), SDK, REST. **(Day 19)**
24. HN launch — "Show HN: UnSearch — verifiable web retrieval for AI agents (signed snapshots, MCP-native, Apache-2.0)". **(Day 20)**
25. Outreach to first 10 named ICP-1 customers (per [mrr-plan.md](./strategy/mrr-plan.md)). **(Day 20–21)**

---

## P1 — Month 2 (deepens ICP-1 activation)

26. **LangChain `langchain-community` integration PR** open (table stakes).
27. **Vercel AI SDK adapter** published.
28. **`/playground` "copy as cURL / TS / Python" buttons.**
29. **MCP server telemetry → PostHog** for the activation funnel.
30. **Better Auth migration** off the localStorage JWT placeholder.
31. **Google OAuth + GitHub OAuth** wired (keys already in `.env.example`).
32. **Public roadmap + issue tracker** discipline on GitHub.
33. **Self-host quickstart polish** — `wrangler deploy` from forked repo in < 5 min, with a `/deploy` guided UX in the dashboard.

---

## P2 — Month 3 (verification wedge maturity)

34. **`verify/claim` v2** with span-level evidence highlighting in dashboard.
35. **WACZ export endpoint** — download a signed `.wacz` for any audit-log entry. Submit to Webrecorder community for feedback.
36. **BYO storage** (S3, GCS, Azure Blob) for snapshot store on self-host.
37. **Stripe metered overage billing** (schema fields exist; wire Stripe metered prices).
38. **PQL automation** — Workers cron flags Free/Pro accounts crossing 50% utilization → Slack channel → founder DM template.
39. **Quarterly "Hallucinated Citation Index" v1 published.**

---

## P3 — Months 4–6 (unlock ICP-2 — David)

40. **Self-host paid contract motion** — first self-host v1 ($24K/yr) close; documentation hardening based on first 3 deployments.
41. **SOC 2 Type I** evidence package ready. Engage vCISO / Drata / Vanta.
42. **HIPAA BAA-ready** baseline; first healthcare customer reachable.
43. **GDPR DPA** templated (already in market via Common Paper).
44. **Customer-success automation** — docs-search-bot dogfooding our own MCP for tier-1 support.
45. **First Cloudflare Workers Launchpad** co-sell.
46. **Three published customer case studies** by Month 6 (legal, medical, fintech).

---

## P4 — Months 7–9 (Self-host v2 + Enterprise)

47. **WACZ public-key signing (PKI v2)** — replaces HMAC v1 for self-host customers who want cryptographic provenance owned by them.
48. **Differential snapshot diffs** — surface changes when a source mutates between fetches.
49. **Enterprise SSO (SAML / OIDC) + RBAC.**
50. **Dedicated Container replicas + Durable-Object pool** for Enterprise / Self-host v2 SLA tier.
51. **SOC 2 Type II audit** underway; **ISO 42001 attestation** in flight.
52. **Per-customer "agent run replay" UI** in dashboard.
53. **Self-host v2 ($99K/yr)** GA with full BAA + DPA + dedicated co-managed CF-account deployment.
54. **Knowledge-graph endpoints** brought to GA if a paying Enterprise customer requires them.

---

## P5 — Months 10–12 (compliance partner motion)

55. **BYOC (Bring Your Own Cloud) generalization** beyond Cloudflare — AWS / GCP / Azure deploy templates.
56. **Marketplace listings** — AWS, Azure, Google Cloud.
57. **Big4 / Tier-1 consultancy co-sell** pipeline operationalized (Deloitte AI Risk, EY Trusted AI, PwC AI Governance, KPMG AI Risk).
58. **NIST AI RMF examples directory** submission (post-SOC 2 Type I).
59. **First BigLaw or top-10-bank logo.**

---

## Anti-roadmap — explicitly NOT shipping

- Vector DB hosting (Vectorize is enough).
- Vertical legal / medical UI (we are infra, not apps — Harvey, Hebbia, Casetext are not the target).
- Generic SEO scraping (we respect robots.txt and ToS).
- Closed-source SaaS-only paths.
- Per-seat pricing.
- Free-tier removal under any circumstance.
- White-label / private-fork self-host (refuse politely; Apache 2.0 is the lever).
- Open-core feature splits (closed feature + open base would break the wedge).

---

## Technical debt

### High priority
| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| Hardcoded localhost URLs | `backend/app/config.py:31,37,47,79,140` | Container deploy blocks | Week 1, Day 4 — env-driven container DNS |
| Container binding disabled | `apps/workers/wrangler.toml:84-90` | Workers cannot reach FastAPI | Week 1, Day 5 — uncomment after container deploys |
| `engines_succeeded` not tracked | `backend/app/api/v1/search.py:193` | Metric gap | Low priority; close-out post-Week 3 |
| localStorage JWT placeholder | `apps/web/lib/auth.ts` | v1 only; not production for ICP-2 | Month 2 — Better Auth migration |

### Medium priority
| Issue | Location | Impact |
|-------|----------|--------|
| Sync DB operations | Multiple files | Performance |
| Missing retries on third-party engine calls | `backend/app/services/searxng.py` (partial) | Reliability |
| No request tracing | Middleware | Debugging |

### Low priority
| Issue | Location | Impact |
|-------|----------|--------|
| Inconsistent naming | Services | Maintainability |
| Missing docstrings | Some files | Documentation |
| Unused imports | Various | Clean code |

---

## API endpoint summary

### Total endpoints: 93 across 14 routers

| Category | Count | Path prefix |
|----------|-------|-------------|
| Agent (Tavily-compatible compatibility surface) | 5 | `/api/v1/agent/` |
| Search | 6 | `/api/v1/search/` |
| Neural (Exa-compatible) | 6 | `/api/v1/neural/` |
| Knowledge (in beta) | 5 | `/api/v1/knowledge/` |
| Monitor (in beta) | 6 | `/api/v1/monitor/` |
| **Verify (the wedge)** | 4 (3 GA Week 2) | `/api/v1/verify/` |
| **Audit (the wedge)** | 1 (GA Week 2) | `/api/v1/audit/` |
| RAG | 8 | `/api/v1/rag/` |
| Enhanced | 6 | `/api/v1/enhanced/` |
| Advanced v2 | 15 | `/api/v1/v2/advanced/` |
| Auth | 6 | `/api/v1/auth/` |
| Billing | 4 | `/api/v1/billing/` |
| **MCP transport** | 1 endpoint (4 tools) | `/mcp` |

---

## Success metrics

### Technical

| Metric | Target | Current |
|--------|--------|---------|
| API uptime | 99.5% v1 / 99.9% Enterprise | N/A (not deployed) |
| `search` P95 latency | <800ms | N/A |
| `verify/claim` P95 latency | <2s | N/A |
| Container idle cost | <$15/mo | N/A |
| Edge p50 | <50ms | N/A |
| Test coverage | >80% | ~40% |
| Error rate | <0.1% | ~1% on internal benchmark |

### Business — see [strategy/mrr-plan.md](./strategy/mrr-plan.md) for the month-by-month plan

| Milestone | Target month |
|-----------|--------------|
| $25K MRR | Month 3 |
| $250K MRR | Month 9 |
| $750K MRR | Month 12 |

---

## Contact & resources

- **Feature matrix:** [`docs/feature-matrix.md`](./feature-matrix.md)
- **Architecture:** [`docs/architecture.md`](./architecture.md)
- **Cloudflare architecture:** [`docs/cloudflare-architecture.md`](./cloudflare-architecture.md)
- **AI pipeline:** [`docs/ai-pipeline.md`](./ai-pipeline.md)
- **Citation envelope schema:** [`docs/citation-envelope.md`](./citation-envelope.md)
- **API reference:** `http://localhost:8000/docs` (local) / [api.unsearch.dev/docs](https://api.unsearch.dev/docs) (after Week 1 deploy)
- **Edge Worker docs:** [`apps/workers/README.md`](../apps/workers/README.md)
- **Approved 3-week rebuild plan:** `~/.claude/plans/app-unsearch-dev-is-not-deployed-luminous-wilkinson.md`

---
**Owner:** Rakesh Roushan · **Last reviewed:** 2026-06-21 · **Review by:** 2026-09-21
