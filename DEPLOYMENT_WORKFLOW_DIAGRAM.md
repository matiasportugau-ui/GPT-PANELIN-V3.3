# GPT-PANELIN V3.3 - Deployment Workflow Diagram

**Visual Guide to Deployment Processes**

Version: 3.3  
Last Updated: 2026-02-17

---

## Deployment Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GPT-PANELIN V3.3                              │
│                   Deployment Architecture                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ├─────────────────────────────────────────┐
                               │                                         │
                    ┌──────────▼──────────┐                  ┌──────────▼──────────┐
                    │   GPT (OpenAI)      │                  │   Infrastructure     │
                    │   Custom GPT        │                  │   Deployment         │
                    └──────────┬──────────┘                  └──────────┬──────────┘
                               │                                         │
                   ┌───────────┴───────────┐                ┌───────────┴───────────┐
                   │                       │                │                       │
        ┌──────────▼──────────┐ ┌─────────▼────────┐ ┌─────▼──────┐  ┌──────────▼──────┐
        │  Knowledge Base     │ │  Configuration   │ │   Docker   │  │   GCP Cloud Run │
        │  (21 files)         │ │  & Instructions  │ │   Local    │  │   Production    │
        └─────────────────────┘ └──────────────────┘ └────────────┘  └─────────────────┘
```

---

## 1. GPT (OpenAI) Deployment Workflow

```
START: Generate GPT Configuration
│
├─► [AUTOMATED] Generate Config Package
│   │
│   ├─► python autoconfig_gpt.py
│   │   │
│   │   ├─► Load base config (Panelin_GPT_config.json)
│   │   ├─► Validate 21 KB files
│   │   ├─► Generate deployment configs
│   │   └─► Create GPT_Deploy_Package/
│   │       ├─► gpt_deployment_config.json
│   │       ├─► openai_gpt_config.json
│   │       ├─► DEPLOYMENT_GUIDE.md
│   │       ├─► QUICK_REFERENCE.txt
│   │       └─► validation_report.json
│   │
│   └─► OR: GitHub Actions Workflow
│       │
│       ├─► Trigger: Push to main (KB changes) or Manual
│       ├─► Run: .github/workflows/generate-gpt-config.yml
│       ├─► Validate files
│       ├─► Generate package
│       └─► Upload artifact (30-day retention)
│
├─► [MANUAL] Upload to OpenAI GPT Builder
│   │
│   ├─► Open: https://chat.openai.com/gpts/editor
│   │
│   ├─► Phase 1: Master KB (4 files)
│   │   ├─► BMC_Base_Conocimiento_GPT-2.json
│   │   ├─► bromyros_pricing_master.json
│   │   ├─► accessories_catalog.json
│   │   ├─► bom_rules.json
│   │   └─► PAUSE 2-3 minutes ⏸️
│   │
│   ├─► Phase 2: Optimized Lookups (3 files)
│   │   ├─► bromyros_pricing_gpt_optimized.json
│   │   ├─► shopify_catalog_v1.json
│   │   ├─► shopify_catalog_index_v1.csv
│   │   └─► PAUSE 2 minutes ⏸️
│   │
│   ├─► Phase 3: Validation (2 files)
│   │   ├─► BMC_Base_Unificada_v4.json
│   │   ├─► panelin_truth_bmcuruguay_web_only_v2.json
│   │   └─► PAUSE 1 minute ⏸️
│   │
│   ├─► Phase 4: Documentation (9 files)
│   │   ├─► PANELIN_KNOWLEDGE_BASE_GUIDE.md
│   │   ├─► PANELIN_QUOTATION_PROCESS.md
│   │   ├─► PANELIN_TRAINING_GUIDE.md
│   │   ├─► GPT_PDF_INSTRUCTIONS.md
│   │   ├─► GPT_INSTRUCTIONS_PRICING.md
│   │   ├─► panelin_context_consolidacion_sin_backend.md
│   │   ├─► Instrucciones GPT.rtf
│   │   ├─► quotation_calculator_v3.py
│   │   ├─► Aleros -2.rtf
│   │   └─► PAUSE 1 minute ⏸️
│   │
│   ├─► Phase 5: Supporting Files (2 files)
│   │   ├─► perfileria_index.json
│   │   ├─► corrections_log.json
│   │   └─► PAUSE 1 minute ⏸️
│   │
│   └─► Phase 6: Assets (1 file)
│       └─► bmc_logo.png
│
├─► [MANUAL] Configure GPT Settings
│   ├─► Set name: "Panelin - BMC Assistant Pro"
│   ├─► Set description
│   ├─► Copy instructions
│   ├─► Add conversation starters (6)
│   └─► Enable capabilities
│       ├─► ✅ Web Browsing
│       ├─► ✅ Code Interpreter
│       ├─► ✅ Image Generation
│       └─► ✅ Canvas
│
├─► [VALIDATION] Test GPT
│   ├─► Test quotation workflow
│   ├─► Test price lookups
│   ├─► Test BOM calculations
│   ├─► Test PDF generation
│   └─► Test SOP commands
│
└─► [PUBLISH] Deploy to Production
    ├─► Review all settings
    ├─► Click "Publish" or "Update"
    ├─► Choose sharing option
    ├─► Copy GPT URL
    └─► Document deployment

