# GCP Deployment Guide - Panelin Web Application

This guide provides comprehensive instructions for deploying the Panelin application on Google Cloud Platform (GCP) using Cloud Run, Cloud SQL, and automated CI/CD with Cloud Build.

---

## 📋 Table of Contents

- [Introduction](#introduction)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Infrastructure Deployment with Terraform](#infrastructure-deployment-with-terraform)
- [CI/CD Pipeline with Cloud Build](#cicd-pipeline-with-cloud-build)
- [Application Usage](#application-usage)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

---

## 🎯 Introduction

This deployment architecture provides a scalable, secure, and easily updatable web application on Google Cloud Platform. The application consists of:

- **Frontend Service**: Flask-based web interface that communicates with the backend
- **Backend Service**: Flask API that connects to Cloud SQL PostgreSQL database
- **Cloud SQL**: Managed PostgreSQL database for persistent data storage
- **Secret Manager**: Secure storage for database credentials and sensitive configuration
- **Artifact Registry**: Private Docker registry for container images
- **Cloud Build**: Automated CI/CD pipeline triggered by GitHub changes
- **Cloud Run**: Serverless container platform for running the services

---

## 🏗️ Architecture

### Component Overview

```
┌──────────────────────────────────────────────────────────┐
│                     GitHub Repository                      │
│                  (Source Code & Changes)                   │
└────────────────────┬─────────────────────────────────────┘
                     │ Push/Commit
                     ↓
┌──────────────────────────────────────────────────────────┐
│                      Cloud Build                          │
│   • Build Docker Images                                   │
│   • Push to Artifact Registry                            │
│   • Deploy to Cloud Run                                  │
└────────────────────┬─────────────────────────────────────┘
                     │ Deploy
                     ↓
┌──────────────────────────────────────────────────────────┐
│                   Global Load Balancer                    │
│              (Public HTTPS Access Point)                  │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────────┐
│                 Frontend Service (Cloud Run)              │
│   • Flask Web Application                                │
│   • Internal networking to backend                       │
│   • Health checks on /health                             │
└────────────────────┬─────────────────────────────────────┘
                     │ Internal HTTP
                     ↓
┌──────────────────────────────────────────────────────────┐
│                 Backend Service (Cloud Run)               │
│   • Flask API Application                                │
│   • Connects to Cloud SQL via Unix socket               │
│   • Reads secrets from Secret Manager                   │
│   • Health checks on /health                             │
└────────────────────┬─────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
┌──────────────────┐    ┌──────────────────┐
│  Cloud SQL       │    │ Secret Manager   │
│  PostgreSQL 16   │    │ (DB Credentials) │
│  Database        │    │                  │
└──────────────────┘    └──────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Flask (Python 3.9) | Web interface and API consumer |
| Backend | Flask (Python 3.9) | API server and database interface |
| Database | Cloud SQL PostgreSQL 16 | Persistent data storage |
| Container Runtime | Cloud Run | Serverless container execution |
| CI/CD | Cloud Build | Automated deployment pipeline |
| Registry | Artifact Registry | Private Docker image storage |
| Secrets | Secret Manager | Secure credential management |
| Networking | VPC/Load Balancer | Secure internal communication |

---

## ✅ Prerequisites

### Required Tools

Before starting, ensure you have the following installed:

1. **Google Cloud SDK (gcloud)**: [Installation Guide](https://cloud.google.com/sdk/docs/install)
2. **Terraform** (v1.0+): [Installation Guide](https://developer.hashicorp.com/terraform/downloads)
3. **Git**: For repository management
4. **Docker** (optional): For local testing

### GCP Project Requirements

1. **GCP Account**: Active Google Cloud Platform account
2. **Billing Enabled**: Billing must be enabled on your GCP project
3. **Project ID**: Note your GCP project ID (e.g., `my-panelin-project`)
4. **Sufficient Permissions**: You need the following roles:
   - Project Owner or Editor
   - Service Account Admin
   - Cloud Build Editor
   - Secret Manager Admin

### API Quotas

Ensure your project has sufficient quotas for:
- Cloud Run services (minimum 2 services)
- Cloud SQL instances (1 instance)
- Cloud Build concurrent builds (minimum 1)

---

## 🚀 Initial Setup

### Step 1: Authenticate with GCP

```bash
# Login to Google Cloud
gcloud auth login

# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable Application Default Credentials for Terraform
gcloud auth application-default login
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3.git
cd GPT-PANELIN-V3.3
```

### Step 3: Configure Environment Variables

Create a `terraform.tfvars` file in the `terraform/` directory:

```bash
cat > terraform/terraform.tfvars <<EOF
project_id       = "your-project-id"
region          = "us-central1"
db_root_password = "your-secure-password-here"
EOF
```

**⚠️ Security Note**: Never commit `terraform.tfvars` to version control. It's already included in `.gitignore`.

---

## 🏗️ Infrastructure Deployment with Terraform

### Step 1: Initialize Terraform

```bash
cd terraform
terraform init
```

This command downloads the required provider plugins (Google Cloud Provider).

### Step 2: Review the Infrastructure Plan

```bash
terraform plan
```

Review the resources that will be created:
- Service accounts and IAM roles
- Cloud SQL PostgreSQL instance
- Secret Manager secrets
- Artifact Registry repository
- API enablement

### Step 3: Apply the Infrastructure

```bash
terraform apply
```

Type `yes` when prompted. This process takes approximately 5-10 minutes.

### Step 4: Capture Important Outputs

After successful deployment, note the outputs:

```bash
terraform output
```

You'll see:
- `cloud_sql_connection_name`: Connection string for Cloud SQL
- `db_secret_name`: Name of the database secret
- `artifact_registry_repo_name`: Docker repository name
- `cloud_run_service_account_email`: Service account email

Save these values for reference.

---

## 🔄 CI/CD Pipeline with Cloud Build

### Pipeline Overview

The Cloud Build pipeline (`cloudbuild.yaml`) automates:

1. **Build**: Creates Docker images for frontend and backend
2. **Push**: Uploads images to Artifact Registry
3. **Deploy**: Deploys services to Cloud Run with proper configuration

### Step 1: Connect GitHub Repository to Cloud Build

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click **"Create Trigger"**
3. Configure the trigger:
   - **Name**: `deploy-on-push`
   - **Event**: Push to a branch
   - **Repository**: Connect your GitHub repository
   - **Branch**: `^main$` (or your preferred branch)
   - **Configuration**: Cloud Build configuration file (`cloudbuild.yaml`)
4. Click **"Create"**

### Step 2: Grant Cloud Build Permissions

```bash
# Grant Cloud Build service account necessary permissions
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/run.admin

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser
```

### Step 3: Test the Pipeline

Trigger the pipeline manually or push a commit:

```bash
# Manual trigger from Cloud Build UI
# Or push a commit to trigger automatically
git add .
git commit -m "Initial deployment"
git push origin main
```

Monitor the build progress:
```bash
gcloud builds list --limit=5
```

Or view in the [Cloud Build Console](https://console.cloud.google.com/cloud-build/builds).

### Step 4: Update Backend Service URL

After the backend is deployed, you need to update the frontend with the actual backend URL:

```bash
# Get the backend service URL
BACKEND_URL=$(gcloud run services describe backend-service \
    --region=us-central1 \
    --format='value(status.url)')

echo "Backend URL: $BACKEND_URL"

# Update the cloudbuild.yaml file to use this URL instead of the placeholder
# Edit line 72 in cloudbuild.yaml:
#   '--set-env-vars=BACKEND_SERVICE_URL=$BACKEND_URL'
```

Then redeploy the frontend or update it manually:

```bash
gcloud run services update frontend-service \
    --region=us-central1 \
    --set-env-vars=BACKEND_SERVICE_URL=$BACKEND_URL
```

---

## 🌐 Application Usage

### Accessing the Application

#### Option 1: Direct Cloud Run Access (with authentication)

Get the service URLs:

```bash
# Frontend URL
FRONTEND_URL=$(gcloud run services describe frontend-service \
    --region=us-central1 \
    --format='value(status.url)')

echo "Frontend URL: $FRONTEND_URL"

# Backend URL  
BACKEND_URL=$(gcloud run services describe backend-service \
    --region=us-central1 \
    --format='value(status.url)')

echo "Backend URL: $BACKEND_URL"
```

Access with authentication:

```bash
# Get an identity token
TOKEN=$(gcloud auth print-identity-token)

# Access the frontend
curl -H "Authorization: Bearer $TOKEN" $FRONTEND_URL

# Access the backend API
curl -H "Authorization: Bearer $TOKEN" $BACKEND_URL/api/data
```

#### Option 2: Configure Public Access (Production Setup)

For production deployment with public access:

1. **Enable unauthenticated access** (if needed):

```bash
gcloud run services add-iam-policy-binding frontend-service \
    --region=us-central1 \
    --member="allUsers" \
    --role="roles/run.invoker"
```

2. **Set up Global Load Balancer** (recommended for production):
   - Follow [Cloud Load Balancing with Cloud Run](https://cloud.google.com/load-balancing/docs/https/setup-global-ext-https-serverless)
   - Configure SSL certificates for HTTPS
   - Set up custom domain

### API Endpoints

#### Frontend Service

- `GET /` - Main page, fetches and displays backend data
  - Returns: JSON with backend response
  - Status codes: 200 (success), 503 (backend unavailable), 504 (timeout)

- `GET /health` - Health check endpoint
  - Returns: `{"status": "healthy", "service": "frontend"}`

#### Backend Service

- `GET /api/data` - Database query endpoint
  - Returns: JSON with database version and sample data
  - Creates test table and data on first access

- `GET /health` - Health check endpoint
  - Returns: `{"status": "healthy", "service": "backend"}`

### Testing the Deployment

```bash
# Test frontend health
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    $(gcloud run services describe frontend-service --region=us-central1 --format='value(status.url)')/health

# Test backend health
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    $(gcloud run services describe backend-service --region=us-central1 --format='value(status.url)')/health

# Test full integration (frontend -> backend -> database)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    $(gcloud run services describe frontend-service --region=us-central1 --format='value(status.url)')
```

---

## 📊 Monitoring and Maintenance

### Viewing Logs

#### Cloud Run Logs

```bash
# Frontend logs
gcloud run services logs read frontend-service --region=us-central1 --limit=50

# Backend logs
gcloud run services logs read backend-service --region=us-central1 --limit=50
```

Or use [Cloud Logging Console](https://console.cloud.google.com/logs).

#### Cloud Build Logs

```bash
# View recent builds
gcloud builds list --limit=10

# View specific build logs
gcloud builds log <BUILD_ID>
```

### Monitoring Metrics

Access [Cloud Monitoring](https://console.cloud.google.com/monitoring) to view:
- Request count and latency
- Error rates
- Container instance count
- CPU and memory utilization

### Database Management

#### Connect to Cloud SQL

```bash
# Using Cloud SQL Proxy
cloud_sql_proxy -instances=$PROJECT_ID:us-central1:web-app-db=tcp:5432

# In another terminal, connect with psql
psql -h 127.0.0.1 -U postgres -d app_database
```

#### Database Backups

Backups are automatically configured to run daily at 3 AM UTC. To create a manual backup:

```bash
gcloud sql backups create \
    --instance=web-app-db \
    --project=$PROJECT_ID
```

### Updating the Application

1. Make code changes in the repository
2. Commit and push to the configured branch:
   ```bash
   git add .
   git commit -m "Your update description"
   git push origin main
   ```
3. Cloud Build automatically builds and deploys the new version
4. Monitor the deployment in Cloud Build console

### Rolling Back

If you need to rollback to a previous version:

```bash
# List revisions
gcloud run revisions list --service=frontend-service --region=us-central1

# Route traffic to previous revision
gcloud run services update-traffic frontend-service \
    --region=us-central1 \
    --to-revisions=<REVISION_NAME>=100
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Cloud Build Fails to Deploy

**Error**: "Permission denied" or "Service account does not have permissions"

**Solution**:
```bash
# Grant necessary permissions to Cloud Build service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/run.admin

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser
```

#### 2. Backend Cannot Connect to Cloud SQL

**Error**: "Could not connect to database"

**Solution**:
- Verify Cloud SQL instance is running: `gcloud sql instances list`
- Check that Cloud SQL connection is properly configured in Cloud Run
- Verify service account has `cloudsql.client` role
- Check environment variables are set correctly

#### 3. Frontend Cannot Reach Backend

**Error**: "Cannot connect to backend service"

**Solution**:
- Verify backend URL is correct in frontend environment variables
- Check that backend service allows internal traffic
- Verify service account has `run.invoker` role
- Use backend's internal URL format for service-to-service communication

#### 4. Terraform Apply Fails

**Error**: API not enabled or quota exceeded

**Solution**:
```bash
# Enable required APIs manually
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Check quotas in Cloud Console
```

### Debugging Tips

1. **Check Service Logs**: Always start by checking logs
   ```bash
   gcloud run services logs read <SERVICE_NAME> --region=us-central1
   ```

2. **Test Health Endpoints**: Verify services are responding
   ```bash
   curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <SERVICE_URL>/health
   ```

3. **Verify Environment Variables**: Check that all required env vars are set
   ```bash
   gcloud run services describe <SERVICE_NAME> --region=us-central1
   ```

4. **Check IAM Permissions**: Verify service accounts have necessary roles
   ```bash
   gcloud projects get-iam-policy $PROJECT_ID
   ```

---

## 💰 Cost Optimization

### Estimated Monthly Costs

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Cloud Run (2 services) | 1M requests, 10 GB-hours | $5-10 |
| Cloud SQL (db-f1-micro) | 30 days continuous | $7-15 |
| Cloud Build | 30 builds/month | Free tier |
| Artifact Registry | <10 GB storage | $0.10 |
| Secret Manager | <10 secrets | $0.06 |
| **Total** | | **~$12-25/month** |

### Cost Reduction Tips

1. **Use smaller Cloud SQL instances**: Switch to `db-f1-micro` for development
2. **Enable autoscaling**: Configure min instances to 0 for Cloud Run services
3. **Optimize container images**: Use smaller base images, multi-stage builds
4. **Schedule database backups**: Reduce backup frequency if not needed
5. **Use Cloud SQL proxy**: Avoid public IP to save costs
6. **Monitor usage**: Set up budget alerts in GCP Console

### Production Scaling

For production workloads, consider:
- Increase Cloud SQL instance size based on load
- Configure Cloud Run max instances based on traffic patterns
- Enable Cloud CDN for static content caching
- Use Cloud Armor for DDoS protection
- Implement Cloud Monitoring alerting

---

## 📚 Additional Resources

### Documentation

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

### Best Practices

- [Cloud Run Best Practices](https://cloud.google.com/run/docs/best-practices)
- [Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)

### Support

- [GCP Support](https://cloud.google.com/support)
- [Stack Overflow - Google Cloud Platform](https://stackoverflow.com/questions/tagged/google-cloud-platform)
- [GCP Community](https://www.googlecloudcommunity.com/)

---

## 📝 Summary

This deployment guide covered:

✅ Complete GCP architecture overview  
✅ Infrastructure as Code with Terraform  
✅ Automated CI/CD with Cloud Build  
✅ Service deployment to Cloud Run  
✅ Database management with Cloud SQL  
✅ Secure credential management  
✅ Monitoring and troubleshooting  
✅ Cost optimization strategies  

Your Panelin application is now deployed on a scalable, secure, and maintainable Google Cloud Platform infrastructure!

---

**Last Updated**: 2024  
**Version**: 1.0  
**Maintainer**: Panelin Development Team
