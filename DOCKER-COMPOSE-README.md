# Docker Compose Files

## docker-compose.yml
**Purpose:** Full development environment
**Use:** `docker compose up -d`
**Includes:** All services (API, Web, SearXNG, PostgreSQL, Redis, Nginx, Celery)

## docker-compose.prod.yml
**Purpose:** Production deployment template
**Use:** `docker compose -f docker-compose.prod.yml up -d`
**Optimized:** Smaller images, production settings

## docker-compose.quickstart.yml
**Purpose:** Quick demo/testing (minimal services)
**Use:** `docker compose -f docker-compose.quickstart.yml up -d`
**Includes:** Only essential services (API, SearXNG, Redis)