END: GPT Live in Production
Time: ~1 min automated + ~15 min manual = ~16 min total
```

---

## 2. Docker Local Deployment Workflow

```
START: Docker Local Deployment
│
├─► [PREPARATION] Setup Environment
│   ├─► Clone repository
│   ├─► Install Docker & Docker Compose
│   ├─► Copy .env.example to .env
│   └─► Configure environment variables
│
├─► [BUILD] Create Docker Image
│   │
│   ├─► docker build -t gpt-panelin:latest .
│   │   │
│   │   ├─► Stage 1: Builder
│   │   │   ├─► FROM python:3.11-slim
│   │   │   ├─► Install build dependencies
│   │   │   ├─► Copy requirements.txt files
│   │   │   └─► Install Python packages
│   │   │
│   │   └─► Stage 2: Production
│   │       ├─► FROM python:3.11-slim
│   │       ├─► Copy Python packages from builder
│   │       ├─► Copy application code
│   │       ├─► Copy KB files (21 files)
│   │       ├─► Create non-root user (panelin:1000)
│   │       ├─► Set environment variables
│   │       └─► Configure health check
│   │
│   └─► Verify image created
│
├─► [CONFIGURE] Docker Compose
│   ├─► Review docker-compose.yml
│   ├─► Configure volumes
│   │   ├─► KB files (read-only)
│   │   ├─► Logs directory
│   │   └─► PDF output directory
│   ├─► Configure ports (8000, 9090)
│   └─► Set resource limits (2 CPU, 2GB RAM)
│
├─► [DEPLOY] Start Services
│   │
│   ├─► docker-compose up -d
│   │   │
│   │   ├─► Create network: panelin-network
│   │   ├─► Create volumes
│   │   ├─► Start container: gpt-panelin-v32
│   │   │   ├─► Load environment variables
│   │   │   ├─► Mount KB files
│   │   │   ├─► Start MCP server on port 8000
│   │   │   ├─► Start metrics server on port 9090
│   │   │   └─► Run health check (30s interval)
│   │   │
│   │   └─► Container status: healthy ✅
│   │
│   └─► docker-compose ps (verify running)
│
├─► [VALIDATION] Test Deployment
│   ├─► curl http://localhost:8000/health
│   ├─► curl http://localhost:9090/metrics
│   ├─► Test price check tool
│   ├─► Test BOM calculation
│   ├─► Test catalog search
│   └─► Review logs: docker-compose logs -f
│
└─► [MONITORING] Ongoing Operations
    ├─► Monitor logs: docker-compose logs -f panelin-bot
    ├─► Check stats: docker stats gpt-panelin-v32
    ├─► Restart if needed: docker-compose restart
    └─► Stop: docker-compose down

