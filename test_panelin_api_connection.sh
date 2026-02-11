#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${PANELIN_API_BASE_URL:-https://panelin-api-642127786762.us-central1.run.app}"
API_KEY="${WOLF_API_KEY:-${PANELIN_API_KEY:-}}"

printf "== Panelin API connection test ==\n"
printf "Base URL: %s\n" "$BASE_URL"

printf "\n[1/3] Health check (no auth) ...\n"
HEALTH_CODE=$(curl -sS -o /tmp/panelin_health.json -w "%{http_code}" "$BASE_URL/health")
printf "HTTP %s\n" "$HEALTH_CODE"
cat /tmp/panelin_health.json; printf "\n"

printf "\n[2/3] Ready check (no auth) ...\n"
READY_CODE=$(curl -sS -o /tmp/panelin_ready.json -w "%{http_code}" "$BASE_URL/ready")
printf "HTTP %s\n" "$READY_CODE"
cat /tmp/panelin_ready.json; printf "\n"

if [[ -z "$API_KEY" ]]; then
  printf "\n[3/3] Authenticated tests skipped: set WOLF_API_KEY (or PANELIN_API_KEY).\n"
  exit 0
fi

printf "\n[3/3] Authenticated endpoint /find_products ...\n"
FIND_CODE=$(curl -sS -o /tmp/panelin_find_products.json -w "%{http_code}" \
  -X POST "$BASE_URL/find_products" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query":"precio isodec 100mm"}')
printf "HTTP %s\n" "$FIND_CODE"
cat /tmp/panelin_find_products.json; printf "\n"

if [[ "$HEALTH_CODE" != "200" || "$READY_CODE" != "200" ]]; then
  printf "\nConnection checks failed.\n" >&2
  exit 1
fi

if [[ "$FIND_CODE" != "200" ]]; then
  printf "\nAuthenticated test failed (check API key or endpoint permissions).\n" >&2
  exit 1
fi

printf "\nAll connection checks passed.\n"
