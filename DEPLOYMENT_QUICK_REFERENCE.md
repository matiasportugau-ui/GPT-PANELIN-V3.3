# GPT-PANELIN V3.3 - Quick Deployment Reference

**One-Page Quick Reference for All Deployment Configurations**

---

## 🚀 Deployment Targets

| Target | Command | Time | Prerequisites |
|--------|---------|------|---------------|
| **GPT (OpenAI)** | `python autoconfig_gpt.py` | 1 min auto + 15 min manual | ChatGPT Plus/Enterprise |
| **Docker Local** | `docker-compose up -d` | 5 min | Docker installed |
| **GCP Cloud Run** | `terraform apply` | 20-30 min | GCP account, gcloud CLI |
| **Claude Desktop** | `python setup_claude_mcp.py` | 5 min | Claude Desktop app |

---

## 📦 GPT Deployment (OpenAI)

### Generate Configuration
```bash
python autoconfig_gpt.py
# Output: GPT_Deploy_Package/ (5 files)
```

### Files Generated
- `gpt_deployment_config.json` - Complete config
- `openai_gpt_config.json` - OpenAI format
- `DEPLOYMENT_GUIDE.md` - Step-by-step guide
- `QUICK_REFERENCE.txt` - Quick ref
- `validation_report.json` - Validation results

### Upload to OpenAI
1. Visit https://chat.openai.com/gpts/editor
2. Upload 21 files in 6 phases (with 2-3 min pauses)
3. Configure name, description, instructions
4. Enable capabilities: Web Browsing, Code Interpreter, Image Generation, Canvas
5. Test and publish

**Time**: ~15 minutes manual upload

---

## 🐳 Docker Deployment

### Local Development
```bash
# Build image
docker build -t gpt-panelin:latest .

# Run with compose
docker-compose up -d

# View logs
docker-compose logs -f panelin-bot

# Stop
docker-compose down
```

### Configuration Files
- `Dockerfile` - Main MCP server image
- `docker-compose.yml` - Compose configuration
- `.env` - Environment variables (copy from `.env.example`)

### Ports
- `8000` - MCP server
- `9090` - Metrics

---

## ☁️ GCP Cloud Run Deployment

### Infrastructure Setup (Terraform)
```bash
cd terraform

# Initialize
terraform init

# Deploy infrastructure
terraform apply \
  -var="project_id=YOUR_PROJECT" \
  -var="db_root_password=YOUR_PASSWORD"
```

### Application Deployment (Cloud Build)
```bash
# Deploy via Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Or trigger from GitHub (automated)
# Push to main branch triggers cloudbuild.yaml
```

### Services Deployed
- **Backend**: `backend-service` (internal, Cloud SQL connection)
- **Frontend**: `frontend-service` (load balancer accessible)

### Infrastructure Created
- Cloud SQL PostgreSQL 16 (`web-app-db`)
- Artifact Registry (`cloud-run-repo`)
- Service Account with IAM roles
- Secret Manager secrets
- Cloud Run services

---

## 🔧 Environment Configuration

### Copy and Configure
```bash
cp .env.example .env
# Edit .env with your values
```

### Critical Variables
```bash
# OpenAI
OPENAI_API_KEY=your_key_here

# Wolf API (v3.4 - KB Write)
WOLF_API_URL=https://panelin-api-642127786762.us-central1.run.app
WOLF_API_KEY=your_key_here
WOLF_KB_WRITE_PASSWORD=change_from_default

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## 🧪 Testing & Validation

### Validate Configuration
```bash
# Validate GPT files
python validate_gpt_files.py

# Package GPT files
python package_gpt_files.py

# Run tests
pytest mcp/tests/test_handlers.py -v

# Test MCP server locally
python -m mcp.server
```

### Health Checks
```bash
# Docker health
docker ps  # Check HEALTH status

# Cloud Run health
curl https://YOUR-SERVICE-URL/health

