# Observability — UnSearch Workers

## Built-in (zero config)

- **Workers Analytics Engine** — every request emits a data point in
  `src/middleware/logging.ts` with method, path, country, plan, latency,
  status. Query via the dashboard or `wrangler analytics`.
- **`/health` endpoint** — used by uptime monitors and CF Containers
  health probes.
- **`X-Request-Id` propagation** — accepted from clients, generated when
  absent, returned on every response, included in every log line.

## Sentry

Set `SENTRY_DSN` secret. The `wrapSentry` HOC in
`src/middleware/sentry.ts` wraps the Worker handler so unhandled
exceptions ship to Sentry with environment + path tags. Sample rate is
10% in prod, 100% elsewhere.

```bash
wrangler secret put SENTRY_DSN --env production
```

## Logpush

CF Workers Logpush ships every console log + analytics event to R2 (or
S3-compatible). Enable in the CF dashboard:
*Workers & Pages → Workers Logs → Logpush → R2 bucket `unsearch-storage`,
prefix `logs/`*.

## PostHog (frontend only)

The dashboard at `apps/web` initializes PostHog if
`NEXT_PUBLIC_POSTHOG_KEY` is set. Track product usage; the API itself
goes through Workers Analytics.

## Daily D1 backup

`workers/src/scheduled.ts` runs at `0 3 * * *` UTC and dumps every
table to R2 at `backups/d1/<YYYY-MM-DD>.json`. Restore via
`scripts/migrate_pg_to_d1.py` (point it at the JSON dump in R2).

## Alerts

Configure CF alerts (dashboard → Notifications):
- Worker error-rate > 1%
- Container health-check failures
- D1 quota at 80%
- KV quota at 80%
- R2 egress > $50/day (cost guardrail)