END: Docker Service Running Locally
Time: ~5-10 minutes
```

---

## 3. GCP Cloud Run Deployment Workflow

```
START: GCP Cloud Run Deployment
│
├─► [INFRASTRUCTURE] Terraform Setup
│   │
│   ├─► cd terraform/
│   │
│   ├─► terraform init
│   │   └─► Download provider plugins
│   │
│   ├─► terraform plan
│   │   ├─► Review planned resources
│   │   └─► Verify configuration
│   │
│   └─► terraform apply
│       │
│       ├─► Enable Required APIs (9 APIs)
│       │   ├─► Cloud Run API
│       │   ├─► Cloud SQL Admin API
│       │   ├─► Secret Manager API
│       │   ├─► Compute Engine API
│       │   ├─► Cloud Build API
│       │   ├─► Artifact Registry API
│       │   ├─► Service Networking API
│       │   ├─► VPC Access API
│       │   └─► IAM API
│       │
│       ├─► Create Service Account
│       │   ├─► Name: cloud-run-service-account
│       │   └─► Grant IAM Roles
│       │       ├─► roles/secretmanager.secretAccessor
│       │       ├─► roles/cloudsql.client
│       │       └─► roles/run.invoker
│       │
│       ├─► Provision Cloud SQL
│       │   ├─► Instance: web-app-db
│       │   ├─► Version: PostgreSQL 16
│       │   ├─► Tier: db-f1-micro
│       │   ├─► Region: us-central1
│       │   ├─► Private IP only
│       │   ├─► Database: app_database
│       │   ├─► User: postgres
│       │   ├─► Enable backups (daily 3 AM UTC)
│       │   └─► Point-in-time recovery
│       │
│       ├─► Create Secret Manager Secret
│       │   ├─► Secret: db-secret
│       │   └─► Store DB credentials
│       │
│       └─► Create Artifact Registry
│           ├─► Repository: cloud-run-repo
│           ├─► Format: Docker
│           └─► Region: us-central1
│
├─► [BUILD] Docker Images
│   │
│   ├─► Backend Service
│   │   ├─► cd backend/
│   │   ├─► docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/backend-service:latest .
│   │   └─► docker push us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/backend-service:latest
│   │
│   └─► Frontend Service
│       ├─► cd frontend/
│       ├─► docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/frontend-service:latest .
│       └─► docker push us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/frontend-service:latest
│
├─► [DEPLOY] Cloud Build Pipeline
│   │
│   ├─► gcloud builds submit --config cloudbuild.yaml
│   │   │
│   │   ├─► Step 1: Build backend image
│   │   ├─► Step 2: Push backend to Artifact Registry
│   │   ├─► Step 3: Build frontend image
│   │   ├─► Step 4: Push frontend to Artifact Registry
│   │   ├─► Step 5: Deploy backend to Cloud Run
│   │   │   ├─► Service: backend-service
│   │   │   ├─► Region: us-central1
│   │   │   ├─► Platform: managed
│   │   │   ├─► Attach Cloud SQL instance
│   │   │   ├─► Mount secrets from Secret Manager
│   │   │   ├─► Set environment variables
│   │   │   ├─► Configure service account
│   │   │   └─► Ingress: Internal only
│   │   │
│   │   └─► Step 6: Deploy frontend to Cloud Run
│   │       ├─► Service: frontend-service
│   │       ├─► Region: us-central1
│   │       ├─► Platform: managed
│   │       ├─► Set backend URL
│   │       ├─► Configure service account
│   │       └─► Ingress: Internal + Cloud Load Balancing
│   │
│   └─► OR: Manual Deployment
│       ├─► gcloud run deploy backend-service ...
│       └─► gcloud run deploy frontend-service ...
│
├─► [CONFIGURE] Post-Deployment Setup
│   ├─► Initialize database
│   │   ├─► Connect via Cloud SQL Proxy
│   │   ├─► Run migrations
│   │   └─► Seed initial data
│   │
│   ├─► Configure Monitoring
│   │   ├─► Enable Cloud Logging
│   │   ├─► Create uptime checks
│   │   ├─► Configure alerts
│   │   └─► Set up dashboards
│   │
│   └─► Configure Load Balancer (optional)
│       ├─► Create HTTPS load balancer
│       ├─► Add frontend as backend
│       ├─► Configure SSL certificate
│       └─► Set up custom domain
│
├─► [VALIDATION] Test Services
│   ├─► Backend health check
│   │   └─► curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" $BACKEND_URL/health
│   │
│   ├─► Frontend health check
│   │   └─► curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" $FRONTEND_URL/health
│   │
│   ├─► Database connectivity
│   ├─► Secret access
│   └─► Review logs in Cloud Console
│
└─► [MONITORING] Production Operations
    ├─► Monitor Cloud Run metrics
    ├─► Review Cloud Logging logs
    ├─► Track error rates
    ├─► Monitor resource usage
    └─► Respond to alerts

