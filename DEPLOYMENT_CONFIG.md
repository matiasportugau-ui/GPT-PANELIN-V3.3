# GPT-PANELIN V3.3 - Deployment Configuration Manifest

**Version**: 3.3  
**Last Updated**: 2026-02-17  
**Status**: ✅ Complete  

This document provides a comprehensive overview of ALL configuration files required for deploying GPT-PANELIN across different environments and platforms.

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [GPT (OpenAI) Deployment](#gpt-openai-deployment)
3. [Docker Deployment](#docker-deployment)
4. [GCP Cloud Run Deployment](#gcp-cloud-run-deployment)
5. [MCP Server Configuration](#mcp-server-configuration)
6. [Environment Configuration](#environment-configuration)
7. [CI/CD Workflows](#cicd-workflows)
8. [Infrastructure as Code (Terraform)](#infrastructure-as-code-terraform)
9. [Deployment Checklist](#deployment-checklist)

---

## Deployment Overview

GPT-PANELIN V3.3 supports multiple deployment targets:

| Deployment Target | Purpose | Configuration Files | Time Required |
|------------------|---------|---------------------|---------------|
| **OpenAI GPT** | Custom GPT in ChatGPT | `GPT_Deploy_Package/` | 15-20 min |
| **Docker Local** | Local development/testing | `Dockerfile`, `docker-compose.yml` | 5-10 min |
| **GCP Cloud Run** | Production cloud deployment | `cloudbuild.yaml`, `terraform/` | 20-30 min |
| **MCP Server** | Model Context Protocol integration | `mcp/config/` | 5 min |
| **Claude Desktop** | Claude integration | `setup_claude_mcp.py` | 5 min |

---

## GPT (OpenAI) Deployment

### Configuration Files

```
GPT_Deploy_Package/
├── gpt_deployment_config.json       # Complete GPT configuration
├── openai_gpt_config.json           # OpenAI-compatible format
├── DEPLOYMENT_GUIDE.md              # Step-by-step deployment guide
├── QUICK_REFERENCE.txt              # Quick reference card
└── validation_report.json           # Pre-deployment validation results
```

### Base Configuration

- **File**: `Panelin_GPT_config.json`
- **Purpose**: Master GPT configuration (name, description, instructions, capabilities)
- **Version**: 2.5 Canonical
- **KB Version**: 7.0

### Knowledge Base Files (21 files total)

#### Phase 1 - Master KB (4 files)
```
BMC_Base_Conocimiento_GPT-2.json    # 523 KB - Main knowledge base
bromyros_pricing_master.json        # 189 KB - Complete pricing catalog
accessories_catalog.json            # 28 KB - 70+ accessories with prices
bom_rules.json                      # 85 KB - BOM calculation rules + autoportancia
```

#### Phase 2 - Optimized Lookups (3 files)
```
bromyros_pricing_gpt_optimized.json # 156 KB - Fast SKU/family search
shopify_catalog_v1.json             # 234 KB - Product catalog with descriptions
shopify_catalog_index_v1.csv        # 45 KB - Quick lookup index
```

#### Phase 3 - Validation (2 files)
```
BMC_Base_Unificada_v4.json          # 178 KB - Historical validation
panelin_truth_bmcuruguay_web_only_v2.json  # 89 KB - Web pricing validation
```

#### Phase 4 - Documentation (9 files)
```
PANELIN_KNOWLEDGE_BASE_GUIDE.md     # KB hierarchy and usage rules
PANELIN_QUOTATION_PROCESS.md        # Step-by-step quotation workflow
PANELIN_TRAINING_GUIDE.md           # Training and evaluation guide
GPT_PDF_INSTRUCTIONS.md             # PDF generation instructions
GPT_INSTRUCTIONS_PRICING.md         # Pricing lookup instructions
panelin_context_consolidacion_sin_backend.md  # Context consolidation
Instrucciones GPT.rtf               # Legacy instructions (reference)
quotation_calculator_v3.py          # Python calculator code
Aleros -2.rtf                       # Technical documentation
```

#### Phase 5 - Supporting Files (2 files)
```
perfileria_index.json               # Perfileria product index
corrections_log.json                # KB corrections log
```

#### Phase 6 - Assets (1 file)
```
bmc_logo.png                        # BMC Uruguay branding logo
```

### Generation Script

```bash
# Run autoconfiguration tool
python autoconfig_gpt.py

# Or use GitHub Actions
# Workflow: .github/workflows/generate-gpt-config.yml
# Trigger: Manual dispatch or push to main with KB changes
```

### Important Notes

⚠️ **No API Available**: OpenAI does NOT provide an API for Custom GPT deployment. Manual upload required.

⏱️ **Upload Time**: 15-20 minutes with required pauses between phases

📦 **Package Size**: ~1.4 MB total (21 files)

🔐 **Access**: Requires ChatGPT Plus or Enterprise account

---

## Docker Deployment

### Configuration Files

#### Main Dockerfile
- **File**: `Dockerfile`
- **Base Image**: `python:3.11-slim`
- **Multi-stage**: ✅ Yes (builder + production)
- **Non-root User**: `panelin` (UID 1000)
- **Ports**: 8000 (MCP server), 9090 (metrics)

#### Docker Compose
- **File**: `docker-compose.yml`
- **Services**: `panelin-bot` (+ optional Redis)
- **Volumes**: KB files (read-only), logs, PDF outputs
- **Network**: `panelin-network`
- **Resource Limits**: 2 CPU / 2GB RAM

#### Backend Service Dockerfile
- **File**: `backend/Dockerfile`
- **Purpose**: GCP Cloud Run backend service
- **Base Image**: `python:3.11-slim`
- **Port**: 8080
- **Healthcheck**: `/health` endpoint

#### Frontend Service Dockerfile
- **File**: `frontend/Dockerfile`
- **Purpose**: GCP Cloud Run frontend service
- **Base Image**: `python:3.11-slim`
- **Port**: 8080
- **Healthcheck**: `/health` endpoint

### Docker Ignore
- **File**: `.dockerignore`
- **Purpose**: Exclude unnecessary files from Docker context

### Deployment Commands

```bash
# Build image
docker build -t gpt-panelin:latest .

# Run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f panelin-bot

# Stop services
docker-compose down
```

---

## GCP Cloud Run Deployment

### Configuration Files

#### Cloud Build Configuration
- **File**: `cloudbuild.yaml`
- **Purpose**: Automated CI/CD pipeline
- **Triggers**: GitHub repository changes
- **Steps**:
  1. Build backend service image
  2. Build frontend service image
  3. Push images to Artifact Registry
  4. Deploy backend to Cloud Run
  5. Deploy frontend to Cloud Run

#### Build Configuration Details
```yaml
Project: $PROJECT_ID
Region: us-central1
Artifact Registry: cloud-run-repo
Machine Type: N1_HIGHCPU_8
```

#### Cloud Run Services

**Backend Service**:
- Name: `backend-service`
- Image: `us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/backend-service`
- Platform: managed
- Region: us-central1
- Auth: No public access (internal only)
- Cloud SQL: Enabled (`$PROJECT_ID:us-central1:web-app-db`)
- Ingress: Internal only

**Frontend Service**:
- Name: `frontend-service`
- Image: `us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/frontend-service`
- Platform: managed
- Region: us-central1
- Auth: No public access (requires authentication)
- Ingress: Internal + Cloud Load Balancing

### Deployment Commands

```bash
# Deploy via Cloud Build (automated)
gcloud builds submit --config cloudbuild.yaml

# Manual deployment
gcloud run deploy backend-service \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/backend-service:latest \
  --platform=managed \
  --region=us-central1

gcloud run deploy frontend-service \
  --image=us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/frontend-service:latest \
  --platform=managed \
  --region=us-central1
```

---

## Infrastructure as Code (Terraform)

### Configuration Files

```
terraform/
├── main.tf         # Main infrastructure definition
├── variables.tf    # Variable declarations
└── outputs.tf      # Output values
```

### Resources Defined

#### main.tf

**1. Enable Required APIs**:
- Cloud Run API
- Cloud SQL Admin API
- Secret Manager API
- Compute Engine API
- Cloud Build API
- Artifact Registry API
- Service Networking API
- VPC Access API
- IAM API

**2. Service Account**:
- Name: `cloud-run-service-account`
- Roles:
  - `roles/secretmanager.secretAccessor`
  - `roles/cloudsql.client`
  - `roles/run.invoker`

**3. Cloud SQL PostgreSQL**:
- Instance: `web-app-db`
- Version: PostgreSQL 16
- Region: us-central1
- Tier: db-f1-micro
- Features:
  - Automatic backups (daily at 3 AM UTC)
  - Point-in-time recovery
  - Maintenance window (Sunday 4 AM UTC)
  - Private IP only (no public access)

**4. Database**:
- Name: `app_database`
- User: `postgres`

**5. Secret Manager**:
- Secret: `db-secret`
- Contains: DB credentials (username, password, database, host)

**6. Artifact Registry**:
- Repository: `cloud-run-repo`
- Format: Docker
- Region: us-central1

#### variables.tf

Required variables:
- `project_id`: GCP project ID
- `region`: Deployment region (default: us-central1)
- `db_root_password`: PostgreSQL root password

#### outputs.tf

Outputs:
- Cloud SQL connection name
- Database name
- Service account email
- Artifact Registry URL

### Deployment Commands

```bash
# Initialize Terraform
cd terraform
terraform init

# Plan deployment
terraform plan -var="project_id=YOUR_PROJECT_ID" \
              -var="db_root_password=YOUR_PASSWORD"

# Apply infrastructure
terraform apply -var="project_id=YOUR_PROJECT_ID" \
               -var="db_root_password=YOUR_PASSWORD"

# Destroy infrastructure (when needed)
terraform destroy
```

---

## MCP Server Configuration

### Configuration Files

#### MCP Server Config
- **File**: `mcp/config/mcp_server_config.json`
- **Version**: 0.3.0
- **Transport**: stdio, sse
- **Tools**: 23 tools defined

#### Tool Definitions (in `mcp/tools/`)
```
price_check.json                 # Price lookup by SKU/family/type
catalog_search.json              # Search product catalog
bom_calculate.json               # Calculate BOM with accessories
report_error.json                # Error reporting
quotation_store.json             # Store quotation in memory
persist_conversation.json        # Wolf API: Save conversation
register_correction.json         # Wolf API: Register KB correction
save_customer.json               # Wolf API: Save customer data
lookup_customer.json             # Wolf API: Retrieve customer
batch_bom_calculate.json         # Background: Batch BOM calculation
bulk_price_check.json            # Background: Bulk price checks
full_quotation.json              # Background: Complete quotation generation
task_status.json                 # Background: Task status check
task_result.json                 # Background: Task result retrieval
task_list.json                   # Background: List all tasks
task_cancel.json                 # Background: Cancel task
```

#### Knowledge Base Paths
```json
{
  "pricing_master": "../bromyros_pricing_master.json",
  "pricing_optimized": "../bromyros_pricing_gpt_optimized.json",
  "accessories": "../accessories_catalog.json",
  "bom_rules": "../bom_rules.json",
  "shopify_catalog": "../shopify_catalog_v1.json",
  "shopify_index": "../shopify_catalog_index_v1.csv",
  "core_kb": "../BMC_Base_Conocimiento_GPT-2.json",
  "corrections_log": "../corrections_log.json"
}
```

#### Wolf API Configuration
```json
{
  "base_url_env": "WOLF_API_URL",
  "api_key_env": "WOLF_API_KEY",
  "default_base_url": "https://panelin-api-642127786762.us-central1.run.app",
  "kb_write_password_env": "WOLF_KB_WRITE_PASSWORD",
  "timeout_seconds": 10
}
```

### Claude Desktop Setup

- **File**: `setup_claude_mcp.py`
- **Purpose**: Configure Claude Desktop for automatic MCP server startup
- **Provides**: 6 deployment tools for Claude
- **Run**: `python setup_claude_mcp.py`

---

## Environment Configuration

### Environment Variables File

- **File**: `.env.example`
- **Copy to**: `.env` (DO NOT commit .env to version control!)

### Required Variables

#### OpenAI Configuration
```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7
```

#### MCP Server Configuration
```bash
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
MCP_SERVER_LOG_LEVEL=INFO
MCP_SERVER_TRANSPORT=stdio
```

#### Application Settings
```bash
APP_NAME=GPT-PANELIN-V3.2
APP_VERSION=3.2.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

#### Knowledge Base Paths
```bash
KB_PRICING_MASTER=bromyros_pricing_master.json
KB_PRICING_OPTIMIZED=bromyros_pricing_gpt_optimized.json
KB_ACCESSORIES=accessories_catalog.json
KB_BOM_RULES=bom_rules.json
KB_SHOPIFY_CATALOG=shopify_catalog_v1.json
KB_CORE=BMC_Base_Conocimiento_GPT-2.json
KB_CORRECTIONS_LOG=corrections_log.json
```

#### Wolf API Configuration (v3.4)
```bash
WOLF_API_URL=https://panelin-api-642127786762.us-central1.run.app
WOLF_API_KEY=                        # Required: Obtain from admin
WOLF_KB_WRITE_PASSWORD=              # Required: Change from default in production
```

#### Security Settings
```bash
API_KEY_REQUIRED=true
API_KEY=
CORS_ENABLED=false
CORS_ORIGINS=*
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

#### IVA Configuration
```bash
IVA_RATE=0.22                        # 22% IVA for Uruguay
```

#### Feature Flags
```bash
ENABLE_BACKGROUND_TASKS=true
ENABLE_BATCH_OPERATIONS=true
ENABLE_FULL_QUOTATION=true
ENABLE_ERROR_REPORTING=true
ENABLE_QUOTATION_STORE=true
ENABLE_CACHE=true
```

---

## CI/CD Workflows

### GitHub Actions Workflows

```
.github/workflows/
├── ci-cd.yml                    # Main CI/CD pipeline
├── generate-gpt-config.yml      # GPT configuration generation
├── test.yml                     # Unit and integration tests
├── mcp-tests.yml                # MCP server tests
├── health-check.yml             # Repository health checks
└── evolucionador-daily.yml      # Daily automated improvements
```

### Workflow Details

#### 1. CI/CD Pipeline (`ci-cd.yml`)
- **Trigger**: Push to main, pull requests
- **Steps**:
  - Checkout code
  - Setup Python 3.11
  - Install dependencies
  - Run linting (flake8, black)
  - Run tests with coverage
  - Build Docker image
  - Push to registry (if main branch)

#### 2. Generate GPT Config (`generate-gpt-config.yml`)
- **Trigger**: Push to main (KB changes), manual dispatch
- **Steps**:
  - Validate GPT files
  - Generate configuration package
  - Upload artifacts (30-day retention)
  - Create deployment summary
- **Output**: `GPT_Deploy_Package/` as artifact
- **Time**: ~1 minute

#### 3. Test Suite (`test.yml`)
- **Trigger**: Push, pull requests
- **Steps**:
  - Unit tests
  - Integration tests
  - MCP handler tests
  - Ecosystem validation tests
- **Coverage**: Tracks code coverage
- **Matrix**: Multiple Python versions (if configured)

#### 4. MCP Tests (`mcp-tests.yml`)
- **Trigger**: Changes to `mcp/` directory
- **Steps**:
  - Install MCP dependencies
  - Run MCP-specific tests
  - Validate tool schemas

#### 5. Health Check (`health-check.yml`)
- **Trigger**: Schedule (daily), manual dispatch
- **Steps**:
  - Check KB file integrity
  - Validate pricing data consistency
  - Check for outdated dependencies
  - Generate health report

#### 6. Evolucionador Daily (`evolucionador-daily.yml`)
- **Trigger**: Schedule (daily)
- **Purpose**: Automated KB improvements
- **Steps**:
  - Run Evolucionador analysis
  - Generate improvement suggestions
  - Create issues for review

---

## Deployment Checklist

### Pre-Deployment Checklist

- [ ] All KB files validated (`python validate_gpt_files.py`)
- [ ] Environment variables configured (`.env` file)
- [ ] Secrets configured (API keys, passwords)
- [ ] Docker images built and tested locally
- [ ] Unit tests passing (`pytest`)
- [ ] Integration tests passing
- [ ] Security scan completed (CodeQL)
- [ ] Dependencies up to date (no vulnerabilities)

### GPT Deployment Checklist

- [ ] Run `python autoconfig_gpt.py` to generate package
- [ ] Download `GPT_Deploy_Package/` from GitHub Actions artifact (if using workflow)
- [ ] Verify all 21 files in package
- [ ] Review `validation_report.json`
- [ ] Open OpenAI GPT Builder (https://chat.openai.com/gpts/editor)
- [ ] Upload files following phase order (with pauses)
- [ ] Configure GPT settings (name, description, instructions)
- [ ] Enable capabilities (Web Browsing, Code Interpreter, Image Generation, Canvas)
- [ ] Test quotation workflow
- [ ] Test PDF generation
- [ ] Verify pricing accuracy
- [ ] Publish GPT (when ready)

### Docker Deployment Checklist

- [ ] `.env` file configured
- [ ] Build Docker image: `docker build -t gpt-panelin:latest .`
- [ ] Test image locally: `docker run -p 8000:8000 gpt-panelin:latest`
- [ ] Verify health check passes
- [ ] Configure docker-compose.yml volumes
- [ ] Start services: `docker-compose up -d`
- [ ] Check logs: `docker-compose logs -f`
- [ ] Test MCP endpoints
- [ ] Verify KB file access
- [ ] Test quotation generation

### GCP Cloud Run Deployment Checklist

- [ ] GCP project created
- [ ] Terraform initialized
- [ ] Infrastructure deployed (`terraform apply`)
- [ ] Cloud SQL instance provisioned
- [ ] Database initialized
- [ ] Secrets created in Secret Manager
- [ ] Service account configured with correct roles
- [ ] Artifact Registry repository created
- [ ] Docker images pushed to Artifact Registry
- [ ] Backend service deployed to Cloud Run
- [ ] Frontend service deployed to Cloud Run
- [ ] Cloud SQL connection configured
- [ ] Environment variables set on Cloud Run services
- [ ] Health checks passing
- [ ] Test internal endpoints
- [ ] Configure Cloud Load Balancer (if needed)
- [ ] Setup custom domain (if needed)
- [ ] Enable monitoring and logging

### Post-Deployment Validation

- [ ] Health endpoints responding (`/health`)
- [ ] MCP server accessible
- [ ] Price check tool working
- [ ] BOM calculation accurate
- [ ] PDF generation functional
- [ ] Wolf API write operations working (with password)
- [ ] Customer data persistence verified
- [ ] Background tasks processing
- [ ] Error reporting functional
- [ ] Logs being captured
- [ ] Metrics being collected
- [ ] Alerts configured (if production)

---

## Quick Start Commands

### Generate All Deployment Configurations

```bash
# 1. Generate GPT deployment package
python autoconfig_gpt.py

# 2. Validate all files
python validate_gpt_files.py

# 3. Build Docker image
docker build -t gpt-panelin:latest .

# 4. Test locally with Docker Compose
docker-compose up -d

# 5. Deploy to GCP (if configured)
cd terraform
terraform init
terraform apply

# 6. Trigger GitHub Actions workflow (manual)
# Go to: https://github.com/your-repo/actions/workflows/generate-gpt-config.yml
# Click "Run workflow"
```

---

## Support Documentation

### Primary Documentation Files

- `DEPLOYMENT.md` - High-level deployment guide
- `README.md` - Repository overview and getting started
- `AUTOCONFIG_QUICK_START.md` - Quick start for GPT autoconfiguration
- `GPT_AUTOCONFIG_GUIDE.md` - Detailed GPT configuration guide
- `GITHUB_ACTIONS_GPT_CONFIG.md` - GitHub Actions automation guide
- `CLAUDE_MCP_SETUP_GUIDE.md` - Claude Desktop MCP setup
- `CLAUDE_COMPUTER_USE_AUTOMATION.md` - Claude Computer Use deployment automation
- `GCP_README.md` - GCP deployment guide
- `GCP_PHASE1_IMPLEMENTATION.md` - GCP Phase 1 implementation details
- `BACKGROUND_TASKS_GUIDE.md` - Background tasks configuration
- `MCP_QUICK_START.md` - MCP server quick start

### Technical Guides

- `PANELIN_KNOWLEDGE_BASE_GUIDE.md` - KB hierarchy and usage
- `PANELIN_QUOTATION_PROCESS.md` - Quotation workflow
- `PANELIN_TRAINING_GUIDE.md` - Training and evaluation
- `GPT_PDF_INSTRUCTIONS.md` - PDF generation guide
- `GPT_INSTRUCTIONS_PRICING.md` - Pricing lookup guide

---

## Troubleshooting

### Common Issues

**Issue**: GPT autoconfiguration fails
- **Solution**: Run `python validate_gpt_files.py` to check for missing files

**Issue**: Docker build fails
- **Solution**: Ensure all KB files are present in repository root

**Issue**: MCP server not starting
- **Solution**: Check `mcp/config/mcp_server_config.json` paths are correct

**Issue**: Cloud Run deployment fails
- **Solution**: Verify service account has correct IAM roles

**Issue**: Wolf API write operations fail
- **Solution**: Check `WOLF_API_KEY` and `WOLF_KB_WRITE_PASSWORD` are set correctly

### Logs and Debugging

```bash
# Docker logs
docker-compose logs -f panelin-bot

# Cloud Run logs
gcloud run services logs read backend-service --region=us-central1

# Check MCP server status
curl http://localhost:8000/health

# Validate KB files
python validate_gpt_files.py

# Test MCP handlers
pytest mcp/tests/test_handlers.py -v
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.3 | 2026-02-17 | Complete deployment configuration manifest created |
| 3.2 | 2026-02-14 | Wolf API KB Write integration |
| 3.1 | 2026-02-06 | KB v7.0 with BOM rules and accessories |
| 3.0 | 2026-01-15 | MCP server v0.3.0, background tasks |

---

## Contacts and Support

**Repository**: https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3  
**Issues**: https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3/issues  

For deployment support, please create an issue with:
- Deployment target (GPT, Docker, GCP)
- Error messages or logs
- Steps to reproduce
- Environment details

---

*Last updated: 2026-02-17 by GPT-PANELIN Deployment Team*
