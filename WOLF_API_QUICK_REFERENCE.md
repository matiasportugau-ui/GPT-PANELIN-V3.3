# Wolf API Quick Reference

## 🎯 What is Wolf API?

FastAPI backend service for Panelin GPT Knowledge Base operations. Persists conversation data, corrections, and customer information to Google Cloud Storage.

**Location:** `wolf_api/` directory  
**Version:** 2.1.0  
**Status:** ✅ Implemented, ⏳ Awaiting first deployment

---

## 📂 Files

```
wolf_api/
├── main.py                          # FastAPI app (273 lines)
├── Dockerfile                       # Production image
├── requirements.txt                 # fastapi, uvicorn, google-cloud-storage
├── requirements-test.txt            # pytest, httpx
├── tests/
│   └── test_kb_conversations.py    # 10 tests (all passing)
├── README.md                        # Quick start
├── DEPLOYMENT.md                    # Complete deployment guide
└── IAM_SETUP.md                     # IAM permissions guide
```

---

## 🚀 Quick Start

### Local Development

```bash
cd wolf_api
pip install -r requirements.txt
export WOLF_API_KEY="your-key"
export KB_GCS_BUCKET="your-bucket"
uvicorn main:app --reload --port 8080
open http://localhost:8080/docs
```

### Run Tests

```bash
cd /home/runner/work/GPT-PANELIN-V3.3/GPT-PANELIN-V3.3
pytest wolf_api/tests/ -v
```

### Build Docker Image

```bash
cd wolf_api
docker build -t wolf-api .
docker run -p 8080:8080 -e WOLF_API_KEY=xxx -e KB_GCS_BUCKET=xxx wolf-api
```

---

## 🔌 API Endpoints

### Core Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | ❌ | API info |
| `/health` | GET | ❌ | Health check |
| `/ready` | GET | ❌ | Readiness |
| `/docs` | GET | ❌ | OpenAPI UI |
| `/openapi.json` | GET | ❌ | OpenAPI spec |

### KB Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/kb/conversations` | POST | ✅ X-API-Key | Persist conversation data |

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WOLF_API_KEY` | ✅ Yes | - | API key for auth |
| `KB_GCS_BUCKET` | ✅ Yes | - | GCS bucket name |
| `KB_GCS_PREFIX` | ❌ No | `kb/conversations` | Object prefix |
| `KB_GCS_MODE` | ❌ No | `daily_jsonl` | `daily_jsonl` or `per_event_jsonl` |
| `KB_GCS_MAX_RETRIES` | ❌ No | `5` | Max compose retries |

---

## 📦 Deployment

### GitHub Actions (Automated)

1. Configure GitHub Secrets (5 required)
2. Push to `wolf_api/` directory
3. Workflow auto-deploys to Cloud Run

**Workflow:** `.github/workflows/deploy-wolf-api.yml`

### Manual with gcloud

```bash
cd wolf_api

# Build image
gcloud builds submit --tag us-central1-docker.pkg.dev/chatbot-bmc-live/cloud-run-repo/wolf-api:latest

# Deploy
gcloud run deploy panelin-api \
  --region=us-central1 \
  --image=us-central1-docker.pkg.dev/chatbot-bmc-live/cloud-run-repo/wolf-api:latest \
  --service-account=wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com \
  --update-env-vars="WOLF_API_KEY=${WOLF_API_KEY},KB_GCS_BUCKET=${KB_GCS_BUCKET}"
```

---

## 🔐 IAM Setup (One-time)

### 1. Create GCS Bucket

```bash
gsutil mb -p chatbot-bmc-live -l us-central1 gs://panelin-kb-data
```

### 2. Create Service Accounts

```bash
gcloud iam service-accounts create wolf-api-runtime --project=chatbot-bmc-live
gcloud iam service-accounts create github-actions-deployer --project=chatbot-bmc-live
```

### 3. Grant Permissions

```bash
# Runtime SA → GCS
gsutil iam ch serviceAccount:wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://panelin-kb-data

# Deployment SA → Cloud Run
gcloud projects add-iam-policy-binding chatbot-bmc-live \
  --member="serviceAccount:github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

**Full guide:** `wolf_api/IAM_SETUP.md`

---

## 🧪 Testing

```bash
# Run all tests
pytest wolf_api/tests/ -v

# Run with coverage
pytest wolf_api/tests/ --cov=wolf_api --cov-report=term-missing

# Test deployed service
curl https://panelin-api-642127786762.us-central1.run.app/health
curl https://panelin-api-642127786762.us-central1.run.app/openapi.json | jq '.paths | keys'
```

---

## 🐛 Troubleshooting

### 401 Unauthorized
- Check `WOLF_API_KEY` matches request header
- Verify key is set in Cloud Run environment

### 503 Service Unavailable
- Missing `WOLF_API_KEY` or `KB_GCS_BUCKET` env var
- Redeploy with correct configuration

### 403 Forbidden (GCS)
- Runtime service account lacks GCS permissions
- Run: `gsutil iam get gs://your-bucket | grep wolf-api-runtime`
- Grant: `roles/storage.objectAdmin`

### 412 Precondition Failed
- Expected behavior in daily_jsonl mode
- Service retries automatically (up to 5 times)
- If persistent, consider switching to per_event_jsonl mode

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `wolf_api/README.md` | Quick start and API overview |
| `wolf_api/DEPLOYMENT.md` | Complete deployment guide (450 lines) |
| `wolf_api/IAM_SETUP.md` | IAM and service account setup (420 lines) |
| `WOLF_API_IMPLEMENTATION_SUMMARY.md` | Implementation details and architecture |

---

## 🔗 Related Files

- **MCP Client:** `panelin_mcp_integration/panelin_mcp_server.py` (line 252)
- **MCP Handler:** `mcp/handlers/wolf_kb_write.py`
- **MCP Tool Schema:** `mcp/tools/persist_conversation.json`
- **Workflow:** `.github/workflows/deploy-wolf-api.yml`

---

## ✅ Verification Checklist

After first deployment:

- [ ] Health endpoint responds: `/health`
- [ ] OpenAPI includes `/kb/conversations`: `/openapi.json`
- [ ] Test request succeeds with API key
- [ ] GCS objects created in bucket
- [ ] Cloud Run logs show no errors
- [ ] Service account has correct permissions

---

## 🎯 Next Steps

1. Complete IAM setup (service accounts, bucket, permissions)
2. Configure GitHub Secrets (5 required)
3. First manual deployment to verify
4. Enable automated deployments via GitHub Actions
5. Monitor production for errors
6. Implement additional KB endpoints (/kb/corrections, /kb/customers)

---

**Generated:** 2026-02-19  
**Author:** Copilot Agent  
**PR:** copilot/implement-post-kb-conversations
