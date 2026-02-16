#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${PANELIN_API_BASE_URL:-https://panelin-api-642127786762.us-central1.run.app}"
API_KEY="${WOLF_API_KEY:-${PANELIN_API_KEY:-}}"

# Validate API_KEY is set
if [[ -z "$API_KEY" ]]; then
  printf "ERROR: WOLF_API_KEY (or PANELIN_API_KEY) environment variable is not set.\n" >&2
  printf "Set it in your environment before running this script.\n" >&2
  printf "Example: export WOLF_API_KEY='your-key-here'\n" >&2
  exit 1
fi

# Create secure temp files
TMPDIR="${TMPDIR:-/tmp}"
HEALTH_RESP=$(mktemp "$TMPDIR/panelin_health.XXXXXX")
READY_RESP=$(mktemp "$TMPDIR/panelin_ready.XXXXXX")
FIND_RESP=$(mktemp "$TMPDIR/panelin_find.XXXXXX")
CURL_CONFIG=$(mktemp "$TMPDIR/panelin_curl.XXXXXX")

# Cleanup temp files on exit
trap 'rm -f "$HEALTH_RESP" "$READY_RESP" "$FIND_RESP" "$CURL_CONFIG"' EXIT

# Secure curl config file for API key
chmod 600 "$CURL_CONFIG"

printf "== Panelin API connection test ==\n"
printf "Base URL: %s\n" "$BASE_URL"

printf "\n[1/3] Health check (no auth) ...\n"
HEALTH_CODE=$(curl -sS --connect-timeout 10 --max-time 30 --retry 2 --retry-delay 1 \
  -o "$HEALTH_RESP" -w "%{http_code}" "$BASE_URL/health")
printf "HTTP %s\n" "$HEALTH_CODE"
cat "$HEALTH_RESP"; printf "\n"

printf "\n[2/3] Ready check (no auth) ...\n"
READY_CODE=$(curl -sS --connect-timeout 10 --max-time 30 --retry 2 --retry-delay 1 \
  -o "$READY_RESP" -w "%{http_code}" "$BASE_URL/ready")
printf "HTTP %s\n" "$READY_CODE"
cat "$READY_RESP"; printf "\n"

printf "\n[3/3] Authenticated endpoint /find_products ...\n"
# Write API key to secure curl config file
cat > "$CURL_CONFIG" <<CURL_CONFIG
header = "X-API-Key: $API_KEY"
CURL_CONFIG

FIND_CODE=$(curl -sS --connect-timeout 10 --max-time 30 --retry 2 --retry-delay 1 \
  -o "$FIND_RESP" -w "%{http_code}" \
  -X POST "$BASE_URL/find_products" \
  -H "Content-Type: application/json" \
  -K "$CURL_CONFIG" \
  -d '{"query":"precio isodec 100mm"}')
printf "HTTP %s\n" "$FIND_CODE"
cat "$FIND_RESP"; printf "\n"

if [[ "$HEALTH_CODE" != "200" || "$READY_CODE" != "200" ]]; then
  printf "\nConnection checks failed.\n" >&2
  exit 1
fi

if [[ "$FIND_CODE" != "200" ]]; then
  printf "\nAuthenticated test failed (check API key or endpoint permissions).\n" >&2
  exit 1
fi

printf "\nAll connection checks passed.\n"
