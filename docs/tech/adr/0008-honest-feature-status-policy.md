# ADR-0008: Honest feature-status policy (✅ / 🔶 / 📋)

- Status: Accepted
- Date: 2026-04-20
- Deciders: @Rakesh1002

## Context

In the v1 README we claimed "Glean parity ✅" for a feature set that didn't exist (Glean searches inside-company corpora via connectors we haven't built). We claimed Knowledge Graph, Topic Monitoring, Fact Verification, and Deep Research Agent were "Completed" when in fact the code paths existed but coverage, edge cases, and accuracy were still being closed out.

That kind of marketing-vs-reality gap is the single fastest way to lose Persona A trust. A senior engineer who tries a feature, finds it half-baked, and feels lied to will not come back for v2.

We need a way to communicate "this exists, but use it with eyes open" that is more useful than ❌ and more honest than ✅.

## Decision

Adopt a **three-level status taxonomy** used uniformly across docs:

| Symbol | Meaning | Bar |
|--------|---------|-----|
| ✅ | Shipped | Production code path, end-to-end tested, on the public API, in the SDKs, in CHANGELOG. Promises stability. |
| 🔶 | In beta | Code paths exist and respond, but coverage, edge cases, or polish are still being closed out. Visible in the API. May change shape with notice. |
| 📋 | Planned | On the roadmap, not in the code. Not in the API. |

Rules:

1. **`docs/feature-matrix.md` is the single source of truth.** Any other doc (README, roadmap, marketing site) that claims a status must match it.
2. **Every 🔶 row links to the CHANGELOG `[Unreleased] — Deferred to follow-up` section** explaining what still needs to land before it ships to ✅.
3. **Lying upward is the worst sin.** Marking a 🔶 feature as ✅ to make the matrix look better is a fireable mistake (for the founder; for an intern it's a learning moment).
4. **Lying downward is wasteful.** Marking a feature 📋 because we want to look modest costs us deals; if it works, mark it ✅.
5. **The CHANGELOG records every transition.** A 🔶 → ✅ promotion lands in a release entry. A ✅ → 🔶 demotion (yes, this happens) lands too — with the reason.

The same policy applies to the roadmap document, sales decks, the homepage, and the public docs site at docs.unsearch.dev.

## Consequences

- **Pro:** Persona A trust is the company's most expensive asset. This policy directly protects it.
- **Pro:** It gives the sales conversation a clean line: "Here's what works today. Here's what's in beta — try it, file issues, we're hardening it. Here's what we'll build next." Way better than feature-matrix arms-race claims.
- **Pro:** It frames our 🔶 features as *differentiation* rather than as competitor parity. Tavily/Exa/Brave don't have a Knowledge Graph at all — ours being 🔶 is still more than zero, and saying so honestly converts better than fake-✅ would.
- **Con:** Sales-ops and marketing partners sometimes push for ✅ everywhere. We hold the line.
- **Con:** Investors who skim the matrix may discount 🔶 to ❌ mentally. We accept this — the right investor for us is one who can read the matrix carefully.

## Alternatives considered

- **Binary ✅ / ❌.** Rejected — fails for the half-built case, which is most of the interesting roadmap surface.
- **Five-level (alpha / beta / GA / stable / deprecated).** Rejected — too many states, no useful product distinction between "alpha" and "beta" at our stage.
- **Per-endpoint maturity badges, with no top-level matrix.** Considered. Rejected — sales conversations need a single page to point at; per-endpoint badges fragment that.
- **"Status: experimental" prose without a symbol.** Rejected — symbols make the matrix scannable, which is the only way prospects actually read it.
