# Wolf API IAM Setup Guide

This guide covers the IAM permissions and service account setup required for Wolf API deployment to Cloud Run.

## Overview

The Wolf API requires two service accounts:
1. **Deployment Service Account**: Used by GitHub Actions to deploy to Cloud Run
2. **Runtime Service Account**: Used by Cloud Run to access GCS

## Prerequisites

- GCP project: `chatbot-bmc-live`
- GCP region: `us-central1`
- GCS bucket for KB data (create if not exists)
- GitHub repository with Workload Identity Federation configured

## Step 1: Create GCS Bucket

```bash
# Create bucket for KB data
gsutil mb -p chatbot-bmc-live -l us-central1 gs://panelin-kb-data

# Verify bucket
gsutil ls -p chatbot-bmc-live | grep panelin-kb-data
```

## Step 2: Create Runtime Service Account

```bash
# Create service account for Cloud Run runtime
gcloud iam service-accounts create wolf-api-runtime \
  --display-name="Wolf API Runtime Service Account" \
  --project=chatbot-bmc-live

# Verify
gcloud iam service-accounts list --project=chatbot-bmc-live | grep wolf-api-runtime
```

## Step 3: Grant GCS Permissions to Runtime SA

The runtime service account needs permissions to write to GCS:

```bash
# Grant Storage Object Admin role (allows compose operations)
gsutil iam ch serviceAccount:wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://panelin-kb-data

# Verify permissions
gsutil iam get gs://panelin-kb-data
```

**Alternative (Minimum Permissions):**
If you only need create operations (per-event mode), use:
```bash
gsutil iam ch serviceAccount:wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com:roles/storage.objectCreator \
  gs://panelin-kb-data
```

**Note:** For `daily_jsonl` mode with compose, `objectAdmin` is required.

## Step 4: Create Deployment Service Account (GitHub Actions)

```bash
# Create service account for GitHub Actions deployment
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer" \
  --project=chatbot-bmc-live

# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding chatbot-bmc-live \
  --member="serviceAccount:github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Grant Service Account User role (to assign runtime SA)
gcloud projects add-iam-policy-binding chatbot-bmc-live \
  --member="serviceAccount:github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Grant Artifact Registry Writer role
gcloud projects add-iam-policy-binding chatbot-bmc-live \
  --member="serviceAccount:github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

## Step 5: Set Up Workload Identity Federation

If not already configured, set up Workload Identity Federation for GitHub Actions:

```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="chatbot-bmc-live" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="chatbot-bmc-live" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow GitHub repository to impersonate the deployer service account
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com \
  --project=chatbot-bmc-live \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/matiasportugau-ui/GPT-PANELIN-V3.3"
```

**Replace `PROJECT_NUMBER` with your actual project number:**
```bash
gcloud projects describe chatbot-bmc-live --format="value(projectNumber)"
```

## Step 6: Configure GitHub Secrets

Add the following secrets to your GitHub repository (Settings > Secrets and variables > Actions):

1. **GCP_WIF_PROVIDER**
   ```
   projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
   ```

2. **GCP_DEPLOY_SA_EMAIL**
   ```
   github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com
   ```

3. **GCP_RUNTIME_SA_EMAIL**
   ```
   wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com
   ```

4. **WOLF_API_KEY**
   ```
   <your-secure-api-key>
   ```
   Generate a strong random key:
   ```bash
   openssl rand -base64 32
   ```

5. **KB_GCS_BUCKET**
   ```
   panelin-kb-data
   ```

## Step 7: Verify IAM Setup

```bash
# Check runtime SA has GCS permissions
gcloud projects get-iam-policy chatbot-bmc-live \
  --flatten="bindings[].members" \
  --filter="bindings.members:wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com"

# Check deployer SA has Cloud Run permissions
gcloud projects get-iam-policy chatbot-bmc-live \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com"
```

## Step 8: Test Deployment

Trigger a deployment:

```bash
# Push to main to trigger workflow
git push origin main

