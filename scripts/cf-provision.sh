#!/usr/bin/env bash
# Idempotently provision all Cloudflare resources for UnSearch.
# Safe to re-run: every command tolerates "already exists" errors.
#
# Prereqs:
#   - `wrangler login` (interactive, runs once per machine)
#   - $CLOUDFLARE_ACCOUNT_ID exported (or single-account on wrangler)
#
# Output: writes the resource IDs to apps/workers/.cf-resources.env which is
# then used to populate apps/workers/wrangler.toml placeholders.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/apps/workers"

ENV_FILE="$REPO_ROOT/apps/workers/.cf-resources.env"
: > "$ENV_FILE"

echo ">>> Provisioning Cloudflare resources for UnSearch"
echo ">>> Resource IDs will be written to: $ENV_FILE"
echo

run() {
  echo "+ $*"
  set +e
  OUT="$("$@" 2>&1)"
  RC=$?
  set -e
  echo "$OUT"
  if [ $RC -ne 0 ] && ! echo "$OUT" | grep -qiE "already exists|duplicate|conflict"; then
    return $RC
  fi
  return 0
}

extract_id() {
  echo "$1" | grep -oE '[a-f0-9]{32}' | head -n 1 || true
}

# ---- D1 ----
echo "[1/8] D1 database"
D1_OUT="$(npx wrangler d1 create unsearch-prod 2>&1 || true)"
echo "$D1_OUT"
D1_ID="$(echo "$D1_OUT" | grep -oE 'database_id = "[a-f0-9-]+"' | head -1 | cut -d\" -f2 || true)"
if [ -z "$D1_ID" ]; then
  D1_ID="$(npx wrangler d1 list 2>/dev/null | grep -E '\bunsearch-prod\b' | awk '{print $1}' | head -1)"
fi
echo "D1_PROD_ID=$D1_ID" >> "$ENV_FILE"

# ---- KV namespaces ----
echo
echo "[2/8] KV namespaces"
for BINDING in CACHE RATE_LIMIT SESSIONS API_KEYS; do
  KV_OUT="$(npx wrangler kv namespace create "$BINDING" 2>&1 || true)"
  echo "$KV_OUT"
  KV_ID="$(echo "$KV_OUT" | grep -oE 'id = "[a-f0-9]+"' | head -1 | cut -d\" -f2 || true)"
  if [ -z "$KV_ID" ]; then
    KV_ID="$(npx wrangler kv namespace list 2>/dev/null | jq -r --arg n "$BINDING" '.[] | select(.title|endswith($n)) | .id' | head -1 || true)"
  fi
  echo "KV_${BINDING}_ID=$KV_ID" >> "$ENV_FILE"
done

# ---- R2 bucket ----
echo
echo "[3/8] R2 bucket"
run npx wrangler r2 bucket create unsearch-storage

# ---- Vectorize index ----
echo
echo "[4/8] Vectorize index"
run npx wrangler vectorize create unsearch-vectors --dimensions=1024 --metric=cosine

# ---- Queues ----
echo
echo "[5/8] Queues"
run npx wrangler queues create unsearch-tasks
run npx wrangler queues create unsearch-tasks-dlq

# ---- Analytics Engine dataset (auto-created on first write, but document it) ----
echo
echo "[6/8] Analytics Engine dataset 'unsearch_analytics' will be auto-created on first write."

# ---- Pages projects ----
echo
echo "[7/8] Pages projects"
run npx wrangler pages project create unsearch-web --production-branch=main --compatibility-date=2025-04-01
run npx wrangler pages project create unsearch-docs --production-branch=main --compatibility-date=2025-04-01

# ---- D1 schema ----
echo
echo "[8/8] Applying D1 schema"
if [ -n "$D1_ID" ]; then
  npx wrangler d1 execute unsearch-prod --remote --file=./schema.sql
else
  echo "WARN: D1_PROD_ID not captured; skipping schema apply. Run manually:"
  echo "      npx wrangler d1 execute unsearch-prod --remote --file=./schema.sql"
fi

echo
echo ">>> Done. Now update apps/workers/wrangler.toml with these IDs:"
cat "$ENV_FILE"
echo
echo ">>> Next: set secrets per environment (see apps/workers/SECRETS.md):"
echo "    npx wrangler secret put SECRET_KEY"
echo "    npx wrangler secret put STRIPE_SECRET_KEY"
echo "    npx wrangler secret put STRIPE_WEBHOOK_SECRET"
echo "    npx wrangler secret put RESEND_API_KEY"
echo "    npx wrangler secret put GOOGLE_CLIENT_SECRET"
echo "    npx wrangler secret put GITHUB_CLIENT_SECRET"
echo "    (full list in apps/workers/SECRETS.md)"