END: GCP Cloud Run Services Running
Time: ~20-30 minutes
```

---

## 4. CI/CD Pipeline Workflow

```
START: GitHub Push or PR
│
├─► [TRIGGER] GitHub Actions Workflows
│   │
│   ├─► Workflow: CI/CD (.github/workflows/ci-cd.yml)
│   │   ├─► Trigger: Push to main, Pull Request
│   │   ├─► Setup Python 3.11
│   │   ├─► Install dependencies
│   │   ├─► Run linting (flake8, black)
│   │   ├─► Run tests with coverage
│   │   ├─► Build Docker image
│   │   └─► Push to registry (if main branch)
│   │
│   ├─► Workflow: Test Suite (.github/workflows/test.yml)
│   │   ├─► Trigger: Push, Pull Request
│   │   ├─► Unit tests
│   │   ├─► Integration tests
│   │   ├─► MCP handler tests
│   │   └─► Ecosystem validation tests
│   │
│   ├─► Workflow: Generate GPT Config (.github/workflows/generate-gpt-config.yml)
│   │   ├─► Trigger: Push to main (KB changes), Manual
│   │   ├─► Validate GPT files
│   │   ├─► Run autoconfig_gpt.py
│   │   ├─► Generate deployment package
│   │   ├─► Upload artifacts (30-day retention)
│   │   └─► Create deployment summary
│   │
│   ├─► Workflow: MCP Tests (.github/workflows/mcp-tests.yml)
│   │   ├─► Trigger: Changes to mcp/ directory
│   │   ├─► Install MCP dependencies
│   │   ├─► Run MCP-specific tests
│   │   └─► Validate tool schemas
│   │
│   ├─► Workflow: Health Check (.github/workflows/health-check.yml)
│   │   ├─► Trigger: Daily schedule, Manual
│   │   ├─► Check KB file integrity
│   │   ├─► Validate pricing consistency
│   │   ├─► Check dependencies
│   │   └─► Generate health report
│   │
│   └─► Workflow: Evolucionador Daily (.github/workflows/evolucionador-daily.yml)
│       ├─► Trigger: Daily schedule
│       ├─► Run Evolucionador analysis
│       ├─► Generate improvements
│       └─► Create issues for review
│
└─► [RESULTS] Workflow Outputs
    ├─► Test results
    ├─► Coverage reports
    ├─► Lint results
    ├─► Build artifacts
    ├─► GPT deployment package
    └─► Status badges

