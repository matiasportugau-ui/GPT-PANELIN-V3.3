# GPT-PANELIN V3.3 - Deployment Checklist

**Complete checklist for deploying GPT-PANELIN across all platforms**

Version: 3.3  
Last Updated: 2026-02-17

---

## Table of Contents

1. [Pre-Deployment Preparation](#pre-deployment-preparation)
2. [GPT (OpenAI) Deployment Checklist](#gpt-openai-deployment-checklist)
3. [Docker Local Deployment Checklist](#docker-local-deployment-checklist)
4. [GCP Cloud Run Deployment Checklist](#gcp-cloud-run-deployment-checklist)
5. [MCP Server Configuration Checklist](#mcp-server-configuration-checklist)
6. [Post-Deployment Validation](#post-deployment-validation)
7. [Production Readiness Checklist](#production-readiness-checklist)

---

## Pre-Deployment Preparation

### Repository Setup
- [ ] Clone repository: `git clone https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3`
- [ ] Checkout correct branch (usually `main`)
- [ ] Verify all files present: `ls -la`
- [ ] Check repository status: `git status`

### Environment Setup
- [ ] Python 3.11 installed: `python --version`
- [ ] Virtual environment created: `python3 -m venv venv`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] MCP dependencies installed: `pip install -r mcp/requirements.txt`

### Configuration Files
- [ ] Copy `.env.example` to `.env`: `cp .env.example .env`
- [ ] Edit `.env` with your values
- [ ] Verify KB files present (21 files)
- [ ] Check `Panelin_GPT_config.json` exists
- [ ] Verify `bmc_logo.png` present

### Validation
- [ ] Run file validation: `python validate_gpt_files.py`
- [ ] All validation checks pass
- [ ] No missing files reported
- [ ] File sizes correct (~1.4 MB total)

### Testing
- [ ] Run unit tests: `pytest mcp/tests/test_handlers.py -v`
- [ ] All tests pass
- [ ] No critical errors in logs
- [ ] Coverage acceptable (>80% recommended)

---

## GPT (OpenAI) Deployment Checklist

### Pre-requisites
- [ ] ChatGPT Plus or Enterprise account
- [ ] Access to OpenAI GPT Builder (https://chat.openai.com/gpts/editor)
- [ ] All 21 KB files validated

### Configuration Generation
- [ ] Run autoconfiguration: `python autoconfig_gpt.py`
- [ ] Answer "yes" to approval prompt
- [ ] Verify `GPT_Deploy_Package/` created
- [ ] Check 5 files generated:
  - [ ] `gpt_deployment_config.json` (complete config)
  - [ ] `openai_gpt_config.json` (OpenAI format)
  - [ ] `DEPLOYMENT_GUIDE.md` (step-by-step guide)
  - [ ] `QUICK_REFERENCE.txt` (quick reference)
  - [ ] `validation_report.json` (validation results)

### Alternative: GitHub Actions
- [ ] Navigate to Actions tab
- [ ] Select "Generate GPT Configuration" workflow
- [ ] Click "Run workflow"
- [ ] Wait for completion (~1 minute)
- [ ] Download `gpt-deployment-package` artifact
- [ ] Extract to local directory

### Review Configuration
- [ ] Open `validation_report.json`
- [ ] Verify all files found: `"all_files_found": true`
- [ ] Check total size: `"total_size_mb": ~1.4`
- [ ] Review `DEPLOYMENT_GUIDE.md` for upload instructions
- [ ] Read `QUICK_REFERENCE.txt` for phase order

### Upload Phase 1 - Master KB (4 files)
- [ ] Open OpenAI GPT Builder
- [ ] Click "Configure" → "Knowledge"
- [ ] Upload `BMC_Base_Conocimiento_GPT-2.json`
- [ ] Upload `bromyros_pricing_master.json`
- [ ] Upload `accessories_catalog.json`
- [ ] Upload `bom_rules.json`
- [ ] **PAUSE 2-3 minutes** (critical!)

### Upload Phase 2 - Optimized Lookups (3 files)
- [ ] Upload `bromyros_pricing_gpt_optimized.json`
- [ ] Upload `shopify_catalog_v1.json`
- [ ] Upload `shopify_catalog_index_v1.csv`
- [ ] **PAUSE 2 minutes**

### Upload Phase 3 - Validation (2 files)
- [ ] Upload `BMC_Base_Unificada_v4.json`
- [ ] Upload `panelin_truth_bmcuruguay_web_only_v2.json`
- [ ] **PAUSE 1 minute**

### Upload Phase 4 - Documentation (9 files)
- [ ] Upload `PANELIN_KNOWLEDGE_BASE_GUIDE.md`
- [ ] Upload `PANELIN_QUOTATION_PROCESS.md`
- [ ] Upload `PANELIN_TRAINING_GUIDE.md`
- [ ] Upload `GPT_PDF_INSTRUCTIONS.md`
- [ ] Upload `GPT_INSTRUCTIONS_PRICING.md`
- [ ] Upload `panelin_context_consolidacion_sin_backend.md`
- [ ] Upload `Instrucciones GPT.rtf`
- [ ] Upload `quotation_calculator_v3.py`
- [ ] Upload `Aleros -2.rtf`
- [ ] **PAUSE 1 minute**

### Upload Phase 5 - Supporting Files (2 files)
- [ ] Upload `perfileria_index.json`
- [ ] Upload `corrections_log.json`
- [ ] **PAUSE 1 minute**

### Upload Phase 6 - Assets (1 file)
- [ ] Upload `bmc_logo.png`
- [ ] Verify all 21 files uploaded

### Configure GPT Settings
- [ ] Set name: "Panelin - BMC Assistant Pro"
- [ ] Set description (from `Panelin_GPT_config.json`)
- [ ] Copy instructions from `openai_gpt_config.json` → `instructions` field
- [ ] Set conversation starters (6 starters from config)

### Enable Capabilities
- [ ] Enable Web Browsing
- [ ] Enable Code Interpreter
- [ ] Enable Image Generation (DALL-E)
- [ ] Enable Canvas

### Test GPT
- [ ] Start new conversation
- [ ] Test: "Necesito una cotización para Isopanel EPS 50mm"
- [ ] Verify: GPT asks for area, luz, uso
- [ ] Test: Price check for "BROMYROS ISOROOF PIR 100mm"
- [ ] Verify: Pricing data retrieved correctly
- [ ] Test: "Genera un PDF para cotización"
- [ ] Verify: PDF generation instructions provided
- [ ] Test: "/estado" command
- [ ] Verify: SOP command works

### Publish
- [ ] Review all settings one final time
- [ ] Click "Publish" or "Update"
- [ ] Choose sharing option (Only me / Anyone with link / Public)
- [ ] Copy GPT URL
- [ ] Save GPT ID for future updates

### Documentation
- [ ] Record GPT URL
- [ ] Note deployment date
- [ ] Save any custom configurations made
- [ ] Update internal documentation

---

## Docker Local Deployment Checklist

### Pre-requisites
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker-compose --version`
- [ ] Docker daemon running: `docker ps`
- [ ] `.env` file configured

### Build Image
- [ ] Review `Dockerfile`
- [ ] Check base image: `python:3.11-slim`
- [ ] Build image: `docker build -t gpt-panelin:latest .`
- [ ] Build completes without errors
- [ ] Image size reasonable (<500 MB recommended)
- [ ] Verify image created: `docker images | grep gpt-panelin`

### Configure Docker Compose
- [ ] Review `docker-compose.yml`
- [ ] Update environment variables if needed
- [ ] Configure volume mounts (KB files)
- [ ] Set port mappings (8000, 9090)
- [ ] Configure resource limits (CPU, memory)
- [ ] Set restart policy

### Start Services
- [ ] Start in detached mode: `docker-compose up -d`
- [ ] Check container status: `docker-compose ps`
- [ ] Verify container is "healthy" (not just "up")
- [ ] Wait 30 seconds for health check

### Verify Logs
- [ ] View logs: `docker-compose logs -f panelin-bot`
- [ ] No critical errors
- [ ] MCP server started successfully
- [ ] KB files loaded
- [ ] Port 8000 bound successfully

### Test Endpoints
- [ ] Health check: `curl http://localhost:8000/health`
- [ ] Metrics: `curl http://localhost:9090/metrics`
- [ ] MCP server responding
- [ ] KB data accessible

### Test Functionality
- [ ] Test price check tool
- [ ] Test BOM calculation
- [ ] Test catalog search
- [ ] Verify KB file read access
- [ ] Test PDF generation (if applicable)

### Volume Verification
- [ ] Check KB volumes mounted: `docker exec gpt-panelin-v32 ls -la /app/*.json`
- [ ] Logs directory writable
- [ ] PDF output directory writable
- [ ] Corrections log writable

### Resource Monitoring
- [ ] Check CPU usage: `docker stats gpt-panelin-v32`
- [ ] Check memory usage
- [ ] Verify within limits (2GB max)
- [ ] No memory leaks observed

---

## GCP Cloud Run Deployment Checklist

### GCP Project Setup
- [ ] GCP project created
- [ ] Project ID noted: `PROJECT_ID`
- [ ] Billing enabled
- [ ] `gcloud` CLI installed: `gcloud --version`
- [ ] Authenticated: `gcloud auth login`
- [ ] Project set: `gcloud config set project PROJECT_ID`

### Terraform Infrastructure

#### Initialize Terraform
- [ ] Navigate to terraform directory: `cd terraform`
- [ ] Initialize: `terraform init`
- [ ] No errors during initialization
- [ ] Provider plugins downloaded

#### Configure Variables
- [ ] Create `terraform.tfvars` file
- [ ] Set `project_id`
- [ ] Set `region` (default: us-central1)
- [ ] Set `db_root_password` (strong password)

#### Plan Infrastructure
- [ ] Run plan: `terraform plan`
- [ ] Review planned changes
- [ ] Verify all resources correct:
  - [ ] Cloud SQL instance
  - [ ] Database
  - [ ] Service account
  - [ ] IAM bindings
  - [ ] Artifact Registry
  - [ ] Secret Manager secret
- [ ] No unexpected changes

#### Apply Infrastructure
- [ ] Apply: `terraform apply`
- [ ] Type "yes" to confirm
- [ ] Wait for completion (~10-15 minutes)
- [ ] No errors during apply
- [ ] Note outputs:
  - [ ] Cloud SQL connection name
  - [ ] Service account email
  - [ ] Artifact Registry URL

### Enable APIs
- [ ] Cloud Run API enabled
- [ ] Cloud SQL Admin API enabled
- [ ] Secret Manager API enabled
- [ ] Cloud Build API enabled
- [ ] Artifact Registry API enabled
- [ ] IAM API enabled

### Service Account Configuration
- [ ] Service account created: `cloud-run-service-account`
- [ ] Roles assigned:
  - [ ] `roles/secretmanager.secretAccessor`
  - [ ] `roles/cloudsql.client`
  - [ ] `roles/run.invoker`
- [ ] Cloud Build service account has `roles/run.developer`

### Cloud SQL Setup
- [ ] Instance created: `web-app-db`
- [ ] PostgreSQL 16
- [ ] Database created: `app_database`
- [ ] User created: `postgres`
- [ ] Password set securely
- [ ] Private IP only (no public access)
- [ ] Backups enabled (daily at 3 AM UTC)
- [ ] Point-in-time recovery enabled

### Secret Manager
- [ ] Secret created: `db-secret`
- [ ] Secret version created with DB credentials
- [ ] Service account has access

### Artifact Registry
- [ ] Repository created: `cloud-run-repo`
- [ ] Format: Docker
- [ ] Region: us-central1

### Build and Push Images

#### Backend Service
- [ ] Navigate to backend: `cd backend`
- [ ] Build: `docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/backend-service:latest .`
- [ ] Authenticate Docker: `gcloud auth configure-docker us-central1-docker.pkg.dev`
- [ ] Push: `docker push us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/backend-service:latest`
- [ ] Image pushed successfully

#### Frontend Service
- [ ] Navigate to frontend: `cd frontend`
- [ ] Build: `docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/frontend-service:latest .`
- [ ] Push: `docker push us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/frontend-service:latest`
- [ ] Image pushed successfully

### Cloud Build Deployment
- [ ] Review `cloudbuild.yaml`
- [ ] Update PROJECT_ID if hardcoded
- [ ] Submit build: `gcloud builds submit --config cloudbuild.yaml`
- [ ] Build completes successfully
- [ ] Images pushed to Artifact Registry
- [ ] Services deployed to Cloud Run

### Verify Cloud Run Services

#### Backend Service
- [ ] Service deployed: `gcloud run services list --region=us-central1`
- [ ] Service name: `backend-service`
- [ ] Image correct
- [ ] Cloud SQL instance connected
- [ ] Environment variables set
- [ ] Service account assigned
- [ ] Ingress: Internal only
- [ ] Get service URL: `gcloud run services describe backend-service --region=us-central1 --format='value(status.url)'`

#### Frontend Service
- [ ] Service deployed
- [ ] Service name: `frontend-service`
- [ ] Image correct
- [ ] Backend URL set in env vars
- [ ] Service account assigned
- [ ] Ingress: Internal and Cloud Load Balancing
- [ ] Get service URL

### Test Services
- [ ] Backend health: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" BACKEND_URL/health`
- [ ] Frontend health: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" FRONTEND_URL/health`
- [ ] Services respond correctly
- [ ] No 500 errors
- [ ] Logs clean

### Database Initialization
- [ ] Connect to Cloud SQL via proxy (if needed)
- [ ] Run database migrations
- [ ] Seed initial data (if applicable)
- [ ] Verify tables created

### Configure Logging
- [ ] Cloud Logging enabled
- [ ] Log sink created (if needed)
- [ ] Log-based metrics created
- [ ] Logs visible in Cloud Console

### Configure Monitoring
- [ ] Cloud Monitoring enabled
- [ ] Uptime checks created
- [ ] Alerts configured:
  - [ ] Service down
  - [ ] High error rate
  - [ ] High latency
  - [ ] Resource exhaustion

### Security Configuration
- [ ] IAM policies reviewed
- [ ] Least privilege enforced
- [ ] No public access to backend
- [ ] Secrets stored in Secret Manager
- [ ] No hardcoded credentials
- [ ] VPC access configured (if needed)

---

## MCP Server Configuration Checklist

### Configuration File
- [ ] `mcp/config/mcp_server_config.json` exists
- [ ] Version: 0.3.0
- [ ] Transport methods defined: stdio, sse
- [ ] 23 tools listed

### Tool Definitions
- [ ] All tool JSON files present in `mcp/tools/`
- [ ] `price_check.json`
- [ ] `catalog_search.json`
- [ ] `bom_calculate.json`
- [ ] `report_error.json`
- [ ] `quotation_store.json`
- [ ] `persist_conversation.json`
- [ ] `register_correction.json`
- [ ] `save_customer.json`
- [ ] `lookup_customer.json`
- [ ] `batch_bom_calculate.json`
- [ ] `bulk_price_check.json`
- [ ] `full_quotation.json`
- [ ] `task_status.json`
- [ ] `task_result.json`
- [ ] `task_list.json`
- [ ] `task_cancel.json`

### KB Paths Configuration
- [ ] All KB paths in config point to correct files
- [ ] `pricing_master`: `../bromyros_pricing_master.json`
- [ ] `pricing_optimized`: `../bromyros_pricing_gpt_optimized.json`
- [ ] `accessories`: `../accessories_catalog.json`
- [ ] `bom_rules`: `../bom_rules.json`
- [ ] `shopify_catalog`: `../shopify_catalog_v1.json`
- [ ] `shopify_index`: `../shopify_catalog_index_v1.csv`
- [ ] `core_kb`: `../BMC_Base_Conocimiento_GPT-2.json`
- [ ] `corrections_log`: `../corrections_log.json`

### Wolf API Configuration
- [ ] Base URL env var: `WOLF_API_URL`
- [ ] API key env var: `WOLF_API_KEY`
- [ ] KB write password env var: `WOLF_KB_WRITE_PASSWORD`
- [ ] Default URL correct
- [ ] Timeout: 10 seconds

### Start MCP Server
- [ ] Start server: `python -m mcp.server`
- [ ] Server starts without errors
- [ ] KB files loaded successfully
- [ ] Tools registered
- [ ] Server listening on configured port

### Test MCP Tools
- [ ] Price check tool works
- [ ] Catalog search tool works
- [ ] BOM calculate tool works
- [ ] Background tasks working
- [ ] Wolf API write operations work (with password)

### Claude Desktop Setup (Optional)
- [ ] Run: `python setup_claude_mcp.py`
- [ ] Claude Desktop config updated
- [ ] MCP server auto-starts with Claude
- [ ] 6 deployment tools available in Claude

---

## Post-Deployment Validation

### Functional Testing

#### GPT Testing (if deployed)
- [ ] GPT accessible via URL
- [ ] Can start new conversation
- [ ] Quotation workflow works end-to-end
- [ ] Price lookup accurate
- [ ] BOM calculation correct
- [ ] PDF generation functional
- [ ] SOP commands work (/estado, /checkpoint, etc.)
- [ ] Training mode functional
- [ ] Sales evaluation functional

#### Docker Testing (if deployed)
- [ ] Container running and healthy
- [ ] Health endpoint responds
- [ ] Metrics endpoint responds
- [ ] MCP server accessible
- [ ] KB files readable
- [ ] Logs being written
- [ ] PDF generation works
- [ ] No memory leaks over time

#### GCP Testing (if deployed)
- [ ] Backend service healthy
- [ ] Frontend service healthy
- [ ] Database connection working
- [ ] Secrets accessible
- [ ] Cloud SQL accessible
- [ ] Logging working
- [ ] Monitoring working
- [ ] Alerts configured

### Performance Testing
- [ ] Response times acceptable (<2s for simple queries)
- [ ] BOM calculation completes in reasonable time
- [ ] Large file uploads handled
- [ ] Concurrent requests handled
- [ ] No timeouts under normal load
- [ ] Memory usage stable
- [ ] CPU usage reasonable

### Security Testing
- [ ] No secrets in logs
- [ ] No secrets in error messages
- [ ] API authentication working
- [ ] Rate limiting functional (if enabled)
- [ ] CORS configured correctly
- [ ] No SQL injection vulnerabilities
- [ ] Input validation working
- [ ] Wolf API write requires password

### Data Integrity
- [ ] Pricing data accurate
- [ ] BOM calculations verified against manual calculations
- [ ] Accessories included correctly
- [ ] Autoportancia validation working
- [ ] IVA calculations correct (22% included in unit prices)
- [ ] PDF outputs formatted correctly

### Monitoring
- [ ] Logs visible and searchable
- [ ] Metrics being collected
- [ ] Dashboards created (if applicable)
- [ ] Alerts triggering correctly
- [ ] Error tracking functional

---

## Production Readiness Checklist

### Documentation
- [ ] Deployment documentation complete
- [ ] API documentation available
- [ ] Configuration documented
- [ ] Troubleshooting guide available
- [ ] Runbooks created for common operations
- [ ] Disaster recovery plan documented

### Backup and Recovery
- [ ] Database backups enabled
- [ ] Backup retention configured (7 days minimum)
- [ ] Point-in-time recovery tested
- [ ] Recovery procedure documented
- [ ] KB files backed up
- [ ] Disaster recovery plan tested

### Security
- [ ] All secrets in Secret Manager (not hardcoded)
- [ ] Service accounts using least privilege
- [ ] No public access to sensitive services
- [ ] Firewall rules configured
- [ ] SSL/TLS enabled
- [ ] Security scanning completed (CodeQL)
- [ ] Vulnerability assessment done
- [ ] No known CVEs in dependencies

### Monitoring and Alerting
- [ ] Uptime monitoring configured
- [ ] Error rate monitoring
- [ ] Latency monitoring
- [ ] Resource utilization monitoring
- [ ] Log-based alerts configured
- [ ] On-call rotation established
- [ ] Escalation procedures defined

### Performance
- [ ] Load testing completed
- [ ] Performance benchmarks established
- [ ] Scaling strategy defined
- [ ] Caching configured (if applicable)
- [ ] CDN configured (if applicable)

### Compliance
- [ ] Data privacy requirements met
- [ ] GDPR compliance (if applicable)
- [ ] Data retention policies enforced
- [ ] Audit logging enabled
- [ ] Terms of service compliance (OpenAI ToS)

### Support
- [ ] Support contact information documented
- [ ] Issue tracking system set up
- [ ] Support procedures documented
- [ ] Knowledge base articles created
- [ ] Training materials available

### Maintenance
- [ ] Update procedures documented
- [ ] Rollback procedures tested
- [ ] Maintenance windows scheduled
- [ ] Change management process defined
- [ ] Version control strategy documented

---

## Sign-off

### Deployment Approval
- [ ] Technical lead approval
- [ ] Security review completed
- [ ] Operations team notified
- [ ] Documentation reviewed
- [ ] Rollback plan approved

### Post-Deployment
- [ ] Deployment date recorded: __________
- [ ] Deployed by: __________
- [ ] Version deployed: __________
- [ ] Post-deployment review scheduled
- [ ] Lessons learned documented

---

## Notes

Use this space for deployment-specific notes:

```
Deployment Date: _________________
Deployed By: _____________________
Environment: _____________________
Special Configurations: __________
___________________________________
___________________________________
___________________________________
Issues Encountered: ______________
___________________________________
___________________________________
___________________________________
```

---

*Deployment Checklist v3.3 - Last updated: 2026-02-17*
