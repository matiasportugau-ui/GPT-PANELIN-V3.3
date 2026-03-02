# Wolf API Deployment Guide

## Overview

The Wolf API is a FastAPI backend service that provides Knowledge Base write operations for the Panelin GPT Assistant. It implements the `/kb/conversations` endpoint with GCS persistence.

**Service Name:** `panelin-api`  
**Base URL:** `https://panelin-api-642127786762.us-central1.run.app`  
**Version:** 2.2.0

## Architecture

```
┌─────────────┐        ┌──────────────┐        ┌─────────────┐
│  MCP Client │───────▶│  Wolf API    │───────▶│  GCS Bucket │
│  (GPT)      │  POST  │  (FastAPI)   │ JSONL  │  (KB Data)  │
└─────────────┘        └──────────────┘        └─────────────┘
    X-API-Key           Service Account           IAM Roles
```

## Features

### Implemented
- ✅ POST `/kb/conversations` - Persist conversation summaries
- ✅ X-API-Key authentication
- ✅ GCS persistence with two modes:
  - `daily_jsonl`: Append to daily file using compose + preconditions
  - `per_event_jsonl`: Create separate file per event
- ✅ Atomic append with retry logic for race conditions
- ✅ Health and readiness endpoints
- ✅ OpenAPI documentation at `/docs`

### Planned
- 🔄 POST `/kb/corrections` - Register knowledge base corrections
- 🔄 POST `/kb/customers` - Save customer information
- 🔄 GET `/kb/customers/{id}` - Lookup customer information

## Prerequisites

### GCP Resources
1. **Cloud Run Service**: `panelin-api` in `us-central1`
2. **GCS Bucket**: For KB data storage
3. **Service Account**: With GCS write permissions
4. **Secrets**: `WOLF_API_KEY` and `KB_GCS_BUCKET`

### IAM Permissions
The Cloud Run service account needs:
- `roles/storage.objectCreator` on the GCS bucket (minimum)
- `roles/storage.objectAdmin` if using compose operations (recommended)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WOLF_API_KEY` | Yes | - | API key for authentication |
| `KB_GCS_BUCKET` | Yes | - | GCS bucket name for KB data |
| `KB_GCS_PREFIX` | No | `kb/conversations` | Prefix for GCS objects |
| `KB_GCS_MODE` | No | `daily_jsonl` | Persistence mode: `daily_jsonl` or `per_event_jsonl` |
| `KB_GCS_MAX_RETRIES` | No | `5` | Max retries for compose operations |
| `PORT` | No | `8080` | Server port |

## Deployment

### Option 1: GitHub Actions (Recommended)

The repository includes a GitHub Actions workflow at `.github/workflows/deploy-wolf-api.yml` that automatically deploys when changes are pushed to `wolf_api/`.

**Required Secrets:**
- `GCP_WIF_PROVIDER`: Workload Identity Federation provider
- `GCP_DEPLOY_SA_EMAIL`: Service account for deployment
- `GCP_RUNTIME_SA_EMAIL`: Service account for Cloud Run runtime
- `WOLF_API_KEY`: API key for authentication
- `KB_GCS_BUCKET`: GCS bucket name

**To deploy manually:**
```bash
git push origin main
```

The workflow will:
1. Authenticate to GCP via Workload Identity Federation
2. Build and push Docker image to Artifact Registry
3. Deploy to Cloud Run with environment variables
4. Output the service URL

### Option 2: Manual Deployment with gcloud

```bash
cd wolf_api

# Build and tag image
gcloud builds submit --tag us-central1-docker.pkg.dev/chatbot-bmc-live/cloud-run-repo/wolf-api:latest

# Deploy to Cloud Run
gcloud run deploy panelin-api \
  --project=chatbot-bmc-live \
  --region=us-central1 \
  --image=us-central1-docker.pkg.dev/chatbot-bmc-live/cloud-run-repo/wolf-api:latest \
  --service-account=wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com \
  --update-env-vars="WOLF_API_KEY=${WOLF_API_KEY},KB_GCS_BUCKET=${KB_GCS_BUCKET},KB_GCS_PREFIX=kb/conversations,KB_GCS_MODE=daily_jsonl,KB_GCS_MAX_RETRIES=5" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=60
```

**Important:** Use `--update-env-vars` (not `--set-env-vars`) to preserve existing environment variables.

### Option 3: Cloud Build

Update `cloudbuild.yaml` to include Wolf API deployment:

```yaml
# Add to existing cloudbuild.yaml
- name: 'gcr.io/cloud-builders/docker'
  id: 'build-wolf-api'
  args:
    - 'build'
    - '-t'
    - 'us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/wolf-api:$COMMIT_SHA'
    - '-t'
    - 'us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/wolf-api:latest'
    - './wolf_api'

- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'deploy-wolf-api'
  entrypoint: 'gcloud'
  args:
    - 'run'
    - 'deploy'
    - 'panelin-api'
    - '--image=us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/wolf-api:$COMMIT_SHA'
    - '--platform=managed'
    - '--region=us-central1'
    - '--allow-unauthenticated'
    - '--service-account=wolf-api-runtime@$PROJECT_ID.iam.gserviceaccount.com'
    - '--update-env-vars=WOLF_API_KEY=$$WOLF_API_KEY,KB_GCS_BUCKET=$$KB_GCS_BUCKET'
  secretEnv: ['WOLF_API_KEY', 'KB_GCS_BUCKET']
```

## Testing

### Run Unit Tests
```bash
cd wolf_api
pip install -r requirements.txt -r requirements-test.txt
PYTHONPATH=.. pytest tests/ -v
```

### Test Deployed Service

```bash
# Health check
curl https://panelin-api-642127786762.us-central1.run.app/health

# OpenAPI spec (verify /kb/conversations is present)
curl https://panelin-api-642127786762.us-central1.run.app/openapi.json | jq '.paths | keys'

# Test endpoint (requires API key)
curl -X POST https://panelin-api-642127786762.us-central1.run.app/kb/conversations \
  -H "X-API-Key: ${WOLF_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "test-client-123",
    "summary": "Test conversation",
    "quotation_ref": "Q-2026-001",
    "products_discussed": ["Panel BMC 20mm"]
  }'
```

Expected response:
```json
{
  "ok": true,
  "stored_at": "2026-02-19T00:00:00.000000+00:00",
  "gcs": {
    "ok": true,
    "bucket": "your-bucket-name",
    "object": "kb/conversations/daily/2026-02-19.jsonl",
    "attempts": 1,
    "mode": "daily_jsonl"
  }
}
```

## GCS Data Format

### Daily JSONL Mode (default)
Files are stored as `kb/conversations/daily/YYYY-MM-DD.jsonl`:

```jsonl
{"received_at":"2026-02-19T00:00:00.000000+00:00","type":"kb.conversation","data":{"client_id":"test-123","summary":"..."}}
{"received_at":"2026-02-19T01:00:00.000000+00:00","type":"kb.conversation","data":{"client_id":"test-456","summary":"..."}}
```

### Per-Event Mode
Each event creates a separate file: `kb/conversations/events/YYYYMMDDTHHMMss-uuid.jsonl`

## Troubleshooting

### 401 Unauthorized
**Cause:** Missing or invalid `X-API-Key` header  
**Solution:** Verify `WOLF_API_KEY` secret matches the key in requests

### 503 Service Unavailable
**Cause:** `WOLF_API_KEY` or `KB_GCS_BUCKET` environment variable not set  
**Solution:** Redeploy with proper environment variables

### 403 Forbidden (GCS)
**Cause:** Service account lacks permissions on GCS bucket  
**Solution:** Grant `roles/storage.objectAdmin` to the runtime service account:
```bash
gsutil iam ch serviceAccount:wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://your-bucket-name
```

### 412 Precondition Failed
**Cause:** Race condition in concurrent compose operations (expected behavior)  
**Solution:** The service automatically retries (up to `KB_GCS_MAX_RETRIES` times)

### OpenAPI doesn't show /kb/conversations
**Cause:** Old version deployed or deployment failed  
**Solution:** 
1. Check Cloud Run service revision
2. Verify deployment logs
3. Force new deployment

## Monitoring

### Cloud Run Metrics
- Request count
- Request latency
- Error rate
- Instance count

### Logs
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=panelin-api" \
  --project=chatbot-bmc-live \
  --limit=50 \
  --format=json

# Filter for errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=panelin-api AND severity>=ERROR" \
  --project=chatbot-bmc-live \
  --limit=20
```

## Security Considerations

1. **API Key Storage**: Store `WOLF_API_KEY` in Secret Manager, not in code
2. **Constant-Time Comparison**: API key validation uses `hmac.compare_digest()` to prevent timing attacks
3. **Service Account**: Use dedicated service account with minimal permissions
4. **Authentication**: All KB write endpoints require `X-API-Key` header
5. **IAM**: Follow principle of least privilege for GCS access

## Performance

- **Cold Start**: ~2-3 seconds (Python 3.11-slim base)
- **Request Latency**: 
  - Health check: ~10ms
  - KB conversations (daily mode): ~200-500ms (includes GCS operations)
  - KB conversations (per-event mode): ~100-200ms
- **Concurrency**: Up to 10 instances (configurable)
- **Memory**: 512Mi (sufficient for current operations)

## Cost Considerations

### Persistence Mode Comparison

**Daily JSONL (compose):**
- Pros: Single file per day, easier to consume
- Cons: Higher latency, compose API costs, more complex retry logic
- Best for: Low-medium volume (<1000 events/day)

**Per-Event JSONL:**
- Pros: Simple, no concurrency issues, predictable costs
- Cons: Many small files, requires aggregation for analysis
- Best for: High volume, simpler operations, reliability

**Recommendation:** Start with `per_event_jsonl` for operational simplicity, migrate to `daily_jsonl` if file count becomes an issue.

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Storage Compose](https://cloud.google.com/storage/docs/composing-objects)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
