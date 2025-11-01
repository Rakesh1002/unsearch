# Backend (UnQuest API)

## Local quick start

- Copy `.env.example` to `.env` and fill values (Neon Postgres, Upstash Redis, Stripe).
- Install deps with Poetry and run startup script:

```bash
poetry install --no-root
scripts/start-all.sh
```

This will:

- Start SearXNG in Docker
- Run Alembic migrations
- Start API on :8000 and Celery worker/beat if broker is configured

## JavaScript rendering (Puppeteer)

- The backend supports js_mode via a Puppeteer render service.
- Configure via env:
  - `PUPPETEER_ENABLED=true`
  - `PUPPETEER_SERVICE_URL=http://localhost:9223`
  - `PUPPETEER_TIMEOUT=30`
- Request fields: `js_mode`, `screenshot`, `pdf`, and `output_format` (`json` or `markdown`).

### Healthcheck

- API `/health` now includes a `puppeteer` entry showing status and latency.
- The healthcheck probes `PUPPETEER_SERVICE_URL` at `/health` then `/` with a 3s timeout.

## Railway deployment

1. Create a new Railway project and add a “Service” for this directory.
2. Set Nixpacks builder (automatic) and the following env vars:

- DATABASE_URL (Neon) — include `sslmode=require`
- REDIS_URL (Upstash)
- SEARXNG_URL (your hosted SearXNG or internal)
- STRIPE\_\* (if using billing)
- API_KEYS (optional, comma-separated)
- ALLOWED_ORIGINS, CORS_METHODS, CORS_HEADERS as JSON arrays if overriding

3. Processes (Procfile):

- web: runs uvicorn
- worker: Celery worker
- beat: Celery beat

On Railway, you can deploy multiple services from the same repo:

- One service using `web` process (exposes $PORT)
- One service using `worker` process
- One service using `beat` process

Alternatively, a single service can run `web` and you create two additional services pointing to the same repo and override the start command to `worker` / `beat`.

### Notes about Neon SSL

We sanitize unsupported DSN params (sslmode, channel_binding, etc.) for asyncpg and set `connect_args["ssl"]=True` automatically when `sslmode` is not `disable`.

### Health checks

- API: `/health`
- Metrics: `/metrics` (if enabled)
