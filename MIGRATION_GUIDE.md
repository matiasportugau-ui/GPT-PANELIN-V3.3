# Panelin v5.0 — Guía de Migración Agno

## Arquitectura

```
Usuario → Agno Agent (backend posee el agente)
    ↓
Backend controla el razonamiento (NO OpenAI)
    ↓
Agno Workflow (7 Steps Python puro + 1 LLM)
    ↓
Pipeline determinístico, no decidido por LLM
    ↓
PostgresDb (Cloud SQL) → Memoria conversacional
MCPTools → 18 tools existentes (SSE)
Playground → UI + API endpoints automáticos
```

## Estructura de Archivos

```
src/
├── core/
│   └── config.py           # pydantic-settings, single source of truth
├── quotation/
│   ├── service.py           # QuotationService wrapping panelin_v4 engine
│   └── tools.py             # Agno @tool wrappers para domain functions
├── agent/
│   ├── workflow.py          # 7 Steps determinísticos + 1 LLM respond
│   └── panelin.py           # Agent conversacional principal
├── integrations/
│   ├── mcp_connector.py     # MCPTools SSE connector
│   ├── sheets.py            # Google Sheets tools
│   └── pdf.py               # PDF generation tool
├── auth/
│   └── jwt_auth.py          # JWT + RBAC (reemplaza API key)
├── knowledge/
│   └── product_kb.py        # JSONKnowledgeBase + PgVector
├── guardrails/
│   └── price_guardrail.py   # Output validation (nunca inventar precios)
└── app.py                   # Entry point (Agno Playground)
```

## Fases de Migración

### FASE 0: Bugs Críticos Corregidos ✅

| Bug | Archivo | Fix |
|-----|---------|-----|
| Wall BOM dimensions swap | `bom_engine.py` | Panel count uses `length_m` for walls, `width_m` for roofs |
| Pricing ignora sub_familia | `pricing_engine.py` | Added sub_familia matching filter |
| CORS allow_origins=["*"] | `wolf_api/main.py` | Reads from `CORS_ALLOWED_ORIGINS` env var |
| set_cotizacion_url broken indentation | `wolf_api/main.py` | Fixed nested if blocks |
| Terraform deletion_protection | `terraform/main.tf` | Set to `true` |
| Missing .gitignore entries | `.gitignore` | Added `*.tfstate*`, `*.tfvars`, `.terraform/` |

### FASE 1: Core Domain Layer ✅

- `src/core/config.py` — pydantic-settings con todas las variables de entorno
- `src/quotation/service.py` — Wrapper stateless del engine panelin_v4
- `src/quotation/tools.py` — 5 tools: quote_from_text, validate, check_price, search_accessories, sai_score

### FASE 2: Agno Agent + Workflow ✅

- `src/agent/workflow.py` — 8 Steps:
  - Steps 1-7: Python puro ($0.00 cada uno)
  - Step 8: LLM agent (~$0.02) para formatear respuesta
- `src/agent/panelin.py` — Agent con tools, PostgresDb, instrucciones en español

### FASE 3: Integration Layer ✅

- `src/integrations/mcp_connector.py` — MCPTools SSE con filtering por toolset
- `src/integrations/sheets.py` — Google Sheets tools (read/write/search/update)
- `src/integrations/pdf.py` — PDF generation con fallback ReportLab

### FASE 4: Production ✅

- `src/auth/jwt_auth.py` — JWT con RBAC (admin/sales/viewer/agent)
- `Dockerfile.agno` — Multi-stage Docker build para Cloud Run
- `docker-compose.agno.yml` — Dev stack con PostgreSQL (pgvector:16) + MCP server
- `requirements-agno.txt` — Dependencias Agno

### FASE 5: Advanced ✅

- `src/knowledge/product_kb.py` — PgVector hybrid search para productos
- `src/guardrails/price_guardrail.py` — Validación de precios contra KB

## Deployment

### Local Development

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con OPENAI_API_KEY, etc.

# 2. Levantar con Docker Compose
docker compose -f docker-compose.agno.yml up -d

# 3. Verificar
curl http://localhost:8080/health
```

### Cloud Run

```bash
# 1. Build imagen
docker build -f Dockerfile.agno -t panelin-agno .

# 2. Tag y push a Artifact Registry
docker tag panelin-agno us-central1-docker.pkg.dev/PROJECT/cloud-run-repo/panelin-agno:latest
docker push us-central1-docker.pkg.dev/PROJECT/cloud-run-repo/panelin-agno:latest

# 3. Deploy
gcloud run deploy panelin-agno \
  --image=us-central1-docker.pkg.dev/PROJECT/cloud-run-repo/panelin-agno:latest \
  --platform=managed \
  --region=us-central1 \
  --port=8080 \
  --set-env-vars="PANELIN_ENVIRONMENT=production" \
  --set-env-vars="PANELIN_DEFAULT_MODEL_ID=gpt-4o" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest" \
  --set-secrets="DB_PASSWORD=db-secret:latest" \
  --add-cloudsql-instances=PROJECT:REGION:INSTANCE \
  --service-account=cloud-run-service-account@PROJECT.iam.gserviceaccount.com
```

## API Endpoints

| Endpoint | Descripción |
|----------|-------------|
| `GET /` | Info del servicio |
| `GET /health` | Health check |
| `GET /docs` | OpenAPI docs |
| `POST /v1/agents/Panelin/runs` | Ejecutar el agente |
| `POST /v1/workflows/PanelinQuotationWorkflow/runs` | Ejecutar el workflow |
| `POST /api/v4/quote` | Engine v4 directo (backward compat) |
| `/legacy/*` | Wolf API original (backward compat) |

## Costo por Cotización

| Componente | Costo |
|------------|-------|
| Steps 1-7 (Python puro) | $0.00 |
| Step 8 (LLM respond) | ~$0.02 |
| **Total** | **~$0.02** |

## Tests

```bash
# Todos los tests (79 total: 34 engine + 45 integration)
PYTHONPATH=/workspace python -m pytest panelin_v4/tests/ tests/integration/ -v

# Solo engine (no requiere dependencias Agno)
python -m pytest panelin_v4/tests/ -v

# Solo integration
PYTHONPATH=/workspace python -m pytest tests/integration/ -v
```