END: CI/CD Pipeline Complete
```

---

## 5. MCP Server Integration Workflow

```
START: MCP Server Configuration
│
├─► [CONFIGURATION] Setup MCP Server
│   │
│   ├─► Configure mcp/config/mcp_server_config.json
│   │   ├─► Set version: 0.3.0
│   │   ├─► Configure transport: stdio, sse
│   │   ├─► List 23 tools
│   │   ├─► Set KB file paths
│   │   └─► Configure Wolf API
│   │
│   ├─► Define Tool Schemas (mcp/tools/)
│   │   ├─► price_check.json
│   │   ├─► catalog_search.json
│   │   ├─► bom_calculate.json
│   │   ├─► Wolf API tools (3)
│   │   └─► Background task tools (7)
│   │
│   └─► Configure Environment (.env)
│       ├─► WOLF_API_URL
│       ├─► WOLF_API_KEY
│       ├─► WOLF_KB_WRITE_PASSWORD
│       └─► MCP_SERVER_PORT=8000
│
├─► [DEPLOYMENT] Start MCP Server
│   │
│   ├─► Via Docker
│   │   └─► docker-compose up -d panelin-bot
│   │
│   ├─► Via Python
│   │   └─► python -m mcp.server
│   │
│   └─► Via Claude Desktop
│       └─► python setup_claude_mcp.py
│
├─► [INTEGRATION] Connect Clients
│   │
│   ├─► OpenAI Custom GPT
│   │   ├─► Upload KB files (21 files)
│   │   └─► Configure GPT with instructions
│   │
│   ├─► Claude Desktop
│   │   ├─► Run setup_claude_mcp.py
│   │   ├─► Restart Claude Desktop
│   │   └─► Access 6 deployment tools
│   │
│   └─► Direct MCP Client
│       ├─► Connect via stdio/sse
│       └─► Call MCP tools via API
│
├─► [TOOLS] Available MCP Tools
│   │
│   ├─► Core Tools
│   │   ├─► price_check: Price lookup by SKU/family/type
│   │   ├─► catalog_search: Search product catalog
│   │   ├─► bom_calculate: Calculate BOM with accessories
│   │   ├─► report_error: Error reporting
│   │   └─► quotation_store: Store quotation in memory
│   │
│   ├─► Wolf API Tools (KB Write)
│   │   ├─► persist_conversation: Save conversation (requires password)
│   │   ├─► register_correction: Register KB correction (requires password)
│   │   ├─► save_customer: Save customer data (requires password)
│   │   └─► lookup_customer: Retrieve customer (no password)
│   │
│   └─► Background Task Tools
│       ├─► batch_bom_calculate: Batch BOM calculations
│       ├─► bulk_price_check: Bulk price checks
│       ├─► full_quotation: Complete quotation generation
│       ├─► task_status: Check task status
│       ├─► task_result: Retrieve task result
│       ├─► task_list: List all tasks
│       └─► task_cancel: Cancel task
│
└─► [VALIDATION] Test MCP Server
    ├─► Test health endpoint
    ├─► Test price check tool
    ├─► Test BOM calculation
    ├─► Test Wolf API tools (with password)
    └─► Test background tasks

END: MCP Server Running and Integrated
```

---

## Configuration File Dependencies

```
                    ┌──────────────────────────────┐
                    │  Panelin_GPT_config.json     │
                    │  (Master GPT Configuration)  │
                    └─────────────┬────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │   Knowledge Base    │    │   Tool Definitions   │
         │   (21 files)        │    │   (23 JSON files)    │
         └──────────┬──────────┘    └──────────┬──────────┘
                    │                           │
         ┌──────────┴──────────┐    ┌──────────┴──────────┐
         │                     │    │                     │
    ┌────▼────┐   ┌────▼────┐ │ ┌──▼──────┐  ┌─────▼────┐
    │  .env   │   │ Docker  │ │ │ MCP     │  │  Wolf    │
    │  vars   │   │ Compose │ │ │ Config  │  │  API     │
    └─────────┘   └─────────┘ │ └─────────┘  └──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
            ┌───────▼──────┐    ┌────────▼───────┐
            │  Terraform   │    │  Cloud Build   │
            │  (main.tf)   │    │  (cloudbuild)  │
            └──────────────┘    └────────────────┘
```

---

## Data Flow During Deployment

```
┌─────────────┐
│  Developer  │
└──────┬──────┘
       │ git push
       ▼
┌─────────────────────────────┐
│  GitHub Repository          │
│  - Code changes             │
│  - KB updates               │
│  - Config modifications     │
└──────┬──────────────────────┘
       │ triggers
       ▼
┌─────────────────────────────┐
│  GitHub Actions Workflows   │
│  - Validate files           │
│  - Run tests                │
│  - Generate configs         │
│  - Build images             │
└──────┬──────────────────────┘
       │
       ├──────────────────┬─────────────────┬───────────────┐
       │                  │                 │               │
       ▼                  ▼                 ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ GPT Package │  │   Docker    │  │   GCP        │  │  Terraform   │
│ Artifact    │  │   Registry  │  │   Artifact   │  │  State       │
│ (Download)  │  │   (Local)   │  │   Registry   │  │              │
└──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘
       │                │                 │                 │
       │ manual         │ docker run      │ deploy          │ apply
       ▼                ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│  OpenAI     │  │   Docker    │  │  Cloud Run   │  │   GCP        │
