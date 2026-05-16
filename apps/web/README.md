# UnSearch Web

Next.js 15 dashboard for UnSearch, deployed on Cloudflare Pages via
`@cloudflare/next-on-pages`.

## Quick start

```bash
pnpm install
# Run the Worker on :8787 in another shell first:
#   cd ../../workers && pnpm dev
pnpm dev
# Open http://localhost:3000
```

The dev server proxies `/api/v1/*` to the Worker so the dashboard talks
to live edge endpoints without CORS pain.

## Build & deploy

```bash
pnpm pages:build       # produces .vercel/output/static
pnpm pages:deploy      # uploads to CF Pages project unsearch-web
```

## Routes shipped in v1

- `/` — marketing landing
- `/login`, `/signup` — auth (talks to Worker `/auth/*`)
- `/dashboard` — usage + plan summary
- `/api-keys` — create/revoke per-key UI
- `/playground` — live search request form
- `/billing` — Stripe checkout + portal
- `/team`, `/settings` — placeholder routes (todo)

## Auth

Token-in-localStorage for v1. Swap to Better Auth or NextAuth in Stage 7
for OAuth + session cookies if needed.