# MCP server health
curl http://localhost:8000/health
```

---

## 📋 Configuration Files Reference

### GPT Configuration
| File | Purpose | Location |
|------|---------|----------|
| `Panelin_GPT_config.json` | Master GPT config | Root |
| `GPT_Deploy_Package/*` | Deployment package | Generated |

### Docker Configuration
| File | Purpose | Location |
|------|---------|----------|
| `Dockerfile` | MCP server image | Root |
| `docker-compose.yml` | Compose config | Root |
| `backend/Dockerfile` | Backend service | backend/ |
| `frontend/Dockerfile` | Frontend service | frontend/ |
| `.dockerignore` | Exclude files | Root |

### GCP Configuration
| File | Purpose | Location |
|------|---------|----------|
| `cloudbuild.yaml` | Cloud Build CI/CD | Root |
| `terraform/main.tf` | Infrastructure | terraform/ |
| `terraform/variables.tf` | Terraform vars | terraform/ |
| `terraform/outputs.tf` | Outputs | terraform/ |

### MCP Configuration
| File | Purpose | Location |
|------|---------|----------|
| `mcp/config/mcp_server_config.json` | MCP server config | mcp/config/ |
| `mcp/tools/*.json` | Tool definitions | mcp/tools/ |

### Environment
| File | Purpose | Location |
|------|---------|----------|
| `.env.example` | Template | Root |
| `.env` | Your config (not committed) | Root |

---

## 🔄 GitHub Actions Workflows

### Trigger Workflows
```bash
# Manual trigger: Generate GPT Config
# Go to: Actions -> Generate GPT Configuration -> Run workflow

# Automatic triggers:
# - Push to main (with KB changes) -> GPT config generation
# - Push/PR -> CI/CD tests
# - Daily schedule -> Health checks
```

### Workflows
| Workflow | File | Trigger |
|----------|------|---------|
| CI/CD | `ci-cd.yml` | Push, PR |
| GPT Config | `generate-gpt-config.yml` | Push (KB changes), manual |
| Tests | `test.yml` | Push, PR |
| MCP Tests | `mcp-tests.yml` | Changes to mcp/ |
| Health Check | `health-check.yml` | Daily, manual |

---

## 📚 Knowledge Base Files (21 files)

### Master KB (Phase 1 - 4 files)
```
BMC_Base_Conocimiento_GPT-2.json
bromyros_pricing_master.json
accessories_catalog.json
bom_rules.json
```

### Optimized Lookups (Phase 2 - 3 files)
```
bromyros_pricing_gpt_optimized.json
shopify_catalog_v1.json
shopify_catalog_index_v1.csv
```

### Validation (Phase 3 - 2 files)
```
BMC_Base_Unificada_v4.json
panelin_truth_bmcuruguay_web_only_v2.json
```

### Documentation (Phase 4 - 9 files)
```
PANELIN_KNOWLEDGE_BASE_GUIDE.md
PANELIN_QUOTATION_PROCESS.md
PANELIN_TRAINING_GUIDE.md
GPT_PDF_INSTRUCTIONS.md
GPT_INSTRUCTIONS_PRICING.md
panelin_context_consolidacion_sin_backend.md
Instrucciones GPT.rtf
quotation_calculator_v3.py
Aleros -2.rtf
```

### Supporting (Phase 5 - 2 files)
```
perfileria_index.json
corrections_log.json
```

### Assets (Phase 6 - 1 file)
```
bmc_logo.png
```

---

## 🛠️ Common Commands

### Development
```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r mcp/requirements.txt

# Run tests
pytest mcp/tests/ -v --cov

# Lint code
flake8 mcp/
black mcp/ --check
```

### Docker
```bash
# Build
docker build -t gpt-panelin:latest .

# Run
docker run -p 8000:8000 --env-file .env gpt-panelin:latest

# Compose
docker-compose up -d       # Start
docker-compose logs -f     # Logs
docker-compose down        # Stop
docker-compose ps          # Status
```

### GCP
```bash
# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Deploy services
gcloud builds submit --config cloudbuild.yaml

# View logs
gcloud run services logs read backend-service --region=us-central1

# List services
gcloud run services list --region=us-central1
```

---

## 🚨 Troubleshooting

### Issue: GPT autoconfiguration fails
**Solution**: `python validate_gpt_files.py`

### Issue: Docker build fails
**Solution**: Check all KB files are in root directory

### Issue: MCP server won't start
**Solution**: Check paths in `mcp/config/mcp_server_config.json`

### Issue: Cloud Run deployment fails
**Solution**: Verify service account IAM roles in Terraform

### Issue: Wolf API write fails
**Solution**: Check `WOLF_API_KEY` and `WOLF_KB_WRITE_PASSWORD` in .env

---

## 📞 Support

**Repository**: https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3  
**Issues**: https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3/issues  
**Documentation**: See `DEPLOYMENT_CONFIG.md` for complete reference

---

## ✅ Pre-Deployment Checklist

- [ ] All KB files present and validated
- [ ] `.env` configured with all required variables
- [ ] Secrets configured (API keys, passwords)
- [ ] Tests passing
- [ ] Docker image builds successfully
- [ ] Infrastructure deployed (if using GCP)
- [ ] Health checks configured

---

## 📈 Deployment Time Estimates

| Activity | Time | Type |
|----------|------|------|
| Generate GPT config | 1 min | Automated |
| Upload to OpenAI | 15 min | Manual |
| Docker local setup | 5 min | Automated |
| Terraform setup | 10 min | Automated |
| Cloud Build deploy | 10-15 min | Automated |
| **Total (all platforms)** | **41-46 min** | Mixed |

---

*Quick Reference v3.3 - Last updated: 2026-02-17*
