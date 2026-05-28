# UnSearch documentation

Start here. This page is the entry point for everyone who isn't sure which file to open.

> **Repositioned 2026-05-28** from "open-source Tavily alternative" to "verifiable web retrieval for AI agents." See [`strategy/positioning.md`](./strategy/positioning.md) for the new one-liner and [`strategy/market.md`](./strategy/market.md) for the structural shifts that drove it. ADRs 0009–0013 capture the technical implications.

## I want to…

### …understand the product

| For | Read |
|-----|------|
| The 30-second pitch | [`/README.md`](../README.md) (repo root) |
| Why we built UnSearch and the problem it solves | [`strategy/market.md`](./strategy/market.md) and [`strategy/positioning.md`](./strategy/positioning.md) |
| Who we sell to | [`strategy/icp.md`](./strategy/icp.md) |
| What's shipped vs. in beta vs. planned | [`feature-matrix.md`](./feature-matrix.md) |
| Pricing rationale | [`strategy/pricing.md`](./strategy/pricing.md) |
| Where the company is going | [`roadmap.md`](./roadmap.md) and [`strategy/mrr-plan.md`](./strategy/mrr-plan.md) |

### …use the API

| For | Read |
|-----|------|
| 60-second MCP install (lead path) | [`/README.md`](../README.md#quick-start--mcp-first) |
| 5-minute self-host quickstart | [`quickstart.md`](./quickstart.md) |
| Migrate from Tavily (compatibility surface) | [`migration/from-tavily.md`](./migration/from-tavily.md) |
| Endpoint contracts | [`API_REFERENCE.md`](./API_REFERENCE.md) (or live OpenAPI at `/docs`) |
| Worked examples per endpoint | [`API_EXAMPLES.md`](./API_EXAMPLES.md) |
| Citation envelope schema (the wedge primitive) | [`citation-envelope.md`](./citation-envelope.md) |
| Which AI model runs each request | [`ai-pipeline.md`](./ai-pipeline.md) (and [`ai-quick-reference.md`](./ai-quick-reference.md) for a one-pager) |
| Use the Python SDK | [`/apps/sdk-py/README.md`](../apps/sdk-py/README.md) |
| Use the TypeScript SDK | [`/apps/sdk-ts/README.md`](../apps/sdk-ts/README.md) |
| Use the LlamaIndex retriever | [`/apps/sdk-llamaindex/README.md`](../apps/sdk-llamaindex/README.md) |

### …contribute to the code

| For | Read |
|-----|------|
| What's where in the repo | [`what-is-what.md`](./what-is-what.md) |
| How the architecture works | [`architecture.md`](./architecture.md) |
| Cloudflare-specific wiring | [`cloudflare-architecture.md`](./cloudflare-architecture.md) and [`/workers/README.md`](../workers/README.md) |
| Why we made each major decision | [`adr/`](./adr/README.md) |
| Repo conventions (testing, commits, naming) | [`/CONTRIBUTING.md`](../CONTRIBUTING.md) and [`/CLAUDE.md`](../CLAUDE.md) |
| What shipped recently | [`/CHANGELOG.md`](../CHANGELOG.md) |

### …operate UnSearch

| For | Read |
|-----|------|
| Deploy to Cloudflare (recommended) | [`/workers/README.md`](../workers/README.md) and [`deployment/quick-reference.md`](./deployment/quick-reference.md) |
| Deploy to Railway | [`deployment/railway.md`](./deployment/railway.md) |
| Deploy to DigitalOcean | [`deployment/digitalocean.md`](./deployment/digitalocean.md) |
| On-call playbooks | [`operations/RUNBOOKS.md`](./operations/RUNBOOKS.md) |
| Observability + dashboards | [`/workers/OBSERVABILITY.md`](../workers/OBSERVABILITY.md) |
| Manage secrets | [`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md) and [`/workers/SECRETS.md`](../workers/SECRETS.md) |
| Configure env vars | [`configuration/env-variables.md`](./configuration/env-variables.md) |
| Set up Stripe billing | [`BILLING_SETUP.md`](./BILLING_SETUP.md), [`configuration/stripe-webhook.md`](./configuration/stripe-webhook.md), [`configuration/webhook-events.md`](./configuration/webhook-events.md) |

### …sell or support UnSearch

| For | Read |
|-----|------|
| The ICP definition | [`strategy/icp.md`](./strategy/icp.md) |
| Jobs-to-be-done framework | [`strategy/jtbd.md`](./strategy/jtbd.md) |
| Sales playbook | [`strategy/sales-playbook.md`](./strategy/sales-playbook.md) |
| GTM plan | [`strategy/gtm.md`](./strategy/gtm.md) |
| User journey + activation | [`strategy/user-journey.md`](./strategy/user-journey.md) |
| Market + competitor landscape | [`strategy/market.md`](./strategy/market.md) |
| Value proposition | [`strategy/value-prop.md`](./strategy/value-prop.md) |

---

## Doc conventions

- **Status taxonomy.** Every feature claim uses ✅ shipped / 🔶 in beta / 📋 planned. See [ADR-0008](./adr/0008-honest-feature-status-policy.md).
- **Single source of truth.** [`feature-matrix.md`](./feature-matrix.md) is canonical for status; [`CHANGELOG.md`](../CHANGELOG.md) is canonical for what shipped when. Other docs link to these — they don't restate.
- **Code/doc co-location.** Per-package READMEs live next to the code: `apps/*/README.md`, `workers/README.md`. Cross-cutting docs live here.
- **No emoji in code or commit messages.** Emoji are fine in docs only.
- **ADRs document non-obvious decisions.** Don't write one for routine implementation choices. See [`adr/README.md`](./adr/README.md).

## When something is wrong

If something in these docs is inaccurate, please file an issue at [github.com/Rakesh1002/unsearch/issues](https://github.com/Rakesh1002/unsearch/issues). Documentation rot is real and we'd rather know.
