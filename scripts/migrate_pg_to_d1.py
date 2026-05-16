"""
One-off Postgres → D1 data migration.

Walks every table in the schema, dumps it to JSON, then bulk-inserts via
the D1 REST API. Use this when cutting over an existing UnSearch
deployment to the new CF-native stack. Skip it for greenfield prod.

Prereqs:
  pip install asyncpg httpx
  Set env vars:
    PG_URL                       — source Postgres URL
    CLOUDFLARE_ACCOUNT_ID        — destination account
    CLOUDFLARE_API_TOKEN         — token with D1:edit
    CLOUDFLARE_D1_DATABASE_ID    — destination D1 DB ID

Usage:
  python scripts/migrate_pg_to_d1.py --batch-size 500 --tables users,api_keys
  python scripts/migrate_pg_to_d1.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any

import asyncpg  # type: ignore[import-not-found]
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pg2d1")

# Order matters: parents before children (FK dependencies)
TABLE_ORDER = [
    "users",
    "plans",
    "api_keys",
    "user_api_keys",
    "subscriptions",
    "usage_records",
    "invoices",
    "webhook_events",
    "search_requests",
    "search_results",
    "scraping_jobs",
    "scrape_requests",
    "cache_entries",
    "error_logs",
]

# Columns that need JSON serialization (PG JSONB → SQLite TEXT)
JSON_COLUMNS = {
    "api_keys": ["metadata"],
    "user_api_keys": ["scopes", "ip_whitelist"],
    "plans": ["features", "metadata"],
    "subscriptions": ["features"],
    "usage_records": ["usage_by_engine", "usage_by_day"],
    "invoices": ["metadata"],
    "webhook_events": ["data"],
    "search_requests": ["engines", "request_headers"],
    "search_results": ["scraped_content"],
    "scraping_jobs": ["urls", "config", "results"],
    "scrape_requests": ["urls", "config"],
    "error_logs": ["error_details"],
}

# Columns that are SQL booleans in PG but need 0/1 ints in SQLite
BOOL_COLUMNS = {
    "users": [
        "is_active", "is_verified", "is_admin",
        "is_agent_placeholder", "is_sandbox_expired",
    ],
    "api_keys": ["is_active"],
    "user_api_keys": ["is_active"],
    "plans": ["is_active", "is_visible"],
    "search_requests": ["cache_hit"],
    "search_results": ["scraped_successfully"],
    "scraping_jobs": ["webhook_success"],
    "webhook_events": ["processed"],
}


def coerce_row(table: str, row: asyncpg.Record) -> list[Any]:
    """Convert a PG row to a D1-compatible parameter list."""
    json_cols = set(JSON_COLUMNS.get(table, []))
    bool_cols = set(BOOL_COLUMNS.get(table, []))
    out: list[Any] = []
    for k, v in row.items():
        if v is None:
            out.append(None)
        elif k in bool_cols:
            out.append(1 if v else 0)
        elif k in json_cols:
            out.append(json.dumps(v) if not isinstance(v, str) else v)
        elif hasattr(v, "isoformat"):
            out.append(v.isoformat())
        elif isinstance(v, (dict, list)):
            out.append(json.dumps(v))
        else:
            out.append(v)
    return out


async def fetch_rows(conn: asyncpg.Connection, table: str) -> list[asyncpg.Record]:
    return await conn.fetch(f"SELECT * FROM {table}")


def build_insert(table: str, columns: list[str]) -> str:
    placeholders = ", ".join(f"?{i + 1}" for i in range(len(columns)))
    return f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"


async def d1_batch_insert(
    client: httpx.AsyncClient,
    table: str,
    columns: list[str],
    batch: list[list[Any]],
) -> None:
    sql = build_insert(table, columns)
    body = [{"sql": sql, "params": params} for params in batch]
    resp = await client.post("/query", json=body)
    payload = resp.json()
    if not payload.get("success"):
        raise RuntimeError(f"D1 insert failed for {table}: {payload.get('errors')}")


async def migrate_table(
    pg: asyncpg.Connection,
    d1: httpx.AsyncClient,
    table: str,
    batch_size: int,
    dry_run: bool,
) -> int:
    rows = await fetch_rows(pg, table)
    if not rows:
        log.info("%s: empty, skipping", table)
        return 0
    columns = list(rows[0].keys())
    log.info("%s: %d rows, %d columns", table, len(rows), len(columns))

    if dry_run:
        return len(rows)

    for i in range(0, len(rows), batch_size):
        chunk = [coerce_row(table, r) for r in rows[i : i + batch_size]]
        await d1_batch_insert(d1, table, columns, chunk)
        log.info("  %s: inserted %d / %d", table, min(i + batch_size, len(rows)), len(rows))
    return len(rows)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--tables", help="comma-separated subset")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    pg_url = os.environ.get("PG_URL")
    if not pg_url:
        log.error("PG_URL env var required")
        return 2

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    api_token = os.environ["CLOUDFLARE_API_TOKEN"]
    db_id = os.environ["CLOUDFLARE_D1_DATABASE_ID"]

    tables = args.tables.split(",") if args.tables else TABLE_ORDER

    pg = await asyncpg.connect(pg_url)
    d1 = httpx.AsyncClient(
        timeout=60.0,
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{db_id}",
    )

    total = 0
    try:
        for table in tables:
            count = await migrate_table(pg, d1, table, args.batch_size, args.dry_run)
            total += count
    finally:
        await pg.close()
        await d1.aclose()

    log.info("Done. %d rows %s.", total, "would migrate" if args.dry_run else "migrated")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
