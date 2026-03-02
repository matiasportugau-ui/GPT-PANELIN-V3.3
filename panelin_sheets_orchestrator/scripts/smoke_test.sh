#!/usr/bin/env bash
set -euo pipefail

: "${ORCH_URL:?Set ORCH_URL (Cloud Run service URL)}"
: "${PANELIN_ORCH_API_KEY:?Set PANELIN_ORCH_API_KEY}"

echo "==> Health check ..."
curl -sf "${ORCH_URL}/healthz" | python3 -m json.tool
echo ""

echo "==> Dry-run fill (expects 400 – template not found unless deployed) ..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${ORCH_URL}/v1/fill" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${PANELIN_ORCH_API_KEY}" \
  -d '{
    "job_id": "smoke-test-001",
    "template_id": "cotizacion_isodec_eps_v1",
    "spreadsheet_id": "FAKE_FOR_SMOKE_TEST",
    "payload": {"cliente": "Test"},
    "dry_run": true
  }')
echo "fill response HTTP code: ${HTTP_CODE}"

if [ "$HTTP_CODE" -eq 401 ]; then
  echo "ERROR: API key rejected."
  exit 1
fi

echo "==> Smoke test passed."
