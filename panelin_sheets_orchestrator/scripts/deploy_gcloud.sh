#!/usr/bin/env bash
set -euo pipefail

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
: "${GCP_REGION:?Set GCP_REGION (e.g. us-central1)}"

ARTIFACT_REPO="${ARTIFACT_REPO:-panelin}"
SERVICE_NAME="${SERVICE_NAME:-panelin-sheets-orchestrator}"
IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}"

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "==> Building image ${IMAGE}:latest ..."
gcloud builds submit \
  --project="$GCP_PROJECT_ID" \
  --tag="${IMAGE}:latest" \
  .

echo "==> Deploying to Cloud Run ..."
gcloud run deploy "$SERVICE_NAME" \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_REGION" \
  --image="${IMAGE}:latest" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="ENV=prod,GCP_PROJECT_ID=${GCP_PROJECT_ID}" \
  --set-secrets="OPENAI_API_KEY=panelin-orch-openai-api-key:latest,PANELIN_ORCH_API_KEY=panelin-orch-api-key:latest" \
  --memory=512Mi \
  --cpu=1 \
  --max-instances=5 \
  --timeout=180

echo "==> Deploy complete."
gcloud run services describe "$SERVICE_NAME" \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_REGION" \
  --format="value(status.url)"
