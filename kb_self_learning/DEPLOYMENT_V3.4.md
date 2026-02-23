# GPT Panel v3.4 - Deployment Guide
## Self-Learning Knowledge Base with Human Approval Workflow

### Release Information
- **Version**: 3.4
- **Release Date**: February 18, 2026
- **Branch**: `release/v3.4-self-learning`
- **Status**: Ready for Production Deployment (NOW)

---

## Architecture Overview

### Core Components
1. **KB Writer Service** (`kb_writer_service.py`)
- Handles KB entry submission and creation
- Stores entries in PostgreSQL with status "pending_approval"
- Entry ID generation and metadata management

2. **Approval Workflow** (`approval_workflow.py`)
- Manages human review queue for KB entries
- Supports approve/reject/request_revision operations
- Tracks approval history and statistics
- Email and Slack notifications for reviewers

3. **Configuration** (`config_v3.4.yaml`)
- PostgreSQL backend configuration (most efficient)
- Approval workflow settings (human approval required)
- Training loop parameters
- Security, monitoring, and deployment settings

---

## Quick Start Deployment

### Prerequisites
- Docker & Kubernetes
- PostgreSQL 13+
- GCP Project with Cloud Storage
- GitHub Actions access
- Slack webhook for notifications (optional)

### Environment Variables Required
```bash
# Database
KB_DB_HOST=your-postgres-host
KB_DB_PORT=5432
KB_DB_USER=kb_admin
KB_DB_PASSWORD=<secure-password>

# GCP
GCP_PROJECT_ID=your-gcp-project
KB_GCS_BUCKET=gpt-panel-kb
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# API
API_BASE_URL=https://api.gpt-panel.com
API_PORT=8000
JWT_SECRET=<secure-jwt-secret>

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
APPROVAL_NOTIFIERS=reviewer@company.com

# Security
CORS_ORIGINS=["https://gpt-panel.com"]
```

### Step 1: Database Setup (PostgreSQL)
```
# Create database
psql -U postgres -c "CREATE DATABASE gpt_panel_kb;"

# Run migrations
python3 kb_self_learning/kb_writer_service.py --migrate

# Initialize approval workflow tables
python3 kb_self_learning/approval_workflow.py --init-db
```

### Step 2: Deploy to Kubernetes
```
# Build Docker image
docker build -t gpt-panel:v3.4 .

# Push to registry
docker tag gpt-panel:v3.4 ${DOCKER_REGISTRY}/gpt-panel:v3.4
docker push ${DOCKER_REGISTRY}/gpt-panel:v3.4

# Deploy to Kubernetes
kubectl apply -f k8s/deployment-v3.4.yaml
kubectl apply -f k8s/service-v3.4.yaml
kubectl apply -f k8s/configmap-v3.4.yaml

# Verify deployment
kubectl get pods -n gpt-panel
kubectl logs -f deployment/gpt-panel-v3.4 -n gpt-panel
```

### Step 3: Health Checks
```
# Test KB writer endpoint
curl -X POST http://localhost:8000/api/v3.4/kb/write-entry \
-H "X-API-Key: ${API_KEY}" \
-H "Content-Type: application/json" \
-d '{
"topic": "test",
"content": "test entry",
"confidence_score": 0.95
}'

# Get pending approvals
curl http://localhost:8000/api/v3.4/approval/pending \
-H "X-API-Key: ${API_KEY}"

# Check approval stats
curl http://localhost:8000/api/v3.4/approval/stats \
-H "X-API-Key: ${API_KEY}"
```

---

## Self-Learning Workflow

### How It Works
1. **Model generates KB entry** during training
2. **Entry submitted** via `/api/v3.4/kb/write-entry` endpoint
3. **Entry stored** in PostgreSQL with status "pending_approval"
4. **Reviewer notified** via email/Slack
5. **Human approves/rejects** via approval dashboard
6. **If approved**: Entry written to persistent KB (GCS + PostgreSQL)
7. **If rejected**: Entry archived with rejection reason

### API Endpoints

#### Submit KB Entry for Approval
```

POST /api/v3.4/kb/write-entry
Content-Type: application/json

{
"topic": "feature_description",
"content": "detailed explanation",
"confidence_score": 0.85,
"tags": ["feature", "important"],
"metadata": {"source": "training_session_001"}
}

Response:
{
"status": "success",
"entry_id": "kb_2026-02-18T09:51:41.123456",
"message": "KB entry submitted for human approval"
}
```

