# ADR-0005: Apache 2.0 license + self-hostable from day one

- Status: Accepted
- Date: 2026-04-15
- Deciders: @Rakesh1002

## Context

The competitive landscape (Tavily, Exa, Brave) is uniformly closed-source. That's both an obvious differentiation lane and a strategic question with multiple wrong answers:

- "Source-available, BSL after N years" (the MongoDB / Sentry / Elastic playbook) is good for hostile-clone defense but bad for the developer-trust pitch we lead with.
- "AGPL" closes off the use case of teams who want to embed our SDK in a closed-source product, which is most of the Persona A market.
- "MIT" is permissive but lacks the patent grant we want for enterprise procurement comfort.

The license choice locks in a lot — it determines who can use the code, whether contributors will assign rights, and whether VC fundraising in the future is constrained by the license history.

## Decision

License everything under **Apache 2.0** and commit to a **working self-host path on day one**.

Concretely:

- All code in the monorepo is Apache-2.0 (`LICENSE` at repo root, restated in every SDK package).
- `docker compose up -d` from a freshly cloned repo produces a working API in <5 minutes, against a free Cloudflare account or no Cloudflare at all.
- Every feature in `docs/feature-matrix.md` marked ✅ works in self-host. Features that require a Cloudflare account (Workers AI tier, Vectorize) are clearly flagged as such.
- The hosted version at `api.unsearch.dev` runs the **same code** as the self-host. No "open-core" / "Enterprise edition" fork — the wedge is hosted convenience + the Cloudflare-native edge, not feature gating.
- No CLA. Contributions sit under the Apache-2.0 grant from the moment they merge.

This decision is the spine of every other one — the SDK choices (separate packages, no proprietary protocols), the architecture (self-hostable Containers, not a closed cloud), the pricing (free tier at 5,000 reqs/mo).

## Consequences

- **Pro:** Eliminates the "what if you get acquired and shut down the API" objection in Persona A and B sales conversations.
- **Pro:** Apache 2.0's patent grant is what enterprise legal teams want to see. Reduces friction at the Persona C tier where procurement reviews the license.
- **Pro:** Self-hosting is the ultimate price-fairness commitment — if the hosted price ever climbs unreasonably, customers can leave. This is also the *honest* answer to the "10× cheaper, but what's the lock-in risk?" question.
- **Pro:** Public source is the strongest possible recruiting signal. We've already seen interns + community PRs.
- **Con:** Hostile competitor can fork the code. We accept this. The moat is the **hosted UX** (billing, dashboard, Cloudflare-native edge deploy, the curated SearXNG engine config) and the **community** (SDKs, integrations, docs), not the code itself.
- **Con:** Some VC firms have soft preferences against permissive-licensed startups. We accept the smaller funnel of sympathetic investors as a non-issue at our stage.
- **Con:** No "Enterprise tier with extra features" — the Enterprise tier is "managed-service + SLA + SOC 2," not "you get features the OSS version doesn't have." This constrains future pricing flexibility, which we judge to be the correct trade.

## Alternatives considered

- **MIT.** Considered — close call. Apache 2.0 won for the patent grant alone. Patent risk for a search API touching multiple LLM patents is non-zero, and the explicit Apache grant pre-empts that conversation.
- **BSL → Apache 2.0 after 4 years (the MongoDB / Sentry / Elastic playbook).** Rejected — the audience we want (Persona A indie devs) reads BSL as "they'll change their mind later," which kills the trust pitch.
- **AGPL.** Rejected — closes off embedding inside closed-source products, which is the majority Persona A use case.
- **Open-core (Apache OSS + proprietary Enterprise add-ons).** Rejected — the maintenance burden of two codebases, plus the eternal "is this feature OSS or paid?" friction.
- **Source-available "Functional Source License" / "FSL."** Considered. Rejected because it's still too new for procurement teams to recognize, defeating one of the main reasons to be OSS at all.