# Or manually trigger
gh workflow run deploy-wolf-api.yml
```

Monitor deployment:
```bash
# View workflow logs
gh run list --workflow=deploy-wolf-api.yml

# View Cloud Run service
gcloud run services describe panelin-api \
  --region=us-central1 \
  --project=chatbot-bmc-live
```

## Troubleshooting

### Error: Permission Denied (403) on GCS

**Symptoms:** API returns 403 when trying to write to GCS

**Solutions:**
1. Verify runtime SA has correct bucket permissions:
   ```bash
   gsutil iam get gs://panelin-kb-data | grep wolf-api-runtime
   ```

2. Ensure Cloud Run service is using the correct service account:
   ```bash
   gcloud run services describe panelin-api \
     --region=us-central1 \
     --project=chatbot-bmc-live \
     --format="value(spec.template.spec.serviceAccountName)"
   ```

3. Grant missing permissions:
   ```bash
   gsutil iam ch serviceAccount:wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com:roles/storage.objectAdmin \
     gs://panelin-kb-data
   ```

### Error: GitHub Actions Cannot Deploy

**Symptoms:** Workflow fails with authentication or permission errors

**Solutions:**
1. Verify Workload Identity Federation setup:
   ```bash
   gcloud iam workload-identity-pools describe github-pool \
     --location=global \
     --project=chatbot-bmc-live
   ```

2. Check service account binding:
   ```bash
   gcloud iam service-accounts get-iam-policy \
     github-actions-deployer@chatbot-bmc-live.iam.gserviceaccount.com \
     --project=chatbot-bmc-live
   ```

3. Verify GitHub secrets are set correctly

### Error: Service Account Not Found

**Symptoms:** Deployment fails with "service account not found"

**Solution:**
Create the runtime service account and grant permissions (Steps 2-3)

### Error: Bucket Not Found

**Symptoms:** 503 error, logs show "KB_GCS_BUCKET is missing" or bucket not found

**Solutions:**
1. Create the bucket (Step 1)
2. Verify KB_GCS_BUCKET secret is set correctly
3. Check bucket name in Cloud Run environment variables:
   ```bash
   gcloud run services describe panelin-api \
     --region=us-central1 \
     --project=chatbot-bmc-live \
     --format="value(spec.template.spec.containers[0].env)"
   ```

## Security Best Practices

1. **Principle of Least Privilege**: Grant only necessary permissions
2. **Service Account Keys**: Never use JSON keys; use Workload Identity Federation
3. **API Key Rotation**: Rotate WOLF_API_KEY periodically
4. **Bucket Policy**: Consider bucket-level policies for additional security
5. **Audit Logging**: Enable Cloud Audit Logs for GCS and Cloud Run
6. **Secret Management**: Store WOLF_API_KEY in Secret Manager (optional enhancement)

## Optional: Store API Key in Secret Manager

For enhanced security, store the API key in Secret Manager:

```bash
# Create secret
echo -n "your-api-key" | gcloud secrets create wolf-api-key \
  --project=chatbot-bmc-live \
  --data-file=-

# Grant access to runtime SA
gcloud secrets add-iam-policy-binding wolf-api-key \
  --member="serviceAccount:wolf-api-runtime@chatbot-bmc-live.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=chatbot-bmc-live

# Update Cloud Run to mount secret
gcloud run services update panelin-api \
  --update-secrets=WOLF_API_KEY=wolf-api-key:latest \
  --region=us-central1 \
  --project=chatbot-bmc-live
```

## Summary

After completing these steps, you will have:

✅ GCS bucket for KB data storage  
✅ Runtime service account with GCS write permissions  
✅ Deployment service account with Cloud Run admin permissions  
✅ Workload Identity Federation configured for GitHub Actions  
✅ GitHub secrets configured for automated deployment  
✅ Secure API key management  

The Wolf API is now ready for automated deployment via GitHub Actions!
