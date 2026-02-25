#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY}"
: "${PANELIN_ORCH_API_KEY:?Set PANELIN_ORCH_API_KEY}"

echo "Creating/updating secrets in project ${GCP_PROJECT_ID} ..."

printf "%s" "$OPENAI_API_KEY" | \
  gcloud secrets versions add panelin-orch-openai-api-key \
    --project="$GCP_PROJECT_ID" --data-file=- 2>/dev/null || \
  printf "%s" "$OPENAI_API_KEY" | \
  gcloud secrets create panelin-orch-openai-api-key \
    --project="$GCP_PROJECT_ID" --data-file=-

printf "%s" "$PANELIN_ORCH_API_KEY" | \
  gcloud secrets versions add panelin-orch-api-key \
    --project="$GCP_PROJECT_ID" --data-file=- 2>/dev/null || \
  printf "%s" "$PANELIN_ORCH_API_KEY" | \
  gcloud secrets create panelin-orch-api-key \
    --project="$GCP_PROJECT_ID" --data-file=-

echo "Done. Verify with: gcloud secrets list --project=${GCP_PROJECT_ID}"
