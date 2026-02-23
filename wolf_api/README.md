# Wolf API - Panelin Knowledge Base Backend

FastAPI backend service for Panelin GPT Assistant Knowledge Base operations.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-test.txt

# Set environment variables
export WOLF_API_KEY="your-api-key"
export KB_GCS_BUCKET="your-gcs-bucket"

# Run server
uvicorn main:app --reload --port 8080

# View docs
open http://localhost:8080/docs
```

### Docker

```bash
# Build image
docker build -t wolf-api .

# Run container
docker run -p 8080:8080 \
  -e WOLF_API_KEY="your-api-key" \
  -e KB_GCS_BUCKET="your-bucket" \
  wolf-api

# Test
curl http://localhost:8080/health
```

## API Endpoints

### Core Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /docs` - OpenAPI documentation
- `GET /openapi.json` - OpenAPI spec

### Knowledge Base Endpoints

#### POST /kb/conversations

Persist conversation summary to Knowledge Base.

**Authentication:** X-API-Key header required

**Request Body:**
```json
{
  "client_id": "client-123",
  "summary": "Discussed panel installation options",
  "quotation_ref": "Q-2026-001",
  "products_discussed": ["Panel BMC 20mm", "Panel BMC 30mm"],
  "date": "2026-02-19T00:00:00Z"
}
```

**Response:**
```json
{
  "ok": true,
  "stored_at": "2026-02-19T00:00:00.000000+00:00",
  "gcs": {
    "ok": true,
    "bucket": "your-bucket",
    "object": "kb/conversations/daily/2026-02-19.jsonl",
    "attempts": 1,
    "mode": "daily_jsonl"
  }
}
```

## Configuration

Environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WOLF_API_KEY` | Yes | - | API authentication key |
| `KB_GCS_BUCKET` | Yes | - | GCS bucket for data storage |
| `KB_GCS_PREFIX` | No | `kb/conversations` | Object prefix in GCS |
| `KB_GCS_MODE` | No | `daily_jsonl` | Storage mode: `daily_jsonl` or `per_event_jsonl` |
| `KB_GCS_MAX_RETRIES` | No | `5` | Max retries for compose operations |
| `PORT` | No | `8080` | Server port |

## Storage Modes

### daily_jsonl (default)
Appends to a single daily file using GCS compose with preconditions. Best for moderate volume with easy consumption.

```
kb/conversations/daily/2026-02-19.jsonl
kb/conversations/daily/2026-02-20.jsonl
```

### per_event_jsonl
Creates one file per event. Best for high volume and operational simplicity.

```
kb/conversations/events/20260219T120000-abc123.jsonl
kb/conversations/events/20260219T120030-def456.jsonl
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=term-missing

# Run specific test
pytest tests/test_kb_conversations.py::test_kb_conversations_success_daily_mode -v
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions including:
- GitHub Actions workflow
- Manual gcloud deployment
- Cloud Build integration
- IAM permissions setup
- Troubleshooting guide

## Architecture

```
┌─────────────────┐
│   MCP Client    │
│   (GPT Agent)   │
└────────┬────────┘
         │ POST /kb/conversations
         │ X-API-Key: xxx
         ▼
┌─────────────────┐
│   Wolf API      │
│   (FastAPI)     │
│  - Auth check   │
│  - Validation   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   GCS Bucket    │
│   JSONL files   │
│  - Compose ops  │
│  - Preconditions│
└─────────────────┘
```

## Security

- **Authentication**: X-API-Key header with constant-time comparison
- **Authorization**: Service account with minimal GCS permissions
- **Secrets**: WOLF_API_KEY stored in Secret Manager
- **Transport**: HTTPS only (enforced by Cloud Run)

## License

See main repository LICENSE file.