#### Get Pending Approvals
```
GET /api/v3.4/approval/pending
Authorization: Bearer {JWT_TOKEN}

Response:
{
"status": "success",
"pending_count": 5,
"entries": [...]
}
```

#### Approve Entry
```
POST /api/v3.4/approval/approve/{entry_id}
Authorization: Bearer {JWT_TOKEN}

{
"reviewer": "reviewer@company.com",
"notes": "Looks good, approved for KB"
}

Response:
{
"status": "approved",
"entry_id": "kb_2026-02-18T09:51:41.123456",
"approved_at": "2026-02-18T09:52:00Z"
}
```

#### Reject Entry
```
POST /api/v3.4/approval/reject/{entry_id}
Authorization: Bearer {JWT_TOKEN}

{
"reviewer": "reviewer@company.com",
"reason": "Not accurate, needs revision"
}

Response:
{
"status": "rejected",
"entry_id": "kb_2026-02-18T09:51:41.123456",
"reason": "Not accurate, needs revision"
}
```

#### Get Approval Stats
```
GET /api/v3.4/approval/stats
Authorization: Bearer {JWT_TOKEN}

Response:
{
"status": "success",
"stats": {
"approved": 42,
"rejected": 3,
"pending": 5,
"total_processed": 45,
"approval_rate": 0.933
}
}
```

---

## Training Loop Integration

### Continuous Learning Configuration
Edit `config_v3.4.yaml`:
```
training:
enabled: true
continuous_learning: true

triggers:
- type: "conversation_completion"
threshold: 10  # Learn after every 10 conversations
- type: "scheduled"
schedule: "0 2 * * *"  # Daily at 2 AM
```

### Training Flow
1. Model processes conversations/interactions
2. Learns patterns and generates KB entries
3. Submits entries for approval
4. Awaits human review
5. Approved entries integrated into KB
6. KB index updated automatically
7. Next training cycle uses enhanced KB

---

## Monitoring & Logging

### Metrics Tracking
- KB entries submitted per day
- Approval rate (approved/total)
- Average approval time
- KB entries integrated per week
- Model accuracy improvements

### Log Locations
```
# Application logs
tail -f /var/log/gpt-panel/v3.4.log

# Kubernetes logs
kubectl logs -f deployment/gpt-panel-v3.4 -n gpt-panel --all-containers

# Database logs
psql -d gpt_panel_kb -c "SELECT * FROM kb_entries WHERE created_at > now() - interval '1 day';"
```

### Audit Trail
All KB modifications are logged with:
- Entry ID
- Submitter (AI model)
- Reviewer name
- Approval/rejection time
- Reason for rejection (if applicable)
- Timestamp

---

## Rollback Procedure

If issues occur after deployment:

```
# Scale down v3.4
kubectl scale deployment gpt-panel-v3.4 --replicas=0 -n gpt-panel

# Switch traffic to v3.3
kubectl patch service gpt-panel -p '{"spec":{"selector":{"version":"v3.3"}}}' -n gpt-panel

# Scale up v3.3
kubectl scale deployment gpt-panel-v3.3 --replicas=3 -n gpt-panel

# Investigate issues
kubectl logs -f deployment/gpt-panel-v3.4 -n gpt-panel

# Once fixed, re-deploy v3.4
kubectl scale deployment gpt-panel-v3.4 --replicas=3 -n gpt-panel
```

---

## Post-Deployment Checklist

- [ ] PostgreSQL database initialized
- [ ] All environment variables set
- [ ] Docker image built and pushed
- [ ] Kubernetes manifests deployed
- [ ] Health checks passing
- [ ] KB writer endpoint responding
- [ ] Approval endpoints accessible
- [ ] Slack/Email notifications working
- [ ] Monitoring dashboards visible
- [ ] Audit logging active
- [ ] Production traffic switched to v3.4

---

## Support & Documentation

- [ ] **API Documentation**: `/api/v3.4/docs` (Swagger UI)
- [ ] **Configuration Guide**: `config_v3.4.yaml`
- [ ] **Troubleshooting**: See `.github/TROUBLESHOOTING.md`
- [ ] **Team**: Reach out to GPT Panel team

---

- [ ] **Deployed**: February 18, 2026
- [ ] **Status**: ✅ Ready for Production