│  GPT        │  │   Container │  │  Services    │  │   Resources  │
│  Builder    │  │   (Local)   │  │              │  │              │
└─────────────┘  └─────────────┘  └──────────────┘  └──────────────┘
       │                │                 │                 │
       └────────────────┴─────────────────┴─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Production     │
                    │   Services       │
                    │   Running        │
                    └──────────────────┘
```

---

## Deployment Decision Tree

```
                        START
                          │
                          ▼
              ┌───────────────────────┐
              │ What are you          │
              │ deploying?            │
              └───────┬───────────────┘
                      │
        ┏─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    ┌───────┐    ┌────────┐    ┌─────────┐
    │  GPT  │    │ Docker │    │   GCP   │
    │ (AI)  │    │ Local  │    │  Cloud  │
    └───┬───┘    └───┬────┘    └────┬────┘
        │            │               │
        ▼            ▼               ▼
┌───────────────┐ ┌──────────────┐ ┌─────────────────┐
│ Use Case:     │ │ Use Case:    │ │ Use Case:       │
│ - ChatGPT     │ │ - Dev/Test   │ │ - Production    │
│ - End users   │ │ - Local run  │ │ - Scalable      │
│ - No infra    │ │ - Quick test │ │ - Managed       │
└───┬───────────┘ └──────┬───────┘ └────┬────────────┘
    │                    │               │
    ▼                    ▼               ▼
┌───────────────┐ ┌──────────────┐ ┌─────────────────┐
│ Steps:        │ │ Steps:       │ │ Steps:          │
│ 1. Generate   │ │ 1. Build     │ │ 1. Terraform    │
│    config     │ │    image     │ │    apply        │
│ 2. Upload     │ │ 2. Compose   │ │ 2. Build images │
│    21 files   │ │    up        │ │ 3. Deploy CR    │
│ 3. Configure  │ │ 3. Test      │ │ 4. Configure    │
│ 4. Test       │ │              │ │ 5. Monitor      │
│ 5. Publish    │ │              │ │                 │
└───────────────┘ └──────────────┘ └─────────────────┘
        │                │                     │
        └────────────────┴─────────────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │ Deployment  │
                  │  Complete   │
                  └─────────────┘
```

---

## Timeline Comparison

```
Deployment Type         │ Setup Time │ Deploy Time │ Total Time │ Automation
────────────────────────┼────────────┼─────────────┼────────────┼───────────
GPT (OpenAI)            │   1 min    │   15 min    │   16 min   │ Partial
                        │ (auto gen) │  (manual)   │            │ (1 min auto)
────────────────────────┼────────────┼─────────────┼────────────┼───────────
Docker Local            │   2 min    │    3 min    │    5 min   │ Full
                        │            │             │            │
────────────────────────┼────────────┼─────────────┼────────────┼───────────
GCP Cloud Run (first)   │  10 min    │   15 min    │   25 min   │ Full
                        │ (terraform)│ (cloudbuild)│            │
────────────────────────┼────────────┼─────────────┼────────────┼───────────
GCP Cloud Run (update)  │   0 min    │    5 min    │    5 min   │ Full
                        │            │ (cloudbuild)│            │
────────────────────────┴────────────┴─────────────┴────────────┴───────────
```

---

## Support and Troubleshooting

### Common Issues Decision Tree

```
                    Deployment Failed?
                           │
                 ┌─────────┴─────────┐
                 │                   │
           ┌─────▼─────┐      ┌──────▼──────┐
           │ GPT       │      │ Docker/GCP  │
           │ Upload    │      │ Deployment  │
           └─────┬─────┘      └──────┬──────┘
                 │                   │
       ┌─────────┴────────┐   ┌──────┴───────┐
       │                  │   │              │
  ┌────▼────┐      ┌──────▼──┐  ┌───▼────┐  ┌────▼────┐
  │ Files   │      │  Size   │  │ Build  │  │ Runtime │
  │ Missing │      │  Limit  │  │ Error  │  │ Error   │
  └────┬────┘      └──────┬──┘  └───┬────┘  └────┬────┘
       │                  │         │            │
       ▼                  ▼         ▼            ▼
  Run validate       Upload in    Fix          Check
  script             phases       dependencies  logs
```

---

*Deployment Workflow Diagram v3.3 - Last updated: 2026-02-17*
